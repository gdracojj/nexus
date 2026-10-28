from datetime import datetime, timezone
from contextlib import contextmanager
from hashlib import sha256
import json

from sqlalchemy import text

from app.database.connection import obter_engine, obter_session_factory
from app.pncp.client import URL_PNCP


ENDPOINT_PNCP = URL_PNCP
CHAVE_LOCK_COLETA_PNCP = int.from_bytes(b"NEXUSPNC", "big", signed=True)
TAMANHO_LOTE_UPSERT = 250


class ColetaPNCPJaEmAndamentoError(RuntimeError):
    """Já existe uma coleta PNCP ativa neste banco de dados."""


@contextmanager
def lock_coleta_pncp():
    """Limita a uma coleta PNCP simultânea entre processos e workers."""
    conexao = obter_engine().connect()
    bloqueio_adquirido = False
    try:
        bloqueio_adquirido = bool(
            conexao.execute(
                text("SELECT pg_try_advisory_lock(:chave)"),
                {"chave": CHAVE_LOCK_COLETA_PNCP},
            ).scalar_one()
        )
        if not bloqueio_adquirido:
            raise ColetaPNCPJaEmAndamentoError(
                "Já existe uma coleta PNCP em andamento."
            )

        yield
    finally:
        try:
            if bloqueio_adquirido:
                conexao.execute(
                    text("SELECT pg_advisory_unlock(:chave)"),
                    {"chave": CHAVE_LOCK_COLETA_PNCP},
                )
                conexao.commit()
        except Exception:
            # Se o unlock falhar, não devolve ao pool uma conexão que possa
            # manter o lock de sessão ativo.
            conexao.invalidate()
            raise
        finally:
            conexao.close()


def iniciar_execucao(parametros: dict) -> int:
    from app.database.models import SyncExecucao

    with obter_session_factory()() as sessao:
        execucao = SyncExecucao(
            endpoint=ENDPOINT_PNCP,
            parametros=parametros,
            status="executando",
        )
        sessao.add(execucao)
        sessao.commit()
        return execucao.id


def concluir_execucao(
    execucao_id: int,
    registros: list[dict],
    paginas_consultadas: int = 0,
) -> None:
    """Upsert atômico das contratações/payloads e conclusão da execução."""
    from sqlalchemy.dialects.postgresql import insert

    from app.database.models import Licitacao, PncpPayload, SyncExecucao

    agora = datetime.now(timezone.utc)
    with obter_session_factory()() as sessao:
        try:
            # Registros repetidos podem aparecer em páginas diferentes. O
            # último payload vence, sem gerar chaves duplicadas no mesmo lote.
            unicos = {}
            for registro in registros:
                unicos[registro["numero_controle_pncp"]] = registro
            registros_unicos = list(unicos.values())

            for inicio in range(0, len(registros_unicos), TAMANHO_LOTE_UPSERT):
                lote = registros_unicos[inicio:inicio + TAMANHO_LOTE_UPSERT]
                valores_licitacao = []
                payloads_por_controle = {}
                for registro in lote:
                    controle = registro["numero_controle_pncp"]
                    payload = registro["payload"]
                    payload_hash = sha256(
                        json.dumps(
                            payload,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode("utf-8")
                    ).hexdigest()
                    payloads_por_controle[controle] = (payload, payload_hash)
                    valores = {
                        chave: valor
                        for chave, valor in registro.items()
                        if chave != "payload"
                    }
                    valores.update(
                        coletada_em=agora,
                        ultima_execucao_id=execucao_id,
                        atualizada_em=agora,
                    )
                    valores_licitacao.append(valores)

                inserir_licitacoes = insert(Licitacao).values(valores_licitacao)
                atualizar = {
                    coluna: getattr(inserir_licitacoes.excluded, coluna)
                    for coluna in valores_licitacao[0]
                    if coluna not in {"numero_controle_pncp", "coletada_em"}
                }
                ids_por_controle = dict(
                    sessao.execute(
                        inserir_licitacoes.on_conflict_do_update(
                            index_elements=[Licitacao.numero_controle_pncp],
                            set_=atualizar,
                        ).returning(
                            Licitacao.numero_controle_pncp,
                            Licitacao.id,
                        )
                    ).all()
                )

                valores_payload = [
                    {
                        "licitacao_id": ids_por_controle[controle],
                        "payload": payload,
                        "sha256": payload_hash,
                        "recebido_em": agora,
                    }
                    for controle, (payload, payload_hash)
                    in payloads_por_controle.items()
                ]
                inserir_payloads = insert(PncpPayload).values(valores_payload)
                sessao.execute(
                    inserir_payloads.on_conflict_do_update(
                        index_elements=[PncpPayload.licitacao_id],
                        set_={
                            "payload": inserir_payloads.excluded.payload,
                            "sha256": inserir_payloads.excluded.sha256,
                            "recebido_em": inserir_payloads.excluded.recebido_em,
                        },
                        where=PncpPayload.sha256 != inserir_payloads.excluded.sha256,
                    )
                )

            execucao = sessao.get(SyncExecucao, execucao_id)
            execucao.status = "concluida"
            execucao.finalizada_em = agora
            execucao.paginas_consultadas = paginas_consultadas
            execucao.registros_recebidos = len(registros)
            execucao.registros_processados = len(registros)
            execucao.registros_com_erro = 0
            execucao.resumo_falhas = None
            sessao.commit()
        except Exception:
            sessao.rollback()
            raise


def falhar_execucao(
    execucao_id: int,
    erro: Exception,
    recebidos: int = 0,
    erros: int = 1,
    paginas_consultadas: int = 0,
) -> None:
    from app.database.models import SyncExecucao

    with obter_session_factory()() as sessao:
        execucao = sessao.get(SyncExecucao, execucao_id)
        if execucao is not None:
            execucao.status = "falhou"
            execucao.finalizada_em = datetime.now(timezone.utc)
            execucao.paginas_consultadas = paginas_consultadas
            execucao.registros_recebidos = recebidos
            execucao.registros_processados = 0
            execucao.registros_com_erro = erros
            # Apenas o tipo é salvo para evitar persistir URLs, payloads ou DSNs de erro.
            execucao.resumo_falhas = {"tipo": type(erro).__name__}
            sessao.commit()


def consultar_licitacoes(
    uf: str,
    produto: str = "",
) -> tuple[int, list[dict]]:
    """Consulta os registros persistidos sem acessar o PNCP."""
    from sqlalchemy import func, or_, select

    from app.database.models import Licitacao

    with obter_session_factory()() as sessao:
        agora = datetime.now(timezone.utc)
        filtros = (
            Licitacao.uf == uf,
            or_(
                Licitacao.data_encerramento_proposta.is_(None),
                Licitacao.data_encerramento_proposta >= agora,
            ),
        )
        total_consultado = sessao.scalar(
            select(func.count()).select_from(Licitacao).where(*filtros)
        )

        consulta = select(Licitacao).where(*filtros)
        if produto:
            consulta = consulta.where(
                Licitacao.descricao.icontains(produto, autoescape=True)
            )
        registros = sessao.scalars(
            consulta.order_by(
                Licitacao.data_encerramento_proposta.asc().nullslast(),
                Licitacao.numero,
            )
        ).all()
        return total_consultado, [_formatar_licitacao(registro) for registro in registros]


def _formatar_licitacao(registro) -> dict:
    return {
        "numero": registro.numero,
        "descricao": registro.descricao,
        "codigo_unidade": registro.codigo_unidade,
        "municipio": registro.municipio,
        "uf": registro.uf,
        "data_encerramento_proposta": (
            registro.data_encerramento_proposta.isoformat()
            if registro.data_encerramento_proposta else None
        ),
    }

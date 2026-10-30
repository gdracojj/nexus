from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
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


def obter_execucao_incompleta(parametros: dict) -> dict | None:
    """Retorna o checkpoint mais recente para os mesmos parâmetros."""
    from sqlalchemy import select

    from app.database.models import SyncExecucao

    with obter_session_factory()() as sessao:
        ultima_execucao = sessao.scalar(
            select(SyncExecucao)
            .where(
                SyncExecucao.endpoint == ENDPOINT_PNCP,
                SyncExecucao.parametros == parametros,
            )
            .order_by(SyncExecucao.id.desc())
            .limit(1)
        )
        if ultima_execucao is None or ultima_execucao.status not in {
            "executando",
            "parcial",
        }:
            return None
        return {
            "id": ultima_execucao.id,
            "pagina_seguinte": ultima_execucao.paginas_consultadas + 1,
            "registros_processados": ultima_execucao.registros_processados,
        }


def retomar_execucao(execucao_id: int) -> None:
    from app.database.models import SyncExecucao

    with obter_session_factory()() as sessao:
        execucao = sessao.get(SyncExecucao, execucao_id)
        if execucao is None:
            raise ValueError("Execução PNCP não encontrada.")
        if execucao.status not in {"executando", "parcial"}:
            raise ValueError("A execução PNCP não pode ser retomada.")
        execucao.status = "executando"
        execucao.finalizada_em = None
        execucao.registros_com_erro = 0
        execucao.resumo_falhas = None
        sessao.commit()


def registros_da_coleta_recente(
    parametros: dict,
    janela_segundos: int,
) -> int | None:
    """Retorna o total processado na última coleta equivalente ainda recente."""
    if janela_segundos <= 0:
        return None

    from sqlalchemy import select

    from app.database.models import SyncExecucao

    limite = datetime.now(timezone.utc) - timedelta(seconds=janela_segundos)
    with obter_session_factory()() as sessao:
        consulta = (
            select(
                SyncExecucao.status,
                SyncExecucao.registros_processados,
                SyncExecucao.finalizada_em,
            )
            .where(
                SyncExecucao.endpoint == ENDPOINT_PNCP,
                SyncExecucao.parametros == parametros,
                SyncExecucao.iniciada_em >= limite,
            )
            .order_by(SyncExecucao.id.desc())
            .limit(1)
        )
        ultima_execucao = sessao.execute(consulta).one_or_none()
        if (
            ultima_execucao is None
            or ultima_execucao.status != "concluida"
            or ultima_execucao.finalizada_em is None
            or ultima_execucao.finalizada_em < limite
        ):
            return None
        return ultima_execucao.registros_processados


def _upsert_registros(
    sessao,
    execucao_id: int,
    registros: list[dict],
    agora: datetime,
) -> int:
    from sqlalchemy.dialects.postgresql import insert

    from app.database.models import Licitacao, PncpPayload

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

    return len(registros_unicos)


def concluir_execucao(
    execucao_id: int,
    registros: list[dict],
    paginas_consultadas: int = 0,
) -> int:
    """Upsert atômico das contratações/payloads e conclusão da execução."""
    from app.database.models import SyncExecucao

    agora = datetime.now(timezone.utc)
    with obter_session_factory()() as sessao:
        try:
            quantidade_unica = _upsert_registros(
                sessao,
                execucao_id,
                registros,
                agora,
            )
            execucao = sessao.get(SyncExecucao, execucao_id)
            execucao.status = "concluida"
            execucao.finalizada_em = agora
            execucao.paginas_consultadas = paginas_consultadas
            execucao.registros_recebidos = len(registros)
            execucao.registros_processados = quantidade_unica
            execucao.registros_com_erro = 0
            execucao.resumo_falhas = None
            sessao.commit()
            return quantidade_unica
        except Exception:
            sessao.rollback()
            raise


def persistir_pagina_execucao(
    execucao_id: int,
    pagina: int,
    registros: list[dict],
    registros_recebidos: int,
) -> int:
    """Confirma um lote de página e seu checkpoint na mesma transação."""
    from sqlalchemy import func, select

    from app.database.models import Licitacao, SyncExecucao

    agora = datetime.now(timezone.utc)
    with obter_session_factory()() as sessao:
        try:
            execucao = sessao.get(SyncExecucao, execucao_id)
            if execucao is None:
                raise ValueError("Execução PNCP não encontrada.")
            if pagina != execucao.paginas_consultadas + 1:
                raise ValueError("Página PNCP fora da sequência esperada.")

            _upsert_registros(sessao, execucao_id, registros, agora)
            execucao.paginas_consultadas = pagina
            execucao.registros_recebidos += registros_recebidos
            execucao.registros_processados = sessao.scalar(
                select(func.count()).select_from(Licitacao).where(
                    Licitacao.ultima_execucao_id == execucao_id
                )
            )
            execucao.registros_com_erro = 0
            sessao.commit()
            return execucao.registros_processados
        except Exception:
            sessao.rollback()
            raise


def concluir_execucao_incremental(execucao_id: int) -> int:
    from app.database.models import SyncExecucao

    with obter_session_factory()() as sessao:
        execucao = sessao.get(SyncExecucao, execucao_id)
        if execucao is None:
            raise ValueError("Execução PNCP não encontrada.")
        execucao.status = "concluida"
        execucao.finalizada_em = datetime.now(timezone.utc)
        execucao.registros_com_erro = 0
        execucao.resumo_falhas = None
        sessao.commit()
        return execucao.registros_processados


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
            tem_checkpoint = execucao.paginas_consultadas > 0
            execucao.status = "parcial" if tem_checkpoint else "falhou"
            execucao.finalizada_em = datetime.now(timezone.utc)
            execucao.paginas_consultadas = max(
                execucao.paginas_consultadas,
                paginas_consultadas,
            )
            if not tem_checkpoint:
                execucao.registros_recebidos = recebidos
                execucao.registros_processados = 0
            execucao.registros_com_erro = erros
            # Apenas o tipo é salvo para evitar persistir URLs, payloads ou DSNs de erro.
            execucao.resumo_falhas = {"tipo": type(erro).__name__}
            sessao.commit()


def consultar_licitacoes(
    uf: str | None,
    produto: str = "",
    page: int = 1,
    page_size: int = 25,
    prazo_dias: int | None = None,
) -> tuple[int, int, list[dict], str | None, dict | None]:
    """Consulta os registros persistidos sem acessar o PNCP."""
    from sqlalchemy import func, or_, select

    from app.database.models import Licitacao, SyncExecucao

    with obter_session_factory()() as sessao:
        agora = datetime.now(timezone.utc)
        filtros = [
            or_(
                Licitacao.data_encerramento_proposta.is_(None),
                Licitacao.data_encerramento_proposta >= agora,
            ),
        ]
        if uf is not None:
            filtros.append(Licitacao.uf == uf)
        if prazo_dias is not None:
            filtros.append(
                Licitacao.data_encerramento_proposta <= agora + timedelta(days=prazo_dias)
            )
        total_consultado = sessao.scalar(
            select(func.count()).select_from(Licitacao).where(*filtros)
        )

        filtros_resultado = list(filtros)
        if produto:
            filtros_resultado.append(
                Licitacao.descricao.icontains(produto, autoescape=True)
            )
        total = sessao.scalar(
            select(func.count()).select_from(Licitacao).where(*filtros_resultado)
        )
        consulta = select(Licitacao).where(*filtros_resultado)
        registros = sessao.scalars(
            consulta.order_by(
                Licitacao.data_encerramento_proposta.asc().nullslast(),
                Licitacao.numero,
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        filtros_execucao = [SyncExecucao.endpoint == ENDPOINT_PNCP]
        if uf is not None:
            filtros_execucao.append(SyncExecucao.parametros["uf"].astext == uf)
        ultima_execucao = sessao.scalar(
            select(SyncExecucao)
            .where(*filtros_execucao)
            .order_by(SyncExecucao.id.desc())
            .limit(1)
        )
        ultima_sincronizacao = sessao.scalar(
            select(func.max(SyncExecucao.finalizada_em)).where(
                *filtros_execucao,
                SyncExecucao.status == "concluida",
            )
        )
        resumo_ultima_execucao = (
            {
                "status": ultima_execucao.status,
                "iniciada_em": ultima_execucao.iniciada_em.isoformat(),
                "finalizada_em": (
                    ultima_execucao.finalizada_em.isoformat()
                    if ultima_execucao.finalizada_em
                    else None
                ),
                "paginas_consultadas": ultima_execucao.paginas_consultadas,
                "registros_processados": ultima_execucao.registros_processados,
            }
            if ultima_execucao
            else None
        )
        return (
            total_consultado,
            total,
            [_formatar_licitacao(registro) for registro in registros],
            ultima_sincronizacao.isoformat() if ultima_sincronizacao else None,
            resumo_ultima_execucao,
        )


def _formatar_licitacao(registro) -> dict:
    return {
        "numero_controle_pncp": registro.numero_controle_pncp,
        "numero": registro.numero,
        "descricao": registro.descricao,
        "codigo_unidade": registro.codigo_unidade,
        "unidade": registro.codigo_unidade,
        "orgao": registro.nome_orgao,
        "codigo_modalidade": registro.codigo_modalidade,
        "municipio": registro.municipio,
        "uf": registro.uf,
        "valor_estimado": registro.valor_estimado,
        "situacao": registro.situacao,
        "data_encerramento_proposta": (
            registro.data_encerramento_proposta.isoformat()
            if registro.data_encerramento_proposta else None
        ),
    }

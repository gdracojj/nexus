from datetime import datetime, timezone
from hashlib import sha256
import json

from app.database.connection import obter_session_factory
from app.pncp.client import URL_PNCP


ENDPOINT_PNCP = URL_PNCP


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
            for registro in registros:
                payload = registro["payload"]
                payload_hash = sha256(
                    json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest()
                valores = {
                    chave: valor
                    for chave, valor in registro.items()
                    if chave != "payload"
                }
                valores.update(coletada_em=agora, ultima_execucao_id=execucao_id)
                valores["atualizada_em"] = agora

                inserir_licitacao = insert(Licitacao).values(**valores)
                atualizar = {
                    coluna: getattr(inserir_licitacao.excluded, coluna)
                    for coluna in valores
                    if coluna != "numero_controle_pncp"
                }
                id_licitacao = sessao.scalar(
                    inserir_licitacao.on_conflict_do_update(
                        index_elements=[Licitacao.numero_controle_pncp],
                        set_=atualizar,
                    ).returning(Licitacao.id)
                )

                inserir_payload = insert(PncpPayload).values(
                    licitacao_id=id_licitacao,
                    payload=payload,
                    sha256=payload_hash,
                    recebido_em=agora,
                )
                sessao.execute(
                    inserir_payload.on_conflict_do_update(
                        index_elements=[PncpPayload.licitacao_id],
                        set_={"payload": inserir_payload.excluded.payload,
                              "sha256": inserir_payload.excluded.sha256,
                              "recebido_em": inserir_payload.excluded.recebido_em},
                        where=PncpPayload.sha256 != inserir_payload.excluded.sha256,
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


def listar_licitacoes(
    uf: str,
    numero_controles: list[str],
    produto: str = "",
) -> list[dict]:
    from sqlalchemy import select

    from app.database.models import Licitacao

    if not numero_controles:
        return []

    with obter_session_factory()() as sessao:
        consulta = select(Licitacao).where(
            Licitacao.uf == uf,
            Licitacao.numero_controle_pncp.in_(numero_controles),
        )
        if produto:
            consulta = consulta.where(Licitacao.descricao.icontains(produto, autoescape=True))
        registros = sessao.scalars(consulta.order_by(Licitacao.data_encerramento_proposta.asc().nullslast(), Licitacao.numero)).all()
        return [
            {
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
            for registro in registros
        ]

"""Testes de integração para PostgreSQL real via NEXUS_TEST_DATABASE_URL."""
import os
import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.database import models  # noqa: F401
from app.repositories import licitacao_repository as repositorio


@pytest.fixture
def banco_postgres(monkeypatch):
    url = os.getenv("NEXUS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("defina NEXUS_TEST_DATABASE_URL para executar integração PostgreSQL")
    if not url.startswith("postgresql"):
        pytest.fail("NEXUS_TEST_DATABASE_URL deve apontar para PostgreSQL, não SQLite")

    schema = f"nexus_test_{uuid.uuid4().hex}"
    admin = create_engine(url)
    engine = None
    schema_criado = False
    try:
        with admin.begin() as conexao:
            conexao.execute(text(f'CREATE SCHEMA "{schema}"'))
        schema_criado = True

        scoped_url = make_url(url).update_query_dict(
            {"options": f"-csearch_path={schema}"}
        )
        monkeypatch.setenv("DATABASE_URL", str(scoped_url))
        engine = create_engine(scoped_url)
        alembic_config = Config("alembic.ini")
        command.upgrade(alembic_config, "head")
        command.check(alembic_config)
        monkeypatch.setattr(
            repositorio,
            "obter_session_factory",
            lambda: sessionmaker(bind=engine, expire_on_commit=False),
        )
        yield engine
    finally:
        try:
            if engine is not None:
                engine.dispose()
        finally:
            try:
                if schema_criado:
                    with admin.begin() as conexao:
                        conexao.execute(
                            text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
                        )
            finally:
                admin.dispose()


def registro(payload_objeto="Compra de material"):
    payload = {
        "numeroControlePNCP": "12345678000199-1-000001/2026",
        "numeroCompra": "1/2026",
        "anoCompra": 2026,
        "codigoModalidadeContratacao": 6,
        "objetoCompra": payload_objeto,
        "valorTotalEstimado": 120.50,
        "dataPublicacaoPncp": "2026-10-20",
        "dataAberturaProposta": "2026-10-21T09:00:00-03:00",
        "dataEncerramentoProposta": "2026-10-30T18:00:00-03:00",
        "situacaoCompraNome": "Divulgada no PNCP",
        "orgaoEntidade": {"cnpj": "12345678000199", "razaoSocial": "Órgão de teste"},
        "unidadeOrgao": {
            "codigoUnidade": "1",
            "municipioNome": "São Paulo",
            "ufSigla": "SP",
        },
    }
    from app.pncp.parser import registro_para_persistencia

    return registro_para_persistencia(payload)


def test_upsert_e_idempotente_e_atualiza_payload_quando_muda(banco_postgres):
    primeiro_id = repositorio.iniciar_execucao({"uf": "SP"})
    primeira = registro()
    repositorio.concluir_execucao(primeiro_id, [primeira, primeira])

    with sessionmaker(bind=banco_postgres)() as sessao:
        licitacoes = sessao.scalars(select(models.Licitacao)).all()
        assert len(licitacoes) == 1
        id_licitacao = licitacoes[0].id
        recebido_inicial = sessao.get(models.PncpPayload, id_licitacao).recebido_em

    segundo_id = repositorio.iniciar_execucao({"uf": "SP"})
    repositorio.concluir_execucao(segundo_id, [registro("Compra de material revisada")])

    with sessionmaker(bind=banco_postgres)() as sessao:
        licitacoes = sessao.scalars(select(models.Licitacao)).all()
        assert len(licitacoes) == 1
        assert licitacoes[0].id == id_licitacao
        assert licitacoes[0].descricao == "Compra de material revisada"
        assert licitacoes[0].valor_estimado == 120.5000
        payload = sessao.get(models.PncpPayload, id_licitacao)
        assert payload.payload["objetoCompra"] == "Compra de material revisada"
        assert payload.sha256
        assert payload.recebido_em >= recebido_inicial
        execucao = sessao.get(models.SyncExecucao, segundo_id)
        assert (
            execucao.status,
            execucao.paginas_consultadas,
            execucao.registros_recebidos,
            execucao.registros_processados,
        ) == (
            "concluida", 0, 1, 1
        )


def test_falha_de_transacao_nao_deixa_licitacao_parcial(banco_postgres):
    execucao_id = repositorio.iniciar_execucao({"uf": "SP"})
    with pytest.raises(Exception):
        repositorio.concluir_execucao(execucao_id, [{"payload": {"raw": True}}])
    repositorio.falhar_execucao(execucao_id, ValueError("detalhe que não deve ser salvo"))

    with sessionmaker(bind=banco_postgres)() as sessao:
        assert sessao.scalar(select(models.Licitacao.id)) is None
        execucao = sessao.get(models.SyncExecucao, execucao_id)
        assert execucao.status == "falhou"
        assert execucao.registros_com_erro == 1
        assert execucao.resumo_falhas == {"tipo": "ValueError"}


def test_repositorio_filtra_com_texto_insensivel_a_caixa(banco_postgres):
    execucao_id = repositorio.iniciar_execucao({"uf": "SP"})
    repositorio.concluir_execucao(execucao_id, [registro()])

    encontrados = repositorio.listar_licitacoes(
        "SP", ["12345678000199-1-000001/2026"], "MATERIAL"
    )
    assert len(encontrados) == 1
    assert encontrados[0]["descricao"] == "Compra de material"
    assert encontrados[0]["uf"] == "SP"


def test_endpoint_responde_com_registros_persistidos_da_consulta_atual(
    banco_postgres,
    monkeypatch,
):
    from app import main
    from app.services import licitacao_service

    monkeypatch.setattr(licitacao_service, "buscar_licitacoes", lambda *_args, **_kwargs: [registro()])

    resposta = main.listar_licitacoes("SP", "MATERIAL")

    assert resposta["total_consultado"] == 1
    assert resposta["total"] == 1
    assert resposta["resultados"] == [
        {
            "numero": "1/2026",
            "descricao": "Compra de material",
            "codigo_unidade": "1",
            "municipio": "São Paulo",
            "uf": "SP",
            "data_encerramento_proposta": "2026-10-30T18:00:00-03:00",
        }
    ]

"""Testes de integração para PostgreSQL real via NEXUS_TEST_DATABASE_URL."""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, select, text
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
        monkeypatch.setattr(repositorio, "obter_engine", lambda: engine)
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
        "dataEncerramentoProposta": (
            datetime.now(timezone(timedelta(hours=-3))) + timedelta(days=3)
        ).isoformat(),
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
        execucao_inicial = sessao.get(models.SyncExecucao, primeiro_id)
        assert execucao_inicial.registros_recebidos == 2
        assert execucao_inicial.registros_processados == 1

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

    total, encontrados = repositorio.consultar_licitacoes("SP", "MATERIAL")
    assert total == 1
    assert len(encontrados) == 1
    assert encontrados[0]["descricao"] == "Compra de material"
    assert encontrados[0]["uf"] == "SP"


def test_upsert_preserva_data_da_primeira_coleta(banco_postgres):
    primeira_execucao = repositorio.iniciar_execucao({"uf": "SP"})
    oportunidade = registro()
    repositorio.concluir_execucao(primeira_execucao, [oportunidade])

    with sessionmaker(bind=banco_postgres)() as sessao:
        primeira = sessao.scalar(select(models.Licitacao))
        coletada_em_original = primeira.coletada_em
        atualizada_em_original = primeira.atualizada_em

    segunda_execucao = repositorio.iniciar_execucao({"uf": "SP"})
    repositorio.concluir_execucao(segunda_execucao, [oportunidade])

    with sessionmaker(bind=banco_postgres)() as sessao:
        atual = sessao.scalar(select(models.Licitacao))
        assert atual.coletada_em == coletada_em_original
        assert atual.atualizada_em >= atualizada_em_original


def test_upsert_em_lote_usa_duas_instrucoes_para_multiplas_linhas(banco_postgres):
    execucao_id = repositorio.iniciar_execucao({"uf": "SP"})
    oportunidades = []
    for indice in range(3):
        oportunidade = registro()
        oportunidade["numero_controle_pncp"] = f"12345678000199-1-00000{indice}/2026"
        oportunidade["numero"] = f"{indice}/2026"
        oportunidade["payload"]["numeroControlePNCP"] = oportunidade[
            "numero_controle_pncp"
        ]
        oportunidades.append(oportunidade)

    instrucoes = []

    def contar_insercoes(_conexao, _cursor, instrucao, _parametros, _contexto, _executemany):
        instrucoes.append(instrucao.lower())

    event.listen(banco_postgres, "before_cursor_execute", contar_insercoes)
    try:
        repositorio.concluir_execucao(execucao_id, oportunidades)
    finally:
        event.remove(banco_postgres, "before_cursor_execute", contar_insercoes)

    assert sum(
        instrucao.lstrip().startswith("insert into licitacoes")
        for instrucao in instrucoes
    ) == 1
    assert sum(
        instrucao.lstrip().startswith("insert into pncp_payloads")
        for instrucao in instrucoes
    ) == 1
    # Duas instruções de upsert em lote + SELECT/UPDATE da execução.
    assert len(instrucoes) == 4
    with sessionmaker(bind=banco_postgres)() as sessao:
        assert len(sessao.scalars(select(models.Licitacao)).all()) == 3


def test_consulta_persistida_omite_oportunidades_com_prazo_encerrado(banco_postgres):
    execucao_id = repositorio.iniciar_execucao({"uf": "SP"})
    oportunidade = registro()
    oportunidade["data_encerramento_proposta"] = datetime.now(timezone.utc) - timedelta(days=1)
    repositorio.concluir_execucao(execucao_id, [oportunidade])

    total, encontrados = repositorio.consultar_licitacoes("SP")

    assert total == 0
    assert encontrados == []


def test_lock_global_impede_duas_coletas_simultaneas(banco_postgres):
    with repositorio.lock_coleta_pncp():
        with pytest.raises(repositorio.ColetaPNCPJaEmAndamentoError):
            with repositorio.lock_coleta_pncp():
                pass


def test_cache_de_coleta_exige_sucesso_parametros_iguais_e_janela_vigente(
    banco_postgres,
):
    parametros = {"uf": "SP", "dataInicial": "20261028"}
    execucao_id = repositorio.iniciar_execucao(parametros)
    repositorio.concluir_execucao(execucao_id, [registro()])

    assert repositorio.registros_da_coleta_recente(parametros, 900) == 1
    assert repositorio.registros_da_coleta_recente({"uf": "RJ"}, 900) is None
    assert repositorio.registros_da_coleta_recente(parametros, 0) is None

    with sessionmaker(bind=banco_postgres)() as sessao:
        execucao = sessao.get(models.SyncExecucao, execucao_id)
        execucao.finalizada_em = datetime.now(timezone.utc) - timedelta(minutes=20)
        sessao.commit()

    assert repositorio.registros_da_coleta_recente(parametros, 900) is None


def test_cache_nao_reutiliza_coleta_falha(banco_postgres):
    parametros = {"uf": "SP", "dataInicial": "20261028"}
    execucao_id = repositorio.iniciar_execucao(parametros)
    repositorio.falhar_execucao(execucao_id, RuntimeError("falha externa"))

    assert repositorio.registros_da_coleta_recente(parametros, 900) is None


def test_falha_mais_recente_invalida_cache_de_coleta_anterior(banco_postgres):
    parametros = {"uf": "SP", "dataInicial": "20261028"}
    sucesso_id = repositorio.iniciar_execucao(parametros)
    repositorio.concluir_execucao(sucesso_id, [registro()])
    falha_id = repositorio.iniciar_execucao(parametros)
    repositorio.falhar_execucao(falha_id, RuntimeError("falha externa"))

    assert repositorio.registros_da_coleta_recente(parametros, 900) is None


def test_endpoint_consulta_registros_persistidos_sem_iniciar_coleta(banco_postgres):
    from app import main

    execucao_id = repositorio.iniciar_execucao({"uf": "SP"})
    oportunidade = registro()
    repositorio.concluir_execucao(execucao_id, [oportunidade])

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
            "data_encerramento_proposta": oportunidade[
                "data_encerramento_proposta"
            ].isoformat(),
        }
    ]

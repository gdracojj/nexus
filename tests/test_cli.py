from contextlib import nullcontext

import pytest

from app.cli import main
from app.core.config import obter_janela_reuso_coleta_segundos
from app.repositories import licitacao_repository
from app.services import licitacao_service


def test_coleta_nao_inicia_quando_o_lock_global_esta_ocupado(monkeypatch):
    def lock_ocupado():
        raise licitacao_repository.ColetaPNCPJaEmAndamentoError(
            "Já existe uma coleta PNCP em andamento."
        )

    def execucao_nao_esperada(*_args, **_kwargs):
        pytest.fail("não deve criar histórico para uma coleta que não iniciou")

    monkeypatch.setattr(licitacao_repository, "lock_coleta_pncp", lock_ocupado)
    monkeypatch.setattr(licitacao_repository, "iniciar_execucao", execucao_nao_esperada)

    with pytest.raises(licitacao_repository.ColetaPNCPJaEmAndamentoError):
        licitacao_service.sincronizar_licitacoes("RJ")


def test_sincronizacao_reutiliza_coleta_recente_com_os_mesmos_parametros(monkeypatch):
    parametros = {"uf": "RJ", "dataInicial": "20261028"}
    monkeypatch.setattr(
        licitacao_service,
        "parametros_consulta",
        lambda _uf: parametros,
    )
    monkeypatch.setattr(
        licitacao_service,
        "obter_janela_reuso_coleta_segundos",
        lambda: 900,
    )
    monkeypatch.setattr(licitacao_repository, "lock_coleta_pncp", nullcontext)
    monkeypatch.setattr(licitacao_repository, "obter_execucao_incompleta", lambda _p: None)
    consultas = []
    monkeypatch.setattr(
        licitacao_repository,
        "registros_da_coleta_recente",
        lambda recebidos, janela: consultas.append((recebidos, janela)) or 0,
    )
    monkeypatch.setattr(
        licitacao_repository,
        "iniciar_execucao",
        lambda _parametros: pytest.fail("não deve iniciar coleta recente equivalente"),
    )
    monkeypatch.setattr(
        licitacao_service,
        "buscar_licitacoes",
        lambda *_args, **_kwargs: pytest.fail("não deve chamar o PNCP"),
    )

    assert licitacao_service.sincronizar_licitacoes("RJ") == 0
    assert consultas == [(parametros, 900)]


def test_sincronizacao_em_cache_miss_retorna_contagem_deduplicada(monkeypatch):
    parametros = {"uf": "RJ", "dataInicial": "20261028"}
    monkeypatch.setattr(
        licitacao_service,
        "parametros_consulta",
        lambda _uf: parametros,
    )
    monkeypatch.setattr(
        licitacao_service,
        "obter_janela_reuso_coleta_segundos",
        lambda: 900,
    )
    monkeypatch.setattr(licitacao_repository, "lock_coleta_pncp", nullcontext)
    monkeypatch.setattr(licitacao_repository, "obter_execucao_incompleta", lambda _p: None)
    monkeypatch.setattr(licitacao_repository, "registros_da_coleta_recente", lambda *_args: None)
    monkeypatch.setattr(licitacao_repository, "iniciar_execucao", lambda _parametros: 42)
    def buscar(*_args, ao_processar_pagina, **_kwargs):
        ao_processar_pagina(
            1,
            1,
            [
                {"numero_controle_pncp": "id-1"},
                {"numero_controle_pncp": "id-1"},
            ],
            2,
        )

    monkeypatch.setattr(licitacao_service, "buscar_licitacoes", buscar)
    paginas_salvas = []
    monkeypatch.setattr(
        licitacao_repository,
        "persistir_pagina_execucao",
        lambda execucao, pagina, registros, recebidos: paginas_salvas.append(
            (execucao, pagina, registros, recebidos)
        ),
    )
    monkeypatch.setattr(
        licitacao_repository,
        "concluir_execucao_incremental",
        lambda _execucao: 1,
    )

    assert licitacao_service.sincronizar_licitacoes("RJ") == 1
    assert len(paginas_salvas) == 1
    assert paginas_salvas[0][0:2] == (42, 1)
    assert len(paginas_salvas[0][2]) == 2
    assert paginas_salvas[0][3] == 2


def test_sincronizacao_retoma_do_checkpoint_persistido(monkeypatch):
    parametros = {"uf": "RS", "dataInicial": "20261028"}
    monkeypatch.setattr(licitacao_service, "parametros_consulta", lambda _uf: parametros)
    monkeypatch.setattr(licitacao_service, "obter_janela_reuso_coleta_segundos", lambda: 900)
    monkeypatch.setattr(licitacao_repository, "lock_coleta_pncp", nullcontext)
    monkeypatch.setattr(
        licitacao_repository,
        "obter_execucao_incompleta",
        lambda _p: {"id": 77, "pagina_seguinte": 63, "registros_processados": 620},
    )
    monkeypatch.setattr(
        licitacao_repository,
        "retomar_execucao",
        lambda _execucao: None,
    )
    monkeypatch.setattr(
        licitacao_repository,
        "registros_da_coleta_recente",
        lambda *_args: pytest.fail("checkpoint deve ser retomado antes do cache"),
    )
    argumentos = []

    def buscar(*_args, **kwargs):
        argumentos.append(kwargs)
        return []

    monkeypatch.setattr(licitacao_service, "buscar_licitacoes", buscar)
    monkeypatch.setattr(
        licitacao_repository,
        "concluir_execucao_incremental",
        lambda _execucao: 620,
    )

    assert licitacao_service.sincronizar_licitacoes("RS") == 620
    assert argumentos[0]["pagina_inicial"] == 63
    assert argumentos[0]["ao_processar_pagina"]


def test_cli_coleta_retorna_codigo_zero_em_sucesso(monkeypatch, capsys):
    chamadas = []
    monkeypatch.setattr(
        "app.cli.sincronizar_licitacoes",
        lambda uf: chamadas.append(uf) or 12,
    )

    codigo = main(["coletar", "--uf", " rj "])

    assert codigo == 0
    assert chamadas == ["RJ"]
    assert "12 registros processados" in capsys.readouterr().out


def test_cli_coleta_falha_sem_expor_detalhes_da_excecao(monkeypatch, capsys):
    def falhar(_uf):
        raise RuntimeError("postgresql://usuario:senha-secreta@host/db")

    monkeypatch.setattr("app.cli.sincronizar_licitacoes", falhar)

    codigo = main(["coletar", "--uf", "SP"])
    saida = capsys.readouterr()

    assert codigo == 1
    assert "RuntimeError" in saida.err
    assert "senha-secreta" not in saida.err


@pytest.mark.parametrize("valor", ["-1", "86401", "invalido"])
def test_janela_reuso_rejeita_configuracao_invalida(monkeypatch, valor):
    monkeypatch.setenv("PNCP_SYNC_CACHE_TTL_SECONDS", valor)

    with pytest.raises(RuntimeError, match="PNCP_SYNC_CACHE_TTL_SECONDS"):
        obter_janela_reuso_coleta_segundos()


def test_janela_reuso_zero_desativa_cache(monkeypatch):
    monkeypatch.setenv("PNCP_SYNC_CACHE_TTL_SECONDS", "0")

    assert obter_janela_reuso_coleta_segundos() == 0

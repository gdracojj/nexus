import pytest
import requests
from fastapi import HTTPException

from app import main
from app.pncp import client


def test_buscar_licitacoes_processa_ate_o_limite_de_paginas(monkeypatch):
    paginas_solicitadas = []

    def buscar_pagina_fake(url, parametros):
        paginas_solicitadas.append(parametros["pagina"])
        return {"data": [], "totalPaginas": client.MAX_PAGINAS_CONSULTA}

    monkeypatch.setattr(client, "buscar_pagina", buscar_pagina_fake)
    monkeypatch.setattr(client.time, "sleep", lambda _segundos: None)

    resultado = client.buscar_licitacoes("RJ")

    assert resultado == []
    assert paginas_solicitadas == list(
        range(1, client.MAX_PAGINAS_CONSULTA + 1)
    )


def test_buscar_licitacoes_aceita_resposta_vazia_com_zero_paginas(monkeypatch):
    monkeypatch.setattr(
        client,
        "buscar_pagina",
        lambda _url, _parametros: {"data": [], "totalPaginas": 0},
    )

    assert client.buscar_licitacoes("RJ") == []


def test_buscar_licitacoes_rejeita_total_de_paginas_acima_do_limite(monkeypatch):
    chamadas = []

    def buscar_pagina_fake(url, parametros):
        chamadas.append(parametros["pagina"])
        return {"data": [], "totalPaginas": client.MAX_PAGINAS_CONSULTA + 1}

    monkeypatch.setattr(client, "buscar_pagina", buscar_pagina_fake)

    with pytest.raises(client.LimitePaginacaoPNCPError, match="101.*100"):
        client.buscar_licitacoes("RJ")

    assert chamadas == [1]


def test_buscar_licitacoes_revalida_limite_em_cada_pagina(monkeypatch):
    chamadas = []

    def buscar_pagina_fake(_url, parametros):
        pagina = parametros["pagina"]
        chamadas.append(pagina)
        total_paginas = 2 if pagina == 1 else client.MAX_PAGINAS_CONSULTA + 1
        return {"data": [], "totalPaginas": total_paginas}

    monkeypatch.setattr(client, "buscar_pagina", buscar_pagina_fake)
    monkeypatch.setattr(client.time, "sleep", lambda _segundos: None)

    with pytest.raises(client.LimitePaginacaoPNCPError):
        client.buscar_licitacoes("RJ")

    assert chamadas == [1, 2]


def test_limite_de_paginacao_retorna_502_generico_na_rota(monkeypatch):
    monkeypatch.setattr(
        client,
        "buscar_pagina",
        lambda _url, _parametros: {
            "data": [],
            "totalPaginas": client.MAX_PAGINAS_CONSULTA + 1,
        },
    )

    with pytest.raises(HTTPException) as erro:
        main.listar_licitacoes("RJ")

    assert erro.value.status_code == 502
    assert erro.value.detail == (
        "Não foi possível consultar o PNCP. Tente novamente mais tarde."
    )


@pytest.mark.parametrize("total_paginas", [-1, None, "2", True])
def test_buscar_licitacoes_rejeita_total_de_paginas_invalido(
    monkeypatch,
    total_paginas,
):
    monkeypatch.setattr(
        client,
        "buscar_pagina",
        lambda _url, _parametros: {"data": [], "totalPaginas": total_paginas},
    )

    with pytest.raises(requests.exceptions.RequestException, match="inválido"):
        client.buscar_licitacoes("RJ")


def test_buscar_licitacoes_rejeita_registros_com_zero_paginas(monkeypatch):
    monkeypatch.setattr(
        client,
        "buscar_pagina",
        lambda _url, _parametros: {
            "data": [{"numeroCompra": "1"}],
            "totalPaginas": 0,
        },
    )

    with pytest.raises(requests.exceptions.RequestException, match="zero"):
        client.buscar_licitacoes("RJ")

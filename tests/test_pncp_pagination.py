import pytest
import requests

from app.pncp import client


def test_buscar_licitacoes_processa_ate_o_limite_de_paginas(monkeypatch):
    paginas_solicitadas = []

    def buscar_pagina_fake(url, parametros, **_kwargs):
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
        lambda _url, _parametros, **_kwargs: {
            "data": [], "totalPaginas": 0
        },
    )

    assert client.buscar_licitacoes("RJ") == []


def test_buscar_licitacoes_rejeita_total_de_paginas_acima_do_limite(monkeypatch):
    chamadas = []

    def buscar_pagina_fake(url, parametros, **_kwargs):
        chamadas.append(parametros["pagina"])
        return {"data": [], "totalPaginas": client.MAX_PAGINAS_CONSULTA + 1}

    monkeypatch.setattr(client, "buscar_pagina", buscar_pagina_fake)

    with pytest.raises(client.LimitePaginacaoPNCPError, match="101.*100"):
        client.buscar_licitacoes("RJ")

    assert chamadas == [1]


def test_buscar_licitacoes_revalida_limite_em_cada_pagina(monkeypatch):
    chamadas = []

    def buscar_pagina_fake(_url, parametros, **_kwargs):
        pagina = parametros["pagina"]
        chamadas.append(pagina)
        total_paginas = 2 if pagina == 1 else client.MAX_PAGINAS_CONSULTA + 1
        return {"data": [], "totalPaginas": total_paginas}

    monkeypatch.setattr(client, "buscar_pagina", buscar_pagina_fake)
    monkeypatch.setattr(client.time, "sleep", lambda _segundos: None)

    with pytest.raises(client.LimitePaginacaoPNCPError):
        client.buscar_licitacoes("RJ")

    assert chamadas == [1, 2]


def test_buscar_licitacoes_reporta_recebidos_antes_de_falha_de_pagina(monkeypatch):
    recebidos = []
    paginas = []

    def buscar_pagina_fake(_url, parametros, **_kwargs):
        if parametros["pagina"] == 1:
            return {"data": [{"numeroCompra": "1"}], "totalPaginas": 2}
        raise requests.exceptions.Timeout("timeout")

    monkeypatch.setattr(client, "buscar_pagina", buscar_pagina_fake)
    monkeypatch.setattr(client.time, "sleep", lambda _segundos: None)

    with pytest.raises(requests.exceptions.Timeout):
        client.buscar_licitacoes(
            "RJ",
            ao_receber_registros=recebidos.append,
            ao_consultar_pagina=lambda pagina, _quantidade: paginas.append(pagina),
        )

    assert recebidos == [1]
    assert paginas == [1]


@pytest.mark.parametrize("total_paginas", [-1, None, "2", True])
def test_buscar_licitacoes_rejeita_total_de_paginas_invalido(
    monkeypatch,
    total_paginas,
):
    monkeypatch.setattr(
        client,
        "buscar_pagina",
        lambda _url, _parametros, **_kwargs: {
            "data": [],
            "totalPaginas": total_paginas,
        },
    )

    with pytest.raises(requests.exceptions.RequestException, match="inválido"):
        client.buscar_licitacoes("RJ")


def test_buscar_licitacoes_rejeita_registros_com_zero_paginas(monkeypatch):
    monkeypatch.setattr(
        client,
        "buscar_pagina",
        lambda _url, _parametros, **_kwargs: {
            "data": [{"numeroCompra": "1"}],
            "totalPaginas": 0,
        },
    )

    with pytest.raises(requests.exceptions.RequestException, match="zero"):
        client.buscar_licitacoes("RJ")

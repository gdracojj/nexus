import pytest
import requests

from app.pncp import client


@pytest.mark.parametrize(
    ("estado", "limite"),
    [("RJ", client.MAX_PAGINAS_CONSULTA), ("SP", client.MAX_PAGINAS_CONSULTA_SP)],
)
def test_buscar_licitacoes_processa_ate_o_limite_de_paginas(
    monkeypatch, estado, limite
):
    paginas_solicitadas = []

    def buscar_pagina_fake(url, parametros, **_kwargs):
        paginas_solicitadas.append(parametros["pagina"])
        return {"data": [], "totalPaginas": limite}

    monkeypatch.setattr(client, "buscar_pagina", buscar_pagina_fake)
    monkeypatch.setattr(client.time, "sleep", lambda _segundos: None)

    resultado = client.buscar_licitacoes(estado)

    assert resultado == []
    assert paginas_solicitadas == list(
        range(1, limite + 1)
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


@pytest.mark.parametrize(
    ("estado", "limite"),
    [("RJ", client.MAX_PAGINAS_CONSULTA), ("SP", client.MAX_PAGINAS_CONSULTA_SP)],
)
def test_buscar_licitacoes_rejeita_total_de_paginas_acima_do_limite(
    monkeypatch, estado, limite
):
    chamadas = []

    def buscar_pagina_fake(url, parametros, **_kwargs):
        chamadas.append(parametros["pagina"])
        return {"data": [], "totalPaginas": limite + 1}

    monkeypatch.setattr(client, "buscar_pagina", buscar_pagina_fake)

    with pytest.raises(
        client.LimitePaginacaoPNCPError,
        match=rf"{limite + 1}.*{limite}",
    ):
        client.buscar_licitacoes(estado)

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


def test_buscar_licitacoes_processa_e_persiste_pagina_antes_de_continuar(monkeypatch):
    chamadas = []
    paginas_persistidas = []

    def buscar_pagina_fake(_url, parametros, **_kwargs):
        pagina = parametros["pagina"]
        chamadas.append(pagina)
        return {"data": [], "totalPaginas": 4}

    monkeypatch.setattr(client, "buscar_pagina", buscar_pagina_fake)
    monkeypatch.setattr(client.time, "sleep", lambda _segundos: None)

    resultado = client.buscar_licitacoes(
        "RS",
        pagina_inicial=3,
        ao_processar_pagina=lambda pagina, total, registros, recebidos: (
            paginas_persistidas.append((pagina, total, registros, recebidos))
        ),
    )

    assert resultado == []
    assert chamadas == [3, 4]
    assert paginas_persistidas == [(3, 4, [], 0), (4, 4, [], 0)]


@pytest.mark.parametrize("pagina_inicial", [0, -1, "2", True])
def test_buscar_licitacoes_rejeita_pagina_inicial_invalida(
    monkeypatch,
    pagina_inicial,
):
    monkeypatch.setattr(
        client,
        "buscar_pagina",
        lambda *_args, **_kwargs: pytest.fail("não deve solicitar página"),
    )

    with pytest.raises(ValueError, match="pagina_inicial"):
        client.buscar_licitacoes("RS", pagina_inicial=pagina_inicial)


def test_buscar_licitacoes_reporta_recebidos_antes_de_falha_de_pagina(monkeypatch):
    recebidos = []
    paginas = []

    def buscar_pagina_fake(_url, parametros, **_kwargs):
        if parametros["pagina"] == 1:
            return {
                "data": [
                    {
                        "numeroCompra": "1",
                        "objetoCompra": "Compra teste",
                        "unidadeOrgao": {"ufSigla": "RJ"},
                    }
                ],
                "totalPaginas": 2,
            }
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

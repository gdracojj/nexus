import pytest
import requests
from fastapi import HTTPException

from app import main
from app.pncp import client


def registro_valido():
    return {
        "numeroCompra": "12/2026",
        "objetoCompra": "Compra de material",
        "unidadeOrgao": {
            "codigoUnidade": "123456",
            "municipioNome": "Rio de Janeiro",
            "ufSigla": "RJ",
        },
        "dataEncerramentoProposta": "2026-10-30T18:00:00",
    }


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {},
        {"data": []},
        {"totalPaginas": 1},
        {"totalPaginas": 1, "data": None},
        {"totalPaginas": 1, "data": {}},
    ],
)
def test_resposta_pncp_com_envelope_invalido_e_rejeitada(monkeypatch, payload):
    monkeypatch.setattr(
        client,
        "buscar_pagina",
        lambda _url, _parametros, **_kwargs: payload,
    )

    with pytest.raises(requests.exceptions.RequestException):
        client.buscar_licitacoes("RJ")


def test_registro_malformado_rejeita_lote_com_indice_sem_expor_payload(
    monkeypatch,
):
    registro_invalido = registro_valido()
    registro_invalido["objetoCompra"] = "DADO INTERNO DE TESTE"
    del registro_invalido["numeroCompra"]
    monkeypatch.setattr(
        client,
        "buscar_pagina",
        lambda _url, _parametros, **_kwargs: {
            "data": [registro_valido(), registro_invalido],
            "totalPaginas": 1,
        },
    )

    with pytest.raises(requests.exceptions.RequestException) as erro:
        client.buscar_licitacoes("RJ")

    assert "posição 2" in str(erro.value)
    assert "numeroCompra" in str(erro.value)
    assert "DADO INTERNO DE TESTE" not in str(erro.value)


def test_registro_malformado_vira_502_com_mensagem_publica_generica(
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(
        client,
        "buscar_pagina",
        lambda _url, _parametros, **_kwargs: {
            "data": [{"numeroCompra": "DADO INTERNO DE TESTE"}],
            "totalPaginas": 1,
        },
    )

    with pytest.raises(HTTPException) as erro:
        main.listar_licitacoes("RJ")

    assert erro.value.status_code == 502
    assert erro.value.detail == (
        "Não foi possível consultar o PNCP. Tente novamente mais tarde."
    )
    assert "DADO INTERNO DE TESTE" not in erro.value.detail

    diagnostico = capsys.readouterr().out
    assert "ERRO PNCP:" in diagnostico
    assert "registro inválido na posição 1" in diagnostico
    assert "objetoCompra" in diagnostico
    assert "DADO INTERNO DE TESTE" not in diagnostico

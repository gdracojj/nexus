import pytest
import requests
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
    assert erro.value.registros_recebidos == 2
    assert erro.value.registros_com_erro == 1
    assert "DADO INTERNO DE TESTE" not in str(erro.value)


def test_registro_malformado_registra_falha_da_coleta(monkeypatch):
    from contextlib import nullcontext

    from app.repositories import licitacao_repository
    from app.services import licitacao_service

    falhas_registradas = []
    monkeypatch.setattr(
        licitacao_repository,
        "lock_coleta_pncp",
        lambda: nullcontext(),
    )
    monkeypatch.setattr(licitacao_repository, "iniciar_execucao", lambda _parametros: 1)
    monkeypatch.setattr(
        licitacao_repository,
        "falhar_execucao",
        lambda *args: falhas_registradas.append(args),
    )
    monkeypatch.setattr(
        client,
        "buscar_pagina",
        lambda _url, _parametros, **_kwargs: {
            "data": [{"numeroCompra": "DADO INTERNO DE TESTE"}],
            "totalPaginas": 1,
        },
    )

    with pytest.raises(requests.exceptions.RequestException) as erro:
        licitacao_service.sincronizar_licitacoes("RJ")

    assert "posição 1" in str(erro.value)
    assert "DADO INTERNO DE TESTE" not in str(erro.value)
    assert len(falhas_registradas) == 1
    assert falhas_registradas[0][0] == 1
    assert falhas_registradas[0][2:] == (1, 1, 1)

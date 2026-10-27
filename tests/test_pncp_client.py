from datetime import datetime, timezone

import pytest
import requests

from app.pncp import client


class RespostaFake:
    def __init__(self, status_code, *, headers=None, payload=None):
        self.status_code = status_code
        self.headers = headers or {}
        self.payload = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(
                f"HTTP {self.status_code}"
            )

    def json(self):
        return self.payload


def test_buscar_pagina_envia_timeout_e_retorna_json(monkeypatch):
    chamadas = []
    payload = {"data": [], "totalPaginas": 0}

    def get_fake(url, *, params, timeout):
        chamadas.append((url, params, timeout))
        return RespostaFake(200, payload=payload)

    monkeypatch.setattr(client.requests, "get", get_fake)

    resultado = client.buscar_pagina(client.URL_PNCP, {"uf": "RJ"})

    assert resultado == payload
    assert chamadas == [
        (
            client.URL_PNCP,
            {"uf": "RJ"},
            client.TIMEOUT_REQUISICAO_SEGUNDOS,
        )
    ]


def test_buscar_pagina_nao_repete_erro_http_nao_temporario(monkeypatch):
    chamadas = []
    sleeps = []

    def get_fake(*_args, **_kwargs):
        chamadas.append(1)
        return RespostaFake(400)

    monkeypatch.setattr(client.requests, "get", get_fake)
    monkeypatch.setattr(client.time, "sleep", sleeps.append)

    with pytest.raises(requests.exceptions.HTTPError, match="HTTP 400"):
        client.buscar_pagina(client.URL_PNCP, {})

    assert len(chamadas) == 1
    assert sleeps == []


def test_buscar_pagina_repete_429_e_respeita_retry_after(monkeypatch):
    respostas = iter(
        [
            RespostaFake(429, headers={"Retry-After": "3"}),
            RespostaFake(200, payload={"ok": True}),
        ]
    )
    chamadas = []
    sleeps = []

    def get_fake(*_args, **_kwargs):
        chamadas.append(1)
        return next(respostas)

    monkeypatch.setattr(client.requests, "get", get_fake)
    monkeypatch.setattr(client.time, "sleep", sleeps.append)

    assert client.buscar_pagina(client.URL_PNCP, {}) == {"ok": True}
    assert len(chamadas) == 2
    assert sleeps == [3]


def test_buscar_pagina_usa_backoff_exponencial_para_retry_after_invalido(
    monkeypatch,
):
    respostas = iter(
        [
            RespostaFake(429, headers={"Retry-After": "formato inválido"}),
            RespostaFake(200, payload={"ok": True}),
        ]
    )
    sleeps = []

    monkeypatch.setattr(
        client.requests,
        "get",
        lambda *_args, **_kwargs: next(respostas),
    )
    monkeypatch.setattr(client.time, "sleep", sleeps.append)

    assert client.buscar_pagina(client.URL_PNCP, {}) == {"ok": True}
    assert sleeps == [2]


def test_buscar_pagina_limita_total_de_tentativas_429(monkeypatch):
    chamadas = []
    sleeps = []

    def get_fake(*_args, **_kwargs):
        chamadas.append(1)
        return RespostaFake(429, headers={"Retry-After": "0"})

    monkeypatch.setattr(client.requests, "get", get_fake)
    monkeypatch.setattr(client.time, "sleep", sleeps.append)

    with pytest.raises(requests.exceptions.HTTPError, match="HTTP 429"):
        client.buscar_pagina(client.URL_PNCP, {})

    assert len(chamadas) == client.MAX_TENTATIVAS
    assert len(sleeps) == client.MAX_TENTATIVAS - 1


def test_buscar_pagina_rejeita_retry_after_acima_do_limite(monkeypatch):
    chamadas = []

    def get_fake(*_args, **_kwargs):
        chamadas.append(1)
        return RespostaFake(
            429,
            headers={
                "Retry-After": str(client.MAX_ESPERA_RETRY_AFTER + 1)
            },
        )

    monkeypatch.setattr(client.requests, "get", get_fake)

    with pytest.raises(
        requests.exceptions.HTTPError,
        match="Retry-After excede o limite máximo",
    ):
        client.buscar_pagina(client.URL_PNCP, {})

    assert len(chamadas) == 1


def test_buscar_pagina_propaga_falha_de_conexao(monkeypatch):
    chamadas = []
    sleeps = []

    def get_fake(*_args, **_kwargs):
        chamadas.append(1)
        raise requests.exceptions.ConnectionError("conexão indisponível")

    monkeypatch.setattr(client.requests, "get", get_fake)
    monkeypatch.setattr(client.time, "sleep", sleeps.append)

    with pytest.raises(requests.exceptions.ConnectionError):
        client.buscar_pagina(client.URL_PNCP, {})

    assert len(chamadas) == client.MAX_TENTATIVAS
    assert sleeps == [2, 4, 8, 16]


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("12", 12),
        ("inválido", None),
        ("Wed, 21 Oct 2015 07:28:30 GMT", 30),
    ],
)
def test_calcular_espera_retry_after(valor, esperado):
    agora = datetime(2015, 10, 21, 7, 28, 0, tzinfo=timezone.utc)

    assert client._calcular_espera_retry_after(valor, agora) == esperado


def test_calcular_espera_retry_after_rejeita_data_sem_timezone():
    assert (
        client._calcular_espera_retry_after("Wed, 21 Oct 2015 07:28:00")
        is None
    )


def test_calcular_espera_retry_after_sinaliza_valor_acima_do_limite():
    espera = client._calcular_espera_retry_after(
        str(client.MAX_ESPERA_RETRY_AFTER + 1)
    )

    assert espera == client.MAX_ESPERA_RETRY_AFTER + 1

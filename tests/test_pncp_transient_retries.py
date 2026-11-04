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
            raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


def test_buscar_pagina_repete_timeout_transitorio(monkeypatch):
    respostas = iter(
        [
            requests.exceptions.Timeout("timeout simulado"),
            RespostaFake(200, payload={"ok": True}),
        ]
    )
    chamadas = []
    esperas = []

    def get_fake(*_args, **_kwargs):
        chamadas.append(1)
        resposta = next(respostas)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta

    monkeypatch.setattr(client.requests, "get", get_fake)
    monkeypatch.setattr(client.time, "sleep", esperas.append)

    assert client.buscar_pagina(client.URL_PNCP, {}) == {"ok": True}
    assert len(chamadas) == 2
    assert esperas == [2]


def test_buscar_pagina_limita_retentativas_de_falha_de_conexao(monkeypatch):
    chamadas = []
    esperas = []

    def get_fake(*_args, **_kwargs):
        chamadas.append(1)
        raise requests.exceptions.ConnectionError("conexão simulada")

    monkeypatch.setattr(client.requests, "get", get_fake)
    monkeypatch.setattr(client.time, "sleep", esperas.append)

    with pytest.raises(requests.exceptions.ConnectionError):
        client.buscar_pagina(client.URL_PNCP, {})

    assert len(chamadas) == client.MAX_TENTATIVAS
    assert esperas == [2, 4, 8, 16]


def test_buscar_pagina_repete_http_503_e_respeita_retry_after(monkeypatch):
    respostas = iter(
        [
            RespostaFake(503, headers={"Retry-After": "5"}),
            RespostaFake(200, payload={"ok": True}),
        ]
    )
    esperas = []

    monkeypatch.setattr(
        client.requests,
        "get",
        lambda *_args, **_kwargs: next(respostas),
    )
    monkeypatch.setattr(client.time, "sleep", esperas.append)

    assert client.buscar_pagina(client.URL_PNCP, {}) == {"ok": True}
    assert esperas == [5]


@pytest.mark.parametrize("status_code", [408, 500, 502, 504])
def test_buscar_pagina_repete_outros_erros_http_transitorios_com_backoff(
    monkeypatch,
    status_code,
):
    respostas = iter(
        [
            RespostaFake(status_code),
            RespostaFake(200, payload={"ok": True}),
        ]
    )
    esperas = []

    monkeypatch.setattr(
        client.requests,
        "get",
        lambda *_args, **_kwargs: next(respostas),
    )
    monkeypatch.setattr(client.time, "sleep", esperas.append)

    assert client.buscar_pagina(client.URL_PNCP, {}) == {"ok": True}
    assert esperas == [2]


def test_buscar_pagina_preserva_retry_de_rate_limit_429(monkeypatch):
    respostas = iter(
        [
            RespostaFake(429, headers={"Retry-After": "4"}),
            RespostaFake(200, payload={"ok": True}),
        ]
    )
    esperas = []

    monkeypatch.setattr(
        client.requests,
        "get",
        lambda *_args, **_kwargs: next(respostas),
    )
    monkeypatch.setattr(client.time, "sleep", esperas.append)

    assert client.buscar_pagina(client.URL_PNCP, {}) == {"ok": True}
    assert esperas == [4]


def test_buscar_pagina_nao_repete_erro_http_permanente(monkeypatch):
    chamadas = []
    esperas = []

    def get_fake(*_args, **_kwargs):
        chamadas.append(1)
        return RespostaFake(400)

    monkeypatch.setattr(client.requests, "get", get_fake)
    monkeypatch.setattr(client.time, "sleep", esperas.append)

    with pytest.raises(requests.exceptions.HTTPError, match="HTTP 400"):
        client.buscar_pagina(client.URL_PNCP, {})

    assert len(chamadas) == 1
    assert esperas == []


def test_buscar_pagina_nao_repete_falha_tls(monkeypatch):
    chamadas = []
    esperas = []

    def get_fake(*_args, **_kwargs):
        chamadas.append(1)
        raise requests.exceptions.SSLError("certificado inválido")

    monkeypatch.setattr(client.requests, "get", get_fake)
    monkeypatch.setattr(client.time, "sleep", esperas.append)

    with pytest.raises(requests.exceptions.SSLError):
        client.buscar_pagina(client.URL_PNCP, {})

    assert len(chamadas) == 1
    assert esperas == []


def test_buscar_pagina_apos_maximo_de_http_503_propaga_http_error(monkeypatch):
    chamadas = []
    esperas = []

    def get_fake(*_args, **_kwargs):
        chamadas.append(1)
        return RespostaFake(503)

    monkeypatch.setattr(client.requests, "get", get_fake)
    monkeypatch.setattr(client.time, "sleep", esperas.append)

    with pytest.raises(requests.exceptions.HTTPError, match="HTTP 503"):
        client.buscar_pagina(client.URL_PNCP, {})

    assert len(chamadas) == client.MAX_TENTATIVAS
    assert esperas == [2, 4, 8, 16]


def test_buscar_pagina_limita_timeout_ao_tempo_restante(monkeypatch):
    timeouts = []

    def get_fake(*_args, timeout, **_kwargs):
        timeouts.append(timeout)
        return RespostaFake(200, payload={"ok": True})

    monkeypatch.setattr(client.time, "monotonic", lambda: 10.0)
    monkeypatch.setattr(client.requests, "get", get_fake)

    assert (
        client.buscar_pagina(client.URL_PNCP, {}, prazo_final=15.0)
        == {"ok": True}
    )
    assert timeouts == [5.0]


def test_buscar_pagina_nao_inicia_requisicao_depois_do_prazo(monkeypatch):
    monkeypatch.setattr(client.time, "monotonic", lambda: 15.0)
    monkeypatch.setattr(
        client.requests,
        "get",
        lambda *_args, **_kwargs: pytest.fail("requisição após o prazo"),
    )

    with pytest.raises(client.PrazoTotalConsultaPNPCError):
        client.buscar_pagina(client.URL_PNCP, {}, prazo_final=15.0)


def test_buscar_pagina_nao_aguarda_retry_que_excede_o_prazo(monkeypatch):
    esperas = []
    relogio = [10.0]

    def dormir(segundos):
        esperas.append(segundos)
        relogio[0] += segundos

    monkeypatch.setattr(client.time, "monotonic", lambda: relogio[0])
    monkeypatch.setattr(
        client.requests,
        "get",
        lambda *_args, **_kwargs: RespostaFake(503),
    )
    monkeypatch.setattr(client.time, "sleep", dormir)

    with pytest.raises(client.PrazoTotalConsultaPNPCError):
        client.buscar_pagina(client.URL_PNCP, {}, prazo_final=15.0)

    assert esperas == [2]


def test_buscar_pagina_aplica_prazo_a_backoff_de_falha_de_rede(monkeypatch):
    chamadas = []
    esperas = []
    timeouts = []
    relogio = [10.0]

    def get_fake(*_args, timeout, **_kwargs):
        chamadas.append(1)
        timeouts.append(timeout)
        relogio[0] += 0.5
        raise requests.exceptions.Timeout("timeout simulado")

    def dormir(segundos):
        esperas.append(segundos)
        relogio[0] += segundos

    monkeypatch.setattr(client.time, "monotonic", lambda: relogio[0])
    monkeypatch.setattr(client.requests, "get", get_fake)
    monkeypatch.setattr(client.time, "sleep", dormir)

    with pytest.raises(client.PrazoTotalConsultaPNPCError):
        client.buscar_pagina(client.URL_PNCP, {}, prazo_final=13.0)

    assert len(chamadas) == 2
    assert timeouts == [3.0, 0.5]
    assert esperas == [2]


def test_buscar_licitacoes_compartilha_um_prazo_entre_paginas(monkeypatch):
    prazos = []

    def buscar_pagina_fake(_url, parametros, *, prazo_final):
        prazos.append(prazo_final)
        return {"data": [], "totalPaginas": 2}

    monkeypatch.setattr(client.time, "monotonic", lambda: 10.0)
    monkeypatch.setattr(client.time, "sleep", lambda _segundos: None)
    monkeypatch.setattr(client, "buscar_pagina", buscar_pagina_fake)

    assert client.buscar_licitacoes("RJ") == []
    assert prazos == [310.0, 310.0]


def test_buscar_licitacoes_interrompe_paginacao_ao_exceder_prazo(monkeypatch):
    chamadas = []
    relogio = iter([0.0, 1.0, 2.0, 3.0, 4.0, 301.0])

    def buscar_pagina_fake(_url, parametros, *, prazo_final):
        chamadas.append(parametros["pagina"])
        return {"data": [], "totalPaginas": 2}

    monkeypatch.setattr(client.time, "monotonic", lambda: next(relogio))
    monkeypatch.setattr(client.time, "sleep", lambda _segundos: None)
    monkeypatch.setattr(client, "buscar_pagina", buscar_pagina_fake)

    with pytest.raises(client.PrazoTotalConsultaPNPCError):
        client.buscar_licitacoes("RJ")

    assert chamadas == [1]

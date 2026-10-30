import requests
from fastapi.testclient import TestClient

from app import main
from app.pncp import client as pncp_client
from app.repositories import licitacao_repository
from app.services import licitacao_service


def test_get_licitacoes_retorna_contrato_json_e_filtros_normalizados(monkeypatch):
    chamadas = []
    resultados = [
        {
            "numero": "1/2026",
            "descricao": "Compra de material",
            "codigo_unidade": "123",
            "municipio": "Niterói",
            "uf": "RJ",
            "data_encerramento_proposta": "2026-10-30T18:00:00-03:00",
        }
    ]

    def consultar(uf, produto):
        chamadas.append((uf, produto))
        return 4, resultados, "2026-10-30T12:00:00+00:00"

    monkeypatch.setattr(licitacao_repository, "consultar_licitacoes", consultar)

    with TestClient(main.app) as cliente:
        resposta = cliente.get("/api/licitacoes", params={"uf": " rj ", "produto": " MATERIAL "})

    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("application/json")
    assert resposta.json() == {
        "uf": "RJ",
        "produto": "material",
        "total_consultado": 4,
        "total": 1,
        "resultados": resultados,
        "ultima_sincronizacao": "2026-10-30T12:00:00+00:00",
    }
    assert chamadas == [("RJ", "material")]


def test_get_licitacoes_sem_registros_retorna_lista_vazia(monkeypatch):
    monkeypatch.setattr(
        licitacao_repository,
        "consultar_licitacoes",
        lambda _uf, _produto: (0, [], None),
    )

    with TestClient(main.app) as cliente:
        resposta = cliente.get("/api/licitacoes", params={"uf": "SP"})

    assert resposta.status_code == 200
    assert resposta.json() == {
        "uf": "SP",
        "produto": "",
        "total_consultado": 0,
        "total": 0,
        "resultados": [],
        "ultima_sincronizacao": None,
    }


def test_get_licitacoes_nao_consulta_pncp_e_funciona_se_pncp_estiver_indisponivel(
    monkeypatch,
):
    def pncp_indisponivel(*_args, **_kwargs):
        raise requests.ConnectionError("PNCP indisponível")

    monkeypatch.setattr(pncp_client, "buscar_licitacoes", pncp_indisponivel)
    monkeypatch.setattr(licitacao_service, "buscar_licitacoes", pncp_indisponivel)
    monkeypatch.setattr(
        licitacao_repository,
        "consultar_licitacoes",
        lambda _uf, _produto: (
            1,
            [{"numero": "2/2026", "descricao": "Registro salvo"}],
            "2026-10-30T12:00:00+00:00",
        ),
    )

    with TestClient(main.app) as cliente:
        resposta = cliente.get("/api/licitacoes", params={"uf": "SP"})

    assert resposta.status_code == 200
    assert resposta.json()["total"] == 1
    assert resposta.json()["resultados"][0]["descricao"] == "Registro salvo"


def test_get_licitacoes_valida_parametro_uf(monkeypatch):
    monkeypatch.setattr(
        licitacao_repository,
        "consultar_licitacoes",
        lambda _uf, _produto: (0, [], None),
    )

    with TestClient(main.app) as cliente:
        sem_uf = cliente.get("/api/licitacoes")
        uf_invalida = cliente.get("/api/licitacoes", params={"uf": "R"})

    assert sem_uf.status_code == 200
    assert uf_invalida.status_code == 400
    assert uf_invalida.json() == {
        "detail": "Informe a sigla do estado com 2 letras."
    }


def test_get_licitacoes_oculta_detalhes_de_falha_interna(monkeypatch, caplog):
    def falha_banco(_uf, _produto):
        raise RuntimeError("senha=nao-deve-aparecer")

    monkeypatch.setattr(licitacao_repository, "consultar_licitacoes", falha_banco)

    with TestClient(main.app) as cliente:
        resposta = cliente.get("/api/licitacoes", params={"uf": "SP"})

    assert resposta.status_code == 500
    assert resposta.json() == {"detail": "Erro interno ao processar a consulta."}
    assert "senha=nao-deve-aparecer" not in resposta.text
    assert "senha=nao-deve-aparecer" not in caplog.text
    assert "RuntimeError" in caplog.text


def test_aplicacao_serve_frontend_e_assets_estaticos():
    with TestClient(main.app) as cliente:
        pagina = cliente.get("/")
        app_js = cliente.get("/app.js")
        api_js = cliente.get("/api.js")
        estilos = cliente.get("/nexus.css")

    assert pagina.status_code == 200
    assert 'src="app.js"' in pagina.text
    assert app_js.status_code == api_js.status_code == estilos.status_code == 200
    assert app_js.headers["content-type"].startswith("text/javascript")
    assert "Consultando a base do NEXUS" in app_js.text


def test_frontend_funciona_fora_do_diretorio_do_repositorio(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    with TestClient(main.app) as cliente:
        resposta = cliente.get("/")

    assert resposta.status_code == 200
    assert "NEXUS · Licitações" in resposta.text


def test_get_licitacoes_permite_consultar_todas_as_ufs(monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        licitacao_repository,
        "consultar_licitacoes",
        lambda uf, produto: chamadas.append((uf, produto)) or (2, [], None),
    )

    with TestClient(main.app) as cliente:
        resposta = cliente.get("/api/licitacoes")

    assert resposta.status_code == 200
    assert resposta.json()["uf"] is None
    assert chamadas == [(None, "")]

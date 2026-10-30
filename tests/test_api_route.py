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

    def consultar(uf, produto, page, page_size, prazo_dias):
        chamadas.append((uf, produto, page, page_size, prazo_dias))
        return 4, 1, resultados, "2026-10-30T12:00:00+00:00", {
            "status": "concluida",
            "iniciada_em": "2026-10-30T11:59:00+00:00",
            "finalizada_em": "2026-10-30T12:00:00+00:00",
            "paginas_consultadas": 1,
            "registros_processados": 1,
        }

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
        "page": 1,
        "page_size": 25,
        "total_pages": 1,
        "resultados": resultados,
        "ultima_sincronizacao": "2026-10-30T12:00:00+00:00",
        "ultima_execucao": {
            "status": "concluida",
            "iniciada_em": "2026-10-30T11:59:00+00:00",
            "finalizada_em": "2026-10-30T12:00:00+00:00",
            "paginas_consultadas": 1,
            "registros_processados": 1,
        },
    }
    assert chamadas == [("RJ", "material", 1, 25, None)]


def test_get_licitacoes_sem_registros_retorna_lista_vazia(monkeypatch):
    monkeypatch.setattr(
        licitacao_repository,
        "consultar_licitacoes",
        lambda _uf, _produto, **_kwargs: (0, 0, [], None, None),
    )

    with TestClient(main.app) as cliente:
        resposta = cliente.get("/api/licitacoes", params={"uf": "SP"})

    assert resposta.status_code == 200
    assert resposta.json() == {
        "uf": "SP",
        "produto": "",
        "total_consultado": 0,
        "total": 0,
        "page": 1,
        "page_size": 25,
        "total_pages": 0,
        "resultados": [],
        "ultima_sincronizacao": None,
        "ultima_execucao": None,
    }


def test_get_licitacoes_repassa_paginacao_e_prazo_ao_servico(monkeypatch):
    chamadas = []

    def consultar(uf, produto, page, page_size, prazo_dias):
        chamadas.append((uf, produto, page, page_size, prazo_dias))
        return 20, 12, [{"numero": str(page)}], None, None

    monkeypatch.setattr(licitacao_repository, "consultar_licitacoes", consultar)

    with TestClient(main.app) as cliente:
        resposta = cliente.get(
            "/api/licitacoes",
            params={"page": 2, "page_size": 5, "prazo_dias": 7},
        )

    assert resposta.status_code == 200
    assert resposta.json()["page"] == 2
    assert resposta.json()["page_size"] == 5
    assert resposta.json()["total_pages"] == 3
    assert resposta.json()["total"] == 12
    assert chamadas == [(None, "", 2, 5, 7)]


def test_get_licitacoes_rejeita_limites_de_paginacao_e_prazo(monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        licitacao_repository,
        "consultar_licitacoes",
        lambda *_args, **_kwargs: chamadas.append(1) or (0, 0, [], None, None),
    )

    with TestClient(main.app) as cliente:
        paginas_invalidas = [
            cliente.get("/api/licitacoes", params={"page": 0}),
            cliente.get("/api/licitacoes", params={"page": 10001}),
            cliente.get("/api/licitacoes", params={"page_size": 0}),
            cliente.get("/api/licitacoes", params={"page_size": 101}),
            cliente.get("/api/licitacoes", params={"prazo_dias": 31}),
        ]

    assert all(resposta.status_code == 422 for resposta in paginas_invalidas)
    assert chamadas == []


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
        lambda _uf, _produto, **_kwargs: (
            1,
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
        lambda _uf, _produto, **_kwargs: (0, 0, [], None, None),
    )

    with TestClient(main.app) as cliente:
        sem_uf = cliente.get("/api/licitacoes")
        uf_curta = cliente.get("/api/licitacoes", params={"uf": "R"})
        uf_desconhecida = cliente.get("/api/licitacoes", params={"uf": "ZZ"})

    assert sem_uf.status_code == 200
    assert uf_curta.status_code == uf_desconhecida.status_code == 400
    assert uf_curta.json() == uf_desconhecida.json() == {
        "detail": "Informe uma sigla de UF válida."
    }


def test_get_licitacoes_rejeita_produto_acima_de_cem_caracteres(monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        licitacao_repository,
        "consultar_licitacoes",
        lambda *_args, **_kwargs: chamadas.append(1) or (0, 0, [], None, None),
    )

    with TestClient(main.app) as cliente:
        resposta = cliente.get("/api/licitacoes", params={"produto": "x" * 101})

    assert resposta.status_code == 422
    assert chamadas == []


def test_get_licitacoes_oculta_detalhes_de_falha_interna(monkeypatch, caplog):
    def falha_banco(_uf, _produto, **_kwargs):
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
        logo = cliente.get("/assets/nexus-logo.png")
        favicon = cliente.get("/assets/favicon.png")

    assert pagina.status_code == 200
    assert 'src="app.js"' in pagina.text
    assert app_js.status_code == api_js.status_code == estilos.status_code == 200
    assert logo.status_code == favicon.status_code == 200
    assert logo.headers["content-type"] == favicon.headers["content-type"] == "image/png"
    assert 'href="assets/favicon.png"' in pagina.text
    assert 'src="assets/nexus-logo.png"' in pagina.text
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
        lambda uf, produto, **_kwargs: chamadas.append((uf, produto))
        or (2, 2, [], None, None),
    )

    with TestClient(main.app) as cliente:
        resposta = cliente.get("/api/licitacoes")

    assert resposta.status_code == 200
    assert resposta.json()["uf"] is None
    assert chamadas == [(None, "")]

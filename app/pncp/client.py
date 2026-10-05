import requests

from app.pncp.parser import normalizar_licitacao


def buscar_licitacoes(estado: str):

    url = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"

    parametros = {
        "dataInicial": "20260901",
        "dataFinal": "20260930",
        "codigoModalidadeContratacao": 6,
        "uf": estado,
        "pagina": 1,
    }

    resposta = requests.get(
        url,
        params=parametros,
        timeout=30,
    )

    resposta.raise_for_status()

    dados = resposta.json()

    licitacoes_pncp = dados["data"]

    return [
        normalizar_licitacao(licitacao)
        for licitacao in licitacoes_pncp
    ]
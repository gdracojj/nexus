import requests
from datetime import datetime, timedelta

from app.pncp.parser import normalizar_licitacao


def buscar_licitacoes(estado: str):
    url = "https://pncp.gov.br/api/consulta/v1/contratacoes/proposta"

    hoje = datetime.now()
    data_inicio = hoje.strftime("%Y%m%d")
    data_fim = (hoje + timedelta(days=7)).strftime("%Y%m%d")

    pagina = 1
    todas_licitacoes = []

    while True:
        parametros = {
            "dataInicial": data_inicio,
            "dataFinal": data_fim,
            "codigoModalidadeContratacao": 6,
            "uf": estado,
            "pagina": pagina,
        }

        resposta = requests.get(
            url,
            params=parametros,
            timeout=30,
        )

        resposta.raise_for_status()

        dados = resposta.json()

        licitacoes_pagina = dados.get("data", [])
        todas_licitacoes.extend(licitacoes_pagina)

        total_paginas = dados.get("totalPaginas", 1)

        if pagina >= total_paginas:
            break

        pagina += 1

    return [
        normalizar_licitacao(licitacao)
        for licitacao in todas_licitacoes
    ]
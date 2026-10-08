import time
from datetime import datetime, timedelta

import requests

from app.pncp.parser import normalizar_licitacao


URL_PNCP = "https://pncp.gov.br/api/consulta/v1/contratacoes/proposta"

INTERVALO_ENTRE_PAGINAS = 1.0
MAX_TENTATIVAS = 5


def buscar_pagina(
    url: str,
    parametros: dict,
) -> dict:

    for tentativa in range(1, MAX_TENTATIVAS + 1):

        resposta = requests.get(
            url,
            params=parametros,
            timeout=30,
        )

        if resposta.status_code != 429:
            resposta.raise_for_status()
            return resposta.json()

        retry_after = resposta.headers.get("Retry-After")

        if retry_after:
            espera = int(retry_after)
        else:
            espera = 2 ** tentativa

        print(
            f"PNCP rate limitado (429). "
            f"Tentativa {tentativa}/{MAX_TENTATIVAS}. "
            f"Aguardando {espera}s..."
        )

        if tentativa == MAX_TENTATIVAS:
            resposta.raise_for_status()

        time.sleep(espera)

    raise RuntimeError("Não foi possível consultar o PNCP.")


def buscar_licitacoes(estado: str):

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

        dados = buscar_pagina(
            URL_PNCP,
            parametros,
        )

        licitacoes_pagina = dados.get("data", [])

        todas_licitacoes.extend(licitacoes_pagina)

        total_paginas = dados.get("totalPaginas", 1)

        print(
            f"PNCP: página {pagina}/{total_paginas} "
            f"- {len(licitacoes_pagina)} registros"
        )

        if pagina >= total_paginas:
            break

        pagina += 1

        time.sleep(INTERVALO_ENTRE_PAGINAS)

    return [
        normalizar_licitacao(licitacao)
        for licitacao in todas_licitacoes
    ]
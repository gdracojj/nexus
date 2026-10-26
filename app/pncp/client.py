import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests

from app.pncp.parser import (
    RegistroPNCPInvalidoError,
    normalizar_licitacao,
)


URL_PNCP = "https://pncp.gov.br/api/consulta/v1/contratacoes/proposta"

INTERVALO_ENTRE_PAGINAS = 1.0
MAX_TENTATIVAS = 5
MAX_ESPERA_RETRY_AFTER = 60
MAX_PAGINAS_CONSULTA = 100


class LimitePaginacaoPNCPError(requests.exceptions.RequestException):
    """O PNCP informou mais páginas do que esta consulta aceita processar."""


def _calcular_espera_retry_after(
    valor: str | None,
    agora: datetime | None = None,
) -> float | None:
    if valor is None:
        return None

    valor = valor.strip()

    if valor.isascii() and valor.isdecimal():
        segundos = valor.lstrip("0") or "0"
        if len(segundos) > len(str(MAX_ESPERA_RETRY_AFTER)):
            return MAX_ESPERA_RETRY_AFTER + 1
        espera = int(segundos)
    else:
        try:
            data_retentativa = parsedate_to_datetime(valor)
        except (TypeError, ValueError, OverflowError):
            return None

        if data_retentativa is None or data_retentativa.tzinfo is None:
            return None

        agora = agora or datetime.now(timezone.utc)
        espera = max(0, (data_retentativa - agora).total_seconds())

    return espera


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
        espera = _calcular_espera_retry_after(retry_after)

        if espera is None:
            espera = 2 ** tentativa
        elif espera > MAX_ESPERA_RETRY_AFTER:
            raise requests.exceptions.HTTPError(
                "Retry-After excede o limite máximo de espera.",
                response=resposta,
            )

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

        if not isinstance(dados, dict):
            raise requests.exceptions.RequestException(
                "PNCP retornou uma resposta que não é um objeto JSON."
            )

        total_paginas = dados.get("totalPaginas")
        if (
            isinstance(total_paginas, bool)
            or not isinstance(total_paginas, int)
            or total_paginas < 0
        ):
            raise requests.exceptions.RequestException(
                "PNCP retornou um total de páginas inválido."
            )

        if total_paginas > MAX_PAGINAS_CONSULTA:
            raise LimitePaginacaoPNCPError(
                f"PNCP informou {total_paginas} páginas; "
                f"o limite desta consulta é {MAX_PAGINAS_CONSULTA}."
            )

        licitacoes_pagina = dados.get("data")
        if not isinstance(licitacoes_pagina, list):
            raise requests.exceptions.RequestException(
                "PNCP retornou o campo 'data' fora do formato de lista."
            )
        if total_paginas == 0 and licitacoes_pagina:
            raise requests.exceptions.RequestException(
                "PNCP retornou registros com total de páginas igual a zero."
            )

        todas_licitacoes.extend(licitacoes_pagina)

        print(
            f"PNCP: página {pagina}/{total_paginas} "
            f"- {len(licitacoes_pagina)} registros"
        )

        if pagina >= total_paginas:
            break

        pagina += 1

        time.sleep(INTERVALO_ENTRE_PAGINAS)

    licitacoes_normalizadas = []
    for indice, licitacao in enumerate(todas_licitacoes, start=1):
        try:
            licitacoes_normalizadas.append(normalizar_licitacao(licitacao))
        except RegistroPNCPInvalidoError as erro:
            raise requests.exceptions.RequestException(
                f"PNCP retornou registro inválido na posição {indice}: {erro}"
            ) from erro

    return licitacoes_normalizadas

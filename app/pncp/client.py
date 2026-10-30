import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests

from app.pncp.parser import (
    RegistroPNCPInvalidoError,
    normalizar_licitacao,
    registro_para_persistencia,
)


URL_PNCP = "https://pncp.gov.br/api/consulta/v1/contratacoes/proposta"

INTERVALO_ENTRE_PAGINAS = 1.0
MAX_TENTATIVAS = 5
MAX_ESPERA_RETRY_AFTER = 60
MAX_PAGINAS_CONSULTA = 110
MAX_PAGINAS_CONSULTA_SP = 160
PRAZO_TOTAL_CONSULTA_SEGUNDOS = 300.0
TIMEOUT_REQUISICAO_SEGUNDOS = 30.0
CODIGOS_HTTP_REPETIVEIS = frozenset({408, 429, 500, 502, 503, 504})


class LimitePaginacaoPNCPError(requests.exceptions.RequestException):
    """O PNCP informou mais páginas do que esta consulta aceita processar."""


def _limite_paginas_consulta(estado: str) -> int:
    if estado.strip().upper() == "SP":
        return MAX_PAGINAS_CONSULTA_SP
    return MAX_PAGINAS_CONSULTA


def parametros_consulta(estado: str, agora: datetime | None = None) -> dict:
    hoje = agora or datetime.now()
    return {
        "dataInicial": hoje.strftime("%Y%m%d"),
        "dataFinal": (hoje + timedelta(days=7)).strftime("%Y%m%d"),
        "codigoModalidadeContratacao": 6,
        "uf": estado,
    }


class PrazoTotalConsultaPNPCError(requests.exceptions.RequestException):
    """O prazo total da consulta ao PNCP foi excedido."""


def _verificar_prazo(prazo_final: float) -> float:
    tempo_restante = prazo_final - time.monotonic()
    if tempo_restante <= 0:
        raise PrazoTotalConsultaPNPCError(
            "O prazo total da consulta ao PNCP foi excedido."
        )
    return tempo_restante


def _aguardar_com_prazo(espera: float, prazo_final: float) -> None:
    tempo_restante = _verificar_prazo(prazo_final)
    if espera >= tempo_restante:
        raise PrazoTotalConsultaPNPCError(
            "O prazo total da consulta ao PNCP não permite outra tentativa."
        )

    time.sleep(espera)
    _verificar_prazo(prazo_final)


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
    prazo_final: float | None = None,
) -> dict:
    if prazo_final is None:
        prazo_final = time.monotonic() + PRAZO_TOTAL_CONSULTA_SEGUNDOS

    for tentativa in range(1, MAX_TENTATIVAS + 1):
        tempo_restante = _verificar_prazo(prazo_final)
        try:
            resposta = requests.get(
                url,
                params=parametros,
                timeout=min(TIMEOUT_REQUISICAO_SEGUNDOS, tempo_restante),
            )
            _verificar_prazo(prazo_final)
        except requests.exceptions.SSLError:
            raise
        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
        ):
            if tentativa == MAX_TENTATIVAS:
                raise

            espera = 2**tentativa
            print(
                f"Falha transitória de comunicação com o PNCP. "
                f"Tentativa {tentativa}/{MAX_TENTATIVAS}. "
                f"Aguardando {espera}s..."
            )
            _aguardar_com_prazo(espera, prazo_final)
            continue

        if resposta.status_code not in CODIGOS_HTTP_REPETIVEIS:
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

        if resposta.status_code == 429:
            motivo = "rate limitado"
        else:
            motivo = f"resposta HTTP {resposta.status_code} transitória"

        print(
            f"PNCP {motivo}. Tentativa {tentativa}/{MAX_TENTATIVAS}. "
            f"Aguardando {espera}s..."
        )

        if tentativa == MAX_TENTATIVAS:
            resposta.raise_for_status()

        _aguardar_com_prazo(espera, prazo_final)

    raise RuntimeError("Não foi possível consultar o PNCP.")


def buscar_licitacoes(
    estado: str,
    incluir_payload: bool = False,
    parametros_base=None,
    ao_receber_registros=None,
    ao_consultar_pagina=None,
):
    prazo_final = time.monotonic() + PRAZO_TOTAL_CONSULTA_SEGUNDOS
    limite_paginas = _limite_paginas_consulta(estado)

    if parametros_base is None:
        parametros_base = parametros_consulta(estado)

    pagina = 1
    todas_licitacoes = []

    while True:
        _verificar_prazo(prazo_final)

        parametros = {**parametros_base, "pagina": pagina}

        dados = buscar_pagina(
            URL_PNCP,
            parametros,
            prazo_final=prazo_final,
        )
        _verificar_prazo(prazo_final)

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

        if total_paginas > limite_paginas:
            raise LimitePaginacaoPNCPError(
                f"PNCP informou {total_paginas} páginas; "
                f"o limite desta consulta é {limite_paginas}."
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
        if ao_receber_registros is not None:
            ao_receber_registros(len(licitacoes_pagina))
        if ao_consultar_pagina is not None:
            ao_consultar_pagina(pagina, len(licitacoes_pagina))

        print(
            f"PNCP: página {pagina}/{total_paginas} "
            f"- {len(licitacoes_pagina)} registros"
        )

        if pagina >= total_paginas:
            break

        pagina += 1

        _aguardar_com_prazo(INTERVALO_ENTRE_PAGINAS, prazo_final)

    licitacoes_normalizadas = []
    for indice, licitacao in enumerate(todas_licitacoes, start=1):
        _verificar_prazo(prazo_final)
        try:
            if incluir_payload:
                licitacoes_normalizadas.append(registro_para_persistencia(licitacao))
            else:
                licitacoes_normalizadas.append(normalizar_licitacao(licitacao))
        except RegistroPNCPInvalidoError as erro:
            falha = requests.exceptions.RequestException(
                f"PNCP retornou registro inválido na posição {indice}: {erro}"
            )
            falha.registros_recebidos = len(todas_licitacoes)
            falha.registros_com_erro = 1
            raise falha from erro

    _verificar_prazo(prazo_final)
    return licitacoes_normalizadas

from datetime import datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo


class RegistroPNCPInvalidoError(ValueError):
    """Registro do PNCP ausente, malformado ou fora do formato esperado."""


def _texto_obrigatorio(dados, campo):
    valor = dados.get(campo)
    if not isinstance(valor, str) or not valor.strip():
        raise RegistroPNCPInvalidoError(
            f"campo '{campo}' deve ser um texto não vazio."
        )
    return valor.strip()


def _texto_opcional(dados, campo):
    valor = dados.get(campo)
    if valor is None:
        return None
    if not isinstance(valor, str):
        raise RegistroPNCPInvalidoError(
            f"campo '{campo}' deve ser texto ou nulo."
        )
    return valor.strip()


def normalizar_licitacao(licitacao):
    if not isinstance(licitacao, dict):
        raise RegistroPNCPInvalidoError("registro deve ser um objeto JSON.")

    numero = _texto_obrigatorio(licitacao, "numeroCompra")
    descricao = _texto_obrigatorio(licitacao, "objetoCompra")

    unidade = licitacao.get("unidadeOrgao")
    if not isinstance(unidade, dict):
        raise RegistroPNCPInvalidoError(
            "campo 'unidadeOrgao' deve ser um objeto JSON."
        )

    codigo_unidade = _texto_opcional(unidade, "codigoUnidade")
    municipio = _texto_opcional(unidade, "municipioNome")
    uf = _texto_obrigatorio(unidade, "ufSigla").upper()
    if len(uf) != 2 or not uf.isascii() or not uf.isalpha():
        raise RegistroPNCPInvalidoError(
            "campo 'unidadeOrgao.ufSigla' deve conter duas letras ASCII."
        )

    data_encerramento = _texto_opcional(
        licitacao,
        "dataEncerramentoProposta",
    )

    return {
        "numero": numero,
        "descricao": descricao,
        "codigo_unidade": codigo_unidade,
        "municipio": municipio,
        "uf": uf,
        "data_encerramento_proposta": data_encerramento,
    }


def registro_para_persistencia(licitacao):
    """Extrai campos documentados do resumo PNCP e mantém o JSON de origem."""
    normalizado = normalizar_licitacao(licitacao)
    controle = _texto_obrigatorio(licitacao, "numeroControlePNCP")
    if len(controle) > 40:
        raise RegistroPNCPInvalidoError("campo 'numeroControlePNCP' excede 40 caracteres.")

    orgao = licitacao.get("orgaoEntidade") or {}
    if not isinstance(orgao, dict):
        raise RegistroPNCPInvalidoError("campo 'orgaoEntidade' deve ser um objeto JSON ou nulo.")

    data = {
        "numero_controle_pncp": controle,
        "cnpj_orgao": _texto_opcional(orgao, "cnpj"),
        "nome_orgao": _texto_opcional(orgao, "razaoSocial"),
        "codigo_modalidade": _inteiro_opcional(licitacao, "codigoModalidadeContratacao"),
        "numero": normalizado["numero"],
        "codigo_unidade": normalizado["codigo_unidade"],
        "ano": _inteiro_opcional(licitacao, "anoCompra"),
        "descricao": normalizado["descricao"],
        "uf": normalizado["uf"],
        "municipio": normalizado["municipio"],
        "data_publicacao": _data_opcional(licitacao, "dataPublicacaoPncp"),
        "data_abertura_proposta": _data_opcional(licitacao, "dataAberturaProposta"),
        "data_encerramento_proposta": _data_opcional(licitacao, "dataEncerramentoProposta"),
        "valor_estimado": _decimal_opcional(licitacao, "valorTotalEstimado"),
        "situacao": _texto_opcional(licitacao, "situacaoCompraNome"),
        "payload": licitacao,
    }
    return data


def _inteiro_opcional(dados, campo):
    valor = dados.get(campo)
    if valor is None:
        return None
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise RegistroPNCPInvalidoError(f"campo '{campo}' deve ser inteiro ou nulo.")
    return valor


def _decimal_opcional(dados, campo):
    valor = dados.get(campo)
    if valor is None:
        return None
    if isinstance(valor, bool) or not isinstance(valor, (int, float, str)):
        raise RegistroPNCPInvalidoError(f"campo '{campo}' deve ser numérico ou nulo.")
    try:
        numero = Decimal(str(valor))
    except InvalidOperation as erro:
        raise RegistroPNCPInvalidoError(f"campo '{campo}' deve ser numérico ou nulo.") from erro
    if not numero.is_finite():
        raise RegistroPNCPInvalidoError(f"campo '{campo}' deve ser um número finito.")
    return numero


def _data_opcional(dados, campo):
    valor = dados.get(campo)
    if valor is None:
        return None
    if not isinstance(valor, str):
        raise RegistroPNCPInvalidoError(f"campo '{campo}' deve ser texto ISO ou nulo.")
    try:
        data = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError as erro:
        raise RegistroPNCPInvalidoError(f"campo '{campo}' deve ser uma data ISO válida.") from erro
    if data.tzinfo is None:
        data = data.replace(tzinfo=ZoneInfo("America/Sao_Paulo"))
    return data

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

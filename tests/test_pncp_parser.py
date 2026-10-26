import pytest

from app.pncp.parser import (
    RegistroPNCPInvalidoError,
    normalizar_licitacao,
)
from app.services.licitacao_service import filtrar_licitacoes


def registro_valido():
    return {
        "numeroCompra": "  12/2026  ",
        "objetoCompra": "  Compra de material  ",
        "unidadeOrgao": {
            "codigoUnidade": "123456",
            "municipioNome": "Rio de Janeiro",
            "ufSigla": " rj ",
        },
        "dataEncerramentoProposta": "2026-10-30T18:00:00",
    }


def test_normalizar_licitacao_valida_e_normaliza_campos():
    assert normalizar_licitacao(registro_valido()) == {
        "numero": "12/2026",
        "descricao": "Compra de material",
        "codigo_unidade": "123456",
        "municipio": "Rio de Janeiro",
        "uf": "RJ",
        "data_encerramento_proposta": "2026-10-30T18:00:00",
    }


@pytest.mark.parametrize(
    "campo",
    ["numeroCompra", "objetoCompra", "unidadeOrgao", "unidadeOrgao.ufSigla"],
)
def test_normalizar_licitacao_rejeita_campo_obrigatorio_ausente(campo):
    registro = registro_valido()
    if campo.startswith("unidadeOrgao."):
        del registro["unidadeOrgao"][campo.split(".", 1)[1]]
    else:
        del registro[campo]

    with pytest.raises(RegistroPNCPInvalidoError, match="campo"):
        normalizar_licitacao(registro)


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("numeroCompra", None),
        ("objetoCompra", 12),
        ("unidadeOrgao", []),
        ("unidadeOrgao.ufSigla", None),
        ("unidadeOrgao.ufSigla", "R"),
        ("unidadeOrgao.ufSigla", "R1"),
    ],
)
def test_normalizar_licitacao_rejeita_tipo_ou_valor_critico_invalido(
    campo,
    valor,
):
    registro = registro_valido()
    if campo.startswith("unidadeOrgao."):
        registro["unidadeOrgao"][campo.split(".", 1)[1]] = valor
    else:
        registro[campo] = valor

    with pytest.raises(RegistroPNCPInvalidoError):
        normalizar_licitacao(registro)


@pytest.mark.parametrize("registro", [None, [], "registro"])
def test_normalizar_licitacao_rejeita_raiz_que_nao_seja_objeto(registro):
    with pytest.raises(RegistroPNCPInvalidoError, match="objeto JSON"):
        normalizar_licitacao(registro)


def test_normalizar_licitacao_preserva_campos_opcionais_ausentes_ou_nulos():
    registro = registro_valido()
    del registro["unidadeOrgao"]["codigoUnidade"]
    registro["unidadeOrgao"]["municipioNome"] = None
    del registro["dataEncerramentoProposta"]

    resultado = normalizar_licitacao(registro)

    assert resultado["codigo_unidade"] is None
    assert resultado["municipio"] is None
    assert resultado["data_encerramento_proposta"] is None


def test_campos_opcionais_nulos_nao_interrompem_o_filtro_do_servico():
    registro = registro_valido()
    del registro["unidadeOrgao"]["codigoUnidade"]
    registro["unidadeOrgao"]["municipioNome"] = None
    registro["dataEncerramentoProposta"] = None
    normalizada = normalizar_licitacao(registro)

    assert filtrar_licitacoes([normalizada], "RJ", "material") == [normalizada]


@pytest.mark.parametrize(
    ("objeto", "campo", "valor"),
    [
        ("unidadeOrgao", "codigoUnidade", 123),
        ("unidadeOrgao", "municipioNome", []),
        ("registro", "dataEncerramentoProposta", 20261030),
    ],
)
def test_normalizar_licitacao_rejeita_tipo_invalido_em_campo_opcional(
    objeto,
    campo,
    valor,
):
    registro = registro_valido()
    alvo = registro["unidadeOrgao"] if objeto == "unidadeOrgao" else registro
    alvo[campo] = valor

    with pytest.raises(RegistroPNCPInvalidoError):
        normalizar_licitacao(registro)

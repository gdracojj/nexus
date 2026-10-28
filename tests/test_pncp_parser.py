import pytest

from app.pncp.parser import (
    RegistroPNCPInvalidoError,
    normalizar_licitacao,
    registro_para_persistencia,
)


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


def test_fuso_horario_tem_dados_de_fallback_instalados():
    import zoneinfo

    pytest.importorskip("tzdata")
    caminho_original = zoneinfo.TZPATH
    zoneinfo.reset_tzpath(())
    zoneinfo.ZoneInfo.clear_cache()
    try:
        assert zoneinfo.ZoneInfo("America/Sao_Paulo").key == "America/Sao_Paulo"
    except zoneinfo.ZoneInfoNotFoundError:
        pytest.fail("tzdata está instalado, mas não contém America/Sao_Paulo")
    finally:
        zoneinfo.reset_tzpath(caminho_original)
        zoneinfo.ZoneInfo.clear_cache()


def test_registro_para_persistencia_mapeia_identidade_valor_datas_e_payload():
    registro = registro_valido()
    registro.update(
        numeroControlePNCP="12345678000199-1-000001/2026",
        anoCompra=2026,
        codigoModalidadeContratacao=6,
        dataPublicacaoPncp="2026-10-20",
        dataAberturaProposta="2026-10-22T09:00:00-03:00",
        valorTotalEstimado=1234.5678,
        situacaoCompraNome="Divulgada no PNCP",
        orgaoEntidade={"cnpj": "12345678000199", "razaoSocial": "Órgão de teste"},
    )

    resultado = registro_para_persistencia(registro)

    assert resultado["numero_controle_pncp"] == registro["numeroControlePNCP"]
    assert resultado["cnpj_orgao"] == "12345678000199"
    assert resultado["nome_orgao"] == "Órgão de teste"
    assert resultado["codigo_modalidade"] == 6
    assert resultado["ano"] == 2026
    assert str(resultado["valor_estimado"]) == "1234.5678"
    assert resultado["data_publicacao"].tzinfo is not None
    assert resultado["data_abertura_proposta"].tzinfo is not None
    assert resultado["payload"] is registro


def test_registro_para_persistencia_aceita_campos_opcionais_ausentes():
    registro = registro_valido()
    registro["numeroControlePNCP"] = "12345678000199-1-000001/2026"

    resultado = registro_para_persistencia(registro)

    assert resultado["cnpj_orgao"] is None
    assert resultado["valor_estimado"] is None
    assert resultado["data_publicacao"] is None
    assert resultado["data_abertura_proposta"] is None


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

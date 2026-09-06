import requests


url = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"


def normalizar_licitacao(licitacao):

    resultado = {
        "numero": licitacao["numeroCompra"],
        "descricao": licitacao["objetoCompra"],
        "codigo_unidade": licitacao["unidadeOrgao"]["codigoUnidade"],
        "municipio": licitacao["unidadeOrgao"]["municipioNome"],
        "uf": licitacao["unidadeOrgao"]["ufSigla"]
    }

    return resultado


def filtrar_licitacoes(dados, estado, produto):

    resultado = []

    for licitacao in dados:

        if (
            licitacao["uf"] == estado
            and produto in licitacao["descricao"].lower()
        ):
            resultado.append(licitacao)

    return resultado


def main():

    print("NEXUS - iniciado com sucesso")

    estado = input("Digite o estado: ").upper()
    produto = input("Digite o produto desejado: ").lower()

    parametros = {
        "dataInicial": "20260901",
        "dataFinal": "20260930",
        "codigoModalidadeContratacao": 6,
        "uf": estado,
        "pagina": 1
    }

    resposta = requests.get(
        url,
        params=parametros,
        timeout=30
    )

    print(f"Status da consulta: {resposta.status_code}")

    dados = resposta.json()

    licitacoes_pncp = dados["data"]

    licitacoes_normalizadas = []

    for licitacao in licitacoes_pncp:
        licitacao_normalizada = normalizar_licitacao(licitacao)
        licitacoes_normalizadas.append(licitacao_normalizada)

    resultado = filtrar_licitacoes(
        licitacoes_normalizadas,
        estado,
        produto
    )

    quantidade = len(resultado)

    for licitacao in resultado:
        print(f'Número: {licitacao["numero"]}')
        print(f'Descrição: {licitacao["descricao"]}')
        print(f'Município: {licitacao["municipio"]}')
        print(f'UF: {licitacao["uf"]}')
        print()

    print(
        f"NEXUS - Quantidade de licitações encontradas: {quantidade}"
    )

    if quantidade == 0:
        print(
            "NEXUS - Nenhuma licitação encontrada "
            "com os filtros informados."
        )
    else:
        print(f"NEXUS - Licitações em {estado} encontradas.")


if __name__ == "__main__":
    main()
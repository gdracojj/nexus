from app.pncp.client import buscar_licitacoes


def filtrar_licitacoes(dados, estado, produto):
    resultado = []

    for licitacao in dados:
        if licitacao["uf"] != estado:
            continue

        if produto and produto not in licitacao["descricao"].lower():
            continue

        resultado.append(licitacao)

    return resultado


def buscar_e_filtrar_licitacoes(estado, produto):
    dados = buscar_licitacoes(estado)

    resultados = filtrar_licitacoes(
        dados,
        estado,
        produto,
    )

    return dados, resultados
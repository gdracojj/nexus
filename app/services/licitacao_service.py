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
    from app.pncp.client import parametros_consulta
    from app.repositories import licitacao_repository as repositorio

    parametros = parametros_consulta(estado)
    execucao_id = repositorio.iniciar_execucao(parametros)
    recebidos = 0
    paginas_consultadas = 0

    def contabilizar_recebidos(quantidade):
        nonlocal recebidos
        recebidos += quantidade

    def contabilizar_pagina(pagina, _quantidade):
        nonlocal paginas_consultadas
        paginas_consultadas = pagina

    try:
        dados = buscar_licitacoes(
            estado,
            incluir_payload=True,
            parametros_base=parametros,
            ao_receber_registros=contabilizar_recebidos,
            ao_consultar_pagina=contabilizar_pagina,
        )
        repositorio.concluir_execucao(execucao_id, dados, paginas_consultadas)
    except Exception as erro:
        recebidos = getattr(erro, "registros_recebidos", recebidos)
        erros = getattr(erro, "registros_com_erro", 1)
        try:
            repositorio.falhar_execucao(
                execucao_id,
                erro,
                recebidos,
                erros,
                paginas_consultadas,
            )
        except Exception:
            # Preserva a causa original se o banco também estiver indisponível
            # durante a tentativa de registrar a falha.
            pass
        raise

    controles = [registro["numero_controle_pncp"] for registro in dados]
    persistidos = repositorio.listar_licitacoes(estado, controles)
    resultados = repositorio.listar_licitacoes(
        estado,
        controles,
        produto,
    )
    return persistidos, resultados

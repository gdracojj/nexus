from app.core.config import obter_janela_reuso_coleta_segundos
from app.pncp.client import buscar_licitacoes, parametros_consulta


def consultar_licitacoes(
    estado: str | None,
    produto: str = "",
    page: int = 1,
    page_size: int = 25,
    prazo_dias: int | None = None,
) -> tuple[int, int, list[dict], str | None, dict | None]:
    """Retorna apenas dados persistidos; não inicia comunicação com o PNCP."""
    from app.repositories import licitacao_repository as repositorio

    return repositorio.consultar_licitacoes(
        estado,
        produto,
        page=page,
        page_size=page_size,
        prazo_dias=prazo_dias,
    )


def sincronizar_licitacoes(estado: str) -> int:
    """Coleta o PNCP e persiste os resultados fora do caminho HTTP de leitura."""
    from app.repositories import licitacao_repository as repositorio

    parametros = parametros_consulta(estado)
    with repositorio.lock_coleta_pncp():
        checkpoint = repositorio.obter_execucao_incompleta(parametros)
        if checkpoint is not None:
            execucao_id = checkpoint["id"]
            pagina_inicial = checkpoint["pagina_seguinte"]
            repositorio.retomar_execucao(execucao_id)
        else:
            janela_reuso = obter_janela_reuso_coleta_segundos()
            registros_reutilizados = repositorio.registros_da_coleta_recente(
                parametros,
                janela_reuso,
            )
            if registros_reutilizados is not None:
                return registros_reutilizados

            execucao_id = repositorio.iniciar_execucao(parametros)
            pagina_inicial = 1

        def persistir_pagina(pagina, _total_paginas, registros, recebidos):
            repositorio.persistir_pagina_execucao(
                execucao_id,
                pagina,
                registros,
                recebidos,
            )

        try:
            buscar_licitacoes(
                estado,
                incluir_payload=True,
                parametros_base=parametros,
                ao_processar_pagina=persistir_pagina,
                pagina_inicial=pagina_inicial,
            )
            registros_processados = repositorio.concluir_execucao_incremental(
                execucao_id
            )
        except Exception as erro:
            recebidos = getattr(erro, "registros_recebidos", 0)
            erros = getattr(erro, "registros_com_erro", 1)
            try:
                repositorio.falhar_execucao(
                    execucao_id,
                    erro,
                    recebidos,
                    erros,
                )
            except Exception:
                # Preserva a falha original se o banco também estiver
                # indisponível ao tentar registrar o erro.
                pass
            raise

    return registros_processados

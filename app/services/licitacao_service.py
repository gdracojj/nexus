from app.core.config import obter_janela_reuso_coleta_segundos
from app.pncp.client import buscar_licitacoes, parametros_consulta


def consultar_licitacoes(
    estado: str | None,
    produto: str = "",
    page: int = 1,
    page_size: int = 25,
    prazo_dias: int | None = None,
) -> tuple[int, int, list[dict], str | None]:
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
        janela_reuso = obter_janela_reuso_coleta_segundos()
        registros_reutilizados = repositorio.registros_da_coleta_recente(
            parametros,
            janela_reuso,
        )
        if registros_reutilizados is not None:
            return registros_reutilizados

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
            registros_processados = repositorio.concluir_execucao(
                execucao_id,
                dados,
                paginas_consultadas,
            )
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
                # Preserva a falha original se o banco também estiver
                # indisponível ao tentar registrar o erro.
                pass
            raise

    return registros_processados

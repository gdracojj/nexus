import time

from app.services.licitacao_service import sincronizar_licitacoes


UFS_BRASIL = (
    "AC", "AL", "AP", "AM", "BA", "CE", "DF",
    "ES", "GO", "MA", "MT", "MS", "MG", "PA",
    "PB", "PR", "PE", "PI", "RJ", "RN", "RS",
    "RO", "RR", "SC", "SP", "SE", "TO",
)

INTERVALO_ENTRE_UFS = 5.0


def sincronizar_todas_ufs() -> dict:
    """
    Executa a sincronização das 27 UFs em sequência.

    Uma falha individual não interrompe as demais coletas.
    """

    resultados = []

    for indice, uf in enumerate(UFS_BRASIL):
        print(f"\nIniciando coleta da UF {uf}...")

        try:
            quantidade = sincronizar_licitacoes(uf)

            resultados.append({
                "uf": uf,
                "status": "concluida",
                "registros_processados": quantidade,
                "erro": None,
            })

            print(
                f"Coleta de {uf} concluída: "
                f"{quantidade} registros."
            )

        except Exception as erro:
            resultados.append({
                "uf": uf,
                "status": "falhou",
                "registros_processados": 0,
                "erro": type(erro).__name__,
            })

            print(
                f"Falha na coleta de {uf}: "
                f"{type(erro).__name__}."
            )

        # Aguarda antes de iniciar a próxima UF.
        if indice < len(UFS_BRASIL) - 1:
            time.sleep(INTERVALO_ENTRE_UFS)

    concluidas = sum(
        resultado["status"] == "concluida"
        for resultado in resultados
    )

    falhas = sum(
        resultado["status"] == "falhou"
        for resultado in resultados
    )

    total_registros = sum(
        resultado["registros_processados"]
        for resultado in resultados
    )

    return {
        "total_ufs": len(UFS_BRASIL),
        "ufs_concluidas": concluidas,
        "ufs_com_falha": falhas,
        "total_registros_processados": total_registros,
        "resultados": resultados,
    }
import time

INTERVALO_ENTRE_UFS = 5.0

def sincronizar_todas_ufs() -> dict:
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

        except Exception as erro:
            resultados.append({
                "uf": uf,
                "status": "falhou",
                "registros_processados": 0,
                "erro": type(erro).__name__,
            })

        # Não aguarda depois da última UF.
        if indice < len(UFS_BRASIL) - 1:
            time.sleep(INTERVALO_ENTRE_UFS)

    concluidas = sum(
        r["status"] == "concluida" for r in resultados
    )
    falhas = sum(
        r["status"] == "falhou" for r in resultados
    )
    total_registros = sum(
        r["registros_processados"] for r in resultados
    )

    return {
        "total_ufs": len(UFS_BRASIL),
        "ufs_concluidas": concluidas,
        "ufs_com_falha": falhas,
        "total_registros_processados": total_registros,
        "resultados": resultados,
    }
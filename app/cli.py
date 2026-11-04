import argparse
import sys

from app.repositories.licitacao_repository import (
    ColetaPNCPJaEmAndamentoError,
)
from app.services.licitacao_service import sincronizar_licitacoes
from app.services.coleta_nacional_service import sincronizar_todas_ufs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Operações controladas do Nexus"
    )

    comandos = parser.add_subparsers(
        dest="comando",
        required=True,
    )

    # Coleta individual por UF
    coletar = comandos.add_parser(
        "coletar",
        help="Coleta oportunidades do PNCP por UF",
    )
    coletar.add_argument(
        "--uf",
        required=True,
        help="Sigla da UF, por exemplo RJ",
    )

    # Coleta nacional
    comandos.add_parser(
        "coletar-nacional",
        help="Coleta oportunidades do PNCP em todas as UFs",
    )

    argumentos = parser.parse_args(argv)

    if argumentos.comando == "coletar":
        uf = argumentos.uf.strip().upper()

        if len(uf) != 2 or not uf.isascii() or not uf.isalpha():
            parser.error("--uf deve conter duas letras ASCII")

        try:
            quantidade = sincronizar_licitacoes(uf)

        except ColetaPNCPJaEmAndamentoError as erro:
            print(str(erro), file=sys.stderr)
            return 1

        except Exception as erro:
            # Evita expor URLs, respostas externas ou DSNs.
            print(
                f"Falha na coleta ({type(erro).__name__}).",
                file=sys.stderr,
            )
            return 1

        print(
            f"Sincronização concluída para {uf}: "
            f"{quantidade} registros processados."
        )
        return 0

    if argumentos.comando == "coletar-nacional":
        try:
            resultado = sincronizar_todas_ufs()

        except Exception as erro:
            print(
                f"Falha na coleta nacional ({type(erro).__name__}).",
                file=sys.stderr,
            )
            return 1

        print("\n===== RESUMO DA COLETA NACIONAL =====")

        for item in resultado["resultados"]:
            uf = item["uf"]
            status = item["status"]
            quantidade = item["registros_processados"]

            if status == "concluida":
                print(f"{uf}: concluída — {quantidade} registros")
            else:
                print(
                    f"{uf}: falhou — {item['erro']}",
                    file=sys.stderr,
                )

        print("\n===== RESULTADO FINAL =====")
        print(f"UFs processadas: {resultado['total_ufs']}")
        print(f"UFs concluídas: {resultado['ufs_concluidas']}")
        print(f"UFs com falha: {resultado['ufs_com_falha']}")
        print(
            "Total de registros: "
            f"{resultado['total_registros_processados']}"
        )

        return 1 if resultado["ufs_com_falha"] > 0 else 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
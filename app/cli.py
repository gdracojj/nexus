import argparse
import sys

from app.repositories.licitacao_repository import ColetaPNCPJaEmAndamentoError
from app.services.licitacao_service import sincronizar_licitacoes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Operações controladas do Nexus")
    comandos = parser.add_subparsers(dest="comando", required=True)
    coletar = comandos.add_parser("coletar", help="coleta oportunidades do PNCP")
    coletar.add_argument("--uf", required=True, help="sigla da UF, por exemplo RJ")
    argumentos = parser.parse_args(argv)

    uf = argumentos.uf.strip().upper()
    if len(uf) != 2 or not uf.isascii() or not uf.isalpha():
        parser.error("--uf deve conter duas letras ASCII")

    try:
        quantidade = sincronizar_licitacoes(uf)
    except ColetaPNCPJaEmAndamentoError as erro:
        print(str(erro), file=sys.stderr)
        return 1
    except Exception as erro:
        # A exceção pode conter URL, resposta externa ou DSN do banco.
        print(
            f"Falha na coleta ({type(erro).__name__}).",
            file=sys.stderr,
        )
        return 1

    print(f"Coleta concluída para {uf}: {quantidade} registros processados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

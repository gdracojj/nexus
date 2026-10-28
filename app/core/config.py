import os

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # permits importing the app before dependencies are installed
    load_dotenv = lambda: None


load_dotenv()


def obter_database_url() -> str:
    """Retorna a URL do PostgreSQL configurada para a aplicação."""
    url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if not url:
        raise RuntimeError(
            "Configure DATABASE_URL com a URL de conexão do PostgreSQL."
        )
    # URLs de alguns provedores usam o prefixo legado postgres://.
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


def obter_janela_reuso_coleta_segundos() -> int:
    """Janela para reutilizar a última coleta concluída com os mesmos parâmetros."""
    valor = os.getenv("PNCP_SYNC_CACHE_TTL_SECONDS", "900")
    try:
        segundos = int(valor)
    except ValueError as erro:
        raise RuntimeError(
            "PNCP_SYNC_CACHE_TTL_SECONDS deve ser um inteiro entre 0 e 86400."
        ) from erro
    if segundos < 0 or segundos > 86_400:
        raise RuntimeError(
            "PNCP_SYNC_CACHE_TTL_SECONDS deve estar entre 0 e 86400."
        )
    return segundos

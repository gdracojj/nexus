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

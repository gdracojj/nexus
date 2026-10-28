from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import obter_database_url


TAMANHO_POOL = 5
EXCESSO_MAXIMO_POOL = 10
TIMEOUT_POOL_SEGUNDOS = 30


class Base(DeclarativeBase):
    pass


@lru_cache(maxsize=1)
def obter_engine():
    return create_engine(
        obter_database_url(),
        pool_pre_ping=True,
        pool_size=TAMANHO_POOL,
        max_overflow=EXCESSO_MAXIMO_POOL,
        pool_timeout=TIMEOUT_POOL_SEGUNDOS,
    )


@lru_cache(maxsize=1)
def obter_session_factory():
    return sessionmaker(bind=obter_engine(), expire_on_commit=False)


def fechar_engine():
    if obter_engine.cache_info().currsize:
        obter_engine().dispose()

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import obter_database_url


class Base(DeclarativeBase):
    pass


@lru_cache(maxsize=1)
def obter_engine():
    return create_engine(obter_database_url(), pool_pre_ping=True)


@lru_cache(maxsize=1)
def obter_session_factory():
    return sessionmaker(bind=obter_engine(), expire_on_commit=False)


def fechar_engine():
    if obter_engine.cache_info().currsize:
        obter_engine().dispose()

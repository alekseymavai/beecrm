from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

import settings


def get_engine():
    url = settings.DB_URL
    if not url:
        raise RuntimeError("DB_URL не задан — вызовите settings.startup_check() при старте")
    return create_engine(url, pool_pre_ping=True)


class Base(DeclarativeBase):
    pass


# engine и SessionLocal создаются лениво — при первом обращении через get_engine()
# В main.py lifespan инициализирует движок и прокидывает его сюда.
_engine = None
SessionLocal = None


def init_db(url: str | None = None) -> None:
    """Инициализировать движок. Вызывается из lifespan main.py после startup_check()."""
    global _engine, SessionLocal
    db_url = url or settings.DB_URL
    _engine = create_engine(db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def get_session():
    """FastAPI Depends — генератор сессии."""
    if SessionLocal is None:
        raise RuntimeError("БД не инициализирована. Вызовите init_db() при старте.")
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

"""conftest.py — фикстуры для тестов (SQLite in-memory)."""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import JSON, create_engine
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DB_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret")

# SQLite не знает JSONB — патчим компилятор чтобы рендерил как JSON
SQLiteTypeCompiler.visit_JSONB = SQLiteTypeCompiler.visit_JSON  # type: ignore

from db import Base, get_session
from main import app

TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine):
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def client(engine):
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_session():
        session = Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

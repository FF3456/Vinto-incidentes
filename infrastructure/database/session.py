"""Motor y fábrica de sesiones. SQLite por defecto (RNF-06 Portabilidad)."""
from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from infrastructure.database.models import Base


def crear_motor(url: str = "sqlite:///data/vinto.db") -> Engine:
    if url.startswith("sqlite"):
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in url:
            kwargs["poolclass"] = StaticPool          # misma conexión para toda la prueba
        engine = create_engine(url, **kwargs)

        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _):                    # SQLite ignora las FK por defecto
            dbapi_conn.execute("PRAGMA foreign_keys=ON")
        return engine
    return create_engine(url)


def crear_tablas(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def crear_fabrica_sesiones(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)

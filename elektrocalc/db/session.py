from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

def make_engine(db_url: str, echo: bool = False):
    # SQLite: enable FK constraints and allow cross-thread usage in local web server context.
    connect_args = {}
    if db_url.startswith("sqlite:///"):
        connect_args = {"check_same_thread": False}

    engine = create_engine(db_url, echo=echo, future=True, connect_args=connect_args)

    if db_url.startswith("sqlite:///"):
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()

    return engine

def make_session_factory(db_url: str, echo: bool = False):
    engine = make_engine(db_url, echo=echo)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

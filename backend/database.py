import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def _database_url() -> str:
    value = os.getenv("DATABASE_URL", "sqlite:///./zenpsa_local.db")
    if value.startswith("postgres://"):
        value = value.replace("postgres://", "postgresql+psycopg://", 1)
    elif value.startswith("postgresql://"):
        value = value.replace("postgresql://", "postgresql+psycopg://", 1)
    return value


DATABASE_URL = _database_url()
CONNECT_ARGS = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args=CONNECT_ARGS,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_database_tables() -> None:
    from record_models import TestRecord

    print(
        "ZENPSA DB engine:",
        engine.url.render_as_string(
            hide_password=True
        ),
        flush=True,
    )

    print(
        "ZENPSA DB registered tables:",
        list(Base.metadata.tables.keys()),
        flush=True,
    )

    Base.metadata.create_all(
        bind=engine
    )

    print(
        "ZENPSA DB initialization completed",
        flush=True,
    )


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session

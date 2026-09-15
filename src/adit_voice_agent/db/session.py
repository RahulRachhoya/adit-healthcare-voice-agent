"""Database connection creation. Schema changes are performed with Alembic."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def create_session_factory(url: str):
    options = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url:
            options["poolclass"] = StaticPool
    elif url.startswith("postgresql"):
        # A stopped database must not leave setup or call admission waiting indefinitely.
        options["connect_args"] = {"connect_timeout": 5}
        options["pool_timeout"] = 5
    engine = create_engine(url, **options)
    return sessionmaker(engine, expire_on_commit=False)

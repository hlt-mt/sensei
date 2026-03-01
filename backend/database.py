from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings

settings = get_settings()

engine_kwargs = {}
if settings.db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    # Ensure in-memory SQLite is shared across all sessions/connections.
    if ":memory:" in settings.db_url:
        connect_args["uri"] = True
        engine_kwargs["poolclass"] = StaticPool
    engine_kwargs["connect_args"] = connect_args

engine = create_engine(settings.db_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass

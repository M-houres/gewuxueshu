from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()


def _create_engine():
    mysql_engine = create_engine(
        settings.mysql_dsn,
        pool_pre_ping=True,
        pool_recycle=3600,
        future=True,
    )
    try:
        with mysql_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return mysql_engine
    except Exception:
        if not settings.db_fallback_sqlite:
            raise
        return create_engine(
            settings.sqlite_dsn,
            connect_args={"check_same_thread": False},
            future=True,
        )


engine = _create_engine()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


class Base(DeclarativeBase):
    pass


@contextmanager
def db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

"""SQLAlchemy Database Engine and Session Factory for MySQL."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Create SQLAlchemy Engine
engine = create_engine(
    settings.mysql_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

# Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative Base
Base = declarative_base()


def get_db():
    """Dependency provider for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

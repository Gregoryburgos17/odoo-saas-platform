#!/usr/bin/env python3
"""
Shared database connection utilities for Odoo SaaS Platform
"""

import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool

# Database configuration from environment variables
DATABASE_URL = os.environ.get('DATABASE_URL')

# Fallback to individual environment variables if DATABASE_URL is not set
if not DATABASE_URL:
    host = os.environ.get('PG_HOST', os.environ.get('DB_HOST', 'localhost'))
    port = os.environ.get('PG_PORT', os.environ.get('DB_PORT', '5432'))
    user = os.environ.get('PG_USER', os.environ.get('DB_USER', os.environ.get('POSTGRES_USER', 'odoo')))
    password = os.environ.get('PG_PASSWORD', os.environ.get('DB_PASSWORD', os.environ.get('POSTGRES_PASSWORD', 'password')))
    database = os.environ.get('PG_DATABASE', os.environ.get('POSTGRES_DB', 'odoo_saas_platform'))

    DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{database}"

# Create database engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Enable connection health checks
    pool_recycle=3600,   # Recycle connections after 1 hour
    echo=os.environ.get('SQL_ECHO', 'false').lower() == 'true'
)

# Create session factory
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))


@contextmanager
def get_db_session():
    """
    Provide a transactional scope for database operations.

    Usage:
        with get_db_session() as session:
            # Use session here
            user = session.query(User).first()
            session.commit()

    The session will be automatically committed if no exception occurs,
    and rolled back if an exception is raised.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """
    Initialize database tables.
    This should be called when the application starts.
    """
    from shared.models import Base
    Base.metadata.create_all(bind=engine)


def get_engine():
    """
    Get the database engine instance.

    Returns:
        sqlalchemy.engine.Engine: Database engine
    """
    return engine


def get_session_factory():
    """
    Get the session factory.

    Returns:
        sqlalchemy.orm.scoped_session: Session factory
    """
    return SessionLocal

"""
Database connection management for Odoo SaaS Platform
"""
import os
import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.pool import QueuePool

from .models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database connection manager"""

    _engine = None
    _session_factory = None
    _scoped_session = None

    @classmethod
    def get_database_url(cls) -> str:
        """Build database URL from environment variables"""
        host = os.getenv('PG_HOST', 'postgres')
        port = os.getenv('PG_PORT', '5432')
        user = os.getenv('PG_USER', 'odoo')
        password = os.getenv('PG_PASSWORD', 'odoo_password')
        database = os.getenv('PG_DATABASE', 'odoo_saas')

        return f"postgresql://{user}:{password}@{host}:{port}/{database}"

    @classmethod
    def get_engine(cls):
        """Get or create database engine"""
        if cls._engine is None:
            database_url = cls.get_database_url()

            cls._engine = create_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=int(os.getenv('PG_POOL_SIZE', '10')),
                max_overflow=int(os.getenv('PG_MAX_OVERFLOW', '20')),
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=os.getenv('SQL_DEBUG', 'false').lower() == 'true',
            )

            # Log connection events
            @event.listens_for(cls._engine, "connect")
            def on_connect(dbapi_conn, connection_record):
                logger.debug("Database connection established")

            @event.listens_for(cls._engine, "checkout")
            def on_checkout(dbapi_conn, connection_record, connection_proxy):
                logger.debug("Database connection checked out from pool")

        return cls._engine

    @classmethod
    def get_session_factory(cls):
        """Get or create session factory"""
        if cls._session_factory is None:
            cls._session_factory = sessionmaker(
                bind=cls.get_engine(),
                autocommit=False,
                autoflush=False,
            )
        return cls._session_factory

    @classmethod
    def get_scoped_session(cls):
        """Get or create scoped session"""
        if cls._scoped_session is None:
            cls._scoped_session = scoped_session(cls.get_session_factory())
        return cls._scoped_session

    @classmethod
    def init_db(cls):
        """Initialize database tables"""
        engine = cls.get_engine()
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")

    @classmethod
    def drop_db(cls):
        """Drop all database tables (use with caution!)"""
        engine = cls.get_engine()
        Base.metadata.drop_all(bind=engine)
        logger.warning("All database tables dropped")

    @classmethod
    def health_check(cls) -> bool:
        """Check database connectivity"""
        try:
            engine = cls.get_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    @classmethod
    def close(cls):
        """Close all connections and reset state"""
        if cls._scoped_session:
            cls._scoped_session.remove()
            cls._scoped_session = None

        if cls._engine:
            cls._engine.dispose()
            cls._engine = None

        cls._session_factory = None
        logger.info("Database connections closed")


# Convenience functions
def get_engine():
    """Get database engine"""
    return DatabaseManager.get_engine()


def get_session() -> Session:
    """Get a new database session"""
    return DatabaseManager.get_session_factory()()


def get_scoped_session():
    """Get scoped session"""
    return DatabaseManager.get_scoped_session()


def init_db():
    """Initialize database"""
    DatabaseManager.init_db()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    Automatically commits on success, rolls back on error.

    Usage:
        with session_scope() as session:
            session.add(some_object)
            # Auto-commits when exiting the block
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()


def create_tenant_database(db_name: str) -> bool:
    """
    Create a new database for a tenant.
    Uses a separate connection to avoid transaction issues.
    """
    from sqlalchemy import create_engine, text

    try:
        # Connect to postgres database to create new database
        admin_url = DatabaseManager.get_database_url().rsplit('/', 1)[0] + '/postgres'
        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

        with admin_engine.connect() as conn:
            # Check if database exists
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": db_name}
            )
            if result.fetchone():
                logger.warning(f"Database {db_name} already exists")
                return True

            # Create database
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
            logger.info(f"Created tenant database: {db_name}")

        admin_engine.dispose()
        return True

    except Exception as e:
        logger.error(f"Failed to create tenant database {db_name}: {e}")
        return False


def drop_tenant_database(db_name: str) -> bool:
    """
    Drop a tenant database.
    Uses a separate connection to avoid transaction issues.
    """
    from sqlalchemy import create_engine, text

    try:
        # Connect to postgres database
        admin_url = DatabaseManager.get_database_url().rsplit('/', 1)[0] + '/postgres'
        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

        with admin_engine.connect() as conn:
            # Terminate existing connections
            conn.execute(text(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{db_name}'
                AND pid <> pg_backend_pid()
            """))

            # Drop database
            conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
            logger.info(f"Dropped tenant database: {db_name}")

        admin_engine.dispose()
        return True

    except Exception as e:
        logger.error(f"Failed to drop tenant database {db_name}: {e}")
        return False

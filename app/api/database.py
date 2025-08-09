"""Database configuration for the optimisation platform.

This module sets up the SQLAlchemy engine, session and base class for
the application's models.  The database URL is read from the
``SQLALCHEMY_DATABASE_URI`` environment variable with a sensible
default of an in‑memory SQLite database for development and testing.
Production deployments should provide a PostgreSQL URL via
Terraform/Kubernetes secrets or environment variables.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Read the database URL from the environment, falling back to an in‑memory
# SQLite database for local development.  The recommended production
# configuration is a managed PostgreSQL instance (e.g. RDS or Cloud SQL).
DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite+pysqlite:///:memory:")

# Create the SQLAlchemy engine.  ``future=True`` enables SQLAlchemy 2.0
# behaviours.  ``pool_pre_ping`` ensures connections are tested for
# liveness before use.
engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

# Configure a session factory bound to the engine.  Sessions are not
# autocommitted by default so callers must explicitly commit or rollback.
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

# Base class for declarative models
Base = declarative_base()


def get_db():
    """Yield a SQLAlchemy session scoped to the current context.

    This function is designed to be used as a dependency in FastAPI
    endpoints.  It creates a session, yields it to the caller and
    automatically closes the session when the request is completed.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

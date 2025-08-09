"""SQLAlchemy ORM models for the optimisation platform.

This module defines the core data model for the application.  Each
class corresponds to a table in the database and captures the
relationships between organisations, users, projects, models, runs
and related entities.  The schema follows the specification laid out
in the requirements and is designed to support versioning, auditing
and multi‑tenant access control.
"""

from __future__ import annotations

import datetime as _dt
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from .database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    plan = Column(String(100), nullable=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=_dt.datetime.utcnow)
    updated_at = Column(DateTime, default=_dt.datetime.utcnow, onupdate=_dt.datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="organization", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=True)
    auth_provider = Column(String(50), nullable=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    role = Column(String(50), default="viewer")  # admin/editor/viewer
    created_at = Column(DateTime, default=_dt.datetime.utcnow)
    updated_at = Column(DateTime, default=_dt.datetime.utcnow, onupdate=_dt.datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="users")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_dt.datetime.utcnow)
    updated_at = Column(DateTime, default=_dt.datetime.utcnow, onupdate=_dt.datetime.utcnow)

    organization = relationship("Organization", back_populates="projects")
    models = relationship("Model", back_populates="project", cascade="all, delete-orphan")
    datasets = relationship("Dataset", back_populates="project", cascade="all, delete-orphan")
    webhooks = relationship("Webhook", back_populates="project", cascade="all, delete-orphan")


class Model(Base):
    __tablename__ = "models"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # LP, MIP, QP, NLP, BO, CUSTOM
    status = Column(String(50), default="draft")  # draft, validated, approved
    source = Column(String(50), default="json")  # json, pyomo, cvx
    version = Column(String(50), nullable=True)
    checksum = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=_dt.datetime.utcnow)
    updated_at = Column(DateTime, default=_dt.datetime.utcnow, onupdate=_dt.datetime.utcnow)

    project = relationship("Project", back_populates="models")
    versions = relationship("ModelVersion", back_populates="model", cascade="all, delete-orphan")
    runs = relationship("Run", back_populates="model", cascade="all, delete-orphan")
    audits = relationship("ConstraintsAudit", back_populates="model", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="model", cascade="all, delete-orphan")


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True)
    model_id = Column(Integer, ForeignKey("models.id"), nullable=False)
    version = Column(String(50), nullable=False)
    definition_json = Column(JSON, nullable=True)
    pyomo_script = Column(Text, nullable=True)
    validation_report_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=_dt.datetime.utcnow)
    updated_at = Column(DateTime, default=_dt.datetime.utcnow, onupdate=_dt.datetime.utcnow)

    model = relationship("Model", back_populates="versions")
    runs = relationship("Run", back_populates="model_version", cascade="all, delete-orphan")
    audits = relationship("ConstraintsAudit", back_populates="model_version", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="model_version", cascade="all, delete-orphan")


class Run(Base):
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True)
    model_version_id = Column(Integer, ForeignKey("model_versions.id"), nullable=False)
    solver = Column(String(50), nullable=False)
    parameters_json = Column(JSON, nullable=True)
    status = Column(String(50), default="pending")  # pending, running, succeeded, failed, canceled
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    objective_value = Column(Float, nullable=True)
    gap = Column(Float, nullable=True)
    best_bound = Column(Float, nullable=True)
    seed = Column(Integer, nullable=True)
    time_limit_sec = Column(Integer, nullable=True)
    artifact_uri = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=_dt.datetime.utcnow)
    updated_at = Column(DateTime, default=_dt.datetime.utcnow, onupdate=_dt.datetime.utcnow)

    model_version = relationship("ModelVersion", back_populates="runs")
    model = relationship("Model", back_populates="runs")


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    schema_json = Column(JSON, nullable=True)
    sample_uri = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=_dt.datetime.utcnow)
    updated_at = Column(DateTime, default=_dt.datetime.utcnow, onupdate=_dt.datetime.utcnow)

    project = relationship("Project", back_populates="datasets")


class ConstraintsAudit(Base):
    __tablename__ = "constraints_audit"

    id = Column(Integer, primary_key=True)
    model_version_id = Column(Integer, ForeignKey("model_versions.id"), nullable=False)
    findings_json = Column(JSON, nullable=True)
    severity = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=_dt.datetime.utcnow)
    updated_at = Column(DateTime, default=_dt.datetime.utcnow, onupdate=_dt.datetime.utcnow)

    model_version = relationship("ModelVersion", back_populates="audits")
    model = relationship("Model", back_populates="audits")


class Secret(Base):
    __tablename__ = "secrets"

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    key_name = Column(String(255), nullable=False)
    ciphertext = Column(Text, nullable=False)
    scope = Column(String(50), nullable=False)  # solver|provider|webhook
    created_at = Column(DateTime, default=_dt.datetime.utcnow)
    updated_at = Column(DateTime, default=_dt.datetime.utcnow, onupdate=_dt.datetime.utcnow)


class Webhook(Base):
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    url = Column(String(1024), nullable=False)
    events = Column(String(255), nullable=False)  # comma-separated events
    secret = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=_dt.datetime.utcnow)
    updated_at = Column(DateTime, default=_dt.datetime.utcnow, onupdate=_dt.datetime.utcnow)

    project = relationship("Project", back_populates="webhooks")


class ApiToken(Base):
    __tablename__ = "api_tokens"

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    hash = Column(String(512), nullable=False)
    scopes = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=_dt.datetime.utcnow)
    updated_at = Column(DateTime, default=_dt.datetime.utcnow, onupdate=_dt.datetime.utcnow)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True)
    model_version_id = Column(Integer, ForeignKey("model_versions.id"), nullable=False)
    kind = Column(String(50), nullable=False)  # solver|hyperparam|reformulation
    content_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=_dt.datetime.utcnow)
    updated_at = Column(DateTime, default=_dt.datetime.utcnow, onupdate=_dt.datetime.utcnow)

    model_version = relationship("ModelVersion", back_populates="recommendations")
    model = relationship("Model", back_populates="recommendations")

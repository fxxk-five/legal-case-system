from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.security import create_access_token, get_password_hash
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.case import Case
from app.models.file import File
from app.models.tenant import Tenant
from app.models.user import User


@pytest.fixture(autouse=True)
def reset_runtime_settings():
    original = {
        "AI_MOCK_MODE": settings.AI_MOCK_MODE,
        "QUEUE_DRIVER": settings.QUEUE_DRIVER,
        "AI_DB_QUEUE_EAGER": settings.AI_DB_QUEUE_EAGER,
        "AI_DB_QUEUE_EAGER_BLOCKING": settings.AI_DB_QUEUE_EAGER_BLOCKING,
        "AI_DB_QUEUE_MAX_RETRIES": settings.AI_DB_QUEUE_MAX_RETRIES,
        "AI_DB_QUEUE_RETRY_BACKOFF_SECONDS": settings.AI_DB_QUEUE_RETRY_BACKOFF_SECONDS,
        "AI_DB_QUEUE_STALE_TASK_SECONDS": settings.AI_DB_QUEUE_STALE_TASK_SECONDS,
        "AI_DB_QUEUE_HEALTHCHECK_MAX_AGE_SECONDS": settings.AI_DB_QUEUE_HEALTHCHECK_MAX_AGE_SECONDS,
        "AI_DB_QUEUE_HEARTBEAT_FILE": settings.AI_DB_QUEUE_HEARTBEAT_FILE,
        "AI_DB_QUEUE_WORKER_ID": settings.AI_DB_QUEUE_WORKER_ID,
        "TENCENT_QUEUE_REGION": settings.TENCENT_QUEUE_REGION,
        "TENCENT_QUEUE_NAMESPACE": settings.TENCENT_QUEUE_NAMESPACE,
        "TENCENT_QUEUE_TOPIC_NAME": settings.TENCENT_QUEUE_TOPIC_NAME,
        "TENCENT_QUEUE_SUBSCRIPTION_NAME": settings.TENCENT_QUEUE_SUBSCRIPTION_NAME,
        "TENCENT_QUEUE_ENDPOINT": settings.TENCENT_QUEUE_ENDPOINT,
        "TENCENT_QUEUE_SECRET_ID": settings.TENCENT_QUEUE_SECRET_ID,
        "TENCENT_QUEUE_SECRET_KEY": settings.TENCENT_QUEUE_SECRET_KEY,
    }

    settings.AI_MOCK_MODE = True
    settings.QUEUE_DRIVER = "db"
    settings.AI_DB_QUEUE_EAGER = True
    settings.AI_DB_QUEUE_EAGER_BLOCKING = True
    settings.AI_DB_QUEUE_MAX_RETRIES = 3
    settings.AI_DB_QUEUE_RETRY_BACKOFF_SECONDS = 30
    settings.AI_DB_QUEUE_STALE_TASK_SECONDS = 900
    settings.AI_DB_QUEUE_HEALTHCHECK_MAX_AGE_SECONDS = 90
    settings.AI_DB_QUEUE_HEARTBEAT_FILE = "/tmp/legal-ai-worker-heartbeat.json"
    settings.AI_DB_QUEUE_WORKER_ID = ""
    settings.TENCENT_QUEUE_REGION = ""
    settings.TENCENT_QUEUE_NAMESPACE = ""
    settings.TENCENT_QUEUE_TOPIC_NAME = ""
    settings.TENCENT_QUEUE_SUBSCRIPTION_NAME = ""
    settings.TENCENT_QUEUE_ENDPOINT = ""
    settings.TENCENT_QUEUE_SECRET_ID = ""
    settings.TENCENT_QUEUE_SECRET_KEY = ""

    try:
        yield
    finally:
        for key, value in original.items():
            setattr(settings, key, value)


@pytest.fixture(scope="session")
def engine():
    return create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture(scope="session")
def session_factory(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session(engine, session_factory):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = session_factory()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def client(session_factory, db_session):
    _ = db_session

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.state.session_factory = session_factory

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    if hasattr(app.state, "session_factory"):
        delattr(app.state, "session_factory")


@pytest.fixture(scope="function")
def seeded_data(db_session):
    tenant = Tenant(
        tenant_code="tenant_demo",
        name="Tenant Demo",
        type="organization",
        status=1,
    )
    db_session.add(tenant)
    db_session.flush()

    lawyer = User(
        tenant_id=tenant.id,
        role="lawyer",
        is_tenant_admin=False,
        phone="13800000001",
        password_hash=get_password_hash("pwd123456"),
        real_name="Lawyer",
        status=1,
    )
    client_user = User(
        tenant_id=tenant.id,
        role="client",
        is_tenant_admin=False,
        phone="13800000002",
        password_hash=get_password_hash("pwd123456"),
        real_name="Client",
        status=1,
    )
    outsider_client = User(
        tenant_id=tenant.id,
        role="client",
        is_tenant_admin=False,
        phone="13800000003",
        password_hash=get_password_hash("pwd123456"),
        real_name="Outsider",
        status=1,
    )
    db_session.add_all([lawyer, client_user, outsider_client])
    db_session.flush()

    case = Case(
        tenant_id=tenant.id,
        case_number="CASE-001",
        title="Contract Dispute",
        client_id=client_user.id,
        assigned_lawyer_id=lawyer.id,
        status="new",
    )
    db_session.add(case)
    db_session.flush()

    file_record = File(
        tenant_id=tenant.id,
        case_id=case.id,
        uploader_id=lawyer.id,
        file_name="claim.pdf",
        file_url="storage/tenant_demo/claim.pdf",
        file_type="application/pdf",
    )
    db_session.add(file_record)
    db_session.commit()

    def make_token(user: User) -> str:
        return create_access_token(
            user.id,
            extra_data={
                "tenant_id": user.tenant_id,
                "role": user.role,
                "is_tenant_admin": user.is_tenant_admin,
            },
        )

    return {
        "tenant": tenant,
        "case": case,
        "file": file_record,
        "lawyer_token": make_token(lawyer),
        "client_token": make_token(client_user),
        "outsider_token": make_token(outsider_client),
    }

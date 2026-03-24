from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.security import create_access_token, get_password_hash
from app.models.case import Case
from app.models.file import File
from app.models.tenant import Tenant
from app.models.user import User


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_list_clients_returns_aggregated_client_rows(client, db_session, seeded_data):
    tenant = seeded_data["tenant"]
    lawyer = db_session.query(User).filter(User.phone == "13800000001").first()
    client_user = db_session.query(User).filter(User.phone == "13800000002").first()
    assert lawyer is not None
    assert client_user is not None

    second_case = Case(
        tenant_id=tenant.id,
        case_number="CASE-002",
        title="Second Case",
        legal_type="contract_dispute",
        client_id=client_user.id,
        assigned_lawyer_id=lawyer.id,
        status="processing",
        deadline=datetime.now(timezone.utc) + timedelta(days=5),
    )
    db_session.add(second_case)
    db_session.flush()

    latest_file = File(
        tenant_id=tenant.id,
        case_id=second_case.id,
        uploader_id=lawyer.id,
        uploader_role="lawyer",
        file_name="latest.pdf",
        file_url="storage/tenant_demo/latest.pdf",
        file_type="application/pdf",
    )
    db_session.add(latest_file)
    db_session.commit()

    response = client.get("/api/v1/clients", headers=_auth_header(seeded_data["lawyer_token"]))
    assert response.status_code == 200
    payload = response.json()

    assert len(payload) == 1
    assert payload[0]["id"] == client_user.id
    assert payload[0]["case_count"] == 2
    assert payload[0]["last_uploaded_at"] is not None


def test_get_client_detail_includes_cases_and_update_support(client, db_session, seeded_data):
    client_user = db_session.query(User).filter(User.phone == "13800000002").first()
    assert client_user is not None

    detail_resp = client.get(f"/api/v1/clients/{client_user.id}", headers=_auth_header(seeded_data["lawyer_token"]))
    assert detail_resp.status_code == 200
    detail_payload = detail_resp.json()
    assert detail_payload["id"] == client_user.id
    assert detail_payload["cases"]
    assert detail_payload["cases"][0]["case_number"] == "CASE-001"

    update_resp = client.patch(
        f"/api/v1/clients/{client_user.id}",
        headers=_auth_header(seeded_data["lawyer_token"]),
        json={"real_name": "Updated Client", "phone": "13800000022"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["real_name"] == "Updated Client"
    assert update_resp.json()["phone"] == "13800000022"


def test_personal_lawyer_only_sees_clients_of_visible_cases(client, db_session, seeded_data):
    tenant = seeded_data["tenant"]
    tenant.type = "personal"
    db_session.add(tenant)

    another_client = User(
        tenant_id=tenant.id,
        role="client",
        is_tenant_admin=False,
        phone="13800000991",
        password_hash=get_password_hash("pwd123456"),
        real_name="Another Client",
        status=1,
    )
    another_lawyer = User(
        tenant_id=tenant.id,
        role="lawyer",
        is_tenant_admin=False,
        phone="13800000992",
        password_hash=get_password_hash("pwd123456"),
        real_name="Another Lawyer",
        status=1,
    )
    db_session.add_all([another_client, another_lawyer])
    db_session.flush()

    another_case = Case(
        tenant_id=tenant.id,
        case_number="CASE-OTHER",
        title="Other Personal Case",
        legal_type="other",
        client_id=another_client.id,
        assigned_lawyer_id=another_lawyer.id,
        status="new",
    )
    db_session.add(another_case)
    db_session.flush()

    another_file = File(
        tenant_id=tenant.id,
        case_id=another_case.id,
        uploader_id=another_lawyer.id,
        uploader_role="lawyer",
        file_name="other.pdf",
        file_url="storage/tenant_demo/other.pdf",
        file_type="application/pdf",
    )
    db_session.add(another_file)
    db_session.commit()

    response = client.get("/api/v1/clients", headers=_auth_header(seeded_data["lawyer_token"]))
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["phone"] == "13800000002"


def test_client_role_cannot_access_clients_management(client, seeded_data):
    response = client.get("/api/v1/clients", headers=_auth_header(seeded_data["client_token"]))
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_client_detail_is_scoped_to_tenant_visibility(client, db_session, seeded_data):
    tenant = seeded_data["tenant"]
    another_tenant = Tenant(
        tenant_code="tenant-clients-cross",
        name="Cross Tenant",
        type="organization",
        status=1,
    )
    db_session.add(another_tenant)
    db_session.flush()

    outsider_client = User(
        tenant_id=another_tenant.id,
        role="client",
        is_tenant_admin=False,
        phone="13800000666",
        password_hash=get_password_hash("pwd123456"),
        real_name="Outsider Client",
        status=1,
    )
    db_session.add(outsider_client)
    db_session.commit()

    response = client.get(
        f"/api/v1/clients/{outsider_client.id}",
        headers=_auth_header(seeded_data["lawyer_token"]),
    )
    assert response.status_code == 404
    assert response.json()["code"] == "USER_NOT_FOUND"

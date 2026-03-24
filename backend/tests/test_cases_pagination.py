from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.case import Case


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_extra_cases(db_session, seeded_data, count: int) -> None:
    tenant_id = seeded_data["tenant"].id
    client_id = seeded_data["case"].client_id
    lawyer_id = seeded_data["case"].assigned_lawyer_id
    for idx in range(count):
        db_session.add(
            Case(
                tenant_id=tenant_id,
                case_number=f"CASE-PG-{idx:03d}",
                title=f"Pagination Case {idx}",
                client_id=client_id,
                assigned_lawyer_id=lawyer_id,
                status="new",
            )
        )
    db_session.commit()


def test_cases_list_supports_page_page_size(client, db_session, seeded_data):
    _seed_extra_cases(db_session, seeded_data, count=25)
    headers = _auth_header(seeded_data["lawyer_token"])

    response = client.get("/api/v1/cases?page=2&page_size=10", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 10
    assert response.headers["X-Page"] == "2"
    assert response.headers["X-Page-Size"] == "10"


def test_cases_list_supports_skip_limit(client, db_session, seeded_data):
    _seed_extra_cases(db_session, seeded_data, count=25)
    headers = _auth_header(seeded_data["lawyer_token"])

    response = client.get("/api/v1/cases?skip=10&limit=5", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 5
    assert response.headers["X-Page"] == "3"
    assert response.headers["X-Page-Size"] == "5"


def test_cases_list_accepts_equivalent_mixed_params(client, db_session, seeded_data):
    _seed_extra_cases(db_session, seeded_data, count=25)
    headers = _auth_header(seeded_data["lawyer_token"])

    response = client.get("/api/v1/cases?page=2&page_size=10&skip=10&limit=10", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 10


def test_cases_list_rejects_conflicting_mixed_params(client, seeded_data):
    headers = _auth_header(seeded_data["lawyer_token"])

    response = client.get("/api/v1/cases?page=1&page_size=20&skip=10&limit=20", headers=headers)

    assert response.status_code == 400
    payload = response.json()
    assert payload["code"] == "VALIDATION_ERROR"


def test_cases_list_default_page_size_unchanged(client, db_session, seeded_data):
    _seed_extra_cases(db_session, seeded_data, count=30)
    headers = _auth_header(seeded_data["lawyer_token"])

    response = client.get("/api/v1/cases", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 20
    assert response.headers["X-Page"] == "1"
    assert response.headers["X-Page-Size"] == "20"


def test_cases_list_supports_search_sort_and_headers(client, db_session, seeded_data):
    tenant_id = seeded_data["tenant"].id
    client_id = seeded_data["case"].client_id
    lawyer_id = seeded_data["case"].assigned_lawyer_id

    case_urgent = Case(
        tenant_id=tenant_id,
        case_number="CASE-SEARCH-URGENT",
        title="Keyword Urgent",
        client_id=client_id,
        assigned_lawyer_id=lawyer_id,
        status="processing",
        deadline=datetime.now(timezone.utc) + timedelta(days=1),
    )
    case_normal = Case(
        tenant_id=tenant_id,
        case_number="CASE-SEARCH-NORMAL",
        title="Keyword Normal",
        client_id=client_id,
        assigned_lawyer_id=lawyer_id,
        status="processing",
        deadline=datetime.now(timezone.utc) + timedelta(days=7),
    )
    case_other = Case(
        tenant_id=tenant_id,
        case_number="CASE-OTHER",
        title="Other",
        client_id=client_id,
        assigned_lawyer_id=lawyer_id,
        status="done",
    )
    db_session.add_all([case_urgent, case_normal, case_other])
    db_session.commit()

    headers = _auth_header(seeded_data["lawyer_token"])
    response = client.get(
        "/api/v1/cases?q=Keyword&status=processing&sort_by=deadline&sort_order=asc&page=1&page_size=10",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 2
    assert all(item["status"] == "processing" for item in payload)
    assert all("Keyword" in item["title"] or "KEYWORD" in item["title"].upper() for item in payload)
    assert payload[0]["deadline"] <= payload[1]["deadline"]
    assert response.headers["X-Total-Count"] == str(len(payload))
    assert response.headers["X-Total-Pages"] == "1"

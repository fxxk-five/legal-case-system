from __future__ import annotations

from decimal import Decimal

from app.models.ai_analysis import AIAnalysisResult
from app.models.ai_task import AITask
from app.models.tenant import Tenant


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_ai_usage_returns_windows_and_breakdowns(client, db_session, seeded_data):
    case = seeded_data["case"]
    tenant = seeded_data["tenant"]

    tasks = [
        AITask(
            task_id="task-parse-1",
            tenant_id=tenant.id,
            case_id=case.id,
            task_type="parse",
            status="completed",
            progress=100,
            input_params={},
            created_by=case.assigned_lawyer_id,
        ),
        AITask(
            task_id="task-analyze-1",
            tenant_id=tenant.id,
            case_id=case.id,
            task_type="analyze",
            status="failed",
            progress=55,
            input_params={},
            created_by=case.assigned_lawyer_id,
        ),
    ]
    results = [
        AIAnalysisResult(
            tenant_id=tenant.id,
            case_id=case.id,
            analysis_type="legal_analysis",
            result_data={"summary": "ok"},
            ai_model="gpt-4o-mini",
            token_usage=1200,
            cost=Decimal("0.1200"),
            created_by=case.assigned_lawyer_id,
        ),
        AIAnalysisResult(
            tenant_id=tenant.id,
            case_id=case.id,
            analysis_type="falsify",
            result_data={"summary": "ok"},
            ai_model="gpt-4o-mini",
            token_usage=800,
            cost=Decimal("0.0800"),
            created_by=case.assigned_lawyer_id,
        ),
    ]
    db_session.add_all(tasks + results)
    db_session.commit()

    response = client.get("/api/v1/analytics/ai-usage", headers=_auth_header(seeded_data["lawyer_token"]))
    assert response.status_code == 200
    payload = response.json()

    assert payload["day"]["task_count"] == 2
    assert payload["month"]["token_usage"] == 2000
    assert payload["month"]["cost_total"] == 0.2
    assert {item["key"] for item in payload["task_type_breakdown"]} == {"parse", "analyze"}
    assert {item["key"] for item in payload["status_breakdown"]} == {"completed", "failed"}
    assert payload["model_breakdown"][0]["model"] == "gpt-4o-mini"


def test_prompt_and_provider_settings_roundtrip(client, db_session, seeded_data):
    tenant = db_session.query(Tenant).filter(Tenant.id == seeded_data["tenant"].id).first()
    assert tenant is not None

    prompts_resp = client.put(
        "/api/v1/analytics/prompts",
        headers=_auth_header(seeded_data["lawyer_token"]),
        json={
            "parse_prompt": "parse prompt",
            "analyze_prompt": "analyze prompt",
            "falsify_prompt": "falsify prompt",
        },
    )
    assert prompts_resp.status_code == 200
    assert prompts_resp.json()["parse_prompt"] == "parse prompt"

    provider_resp = client.put(
        "/api/v1/analytics/provider-settings",
        headers=_auth_header(seeded_data["lawyer_token"]),
        json={
            "provider_type": "openai_compatible",
            "base_url": "https://example.com/v1",
            "model": "gpt-4o-mini",
            "api_key": "sk-test-12345678",
        },
    )
    assert provider_resp.status_code == 200
    provider_payload = provider_resp.json()
    assert provider_payload["provider_type"] == "openai_compatible"
    assert provider_payload["base_url"] == "https://example.com/v1"
    assert provider_payload["model"] == "gpt-4o-mini"
    assert provider_payload["editable"] is True
    assert provider_payload["api_key_masked"]

    get_provider_resp = client.get(
        "/api/v1/analytics/provider-settings",
        headers=_auth_header(seeded_data["lawyer_token"]),
    )
    assert get_provider_resp.status_code == 200
    assert get_provider_resp.json()["locked"] is False

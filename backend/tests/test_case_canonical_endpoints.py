from __future__ import annotations

from pathlib import Path


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _mini_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Client-Platform": "mini-program",
        "X-Client-Source": "wx-mini",
    }


def test_canonical_case_files_list_matches_legacy(client, seeded_data):
    case_id = seeded_data["case"].id
    headers = _auth_header(seeded_data["lawyer_token"])

    legacy_resp = client.get(f"/api/v1/files/case/{case_id}", headers=headers)
    canonical_resp = client.get(f"/api/v1/cases/{case_id}/files", headers=headers)

    assert legacy_resp.status_code == 200
    assert canonical_resp.status_code == 200
    assert canonical_resp.json() == legacy_resp.json()


def test_canonical_upload_policy_matches_legacy(client, seeded_data):
    case_id = seeded_data["case"].id
    headers = _mini_headers(seeded_data["lawyer_token"])

    legacy_resp = client.get(
        f"/api/v1/files/upload-policy?case_id={case_id}&file_name=evidence.pdf",
        headers=headers,
    )
    canonical_resp = client.get(
        f"/api/v1/cases/{case_id}/files/upload-policy?file_name=evidence.pdf",
        headers=headers,
    )

    assert legacy_resp.status_code == 200
    assert canonical_resp.status_code == 200
    legacy_data = legacy_resp.json()
    canonical_data = canonical_resp.json()
    assert legacy_data["mode"] == canonical_data["mode"]
    assert legacy_data["upload_url"] == canonical_data["upload_url"]
    assert legacy_data["method"] == canonical_data["method"]
    assert legacy_data["headers"] == canonical_data["headers"]
    assert legacy_data["form_fields"] == canonical_data["form_fields"]
    assert legacy_data["file_field_name"] == canonical_data["file_field_name"]
    assert legacy_data["backend"] == canonical_data["backend"]
    assert canonical_data["storage_key"].endswith(".pdf")


def test_canonical_upload_endpoint_works(client, seeded_data, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LOCAL_STORAGE_DIR", str(tmp_path))
    case_id = seeded_data["case"].id

    response = client.post(
        f"/api/v1/cases/{case_id}/files",
        headers=_mini_headers(seeded_data["lawyer_token"]),
        files={"upload": ("canonical-upload.pdf", b"%PDF-1.4\n", "application/pdf")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["file_name"] == "canonical-upload.pdf"
    assert body["case_id"] == case_id


def test_canonical_report_endpoint_returns_503_when_service_not_configured(client, seeded_data, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LOCAL_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "REPORT_SERVICE_BASE_URL", "")
    case_id = seeded_data["case"].id

    response = client.get(f"/api/v1/cases/{case_id}/report", headers=_auth_header(seeded_data["lawyer_token"]))
    assert response.status_code == 503
    assert response.json()["code"] == "EXTERNAL_SERVICE_ERROR"


def test_canonical_report_endpoint_returns_latest_pdf(client, seeded_data, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LOCAL_STORAGE_DIR", str(tmp_path))
    case = seeded_data["case"]
    report_dir = Path(tmp_path) / f"tenant_{case.tenant_id}" / f"case_{case.id}" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    first = report_dir / "report-1.pdf"
    second = report_dir / "report-2.pdf"
    first.write_bytes(b"%PDF-1.4\nfirst\n")
    second.write_bytes(b"%PDF-1.4\nsecond\n")

    response = client.get(f"/api/v1/cases/{case.id}/report", headers=_auth_header(seeded_data["lawyer_token"]))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")


def test_canonical_report_endpoint_generates_pdf_via_report_service(client, seeded_data, monkeypatch, tmp_path):
    from app.core.config import settings
    from app.services.report import ReportService

    monkeypatch.setattr(settings, "LOCAL_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "REPORT_SERVICE_BASE_URL", "http://report-service.mock")

    def _fake_generate(self, payload: dict) -> bytes:
        assert payload["case"]["id"] == seeded_data["case"].id
        return b"%PDF-1.4\ngenerated\n"

    monkeypatch.setattr(ReportService, "generate_case_report_pdf", _fake_generate)

    response = client.get(
        f"/api/v1/cases/{seeded_data['case'].id}/report?regenerate=true",
        headers=_auth_header(seeded_data["lawyer_token"]),
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")

    report_dir = Path(tmp_path) / f"tenant_{seeded_data['case'].tenant_id}" / f"case_{seeded_data['case'].id}" / "reports"
    files = list(report_dir.glob("*.pdf"))
    assert files


def test_canonical_report_endpoint_falls_back_to_latest_on_render_error(client, seeded_data, monkeypatch, tmp_path):
    from fastapi import status

    from app.core.config import settings
    from app.core.errors import AppError, ErrorCode
    from app.services.report import ReportService

    monkeypatch.setattr(settings, "LOCAL_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "REPORT_SERVICE_BASE_URL", "http://report-service.mock")
    case = seeded_data["case"]
    report_dir = Path(tmp_path) / f"tenant_{case.tenant_id}" / f"case_{case.id}" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    latest_pdf = report_dir / "report-latest.pdf"
    latest_pdf.write_bytes(b"%PDF-1.4\nlatest\n")

    def _fake_generate_error(self, payload: dict) -> bytes:
        _ = payload
        raise AppError(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message="mock report error",
            detail="mock report error",
        )

    monkeypatch.setattr(ReportService, "generate_case_report_pdf", _fake_generate_error)

    response = client.get(
        f"/api/v1/cases/{case.id}/report?regenerate=true",
        headers=_auth_header(seeded_data["lawyer_token"]),
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert b"latest" in response.content


def test_client_report_endpoint_does_not_return_lawyer_report(client, seeded_data, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LOCAL_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "REPORT_SERVICE_BASE_URL", "")
    case = seeded_data["case"]
    report_dir = Path(tmp_path) / f"tenant_{case.tenant_id}" / f"case_{case.id}" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "report-lawyer-20260322010101.pdf").write_bytes(b"%PDF-1.4\nlawyer-report\n")

    response = client.get(
        f"/api/v1/cases/{case.id}/report",
        headers=_auth_header(seeded_data["client_token"]),
    )
    assert response.status_code == 503
    assert response.json()["code"] == "EXTERNAL_SERVICE_ERROR"


def test_report_history_visibility_lawyer_all_client_latest(client, seeded_data, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LOCAL_STORAGE_DIR", str(tmp_path))
    case = seeded_data["case"]
    report_dir = Path(tmp_path) / f"tenant_{case.tenant_id}" / f"case_{case.id}" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "report-lawyer-20260322010101.pdf").write_bytes(b"%PDF-1.4\nlawyer-1\n")
    (report_dir / "report-client-20260322010102.pdf").write_bytes(b"%PDF-1.4\nclient-1\n")
    (report_dir / "report-lawyer-20260322010103.pdf").write_bytes(b"%PDF-1.4\nlawyer-2\n")

    lawyer_resp = client.get(
        f"/api/v1/cases/{case.id}/reports",
        headers=_auth_header(seeded_data["lawyer_token"]),
    )
    assert lawyer_resp.status_code == 200
    lawyer_reports = lawyer_resp.json()
    assert len(lawyer_reports) == 3

    client_resp = client.get(
        f"/api/v1/cases/{case.id}/reports",
        headers=_auth_header(seeded_data["client_token"]),
    )
    assert client_resp.status_code == 200
    client_reports = client_resp.json()
    assert len(client_reports) == 1
    assert client_reports[0]["report_scope"] == "client"
    assert client_reports[0]["is_latest"] is True


def test_client_cannot_download_historical_report_by_name(client, seeded_data, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LOCAL_STORAGE_DIR", str(tmp_path))
    case = seeded_data["case"]
    report_dir = Path(tmp_path) / f"tenant_{case.tenant_id}" / f"case_{case.id}" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_name = "report-lawyer-20260322010101.pdf"
    (report_dir / report_name).write_bytes(b"%PDF-1.4\nlawyer-only\n")

    response = client.get(
        f"/api/v1/cases/{case.id}/reports/{report_name}",
        headers=_auth_header(seeded_data["client_token"]),
    )
    assert response.status_code == 403
    assert response.json()["code"] == "CASE_ACCESS_DENIED"


def test_lawyer_can_download_historical_report_by_name(client, seeded_data, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LOCAL_STORAGE_DIR", str(tmp_path))
    case = seeded_data["case"]
    report_dir = Path(tmp_path) / f"tenant_{case.tenant_id}" / f"case_{case.id}" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_name = "report-lawyer-20260322010101.pdf"
    (report_dir / report_name).write_bytes(b"%PDF-1.4\nlawyer-history\n")

    response = client.get(
        f"/api/v1/cases/{case.id}/reports/{report_name}",
        headers=_auth_header(seeded_data["lawyer_token"]),
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert b"lawyer-history" in response.content


def test_canonical_report_endpoint_redirects_to_signed_cos_url(client, seeded_data, monkeypatch):
    from app.core.config import settings
    from app.services.report import ReportService
    from tests.test_storage_backends import FakeCOSClient, _configure_cos_settings

    fake_client = FakeCOSClient()
    _configure_cos_settings(monkeypatch, fake_client, direct_upload_enabled=False)
    monkeypatch.setattr(settings, "REPORT_SERVICE_BASE_URL", "http://report-service.mock")

    def _fake_generate(self, payload: dict) -> bytes:
        assert payload["case"]["id"] == seeded_data["case"].id
        return b"%PDF-1.4\ngenerated-cos\n"

    monkeypatch.setattr(ReportService, "generate_case_report_pdf", _fake_generate)

    response = client.get(
        f"/api/v1/cases/{seeded_data['case'].id}/report?regenerate=true",
        headers=_auth_header(seeded_data["lawyer_token"]),
        follow_redirects=False,
    )

    assert response.status_code == 307
    location = response.headers["location"]
    assert location.startswith("https://cos.example.com/tenant_1/case_1/reports/report-lawyer-")
    assert location.endswith(".pdf?expires=600")
    assert any(key.startswith("tenant_1/case_1/reports/report-lawyer-") for key in fake_client.objects)


def test_report_history_visibility_works_with_cos_storage(client, seeded_data, monkeypatch):
    from tests.test_storage_backends import FakeCOSClient, _configure_cos_settings

    fake_client = FakeCOSClient()
    _configure_cos_settings(monkeypatch, fake_client, direct_upload_enabled=False)
    fake_client.objects["tenant_1/case_1/reports/report-lawyer-20260322010101.pdf"] = {
        "body": b"%PDF-1.4\nlawyer-1\n",
        "content_type": "application/pdf",
    }
    fake_client.objects["tenant_1/case_1/reports/report-client-20260322010102.pdf"] = {
        "body": b"%PDF-1.4\nclient-1\n",
        "content_type": "application/pdf",
    }
    fake_client.objects["tenant_1/case_1/reports/report-lawyer-20260322010103.pdf"] = {
        "body": b"%PDF-1.4\nlawyer-2\n",
        "content_type": "application/pdf",
    }

    lawyer_resp = client.get(
        f"/api/v1/cases/{seeded_data['case'].id}/reports",
        headers=_auth_header(seeded_data["lawyer_token"]),
    )
    assert lawyer_resp.status_code == 200
    lawyer_reports = lawyer_resp.json()
    assert len(lawyer_reports) == 3
    assert lawyer_reports[0]["file_name"] == "report-lawyer-20260322010103.pdf"

    client_resp = client.get(
        f"/api/v1/cases/{seeded_data['case'].id}/reports",
        headers=_auth_header(seeded_data["client_token"]),
    )
    assert client_resp.status_code == 200
    client_reports = client_resp.json()
    assert len(client_reports) == 1
    assert client_reports[0]["report_scope"] == "client"
    assert client_reports[0]["is_latest"] is True


def test_case_report_access_link_returns_signed_cos_url(client, seeded_data, monkeypatch):
    from tests.test_storage_backends import FakeCOSClient, _configure_cos_settings

    fake_client = FakeCOSClient()
    _configure_cos_settings(monkeypatch, fake_client, direct_upload_enabled=False)
    fake_client.objects["tenant_1/case_1/reports/report-lawyer-20260322010101.pdf"] = {
        "body": b"%PDF-1.4\nlawyer-history\n",
        "content_type": "application/pdf",
    }

    response = client.get(
        f"/api/v1/cases/{seeded_data['case'].id}/report/access-link",
        headers=_auth_header(seeded_data["lawyer_token"]),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["file_name"] == "report-lawyer-20260322010101.pdf"
    assert payload["access_url"] == "https://cos.example.com/tenant_1/case_1/reports/report-lawyer-20260322010101.pdf?expires=600"


def test_case_report_version_access_link_returns_signed_cos_url(client, seeded_data, monkeypatch):
    from tests.test_storage_backends import FakeCOSClient, _configure_cos_settings

    fake_client = FakeCOSClient()
    _configure_cos_settings(monkeypatch, fake_client, direct_upload_enabled=False)

    report_name = "report-lawyer-20260322010101.pdf"
    fake_client.objects[f"tenant_1/case_1/reports/{report_name}"] = {
        "body": b"%PDF-1.4\nlawyer-history\n",
        "content_type": "application/pdf",
    }

    response = client.get(
        f"/api/v1/cases/{seeded_data['case'].id}/reports/{report_name}/access-link",
        headers=_auth_header(seeded_data["lawyer_token"]),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["file_name"] == report_name
    assert payload["access_url"] == f"https://cos.example.com/tenant_1/case_1/reports/{report_name}?expires=600"


def test_lawyer_can_download_historical_report_by_name_from_cos(client, seeded_data, monkeypatch):
    from tests.test_storage_backends import FakeCOSClient, _configure_cos_settings

    fake_client = FakeCOSClient()
    _configure_cos_settings(monkeypatch, fake_client, direct_upload_enabled=False)

    report_name = "report-lawyer-20260322010101.pdf"
    fake_client.objects[f"tenant_1/case_1/reports/{report_name}"] = {
        "body": b"%PDF-1.4\nlawyer-history\n",
        "content_type": "application/pdf",
    }

    response = client.get(
        f"/api/v1/cases/{seeded_data['case'].id}/reports/{report_name}",
        headers=_auth_header(seeded_data["lawyer_token"]),
        follow_redirects=False,
    )
    assert response.status_code == 307
    assert response.headers["location"] == f"https://cos.example.com/tenant_1/case_1/reports/{report_name}?expires=600"

import io

import pytest

from app import app, get_db, verify_audit_chain
from werkzeug.security import generate_password_hash


@pytest.fixture()
def client(tmp_path):
    app.config.update(
        TESTING=True,
        DATABASE=str(tmp_path / "test.sqlite3"),
        UPLOAD_DIR=str(tmp_path / "uploads"),
        SECRET_KEY="test-secret",
        AUTO_APPROVE_RECORDS=False,
    )
    with app.app_context():
        from app import init_db

        init_db()
        db = get_db()
        for username, password, role in (
            ("submitter", "submit-pass", "submitter"),
            ("reviewer", "review-pass", "reviewer"),
            ("verifier", "verify-pass", "verifier"),
        ):
            db.execute(
                "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, datetime('now'))",
                (username, generate_password_hash(password), role),
            )
        db.commit()
    with app.test_client() as test_client:
        yield test_client


def login(client, username, password):
    return client.post("/login", data={"username": username, "password": password}, follow_redirects=True)


def csrf_token(client, path):
    response = client.get(path)
    marker = b'name="_csrf_token" value="'
    return response.data.split(marker, 1)[1].split(b'"', 1)[0].decode()


def register(client):
    return client.post(
        "/records/new",
        data={
            "asset_type": "Demo plot",
            "area_label": "Kampala sample area",
            "document": (io.BytesIO(b"original document"), "record.txt"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )


def test_registration_and_matching_verification(client):
    assert login(client, "submitter", "submit-pass").status_code == 200
    response = register(client)
    assert b"UG-REC-" in response.data
    with client.application.app_context():
        record = get_db().execute("SELECT public_reference FROM records").fetchone()
    verify = client.post(
        "/verify",
        data={"reference": record["public_reference"], "document": (io.BytesIO(b"original document"), "record.txt")},
        content_type="multipart/form-data",
    )
    assert b"REAL DOCUMENT" in verify.data


def test_land_search_prepares_title_request_without_changing_document_checks(client):
    login(client, "submitter", "submit-pass")
    response = client.post(
        "/land-search",
        data={"_csrf_token": csrf_token(client, "/land-search"), "search_type": "TITLE", "volume": "KLA", "folio": "123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"SEARCH READY" in response.data
    assert b"UG-SEARCH-" in response.data
    with client.application.app_context():
        search = get_db().execute("SELECT search_type, volume, folio FROM land_searches").fetchone()
    assert search["search_type"] == "TITLE"
    assert search["volume"] == "KLA"


def test_subscription_plan_selection_is_recorded_without_claiming_payment(client):
    login(client, "submitter", "submit-pass")
    response = client.post(
        "/billing",
        data={"_csrf_token": csrf_token(client, "/billing"), "plan_code": "INDIVIDUAL"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Payment setup is not connected yet." in response.data
    with client.application.app_context():
        subscription = get_db().execute(
            "SELECT plan_code, status, provider FROM subscriptions WHERE user_id = 1"
        ).fetchone()
    assert subscription["plan_code"] == "INDIVIDUAL"
    assert subscription["status"] == "PAYMENT_REQUIRED"
    assert subscription["provider"] == "checkout_pending"


def test_first_time_help_page_is_public_and_plain_language(client):
    response = client.get("/help")
    assert response.status_code == 200
    assert b"New to LandVerify?" in response.data
    assert b"Create an account" in response.data
    assert b"Check your document" in response.data


def test_land_registration_stores_structured_fields_and_report(client):
    login(client, "submitter", "submit-pass")
    response = client.post(
        "/records/new",
        data={
            "_csrf_token": csrf_token(client, "/records/new"),
            "asset_type": "Land",
            "area_label": "Kampala",
            "district": "Kampala",
            "county": "Kampala Central",
            "block": "12",
            "plot": "45",
            "tenure": "Freehold",
            "title_volume": "KLA",
            "title_folio": "123",
            "document": (io.BytesIO(b"land document"), "land.txt"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    with client.application.app_context():
        record = get_db().execute("SELECT id, district, plot FROM records").fetchone()
    assert record["district"] == "Kampala"
    assert record["plot"] == "45"
    report = client.get(f"/records/{record['id']}/report")
    assert report.status_code == 200
    assert b"LandVerify evidence report" in report.data
    assert b"Content-Disposition" not in report.data


def test_registration_can_auto_approve(client):
    client.application.config["AUTO_APPROVE_RECORDS"] = True
    login(client, "submitter", "submit-pass")
    response = register(client)
    assert b"automatically approved" in response.data
    with client.application.app_context():
        record = get_db().execute("SELECT status FROM records").fetchone()
        event = get_db().execute(
            "SELECT event_type, tx_hash FROM record_events WHERE event_type = 'AUTO_APPROVED'"
        ).fetchone()
    assert record["status"] == "APPROVED"
    assert event["tx_hash"].startswith("demo-ledger-")


def test_modified_file_fails_and_unknown_reference_is_clear(client):
    login(client, "submitter", "submit-pass")
    register(client)
    with client.application.app_context():
        reference = get_db().execute("SELECT public_reference FROM records").fetchone()["public_reference"]
    mismatch = client.post(
        "/verify",
        data={"reference": reference, "document": (io.BytesIO(b"modified document"), "record.txt")},
        content_type="multipart/form-data",
    )
    assert b"FAKE DOCUMENT" in mismatch.data
    unknown = client.post(
        "/verify",
        data={"reference": "UG-REC-UNKNOWN", "document": (io.BytesIO(b"modified document"), "record.txt")},
        content_type="multipart/form-data",
    )
    assert b"RECORD NOT FOUND" in unknown.data


def test_record_number_is_optional_but_document_is_required(client):
    login(client, "submitter", "submit-pass")
    register(client)
    original = client.post(
        "/verify",
        data={"document": (io.BytesIO(b"original document"), "record.txt")},
        content_type="multipart/form-data",
    )
    missing = client.post("/verify", data={"reference": "UG-REC-UNKNOWN"})
    assert b"REAL DOCUMENT" in original.data
    assert b"DOCUMENT REQUIRED" in missing.data
    unregistered = client.post(
        "/verify",
        data={"document": (io.BytesIO(b"never registered"), "record.txt")},
        content_type="multipart/form-data",
    )
    assert b"FAKE DOCUMENT" in unregistered.data


def test_reviewer_can_approve_and_creates_ledger_proof(client):
    login(client, "submitter", "submit-pass")
    register(client)
    with client.application.app_context():
        record_id = get_db().execute("SELECT id FROM records").fetchone()["id"]
    client.post("/logout")
    login(client, "reviewer", "review-pass")
    response = client.post(f"/records/{record_id}/review", data={"decision": "approve"}, follow_redirects=True)
    assert b"APPROVED" in response.data
    with client.application.app_context():
        event = get_db().execute("SELECT tx_hash FROM record_events WHERE record_id = ? AND event_type = 'REVIEWED'", (record_id,)).fetchone()
    assert event["tx_hash"].startswith("demo-ledger-")


def test_verifier_cannot_register(client):
    login(client, "verifier", "verify-pass")
    response = client.get("/records/new", follow_redirects=True)
    assert b"do not have permission" in response.data


def test_security_headers_and_audit_chain(client):
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    login(client, "submitter", "submit-pass")
    with client.application.app_context():
        assert verify_audit_chain()


def test_health_endpoint_reports_database_ready(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json == {"status": "healthy"}


def test_public_verification_form_includes_csrf_token(client):
    response = client.get("/verify")
    assert b'name="_csrf_token"' in response.data


def test_invalid_csrf_shows_a_friendly_message(client):
    client.application.config["TESTING"] = False
    try:
        response = client.post("/verify", data={"reference": "UG-REC-UNKNOWN"})
        assert response.status_code == 302
        follow_up = client.get(response.headers["Location"])
        assert b"Please refresh this page" in follow_up.data
    finally:
        client.application.config["TESTING"] = True


def test_login_rejects_external_redirect(client):
    response = client.post(
        "/login?next=https://attacker.example",
        data={"username": "submitter", "password": "submit-pass"},
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")


def test_people_can_register_submitter_accounts(client):
    response = client.post(
        "/register",
        data={
            "username": "new_submitter",
            "password": "NewSubmitterPassword-2026!",
            "password_confirmation": "NewSubmitterPassword-2026!",
        },
        follow_redirects=True,
    )
    assert b"Account created" in response.data
    with client.application.app_context():
        user = get_db().execute(
            "SELECT role, status FROM users WHERE username = ?", ("new_submitter",)
        ).fetchone()
    assert user["role"] == "submitter"
    assert user["status"] == "active"


def test_account_registration_rejects_weak_or_mismatched_password(client):
    weak = client.post(
        "/register",
        data={"username": "weakuser", "password": "short", "password_confirmation": "short"},
    )
    mismatch = client.post(
        "/register",
        data={
            "username": "mismatchuser",
            "password": "StrongPassword-2026!",
            "password_confirmation": "DifferentPassword-2026!",
        },
    )
    assert weak.status_code == 400
    assert mismatch.status_code == 400


def test_invalid_verification_upload_is_rejected(client):
    login(client, "submitter", "submit-pass")
    register(client)
    with client.application.app_context():
        reference = get_db().execute("SELECT public_reference FROM records").fetchone()["public_reference"]
    response = client.post(
        "/verify",
        data={"reference": reference, "document": (io.BytesIO(b"not-a-pdf"), "record.pdf")},
        content_type="multipart/form-data",
    )
    assert b"FILE NOT SUPPORTED" in response.data


def test_finalized_record_cannot_be_reviewed_again(client):
    login(client, "submitter", "submit-pass")
    register(client)
    with client.application.app_context():
        record_id = get_db().execute("SELECT id FROM records").fetchone()["id"]
    client.post("/logout")
    login(client, "reviewer", "review-pass")
    first = client.post(f"/records/{record_id}/review", data={"decision": "approve"}, follow_redirects=True)
    assert b"Review decision saved" in first.data
    second = client.post(f"/records/{record_id}/review", data={"decision": "reject", "reason": "late"}, follow_redirects=True)
    assert b"Only records pending review" in second.data

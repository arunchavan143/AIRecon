import html
import re

import pytest

from app import app, db, init_db


@pytest.fixture()
def client(tmp_path):
    app.config.update(
        TESTING=True,
        DATABASE_PATH=str(tmp_path / "lab.sqlite3"),
        RESET_TOKEN_TTL_SECONDS=60,
        RATE_LIMIT_PER_HOUR=5,
        LAB_BASE_URL="http://127.0.0.1:5000",
    )
    with app.app_context():
        init_db()
    with app.test_client() as test_client:
        yield test_client


def latest_token(client, mode):
    response = client.get(f"/mail?mode={mode}")
    text = html.unescape(response.get_data(as_text=True))
    match = re.search(r"/reset\?token=([^&< ]+)", text)
    assert match, "No reset token was found in the local inbox"
    return match.group(1)


def reset_payload(token, username="alice", password="Valid-Lab-Password-2026x"):
    return {"token": token, "username": username, "new_password": password, "confirm_password": password}


def request_reset(client, identifier, mode):
    response = client.post("/forgot-password", data={"identifier": identifier, "mode": mode})
    assert response.status_code == 200
    return latest_token(client, mode)


def test_secure_token_is_single_use(client):
    token = request_reset(client, "alice@test.local", "secure")
    first = client.post("/api/reset?mode=secure", json=reset_payload(token))
    second = client.post("/api/reset?mode=secure", json=reset_payload(token, password="Another-Lab-Password-2026x"))
    assert first.status_code == 200
    assert first.json["ok"] is True
    assert second.status_code == 400
    assert "already been used" in second.json["error"]


def test_secure_mode_binds_token_to_user(client):
    token = request_reset(client, "alice@test.local", "secure")
    response = client.post("/api/reset?mode=secure", json=reset_payload(token, username="bob"))
    assert response.status_code == 200
    assert response.json["target_user_id"] == 1


def test_vulnerable_client_identifier_changes_submitted_account(client):
    token = request_reset(client, "alice@test.local", "vulnerable-client-id")
    response = client.post("/api/reset?mode=vulnerable-client-id", json=reset_payload(token, username="bob", password="Attacker-Lab-Password-2026x"))
    assert response.status_code == 200
    with db() as conn:
        bob = conn.execute("SELECT password_hash FROM users WHERE username = 'bob'").fetchone()
    from werkzeug.security import check_password_hash
    assert check_password_hash(bob["password_hash"], "Attacker-Lab-Password-2026x")


def test_secure_mode_rejects_missing_token(client):
    response = client.post("/api/reset?mode=secure", json=reset_payload("", username="alice"))
    assert response.status_code == 400
    assert response.json["ok"] is False


def test_secure_reset_revokes_existing_session(client):
    first_session = app.test_client()
    second_session = app.test_client()
    login_data = {"identifier": "alice", "password": "Alice-Lab-2026!", "mode": "secure"}
    assert first_session.post("/login", data=login_data).status_code == 302
    assert second_session.post("/login", data=login_data).status_code == 302
    token = request_reset(client, "alice@test.local", "secure")
    response = client.post("/api/reset?mode=secure", json=reset_payload(token, username="alice"))
    assert response.status_code == 200
    assert first_session.get("/account?mode=secure").status_code == 302
    assert second_session.get("/account?mode=secure").status_code == 302

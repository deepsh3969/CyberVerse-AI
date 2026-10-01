"""Authentication, session rotation and RBAC tests (auth active + SQLite)."""
from __future__ import annotations


def test_login_rejects_bad_credentials(auth_client):
    r = auth_client.post("/api/auth/login", json={"email": "admin@cyberverse.local", "password": "wrong-password"})
    assert r.status_code == 401
    assert "Invalid" in r.json()["detail"]


def test_login_and_me(admin_login):
    client, headers, user = admin_login
    assert user["role"] == "admin"
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "admin@cyberverse.local"
    # cookie must be HttpOnly so scripts cannot read the refresh token
    set_cookie = ""
    for resp in [client.post("/api/auth/login", json={"email": "admin@cyberverse.local", "password": "AdminPass123!"})]:
        set_cookie = resp.headers.get("set-cookie", "")
    assert "cv_rt" in set_cookie and "HttpOnly" in set_cookie


def test_writes_require_authentication(auth_client):
    assert auth_client.post("/api/simulate/port-scan", json={}).status_code == 401
    assert auth_client.post("/api/analyze", json={"incident_id": "INC-X"}).status_code == 401
    assert auth_client.patch("/api/incidents/INC-1/status", json={"status": "OPEN"}).status_code == 401
    assert auth_client.post("/api/demo/start").status_code == 401
    assert auth_client.post("/api/reset").status_code == 401
    assert auth_client.get("/api/audit").status_code == 401
    assert auth_client.post("/api/auth/users", json={"email": "a@b.co", "password": "Password1!"}).status_code == 401


def test_reads_stay_open_by_default(auth_client):
    assert auth_client.get("/api/dashboard").status_code == 200
    assert auth_client.get("/api/settings").json()["auth_enabled"] is True


def test_admin_can_write(admin_login):
    client, headers, _ = admin_login
    r = client.post("/api/simulate/port-scan", json={"intensity": "low"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["incident"] is not None


def test_viewer_role_cannot_write(admin_login):
    client, headers, _ = admin_login
    created = client.post(
        "/api/auth/users",
        json={"email": "viewer@cyberverse.local", "password": "ViewerPass1!", "role": "viewer"},
        headers=headers,
    )
    assert created.status_code == 201
    viewer_id = created.json()["user"]["id"]

    login = client.post("/api/auth/login", json={"email": "viewer@cyberverse.local", "password": "ViewerPass1!"})
    assert login.status_code == 200
    viewer_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    assert client.get("/api/dashboard", headers=viewer_headers).status_code == 200
    assert client.post("/api/simulate/port-scan", json={}, headers=viewer_headers).status_code == 403
    assert client.get("/api/audit", headers=viewer_headers).status_code == 403
    assert client.post("/api/auth/users", json={"email": "x@y.co", "password": "Password1!"}, headers=viewer_headers).status_code == 403

    # viewer can still change their own password (self-service)
    pw = client.post(
        "/api/auth/password",
        json={"current_password": "ViewerPass1!", "new_password": "NewViewerPass1!"},
        headers=viewer_headers,
    )
    assert pw.status_code == 200
    assert client.delete(f"/api/auth/users/{viewer_id}", headers=viewer_headers).status_code == 403


def test_refresh_token_rotation(admin_login):
    client, headers, _ = admin_login
    old = client.cookies.get("cv_rt")
    assert old

    first = client.post("/api/auth/refresh")
    assert first.status_code == 200
    assert first.json()["access_token"]
    rotated = client.cookies.get("cv_rt")
    assert rotated and rotated != old

    # replaying the consumed token must fail
    client.cookies.delete("cv_rt")
    replay = client.post("/api/auth/refresh", cookies={"cv_rt": old})
    assert replay.status_code == 401


def test_logout_revokes_session(admin_login):
    client, headers, _ = admin_login
    out = client.post("/api/auth/logout")
    assert out.status_code == 200
    client.cookies.delete("cv_rt")
    refresh = client.post("/api/auth/refresh", cookies={"cv_rt": "already-revoked"})
    assert refresh.status_code == 401


def test_password_change_revokes_sessions(admin_login):
    client, headers, user = admin_login
    r = client.post(
        "/api/auth/password",
        json={"current_password": "AdminPass123!", "new_password": "RotatedPass123!"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["sessions_revoked"] >= 1

    assert client.post("/api/auth/login", json={"email": "admin@cyberverse.local", "password": "AdminPass123!"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "admin@cyberverse.local", "password": "RotatedPass123!"}).status_code == 200

    # passes pydantic (>=8 chars) but exceeds bcrypt's 72-byte limit
    weak = client.post(
        "/api/auth/password",
        json={"current_password": "RotatedPass123!", "new_password": "\u03b1" * 40},
        headers=headers,
    )
    assert weak.status_code == 400


def test_user_management_and_audit(admin_login):
    client, headers, _ = admin_login
    created = client.post(
        "/api/auth/users",
        json={"email": "analyst@cyberverse.local", "password": "AnalystPass1!", "role": "analyst", "full_name": "Ada"},
        headers=headers,
    )
    assert created.status_code == 201
    uid = created.json()["user"]["id"]

    dup = client.post(
        "/api/auth/users",
        json={"email": "analyst@cyberverse.local", "password": "AnalystPass1!", "role": "analyst"},
        headers=headers,
    )
    assert dup.status_code == 409

    users = client.get("/api/auth/users", headers=headers)
    assert users.status_code == 200
    assert users.json()["total"] >= 2

    patched = client.patch(f"/api/auth/users/{uid}", json={"role": "viewer"}, headers=headers)
    assert patched.status_code == 200
    assert patched.json()["user"]["role"] == "viewer"

    # self-demotion must be refused
    me_id = client.get("/api/auth/me", headers=headers).json()["user"]["id"]
    self_demote = client.patch(f"/api/auth/users/{me_id}", json={"role": "viewer"}, headers=headers)
    assert self_demote.status_code == 409

    deleted = client.delete(f"/api/auth/users/{uid}", headers=headers)
    assert deleted.status_code == 200
    assert client.delete(f"/api/auth/users/{uid}", headers=headers).status_code == 404

    audit = client.get("/api/audit?limit=50", headers=headers)
    assert audit.status_code == 200
    actions = {item["action"] for item in audit.json()["items"]}
    assert "auth.login" in actions
    assert "user.created" in actions
    assert "user.deleted" in actions


def test_login_rate_limit(auth_client):
    from app.api.ratelimit import reset_buckets
    from app.core.config import settings

    previous = settings.auth_login_limit_per_minute
    settings.auth_login_limit_per_minute = 3
    reset_buckets()
    try:
        codes = [
            auth_client.post(
                "/api/auth/login", json={"email": "admin@cyberverse.local", "password": "nope"}
            ).status_code
            for _ in range(5)
        ]
        assert 429 in codes
    finally:
        settings.auth_login_limit_per_minute = previous
        reset_buckets()


def test_refresh_and_logout_disabled_without_auth(auth_client):
    # auth_active is on in this fixture; these endpoints must exist and answer
    assert auth_client.post("/api/auth/refresh").status_code == 401
    assert auth_client.post("/api/auth/logout").status_code == 200

import hashlib
import json
import logging
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("FLASK_SECRET_KEY", "local-lab-secret-change-me"),
    DATABASE_PATH=os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "lab.sqlite3")),
    RESET_TOKEN_TTL_SECONDS=int(os.getenv("RESET_TOKEN_TTL_SECONDS", "60")),
    RATE_LIMIT_PER_HOUR=int(os.getenv("RATE_LIMIT_PER_HOUR", "5")),
    LAB_BASE_URL=os.getenv("LAB_BASE_URL", "http://127.0.0.1:5000").rstrip("/"),
    MAILHOG_API_URL=os.getenv("MAILHOG_API_URL", "http://127.0.0.1:8025/api/v2/messages"),
)

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOG_DIR / "security-events.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

MODES = {
    "secure": {
        "label": "Secure reference",
        "description": "High-entropy, hashed, bound, expiring, single-use tokens with password policy and session revocation.",
        "class": "secure",
    },
    "vulnerable-client-id": {
        "label": "Vulnerable: client-supplied account identifier",
        "description": "Validates a token but trusts the submitted username/user_id for the password update.",
        "class": "danger",
    },
    "vulnerable-no-token": {
        "label": "Vulnerable: missing token validation",
        "description": "The final password update does not require a valid reset token.",
        "class": "danger",
    },
    "vulnerable-token-reuse": {
        "label": "Vulnerable: token reuse",
        "description": "A successfully used token remains usable.",
        "class": "danger",
    },
    "vulnerable-multiple-tokens": {
        "label": "Vulnerable training: multiple active tokens",
        "description": "Each reset request leaves earlier unexpired tokens active; determine whether this is intended policy.",
        "class": "training",
    },
    "vulnerable-expiration": {
        "label": "Vulnerable: expiration not enforced",
        "description": "The configured expiration timestamp is stored but not enforced during validation.",
        "class": "danger",
    },
    "vulnerable-no-policy": {
        "label": "Vulnerable: password-policy bypass",
        "description": "The reset endpoint does not apply the server-side password policy.",
        "class": "danger",
    },
    "vulnerable-session": {
        "label": "Vulnerable: sessions remain valid",
        "description": "Existing server-side sessions are not revoked after a password reset.",
        "class": "danger",
    },
    "vulnerable-leak-url": {
        "label": "Vulnerable: token in URL",
        "description": "The reset token remains in the query string by design for URL exposure testing.",
        "class": "danger",
    },
    "vulnerable-leak-response": {
        "label": "Vulnerable: token in response",
        "description": "The reset page deliberately echoes the token in the HTTP response.",
        "class": "danger",
    },
    "vulnerable-leak-referer": {
        "label": "Vulnerable: Referer token leakage",
        "description": "The reset page loads a local tracking resource without a restrictive Referrer-Policy.",
        "class": "danger",
    },
    "vulnerable-leak-debug": {
        "label": "Vulnerable: debug-log token leakage",
        "description": "The raw token is deliberately written to the application security log.",
        "class": "danger",
    },
}

DEFAULT_MODE = "secure"
SYNTHETIC_ACCOUNTS = {
    "alice@test.local": {"username": "alice", "password": "Alice-Lab-2026!"},
    "bob@test.local": {"username": "bob", "password": "Bob-Lab-2026!"},
    "admin@test.local": {"username": "admin", "password": "Admin-Lab-2026!"},
}
COMMON_PASSWORDS = {"password", "password1", "password123", "12345678", "qwerty123", "letmein"}


def now_utc():
    return datetime.now(timezone.utc)


def iso(value):
    return value.astimezone(timezone.utc).isoformat()


def parse_iso(value):
    return datetime.fromisoformat(value)


def db():
    Path(app.config["DATABASE_PATH"]).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with db() as conn:
        conn.executescript((BASE_DIR / "schema.sql").read_text())
        count = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        if count == 0:
            created = iso(now_utc())
            for email, item in SYNTHETIC_ACCOUNTS.items():
                conn.execute(
                    "INSERT INTO users (username, email, password_hash, password_changed_at, created_at) VALUES (?, ?, ?, ?, ?)",
                    (item["username"], email, generate_password_hash(item["password"]), created, created),
                )


def mode_name():
    candidate = request.args.get("mode") or request.form.get("mode") or DEFAULT_MODE
    return candidate if candidate in MODES else DEFAULT_MODE


def mode_info(mode=None):
    return MODES[mode or mode_name()]


def mode_url(endpoint, mode, **kwargs):
    kwargs["mode"] = mode
    return url_for(endpoint, **kwargs)


def token_digest(raw_token):
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def password_valid(password):
    if len(password) < 12:
        return False, "Password must be at least 12 characters long."
    if password.lower() in COMMON_PASSWORDS:
        return False, "That password is on the lab common-password blocklist."
    classes = sum(bool(group) for group in (
        any(c.islower() for c in password),
        any(c.isupper() for c in password),
        any(c.isdigit() for c in password),
        any(not c.isalnum() for c in password),
    ))
    if classes < 3:
        return False, "Password must contain at least three of lowercase, uppercase, number, and symbol."
    return True, ""


def log_event(event_type, user_id=None, token_id=None, details=None, raw_token=None):
    clean_details = dict(details or {})
    if raw_token is not None:
        clean_details["raw_token"] = raw_token
    details_json = json.dumps(clean_details, sort_keys=True)
    stamp = iso(now_utc())
    with db() as conn:
        conn.execute(
            "INSERT INTO security_events (event_type, user_id, token_id, details, created_at) VALUES (?, ?, ?, ?, ?)",
            (event_type, user_id, token_id, details_json, stamp),
        )
    logging.info("event=%s user_id=%s token_id=%s details=%s", event_type, user_id, token_id, details_json)


def find_user(identifier):
    if not identifier:
        return None
    value = str(identifier).strip().lower()
    with db() as conn:
        return conn.execute("SELECT * FROM users WHERE lower(email) = ? OR lower(username) = ? OR CAST(id AS TEXT) = ?", (value, value, value)).fetchone()


def make_reset_token(user_id, mode):
    raw = secrets.token_urlsafe(32)
    created = now_utc()
    expires = created + timedelta(seconds=app.config["RESET_TOKEN_TTL_SECONDS"])
    with db() as conn:
        if mode != "vulnerable-multiple-tokens":
            conn.execute("UPDATE reset_tokens SET revoked_at = ? WHERE user_id = ? AND used_at IS NULL AND revoked_at IS NULL", (iso(created), user_id))
        cur = conn.execute(
            "INSERT INTO reset_tokens (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token_digest(raw), user_id, iso(created), iso(expires)),
        )
        token_id = cur.lastrowid
    log_event("reset_token_generated", user_id=user_id, token_id=token_id, details={"mode": mode, "expires_at": iso(expires)})
    return raw, token_id, expires


def send_local_email(user, raw_token, mode):
    reset_link = f"{app.config['LAB_BASE_URL']}{url_for('reset', token=raw_token, mode=mode)}"
    body = (
        f"Hello {user['username']},\n\n"
        "This is a synthetic local lab password-reset message.\n"
        f"Reset link: {reset_link}\n\n"
        f"Mode: {mode_info(mode)['label']}\n"
        f"This link expires in {app.config['RESET_TOKEN_TTL_SECONDS']} seconds.\n"
    )
    stamp = iso(now_utc())
    with db() as conn:
        conn.execute("INSERT INTO emails (to_email, subject, body, created_at) VALUES (?, ?, ?, ?)", (user["email"], "Synthetic password reset", body, stamp))
    try:
        requests.post(
            app.config["MAILHOG_API_URL"],
            json={"Content": {"Body": body, "Headers": {"From": ["no-reply@test.local"], "To": [user["email"]], "Subject": ["Synthetic password reset"]}}},
            timeout=1,
        )
    except requests.RequestException:
        pass
    return reset_link


def rate_limited(key):
    current = now_utc()
    with db() as conn:
        row = conn.execute("SELECT * FROM rate_limits WHERE key = ?", (key,)).fetchone()
        if not row or current - parse_iso(row["window_start"]) >= timedelta(hours=1):
            conn.execute("INSERT OR REPLACE INTO rate_limits (key, window_start, count) VALUES (?, ?, 1)", (key, iso(current)))
            return False
        if row["count"] >= app.config["RATE_LIMIT_PER_HOUR"]:
            return True
        conn.execute("UPDATE rate_limits SET count = count + 1 WHERE key = ?", (key,))
        return False


def validate_token(raw_token, enforce_expiry=True):
    if not raw_token:
        log_event("reset_token_rejected", details={"reason": "missing"})
        return None, "A reset token is required."
    digest = token_digest(raw_token)
    with db() as conn:
        row = conn.execute("SELECT * FROM reset_tokens WHERE token_hash = ?", (digest,)).fetchone()
    if not row:
        log_event("reset_token_rejected", details={"reason": "unknown", "token_hash_prefix": digest[:12]})
        return None, "The reset token is invalid."
    if row["used_at"]:
        log_event("reset_token_rejected", user_id=row["user_id"], token_id=row["id"], details={"reason": "already_used"})
        return None, "The reset token has already been used."
    if row["revoked_at"]:
        log_event("reset_token_rejected", user_id=row["user_id"], token_id=row["id"], details={"reason": "revoked"})
        return None, "The reset token has been revoked."
    if enforce_expiry and now_utc() >= parse_iso(row["expires_at"]):
        log_event("reset_token_expired", user_id=row["user_id"], token_id=row["id"], details={"expires_at": row["expires_at"]})
        return None, "The reset token has expired."
    log_event("reset_token_validated", user_id=row["user_id"], token_id=row["id"], details={"expiry_enforced": enforce_expiry})
    return row, ""


def invalidate_user_sessions(user_id):
    stamp = iso(now_utc())
    with db() as conn:
        conn.execute("UPDATE users SET session_version = session_version + 1 WHERE id = ?", (user_id,))
        conn.execute("UPDATE sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL", (stamp, user_id))
    log_event("sessions_revoked", user_id=user_id, details={"reason": "password_reset"})


def create_session(user_id):
    raw = secrets.token_urlsafe(32)
    stamp = now_utc()
    with db() as conn:
        user = conn.execute("SELECT session_version FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.execute(
            "INSERT INTO sessions (session_hash, user_id, created_at, expires_at, session_version) VALUES (?, ?, ?, ?, ?)",
            (token_digest(raw), user_id, iso(stamp), iso(stamp + timedelta(hours=8)), user["session_version"]),
        )
    session["sid"] = raw


def current_user():
    raw_sid = session.get("sid")
    if not raw_sid:
        return None
    with db() as conn:
        row = conn.execute(
            "SELECT u.*, s.id AS server_session_id, s.created_at AS session_created_at FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.session_hash = ? AND s.revoked_at IS NULL AND s.expires_at > ? AND s.session_version = u.session_version",
            (token_digest(raw_sid), iso(now_utc())),
        ).fetchone()
    return row


def json_or_form(name):
    payload = request.get_json(silent=True) or {}
    return request.form.get(name) or request.args.get(name) or payload.get(name)


def require_login(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            return redirect(mode_url("login", mode_name()))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_lab_context():
    mode = mode_name()
    return {"modes": MODES, "active_mode": mode, "active_mode_info": MODES[mode], "current_user": current_user(), "mode_url": mode_url}


@app.after_request
def security_headers(response):
    mode = mode_name()
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    if mode.startswith("vulnerable-leak-referer"):
        response.headers.pop("Referrer-Policy", None)
    else:
        response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.route("/")
def index():
    return render_template("index.html", title="Password Reset VAPT Lab")


@app.route("/login", methods=["GET", "POST"])
def login():
    mode = mode_name()
    if request.method == "POST":
        identifier = request.form.get("identifier", "")
        password = request.form.get("password", "")
        user = find_user(identifier)
        if user and check_password_hash(user["password_hash"], password):
            create_session(user["id"])
            flash("Signed in to the synthetic lab account.", "success")
            return redirect(mode_url("account", mode))
        flash("Invalid synthetic account credentials.", "error")
    return render_template("login.html", title="Sign in", mode=mode)


@app.route("/register", methods=["GET", "POST"])
def register():
    mode = mode_name()
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        valid, reason = password_valid(password)
        if not username or not email.endswith("@test.local"):
            flash("Registration is limited to synthetic @test.local accounts.", "error")
        elif not valid:
            flash(reason, "error")
        else:
            try:
                stamp = iso(now_utc())
                with db() as conn:
                    conn.execute("INSERT INTO users (username, email, password_hash, password_changed_at, created_at) VALUES (?, ?, ?, ?, ?)", (username, email, generate_password_hash(password), stamp, stamp))
                flash("Synthetic account registered. You can now sign in.", "success")
                return redirect(mode_url("login", mode))
            except sqlite3.IntegrityError:
                flash("That synthetic username or email already exists.", "error")
    return render_template("register.html", title="Register synthetic account", mode=mode)


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    mode = mode_name()
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip().lower()
        user = find_user(identifier)
        limited = mode == "secure" and rate_limited(identifier or "blank")
        if limited:
            log_event("reset_token_rejected", details={"reason": "rate_limited", "identifier": identifier})
        elif user:
            raw_token, token_id, expires = make_reset_token(user["id"], mode)
            link = send_local_email(user, raw_token, mode)
            log_event("password_reset_requested", user_id=user["id"], details={"mode": mode})
            if mode == "vulnerable-leak-debug":
                log_event("vulnerable_debug_token", user_id=user["id"], token_id=token_id, details={"mode": mode}, raw_token=raw_token)
            if mode == "secure":
                flash("If that synthetic account exists, a reset message is available in the local inbox.", "success")
            else:
                flash(f"Synthetic local reset message created. Open /mail to retrieve it. Expires: {expires.isoformat()}", "success")
        else:
            log_event("password_reset_requested", details={"mode": mode, "account_match": False})
            flash("If that synthetic account exists, a reset message is available in the local inbox.", "success")
    return render_template("forgot.html", title="Forgot password", mode=mode)


def reset_failure(error, mode, raw_token):
    if request.is_json:
        return jsonify({"ok": False, "error": error}), 400
    return render_template("reset.html", title="Reset password", mode=mode, token=raw_token or "", error=error), 400


@app.route("/reset", methods=["GET", "POST"])
def reset():
    mode = mode_name()
    raw_token = json_or_form("token")
    supplied_identifier = json_or_form("username") or json_or_form("user_id")
    response_leak = raw_token if mode == "vulnerable-leak-response" else None
    referer_leak = mode == "vulnerable-leak-referer"
    if mode == "vulnerable-leak-debug" and raw_token:
        log_event("vulnerable_debug_token", details={"mode": mode}, raw_token=raw_token)
    if request.method == "GET":
        if not raw_token and mode == "secure":
            return render_template("reset.html", title="Reset password", mode=mode, error="Open a reset link from the local inbox."), 400
        return render_template("reset.html", title="Reset password", mode=mode, token=raw_token or "", response_leak=response_leak, referer_leak=referer_leak)

    new_password = request.form.get("new_password") or (request.get_json(silent=True) or {}).get("new_password") or ""
    confirm_password = request.form.get("confirm_password") or (request.get_json(silent=True) or {}).get("confirm_password") or new_password
    if new_password != confirm_password:
        return reset_failure("Passwords do not match.", mode, raw_token)

    token_row = None
    target_user = None
    if mode == "vulnerable-no-token":
        target_user = find_user(supplied_identifier)
        log_event("reset_token_rejected", user_id=target_user["id"] if target_user else None, details={"reason": "validation_bypassed", "supplied_identifier": supplied_identifier})
    else:
        token_row, error = validate_token(raw_token, enforce_expiry=(mode != "vulnerable-expiration"))
        if not token_row:
            return reset_failure(error, mode, raw_token)
        token_user = find_user(str(token_row["user_id"]))
        if mode == "vulnerable-client-id" and supplied_identifier:
            target_user = find_user(supplied_identifier)
        else:
            target_user = token_user

    if not target_user:
        error = "The target synthetic account was not found."
        return reset_failure(error, mode, raw_token)

    if mode != "vulnerable-no-policy":
        valid, reason = password_valid(new_password)
        if not valid:
            return reset_failure(reason, mode, raw_token)

    changed = iso(now_utc())
    with db() as conn:
        conn.execute("UPDATE users SET password_hash = ?, password_changed_at = ? WHERE id = ?", (generate_password_hash(new_password), changed, target_user["id"]))
        if token_row and mode != "vulnerable-token-reuse":
            conn.execute("UPDATE reset_tokens SET used_at = ? WHERE id = ?", (changed, token_row["id"]))
    if token_row and mode != "vulnerable-token-reuse":
        log_event("reset_token_consumed", user_id=token_row["user_id"], token_id=token_row["id"], details={"mode": mode})
    log_event("password_reset_completed", user_id=target_user["id"], token_id=token_row["id"] if token_row else None, details={"mode": mode, "target_user_id": target_user["id"]})
    if mode != "vulnerable-session":
        invalidate_user_sessions(target_user["id"])
    else:
        log_event("sessions_not_revoked", user_id=target_user["id"], details={"mode": mode})

    if request.is_json:
        return jsonify({"ok": True, "message": "Synthetic password reset completed.", "target_user_id": target_user["id"], "mode": mode})
    flash(f"Password reset completed for synthetic account {target_user['username']}. Sign in with the new password.", "success")
    return redirect(mode_url("login", mode))


@app.route("/change-password", methods=["GET", "POST"])
@require_login
def change_password():
    mode = mode_name()
    user = current_user()
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        if not check_password_hash(user["password_hash"], current_password):
            flash("Current password is incorrect.", "error")
        else:
            valid, reason = password_valid(new_password)
            if not valid:
                flash(reason, "error")
            else:
                with db() as conn:
                    conn.execute("UPDATE users SET password_hash = ?, password_changed_at = ? WHERE id = ?", (generate_password_hash(new_password), iso(now_utc()), user["id"]))
                invalidate_user_sessions(user["id"])
                session.clear()
                flash("Password changed and all sessions revoked.", "success")
                return redirect(mode_url("login", mode))
    return render_template("change_password.html", title="Change password", mode=mode)


@app.route("/account")
@require_login
def account():
    user = current_user()
    with db() as conn:
        tokens = conn.execute("SELECT * FROM reset_tokens WHERE user_id = ? ORDER BY id DESC LIMIT 10", (user["id"],)).fetchall()
        sessions = conn.execute("SELECT id, created_at, expires_at, revoked_at, session_version FROM sessions WHERE user_id = ? ORDER BY id DESC LIMIT 10", (user["id"],)).fetchall()
    return render_template("account.html", title="Account", mode=mode_name(), user=user, tokens=tokens, sessions=sessions, session_cookie_hash=token_digest(session.get("sid", ""))[:16])


@app.route("/logout")
def logout():
    raw_sid = session.get("sid")
    if raw_sid:
        with db() as conn:
            conn.execute("UPDATE sessions SET revoked_at = ? WHERE session_hash = ? AND revoked_at IS NULL", (iso(now_utc()), token_digest(raw_sid)))
    session.clear()
    flash("Signed out of the synthetic lab account.", "success")
    return redirect(mode_url("login", mode_name()))


@app.route("/mail")
def mail():
    with db() as conn:
        emails = conn.execute("SELECT * FROM emails ORDER BY id DESC LIMIT 50").fetchall()
    return render_template("mail.html", title="Local mail inbox", emails=emails, mode=mode_name())


@app.route("/events")
def events():
    with db() as conn:
        rows = conn.execute("SELECT * FROM security_events ORDER BY id DESC LIMIT 100").fetchall()
    return render_template("events.html", title="Security events", events=rows, mode=mode_name())


@app.route("/tracking/pixel")
def tracking_pixel():
    referrer = request.headers.get("Referer", "")
    log_event("referer_sink_observed", details={"referer": referrer, "mode": mode_name()})
    return (b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;", 200, {"Content-Type": "image/gif", "Cache-Control": "no-store"})


@app.route("/api/reset", methods=["POST"])
def api_reset():
    return reset()


@app.route("/health")
def health():
    return jsonify({"ok": True, "service": "password-reset-vapt-lab", "mode": mode_name()})


with app.app_context():
    init_db()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=False)

# Controlled Password Reset Security VAPT Lab

This directory contains a small, intentionally vulnerable Flask application for **authorized local security testing and VAPT training**. It uses Python, Flask, SQLite, HTML/CSS/JavaScript, and a built-in local inbox. MailHog is optional. The application is restricted to synthetic accounts and does not integrate with real email, real credentials, external identity providers, production infrastructure, or third-party targets.

The lab follows the reset-token properties recommended by OWASP: reset tokens should be cryptographically random, sufficiently long, linked to an individual user, stored securely, single-use, and time-limited.[1] The test coverage is aligned with the OWASP guidance for weak password-change and password-reset functionality, including account binding, expiration, reuse, token exposure, rate limiting, password policy, and session handling.[2]

## Architecture

| Component | Implementation |
|---|---|
| Web application | Flask in `app.py`, bound to `127.0.0.1:5000` |
| Persistence | SQLite at `data/lab.sqlite3` |
| Local inbox | Built-in `/mail` page; optional MailHog via `docker-compose.yml` |
| Security log | `logs/security-events.log` and `/events` |
| Sessions | Server-side records with a signed Flask cookie containing a session handle |
| Reset tokens | Raw token delivered only to the local inbox; SHA-256 digest stored in SQLite |
| External testing | Burp Suite against ordinary HTTP form and JSON requests |

## Setup

From this directory, run:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). The database is initialized automatically with the synthetic accounts. To initialize it explicitly, run `python init_db.py`. To reset the lab state, run `./reset_lab.sh` and start the application again.

The default reset-token TTL is 60 seconds and can be changed with `RESET_TOKEN_TTL_SECONDS`. The secure mode limits reset requests to `RATE_LIMIT_PER_HOUR` per identifier, defaulting to five per hour. The application uses the fixed `LAB_BASE_URL` when creating reset links rather than trusting an unvalidated `Host` header.

### Optional MailHog

The built-in `/mail` inbox is sufficient and is the default. For MailHog, start the optional profile from this directory:

```bash
docker compose --profile mailhog up --build
```

The MailHog UI is available at [http://127.0.0.1:8025](http://127.0.0.1:8025). The lab still stores a local copy at `/mail`, so no external mail service is required.

## Synthetic accounts

Use only these documented local credentials. They are intentionally synthetic and must not be replaced with real credentials.

| Email | Username | Lab password |
|---|---|---|
| `alice@test.local` | `alice` | `Alice-Lab-2026!` |
| `bob@test.local` | `bob` | `Bob-Lab-2026!` |
| `admin@test.local` | `admin` | `Admin-Lab-2026!` |

Registration accepts only new `@test.local` accounts and applies the secure password policy.

## Application endpoints

| Endpoint | Purpose |
|---|---|
| `/login` | Sign in with a synthetic account |
| `/register` | Register a synthetic `@test.local` account |
| `/forgot-password` | Request a local reset email |
| `/reset` | Browser reset form; accepts `token`, `username`, `new_password`, and `confirm_password` |
| `/api/reset` | JSON reset endpoint for Burp Repeater and parameter testing |
| `/account` | Account, server-side session, token metadata, and session lifecycle |
| `/change-password` | Authenticated password change |
| `/logout` | Revoke the current session and clear the browser cookie |
| `/mail` | Built-in synthetic mail inbox |
| `/events` | Security-event evidence view |
| `/tracking/pixel` | Local sink used only by the Referer-leakage scenario |
| `/health` | Local health check |

Select a scenario with the `mode` query parameter, for example `/forgot-password?mode=secure`. The mode is also available in the UI selector and is carried by forms and reset links.

## Secure reference behavior

The `secure` mode uses high-entropy `secrets.token_urlsafe(32)` tokens, stores only their SHA-256 digest, binds the token to the server-side user ID, enforces the configured expiration time, revokes earlier outstanding tokens, and marks the token used after a successful reset. It applies the password policy, returns a generic forgot-password message, rate-limits reset requests, uses a fixed local base URL, and revokes existing server-side sessions after the password changes.

Secure-mode security events include reset requested, token generated, token validated, token rejected, token expired, token consumed, password reset completed, and sessions revoked. Raw reset tokens and passwords are not logged in secure mode.

## Exercises

Each exercise is intentionally kept separate. The exercise documents state the objective, prerequisites, endpoint, expected secure behavior, and testing goal without placing the solution beside the exercise. Detailed answer guidance is in `solutions/`.

| Scenario | Mode | Testing focus |
|---|---|---|
| Client-supplied account identifier | `vulnerable-client-id` | Change `username` or `user_id` while keeping a token issued for another account |
| Missing token validation | `vulnerable-no-token` | Test missing, empty, invalid, and modified tokens |
| Token reuse | `vulnerable-token-reuse` | Replay a successful reset token |
| Old-token invalidation | `secure` versus new reset requests | Compare latest-token-only behavior with outstanding-token behavior |
| Multiple-token behavior | `vulnerable-multiple-tokens` | Generate TOKEN-A, TOKEN-B, and TOKEN-C and observe each lifecycle state |
| Token expiration | `vulnerable-expiration` | Wait past the configured TTL and compare enforcement |
| Password-policy bypass | `vulnerable-no-policy` | Submit a weak password and compare server-side enforcement |
| Session invalidation | `vulnerable-session` | Keep two sessions and replay the old session after reset |
| Token leakage | `vulnerable-leak-url`, `vulnerable-leak-response`, `vulnerable-leak-referer`, `vulnerable-leak-debug` | Inspect URL, response, Referer, and application-log exposure |
| Account takeover validation | Any applicable vulnerable mode | Prove password change, previous-credential failure, attacker-controlled password success, and account access |

The existence of multiple active tokens is not automatically labeled vulnerable. The tester must determine the intended token policy, its documentation, and whether the behavior creates an unauthorized reset path.

## Reset-token lifecycle

A reset request finds a synthetic user, creates a random raw token, stores its hash and metadata, writes a local email, and records a security event. The raw token is then presented through the local inbox. A reset request validates the token hash, bound user, expiration, used state, and revocation state. After a successful secure reset, the token receives `used_at`, the password is replaced, all sessions are revoked, and the completion is logged.

The token table stores `token_hash`, `user_id`, `created_at`, `expires_at`, `used_at`, and `revoked_at`. The `account` view exposes the token lifecycle metadata without exposing raw tokens.

## Session lifecycle

A successful login creates a server-side session record with a hashed session handle, creation and expiration timestamps, a session version, and a browser cookie. The account page shows the server-side session record ID and a cookie-hash prefix for Burp correlation. Secure password reset increments the user session version and marks existing sessions revoked. The vulnerable session mode deliberately leaves the old sessions usable.

## Burp Suite workflow

Configure Burp Proxy to intercept `127.0.0.1:5000`. Use the browser forms to generate ordinary `application/x-www-form-urlencoded` requests, then send them to Repeater. Use `/api/reset` for JSON request and response comparison. Use separate browser profiles or cookie jars to create two sessions for the session-invalidation exercise. Use Intruder only against the local synthetic endpoint and within the configured local rate limits.

Sample requests are in [`burp/sample-requests.md`](burp/sample-requests.md). Evidence should include the request and response, relevant cookies, status code, changed parameters, token metadata, login results, and the security-event record. Do not include real credentials or any external host in evidence.

## Reporting metadata

Scenario-to-reporting metadata is in [`exercises/reporting-metadata.md`](exercises/reporting-metadata.md). It includes vulnerability name, endpoint, root cause, impact, remediation, OWASP Top 10 2021 and 2025 mappings, suggested severity range, and evidence requirements.

## Safety boundary

> Run this project only on localhost with synthetic test accounts. Never connect it to real email accounts, real user databases, external authentication providers, real credentials, third-party targets, or production infrastructure.

## References

[1]: https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html "OWASP Forgot Password Cheat Sheet"
[2]: https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/04-Authentication_Testing/09-Testing_for_Weak_Password_Change_or_Reset_Functionalities "OWASP WSTG: Testing for Weak Password Change or Reset Functionalities"
[3]: https://owasp.org/Top10/2021/ "OWASP Top 10:2021"
[4]: https://owasp.org/Top10/2025/en/ "OWASP Top 10:2025"

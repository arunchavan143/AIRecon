# Sample Burp Requests

Run the lab at `http://127.0.0.1:5000`. These examples use synthetic accounts only. Capture the normal browser requests in Proxy first; use Repeater to change one parameter at a time.

## Secure reset rejects an invalid token

```http
POST /api/reset?mode=secure HTTP/1.1
Host: 127.0.0.1:5000
Content-Type: application/json

{"token":"invalid-token","username":"alice","new_password":"Valid-Lab-Password-2026x","confirm_password":"Valid-Lab-Password-2026x"}
```

Expected secure behavior is an HTTP 400 response with `ok: false`.

## Client-supplied account identifier comparison

1. Request a reset for `alice@test.local` in `vulnerable-client-id` mode and copy the token from `/mail`.
2. Send the normal request with `username=alice`.
3. In Repeater, change only `username= bob` while keeping the same token.

```http
POST /api/reset?mode=vulnerable-client-id HTTP/1.1
Host: 127.0.0.1:5000
Content-Type: application/json

{"token":"TOKEN-A","username":"bob","new_password":"Attacker-Lab-Password-2026x","confirm_password":"Attacker-Lab-Password-2026x"}
```

Compare the target account's login behavior and `/account` record. Repeat with `mode=secure`; the token-bound account must be used instead of the client value.

## Missing-token validation comparison

```http
POST /api/reset?mode=vulnerable-no-token HTTP/1.1
Host: 127.0.0.1:5000
Content-Type: application/json

{"token":"","username":"bob","new_password":"Attacker-Lab-Password-2026x","confirm_password":"Attacker-Lab-Password-2026x"}
```

Repeat with `mode=secure`. The secure mode must reject missing, empty, invalid, and modified tokens.

## Password policy comparison

```http
POST /api/reset?mode=vulnerable-no-policy HTTP/1.1
Host: 127.0.0.1:5000
Content-Type: application/json

{"token":"TOKEN-A","username":"alice","new_password":"short","confirm_password":"short"}
```

The secure mode must reject the same password even when the token is valid.

## Session invalidation

1. Sign in to the same synthetic account in two cookie jars or two browser sessions.
2. Reset that account's password in `vulnerable-session` mode.
3. Replay the old `/account` request with the first cookie.
4. Repeat in `secure` mode.

The secure mode increments the user's session version, revokes server-side sessions, and requires sign-in again.

## Token leakage

Use the four isolated modes below and inspect Burp HTTP history, response bodies, Referer headers, and the local log file:

| Mode | Evidence location |
|---|---|
| `vulnerable-leak-url` | Reset URL query string |
| `vulnerable-leak-response` | Reset page response body |
| `vulnerable-leak-referer` | Request to `/tracking/pixel` and its `Referer` header |
| `vulnerable-leak-debug` | `logs/security-events.log` and `/events` |

The local application deliberately contains no third-party resource or external email integration.

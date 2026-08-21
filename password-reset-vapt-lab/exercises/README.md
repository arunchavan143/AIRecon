# Exercises

These exercises are designed for self-testing. Complete each objective before opening the corresponding solution file. Use only the synthetic accounts in the main README.

## 1. Client-supplied account identifier

**Objective.** Determine whether a reset token is bound to the account selected by the server or to a client-supplied username or user ID.

**Prerequisites.** Request a reset for Alice and copy the token from `/mail`.

**Endpoint.** `POST /api/reset?mode=vulnerable-client-id` and the same request with `mode=secure`.

**Expected secure behavior.** The server derives the target account from the token and ignores any conflicting client-supplied account identifier.

**Testing goal.** Compare `TOKEN-A + Alice` with `TOKEN-A + Bob`, record the password-login result for both accounts, and capture the request and response evidence.

## 2. Missing token validation

**Objective.** Determine whether the final password-change operation requires a valid reset token.

**Prerequisites.** Know a synthetic username and a policy-compliant test password.

**Endpoint.** `POST /api/reset?mode=vulnerable-no-token` and `mode=secure`.

**Expected secure behavior.** Missing, empty, invalid, and modified tokens are rejected before any password update.

**Testing goal.** Submit each token condition while keeping the target account and password constant. Confirm whether the password changes.

## 3. Token reuse

**Objective.** Determine whether a token can be replayed after a successful password reset.

**Prerequisites.** One valid synthetic reset token.

**Endpoint.** `POST /api/reset?mode=vulnerable-token-reuse` and `mode=secure`.

**Expected secure behavior.** A successful reset marks the token used and rejects a second attempt.

**Testing goal.** Send the identical token twice with different new passwords and compare the responses and token metadata.

## 4. Old-token invalidation

**Objective.** Determine whether a newer reset request revokes an earlier outstanding token.

**Prerequisites.** A synthetic account and a reset-token TTL long enough to perform two requests.

**Endpoint.** `/forgot-password?mode=secure` followed by `/api/reset?mode=secure`.

**Expected secure behavior.** The reference implementation applies a latest-token-only policy by revoking earlier unused tokens when a new reset is requested.

**Testing goal.** Generate TOKEN-A, request a second reset for TOKEN-B, and observe the `revoked_at` state and validation result for both.

## 5. Multiple-token behavior

**Objective.** Determine the intended behavior when several unexpired tokens exist.

**Prerequisites.** A synthetic account and three reset requests.

**Endpoint.** `/forgot-password?mode=vulnerable-multiple-tokens` and `/api/reset?mode=vulnerable-multiple-tokens`.

**Expected secure behavior.** The application policy should be explicit, consistently enforced, and documented; multiple active tokens are not automatically a vulnerability.

**Testing goal.** Generate TOKEN-A, TOKEN-B, and TOKEN-C, test each, and record whether the observed behavior matches the stated policy.

## 6. Token expiration

**Objective.** Determine whether an expired reset token remains usable.

**Prerequisites.** A token and the default 60-second TTL, or a shorter test TTL set with `RESET_TOKEN_TTL_SECONDS`.

**Endpoint.** `/api/reset?mode=vulnerable-expiration` and `mode=secure`.

**Expected secure behavior.** A token whose `expires_at` is in the past is rejected and logged as expired.

**Testing goal.** Wait beyond the TTL, submit the same token in both modes, and compare the result with the metadata and security events.

## 7. Password-policy bypass

**Objective.** Determine whether password strength is validated server-side during reset.

**Prerequisites.** A valid reset token for a synthetic account.

**Endpoint.** `/api/reset?mode=vulnerable-no-policy` and `mode=secure`.

**Expected secure behavior.** The reset endpoint applies the same minimum length, common-password rejection, and three-character-class policy used elsewhere.

**Testing goal.** Submit a short or common password and compare the HTTP result and subsequent login behavior.

## 8. Session invalidation

**Objective.** Determine whether existing authenticated sessions survive a password reset.

**Prerequisites.** Two browser sessions or two Burp cookie jars for the same synthetic account.

**Endpoint.** `/account` before and after `/api/reset?mode=vulnerable-session` or `mode=secure`.

**Expected secure behavior.** All existing sessions are revoked, the session version changes, and the old `/account` request requires authentication again.

**Testing goal.** Replay the old session cookie after reset and record the status, redirect, server session ID, and session table evidence.

## 9. Password-reset token leakage

**Objective.** Identify controlled reset-token exposure in URLs, responses, Referer headers, and debug logs.

**Prerequisites.** A reset request and access to `/mail`, Burp HTTP history, and the local `logs/security-events.log` file.

**Endpoint.** `/reset?mode=vulnerable-leak-url`, `vulnerable-leak-response`, `vulnerable-leak-referer`, and `vulnerable-leak-debug`.

**Expected secure behavior.** The reset page avoids unnecessary response reflection and third-party requests, sends `Referrer-Policy: no-referrer`, and never writes raw tokens to logs.

**Testing goal.** Capture where each mode exposes the token, then compare with secure mode and identify the relevant remediation.

## 10. Account takeover validation

**Objective.** Validate end-to-end impact using synthetic accounts only.

**Prerequisites.** A reproducible finding from one of the vulnerable reset modes.

**Endpoint.** The affected reset endpoint, followed by `/login` and `/account`.

**Expected secure behavior.** Password-reset authorization is required, only the intended account changes, the previous password stops working after a valid reset, and sessions are handled according to the secure policy.

**Testing goal.** Prove authorization or bypass, password change, previous-credential failure where appropriate, attacker-controlled password success, and access to the synthetic account. Record no real-world data.

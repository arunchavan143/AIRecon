# Solutions

These notes are intentionally separate from the exercise prompts. Use them only after recording your own observations.

## 1. Client-supplied account identifier

In `vulnerable-client-id`, the token is validated, but the final target is selected from the submitted `username` or `user_id`. A token issued for Alice can therefore be paired with Bob and update Bob's password. In `secure`, the target is always `reset_tokens.user_id`; changing the submitted identifier does not change the account bound to the token. The remediation is to ignore client account selectors for authorization and to reject any conflicting selector if the API requires one for display.

## 2. Missing token validation

In `vulnerable-no-token`, the target identifier is accepted and the password is changed even when `token` is missing, empty, invalid, or modified. In `secure`, all four requests fail before the password update. The remediation is to perform token lookup, hash comparison, expiration, revocation, used-state, and user binding checks in the final password-change operation rather than only on the page-rendering step.

## 3. Token reuse

In `vulnerable-token-reuse`, the reset succeeds and the token remains without `used_at`, so replay can change the password again. In `secure`, the first success sets `used_at` and the replay returns an already-used error. The remediation is to consume the token atomically with the password update and make the database update conditional on an unused state.

## 4. Old-token invalidation

The secure reference uses latest-token-only behavior. When TOKEN-B is generated for the same account, older unused tokens receive `revoked_at`; TOKEN-A fails validation while TOKEN-B remains eligible until use or expiration. This is a policy choice, not an automatic vulnerability. A finding requires a mismatch between the documented policy and the observed behavior, or a concrete authorization impact.

## 5. Multiple-token behavior

`vulnerable-multiple-tokens` intentionally leaves TOKEN-A, TOKEN-B, and TOKEN-C outstanding. Each should be tested independently. The correct conclusion is based on the intended policy: multiple active tokens can be acceptable when every token is strongly random, bound, short-lived, single-use, and revocable. Do not report the count alone as a vulnerability.

## 6. Token expiration

`vulnerable-expiration` stores an expiration time but calls validation with expiry enforcement disabled. A token can therefore work beyond the configured TTL. `secure` rejects the same token once the current UTC time is at or beyond `expires_at` and writes `reset_token_expired`. The remediation is to enforce the timestamp server-side and test boundary conditions using a consistent timezone.

## 7. Password-policy bypass

`vulnerable-no-policy` allows a short or common password because it skips `password_valid`. `secure` rejects passwords shorter than 12 characters, in the common-password blocklist, or with fewer than three character classes. The remediation is to centralize policy and invoke it on registration, authenticated change, and reset—not only in the UI.

## 8. Session invalidation

Create two sessions, reset the account, and request `/account` with the old cookies. In `vulnerable-session`, existing session records remain valid and the old session can continue to access the account. In `secure`, all session records are marked revoked and the user's session version is incremented, so old cookies no longer resolve to a current user. The remediation is to revoke all sessions or enforce a server-side session-version change after reset.

## 9. Token leakage

The four leak modes have distinct evidence locations. `vulnerable-leak-url` preserves the token in the reset query string. `vulnerable-leak-response` echoes it in the response body. `vulnerable-leak-referer` causes the local tracking request to receive the reset URL in `Referer` because the restrictive header is omitted. `vulnerable-leak-debug` writes the raw token to `logs/security-events.log` and `/events`. The secure mode uses `Referrer-Policy: no-referrer`, does not reflect the token, and never logs the raw token.

## 10. Account takeover validation

Use only the synthetic accounts. First prove the reset authorization condition or bypass. Then submit an attacker-controlled policy-compliant password, verify that the old password no longer works where the account was legitimately reset, verify that the new password works, and open `/account`. For session-related findings, separately record whether an older authenticated session remains usable. The impact statement should identify the exact synthetic account and the exact request/response evidence without suggesting testing against any external target.

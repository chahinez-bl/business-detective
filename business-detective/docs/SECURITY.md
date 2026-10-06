# Security notes

| Concern | Implementation |
|---|---|
| Passwords | bcrypt (cost 12), length/complexity rules, never returned by the API |
| Sessions | signed JWT (HS256, `SECRET_KEY`), 12 h default expiry, `jti` stored on logout → token rejected server-side |
| Brute force | per IP+email throttle (8 failures / 15 min → 429). Per-process; add a gateway limit when scaling out |
| Authorization | every business route resolves the caller's `BusinessMember`; non-members get 404; write routes need owner/admin/member; settings/members/deletes need owner/admin |
| Isolation | all rows carry `business_id`; cross-references (action→insight, dataset→business) are re-verified; covered by `tests/test_isolation.py` (≈25 endpoint probes) |
| Uploads | `.csv`/`.xlsx` only, size cap (default 15 MB, streamed), row cap, magic-byte check, zip expansion cap, random server-side file names under a per-business private directory, sanitized display names (no path traversal) |
| Files & reports | never exposed as static files; downloaded only via authenticated endpoints |
| Errors | `ApiError` messages are written for customers; unexpected errors return a reference id only; no stack traces |
| Logging | exception type + path + reference; request bodies and dataset values are never logged |
| Transport | terminate HTTPS at the host/proxy; security headers set (`nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`); API responses `Cache-Control: no-store` |
| CORS | closed by default in production; only `CORS_ORIGINS` allowed |
| Secrets | environment only; production refuses to start with a missing/short `SECRET_KEY`; `.env` is git-ignored |
| AI | off by default; facts only; numeric-consistency guard on replies |

Known gaps: no email verification / password reset, no MFA, localStorage token (see README), no audit log, no virus scanning of uploads (files are parsed as data and never executed or served).

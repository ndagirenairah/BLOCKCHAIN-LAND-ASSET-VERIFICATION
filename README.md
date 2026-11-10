# LandVerify

LandVerify is a Flask application for integrity-focused land and asset document verification. It calculates a server-side SHA-256 fingerprint, stores permitted metadata and a private file pointer, records review/audit events, and lets an authorized verifier compare a file with its registered version.

## Important legal and operational boundary

This software does not prove legal ownership, replace an official land registry, certify an issuing authority, or prevent fraud outside the system. A matching hash proves only that the submitted bytes match the version registered in this application. Real land records must be processed only after written authorization, privacy/legal review, an accountable data owner, an approved retention policy, and a trusted authoritative source.

The application no longer creates demo users or demo records at startup. Never put real personal data or confidential documents on a public blockchain.

## Features

- Server-side SHA-256 hashing of exact uploaded bytes.
- Private file storage outside the static web directory.
- Unique record references and review statuses.
- Submitter, verifier, reviewer, and administrator roles.
- Reviewer approval, rejection, and flagging with reasons.
- Append-only application event history and security audit records.
- Hash-chained audit entries with an integrity verification helper; production deployments should additionally ship logs to an external append-only sink.
- Integrity verification results: `HASH_MATCH`, `HASH_MISMATCH`, and `RECORD_NOT_FOUND`.
- The verification screen presents a matching file as `REAL DOCUMENT` in green and a non-matching file as `FAKE DOCUMENT` in red; a mismatch is an integrity warning, not by itself legal proof that a document is fraudulent.
- The interface uses a local land photograph from Unsplash under the Unsplash License; it is bundled with the application and is not fetched at runtime.
- CSRF protection for state-changing forms.
- Password hashing, session renewal on login, HttpOnly/SameSite cookies, and production secure-cookie mode.
- Login attempt throttling.
- Upload extension, size, and basic file-signature validation.
- Security response headers including CSP, frame protection, MIME sniffing protection, and referrer policy.
- Local ledger adapter that writes only opaque proof data; replace it with an approved permissioned-ledger adapter before production.

## Project layout

```text
app.py                 Flask application and routes
bootstrap_admin.py     One-time administrator provisioning command
templates/             Jinja pages
static/style.css       Responsive dark dashboard UI
static/landscape.jpg   Locally stored land background photograph
tests/test_app.py      Automated workflow tests
requirements.txt       Python dependencies
.env.example           Environment variable example
```

## Requirements and device support

- Python 3.12+ recommended.
- Flask 3.x.
- PostgreSQL is supported for production through `psycopg`. SQLite remains available for local tests and single-process development.
- A production WSGI server such as Waitress, Gunicorn, or uWSGI.
- TLS termination at a trusted reverse proxy or cloud load balancer.
- Secret storage such as Google Secret Manager, never source code or chat.

The application is designed for current Windows, macOS, and Linux environments. Docker Compose provides the most consistent deployment across operating systems. The responsive web interface works on desktop, tablet, and mobile browsers. For local development, use `python app.py`; for a production-like deployment, use Docker Compose or a Linux/container WSGI server.

## Local run

```powershell
cd D:\BLOCKCHAIN-LAND-ASSET-VERIFICATION
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:SECRET_KEY = python -c "import secrets; print(secrets.token_urlsafe(48))"
python app.py
```

Open the local live application at:

<http://127.0.0.1:5000/>

No accounts are created automatically. Provision an administrator explicitly:

```powershell
$env:ADMIN_USERNAME = "your-admin-name"
$env:ADMIN_PASSWORD = "use-a-unique-password-at-least-14-characters"
python bootstrap_admin.py
```

Do not use the example values for a real deployment. Create additional users through an approved administration workflow before onboarding real users.

People can create their own submitter accounts at <http://127.0.0.1:8000/register>. Self-registration never grants reviewer, verifier, or administrator access. Those roles remain administrator-provisioned.

The current Docker configuration sets `AUTO_APPROVE_RECORDS=true`, so a successful registration is immediately marked `APPROVED` and receives an explicit `AUTO_APPROVED` audit event and proof reference. For deployments requiring human review, set `AUTO_APPROVE_RECORDS=false` before starting the app.

## Docker deployment

The included Compose file runs the application with PostgreSQL and private persistent volumes:

```powershell
Copy-Item .env.example .env
# Edit .env and set unique random SECRET_KEY and POSTGRES_PASSWORD values.
docker compose up --build -d
docker compose exec -e ADMIN_USERNAME=your-admin -e ADMIN_PASSWORD=use-a-unique-password-at-least-14-characters app python bootstrap_admin.py
```

The application listens on `127.0.0.1:8000`; place it behind an HTTPS reverse proxy before exposing it beyond the host. Check readiness at `http://127.0.0.1:8000/healthz`.

### Windows Command Prompt (CMD)

Run these commands in `cmd.exe` from the project directory. The generated secret must be assigned to `SECRET_KEY`; printing it alone does not configure Docker Compose.

```bat
D:
cd /d D:\BLOCKCHAIN-LAND-ASSET-VERIFICATION
copy /Y .env.example .env
for /f "delims=" %i in ('python -c "import secrets; print(secrets.token_urlsafe(48))"') do set SECRET_KEY=%i
set POSTGRES_PASSWORD=replace-this-with-a-long-random-password
docker compose config --quiet
docker compose up --build -d
docker compose ps
curl http://127.0.0.1:8000/healthz
```

On macOS or Linux, use the same Docker Compose commands from the project directory. Replace the Windows `copy`, `set`, and PowerShell commands with the shell equivalents, for example:

```sh
cp .env.example .env
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export POSTGRES_PASSWORD="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
docker compose config --quiet
docker compose up --build -d
curl http://127.0.0.1:8000/healthz
```

For a real deployment, set `POSTGRES_PASSWORD` to a unique password. Environment variables set in CMD override values in `.env` for the current command window. To make the values persistent across terminal sessions, edit `.env` directly instead of using `set`.

Provision the first administrator from CMD:

```bat
docker compose exec -e ADMIN_USERNAME=your-admin -e ADMIN_PASSWORD=use-a-unique-password-at-least-14-characters app python bootstrap_admin.py
```

## Production configuration

Required:

- `APP_ENV=production`
- `SECRET_KEY` from a secret manager, at least 32 random bytes, rotated through an operational process.
- `DATABASE` containing a PostgreSQL connection URL for production, or a private SQLite path for local development.
- `UPLOAD_DIR` pointing to private durable storage with process-only permissions.
- `HOST=127.0.0.1` behind a TLS reverse proxy, or the private bind address required by the platform.
- `PORT` supplied by the process manager.

Production requirements:

1. Use PostgreSQL or another approved managed relational database. The included Docker Compose deployment provides PostgreSQL for controlled environments; managed PostgreSQL is preferred for high availability.
2. Run behind HTTPS; configure HSTS only when HTTPS is guaranteed.
3. Use a production WSGI server. Do not run `python app.py` as the public internet server.
4. Store uploads in private object storage or a private volume. Block directory listing and public reads.
5. Add malware scanning/quarantine before accepting real documents.
6. Replace the simulated ledger with an approved permissioned-ledger adapter and document network identity, chain ID, contract/schema, confirmation policy, and recovery behavior.
7. Integrate the authorized partner API only after receiving its sandbox contract, authentication method, field allowlist, error semantics, and written data-access permission.
8. Configure centralized encrypted backups, restore drills, monitoring, alerting, incident response, access reviews, and retention/deletion procedures.
9. Put audit logs in a separately protected append-only or externally monitored sink; the local hash chain detects ordinary changes but the local database is not a tamper-proof forensic record if an attacker can rewrite the entire database.
10. Complete an independent penetration test, privacy review, threat model, and legal review before public launch.

## Security notes

- Production startup fails when `APP_ENV=production` and `SECRET_KEY` is absent.
- Development startup generates a random in-memory fallback secret; restarting invalidates sessions. This fallback must never be used for production.
- There are no repository credentials or seeded administrator accounts.
- Login redirects reject external destinations.
- Login attempts are throttled per source address. A distributed deployment should replace this in-memory control with a shared rate-limit store.
- All POST forms include a session-bound CSRF token.
- File extensions are not trusted alone; PDF/PNG/JPEG signatures are checked. This is not a malware scanner.
- The current SQLite audit trail can be modified by anyone who obtains database write access; use external append-only logging for real operations.

## Testing

```powershell
python -m pytest -q
```

The test suite covers registration, matching and modified-file verification, unknown references, reviewer ledger proof creation, role restrictions, land-search requests, subscriptions, and first-time help. Tests create isolated users and databases; they do not depend on production or demo accounts.

## Operational limitations

This repository is a hardened deployable foundation, not a certified public-service deployment. The missing partner API contract, permissioned-ledger endpoint, compliance owner, MFA integration, malware scanning, external audit sink, backup/restore drills, monitoring, and operational approvals must be completed before processing real records.

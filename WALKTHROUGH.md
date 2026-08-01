# Sprint 3: Projects + Targets CRUD Walkthrough

## 1. What was built
- Added Pydantic models for Projects and Targets (`ProjectCreate`, `ProjectOut`, `TargetCreate`, `TargetOut`).
- Implemented four API endpoints in `backend/main.py`:
  - `POST /projects`: Create a new project.
  - `GET /projects`: List all projects.
  - `POST /projects/{project_id}/targets`: Add a target to an existing project.
  - `GET /projects/{project_id}/targets`: List targets for a specific project.
- Used raw SQL via `psycopg2` with parameterized queries to prevent SQL injection.
- Added 404 error handling for adding or retrieving targets for non-existent projects.

## 2. API Endpoints and `curl` Commands

### Create a Project (`POST /projects`)
```bash
curl -X POST "http://127.0.0.1:8000/projects" \
     -H "Content-Type: application/json" \
     -d '{"name": "ACME Corp"}'
```
**Expected Response:**
```json
{"id": 1, "name": "ACME Corp", "created_at": "2026-08-01T12:00:00"}
```

### List Projects (`GET /projects`)
```bash
curl -X GET "http://127.0.0.1:8000/projects"
```
**Expected Response:**
```json
[{"id": 1, "name": "ACME Corp", "created_at": "2026-08-01T12:00:00"}]
```

### Add a Target (`POST /projects/{project_id}/targets`)
```bash
curl -X POST "http://127.0.0.1:8000/projects/1/targets" \
     -H "Content-Type: application/json" \
     -d '{"domain": "acme.com"}'
```
**Expected Response:**
```json
{"id": 1, "project_id": 1, "domain": "acme.com", "added_at": "2026-08-01T12:05:00"}
```

### List Targets (`GET /projects/{project_id}/targets`)
```bash
curl -X GET "http://127.0.0.1:8000/projects/1/targets"
```
**Expected Response:**
```json
[{"id": 1, "project_id": 1, "domain": "acme.com", "added_at": "2026-08-01T12:05:00"}]
```

### 404 Error Handling Example
```bash
curl -X POST "http://127.0.0.1:8000/projects/999/targets" \
     -H "Content-Type: application/json" \
     -d '{"domain": "notfound.com"}'
```
**Expected Response:**
```json
{"detail": "Project not found"}
```

## 3. Assumptions and Edge Cases Not Handled
- **Pagination:** The GET endpoints currently return all rows in the database. For a real-world scenario with many targets, pagination would need to be added.
- **Uniqueness / Integrity:** The `domain` field on `targets` doesn't have a unique constraint, meaning the same domain could be added multiple times to a project.
- **Input Validation:** Pydantic is checking that strings are passed, but there's no regex validation for checking if the target domain is properly formatted (e.g. ensuring it has no `http://` prefix for a raw domain).
- **Date Handling:** `added_at` and `created_at` are provided by Postgres `now()`. The returned JSON timestamps omit timezone information depending on database configuration.

---

# Sprint 4: Subfinder Wrapper Walkthrough

## 1. What was built
- Implemented `run_subfinder(domain, timeout)` in `backend/recon.py` to act as a Python wrapper around the external `subfinder` binary.
- Used Python's `subprocess` to call `subfinder -d <domain> -silent`.
- Captured `stdout`, handled empty lines, and returned a cleanly stripped list of domains.
- Added strict error handling that throws a clear `RuntimeError` on:
  - Missing `subfinder` binary (`FileNotFoundError`)
  - Command timeout (`TimeoutExpired`)
  - Non-zero exit codes (capturing and logging `stderr`).
- Added a standalone test block at the bottom of the script for `python3 recon.py`.

## 2. Command to Test Standalone
```bash
cd backend
python recon.py
```

## 3. Real Output Example (against hackerone.com)
```text
Running subfinder test on hackerone.com...
Found 17 subdomains. Here are the first 10:
mta-sts.managed.hackerone.com
www.hackerone.com
mta-sts.forwarding.hackerone.com
mta-sts.hackerone.com
websockets.hackerone.com
hackerone.com
a.ns.hackerone.com
b.ns.hackerone.com
events.hackerone.com
gslink.hackerone.com
```

## 4. Error Cases and Testing
- **Binary Missing:** Tested by renaming `subfinder.exe` to `subfinder.exe.bak` and running the script.
  - *Resulting Error:* `Error: subfinder not found - ensure it's installed and on PATH`
- **Non-Zero Exit / stderr Logging:** Handled by validating `result.returncode != 0`. The script captures `stderr` and displays it in the `RuntimeError`.
- **Timeouts:** Simulated logic using `subprocess.run(timeout=60)`. If the subfinder command exceeds the specified timeout (default 60s), a `subprocess.TimeoutExpired` exception is caught, and a `RuntimeError` stating the exact timeout is raised.

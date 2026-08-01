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

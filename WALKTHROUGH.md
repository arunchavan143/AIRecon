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
python3 recon.py
```

## 3. Verification Note
> [!IMPORTANT]
> This has not been executed - verification must happen on the Kali VM where subfinder is actually installed.

---

# Sprint 5: Httpx Wrapper Walkthrough

## 1. What was built
- Implemented `run_httpx(hostnames, timeout)` in `backend/recon.py` to act as a Python wrapper around the external `httpx-toolkit` binary.
  - *Note: We use `httpx-toolkit` instead of stock `httpx` to avoid binary name collisions with the Python `httpx` library on the target Kali system.*
- Configured Python's `subprocess` to call `httpx-toolkit -silent -json -tech-detect -status-code -title` and passed the input list of hostnames via `stdin`.
- Processed each output line as JSON, safely handling potential `JSONDecodeError`s with warnings.
- Extracted relevant fields (hostname, IP, status code, title, tech, server) into a structured dictionary for each successful result.
- **Bug Fix:** Addressed an issue where the `ip` field was incorrectly populated with the hostname. Based on research of the `httpx` JSON schema, the resolved IPs are output in an array under the `a` key (A records), or sometimes as an `ip` string field depending on flags and version. The code now checks both.
  - *Note: This fix requires manual verification on the Kali VM since we cannot run it locally to confirm the exact schema.*
- Added rigorous error handling analogous to `run_subfinder`, raising `RuntimeError`s for missing binaries, timeouts, and non-zero exit codes.
- Updated the standalone test block to chain `run_subfinder` and `run_httpx` together.

## 2. Command to Test Standalone
```bash
cd backend
python3 recon.py
```

## 3. Verification Note
> [!IMPORTANT]
> This has not been executed - verification must happen on the Kali VM.

---

# Sprint 6: Modular Recon Package Refactoring

## 1. What was built
- Refactored `backend/recon.py` into a modular `backend/recon/` package structure to allow easy extensibility for future recon tools. No existing logic or error handling was changed.
- Created `base.py` containing abstract base classes `SubdomainTool` and `HTTPProbeTool` to enforce a standard interface across tools.
- Moved `run_subfinder()` into its own `subfinder.py` file, wrapping it in the `Subfinder` class inheriting from `SubdomainTool`.
- Moved `run_httpx()` into its own `httpx_toolkit.py` file, wrapping it in the `HttpxToolkit` class inheriting from `HTTPProbeTool`.
- Added a `pipeline.py` orchestrator script that ties the tools together in sequence.
- Deleted the old monolithic `backend/recon.py` file to prevent confusion.

## 2. Command to Test Standalone
```bash
cd backend
python3 -m recon.pipeline
```

## 3. Verification Note
> [!IMPORTANT]
> This has not been executed - verification must happen on the Kali VM.

---

# Sprint 6 (Part 2): Wiring Pipeline to DB API Endpoints

## 1. What was built
- Created Pydantic models `HostOut` and `ScanSummary` in `models.py` to type output structures.
- Added `POST /targets/{target_id}/scan` to `main.py` which:
  - Fetches the target domain from the DB.
  - Calls `run_full_pipeline` to orchestrate recon tools synchronously.
  - Upserts discovered host data into the `hosts` table matching by `(target_id, hostname)`. It updates existing hosts by refreshing their details and `last_seen` timestamp, or inserts newly found hosts.
  - Captures `RuntimeError` from the pipeline tools (e.g. missing tools) and maps them to clean `HTTP 500` error responses to prevent application crashes.
- Added `GET /targets/{target_id}/hosts` to `main.py` to list discovered hosts, featuring optional query filters for `alive` status and `tech` stack (using PostgreSQL's `ANY()` array matching).

## 2. API Endpoints and `curl` Commands

### Run a Scan (`POST /targets/{target_id}/scan`)
```bash
curl -X POST "http://127.0.0.1:8000/targets/1/scan"
```
**Expected Successful Response:**
```json
{
  "target_id": 1,
  "hosts_found": 45,
  "hosts_new": 40,
  "hosts_updated": 5
}
```

### List Hosts (`GET /targets/{target_id}/hosts`)
```bash
# List all hosts
curl -X GET "http://127.0.0.1:8000/targets/1/hosts"

# Filter by alive status and specific technology
curl -X GET "http://127.0.0.1:8000/targets/1/hosts?alive=true&tech=Nginx"
```
**Expected Successful Response:**
```json
[
  {
    "id": 1,
    "target_id": 1,
    "hostname": "api.acme.com",
    "ip": "104.16.132.229",
    "status_code": 200,
    "title": "ACME API Docs",
    "tech_stack": ["Nginx", "React"],
    "server": "nginx",
    "alive": true,
    "first_seen": "2026-08-01T12:00:00",
    "last_seen": "2026-08-01T12:30:00"
  }
]
```

## 3. Verification Note
> [!IMPORTANT]
> This has not been executed - verification must happen on the Kali VM.

---

# Sprint 6 (Part 3): Timeout Fix

## 1. What was built
- Increased the default scan timeout passed to `run_full_pipeline` (and the underlying `subfinder` and `httpx-toolkit` calls) from 60 seconds to 180 seconds.
- Made the timeout fully configurable via the `TIMEOUT` environment variable in `backend/recon/pipeline.py`.
- **Why:** The combined execution of subfinder and httpx-toolkit on larger targets can easily exceed 60 seconds. Upping the limit prevents the pipeline from aborting prematurely.

## 2. Verification Note
> [!IMPORTANT]
> This timeout fix has not been executed locally and its effectiveness on real targets requires manual verification on the Kali VM.

---

# Sprint 6 (Part 4): Subfinder Output Sanitization

## 1. What was built
- Added stricter output sanitization in `Subfinder.run()` to defensively catch and clean markdown link syntax (e.g. `[www.hackerone.com](https://www.hackerone.com)`) that was appearing in the subfinder output.
- Added a basic hostname validation check (regex matching alphanumeric characters, dots, and hyphens) to reject and log any lines that don't match, ensuring only clean hostnames enter the pipeline.
- **Why:** Malformed output was observed but the root cause (terminal artifacts, subfinder version quirks, etc.) couldn't be determined locally.

## 2. Verification Note
> [!IMPORTANT]
> This fix is defensive/preventive since the raw malformed output could not be directly observed locally. Real verification requires re-running a scan on the Kali VM and confirming the hostnames come back clean.

---

# Sprint 7: Frontend Scaffold & Projects Screen

## 1. What was built
- Initialized a new React frontend using `create-vite` in the `frontend/` directory (JavaScript, no TypeScript).
- Configured `frontend/vite.config.js` to bind to `0.0.0.0` so the Vite development server is accessible from other machines on the network.
- Created an API wrapper (`frontend/src/api.js`) that defines standard `fetch` calls mapped to all existing backend endpoints (Projects, Targets, Scan, and Hosts). It is temporarily hardcoded to point to the Kali VM IP `http://192.168.126.128:8000`.
- Built the `Projects` page (`frontend/src/pages/Projects.jsx`) which:
  - Fetches and renders a list of projects from the backend on load, including their IDs, Names, and Creation timestamps.
  - Contains a form to create a new project, automatically refreshing the project list upon success.
  - Features robust loading and error states (e.g. gracefully handling an unreachable backend).
- Configured `App.jsx` to render the `Projects` page by default.
- Added a `README.md` in `frontend/` providing clear instructions on how to start the frontend server.

## 2. Command to Run Frontend
Execute the following commands on the Kali VM to start the frontend:
```bash
cd frontend
npm install
npm run dev
```
You can then access the UI at **http://192.168.126.128:5173** from any machine on the network.

## 3. Verification Note
> [!IMPORTANT]
> This has not been executed - verification must happen on the Kali VM since npm and the browser cannot be run/viewed in the local Dev environment.

---

# Sprint 7 (Part 2): CORS & UI Redesign

## 1. What was built
- **CORS Fix:** Added `CORSMiddleware` to the FastAPI backend (`main.py`) to allow cross-origin requests from the frontend dev server (`0.0.0.0`). This directly resolves the `Access-Control-Allow-Origin` errors observed in the browser console.
- **Cyberpunk UI Redesign:** Re-styled the frontend to match a terminal/SOC-dashboard aesthetic.
  - Added a global stylesheet (`frontend/src/index.css`) establishing a dark theme (`#0a0e14` background), electric green (`#00ff9d`) accent color, and monospaced typography for data/headers.
  - Redesigned `Projects.jsx` to utilize subtle bordered panels, inline alert boxes with a red-accent left border for errors, and a custom `LOADING_PROJECTS...` pulse animation instead of generic spinners.
  - Project lists are now cleanly formatted in a data table style, and empty states feel intentional.
  - Avoided heavy UI component libraries, relying on pure, lightweight CSS.

## 2. Verification Note
> [!IMPORTANT]
> - The CORS fix should immediately resolve backend connectivity issues.
> - The new UI restyle needs visual verification via screenshot or local testing on the Kali VM, as rendering and layout cannot be observed from this environment.

---

# Sprint 8: Targets Screen & Routing

## 1. What was built
- **React Router Integration:** Added `react-router-dom` to the project and wrapped the application in a `BrowserRouter` inside `App.jsx`.
- **Project Navigation:** Made the project rows in `Projects.jsx` clickable. Clicking a project navigates the user to its specific targets view (`/projects/:projectId/targets`), passing the project name via router state.
- **Targets Page (`Targets.jsx`):** 
  - Fetches and displays a table of all targets associated with the selected project.
  - Maintains the established cyberpunk/SOC-dashboard aesthetic.
  - Includes a "BACK_TO_PROJECTS" breadcrumb for easy navigation.
  - Includes a form to easily add new target domains.
- **Scan Trigger Integration:** Added a "RUN_RECON" button for each target row.
  - Clicking this button hits the `POST /targets/:targetId/scan` endpoint.
  - Since scans are synchronous and block for up to 180 seconds, built per-row state tracking so only the targeted row transitions to a `SCANNING...` state, disabling its button.
  - Handles the results gracefully inline, either rendering a success summary (`[SUCCESS] Found:45 (New:40 Upd:5)`) or displaying the established inline red alert box if the scan tool errors out or times out.

## 2. Verification Note
> [!IMPORTANT]
> This has not been executed locally. Visual rendering, routing behaviors, and the long-polling scan states must be verified via testing on the Kali VM.

---

# Sprint 9: Hosts Table & Filtering

## 1. What was built
- **New Route:** Added `/targets/:targetId/hosts` mapping to `<Hosts />` in `App.jsx`.
- **Target Navigation:** Target rows in `Targets.jsx` are now clickable, navigating directly to the new Hosts page while safely ignoring clicks on the "RUN_RECON" button.
- **Hosts Page (`Hosts.jsx`):**
  - Fetches and renders all hosts discovered for a given target.
  - **Aesthetic Match:** Strictly follows the established cyberpunk UI (dark background, monospace text, electric green accents, bordered panels).
  - **Data Presentation:** 
    - Tech stack items render as individual stylized chips/tags.
    - Status codes are color-coded (green for 2xx/3xx, red for 4xx/5xx).
    - Alive status renders with a distinct colored indicator.
    - Long page titles clip gracefully.
  - **Client-Side Filtering:** Implemented an "Alive only" toggle and a case-insensitive tech stack filter box to quickly search for specific technologies (e.g. "nginx", "php").
  - **State Handling:** Includes cohesive loading, error, and empty states.

## 2. Verification Note
> [!IMPORTANT]
> This code has not been rendered locally. Please test the new route, clickable rows, table rendering, and client-side filtering on the Kali VM.

---

# Sprint 10: v1 Hardening & Documentation

## 1. What was built
This sprint focused exclusively on polish, error resilience, and getting the codebase ready for a v1.0 tag:
- **Error States Audit:** Across `Projects.jsx`, `Targets.jsx`, and `Hosts.jsx`, `fetch` catch blocks were updated to explicitly handle `Failed to fetch` errors, presenting the user with a clear `BACKEND_UNREACHABLE` message rather than a generic network error.
- **Empty States Audit:** Confirmed and refined empty states across all views, ensuring the `Hosts` view provides a clear call-to-action (`RUN_A_SCAN_FROM_THE_TARGETS_PAGE`) when a target has no hosts yet.
- **Loading States Audit:** Ensured all views correctly display their `[ LOADING... ]` text on initial mount.
- **Data Quirks Documentation:** Added an explicit inline code comment in `Hosts.jsx` documenting that non-2xx status codes (like 404) are intentionally mapped to `alive: true`, since the host successfully answered the HTTP request.
- **Input Validation:** 
  - Added checks to prevent empty/whitespace-only project and target submissions.
  - Added a defensive regex in `Targets.jsx` to automatically strip accidental `http://` or `https://` prefixes from user input before hitting the backend API.
- **v1 Documentation:** Rewrote the root repository `README.md` to be a comprehensive "Getting Started" guide covering prerequisites, environment setup, database initialization, server execution, and the typical user workflow.

## 2. Verification Note
> [!IMPORTANT]
> The v1.0 tag will be applied directly on the Kali VM by the user after visually verifying these frontend resilience improvements.

---

# Sprint 11: URL Discovery Tooling (Katana)

## 1. What was built
Added robust integration for ProjectDiscovery's `katana` to allow discovery of URLs from resolved hostnames.
- **Base Class Addition:** Extended `backend/recon/base.py` with an abstract `URLDiscoveryTool` class enforcing the standard `run(hostnames, timeout)` contract.
- **Katana Wrapper (`katana.py`):**
  - Defensively checks for `katana` in system `PATH` and handles execution timeouts/errors gracefully (returning structured `RuntimeError`s).
  - Uses the `katana -silent -jc -d 2` command (JS crawling, depth 2) via stdin piping.
  - Safely extracts the domain/netloc from each discovered URL using `urllib.parse.urlparse`.
  - Reconciles and maps each discovered URL back to its original input hostname using an `O(1)` case-insensitive set lookup.
  - Explicitly logs and skips malformed output or URLs that do not belong to the initial scan scope.

# AIRecon v1.0

AIRecon is a modular, automated reconnaissance pipeline designed for security operations and bug bounty workflows. It leverages tools like `subfinder` and `httpx-toolkit` to map target domains and stores the results in a PostgreSQL database, all wrapped in a React-based SOC-style dashboard.

## 1. Prerequisites
- **Kali Linux VM** (or equivalent environment with Go installed)
- **PostgreSQL** database server
- **Python 3.10+** (Backend)
- **Node.js & NPM** (Frontend)

The following external tools MUST be installed and available on your system's `PATH`:
- [subfinder](https://github.com/projectdiscovery/subfinder)
- [httpx-toolkit](https://github.com/projectdiscovery/httpx)

## 2. Environment Setup

### Database Initialization
1. Create a PostgreSQL database (e.g., `airecon`).
2. Run the schema creation script located in `backend/schema.sql` (if available) or rely on your DB initialization routine.

### Backend Configuration
Create a `.env` file in the `backend/` directory or export the following variables:
```bash
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="airecon"
export DB_USER="postgres"
export DB_PASSWORD="yourpassword"
export TIMEOUT="180" # Optional: Override default 180s tool timeout
```

## 3. Starting the Servers

You need two terminal windows to run AIRecon—one for the FastAPI backend and one for the Vite React frontend.

**Start the Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Start the Frontend:**
```bash
cd frontend
npm install
npm run dev
```
The frontend is bound to `0.0.0.0:5173` and can be accessed securely from any machine on your network.

## 4. Typical Workflow
1. **Create a Project:** Navigate to the main dashboard (`http://<KALI_IP>:5173`) and initialize a new Project (e.g., "Acme Corp Recon").
2. **Add a Target:** Click on the project to enter the Targets view. Add a base domain (e.g., `acme.com`).
3. **Run Recon:** Click the `RUN_RECON` button next to your new target. This triggers a synchronous pipeline (`subfinder` piped to `httpx-toolkit`). This can take up to 3 minutes; wait for the success indicator.
4. **View Hosts:** Click the target row to drill down into the Hosts view. Here you can filter by "Alive Only" or rapidly search for specific technologies (e.g., "nginx", "php") in the `TECH_FILTER` bar.

from fastapi import FastAPI, HTTPException
from typing import List
from psycopg2.extras import RealDictCursor

from db import get_connection
from models import ProjectCreate, ProjectOut, TargetCreate, TargetOut, HostOut, ScanSummary, UrlOut
from recon.pipeline import run_full_pipeline

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only - fine for now, single-user local tool
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/projects", response_model=ProjectOut)
def create_project(project: ProjectCreate):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO projects (name) VALUES (%s) RETURNING id, name, created_at;",
                (project.name,)
            )
            new_project = cur.fetchone()
            conn.commit()
            return new_project
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/projects", response_model=List[ProjectOut])
def list_projects():
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, name, created_at FROM projects ORDER BY id;")
            projects = cur.fetchall()
            return projects
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/projects/{project_id}/targets", response_model=TargetOut)
def add_target(project_id: int, target: TargetCreate):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id FROM projects WHERE id = %s;", (project_id,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="Project not found")
            
            cur.execute(
                "INSERT INTO targets (project_id, domain) VALUES (%s, %s) RETURNING id, project_id, domain, added_at;",
                (project_id, target.domain)
            )
            new_target = cur.fetchone()
            conn.commit()
            return new_target
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/projects/{project_id}/targets", response_model=List[TargetOut])
def list_targets(project_id: int):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id FROM projects WHERE id = %s;", (project_id,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="Project not found")
            
            cur.execute(
                "SELECT id, project_id, domain, added_at FROM targets WHERE project_id = %s ORDER BY id;",
                (project_id,)
            )
            targets = cur.fetchall()
            return targets
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/targets/{target_id}/scan", response_model=ScanSummary)
def run_scan(target_id: int):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Look up target domain
            cur.execute("SELECT domain FROM targets WHERE id = %s;", (target_id,))
            target = cur.fetchone()
            if not target:
                raise HTTPException(status_code=404, detail="Target not found")
            
            domain = target['domain']
            
            # Run the recon pipeline
            try:
                results = run_full_pipeline(domain)
                hosts = results["hosts"]
                urls = results["urls"]
            except RuntimeError as e:
                raise HTTPException(status_code=500, detail=str(e))
                
            hosts_found = len(hosts)
            hosts_new = 0
            hosts_updated = 0
            
            # Upsert into hosts table
            for res in hosts:
                # PostgreSQL doesn't have arrays in standard %s syntax without adaptation,
                # but psycopg2 handles Python lists gracefully when passed as %s
                cur.execute(
                    "SELECT id FROM hosts WHERE target_id = %s AND hostname = %s;",
                    (target_id, res['hostname'])
                )
                existing_host = cur.fetchone()
                
                if existing_host:
                    cur.execute(
                        """
                        UPDATE hosts
                        SET ip = %s, status_code = %s, title = %s, tech_stack = %s, server = %s, alive = true, last_seen = now()
                        WHERE id = %s;
                        """,
                        (res['ip'], res['status_code'], res['title'], res['tech'], res['server'], existing_host['id'])
                    )
                    hosts_updated += 1
                else:
                    cur.execute(
                        """
                        INSERT INTO hosts (target_id, hostname, ip, status_code, title, tech_stack, server, alive, first_seen, last_seen)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, true, now(), now());
                        """,
                        (target_id, res['hostname'], res['ip'], res['status_code'], res['title'], res['tech'], res['server'])
                    )
                    hosts_new += 1
                    
            # Insert into urls table (we can just ignore duplicates for now or use ON CONFLICT if we added a unique constraint, 
            # but since we didn't add a unique constraint in schema.sql, we'll just insert or delete existing)
            cur.execute("DELETE FROM urls WHERE target_id = %s;", (target_id,))
            for u in urls:
                cur.execute(
                    "INSERT INTO urls (target_id, hostname, url, discovered_at) VALUES (%s, %s, %s, now());",
                    (target_id, u["hostname"], u["url"])
                )
                
            conn.commit()
            return {
                "target_id": target_id,
                "hosts_found": hosts_found,
                "hosts_new": hosts_new,
                "hosts_updated": hosts_updated,
                "urls_found": len(urls)
            }
            
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/targets/{target_id}/hosts", response_model=List[HostOut])
def list_hosts(target_id: int, alive: bool = None, tech: str = None):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id FROM targets WHERE id = %s;", (target_id,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="Target not found")
            
            query = "SELECT id, target_id, hostname, ip, status_code, title, tech_stack, server, alive, first_seen, last_seen FROM hosts WHERE target_id = %s"
            params = [target_id]
            
            if alive is not None:
                query += " AND alive = %s"
                params.append(alive)
                
            if tech is not None:
                query += " AND %s = ANY(tech_stack)"
                params.append(tech)
                
            query += " ORDER BY hostname;"
            
            cur.execute(query, tuple(params))
            hosts = cur.fetchall()
            return hosts
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/targets/{target_id}/urls", response_model=List[UrlOut])
def list_urls(target_id: int):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id FROM targets WHERE id = %s;", (target_id,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="Target not found")
            
            cur.execute(
                "SELECT id, target_id, hostname, url, discovered_at FROM urls WHERE target_id = %s ORDER BY id;",
                (target_id,)
            )
            urls = cur.fetchall()
            return urls
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

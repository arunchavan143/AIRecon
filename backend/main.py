from fastapi import FastAPI, HTTPException
from typing import List
from psycopg2.extras import RealDictCursor

from db import get_connection
from models import ProjectCreate, ProjectOut, TargetCreate, TargetOut

app = FastAPI()

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

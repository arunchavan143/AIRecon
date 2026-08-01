from pydantic import BaseModel
from datetime import datetime

class ProjectCreate(BaseModel):
    name: str

class ProjectOut(BaseModel):
    id: int
    name: str
    created_at: datetime

class TargetCreate(BaseModel):
    domain: str

class TargetOut(BaseModel):
    id: int
    project_id: int
    domain: str
    added_at: datetime

class HostOut(BaseModel):
    id: int
    target_id: int
    hostname: str
    ip: str | None = None
    status_code: int | None = None
    title: str | None = None
    tech_stack: list[str] | None = None
    server: str | None = None
    alive: bool
    first_seen: datetime
    last_seen: datetime

class ScanSummary(BaseModel):
    target_id: int
    hosts_found: int
    hosts_new: int
    hosts_updated: int

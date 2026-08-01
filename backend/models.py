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

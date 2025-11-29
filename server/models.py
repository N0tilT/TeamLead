from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid

class ChangeRequest(BaseModel):
    old_text: str
    new_text: str
    comments: Optional[str] = None

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    task_type: str 
    acceptance_criteria: List[str]
    priority: str 

class Risk(BaseModel):
    category: str
    description: str
    probability: str
    impact: str
    mitigation: List[str]

class Metrics(BaseModel):
    changes_processed: int
    tasks_generated: int
    risks_identified: int
    avg_task_priority: str
    trends: str

class AnalysisResult(BaseModel):
    change_summary: str
    tasks: List[Task]
    risks: List[Risk] = []
    keywords: Dict[str, Any] = {}
    overall_description: str = ""
    metrics: Metrics = Metrics(changes_processed=0, tasks_generated=0, risks_identified=0, avg_task_priority="", trends="")
    tracker_ids: List[str] = [] 
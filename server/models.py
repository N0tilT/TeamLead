from pydantic import BaseModel
from typing import List, Dict, Any

class ChangeRequest(BaseModel):
    old_text: str
    new_text: str
    comments: str

class Task(BaseModel):
    id: str
    title: str
    description: str
    task_type: str
    acceptance_criteria: List[str]
    priority: str = "Medium"

class Risk(BaseModel):
    category: str
    description: str
    probability: str
    impact: str
    mitigation: str

class AnalysisResult(BaseModel):
    change_summary: str
    tasks: List[Task]
    risks: List[Risk]
    overall_description: str
    metrics: Dict[str, Any]
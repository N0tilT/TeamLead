from pydantic import BaseModel, Field
from typing import Literal, List
from datetime import datetime

class TaskInput(BaseModel):
    task_id: str
    code_changes_lines: float = Field(ge=0, le=1000)
    dependencies_count: int = Field(ge=0, le=15)
    team_expertise: float = Field(ge=1.0, le=5.0)
    requirement_uncertainty_pct: float = Field(ge=0, le=100)
    task_type: Literal["feature", "bugfix", "tech_debt", "docs"]

class TaskOutput(BaseModel):
    task_id: str
    complexity_score: float
    risk_score: float
    risk_category: Literal["Low", "Medium", "High", "Critical"]
    mitigation_strategies: List[str]
    evaluated_at: datetime
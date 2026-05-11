from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any,Union,Literal

class TaskInput(BaseModel):
    task_id: str
    code_changes_lines: float
    dependencies_count: float
    team_expertise: float
    requirement_uncertainty_pct: float
    task_type: str = "feature"

class TaskOutput(BaseModel):
    task_id: str
    complexity_score: float
    risk_score: float
    risk_category: str
    mitigation_strategies: List[str]
    evaluated_at: datetime

class FeedbackInput(BaseModel):
    """Фидбэк от пользователя с исходными параметрами оценки"""
    task_id: str
    code_changes_lines: float = Field(ge=0, le=1000)
    dependencies_count: int = Field(ge=0, le=15)
    team_expertise: float = Field(ge=1.0, le=5.0)
    requirement_uncertainty_pct: float = Field(ge=0, le=100)
    task_type: Literal["feature", "bugfix", "tech_debt", "docs"]
    actual_effort_hours: Optional[float] = Field(default=None, ge=0, le=500)
    actual_risk_score: Optional[float] = Field(default=None, ge=0, le=100)

class ConfigImportRequest(BaseModel):
    config: Dict[str, Any]

class AgentMetrics(BaseModel):
    mae: float
    rmse: float
    spearman_rho: float
    samples_count: int


class EvaluateInputs(BaseModel):
    volume: Optional[float] = None
    dependencies: Optional[float] = None
    expertise: Optional[float] = None
    uncertainty: Optional[float] = None

class EvaluatePredictions(BaseModel):
    complexity_score: Optional[float] = None
    risk_score: Optional[float] = None
    risk_category: str = "Unknown"

class EvaluateFeedback(BaseModel):
    actual_effort_hours: Optional[float] = None
    actual_risk_score: Optional[float] = None
    user_rating: Optional[str] = None
    feedback_at: Optional[str] = None

class EvaluateResultResponse(BaseModel):
    """Ответ для GET /evaluate/{task_id}"""
    task_id: str
    inputs: EvaluateInputs
    task_type: Optional[str] = None
    predictions: EvaluatePredictions
    feedback: Optional[EvaluateFeedback] = None
    evaluated_at: Optional[str] = None
    
    class Config:
        from_attributes = True

class SyntheticFeedbackRequest(BaseModel):
    task_ids: Optional[List[str]] = Field(None, description="Список task_id для обработки. Если None — все задачи без фидбэка")
    inflation_min: float = Field(1.2, ge=1.0, le=2.0, description="Минимальный множитель завышения")
    inflation_max: float = Field(1.3, ge=1.0, le=2.0, description="Максимальный множитель завышения")
    dry_run: bool = Field(False, description="Если True — только подсчёт, без записи в БД")

class OptimizationRequest(BaseModel):
    agent: Literal["effort", "risk", "all"] = Field(
        default="all", 
        description="Какой агент оптимизировать"
    )
    min_samples: int = Field(
        default=15, 
        ge=5, le=500,
        description="Минимальное количество записей для обучения"
    )
    method: Optional[Literal["grid", "random", "bayesian"]] = Field(
        default=None,
        description="Метод оптимизации (None = автовыбор)"
    )
    force: bool = Field(
        default=False,
        description="Игнорировать порог срабатывания и запустить принудительно"
    )

class OptimizationMetrics(BaseModel):
    mae: float
    rmse: float
    spearman_rho: float

class OptimizationResultSuccess(BaseModel):
    status: Literal["success"]
    method_used: Optional[str] = None
    metrics: OptimizationMetrics
    samples_used: int
    config_updated: bool

class OptimizationResultSkipped(BaseModel):
    status: Literal["skipped"]
    reason: str
    available_samples: Optional[int] = None

class OptimizationResultFailed(BaseModel):
    status: Literal["failed", "error"]
    error: str
    method_used: Optional[str] = None

AgentOptimizationResult = Union[
    OptimizationResultSuccess, 
    OptimizationResultSkipped, 
    OptimizationResultFailed
]

class OptimizationResponse(BaseModel):
    status: Literal["completed", "partial", "failed"]
    agents_processed: int
    success_count: int
    results: Dict[str, AgentOptimizationResult]
    checkpoint_updated: Optional[Dict[str, Any]] = None
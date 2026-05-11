import os
import json
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Literal, Union, Any
from loguru import logger
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from schemas import TaskInput, TaskOutput, FeedbackInput, ConfigImportRequest
from engine import FuzzyAgent, FuzzyOptimizer
from knowledge import TASK_TYPE_WEIGHTS, MITIGATION_STRATEGIES
from fuzzy_repository import FuzzyFeedbackRepository
from database import DatabaseConfig, DatabaseConnection

app = FastAPI(title="Fuzzy Complexity & Risk Agent", version="2.0.0")

db_config = DatabaseConfig(
    database=os.getenv("FUZZY_DB_NAME", "fuzzy_agent_db"),
    host=os.getenv("FUZZY_DB_HOST", "postgres"),
    user=os.getenv("FUZZY_DB_USER", "postgres"),
    password=os.getenv("FUZZY_DB_PASSWORD", "postgres"),
    port=int(os.getenv("FUZZY_DB_PORT", 5432))
)
db_conn = DatabaseConnection(db_config)
feedback_repo = FuzzyFeedbackRepository(db_conn)

effort_agent = FuzzyAgent("configs/effort_config.json", "effort")
risk_agent = FuzzyAgent("configs/risk_config.json", "risk")
effort_tuner = FuzzyOptimizer(effort_agent)
risk_tuner = FuzzyOptimizer(risk_agent)

CHECKPOINT_FILE = "optimizer_state.json"
def load_checkpoint() -> dict:
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            return json.load(f)
    return {"effort_last": 0, "risk_last": 0, "threshold": 50}

def save_checkpoint(state: dict):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(state, f)

checkpoint = load_checkpoint()

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

class OptimizationResponse(BaseModel):
    status: Literal["completed", "partial", "failed"]
    agents_processed: int
    success_count: int
    results: Dict[str, Union[OptimizationResultSuccess, OptimizationResultSkipped, OptimizationResultFailed]]
    checkpoint_updated: Optional[Dict[str, Any]] = None

class OptimizationRequest(BaseModel):
    agent: Literal["effort", "risk", "all"] = Field(default="all")
    min_samples: int = Field(default=15, ge=5, le=500)
    method: Optional[Literal["centroid", "bisector", "mom", "lom", "som"]] = Field(default=None)
    force: bool = Field(default=False)
    n_trials: int = Field(default=50, ge=10, le=200)
    timeout: int = Field(default=120, ge=30, le=600)

def run_auto_optimization(agent_name: str):
    try:
        agent = effort_agent if agent_name == "effort" else risk_agent
        tuner = effort_tuner if agent_name == "effort" else risk_tuner
        training_data = feedback_repo.get_training_data(agent_name, limit=200)
        if len(training_data) < 15:
            return
        agent.feedback_history = training_data
        result = tuner.optimize_with_method_selection(min_samples=15, n_trials_per_method=30, timeout_per_method=90)
        if "error" not in result:
            agent.save_config()
            total = feedback_repo.get_count()
            checkpoint[f"{agent_name}_last"] = total
            save_checkpoint(checkpoint)
            logger.info(f"[AUTO-OPT] {agent_name} optimized. New MAE: {result['metrics']['mae']:.2f}")
    except Exception as e:
        logger.error(f"[AUTO-OPT] Failed for {agent_name}: {e}")

@app.post("/evaluate", response_model=TaskOutput)
async def evaluate_task(payload: TaskInput):
    try:
        inputs = {
            "volume": payload.code_changes_lines,
            "dependencies": payload.dependencies_count,
            "expertise": payload.team_expertise,
            "uncertainty": payload.requirement_uncertainty_pct
        }
        complexity_pred = effort_agent.evaluate(inputs)
        risk_pred = risk_agent.evaluate(inputs)
        weight = TASK_TYPE_WEIGHTS.get(payload.task_type, 1.0)
        complexity = float(np.clip(complexity_pred * weight, 0, 100))
        risk = float(np.clip(risk_pred * weight, 0, 100))
        category = "Low" if risk < 35 else "Medium" if risk < 60 else "High" if risk < 80 else "Critical"
        predictions = {"complexity_score": complexity, "risk_score": risk}
        feedback_repo.save_evaluate_result(
            task_id=payload.task_id,
            inputs=inputs,
            predictions=predictions,
            task_type=payload.task_type
        )
        return TaskOutput(
            task_id=payload.task_id,
            complexity_score=round(complexity, 2),
            risk_score=round(risk, 2),
            risk_category=category,
            mitigation_strategies=MITIGATION_STRATEGIES[category],
            evaluated_at=datetime.utcnow()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/evaluate/{task_id}")
async def get_evaluate_result(task_id: str):
    result = feedback_repo.get_evaluate_by_task_id(task_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"No evaluation found for task_id: {task_id}")
    return result

@app.post("/feedback")
async def submit_feedback(payload: FeedbackInput, background_tasks: BackgroundTasks):
    try:
        inputs = {
            "volume": payload.code_changes_lines,
            "dependencies": payload.dependencies_count,
            "expertise": payload.team_expertise,
            "uncertainty": payload.requirement_uncertainty_pct
        }
        predictions = {
            "complexity_score": effort_agent.evaluate(inputs),
            "risk_score": risk_agent.evaluate(inputs)
        }
        actual_data = {
            "actual_effort_hours": payload.actual_effort_hours,
            "actual_risk_score": payload.actual_risk_score
        }
        feedback_repo.save_feedback(task_id=payload.task_id, actual_data=actual_data)
        if payload.actual_effort_hours is not None:
            target_effort = min(max(payload.actual_effort_hours, 0.0), 100.0)
            effort_agent.add_feedback(inputs, predictions["complexity_score"], target_effort)
        if payload.actual_risk_score is not None:
            target_risk = min(max(payload.actual_risk_score * 100, 0.0), 100.0)
            risk_agent.add_feedback(inputs, predictions["risk_score"], target_risk)
        total_count = feedback_repo.get_count()
        if total_count >= checkpoint["effort_last"] + checkpoint["threshold"]:
            background_tasks.add_task(run_auto_optimization, "effort")
        if total_count >= checkpoint["risk_last"] + checkpoint["threshold"]:
            background_tasks.add_task(run_auto_optimization, "risk")
        return {"status": "feedback_saved", "total_samples": total_count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/config/export")
async def export_config(agent: str = Query("all", pattern="^(all|effort|risk)$")):
    result = {}
    if agent in ("all", "effort"):
        result["effort"] = effort_agent.config
    if agent in ("all", "risk"):
        result["risk"] = risk_agent.config
    return result

@app.post("/config/import")
async def import_config(payload: ConfigImportRequest, agent: str = Query("all", pattern="^(all|effort|risk)$")):
    try:
        required = {"universes", "antecedents", "consequent", "rules"}
        if not required.issubset(payload.config.keys()):
            raise ValueError("Missing required config sections")
        if agent in ("all", "effort"):
            with open("configs/effort_config.json", "w") as f:
                json.dump(payload.config, f, indent=2, ensure_ascii=False)
            effort_agent.config = payload.config
            effort_agent.rebuild()
        if agent in ("all", "risk"):
            with open("configs/risk_config.json", "w") as f:
                json.dump(payload.config, f, indent=2, ensure_ascii=False)
            risk_agent.config = payload.config
            risk_agent.rebuild()
        return {"status": "config_imported", "reloaded_agents": agent}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")

@app.get("/metrics")
async def get_metrics():
    total = feedback_repo.get_count()
    eff_hist = effort_agent.feedback_history
    risk_hist = risk_agent.feedback_history
    return {
        "total_feedback": total,
        "next_optimization_in": max(0, checkpoint["threshold"] - (total - max(checkpoint["effort_last"], checkpoint["risk_last"]))),
        "effort": FuzzyOptimizer(effort_agent)._compute_metrics(eff_hist) if eff_hist else {"mae": 0, "rmse": 0, "spearman_rho": 0},
        "risk": FuzzyOptimizer(risk_agent)._compute_metrics(risk_hist) if risk_hist else {"mae": 0, "rmse": 0, "spearman_rho": 0}
    }

@app.post("/dev/generate-synthetic-feedback", include_in_schema=False)
async def generate_synthetic_feedback():
    if os.getenv("FUZZY_DEV_MODE", "false").lower() != "true":
        raise HTTPException(status_code=403, detail="Endpoint disabled. Set FUZZY_DEV_MODE=true.")
    result = feedback_repo.generate_synthetic_feedback()
    return {"status": "completed", **result}

@app.post("/optimize", response_model=OptimizationResponse)
async def trigger_optimization(payload: OptimizationRequest = OptimizationRequest()):
    logger.info(f"[API-OPT] Received request: agent={payload.agent}, method={payload.method}, n_trials={payload.n_trials}, timeout={payload.timeout}")
    
    results: Dict[str, Union[OptimizationResultSuccess, OptimizationResultSkipped, OptimizationResultFailed]] = {}
    agents = ["effort", "risk"] if payload.agent == "all" else [payload.agent]
    
    for agent_name in agents:
        logger.info(f"[API-OPT] Processing agent: {agent_name}")
        try:
            agent = effort_agent if agent_name == "effort" else risk_agent
            tuner = effort_tuner if agent_name == "effort" else risk_tuner
            available_samples = feedback_repo.get_count()
            logger.debug(f"[API-OPT] {agent_name}: available samples={available_samples}")
            
            if available_samples < payload.min_samples and not payload.force:
                results[agent_name] = OptimizationResultSkipped(
                    status="skipped",
                    reason=f"Insufficient samples: {available_samples} < {payload.min_samples}",
                    available_samples=available_samples
                )
                continue
            
            training_data = feedback_repo.get_training_data(agent_name, limit=500)
            if len(training_data) < payload.min_samples and not payload.force:
                results[agent_name] = OptimizationResultSkipped(
                    status="skipped",
                    reason=f"Insufficient training data: {len(training_data)} < {payload.min_samples}",
                    available_samples=len(training_data)
                )
                continue
            
            agent.feedback_history = training_data
            
            result = tuner.optimize_with_method_selection(
                min_samples=payload.min_samples,
                preferred_method=payload.method,
                n_trials_per_method=payload.n_trials,
                timeout_per_method=payload.timeout
            )
            
            if "error" in result:
                logger.warning(f"[API-OPT] {agent_name}: optimization returned error: {result['error']}")
                results[agent_name] = OptimizationResultFailed(
                    status="failed",
                    error=result["error"],
                    method_used=result.get("selected_method")
                )
            else:
                agent.save_config()
                checkpoint[f"{agent_name}_last"] = available_samples
                save_checkpoint(checkpoint)
                results[agent_name] = OptimizationResultSuccess(
                    status="success",
                    method_used=result["selected_method"],
                    metrics=OptimizationMetrics(
                        mae=round(result["metrics"]["mae"], 4),
                        rmse=round(result["metrics"]["rmse"], 4),
                        spearman_rho=round(result["metrics"]["spearman_rho"], 4)
                    ),
                    samples_used=len(training_data),
                    config_updated=True
                )
                logger.success(f"[API-OPT] {agent_name}: optimization completed successfully")
        except Exception as e:
            logger.error(f"[API-OPT] {agent_name}: unexpected error: {e}", exc_info=True)
            results[agent_name] = OptimizationResultFailed(status="error", error=str(e))
    
    success_count = sum(1 for r in results.values() if getattr(r, "status", None) == "success")
    overall_status = "completed" if success_count == len(agents) else "partial" if success_count > 0 else "failed"
    
    return OptimizationResponse(
        status=overall_status,
        agents_processed=len(agents),
        success_count=success_count,
        results=results,
        checkpoint_updated=checkpoint
    )
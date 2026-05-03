from fastapi import FastAPI, HTTPException
from schemas import TaskInput, TaskOutput
from engine import fuzzy_engine
from knowledge import TASK_TYPE_WEIGHTS, MITIGATION_STRATEGIES
from datetime import datetime
import numpy as np

app = FastAPI(title="Fuzzy Complexity & Risk Agent", version="1.0.0")

@app.post("/evaluate", response_model=TaskOutput)
async def evaluate_task(payload: TaskInput):
    try:
        inputs = {
            "volume": payload.code_changes_lines,
            "dependencies": payload.dependencies_count,
            "expertise": payload.team_expertise,
            "uncertainty": payload.requirement_uncertainty_pct
        }
        result = fuzzy_engine.evaluate(inputs)

        weight = TASK_TYPE_WEIGHTS.get(payload.task_type, 1.0)
        complexity = float(np.clip(result["complexity_score"] * weight, 0, 100))
        risk = float(np.clip(result["risk_score"] * weight, 0, 100))

        if risk < 35:
            category = "Low"
        elif risk < 60:
            category = "Medium"
        elif risk < 80:
            category = "High"
        else:
            category = "Critical"

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
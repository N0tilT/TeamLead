from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uuid
from agent import Coordinator
from models import AnalysisResult, ChangeRequest

app = FastAPI(title="Team Manager AI Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

coordinator = Coordinator()

@app.post("/api/analyze", response_model=AnalysisResult)
async def analyze_changes(change_request: ChangeRequest):
    try:
        result = await coordinator.process_changes(change_request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uuid
import os 
from dotenv import load_dotenv 

from agent import Coordinator
from models import AnalysisResult, ChangeRequest
from llm_service import YandexGPTService
from tracker_service import YandexTrackerService

load_dotenv()

app = FastAPI(title="Team Manager AI Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

print(os.getenv("YANDEX_API_KEY", "YOUR_YANDEX_API_KEY"))
print(os.getenv("YANDEX_FOLDER_ID", "YOUR_FOLDER_ID"))
print(os.getenv("YANDEX_CLOUD_MODEL","yandexgpt-lite/rc"))
print(os.getenv("YANDEX_OAUTH_TOKEN", "YOUR_OAUTH_TOKEN"))
print(os.getenv("YANDEX_ORG_ID", "YOUR_ORG_ID"))
print(os.getenv("YANDEX_QUEUE_KEY", "YOUR_QUEUE_KEY"))

llm_service = YandexGPTService(
    api_key=os.getenv("YANDEX_API_KEY", "YOUR_YANDEX_API_KEY"),
    folder_id=os.getenv("YANDEX_FOLDER_ID", "YOUR_FOLDER_ID"),
    model=os.getenv("YANDEX_CLOUD_MODEL","yandexgpt-lite/rc"),
    is_async=True
)
tracker_service = YandexTrackerService(
    oauth_token=os.getenv("YANDEX_OAUTH_TOKEN", "YOUR_OAUTH_TOKEN"),
    org_id=os.getenv("YANDEX_ORG_ID", "YOUR_ORG_ID"),
    queue_key=os.getenv("YANDEX_QUEUE_KEY", "YOUR_QUEUE_KEY")
)
coordinator = Coordinator(llm_service, tracker_service)

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
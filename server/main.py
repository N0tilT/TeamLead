from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uuid
import os 
from dotenv import load_dotenv 
import redis.asyncio as redis
import json
import asyncio

from models import ChangeRequest
from llm_service import YandexGPTService
from tracker_service import YandexTrackerService
from agent import Coordinator

load_dotenv()

app = FastAPI(title="Team Manager AI Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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

redis_conn = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
coordinator = Coordinator(llm_service, tracker_service, redis_conn)
ANALYSIS_CHANNEL = "analysis_result"

@app.post("/api/enqueue")
async def enqueue_change(change_request: ChangeRequest):
    tracking_id = str(uuid.uuid4())
    payload = json.dumps({"tracking_id": tracking_id, "change": change_request.dict()})
    await redis_conn.rpush("doc_queue", payload)
    await redis_conn.publish("new_doc", json.dumps({"tracking_id": tracking_id}))
    return {"status": "enqueued", "tracking_id": tracking_id}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

@app.websocket("/ws/{tracking_id}")
async def websocket_endpoint(websocket: WebSocket, tracking_id: str):
    await websocket.accept()
    
    pubsub = redis_conn.pubsub()
    await pubsub.subscribe(ANALYSIS_CHANNEL)
    
    try:
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    if data.get('tracking_id') == tracking_id:
                        await websocket.send_text(data.get("result", ""))
                except json.JSONDecodeError:
                    continue
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(ANALYSIS_CHANNEL)
        await pubsub.close()

@app.on_event("startup")
async def startup_event():
    await redis_conn.publish(ANALYSIS_CHANNEL, json.dumps({
        "result": "Server started", 
        "tracking_id": "system"
    }))
    print("Server started, Redis connected")

@app.on_event("shutdown")
async def shutdown_event():
    await coordinator.close()
    await redis_conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
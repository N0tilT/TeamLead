import asyncio
import json
import os
from loguru import logger
import redis.asyncio as redis
from agent import Coordinator
from models import ChangeRequest
from llm_service import YandexGPTService
from tracker_service import YandexTrackerService
from dotenv import load_dotenv 

from database import DatabaseConfig,DatabaseConnection
from migrations import MigrationManager
from analysis_repository import AnalysisRepository

db_config= DatabaseConfig(
    'teamlead-analysis',
    'postgres',
    'postgres',
    '123Secret_a',
    5432
)
db_connection = DatabaseConnection(db_config)
repository = AnalysisRepository(db_connection)

load_dotenv()

logger.add("logs/analysis_worker.log", level="DEBUG", rotation="1 MB")

llm_service = YandexGPTService(
    api_key=os.getenv("YANDEX_API_KEY"),
    folder_id=os.getenv("YANDEX_FOLDER_ID"),
    model=os.getenv("YANDEX_CLOUD_MODEL", "yandexgpt-lite/rc"),
    is_async=True
)
tracker_service = YandexTrackerService(
    oauth_token=os.getenv("YANDEX_OAUTH_TOKEN"),
    org_id=os.getenv("YANDEX_ORG_ID"),
    queue_key=os.getenv("YANDEX_QUEUE_KEY")
)
redis_conn = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
coordinator = Coordinator(llm_service, tracker_service, redis_conn)

DOC_QUEUE = "doc_queue"
NEW_DOC_CHANNEL = "new_doc"
NEW_TASK_CHANNEL = "new_task"
ANALYSIS_CHANNEL = "analysis_result"
async def process_doc_from_message(message_data):
    """Обработать конкретное сообщение, полученное из канала"""
    data = json.loads(message_data)
    logger.info(f"START PROCESSING doc {data}")
    change = ChangeRequest(**data["change"])
    tracking_id = data["tracking_id"]
    logger.info(f"START PROCESSING doc {tracking_id}")
    
    try:
        result = await coordinator.process_changes(change)
        result_json = result.model_dump_json()
        
        await redis_conn.setex(f"result:{tracking_id}", 3600, result_json)
        
        for tracker_id in result.tracker_ids:
            await redis_conn.publish(NEW_TASK_CHANNEL, json.dumps({"issue_key": tracker_id, "tracking_id": tracking_id}))
        
        await redis_conn.publish(ANALYSIS_CHANNEL, json.dumps({"result": result_json, "tracking_id": tracking_id}))
        repository.create_analysis(analysis=result, tracking_id=tracking_id)
        logger.info(f"Processed doc {tracking_id}")
        return True
    except Exception as e:
        await redis_conn.rpush(DOC_QUEUE, message_data)
        logger.error(f"Failed doc {tracking_id}: {e}")
        return False

async def main():
    pubsub = redis_conn.pubsub()
    await pubsub.subscribe(NEW_DOC_CHANNEL)
    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True)
        if message:
            await process_doc_from_message(message['data'])
        
        serialized = await redis_conn.lpop(DOC_QUEUE)
        if serialized:
            await process_doc_from_message(serialized)
        
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
import asyncio
import json
import os
from loguru import logger
import redis.asyncio as redis
import json
import asyncio
from agent import Coordinator
from models import ChangeRequest
from llm_service import YandexGPTService
from tracker_service import YandexTrackerService

from dotenv import load_dotenv 
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
redis = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
coordinator = Coordinator(llm_service, tracker_service, redis)

DOC_QUEUE = "doc_queue"
NEW_DOC_CHANNEL = "new_doc"
NEW_TASK_CHANNEL = "new_task"
ANALYSIS_CHANNEL = "analysis_result"

async def process_one_doc():
    serialized = await redis.lpop(DOC_QUEUE)
    if serialized:
        data = json.loads(serialized)
        change = ChangeRequest(**data["change"])
        tracking_id = data["tracking_id"]
        try:
            result = await coordinator.process_changes(change)
            for tracker_id in result.tracker_ids:
                await redis.publish(NEW_TASK_CHANNEL, json.dumps({"issue_key": tracker_id, "tracking_id": tracking_id}))
            await redis.publish(ANALYSIS_CHANNEL,json.dumps({"result":result.model_dump_json(),"tracking_id": tracking_id}))
            logger.info(f"Processed doc {tracking_id}, published {len(result.tracker_ids)} tasks")
            return True
        except Exception as e:
            await redis.rpush(DOC_QUEUE, serialized)
            logger.error(f"Failed doc {tracking_id}: {e}")
    return False

async def main():
    pubsub = redis.pubsub()
    await pubsub.subscribe(NEW_DOC_CHANNEL)
    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True)
        if message:
            logger.info("New doc event, processing one...")
            await process_one_doc()
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
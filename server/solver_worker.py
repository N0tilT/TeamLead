import asyncio
import json
import os
from loguru import logger
import redis.asyncio as redis
import json
import asyncio
from agent import SolverAgent
from models import Task
from llm_service import YandexGPTService
from tracker_service import YandexTrackerService
from typing import List, Dict, Any

from dotenv import load_dotenv 
load_dotenv()

logger.add("logs/solver_worker.log", level="DEBUG", rotation="1 MB")

STYLE = os.getenv("SOLVER_STYLE", "balanced")

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
solver = SolverAgent(llm_service, STYLE)
redis = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

TASK_QUEUE = "task_queue"
NEW_TASK_CHANNEL = "new_task"
SOLUTION_CHANNEL = "solution_generated"

async def process_task_from_event(data: Dict):
    issue_key = data["issue_key"]
    processed_key = f"processed_tasks:{STYLE}:{issue_key}"
    if await redis.exists(processed_key):
        logger.debug(f"Skipping duplicate for {issue_key} in {STYLE}")
        return False
    await redis.set(processed_key, "1", ex=3600)

    issue = await tracker_service.get_issue(issue_key)
    if not issue:
        return False
    task = Task(
        id=issue["id"],
        title=issue["summary"],
        description=issue["description"],
        task_type=issue.get("type", {}).get("key", "task"),
        acceptance_criteria=[],
        priority=issue.get("priority", {}).get("key", "normal")
    )
    try:
        solution = await solver.generate_solution(task)
        await redis.publish(SOLUTION_CHANNEL, json.dumps({"issue_key": issue_key, "style": STYLE, "solution": solution}))
        logger.info(f"Generated solution for {issue_key} with style {STYLE}")
        return True
    except Exception as e:
        logger.error(f"Failed solver for {issue_key}: {e}")
        await redis.delete(processed_key)
    return False

async def main():
    pubsub = redis.pubsub()
    await pubsub.subscribe(NEW_TASK_CHANNEL)
    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True)
        if message:
            try:
                data = json.loads(message["data"])
                logger.info(f"New task event for {data['issue_key']}, processing with style {STYLE}...")
                await process_task_from_event(data)
            except Exception as e:
                logger.error(f"Error processing event: {e}")
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
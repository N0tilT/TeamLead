import asyncio
import json
import os
from loguru import logger
import redis.asyncio as redis
import json
import asyncio

from agent import EvaluatorAgent
from models import Task
from llm_service import YandexGPTService
from tracker_service import YandexTrackerService

from dotenv import load_dotenv 
load_dotenv()

logger.add("logs/evaluator_worker.log", level="DEBUG", rotation="1 MB")

NUM_SOLVERS = int(os.getenv("NUM_SOLVERS", 3))

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
evaluator = EvaluatorAgent(llm_service)
redis = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

NEW_TASK_CHANNEL = "new_task"
SOLUTION_CHANNEL = "solution_generated"

async def process_solutions(issue_key: str):
    solutions_key = f"solutions:{issue_key}"
    solutions = await redis.lrange(solutions_key, 0, -1)
    unique_solutions = list(set(solutions)) 
    if len(unique_solutions) == NUM_SOLVERS:
        issue = await tracker_service.get_issue(issue_key)
        task = Task(
            id=issue["id"],
            title=issue["summary"],
            description=issue["description"],
            task_type=issue.get("type", {}).get("key", "task"),
            acceptance_criteria=[],
            priority=issue.get("priority", {}).get("key", "normal")
        )
        solutions_list = [json.loads(s) for s in unique_solutions]
        best_solution = await evaluator.evaluate_solutions(task, [s["solution"] for s in solutions_list])
        if "Ошибка оценки" in best_solution:
            await redis.publish(NEW_TASK_CHANNEL, json.dumps({"issue_key": issue_key}))
            return
        new_description = f"{task.description}\n\n{best_solution}"
        updated = await tracker_service.update_issue(issue_key, new_description)
        if updated:
            await redis.delete(solutions_key)
            logger.success(f"Evaluated and updated {issue_key}")
        else:
            logger.warning(f"Failed update for {issue_key}, keeping solutions")

async def main():
    pubsub = redis.pubsub()
    await pubsub.subscribe(SOLUTION_CHANNEL)
    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True)
        if message:
            data = json.loads(message["data"])
            issue_key = data["issue_key"]
            solutions_key = f"solutions:{issue_key}"
            existing = await redis.lrange(solutions_key, 0, -1)
            if any(json.loads(s)["style"] == data["style"] for s in existing):
                logger.debug(f"Skipping duplicate solution for {issue_key} style {data['style']}")
                continue
            await redis.rpush(solutions_key, json.dumps(data))
            await redis.expire(solutions_key, 3600)
            await process_solutions(issue_key)
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
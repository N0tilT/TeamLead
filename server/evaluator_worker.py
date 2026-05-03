import asyncio
import json
import os
import re
from loguru import logger
import redis.asyncio as redis

from agent import EvaluatorAgent
from models import Task
from llm_service import YandexGPTService
from tracker_service import YandexTrackerService
from fuzzy_client import FuzzyLogicClient

from dotenv import load_dotenv 
load_dotenv()

logger.add("logs/evaluator_worker.log", level="DEBUG", rotation="1 MB")

NUM_SOLVERS = int(os.getenv("NUM_SOLVERS", 3))
FUZZY_API_URL = os.getenv("FUZZY_API_URL", "http://localhost:8000")

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
fuzzy_client = FuzzyLogicClient(base_url=FUZZY_API_URL)
evaluator = EvaluatorAgent(llm_service)
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

SOLUTION_CHANNEL = "solution_generated"
NEW_TASK_CHANNEL = "new_task"

def _extract_field_value(field_value, default="unknown"):
    """Извлекает значение из поля, которое может быть строкой или словарём."""
    if isinstance(field_value, dict):
        return field_value.get("name") or field_value.get("key", default)
    elif isinstance(field_value, str) and field_value:
        return field_value
    return default

def _extract_code_lines(description: str) -> float:
    """Извлекает количество строк кода из описания."""
    match = re.search(r'(\d+)\s*(?:строк?|lines?)', description, re.I)
    return float(match.group(1)) if match else 100.0

def _count_dependencies(description: str) -> int:
    """Подсчитывает количество зависимостей в описании."""
    matches = re.findall(r'(?:зависимост[ья]|dependency|module|component)[\s:]*(\d+)', description, re.I)
    return int(matches[0]) if matches else 3

def _estimate_uncertainty(description: str) -> float:
    """Оценивает неопределённость требований по ключевым словам."""
    uncertainty_keywords = [
        'неясно', 'требует уточнения', 'возможно', 'может быть', 
        'потенциально', 'unclear', 'TBD', 'to be defined'
    ]
    count = sum(1 for kw in uncertainty_keywords if kw.lower() in description.lower())
    return min(100.0, count * 15.0)

def _map_task_type_to_fuzzy(task_type: str) -> str:
    """Маппинг типов задач для fuzzy-клиента."""
    mapping = {
        "bug": "bugfix",
        "task": "feature",
        "test": "feature",
        "subtask": "feature"
    }
    return mapping.get(task_type.lower(), "feature")

async def process_solutions(issue_key: str):
    """Обрабатывает накопленные решения, когда собрано нужное количество."""
    solutions_key = f"solutions:{issue_key}"
    solutions = await redis_client.lrange(solutions_key, 0, -1)
    unique_solutions = list(set(solutions))
    
    if len(unique_solutions) == NUM_SOLVERS:
        issue = tracker_service.get_issue(issue_key)
        if not issue:
            logger.warning(f"Issue {issue_key} not found, skipping evaluation")
            return
            
        task = Task(
            id=issue.get("id") or issue_key,
            title=issue.get("summary", "No title"),
            description=issue.get("description", ""),
            task_type=_extract_field_value(issue.get("type"), default="task").lower(),
            acceptance_criteria=[],
            priority=_extract_field_value(issue.get("priority"), default="normal").lower()
        )
        
        # === Fuzzy Logic Evaluation ===
        fuzzy_result = None
        if await fuzzy_client.health_check():
            try:
                fuzzy_result = await fuzzy_client.evaluate_task(
                    task_id=issue_key,
                    code_changes_lines=_extract_code_lines(issue.get("description", "")),
                    dependencies_count=_count_dependencies(issue.get("description", "")),
                    team_expertise=float(os.getenv("DEFAULT_TEAM_EXPERTISE", 3.5)),
                    requirement_uncertainty_pct=_estimate_uncertainty(issue.get("description", "")),
                    task_type=_map_task_type_to_fuzzy(task.task_type)
                )
                logger.debug(f"Fuzzy result for {issue_key}: {fuzzy_result}")
            except Exception as e:
                logger.error(f"Fuzzy evaluation failed for {issue_key}: {e}", exc_info=True)
        else:
            logger.warning(f"Fuzzy client not available for {issue_key}")
        # ===============================
        
        solutions_list = [json.loads(s) for s in unique_solutions]
        best_solution = await evaluator.evaluate_solutions(
            task, 
            [s["solution"] for s in solutions_list]
        )
        
        if "Ошибка оценки" in best_solution:
            logger.warning(f"Evaluation error for {issue_key}, retrying...")
            await redis_client.publish(NEW_TASK_CHANNEL, json.dumps({"issue_key": issue_key}))
            return
        
        if fuzzy_result:
            new_description = f"{task.description}\nОбработка с помощью нечёткой логики:\n- Оценка сложности {fuzzy_result["complexity_score"]}\n- Оценка рисков {fuzzy_result["risk_score"]}\n- Уровень риска: {fuzzy_result["risk_category"]}\n- Действия для снижения рисков: {fuzzy_result["mitigation_strategies"]}\n\n\n{best_solution}"
        else:
            new_description = f"{task.description}\n\n{best_solution}"
        updated = tracker_service.update_issue(issue_key, new_description, fuzzy_result)
        
        if updated:
            await redis_client.delete(solutions_key)
            logger.success(f"Evaluated and updated {issue_key} (fuzzy_risk={fuzzy_result.get('risk_category') if fuzzy_result else 'N/A'})")
        else:
            logger.warning(f"Failed to update {issue_key}, keeping solutions for retry")

async def main():
    """Основной цикл: подписка на канал решений, дедупликация, запуск оценки."""
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(SOLUTION_CHANNEL)
    
    logger.info(f"Evaluator started, waiting for {NUM_SOLVERS} solutions per task")
    
    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True)
        if message:
            try:
                data = json.loads(message["data"])
                issue_key = data["issue_key"]
                style = data.get("style", "unknown")
                solutions_key = f"solutions:{issue_key}"
                
                # Проверка на дубликаты по стилю
                existing = await redis_client.lrange(solutions_key, 0, -1)
                if any(json.loads(s).get("style") == style for s in existing):
                    logger.debug(f"Skipping duplicate solution for {issue_key} style {style}")
                    continue
                
                # Сохраняем решение в список
                await redis_client.rpush(solutions_key, json.dumps(data))
                await redis_client.expire(solutions_key, 3600)  # TTL 1 час
                
                # Пробуем обработать, если набралось нужное количество
                await process_solutions(issue_key)
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse message data: {e}")
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
        await asyncio.sleep(0.1)  # Небольшая пауза для снижения нагрузки

if __name__ == "__main__":
    asyncio.run(main())
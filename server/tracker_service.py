import aiohttp
import json
from loguru import logger
from models import Task

class YandexTrackerService:
    def __init__(self, oauth_token: str, org_id: str, queue_key: str = "TREK", base_url: str = "https://api.tracker.yandex.net/v3"):
        self.oauth_token = oauth_token
        self.org_id = org_id
        self.queue_key = queue_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"OAuth {self.oauth_token}",
            "X-Org-ID": self.org_id,
            "Content-Type": "application/json"
        }

    async def create_issue(self, task: Task) -> str | None:
        """Создание задачи в YandexTracker на основе сгенерированной Task"""
        payload = {
            "summary": task.title,
            "queue": self.queue_key,
            "description": task.description,
            "type": self._map_task_type(task.task_type),
            "priority": task.priority.lower(),
            "markupType": "md" if "markdown" in task.description.lower() else None,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/issues/", headers=self.headers, json=payload) as response:
                if response.status == 201:
                    data = await response.json()
                    issue_key = data.get("key")
                    logger.success(f"Created issue {issue_key} for task {task.id}")
                    return issue_key
                else:
                    error = await response.text()
                    logger.error(f"Failed to create issue: {response.status} - {error}")
                    return None

    def _map_task_type(self, task_type: str) -> str:
        """Маппинг типов задач из внутренней модели в YandexTracker"""
        mapping = {
            "Development": "task",
            "Refactoring": "task",
            "Testing": "test",
            "Documentation": "task",
            "Bugfix": "bug"
        }
        return mapping.get(task_type, "task")
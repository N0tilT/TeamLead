import aiohttp
import json
import datetime
from loguru import logger
from models import Task
from typing import List, Dict, Any

class YandexTrackerService:
    def __init__(self, oauth_token: str, org_id: str, queue_key: str = "TREK", base_url: str = "https://api.tracker.yandex.net/v3"):
        self.oauth_token = oauth_token
        self.org_id = org_id
        self.queue_key = queue_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"OAuth {self.oauth_token}",
            "X-Cloud-Org-ID": self.org_id,
            "Content-Type": "application/json"
        }

    async def create_issue(self, task: Task) -> str | None:
        payload = {
            "summary": task.title,
            "queue": self.queue_key,
            "description": task.description + f"\nКритерии приёмки:\n{"\n".join(task.acceptance_criteria)}",
            "type": self._map_task_type(task.task_type),
            "priority": task.priority.lower(),
            "markupType": "md",
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
        mapping = {
            "Development": "task",
            "Refactoring": "task",
            "Testing": "test",
            "Documentation": "task",
            "Bugfix": "bug"
        }
        return mapping.get(task_type, "task")

    async def get_recent_issues(self, limit: int = 10, since_days: int = 1) -> List[Dict[str, Any]]:
        since = (datetime.datetime.now() - datetime.timedelta(days=since_days)).strftime("%Y-%m-%d")
        payload = {
            "filter": {
                "queue": self.queue_key,
                "created": f">={since}"
            },
            "perPage": limit
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/issues/_search", headers=self.headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Fetched {len(data)} recent issues")
                    return data
                else:
                    error = await response.text()
                    logger.error(f"Failed to fetch issues: {response.status} - {error}")
                    return []

    async def update_issue(self, issue_key: str, new_description: str) -> bool:
        payload = {
            "description": new_description,
            "markupType": "md"
        }
        async with aiohttp.ClientSession() as session:
            async with session.patch(f"{self.base_url}/issues/{issue_key}", headers=self.headers, json=payload) as response:
                if response.status == 200:
                    logger.success(f"Updated issue {issue_key}")
                    return True
                else:
                    error = await response.text()
                    logger.error(f"Failed to update issue {issue_key}: {response.status} - {error}")
                    return False

    async def get_issue(self, issue_key: str) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/issues/{issue_key}", headers=self.headers) as response:
                if response.status == 200:
                    logger.success(f"Get task {response.json()}")
                    return await response.json()
                else:
                    logger.error(f"Failed to get issue {issue_key}")
                    return {}
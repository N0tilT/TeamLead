import datetime
from loguru import logger
from models import Task
from typing import List, Dict, Any, Optional

from yandex_tracker_client import TrackerClient
from yandex_tracker_client.exceptions import NotFound


class YandexTrackerService:
    """
    Сервис для работы с Yandex Tracker через официальный клиент.
    
    Примечание: библиотека yandex_tracker_client является синхронной.
    При использовании в async-контексте вызовы методов можно оборачивать
    через asyncio.to_thread() или запускать в executor.
    """

    def __init__(self, oauth_token: str, org_id: str, queue_key: str = "TREK"):
        """
        Инициализация сервиса.
        
        Args:
            oauth_token: OAuth 2.0 токен для авторизации
            org_id: ID организации (для Yandex Cloud используется cloud_org_id)
            queue_key: Ключ очереди по умолчанию (по умолчанию: "TREK")
        """
        self.oauth_token = oauth_token
        self.org_id = org_id
        self.queue_key = queue_key
        # Для Yandex Cloud организаций используется параметр cloud_org_id
        self.client = TrackerClient(token=oauth_token, cloud_org_id=org_id)

    def create_issue(self, task: Task, fuzzy_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Создание новой задачи в Yandex Tracker.
        
        Args:
            task: Объект Task с данными для задачи
            fuzzy_data: Опциональные данные нечёткой логики
            
        Returns:
            Ключ созданной задачи (например, "TREK-123") или None при ошибке
        """
        description = task.description
        if task.acceptance_criteria:
            description += f"\n\nКритерии приёмки:\n" + "\n".join(f"- {c}" for c in task.acceptance_criteria)
        
        if fuzzy_data:
            description += f"\n\nОценка сложности (нечёткая логика): {fuzzy_data['complexity_score']}/100"
            description += f"\nУровень риска: {fuzzy_data['risk_category']} (score: {fuzzy_data['risk_score']}/100)"
            if fuzzy_data.get('mitigation_strategies'):
                description += f"\nРекомендации: {', '.join(fuzzy_data['mitigation_strategies'])}"
        
        payload = {
            "queue": self.queue_key,
            "summary": task.title,
            "description": description,
            "type": {"name": self._map_task_type(task.task_type)},
            "markupType": "md",
        }
        
        # Приоритет: из fuzzy_data или из task
        if fuzzy_data:
            payload["priority"] = self._map_priority(fuzzy_data['risk_category'])
        else:
            payload["priority"] = task.priority.lower()
        
        try:
            issue = self.client.issues.create(**payload)
            logger.success(f"Created issue {issue.key} for task {task.id}")
            return issue.key
        except Exception as e:
            logger.error(f"Failed to create issue: {e}")
            return None

    def _map_task_type(self, task_type: str) -> str:
        """Маппинг внутренних типов задач на типы Yandex Tracker."""
        mapping = {
            "Development": "Задача",
            "Refactoring": "Задача",
            "Testing": "Задача",
            "Documentation": "Задача",
            "Bugfix": "Ошибка"
        }
        return mapping.get(task_type, "Задача")

    def _map_priority(self, risk_category: str) -> str:
        """Маппинг категорий риска на приоритеты Yandex Tracker."""
        mapping = {
            "Low": "minor",
            "Medium": "normal",
            "High": "critical",
            "Critical": "critical"
        }
        return mapping.get(risk_category, "normal")

    def get_recent_issues(self, limit: int = 10, since_days: int = 1) -> List[Dict[str, Any]]:
        """
        Получение недавних задач из очереди.
        
        Args:
            limit: Максимальное количество задач
            since_days: Период в днях для фильтрации по дате создания
            
        Returns:
            Список словарей с данными задач
        """
        since = (datetime.datetime.now() - datetime.timedelta(days=since_days)).strftime("%Y-%m-%d")
        try:
            issues = self.client.issues.find(
                filter={'queue': self.queue_key, 'created': {'from': since}},
                per_page=limit
            )
            result = [self._issue_to_dict(issue) for issue in issues]
            logger.info(f"Fetched {len(result)} recent issues")
            return result
        except Exception as e:
            logger.error(f"Failed to fetch issues: {e}")
            return []

    def _issue_to_dict(self, issue) -> Dict[str, Any]:
        """Конвертация объекта задачи Tracker в словарь."""
        # Попытка получить внутренние данные (зависит от версии библиотеки)
        if hasattr(issue, '_data') and isinstance(issue._data, dict):
            return issue._data
        # Fallback: сборка словаря из основных атрибутов
        return {
            'key': getattr(issue, 'key', None),
            'summary': getattr(issue, 'summary', None),
            'description': getattr(issue, 'description', None),
            'status': getattr(issue, 'status', None) if not hasattr(getattr(issue, 'status', None), 'name') 
                     else getattr(issue.status, 'name', None),
            'priority': getattr(issue, 'priority', None) if not hasattr(getattr(issue, 'priority', None), 'name')
                       else getattr(issue.priority, 'name', None),
            'createdAt': getattr(issue, 'createdAt', None),
            'updatedAt': getattr(issue, 'updatedAt', None),
            'type': getattr(issue, 'type', None) if not hasattr(getattr(issue, 'type', None), 'name')
                   else getattr(issue.type, 'name', None),
        }

    def update_issue(self, issue_key: str, new_description: str, fuzzy_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Обновление существующей задачи.
        
        Args:
            issue_key: Ключ задачи в Tracker (например, "TREK-123")
            new_description: Новое описание
            fuzzy_data: Опциональные обновлённые данные нечёткой логики
            
        Returns:
            True при успешном обновлении, False при ошибке
        """
        try:
            issue = self.client.issues[issue_key]
            payload = {"description": new_description}
            issue.update(**payload)
            logger.success(f"Updated issue {issue_key}")
            return True
        except NotFound:
            logger.error(f"Issue {issue_key} not found")
            return False
        except Exception as e:
            logger.error(f"Failed to update issue {issue_key}: {e}")
            return False

    def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """
        Получение задачи по ключу.
        
        Args:
            issue_key: Ключ задачи в Tracker (например, "TREK-123")
            
        Returns:
            Словарь с данными задачи или пустой словарь, если задача не найдена
        """
        try:
            issue = self.client.issues[issue_key]
            logger.success(f"Got issue {issue.key}")
            return self._issue_to_dict(issue)
        except NotFound:
            logger.error(f"Issue {issue_key} not found")
            return {}
        except Exception as e:
            logger.error(f"Failed to get issue {issue_key}: {e}")
            return {}
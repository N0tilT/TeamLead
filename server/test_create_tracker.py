from tracker_service import YandexTrackerService
from models import Task
import os
import asyncio
import uuid
from dotenv import load_dotenv

load_dotenv()

# Инициализация сервиса
tracker_service = YandexTrackerService(
    oauth_token=os.getenv("YANDEX_OAUTH_TOKEN", "YOUR_OAUTH_TOKEN"),
    org_id=os.getenv("YANDEX_ORG_ID", "YOUR_ORG_ID"),
    queue_key=os.getenv("YANDEX_QUEUE_KEY", "TREK")
)


async def main():
    task = Task(
        id=str(uuid.uuid4()),
        title="🧪 Тестовая задача из скрипта",
        description="Это тестовое описание задачи, созданной через yandex_tracker_client.\n\nПроверяем работу метода create_issue.",
        task_type="Development",
        acceptance_criteria=[
            "Задача успешно создана в Tracker",
            "Описание отображается в Markdown",
            "Приоритет установлен корректно"
        ],
        priority="High"
    )
    fuzzy_data = {
        "complexity_score": 75,
        "risk_score": 40,
        "risk_category": "Medium",
        "mitigation_strategies": ["Добавить тесты", "Провести код-ревью"]
    }

    issue_key = await asyncio.to_thread(
        tracker_service.create_issue,
        task=task,
        fuzzy_data=fuzzy_data
    )

    if issue_key:
        print(f"✅ Задача успешно создана: {issue_key}")
        created = await asyncio.to_thread(tracker_service.get_issue, issue_key)
        print(f"📋 Summary: {created.get('summary')}")
        print(f"🎯 Priority: {created.get('priority')}")
        print(f"📦 Type: {created.get('type')}")
    else:
        print("❌ Не удалось создать задачу — проверьте логи и настройки авторизации")


if __name__ == "__main__":
    asyncio.run(main())
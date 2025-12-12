from tracker_service import YandexTrackerService
import os
import asyncio
from dotenv import load_dotenv 
load_dotenv()

tracker_service = YandexTrackerService(
    oauth_token=os.getenv("YANDEX_OAUTH_TOKEN", "YOUR_OAUTH_TOKEN"),
    org_id=os.getenv("YANDEX_ORG_ID", "YOUR_ORG_ID"),
    queue_key=os.getenv("YANDEX_QUEUE_KEY", "YOUR_QUEUE_KEY")
)

async def main():
    issue = await tracker_service.get_issue('SHARD-20')
    print(issue)

if __name__ == "__main__":
    asyncio.run(main())
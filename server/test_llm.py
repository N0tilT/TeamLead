import asyncio
import os
from loguru import logger
from llm_service import YandexGPTService
from models import ChangeRequest

def setup_global_logging():
    os.makedirs("logs", exist_ok=True)
    logger.remove()
    
    logger.add(
        sink=lambda msg: print(msg, end=""),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True
    )
    
    logger.add(
        sink="logs/app.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="1 MB",
        retention="10 days",
        compression="zip"
    )
    
    logger.add(
        sink="logs/errors.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="1 MB",
        retention="30 days"
    )
    
    logger.add(
        sink="logs/llm_responses.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | LLM_RESPONSE | {message}",
        level="INFO",
        rotation="1 MB",
        retention="10 days",
        filter=lambda record: "llm_response" in record["extra"]
    )

async def main():
    setup_global_logging()
    logger.info("Starting application main function")
    
    try:
        logger.info("Initializing YandexGPTService")
        service = YandexGPTService(
            api_key=YANDEX_CLOUD_API_KEY,
            folder_id=YANDEX_CLOUD_FOLDER,
        )

        change = ChangeRequest(
            old_text="Старое описание API...",
            new_text="Новое описание с поддержкой OAuth2 и JWT refresh tokens",
            comments="Срочно обновить все клиенты до новой версии"
        )
        logger.debug(f"Created ChangeRequest - Old text: {len(change.old_text)} chars, New text: {len(change.new_text)} chars")

        logger.info("Processing change request for AuthService")
        result = await service.process_change_full(change, affected_component="AuthService")
        logger.success(f"Change processing completed - Tasks created: {len(result.tasks)}")
        
        print(f"Создано задач: {len(result.tasks)}")
        for task in result.tasks:
            print(task.title)
            logger.debug(f"Generated task: {task.title} (Type: {task.task_type}, Priority: {task.priority})")

        logger.info("Generating summary report")
        report = await service.generate_summary_report(
            processed_changes=47,
            total_tasks_created=189,
            all_keywords=[result.keywords],
            period="последние 24 часа"
        )
        logger.success(f"Summary report generated - Length: {len(report)} chars")
        print(report)

        logger.info("Application completed successfully")
        
    except Exception as e:
        logger.error(f"Application failed with error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
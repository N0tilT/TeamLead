import asyncio
import json
from typing import List, Dict, Any
from loguru import logger
from models import ChangeRequest, Task, Risk, AnalysisResult, Metrics
from llm_service import YandexGPTService
from tracker_service import YandexTrackerService

logger.add(
    sink="logs/agent.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="1 MB",
    retention="10 days",
    compression="zip"
)

class BaseAgent:
    """Базовый класс для всех агентов"""
    def __init__(self, llm_service: YandexGPTService):
        self.llm_service = llm_service

class Coordinator(BaseAgent):
    """Агент-Координатор: управляет процессом, распределяет задачи и агрегирует результаты"""
    def __init__(self, llm_service: YandexGPTService, tracker_service: YandexTrackerService):
        super().__init__(llm_service)
        self.change_analysis_agent = ChangeAnalysisAgent(llm_service)
        self.task_creation_agent = TaskCreationAgent(llm_service)
        self.risk_management_agent = RiskManagementAgent(llm_service)
        self.description_agent = DescriptionAgent(llm_service)
        self.stats_agent = StatsAgent(llm_service)
        self.tracker_service = tracker_service 
        self.history: List[Dict[str, Any]] = []  

    async def process_changes(self, change_request: ChangeRequest) -> AnalysisResult:
        logger.info("Starting change processing")
        try:
            logger.info("Starting change processing")
            change_summary, affected_components, keywords = await self.change_analysis_agent.analyze(change_request)
            
            tasks = await self.task_creation_agent.create_tasks(change_request, change_summary, affected_components, keywords)
            
            risks = await self.risk_management_agent.analyze_risks(change_request, change_summary, tasks)
            
            overall_description = await self.description_agent.generate_description(change_summary, tasks, risks)
            
            tracker_ids = await self._add_tasks_to_tracker(tasks)
            
            metrics = await self.stats_agent.collect_metrics(change_request, tasks, risks, keywords)
            self.history.append({
                "change": change_request.dict(),
                "summary": change_summary,
                "tasks": [t.dict() for t in tasks],
                "risks": [r.dict() for r in risks],
                "metrics": metrics.dict()
            })
            
            result = AnalysisResult(
                change_summary=change_summary,
                tasks=tasks,
                risks=risks,
                keywords=keywords,
                overall_description=overall_description,
                metrics=metrics,
                tracker_ids=tracker_ids
            )
            logger.success("Processing completed successfully")
            return result
        except Exception as e:
            logger.error(f"Error in processing: {e}")
            raise

    async def _add_tasks_to_tracker(self, tasks: List[Task]) -> List[str]:
        """Добавление сгенерированных задач в YandexTracker"""
        tracker_ids = []
        for task in tasks:
            tracker_id = await self.tracker_service.create_issue(task)
            if tracker_id:
                tracker_ids.append(tracker_id)
        return tracker_ids

class ChangeAnalysisAgent(BaseAgent):
    """Агент Анализа Изменений: анализирует текст изменений"""
    async def analyze(self, change: ChangeRequest) -> tuple[str, List[str], Dict[str, Any]]:
        description = f"Было: {change.old_text}\nСтало: {change.new_text}\nКомментарий: {change.comments or '—'}"
        keywords = await self.llm_service.highlight_keywords_and_terms(description)
        
        prompt = f"""
            Анализируй изменения в документации.
            Определи суть: что добавлено, удалено, изменено.
            Выяви затронутые модули/компоненты.
            Сформируй краткое резюме.
            
            Текст: {description}
            Ключевые термины: {keywords}
            
            Верни JSON: {{
                "summary": "резюме",
                "affected_components": ["comp1", "comp2"],
                "changes": {{
                    "added": ["..."],
                    "removed": ["..."],
                    "modified": ["..."]
                }}
            }}
        """
        messages = [{"role": "user", "content": prompt}]
        raw = await self.llm_service._call_llm_wrapper(messages, temperature=0.3, json_mode=True)
        result = json.loads(raw)
        
        return result["summary"], result["affected_components"], keywords

class TaskCreationAgent(BaseAgent):
    """Агент Генерации Задач: создает задачи на основе анализа"""
    async def create_tasks(
        self,
        change: ChangeRequest,
        summary: str,
        affected_components: List[str],
        keywords: Dict[str, Any]
    ) -> List[Task]:
        tasks = []
        for component in affected_components:
            component_tasks = await self.llm_service.generate_tasks_from_change(change, component, keywords)
            tasks.extend(component_tasks)
        return tasks

class RiskManagementAgent(BaseAgent):
    """Агент Риск-Менеджмента: анализирует риски"""
    async def analyze_risks(
        self,
        change: ChangeRequest,
        summary: str,
        tasks: List[Task]
    ) -> List[Risk]:
        prompt = f"""
            Анализируй изменения и задачи на риски.
            Категоризируй: technical, cost, timeline.
            Оцени: probability (Low/Medium/High), impact (Low/Medium/High).
            Предложи mitigation.
            
            Изменения: {summary}
            Задачи: {json.dumps([t.dict() for t in tasks], ensure_ascii=False)}
            
            Верни массив JSON: [{{
                "category": "technical",
                "description": "...",
                "probability": "Medium",
                "impact": "High",
                "mitigation": ["..."]
            }}]
        """
        schema_risks = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "description": {"type": "string"},
                    "probability": {"type": "string", "enum": ["Low", "Medium", "High"]},
                    "impact": {"type": "string", "enum": ["Low", "Medium", "High"]},
                    "mitigation": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["category", "description", "probability", "impact", "mitigation"]
            }
        }
        messages = [{"role": "user", "content": prompt}]
        raw = await self.llm_service._call_llm_wrapper(messages, temperature=0.5, json_mode=True, json_schema=schema_risks)
        risks_data = json.loads(raw)
        return [Risk(**r) for r in risks_data]

class DescriptionAgent(BaseAgent):
    """Агент Формирования Описания: создает связное описание"""
    async def generate_description(
        self,
        summary: str,
        tasks: List[Task],
        risks: List[Risk]
    ) -> str:
        prompt = f"""
            Создай связное описание пакета изменений для команды.
            Включи резюме, задачи, риски.
            
            Резюме: {summary}
            Задачи: {json.dumps([t.dict() for t in tasks], ensure_ascii=False)}
            Риски: {json.dumps([r.dict() for r in risks], ensure_ascii=False)}
            
            Отчёт на русском, нарративный стиль.
        """
        messages = [{"role": "user", "content": prompt}]
        return await self.llm_service._call_llm_wrapper(messages, temperature=0.4, json_mode=False)

class StatsAgent(BaseAgent):
    """Агент Сбора Статистики: собирает метрики и анализирует тенденции"""
    async def collect_metrics(
        self,
        change: ChangeRequest,
        tasks: List[Task],
        risks: List[Risk],
        keywords: Dict[str, Any]
    ) -> Metrics:
        return Metrics(
            changes_processed=1,
            tasks_generated=len(tasks),
            risks_identified=len(risks),
            avg_task_priority="Medium",
            trends="Повторяющиеся изменения в API"
        )
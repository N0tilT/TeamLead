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
    def __init__(self, llm_service: YandexGPTService):
        self.llm_service = llm_service

class Coordinator(BaseAgent):
    def __init__(self, llm_service: YandexGPTService, tracker_service: YandexTrackerService, redis):
        super().__init__(llm_service)
        self.change_analysis_agent = ChangeAnalysisAgent(llm_service)
        self.task_creation_agent = TaskCreationAgent(llm_service)
        self.risk_management_agent = RiskManagementAgent(llm_service)
        self.description_agent = DescriptionAgent(llm_service)
        self.stats_agent = StatsAgent(llm_service)
        self.tracker_service = tracker_service 
        self.history: List[Dict[str, Any]] = []  
        self.redis = redis
        self.processed_set_key = "processed_issues"

    async def process_changes(self, change_request: ChangeRequest) -> AnalysisResult:
        logger.info("Starting change processing")
        try:
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
        tracker_ids = []
        for task in tasks:
            tracker_id = await self.tracker_service.create_issue(task)
            if tracker_id:
                tracker_ids.append(tracker_id)
        return tracker_ids

    async def close(self):
        await self.redis.close()

class ChangeAnalysisAgent(BaseAgent):
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

class SolverAgent(BaseAgent):
    def __init__(self, llm_service: YandexGPTService, style: str = "balanced"):
        super().__init__(llm_service)
        self.style = style

    async def generate_solution(self, task: Task) -> str:
        prompt = f"""
            Ты — эксперт-разработчик в стиле '{self.style}'.
            Для задачи: {task.title}
            Описание: {task.description}
            Предложи алгоритм решения: шаги, псевдокод, ключевые соображения.
            Фокус на точности, полноте, ясности.
        """
        messages = [{"role": "user", "content": prompt}]
        return await self.llm_service._call_llm_wrapper(messages, temperature=0.7, json_mode=False)

class EvaluatorAgent(BaseAgent):
    async def evaluate_solutions(self, task: Task, solutions: List[str]) -> str:
        solutions_str = "\n".join([f"Решение {i+1}: {sol}" for i, sol in enumerate(solutions)])
        prompt = f"""
            Ты — объективный оценщик решений.
            Шаг 1: Оцени каждое решение по критериям:
            - Точность: соответствие задаче.
            - Полнота: покрытие всех аспектов.
            - Ясность: понятность описания.

            Шаг 2: Выбери лучшее решение на основе критериев.
            Шаг 3: Объясни выбор кратко (1-2 предложения).
            Шаг 4: Верни ТОЛЬКО JSON: {{"best_solution": "полный текст лучшего решения", "reason": "краткое объяснение"}}

            Пример input:
            Решения:
            Решение 1: Шаг 1: A. Шаг 2: B.
            Решение 2: Шаг 1: X. Шаг 2: Y.

            Пример output:
            {{"best_solution": "Шаг 1: A. Шаг 2: B.", "reason": "Это решение лучше по полноте и ясности."}}

            Задача: {task.title} ({task.description}).
            Решения:
            {solutions_str}
        """
        schema = {
            "type": "object",
            "properties": {
                "best_solution": {"type": "string"},
                "reason": {"type": "string"}
            },
            "required": ["best_solution", "reason"],
            "additionalProperties": False
        }
        messages = [{"role": "user", "content": prompt}]
        raw = await self.llm_service._call_llm_wrapper(messages, temperature=0.1, json_mode=True, json_schema=schema)
        try:
            result = json.loads(raw)
            best_solution = result["best_solution"]
            reason = result["reason"]
            logger.info(f"Evaluation reason: {reason}")
            return f"Предложение по решению (сгенерировано LLM):\n\n{best_solution}"
        except Exception as e:
            logger.error(f"Failed to parse evaluation: {e}")
            return "Ошибка оценки: повторите запрос."

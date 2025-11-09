from typing import List, Dict, Any, Optional
import asyncio
import json
import uuid
from models import *
from language_model import MockLLMService

class ChangeAnalysisAgent:
    def __init__(self, llm_service):
        self.llm = llm_service

    async def analyze_changes(self, change_request: ChangeRequest) -> str:
        prompt = f"""
        Проанализируй изменения в документации:
        
        Было: {change_request.old_text}
        Стало: {change_request.new_text}
        Комментарии: {change_request.comments}
        
        Выяви:
        1. Что добавлено, удалено, изменено
        2. Затронутые модули системы
        3. Краткое резюме изменений
        """
        return await self.llm.generate_text(prompt)

class TaskCreationAgent:
    def __init__(self, llm_service):
        self.llm = llm_service

    async def create_tasks(self, change_summary: str) -> List[Task]:
        prompt = f"""
        На основе анализа изменений создай задачи:
        {change_summary}
        
        Для каждой задачи укажи:
        - Заголовок
        - Детальное описание
        - Тип задачи (доработка, исправление бага, обновление документации)
        - Критерии приемки
        """
        result = await self.llm.generate_text(prompt)
        
        try:
            tasks_data = json.loads(result)
            return [
                Task(
                    id=str(uuid.uuid4()),
                    title=task["title"],
                    description=task["description"],
                    task_type=task["type"],
                    acceptance_criteria=task["acceptance_criteria"]
                ) for task in tasks_data
            ]
        except:
            # Fallback задачи
            return [
                Task(
                    id=str(uuid.uuid4()),
                    title="Реализация изменений требований",
                    description=f"Выполнить работы по изменению: {change_summary}",
                    task_type="доработка",
                    acceptance_criteria=["Соответствие новым требованиям", "Прохождение тестов"]
                )
            ]

class RiskManagementAgent:
    def __init__(self, llm_service):
        self.llm = llm_service

    async def analyze_risks(self, change_summary: str, tasks: List[Task]) -> List[Risk]:
        prompt = f"""
        Проанализируй риски:
        Изменения: {change_summary}
        Задачи: {[task.title for task in tasks]}
        
        Оцени риски по категориям:
        - Технические
        - Стоимостные  
        - Риски сроков
        
        Для каждого риска укажи вероятность и влияние (Low, Medium, High)
        """
        result = await self.llm.generate_text(prompt)
        
        try:
            risks_data = json.loads(result)
            return [
                Risk(
                    category=risk["category"],
                    description=risk["description"],
                    probability=risk["probability"],
                    impact=risk["impact"],
                    mitigation=risk["mitigation"]
                ) for risk in risks_data
            ]
        except:
            return [
                Risk(
                    category="технические",
                    description="Возможные проблемы при интеграции изменений",
                    probability="Medium",
                    impact="High",
                    mitigation="Тщательное тестирование и поэтапное внедрение"
                )
            ]

class DescriptionAgent:
    def __init__(self, llm_service):
        self.llm = llm_service

    async def generate_description(self, change_summary: str, tasks: List[Task], risks: List[Risk]) -> str:
        prompt = f"""
        Создай связное описание пакета изменений:
        
        Резюме изменений: {change_summary}
        Задачи: {[task.title for task in tasks]}
        Риски: {[risk.description for risk in risks]}
        
        Сформируй отчет для команды разработки.
        """
        return await self.llm.generate_text(prompt)

class MetricsAgent:
    def __init__(self):
        self.analysis_count = 0
        self.total_tasks = 0

    async def calculate_metrics(self, tasks: List[Task], risks: List[Risk]) -> Dict[str, Any]:
        self.analysis_count += 1
        self.total_tasks += len(tasks)
        
        high_risks = len([r for r in risks if r.impact == "High"])
        
        return {
            "analysis_count": self.analysis_count,
            "tasks_generated": len(tasks),
            "total_tasks_overall": self.total_tasks,
            "high_priority_risks": high_risks,
            "task_types": {task.task_type for task in tasks},
            "risk_distribution": {
                "technical": len([r for r in risks if "техни" in r.category.lower()]),
                "schedule": len([r for r in risks if "срок" in r.category.lower()]),
                "cost": len([r for r in risks if "стоим" in r.category.lower()])
            }
        }

class Coordinator:
    def __init__(self):
        llm_service = MockLLMService()
        self.change_agent = ChangeAnalysisAgent(llm_service)
        self.task_agent = TaskCreationAgent(llm_service)
        self.risk_agent = RiskManagementAgent(llm_service)
        self.desc_agent = DescriptionAgent(llm_service)
        self.metrics_agent = MetricsAgent()

    async def process_changes(self, change_request: ChangeRequest) -> AnalysisResult:
        change_summary = await self.change_agent.analyze_changes(change_request)
        
        tasks, risks = await asyncio.gather(
            self.task_agent.create_tasks(change_summary),
            self.risk_agent.analyze_risks(change_summary, [])
        )
        
        risks = await self.risk_agent.analyze_risks(change_summary, tasks)
        
        description, metrics = await asyncio.gather(
            self.desc_agent.generate_description(change_summary, tasks, risks),
            self.metrics_agent.calculate_metrics(tasks, risks)
        )
        
        return AnalysisResult(
            change_summary=change_summary,
            tasks=tasks,
            risks=risks,
            overall_description=description,
            metrics=metrics
        )
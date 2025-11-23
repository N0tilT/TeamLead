import json
import uuid
import os
from typing import List, Dict, Any, Literal
from loguru import logger

from models import ChangeRequest, Task, AnalysisResult
from llm_client import YandexGPTClient

logger.add(
    sink="logs/llm-service.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="1 MB",
    retention="10 days",
    compression="zip"
)

class YandexGPTService:
    def __init__(
        self,
        api_key: str,
        folder_id: str,
        model: str = "yandexgpt-lite/latest",
        is_async:bool = False
    ):
        logger.info(f"Initializing YandexGPTService with model: {model}, folder_id: {folder_id[:8]}, async: {is_async}")
        self.client = YandexGPTClient(
            api_key=api_key,
            folder_id=folder_id,
            model=model,
        )
        self.is_async =is_async

    async def _call_llm_async(
        self,
        messages: List[Dict[str, str]],
        temperature: float | None = None,
        json_mode: bool = True,
        json_schema: Dict | None = None,
        max_tokens: int = 4000,
    ) -> str:
        return await self.client.chat_completion_async(
            messages=messages,
            temperature=temperature,
            json_mode=json_mode,
            json_schema=json_schema,
            max_tokens=max_tokens,
        )

    def _call_llm(
        self,
        messages: List[Dict[str, str]],
        temperature: float | None = None,
        json_mode: bool = True,
        json_schema: Dict | None = None,
        max_tokens: int = 4000,
    ) -> str:
        return self.client.chat_completion(
            messages=messages,
            temperature=temperature,
            json_mode=json_mode,
            json_schema=json_schema,
            max_tokens=max_tokens,
        )

    async def _call_llm_wrapper(
        self,
        messages: List[Dict[str, str]],
        temperature: float | None = None,
        json_mode: bool = True,
        json_schema: Dict | None = None,
        max_tokens: int = 4000,
    ) -> str:
        """Обертка, которая выбирает синхронный или асинхронный вызов LLM"""
        if self.is_async:
            return await self._call_llm_async(
                messages=messages,
                temperature=temperature,
                json_mode=json_mode,
                json_schema=json_schema,
                max_tokens=max_tokens,
            )
        else:
            return self._call_llm(
                messages=messages,
                temperature=temperature,
                json_mode=json_mode,
                json_schema=json_schema,
                max_tokens=max_tokens,
            )

    async def highlight_keywords_and_terms(self, change_description: str) -> Dict[str, Any]:
        """
            Выделение ключевых слов из текста с изменениями документации
        """
        prompt = f"""
                    Ты — эксперт по анализу технической документации.
                    Извлеки из текста все ключевые слова, технические термины, названия компонентов, API, аббревиатуры.
                    Верни строго валидный JSON с ключами:
                    - keywords: массив обычных ключевых слов
                    - technical_terms: массив технических терминов и технологий
                    - components: массив названий компонентов/сервисов
                    - abbreviations: объект {{"JWT": "JSON Web Token", ...}}

                    Текст:
                    {change_description}

                    Ответь ТОЛЬКО валидным JSON без пояснительного текста.
                """
        schema_keywords = {
            "type": "object",
            "properties": {
                "keywords": {"type": "array", "items": {"type": "string"}},
                "technical_terms": {"type": "array", "items": {"type": "string"}},
                "components": {"type": "array", "items": {"type": "string"}},
                "abbreviations": {"type": "object", "additionalProperties": {"type": "string"}},
            },
            "required": ["keywords", "technical_terms", "components", "abbreviations"],
            "additionalProperties": False,
        }
        messages = [{"role": "user", "content": prompt}]
        try:
            raw = await self._call_llm_wrapper(
                messages, 
                temperature=0.2, 
                json_mode=False, 
                json_schema=schema_keywords
            )
            result = json.loads(raw)
            logger.info(f"Extracted keywords: {len(result.get('keywords', []))} + {len(result.get('technical_terms', []))} terms")
            return result
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error in keywords: {e}")
            return {"keywords": [], "technical_terms": [], "components": [], "abbreviations": {}}
        except Exception as e:
            logger.error(f"Error in highlight_keywords_and_terms: {e}")
            return {"keywords": [], "technical_terms": [], "components": [], "abbreviations": {}}

    async def generate_tasks_from_change(
        self,
        change: ChangeRequest,
        affected_component: str,
        keywords_result: Dict[str, Any] | None = None,
    ) -> List[Task]:
        """
            Генерация текстов задач на основе описания изменений, затронутых компонентов и ключевых слов
        """
        keywords_hint = ""
        if keywords_result:
            all_terms = (
                keywords_result.get("keywords", []) +
                keywords_result.get("technical_terms", []) +
                keywords_result.get("components", [])
            )
            keywords_hint = f"Ключевые термины: {', '.join(all_terms[:50])}"
        prompt = f"""
                    Ты — технический лид. На основе изменений в документации создай задачи для разработчиков и тестировщиков.
                    Затронутый компонент: {affected_component}
                    Комментарий: {change.comments or "—"}
                    Старый текст:
                    {change.old_text[:3000]}
                    Новый текст:
                    {change.new_text[:3000]}
                    {keywords_hint}

                    Создай массив задач в строгом JSON формате. Каждая задача:
                    {{
                    "id": "<uuid4>",
                    "title": "Краткое название",
                    "description": "Что нужно сделать",
                    "task_type": "Development|Refactoring|Testing|Documentation|Bugfix",
                    "acceptance_criteria": ["критерий 1", "критерий 2"],
                    "priority": "High|Medium|Low"
                    }}

                    Верни ТОЛЬКО массив JSON. Ничего больше.
                """
        schema_tasks = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "task_type": {"type": "string", "enum": ["Development", "Refactoring", "Testing", "Documentation", "Bugfix"]},
                    "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
                    "priority": {"type": "string", "enum": ["High", "Medium", "Low"]},
                },
                "required": ["id", "title", "description", "task_type", "acceptance_criteria", "priority"],
                "additionalProperties": False,
            },
        }

        messages = [{"role": "user", "content": prompt}]
        try:
            raw = await self._call_llm_wrapper(
                messages, 
                temperature=0.7, 
                json_mode=True,
                json_schema=schema_tasks
            )
            tasks_data = json.loads(raw)
            if not isinstance(tasks_data, list):
                tasks_data = [tasks_data]

            tasks = []
            for t in tasks_data:
                if "id" not in t or not t["id"]:
                    t["id"] = str(uuid.uuid4())
                tasks.append(Task(**t))

            logger.success(f"Generated {len(tasks)} tasks for {affected_component}")
            return tasks
        except Exception as e:
            logger.error(f"Task parsing failed: {e}")
            return []

    async def generate_summary_report(
        self,
        processed_changes: int,
        total_tasks_created: int,
        all_keywords: Dict[str, Any],
        period: str = "последние 24 часа",
    ) -> str:
        """
            Генерация краткого отчёта о работе системы, включающего основные метрики (количество изменений, созданных задач)
        """
        from collections import Counter

        flat_keywords = []
        flat_terms = []
        flat_components = []
        for kw in all_keywords:
            flat_keywords.extend(kw.get("keywords", []))
            flat_terms.extend(kw.get("technical_terms", []))
            flat_components.extend(kw.get("components", []))

        top_keywords = [k for k, _ in Counter(flat_keywords).most_common(10)]
        top_terms = [k for k, _ in Counter(flat_terms).most_common(8)]
        top_components = [k for k, _ in Counter(flat_components).most_common(6)]
        avg_tasks = total_tasks_created / processed_changes if processed_changes else 0

        prompt = f"""
                    Составь краткий отчёт для руководителя о работе системы обработки изменений документации за {period}.
                    Метрики:
                    • Обработано изменений: {processed_changes}
                    • Создано задач: {total_tasks_created} (в среднем {avg_tasks:.2f} на изменение)
                    • Топ ключевых слов: {', '.join(top_keywords) or "—"}
                    • Топ терминов/технологий: {', '.join(top_terms) or "—"}
                    • Чаще всего затрагиваемые компоненты: {', '.join(top_components) or "—"}

                    Отчёт на русском, деловой стиль, 5–7 предложений.
                """
        messages = [{"role": "user", "content": prompt}]
        report = await self._call_llm_wrapper(messages, temperature=0.4, json_mode=False)
        return report


    async def process_change_full(
        self,
        change: ChangeRequest,
        affected_component: str,
    ) -> AnalysisResult:
        """
            Обработка изменений в документации, создание отчета о проделанной работе
        """
        description = f"Изменение в {affected_component}\nБыло: {change.old_text[:1000]}\nСтало: {change.new_text[:1000]}\nКомментарий: {change.comments or '—'}"
        keywords = await self.highlight_keywords_and_terms(description)
        tasks = await self.generate_tasks_from_change(change, affected_component, keywords)

        return AnalysisResult(
            change_summary=description[:500] + ("..." if len(description) > 500 else ""),
            tasks=tasks,
            keywords=keywords,
            risks=[],
            overall_description=f"Обработано изменение в {affected_component}. Создано задач: {len(tasks)}",
            metrics={
                "keywords_count": len(keywords.get("keywords", [])) + len(keywords.get("technical_terms", [])),
                "tasks_generated": len(tasks),
                "component": affected_component,
            },
        )
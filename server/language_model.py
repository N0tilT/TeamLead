import asyncio
import json

class MockLLMService:
    async def generate_text(self, prompt: str) -> str:
        await asyncio.sleep(1)
        
        if "анализ изменений" in prompt.lower():
            return "Изменения затрагивают модуль аутентификации: добавлена двухфакторная авторизация, обновлены требования к паролям."
        elif "генерация задач" in prompt.lower():
            return json.dumps([
                {
                    "title": "Реализация двухфакторной аутентификации",
                    "description": "Добавить поддерку SMS и email подтверждения для входа",
                    "type": "доработка",
                    "acceptance_criteria": ["Поддержка SMS", "Поддержка email", "Настройка времени жизни кода"]
                }
            ])
        elif "анализ рисков" in prompt.lower():
            return json.dumps([
                {
                    "category": "технические",
                    "description": "Увеличение времени входа может повлиять на UX",
                    "probability": "Medium",
                    "impact": "High",
                    "mitigation": "Оптимизировать процесс подтверждения"
                }
            ])
        return "Результат анализа"
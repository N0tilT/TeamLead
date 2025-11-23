import openai
import os
from loguru import logger
from typing import List, Dict, Any, Literal

logger.add(
    sink="logs/llm-client.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="1 MB",
    retention="10 days",
    compression="zip"
)

class YandexGPTClient:
    def __init__(
        self,
        api_key: str,
        folder_id: str,
        model: str = "yandexgpt-lite/latest",
        base_url: str = "https://llm.api.cloud.yandex.net/v1",
    ):
        logger.info(f"Initializing YandexGPTClient with model: {model}, folder_id: {folder_id[:8]}...")
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.folder_id = folder_id
        self.model = model
        self.model_uri = f"gpt://{folder_id}/{model}"
        logger.success("YandexGPTClient initialized successfully")

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float | None = None,
        json_mode: bool = False,
        json_schema: Dict | None = None,
        max_tokens: int = 4000,
    ) -> str:
        """
            Синхронный вызов YandexGPT через OpenAI-совместимый API
        """
        logger.debug(f"Sync LLM call - Model: {self.model}, Messages: {messages}, Temperature: {temperature}, JSON mode: {json_mode}, Max tokens: {max_tokens}")
        response_format = None
        if json_schema:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "strict": True,
                    "schema": json_schema,
                },
            }
        elif json_mode:
            response_format = {"type": "json_object"}

        try:
            response = self.client.chat.completions.create(
                model=self.model_uri,
                messages=messages,
                temperature=temperature or 0.6,
                max_tokens=max_tokens,
                response_format=response_format,
            )
            content = response.choices[0].message.content
            result = content.strip() if content else ""
            logger.info(f"MODEL: {self.model} | TEMPERATURE: {temperature} | JSON_MODE: {json_mode} | RESPONSE: {result}")
            logger.debug(f"Sync LLM call completed, response length: {len(result)}")
            return result
        except Exception as e:
            logger.error(f"YandexGPT API error: {e}")
            raise
            
    async def chat_completion_async(
        self,
        messages: List[Dict[str, str]],
        temperature: float | None = None,
        json_mode: bool = False,
        json_schema: Dict | None = None,
        max_tokens: int = 4000,
    ) -> str:
        """
        Асинхронный вызов (через async клиент OpenAI)
        """
        response_format = None
        if json_schema:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "strict": True,
                    "schema": json_schema,
                },
            }
        elif json_mode:
            response_format = {"type": "json_object"}

        try:
            logger.debug(f"Async LLM call - Model: {self.model}, Messages: {len(messages)}, Temperature: {temperature}, JSON mode: {json_mode}, Max tokens: {max_tokens}")
            async_client = openai.AsyncOpenAI(
                api_key=self.client.api_key,
                base_url=self.client.base_url,
            )
            response = await async_client.chat.completions.create(
                model=self.model_uri,
                messages=messages,
                temperature=temperature or 0.6,
                max_tokens=max_tokens,
                response_format=response_format,
            )
            content = response.choices[0].message.content
            result=content.strip() if content else ""
            logger.info(f"MODEL: {self.model} | TEMPERATURE: {temperature} | JSON_MODE: {json_mode} | RESPONSE: {result}")
            logger.debug(f"Async LLM call completed, response length: {len(result)}")
            
            return result
        except Exception as e:
            logger.error(f"YandexGPT async API error: {e}")
            raise
        finally:
            await async_client.close()
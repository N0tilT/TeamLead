import aiohttp
from loguru import logger
from typing import Optional, Dict, Any

class FuzzyLogicClient:
    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
    
    async def evaluate_task(
        self,
        task_id: str,
        code_changes_lines: float,
        dependencies_count: int,
        team_expertise: float,
        requirement_uncertainty_pct: float,
        task_type: str
    ) -> Optional[Dict[str, Any]]:
        payload = {
            "task_id": task_id,
            "code_changes_lines": code_changes_lines,
            "dependencies_count": dependencies_count,
            "team_expertise": team_expertise,
            "requirement_uncertainty_pct": requirement_uncertainty_pct,
            "task_type": task_type
        }
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.base_url}/evaluate",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.debug(f"Fuzzy evaluation for {task_id}: risk={result['risk_category']}, complexity={result['complexity_score']}")
                        return result
                    else:
                        error_text = await response.text()
                        logger.warning(f"Fuzzy API error {response.status}: {error_text}")
                        return None
        except aiohttp.ClientError as e:
            logger.error(f"Failed to connect to fuzzy logic server: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in fuzzy evaluation: {e}")
            return None
    
    async def health_check(self) -> bool:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{self.base_url}/docs") as response:
                    return response.status == 200
        except Exception:
            return False
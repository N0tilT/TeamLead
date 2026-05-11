# fuzzy_repository.py
import json
from datetime import datetime
from typing import List, Dict, Optional
from loguru import logger
from database import DatabaseConnection

class FuzzyFeedbackRepository:
    """Изолированный репозиторий для хранения результатов evaluate и фидбэка"""
    
    def __init__(self, connection: DatabaseConnection):
        self.connection = connection
        self._ensure_tables()

    def _ensure_tables(self):
        """Создание таблиц evaluate_results и feedback с FK-связью"""
        try:
            conn = self.connection.get_connection()
            cursor = conn.cursor()
            
            # Таблица результатов evaluate
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS evaluate_results (
                    id SERIAL PRIMARY KEY,
                    task_id VARCHAR(255) UNIQUE NOT NULL,
                    input_volume FLOAT,
                    input_dependencies FLOAT,
                    input_expertise FLOAT,
                    input_uncertainty FLOAT,
                    task_type VARCHAR(50),
                    predicted_complexity FLOAT,
                    predicted_risk FLOAT,
                    evaluated_at TIMESTAMP DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_evaluate_task ON evaluate_results(task_id);
                CREATE INDEX IF NOT EXISTS idx_evaluate_at ON evaluate_results(evaluated_at);
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id SERIAL PRIMARY KEY,
                    evaluate_id INTEGER REFERENCES evaluate_results(id) ON DELETE CASCADE,
                    task_id VARCHAR(255) NOT NULL UNIQUE,
                    actual_effort_hours FLOAT,
                    actual_risk_score FLOAT,
                    user_rating VARCHAR(20),
                    feedback_at TIMESTAMP DEFAULT NOW(),
                    CONSTRAINT fk_evaluate FOREIGN KEY (task_id) 
                        REFERENCES evaluate_results(task_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_feedback_task ON feedback(task_id);
                CREATE INDEX IF NOT EXISTS idx_feedback_at ON feedback(feedback_at);
            """)
            
            conn.commit()
            cursor.close()
            logger.info("Tables evaluate_results and feedback ensured")
        except Exception as e:
            logger.error(f"Failed to ensure tables: {e}")
            raise
        finally:
            if conn: conn.close()

    def save_evaluate_result(self, task_id: str, inputs: Dict, predictions: Dict, task_type: str = None) -> int:
        """Сохраняет результат /evaluate, возвращает ID записи"""
        try:
            conn = self.connection.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO evaluate_results (
                    task_id, input_volume, input_dependencies, input_expertise, input_uncertainty,
                    task_type, predicted_complexity, predicted_risk
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (task_id) DO UPDATE SET
                    input_volume = EXCLUDED.input_volume,
                    input_dependencies = EXCLUDED.input_dependencies,
                    input_expertise = EXCLUDED.input_expertise,
                    input_uncertainty = EXCLUDED.input_uncertainty,
                    task_type = EXCLUDED.task_type,
                    predicted_complexity = EXCLUDED.predicted_complexity,
                    predicted_risk = EXCLUDED.predicted_risk,
                    evaluated_at = EXCLUDED.evaluated_at
                RETURNING id
            """, (
                task_id, inputs["volume"], inputs["dependencies"], 
                inputs["expertise"], inputs["uncertainty"],
                task_type, predictions["complexity_score"], predictions["risk_score"]
            ))
            result = cursor.fetchone()
            evaluate_id = result[0] if result else None
            conn.commit()
            cursor.close()
            return evaluate_id
        except Exception as e:
            logger.error(f"Save evaluate result failed: {e}")
            raise
        finally:
            if conn: conn.close()

    def save_feedback(self, task_id: str, actual_data: Dict) -> bool:
        """Сохраняет фидбэк, связывая с существующей записью evaluate_results"""
        try:
            conn = self.connection.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO feedback (
                    task_id, actual_effort_hours, actual_risk_score, user_rating
                ) VALUES (%s, %s, %s, %s)
                ON CONFLICT (task_id) DO UPDATE SET
                    actual_effort_hours = COALESCE(EXCLUDED.actual_effort_hours, feedback.actual_effort_hours),
                    actual_risk_score = COALESCE(EXCLUDED.actual_risk_score, feedback.actual_risk_score),
                    user_rating = COALESCE(EXCLUDED.user_rating, feedback.user_rating),
                    feedback_at = EXCLUDED.feedback_at
            """, (
                task_id,
                actual_data.get("actual_effort_hours"),
                actual_data.get("actual_risk_score"),
                actual_data.get("user_rating")
            ))
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Save feedback failed: {e}")
            raise
        finally:
            if conn: conn.close()

    def get_count(self) -> int:
        """Количество записей с фидбэком (есть actual_*)"""
        try:
            conn = self.connection.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM feedback 
                WHERE actual_effort_hours IS NOT NULL OR actual_risk_score IS NOT NULL
            """)
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        finally:
            if conn: conn.close()

    def get_training_data(self, agent_name: str, limit: int = 200) -> List[Dict]:
        """Возвращает данные для обучения: джойн evaluate_results + feedback"""
        target_col = "actual_effort_hours" if agent_name == "effort" else "actual_risk_score"
        pred_col = "predicted_complexity" if agent_name == "effort" else "predicted_risk"
        
        try:
            conn = self.connection.get_connection()
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT 
                    e.input_volume, e.input_dependencies, e.input_expertise, e.input_uncertainty,
                    e.{pred_col}, f.{target_col}
                FROM evaluate_results e
                INNER JOIN feedback f ON e.task_id = f.task_id
                WHERE f.{target_col} IS NOT NULL
                ORDER BY f.feedback_at DESC LIMIT %s
            """, (limit,))
            rows = cursor.fetchall()
            cursor.close()
            
            data = []
            for r in rows:
                raw_target = r[5]
                if raw_target is None:
                    continue
                target = min(max(raw_target, 0.0), 100.0)
                
                data.append({
                    "inputs": {
                        "volume": r[0], "dependencies": r[1],
                        "expertise": r[2], "uncertainty": r[3]
                    },
                    "predicted": r[4],
                    "target": target
                })
            return data
        finally:
            if conn: conn.close()

    def get_evaluate_history(self, task_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Получение истории оценок для аналитики"""
        try:
            conn = self.connection.get_connection()
            cursor = conn.cursor()
            
            if task_id:
                cursor.execute("""
                    SELECT e.*, f.actual_effort_hours, f.actual_risk_score, f.user_rating, f.feedback_at
                    FROM evaluate_results e
                    LEFT JOIN feedback f ON e.task_id = f.task_id
                    WHERE e.task_id = %s
                """, (task_id,))
            else:
                cursor.execute("""
                    SELECT e.*, f.actual_effort_hours, f.actual_risk_score, f.user_rating, f.feedback_at
                    FROM evaluate_results e
                    LEFT JOIN feedback f ON e.task_id = f.task_id
                    ORDER BY e.evaluated_at DESC LIMIT %s
                """, (limit,))
            
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            cursor.close()
            return results
        finally:
            if conn: conn.close()

    def get_evaluate_by_task_id(self, task_id: str) -> Optional[Dict]:
        """Получает полную информацию по задаче: предсказания + фидбэк (если есть)"""
        try:
            conn = self.connection.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    e.id, e.task_id,
                    e.input_volume, e.input_dependencies, e.input_expertise, e.input_uncertainty,
                    e.task_type,
                    e.predicted_complexity, e.predicted_risk,
                    e.evaluated_at,
                    f.actual_effort_hours, f.actual_risk_score, f.user_rating, f.feedback_at
                FROM evaluate_results e
                LEFT JOIN feedback f ON e.task_id = f.task_id
                WHERE e.task_id = %s
                ORDER BY e.evaluated_at DESC
                LIMIT 1
            """, (task_id,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if not row:
                return None
                
            # Маппинг колонок в словарь
            columns = [
                "id", "task_id", "input_volume", "input_dependencies", 
                "input_expertise", "input_uncertainty", "task_type",
                "predicted_complexity", "predicted_risk", "evaluated_at",
                "actual_effort_hours", "actual_risk_score", "user_rating", "feedback_at"
            ]
            result = dict(zip(columns, row))
            
            # Форматируем ответ для UI
            return {
                "task_id": result["task_id"],
                "inputs": {
                    "volume": result["input_volume"],
                    "dependencies": result["input_dependencies"],
                    "expertise": result["input_expertise"],
                    "uncertainty": result["input_uncertainty"]
                },
                "task_type": result["task_type"],
                "predictions": {
                    "complexity_score": round(result["predicted_complexity"], 2) if result["predicted_complexity"] else None,
                    "risk_score": round(result["predicted_risk"], 2) if result["predicted_risk"] else None,
                    "risk_category": self._calculate_risk_category(result["predicted_risk"])
                },
                "feedback": {
                    "actual_effort_hours": result["actual_effort_hours"],
                    "actual_risk_score": result["actual_risk_score"],
                    "user_rating": result["user_rating"],
                    "feedback_at": result["feedback_at"].isoformat() if result["feedback_at"] else None
                } if result["actual_effort_hours"] or result["actual_risk_score"] else None,
                "evaluated_at": result["evaluated_at"].isoformat() if result["evaluated_at"] else None
            }
        except Exception as e:
            logger.error(f"Get evaluate by task_id failed: {e}")
            raise
        finally:
            if conn: conn.close()

    @staticmethod
    def _calculate_risk_category(risk_score: Optional[float]) -> str:
        """Вспомогательный метод для категоризации риска"""
        if risk_score is None:
            return "Unknown"
        if risk_score < 35:
            return "Low"
        elif risk_score < 60:
            return "Medium"
        elif risk_score < 80:
            return "High"
        else:
            return "Critical"
    
    def generate_synthetic_feedback(self, task_ids: Optional[List[str]] = None, inflation_range: tuple = (1.2, 1.3)) -> Dict[str, int]:
        """
        Генерирует синтетические actual_* значения для задач без фидбэка.
        Значения завышаются относительно предсказанных на случайный множитель из inflation_range.
        
        Args:
            task_ids: список task_id для обработки (None = все задачи без фидбэка)
            inflation_range: кортеж (min_multiplier, max_multiplier) для случайного завышения
        
        Returns:
            Dict со статистикой: сколько записей обработано/пропущено/ошибок
        """
        import random
        from decimal import Decimal, ROUND_HALF_UP
        
        stats = {"processed": 0, "skipped": 0, "errors": 0}
        
        try:
            conn = self.connection.get_connection()
            cursor = conn.cursor()
            
            # Выбираем задачи из evaluate_results, для которых ещё нет записей в feedback
            if task_ids:
                placeholders = ','.join(['%s'] * len(task_ids))
                cursor.execute(f"""
                    SELECT e.task_id, e.predicted_complexity, e.predicted_risk 
                    FROM evaluate_results e
                    LEFT JOIN feedback f ON e.task_id = f.task_id
                    WHERE e.task_id IN ({placeholders}) AND f.task_id IS NULL
                """, task_ids)
            else:
                cursor.execute("""
                    SELECT e.task_id, e.predicted_complexity, e.predicted_risk 
                    FROM evaluate_results e
                    LEFT JOIN feedback f ON e.task_id = f.task_id
                    WHERE f.task_id IS NULL
                """)
            
            rows = cursor.fetchall()
            
            for task_id, pred_complexity, pred_risk in rows:
                try:
                    # Пропускаем, если предсказания отсутствуют
                    if pred_complexity is None or pred_risk is None:
                        stats["skipped"] += 1
                        continue
                    
                    # Генерируем случайный множитель завышения в заданном диапазоне
                    inflation_factor = random.uniform(*inflation_range)
                    
                    # Рассчитываем завышенные значения с округлением до 2 знаков
                    actual_effort = float(Decimal(str(pred_complexity * inflation_factor)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
                    actual_risk = float(Decimal(str(pred_risk * inflation_factor)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
                    
                    # Ограничиваем значения диапазоном [0, 100]
                    actual_effort = min(max(actual_effort, 0.0), 100.0)
                    actual_risk = min(max(actual_risk, 0.0), 100.0)
                    
                    # Вставляем запись в feedback
                    cursor.execute("""
                        INSERT INTO feedback (
                            task_id, actual_effort_hours, actual_risk_score, user_rating, feedback_at
                        ) VALUES (%s, %s, %s, %s, NOW())
                        ON CONFLICT (task_id) DO UPDATE SET
                            actual_effort_hours = EXCLUDED.actual_effort_hours,
                            actual_risk_score = EXCLUDED.actual_risk_score,
                            feedback_at = EXCLUDED.feedback_at
                    """, (task_id, actual_effort, actual_risk, "synthetic"))
                    
                    stats["processed"] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to generate feedback for {task_id}: {e}")
                    stats["errors"] += 1
                    continue
            
            conn.commit()
            cursor.close()
            logger.info(f"Synthetic feedback generated: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Generate synthetic feedback failed: {e}")
            raise
        finally:
            if conn:
                conn.close()
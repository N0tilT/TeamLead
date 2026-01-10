import json
import logging
from datetime import datetime
from typing import List, Optional
from models import AnalysisResult, Task, Risk, Metrics
from database import DatabaseConnection
from loguru import logger

logger.add("logs/analysis_worker.log", level="DEBUG", rotation="1 MB")

class AnalysisRepository:
    '''Класс-репозиторий для доступа к данным анализа'''

    def __init__(self, connection: DatabaseConnection):
        self.connection = connection
        logger.debug(f"AnalysisRepository initialized with connection: {connection}")

    def create_analysis(self, analysis: AnalysisResult, tracking_id: str) -> AnalysisResult:
        """Создание нового результата анализа"""
        
        logger.info(f"Creating new analysis with tracking_id: {tracking_id}")
        logger.debug(f"Analysis data: {analysis.model_dump_json(exclude={'id', 'created_at'})}")
        
        try:
            conn = self.connection.get_connection()
            cursor = conn.cursor()
            
            tasks_json = json.dumps([task.model_dump() for task in analysis.tasks])
            risks_json = json.dumps([risk.model_dump() for risk in analysis.risks])
            keywords_json = json.dumps(analysis.keywords)
            metrics_json = json.dumps(analysis.metrics.model_dump())
            tracker_ids_json = json.dumps(analysis.tracker_ids)
            
            logger.debug(f"Executing SQL insert for tracking_id: {tracking_id}")
            cursor.execute('''
                INSERT INTO analysis_results 
                (tracking_id, change_summary, tasks, risks, keywords, 
                 overall_description, metrics, tracker_ids)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, created_at
            ''', (
                tracking_id,
                analysis.change_summary,
                tasks_json,
                risks_json,
                keywords_json,
                analysis.overall_description,
                metrics_json,
                tracker_ids_json
            ))
            
            result = cursor.fetchone()
            analysis.id = result[0]
            analysis.created_at = result[1]
            conn.commit()
            
            logger.info(f"Analysis created successfully with id: {analysis.id}")
            logger.debug(f"Created analysis details: id={analysis.id}, created_at={analysis.created_at}")
            
        except Exception as e:
            logger.error(f"Failed to create analysis for tracking_id: {tracking_id}")
            logger.exception(f"Database error: {str(e)}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
                logger.debug("Database connection closed")
        
        return analysis

    def get_all(self) -> List[AnalysisResult]:
        """Получить все результаты анализа"""
        
        logger.info("Fetching all analysis results")
        
        try:
            conn = self.connection.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, tracking_id, change_summary, tasks, risks, keywords,
                       overall_description, metrics, tracker_ids, created_at
                FROM analysis_results 
                ORDER BY created_at DESC
            """)
            
            rows = cursor.fetchall()
            analyses = []
            
            logger.debug(f"Found {len(rows)} analysis results")
            
            for row in rows:
                
                try:
                    tasks = [Task(**task) for task in row[3]]
                    risks = [Risk(**risk) for risk in row[4]]
                    keywords = row[5]
                    metrics_data = row[7]
                    tracker_ids = row[8]
                    
                    analysis = AnalysisResult(
                        id=row[0],
                        change_summary=row[2],
                        tasks=tasks,
                        risks=risks,
                        keywords=keywords,
                        overall_description=row[6],
                        metrics=Metrics(**metrics_data),
                        tracker_ids=tracker_ids
                    )
                    analysis.tracking_id = row[1]
                    analysis.created_at = row[9]
                    analyses.append(analysis)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parsing error for analysis id {row[0]}: {str(e)}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing analysis id {row[0]}: {str(e)}")
                    continue
            
            logger.info(f"Successfully retrieved {len(analyses)} analyses")
            
        except Exception as e:
            logger.error("Failed to fetch all analysis results")
            logger.exception(f"Database error: {str(e)}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
                logger.debug("Database connection closed")
        
        return analyses

    def get_by_id(self, analysis_id: int) -> Optional[AnalysisResult]:
        """Получить результат анализа по ID"""
        
        logger.info(f"Fetching analysis by id: {analysis_id}")
        
        try:
            conn = self.connection.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, tracking_id, change_summary, tasks, risks, keywords,
                       overall_description, metrics, tracker_ids, created_at
                FROM analysis_results 
                WHERE id = %s
            """, (analysis_id,))
            
            row = cursor.fetchone()
            
            if not row:
                logger.warning(f"Analysis with id {analysis_id} not found")
                return None
            
            logger.debug(f"Found analysis id {analysis_id}")
            
            tasks = [Task(**task) for task in json.loads(row[3])]
            risks = [Risk(**risk) for risk in json.loads(row[4])]
            keywords = json.loads(row[5])
            metrics_data = json.loads(row[7])
            tracker_ids = json.loads(row[8])
            
            analysis = AnalysisResult(
                id=row[0],
                change_summary=row[2],
                tasks=tasks,
                risks=risks,
                keywords=keywords,
                overall_description=row[6],
                metrics=Metrics(**metrics_data),
                tracker_ids=tracker_ids
            )
            analysis.tracking_id = row[1]
            analysis.created_at = row[9]
            
            logger.info(f"Successfully retrieved analysis id {analysis_id}")
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error for analysis id {analysis_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to fetch analysis id {analysis_id}")
            logger.exception(f"Database error: {str(e)}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
                logger.debug("Database connection closed")
        
        return analysis

    def get_by_tracking_id(self, tracking_id: str) -> List[AnalysisResult]:
        """Получить результаты анализа по tracking_id"""
        
        logger.info(f"Fetching analyses by tracking_id: {tracking_id}")
        
        try:
            conn = self.connection.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, tracking_id, change_summary, tasks, risks, keywords,
                       overall_description, metrics, tracker_ids, created_at
                FROM analysis_results 
                WHERE tracking_id = %s
                ORDER BY created_at DESC
            """, (tracking_id,))
            
            rows = cursor.fetchall()
            analyses = []
            
            logger.debug(f"Found {len(rows)} analyses for tracking_id {tracking_id}")
            
            for row in rows:
                try:
                    tasks = [Task(**task) for task in row[3]]
                    risks = [Risk(**risk) for risk in row[4]]
                    keywords = row[5]
                    metrics_data = row[7]
                    tracker_id = row[8]
                    
                    analysis = AnalysisResult(
                        id=row[0],
                        change_summary=row[2],
                        tasks=tasks,
                        risks=risks,
                        keywords=keywords,
                        overall_description=row[6],
                        metrics=Metrics(**metrics_data),
                        tracker_ids=tracker_ids
                    )
                    analysis.tracking_id = row[1]
                    analysis.created_at = row[9]
                    analyses.append(analysis)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parsing error for analysis id {row[0]}: {str(e)}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing analysis id {row[0]}: {str(e)}")
                    continue
            
            logger.info(f"Successfully retrieved {len(analyses)} analyses for tracking_id {tracking_id}")
            
        except Exception as e:
            logger.error(f"Failed to fetch analyses for tracking_id {tracking_id}")
            logger.exception(f"Database error: {str(e)}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
                logger.debug("Database connection closed")
        
        return analyses

    def update_analysis(self, analysis: AnalysisResult) -> Optional[AnalysisResult]:
        """Обновить существующий результат анализа"""
        
        logger.info(f"Updating analysis id: {analysis.id}")
        logger.debug(f"Update data: {analysis.model_dump_json(exclude={'created_at'})}")
        
        try:
            existing = self.get_by_id(analysis.id)
            if not existing:
                logger.warning(f"Cannot update: analysis id {analysis.id} not found")
                return None
            
            conn = self.connection.get_connection()
            cursor = conn.cursor()
            
            tasks_json = json.dumps([task.model_dump() for task in analysis.tasks])
            risks_json = json.dumps([risk.model_dump() for risk in analysis.risks])
            keywords_json = json.dumps(analysis.keywords)
            metrics_json = json.dumps(analysis.metrics.model_dump())
            tracker_ids_json = json.dumps(analysis.tracker_ids)
            
            logger.debug(f"Executing SQL update for analysis id: {analysis.id}")
            cursor.execute('''
                UPDATE analysis_results
                SET change_summary = %s,
                    tasks = %s,
                    risks = %s,
                    keywords = %s,
                    overall_description = %s,
                    metrics = %s,
                    tracker_ids = %s
                WHERE id = %s
            ''', (
                analysis.change_summary,
                tasks_json,
                risks_json,
                keywords_json,
                analysis.overall_description,
                metrics_json,
                tracker_ids_json,
                analysis.id
            ))
            
            conn.commit()
            updated = cursor.rowcount
            
            if updated > 0:
                logger.info(f"Analysis id {analysis.id} updated successfully")
                logger.debug(f"Rows affected: {updated}")
                return analysis
            else:
                logger.warning(f"No rows updated for analysis id {analysis.id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to update analysis id {analysis.id}")
            logger.exception(f"Database error: {str(e)}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
                logger.debug("Database connection closed")

    def delete_analysis(self, analysis_id: int) -> bool:
        """Удалить результат анализа"""
        
        logger.info(f"Deleting analysis id: {analysis_id}")
        
        try:
            conn = self.connection.get_connection()
            cursor = conn.cursor()
            
            logger.debug(f"Executing SQL delete for analysis id: {analysis_id}")
            cursor.execute('''
                DELETE FROM analysis_results 
                WHERE id = %s
            ''', (analysis_id,))
            
            conn.commit()
            deleted = cursor.rowcount
            
            if deleted > 0:
                logger.info(f"Analysis id {analysis_id} deleted successfully")
                logger.debug(f"Rows affected: {deleted}")
            else:
                logger.warning(f"No analysis found with id {analysis_id} to delete")
            
        except Exception as e:
            logger.error(f"Failed to delete analysis id {analysis_id}")
            logger.exception(f"Database error: {str(e)}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
                logger.debug("Database connection closed")
        
        return deleted > 0

    def get_recent_analyses(self, limit: int = 10) -> List[AnalysisResult]:
        """Получить последние результаты анализа"""
        
        logger.info(f"Fetching recent analyses, limit: {limit}")
        
        try:
            conn = self.connection.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, tracking_id, change_summary, tasks, risks, keywords,
                       overall_description, metrics, tracker_ids, created_at
                FROM analysis_results 
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            
            rows = cursor.fetchall()
            analyses = []
            
            logger.debug(f"Found {len(rows)} recent analyses")
            
            for row in rows:
                try:
                    tasks = [Task(**task) for task in json.loads(row[3])]
                    risks = [Risk(**risk) for risk in json.loads(row[4])]
                    keywords = json.loads(row[5])
                    metrics_data = json.loads(row[7])
                    tracker_ids = json.loads(row[8])
                    
                    analysis = AnalysisResult(
                        id=row[0],
                        change_summary=row[2],
                        tasks=tasks,
                        risks=risks,
                        keywords=keywords,
                        overall_description=row[6],
                        metrics=Metrics(**metrics_data),
                        tracker_ids=tracker_ids
                    )
                    analysis.tracking_id = row[1]
                    analysis.created_at = row[9]
                    analyses.append(analysis)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parsing error for analysis id {row[0]}: {str(e)}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing analysis id {row[0]}: {str(e)}")
                    continue
            
            logger.info(f"Successfully retrieved {len(analyses)} recent analyses")
            
        except Exception as e:
            logger.error("Failed to fetch recent analyses")
            logger.exception(f"Database error: {str(e)}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
                logger.debug("Database connection closed")
        
        return analyses
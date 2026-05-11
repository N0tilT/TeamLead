// src/components/ResultsSection.jsx
import React, { useEffect, useState, useCallback } from 'react';
import MetricCard from './MetricCard';
import TaskCard from './TaskCard';
import RiskBadge from './RiskBadge';

const ResultsSection = ({ result }) => {
  const [fuzzyEvaluations, setFuzzyEvaluations] = useState({});
  const [loadingTasks, setLoadingTasks] = useState({});

  // 🔍 Загрузка оценки нечёткого агента по tracker_id (соответствует task по индексу)
  const fetchFuzzyEvaluation = useCallback(async (trackerId, taskIndex) => {
    if (!trackerId) return;
    
    const cacheKey = `idx_${taskIndex}`;
    if (fuzzyEvaluations[cacheKey] || loadingTasks[cacheKey]) return;
    
    setLoadingTasks(prev => ({ ...prev, [cacheKey]: true }));
    
    try {
      // 📡 Запрос к fuzzy-агенту: /fuzzy/evaluate/{tracker_id}
      const response = await fetch(`/fuzzy/evaluate/${trackerId}`);
      
      if (response.ok) {
        const data = await response.json();
        setFuzzyEvaluations(prev => ({
          ...prev,
          [cacheKey]: {
            tracker_id: trackerId,
            complexity_score: data.predictions?.complexity_score,
            risk_score: data.predictions?.risk_score,
            inputs: data.inputs,
            task_type: data.task_type,
            evaluated_at: data.evaluated_at
          }
        }));
      } else if (response.status === 404) {
        // 🆕 Если оценки нет — можно создать её "на лету" (опционально)
        console.log(`No evaluation found for tracker_id: ${trackerId}`);
      }
    } catch (error) {
      console.warn(`Failed to fetch fuzzy evaluation for ${trackerId}:`, error);
    } finally {
      setLoadingTasks(prev => ({ ...prev, [cacheKey]: false }));
    }
  }, [fuzzyEvaluations, loadingTasks]);

  // Загружаем оценки при монтировании или изменении result
  useEffect(() => {
    if (result?.tasks?.length && result.tracker_ids?.length) {
      result.tasks.forEach((task, index) => {
        const trackerId = result.tracker_ids[index];
        const cacheKey = `idx_${index}`;
        
        if (trackerId && !fuzzyEvaluations[cacheKey]) {
          fetchFuzzyEvaluation(trackerId, index);
        }
      });
    }
  }, [result, fetchFuzzyEvaluation]);

  // 🔄 Обработчик успешной отправки фидбека
  const handleFeedbackSuccess = useCallback((taskIndex, feedbackResult) => {
    const trackerId = result?.tracker_ids?.[taskIndex];
    console.log(`Feedback sent for tracker_id ${trackerId}:`, feedbackResult);
    // Можно добавить тост-уведомление или обновить локальное состояние
  }, [result]);

  if (!result) return null;

  return (
    <div className="results fade-in">
      <section className="result-section">
        <h2>📋 Анализ изменений</h2>
        <div className="summary-card"><p>{result.change_summary}</p></div>
      </section>

      <section className="result-section">
        <h2>📈 Метрики</h2>
        <div className="metrics-grid">
          <MetricCard title="Задач создано" value={result.metrics.tasks_generated} />
          <MetricCard title="Рисков найдено" value={result.metrics.risks_identified} />
          <MetricCard title="Приоритет" value={result.metrics.avg_task_priority} />
        </div>
      </section>

      <section className="result-section">
        <h2>📝 Задачи</h2>
        <div className="tasks-grid">
          {result.tasks.map((task, index) => {
            const trackerId = result.tracker_ids?.[index];
            const cacheKey = `idx_${index}`;
            const fuzzyData = fuzzyEvaluations[cacheKey];
            const isLoading = loadingTasks[cacheKey];
            
            return (
              <TaskCard
                key={task.id || index}
                task={task}
                trackerId={trackerId}
                fuzzyEvaluation={fuzzyData}
                loadingFuzzy={isLoading}
                onFetchFuzzy={() => fetchFuzzyEvaluation(trackerId, index)}
                onFeedbackSuccess={(data) => handleFeedbackSuccess(index, data)}
              />
            );
          })}
        </div>
      </section>

      <section className="result-section">
        <h2>⚠️ Риски</h2>
        <div className="risks-grid">
          {result.risks.map((risk, index) => (
            <RiskBadge key={index} risk={risk} />
          ))}
        </div>
      </section>
    </div>
  );
};

export default ResultsSection;
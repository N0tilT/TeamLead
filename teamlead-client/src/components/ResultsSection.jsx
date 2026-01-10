import React from 'react';
import MetricCard from './MetricCard';
import TaskCard from './TaskCard';
import RiskBadge from './RiskBadge';

const ResultsSection = ({ result }) => {
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
          {result.tasks.map((task, index) => (
            <TaskCard key={task.id} task={task} trackerId={result.tracker_ids?.[index]} />
          ))}
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
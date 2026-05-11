// src/components/TaskCard.jsx
import React, { useState } from 'react';
const getTaskTypeColor = (type) => {
  switch (type?.toLowerCase()) {
    case 'доработка':
    case 'feature': return '#2196F3';
    case 'исправление бага':
    case 'bugfix': return '#f44336';
    case 'обновление документации':
    case 'docs': return '#4CAF50';
    case 'tech_debt': return '#9C27B0';
    default: return '#9E9E9E';
  }
};

const TaskCard = ({ 
  task, 
  trackerId,
  fuzzyEvaluation,
  loadingFuzzy = false,
  onFetchFuzzy,
  onFeedbackSuccess 
}) => {
  const [showFeedback, setShowFeedback] = useState(false);
  const [actualEffort, setActualEffort] = useState('');
  const [actualRisk, setActualRisk] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState({ type: '', text: '' });

  const handleFeedbackSubmit = async (e) => {
    e.preventDefault();
    if (!actualEffort && !actualRisk) {
      setFeedbackMsg({ type: 'error', text: 'Заполните хотя бы одно поле' });
      return;
    }

    setSubmitting(true);
    setFeedbackMsg({ type: '', text: '' });

    try {
      const payload = {
        task_id: trackerId,
        code_changes_lines: fuzzyEvaluation?.inputs?.volume || 0,
        dependencies_count: fuzzyEvaluation?.inputs?.dependencies || 0,
        team_expertise: fuzzyEvaluation?.inputs?.expertise || 3,
        requirement_uncertainty_pct: fuzzyEvaluation?.inputs?.uncertainty || 50,
        task_type: fuzzyEvaluation?.task_type || task.task_type || 'feature',
        actual_effort_hours: actualEffort ? parseFloat(actualEffort) : null,
        actual_risk_score: actualRisk ? parseFloat(actualRisk) : null,
      };

      const response = await fetch('/fuzzy/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || 'Ошибка отправки фидбека');
      }

      const result = await response.json();
      setFeedbackMsg({ 
        type: 'success', 
        text: `Фидбэк сохранён! Образцов: ${result.total_samples}` 
      });
      
      if (onFeedbackSuccess) onFeedbackSuccess(result);
      
      setTimeout(() => {
        setShowFeedback(false);
        setActualEffort('');
        setActualRisk('');
        setFeedbackMsg({ type: '', text: '' });
      }, 2000);
      
    } catch (error) {
      setFeedbackMsg({ type: 'error', text: `⚠️ ${error.message}` });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="task-card">
      <div className="task-header">
        <h4>{task.title}</h4>
        <div className="task-tags">
          <span 
            className="task-type" 
            style={{ backgroundColor: getTaskTypeColor(task.task_type) }}
          >
            {task.task_type}
          </span>
          <span className={`task-priority priority ${task.priority?.toLowerCase()}`}>
            {task.priority}
          </span>
        </div>
      </div>
      
      <p className="task-description">{task.description}</p>
      
      <div className="acceptance-criteria">
        <strong>Критерии приемки:</strong>
        <ul>
          {task.acceptance_criteria?.map((criteria, index) => (
            <li key={index}>✓ {criteria}</li>
          ))}
        </ul>
      </div>

      {trackerId && (
        <a 
          href={`https://tracker.yandex.ru/${trackerId}`} 
          target="_blank" 
          rel="noopener noreferrer" 
          className="tracker-link"
        >
          Открыть в Tracker ({trackerId})
        </a>
      )}

      <div className="fuzzy-section">
        <div className="fuzzy-header">
          <span className="fuzzy-title">🧠 Оценка агента</span>
          {fuzzyEvaluation ? (
            <button 
              className="toggle-feedback-btn"
              onClick={() => setShowFeedback(!showFeedback)}
            >
              {showFeedback ? '✕ Скрыть' : '📝 Фидбэк'}
            </button>
          ) : (
            <button 
              className="fetch-fuzzy-btn"
              onClick={onFetchFuzzy}
              disabled={loadingFuzzy}
            >
              {loadingFuzzy ? '⏳ Загрузка...' : '🔄 Загрузить оценку'}
            </button>
          )}
        </div>

        {fuzzyEvaluation && (
          <>
            <div className="fuzzy-scores">
              <div className="fuzzy-score complexity">
                <span className="score-label">Сложность</span>
                <span className="score-value">
                  {fuzzyEvaluation.complexity_score?.toFixed(1) || '—'}
                </span>
              </div>
              <div className="fuzzy-score risk">
                <span className="score-label">Риск</span>
                <span className="score-value">
                  {fuzzyEvaluation.risk_score?.toFixed(1) || '—'}
                </span>
              </div>
            </div>

            {/* 🔽 Раскрывающаяся форма фидбека */}
            {showFeedback && (
              <form onSubmit={handleFeedbackSubmit} className="feedback-form">
                <div className="feedback-row">
                  <div className="feedback-field">
                    <label>Факт. сложность (часы)</label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      step="0.1"
                      value={actualEffort}
                      onChange={(e) => setActualEffort(e.target.value)}
                      placeholder="0–100"
                      disabled={submitting}
                    />
                  </div>
                  <div className="feedback-field">
                    <label>Факт. риск (0–100)</label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      step="0.1"
                      value={actualRisk}
                      onChange={(e) => setActualRisk(e.target.value)}
                      placeholder="0–100"
                      disabled={submitting}
                    />
                  </div>
                </div>

                {feedbackMsg.text && (
                  <div className={`feedback-message ${feedbackMsg.type}`}>
                    {feedbackMsg.text}
                  </div>
                )}

                <button 
                  type="submit" 
                  disabled={submitting}
                  className="submit-feedback-btn"
                >
                  {submitting ? 'Отправка...' : '📤 Отправить фидбэк'}
                </button>
              </form>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default TaskCard;
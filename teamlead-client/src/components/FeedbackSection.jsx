// src/components/FeedbackSection.jsx
import React, { useState } from 'react';
import './FeedbackSection.css';

const FeedbackSection = ({ 
  taskId, 
  predictedComplexity, 
  predictedRisk, 
  originalInputs,
  taskType = "feature",
  onSubmitSuccess 
}) => {
  const [actualEffort, setActualEffort] = useState('');
  const [actualRisk, setActualRisk] = useState('');
  const [userRating, setUserRating] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage({ type: '', text: '' });

    try {
      const payload = {
        task_id: taskId,
        code_changes_lines: originalInputs?.volume || 0,
        dependencies_count: originalInputs?.dependencies || 0,
        team_expertise: originalInputs?.expertise || 3,
        requirement_uncertainty_pct: originalInputs?.uncertainty || 50,
        task_type: taskType,
        actual_effort_hours: actualEffort ? parseFloat(actualEffort) : null,
        actual_risk_score: actualRisk ? parseFloat(actualRisk) : null,
      };

      const response = await fetch('/fuzzy/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Ошибка отправки фидбека');
      }

      const result = await response.json();
      setMessage({ 
        type: 'success', 
        text: `✅ Фидбэк сохранён! Всего образцов: ${result.total_samples}` 
      });
      
      if (onSubmitSuccess) onSubmitSuccess(result);
      
      // Очистка полей после успешной отправки
      setActualEffort('');
      setActualRisk('');
      setUserRating('');
      
    } catch (error) {
      setMessage({ type: 'error', text: `⚠️ ${error.message}` });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="feedback-section">
      <h4>📊 Оценка нечёткого агента</h4>
      
      <div className="predicted-scores">
        <div className="score-card complexity">
          <span className="label">Сложность (прогноз)</span>
          <span className="value">{predictedComplexity?.toFixed(1) || '—'}</span>
        </div>
        <div className="score-card risk">
          <span className="label">Риск (прогноз)</span>
          <span className="value">{predictedRisk?.toFixed(1) || '—'}</span>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="feedback-form">
        <div className="form-row">
          <div className="form-group">
            <label>Фактическая сложность (часы)</label>
            <input
              type="number"
              min="0"
              max="500"
              step="0.1"
              value={actualEffort}
              onChange={(e) => setActualEffort(e.target.value)}
              placeholder="0–500"
              disabled={loading}
            />
          </div>
          <div className="form-group">
            <label>Фактический риск (0–100)</label>
            <input
              type="number"
              min="0"
              max="100"
              step="0.1"
              value={actualRisk}
              onChange={(e) => setActualRisk(e.target.value)}
              placeholder="0–100"
              disabled={loading}
            />
          </div>
        </div>

        <button 
          type="submit" 
          disabled={loading || (!actualEffort && !actualRisk)}
          className="submit-feedback-btn"
        >
          {loading ? 'Отправка...' : 'Отправить фидбэк'}
        </button>
      </form>
    </div>
  );
};

export default FeedbackSection;
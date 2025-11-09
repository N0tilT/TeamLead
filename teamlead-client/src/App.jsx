import React, { useState } from 'react';
import './App.css';

function App() {
  const [changeRequest, setChangeRequest] = useState({
    old_text: '',
    new_text: '', 
    comments: ''
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(changeRequest),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error('Error:', error);
      setError('Ошибка при анализе изменений. Проверьте подключение к серверу.');
    } finally {
      setLoading(false);
    }
  };

  const RiskBadge = ({ risk }) => {
    const getRiskColor = (impact) => {
      switch (impact) {
        case 'High': return '#ff4444';
        case 'Medium': return '#ffaa00';
        case 'Low': return '#44ff44';
        default: return '#888888';
      }
    };

    const getProbabilityColor = (probability) => {
      switch (probability) {
        case 'High': return '#ff4444';
        case 'Medium': return '#ffaa00';
        case 'Low': return '#44ff44';
        default: return '#888888';
      }
    };

    return (
      <div className="risk-card" style={{ borderLeft: `4px solid ${getRiskColor(risk.impact)}` }}>
        <div className="risk-header">
          <h4>{risk.category}</h4>
          <div className="risk-indicators">
            <span 
              className="risk-indicator" 
              style={{ backgroundColor: getProbabilityColor(risk.probability) }}
            >
              Вероятность: {risk.probability}
            </span>
            <span 
              className="risk-indicator"
              style={{ backgroundColor: getRiskColor(risk.impact) }}
            >
              Влияние: {risk.impact}
            </span>
          </div>
        </div>
        <p className="risk-description">{risk.description}</p>
        <div className="risk-mitigation">
          <strong>Снижение риска:</strong> {risk.mitigation}
        </div>
      </div>
    );
  };

  const TaskCard = ({ task }) => {
    const getTaskTypeColor = (type) => {
      switch (type) {
        case 'доработка': return '#2196F3';
        case 'исправление бага': return '#f44336';
        case 'обновление документации': return '#4CAF50';
        default: return '#9E9E9E';
      }
    };

    const getPriorityColor = (priority) => {
      switch (priority) {
        case 'High': return '#f44336';
        case 'Medium': return '#ff9800';
        case 'Low': return '#4caf50';
        default: return '#9E9E9E';
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
            <span 
              className="task-priority"
              style={{ color: getPriorityColor(task.priority) }}
            >
              {task.priority} priority
            </span>
          </div>
        </div>
        <p className="task-description">{task.description}</p>
        <div className="acceptance-criteria">
          <strong>Критерии приемки:</strong>
          <ul>
            {task.acceptance_criteria.map((criteria, index) => (
              <li key={index}>✓ {criteria}</li>
            ))}
          </ul>
        </div>
      </div>
    );
  };

  const MetricCard = ({ title, value, subtitle }) => (
    <div className="metric-card">
      <h3>{title}</h3>
      <div className="metric-value">{value}</div>
      {subtitle && <div className="metric-subtitle">{subtitle}</div>}
    </div>
  );

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1>Ассистент Менеджера Команды</h1>
          <p>Автоматический анализ изменений документации и генерация задач</p>
        </div>
      </header>

      <div className="container">
        <form onSubmit={handleSubmit} className="change-form">
          <div className="form-section">
            <h2>📄 Ввод изменений документации</h2>
            
            <div className="form-group">
              <label>Исходный текст документации:</label>
              <textarea
                value={changeRequest.old_text}
                onChange={(e) => setChangeRequest({...changeRequest, old_text: e.target.value})}
                rows={6}
                placeholder="Введите оригинальный текст документации..."
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label>Измененная документация:</label>
              <textarea
                value={changeRequest.new_text}
                onChange={(e) => setChangeRequest({...changeRequest, new_text: e.target.value})}
                rows={6}
                placeholder="Введите измененный текст документации..."
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label>Комментарии к изменениям:</label>
              <textarea
                value={changeRequest.comments}
                onChange={(e) => setChangeRequest({...changeRequest, comments: e.target.value})}
                rows={3}
                placeholder="Пояснения, причины изменений, дополнительные контекст..."
                disabled={loading}
              />
            </div>

            <button type="submit" disabled={loading} className="submit-button">
              {loading ? (
                <>
                  <div className="spinner"></div>
                  Анализ изменений...
                </>
              ) : (
                '🚀 Проанализировать изменения'
              )}
            </button>
          </div>
        </form>

        {error && (
          <div className="error-message">
            ⚠️ {error}
          </div>
        )}

        {result && (
          <div className="results">
            <section className="result-section">
              <h2>📋 Анализ изменений</h2>
              <div className="summary-card">
                <div className="section-icon">🔍</div>
                <p>{result.change_summary}</p>
              </div>
            </section>

            <section className="result-section">
              <h2>📈 Метрики анализа</h2>
              <div className="metrics-grid">
                <MetricCard 
                  title="Всего анализов" 
                  value={result.metrics.analysis_count}
                  subtitle="за все время"
                />
                <MetricCard 
                  title="Сгенерировано задач" 
                  value={result.metrics.tasks_generated}
                  subtitle="в этом анализе"
                />
                <MetricCard 
                  title="Высокорисковых задач" 
                  value={result.metrics.high_priority_risks}
                  subtitle="требуют внимания"
                />
                <MetricCard 
                  title="Типы задач" 
                  value={result.metrics.task_types.length}
                  subtitle={result.metrics.task_types.join(', ')}
                />
              </div>
            </section>

            <section className="result-section">
              <div className="section-header">
                <h2>📝 Сгенерированные задачи</h2>
                <span className="badge">{result.tasks.length}</span>
              </div>
              <div className="tasks-grid">
                {result.tasks.map((task) => (
                  <TaskCard key={task.id} task={task} />
                ))}
              </div>
            </section>

            <section className="result-section">
              <div className="section-header">
                <h2>⚠️ Анализ рисков</h2>
                <span className="badge">{result.risks.length}</span>
              </div>
              <div className="risks-grid">
                {result.risks.map((risk, index) => (
                  <RiskBadge key={index} risk={risk} />
                ))}
              </div>
            </section>

            <section className="result-section">
              <h2>📊 Итоговый отчет</h2>
              <div className="description-card">
                <div className="section-icon">📋</div>
                <p>{result.overall_description}</p>
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
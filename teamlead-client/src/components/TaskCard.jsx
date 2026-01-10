import React from 'react';

const getTaskTypeColor = (type) => {
  switch (type) {
    case 'доработка': return '#2196F3';
    case 'исправление бага': return '#f44336';
    case 'обновление документации': return '#4CAF50';
    default: return '#9E9E9E';
  }
};

const TaskCard = ({ task, trackerId }) => {
  return (
    <div className="task-card">
      <div className="task-header">
        <h4>{task.title}</h4>
        <div className="task-tags">
          <span className="task-type" style={{ backgroundColor: getTaskTypeColor(task.task_type) }}>
            {task.task_type}
          </span>
          <span className="task-priority">{task.priority} priority</span>
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
      {trackerId && (
        <a href={`https://tracker.yandex.ru/${trackerId}`} target="_blank" rel="noopener noreferrer" className="tracker-link">
          Открыть в Tracker ({trackerId})
        </a>
      )}
    </div>
  );
};

export default TaskCard;
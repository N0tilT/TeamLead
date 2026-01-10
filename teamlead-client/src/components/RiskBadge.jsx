import React from 'react';

const getRiskColor = (impact) => {
  switch (impact) {
    case 'High': return '#ff4444';
    case 'Medium': return '#ffaa00';
    case 'Low': return '#44ff44';
    default: return '#888888';
  }
};

const RiskBadge = ({ risk }) => {
  return (
    <div className="risk-card" style={{ borderLeft: `4px solid ${getRiskColor(risk.impact)}` }}>
      <div className="risk-header">
        <h4>{risk.category}</h4>
        <div className="risk-indicators">
          <span className="risk-indicator" style={{ backgroundColor: getRiskColor(risk.probability) }}>
            Вероятность: {risk.probability}
          </span>
          <span className="risk-indicator" style={{ backgroundColor: getRiskColor(risk.impact) }}>
            Влияние: {risk.impact}
          </span>
        </div>
      </div>
      <p className="risk-description">{risk.description}</p>
      <div className="risk-mitigation">
        <strong>Снижение риска:</strong> {Array.isArray(risk.mitigation) ? risk.mitigation.join(', ') : risk.mitigation}
      </div>
    </div>
  );
};

export default RiskBadge;
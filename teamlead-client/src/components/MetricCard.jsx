import React from 'react';

const MetricCard = ({ title, value, subtitle }) => (
  <div className="metric-card">
    <h3>{title}</h3>
    <div className="metric-value">{value}</div>
    {subtitle && <div className="metric-subtitle">{subtitle}</div>}
  </div>
);

export default MetricCard;
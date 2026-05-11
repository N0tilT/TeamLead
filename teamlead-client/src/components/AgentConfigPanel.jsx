// src/components/AgentConfigPanel.jsx
import React, { useState, useEffect } from 'react';

const AgentConfigPanel = ({ agentType = 'all' }) => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  const fetchConfig = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/fuzzy/config/export?agent=${agentType}`);
      const data = await res.json();
      setConfig(data);
    } catch (e) {
      setMessage({ type: 'error', text: 'Ошибка загрузки конфигурации' });
    }
    setLoading(false);
  };

  const handleExport = () => {
    if (!config) return;
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `fuzzy-config-${agentType}-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImport = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    try {
      const configData = JSON.parse(await file.text());
      const res = await fetch(`/fuzzy/config/import?agent=${agentType}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config: configData })
      });
      
      if (!res.ok) throw new Error('Импорт не удался');
      setMessage({ type: 'success', text: '✅ Конфигурация применена!' });
      fetchConfig(); // обновить отображение
    } catch (err) {
      setMessage({ type: 'error', text: `⚠️ ${err.message}` });
    }
  };

  return (
    <div className="config-panel">
      <div className="config-actions">
        <button onClick={fetchConfig} disabled={loading}>
          {loading ? 'Загрузка...' : '📥 Загрузить конфиг'}
        </button>
        <button onClick={handleExport} disabled={!config}>
          📤 Экспорт
        </button>
        <label className="import-btn">
          📁 Импорт
          <input type="file" accept=".json" onChange={handleImport} hidden />
        </label>
      </div>
      {message.text && <div className={`config-message ${message.type}`}>{message.text}</div>}
      {config && (
        <pre className="config-preview">
          {JSON.stringify(config, null, 2).slice(0, 500)}...
        </pre>
      )}
    </div>
  );
};

export default AgentConfigPanel;
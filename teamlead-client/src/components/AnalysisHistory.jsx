import React, { useEffect, useState } from 'react';
import { fetchResultsList } from '../api';
import ResultsSection from './ResultsSection';

const AnalysisHistory = ({ refreshTrigger }) => {
  const [history, setHistory] = useState([]);
  const [selectedAnalysis, setSelectedAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const data = await fetchResultsList();
      setHistory(Array.isArray(data) ? data.reverse() : []);
    } catch (err) {
      console.error("History load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, [refreshTrigger]);

  return (
    <div className="history-container">
      <div className="history-sidebar">
        <h3>История анализов</h3>
        {loading && <div className="spinner-small">Загрузка...</div>}
        <div className="history-list">
          {history.map((item) => (
            <div 
              key={item.tracking_id} 
              className={`history-item ${selectedAnalysis?.tracking_id === item.tracking_id ? 'active' : ''}`}
              onClick={() => setSelectedAnalysis(item)}
            >
              <div className="item-date">
                ID: {item.tracking_id.slice(0, 8)}...
              </div>
              <div className="item-summary">
                {item.change_summary?.slice(0, 60)}...
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="history-details">
        {selectedAnalysis ? (
          <>
            <button className="close-details" onClick={() => setSelectedAnalysis(null)}>✕ Закрыть</button>
            <ResultsSection result={selectedAnalysis} />
          </>
        ) : (
          <div className="empty-state">Выберите анализ из списка для просмотра деталей</div>
        )}
      </div>
    </div>
  );
};

export default AnalysisHistory;
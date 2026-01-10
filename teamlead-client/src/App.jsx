import React, { useState } from 'react';
import useLocalStorage from './hooks/useLocalStorage';
import useAnalysis from './hooks/useAnalysis';
import ChangeForm from './components/ChangeForm';
import ResultsSection from './components/ResultsSection';
import AnalysisHistory from './components/AnalysisHistory';
import './App.css';

function App() {
  const [changeRequest, setChangeRequest] = useLocalStorage('changeRequest', {
    old_text: '',
    new_text: '',
    comments: '',
  });
  
  const [storedResult, setStoredResult] = useLocalStorage('analysisResult', null);
  const [storedTrackingId, setStoredTrackingId] = useLocalStorage('trackingId', null);
  const [refreshHistory, setRefreshHistory] = useState(0);
  
  const {
    result,
    trackingId,
    loading,
    error,
    submitAnalysis,
    resetAnalysis,
  } = useAnalysis();

  const handleSubmit = async (e) => {
    e.preventDefault();
    await submitAnalysis(changeRequest);
    setRefreshHistory(prev => prev + 1);
  };

  const handleReset = () => {
    localStorage.clear();
    setChangeRequest({ old_text: '', new_text: '', comments: '' });
    resetAnalysis();
  };

  const updateChangeRequest = (field, value) => {
    setChangeRequest(prev => ({ ...prev, [field]: value }));
  };

  const displayResult = result || storedResult;

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1>Ассистент Менеджера Команды</h1>
          <button onClick={handleReset} className="reset-button">Новый анализ</button>
        </div>
      </header>

      <main className="main-layout">
        <section className="left-panel">
          <ChangeForm
            changeRequest={changeRequest}
            onUpdate={updateChangeRequest}
            loading={loading}
            onSubmit={handleSubmit}
          />
          {error && <div className="error-message">⚠️ {error}</div>}
          {trackingId && !displayResult && (
            <div className="loading-message">Обработка запроса {trackingId}...</div>
          )}
          {displayResult && (
            <div className="current-result">
              <h2>Текущий результат</h2>
              <ResultsSection result={displayResult} />
            </div>
          )}
        </section>

        <section className="right-panel">
          <AnalysisHistory refreshTrigger={refreshHistory} />
        </section>
      </main>
    </div>
  );
}

export default App;
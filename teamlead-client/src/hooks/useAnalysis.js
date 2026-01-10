import { useState, useEffect, useCallback } from 'react';
import { enqueueChangeRequest, fetchResult, createWebSocket } from '../api';

function useAnalysis() {
  const [result, setResult] = useState(null);
  const [trackingId, setTrackingId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const checkStatus = async () => {
      if (trackingId && !result) {
        try {
          const data = await fetchResult(trackingId);
          if (data && data.tasks) {
            setResult(data);
          }
        } catch (err) {
          console.error('Fetch error:', err);
        }
      }
    };
    checkStatus();
  }, [trackingId, result]);

  useEffect(() => {
    if (trackingId && !result) {
      const ws = createWebSocket(trackingId, setResult, setError);
      return () => ws.close();
    }
  }, [trackingId, result]);

  const submitAnalysis = useCallback(async (changeRequest) => {
    setLoading(true);
    setError('');
    setResult(null);
    setTrackingId(null);
    
    try {
      const data = await enqueueChangeRequest(changeRequest);
      setTrackingId(data.tracking_id);
    } catch (error) {
      setError('Ошибка при отправке данных.');
    } finally {
      setLoading(false);
    }
  }, []);

  const resetAnalysis = useCallback(() => {
    setResult(null);
    setTrackingId(null);
    setError('');
  }, []);

  return {
    result,
    trackingId,
    loading,
    error,
    submitAnalysis,
    resetAnalysis,
    setResult,
    setTrackingId,
  };
}

export default useAnalysis;
const API_BASE = '';

export const enqueueChangeRequest = async (changeRequest) => {
  const response = await fetch(`${API_BASE}/api/enqueue`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(changeRequest),
  });
  
  if (!response.ok) throw new Error('Network response was not ok');
  return response.json();
};

export const fetchResult = async (trackingId) => {
  const response = await fetch(`${API_BASE}/api/result/${trackingId}`);
  if (!response.ok) throw new Error('Network response was not ok');
  return response.json();
};

export const fetchResultsList = async () => {
  const response = await fetch(`${API_BASE}/api/result-list`);
  if (!response.ok) throw new Error('Ошибка при загрузке списка');
  const data = await response.json();
  return typeof data === 'string' ? JSON.parse(data) : data;
};

export const createWebSocket = (trackingId, onMessage, onError) => {
  const ws = new WebSocket(`ws://${window.location.host}/ws/${trackingId}`);
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (err) {
      console.error('WS parse error:', err);
    }
  };
  
  ws.onerror = () => onError('WebSocket connection error');
  return ws;
};
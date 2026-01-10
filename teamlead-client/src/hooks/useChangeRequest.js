import { useState, useCallback } from 'react';

function useChangeRequest() {
  const [changeRequest, setChangeRequest] = useState({
    old_text: '',
    new_text: '',
    comments: '',
  });

  const updateField = useCallback((field, value) => {
    setChangeRequest(prev => ({ ...prev, [field]: value }));
  }, []);

  const reset = useCallback(() => {
    setChangeRequest({ old_text: '', new_text: '', comments: '' });
  }, []);

  return { changeRequest, updateField, reset, setChangeRequest };
}

export default useChangeRequest;
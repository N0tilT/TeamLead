import React from 'react';

const ChangeForm = ({ changeRequest, onUpdate, loading, onSubmit }) => {
  const handleChange = (field) => (e) => {
    onUpdate(field, e.target.value);
  };

  return (
    <form onSubmit={onSubmit} className="change-form">
      <div className="form-section">
        <h2>📄 Ввод изменений</h2>
        <div className="form-group">
          <label>Исходный текст:</label>
          <textarea
            value={changeRequest.old_text}
            onChange={handleChange('old_text')}
            rows={4}
            disabled={loading}
          />
        </div>
        <div className="form-group">
          <label>Новый текст:</label>
          <textarea
            value={changeRequest.new_text}
            onChange={handleChange('new_text')}
            rows={4}
            disabled={loading}
          />
        </div>
        <div className="form-group">
          <label>Комментарии:</label>
          <textarea
            value={changeRequest.comments}
            onChange={handleChange('comments')}
            rows={2}
            disabled={loading}
          />
        </div>
        <button type="submit" disabled={loading} className="submit-button">
          {loading ? 'Анализ...' : '🚀 Проанализировать'}
        </button>
      </div>
    </form>
  );
};

export default ChangeForm;
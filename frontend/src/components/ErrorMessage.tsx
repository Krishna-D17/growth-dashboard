import React from 'react';

interface ErrorMessageProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export const ErrorMessage: React.FC<ErrorMessageProps> = ({
  title = 'Data Fetch Error',
  message,
  onRetry,
}) => {
  return (
    <div className="error-card">
      <div className="error-icon">⚠️</div>
      <div className="error-body">
        <h3 className="error-title">{title}</h3>
        <p className="error-message">{message}</p>
        {onRetry && (
          <button type="button" className="btn btn-sm btn-secondary" onClick={onRetry}>
            Retry Request
          </button>
        )}
      </div>
    </div>
  );
};

import React from 'react';

export const LoadingSkeleton: React.FC = () => {
  return (
    <div className="skeleton-grid">
      <div className="skeleton-card"></div>
      <div className="skeleton-card"></div>
      <div className="skeleton-card"></div>
      <div className="skeleton-card"></div>
    </div>
  );
};

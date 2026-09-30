import React from 'react';

interface ChartCardProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}

export const ChartCard: React.FC<ChartCardProps> = ({ title, subtitle, children }) => {
  return (
    <div className="section-card chart-card">
      <div className="chart-card-header">
        <h3 className="section-title">{title}</h3>
        {subtitle && <p className="section-desc">{subtitle}</p>}
      </div>
      <div className="chart-card-body">{children}</div>
    </div>
  );
};

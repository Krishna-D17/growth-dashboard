import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import type { AnomalyResult } from '../../types';

interface AnomaliesSeverityChartProps {
  anomalies: AnomalyResult[];
}

const SEVERITY_COLORS: Record<string, string> = {
  LOW: '#3b82f6',
  MEDIUM: '#f59e0b',
  HIGH: '#f43f5e',
};

export const AnomaliesSeverityChart: React.FC<AnomaliesSeverityChartProps> = ({ anomalies }) => {
  if (!anomalies || anomalies.length === 0) {
    return (
      <div className="chart-empty-state">
        <p className="text-muted">No growth anomalies detected for this profile baseline.</p>
      </div>
    );
  }

  const counts: Record<string, number> = {
    LOW: 0,
    MEDIUM: 0,
    HIGH: 0,
  };

  anomalies.forEach((a) => {
    const sev = (a.severity || 'low').toUpperCase();
    if (sev in counts) {
      counts[sev] += 1;
    } else {
      counts[sev] = 1;
    }
  });

  const data = [
    { name: 'Low Severity', key: 'LOW', count: counts.LOW, color: SEVERITY_COLORS.LOW },
    { name: 'Medium Severity', key: 'MEDIUM', count: counts.MEDIUM, color: SEVERITY_COLORS.MEDIUM },
    { name: 'High Severity', key: 'HIGH', count: counts.HIGH, color: SEVERITY_COLORS.HIGH },
  ].filter((item) => item.count > 0);

  if (data.length === 0) {
    return (
      <div className="chart-empty-state">
        <p className="text-muted">No severity breakdown available.</p>
      </div>
    );
  }

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const item = payload[0].payload;
      return (
        <div className="chart-tooltip">
          <p className="tooltip-title">{item.name}</p>
          <p className="tooltip-value">
            Detected Events: <strong>{item.count}</strong>
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div style={{ width: '100%', height: 220 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 15, right: 20, left: 0, bottom: 15 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis dataKey="name" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} />
          <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} allowDecimals={false} />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="count" radius={[6, 6, 0, 0]}>
            {data.map((entry, index) => (
              <Cell key={`cell-sev-${index}`} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

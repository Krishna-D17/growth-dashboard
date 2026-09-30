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
import type { FrequencyAnalytics } from '../../types';
import { formatNumber } from '../../utils/formatters';

interface FrequencyDistributionChartProps {
  frequency: FrequencyAnalytics | null;
  type: 'weekday' | 'hourly';
}

export const FrequencyDistributionChart: React.FC<FrequencyDistributionChartProps> = ({
  frequency,
  type,
}) => {
  if (!frequency) {
    return (
      <div className="chart-empty-state">
        <p className="text-muted">No publishing frequency data available.</p>
      </div>
    );
  }

  if (type === 'weekday') {
    const rawData = frequency.weekday_distribution || {};
    const entries = Object.entries(rawData);
    const hasData = entries.some(([, count]) => count > 0);

    if (!hasData || entries.length === 0) {
      return (
        <div className="chart-empty-state">
          <p className="text-muted">No weekday posting timestamps recorded yet.</p>
        </div>
      );
    }

    const data = entries.map(([day, count]) => ({
      name: day.substring(0, 3),
      fullName: day,
      count,
    }));

    const CustomTooltip = ({ active, payload }: any) => {
      if (active && payload && payload.length) {
        const item = payload[0].payload;
        return (
          <div className="chart-tooltip">
            <p className="tooltip-title">{item.fullName}</p>
            <p className="tooltip-value">
              Posts Published: <strong>{formatNumber(item.count)}</strong>
            </p>
          </div>
        );
      }
      return null;
    };

    return (
      <div style={{ width: '100%', height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 15, right: 15, left: 0, bottom: 15 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis dataKey="name" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} />
            <YAxis
              stroke="#94a3b8"
              tick={{ fill: '#94a3b8', fontSize: 12 }}
              allowDecimals={false}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="count" fill="#06b6d4" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // Hourly distribution
  const rawHourly = frequency.hourly_distribution || {};
  const entries = Object.entries(rawHourly);
  const hasData = entries.some(([, count]) => count > 0);

  if (!hasData || entries.length === 0) {
    return (
      <div className="chart-empty-state">
        <p className="text-muted">No hourly posting timestamps recorded yet.</p>
      </div>
    );
  }

  const data = Array.from({ length: 24 }, (_, i) => {
    const rawMap = rawHourly as Record<string | number, number>;
    const count = Number(rawMap[i] ?? rawMap[String(i)] ?? 0);
    return {
      hour: `${String(i).padStart(2, '0')}:00`,
      count,
    };
  });

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const item = payload[0].payload;
      return (
        <div className="chart-tooltip">
          <p className="tooltip-title">{item.hour} UTC</p>
          <p className="tooltip-value">
            Posts Published: <strong>{formatNumber(item.count)}</strong>
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div style={{ width: '100%', height: 260 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 15, right: 15, left: 0, bottom: 15 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis
            dataKey="hour"
            stroke="#94a3b8"
            tick={{ fill: '#94a3b8', fontSize: 10 }}
            interval={2}
          />
          <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} allowDecimals={false} />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]}>
            {data.map((entry, index) => (
              <Cell
                key={`cell-h-${index}`}
                fill={entry.count > 0 ? '#6366f1' : 'rgba(255,255,255,0.05)'}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

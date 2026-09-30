import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { ProfileComparisonItem } from '../../types';
import { formatNumber } from '../../utils/formatters';

interface ComparisonMetricsChartProps {
  profiles: ProfileComparisonItem[];
  metricKey: 'current_followers' | 'average_engagement' | 'posts_per_week' | 'growth_7d';
  title: string;
}

// Neutral, distinct colors for profiles without rank implications
const PROFILE_COLORS = ['#06b6d4', '#6366f1', '#8b5cf6', '#10b981', '#f59e0b', '#ec4899'];

export const ComparisonMetricsChart: React.FC<ComparisonMetricsChartProps> = ({
  profiles,
  metricKey,
  title,
}) => {
  if (!profiles || profiles.length === 0) {
    return (
      <div className="chart-empty-state">
        <p className="text-muted">Select target profiles to render cross-profile comparison.</p>
      </div>
    );
  }

  const data = profiles.map((p, idx) => ({
    username: `@${p.username}`,
    platform: p.platform.toUpperCase(),
    value: p[metricKey] !== null ? p[metricKey] : null,
    color: PROFILE_COLORS[idx % PROFILE_COLORS.length],
  }));

  const hasNonNullData = data.some((d) => d.value !== null);
  if (!hasNonNullData) {
    return (
      <div className="chart-empty-state">
        <p className="text-muted">No stored metric values available for the selected targets.</p>
      </div>
    );
  }

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const item = payload[0].payload;
      return (
        <div className="chart-tooltip">
          <p className="tooltip-title">
            {item.username} ({item.platform})
          </p>
          <p className="tooltip-value">
            {title}: <strong>{item.value !== null ? formatNumber(item.value) : 'N/A (Unavailable)'}</strong>
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="chart-container-box" style={{ marginBottom: '1.5rem' }}>
      <h4 className="chart-subhead">{title}</h4>
      <div style={{ width: '100%', height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 20, right: 30, left: 10, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis dataKey="username" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} />
            <YAxis
              stroke="#94a3b8"
              tick={{ fill: '#94a3b8', fontSize: 12 }}
              tickFormatter={(v) => formatNumber(v)}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="value" fill="#6366f1" radius={[6, 6, 0, 0]} name={title} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

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
import type { EngagementAnalytics } from '../../types';
import { formatNumber } from '../../utils/formatters';

interface EngagementBreakdownChartProps {
  engagement: EngagementAnalytics | null;
}

export const EngagementBreakdownChart: React.FC<EngagementBreakdownChartProps> = ({ engagement }) => {
  if (!engagement) {
    return (
      <div className="chart-empty-state">
        <p className="text-muted">No engagement data available.</p>
      </div>
    );
  }

  const rawMetrics = [
    { name: 'Likes', value: engagement.total_likes, color: '#06b6d4' },
    { name: 'Comments', value: engagement.total_comments, color: '#6366f1' },
    { name: 'Shares', value: engagement.total_shares, color: '#8b5cf6' },
    { name: 'Views', value: engagement.total_views, color: '#10b981' },
  ];

  // Only include metrics that are non-null
  const availableMetrics = rawMetrics.filter((m) => m.value !== null);

  if (availableMetrics.length === 0) {
    return (
      <div className="chart-empty-state">
        <p className="text-muted">No specific interaction component totals recorded for this platform profile.</p>
      </div>
    );
  }

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="chart-tooltip">
          <p className="tooltip-title">{data.name}</p>
          <p className="tooltip-value">
            Total Count: <strong>{formatNumber(data.value)}</strong>
          </p>
          <p className="tooltip-sub">
            Sample Base: <strong>{engagement.sample_post_count} posts</strong>
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div style={{ width: '100%', height: 280 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={availableMetrics} margin={{ top: 20, right: 30, left: 10, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis dataKey="name" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} />
          <YAxis
            stroke="#94a3b8"
            tick={{ fill: '#94a3b8', fontSize: 12 }}
            tickFormatter={(v) => formatNumber(v)}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="value" radius={[6, 6, 0, 0]}>
            {availableMetrics.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

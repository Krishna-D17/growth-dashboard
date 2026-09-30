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
import type { GrowthAnalytics } from '../../types';
import { formatNumber, formatPercent } from '../../utils/formatters';

interface GrowthSummaryChartProps {
  growth: GrowthAnalytics | null;
}

export const GrowthSummaryChart: React.FC<GrowthSummaryChartProps> = ({ growth }) => {
  if (!growth || (growth.growth_7d === null && growth.growth_30d === null && growth.absolute_growth === null)) {
    return (
      <div className="chart-empty-state">
        <p className="text-muted">No sufficient historical growth data available yet to display growth trends.</p>
      </div>
    );
  }

  const items = [
    {
      name: '7-Day Growth',
      value: growth.growth_7d,
      percent: growth.growth_percent_7d,
      color: '#06b6d4',
    },
    {
      name: '30-Day Growth',
      value: growth.growth_30d,
      percent: growth.growth_percent_30d,
      color: '#6366f1',
    },
    {
      name: 'Absolute Growth',
      value: growth.absolute_growth,
      percent: growth.growth_percent,
      color: '#8b5cf6',
    },
    {
      name: 'Daily Velocity',
      value: growth.growth_velocity,
      percent: null,
      unit: '/day',
      color: '#10b981',
    },
  ].filter((item) => item.value !== null);

  if (items.length === 0) {
    return (
      <div className="chart-empty-state">
        <p className="text-muted">No non-null historical data available.</p>
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
            Value: <strong>{formatNumber(data.value)}</strong> {data.unit || ''}
          </p>
          {data.percent !== null && (
            <p className="tooltip-sub">
              Change: <strong>{formatPercent(data.percent)}</strong>
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div style={{ width: '100%', height: 300 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={items} margin={{ top: 20, right: 30, left: 10, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis
            dataKey="name"
            stroke="#94a3b8"
            tick={{ fill: '#94a3b8', fontSize: 12 }}
            tickLine={false}
          />
          <YAxis
            stroke="#94a3b8"
            tick={{ fill: '#94a3b8', fontSize: 12 }}
            tickFormatter={(v) => formatNumber(v)}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="value" radius={[6, 6, 0, 0]}>
            {items.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

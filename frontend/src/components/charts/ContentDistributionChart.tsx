import React from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
} from 'recharts';
import type { ContentAnalytics } from '../../types';
import { formatNumber } from '../../utils/formatters';

interface ContentDistributionChartProps {
  content: ContentAnalytics | null;
  mode?: 'donut' | 'engagement' | 'both';
}

const CATEGORY_COLORS: Record<string, string> = {
  IMAGE: '#06b6d4',
  VIDEO: '#6366f1',
  REEL: '#8b5cf6',
  CAROUSEL: '#10b981',
  TEXT: '#f59e0b',
  LINK: '#f43f5e',
  THREAD: '#ec4899',
  UNKNOWN: '#64748b',
};

const DEFAULT_COLOR = '#94a3b8';

export const ContentDistributionChart: React.FC<ContentDistributionChartProps> = ({
  content,
  mode = 'both',
}) => {
  if (!content || !content.by_content_type || content.by_content_type.length === 0) {
    return (
      <div className="chart-empty-state">
        <p className="text-muted">No content classification data available for this profile.</p>
      </div>
    );
  }

  const pieData = content.by_content_type
    .filter((c) => c.post_count > 0)
    .map((c) => ({
      name: c.content_type,
      value: c.post_count,
      color: CATEGORY_COLORS[c.content_type.toUpperCase()] || DEFAULT_COLOR,
    }));

  const barData = content.by_content_type
    .filter((c) => c.average_engagement !== null)
    .map((c) => ({
      name: c.content_type,
      avgEngagement: c.average_engagement,
      medianEngagement: c.median_engagement,
      postCount: c.post_count,
      color: CATEGORY_COLORS[c.content_type.toUpperCase()] || DEFAULT_COLOR,
    }));

  const CustomPieTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0];
      const percent = content.total_posts > 0 ? ((data.value / content.total_posts) * 100).toFixed(1) : 0;
      return (
        <div className="chart-tooltip">
          <p className="tooltip-title">{data.name}</p>
          <p className="tooltip-value">
            Posts: <strong>{data.value}</strong> ({percent}%)
          </p>
        </div>
      );
    }
    return null;
  };

  const CustomBarTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="chart-tooltip">
          <p className="tooltip-title">{data.name}</p>
          <p className="tooltip-value">
            Avg Engagement: <strong>{formatNumber(data.avgEngagement)}</strong>
          </p>
          {data.medianEngagement !== null && (
            <p className="tooltip-sub">
              Median Engagement: <strong>{formatNumber(data.medianEngagement)}</strong>
            </p>
          )}
          <p className="tooltip-sub">
            Sample Count: <strong>{data.postCount} posts</strong>
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="content-charts-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {(mode === 'donut' || mode === 'both') && pieData.length > 0 && (
        <div className="chart-container-box">
          <h4 className="chart-subhead">Content Mix by Category</h4>
          <div style={{ width: '100%', height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={90}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} stroke="rgba(15,22,36,0.8)" strokeWidth={2} />
                  ))}
                </Pie>
                <Tooltip content={<CustomPieTooltip />} />
                <Legend
                  formatter={(value) => <span style={{ color: '#94a3b8', fontSize: 12 }}>{value}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {(mode === 'engagement' || mode === 'both') && barData.length > 0 && (
        <div className="chart-container-box">
          <h4 className="chart-subhead">Average Engagement by Content Type</h4>
          <div style={{ width: '100%', height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={barData} margin={{ top: 20, right: 20, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="name" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <YAxis
                  stroke="#94a3b8"
                  tick={{ fill: '#94a3b8', fontSize: 12 }}
                  tickFormatter={(v) => formatNumber(v)}
                />
                <Tooltip content={<CustomBarTooltip />} />
                <Bar dataKey="avgEngagement" radius={[6, 6, 0, 0]}>
                  {barData.map((entry, index) => (
                    <Cell key={`bar-cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
};

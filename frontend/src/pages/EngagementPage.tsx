import React, { useState, useEffect, useCallback } from 'react';
import type { EngagementAnalytics } from '../types';
import { fetchEngagementAnalytics } from '../api/client';
import { formatNumber, formatPercent } from '../utils/formatters';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { ErrorMessage } from '../components/ErrorMessage';
import { ChartCard, EngagementBreakdownChart } from '../components/charts';

interface EngagementPageProps {
  profileId: string;
  selectedDays?: number;
}

export const EngagementPage: React.FC<EngagementPageProps> = ({ profileId, selectedDays }) => {
  const [engagement, setEngagement] = useState<EngagementAnalytics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchEngagementAnalytics(profileId, selectedDays);
      setEngagement(data);
    } catch (err) {
      setError((err as Error).message || 'Failed to load engagement analytics');
    } finally {
      setLoading(false);
    }
  }, [profileId, selectedDays]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) return <LoadingSkeleton />;
  if (error) return <ErrorMessage message={error} onRetry={loadData} />;

  return (
    <div className="page-content">
      <div className="page-header-row">
        <div>
          <h2 className="page-title">Engagement Analytics</h2>
          <p className="page-subtitle">Content interaction metrics and engagement rate calculations.</p>
        </div>
      </div>

      {engagement && engagement.available_metrics.length === 0 && engagement.sample_post_count > 0 && (
        <div className="info-banner-small" style={{ marginBottom: '1.5rem' }}>
          ℹ️ Public web pages did not expose post-level interaction counts for this collection. Unavailable metrics are preserved as N/A.
        </div>
      )}

      <div className="metric-cards-grid">
        <div className="metric-card">
          <div className="metric-label">Total Engagement</div>
          <div className="metric-value">{formatNumber(engagement?.total_engagement)}</div>
          <div className="metric-sub">Sum of post interactions</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Average Engagement</div>
          <div className="metric-value">{formatNumber(engagement?.average_engagement)}</div>
          <div className="metric-sub">Mean / post</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Median Engagement</div>
          <div className="metric-value">{formatNumber(engagement?.median_engagement)}</div>
          <div className="metric-sub">Median post interaction</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Engagement Rate</div>
          <div className="metric-value">{formatPercent(engagement?.engagement_rate)}</div>
          <div className="metric-sub">(Total Engagement / Followers) * 100</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Total Likes</div>
          <div className="metric-value">{formatNumber(engagement?.total_likes)}</div>
          <div className="metric-sub">Observed likes</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Total Comments</div>
          <div className="metric-value">{formatNumber(engagement?.total_comments)}</div>
          <div className="metric-sub">Observed comments</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Total Shares</div>
          <div className="metric-value">{formatNumber(engagement?.total_shares)}</div>
          <div className="metric-sub">Observed shares / reposts</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Total Views</div>
          <div className="metric-value">{formatNumber(engagement?.total_views)}</div>
          <div className="metric-sub">Observed video views</div>
        </div>
      </div>

      <ChartCard
        title="Component Breakdown Visualization"
        subtitle="Observed interaction volumes by available component metric (excluding unavailable platform components)."
      >
        <EngagementBreakdownChart engagement={engagement} />
      </ChartCard>

      <div className="section-card" style={{ marginTop: '2rem' }}>
        <h3 className="section-title">Available Component Metrics</h3>
        <p className="section-desc">
          Platform collector exposed metrics for this profile target:
        </p>
        <div className="tag-cloud">
          {engagement && engagement.available_metrics.length > 0 ? (
            engagement.available_metrics.map((metric) => (
              <span key={metric} className="tag-item">
                ✓ {metric.toUpperCase()}
              </span>
            ))
          ) : (
            <span className="text-muted">No component metrics detected.</span>
          )}
        </div>
      </div>
    </div>
  );
};

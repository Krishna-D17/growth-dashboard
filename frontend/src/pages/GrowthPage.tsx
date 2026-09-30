import React, { useState, useEffect, useCallback } from 'react';
import type { GrowthAnalytics } from '../types';
import { fetchGrowthAnalytics } from '../api/client';
import { formatNumber, formatPercent, formatDate } from '../utils/formatters';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { ErrorMessage } from '../components/ErrorMessage';
import { ChartCard, GrowthSummaryChart } from '../components/charts';

interface GrowthPageProps {
  profileId: string;
  selectedDays?: number;
}

export const GrowthPage: React.FC<GrowthPageProps> = ({ profileId, selectedDays }) => {
  const [growth, setGrowth] = useState<GrowthAnalytics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchGrowthAnalytics(profileId, selectedDays);
      setGrowth(data);
    } catch (err) {
      setError((err as Error).message || 'Failed to load growth analytics');
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
          <h2 className="page-title">Follower Growth Analytics</h2>
          <p className="page-subtitle">Deterministic growth metrics derived from historical database snapshots.</p>
        </div>
      </div>

      <div className="metric-cards-grid">
        <div className="metric-card">
          <div className="metric-label">Current Followers</div>
          <div className="metric-value">{formatNumber(growth?.current_followers)}</div>
          <div className="metric-sub">As of {formatDate(growth?.end_date)}</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Previous Followers</div>
          <div className="metric-value">{formatNumber(growth?.previous_followers)}</div>
          <div className="metric-sub">Prior observation</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Absolute Growth</div>
          <div className="metric-value">{formatNumber(growth?.absolute_growth)}</div>
          <div className="metric-sub">Growth %: {formatPercent(growth?.growth_percent)}</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">7-Day Growth</div>
          <div className="metric-value">{formatNumber(growth?.growth_7d)}</div>
          <div className="metric-sub">{formatPercent(growth?.growth_percent_7d)} vs 7d snapshot</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">30-Day Growth</div>
          <div className="metric-value">{formatNumber(growth?.growth_30d)}</div>
          <div className="metric-sub">{formatPercent(growth?.growth_percent_30d)} vs 30d snapshot</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Growth Velocity</div>
          <div className="metric-value">{formatNumber(growth?.growth_velocity)}</div>
          <div className="metric-sub">Followers / Day</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Growth Acceleration</div>
          <div className="metric-value">{formatNumber(growth?.growth_acceleration)}</div>
          <div className="metric-sub">Followers / Day²</div>
        </div>
      </div>

      <ChartCard
        title="Follower Growth & Velocity Summary"
        subtitle="Observed follower growth, velocity, and delta metrics calculated strictly from snapshot observations."
      >
        <GrowthSummaryChart growth={growth} />
      </ChartCard>
    </div>
  );
};

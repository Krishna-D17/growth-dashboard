import React, { useState, useEffect, useCallback } from 'react';
import type { FrequencyAnalytics } from '../types';
import { fetchFrequencyAnalytics } from '../api/client';
import { formatNumber } from '../utils/formatters';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { ErrorMessage } from '../components/ErrorMessage';
import { ChartCard, FrequencyDistributionChart } from '../components/charts';

interface FrequencyPageProps {
  profileId: string;
  selectedDays?: number;
}

export const FrequencyPage: React.FC<FrequencyPageProps> = ({ profileId, selectedDays }) => {
  const [frequency, setFrequency] = useState<FrequencyAnalytics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchFrequencyAnalytics(profileId, selectedDays);
      setFrequency(data);
    } catch (err) {
      setError((err as Error).message || 'Failed to load frequency analytics');
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
          <h2 className="page-title">Posting Behavior &amp; Frequency</h2>
          <p className="page-subtitle">Descriptive observations of publishing cadence and interval metrics.</p>
        </div>
      </div>

      {frequency?.posts_per_day === null && (
        <div className="info-banner-small" style={{ marginBottom: '1.5rem' }}>
          ℹ️ Posts observed for this target, but publication timestamps are not exposed on public web pages for this platform.
        </div>
      )}

      <div className="metric-cards-grid">
        <div className="metric-card">
          <div className="metric-label">Posts / Day</div>
          <div className="metric-value">{formatNumber(frequency?.posts_per_day)}</div>
          <div className="metric-sub">Average daily cadence</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Posts / Week</div>
          <div className="metric-value">{formatNumber(frequency?.posts_per_week)}</div>
          <div className="metric-sub">Weekly cadence</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Posts / Month</div>
          <div className="metric-value">{formatNumber(frequency?.posts_per_month)}</div>
          <div className="metric-sub">Monthly cadence</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Avg Posting Interval</div>
          <div className="metric-value">{formatNumber(frequency?.avg_posting_interval_hours)} hrs</div>
          <div className="metric-sub">Between consecutive posts</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Median Interval</div>
          <div className="metric-value">{formatNumber(frequency?.median_posting_interval_hours)} hrs</div>
          <div className="metric-sub">Median gap</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Interval Range</div>
          <div className="metric-value">
            {formatNumber(frequency?.min_posting_interval_hours)} — {formatNumber(frequency?.max_posting_interval_hours)} hrs
          </div>
          <div className="metric-sub">Min to Max gap</div>
        </div>
      </div>

      {/* Frequency Visualization Grid */}
      <div className="grid-two-col" style={{ marginTop: '2rem' }}>
        <ChartCard
          title="Day of Week Distribution"
          subtitle="Frequency of post publishing across days of the week."
        >
          <FrequencyDistributionChart frequency={frequency} type="weekday" />
        </ChartCard>

        <ChartCard
          title="Hour of Day Distribution (UTC)"
          subtitle="Posting timestamp concentration by hour."
        >
          <FrequencyDistributionChart frequency={frequency} type="hourly" />
        </ChartCard>
      </div>

      <div className="grid-two-col" style={{ marginTop: '2rem' }}>
        {/* Weekday Distribution Table */}
        <div className="section-card">
          <h3 className="section-title">Day of Week Distribution</h3>
          {frequency && Object.keys(frequency.weekday_distribution).length > 0 ? (
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Day of Week</th>
                    <th>Posts Published</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(frequency.weekday_distribution).map(([day, count]) => (
                    <tr key={day}>
                      <td>{day}</td>
                      <td>
                        <strong>{count}</strong>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="empty-subtext">No timestamp data available.</p>
          )}
        </div>

        {/* Hourly Distribution Table */}
        <div className="section-card">
          <h3 className="section-title">Hour of Day Distribution (UTC)</h3>
          {frequency && Object.keys(frequency.hourly_distribution).length > 0 ? (
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Hour (UTC)</th>
                    <th>Posts Published</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(frequency.hourly_distribution)
                    .filter(([, count]) => count > 0)
                    .map(([hour, count]) => (
                      <tr key={hour}>
                        <td>{hour.padStart(2, '0')}:00 — {hour.padStart(2, '0')}:59</td>
                        <td>
                          <strong>{count}</strong>
                        </td>
                      </tr>
                    ))}
                  {Object.values(frequency.hourly_distribution).every((c) => c === 0) && (
                    <tr>
                      <td colSpan={2} className="text-muted">
                        No post timestamps recorded yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="empty-subtext">No hourly timestamp data available.</p>
          )}
        </div>
      </div>
    </div>
  );
};

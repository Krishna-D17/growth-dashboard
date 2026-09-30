import React, { useState, useEffect, useCallback } from 'react';
import type { Profile, ComparisonResult } from '../types';
import { fetchProfiles, fetchComparison } from '../api/client';
import { formatNumber, formatPercent } from '../utils/formatters';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { ErrorMessage } from '../components/ErrorMessage';
import { EmptyState } from '../components/EmptyState';
import { ChartCard, ComparisonMetricsChart } from '../components/charts';

export const ComparisonPage: React.FC = () => {
  const [allProfiles, setAllProfiles] = useState<Profile[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [comparing, setComparing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadAll() {
      setLoading(true);
      setError(null);
      try {
        const profiles = await fetchProfiles();
        setAllProfiles(profiles);
        // Default select up to 3 profiles
        const initial = profiles.slice(0, 3).map((p) => p.id);
        setSelectedIds(initial);
      } catch (err) {
        setError((err as Error).message || 'Failed to load tracked profiles for comparison');
      } finally {
        setLoading(false);
      }
    }
    loadAll();
  }, []);

  const runComparison = useCallback(async (ids: string[]) => {
    if (ids.length === 0) {
      setComparison(null);
      return;
    }
    setComparing(true);
    setError(null);
    try {
      const res = await fetchComparison(ids);
      setComparison(res);
    } catch (err) {
      setError((err as Error).message || 'Failed to execute cross-profile comparison');
    } finally {
      setComparing(false);
    }
  }, []);

  useEffect(() => {
    if (selectedIds.length > 0) {
      runComparison(selectedIds);
    }
  }, [selectedIds, runComparison]);

  const toggleSelect = (id: string) => {
    const updated = selectedIds.includes(id)
      ? selectedIds.filter((item) => item !== id)
      : [...selectedIds, id];
    setSelectedIds(updated);
  };

  if (loading) return <LoadingSkeleton />;
  if (allProfiles.length === 0) {
    return (
      <EmptyState
        title="No Tracked Profiles"
        description="Add target profiles to enable side-by-side descriptive analytics comparison."
      />
    );
  }

  return (
    <div className="page-content">
      <div className="page-header-row">
        <div>
          <h2 className="page-title">Cross-Profile Descriptive Comparison</h2>
          <p className="page-subtitle">
            Side-by-side factual metrics observation. Strictly non-judgmental — does not rank or declare winning accounts.
          </p>
        </div>
      </div>

      {/* Target Selection Bar */}
      <div className="section-card">
        <h3 className="section-title">Select Profiles to Compare ({selectedIds.length} Selected)</h3>
        <div className="checkbox-grid">
          {allProfiles.map((p) => (
            <label key={p.id} className={`checkbox-pill ${selectedIds.includes(p.id) ? 'checked' : ''}`}>
              <input
                type="checkbox"
                checked={selectedIds.includes(p.id)}
                onChange={() => toggleSelect(p.id)}
              />
              <span className={`platform-badge platform-${p.platform}`}>{p.platform.toUpperCase()}</span>
              @{p.username}
            </label>
          ))}
        </div>
      </div>

      {error && <ErrorMessage message={error} onRetry={() => runComparison(selectedIds)} />}

      {comparing && <LoadingSkeleton />}

      {!comparing && comparison && comparison.profiles.length > 0 && (
        <>
          <ChartCard
            title="Side-by-Side Metric Visualizations"
            subtitle="Descriptive comparative inspection across selected profile targets."
          >
            <div className="grid-two-col">
              <ComparisonMetricsChart
                profiles={comparison.profiles}
                metricKey="current_followers"
                title="Current Followers"
              />
              <ComparisonMetricsChart
                profiles={comparison.profiles}
                metricKey="average_engagement"
                title="Average Post Engagement"
              />
              <ComparisonMetricsChart
                profiles={comparison.profiles}
                metricKey="posts_per_week"
                title="Posts / Week"
              />
              <ComparisonMetricsChart
                profiles={comparison.profiles}
                metricKey="growth_7d"
                title="7-Day Follower Growth"
              />
            </div>
          </ChartCard>

          <div className="section-card" style={{ marginTop: '2rem' }}>
          <h3 className="section-title">Descriptive Comparison Matrix</h3>
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Metric / Dimension</th>
                  {comparison.profiles.map((p) => (
                    <th key={p.profile_id}>
                      <span className={`platform-badge platform-${p.platform}`}>{p.platform.toUpperCase()}</span>
                      <br />@{p.username}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Current Followers</strong></td>
                  {comparison.profiles.map((p) => (
                    <td key={p.profile_id}>{formatNumber(p.current_followers)}</td>
                  ))}
                </tr>
                <tr>
                  <td><strong>7-Day Growth</strong></td>
                  {comparison.profiles.map((p) => (
                    <td key={p.profile_id}>
                      {formatNumber(p.growth_7d)} ({formatPercent(p.growth_percent_7d)})
                    </td>
                  ))}
                </tr>
                <tr>
                  <td><strong>30-Day Growth</strong></td>
                  {comparison.profiles.map((p) => (
                    <td key={p.profile_id}>
                      {formatNumber(p.growth_30d)} ({formatPercent(p.growth_percent_30d)})
                    </td>
                  ))}
                </tr>
                <tr>
                  <td><strong>Growth Velocity (Followers/Day)</strong></td>
                  {comparison.profiles.map((p) => (
                    <td key={p.profile_id}>{formatNumber(p.growth_velocity)}</td>
                  ))}
                </tr>
                <tr>
                  <td><strong>Average Post Engagement</strong></td>
                  {comparison.profiles.map((p) => (
                    <td key={p.profile_id}>{formatNumber(p.average_engagement)}</td>
                  ))}
                </tr>
                <tr>
                  <td><strong>Engagement Rate</strong></td>
                  {comparison.profiles.map((p) => (
                    <td key={p.profile_id}>{formatPercent(p.engagement_rate)}</td>
                  ))}
                </tr>
                <tr>
                  <td><strong>Publishing Cadence (Posts/Week)</strong></td>
                  {comparison.profiles.map((p) => (
                    <td key={p.profile_id}>{formatNumber(p.posts_per_week)}</td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </>
    )}
    </div>
  );
};

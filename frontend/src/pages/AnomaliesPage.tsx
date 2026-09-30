import React, { useState, useEffect, useCallback } from 'react';
import type { AnomalyResult } from '../types';
import { fetchAnomalies } from '../api/client';
import { formatNumber, formatDate } from '../utils/formatters';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { ErrorMessage } from '../components/ErrorMessage';
import { EmptyState } from '../components/EmptyState';
import { ChartCard, AnomaliesSeverityChart } from '../components/charts';

interface AnomaliesPageProps {
  profileId: string;
}

export const AnomaliesPage: React.FC<AnomaliesPageProps> = ({ profileId }) => {
  const [anomalies, setAnomalies] = useState<AnomalyResult[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAnomalies(profileId);
      setAnomalies(data);
    } catch (err) {
      setError((err as Error).message || 'Failed to load anomalies');
    } finally {
      setLoading(false);
    }
  }, [profileId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) return <LoadingSkeleton />;
  if (error) return <ErrorMessage message={error} onRetry={loadData} />;

  return (
    <div className="page-content">
      <div className="page-header-row">
        <div>
          <h2 className="page-title">Detected Growth Anomalies</h2>
          <p className="page-subtitle">
            Unusual growth spikes detected via Rolling Median and Median Absolute Deviation (MAD).
          </p>
        </div>
      </div>

      {anomalies.length > 0 && (
        <ChartCard
          title="Anomaly Event Distribution by Severity"
          subtitle="Observed growth deviation events categorized by MAD mathematical severity levels."
        >
          <AnomaliesSeverityChart anomalies={anomalies} />
        </ChartCard>
      )}

      {anomalies.length > 0 ? (
        <div className="section-card" style={{ marginTop: '2rem' }}>
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Detected At</th>
                  <th>Metric</th>
                  <th>Observed Value</th>
                  <th>Rolling Median</th>
                  <th>MAD Score</th>
                  <th>Severity</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {anomalies.map((anom, idx) => (
                  <tr key={anom.id || idx}>
                    <td>{formatDate(anom.detected_at)}</td>
                    <td>
                      <span className="badge-pill">{anom.metric}</span>
                    </td>
                    <td>
                      <strong>{formatNumber(anom.observed_value)} / day</strong>
                    </td>
                    <td>{formatNumber(anom.baseline?.rolling_median)} / day</td>
                    <td>{anom.baseline?.score ?? '—'}</td>
                    <td>
                      <span className={`severity-badge severity-${anom.severity}`}>
                        {anom.severity.toUpperCase()}
                      </span>
                    </td>
                    <td className="description-cell">{anom.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <EmptyState
          icon="✅"
          title="No Anomalies Detected"
          description="Follower growth rates for this profile remain within expected mathematical baseline bounds."
        />
      )}
    </div>
  );
};

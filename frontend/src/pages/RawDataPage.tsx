import React, { useState, useEffect, useCallback } from 'react';
import type { CollectionJob, ProfileDetail } from '../types';
import { fetchCollectionHistory, fetchProfile } from '../api/client';
import { formatDate, formatNumber } from '../utils/formatters';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { ErrorMessage } from '../components/ErrorMessage';
import { EmptyState } from '../components/EmptyState';

interface RawDataPageProps {
  profileId: string;
}

export const RawDataPage: React.FC<RawDataPageProps> = ({ profileId }) => {
  const [jobs, setJobs] = useState<CollectionJob[]>([]);
  const [profileDetail, setProfileDetail] = useState<ProfileDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [jData, pData] = await Promise.all([
        fetchCollectionHistory(profileId),
        fetchProfile(profileId),
      ]);
      setJobs(jData);
      setProfileDetail(pData);
    } catch (err) {
      setError((err as Error).message || 'Failed to load raw audit data');
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
          <h2 className="page-title">Raw Data &amp; Collection Audit Logs</h2>
          <p className="page-subtitle">Auditable record of collection runs, collector versions, and historical snapshots.</p>
        </div>
      </div>

      {/* Collection Jobs Audit Table */}
      <div className="section-card">
        <h3 className="section-title">Collection Jobs Audit History</h3>
        {jobs.length > 0 ? (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Job ID</th>
                  <th>Platform</th>
                  <th>Status</th>
                  <th>Started At</th>
                  <th>Completed At</th>
                  <th>Records Collected</th>
                  <th>Collector Version</th>
                  <th>Error Message</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((j) => (
                  <tr key={j.id}>
                    <td className="code-font">{j.id.slice(0, 8)}...</td>
                    <td>
                      <span className={`platform-badge platform-${j.platform}`}>{j.platform.toUpperCase()}</span>
                    </td>
                    <td>
                      <span className={`status-badge status-${j.status}`}>{j.status.toUpperCase()}</span>
                    </td>
                    <td>{formatDate(j.started_at)}</td>
                    <td>{formatDate(j.completed_at)}</td>
                    <td>{formatNumber(j.records_collected)}</td>
                    <td>{j.collector_version || '—'}</td>
                    <td className="error-text-cell">{j.error_message || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No Collection Jobs Found" description="No collection runs recorded for this profile yet." />
        )}
      </div>

      {/* Historical Profile Snapshots Audit Table */}
      <div className="section-card" style={{ marginTop: '2rem' }}>
        <h3 className="section-title">Historical Profile Snapshots</h3>
        {profileDetail && profileDetail.latest_snapshot ? (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Snapshot ID</th>
                  <th>Collected At</th>
                  <th>Followers</th>
                  <th>Following</th>
                  <th>Post Count</th>
                  <th>Collector Version</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="code-font">{profileDetail.latest_snapshot.id.slice(0, 8)}...</td>
                  <td>{formatDate(profileDetail.latest_snapshot.collected_at)}</td>
                  <td>{formatNumber(profileDetail.latest_snapshot.followers)}</td>
                  <td>{formatNumber(profileDetail.latest_snapshot.following)}</td>
                  <td>{formatNumber(profileDetail.latest_snapshot.post_count)}</td>
                  <td>{profileDetail.latest_snapshot.collector_version || '—'}</td>
                </tr>
              </tbody>
            </table>
          </div>
        ) : (
          <p className="empty-subtext">No historical profile snapshots stored yet.</p>
        )}
      </div>
    </div>
  );
};

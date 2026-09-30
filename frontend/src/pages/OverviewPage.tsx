import React, { useState, useEffect, useCallback } from 'react';
import type { ProfileAnalyticsOverview, TopPostItem, ProfileDetail } from '../types';
import { fetchAnalyticsOverview, fetchTopPosts, triggerCollection, fetchProfile, deleteProfile } from '../api/client';
import { formatNumber, formatPercent, formatDate } from '../utils/formatters';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { ErrorMessage } from '../components/ErrorMessage';
import { EmptyState } from '../components/EmptyState';
import {
  ChartCard,
  GrowthSummaryChart,
  ContentDistributionChart,
  EngagementBreakdownChart,
} from '../components/charts';
import { ExportModal } from '../components/ExportModal';
import { AIInsightsCard } from '../components/AIInsightsCard';
import { DeleteProfileModal } from '../components/DeleteProfileModal';

interface OverviewPageProps {
  profileId: string;
  selectedDays?: number;
  onProfileDeleted?: () => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({ profileId, selectedDays, onProfileDeleted }) => {
  const [overview, setOverview] = useState<ProfileAnalyticsOverview | null>(null);
  const [topPosts, setTopPosts] = useState<TopPostItem[]>([]);
  const [profileDetail, setProfileDetail] = useState<ProfileDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [collecting, setCollecting] = useState<boolean>(false);
  const [collectStatus, setCollectStatus] = useState<string | null>(null);
  const [exportModalOpen, setExportModalOpen] = useState<boolean>(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState<boolean>(false);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [ovData, postsData, profData] = await Promise.all([
        fetchAnalyticsOverview(profileId, selectedDays),
        fetchTopPosts(profileId, 'engagement', 5),
        fetchProfile(profileId),
      ]);
      setOverview(ovData);
      setTopPosts(postsData);
      setProfileDetail(profData);
    } catch (err) {
      setError((err as Error).message || 'Failed to load profile analytics overview');
    } finally {
      setLoading(false);
    }
  }, [profileId, selectedDays]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleManualCollect = async () => {
    setCollecting(true);
    setCollectStatus('Initiating collection...');
    try {
      const job = await triggerCollection(profileId, 10);
      setCollectStatus(`Collection completed (Status: ${job.status.toUpperCase()}, Collected: ${job.records_collected} posts)`);
      await loadData();
    } catch (err) {
      setCollectStatus(`Collection failed: ${(err as Error).message}`);
    } finally {
      setCollecting(false);
    }
  };

  const handleDeleteConfirm = async () => {
    setIsDeleting(true);
    try {
      await deleteProfile(profileId);
      setDeleteModalOpen(false);
      if (onProfileDeleted) {
        onProfileDeleted();
      }
    } catch (err) {
      alert(`Deletion failed: ${(err as Error).message}`);
    } finally {
      setIsDeleting(false);
    }
  };

  if (loading) return <LoadingSkeleton />;
  if (error) return <ErrorMessage message={error} onRetry={loadData} />;
  if (!overview) return <EmptyState title="No Data Found" description="No analytics overview available for this profile." />;

  const hasHistory = overview.growth.current_followers !== null || overview.content.total_posts > 0;
  const hasPerformanceMetrics = topPosts.some(
    (p) => (p.likes !== null && p.likes > 0) || (p.comments !== null && p.comments > 0) || (p.engagement !== null && p.engagement > 0)
  );
  const topPostsTitle = hasPerformanceMetrics ? 'Top Performing Posts Preview' : 'Recent Posts Preview';

  return (
    <div className="page-content">
      {/* Profile Header Summary */}
      <div className="profile-header-card">
        <div className="profile-info-main">
          <div className="avatar-placeholder">
            {overview.platform === 'instagram' ? '📷' : overview.platform === 'x' ? '𝕏' : '📘'}
          </div>
          <div>
            <h2 className="profile-title">
              @{overview.username}
              {profileDetail?.verified && <span className="verified-badge">✓</span>}
            </h2>
            <div className="profile-meta">
              <span className={`platform-badge platform-${overview.platform}`}>{overview.platform.toUpperCase()}</span>
              {profileDetail?.display_name && <span>{profileDetail.display_name}</span>}
              {profileDetail?.last_collected_at && <span>Last Collected: {formatDate(profileDetail.last_collected_at)}</span>}
            </div>
          </div>
        </div>

        <div className="profile-header-actions" style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => setExportModalOpen(true)}
          >
            📥 Export Data &amp; Reports
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={handleManualCollect}
            disabled={collecting}
          >
            {collecting ? 'Collecting...' : '⚡ Trigger Manual Collection'}
          </button>
          <button
            type="button"
            className="btn btn-sm"
            style={{ backgroundColor: '#fff1f2', color: '#e11d48', borderColor: '#fecdd3' }}
            onClick={() => setDeleteModalOpen(true)}
          >
            🗑️ Delete Target
          </button>
        </div>
      </div>

      <ExportModal
        profileId={profileId}
        username={overview.username}
        selectedDays={selectedDays}
        isOpen={exportModalOpen}
        onClose={() => setExportModalOpen(false)}
      />

      {deleteModalOpen && (
        <DeleteProfileModal
          isOpen={deleteModalOpen}
          onClose={() => setDeleteModalOpen(false)}
          onConfirm={handleDeleteConfirm}
          username={overview.username}
          platform={overview.platform}
          displayName={profileDetail?.display_name}
          isDeleting={isDeleting}
        />
      )}

      {collectStatus && <div className="info-banner-small">{collectStatus}</div>}

      {!hasHistory && (
        <EmptyState
          icon="📊"
          title="No Historical Observations Yet"
          description="This target has been registered but does not have stored profile snapshots or posts yet. Run a collection to populate metrics."
          actionLabel="Run First Collection"
          onAction={handleManualCollect}
        />
      )}

      {/* Metric Summary Cards */}
      <div className="metric-cards-grid">
        <div className="metric-card">
          <div className="metric-label">Current Followers</div>
          <div className="metric-value">{formatNumber(overview.growth.current_followers)}</div>
          <div className="metric-sub">Latest Observation</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">7-Day Growth</div>
          <div className="metric-value">{formatNumber(overview.growth.growth_7d)}</div>
          <div className="metric-sub">{formatPercent(overview.growth.growth_percent_7d)} vs 7 days ago</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">30-Day Growth</div>
          <div className="metric-value">{formatNumber(overview.growth.growth_30d)}</div>
          <div className="metric-sub">{formatPercent(overview.growth.growth_percent_30d)} vs 30 days ago</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Avg Engagement</div>
          <div className="metric-value">{formatNumber(overview.engagement.average_engagement)}</div>
          <div className="metric-sub">Rate: {formatPercent(overview.engagement.engagement_rate)}</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Posts Tracked</div>
          <div className="metric-value">{overview.content.total_posts}</div>
          <div className="metric-sub">{formatNumber(overview.frequency.posts_per_week)} posts / week</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Detected Anomalies</div>
          <div className="metric-value">{overview.anomalies.length}</div>
          <div className="metric-sub">MAD Growth Spikes</div>
        </div>
      </div>

      {/* Visual Analytics Summary Grid */}
      <div className="grid-two-col" style={{ marginTop: '2rem' }}>
        <ChartCard
          title="Follower Growth & Velocity"
          subtitle="Observed growth totals and velocity across recent snapshot observations."
        >
          <GrowthSummaryChart growth={overview.growth} />
        </ChartCard>

        <ChartCard
          title="Content Mix Distribution"
          subtitle="Proportional breakdown of published posts by canonical content type."
        >
          <ContentDistributionChart content={overview.content} mode="donut" />
        </ChartCard>
      </div>

      <ChartCard
        title="Observed Interaction Components"
        subtitle="Total recorded likes, comments, shares, and views across tracked posts."
      >
        <EngagementBreakdownChart engagement={overview.engagement} />
      </ChartCard>

      {/* AI Insights & Explanation Layer */}
      <AIInsightsCard profileId={profileId} selectedDays={selectedDays} />

      {/* Top Posts Preview */}
      <div className="section-card" style={{ marginTop: '2rem' }}>
        <h3 className="section-title">{topPostsTitle}</h3>
        {topPosts.length > 0 && !hasPerformanceMetrics && (
          <div className="info-banner-small" style={{ marginBottom: '1rem' }}>
            ℹ️ {overview.platform.toUpperCase()} public web pages did not expose post-level interaction counts for this collection. Unavailable metrics are preserved as N/A.
          </div>
        )}
        {topPosts.length > 0 ? (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Platform ID</th>
                  <th>Media Type</th>
                  <th>Caption</th>
                  <th>Posted At</th>
                  <th>Likes</th>
                  <th>Comments</th>
                  <th>Engagement</th>
                </tr>
              </thead>
              <tbody>
                {topPosts.map((post) => (
                  <tr key={post.post_id}>
                    <td>
                      <a href={post.url} target="_blank" rel="noopener noreferrer" className="table-link">
                        {post.platform_post_id} ↗
                      </a>
                    </td>
                    <td>
                      <span className="badge-pill">{post.media_type}</span>
                    </td>
                    <td className="caption-cell">{post.caption || '—'}</td>
                    <td>{formatDate(post.posted_at)}</td>
                    <td>{formatNumber(post.likes)}</td>
                    <td>{formatNumber(post.comments)}</td>
                    <td>
                      <strong>{formatNumber(post.engagement)}</strong>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="empty-subtext">No post data available yet.</p>
        )}
      </div>
    </div>
  );
};

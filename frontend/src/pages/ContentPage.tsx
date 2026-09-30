import React, { useState, useEffect, useCallback } from 'react';
import type { ContentAnalytics, TopPostItem } from '../types';
import { fetchContentAnalytics, fetchTopPosts } from '../api/client';
import { formatNumber, formatDate } from '../utils/formatters';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { ErrorMessage } from '../components/ErrorMessage';
import { ChartCard, ContentDistributionChart } from '../components/charts';

interface ContentPageProps {
  profileId: string;
  selectedDays?: number;
}

export const ContentPage: React.FC<ContentPageProps> = ({ profileId, selectedDays }) => {
  const [content, setContent] = useState<ContentAnalytics | null>(null);
  const [topPosts, setTopPosts] = useState<TopPostItem[]>([]);
  const [sortBy, setSortBy] = useState<string>('engagement');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [cData, pData] = await Promise.all([
        fetchContentAnalytics(profileId, selectedDays),
        fetchTopPosts(profileId, sortBy, 10),
      ]);
      setContent(cData);
      setTopPosts(pData);
    } catch (err) {
      setError((err as Error).message || 'Failed to load content analytics');
    } finally {
      setLoading(false);
    }
  }, [profileId, selectedDays, sortBy]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) return <LoadingSkeleton />;
  if (error) return <ErrorMessage message={error} onRetry={loadData} />;

  return (
    <div className="page-content">
      <div className="page-header-row">
        <div>
          <h2 className="page-title">Content Analytics &amp; Performance</h2>
          <p className="page-subtitle">Categorized breakdown by normalized media types and top post rankings.</p>
        </div>
      </div>

      <ChartCard
        title="Content Breakdown & Performance Visualizations"
        subtitle="Distribution of posts by media category and average engagement per content type."
      >
        <ContentDistributionChart content={content} mode="both" />
      </ChartCard>

      {/* Content Category Breakdown Table */}
      <div className="section-card" style={{ marginTop: '2rem' }}>
        <h3 className="section-title">Performance by Canonical Content Type</h3>
        {content && content.by_content_type.length > 0 ? (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Content Category</th>
                  <th>Post Count</th>
                  <th>Avg Engagement</th>
                  <th>Median Engagement</th>
                  <th>Total Views</th>
                  <th>Avg Views</th>
                  <th>Posts / Day</th>
                </tr>
              </thead>
              <tbody>
                {content.by_content_type.map((typeStats) => (
                  <tr key={typeStats.content_type}>
                    <td>
                      <span className="badge-pill">{typeStats.content_type}</span>
                    </td>
                    <td>{typeStats.post_count}</td>
                    <td>{formatNumber(typeStats.average_engagement)}</td>
                    <td>{formatNumber(typeStats.median_engagement)}</td>
                    <td>{formatNumber(typeStats.total_views)}</td>
                    <td>{formatNumber(typeStats.average_views)}</td>
                    <td>{formatNumber(typeStats.posting_frequency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="empty-subtext">No categorized content available.</p>
        )}
      </div>

      {/* Top Posts Ranking */}
      <div className="section-card" style={{ marginTop: '2rem' }}>
        <div className="flex-between">
          <h3 className="section-title">Top Posts Ranking</h3>
          <div className="sort-control">
            <label>Sort By: </label>
            <select
              className="form-select-sm"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
            >
              <option value="engagement">Engagement</option>
              <option value="engagement_rate">Engagement Rate</option>
              <option value="likes">Likes</option>
              <option value="comments">Comments</option>
              <option value="shares">Shares</option>
              <option value="views">Views</option>
              <option value="newest">Newest</option>
              <option value="oldest">Oldest</option>
            </select>
          </div>
        </div>

        {topPosts.length > 0 ? (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Platform Post ID</th>
                  <th>Media Type</th>
                  <th>Caption</th>
                  <th>Posted At</th>
                  <th>Likes</th>
                  <th>Comments</th>
                  <th>Shares</th>
                  <th>Views</th>
                  <th>Metric Value</th>
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
                    <td>{formatNumber(post.shares)}</td>
                    <td>{formatNumber(post.views)}</td>
                    <td>
                      <strong className="highlight-metric">{formatNumber(post.metric_value)}</strong>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="empty-subtext">No post metrics available for ranking.</p>
        )}
      </div>
    </div>
  );
};

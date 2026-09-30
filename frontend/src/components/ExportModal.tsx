import React, { useState } from 'react';
import { downloadExportFile } from '../api/client';

interface ExportModalProps {
  profileId: string;
  username?: string;
  selectedDays?: number;
  isOpen: boolean;
  onClose: () => void;
}

type ExportCategory = 'report' | 'profile' | 'snapshots' | 'posts' | 'jobs' | 'analytics';
type ExportFormat = 'xlsx' | 'json' | 'csv';

export const ExportModal: React.FC<ExportModalProps> = ({
  profileId,
  username,
  selectedDays,
  isOpen,
  onClose,
}) => {
  const [category, setCategory] = useState<ExportCategory>('report');
  const [format, setFormat] = useState<ExportFormat>('xlsx');
  const [downloading, setDownloading] = useState<boolean>(false);
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  if (!isOpen) return null;

  const handleDownload = async () => {
    setDownloading(true);
    setStatusMsg(null);
    try {
      await downloadExportFile(profileId, category, format, selectedDays);
      setStatusMsg({
        type: 'success',
        text: `Successfully exported ${category.toUpperCase()} data in ${format.toUpperCase()} format.`,
      });
      setTimeout(() => {
        setStatusMsg(null);
      }, 4000);
    } catch (err) {
      setStatusMsg({
        type: 'error',
        text: (err as Error).message || 'Failed to download export file.',
      });
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">📥 Export Data &amp; Reports</h3>
          <button type="button" className="btn-close" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="modal-body">
          {username && (
            <p className="modal-subtitle">
              Export target: <strong>@{username}</strong>
            </p>
          )}

          {/* Dataset Selection */}
          <div className="form-group" style={{ marginBottom: '1.25rem' }}>
            <label className="form-label">Dataset Category:</label>
            <div className="radio-group-grid">
              <label className={`radio-pill ${category === 'report' ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="category"
                  value="report"
                  checked={category === 'report'}
                  onChange={() => setCategory('report')}
                />
                <strong>📊 Complete Report</strong>
                <span className="radio-desc">Multi-table consolidated report</span>
              </label>

              <label className={`radio-pill ${category === 'analytics' ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="category"
                  value="analytics"
                  checked={category === 'analytics'}
                  onChange={() => setCategory('analytics')}
                />
                <strong>📈 Analytics Summary</strong>
                <span className="radio-desc">Growth, engagement, content &amp; frequency</span>
              </label>

              <label className={`radio-pill ${category === 'posts' ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="category"
                  value="posts"
                  checked={category === 'posts'}
                  onChange={() => setCategory('posts')}
                />
                <strong>📝 Posts &amp; Metrics</strong>
                <span className="radio-desc">Published posts and snapshot metrics</span>
              </label>

              <label className={`radio-pill ${category === 'snapshots' ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="category"
                  value="snapshots"
                  checked={category === 'snapshots'}
                  onChange={() => setCategory('snapshots')}
                />
                <strong>📸 Profile Snapshots</strong>
                <span className="radio-desc">Follower and count observations</span>
              </label>

              <label className={`radio-pill ${category === 'profile' ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="category"
                  value="profile"
                  checked={category === 'profile'}
                  onChange={() => setCategory('profile')}
                />
                <strong>👤 Profile Metadata</strong>
                <span className="radio-desc">Account registration &amp; bio details</span>
              </label>

              <label className={`radio-pill ${category === 'jobs' ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="category"
                  value="jobs"
                  checked={category === 'jobs'}
                  onChange={() => setCategory('jobs')}
                />
                <strong>⚡ Collection Jobs</strong>
                <span className="radio-desc">Scraping run history &amp; statuses</span>
              </label>
            </div>
          </div>

          {/* Format Selection */}
          <div className="form-group" style={{ marginBottom: '1.25rem' }}>
            <label className="form-label">Export Format:</label>
            <div className="format-button-group">
              <button
                type="button"
                className={`format-btn ${format === 'xlsx' ? 'active' : ''}`}
                onClick={() => setFormat('xlsx')}
              >
                📗 Excel (.xlsx)
              </button>
              <button
                type="button"
                className={`format-btn ${format === 'json' ? 'active' : ''}`}
                onClick={() => setFormat('json')}
              >
                📜 JSON (.json)
              </button>
              <button
                type="button"
                className={`format-btn ${format === 'csv' ? 'active' : ''}`}
                onClick={() => setFormat('csv')}
              >
                📄 CSV (.csv)
              </button>
            </div>
          </div>

          {statusMsg && (
            <div
              className={statusMsg.type === 'success' ? 'info-banner-small' : 'error-banner-small'}
              style={{ marginBottom: '1rem' }}
            >
              {statusMsg.text}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={downloading}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleDownload}
            disabled={downloading}
          >
            {downloading ? 'Generating Export...' : `Download ${format.toUpperCase()}`}
          </button>
        </div>
      </div>
    </div>
  );
};

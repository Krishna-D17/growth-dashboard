import React, { useState } from 'react';
import type { SocialPlatform, CollectionSchedule } from '../types';

interface AddProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (payload: { platform: SocialPlatform; target: string; collection_schedule: CollectionSchedule }) => Promise<void>;
}

export const AddProfileModal: React.FC<AddProfileModalProps> = ({ isOpen, onClose, onAdd }) => {
  const [platform, setPlatform] = useState<SocialPlatform>('instagram');
  const [target, setTarget] = useState<string>('');
  const [schedule, setSchedule] = useState<CollectionSchedule>('manual');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!target.trim()) {
      setError('Please enter a username or profile URL.');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await onAdd({ platform, target: target.trim(), collection_schedule: schedule });
      setTarget('');
      onClose();
    } catch (err) {
      setError((err as Error).message || 'Failed to register profile target.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Track New Social Target</h2>
          <button type="button" className="modal-close" onClick={onClose}>
            &times;
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          {error && <div className="error-banner-small">{error}</div>}

          <div className="form-group">
            <label>Platform</label>
            <div className="platform-radio-group">
              {(['instagram', 'x', 'facebook'] as SocialPlatform[]).map((p) => (
                <label key={p} className={`radio-pill ${platform === p ? 'selected' : ''}`}>
                  <input
                    type="radio"
                    name="platform"
                    value={p}
                    checked={platform === p}
                    onChange={() => setPlatform(p)}
                  />
                  {p.toUpperCase()}
                </label>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label>Target Handle or Profile URL</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. @username or https://instagram.com/username/"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              disabled={submitting}
            />
          </div>

          <div className="form-group">
            <label>Collection Schedule</label>
            <select
              className="form-select"
              value={schedule}
              onChange={(e) => setSchedule(e.target.value as CollectionSchedule)}
              disabled={submitting}
            >
              <option value="manual">Manual Only</option>
              <option value="every_6_hours">Every 6 Hours</option>
              <option value="every_12_hours">Every 12 Hours</option>
              <option value="daily">Daily</option>
            </select>
          </div>

          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Registering...' : 'Add Target Profile'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

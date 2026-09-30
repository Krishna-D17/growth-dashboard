import React, { useState, useEffect, useCallback } from 'react';
import type { Profile, CollectionSchedule } from '../types';
import { fetchProfiles, updateProfileSchedule, triggerCollection, deleteProfile } from '../api/client';
import { formatDate } from '../utils/formatters';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { ErrorMessage } from '../components/ErrorMessage';
import { EmptyState } from '../components/EmptyState';
import { DeleteProfileModal } from '../components/DeleteProfileModal';

interface ProfilesPageProps {
  onSelectProfile: (profileId: string) => void;
  onAddClick: () => void;
  onProfileDeleted?: () => void;
}

export const ProfilesPage: React.FC<ProfilesPageProps> = ({
  onSelectProfile,
  onAddClick,
  onProfileDeleted,
}) => {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [collectingId, setCollectingId] = useState<string | null>(null);
  const [deletingProfile, setDeletingProfile] = useState<Profile | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchProfiles();
      setProfiles(data);
    } catch (err) {
      setError((err as Error).message || 'Failed to load profiles');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleScheduleChange = async (profileId: string, schedule: CollectionSchedule) => {
    try {
      await updateProfileSchedule(profileId, schedule);
      await loadData();
    } catch (err) {
      alert(`Failed to update schedule: ${(err as Error).message}`);
    }
  };

  const handleCollect = async (profileId: string) => {
    setCollectingId(profileId);
    try {
      await triggerCollection(profileId, 10);
      await loadData();
    } catch (err) {
      alert(`Collection failed: ${(err as Error).message}`);
    } finally {
      setCollectingId(null);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deletingProfile) return;
    setIsDeleting(true);
    try {
      await deleteProfile(deletingProfile.id);
      setSuccessMessage(`Target deleted successfully.`);
      setDeletingProfile(null);
      await loadData();
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

  return (
    <div className="page-content">
      <div className="page-header-row">
        <div>
          <h2 className="page-title">Monitored Social Media Targets</h2>
          <p className="page-subtitle">Tracked profiles, schedule frequency settings, and collection actions.</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={onAddClick}>
          + Add New Target
        </button>
      </div>

      {successMessage && (
        <div className="info-banner-small" style={{ marginBottom: '1.5rem', backgroundColor: '#ecfdf5', borderColor: '#a7f3d0', color: '#065f46' }}>
          ✓ {successMessage}
        </div>
      )}

      {profiles.length > 0 ? (
        <div className="profiles-grid">
          {profiles.map((p) => (
            <div key={p.id} className="profile-card">
              <div className="profile-card-top">
                <span className={`platform-badge platform-${p.platform}`}>{p.platform.toUpperCase()}</span>
                {p.verified && <span className="verified-badge">✓ Verified</span>}
              </div>

              <h3 className="profile-card-handle">@{p.username}</h3>
              {p.display_name && <div className="profile-card-name">{p.display_name}</div>}

              <div className="profile-card-meta">
                <div>URL: <a href={p.profile_url} target="_blank" rel="noopener noreferrer" className="table-link">{p.profile_url}</a></div>
                <div>Last Collected: {formatDate(p.last_collected_at)}</div>
              </div>

              <div className="profile-card-schedule">
                <label>Schedule: </label>
                <select
                  className="form-select-sm"
                  value={p.collection_schedule}
                  onChange={(e) => handleScheduleChange(p.id, e.target.value as CollectionSchedule)}
                >
                  <option value="manual">Manual Only</option>
                  <option value="every_6_hours">Every 6 Hours</option>
                  <option value="every_12_hours">Every 12 Hours</option>
                  <option value="daily">Daily</option>
                </select>
              </div>

              <div className="profile-card-actions" style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => onSelectProfile(p.id)}
                >
                  View Analytics
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => handleCollect(p.id)}
                  disabled={collectingId === p.id}
                >
                  {collectingId === p.id ? 'Collecting...' : '⚡ Collect Now'}
                </button>
                <button
                  type="button"
                  className="btn btn-sm"
                  style={{ backgroundColor: '#fff1f2', color: '#e11d48', borderColor: '#fecdd3' }}
                  onClick={() => setDeletingProfile(p)}
                >
                  🗑️ Delete Target
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState
          icon="👥"
          title="No Tracked Profiles"
          description="You are not monitoring any social media targets yet. Add your first Instagram, X, or Facebook Page target."
          actionLabel="+ Add Target Profile"
          onAction={onAddClick}
        />
      )}

      {deletingProfile && (
        <DeleteProfileModal
          isOpen={!!deletingProfile}
          onClose={() => setDeletingProfile(null)}
          onConfirm={handleDeleteConfirm}
          username={deletingProfile.username}
          platform={deletingProfile.platform}
          displayName={deletingProfile.display_name}
          isDeleting={isDeleting}
        />
      )}
    </div>
  );
};

import React from 'react';
import type { Profile } from '../types';

interface ProfileSelectorProps {
  profiles: Profile[];
  selectedProfileId: string | null;
  onSelectProfile: (profileId: string) => void;
  onAddProfileClick: () => void;
}

export const ProfileSelector: React.FC<ProfileSelectorProps> = ({
  profiles,
  selectedProfileId,
  onSelectProfile,
  onAddProfileClick,
}) => {
  const currentProfile = profiles.find((p) => p.id === selectedProfileId);

  return (
    <div className="profile-selector-container">
      {profiles.length > 0 ? (
        <select
          className="profile-select"
          value={selectedProfileId || ''}
          onChange={(e) => onSelectProfile(e.target.value)}
        >
          {profiles.map((p) => (
            <option key={p.id} value={p.id}>
              {p.platform.toUpperCase()} — @{p.username} {p.display_name ? `(${p.display_name})` : ''}
            </option>
          ))}
        </select>
      ) : (
        <div className="no-profiles-tag">No profiles tracked</div>
      )}

      {currentProfile && (
        <span className={`platform-badge platform-${currentProfile.platform}`}>
          {currentProfile.platform.toUpperCase()}
        </span>
      )}

      <button type="button" className="btn btn-secondary btn-sm" onClick={onAddProfileClick}>
        + Add Target
      </button>
    </div>
  );
};

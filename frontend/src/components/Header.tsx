import React from 'react';
import type { Profile } from '../types';
import { ProfileSelector } from './ProfileSelector';
import { TimeRangeSelector } from './TimeRangeSelector';

interface HeaderProps {
  profiles: Profile[];
  selectedProfileId: string | null;
  onSelectProfile: (profileId: string) => void;
  selectedDays?: number;
  onTimeRangeChange: (days: number | undefined) => void;
  onAddProfileClick: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  profiles,
  selectedProfileId,
  onSelectProfile,
  selectedDays,
  onTimeRangeChange,
  onAddProfileClick,
}) => {
  return (
    <header className="header-bar">
      <div className="header-brand">
        <div className="brand-logo">SS</div>
        <div>
          <h1 className="brand-title">SocialScope</h1>
          <div className="brand-subtitle">Intelligence &amp; Growth Platform</div>
        </div>
      </div>

      <div className="header-actions">
        <ProfileSelector
          profiles={profiles}
          selectedProfileId={selectedProfileId}
          onSelectProfile={onSelectProfile}
          onAddProfileClick={onAddProfileClick}
        />
        <TimeRangeSelector selectedDays={selectedDays} onChange={onTimeRangeChange} />
      </div>
    </header>
  );
};

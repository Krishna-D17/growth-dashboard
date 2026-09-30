import React from 'react';
import type { DashboardTab } from '../router';

interface SidebarProps {
  currentTab: DashboardTab;
  profileId: string | null;
  onNavigate: (path: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, profileId, onNavigate }) => {
  const navItems: { tab: DashboardTab; label: string; path: string; icon: string }[] = [
    { tab: 'overview', label: 'Overview', path: profileId ? `/profiles/${profileId}` : '/profiles', icon: '📊' },
    { tab: 'growth', label: 'Growth', path: profileId ? `/profiles/${profileId}/growth` : '/profiles', icon: '📈' },
    { tab: 'content', label: 'Content', path: profileId ? `/profiles/${profileId}/content` : '/profiles', icon: '📷' },
    { tab: 'engagement', label: 'Engagement', path: profileId ? `/profiles/${profileId}/engagement` : '/profiles', icon: '💬' },
    { tab: 'frequency', label: 'Frequency', path: profileId ? `/profiles/${profileId}/frequency` : '/profiles', icon: '⏱️' },
    { tab: 'anomalies', label: 'Anomalies', path: profileId ? `/profiles/${profileId}/anomalies` : '/profiles', icon: '⚠️' },
    { tab: 'raw-data', label: 'Raw Data & Audit', path: profileId ? `/profiles/${profileId}/raw-data` : '/profiles', icon: '📋' },
    { tab: 'comparison', label: 'Comparison', path: '/comparison', icon: '⚖️' },
    { tab: 'profiles', label: 'All Profiles', path: '/profiles', icon: '👥' },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-section-label">DASHBOARD NAVIGATION</div>
      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const isActive = currentTab === item.tab;
          const isDisabled = !profileId && item.tab !== 'profiles' && item.tab !== 'comparison';

          return (
            <button
              key={item.tab}
              type="button"
              className={`sidebar-link ${isActive ? 'active' : ''} ${isDisabled ? 'disabled' : ''}`}
              onClick={() => {
                if (!isDisabled) onNavigate(item.path);
              }}
              disabled={isDisabled}
            >
              <span className="sidebar-icon">{item.icon}</span>
              <span className="sidebar-text">{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="system-status">
          <span className="status-dot"></span> System Operational
        </div>
      </div>
    </aside>
  );
};

import { useState, useEffect, useCallback } from 'react';
import type { Profile, SocialPlatform, CollectionSchedule } from './types';
import { fetchProfiles, createProfile } from './api/client';
import { useRoute } from './router';

import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { AddProfileModal } from './components/AddProfileModal';

import { OverviewPage } from './pages/OverviewPage';
import { GrowthPage } from './pages/GrowthPage';
import { ContentPage } from './pages/ContentPage';
import { EngagementPage } from './pages/EngagementPage';
import { FrequencyPage } from './pages/FrequencyPage';
import { AnomaliesPage } from './pages/AnomaliesPage';
import { RawDataPage } from './pages/RawDataPage';
import { ComparisonPage } from './pages/ComparisonPage';
import { ProfilesPage } from './pages/ProfilesPage';

function App() {
  const { route, navigate } = useRoute();
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [selectedDays, setSelectedDays] = useState<number | undefined>(undefined);
  const [isAddModalOpen, setIsAddModalOpen] = useState<boolean>(false);

  const loadProfilesList = useCallback(async () => {
    try {
      const data = await fetchProfiles();
      setProfiles(data);

      // If no profileId in URL and profiles exist, auto-select first profile for Overview
      if (!route.profileId && data.length > 0 && route.tab !== 'comparison' && route.tab !== 'profiles') {
        navigate(`/profiles/${data[0].id}`);
      }
    } catch {
      // Handled gracefully in pages
    }
  }, [route.profileId, route.tab, navigate]);

  useEffect(() => {
    loadProfilesList();
  }, [loadProfilesList]);

  const handleSelectProfile = (profileId: string) => {
    const subTab = route.tab === 'profiles' ? 'overview' : route.tab;
    const path = subTab === 'overview' ? `/profiles/${profileId}` : `/profiles/${profileId}/${subTab}`;
    navigate(path);
  };

  const handleAddProfile = async (payload: {
    platform: SocialPlatform;
    target: string;
    collection_schedule: CollectionSchedule;
  }) => {
    const newProfile = await createProfile(payload);
    await loadProfilesList();
    navigate(`/profiles/${newProfile.id}`);
  };

  const handleProfileDeleted = async () => {
    try {
      const data = await fetchProfiles();
      setProfiles(data);
      if (data.length > 0) {
        const nextId = data[0].id;
        const subTab = route.tab === 'profiles' ? 'profiles' : route.tab;
        if (subTab === 'profiles') {
          navigate('/profiles');
        } else {
          const path = subTab === 'overview' ? `/profiles/${nextId}` : `/profiles/${nextId}/${subTab}`;
          navigate(path);
        }
      } else {
        navigate('/profiles');
      }
    } catch {
      navigate('/profiles');
    }
  };

  const activeProfileId = route.profileId || (profiles.length > 0 ? profiles[0].id : null);

  return (
    <div className="app-shell">
      <Header
        profiles={profiles}
        selectedProfileId={activeProfileId}
        onSelectProfile={handleSelectProfile}
        selectedDays={selectedDays}
        onTimeRangeChange={setSelectedDays}
        onAddProfileClick={() => setIsAddModalOpen(true)}
      />

      <div className="app-body">
        <Sidebar
          currentTab={route.tab}
          profileId={activeProfileId}
          onNavigate={navigate}
        />

        <main className="main-viewport">
          {route.tab === 'profiles' && (
            <ProfilesPage
              onSelectProfile={handleSelectProfile}
              onAddClick={() => setIsAddModalOpen(true)}
              onProfileDeleted={handleProfileDeleted}
            />
          )}

          {route.tab === 'comparison' && <ComparisonPage />}

          {activeProfileId && (
            <>
              {route.tab === 'overview' && (
                <OverviewPage
                  profileId={activeProfileId}
                  selectedDays={selectedDays}
                  onProfileDeleted={handleProfileDeleted}
                />
              )}

              {route.tab === 'growth' && (
                <GrowthPage profileId={activeProfileId} selectedDays={selectedDays} />
              )}

              {route.tab === 'content' && (
                <ContentPage profileId={activeProfileId} selectedDays={selectedDays} />
              )}

              {route.tab === 'engagement' && (
                <EngagementPage profileId={activeProfileId} selectedDays={selectedDays} />
              )}

              {route.tab === 'frequency' && (
                <FrequencyPage profileId={activeProfileId} selectedDays={selectedDays} />
              )}

              {route.tab === 'anomalies' && <AnomaliesPage profileId={activeProfileId} />}

              {route.tab === 'raw-data' && <RawDataPage profileId={activeProfileId} />}
            </>
          )}

          {!activeProfileId && route.tab !== 'profiles' && route.tab !== 'comparison' && (
            <ProfilesPage
              onSelectProfile={handleSelectProfile}
              onAddClick={() => setIsAddModalOpen(true)}
              onProfileDeleted={handleProfileDeleted}
            />
          )}
        </main>
      </div>

      <AddProfileModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onAdd={handleAddProfile}
      />
    </div>
  );
}

export default App;

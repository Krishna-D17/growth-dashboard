import { useState, useEffect } from 'react';

export type DashboardTab =
  | 'overview'
  | 'growth'
  | 'content'
  | 'engagement'
  | 'frequency'
  | 'anomalies'
  | 'raw-data'
  | 'comparison'
  | 'profiles';

export interface RouteState {
  path: string;
  tab: DashboardTab;
  profileId: string | null;
}

export function parsePath(pathname: string): RouteState {
  const clean = pathname.replace(/\/+$/, '') || '/';

  if (clean === '/' || clean === '/profiles') {
    return { path: clean, tab: 'profiles', profileId: null };
  }

  if (clean === '/comparison') {
    return { path: clean, tab: 'comparison', profileId: null };
  }

  const match = clean.match(/^\/profiles\/([^/]+)(?:\/(growth|content|engagement|frequency|anomalies|raw-data))?$/);

  if (match) {
    const profileId = match[1];
    const section = match[2] as DashboardTab | undefined;
    return {
      path: clean,
      tab: section || 'overview',
      profileId,
    };
  }

  return { path: clean, tab: 'profiles', profileId: null };
}

export function navigate(path: string) {
  if (window.location.pathname !== path) {
    window.history.pushState({}, '', path);
    window.dispatchEvent(new Event('popstate'));
  }
}

export function useRoute(): { route: RouteState; navigate: (path: string) => void } {
  const [route, setRoute] = useState<RouteState>(() => parsePath(window.location.pathname));

  useEffect(() => {
    const handlePopState = () => {
      setRoute(parsePath(window.location.pathname));
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  return { route, navigate };
}

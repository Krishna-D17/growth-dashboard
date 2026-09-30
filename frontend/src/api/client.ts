import type {
  Profile,
  ProfileDetail,
  CollectionJob,
  GrowthAnalytics,
  EngagementAnalytics,
  ContentAnalytics,
  FrequencyAnalytics,
  TopPostItem,
  AnomalyResult,
  ComparisonResult,
  ProfileAnalyticsOverview,
  AIInsight,
} from '../types';

const BASE_URL = '/api';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `HTTP ${res.status} ${res.statusText}`;
    try {
      const errData = await res.json();
      if (errData && errData.detail) {
        if (typeof errData.detail === 'string') {
          errorDetail = errData.detail;
        } else if (Array.isArray(errData.detail)) {
          errorDetail = errData.detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ');
        }
      }
    } catch {
      // Ignore JSON parse failure for error response body
    }
    throw new Error(errorDetail);
  }
  return res.json() as Promise<T>;
}

export async function fetchProfiles(platform?: string): Promise<Profile[]> {
  const url = platform ? `${BASE_URL}/profiles?platform=${encodeURIComponent(platform)}` : `${BASE_URL}/profiles`;
  const res = await fetch(url);
  return handleResponse<Profile[]>(res);
}

export async function fetchProfile(profileId: string): Promise<ProfileDetail> {
  const res = await fetch(`${BASE_URL}/profiles/${encodeURIComponent(profileId)}`);
  return handleResponse<ProfileDetail>(res);
}

export async function createProfile(payload: {
  platform: string;
  target: string;
  collection_schedule?: string;
}): Promise<Profile> {
  const res = await fetch(`${BASE_URL}/profiles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<Profile>(res);
}

export async function updateProfileSchedule(
  profileId: string,
  schedule: string
): Promise<Profile> {
  const res = await fetch(`${BASE_URL}/profiles/${encodeURIComponent(profileId)}/schedule`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ collection_schedule: schedule }),
  });
  return handleResponse<Profile>(res);
}

export async function triggerCollection(
  profileId: string,
  postLimit: number = 10
): Promise<CollectionJob> {
  const res = await fetch(
    `${BASE_URL}/profiles/${encodeURIComponent(profileId)}/collect?post_limit=${postLimit}`,
    { method: 'POST' }
  );
  return handleResponse<CollectionJob>(res);
}

export async function fetchCollectionHistory(profileId: string): Promise<CollectionJob[]> {
  const res = await fetch(`${BASE_URL}/profiles/${encodeURIComponent(profileId)}/collection-jobs`);
  return handleResponse<CollectionJob[]>(res);
}

export async function fetchAnalyticsOverview(
  profileId: string,
  days?: number
): Promise<ProfileAnalyticsOverview> {
  const query = days ? `?days=${days}` : '';
  const res = await fetch(`${BASE_URL}/profiles/${encodeURIComponent(profileId)}/analytics/overview${query}`);
  return handleResponse<ProfileAnalyticsOverview>(res);
}

export async function fetchGrowthAnalytics(
  profileId: string,
  days?: number
): Promise<GrowthAnalytics> {
  const query = days ? `?days=${days}` : '';
  const res = await fetch(`${BASE_URL}/profiles/${encodeURIComponent(profileId)}/analytics/growth${query}`);
  return handleResponse<GrowthAnalytics>(res);
}

export async function fetchEngagementAnalytics(
  profileId: string,
  days?: number
): Promise<EngagementAnalytics> {
  const query = days ? `?days=${days}` : '';
  const res = await fetch(`${BASE_URL}/profiles/${encodeURIComponent(profileId)}/analytics/engagement${query}`);
  return handleResponse<EngagementAnalytics>(res);
}

export async function fetchContentAnalytics(
  profileId: string,
  days?: number
): Promise<ContentAnalytics> {
  const query = days ? `?days=${days}` : '';
  const res = await fetch(`${BASE_URL}/profiles/${encodeURIComponent(profileId)}/analytics/content${query}`);
  return handleResponse<ContentAnalytics>(res);
}

export async function fetchFrequencyAnalytics(
  profileId: string,
  days?: number
): Promise<FrequencyAnalytics> {
  const query = days ? `?days=${days}` : '';
  const res = await fetch(`${BASE_URL}/profiles/${encodeURIComponent(profileId)}/analytics/frequency${query}`);
  return handleResponse<FrequencyAnalytics>(res);
}

export async function fetchTopPosts(
  profileId: string,
  sortBy: string = 'engagement',
  limit: number = 10
): Promise<TopPostItem[]> {
  const res = await fetch(
    `${BASE_URL}/profiles/${encodeURIComponent(profileId)}/analytics/top-posts?sort_by=${encodeURIComponent(
      sortBy
    )}&limit=${limit}`
  );
  return handleResponse<TopPostItem[]>(res);
}

export async function fetchAnomalies(profileId: string): Promise<AnomalyResult[]> {
  const res = await fetch(`${BASE_URL}/profiles/${encodeURIComponent(profileId)}/analytics/anomalies`);
  return handleResponse<AnomalyResult[]>(res);
}

export async function fetchComparison(profileIds: string[]): Promise<ComparisonResult> {
  const param = profileIds.join(',');
  const res = await fetch(`${BASE_URL}/comparison?profile_ids=${encodeURIComponent(param)}`);
  return handleResponse<ComparisonResult>(res);
}

export async function downloadExportFile(
  profileId: string,
  category: 'profile' | 'snapshots' | 'posts' | 'jobs' | 'analytics' | 'report',
  format: 'csv' | 'json' | 'xlsx',
  days?: number
): Promise<void> {
  const queryParams = new URLSearchParams();
  queryParams.set('format', format);
  if (days && (category === 'analytics' || category === 'report')) {
    queryParams.set('days', String(days));
  }

  const url = `${BASE_URL}/profiles/${encodeURIComponent(profileId)}/export/${category}?${queryParams.toString()}`;
  const res = await fetch(url);
  if (!res.ok) {
    let errorMsg = `Export failed (HTTP ${res.status})`;
    try {
      const errData = await res.json();
      if (errData?.detail) errorMsg = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
    } catch {
      // Ignore JSON parse error
    }
    throw new Error(errorMsg);
  }

  const blob = await res.blob();
  const disposition = res.headers.get('content-disposition');
  let filename = `socialscope_${category}.${format}`;
  if (disposition && disposition.includes('filename=')) {
    const match = disposition.match(/filename="?([^";]+)"?/);
    if (match && match[1]) {
      filename = match[1];
    }
  }

  const blobUrl = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = blobUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(blobUrl);
}

export async function fetchAIInsights(
  profileId: string,
  days?: number
): Promise<AIInsight> {
  const query = days ? `?days=${days}` : '';
  const res = await fetch(`${BASE_URL}/profiles/${encodeURIComponent(profileId)}/ai-insights${query}`);
  return handleResponse<AIInsight>(res);
}

export async function deleteProfile(
  profileId: string
): Promise<{ detail: string; id: string; username?: string; platform?: string }> {
  const res = await fetch(`${BASE_URL}/profiles/${encodeURIComponent(profileId)}`, {
    method: 'DELETE',
  });
  return handleResponse<{ detail: string; id: string; username?: string; platform?: string }>(res);
}



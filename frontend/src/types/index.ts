export type SocialPlatform = 'instagram' | 'x' | 'facebook';

export type CollectionSchedule = 'manual' | 'every_6_hours' | 'every_12_hours' | 'daily';

export type JobStatus = 'pending' | 'running' | 'success' | 'partial' | 'failed';

export interface Profile {
  id: string;
  platform: SocialPlatform;
  platform_profile_id: string | null;
  username: string;
  display_name: string | null;
  profile_url: string;
  bio: string | null;
  profile_image_url: string | null;
  verified: boolean;
  collection_schedule: CollectionSchedule;
  last_collected_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProfileSnapshot {
  id: string;
  collected_at: string;
  followers: number | null;
  following: number | null;
  post_count: number | null;
  other_platform_metrics: Record<string, any> | null;
  collector_version: string | null;
}

export interface ProfileDetail extends Profile {
  latest_snapshot: ProfileSnapshot | null;
}

export interface CollectionJob {
  id: string;
  profile_id: string;
  platform: SocialPlatform;
  started_at: string;
  completed_at: string | null;
  status: JobStatus;
  records_collected: number;
  error_message: string | null;
  collector_version: string | null;
}

export interface GrowthAnalytics {
  current_followers: number | null;
  previous_followers: number | null;
  absolute_growth: number | null;
  growth_percent: number | null;
  growth_7d: number | null;
  growth_percent_7d: number | null;
  growth_30d: number | null;
  growth_percent_30d: number | null;
  growth_velocity: number | null;
  growth_acceleration: number | null;
  start_date: string | null;
  end_date: string | null;
}

export interface EngagementAnalytics {
  total_engagement: number | null;
  average_engagement: number | null;
  median_engagement: number | null;
  engagement_rate: number | null;
  available_metrics: string[];
  total_likes: number | null;
  total_comments: number | null;
  total_shares: number | null;
  total_views: number | null;
  sample_post_count: number;
}

export interface ContentTypeStats {
  content_type: string;
  post_count: number;
  average_engagement: number | null;
  median_engagement: number | null;
  total_views: number | null;
  average_views: number | null;
  posting_frequency: number | null;
}

export interface ContentAnalytics {
  by_content_type: ContentTypeStats[];
  total_posts: number;
}

export interface FrequencyAnalytics {
  posts_per_day: number;
  posts_per_week: number;
  posts_per_month: number;
  weekday_distribution: Record<string, number>;
  hourly_distribution: Record<number, number>;
  avg_posting_interval_hours: number | null;
  median_posting_interval_hours: number | null;
  min_posting_interval_hours: number | null;
  max_posting_interval_hours: number | null;
}

export interface TopPostItem {
  post_id: string;
  platform_post_id: string;
  url: string;
  caption: string | null;
  posted_at: string | null;
  media_type: string | null;
  metric_name: string;
  metric_value: number | null;
  likes: number | null;
  comments: number | null;
  shares: number | null;
  views: number | null;
  engagement: number | null;
  engagement_rate: number | null;
}

export interface AnomalyResult {
  id?: string;
  profile_id: string;
  metric: string;
  baseline: Record<string, any>;
  observed_value: number;
  severity: 'low' | 'medium' | 'high' | string;
  method: string;
  description: string;
  detected_at: string;
}

export interface ProfileComparisonItem {
  profile_id: string;
  platform: string;
  username: string;
  display_name: string | null;
  current_followers: number | null;
  growth_7d: number | null;
  growth_percent_7d: number | null;
  growth_30d: number | null;
  growth_percent_30d: number | null;
  growth_velocity: number | null;
  average_engagement: number | null;
  engagement_rate: number | null;
  posts_per_week: number;
  content_distribution: Record<string, number>;
}

export interface ComparisonResult {
  profiles: ProfileComparisonItem[];
  generated_at: string;
}

export interface ProfileAnalyticsOverview {
  profile_id: string;
  platform: string;
  username: string;
  growth: GrowthAnalytics;
  engagement: EngagementAnalytics;
  content: ContentAnalytics;
  frequency: FrequencyAnalytics;
  anomalies: AnomalyResult[];
}

export interface AIObservation {
  category: string;
  statement: string;
  supporting_metrics: string[];
}

export interface AIInsight {
  title: string;
  summary: string;
  observations: AIObservation[];
  data_points: string[];
  limitations?: string | null;
  provider: string;
  generated_at: string;
}


import React, { useState, useEffect, useCallback } from 'react';
import type { AIInsight } from '../types';
import { fetchAIInsights } from '../api/client';

interface AIInsightsCardProps {
  profileId: string;
  selectedDays?: number;
}

export const AIInsightsCard: React.FC<AIInsightsCardProps> = ({ profileId, selectedDays }) => {
  const [insight, setInsight] = useState<AIInsight | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [notConfigured, setNotConfigured] = useState<boolean>(false);

  const loadInsights = useCallback(async () => {
    setLoading(true);
    setError(null);
    setNotConfigured(false);
    try {
      const data = await fetchAIInsights(profileId, selectedDays);
      setInsight(data);
    } catch (err) {
      const msg = (err as Error).message || '';
      if (msg.includes('503') || msg.toLowerCase().includes('not configured')) {
        setNotConfigured(true);
      } else {
        setError(msg || 'AI insights temporarily unavailable.');
      }
    } finally {
      setLoading(false);
    }
  }, [profileId, selectedDays]);

  useEffect(() => {
    loadInsights();
  }, [loadInsights]);

  return (
    <div className="section-card ai-insights-card" style={{ marginTop: '2rem' }}>
      <div className="ai-card-header flex-between">
        <div>
          <h3 className="section-title flex-align-center" style={{ gap: '0.5rem' }}>
            <span>🤖</span> AI Insights &amp; Explanations
            <span className="badge-pill" style={{ background: 'rgba(139, 92, 246, 0.15)', color: '#a78bfa' }}>
              LLM Explanation Layer
            </span>
          </h3>
          <p className="section-desc">
            Generated from deterministic SocialScope analytics context. Explains observed metrics without modifying raw data.
          </p>
        </div>
        {insight && (
          <span className="provider-tag" style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Provider: <strong>{insight.provider}</strong>
          </span>
        )}
      </div>

      <div className="ai-card-body" style={{ marginTop: '1.25rem' }}>
        {loading && (
          <div className="ai-loading-state" style={{ padding: '1.5rem', textAlign: 'center' }}>
            <p className="text-muted">✨ Generating analytical insights from snapshot data...</p>
          </div>
        )}

        {!loading && notConfigured && (
          <div className="info-banner-small">
            ℹ️ <strong>AI Insights are not configured.</strong> Set <code>AI_PROVIDER</code> and <code>AI_API_KEY</code> in <code>.env</code> to enable LLM explanations. Raw deterministic metrics and export features remain 100% operational.
          </div>
        )}

        {!loading && error && !notConfigured && (
          <div className="error-banner-small flex-between">
            <span>⚠️ {error}</span>
            <button type="button" className="btn btn-secondary btn-sm" onClick={loadInsights}>
              Retry AI Generation
            </button>
          </div>
        )}

        {!loading && insight && !notConfigured && (
          <div className="ai-content-box">
            <h4 className="ai-title" style={{ fontSize: '1.05rem', color: 'var(--accent-cyan)', marginBottom: '0.5rem' }}>
              {insight.title}
            </h4>

            <p className="ai-summary" style={{ lineHeight: '1.6', color: '#e2e8f0', marginBottom: '1.25rem' }}>
              {insight.summary}
            </p>

            {/* Categorized Observations */}
            {insight.observations && insight.observations.length > 0 && (
              <div className="ai-observations-list" style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                <h5 style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Categorized Observations:</h5>
                {insight.observations.map((obs, idx) => (
                  <div key={idx} className="ai-observation-item" style={{ background: 'rgba(15, 22, 36, 0.6)', border: '1px solid var(--border-card)', borderRadius: '8px', padding: '0.85rem 1rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
                      <span className={`severity-badge severity-${obs.category === 'anomaly' ? 'high' : 'low'}`} style={{ textTransform: 'uppercase', fontSize: '0.7rem' }}>
                        {obs.category}
                      </span>
                      <span style={{ fontSize: '0.85rem', color: '#f8fafc', fontWeight: 500 }}>{obs.statement}</span>
                    </div>
                    {obs.supporting_metrics && obs.supporting_metrics.length > 0 && (
                      <div className="tag-cloud" style={{ marginTop: '0.35rem' }}>
                        {obs.supporting_metrics.map((m, mIdx) => (
                          <span key={mIdx} className="tag-item" style={{ fontSize: '0.75rem', background: 'rgba(255,255,255,0.04)', color: '#cbd5e1', border: '1px solid rgba(255,255,255,0.08)' }}>
                            {m}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Limitations disclaimer */}
            {insight.limitations && (
              <div className="ai-limitations-box" style={{ marginTop: '1.25rem', padding: '0.75rem 1rem', background: 'rgba(245, 158, 11, 0.08)', borderLeft: '3px solid var(--amber)', borderRadius: '6px', fontSize: '0.82rem', color: '#fef08a' }}>
                <strong>Observation Caveat:</strong> {insight.limitations}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

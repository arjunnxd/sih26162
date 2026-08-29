import type { Hotspot } from '../types/hotspot';
import { StatusBadge } from './StatusBadge';

interface HotspotDetailProps {
  hotspot: Hotspot | null;
  loading: boolean;
  error: string | null;
}

export function HotspotDetail({ hotspot, loading, error }: HotspotDetailProps) {
  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>
        <p style={{ fontSize: '0.875rem' }}>Loading hotspot intelligence…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p style={{ color: '#dc2626', fontSize: '0.875rem', fontWeight: 600 }}>Unable to load detail</p>
        <p style={{ color: '#64748b', fontSize: '0.75rem', marginTop: '0.375rem' }}>{error}</p>
      </div>
    );
  }

  if (!hotspot) {
    return (
      <div style={{ padding: '3rem 2rem', textAlign: 'center', color: '#94a3b8' }}>
        <p style={{ fontSize: '2rem', margin: '0 0 0.5rem 0' }}>🛰️</p>
        <p style={{ margin: 0, fontSize: '0.875rem' }}>
          Select a hotspot from the list to view detailed intelligence.
        </p>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Header */}
      <div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center', justifyContent: 'space-between' }}>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: '#0f172a', fontFamily: 'ui-monospace, Consolas, monospace' }}>
            {hotspot.id}
          </h3>
          <StatusBadge level={hotspot.priority_level} size="sm" />
        </div>
        <p style={{ margin: '0.375rem 0 0 0', fontSize: '0.75rem', color: '#64748b' }}>
          {hotspot.latitude.toFixed(4)}°N, {hotspot.longitude.toFixed(4)}°E
        </p>
      </div>

      {/* Detail sections */}
      <DetailSection title="THERMAL INFORMATION">
        <DetailRow label="FRP" value={`${hotspot.frp} MW`} />
        <DetailRow label="Brightness" value={`${hotspot.brightness.toFixed(1)} K`} />
        <DetailRow label="Confidence" value={`${(hotspot.confidence * 100).toFixed(0)}%`} />
        <DetailRow label="Detection Time" value={formatDate(hotspot.detected_at)} />
      </DetailSection>

      <DetailSection title="RISK">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <DetailRow label="Risk Score" value={hotspot.risk_score.toFixed(2)} />
          <StatusBadge level={hotspot.risk_level} size="sm" />
        </div>
      </DetailSection>

      <DetailSection title="HISTORICAL INTELLIGENCE">
        <DetailRow label="Historical Avg FRP" value={`${hotspot.historical_avg_frp.toFixed(1)} MW`} />
        <DetailRow label="Historical Max FRP" value={`${hotspot.historical_max_frp.toFixed(1)} MW`} />
        <DetailRow label="Detection Count" value={String(hotspot.historical_detection_count)} />
        <DetailRow label="New Event" value={hotspot.is_new_event ? 'Yes' : 'No'} />
        <DetailRow label="Recurring Event" value={hotspot.is_recurring ? 'Yes' : 'No'} />
      </DetailSection>

      <DetailSection title="ANOMALY">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <DetailRow label="Anomaly Score" value={hotspot.anomaly_score.toFixed(2)} />
          <StatusBadge level={hotspot.anomaly_level} size="sm" />
        </div>
      </DetailSection>

      <DetailSection title="PRIORITY">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <DetailRow label="Priority Score" value={hotspot.priority_score.toFixed(2)} />
          <StatusBadge level={hotspot.priority_level} size="sm" />
        </div>
      </DetailSection>

      <DetailSection title="WHY THIS PRIORITY">
        <ul style={{ margin: 0, padding: '0 0 0 1.25rem', display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
          {hotspot.priority_factors.map((factor, index) => (
            <li key={index} style={{ fontSize: '0.8125rem', color: '#334155', lineHeight: 1.5 }}>
              {factor}
            </li>
          ))}
        </ul>
      </DetailSection>
    </div>
  );
}

function DetailSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section style={{
      border: '1px solid #e2e8f0',
      borderRadius: '0.5rem',
      overflow: 'hidden',
      background: '#ffffff',
    }}>
      <h4 style={{
        margin: 0,
        padding: '0.625rem 1rem',
        fontSize: '0.6875rem',
        fontWeight: 700,
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        background: '#f8fafc',
        color: '#64748b',
        borderBottom: '1px solid #e2e8f0',
      }}>
        {title}
      </h4>
      <div style={{ padding: '0.875rem 1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {children}
      </div>
    </section>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.5rem' }}>
      <span style={{ fontSize: '0.75rem', color: '#64748b' }}>{label}</span>
      <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#0f172a' }}>{value}</span>
    </div>
  );
}

function formatDate(isoString: string): string {
  try {
    return new Date(isoString).toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoString;
  }
}
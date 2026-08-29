import type { Hotspot } from '../types/hotspot';
import { StatusBadge } from './StatusBadge';

interface HotspotCardProps {
  hotspot: Hotspot;
  selected: boolean;
  onClick: () => void;
}

export function HotspotCard({ hotspot, selected, onClick }: HotspotCardProps) {
  const isTopPriority = hotspot.priority_level === 'HIGH' || hotspot.priority_level === 'CRITICAL';

  return (
    <button
      onClick={onClick}
      style={{
        display: 'block',
        width: '100%',
        textAlign: 'left',
        cursor: 'pointer',
        background: selected
          ? 'linear-gradient(135deg, #eef2ff, #f8fafc)'
          : '#ffffff',
        border: selected ? '2px solid #6366f1' : '1px solid #e2e8f0',
        borderRadius: '0.75rem',
        padding: '1rem 1.25rem',
        marginBottom: '0.75rem',
        boxShadow: selected ? '0 4px 12px rgba(99, 102, 241, 0.15)' : '0 1px 3px rgba(0,0,0,0.05)',
        transition: 'box-shadow 0.2s, transform 0.2s, border-color 0.2s',
        position: 'relative',
        fontFamily: 'inherit',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
        e.currentTarget.style.transform = 'translateY(-2px)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = selected ? '0 4px 12px rgba(99, 102, 241, 0.15)' : '0 1px 3px rgba(0,0,0,0.05)';
        e.currentTarget.style.transform = 'translateY(0)';
      }}
    >
      {isTopPriority && (
        <span
          style={{
            position: 'absolute',
            top: '-0.625rem',
            left: '1rem',
            background: '#ef4444',
            color: 'white',
            fontSize: '0.625rem',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            padding: '0.125rem 0.625rem',
            borderRadius: '9999px',
            boxShadow: '0 2px 6px rgba(239, 68, 68, 0.4)',
          }}
        >
          ★ Top Priority
        </span>
      )}

      {/* Card header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
        <span style={{
          fontFamily: 'ui-monospace, Consolas, monospace',
          fontSize: '0.875rem',
          fontWeight: 600,
          color: '#0f172a',
        }}>
          {hotspot.id}
        </span>
        <StatusBadge level={hotspot.priority_level} size="sm" />
      </div>

      {/* Metrics grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(90px, 1fr))', gap: '0.5rem' }}>
        <Metric label="Priority" value={hotspot.priority_score.toFixed(1)} />
        <Metric label="Risk" value={hotspot.risk_level} />
        <Metric label="Anomaly" value={hotspot.anomaly_level} />
        <Metric label="FRP" value={`${hotspot.frp} MW`} />
        <Metric label="Confidence" value={`${(hotspot.confidence * 100).toFixed(0)}%`} />
      </div>

      {/* Status flags */}
      <div style={{ marginTop: '0.75rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
        {hotspot.is_new_event && <Flag label="NEW EVENT" bg="#fef3c7" color="#92400e" />}
        {hotspot.is_recurring && <Flag label="RECURRING" bg="#ede9fe" color="#6d28d9" />}
        {!hotspot.is_new_event && !hotspot.is_recurring && (
          <Flag label="STANDARD" bg="#f1f5f9" color="#475569" />
        )}
      </div>
    </button>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p style={{ margin: 0, fontSize: '0.625rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', color: '#64748b' }}>
        {label}
      </p>
      <p style={{ margin: 0, fontSize: '0.8125rem', fontWeight: 600, color: '#0f172a' }}>
        {value}
      </p>
    </div>
  );
}

function Flag({ label, bg, color }: { label: string; bg: string; color: string }) {
  return (
    <span style={{
      background: bg,
      color,
      fontSize: '0.625rem',
      fontWeight: 700,
      textTransform: 'uppercase',
      letterSpacing: '0.04em',
      padding: '0.1875rem 0.5rem',
      borderRadius: '0.25rem',
    }}>
      {label}
    </span>
  );
}
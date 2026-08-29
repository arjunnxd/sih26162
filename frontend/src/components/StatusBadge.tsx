import type { SeverityLevel } from '../types/hotspot';

interface StatusBadgeProps {
  level: string;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

const severityStyles: Record<string, { bg: string; text: string; border: string }> = {
  LOW: { bg: '#dcfce7', text: '#166534', border: '#86efac' },
  MODERATE: { bg: '#fef3c7', text: '#92400e', border: '#fcd34d' },
  MEDIUM: { bg: '#fef3c7', text: '#92400e', border: '#fcd34d' },
  HIGH: { bg: '#fee2e2', text: '#991b1b', border: '#fca5a5' },
  CRITICAL: { bg: '#fecaca', text: '#7f1d1d', border: '#ef4444' },
  NORMAL: { bg: '#dbeafe', text: '#1e40af', border: '#93c5fd' },
  UNUSUAL: { bg: '#fef3c7', text: '#92400e', border: '#fcd34d' },
  // Event classification types — visually distinct (purple/indigo family)
  HIGH_PRIORITY_INCIDENT: { bg: '#ede9fe', text: '#5b21b6', border: '#c4b5fd' },
  INDUSTRIAL_THERMAL_ACTIVITY: { bg: '#cffafe', text: '#155e75', border: '#67e8f9' },
  UNUSUAL_THERMAL_EVENT: { bg: '#fef3c7', text: '#92400e', border: '#fcd34d' },
  NORMAL_RECURRING_ACTIVITY: { bg: '#dcfce7', text: '#166534', border: '#86efac' },
  UNKNOWN: { bg: '#f1f5f9', text: '#475569', border: '#cbd5e1' },
};

export function StatusBadge({ level, size = 'md', showLabel = true }: StatusBadgeProps) {
  const normalizedLevel = level.toUpperCase() as SeverityLevel;
  const style = severityStyles[normalizedLevel] || severityStyles.LOW;

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.375rem',
        padding: size === 'sm' ? '0.125rem 0.5rem' : size === 'md' ? '0.25rem 0.75rem' : '0.375rem 1rem',
        fontSize: size === 'sm' ? '0.75rem' : size === 'md' ? '0.875rem' : '1rem',
        fontWeight: 600,
        borderRadius: '9999px',
        backgroundColor: style.bg,
        color: style.text,
        border: `1px solid ${style.border}`,
        textTransform: 'uppercase',
        letterSpacing: '0.025em',
      }}
    >
      {showLabel && (
        <span style={{
          width: '0.5rem',
          height: '0.5rem',
          borderRadius: '50%',
          backgroundColor: style.text,
        }} />
      )}
      {level}
    </span>
  );
}
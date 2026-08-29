import type { Hotspot } from '../types/hotspot';
import { HotspotCard } from './HotspotCard';

interface HotspotListProps {
  hotspots: Hotspot[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function HotspotList({ hotspots, selectedId, onSelect }: HotspotListProps) {
  // Sort by priority_score descending
  const sorted = [...hotspots].sort((a, b) => b.priority_score - a.priority_score);

  return (
    <section style={{ flex: 1, minWidth: 0 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 style={{ margin: 0, fontSize: '1.125rem', fontWeight: 700, color: '#0f172a' }}>
          Thermal Hotspots
        </h2>
        <span style={{ fontSize: '0.75rem', color: '#64748b', background: '#f1f5f9', padding: '0.25rem 0.625rem', borderRadius: '9999px', fontWeight: 600 }}>
          Sorted by priority ↓
        </span>
      </div>

      <div style={{ maxHeight: 'calc(100vh - 320px)', overflowY: 'auto', paddingRight: '0.25rem' }}>
        {sorted.map((hotspot) => (
          <HotspotCard
            key={hotspot.id}
            hotspot={hotspot}
            selected={selectedId === hotspot.id}
            onClick={() => onSelect(hotspot.id)}
          />
        ))}
      </div>
    </section>
  );
}
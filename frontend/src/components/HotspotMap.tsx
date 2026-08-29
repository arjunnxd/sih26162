import { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import type { Hotspot } from '../types/hotspot';

interface HotspotMapProps {
  hotspots: Hotspot[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

// Priority-level → marker color mapping (consistent with dashboard severity semantics)
const PRIORITY_COLORS: Record<string, string> = {
  LOW: '#16a34a', // green
  MODERATE: '#f59e0b', // amber / yellow-orange
  MEDIUM: '#f59e0b', // amber / yellow-orange
  HIGH: '#f97316', // orange / red-orange
  CRITICAL: '#dc2626', // red
};

const DEFAULT_CENTER: [number, number] = [20.5937, 78.9629]; // India overview
const DEFAULT_ZOOM = 4;

function isValidPosition(hotspot: Hotspot): boolean {
  return (
    Number.isFinite(hotspot.latitude) &&
    Number.isFinite(hotspot.longitude) &&
    hotspot.latitude >= -90 &&
    hotspot.latitude <= 90 &&
    hotspot.longitude >= -180 &&
    hotspot.longitude <= 180
  );
}

function createMarkerIcon(priorityLevel: string, isSelected: boolean) {
  const color = PRIORITY_COLORS[priorityLevel.toUpperCase()] ?? '#94a3b8';
  const size = isSelected ? 34 : 26;
  const html = [
    '<div style="',
    `width:${size}px;height:${size}px;`,
    'border-radius:50%;',
    `background:${color};`,
    'border:3px solid #ffffff;',
    'box-shadow:0 2px 6px rgba(0,0,0,0.45);',
    isSelected ? `outline:2px solid ${color};outline-offset:2px;` : '',
    '"></div>',
  ].join('');

  return L.divIcon({
    className: '',
    html,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
}

// Re-fits the viewport whenever the hotspot set changes
function FitBounds({ hotspots }: { hotspots: Hotspot[] }) {
  const map = useMap();

  useEffect(() => {
    const valid = hotspots.filter(isValidPosition);
    if (valid.length > 0) {
      const points = valid.map(
        (h): [number, number] => [h.latitude, h.longitude],
      );
      map.fitBounds(points, { padding: [28, 28] });
    }
  }, [hotspots, map]);

  return null;
}
export function HotspotMap({ hotspots, selectedId, onSelect }: HotspotMapProps) {
  const validHotspots = useMemo(
    () => hotspots.filter(isValidPosition),
    [hotspots],
  );

  const showEmptyState = hotspots.length === 0;
  const showNoCoordinates = hotspots.length > 0 && validHotspots.length === 0;

  return (
    <div
      style={{
        position: 'relative',
        height: '420px',
        borderRadius: '0.75rem',
        overflow: 'hidden',
        border: '1px solid #e2e8f0',
        zIndex: 0, // keep Leaflet panes inside this stacking context
      }}
    >
      <MapContainer
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        style={{ height: '100%', width: '100%', background: '#dbeafe' }}
        zoomControl
        scrollWheelZoom
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {validHotspots.length > 0 && (
          <FitBounds hotspots={validHotspots} />
        )}

        {validHotspots.map((hotspot) => (
          <Marker
            key={hotspot.id}
            position={[hotspot.latitude, hotspot.longitude]}
            icon={createMarkerIcon(hotspot.priority_level, selectedId === hotspot.id)}
            eventHandlers={{ click: () => onSelect(hotspot.id) }}
          >
            <Popup>
              <div style={{ fontFamily: 'system-ui, Segoe UI, Roboto, sans-serif', minWidth: '190px' }}>
                <div style={{ fontWeight: 700, fontSize: '0.8125rem', color: '#0f172a', fontFamily: 'ui-monospace, Consolas, monospace' }}>
                  {hotspot.id}
                </div>
                <div style={{ marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <PopupRow label="Priority Level" value={hotspot.priority_level} />
                  <PopupRow label="Priority Score" value={hotspot.priority_score.toFixed(2)} />
                  <PopupRow label="Risk Level" value={hotspot.risk_level} />
                  <PopupRow label="FRP" value={`${hotspot.frp} MW`} />
                  <PopupRow label="Confidence" value={`${(hotspot.confidence * 100).toFixed(0)}%`} />
                </div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>

      {/* Empty / invalid-coordinates overlays */}
      {showEmptyState && (
        <Overlay emoji="📡" title="No hotspots to display" subtitle="Satellite tracking is active." />
      )}
      {showNoCoordinates && (
        <Overlay emoji="🗺️" title="Coordinates unavailable" subtitle="Hotspot positions are missing or invalid." />
      )}

      {/* Priority legend */}
      <div
        style={{
          position: 'absolute',
          bottom: '1rem',
          left: '1rem',
          background: 'rgba(255,255,255,0.95)',
          border: '1px solid #e2e8f0',
          borderRadius: '0.5rem',
          padding: '0.5rem 0.75rem',
          boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
          display: 'flex',
          flexWrap: 'wrap',
          gap: '0.5rem',
          zIndex: 10,
        }}
      >
        {Object.entries(PRIORITY_COLORS).map(([level, color]) => (
          <span
            key={level}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3125rem', fontSize: '0.6875rem', fontWeight: 600, color: '#334155', textTransform: 'uppercase', letterSpacing: '0.03em' }}
          >
            <span style={{ width: '0.625rem', height: '0.625rem', borderRadius: '50%', backgroundColor: color }} />
            {level}
          </span>
        ))}
      </div>
    </div>
  );
}

function PopupRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', fontSize: '0.75rem' }}>
      <span style={{ color: '#64748b' }}>{label}</span>
      <span style={{ fontWeight: 600, color: '#0f172a' }}>{value}</span>
    </div>
  );
}

function Overlay({ emoji, title, subtitle }: { emoji: string; title: string; subtitle: string }) {
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f1f5f9',
        border: '1px solid #e2e8f0',
        borderRadius: '0.75rem',
        zIndex: 10,
        textAlign: 'center',
      }}
    >
      <p style={{ fontSize: '2rem', margin: '0 0 0.5rem 0' }}>{emoji}</p>
      <p style={{ margin: 0, fontSize: '0.9375rem', fontWeight: 700, color: '#0f172a' }}>{title}</p>
      <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.8125rem', color: '#64748b' }}>{subtitle}</p>
    </div>
  );
}
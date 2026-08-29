import type { Hotspot } from '../types/hotspot';

interface SummaryCardsProps {
  hotspots: Hotspot[];
}

export function SummaryCards({ hotspots }: SummaryCardsProps) {
  const totalHotspots = hotspots.length;
  const highCriticalCount = hotspots.filter(h => 
    h.priority_level === 'HIGH' || h.priority_level === 'CRITICAL'
  ).length;
  const newEventsCount = hotspots.filter(h => h.is_new_event).length;
  const recurringCount = hotspots.filter(h => h.is_recurring).length;

  const cards = [
    {
      label: 'Total Hotspots',
      value: totalHotspots,
      icon: '📍',
      color: '#3b82f6',
      bg: '#dbeafe',
    },
    {
      label: 'High / Critical Priority',
      value: highCriticalCount,
      icon: '🔴',
      color: '#ef4444',
      bg: '#fecaca',
    },
    {
      label: 'New Thermal Events',
      value: newEventsCount,
      icon: '⚡',
      color: '#f59e0b',
      bg: '#fef3c7',
    },
    {
      label: 'Recurring Thermal Sources',
      value: recurringCount,
      icon: '🔄',
      color: '#8b5cf6',
      bg: '#ede9fe',
    },
  ];

  return (
    <section style={{
      padding: '1.5rem 2rem',
      backgroundColor: '#f8fafc',
      borderBottom: '1px solid #e2e8f0',
    }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '1rem',
        }}>
          {cards.map((card, index) => (
            <div
              key={index}
              style={{
                background: 'white',
                borderRadius: '0.75rem',
                padding: '1.25rem',
                border: '1px solid #e2e8f0',
                boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                display: 'flex',
                alignItems: 'center',
                gap: '1rem',
                transition: 'box-shadow 0.2s, transform 0.2s',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)'; e.currentTarget.style.transform = 'translateY(-2px)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.05)'; e.currentTarget.style.transform = 'translateY(0)'; }}
            >
              <div style={{
                width: '3rem',
                height: '3rem',
                borderRadius: '0.75rem',
                backgroundColor: card.bg,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.5rem',
              }}>
                {card.icon}
              </div>
              <div>
                <p style={{
                  margin: 0,
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  color: '#64748b',
                }}>
                  {card.label}
                </p>
                <p style={{
                  margin: '0.25rem 0 0 0',
                  fontSize: '2rem',
                  fontWeight: 700,
                  color: '#0f172a',
                  lineHeight: 1,
                }}>
                  {card.value}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
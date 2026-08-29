export function Header() {
  return (
    <header style={{
      background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
      color: 'white',
      padding: '1.5rem 2rem',
      borderBottom: '1px solid #334155',
    }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h1 style={{
              margin: 0,
              fontSize: '1.75rem',
              fontWeight: 700,
              letterSpacing: '-0.025em',
              color: '#f8fafc',
            }}>
              AI THERMAL INTELLIGENCE PLATFORM
            </h1>
            <p style={{
              margin: '0.375rem 0 0 0',
              fontSize: '0.9375rem',
              color: '#94a3b8',
              fontWeight: 400,
            }}>
              Satellite Hotspot Monitoring and Prioritization
            </p>
          </div>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
            fontSize: '0.875rem',
            color: '#94a3b8',
          }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
              <span style={{
                width: '0.5rem',
                height: '0.5rem',
                borderRadius: '50%',
                backgroundColor: '#22c55e',
                boxShadow: '0 0 8px #22c55e',
              }} />
              LIVE
            </span>
            <span style={{ color: '#475569' }}>|</span>
            <span id="last-updated">Last updated: —</span>
          </div>
        </div>
      </div>
    </header>
  );
}
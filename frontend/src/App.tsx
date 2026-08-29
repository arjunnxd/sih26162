import { useEffect, useState, useCallback } from 'react';
import type { Hotspot } from './types/hotspot';
import { fetchHotspots, fetchHotspotDetail, checkHealth } from './services/api';
import { Header } from './components/Header';
import { SummaryCards } from './components/SummaryCards';
import { HotspotList } from './components/HotspotList';
import { HotspotDetail } from './components/HotspotDetail';
import { HotspotMap } from './components/HotspotMap';

function App() {
  const [hotspots, setHotspots] = useState<Hotspot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<Hotspot | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  function setLastUpdated() {
    const el = document.getElementById('last-updated');
    if (el) {
      el.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
    }
  }

  const refresh = useCallback(async () => {
    try {
      const [list, online] = await Promise.all([fetchHotspots(), checkHealth()]);
      setHotspots(list);
      setApiOnline(online);
      setLastUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setApiOnline(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadInitial() {
      try {
        const [list, online] = await Promise.all([fetchHotspots(), checkHealth()]);
        if (cancelled) return;
        setHotspots(list);
        setApiOnline(online);
        setLastUpdated();
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'Unknown error');
        setApiOnline(false);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadInitial();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectHotspot = useCallback(async (id: string) => {
    setSelectedId(id);
    setDetailLoading(true);
    setDetailError(null);
    setDetail(null);
    try {
      const d = await fetchHotspotDetail(id);
      setDetail(d);
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setDetailLoading(false);
    }
  }, []);

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', backgroundColor: '#e9edf2' }}>
        <Header />
        <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '4rem 2rem' }}>
          <div style={{ textAlign: 'center' }}>
            <p style={{ fontSize: '2rem', margin: '0 0 0.75rem 0' }}>🛰️</p>
            <p style={{ color: '#334155', fontWeight: 600, fontSize: '1rem', margin: 0 }}>
              Loading satellite intelligence…
            </p>
            <p style={{ color: '#94a3b8', fontSize: '0.8125rem', marginTop: '0.375rem' }}>
              Connecting to http://127.0.0.1:8000/api/hotspots
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', backgroundColor: '#e9edf2' }}>
        <Header />
        <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '4rem 2rem' }}>
          <div style={{ textAlign: 'center', maxWidth: '480px' }}>
            <p style={{ fontSize: '2rem', margin: '0 0 0.75rem 0' }}>⚠️</p>
            <p style={{ color: '#dc2626', fontWeight: 700, fontSize: '1.125rem', margin: '0 0 0.5rem 0' }}>
              Unable to reach the intelligence backend
            </p>
            <p style={{ color: '#64748b', fontSize: '0.875rem', margin: '0 0 1.25rem 0', lineHeight: 1.6 }}>
              {error}
              <br />
              Ensure the backend is running at http://127.0.0.1:8000
            </p>
            <button
              onClick={() => {
                setError(null);
                setLoading(true);
                refresh();
              }}
              style={{
                padding: '0.625rem 1.5rem',
                borderRadius: '0.5rem',
                border: 'none',
                background: '#2563eb',
                color: 'white',
                fontWeight: 600,
                fontSize: '0.875rem',
                cursor: 'pointer',
              }}
            >
              Retry Connection
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Header />
      <SummaryCards hotspots={hotspots} />

      <main style={{ padding: '1.5rem 2rem 2rem 2rem', flex: 1 }}>
        <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
          <section style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <h2 style={{ margin: 0, fontSize: '1.125rem', fontWeight: 700, color: '#0f172a' }}>
                Geospatial Overview
              </h2>
              <span style={{ fontSize: '0.75rem', color: '#64748b', background: '#f1f5f9', padding: '0.25rem 0.625rem', borderRadius: '9999px', fontWeight: 600 }}>
                {hotspots.length} tracked
              </span>
            </div>
            <HotspotMap hotspots={hotspots} selectedId={selectedId} onSelect={selectHotspot} />
          </section>

          {hotspots.length === 0 ? (
            <div style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: '0.75rem', padding: '3rem 2rem', textAlign: 'center' }}>
              <p style={{ fontSize: '2rem', margin: '0 0 0.75rem 0' }}>📡</p>
              <p style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: '#0f172a' }}>
                No hotspots detected
              </p>
              <p style={{ margin: '0.375rem 0 0 0', fontSize: '0.875rem', color: '#64748b' }}>
                Hotspots will appear here once satellite data is available.
              </p>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(0, 1fr)', gap: '1.5rem', alignItems: 'start' }}>
              <HotspotList hotspots={hotspots} selectedId={selectedId} onSelect={selectHotspot} />
              <section style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: '0.75rem', overflow: 'hidden', position: 'sticky', top: '1rem' }}>
                <div style={{ padding: '0.875rem 1.25rem', borderBottom: '1px solid #e2e8f0', background: '#f8fafc' }}>
                  <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: '#0f172a' }}>
                    Hotspot Intelligence
                  </h2>
                </div>
                <div style={{ padding: '1.25rem' }}>
                  <HotspotDetail hotspot={detail} loading={detailLoading} error={detailError} />
                </div>
              </section>
            </div>
          )}
        </div>
      </main>

      <footer style={{ padding: '1rem 2rem', textAlign: 'center', fontSize: '0.75rem', color: '#94a3b8', borderTop: '1px solid #e2e8f0', background: 'white' }}>
        SIH26162 · Thermal Intelligence Dashboard · Backend: {apiOnline ? 'ONLINE' : 'OFFLINE'}
      </footer>
    </div>
  );
}

export default App;

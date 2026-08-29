import { useEffect, useState } from 'react';

interface Hotspot {
  id: string;
  latitude: number;
  longitude: number;
  detected_at: string;
  brightness: number;
  frp: number;
  confidence: number;
}

interface HotspotListResponse {
  hotspots: Hotspot[];
}

function App() {
  const [hotspots, setHotspots] = useState<Hotspot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchHotspots() {
      try {
        setLoading(true);
        const response = await fetch('http://127.0.0.1:8000/api/hotspots');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data: HotspotListResponse = await response.json();
        setHotspots(data.hotspots);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }

    fetchHotspots();
  }, []);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', fontSize: '24px' }}>
        Loading...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', fontSize: '24px', color: 'red' }}>
        Error: {error}
      </div>
    );
  }

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h1>Hotspots</h1>
      <p>Total count: {hotspots.length}</p>
      <ul style={{ listStyle: 'none', padding: 0 }}>
        {hotspots.map((hotspot) => (
          <li key={hotspot.id} style={{ border: '1px solid #ccc', marginBottom: '10px', padding: '10px', borderRadius: '4px' }}>
            <strong>ID:</strong> {hotspot.id}<br />
            <strong>Latitude:</strong> {hotspot.latitude}<br />
            <strong>Longitude:</strong> {hotspot.longitude}<br />
            <strong>FRP:</strong> {hotspot.frp}<br />
            <strong>Confidence:</strong> {hotspot.confidence}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default App;

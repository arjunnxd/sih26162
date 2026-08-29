import type { Hotspot, HotspotListResponse } from '../types/hotspot';

const API_BASE = 'http://127.0.0.1:8000';

export async function fetchHotspots(): Promise<Hotspot[]> {
  const response = await fetch(`${API_BASE}/api/hotspots`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  const data: HotspotListResponse = await response.json();
  return data.hotspots;
}

export async function fetchHotspotDetail(hotspotId: string): Promise<Hotspot> {
  const response = await fetch(`${API_BASE}/api/hotspots/${hotspotId}`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/health`);
    return response.ok;
  } catch {
    return false;
  }
}
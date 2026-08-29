export interface Hotspot {
  // Original fields
  id: string;
  latitude: number;
  longitude: number;
  detected_at: string;
  brightness: number;
  frp: number;
  confidence: number;

  // Risk fields
  risk_level: string;
  risk_score: number;

  // Historical fields
  historical_avg_frp: number;
  historical_max_frp: number;
  historical_detection_count: number;
  is_recurring: boolean;
  is_new_event: boolean;

  // Anomaly fields
  anomaly_score: number;
  anomaly_level: string;

  // Priority fields
  priority_score: number;
  priority_level: string;
  priority_factors: string[];
}

export interface HotspotListResponse {
  hotspots: Hotspot[];
}

export type SeverityLevel = 'LOW' | 'MODERATE' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'NORMAL' | 'UNUSUAL';
export interface ClassificationScoreBreakdown {
  winning_rule: string;
  precedence_order: string[];
  availability_ratio: number;
  present_signal_groups: string[];
  missing_signal_groups: string[];
  rule_strength: number;
  matched_conditions: number;
  considered_conditions: number;
  consistency_factor: number;
  normalization_warnings: string[];
}

export interface MatchedSignals {
  thermal?: { frp: number; confidence: number };
  risk?: { risk_score: number; risk_level: string };
  history?: {
    historical_avg_frp: number;
    historical_max_frp: number;
    historical_detection_count: number;
    is_recurring: boolean;
    is_new_event: boolean;
  };
  anomaly?: { anomaly_score: number; anomaly_level: string };
  geospatial?: {
    nearest_facility_type: string;
    nearest_facility_distance_m: number;
    industrial_proximity_score: number;
    near_critical_infrastructure: boolean;
  };
  present_signals: string[];
  missing_signals: string[];
  used_signals: string[];
}

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

  // Geospatial / proximity intelligence (optional — null when unavailable)
  nearest_facility_name: string | null;
  nearest_facility_type: string | null;
  nearest_facility_distance_m: number | null;
  nearby_facility_count: number | null;
  industrial_proximity_score: number | null;
  near_critical_infrastructure: boolean | null;

  // Explainable event classification
  event_type: string;
  classification_confidence: number;
  classification_reasons: string[];
  matched_signals: MatchedSignals;
  classification_score_breakdown: ClassificationScoreBreakdown;
  disclaimer: string;
}

export interface HotspotListResponse {
  hotspots: Hotspot[];
}

export type SeverityLevel = 'LOW' | 'MODERATE' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'NORMAL' | 'UNUSUAL';
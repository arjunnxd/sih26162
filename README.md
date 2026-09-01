🔥 AgniVega
AI-Powered Satellite Thermal Intelligence & Hotspot Prioritization Platform

AgniVega is an explainable thermal intelligence platform designed to transform raw satellite thermal hotspot observations into actionable, prioritized geospatial intelligence.

Instead of simply displaying detected hotspots, AgniVega analyzes each thermal event through multiple intelligence layers — thermal risk, historical behavior, anomaly detection, infrastructure proximity, priority scoring, and explainable event classification — and presents the results through an interactive dashboard and geospatial map.

🎯 Objective

The objective of AgniVega is to help operators quickly understand and prioritize thermal events detected through satellite data.

The system answers:

🔥 How risky is the thermal hotspot?
📊 Is the event new or recurring?
📈 Is the thermal activity anomalous compared with historical behavior?
🏭 Is it near industrial infrastructure?
🏢 Is it near critical infrastructure?
🚨 Which hotspot should receive attention first?
🧠 What type of thermal event does the available evidence suggest?
💡 Why did the system assign that priority or classification?



🚀 Core Workflow
Satellite Thermal Data
        ↓
Data Normalization
        ↓
Data Quality & Deduplication
        ↓
Risk Analysis
        ↓
Historical Intelligence
        ↓
Anomaly Detection
        ↓
Geospatial / Infrastructure Analysis
        ↓
Priority Scoring
        ↓
Explainable Event Classification
        ↓
FastAPI REST API
        ↓
React Dashboard
        ↓
Interactive OpenStreetMap



🧠 Intelligence Layers

1. Thermal Risk Analysis

Evaluates thermal activity using signals such as:

Fire Radiative Power (FRP)
Detection confidence

Produces a normalized risk score and risk level.

2. Historical Intelligence

Analyzes previous observations to determine:

Historical average FRP
Historical maximum FRP
Detection frequency
Recurring activity
Newly detected events
3. Anomaly Detection

Identifies thermal behavior that significantly differs from historical patterns.

4. Geospatial Intelligence

Adds location-based context using:

Nearby infrastructure
Nearest facility
Facility type
Distance
Industrial proximity
Critical-infrastructure proximity
5. Priority Analysis

Combines available intelligence signals to rank hotspots into:

LOW
MODERATE
HIGH
CRITICAL

Each priority also provides explainable factors describing why the hotspot received that priority.

6. Explainable Event Classification

AgniVega classifies thermal events into:

HIGH_PRIORITY_INCIDENT
INDUSTRIAL_THERMAL_ACTIVITY
UNUSUAL_THERMAL_EVENT
NORMAL_RECURRING_ACTIVITY
UNKNOWN

The classification engine is:

Deterministic
Rule-based
Explainable
Configurable
Safe with missing or invalid data



🗺️ Interactive Geospatial Dashboard

AgniVega provides an interactive OpenStreetMap-based visualization using Leaflet.

The dashboard provides:

Real hotspot coordinates
Priority-based markers
Map zoom and controls
Hotspot popups
Automatic map bounds
Hotspot selection
Synchronized intelligence panel
Infrastructure context



🏗️ Technology Stack

Layer	Technology
Backend	Python
API	FastAPI
Server	Uvicorn
Validation	Pydantic
Frontend	React
Language	TypeScript
Build Tool	Vite
Mapping	Leaflet
React Mapping	React-Leaflet
Map Data	OpenStreetMap
Intelligence	Rule-Based Analysis
Geospatial	Geographic Distance Calculations



⭐ Why AgniVega?

Traditional systems:

Satellite Detection
        ↓
Hotspot
        ↓
Map

AgniVega:

Satellite Detection
        ↓
Quality
        ↓
Risk
        ↓
Historical Behaviour
        ↓
Anomaly
        ↓
Infrastructure Context
        ↓
Priority
        ↓
Event Classification
        ↓
Explainable Decision Support
        ↓
Dashboard + Map

AgniVega doesn't just show where a hotspot is — it helps explain what the hotspot means and which events deserve attention first.




⚠️ Decision-Support Disclaimer

AgniVega is a decision-support intelligence platform.

Its scores and classifications are derived from available thermal, historical, and geospatial signals. They should not be interpreted as definitive confirmation of a fire, explosion, industrial accident, or emergency.

Human/operator verification remains necessary before operational decisions are made.

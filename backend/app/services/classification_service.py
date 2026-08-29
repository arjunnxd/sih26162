"""Explainable, rule-based Thermal Event Classification Engine (SIH26162).

Part of Member 2's Intelligence and Data Analysis layer.

PURPOSE
-------
Classify a thermal hotspot into one prototype decision-support category using
existing intelligence signals: risk, history/anomaly, and geospatial proximity.
The classifier is rule-based, deterministic, explainable, configurable, and
uses no machine learning and no randomness.

HONESTY DISCLAIMER
------------------
These categories are DECISION-SUPPORT labels derived from available thermal
signals. They do NOT claim a real fire, explosion, industrial accident, or
emergency is occurring, and no real-world certainty should be inferred.

CATEGORIES
----------
* HIGH_PRIORITY_INCIDENT ........ high thermal risk combined with novelty
                                   (newly detected and/or strong anomaly) and/or
                                   proximity to critical infrastructure.
* INDUSTRIAL_THERMAL_ACTIVITY ... meaningful proximity to industrial
                                   infrastructure plus historical consistency
                                   (recurring or within-bounds thermal pattern).
* UNUSUAL_THERMAL_EVENT ......... newly detected and/or strongly anomalous
                                   thermal signal without elevated risk.
* NORMAL_RECURRING_ACTIVITY ..... recurring, low-anomaly, low-risk pattern.
* UNKNOWN ........................ insufficient evidence or no rule matched.

RULE PRECEDENCE (first match wins, highest -> lowest)
-----------------------------------------------------
HIGH_PRIORITY_INCIDENT -> INDUSTRIAL_THERMAL_ACTIVITY -> UNUSUAL_THERMAL_EVENT
-> NORMAL_RECURRING_ACTIVITY -> UNKNOWN

INPUT TOLERANCE
---------------
Every input is optional. Missing / None / invalid / out-of-range values are
handled with safe defaults (see ``_normalize_score`` and helpers). The
classifier never raises for bad inputs and never imports FastAPI or Pydantic.

CONFIDENCE (0-100, deterministic)
---------------------------------
Rule confidence, not real-world certainty::

    confidence = (0.60 * rule_strength + 0.40 * availability) * consistency

* rule_strength = fraction of the winning rule's considered conditions that
  were satisfied (0..1)
* availability  = fraction of the four signal groups present (risk, history,
  anomaly, geospatial) (0..1)
* consistency   = 1.0 by default, 0.9 when a contradicting signal is present
  (e.g. recurring activity matched as a new/incident-like category)
* UNKNOWN confidence is capped at ``UNKNOWN_CONFIDENCE_MAX`` (max 20).
"""

from __future__ import annotations

import math
from typing import Optional

EVENT_TYPES = (
    "NORMAL_RECURRING_ACTIVITY",
    "INDUSTRIAL_THERMAL_ACTIVITY",
    "UNUSUAL_THERMAL_EVENT",
    "HIGH_PRIORITY_INCIDENT",
    "UNKNOWN",
)

PRECEDENCE_ORDER = (
    "HIGH_PRIORITY_INCIDENT",
    "INDUSTRIAL_THERMAL_ACTIVITY",
    "UNUSUAL_THERMAL_EVENT",
    "NORMAL_RECURRING_ACTIVITY",
    "UNKNOWN",
)

class ClassificationConfig:
    """Configurable rule thresholds for the thermal event classifier.

    All values are deterministic and documented; tuning these constants keeps
    the whole engine explainable without touching rule logic.
    """

    # --- Risk signal thresholds --------------------------------
    HIGH_RISK_MIN_SCORE = 60.0  # risk_score >= this is "high risk"
    HIGH_RISK_LEVELS = ("HIGH", "CRITICAL")
    LOW_RISK_MAX_SCORE = 30.0  # risk_score < this is "low risk"
    LOW_RISK_LEVELS = ("LOW",)

    # --- Anomaly signal thresholds -----------------------------
    HIGH_ANOMALY_MIN_SCORE = 50.0  # anomaly_score >= this is strong anomaly
    HIGH_ANOMALY_LEVELS = ("UNUSUAL", "HIGHLY_UNUSUAL")
    LOW_ANOMALY_MAX_SCORE = 30.0  # anomaly_score < this is low anomaly
    LOW_ANOMALY_LEVELS = ("NORMAL",)

    # --- Historical / recurrence thresholds ---------------------
    RECURRING_MIN_DETECTION_COUNT = 3  # count >= this is recurring behaviour

    # --- Geospatial / proximity thresholds ----------------------
    INDUSTRIAL_PROXIMITY_MIN_SCORE = 50.0  # proximity score >= this is "meaningful"
    NEAR_FACILITY_MAX_DISTANCE_M = 5000.0  # nearest facility within this = near
    INDUSTRIAL_FACILITY_TYPES = (
        "industrial_plant",
        "power_plant",
        "refinery",
        "chemical_facility",
        "warehouse",
    )

    # --- Supporting thermal signals -----------------------------
    HIGH_FRP_MIN = 200.0  # FRP >= this is an elevated signal
    HIGH_CONFIDENCE_MIN = 0.80  # detection confidence >= this is high

    # --- Confidence construction --------------------------------
    STRENGTH_WEIGHT = 0.60
    AVAILABILITY_WEIGHT = 0.40
    CONSISTENCY_PENALTY = 0.90  # multiplier when a contradicting signal exists
    UNKNOWN_CONFIDENCE_MAX = 20.0  # UNKNOWN confidence never exceeds this


def _to_float(value, default=None, clamp_min=None, clamp_max=None):
    """Coerce a raw value into a float, or return ``default`` when unsafe.

    Rejects None, booleans, non-numeric strings, NaN and infinities. Optionally
    clamps into ``[clamp_min, clamp_max]`` so bad values degrade to the boundary.
    """
    if value is None or isinstance(value, bool):
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(number) or math.isinf(number):
        return default
    if clamp_min is not None:
        number = max(number, float(clamp_min))
    if clamp_max is not None:
        number = min(number, float(clamp_max))
    return number


def _normalize_score(value, name):
    """Normalize a 0-100 score, returning ``(value, warning_or_None)``."""
    if value is None:
        return None, None  # absent signal, not a normalization error
    if isinstance(value, bool):
        return None, f"{name} is not a numeric score"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None, f"{name} is not a numeric score"
    if math.isnan(number) or math.isinf(number):
        return None, f"{name} is not a finite score"
    warning = None
    if number < 0.0:
        number, warning = 0.0, f"{name} was below 0 and was clamped to 0"
    elif number > 100.0:
        number, warning = 100.0, f"{name} was above 100 and was clamped to 100"
    return round(number, 2), warning


def _to_bool(value, default=None):
    """Coerce common truthy/falsy values to bool, else ``default``."""
    if value is None or isinstance(value, bool):
        return value if value is not None else default
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("true", "1", "yes", "y", "on"):
            return True
        if text in ("false", "0", "no", "n", "off"):
            return False
    return default

def _clean_signals(**kwargs) -> dict:
    """Sanitize every input into a deterministic internal signal bundle.

    Keys match the caller's parameter names plus a ``warnings`` list.
    Out-of-range 0-100 scores are clamped and reported; absent signals stay None.
    """
    risk_score, w1 = _normalize_score(kwargs.get("risk_score"), "risk_score")
    anomaly_score, w2 = _normalize_score(kwargs.get("anomaly_score"), "anomaly_score")
    industrial_proximity_score, w3 = _normalize_score(
        kwargs.get("industrial_proximity_score"), "industrial_proximity_score"
    )

    detection_count = _to_float(kwargs.get("historical_detection_count"), clamp_min=0.0)
    if detection_count is not None:
        detection_count = int(round(detection_count))

    risk_level_raw = kwargs.get("risk_level")
    risk_level_value = (
        risk_level_raw.strip().upper() if isinstance(risk_level_raw, str) else None
    )
    anomaly_level_raw = kwargs.get("anomaly_level")
    anomaly_level_value = (
        anomaly_level_raw.strip().upper() if isinstance(anomaly_level_raw, str) else None
    )
    facility_type_raw = kwargs.get("nearest_facility_type")
    facility_type_value = (
        facility_type_raw.strip() if isinstance(facility_type_raw, str) else None
    )

    return {
        "frp": _to_float(kwargs.get("frp"), clamp_min=0.0),
        "confidence": _to_float(kwargs.get("confidence"), clamp_min=0.0),
        "risk_score": risk_score,
        "risk_level": risk_level_value,
        "historical_avg_frp": _to_float(kwargs.get("historical_avg_frp"), clamp_min=0.0),
        "historical_max_frp": _to_float(kwargs.get("historical_max_frp"), clamp_min=0.0),
        "historical_detection_count": detection_count,
        "is_recurring": _to_bool(kwargs.get("is_recurring")),
        "is_new_event": _to_bool(kwargs.get("is_new_event")),
        "anomaly_score": anomaly_score,
        "anomaly_level": anomaly_level_value,
        "nearest_facility_type": facility_type_value,
        "nearest_facility_distance_m": _to_float(
            kwargs.get("nearest_facility_distance_m"), clamp_min=0.0
        ),
        "industrial_proximity_score": industrial_proximity_score,
        "near_critical_infrastructure": _to_bool(kwargs.get("near_critical_infrastructure")),
        "warnings": [note for note in (w1, w2, w3) if note],
    }


def _strength(conditions):
    """Return ``(strength_ratio, met_count, considered_count)``.

    Strength is the fraction of a rule's *considered* conditions that were met;
    conditions whose underlying signals are absent are excluded so missing data
    does not inflate strength (availability handles that instead).
    """
    considered = [condition for condition in conditions if condition[2]]
    met = [condition for condition in considered if condition[1]]
    if not considered:
        return 0.0, 0, 0
    return round(len(met) / len(considered), 4), len(met), len(considered)


def _signal_groups(signals: dict) -> dict:
    """Group presence of the four signal families: risk, history, anomaly, geospatial."""
    risk = signals["risk_score"] is not None or signals["risk_level"] is not None
    history = any(
        signals[key] is not None
        for key in (
            "historical_avg_frp",
            "historical_max_frp",
            "historical_detection_count",
            "is_recurring",
            "is_new_event",
        )
    )
    anomaly = signals["anomaly_score"] is not None or signals["anomaly_level"] is not None
    geospatial = any(
        signals[key] is not None
        for key in (
            "nearest_facility_type",
            "nearest_facility_distance_m",
            "industrial_proximity_score",
            "near_critical_infrastructure",
        )
    )
    return {"risk": risk, "history": history, "anomaly": anomaly, "geospatial": geospatial}

def _rule_high_priority(signals: dict, cfg: ClassificationConfig) -> dict:
    """HIGH_PRIORITY_INCIDENT: high risk AND (novelty OR critical proximity)."""
    risk_known = signals["risk_score"] is not None or signals["risk_level"] is not None
    high_risk = (
        signals["risk_score"] is not None and signals["risk_score"] >= cfg.HIGH_RISK_MIN_SCORE
    ) or (signals["risk_level"] in cfg.HIGH_RISK_LEVELS)

    novelty_known = (
        signals["is_new_event"] is not None
        or signals["anomaly_score"] is not None
        or signals["anomaly_level"] is not None
    )
    novel = (
        signals["is_new_event"] is True
        or (
            signals["anomaly_score"] is not None
            and signals["anomaly_score"] >= cfg.HIGH_ANOMALY_MIN_SCORE
        )
        or (signals["anomaly_level"] in cfg.HIGH_ANOMALY_LEVELS)
    )

    critical_known = signals["near_critical_infrastructure"] is not None
    critical_near = signals["near_critical_infrastructure"] is True

    conditions = [
        ("high_risk", high_risk, risk_known),
        ("novel_or_strongly_anomalous", novel, novelty_known),
        ("near_critical_infrastructure", critical_near, critical_known),
    ]
    matched = high_risk and (novel or critical_near)

    reasons = []
    if high_risk:
        reasons.append("High thermal risk detected")
    if signals["is_new_event"] is True:
        reasons.append("Thermal activity is newly detected")
    if (
        signals["anomaly_score"] is not None
        and signals["anomaly_score"] >= cfg.HIGH_ANOMALY_MIN_SCORE
    ) or (signals["anomaly_level"] in cfg.HIGH_ANOMALY_LEVELS):
        reasons.append("Strong deviation from historical thermal pattern")
    if critical_near:
        reasons.append("Hotspot is near critical infrastructure")

    consistency = 1.0
    if signals["is_recurring"] is True:
        consistency = cfg.CONSISTENCY_PENALTY
        reasons.append("Note: activity is historically recurring (reduces novelty)")

    return {"matched": matched, "conditions": conditions,
            "reasons": reasons, "consistency": consistency}


def _rule_industrial(signals: dict, cfg: ClassificationConfig) -> dict:
    """INDUSTRIAL_THERMAL_ACTIVITY: industrial proximity + historical consistency."""
    proximity_known = (
        signals["industrial_proximity_score"] is not None
        or (
            signals["nearest_facility_type"] is not None
            and signals["nearest_facility_distance_m"] is not None
        )
    )
    proximity = (
        signals["industrial_proximity_score"] is not None
        and signals["industrial_proximity_score"] >= cfg.INDUSTRIAL_PROXIMITY_MIN_SCORE
    ) or (
        signals["nearest_facility_type"] in cfg.INDUSTRIAL_FACILITY_TYPES
        and signals["nearest_facility_distance_m"] is not None
        and signals["nearest_facility_distance_m"] <= cfg.NEAR_FACILITY_MAX_DISTANCE_M
    )

    history_known = (
        signals["is_recurring"] is not None
        or signals["historical_detection_count"] is not None
        or signals["anomaly_score"] is not None
        or signals["anomaly_level"] is not None
    )
    history_consistent = (
        signals["is_recurring"] is True
        or (
            signals["historical_detection_count"] is not None
            and signals["historical_detection_count"] >= cfg.RECURRING_MIN_DETECTION_COUNT
        )
        or (
            signals["anomaly_score"] is not None
            and signals["anomaly_score"] < cfg.HIGH_ANOMALY_MIN_SCORE
        )
        or (signals["anomaly_level"] in cfg.LOW_ANOMALY_LEVELS)
    )

    type_near_known = (
        signals["nearest_facility_type"] is not None
        and signals["nearest_facility_distance_m"] is not None
    )
    type_near = (
        signals["nearest_facility_type"] in cfg.INDUSTRIAL_FACILITY_TYPES
        and signals["nearest_facility_distance_m"] is not None
        and signals["nearest_facility_distance_m"] <= cfg.NEAR_FACILITY_MAX_DISTANCE_M
    )

    conditions = [
        ("industrial_proximity", proximity, proximity_known),
        ("historically_consistent", history_consistent, history_known),
        ("industrial_facility_type_nearby", type_near, type_near_known),
    ]
    matched = proximity and history_consistent

    reasons = []
    if proximity:
        reasons.append("Hotspot is near industrial infrastructure")
    if history_consistent:
        if signals["is_recurring"] is True:
            reasons.append("Activity pattern is historically recurring")
        elif (
            signals["historical_detection_count"] is not None
            and signals["historical_detection_count"] >= cfg.RECURRING_MIN_DETECTION_COUNT
        ):
            reasons.append("Repeated thermal detections recorded at this location")
        elif signals["anomaly_score"] is not None or signals["anomaly_level"] is not None:
            reasons.append("Thermal activity is consistent with past patterns")

    consistency = 1.0
    if signals["is_new_event"] is True:
        consistency = cfg.CONSISTENCY_PENALTY
        reasons.append(
            "Note: activity is newly detected "
            "(weakens the industrial-consistency interpretation)"
        )

    return {"matched": matched, "conditions": conditions,
            "reasons": reasons, "consistency": consistency}

def _rule_unusual(signals: dict, cfg: ClassificationConfig) -> dict:
    """UNUSUAL_THERMAL_EVENT: newly detected and/or strongly anomalous."""
    new_known = signals["is_new_event"] is not None
    new_event = signals["is_new_event"] is True

    anomaly_known = (
        signals["anomaly_score"] is not None or signals["anomaly_level"] is not None
    )
    strong_anomaly = (
        signals["anomaly_score"] is not None
        and signals["anomaly_score"] >= cfg.HIGH_ANOMALY_MIN_SCORE
    ) or (signals["anomaly_level"] in cfg.HIGH_ANOMALY_LEVELS)

    conditions = [
        ("newly_detected", new_event, new_known),
        ("strongly_anomalous", strong_anomaly, anomaly_known),
    ]
    matched = new_event or strong_anomaly

    reasons = []
    if new_event:
        reasons.append("Thermal activity is newly detected")
    if strong_anomaly:
        reasons.append("Strong deviation from historical thermal pattern")

    consistency = 1.0
    if signals["is_recurring"] is True:
        consistency = cfg.CONSISTENCY_PENALTY
        reasons.append("Note: activity is historically recurring (reduces novelty)")

    return {"matched": matched, "conditions": conditions,
            "reasons": reasons, "consistency": consistency}


def _rule_normal(signals: dict, cfg: ClassificationConfig) -> dict:
    """NORMAL_RECURRING_ACTIVITY: recurring + not new + low anomaly + low risk."""
    recurring_known = (
        signals["is_recurring"] is not None
        or signals["historical_detection_count"] is not None
    )
    recurring = (
        signals["is_recurring"] is True
        or (
            signals["historical_detection_count"] is not None
            and signals["historical_detection_count"] >= cfg.RECURRING_MIN_DETECTION_COUNT
        )
    )
    not_new_known = signals["is_new_event"] is not None
    not_new = not (signals["is_new_event"] is True)

    anomaly_known = (
        signals["anomaly_score"] is not None or signals["anomaly_level"] is not None
    )
    low_anomaly = (
        signals["anomaly_score"] is None
        or signals["anomaly_score"] < cfg.LOW_ANOMALY_MAX_SCORE
        or signals["anomaly_level"] in cfg.LOW_ANOMALY_LEVELS
    )

    risk_known = signals["risk_score"] is not None or signals["risk_level"] is not None
    low_risk = (
        signals["risk_score"] is None
        or signals["risk_score"] < cfg.LOW_RISK_MAX_SCORE
        or signals["risk_level"] in cfg.LOW_RISK_LEVELS
    )

    conditions = [
        ("recurring_activity", recurring, recurring_known),
        ("not_newly_detected", not_new, not_new_known),
        ("low_anomaly", low_anomaly, anomaly_known),
        ("low_risk", low_risk, risk_known),
    ]
    matched = recurring and not_new and low_anomaly and low_risk

    reasons = []
    if recurring:
        reasons.append("Activity pattern is historically recurring")
    if low_anomaly and anomaly_known:
        reasons.append("Historical thermal pattern is within expected bounds")
    if low_risk and risk_known:
        reasons.append("Thermal risk is not elevated")

    return {"matched": matched, "conditions": conditions,
            "reasons": reasons, "consistency": 1.0}

def classify_thermal_event(
    frp=None,
    confidence=None,
    risk_score=None,
    risk_level=None,
    historical_avg_frp=None,
    historical_max_frp=None,
    historical_detection_count=None,
    is_recurring=None,
    is_new_event=None,
    anomaly_score=None,
    anomaly_level=None,
    nearest_facility_type=None,
    nearest_facility_distance_m=None,
    industrial_proximity_score=None,
    near_critical_infrastructure=None,
    config=None,
) -> dict:
    """Classify a thermal event using the documented rule precedence.

    All inputs are optional; missing, None, invalid, or out-of-range values are
    handled with safe normalization (see ``_clean_signals``). This function
    never raises for bad data and has no FastAPI/Pydantic dependency.

    Returns::

        {
            "event_type": str,                    # one of EVENT_TYPES
            "classification_confidence": float,   # 0..100
            "classification_reasons": [str, ...],
            "matched_signals": {...},
            "classification_score_breakdown": {...},
            "disclaimer": str,
        }
    """
    cfg = config if config is not None else ClassificationConfig()

    signals = _clean_signals(
        frp=frp,
        confidence=confidence,
        risk_score=risk_score,
        risk_level=risk_level,
        historical_avg_frp=historical_avg_frp,
        historical_max_frp=historical_max_frp,
        historical_detection_count=historical_detection_count,
        is_recurring=is_recurring,
        is_new_event=is_new_event,
        anomaly_score=anomaly_score,
        anomaly_level=anomaly_level,
        nearest_facility_type=nearest_facility_type,
        nearest_facility_distance_m=nearest_facility_distance_m,
        industrial_proximity_score=industrial_proximity_score,
        near_critical_infrastructure=near_critical_infrastructure,
    )

    groups = _signal_groups(signals)
    availability_ratio = round(sum(groups.values()) / len(groups), 4)
    present_groups = [name for name, present in groups.items() if present]
    missing_groups = [name for name, present in groups.items() if not present]

    rules = (
        ("HIGH_PRIORITY_INCIDENT", _rule_high_priority),
        ("INDUSTRIAL_THERMAL_ACTIVITY", _rule_industrial),
        ("UNUSUAL_THERMAL_EVENT", _rule_unusual),
        ("NORMAL_RECURRING_ACTIVITY", _rule_normal),
    )

    winner_type = None
    winner = None
    for event_type, rule_fn in rules:
        evaluated = rule_fn(signals, cfg)
        if evaluated["matched"]:
            winner_type, winner = event_type, evaluated
            break

    if winner is None:
        winner_type = "UNKNOWN"
        winner = {
            "matched": False,
            "conditions": [],
            "reasons": [
                "Insufficient thermal information for confident classification",
                "No primary classification rule matched with the available signals",
            ],
            "consistency": 1.0,
        }

    strength_ratio, met_count, considered_count = _strength(winner["conditions"])

    if winner_type == "UNKNOWN":
        confidence = round(cfg.UNKNOWN_CONFIDENCE_MAX * availability_ratio, 2)
    else:
        raw = (
            cfg.STRENGTH_WEIGHT * strength_ratio
            + cfg.AVAILABILITY_WEIGHT * availability_ratio
        ) * winner["consistency"] * 100.0
        confidence = round(max(0.0, min(100.0, raw)), 2)

    return _build_output(
        winner_type=winner_type,
        winner=winner,
        signals=signals,
        strength_ratio=strength_ratio,
        met_count=met_count,
        considered_count=considered_count,
        availability_ratio=availability_ratio,
        present_groups=present_groups,
        missing_groups=missing_groups,
        confidence=confidence,
        cfg=cfg,
    )

def _build_output(
    *,
    winner_type: str,
    winner: dict,
    signals: dict,
    strength_ratio: float,
    met_count: int,
    considered_count: int,
    availability_ratio: float,
    present_groups: list,
    missing_groups: list,
    confidence: float,
    cfg: ClassificationConfig,
) -> dict:
    """Assemble the structured, explainable classification output."""
    reasons = list(winner["reasons"])

    if signals["frp"] is not None and signals["frp"] >= cfg.HIGH_FRP_MIN:
        reasons.append("Elevated radiative power (FRP) signal recorded")
    if (
        signals["confidence"] is not None
        and signals["confidence"] >= cfg.HIGH_CONFIDENCE_MIN
    ):
        reasons.append("High detection confidence recorded")

    for group in missing_groups:
        if group == "risk":
            reasons.append(
                "Risk signals unavailable - classification uses remaining available signals"
            )
        elif group == "history":
            reasons.append(
                "Historical signals unavailable - "
                "classification uses current thermal signals only"
            )
        elif group == "anomaly":
            reasons.append(
                "Anomaly signals unavailable - "
                "classification uses available risk/proximity signals"
            )
        elif group == "geospatial":
            reasons.append(
                "Geospatial signals unavailable - "
                "classification uses thermal signals only"
            )

    used_signals = [condition[0] for condition in winner["conditions"] if condition[1]]

    all_signal_names = (
        "frp",
        "confidence",
        "risk_score",
        "risk_level",
        "historical_avg_frp",
        "historical_max_frp",
        "historical_detection_count",
        "is_recurring",
        "is_new_event",
        "anomaly_score",
        "anomaly_level",
        "nearest_facility_type",
        "nearest_facility_distance_m",
        "industrial_proximity_score",
        "near_critical_infrastructure",
    )

    matched_signals = {
        "thermal": {"frp": signals["frp"], "confidence": signals["confidence"]},
        "risk": {
            "risk_score": signals["risk_score"],
            "risk_level": signals["risk_level"],
        },
        "history": {
            "historical_avg_frp": signals["historical_avg_frp"],
            "historical_max_frp": signals["historical_max_frp"],
            "historical_detection_count": signals["historical_detection_count"],
            "is_recurring": signals["is_recurring"],
            "is_new_event": signals["is_new_event"],
        },
        "anomaly": {
            "anomaly_score": signals["anomaly_score"],
            "anomaly_level": signals["anomaly_level"],
        },
        "geospatial": {
            "nearest_facility_type": signals["nearest_facility_type"],
            "nearest_facility_distance_m": signals["nearest_facility_distance_m"],
            "industrial_proximity_score": signals["industrial_proximity_score"],
            "near_critical_infrastructure": signals["near_critical_infrastructure"],
        },
        "present_signals": [
            name for name in all_signal_names if signals[name] is not None
        ],
        "missing_signals": [
            name for name in all_signal_names if signals[name] is None
        ],
        "used_signals": used_signals,
    }

    breakdown = {
        "winning_rule": winner_type,
        "precedence_order": list(PRECEDENCE_ORDER),
        "availability_ratio": availability_ratio,
        "present_signal_groups": present_groups,
        "missing_signal_groups": missing_groups,
        "rule_strength": strength_ratio,
        "matched_conditions": met_count,
        "considered_conditions": considered_count,
        "consistency_factor": winner["consistency"],
        "normalization_warnings": signals["warnings"],
    }

    return {
        "event_type": winner_type,
        "classification_confidence": confidence,
        "classification_reasons": reasons,
        "matched_signals": matched_signals,
        "classification_score_breakdown": breakdown,
        "disclaimer": (
            "Decision-support category derived from thermal signals only; "
            "it does not confirm a fire, explosion, industrial accident, or emergency."
        ),
    }


_CLASSIFY_PARAMETERS = (
    "frp", "confidence", "risk_score", "risk_level",
    "historical_avg_frp", "historical_max_frp", "historical_detection_count",
    "is_recurring", "is_new_event", "anomaly_score", "anomaly_level",
    "nearest_facility_type", "nearest_facility_distance_m",
    "industrial_proximity_score", "near_critical_infrastructure",
)


def classify_thermal_event_from_signals(signals=None, config=None) -> dict:
    """Dict-based convenience wrapper.

    Accepts any dict (for example an analyzed hotspot dict merged with
    ``proximity_service.analyze_infrastructure_proximity`` output) and forwards
    only the known signal parameters. Extra keys are ignored safely.
    """
    if signals is None:
        signals = {}
    kwargs = {name: signals.get(name) for name in _CLASSIFY_PARAMETERS}
    return classify_thermal_event(config=config, **kwargs)
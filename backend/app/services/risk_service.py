from typing import Literal

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class RiskThresholds:
    FRP_MAX = 200.0
    CONFIDENCE_MAX = 1.0

    LOW_MAX = 25
    MEDIUM_MAX = 50
    HIGH_MAX = 75


def calculate_risk_score(frp: float, confidence: float) -> float:
    frp_normalized = min(frp / RiskThresholds.FRP_MAX, 1.0)
    confidence_normalized = min(max(confidence, 0.0), 1.0)

    score = (frp_normalized * 0.7 + confidence_normalized * 0.3) * 100
    return round(max(0.0, min(100.0, score)), 2)


def classify_risk(frp: float, confidence: float) -> tuple[RiskLevel, float]:
    if frp is None or confidence is None:
        return "LOW", 0.0

    frp = max(0.0, float(frp))
    confidence = max(0.0, min(1.0, float(confidence)))

    risk_score = calculate_risk_score(frp, confidence)

    if risk_score <= RiskThresholds.LOW_MAX:
        risk_level: RiskLevel = "LOW"
    elif risk_score <= RiskThresholds.MEDIUM_MAX:
        risk_level = "MEDIUM"
    elif risk_score <= RiskThresholds.HIGH_MAX:
        risk_level = "HIGH"
    else:
        risk_level = "CRITICAL"

    return risk_level, risk_score
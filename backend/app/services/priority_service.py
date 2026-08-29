from typing import Literal, Optional

PriorityLevel = Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]


class PriorityThresholds:
    RISK_WEIGHT = 0.50
    ANOMALY_WEIGHT = 0.30
    NEW_EVENT_BONUS = 15.0
    RECURRING_PENALTY = -5.0
    INDUSTRIAL_PROXIMITY_WEIGHT = 0.10
    CRITICAL_INFRA_BONUS = 10.0

    LOW_MAX = 24
    MODERATE_MAX = 49
    HIGH_MAX = 74


def calculate_priority_score(
    risk_score: float,
    anomaly_score: float,
    is_new_event: bool,
    is_recurring: bool,
    industrial_proximity_score: Optional[float] = None,
    near_critical_infrastructure: Optional[bool] = None,
) -> float:
    score = 0.0

    score += risk_score * PriorityThresholds.RISK_WEIGHT
    score += anomaly_score * PriorityThresholds.ANOMALY_WEIGHT

    if is_new_event:
        score += PriorityThresholds.NEW_EVENT_BONUS

    if is_recurring:
        score += PriorityThresholds.RECURRING_PENALTY

    if industrial_proximity_score is not None:
        industrial_proximity_score = max(0.0, min(100.0, industrial_proximity_score))
        score += industrial_proximity_score * PriorityThresholds.INDUSTRIAL_PROXIMITY_WEIGHT

    if near_critical_infrastructure:
        score += PriorityThresholds.CRITICAL_INFRA_BONUS

    score = max(0.0, min(100.0, score))
    return round(score, 2)


def classify_priority(priority_score: float) -> PriorityLevel:
    if priority_score <= PriorityThresholds.LOW_MAX:
        return "LOW"
    elif priority_score <= PriorityThresholds.MODERATE_MAX:
        return "MODERATE"
    elif priority_score <= PriorityThresholds.HIGH_MAX:
        return "HIGH"
    else:
        return "CRITICAL"


def generate_priority_factors(
    risk_score: float,
    anomaly_score: float,
    is_new_event: bool,
    is_recurring: bool,
    industrial_proximity_score: Optional[float] = None,
    near_critical_infrastructure: Optional[bool] = None,
) -> list[str]:
    factors = []

    if risk_score >= 75:
        factors.append("Very high thermal risk")
    elif risk_score >= 50:
        factors.append("High thermal risk")
    elif risk_score >= 25:
        factors.append("Moderate thermal risk")
    else:
        factors.append("Low thermal risk")

    if anomaly_score >= 70:
        factors.append("Highly unusual historical pattern")
    elif anomaly_score >= 30:
        factors.append("Unusual historical pattern")
    else:
        factors.append("Normal historical pattern")

    if is_new_event:
        factors.append("New thermal event")
    if is_recurring:
        factors.append("Recurring thermal event")

    if industrial_proximity_score is not None and industrial_proximity_score > 50:
        factors.append("Near industrial zone")

    if near_critical_infrastructure:
        factors.append("Near critical infrastructure")

    return factors


def analyze_priority(
    risk_score: float,
    anomaly_score: float,
    is_new_event: bool,
    is_recurring: bool,
    industrial_proximity_score: Optional[float] = None,
    near_critical_infrastructure: Optional[bool] = None,
) -> tuple[float, PriorityLevel, list[str]]:
    priority_score = calculate_priority_score(
        risk_score=risk_score,
        anomaly_score=anomaly_score,
        is_new_event=is_new_event,
        is_recurring=is_recurring,
        industrial_proximity_score=industrial_proximity_score,
        near_critical_infrastructure=near_critical_infrastructure,
    )

    priority_level = classify_priority(priority_score)
    priority_factors = generate_priority_factors(
        risk_score=risk_score,
        anomaly_score=anomaly_score,
        is_new_event=is_new_event,
        is_recurring=is_recurring,
        industrial_proximity_score=industrial_proximity_score,
        near_critical_infrastructure=near_critical_infrastructure,
    )

    return priority_score, priority_level, priority_factors
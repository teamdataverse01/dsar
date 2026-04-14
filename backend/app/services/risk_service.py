from app.models.dsar_request import (
    DSARRequest, RequestType, DataSensitivity, SubjectPersona, RiskTier
)

# ── Scoring weights ────────────────────────────────────────────────────────────
_REQUEST_TYPE_SCORE = {
    RequestType.ACCESS: 1,
    RequestType.MODIFICATION: 2,
    RequestType.STOP_PROCESSING: 2,
    RequestType.DELETION: 3,
}

_SENSITIVITY_SCORE = {
    DataSensitivity.PUBLIC: 0,
    DataSensitivity.INTERNAL: 1,
    DataSensitivity.CONFIDENTIAL: 2,
    DataSensitivity.REGULATED: 4,
}

_PERSONA_SCORE = {
    SubjectPersona.GENERAL_PUBLIC: 0,
    SubjectPersona.EMPLOYEE: 1,
    SubjectPersona.VULNERABLE_ADULT: 3,
    SubjectPersona.MINOR: 3,
    SubjectPersona.SUBJECT_OF_INVESTIGATION: 4,
}

_CONTEXT_KEYWORDS = {
    "legal_hold": 3,
    "active_investigation": 4,
    "regulatory_inquiry": 3,
    "court_order": 4,
    "none": 0,
}

# ── Tier thresholds ────────────────────────────────────────────────────────────
def _score_to_tier(score: int) -> RiskTier:
    if score <= 2:
        return RiskTier.LOW
    elif score <= 5:
        return RiskTier.MEDIUM
    elif score <= 8:
        return RiskTier.HIGH
    else:
        return RiskTier.CRITICAL


def assess_risk(request: DSARRequest) -> tuple[RiskTier, str | None]:
    """
    Calculate risk tier for a request.
    Returns (tier, escalation_reason | None).
    """
    score = 0
    score += _REQUEST_TYPE_SCORE.get(request.request_type, 1)
    score += _SENSITIVITY_SCORE.get(request.data_sensitivity, 1)
    score += _PERSONA_SCORE.get(request.subject_persona, 0)
    score += _CONTEXT_KEYWORDS.get(request.special_context or "none", 0)

    tier = _score_to_tier(score)

    escalation_reason = None
    if tier in (RiskTier.HIGH, RiskTier.CRITICAL):
        parts = []
        if request.data_sensitivity == DataSensitivity.REGULATED:
            parts.append("regulated data involved")
        if request.subject_persona in (SubjectPersona.MINOR, SubjectPersona.VULNERABLE_ADULT):
            parts.append("vulnerable subject persona")
        if request.subject_persona == SubjectPersona.SUBJECT_OF_INVESTIGATION:
            parts.append("subject is under investigation")
        if request.special_context in ("legal_hold", "active_investigation",
                                        "regulatory_inquiry", "court_order"):
            parts.append(f"context: {request.special_context}")
        escalation_reason = "; ".join(parts) if parts else "high risk score"

    return tier, escalation_reason

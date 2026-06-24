"""
OneGuard AI - Decision Engine
------------------------------
Transparent, rule-based scoring used to DEMONSTRATE the AI decisioning concept.

In production, every weight and threshold below would be replaced by a model
trained and calibrated on historical VKYC outcomes, chargebacks, manual-review
tags, false-decline labels and spend-quality metrics. The structure (signals ->
weighted score -> confidence band -> reason codes -> recommended action) is
identical to how a production risk model would be served.

All functions are pure (no Streamlit imports) so the logic stays testable.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict


# --------------------------------------------------------------------------- #
#  Shared data structures
# --------------------------------------------------------------------------- #
@dataclass
class Decision:
    score: int
    level: str                       # Low / Medium / High / Critical
    action: str
    action_kind: str                 # approve / monitor / stepup / review / decline
    reason_codes: List[Tuple[str, str]] = field(default_factory=list)  # (code, text)
    confidence: int = 0              # 0-100, model-confidence proxy
    contributions: List[Tuple[str, int]] = field(default_factory=list) # (signal, pts)
    false_decline_warning: bool = False


# --------------------------------------------------------------------------- #
#  Weight tables (shown verbatim in the Assumptions tab)
# --------------------------------------------------------------------------- #
VKYC_WEIGHTS = {
    "face_match":   {"<60%": 25, "60-70%": 12, ">=70%": 0},
    "liveness":     {"<60%": 25, "60-70%": 12, ">=70%": 0},
    "doc_tamper":   {"High": 20, "Medium": 10, "Low": 0},
    "device_risk":  {"High": 15, "Medium": 8,  "Low": 0},
    "geo_mismatch": {"Yes": 10, "No": 0},
    "agent_conf":   {"Low": 12, "Medium": 6, "High": 0},
    "video_quality":{"Poor": 10, "Average": 5, "Good": 0},
}

TXN_WEIGHTS = {
    "amount_dev":   {">6x avg": 30, ">3x avg": 18, "<=3x avg": 0},
    "merchant_cat": {"High-risk category": 15, "Normal category": 0},
    "merchant_risk":{"High": 15, "Medium": 8, "Low": 0},
    "device_change":{"Yes": 12, "No": 0},
    "location":     {"Mismatch": 12, "Match": 0},
    "velocity":     {">6 / hr": 20, ">3 / hr": 10, "<=3 / hr": 0},
    "late_night":   {"00:00-05:00": 10, "Daytime": 0},
}

HIGH_RISK_MCC = {"Crypto exchange", "Online gambling", "Gift cards",
                 "Wire / forex transfer", "Luxury / jewellery"}

# Action thresholds -------------------------------------------------------- #
VKYC_BANDS = [
    (0, 30,  "Approve",                  "approve", "Low"),
    (31, 60, "Step-up verification",     "stepup",  "Medium"),
    (61, 80, "Manual review",            "review",  "High"),
    (81, 100,"Reject / senior fraud review","decline","Critical"),
]
TXN_BANDS = [
    (0, 30,  "Approve",                  "approve", "Low"),
    (31, 60, "Approve with monitoring",  "monitor", "Medium"),
    (61, 80, "Step-up authentication",   "stepup",  "High"),
    (81, 100,"Decline / fraud review",   "decline", "Critical"),
]


def _band(score: int, bands):
    for lo, hi, action, kind, level in bands:
        if lo <= score <= hi:
            return action, kind, level
    return bands[-1][2], bands[-1][3], bands[-1][4]


def _confidence(contributions: List[Tuple[str, int]], score: int) -> int:
    """Confidence proxy: high when signals agree (few but strong, or many),
    lower when the score sits near a band boundary (the ambiguous zone)."""
    active = [p for _, p in contributions if p > 0]
    agreement = min(100, 55 + 9 * len(active)) if active else 90  # clean = confident
    # penalise scores near 30/60/80 boundaries (decision is borderline)
    nearest = min(abs(score - b) for b in (30, 60, 80))
    boundary_pen = max(0, 12 - nearest * 2)
    return int(max(40, min(99, agreement - boundary_pen)))


# --------------------------------------------------------------------------- #
#  1. VKYC Shield
# --------------------------------------------------------------------------- #
def score_vkyc(face_match: float, liveness: float, doc_tamper: str,
               device_risk: str, geo_mismatch: bool, agent_conf: str,
               video_quality: str) -> Decision:
    contribs: List[Tuple[str, int]] = []
    reasons: List[Tuple[str, str]] = []

    # Face match
    if face_match < 60:
        contribs.append(("Face match < 60%", 25))
        reasons.append(("FACE_MATCH_CRITICAL", f"Face match {face_match:.0f}% is far below the 70% trust floor."))
    elif face_match < 70:
        contribs.append(("Face match 60-70%", 12))
        reasons.append(("FACE_MATCH_LOW", f"Face match {face_match:.0f}% sits below the 70% trust floor."))

    # Liveness
    if liveness < 60:
        contribs.append(("Liveness < 60%", 25))
        reasons.append(("LIVENESS_CRITICAL", f"Liveness {liveness:.0f}% suggests possible spoof / deepfake."))
    elif liveness < 70:
        contribs.append(("Liveness 60-70%", 12))
        reasons.append(("LIVENESS_WEAK", f"Liveness {liveness:.0f}% is weak; presentation-attack risk."))

    # Document tamper
    if doc_tamper in ("Medium", "High"):
        pts = VKYC_WEIGHTS["doc_tamper"][doc_tamper]
        contribs.append((f"Doc tamper risk: {doc_tamper}", pts))
        reasons.append(("DOC_TAMPER_SUSPECTED", f"{doc_tamper} document-tampering signal detected."))

    # Device risk
    if device_risk in ("Medium", "High"):
        pts = VKYC_WEIGHTS["device_risk"][device_risk]
        contribs.append((f"Device risk: {device_risk}", pts))
        reasons.append(("DEVICE_RISK", f"{device_risk}-risk device fingerprint (emulator / known-bad / VPN)."))

    # Geo mismatch
    if geo_mismatch:
        contribs.append(("Geo mismatch", 10))
        reasons.append(("GEO_MISMATCH", "Stated address and live geo-location disagree."))

    # Agent confidence
    if agent_conf in ("Low", "Medium"):
        pts = VKYC_WEIGHTS["agent_conf"][agent_conf]
        contribs.append((f"Agent confidence: {agent_conf}", pts))
        reasons.append(("AGENT_LOW_CONFIDENCE", f"VKYC agent flagged {agent_conf.lower()} confidence."))

    # Video quality
    if video_quality in ("Poor", "Average"):
        pts = VKYC_WEIGHTS["video_quality"][video_quality]
        contribs.append((f"Video quality: {video_quality}", pts))
        reasons.append(("VIDEO_QUALITY_LOW", f"{video_quality} video quality limits CV verification reliability."))

    score = min(100, sum(p for _, p in contribs))
    action, kind, level = _band(score, VKYC_BANDS)

    if not reasons:
        reasons.append(("CLEAN_PROFILE", "All onboarding signals within trusted bands."))

    return Decision(
        score=score, level=level, action=action, action_kind=kind,
        reason_codes=reasons, contributions=contribs,
        confidence=_confidence(contribs, score),
    )


# --------------------------------------------------------------------------- #
#  2. Transaction Sentinel
# --------------------------------------------------------------------------- #
def score_transaction(amount: float, avg_amount: float, merchant_cat: str,
                      merchant_risk: str, device_changed: bool,
                      location_mismatch: bool, txns_last_hour: int,
                      txn_hour: int) -> Decision:
    contribs: List[Tuple[str, int]] = []
    reasons: List[Tuple[str, str]] = []
    avg = max(avg_amount, 1.0)
    ratio = amount / avg

    # Amount deviation
    if ratio > 6:
        contribs.append((f"Amount {ratio:.1f}x avg (>6x)", 30))
        reasons.append(("AMOUNT_ANOMALY_SEVERE", f"Amount is {ratio:.1f}x the customer's average spend."))
    elif ratio > 3:
        contribs.append((f"Amount {ratio:.1f}x avg (>3x)", 18))
        reasons.append(("AMOUNT_ANOMALY", f"Amount is {ratio:.1f}x the customer's average spend."))

    # Merchant category
    if merchant_cat in HIGH_RISK_MCC:
        contribs.append((f"High-risk MCC: {merchant_cat}", 15))
        reasons.append(("MERCHANT_CATEGORY_RISK", f"'{merchant_cat}' is a high-risk merchant category."))

    # Merchant risk score
    if merchant_risk in ("Medium", "High"):
        pts = TXN_WEIGHTS["merchant_risk"][merchant_risk]
        contribs.append((f"Merchant risk: {merchant_risk}", pts))
        reasons.append(("MERCHANT_RISK", f"Merchant carries a {merchant_risk.lower()} historical risk score."))

    # Device change
    if device_changed:
        contribs.append(("New / changed device", 12))
        reasons.append(("NEW_DEVICE", "Transaction from a device not previously seen for this user."))

    # Location mismatch
    if location_mismatch:
        contribs.append(("Location mismatch", 12))
        reasons.append(("GEO_MISMATCH", "Transaction geo differs from the customer's usual footprint."))

    # Velocity
    if txns_last_hour > 6:
        contribs.append((f"{txns_last_hour} txns / hr (>6)", 20))
        reasons.append(("VELOCITY_SPIKE_SEVERE", f"{txns_last_hour} transactions in the last hour."))
    elif txns_last_hour > 3:
        contribs.append((f"{txns_last_hour} txns / hr (>3)", 10))
        reasons.append(("VELOCITY_SPIKE", f"{txns_last_hour} transactions in the last hour."))

    # Late night
    if 0 <= txn_hour <= 5:
        contribs.append(("Late-night (00:00-05:00)", 10))
        reasons.append(("LATE_NIGHT_TXN", f"Transaction at {txn_hour:02d}:00, outside usual active hours."))

    score = min(100, sum(p for _, p in contribs))
    action, kind, level = _band(score, TXN_BANDS)

    # ---- False-decline guard (the core business insight) ----------------- #
    # If the model would decline/step-up but the strongest "genuine" signals
    # are intact (same device, same location), the risk is likely driven by a
    # legitimately large or fast purchase. Recommend step-up over hard decline.
    genuine_signals = (not device_changed) and (not location_mismatch)
    if kind in ("decline", "stepup") and genuine_signals:
        fd_warning = True
        reasons.append(("FALSE_DECLINE_GUARD",
                        "Trusted device + location intact: prefer step-up authentication over a hard decline to preserve a likely-genuine spend."))
        if kind == "decline":
            action, kind, level = "Step-up authentication (false-decline guard)", "stepup", "High"
    else:
        fd_warning = False

    if not contribs:
        reasons.append(("CLEAN_TXN", "All transaction signals within normal behaviour."))

    return Decision(
        score=score, level=level, action=action, action_kind=kind,
        reason_codes=reasons, contributions=contribs,
        confidence=_confidence(contribs, score),
        false_decline_warning=fd_warning,
    )


# --------------------------------------------------------------------------- #
#  3. Growth Copilot
# --------------------------------------------------------------------------- #
def recommend_growth(segment: str, spend_trend: str, click_rate: float,
                     preferred_category: str, risk_level: str) -> Dict:
    # Risk gating first: never push aggressive credit/limit offers to risky users
    risky = risk_level in ("High", "Critical")

    # Message theme by spend trend
    theme_map = {
        "Declining":  "Win-back & reactivation",
        "Dormant":    "We-miss-you reactivation",
        "Stable":     "Category-bonus nudge",
        "Growing":    "Rewards acceleration",
    }
    theme = theme_map.get(spend_trend, "Category-bonus nudge")

    # Offer by segment + trend, gated by risk
    if risky:
        offer = f"Trust-first: security tips + low-value {preferred_category} cashback (no limit increase)"
    elif segment == "Premium" and spend_trend in ("Growing", "Stable"):
        offer = f"Accelerated rewards on {preferred_category} + travel/lounge perk"
    elif segment == "New-to-card":
        offer = f"Activation bonus on first {preferred_category} spend"
    elif spend_trend in ("Declining", "Dormant"):
        offer = f"Bonus cashback to re-activate {preferred_category} spends"
    else:
        offer = f"Tiered cashback on {preferred_category}"

    # Channel by click-rate
    if click_rate >= 6:
        channel = "In-app + push (high engagement)"
    elif click_rate >= 3:
        channel = "Push + email"
    else:
        channel = "Email + SMS (re-engagement)"

    # Expected uplift (directional, illustrative only)
    base_ctr = {"Growing": 4.0, "Stable": 3.0, "Declining": 2.0, "Dormant": 1.5}.get(spend_trend, 2.5)
    seg_mult = {"Premium": 1.3, "Mass-affluent": 1.15, "Mass": 1.0, "New-to-card": 1.1}.get(segment, 1.0)
    ctr_uplift = round(base_ctr * seg_mult * (0.6 if risky else 1.0), 1)
    spend_uplift = round(ctr_uplift * 1.8 * (0.7 if risky else 1.0), 1)

    return {
        "theme": theme,
        "offer": offer,
        "channel": channel,
        "ctr_uplift": ctr_uplift,
        "spend_uplift": spend_uplift,
        "risk_gated": risky,
    }

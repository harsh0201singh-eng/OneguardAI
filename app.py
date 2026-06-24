"""
OneGuard AI - Dashboard (Streamlit prototype)
Explainable AI copilot for safer digital credit card journeys.

A HYPOTHETICAL fintech product inspired by digital credit card journeys.
Not an official product of any issuer. Built for the Abakus AI Catalyst task.

Run locally:   streamlit run app.py
Deploy:        push to GitHub -> share.streamlit.io -> point at app.py
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from engine import (
    score_vkyc, score_transaction, recommend_growth,
    VKYC_WEIGHTS, TXN_WEIGHTS, HIGH_RISK_MCC,
    VKYC_BANDS, TXN_BANDS,
)

# --------------------------------------------------------------------------- #
#  Page config + theme
# --------------------------------------------------------------------------- #
st.set_page_config(page_title="OneGuard AI", page_icon="🛡️",
                   layout="wide", initial_sidebar_state="expanded")

NAVY = "#0B1437"
NAVY2 = "#111C44"
TEAL = "#00A896"
MINT = "#02C39A"
AMBER = "#F6A609"
RED = "#E5484D"
INK = "#0B1437"

st.markdown(f"""
<style>
  .stApp {{ background: linear-gradient(160deg,{NAVY} 0%, #0E1A3F 100%); }}
  section[data-testid="stSidebar"] {{ background:{NAVY2}; }}
  h1,h2,h3,h4,p,label,span,div {{ color:#E8ECF8; }}
  .block-container {{ padding-top:2rem; max-width:1250px; }}
  .og-card {{
      background:{NAVY2}; border:1px solid rgba(255,255,255,.06);
      border-radius:16px; padding:18px 20px; margin-bottom:14px;
  }}
  .og-kpi {{ font-size:34px; font-weight:800; color:{MINT}; line-height:1; }}
  .og-kpi-l {{ font-size:13px; color:#9AA7C7; }}
  .og-pill {{
      display:inline-block; padding:4px 12px; border-radius:999px;
      font-size:12px; font-weight:600; margin:3px 6px 3px 0;
      background:rgba(0,168,150,.14); color:{MINT}; border:1px solid rgba(0,168,150,.35);
  }}
  .og-tag {{ font-family:monospace; font-size:12px; font-weight:700; color:{TEAL}; }}
  .badge {{ padding:8px 18px; border-radius:12px; font-weight:800; font-size:18px; display:inline-block; }}
  .stTabs [data-baseweb="tab-list"] {{ gap:4px; }}
  .stTabs [data-baseweb="tab"] {{
      background:{NAVY2}; border-radius:10px 10px 0 0; padding:8px 16px; color:#9AA7C7;
  }}
  .stTabs [aria-selected="true"] {{ background:{TEAL}; color:white; }}
  div[data-testid="stMetricValue"] {{ color:{MINT}; }}
</style>
""", unsafe_allow_html=True)

ACTION_COLORS = {
    "approve": MINT, "monitor": TEAL, "stepup": AMBER,
    "review": AMBER, "decline": RED,
}


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #
def gauge(score, title="Risk score"):
    color = MINT if score <= 30 else TEAL if score <= 60 else AMBER if score <= 80 else RED
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score,
        number={"font": {"size": 44, "color": "#E8ECF8"}},
        title={"text": title, "font": {"size": 14, "color": "#9AA7C7"}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#9AA7C7"},
            "bar": {"color": color, "thickness": 0.28},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 30], "color": "rgba(2,195,154,.18)"},
                {"range": [30, 60], "color": "rgba(0,168,150,.18)"},
                {"range": [60, 80], "color": "rgba(246,166,9,.20)"},
                {"range": [80, 100], "color": "rgba(229,72,77,.22)"},
            ],
        },
    ))
    fig.update_layout(height=240, margin=dict(l=20, r=20, t=40, b=10),
                      paper_bgcolor="rgba(0,0,0,0)")
    return fig


def action_badge(decision):
    c = ACTION_COLORS.get(decision.action_kind, TEAL)
    st.markdown(
        f'<div class="badge" style="background:{c};color:#06121f;">{decision.action}</div>',
        unsafe_allow_html=True)


def render_reasons(decision):
    st.markdown("**Explainability — AI reason codes**")
    for code, text in decision.reason_codes:
        st.markdown(
            f'<div style="margin:6px 0;"><span class="og-tag">{code}</span> '
            f'<span style="color:#C7D0EA;">— {text}</span></div>',
            unsafe_allow_html=True)


def render_contributions(decision):
    if not decision.contributions:
        return
    df = (pd.DataFrame(decision.contributions, columns=["Signal", "Risk points"])
          .sort_values("Risk points", ascending=True))
    fig = go.Figure(go.Bar(
        x=df["Risk points"], y=df["Signal"], orientation="h",
        marker_color=TEAL, text=df["Risk points"], textposition="outside"))
    fig.update_layout(height=max(180, 38 * len(df)), margin=dict(l=10, r=20, t=10, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#C7D0EA"),
                      xaxis=dict(title="Risk points", gridcolor="rgba(255,255,255,.07)"))
    st.markdown("**Score breakdown — what drove the decision**")
    st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------------------------------- #
#  Sidebar
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.markdown(f"<h2 style='color:{MINT};margin-bottom:0;'>🛡️ OneGuard AI</h2>",
                unsafe_allow_html=True)
    st.caption("Explainable AI copilot for safer digital credit card journeys")
    st.markdown("---")
    st.markdown("**Modules**")
    st.markdown("• VKYC Shield — onboarding risk\n\n"
                "• Transaction Sentinel — live txn risk\n\n"
                "• Growth Copilot — risk-aware comms")
    st.markdown("---")
    st.info("Hypothetical fintech product inspired by digital credit card "
            "journeys. Demo uses synthetic inputs and transparent rule-based "
            "scoring. In production, weights are model-trained and calibrated.",
            icon="ℹ️")


st.markdown(f"<h1 style='margin-bottom:2px;'>OneGuard AI <span style='color:{MINT};'>Dashboard</span></h1>",
            unsafe_allow_html=True)
st.markdown("<p style='color:#9AA7C7;margin-top:0;'>Stop fraud without blocking "
            "genuine customers — one explainable decision layer across the journey.</p>",
            unsafe_allow_html=True)

tabs = st.tabs(["📊 Overview", "🛡️ VKYC Shield", "🔎 Transaction Sentinel",
                "🚀 Growth Copilot", "📐 Assumptions"])

# --------------------------------------------------------------------------- #
#  TAB 1 — Overview
# --------------------------------------------------------------------------- #
with tabs[0]:
    st.subheader("The dual problem")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="og-card"><b>1 · Onboarding fraud (VKYC)</b><br>'
                    '<span style="color:#C7D0EA;">Edited documents, fake liveness, deepfake '
                    'video, borrowed and synthetic identities can slip past manual reviewers '
                    'and basic computer-vision checks.</span></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="og-card"><b>2 · False transaction declines</b><br>'
                    '<span style="color:#C7D0EA;">Rigid rule engines decline genuine spends that '
                    '<i>look</i> suspicious — hurting experience, losing good-quality spends and '
                    'flooding fraud queues.</span></div>', unsafe_allow_html=True)

    st.subheader("The OneGuard decision layer")
    f1, f2, f3, f4 = st.columns(4)
    for col, (h, b) in zip([f1, f2, f3, f4], [
        ("Inputs", "VKYC signals · transaction data · customer segment"),
        ("Risk Engine", "Weighted scoring · confidence bands · reason codes"),
        ("Decision", "Approve · step-up · manual review · decline"),
        ("Feedback Loop", "Fraud tags · chargebacks · false-decline labels"),
    ]):
        col.markdown(f'<div class="og-card" style="min-height:130px;"><b style="color:{MINT};">'
                     f'{h}</b><br><span style="color:#C7D0EA;font-size:14px;">{b}</span></div>',
                     unsafe_allow_html=True)

    st.subheader("Expected pilot KPIs")
    k = st.columns(5)
    kpis = [("40-60%", "less VKYC review time"), ("15-25%", "better fraud detection"),
            ("20-35%", "fewer false declines"), ("5-10%", "uplift in good spends"),
            ("30-50%", "less investigation load")]
    for col, (v, l) in zip(k, kpis):
        col.markdown(f'<div class="og-card" style="text-align:center;"><div class="og-kpi">{v}</div>'
                     f'<div class="og-kpi-l">{l}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="og-card" style="text-align:center;border-color:{TEAL};">'
                f'<b style="color:{MINT};font-size:18px;">Business Value = Fraud Loss Prevented '
                f'+ Good Spends Saved + Manual Effort Reduced</b></div>', unsafe_allow_html=True)
    st.caption("KPIs are directional pilot-level assumptions for evaluation, "
               "to be validated against historical outcomes — not guaranteed numbers.")

# --------------------------------------------------------------------------- #
#  TAB 2 — VKYC Shield
# --------------------------------------------------------------------------- #
with tabs[1]:
    st.subheader("🛡️ VKYC Shield — onboarding risk decisioning")
    left, right = st.columns([1, 1.2])
    with left:
        st.markdown("**Onboarding signals**")
        face = st.slider("Face match score (%)", 0, 100, 88)
        live = st.slider("Liveness score (%)", 0, 100, 90)
        doc = st.select_slider("Document tamper risk", ["Low", "Medium", "High"], "Low")
        dev = st.select_slider("Device risk", ["Low", "Medium", "High"], "Low")
        geo = st.toggle("Geo-location mismatch", value=False)
        agent = st.select_slider("Agent confidence", ["Low", "Medium", "High"], "High")
        vq = st.select_slider("Video quality", ["Poor", "Average", "Good"], "Good")
        ex = st.radio("Quick demo profiles", ["—", "Clean applicant", "Synthetic-ID fraud"],
                      horizontal=True)
        if ex == "Clean applicant":
            face, live, doc, dev, geo, agent, vq = 94, 95, "Low", "Low", False, "High", "Good"
            st.caption("Loaded: clean applicant")
        elif ex == "Synthetic-ID fraud":
            face, live, doc, dev, geo, agent, vq = 52, 48, "High", "High", True, "Low", "Poor"
            st.caption("Loaded: synthetic-ID fraud")

    d = score_vkyc(face, live, doc, dev, geo, agent, vq)
    with right:
        st.plotly_chart(gauge(d.score, "VKYC risk score"), use_container_width=True)
        a, b = st.columns(2)
        with a:
            st.markdown("**Recommended action**"); action_badge(d)
        with b:
            st.metric("Risk level", d.level)
            st.metric("Model confidence", f"{d.confidence}%")
    st.markdown("---")
    cc1, cc2 = st.columns([1.1, 1])
    with cc1:
        render_reasons(d)
    with cc2:
        render_contributions(d)

# --------------------------------------------------------------------------- #
#  TAB 3 — Transaction Sentinel
# --------------------------------------------------------------------------- #
with tabs[2]:
    st.subheader("🔎 Transaction Sentinel — live transaction risk")
    left, right = st.columns([1, 1.2])
    with left:
        st.markdown("**Transaction signals**")
        amt = st.number_input("Transaction amount (₹)", 0, 1_000_000, 4500, step=500)
        avg = st.number_input("User's average transaction (₹)", 1, 1_000_000, 3000, step=500)
        mcat = st.selectbox("Merchant category",
                            ["Groceries", "Fuel", "Dining", "Travel", "Electronics",
                             "Luxury / jewellery", "Crypto exchange", "Online gambling",
                             "Gift cards", "Wire / forex transfer"])
        mrisk = st.select_slider("Merchant risk", ["Low", "Medium", "High"], "Low")
        dch = st.toggle("Device changed", value=False)
        loc = st.toggle("Location mismatch", value=False)
        vel = st.slider("Transactions in last hour", 0, 15, 1)
        hour = st.slider("Transaction time (hour)", 0, 23, 14)
        ex = st.radio("Quick demo profiles",
                      ["—", "Genuine big spend", "Account-takeover fraud"], horizontal=True)
        if ex == "Genuine big spend":
            amt, avg, mcat, mrisk, dch, loc, vel, hour = 85000, 5000, "Luxury / jewellery", "Medium", False, False, 2, 19
            st.caption("Large spend on a trusted device — watch the false-decline guard")
        elif ex == "Account-takeover fraud":
            amt, avg, mcat, mrisk, dch, loc, vel, hour = 95000, 3000, "Crypto exchange", "High", True, True, 9, 3
            st.caption("New device + geo jump + velocity at 3am")

    d = score_transaction(amt, avg, mcat, mrisk, dch, loc, vel, hour)
    with right:
        st.plotly_chart(gauge(d.score, "Transaction risk score"), use_container_width=True)
        a, b = st.columns(2)
        with a:
            st.markdown("**Recommended action**"); action_badge(d)
        with b:
            st.metric("Risk level", d.level)
            st.metric("Model confidence", f"{d.confidence}%")
        if d.false_decline_warning:
            st.warning("⚠️ **False-decline guard active** — trusted device + location "
                       "intact. Step-up authentication preserves a likely-genuine spend "
                       "instead of a hard decline.", icon="⚠️")
    st.markdown("---")
    cc1, cc2 = st.columns([1.1, 1])
    with cc1:
        render_reasons(d)
    with cc2:
        render_contributions(d)

# --------------------------------------------------------------------------- #
#  TAB 4 — Growth Copilot
# --------------------------------------------------------------------------- #
with tabs[3]:
    st.subheader("🚀 Growth Copilot — risk-aware customer communication")
    left, right = st.columns([1, 1.2])
    with left:
        st.markdown("**Customer profile**")
        seg = st.selectbox("Customer segment",
                           ["New-to-card", "Mass", "Mass-affluent", "Premium"])
        trend = st.select_slider("Spend trend",
                                 ["Dormant", "Declining", "Stable", "Growing"], "Stable")
        ctr = st.slider("Historical click-through rate (%)", 0.0, 15.0, 3.5, 0.5)
        pref = st.selectbox("Preferred category",
                            ["Travel", "Dining", "Shopping", "Fuel", "Groceries", "Electronics"])
        rlvl = st.select_slider("Risk level", ["Low", "Medium", "High", "Critical"], "Low")

    rec = recommend_growth(seg, trend, ctr, pref, rlvl)
    with right:
        if rec["risk_gated"]:
            st.warning("Risk-gated: high-risk customer — no aggressive limit/credit offers. "
                       "Trust-first messaging only.", icon="🔒")
        st.markdown(f'<div class="og-card"><span class="og-kpi-l">Message theme</span><br>'
                    f'<b style="font-size:20px;color:{MINT};">{rec["theme"]}</b></div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="og-card"><span class="og-kpi-l">Offer suggestion</span><br>'
                    f'<b style="font-size:16px;">{rec["offer"]}</b></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="og-card"><span class="og-kpi-l">Recommended channel</span><br>'
                    f'<b style="font-size:16px;">{rec["channel"]}</b></div>', unsafe_allow_html=True)
        u1, u2 = st.columns(2)
        u1.metric("Expected CTR uplift", f"+{rec['ctr_uplift']}%")
        u2.metric("Expected spend uplift", f"+{rec['spend_uplift']}%")
    st.caption("Uplift figures are illustrative, directional estimates for the prototype.")

# --------------------------------------------------------------------------- #
#  TAB 5 — Assumptions
# --------------------------------------------------------------------------- #
with tabs[4]:
    st.subheader("📐 Assumptions, thresholds & KPI logic")
    st.markdown("Everything here is **transparent and rule-based** to demonstrate the AI "
                "decisioning concept. In production each weight and threshold is **learned "
                "and calibrated** on historical VKYC outcomes, chargebacks, manual-review "
                "tags, false-decline labels and spend-quality metrics.")

    st.markdown("#### VKYC Shield — signal weights (risk points)")
    st.dataframe(pd.DataFrame([
        {"Signal": k, **v} for k, v in VKYC_WEIGHTS.items()
    ]).fillna("—"), use_container_width=True, hide_index=True)

    st.markdown("#### Transaction Sentinel — signal weights (risk points)")
    st.dataframe(pd.DataFrame([
        {"Signal": k, **v} for k, v in TXN_WEIGHTS.items()
    ]).fillna("—"), use_container_width=True, hide_index=True)
    st.caption(f"High-risk merchant categories: {', '.join(sorted(HIGH_RISK_MCC))}")

    cband1, cband2 = st.columns(2)
    with cband1:
        st.markdown("#### VKYC action thresholds")
        st.dataframe(pd.DataFrame(
            [{"Score": f"{lo}-{hi}", "Action": a, "Level": lv}
             for lo, hi, a, _, lv in VKYC_BANDS]),
            use_container_width=True, hide_index=True)
    with cband2:
        st.markdown("#### Transaction action thresholds")
        st.dataframe(pd.DataFrame(
            [{"Score": f"{lo}-{hi}", "Action": a, "Level": lv}
             for lo, hi, a, _, lv in TXN_BANDS]),
            use_container_width=True, hide_index=True)

    st.markdown("#### Expected pilot KPI assumptions")
    st.dataframe(pd.DataFrame([
        ["VKYC manual review time", "40–60% reduction"],
        ["Fraud detection accuracy", "15–25% improvement"],
        ["False transaction declines", "20–35% reduction"],
        ["Good-quality spends", "5–10% uplift"],
        ["Fraud investigation workload", "30–50% reduction"],
    ], columns=["KPI", "Expected pilot impact (directional)"]),
        use_container_width=True, hide_index=True)

    st.info("Core business insight: where possible OneGuard recommends **step-up "
            "authentication instead of a hard decline** — cutting false declines while "
            "preserving genuine, good-quality spends.", icon="💡")

st.markdown("<br><center style='color:#5C6A92;font-size:12px;'>OneGuard AI · hypothetical "
            "fintech prototype · synthetic data · transparent scoring · built for Abakus AI "
            "Catalyst</center>", unsafe_allow_html=True)

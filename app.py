import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from data.fetcher import get_fundamentals
from scoring.scorer import score_company
from scoring.explainer import explain_company
from scoring.ai_summary import generate_summary
from visuals.charts import (
    chart_price_history,
    chart_factor_scores,
    chart_margins,
    chart_revenue_earnings,
)

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Investment Research Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Styles ────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #0E1117; }

    /* Metric cards */
    [data-testid="metric-container"] {
        background-color: #1C2030;
        border: 1px solid #2A3040;
        border-radius: 10px;
        padding: 16px;
    }

    /* Signal badge */
    .signal-badge {
        display: inline-block;
        padding: 8px 20px;
        border-radius: 20px;
        font-size: 18px;
        font-weight: 700;
        margin-bottom: 8px;
    }

    /* Section headers */
    .section-header {
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 1.5px;
        color: #8A94A6;
        text-transform: uppercase;
        margin: 24px 0 12px 0;
    }

    /* Factor explanation cards */
    .factor-card {
        background-color: #1C2030;
        border: 1px solid #2A3040;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 10px;
    }
    .factor-title {
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .factor-text {
        font-size: 14px;
        color: #C0C8D8;
        line-height: 1.5;
    }

    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ── Signal colours ────────────────────────────────────────────────────────────

SIGNAL_STYLE = {
    "Strong Watch": ("background-color:#003D2E; color:#00C48C; border:1px solid #00C48C;"),
    "Watch":        ("background-color:#0D2645; color:#4D9FFF; border:1px solid #4D9FFF;"),
    "Neutral":      ("background-color:#3D2800; color:#FF9F40; border:1px solid #FF9F40;"),
    "Avoid for Now":("background-color:#3D0000; color:#FF4D4D; border:1px solid #FF4D4D;"),
    "High Risk":    ("background-color:#2D0000; color:#FF2020; border:1px solid #FF2020;"),
    "Insufficient Data": ("background-color:#1C2030; color:#8A94A6; border:1px solid #2A3040;"),
}

SCORE_COLOUR = {
    "growth":        "#00C48C",
    "profitability": "#4D9FFF",
    "valuation":     "#FF9F40",
    "health":        "#9B59B6",
    "momentum":      "#FF4D4D",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def fmt_large(val):
    if val is None:
        return "N/A"
    if abs(val) >= 1_000_000_000:
        return f"${val/1_000_000_000:.1f}B"
    if abs(val) >= 1_000_000:
        return f"${val/1_000_000:.1f}M"
    return f"${val:,.0f}"

def fmt_pct(val):
    if val is None:
        return "N/A"
    return f"{val*100:.1f}%"

def fmt_num(val, dp=2):
    if val is None:
        return "N/A"
    return f"{val:.{dp}f}x"

@st.cache_data(ttl=3600)
def load_data(ticker):
    result   = explain_company(ticker)
    data     = score_company(ticker)["data"]
    return result, data


# ── Header ────────────────────────────────────────────────────────────────────

st.markdown("## 📈 Investment Research Dashboard")
st.markdown("<p style='color:#8A94A6; margin-top:-12px;'>Evidence-based company analysis. Not financial advice.</p>", unsafe_allow_html=True)

st.divider()

# ── Ticker input ──────────────────────────────────────────────────────────────

col_input, col_period, col_empty = st.columns([2, 2, 6])

with col_input:
    ticker_input = st.text_input(
        "Ticker Symbol",
        placeholder="e.g. AAPL, TSLA, MSFT",
        label_visibility="collapsed",
    ).upper().strip()

with col_period:
    period = st.selectbox(
        "Period",
        options=["1mo", "3mo", "6mo", "1y", "2y", "5y"],
        index=3,
        label_visibility="collapsed",
    )

# ── Main dashboard ────────────────────────────────────────────────────────────

if ticker_input:
    with st.spinner(f"Fetching data for {ticker_input}..."):
        try:
            result, data = load_data(ticker_input)
        except Exception as e:
            st.error(f"Could not load data for **{ticker_input}**. Check the ticker and try again.")
            st.stop()

    # ── Company header ────────────────────────────────────────────────────────

    name   = result.get("name") or ticker_input
    sector = result.get("sector") or "Unknown sector"
    signal = result.get("signal", "Insufficient Data")
    overall = result.get("overall")
    badge_style = SIGNAL_STYLE.get(signal, SIGNAL_STYLE["Insufficient Data"])

    st.markdown(f"### {name} &nbsp; <span style='font-size:16px; color:#8A94A6;'>({ticker_input})</span>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#8A94A6; margin-top:-12px;'>{sector}</p>", unsafe_allow_html=True)

    col_signal, col_score, col_empty2 = st.columns([2, 2, 6])
    with col_signal:
        st.markdown(f"<div class='signal-badge' style='{badge_style}'>{signal}</div>", unsafe_allow_html=True)
    with col_score:
        if overall:
            st.markdown(f"<div style='padding:8px 0; font-size:16px; color:#8A94A6;'>Overall score: <b style='color:#FAFAFA;'>{overall} / 5.0</b></div>", unsafe_allow_html=True)

    st.divider()

    # ── Key metrics ───────────────────────────────────────────────────────────

    st.markdown("<div class='section-header'>Key Metrics</div>", unsafe_allow_html=True)

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Price",        fmt_large(data.get("current_price")))
    m2.metric("Market Cap",   fmt_large(data.get("market_cap")))
    m3.metric("P/E (Trail.)", fmt_num(data.get("pe_trailing")))
    m4.metric("Revenue Gr.",  fmt_pct(data.get("revenue_growth")))
    m5.metric("Net Margin",   fmt_pct(data.get("net_margin")))
    m6.metric("Debt/Equity",  fmt_num(data.get("debt_to_equity")))

    st.divider()

    # ── Charts row 1: price + factor scores ──────────────────────────────────

    st.markdown("<div class='section-header'>Price & Scores</div>", unsafe_allow_html=True)

    col_price, col_scores = st.columns([3, 2])

    with col_price:
        fig_price = chart_price_history(ticker_input, period)
        st.plotly_chart(fig_price, use_container_width=True)

    with col_scores:
        fig_scores = chart_factor_scores(result["scores"], signal, name)
        st.plotly_chart(fig_scores, use_container_width=True)

    # ── Factor explanations ───────────────────────────────────────────────────

    st.markdown("<div class='section-header'>Factor Analysis</div>", unsafe_allow_html=True)

    factor_order = ["growth", "profitability", "valuation", "health", "momentum"]
    explanations = result.get("explanations", {})
    scores       = result.get("scores", {})

    col_left, col_right = st.columns(2)

    for i, factor in enumerate(factor_order):
        score = scores.get(factor)
        score_str = f"{score:.1f}/5" if score is not None else "N/A"
        explanation = explanations.get(factor, "No data available.")
        colour = SCORE_COLOUR.get(factor, "#8A94A6")

        card_html = f"""
        <div class='factor-card'>
            <div class='factor-title' style='color:{colour};'>{factor.capitalize()} &nbsp; {score_str}</div>
            <div class='factor-text'>{explanation}</div>
        </div>
        """
        if i % 2 == 0:
            col_left.markdown(card_html, unsafe_allow_html=True)
        else:
            col_right.markdown(card_html, unsafe_allow_html=True)

    st.divider()

    # ── Charts row 2: revenue + margins ──────────────────────────────────────

    st.markdown("<div class='section-header'>Financials Over Time</div>", unsafe_allow_html=True)

    col_rev, col_margins = st.columns(2)

    with col_rev:
        fig_rev = chart_revenue_earnings(ticker_input)
        st.plotly_chart(fig_rev, use_container_width=True)

    with col_margins:
        fig_margins = chart_margins(ticker_input)
        st.plotly_chart(fig_margins, use_container_width=True)

    # ── Raw data expander ─────────────────────────────────────────────────────

    # ── AI Summary ───────────────────────────────────────────────────────────

    st.markdown("<div class='section-header'>AI Research Summary</div>", unsafe_allow_html=True)

    if st.button("Generate AI Summary", type="primary"):
        with st.spinner("Analysing company data..."):
            try:
                summary = generate_summary(result, data)
                st.markdown(f"""
                <div style='background-color:#1C2030; border:1px solid #2A3040; border-radius:10px; padding:24px; line-height:1.8; color:#C0C8D8; font-size:15px;'>
                {summary.replace(chr(10), "<br><br>")}
                </div>
                """, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Could not generate summary: {e}")

    st.divider()

    with st.expander("📋 Raw Data"):
        st.json(data)

else:
    st.markdown("""
    <div style='text-align:center; padding: 80px 0; color:#8A94A6;'>
        <div style='font-size:48px; margin-bottom:16px;'>📈</div>
        <div style='font-size:20px; font-weight:600; color:#FAFAFA; margin-bottom:8px;'>Enter a ticker symbol to begin</div>
        <div style='font-size:14px;'>Try AAPL, TSLA, MSFT, NVDA, AMZN</div>
    </div>
    """, unsafe_allow_html=True)

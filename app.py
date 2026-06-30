import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from data.fetcher import get_fundamentals
from scoring.scorer import score_company
from scoring.explainer import explain_company
from scoring.ai_summary import generate_summary
from scoring.sector_comparison import get_sector_comparison
from scoring.news_sentiment import get_news_sentiment
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
    initial_sidebar_state="expanded",
)

# ── Session state init ────────────────────────────────────────────────────────

if "watchlist" not in st.session_state:
    st.session_state.watchlist = []

# ── Styles ────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    [data-testid="metric-container"] {
        background-color: #1C2030; border: 1px solid #2A3040;
        border-radius: 10px; padding: 16px;
    }
    .signal-badge {
        display: inline-block; padding: 8px 20px; border-radius: 20px;
        font-size: 18px; font-weight: 700; margin-bottom: 8px;
    }
    .section-header {
        font-size: 13px; font-weight: 600; letter-spacing: 1.5px;
        color: #8A94A6; text-transform: uppercase; margin: 24px 0 12px 0;
    }
    .factor-card {
        background-color: #1C2030; border: 1px solid #2A3040;
        border-radius: 10px; padding: 16px 20px; margin-bottom: 10px;
    }
    .factor-title {
        font-size: 13px; font-weight: 700; letter-spacing: 1px;
        text-transform: uppercase; margin-bottom: 4px;
    }
    .factor-text { font-size: 14px; color: #C0C8D8; line-height: 1.5; }
    .watchlist-item {
        background-color: #1C2030; border: 1px solid #2A3040;
        border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

SIGNAL_STYLE = {
    "Strong Watch":  "background-color:#003D2E; color:#00C48C; border:1px solid #00C48C;",
    "Watch":         "background-color:#0D2645; color:#4D9FFF; border:1px solid #4D9FFF;",
    "Neutral":       "background-color:#3D2800; color:#FF9F40; border:1px solid #FF9F40;",
    "Avoid for Now": "background-color:#3D0000; color:#FF4D4D; border:1px solid #FF4D4D;",
    "High Risk":     "background-color:#2D0000; color:#FF2020; border:1px solid #FF2020;",
    "Insufficient Data": "background-color:#1C2030; color:#8A94A6; border:1px solid #2A3040;",
}

SCORE_COLOUR = {
    "growth": "#00C48C", "profitability": "#4D9FFF",
    "valuation": "#FF9F40", "health": "#9B59B6", "momentum": "#FF4D4D",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def fmt_large(val):
    if val is None: return "N/A"
    if abs(val) >= 1_000_000_000: return f"${val/1_000_000_000:.1f}B"
    if abs(val) >= 1_000_000: return f"${val/1_000_000:.1f}M"
    return f"${val:,.0f}"

def fmt_pct(val):
    return "N/A" if val is None else f"{val*100:.1f}%"

def fmt_num(val, dp=2):
    return "N/A" if val is None else f"{val:.{dp}f}x"

@st.cache_data(ttl=3600)
def load_data(ticker):
    result = explain_company(ticker)
    data   = score_company(ticker)["data"]
    return result, data


def render_company_dashboard(ticker_input, period, show_ai=True, key_prefix=""):
    """Renders the full dashboard for a single ticker. Used in both Research and Compare tabs."""
    try:
        result, data = load_data(ticker_input)
    except Exception as e:
        st.error(f"Could not load data for **{ticker_input}**.")
        st.exception(e)
        return None, None

    name    = result.get("name") or ticker_input
    sector  = result.get("sector") or "Unknown sector"
    signal  = result.get("signal", "Insufficient Data")
    overall = result.get("overall")
    badge_style = SIGNAL_STYLE.get(signal, SIGNAL_STYLE["Insufficient Data"])

    col_title, col_watch = st.columns([5, 1])
    with col_title:
        st.markdown(f"### {name} &nbsp; <span style='font-size:16px; color:#8A94A6;'>({ticker_input})</span>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:#8A94A6; margin-top:-12px;'>{sector}</p>", unsafe_allow_html=True)
    with col_watch:
        in_watchlist = ticker_input in st.session_state.watchlist
        label = "★ Watching" if in_watchlist else "☆ Add to Watchlist"
        if st.button(label, key=f"{key_prefix}watch_{ticker_input}"):
            if in_watchlist:
                st.session_state.watchlist.remove(ticker_input)
            else:
                st.session_state.watchlist.append(ticker_input)
            st.rerun()

    col_signal, col_score, _ = st.columns([2, 2, 6])
    with col_signal:
        st.markdown(f"<div class='signal-badge' style='{badge_style}'>{signal}</div>", unsafe_allow_html=True)
    with col_score:
        if overall:
            st.markdown(f"<div style='padding:8px 0; font-size:16px; color:#8A94A6;'>Overall score: <b style='color:#FAFAFA;'>{overall} / 5.0</b></div>", unsafe_allow_html=True)

    st.divider()

    st.markdown("<div class='section-header'>Key Metrics</div>", unsafe_allow_html=True)
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Price",        fmt_large(data.get("current_price")))
    m2.metric("Market Cap",   fmt_large(data.get("market_cap")))
    m3.metric("P/E (Trail.)", fmt_num(data.get("pe_trailing")))
    m4.metric("Revenue Gr.",  fmt_pct(data.get("revenue_growth")))
    m5.metric("Net Margin",   fmt_pct(data.get("net_margin")))
    m6.metric("Debt/Equity",  fmt_num(data.get("debt_to_equity")))

    st.divider()

    st.markdown("<div class='section-header'>Price & Scores</div>", unsafe_allow_html=True)
    col_price, col_scores = st.columns([3, 2])
    with col_price:
        st.plotly_chart(chart_price_history(ticker_input, period), use_container_width=True, key=f"{key_prefix}price_{ticker_input}")
    with col_scores:
        st.plotly_chart(chart_factor_scores(result["scores"], signal, name), use_container_width=True, key=f"{key_prefix}scores_{ticker_input}")

    st.markdown("<div class='section-header'>Factor Analysis</div>", unsafe_allow_html=True)
    factor_order = ["growth", "profitability", "valuation", "health", "momentum"]
    explanations = result.get("explanations", {})
    scores = result.get("scores", {})
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
        (col_left if i % 2 == 0 else col_right).markdown(card_html, unsafe_allow_html=True)

    st.divider()
    st.markdown("<div class='section-header'>Financials Over Time</div>", unsafe_allow_html=True)
    col_rev, col_margins = st.columns(2)
    with col_rev:
        st.plotly_chart(chart_revenue_earnings(ticker_input), use_container_width=True, key=f"{key_prefix}rev_{ticker_input}")
    with col_margins:
        st.plotly_chart(chart_margins(ticker_input), use_container_width=True, key=f"{key_prefix}margins_{ticker_input}")

    if show_ai:
        st.markdown("<div class='section-header'>AI Research Summary</div>", unsafe_allow_html=True)
        if st.button("Generate AI Summary", type="primary", key=f"{key_prefix}ai_{ticker_input}"):
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

        st.markdown("<div class='section-header'>News Sentiment</div>", unsafe_allow_html=True)
        if st.button("Check Recent News Sentiment", key=f"{key_prefix}news_{ticker_input}"):
            with st.spinner("Pulling recent headlines and analysing sentiment..."):
                try:
                    news = get_news_sentiment(ticker_input)
                    sentiment_colours = {
                        "Positive": "#00C48C", "Slightly Positive": "#4D9FFF",
                        "Neutral": "#FF9F40", "Slightly Negative": "#FF9F40",
                        "Negative": "#FF4D4D", "No Data": "#8A94A6",
                    }
                    colour = sentiment_colours.get(news["sentiment"], "#8A94A6")

                    st.markdown(f"""
                    <div style='background-color:#1C2030; border:1px solid #2A3040; border-radius:10px; padding:20px; margin-bottom:16px;'>
                        <span style='font-size:16px; font-weight:700; color:{colour};'>{news['sentiment']}</span>
                        <p style='color:#C0C8D8; margin-top:8px; margin-bottom:0;'>{news['rationale']}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    if news["articles"]:
                        for a in news["articles"][:6]:
                            st.markdown(f"""
                            <div style='padding:10px 0; border-bottom:1px solid #2A3040;'>
                                <a href='{a["url"]}' target='_blank' style='color:#FAFAFA; text-decoration:none; font-weight:600; font-size:14px;'>{a["headline"]}</a>
                                <div style='color:#8A94A6; font-size:12px; margin-top:2px;'>{a["source"]}</div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.caption("No recent news found.")
                except Exception as e:
                    st.error(f"Could not load news sentiment: {e}")

        st.divider()
        with st.expander("📋 Raw Data"):
            st.json(data)

    return result, data


# ── Sidebar: Watchlist ────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⭐ Watchlist")

    if not st.session_state.watchlist:
        st.caption("No companies watched yet. Add some from the Research tab.")
    else:
        for t in list(st.session_state.watchlist):
            try:
                wl_result, _ = load_data(t)
                signal = wl_result.get("signal", "N/A")
                overall = wl_result.get("overall", "N/A")
                colour = SIGNAL_COLOURS = {
                    "Strong Watch": "#00C48C", "Watch": "#4D9FFF", "Neutral": "#FF9F40",
                    "Avoid for Now": "#FF4D4D", "High Risk": "#9B3030",
                }.get(signal, "#8A94A6")
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    st.markdown(f"""
                    <div class='watchlist-item'>
                        <b>{t}</b><br>
                        <span style='color:{colour}; font-size:13px;'>{signal}</span>
                        <span style='color:#8A94A6; font-size:12px;'> · {overall}/5.0</span>
                    </div>
                    """, unsafe_allow_html=True)
                with col_b:
                    if st.button("✕", key=f"remove_{t}"):
                        st.session_state.watchlist.remove(t)
                        st.rerun()
            except Exception:
                st.caption(f"{t} — could not load")

    st.divider()
    st.caption("Watchlist is stored for this browser session only.")

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown("## 📈 Investment Research Dashboard")
st.markdown("<p style='color:#8A94A6; margin-top:-12px;'>Evidence-based company analysis. Not financial advice.</p>", unsafe_allow_html=True)

st.divider()

tab_research, tab_compare, tab_sector = st.tabs(["🔍 Research", "⚖️ Compare", "🏢 Sector"])

# ── Tab 1: Research ───────────────────────────────────────────────────────────

with tab_research:
    col_input, col_period, _ = st.columns([2, 2, 6])
    with col_input:
        ticker_input = st.text_input(
            "Ticker Symbol", placeholder="e.g. AAPL, TSLA, MSFT",
            label_visibility="collapsed", key="research_ticker"
        ).upper().strip()
    with col_period:
        period = st.selectbox(
            "Period", options=["1mo", "3mo", "6mo", "1y", "2y", "5y"],
            index=3, label_visibility="collapsed", key="research_period"
        )

    if ticker_input:
        with st.spinner(f"Fetching data for {ticker_input}..."):
            render_company_dashboard(ticker_input, period, show_ai=True, key_prefix="research_")
    else:
        st.markdown("""
        <div style='text-align:center; padding: 80px 0; color:#8A94A6;'>
            <div style='font-size:48px; margin-bottom:16px;'>📈</div>
            <div style='font-size:20px; font-weight:600; color:#FAFAFA; margin-bottom:8px;'>Enter a ticker symbol to begin</div>
            <div style='font-size:14px;'>Try AAPL, TSLA, MSFT, NVDA, AMZN</div>
        </div>
        """, unsafe_allow_html=True)

# ── Tab 2: Compare ────────────────────────────────────────────────────────────

with tab_compare:
    col_a, col_b = st.columns(2)
    with col_a:
        ticker_a = st.text_input("Company A", placeholder="e.g. AAPL", key="compare_a").upper().strip()
    with col_b:
        ticker_b = st.text_input("Company B", placeholder="e.g. MSFT", key="compare_b").upper().strip()

    if ticker_a and ticker_b:
        with st.spinner("Loading comparison..."):
            try:
                result_a, data_a = load_data(ticker_a)
                result_b, data_b = load_data(ticker_b)

                st.markdown("<div class='section-header'>Signal Comparison</div>", unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                for col, ticker, result in [(col1, ticker_a, result_a), (col2, ticker_b, result_b)]:
                    signal = result.get("signal", "N/A")
                    overall = result.get("overall", "N/A")
                    badge_style = SIGNAL_STYLE.get(signal, SIGNAL_STYLE["Insufficient Data"])
                    with col:
                        st.markdown(f"### {result.get('name', ticker)} ({ticker})")
                        st.markdown(f"<div class='signal-badge' style='{badge_style}'>{signal}</div>", unsafe_allow_html=True)
                        st.markdown(f"Overall: **{overall}/5.0**")

                st.divider()
                st.markdown("<div class='section-header'>Metric Comparison</div>", unsafe_allow_html=True)

                rows = [
                    ("Price",          fmt_large(data_a.get("current_price")),   fmt_large(data_b.get("current_price"))),
                    ("Market Cap",     fmt_large(data_a.get("market_cap")),      fmt_large(data_b.get("market_cap"))),
                    ("P/E (Trailing)", fmt_num(data_a.get("pe_trailing")),       fmt_num(data_b.get("pe_trailing"))),
                    ("Revenue Growth", fmt_pct(data_a.get("revenue_growth")),    fmt_pct(data_b.get("revenue_growth"))),
                    ("Gross Margin",   fmt_pct(data_a.get("gross_margin")),      fmt_pct(data_b.get("gross_margin"))),
                    ("Net Margin",     fmt_pct(data_a.get("net_margin")),        fmt_pct(data_b.get("net_margin"))),
                    ("ROE",            fmt_pct(data_a.get("roe")),               fmt_pct(data_b.get("roe"))),
                    ("Debt/Equity",    fmt_num(data_a.get("debt_to_equity")),    fmt_num(data_b.get("debt_to_equity"))),
                    ("Current Ratio",  fmt_num(data_a.get("current_ratio")),     fmt_num(data_b.get("current_ratio"))),
                ]

                import pandas as pd
                df = pd.DataFrame(rows, columns=["Metric", ticker_a, ticker_b])
                st.dataframe(df, use_container_width=True, hide_index=True)

                st.divider()
                st.markdown("<div class='section-header'>Factor Score Comparison</div>", unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    st.plotly_chart(chart_factor_scores(result_a["scores"], result_a["signal"], ticker_a), use_container_width=True, key="cmp_a")
                with col2:
                    st.plotly_chart(chart_factor_scores(result_b["scores"], result_b["signal"], ticker_b), use_container_width=True, key="cmp_b")

            except Exception as e:
                st.error("Could not load comparison data.")
                st.exception(e)
    else:
        st.markdown("""
        <div style='text-align:center; padding: 80px 0; color:#8A94A6;'>
            <div style='font-size:48px; margin-bottom:16px;'>⚖️</div>
            <div style='font-size:20px; font-weight:600; color:#FAFAFA; margin-bottom:8px;'>Enter two tickers to compare</div>
            <div style='font-size:14px;'>e.g. AAPL vs MSFT</div>
        </div>
        """, unsafe_allow_html=True)

# ── Tab 3: Sector Comparison ──────────────────────────────────────────────────

with tab_sector:
    sector_ticker = st.text_input(
        "Ticker Symbol", placeholder="e.g. AAPL",
        label_visibility="collapsed", key="sector_ticker"
    ).upper().strip()

    if sector_ticker:
        with st.spinner(f"Finding peers and comparing {sector_ticker}..."):
            try:
                sector_data = get_sector_comparison(sector_ticker)

                if sector_data["peer_count"] == 0:
                    st.warning(f"No peer data found for **{sector_ticker}**. This may be an unusual or thinly-covered ticker.")
                else:
                    st.markdown(f"### {sector_data['name']} ({sector_ticker})")
                    st.markdown(f"<p style='color:#8A94A6; margin-top:-12px;'>{sector_data['sector']} &nbsp;·&nbsp; Compared against {sector_data['peer_count']} peers: {', '.join(sector_data['peers'])}</p>", unsafe_allow_html=True)

                    st.divider()
                    st.markdown("<div class='section-header'>Metric vs Peer Average</div>", unsafe_allow_html=True)

                    for item in sector_data["comparison"]:
                        target_val = item["target_value"]
                        peer_avg   = item["peer_average"]
                        verdict    = item["verdict"]
                        unit       = item["unit"]

                        if target_val is None or peer_avg is None:
                            continue

                        if unit == "%":
                            target_str = f"{target_val*100:.1f}%"
                            peer_str   = f"{peer_avg*100:.1f}%"
                        else:
                            target_str = f"{target_val:.2f}{unit}"
                            peer_str   = f"{peer_avg:.2f}{unit}"

                        if verdict:
                            colour = "#00C48C" if verdict["is_better"] else "#FF4D4D"
                            arrow  = "▲" if verdict["diff_pct"] > 0 else "▼"
                            diff_label = f"{arrow} {abs(verdict['diff_pct']):.0f}% vs peers"
                        else:
                            colour = "#8A94A6"
                            diff_label = "N/A"

                        col_label, col_target, col_peer, col_verdict = st.columns([2, 1.5, 1.5, 2])
                        with col_label:
                            st.markdown(f"<div style='padding:10px 0; color:#FAFAFA; font-weight:600;'>{item['label']}</div>", unsafe_allow_html=True)
                        with col_target:
                            st.markdown(f"<div style='padding:10px 0; color:#FAFAFA;'>{sector_ticker}: <b>{target_str}</b></div>", unsafe_allow_html=True)
                        with col_peer:
                            st.markdown(f"<div style='padding:10px 0; color:#8A94A6;'>Peers avg: {peer_str}</div>", unsafe_allow_html=True)
                        with col_verdict:
                            st.markdown(f"<div style='padding:10px 0; color:{colour}; font-weight:600;'>{diff_label}</div>", unsafe_allow_html=True)

                    st.divider()
                    st.caption("Peer average calculated from publicly listed direct competitors. 'Better' is directional only — not a recommendation.")

            except Exception as e:
                st.error("Could not load sector comparison.")
                st.exception(e)
    else:
        st.markdown("""
        <div style='text-align:center; padding: 80px 0; color:#8A94A6;'>
            <div style='font-size:48px; margin-bottom:16px;'>🏢</div>
            <div style='font-size:20px; font-weight:600; color:#FAFAFA; margin-bottom:8px;'>Enter a ticker to see how it compares to its sector</div>
            <div style='font-size:14px;'>e.g. AAPL — compared against Dell, HP, NetApp and others</div>
        </div>
        """, unsafe_allow_html=True)

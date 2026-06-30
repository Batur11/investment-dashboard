import os
import requests
import csv
import io
import datetime
import plotly.graph_objects as go
from dotenv import load_dotenv

load_dotenv()

FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")
FINNHUB_BASE = "https://finnhub.io/api/v1"


def fh_get(endpoint, params={}):
    try:
        params["token"] = FINNHUB_KEY
        r = requests.get(f"{FINNHUB_BASE}/{endpoint}", params=params, timeout=10)
        r.raise_for_status()
        return r.json() or None
    except Exception:
        return None


COLOURS = {
    "green": "#00C48C", "red": "#FF4D4D", "blue": "#4D9FFF",
    "orange": "#FF9F40", "background": "#0E1117", "surface": "#1C2030",
    "text": "#FAFAFA", "muted": "#8A94A6",
}

SIGNAL_COLOURS = {
    "Strong Watch": "#00C48C", "Watch": "#4D9FFF",
    "Neutral": "#FF9F40", "Avoid for Now": "#FF4D4D", "High Risk": "#9B3030",
}

BASE_LAYOUT = dict(
    paper_bgcolor=COLOURS["background"],
    plot_bgcolor=COLOURS["surface"],
    font=dict(color=COLOURS["text"], family="Inter, sans-serif"),
    margin=dict(l=40, r=40, t=50, b=40),
    xaxis=dict(gridcolor="#2A3040", showgrid=True),
    yaxis=dict(gridcolor="#2A3040", showgrid=True),
)

PERIOD_DAYS = {
    "1mo": 30, "3mo": 90, "6mo": 180,
    "1y": 365, "2y": 730, "5y": 1825,
}


# ── Price history via Twelve Data (free tier, 800 calls/day) ─────────────────

TWELVE_DATA_KEY = os.getenv("TWELVE_DATA_KEY")

PERIOD_OUTPUTSIZE = {
    "1mo": 30, "3mo": 90, "6mo": 180,
    "1y": 365, "2y": 730, "5y": 1825,
}

def chart_price_history(ticker, period="1y"):
    outputsize = PERIOD_OUTPUTSIZE.get(period, 365)
    fig = go.Figure()

    try:
        r = requests.get(
            "https://api.twelvedata.com/time_series",
            params={
                "symbol": ticker.upper(),
                "interval": "1day",
                "outputsize": outputsize,
                "apikey": TWELVE_DATA_KEY,
            },
            timeout=10,
        )
        r.raise_for_status()
        payload = r.json()
        values = payload.get("values", [])

        if not values:
            fig.add_annotation(text="No price data available", showarrow=False,
                               font=dict(color=COLOURS["muted"]))
        else:
            values = list(reversed(values))  # API returns newest first
            dates  = [v["datetime"] for v in values]
            prices = [float(v["close"]) for v in values]

            fig.add_trace(go.Scatter(
                x=dates, y=prices, mode="lines",
                line=dict(color=COLOURS["green"], width=2),
                fill="tozeroy", fillcolor="rgba(0, 196, 140, 0.1)",
            ))
    except Exception:
        fig.add_annotation(text="No price data available", showarrow=False,
                           font=dict(color=COLOURS["muted"]))

    fig.update_layout(
        **BASE_LAYOUT,
        title=dict(text=f"{ticker.upper()} — Price History ({period})", font=dict(size=16)),
        xaxis_title="", yaxis_title="Price (USD)",
        hovermode="x unified", showlegend=False,
    )
    return fig


# ── Factor scores bar chart ───────────────────────────────────────────────────

def chart_factor_scores(scores, signal, name):
    factors = ["Momentum", "Health", "Valuation", "Profitability", "Growth"]
    keys    = ["momentum", "health", "valuation", "profitability", "growth"]
    values  = [scores.get(k) or 0 for k in keys]

    bar_colours = []
    for v in values:
        if v >= 4.0:   bar_colours.append(COLOURS["green"])
        elif v >= 3.0: bar_colours.append(COLOURS["blue"])
        elif v >= 2.0: bar_colours.append(COLOURS["orange"])
        else:          bar_colours.append(COLOURS["red"])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=values, y=factors, orientation="h",
        marker_color=bar_colours,
        text=[f"{v:.1f}" for v in values],
        textposition="outside",
        textfont=dict(color=COLOURS["text"]),
    ))

    signal_colour = SIGNAL_COLOURS.get(signal, COLOURS["muted"])
    fig.update_layout(
        **BASE_LAYOUT,
        title=dict(
            text=f"{name} — Factor Scores  |  Signal: <b>{signal}</b>",
            font=dict(size=15, color=signal_colour)
        ),
        showlegend=False,
    )
    fig.update_xaxes(range=[0, 5.5], gridcolor="#2A3040")
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
    return fig


# ── Margins over time via Finnhub free metric series ──────────────────────────

def _get_annual_series(ticker, key):
    """Pull an annual metric series from Finnhub's free /stock/metric endpoint."""
    data = fh_get("stock/metric", {"symbol": ticker, "metric": "all"}) or {}
    series = data.get("series", {}).get("annual", {}).get(key, [])
    series = sorted(series, key=lambda x: x.get("period", ""))[-5:]
    dates  = [s["period"][:4] for s in series]
    values = [s.get("v") for s in series]
    return dates, values


def chart_margins(ticker):
    fig = go.Figure()

    dates_g, gross     = _get_annual_series(ticker, "grossMargin")
    dates_o, operating = _get_annual_series(ticker, "operatingMargin")
    dates_n, net        = _get_annual_series(ticker, "netMargin")

    if not dates_g and not dates_n:
        fig.add_annotation(text="No financials data available", showarrow=False,
                           font=dict(color=COLOURS["muted"]))
    else:
        if dates_g:
            fig.add_trace(go.Scatter(x=dates_g, y=[v*100 if v else 0 for v in gross],
                                     name="Gross Margin", mode="lines+markers",
                                     line=dict(color=COLOURS["green"], width=2)))
        if dates_o:
            fig.add_trace(go.Scatter(x=dates_o, y=[v*100 if v else 0 for v in operating],
                                     name="Operating Margin", mode="lines+markers",
                                     line=dict(color=COLOURS["blue"], width=2)))
        if dates_n:
            fig.add_trace(go.Scatter(x=dates_n, y=[v*100 if v else 0 for v in net],
                                     name="Net Margin", mode="lines+markers",
                                     line=dict(color=COLOURS["orange"], width=2)))

    fig.update_layout(
        **BASE_LAYOUT,
        title=dict(text=f"{ticker.upper()} — Margins Over Time (%)", font=dict(size=16)),
        xaxis_title="", yaxis_title="Margin (%)",
        hovermode="x unified",
        legend=dict(bgcolor=COLOURS["surface"], bordercolor="#2A3040", borderwidth=1),
    )
    return fig


# ── Revenue & earnings via salesPerShare * sharesOutstanding ──────────────────

def chart_revenue_earnings(ticker):
    fig = go.Figure()

    profile = fh_get("stock/profile2", {"symbol": ticker}) or {}
    shares  = profile.get("shareOutstanding")  # in millions

    dates_s, sales = _get_annual_series(ticker, "salesPerShare")
    dates_e, eps   = _get_annual_series(ticker, "eps")

    if not shares or not dates_s:
        fig.add_annotation(text="No revenue data available", showarrow=False,
                           font=dict(color=COLOURS["muted"]))
    else:
        revenue = [(v * shares / 1000) if v else 0 for v in sales]  # $B
        net_inc = [(v * shares / 1000) if v else 0 for v in eps] if dates_e else [0]*len(dates_s)

        fig.add_trace(go.Bar(x=dates_s, y=revenue, name="Revenue ($B)",    marker_color=COLOURS["blue"]))
        fig.add_trace(go.Bar(x=dates_s, y=net_inc, name="Net Income ($B)", marker_color=COLOURS["green"]))

    fig.update_layout(
        **BASE_LAYOUT,
        title=dict(text=f"{ticker.upper()} — Revenue & Net Income ($B, est.)", font=dict(size=16)),
        xaxis_title="", yaxis_title="USD Billions",
        barmode="group", hovermode="x unified",
        legend=dict(bgcolor=COLOURS["surface"], bordercolor="#2A3040", borderwidth=1),
    )
    return fig


if __name__ == "__main__":
    from scoring.scorer import score_company
    ticker = "AAPL"
    result = score_company(ticker)
    print(f"Generating charts for {ticker}...")
    chart_price_history(ticker, "1y").show()
    chart_factor_scores(result["scores"], result["signal"], result["name"]).show()
    chart_margins(ticker).show()
    chart_revenue_earnings(ticker).show()
    print("Done.")

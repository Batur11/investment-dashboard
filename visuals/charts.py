import os
import requests
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


def chart_price_history(ticker, period="1y"):
    import time, datetime
    days  = PERIOD_DAYS.get(period, 365)
    to_ts = int(time.time())
    from_ts = int((datetime.datetime.now() - datetime.timedelta(days=days)).timestamp())

    data = fh_get("stock/candle", {
        "symbol": ticker, "resolution": "D",
        "from": from_ts, "to": to_ts,
    })

    fig = go.Figure()

    if not data or data.get("s") == "no_data" or "c" not in data:
        fig.add_annotation(text="No price data available", showarrow=False,
                           font=dict(color=COLOURS["muted"]))
    else:
        import datetime as dt
        dates  = [dt.datetime.fromtimestamp(t).strftime("%Y-%m-%d") for t in data["t"]]
        prices = data["c"]

        fig.add_trace(go.Scatter(
            x=dates, y=prices, mode="lines",
            line=dict(color=COLOURS["green"], width=2),
            fill="tozeroy", fillcolor="rgba(0, 196, 140, 0.1)",
        ))

    fig.update_layout(
        **BASE_LAYOUT,
        title=dict(text=f"{ticker.upper()} — Price History ({period})", font=dict(size=16)),
        xaxis_title="", yaxis_title="Price (USD)",
        hovermode="x unified", showlegend=False,
    )
    return fig


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


def chart_margins(ticker):
    data = fh_get("stock/financials", {"symbol": ticker, "statement": "ic", "freq": "annual"}) or {}
    fig  = go.Figure()

    financials = data.get("financials", [])
    if not financials:
        fig.add_annotation(text="No financials data available", showarrow=False,
                           font=dict(color=COLOURS["muted"]))
    else:
        financials = sorted(financials, key=lambda x: x.get("period", ""))[-5:]
        dates    = [f.get("period", "")[:4] for f in financials]
        gross    = [f.get("grossProfitMargin", 0) * 100 if f.get("grossProfitMargin") else 0 for f in financials]
        operating = [f.get("operatingProfitMargin", 0) * 100 if f.get("operatingProfitMargin") else 0 for f in financials]
        net      = [f.get("netProfitMargin", 0) * 100 if f.get("netProfitMargin") else 0 for f in financials]

        fig.add_trace(go.Scatter(x=dates, y=gross,      name="Gross Margin",
                                 mode="lines+markers", line=dict(color=COLOURS["green"], width=2)))
        fig.add_trace(go.Scatter(x=dates, y=operating,  name="Operating Margin",
                                 mode="lines+markers", line=dict(color=COLOURS["blue"], width=2)))
        fig.add_trace(go.Scatter(x=dates, y=net,        name="Net Margin",
                                 mode="lines+markers", line=dict(color=COLOURS["orange"], width=2)))

    fig.update_layout(
        **BASE_LAYOUT,
        title=dict(text=f"{ticker.upper()} — Margins Over Time (%)", font=dict(size=16)),
        xaxis_title="", yaxis_title="Margin (%)",
        hovermode="x unified",
        legend=dict(bgcolor=COLOURS["surface"], bordercolor="#2A3040", borderwidth=1),
    )
    return fig


def chart_revenue_earnings(ticker):
    data = fh_get("stock/financials", {"symbol": ticker, "statement": "ic", "freq": "annual"}) or {}
    fig  = go.Figure()

    financials = data.get("financials", [])
    if not financials:
        fig.add_annotation(text="No revenue data available", showarrow=False,
                           font=dict(color=COLOURS["muted"]))
    else:
        financials = sorted(financials, key=lambda x: x.get("period", ""))[-5:]
        dates   = [f.get("period", "")[:4] for f in financials]
        revenue = [f.get("revenue", 0) / 1e9 if f.get("revenue") else 0 for f in financials]
        net_inc = [f.get("netIncome", 0) / 1e9 if f.get("netIncome") else 0 for f in financials]

        fig.add_trace(go.Bar(x=dates, y=revenue,  name="Revenue ($B)",    marker_color=COLOURS["blue"]))
        fig.add_trace(go.Bar(x=dates, y=net_inc,  name="Net Income ($B)", marker_color=COLOURS["green"]))

    fig.update_layout(
        **BASE_LAYOUT,
        title=dict(text=f"{ticker.upper()} — Revenue & Net Income ($B)", font=dict(size=16)),
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

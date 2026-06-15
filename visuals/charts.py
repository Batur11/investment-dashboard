import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


# ── Colour palette ────────────────────────────────────────────────────────────

COLOURS = {
    "green":      "#00C48C",
    "red":        "#FF4D4D",
    "blue":       "#4D9FFF",
    "orange":     "#FF9F40",
    "purple":     "#9B59B6",
    "background": "#0E1117",
    "surface":    "#1C2030",
    "text":       "#FAFAFA",
    "muted":      "#8A94A6",
}

SIGNAL_COLOURS = {
    "Strong Watch": "#00C48C",
    "Watch":        "#4D9FFF",
    "Neutral":      "#FF9F40",
    "Avoid for Now":"#FF4D4D",
    "High Risk":    "#9B3030",
}

BASE_LAYOUT = dict(
    paper_bgcolor=COLOURS["background"],
    plot_bgcolor=COLOURS["surface"],
    font=dict(color=COLOURS["text"], family="Inter, sans-serif"),
    margin=dict(l=40, r=40, t=50, b=40),
    xaxis=dict(gridcolor="#2A3040", showgrid=True),
    yaxis=dict(gridcolor="#2A3040", showgrid=True),
)


# ── Price history chart ───────────────────────────────────────────────────────

def chart_price_history(ticker: str, period: str = "1y") -> go.Figure:
    """
    Line chart of closing price over the selected period.
    period options: 1mo, 3mo, 6mo, 1y, 2y, 5y
    """
    stock = yf.Ticker(ticker)
    hist  = stock.history(period=period)

    if hist.empty:
        fig = go.Figure()
        fig.add_annotation(text="No price data available", showarrow=False)
        return fig

    colour = COLOURS["green"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist.index,
        y=hist["Close"],
        mode="lines",
        name="Price",
        line=dict(color=colour, width=2),
        fill="tozeroy",
        fillcolor="rgba(0, 196, 140, 0.1)",
    ))

    fig.update_layout(
        **BASE_LAYOUT,
        title=dict(text=f"{ticker.upper()} — Price History ({period})", font=dict(size=16)),
        xaxis_title="",
        yaxis_title="Price (USD)",
        hovermode="x unified",
        showlegend=False,
    )

    return fig


# ── Factor scores bar chart ───────────────────────────────────────────────────

def chart_factor_scores(scores: dict, signal: str, name: str) -> go.Figure:
    """
    Horizontal bar chart of the 5 factor scores.
    scores: dict with keys growth, profitability, valuation, health, momentum
    """
    factors = ["Momentum", "Health", "Valuation", "Profitability", "Growth"]
    keys    = ["momentum", "health", "valuation", "profitability", "growth"]
    values  = [scores.get(k) or 0 for k in keys]

    bar_colours = []
    for v in values:
        if v >= 4.0:
            bar_colours.append(COLOURS["green"])
        elif v >= 3.0:
            bar_colours.append(COLOURS["blue"])
        elif v >= 2.0:
            bar_colours.append(COLOURS["orange"])
        else:
            bar_colours.append(COLOURS["red"])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=values,
        y=factors,
        orientation="h",
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


# ── Margins over time chart ───────────────────────────────────────────────────

def chart_margins(ticker: str) -> go.Figure:
    """
    Line chart of gross, operating, and net margins over the last 4 annual periods.
    """
    stock      = yf.Ticker(ticker)
    financials = stock.financials  # columns = annual periods

    if financials is None or financials.empty:
        fig = go.Figure()
        fig.add_annotation(text="No financials data available", showarrow=False)
        return fig

    cols = sorted(financials.columns, reverse=False)

    def get_margin(numerator_key, denominator_key="Total Revenue"):
        try:
            num = financials.loc[numerator_key, cols]
            den = financials.loc[denominator_key, cols]
            return (num / den * 100).round(1)
        except KeyError:
            return None

    gross_margin   = get_margin("Gross Profit")
    operating_margin = get_margin("Operating Income")
    net_margin     = get_margin("Net Income")

    fig = go.Figure()

    if gross_margin is not None:
        fig.add_trace(go.Scatter(
            x=cols, y=gross_margin.values,
            name="Gross Margin", mode="lines+markers",
            line=dict(color=COLOURS["green"], width=2),
        ))

    if operating_margin is not None:
        fig.add_trace(go.Scatter(
            x=cols, y=operating_margin.values,
            name="Operating Margin", mode="lines+markers",
            line=dict(color=COLOURS["blue"], width=2),
        ))

    if net_margin is not None:
        fig.add_trace(go.Scatter(
            x=cols, y=net_margin.values,
            name="Net Margin", mode="lines+markers",
            line=dict(color=COLOURS["orange"], width=2),
        ))

    fig.update_layout(
        **BASE_LAYOUT,
        title=dict(text=f"{ticker.upper()} — Margins Over Time (%)", font=dict(size=16)),
        xaxis_title="",
        yaxis_title="Margin (%)",
        hovermode="x unified",
        legend=dict(
            bgcolor=COLOURS["surface"],
            bordercolor="#2A3040",
            borderwidth=1,
        ),
    )

    return fig


# ── Revenue & earnings chart ──────────────────────────────────────────────────

def chart_revenue_earnings(ticker: str) -> go.Figure:
    """
    Grouped bar chart of annual revenue and net income.
    """
    stock      = yf.Ticker(ticker)
    financials = stock.financials

    if financials is None or financials.empty:
        fig = go.Figure()
        fig.add_annotation(text="No financials data available", showarrow=False)
        return fig

    cols = sorted(financials.columns, reverse=False)

    try:
        revenue    = financials.loc["Total Revenue", cols] / 1e9
        net_income = financials.loc["Net Income", cols] / 1e9
    except KeyError:
        fig = go.Figure()
        fig.add_annotation(text="Revenue data unavailable", showarrow=False)
        return fig

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=cols, y=revenue.values,
        name="Revenue ($B)",
        marker_color=COLOURS["blue"],
    ))

    fig.add_trace(go.Bar(
        x=cols, y=net_income.values,
        name="Net Income ($B)",
        marker_color=COLOURS["green"],
    ))

    fig.update_layout(
        **BASE_LAYOUT,
        title=dict(text=f"{ticker.upper()} — Revenue & Net Income ($B)", font=dict(size=16)),
        xaxis_title="",
        yaxis_title="USD Billions",
        barmode="group",
        hovermode="x unified",
        legend=dict(
            bgcolor=COLOURS["surface"],
            bordercolor="#2A3040",
            borderwidth=1,
        ),
    )

    return fig


# ── Quick test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from scoring.scorer import score_company

    ticker = "AAPL"
    result = score_company(ticker)

    print(f"Generating charts for {ticker}...")

    fig1 = chart_price_history(ticker, "1y")
    fig2 = chart_factor_scores(result["scores"], result["signal"], result["name"])
    fig3 = chart_margins(ticker)
    fig4 = chart_revenue_earnings(ticker)

    fig1.show()
    fig2.show()
    fig3.show()
    fig4.show()

    print("Done — 4 charts opened in your browser.")

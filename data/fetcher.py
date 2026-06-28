import os
import requests
from dotenv import load_dotenv

load_dotenv()

FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")
FINNHUB_BASE = "https://finnhub.io/api/v1"


def fh_get(endpoint, params={}):
    try:
        params["token"] = FINNHUB_KEY
        r = requests.get(f"{FINNHUB_BASE}/{endpoint}", params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data if data else None
    except Exception:
        return None


def get_fundamentals(ticker):
    ticker = ticker.upper()

    profile  = fh_get("stock/profile2", {"symbol": ticker}) or {}
    metrics  = fh_get("stock/metric",   {"symbol": ticker, "metric": "all"}) or {}
    quote    = fh_get("quote",          {"symbol": ticker}) or {}

    m = metrics.get("metric", {})

    def g(source, *keys):
        for key in keys:
            val = source.get(key)
            if val is not None and val != 0:
                return val
        return None

    def to_decimal(val):
        if val is None:
            return None
        return val / 100 if abs(val) > 1 else val

    name     = g(profile, "name")
    sector   = g(profile, "finnhubIndustry")
    industry = g(profile, "finnhubIndustry")
    country  = g(profile, "country")
    currency = g(profile, "currency") or "USD"
    exchange = g(profile, "exchange")

    current_price = g(quote, "c")
    market_cap    = profile.get("marketCapitalization")
    if market_cap:
        market_cap = market_cap * 1_000_000

    week_52_high = g(m, "52WeekHigh")
    week_52_low  = g(m, "52WeekLow")
    avg_volume   = g(m, "3MonthAverageTradingVolume")

    if week_52_high and week_52_low and current_price:
        price_range = week_52_high - week_52_low
        week_52_position = (current_price - week_52_low) / price_range if price_range > 0 else None
    else:
        week_52_position = None

    pe_trailing = g(m, "peExclExtraTTM", "peTTM")
    pe_forward  = g(m, "peNormalizedAnnual")
    pb_ratio    = g(m, "pbAnnual", "pbQuarterly")
    ps_ratio    = g(m, "psTTM", "psAnnual")
    ev_ebitda   = g(m, "evEbitdaTTM", "evEbitdaAnnual")
    peg_ratio   = g(m, "pegyrFwdEpsGrowth5Y")

    gross_margin     = to_decimal(g(m, "grossMarginTTM", "grossMarginAnnual"))
    operating_margin = to_decimal(g(m, "operatingMarginTTM", "operatingMarginAnnual"))
    net_margin       = to_decimal(g(m, "netProfitMarginTTM", "netProfitMarginAnnual"))
    roe              = to_decimal(g(m, "roeTTM", "roeAnnual"))
    roa              = to_decimal(g(m, "roaTTM", "roaAnnual"))

    revenue_growth  = to_decimal(g(m, "revenueGrowthTTMYoy", "revenueGrowth5Y"))
    earnings_growth = to_decimal(g(m, "epsGrowthTTMYoy", "epsGrowth5Y"))
    revenue_ttm     = g(m, "revenueTTM", "revenueAnnual")
    earnings_ttm    = g(m, "epsTTM", "epsAnnual")

    debt_to_equity = g(m, "totalDebt/totalEquityAnnual", "totalDebt/totalEquityQuarterly")
    current_ratio  = g(m, "currentRatioAnnual", "currentRatioQuarterly")
    quick_ratio    = g(m, "quickRatioAnnual", "quickRatioQuarterly")
    free_cash_flow = g(m, "freeCashFlowTTM", "freeCashFlowAnnual")
    if free_cash_flow:
        free_cash_flow = free_cash_flow * 1_000_000
    total_cash = g(m, "cashAndEquivalentsAnnual")
    if total_cash:
        total_cash = total_cash * 1_000_000
    total_debt     = g(m, "longTermDebt/equityAnnual")
    dividend_yield = to_decimal(g(m, "dividendYieldIndicatedAnnual"))
    payout_ratio   = to_decimal(g(m, "payoutRatioAnnual"))
    analyst_target = g(m, "targetPrice")

    return {
        "ticker": ticker, "name": name, "sector": sector,
        "industry": industry, "country": country, "currency": currency,
        "exchange": exchange, "current_price": current_price,
        "market_cap": market_cap, "week_52_high": week_52_high,
        "week_52_low": week_52_low, "week_52_position": week_52_position,
        "avg_volume": avg_volume, "pe_trailing": pe_trailing,
        "pe_forward": pe_forward, "pb_ratio": pb_ratio,
        "ps_ratio": ps_ratio, "ev_ebitda": ev_ebitda,
        "peg_ratio": peg_ratio, "gross_margin": gross_margin,
        "operating_margin": operating_margin, "net_margin": net_margin,
        "roe": roe, "roa": roa, "revenue_growth": revenue_growth,
        "earnings_growth": earnings_growth, "revenue_ttm": revenue_ttm,
        "earnings_ttm": earnings_ttm, "debt_to_equity": debt_to_equity,
        "current_ratio": current_ratio, "quick_ratio": quick_ratio,
        "free_cash_flow": free_cash_flow, "total_cash": total_cash,
        "total_debt": total_debt, "dividend_yield": dividend_yield,
        "payout_ratio": payout_ratio, "analyst_target": analyst_target,
        "recommendation": None,
    }


def print_fundamentals(ticker):
    data = get_fundamentals(ticker)

    def fmt_pct(val): return f"{val*100:.1f}%" if val is not None else "N/A"
    def fmt_num(val, dp=2): return f"{val:.{dp}f}" if val is not None else "N/A"
    def fmt_large(val):
        if val is None: return "N/A"
        if abs(val) >= 1_000_000_000: return f"${val/1_000_000_000:.1f}B"
        if abs(val) >= 1_000_000: return f"${val/1_000_000:.1f}M"
        return f"${val:,.0f}"

    print(f"\n{'='*50}")
    print(f"  {data['name']} ({data['ticker']})")
    print(f"  {data['sector']}")
    print(f"{'='*50}")
    print(f"\n  Current Price:    {fmt_large(data['current_price'])}")
    print(f"  Market Cap:       {fmt_large(data['market_cap'])}")
    print(f"  52W Position:     {fmt_pct(data['week_52_position'])}")
    print(f"  P/E (Trailing):   {fmt_num(data['pe_trailing'])}")
    print(f"  Gross Margin:     {fmt_pct(data['gross_margin'])}")
    print(f"  Net Margin:       {fmt_pct(data['net_margin'])}")
    print(f"  ROE:              {fmt_pct(data['roe'])}")
    print(f"  Revenue Growth:   {fmt_pct(data['revenue_growth'])}")
    print(f"  Debt/Equity:      {fmt_num(data['debt_to_equity'])}")
    print(f"  Current Ratio:    {fmt_num(data['current_ratio'])}")
    print(f"  Free Cash Flow:   {fmt_large(data['free_cash_flow'])}")
    print()


if __name__ == "__main__":
    print_fundamentals("AAPL")
    print_fundamentals("TSLA")

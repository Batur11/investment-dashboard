import yfinance as yf


def get_fundamentals(ticker: str) -> dict:
    """
    Fetch key financial metrics for a given ticker symbol.
    Returns a dictionary of metrics, with None for any unavailable values.
    """

    stock = yf.Ticker(ticker)
    info = stock.info

    # --- Helper to safely pull values ---
    def get(key, default=None):
        val = info.get(key, default)
        # yfinance sometimes returns 'Infinity' or 0 for missing data
        if val in [float('inf'), float('-inf')]:
            return None
        return val

    # --- Identity ---
    name        = get("shortName") or get("longName")
    sector      = get("sector")
    industry    = get("industry")
    country     = get("country")
    currency    = get("currency", "USD")
    exchange    = get("exchange")

    # --- Price & Size ---
    current_price   = get("currentPrice") or get("regularMarketPrice")
    market_cap      = get("marketCap")
    week_52_high    = get("fiftyTwoWeekHigh")
    week_52_low     = get("fiftyTwoWeekLow")
    avg_volume      = get("averageVolume")

    # --- Valuation ---
    pe_trailing     = get("trailingPE")
    pe_forward      = get("forwardPE")
    pb_ratio        = get("priceToBook")
    ps_ratio        = get("priceToSalesTrailing12Months")
    ev_ebitda       = get("enterpriseToEbitda")
    peg_ratio       = get("pegRatio")

    # --- Profitability ---
    gross_margin    = get("grossMargins")
    operating_margin = get("operatingMargins")
    net_margin      = get("profitMargins")
    roe             = get("returnOnEquity")
    roa             = get("returnOnAssets")

    # --- Growth ---
    revenue_growth  = get("revenueGrowth")       # YoY
    earnings_growth = get("earningsGrowth")       # YoY
    revenue_ttm     = get("totalRevenue")
    earnings_ttm    = get("netIncomeToCommon")

    # --- Financial Health ---
    debt_to_equity  = get("debtToEquity")
    current_ratio   = get("currentRatio")
    quick_ratio     = get("quickRatio")
    free_cash_flow  = get("freeCashflow")
    total_cash      = get("totalCash")
    total_debt      = get("totalDebt")

    # --- Dividends ---
    dividend_yield  = get("dividendYield")
    payout_ratio    = get("payoutRatio")

    # --- Analyst Sentiment ---
    analyst_target  = get("targetMeanPrice")
    recommendation  = get("recommendationKey")   # e.g. "buy", "hold", "sell"

    # --- 52-week position (0 = at low, 1 = at high) ---
    if week_52_high and week_52_low and current_price:
        price_range = week_52_high - week_52_low
        week_52_position = (current_price - week_52_low) / price_range if price_range > 0 else None
    else:
        week_52_position = None

    return {
        # Identity
        "ticker":               ticker.upper(),
        "name":                 name,
        "sector":               sector,
        "industry":             industry,
        "country":              country,
        "currency":             currency,
        "exchange":             exchange,

        # Price & Size
        "current_price":        current_price,
        "market_cap":           market_cap,
        "week_52_high":         week_52_high,
        "week_52_low":          week_52_low,
        "week_52_position":     week_52_position,
        "avg_volume":           avg_volume,

        # Valuation
        "pe_trailing":          pe_trailing,
        "pe_forward":           pe_forward,
        "pb_ratio":             pb_ratio,
        "ps_ratio":             ps_ratio,
        "ev_ebitda":            ev_ebitda,
        "peg_ratio":            peg_ratio,

        # Profitability
        "gross_margin":         gross_margin,
        "operating_margin":     operating_margin,
        "net_margin":           net_margin,
        "roe":                  roe,
        "roa":                  roa,

        # Growth
        "revenue_growth":       revenue_growth,
        "earnings_growth":      earnings_growth,
        "revenue_ttm":          revenue_ttm,
        "earnings_ttm":         earnings_ttm,

        # Financial Health
        "debt_to_equity":       debt_to_equity,
        "current_ratio":        current_ratio,
        "quick_ratio":          quick_ratio,
        "free_cash_flow":       free_cash_flow,
        "total_cash":           total_cash,
        "total_debt":           total_debt,

        # Dividends
        "dividend_yield":       dividend_yield,
        "payout_ratio":         payout_ratio,

        # Analyst Sentiment
        "analyst_target":       analyst_target,
        "recommendation":       recommendation,
    }


def print_fundamentals(ticker: str):
    """Fetch and print fundamentals in a readable format."""

    data = get_fundamentals(ticker)

    print(f"\n{'='*50}")
    print(f"  {data['name']} ({data['ticker']})")
    print(f"  {data['sector']} | {data['industry']}")
    print(f"{'='*50}")

    def fmt_pct(val):
        return f"{val*100:.1f}%" if val is not None else "N/A"

    def fmt_num(val, dp=2):
        return f"{val:.{dp}f}" if val is not None else "N/A"

    def fmt_large(val):
        if val is None:
            return "N/A"
        if abs(val) >= 1_000_000_000:
            return f"${val/1_000_000_000:.1f}B"
        if abs(val) >= 1_000_000:
            return f"${val/1_000_000:.1f}M"
        return f"${val:,.0f}"

    print(f"\n  PRICE & SIZE")
    print(f"  Current Price:      {fmt_large(data['current_price'])}")
    print(f"  Market Cap:         {fmt_large(data['market_cap'])}")
    print(f"  52W High:           {fmt_large(data['week_52_high'])}")
    print(f"  52W Low:            {fmt_large(data['week_52_low'])}")
    print(f"  52W Position:       {fmt_pct(data['week_52_position'])}")

    print(f"\n  VALUATION")
    print(f"  P/E (Trailing):     {fmt_num(data['pe_trailing'])}")
    print(f"  P/E (Forward):      {fmt_num(data['pe_forward'])}")
    print(f"  P/B Ratio:          {fmt_num(data['pb_ratio'])}")
    print(f"  P/S Ratio:          {fmt_num(data['ps_ratio'])}")
    print(f"  EV/EBITDA:          {fmt_num(data['ev_ebitda'])}")

    print(f"\n  PROFITABILITY")
    print(f"  Gross Margin:       {fmt_pct(data['gross_margin'])}")
    print(f"  Operating Margin:   {fmt_pct(data['operating_margin'])}")
    print(f"  Net Margin:         {fmt_pct(data['net_margin'])}")
    print(f"  ROE:                {fmt_pct(data['roe'])}")
    print(f"  ROA:                {fmt_pct(data['roa'])}")

    print(f"\n  GROWTH")
    print(f"  Revenue Growth:     {fmt_pct(data['revenue_growth'])}")
    print(f"  Earnings Growth:    {fmt_pct(data['earnings_growth'])}")
    print(f"  Revenue (TTM):      {fmt_large(data['revenue_ttm'])}")

    print(f"\n  FINANCIAL HEALTH")
    print(f"  Debt/Equity:        {fmt_num(data['debt_to_equity'])}")
    print(f"  Current Ratio:      {fmt_num(data['current_ratio'])}")
    print(f"  Free Cash Flow:     {fmt_large(data['free_cash_flow'])}")
    print(f"  Total Cash:         {fmt_large(data['total_cash'])}")
    print(f"  Total Debt:         {fmt_large(data['total_debt'])}")

    print(f"\n  ANALYST SENTIMENT")
    print(f"  Recommendation:     {data['recommendation'] or 'N/A'}")
    print(f"  Target Price:       {fmt_large(data['analyst_target'])}")
    print()



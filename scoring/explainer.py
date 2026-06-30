from scoring.scorer import score_company


def fmt_pct(val):
    return "N/A" if val is None else f"{val*100:.1f}%"

def fmt_num(val, dp=1):
    return "N/A" if val is None else f"{val:.{dp}f}"

def fmt_large(val):
    if val is None: return "N/A"
    if abs(val) >= 1_000_000_000: return f"${val/1_000_000_000:.1f}B"
    if abs(val) >= 1_000_000: return f"${val/1_000_000:.1f}M"
    return f"${val:,.0f}"

def score_label(score):
    if score is None: return "N/A"
    if score >= 4.5: return "Excellent"
    if score >= 3.5: return "Good"
    if score >= 2.5: return "Average"
    if score >= 1.5: return "Weak"
    return "Poor"


def explain_growth(data, factor):
    score = factor["score"]
    rev, earn = data.get("revenue_growth"), data.get("earnings_growth")
    label = score_label(score)
    if score is None:
        return "Growth data is unavailable."
    parts = []
    if rev is not None:
        if rev >= 0.15: parts.append(f"strong revenue growth of {fmt_pct(rev)}")
        elif rev >= 0.05: parts.append(f"moderate revenue growth of {fmt_pct(rev)}")
        elif rev >= 0: parts.append(f"slow revenue growth of {fmt_pct(rev)}")
        else: parts.append(f"revenue decline of {fmt_pct(rev)}")
    if earn is not None:
        if earn >= 0.20: parts.append(f"strong earnings growth of {fmt_pct(earn)}")
        elif earn >= 0.05: parts.append(f"moderate earnings growth of {fmt_pct(earn)}")
        elif earn >= 0: parts.append(f"slow earnings growth of {fmt_pct(earn)}")
        else: parts.append(f"earnings decline of {fmt_pct(earn)}")
    description = " and ".join(parts) if parts else "limited growth data available"
    return f"{label} — {description}."


def explain_profitability(data, factor):
    score = factor["score"]
    gm, nm, roe = data.get("gross_margin"), data.get("net_margin"), data.get("roe")
    label = score_label(score)
    if score is None:
        return "Profitability data is unavailable."
    parts = []
    if gm is not None: parts.append(f"gross margin of {fmt_pct(gm)}")
    if nm is not None:
        if nm >= 0.20: parts.append(f"an excellent net margin of {fmt_pct(nm)}")
        elif nm >= 0.10: parts.append(f"a healthy net margin of {fmt_pct(nm)}")
        elif nm >= 0.05: parts.append(f"a thin net margin of {fmt_pct(nm)}")
        else: parts.append(f"a very thin net margin of {fmt_pct(nm)}")
    if roe is not None:
        if roe >= 0.25: parts.append(f"exceptional return on equity of {fmt_pct(roe)}")
        elif roe >= 0.15: parts.append(f"strong return on equity of {fmt_pct(roe)}")
        elif roe >= 0.08: parts.append(f"moderate return on equity of {fmt_pct(roe)}")
        else: parts.append(f"low return on equity of {fmt_pct(roe)}")
    description = ", ".join(parts) if parts else "limited profitability data"
    return f"{label} — {description}."


def explain_valuation(data, factor):
    score = factor["score"]
    pe, pb, ps = data.get("pe_trailing"), data.get("pb_ratio"), data.get("ps_ratio")
    label = score_label(score)
    if score is None:
        return "Valuation data is unavailable."
    parts = []
    if pe is not None:
        if pe < 15: parts.append(f"an attractive P/E of {fmt_num(pe)}")
        elif pe < 25: parts.append(f"a reasonable P/E of {fmt_num(pe)}")
        elif pe < 40: parts.append(f"an elevated P/E of {fmt_num(pe)}")
        else: parts.append(f"a very high P/E of {fmt_num(pe)}")
    if pb is not None:
        if pb < 2: parts.append(f"low P/B of {fmt_num(pb)}")
        elif pb < 5: parts.append(f"moderate P/B of {fmt_num(pb)}")
        else: parts.append(f"high P/B of {fmt_num(pb)}")
    if ps is not None:
        if ps < 2: parts.append(f"low P/S of {fmt_num(ps)}")
        elif ps < 5: parts.append(f"moderate P/S of {fmt_num(ps)}")
        else: parts.append(f"high P/S of {fmt_num(ps)}")
    description = ", ".join(parts) if parts else "limited valuation data"
    suffix = " The market is pricing in significant future growth." if score <= 2 else \
             " The stock appears attractively valued." if score >= 4 else ""
    return f"{label} — {description}.{suffix}"


def explain_health(data, factor):
    score = factor["score"]
    de, cr, fcf = data.get("debt_to_equity"), data.get("current_ratio"), data.get("free_cash_flow")
    label = score_label(score)
    if score is None:
        return "Financial health data is unavailable."
    parts = []
    if de is not None:
        if de < 30: parts.append(f"low debt/equity of {fmt_num(de)}")
        elif de < 80: parts.append(f"moderate debt/equity of {fmt_num(de)}")
        else: parts.append(f"high debt/equity of {fmt_num(de)}")
    if cr is not None:
        if cr >= 2: parts.append(f"strong current ratio of {fmt_num(cr)}")
        elif cr >= 1: parts.append(f"adequate current ratio of {fmt_num(cr)}")
        else: parts.append(f"low current ratio of {fmt_num(cr)} (potential liquidity risk)")
    if fcf is not None:
        parts.append(f"{'positive' if fcf >= 0 else 'negative'} free cash flow of {fmt_large(fcf)}")
    description = ", ".join(parts) if parts else "limited health data"
    return f"{label} — {description}."


def explain_momentum(data, factor):
    score = factor["score"]
    pos = data.get("week_52_position")
    high, low = data.get("week_52_high"), data.get("week_52_low")
    label = score_label(score)
    if score is None or pos is None:
        return "Momentum data is unavailable."
    pct = fmt_pct(pos)
    if pos >= 0.80: direction = "trading near its 52-week high"
    elif pos >= 0.60: direction = "trading in the upper half of its 52-week range"
    elif pos >= 0.40: direction = "trading in the middle of its 52-week range"
    elif pos >= 0.20: direction = "trading in the lower half of its 52-week range"
    else: direction = "trading near its 52-week low"
    return f"{label} — {direction} ({pct} of range, low {fmt_large(low)} / high {fmt_large(high)})."


def explain_company(ticker: str) -> dict:
    result  = score_company(ticker)
    data    = result["data"]
    factors = result["factors"]

    explanations = {
        "growth": explain_growth(data, factors["growth"]),
        "profitability": explain_profitability(data, factors["profitability"]),
        "valuation": explain_valuation(data, factors["valuation"]),
        "health": explain_health(data, factors["health"]),
        "momentum": explain_momentum(data, factors["momentum"]),
    }

    return {
        "ticker": result["ticker"], "name": result["name"], "sector": result["sector"],
        "signal": result["signal"], "overall": result["overall"],
        "scores": result["scores"], "explanations": explanations,
    }

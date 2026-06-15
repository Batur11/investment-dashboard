from data.fetcher import get_fundamentals


# ── Scoring helpers ───────────────────────────────────────────────────────────

def score_between(value, thresholds: list) -> int:
    """
    Given a value and an ascending list of thresholds,
    return a score from 1 (worst) to 5 (best).

    Example: score_between(0.20, [0.05, 0.10, 0.20, 0.30])
    → below 0.05 = 1, below 0.10 = 2, below 0.20 = 3, below 0.30 = 4, above = 5
    """
    if value is None:
        return None
    for i, threshold in enumerate(thresholds):
        if value < threshold:
            return i + 1
    return 5


def score_between_inverted(value, thresholds: list) -> int:
    """
    Same as score_between but inverted — lower value = better score.
    Used for metrics like P/E ratio and Debt/Equity where lower is better.
    """
    if value is None:
        return None
    score = score_between(value, thresholds)
    return 6 - score  # invert: 1→5, 2→4, 3→3, 4→2, 5→1


def average(scores: list) -> float:
    """Average a list of scores, ignoring None values."""
    valid = [s for s in scores if s is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)


# ── Individual factor scoring ─────────────────────────────────────────────────

def score_growth(data: dict) -> dict:
    """
    Score company growth based on revenue and earnings growth (YoY).
    Higher growth = higher score.
    """
    rev = score_between(data.get("revenue_growth"), [-0.05, 0.0, 0.08, 0.15])
    # below -5%=1, below 0%=2, below 8%=3, below 15%=4, above 15%=5

    earn = score_between(data.get("earnings_growth"), [-0.10, 0.0, 0.08, 0.20])
    # below -10%=1, below 0%=2, below 8%=3, below 20%=4, above 20%=5

    score = average([rev, earn])

    return {
        "score": score,
        "components": {
            "revenue_growth": rev,
            "earnings_growth": earn,
        }
    }


def score_profitability(data: dict) -> dict:
    """
    Score profitability based on margins and returns.
    Higher margins and returns = higher score.
    """
    gm  = score_between(data.get("gross_margin"),    [0.10, 0.20, 0.35, 0.50])
    nm  = score_between(data.get("net_margin"),      [0.00, 0.05, 0.10, 0.20])
    roe = score_between(data.get("roe"),             [0.00, 0.08, 0.15, 0.25])

    score = average([gm, nm, roe])

    return {
        "score": score,
        "components": {
            "gross_margin": gm,
            "net_margin": nm,
            "roe": roe,
        }
    }


def score_valuation(data: dict) -> dict:
    """
    Score valuation based on P/E, P/B, and P/S ratios.
    Lower ratios = better value = higher score.
    """
    pe = score_between_inverted(data.get("pe_trailing"), [15, 20, 30, 50])
    # above 50=1, above 30=2, above 20=3, above 15=4, below 15=5

    pb = score_between_inverted(data.get("pb_ratio"), [1, 2, 4, 8])
    ps = score_between_inverted(data.get("ps_ratio"), [1, 2, 5, 10])

    score = average([pe, pb, ps])

    return {
        "score": score,
        "components": {
            "pe_trailing": pe,
            "pb_ratio": pb,
            "ps_ratio": ps,
        }
    }


def score_financial_health(data: dict) -> dict:
    """
    Score financial health based on debt, liquidity, and cash flow.
    """
    # Debt/Equity — lower is better
    de = score_between_inverted(data.get("debt_to_equity"), [20, 50, 100, 200])

    # Current ratio — higher is better (ability to cover short-term debts)
    cr = score_between(data.get("current_ratio"), [0.5, 1.0, 1.5, 2.5])

    # Free cash flow — positive and large is better
    fcf_raw = data.get("free_cash_flow")
    if fcf_raw is None:
        fcf = None
    elif fcf_raw < 0:
        fcf = 1
    elif fcf_raw < 500_000_000:       # under $500M
        fcf = 2
    elif fcf_raw < 2_000_000_000:     # under $2B
        fcf = 3
    elif fcf_raw < 10_000_000_000:    # under $10B
        fcf = 4
    else:
        fcf = 5

    score = average([de, cr, fcf])

    return {
        "score": score,
        "components": {
            "debt_to_equity": de,
            "current_ratio": cr,
            "free_cash_flow": fcf,
        }
    }


def score_momentum(data: dict) -> dict:
    """
    Score momentum based on 52-week price position.
    Position closer to high = stronger momentum.
    """
    pos = data.get("week_52_position")

    mom = score_between(pos, [0.20, 0.40, 0.60, 0.80])

    return {
        "score": mom,
        "components": {
            "week_52_position": mom,
        }
    }


# ── Signal label ──────────────────────────────────────────────────────────────

def signal_label(overall_score: float) -> str:
    if overall_score is None:
        return "Insufficient Data"
    if overall_score >= 4.0:
        return "Strong Watch"
    if overall_score >= 3.0:
        return "Watch"
    if overall_score >= 2.0:
        return "Neutral"
    if overall_score >= 1.0:
        return "Avoid for Now"
    return "High Risk"


# ── Main scoring function ─────────────────────────────────────────────────────

def score_company(ticker: str) -> dict:
    """
    Full pipeline: fetch data → score each factor → return complete result.
    """
    data = get_fundamentals(ticker)

    growth       = score_growth(data)
    profitability = score_profitability(data)
    valuation    = score_valuation(data)
    health       = score_financial_health(data)
    momentum     = score_momentum(data)

    # Equal weights for now — can be adjusted later
    weights = {
        "growth":        0.25,
        "profitability": 0.25,
        "valuation":     0.20,
        "health":        0.20,
        "momentum":      0.10,
    }

    scores = {
        "growth":        growth["score"],
        "profitability": profitability["score"],
        "valuation":     valuation["score"],
        "health":        health["score"],
        "momentum":      momentum["score"],
    }

    # Weighted overall score
    weighted_scores = [
        scores[f] * weights[f]
        for f in weights
        if scores[f] is not None
    ]
    overall = sum(weighted_scores) / sum(
        w for f, w in weights.items() if scores[f] is not None
    ) if weighted_scores else None

    return {
        "ticker":   data["ticker"],
        "name":     data["name"],
        "sector":   data["sector"],
        "signal":   signal_label(overall),
        "overall":  round(overall, 2) if overall else None,
        "scores":   scores,
        "weights":  weights,
        "factors": {
            "growth":        growth,
            "profitability": profitability,
            "valuation":     valuation,
            "health":        health,
            "momentum":      momentum,
        },
        "data": data,
    }


def print_scores(ticker: str):
    """Print a readable scoring breakdown for a ticker."""

    result = score_company(ticker)

    print(f"\n{'='*50}")
    print(f"  {result['name']} ({result['ticker']})")
    print(f"  Sector: {result['sector']}")
    print(f"{'='*50}")

    print(f"\n  FACTOR SCORES  (out of 5)")
    for factor, score in result["scores"].items():
        bar = "█" * int(score) if score else "-"
        score_str = f"{score:.1f}" if score else "N/A"
        print(f"  {factor.capitalize():<16} {score_str}  {bar}")

    print(f"\n  OVERALL SCORE:  {result['overall']} / 5.0")
    print(f"  SIGNAL:         {result['signal']}")
    print()


if __name__ == "__main__":
    print_scores("AAPL")
    print_scores("TSLA")

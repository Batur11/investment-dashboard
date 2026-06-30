from data.fetcher import get_fundamentals


def score_between(value, thresholds: list) -> int:
    if value is None:
        return None
    for i, threshold in enumerate(thresholds):
        if value < threshold:
            return i + 1
    return 5


def score_between_inverted(value, thresholds: list) -> int:
    if value is None:
        return None
    score = score_between(value, thresholds)
    return 6 - score


def average(scores: list):
    valid = [s for s in scores if s is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)


def score_growth(data: dict) -> dict:
    rev  = score_between(data.get("revenue_growth"), [-0.05, 0.0, 0.08, 0.15])
    earn = score_between(data.get("earnings_growth"), [-0.10, 0.0, 0.08, 0.20])
    score = average([rev, earn])
    return {"score": score, "components": {"revenue_growth": rev, "earnings_growth": earn}}


def score_profitability(data: dict) -> dict:
    gm  = score_between(data.get("gross_margin"), [0.10, 0.20, 0.35, 0.50])
    nm  = score_between(data.get("net_margin"),   [0.00, 0.05, 0.10, 0.20])
    roe = score_between(data.get("roe"),           [0.00, 0.08, 0.15, 0.25])
    score = average([gm, nm, roe])
    return {"score": score, "components": {"gross_margin": gm, "net_margin": nm, "roe": roe}}


def score_valuation(data: dict) -> dict:
    pe = score_between_inverted(data.get("pe_trailing"), [15, 20, 30, 50])
    pb = score_between_inverted(data.get("pb_ratio"), [1, 2, 4, 8])
    ps = score_between_inverted(data.get("ps_ratio"), [1, 2, 5, 10])
    score = average([pe, pb, ps])
    return {"score": score, "components": {"pe_trailing": pe, "pb_ratio": pb, "ps_ratio": ps}}


def score_financial_health(data: dict) -> dict:
    de = score_between_inverted(data.get("debt_to_equity"), [20, 50, 100, 200])
    cr = score_between(data.get("current_ratio"), [0.5, 1.0, 1.5, 2.5])

    fcf_raw = data.get("free_cash_flow")
    if fcf_raw is None:
        fcf = None
    elif fcf_raw < 0:
        fcf = 1
    elif fcf_raw < 500_000_000:
        fcf = 2
    elif fcf_raw < 2_000_000_000:
        fcf = 3
    elif fcf_raw < 10_000_000_000:
        fcf = 4
    else:
        fcf = 5

    score = average([de, cr, fcf])
    return {"score": score, "components": {"debt_to_equity": de, "current_ratio": cr, "free_cash_flow": fcf}}


def score_momentum(data: dict) -> dict:
    pos = data.get("week_52_position")
    mom = score_between(pos, [0.20, 0.40, 0.60, 0.80])
    return {"score": mom, "components": {"week_52_position": mom}}


def signal_label(overall_score) -> str:
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


def score_company(ticker: str) -> dict:
    data = get_fundamentals(ticker)

    growth        = score_growth(data)
    profitability = score_profitability(data)
    valuation     = score_valuation(data)
    health        = score_financial_health(data)
    momentum      = score_momentum(data)

    weights = {
        "growth": 0.25, "profitability": 0.25,
        "valuation": 0.20, "health": 0.20, "momentum": 0.10,
    }

    scores = {
        "growth": growth["score"], "profitability": profitability["score"],
        "valuation": valuation["score"], "health": health["score"],
        "momentum": momentum["score"],
    }

    weighted_scores = [scores[f] * weights[f] for f in weights if scores[f] is not None]
    overall = sum(weighted_scores) / sum(
        w for f, w in weights.items() if scores[f] is not None
    ) if weighted_scores else None

    return {
        "ticker": data["ticker"], "name": data["name"], "sector": data["sector"],
        "signal": signal_label(overall),
        "overall": round(overall, 2) if overall else None,
        "scores": scores, "weights": weights,
        "factors": {
            "growth": growth, "profitability": profitability,
            "valuation": valuation, "health": health, "momentum": momentum,
        },
        "data": data,
    }

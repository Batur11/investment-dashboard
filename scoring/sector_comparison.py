import os
import requests
from dotenv import load_dotenv
from data.fetcher import get_fundamentals

load_dotenv()

FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")
FINNHUB_BASE = "https://finnhub.io/api/v1"


def get_peers(ticker: str, max_peers: int = 6) -> list:
    """Fetch peer/competitor tickers for a given company."""
    try:
        r = requests.get(f"{FINNHUB_BASE}/stock/peers",
                         params={"symbol": ticker.upper(), "token": FINNHUB_KEY}, timeout=10)
        r.raise_for_status()
        peers = r.json() or []
        # Remove the company itself, keep up to max_peers
        peers = [p for p in peers if p.upper() != ticker.upper()]
        return peers[:max_peers]
    except Exception:
        return []


def average(values: list):
    valid = [v for v in values if v is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)


def get_sector_comparison(ticker: str) -> dict:
    """
    Build a sector comparison: target company vs average of its peers
    across the key metrics that drive the scoring model.
    """
    ticker = ticker.upper()
    target_data = get_fundamentals(ticker)
    peers = get_peers(ticker)

    peer_data = []
    for p in peers:
        try:
            d = get_fundamentals(p)
            if d.get("name"):  # only keep peers with valid data
                peer_data.append(d)
        except Exception:
            continue

    metrics = [
        ("pe_trailing",     "P/E Ratio",        "lower_better", "x"),
        ("pb_ratio",        "P/B Ratio",        "lower_better", "x"),
        ("gross_margin",    "Gross Margin",     "higher_better", "%"),
        ("net_margin",      "Net Margin",       "higher_better", "%"),
        ("roe",             "Return on Equity", "higher_better", "%"),
        ("revenue_growth",  "Revenue Growth",   "higher_better", "%"),
        ("debt_to_equity",  "Debt/Equity",      "lower_better", "x"),
        ("current_ratio",   "Current Ratio",    "higher_better", "x"),
    ]

    comparison = []
    for key, label, direction, unit in metrics:
        target_val = target_data.get(key)
        peer_vals  = [p.get(key) for p in peer_data]
        peer_avg   = average(peer_vals)

        verdict = None
        if target_val is not None and peer_avg is not None and peer_avg != 0:
            diff_pct = ((target_val - peer_avg) / abs(peer_avg)) * 100
            is_better = (diff_pct > 0) if direction == "higher_better" else (diff_pct < 0)
            verdict = {
                "diff_pct": diff_pct,
                "is_better": is_better,
            }

        comparison.append({
            "key": key,
            "label": label,
            "unit": unit,
            "direction": direction,
            "target_value": target_val,
            "peer_average": peer_avg,
            "verdict": verdict,
        })

    return {
        "ticker": ticker,
        "name": target_data.get("name"),
        "sector": target_data.get("sector"),
        "peers": [p.get("ticker") for p in peer_data],
        "peer_count": len(peer_data),
        "comparison": comparison,
    }

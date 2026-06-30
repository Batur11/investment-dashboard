import os
import datetime
import anthropic
import requests
from dotenv import load_dotenv

load_dotenv()

FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")
FINNHUB_BASE = "https://finnhub.io/api/v1"


def get_recent_news(ticker: str, days: int = 10, limit: int = 8) -> list:
    """Fetch recent news headlines for a ticker."""
    today = datetime.date.today()
    from_date = today - datetime.timedelta(days=days)

    try:
        r = requests.get(f"{FINNHUB_BASE}/company-news", params={
            "symbol": ticker.upper(),
            "from": from_date.isoformat(),
            "to": today.isoformat(),
            "token": FINNHUB_KEY,
        }, timeout=10)
        r.raise_for_status()
        articles = r.json() or []

        # Deduplicate by headline, keep most recent first
        seen = set()
        unique = []
        for a in sorted(articles, key=lambda x: x.get("datetime", 0), reverse=True):
            headline = a.get("headline", "").strip()
            if headline and headline not in seen:
                seen.add(headline)
                unique.append({
                    "headline": headline,
                    "summary": a.get("summary", ""),
                    "source": a.get("source", ""),
                    "url": a.get("url", ""),
                    "datetime": a.get("datetime", 0),
                })
            if len(unique) >= limit:
                break
        return unique
    except Exception:
        return []


def analyse_sentiment(ticker: str, articles: list) -> dict:
    """
    Use Claude to classify overall sentiment from recent headlines.
    Returns sentiment label, score, and a one-line rationale.
    """
    if not articles:
        return {
            "sentiment": "No Data",
            "score": None,
            "rationale": "No recent news found for this company.",
        }

    headlines_text = "\n".join(f"- {a['headline']}" for a in articles)

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    prompt = f"""You are analysing recent news sentiment for {ticker}.

Here are the {len(articles)} most recent headlines:
{headlines_text}

Classify the overall sentiment as exactly one of: Positive, Slightly Positive, Neutral, Slightly Negative, Negative.

Respond in EXACTLY this format with no extra text:
SENTIMENT: <one of the five labels above>
RATIONALE: <one sentence, under 20 words, explaining why>"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}]
    )

    text = message.content[0].text.strip()

    sentiment = "Neutral"
    rationale = "Unable to determine sentiment from available headlines."

    for line in text.split("\n"):
        if line.startswith("SENTIMENT:"):
            sentiment = line.replace("SENTIMENT:", "").strip()
        elif line.startswith("RATIONALE:"):
            rationale = line.replace("RATIONALE:", "").strip()

    return {
        "sentiment": sentiment,
        "rationale": rationale,
    }


def get_news_sentiment(ticker: str) -> dict:
    """Full pipeline: fetch news, analyse sentiment, return combined result."""
    articles = get_recent_news(ticker)
    sentiment_result = analyse_sentiment(ticker, articles)

    return {
        "ticker": ticker.upper(),
        "articles": articles,
        "sentiment": sentiment_result["sentiment"],
        "rationale": sentiment_result["rationale"],
    }

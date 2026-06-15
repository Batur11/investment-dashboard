import os
import anthropic
from dotenv import load_dotenv

load_dotenv()


def generate_summary(result: dict, data: dict) -> str:
    """
    Generate an AI research summary using Claude.
    Takes the scored/explained result and raw data, returns a plain-English summary.
    """

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Build a structured context string from the data
    def fmt_pct(val):
        return f"{val*100:.1f}%" if val is not None else "N/A"

    def fmt_num(val, dp=1):
        return f"{val:.{dp}f}" if val is not None else "N/A"

    def fmt_large(val):
        if val is None: return "N/A"
        if abs(val) >= 1_000_000_000: return f"${val/1_000_000_000:.1f}B"
        if abs(val) >= 1_000_000: return f"${val/1_000_000:.1f}M"
        return f"${val:,.0f}"

    scores    = result.get("scores", {})
    signal    = result.get("signal", "N/A")
    overall   = result.get("overall", "N/A")
    explanations = result.get("explanations", {})

    context = f"""
COMPANY: {data.get('name')} ({data.get('ticker')})
SECTOR: {data.get('sector')} | {data.get('industry')}

INVESTMENT SIGNAL: {signal} (Overall score: {overall}/5.0)

FACTOR SCORES:
- Growth:        {scores.get('growth', 'N/A')}/5 — {explanations.get('growth', '')}
- Profitability: {scores.get('profitability', 'N/A')}/5 — {explanations.get('profitability', '')}
- Valuation:     {scores.get('valuation', 'N/A')}/5 — {explanations.get('valuation', '')}
- Health:        {scores.get('health', 'N/A')}/5 — {explanations.get('health', '')}
- Momentum:      {scores.get('momentum', 'N/A')}/5 — {explanations.get('momentum', '')}

KEY METRICS:
- Current Price:    {fmt_large(data.get('current_price'))}
- Market Cap:       {fmt_large(data.get('market_cap'))}
- P/E (Trailing):   {fmt_num(data.get('pe_trailing'))}
- P/E (Forward):    {fmt_num(data.get('pe_forward'))}
- Revenue Growth:   {fmt_pct(data.get('revenue_growth'))}
- Earnings Growth:  {fmt_pct(data.get('earnings_growth'))}
- Gross Margin:     {fmt_pct(data.get('gross_margin'))}
- Net Margin:       {fmt_pct(data.get('net_margin'))}
- ROE:              {fmt_pct(data.get('roe'))}
- Debt/Equity:      {fmt_num(data.get('debt_to_equity'))}
- Current Ratio:    {fmt_num(data.get('current_ratio'))}
- Free Cash Flow:   {fmt_large(data.get('free_cash_flow'))}
- Analyst Target:   {fmt_large(data.get('analyst_target'))}
- Recommendation:   {data.get('recommendation', 'N/A')}
"""

    prompt = f"""You are a research analyst writing a concise investment research note. 
You have been given structured financial data and factor scores for a company.

Your job is to write a clear, evidence-based research summary in exactly 3 paragraphs:

Paragraph 1 — Business & Growth: Briefly describe what the company does and assess its growth trajectory based on the data.

Paragraph 2 — Profitability & Financial Health: Assess the quality of the business — margins, returns, balance sheet strength.

Paragraph 3 — Valuation & Overall View: Comment on whether the current valuation is justified given the growth and quality, and summarise the investment signal.

Rules:
- Every claim must be grounded in the data provided. Do not invent facts.
- Be direct and analytical. Avoid vague language.
- Do not give explicit buy/sell advice. Frame everything as research and analysis.
- Write for an intelligent reader who understands basic finance.
- Keep each paragraph to 3-4 sentences.
- Do not use bullet points or headers — flowing prose only.

Here is the data:
{context}

Write the 3-paragraph research summary now. Do not include a title or heading — start directly with the first paragraph:"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text.strip()

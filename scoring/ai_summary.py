import os
import anthropic
from dotenv import load_dotenv

load_dotenv()


def generate_summary(result: dict, data: dict) -> str:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def fmt_pct(val): return f"{val*100:.1f}%" if val is not None else "N/A"
    def fmt_num(val, dp=1): return f"{val:.{dp}f}" if val is not None else "N/A"
    def fmt_large(val):
        if val is None: return "N/A"
        if abs(val) >= 1_000_000_000: return f"${val/1_000_000_000:.1f}B"
        if abs(val) >= 1_000_000: return f"${val/1_000_000:.1f}M"
        return f"${val:,.0f}"

    scores  = result.get("scores", {})
    signal  = result.get("signal", "N/A")
    overall = result.get("overall", "N/A")
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
- Revenue Growth:   {fmt_pct(data.get('revenue_growth'))}
- Gross Margin:     {fmt_pct(data.get('gross_margin'))}
- Net Margin:       {fmt_pct(data.get('net_margin'))}
- ROE:              {fmt_pct(data.get('roe'))}
- Debt/Equity:      {fmt_num(data.get('debt_to_equity'))}
- Free Cash Flow:   {fmt_large(data.get('free_cash_flow'))}
"""

    prompt = f"""You are a research analyst writing a concise investment research note.
You have been given structured financial data and factor scores for a company.

Write a clear, evidence-based research summary in exactly 3 paragraphs:

Paragraph 1 — Business & Growth: Briefly describe the company and assess growth trajectory.
Paragraph 2 — Profitability & Financial Health: Assess margins, returns, balance sheet strength.
Paragraph 3 — Valuation & Overall View: Comment on whether valuation is justified given growth and quality.

Rules:
- Every claim must be grounded in the data provided. Do not invent facts.
- Do not give explicit buy/sell advice. Frame everything as research and analysis.
- Keep each paragraph to 3-4 sentences.
- No bullet points or headers — flowing prose only.

Data:
{context}

Write the 3-paragraph research summary now. Do not include a title or heading — start directly with the first paragraph:"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text.strip()

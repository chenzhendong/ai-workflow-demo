# PydanticAI + Gemini — Portfolio Analysis

An AI-powered investment portfolio analyzer built with **PydanticAI** and **Google Gemini**. Give it a list of your stock positions and it will:

1. Fetch real market data (free, no extra API key)
2. Compute financial metrics: Annualized Return, Max Drawdown, Beta, Alpha, Volatility
3. Have Gemini analyze the numbers and write a professional investment report
4. Export everything to a formatted PDF

---

## Quick Start

### Step 1 — Prerequisites

You need **Python 3.10 or later** and **uv** (a fast Python package manager).

Check if you already have them:
```bash
python --version   # should show 3.10 or higher
uv --version
```

If `uv` is not installed, run:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Then restart your terminal.

---

### Step 2 — Get the code

```bash
git clone https://github.com/chenzhendong/ai-workflow-demo.git
cd ai-workflow-demo
```

---

### Step 3 — Install dependencies

```bash
uv venv
uv sync
```

This creates a local virtual environment (`.venv/`) and installs everything automatically. No manual `pip install` needed.

---

### Step 4 — Get a free Gemini API key

1. Go to **https://aistudio.google.com/app/apikey**
2. Sign in with a Google account
3. Click **Create API key**
4. Copy the key (it looks like `AIzaSy...`)

---

### Step 5 — Configure your API key

```bash
cp .env.example .env
```

Open `.env` in any text editor and replace the placeholder:

```
GOOGLE_API_KEY=paste-your-key-here
```

Save the file.

---

### Step 6 — Set up your portfolio

Open `portfolio.json`. It contains a sample portfolio you can use as-is or replace with your own holdings:

```json
[
  {"ticker": "AAPL",  "buy_price": 142.00, "buy_date": "2022-06-01", "shares": 20},
  {"ticker": "NVDA",  "buy_price": 168.00, "buy_date": "2023-01-10", "shares": 15},
  {"ticker": "MSFT",  "buy_price": 255.00, "buy_date": "2022-09-15", "shares": 10},
  {"ticker": "TSLA",  "buy_price": 300.00, "buy_date": "2022-11-01", "shares": 8},
  {"ticker": "JPM",   "buy_price": 125.00, "buy_date": "2023-03-20", "shares": 12}
]
```

| Field | Description | Example |
|-------|-------------|---------|
| `ticker` | Stock symbol (uppercase) | `"AAPL"` |
| `buy_price` | Price you paid per share in USD | `142.00` |
| `buy_date` | Date you bought (YYYY-MM-DD) | `"2022-06-01"` |
| `shares` | Number of shares you own | `20` |

You can add or remove stocks. US-listed stocks and ETFs work (anything supported by Yahoo Finance).

---

### Step 7 — Run the analysis

```bash
uv run python main.py
```

Expected output:

```
=== Demo 3: Portfolio Analysis Assistant ===
Loaded 5 position(s) from portfolio.json
Tickers: AAPL, NVDA, MSFT, TSLA, JPM

Analyzing — please wait...

  Fetching market data for 5 stock(s)...
  - Computing AAPL ...
  - Computing NVDA ...
  ...

============================================================
  Portfolio Analysis Report
  Generated:  2026-05-11
  Benchmark:  S&P 500 (^GSPC)   Risk-free rate: 4.5%
============================================================

  AAPL  Apple Inc.
  Buy price: $142.00   Current: $291.22   Shares: 20
  Market value: $5,824.40   Unrealized P&L: +$2,984.40 (+105.1%)
  Annualized return: +20.0%   Max drawdown: -33.4%
  Volatility: 27.4%   Beta: 1.21   Alpha: +1.4%
  ...

[Risk Overview]
This portfolio exhibits a high level of risk...

[Recommendations]
1. Diversification: ...
...

Full report saved to: portfolio_report.json
```

The full structured report is saved to `portfolio_report.json`.

> **Tip — API quota:** This project uses `gemini-2.5-flash`. Google's free tier allows ~500 requests/day. If you see a `429 RESOURCE_EXHAUSTED` error, wait a few minutes and try again, or visit https://aistudio.google.com to check your quota.

---

### Step 8 — Generate a PDF report

```bash
uv run python generate_pdf.py
```

This reads `portfolio_report.json` and creates `portfolio_report.pdf` — a formatted, print-ready document with:

- Portfolio summary (cost, value, P&L, total return)
- Full metrics table (all stocks side by side)
- AI-written analysis: risk overview, stock insights, market context, recommendations

Open it with any PDF viewer.

---

## Project Structure

```
ai-workflow-demo/
├── .env.example        ← copy this to .env and add your API key
├── pyproject.toml      ← project dependencies (managed by uv)
├── main.py             ← entry point
├── demo_stocks.py      ← agent, tool, Pydantic models, console output
├── generate_pdf.py     ← reads portfolio_report.json → PDF
├── portfolio.json      ← your stock positions (edit this)
└── chat_history.md     ← design conversation that produced this project
```

Generated files (not in repo):
- `portfolio_report.json` — full structured report from last run
- `portfolio_report.pdf` — PDF from last `generate_pdf.py` run

---

## How It Works

### The separation of concerns

```
portfolio.json
     │
     ▼
┌─────────────────────────────────────────────┐
│  Tool: analyze_portfolio()                  │
│  • yfinance  → real market prices           │
│  • pandas    → return calculations          │
│  • numpy     → Beta / covariance matrix     │
│  Pure Python, deterministic, no LLM         │
└─────────────────────┬───────────────────────┘
                      │ precise metrics JSON
                      ▼
┌─────────────────────────────────────────────┐
│  Gemini (via PydanticAI agent)              │
│  • reads the numbers                        │
│  • writes risk summary, insights,           │
│    market context, recommendations          │
│  • fills PortfolioReport Pydantic model     │
└─────────────────────┬───────────────────────┘
                      │ validated structured output
                      ▼
            portfolio_report.json
                      │
                      ▼
            generate_pdf.py → portfolio_report.pdf
```

**Why AI here?** The math is handled by deterministic Python — Beta, Alpha, drawdowns are calculated exactly. The AI's role is to *interpret* the numbers: explain what a Beta of 2.1 means for this specific portfolio, compare against the benchmark, and recommend concrete actions. That narrative layer is where LLMs genuinely add value.

### Financial metrics explained

| Metric | What it measures |
|--------|-----------------|
| **Annualized Return** | Your yearly return rate, accounting for how long you've held the position |
| **Max Drawdown** | The worst peak-to-trough drop since your buy date (more negative = more volatile) |
| **Beta** | How much your stock moves relative to the S&P 500. Beta=1.5 means if S&P drops 10%, your stock likely drops 15% |
| **Alpha** | Your return above/below what CAPM predicts given your risk. Positive Alpha = outperformance |
| **Volatility** | Annualized standard deviation of daily returns — how wildly the price swings |

### Key PydanticAI concepts in this project

**1. `@agent.tool_plain`** — exposes a Python function as a tool the LLM can call:
```python
@agent.tool_plain
def analyze_portfolio(portfolio_json: str) -> str:
    # deterministic math here — yfinance + pandas
    return json.dumps(metrics)
```

**2. `output_type`** — forces the LLM output into a validated Pydantic model:
```python
class PortfolioReport(BaseModel):
    risk_level: Literal["Low Risk", "Medium Risk", "High Risk"]
    risk_summary: str
    recommendations: list[str]
    ...

agent = Agent("google-gla:gemini-2.5-flash", output_type=PortfolioReport)
```
If the LLM returns invalid data (wrong type, missing field), PydanticAI automatically retries.

---

## Going Further — LangGraph

PydanticAI is the right tool for **single-agent, single-task** patterns like this one. For more complex AI systems, the next step is [LangGraph](https://langchain-ai.github.io/langgraph/).

LangGraph lets you build **multi-agent pipelines** where agents hand off work to each other with explicit control flow:

```
[Data Agent]  →  [Risk Agent]  →  Escalate?  →  Yes → [Compliance Agent]
                                               →  No  → [Report Agent]
```

Natural extensions of this project in LangGraph:
- A **macro agent** that pulls economic data (interest rates, sector performance) to add market context
- A **rebalancing agent** that suggests specific trades based on the metrics
- A **human approval gate** that pauses and asks you to confirm before saving the report
- **Scheduled runs** that email you a weekly portfolio update

### Progression path

| Stage | Tool | What you can build |
|-------|------|--------------------|
| Single agent + tools | **PydanticAI** (this project) | Structured analysis, Q&A, data extraction |
| Multi-step pipeline | **LangGraph** | Sequential agents, branching logic |
| Stateful long-running | **LangGraph + persistence** | Approval workflows, recurring tasks |
| Production deployment | **LangGraph Platform** | APIs, scheduling, monitoring |

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `pydantic-ai-slim[google]` | Agent framework + Gemini provider |
| `yfinance` | Free real-time and historical market data (no API key needed) |
| `pandas` | Time-series alignment and return calculations |
| `numpy` | Covariance matrix for Beta computation |
| `reportlab` | PDF generation |
| `python-dotenv` | Load `GOOGLE_API_KEY` from `.env` |

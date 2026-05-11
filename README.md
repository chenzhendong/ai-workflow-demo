# PydanticAI + Gemini — Portfolio Analysis Demo

A focused starter project demonstrating how to build a production-grade AI application with **PydanticAI** and **Google Gemini**. The demo analyzes a stock portfolio from a JSON file and produces a structured report with computed financial metrics and AI-generated investment insights.

---

## What is PydanticAI?

[PydanticAI](https://ai.pydantic.dev/) is a Python agent framework built by the Pydantic team. It brings the same type-safety and validation philosophy of Pydantic models to AI application development.

### Core ideas

**1. Agents**
An `Agent` is the central object. It wraps an LLM, holds a system prompt, and knows which tools it can call. You create one per logical role in your application.

```python
from pydantic_ai import Agent

agent = Agent("google-gla:gemini-2.0-flash", system_prompt="You are a financial analyst.")
result = agent.run_sync("What is the S&P 500?")
print(result.output)
```

**2. Structured Output**
Pass a Pydantic model as `output_type` and the framework guarantees the LLM response is validated and deserialized into that model — no manual JSON parsing, no schema drift.

```python
from pydantic import BaseModel
from typing import Literal

class Report(BaseModel):
    risk_level: Literal["Low Risk", "Medium Risk", "High Risk"]
    summary: str
    recommendations: list[str]

agent = Agent("google-gla:gemini-2.0-flash", output_type=Report)
report = agent.run_sync("Analyze this portfolio...").output
print(report.risk_level)  # always one of the three literals
```

**3. Tool Calling**
Decorate plain Python functions with `@agent.tool_plain` to expose them as tools the LLM can call. Tools handle deterministic work (database queries, API calls, math) while the LLM handles reasoning and synthesis.

```python
@agent.tool_plain
def calculate_metrics(ticker: str, buy_price: float) -> str:
    # fetch real data, run math — no LLM involved here
    return json.dumps({"beta": 1.2, "alpha": 3.5})
```

**4. Dependency Injection**
Use `@agent.tool` with `RunContext[DepsType]` to pass shared state (database connections, user config, API clients) into tools without globals.

```python
from dataclasses import dataclass
from pydantic_ai import RunContext

@dataclass
class AppDeps:
    db: DatabaseConnection

@agent.tool
def get_user_balance(ctx: RunContext[AppDeps]) -> float:
    return ctx.deps.db.query_balance()
```

### Why PydanticAI over raw API calls?

| Concern | Raw API | PydanticAI |
|---------|---------|------------|
| Output validation | Manual JSON parse + guard | Pydantic model, automatic |
| Tool orchestration | Manual loop + schema writing | `@agent.tool` decorator |
| Type safety | None | Full IDE support |
| Retry on validation failure | You write it | Built-in |
| Testing | Hard to mock | Dependency injection by design |

---

## This Project

### What it demonstrates

The portfolio analysis demo shows all three core PydanticAI patterns working together:

- **Tool calling** — `analyze_portfolio` fetches real market data via `yfinance` and computes all financial metrics with `pandas`/`numpy`. The math is deterministic and never touches the LLM.
- **Structured output** — `PortfolioReport` is a Pydantic model. The LLM must fill every field, including typed literals (`"Low Risk"`, `"Medium Risk"`, `"High Risk"`). Invalid output is rejected and retried automatically.
- **AI as analyst** — Once the tool returns precise numbers, the LLM's job is to interpret them: write the risk summary, surface stock-level insights, compare against the benchmark, and suggest concrete actions. This is where the LLM genuinely adds value — translating data into narrative.

### Financial metrics computed (by the tool, not the LLM)

| Metric | Formula |
|--------|---------|
| Annualized Return | `(1 + total_return) ^ (365 / days_held) - 1` |
| Maximum Drawdown | `min((price - rolling_max) / rolling_max)` |
| Volatility | `std(daily_returns) × √252` |
| Beta | `cov(stock, SPY) / var(SPY)` |
| Alpha (CAPM) | `stock_return - (Rf + β × (market_return - Rf))` |

Benchmark: S&P 500 (`^GSPC`). Risk-free rate: 4.5% (approximating the 10-year US Treasury).

---

## Project Structure

```
pydanticai-gemini-starter/
├── .env.example       # API key template
├── pyproject.toml     # uv project — dependencies declared here
├── main.py            # entry point
├── demo_stocks.py     # agent, tool, models, output printer
└── portfolio.json     # your holdings (edit this)
```

---

## Setup

**Requirements:** Python 3.10+, [uv](https://docs.astral.sh/uv/)

```bash
# 1. Clone / enter the project
cd pydanticai-gemini-starter

# 2. Create virtual environment and install dependencies
uv venv
uv sync

# 3. Configure API key
cp .env.example .env
# Edit .env and set GOOGLE_API_KEY=<your key>
# Free key: https://aistudio.google.com/app/apikey

# 4. Edit your portfolio (optional)
# portfolio.json — add your own tickers, buy prices, dates, share counts

# 5. Run
uv run python main.py
```

### portfolio.json format

```json
[
  {"ticker": "AAPL", "buy_price": 150.00, "buy_date": "2023-01-15", "shares": 10},
  {"ticker": "NVDA", "buy_price": 280.00, "buy_date": "2023-05-20", "shares": 6}
]
```

### Output

The report prints to the console and is also saved as `portfolio_report.json`.

---

## Looking Further: LangGraph

PydanticAI is excellent for single-agent patterns: one agent, a set of tools, one structured output. It covers the majority of real-world AI application needs.

For workflows that require **multiple agents collaborating**, **branching logic**, **human-in-the-loop checkpoints**, or **long-running stateful pipelines**, the natural next step is [LangGraph](https://langchain-ai.github.io/langgraph/).

### What LangGraph adds

LangGraph models your AI application as a **directed graph** where each node is an agent, a tool call, or a decision point, and edges define the control flow between them.

```
[Fetch Data] → [Risk Agent] → [Should escalate?] → Yes → [Compliance Agent] → [Report]
                                                  → No  → [Report]
```

Typical use cases where LangGraph shines over a single PydanticAI agent:

| Scenario | Why LangGraph |
|----------|--------------|
| Multi-step research with web search + summarization + fact-checking | Each step is a separate node; results flow between them |
| Approval workflows | Human-in-the-loop nodes pause execution until a user confirms |
| Parallel sub-agents | Fan-out edges run multiple agents concurrently, then merge results |
| Long-horizon tasks | Built-in state persistence across sessions (checkpointing) |
| Agent-to-agent delegation | One orchestrator agent routes subtasks to specialist agents |

### Progression path

```
PydanticAI single agent          — this project
     ↓
PydanticAI multi-tool agent      — add more tools, handle tool errors
     ↓
LangGraph multi-node pipeline    — separate agents per concern, explicit control flow
     ↓
LangGraph with persistence       — stateful workflows, human approval gates
```

A natural extension of this portfolio project in LangGraph would be a pipeline where a **data agent** fetches and computes metrics, a **risk agent** evaluates concentration and volatility, a **macro agent** pulls economic context, and an **editor agent** combines the outputs into a final report — each step independently testable and replaceable.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `pydantic-ai-slim[google]` | Agent framework + Gemini provider |
| `yfinance` | Free real-time and historical market data |
| `pandas` | Time-series alignment and return calculations |
| `numpy` | Covariance matrix for Beta computation |
| `python-dotenv` | Load `GOOGLE_API_KEY` from `.env` |

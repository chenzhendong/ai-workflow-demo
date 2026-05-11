"""
Demo 3: Portfolio Analysis Assistant
Concepts: Tool calling (tool_plain), structured output, AI as analyst

Why AI adds value here:
  - Tools handle precise math (yfinance + pandas/numpy) — deterministic
  - AI translates numbers into a readable English analysis report
  - Structured output ensures the report is consistently formatted and parseable
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
import yfinance as yf
from pydantic import BaseModel, Field
from pydantic_ai import Agent

RISK_FREE_RATE = 0.045  # annualized risk-free rate 4.5%
BENCHMARK = "^GSPC"     # S&P 500


# ── Output models ─────────────────────────────────────────────────────────────

class StockMetrics(BaseModel):
    ticker: str
    company_name: str
    buy_price: float
    current_price: float
    shares: int
    total_cost: float
    market_value: float
    unrealized_pnl: float
    total_return_pct: float
    annualized_return_pct: float
    max_drawdown_pct: float = Field(description="Maximum drawdown (negative number)")
    volatility_pct: float = Field(description="Annualized volatility")
    beta: float = Field(description="Beta relative to S&P 500")
    alpha_pct: float = Field(description="CAPM Alpha, annualized, in percent")


class PortfolioReport(BaseModel):
    generated_at: str
    benchmark: str
    risk_free_rate_pct: float
    stocks: list[StockMetrics]
    portfolio_total_cost: float
    portfolio_total_value: float
    portfolio_unrealized_pnl: float
    portfolio_total_return_pct: float
    # AI-generated analysis
    risk_level: Literal["Low Risk", "Medium Risk", "High Risk"]
    risk_summary: str = Field(description="100-150 word overview of portfolio risk")
    stock_insights: list[str] = Field(description="One insight per stock highlighting Alpha/Beta characteristics")
    recommendations: list[str] = Field(description="3-5 specific, actionable investment recommendations")
    market_context: str = Field(description="Performance analysis relative to the S&P 500 benchmark")


# ── Agent ─────────────────────────────────────────────────────────────────────

agent = Agent(
    "google-gla:gemini-2.5-flash",
    output_type=PortfolioReport,
    system_prompt=f"""You are a professional quantitative investment analyst.

Workflow:
1. Call the analyze_portfolio tool with the portfolio JSON provided by the user.
2. Use the precise metrics returned by the tool to fill all fields of PortfolioReport.
3. Write all analysis content in clear, professional English.

Field rules:
- generated_at: today's date in ISO format
- benchmark: "S&P 500 (^GSPC)"
- risk_free_rate_pct: {RISK_FREE_RATE * 100}
- risk_level: judge from average Beta and max drawdown (Beta>1.3 or drawdown<-30% leans High Risk)
- risk_summary: summarize overall portfolio risk, mentioning Beta, volatility, and drawdown
- stock_insights: one insight per stock, highlighting its Alpha/Beta characteristics
- recommendations: data-driven suggestions (diversification, stop-loss levels, rebalancing, etc.)
- market_context: compare portfolio return against the benchmark
""",
)


# ── Tool: deterministic math, no AI involved ──────────────────────────────────

@agent.tool_plain
def analyze_portfolio(portfolio_json: str) -> str:
    """
    Load portfolio JSON, fetch real market data from yfinance,
    compute all financial metrics per stock, and return a summary JSON
    for the AI to use when generating the analysis report.
    """
    positions = json.loads(portfolio_json)
    stocks_data = []

    print(f"\n  Fetching market data for {len(positions)} stock(s)...")

    # 预先获取基准数据（最早买入日）
    earliest_date = min(p["buy_date"] for p in positions)
    spy_hist = yf.Ticker(BENCHMARK).history(start=earliest_date)

    for pos in positions:
        ticker = pos["ticker"].upper()
        buy_price = float(pos["buy_price"])
        buy_date = pos["buy_date"]
        shares = int(pos["shares"])

        print(f"  - Computing {ticker} ...")
        time.sleep(0.3)  # avoid rate limiting

        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=buy_date)

            if hist.empty:
                print(f"    Warning: no data for {ticker}, skipping")
                continue

            current_price = float(hist["Close"].iloc[-1])
            company_name = stock.info.get("longName", ticker)

            # days held
            buy_ts = pd.Timestamp(buy_date)
            days_held = max((pd.Timestamp.now() - buy_ts).days, 1)

            # daily returns
            daily_returns = hist["Close"].pct_change().dropna()

            # align benchmark to same period
            spy_period = spy_hist[spy_hist.index >= hist.index[0]]
            spy_returns = spy_period["Close"].pct_change().dropna()
            aligned = pd.concat(
                [daily_returns, spy_returns], axis=1, join="inner"
            ).dropna()
            aligned.columns = ["stock", "spy"]

            # max drawdown from buy date
            rolling_max = hist["Close"].cummax()
            drawdown = (hist["Close"] - rolling_max) / rolling_max
            max_drawdown = float(drawdown.min() * 100)

            # annualized return
            total_return = (current_price - buy_price) / buy_price
            annualized = ((1 + total_return) ** (365.0 / days_held) - 1) * 100

            # annualized volatility
            volatility = float(daily_returns.std() * np.sqrt(252) * 100)

            # beta
            if len(aligned) > 5:
                cov_matrix = np.cov(aligned["stock"].values, aligned["spy"].values)
                beta = float(cov_matrix[0, 1] / cov_matrix[1, 1])
            else:
                beta = 1.0

            # alpha (CAPM, annualized)
            spy_total_return = float(
                spy_period["Close"].iloc[-1] / spy_period["Close"].iloc[0] - 1
            )
            spy_annualized = ((1 + spy_total_return) ** (365.0 / days_held) - 1)
            alpha_pct = (
                (annualized / 100) - (RISK_FREE_RATE + beta * (spy_annualized - RISK_FREE_RATE))
            ) * 100

            total_cost = round(buy_price * shares, 2)
            market_value = round(current_price * shares, 2)

            stocks_data.append({
                "ticker": ticker,
                "company_name": company_name,
                "buy_price": round(buy_price, 2),
                "current_price": round(current_price, 2),
                "shares": shares,
                "total_cost": total_cost,
                "market_value": market_value,
                "unrealized_pnl": round(market_value - total_cost, 2),
                "total_return_pct": round(total_return * 100, 2),
                "annualized_return_pct": round(annualized, 2),
                "max_drawdown_pct": round(max_drawdown, 2),
                "volatility_pct": round(volatility, 2),
                "beta": round(beta, 3),
                "alpha_pct": round(alpha_pct, 2),
            })

        except Exception as e:
            print(f"    Error: failed to compute {ticker} - {e}")

    if not stocks_data:
        return json.dumps({"error": "Failed to fetch data for all stocks"})

    # portfolio aggregates
    total_cost = round(sum(s["total_cost"] for s in stocks_data), 2)
    total_value = round(sum(s["market_value"] for s in stocks_data), 2)
    unrealized_pnl = round(total_value - total_cost, 2)
    total_return_pct = round((total_value - total_cost) / total_cost * 100, 2)

    return json.dumps({
        "stocks": stocks_data,
        "portfolio_total_cost": total_cost,
        "portfolio_total_value": total_value,
        "portfolio_unrealized_pnl": unrealized_pnl,
        "portfolio_total_return_pct": total_return_pct,
        "today": datetime.now().strftime("%Y-%m-%d"),
    }, ensure_ascii=False)


# ── Print report ──────────────────────────────────────────────────────────────

def print_report(report: PortfolioReport):
    sep = "─" * 60
    print(f"\n{'=' * 60}")
    print(f"  Portfolio Analysis Report")
    print(f"  Generated:  {report.generated_at}")
    print(f"  Benchmark:  {report.benchmark}   Risk-free rate: {report.risk_free_rate_pct}%")
    print(f"{'=' * 60}")

    for s in report.stocks:
        pnl_sign = "+" if s.unrealized_pnl >= 0 else ""
        ret_sign = "+" if s.total_return_pct >= 0 else ""
        alpha_sign = "+" if s.alpha_pct >= 0 else ""
        print(f"\n  {s.ticker}  {s.company_name}")
        print(sep)
        print(f"  Buy price: ${s.buy_price:.2f}   Current: ${s.current_price:.2f}   Shares: {s.shares}")
        print(f"  Market value: ${s.market_value:,.2f}   Unrealized P&L: {pnl_sign}${s.unrealized_pnl:,.2f} ({ret_sign}{s.total_return_pct:.1f}%)")
        print(f"  Annualized return: {ret_sign}{s.annualized_return_pct:.1f}%   Max drawdown: {s.max_drawdown_pct:.1f}%")
        print(f"  Volatility: {s.volatility_pct:.1f}%   Beta: {s.beta:.2f}   Alpha: {alpha_sign}{s.alpha_pct:.1f}%")

    print(f"\n{'=' * 60}")
    print(f"  Portfolio Summary")
    print(sep)
    pnl_sign = "+" if report.portfolio_unrealized_pnl >= 0 else ""
    ret_sign = "+" if report.portfolio_total_return_pct >= 0 else ""
    print(f"  Total cost:   ${report.portfolio_total_cost:,.2f}")
    print(f"  Total value:  ${report.portfolio_total_value:,.2f}")
    print(f"  Total P&L:    {pnl_sign}${report.portfolio_unrealized_pnl:,.2f}  ({ret_sign}{report.portfolio_total_return_pct:.1f}%)")
    print(f"  Risk level:   {report.risk_level}")

    print(f"\n{'=' * 60}")
    print(f"  AI Analysis Report")
    print(sep)
    print(f"\n[Risk Overview]\n{report.risk_summary}")
    print(f"\n[Stock Insights]")
    for i, insight in enumerate(report.stock_insights, 1):
        print(f"  {i}. {insight}")
    print(f"\n[Market Context]\n{report.market_context}")
    print(f"\n[Recommendations]")
    for i, rec in enumerate(report.recommendations, 1):
        print(f"  {i}. {rec}")
    print(f"\n{'=' * 60}")


# ── Entry point ───────────────────────────────────────────────────────────────

def run(portfolio_path: str = "portfolio.json"):
    print(f"\n=== Demo 3: Portfolio Analysis Assistant ===")

    path = Path(portfolio_path)
    if not path.exists():
        print(f"Error: file not found: {portfolio_path}")
        return

    portfolio_json = path.read_text(encoding="utf-8")
    positions = json.loads(portfolio_json)
    print(f"Loaded {len(positions)} position(s) from {portfolio_path}")

    tickers = ", ".join(p["ticker"].upper() for p in positions)
    print(f"Tickers: {tickers}")

    prompt = (
        f"Please analyze the following portfolio. "
        f"First call analyze_portfolio to get the metrics, then generate the full report:\n\n"
        f"{portfolio_json}"
    )

    print("\nAnalyzing — please wait...")
    result = agent.run_sync(prompt)
    report = result.output

    print_report(report)

    output_path = path.parent / "portfolio_report.json"
    output_path.write_text(
        report.model_dump_json(indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nFull report saved to: {output_path}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    run()

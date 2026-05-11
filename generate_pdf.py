"""
Generate a human-readable PDF report from portfolio_report.json.
Usage: uv run python generate_pdf.py
"""

import json
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)

# ── Colours ───────────────────────────────────────────────────────────────────
DARK_BLUE   = colors.HexColor("#1a2744")
MID_BLUE    = colors.HexColor("#2e4a8e")
LIGHT_BLUE  = colors.HexColor("#e8edf8")
ACCENT      = colors.HexColor("#2e7d32")   # green for positive
DANGER      = colors.HexColor("#c62828")   # red for negative / high risk
AMBER       = colors.HexColor("#e65100")   # amber for medium risk
GREY_TEXT   = colors.HexColor("#555555")
RULE_COLOR  = colors.HexColor("#cccccc")

RISK_COLORS = {
    "High Risk":   DANGER,
    "Medium Risk": AMBER,
    "Low Risk":    ACCENT,
}


# ── Page template with header / footer ───────────────────────────────────────

def _make_doc(output_path: str) -> BaseDocTemplate:
    W, H = A4
    margin = 2 * cm

    doc = BaseDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=2.5 * cm,
        bottomMargin=2 * cm,
    )

    def header_footer(canvas, doc):
        canvas.saveState()
        # Header bar
        canvas.setFillColor(DARK_BLUE)
        canvas.rect(0, H - 1.6 * cm, W, 1.6 * cm, fill=True, stroke=False)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(margin, H - 1.0 * cm, "Portfolio Analysis Report")
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(W - margin, H - 1.0 * cm, f"Generated {datetime.now().strftime('%B %d, %Y')}")
        # Footer
        canvas.setFillColor(GREY_TEXT)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(margin, 1.0 * cm, "Powered by PydanticAI + Google Gemini  |  Market data via yfinance")
        canvas.drawRightString(W - margin, 1.0 * cm, f"Page {doc.page}")
        canvas.restoreState()

    frame = Frame(margin, 2 * cm, W - 2 * margin, H - 4.1 * cm, id="main")
    doc.addPageTemplates([PageTemplate(id="main", frames=frame, onPage=header_footer)])
    return doc


# ── Styles ────────────────────────────────────────────────────────────────────

def _styles():
    base = getSampleStyleSheet()
    s = {}
    s["h1"] = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=22,
                              textColor=DARK_BLUE, spaceAfter=4)
    s["h2"] = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13,
                              textColor=DARK_BLUE, spaceBefore=14, spaceAfter=4)
    s["h3"] = ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=10,
                              textColor=MID_BLUE, spaceBefore=10, spaceAfter=3)
    s["body"] = ParagraphStyle("body", fontName="Helvetica", fontSize=9.5,
                                textColor=GREY_TEXT, leading=15, spaceAfter=6)
    s["bullet"] = ParagraphStyle("bullet", fontName="Helvetica", fontSize=9.5,
                                  textColor=GREY_TEXT, leading=15,
                                  leftIndent=12, spaceAfter=5,
                                  bulletIndent=0, bulletFontName="Helvetica")
    s["meta"] = ParagraphStyle("meta", fontName="Helvetica", fontSize=8.5,
                                textColor=GREY_TEXT)
    s["risk_badge"] = ParagraphStyle("badge", fontName="Helvetica-Bold", fontSize=11)
    return s


# ── Helper: colour a number string ───────────────────────────────────────────

def _signed(val: float, unit: str = "%", decimals: int = 1) -> str:
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.{decimals}f}{unit}"


def _color_cell(val: float, text: str) -> Paragraph:
    color = ACCENT if val >= 0 else DANGER
    style = ParagraphStyle("cc", fontName="Helvetica-Bold", fontSize=8.5,
                            textColor=color, alignment=1)
    return Paragraph(text, style)


# ── Main builder ─────────────────────────────────────────────────────────────

def build_pdf(report_path: str = "portfolio_report.json",
              output_path: str = "portfolio_report.pdf"):

    data = json.loads(Path(report_path).read_text())
    doc  = _make_doc(output_path)
    S    = _styles()
    story = []

    # ── Cover block ───────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("Investment Portfolio", S["h1"]))
    story.append(Paragraph("Analysis Report", ParagraphStyle(
        "sub", fontName="Helvetica", fontSize=16, textColor=MID_BLUE, spaceAfter=6)))

    risk_color = RISK_COLORS.get(data["risk_level"], DANGER)
    story.append(Paragraph(
        f"<font color='#{risk_color.hexval()[2:]}'>&#9632; {data['risk_level']}</font>"
        f"&nbsp;&nbsp;<font color='#555555' size='9'>Benchmark: {data['benchmark']}"
        f"&nbsp;&nbsp;Risk-free rate: {data['risk_free_rate_pct']}%"
        f"&nbsp;&nbsp;As of {data['generated_at']}</font>",
        ParagraphStyle("cover_meta", fontName="Helvetica", fontSize=11, spaceAfter=10)
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=MID_BLUE, spaceAfter=16))

    # ── Portfolio summary cards ────────────────────────────────────────────────
    story.append(Paragraph("Portfolio Summary", S["h2"]))

    pnl  = data["portfolio_unrealized_pnl"]
    ret  = data["portfolio_total_return_pct"]
    summary_data = [
        ["Total Cost", "Market Value", "Unrealized P&L", "Total Return"],
        [
            f"${data['portfolio_total_cost']:,.2f}",
            f"${data['portfolio_total_value']:,.2f}",
            _color_cell(pnl,  _signed(pnl,  "$", 2)),
            _color_cell(ret,  _signed(ret,  "%", 1)),
        ],
    ]
    summary_table = Table(summary_data, colWidths=["25%", "25%", "25%", "25%"])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 9),
        ("FONTNAME",     (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 1), (-1, 1), 12),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS",(0, 1), (-1, 1), [LIGHT_BLUE]),
        ("TOPPADDING",   (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ("GRID",         (0, 0), (-1, -1), 0.4, RULE_COLOR),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.5 * cm))

    # ── Per-stock metrics table ───────────────────────────────────────────────
    story.append(Paragraph("Stock Metrics", S["h2"]))

    hdr_style = ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=8,
                                textColor=colors.white, alignment=1)
    cell_c = ParagraphStyle("tc", fontName="Helvetica", fontSize=8.5,
                             textColor=GREY_TEXT, alignment=1)

    def th(txt): return Paragraph(txt, hdr_style)
    def td(txt): return Paragraph(txt, cell_c)

    headers = ["Ticker", "Company", "Buy\nPrice", "Current\nPrice",
               "Shares", "Market\nValue", "P&L", "Ann.\nReturn",
               "Max\nDrawdown", "Volatility", "Beta", "Alpha"]
    col_w   = [1.1*cm, 3.4*cm, 1.3*cm, 1.3*cm, 1.0*cm,
               1.6*cm, 1.5*cm, 1.3*cm, 1.4*cm, 1.3*cm, 1.0*cm, 1.0*cm]

    rows = [[th(h) for h in headers]]
    for s in data["stocks"]:
        rows.append([
            td(s["ticker"]),
            Paragraph(s["company_name"], ParagraphStyle("co", fontName="Helvetica",
                      fontSize=8, textColor=GREY_TEXT, alignment=0)),
            td(f"${s['buy_price']:.2f}"),
            td(f"${s['current_price']:.2f}"),
            td(str(s["shares"])),
            td(f"${s['market_value']:,.0f}"),
            _color_cell(s["unrealized_pnl"],  _signed(s["total_return_pct"])),
            _color_cell(s["annualized_return_pct"], _signed(s["annualized_return_pct"])),
            _color_cell(s["max_drawdown_pct"], f"{s['max_drawdown_pct']:.1f}%"),
            td(f"{s['volatility_pct']:.1f}%"),
            td(f"{s['beta']:.2f}"),
            _color_cell(s["alpha_pct"], _signed(s["alpha_pct"])),
        ])

    metrics_table = Table(rows, colWidths=col_w, repeatRows=1)
    metrics_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), DARK_BLUE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, LIGHT_BLUE]),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID",          (0, 0), (-1, -1), 0.3, RULE_COLOR),
        ("LINEBELOW",     (0, 0), (-1, 0), 1.5, MID_BLUE),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 0.6 * cm))

    # ── AI Analysis ───────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=RULE_COLOR, spaceAfter=10))
    story.append(Paragraph("AI Analysis", S["h2"]))

    # Risk Overview
    block = [
        Paragraph("Risk Overview", S["h3"]),
        Paragraph(data["risk_summary"], S["body"]),
    ]
    story.append(KeepTogether(block))

    # Stock Insights
    story.append(Paragraph("Stock Insights", S["h3"]))
    for i, insight in enumerate(data["stock_insights"], 1):
        story.append(Paragraph(f"{i}.&nbsp;&nbsp;{insight}", S["bullet"]))

    story.append(Spacer(1, 0.2 * cm))

    # Market Context
    block = [
        Paragraph("Market Context", S["h3"]),
        Paragraph(data["market_context"], S["body"]),
    ]
    story.append(KeepTogether(block))

    # Recommendations
    story.append(Paragraph("Recommendations", S["h3"]))
    for i, rec in enumerate(data["recommendations"], 1):
        story.append(Paragraph(f"{i}.&nbsp;&nbsp;{rec}", S["bullet"]))

    # ── Build ─────────────────────────────────────────────────────────────────
    doc.build(story)
    print(f"Report saved: {output_path}")


if __name__ == "__main__":
    build_pdf()

"""„Scrisoarea lunii”: un PDF pe înțeles, cu grafice, despre cum a mers luna și ce urmează.

Spre deosebire de raportul pentru contabil (tabele), scrisoarea povestește: ce a mers bine,
la ce trebuie atenție și ce e de făcut luna viitoare. Se poate trimite partenerilor sau băncii.
"""

import io
import sqlite3
from datetime import date

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import calc, obligations, planning
from .exports import _register_fonts

INK = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#64748b")
CYAN = colors.HexColor("#0891b2")
GREEN = colors.HexColor("#059669")
RED = colors.HexColor("#dc2626")
GOLD = colors.HexColor("#d97706")
PALETTE = ["#0891b2", "#7c3aed", "#059669", "#d97706", "#db2777", "#2563eb", "#65a30d", "#ea580c", "#64748b"]


def money(value: float) -> str:
    return calc.fmt(value)


def change_text(current: float, previous: float) -> str:
    change = calc.pct_change(current, previous)
    if change is None:
        return ""
    word = "mai mult" if change >= 0 else "mai puțin"
    return f" ({calc.fmt_pct(abs(change))} {word} decât luna trecută)"


def trend_chart(trend: list[dict], regular: str) -> Drawing:
    months = trend[-6:]
    drawing = Drawing(170 * mm, 62 * mm)
    chart = VerticalBarChart()
    chart.x, chart.y, chart.width, chart.height = 14 * mm, 10 * mm, 150 * mm, 44 * mm
    chart.data = [[m["revenue"] for m in months], [max(m["profit"], 0) for m in months]]
    chart.categoryAxis.categoryNames = [m["label"] for m in months]
    chart.categoryAxis.labels.fontName = regular
    chart.categoryAxis.labels.fontSize = 8
    chart.valueAxis.labels.fontName = regular
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.valueMin = 0
    chart.valueAxis.labelTextFormat = lambda v: f"{v / 1000:,.0f}k".replace(",", ".")
    chart.bars[0].fillColor = CYAN
    chart.bars[1].fillColor = GREEN
    chart.bars.strokeColor = None
    chart.barSpacing, chart.groupSpacing = 2, 10
    drawing.add(chart)
    for i, (label, color) in enumerate([("Vânzări", CYAN), ("Profit net", GREEN)]):
        drawing.add(Rect(16 * mm + i * 32 * mm, 57 * mm, 3 * mm, 3 * mm, fillColor=color, strokeColor=None))
        drawing.add(String(21 * mm + i * 32 * mm, 57.3 * mm, label, fontName=regular, fontSize=8, fillColor=INK))
    return drawing


def flow_chart(flow: list[dict], regular: str) -> Drawing:
    drawing = Drawing(170 * mm, 58 * mm)
    items = flow[:8]
    pie = Pie()
    pie.x, pie.y, pie.width, pie.height = 6 * mm, 4 * mm, 48 * mm, 48 * mm
    pie.data = [max(item["amount"], 0.01) for item in items]
    pie.labels = None
    pie.slices.strokeColor = colors.white
    pie.slices.strokeWidth = 1
    for i in range(len(items)):
        pie.slices[i].fillColor = colors.HexColor(PALETTE[i % len(PALETTE)])
    drawing.add(pie)
    for i, item in enumerate(items):
        y = 50 * mm - i * 6 * mm
        drawing.add(Rect(66 * mm, y, 3 * mm, 3 * mm, fillColor=colors.HexColor(PALETTE[i % len(PALETTE)]),
                         strokeColor=None))
        drawing.add(String(71 * mm, y + 0.3 * mm, f"{item['name'][:34]}", fontName=regular, fontSize=8.5,
                           fillColor=INK))
        drawing.add(String(165 * mm, y + 0.3 * mm, f"{money(item['amount'])} · {calc.fmt_pct(item['share'])}",
                           fontName=regular, fontSize=8.5, fillColor=MUTED, textAnchor="end"))
    return drawing


def letter_pdf(conn: sqlite3.Connection, ym: str) -> bytes:
    regular, bold = _register_fonts()
    d = calc.dashboard(conn, ym)
    c, p = d["current"], d["previous"]
    owner = d.get("owner_name") or ""
    styles = {
        "title": ParagraphStyle("t", fontName=bold, fontSize=22, leading=27, textColor=INK),
        "sub": ParagraphStyle("s", fontName=regular, fontSize=10, leading=14, textColor=MUTED),
        "h": ParagraphStyle("h", fontName=bold, fontSize=13, leading=17, textColor=INK, spaceBefore=10, spaceAfter=4),
        "p": ParagraphStyle("p", fontName=regular, fontSize=10.5, leading=15.5, textColor=INK),
        "li": ParagraphStyle("li", fontName=regular, fontSize=10.5, leading=15, textColor=INK, leftIndent=10,
                             bulletIndent=0, spaceAfter=2),
        "small": ParagraphStyle("sm", fontName=regular, fontSize=8, leading=11, textColor=MUTED),
    }
    story = [
        Paragraph(f"Scrisoarea lunii · {c['label']}", styles["title"]),
        Paragraph(f"{d['company']} · pregătită de Testi pe {date.today():%d.%m.%Y}", styles["sub"]),
        Spacer(1, 8 * mm),
    ]
    hello = f"Dragă {owner}," if owner else "Bună ziua,"
    profit_word = "un profit net" if c["profit"] >= 0 else "o pierdere"
    intro = (f"{hello} în {c['label']} firma a vândut de <b>{money(c['revenue'])}</b>{change_text(c['revenue'], p['revenue'])} "
             f"și a încheiat luna cu {profit_word} de <b>{money(abs(c['profit']))}</b>{change_text(c['profit'], p['profit'])}. ")
    if c["owner_income"] > 0:
        intro += f"După impozitul pe dividende, îți rămân <b>{money(c['owner_income'])}</b>."
    if d["in_progress"]:
        intro += f" Luna nu s-a terminat: cifrele sunt până pe {d['compared_until_day']}."
    story += [Paragraph(intro, styles["p"]), Spacer(1, 6 * mm)]

    kpis = [("Vânzări", money(c["revenue"]), CYAN), ("Marjă brută", calc.fmt_pct(c["gross_margin_pct"]), colors.HexColor("#7c3aed")),
            ("Profit net", money(c["profit"]), GREEN if c["profit"] >= 0 else RED), ("Îți rămâne", money(c["owner_income"]), GOLD)]
    table = Table([[Paragraph(f"<font size=8 color='#64748b'>{label}</font><br/><font size=14 color='#{color.hexval()[2:]}'><b>{value}</b></font>",
                              ParagraphStyle("k", fontName=regular, leading=18)) for label, value, color in kpis]],
                  colWidths=[42.5 * mm] * 4)
    table.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#e2e8f0")),
                               ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#e2e8f0")),
                               ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                               ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                               ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
    story += [table, Spacer(1, 4 * mm)]

    story += [KeepTogether([Paragraph("Cum au evoluat lunile", styles["h"]), trend_chart(d["trend"], regular)])]
    if d["flow"]:
        story += [KeepTogether([Paragraph("Unde s-au dus banii", styles["h"]), flow_chart(d["flow"], regular)])]

    good, watch = [], []
    for note in d["insights"]:
        (good if note["tone"] in ("good", "info") else watch).append(note["text"])
    if d["top_products"]:
        best = d["top_products"][0]
        good.append(f"Produsul cu cel mai mare profit: <b>{best['product']}</b> ({money(best['profit'])} profit din "
                    f"{money(best['amount'])} vânzări).")
    if d["top_clients"]:
        best = d["top_clients"][0]
        good.append(f"Cel mai mare client: <b>{best['client']}</b>, cu {money(best['amount'])} în {best['invoices']} facturi.")
    if d.get("goals") and d["goals"].get("revenue"):
        g = d["goals"]["revenue"]
        (good if g["pct"] >= 100 else watch).append(
            f"Obiectivul de vânzări ({money(g['target'])}) a fost atins în proporție de <b>{calc.fmt_pct(g['pct'])}</b>.")
    r = d["receivables"]
    if r["overdue"]:
        names = ", ".join(x["client"] for x in r["clients"] if x["overdue"])[:120]
        watch.append(f"<b>{money(r['overdue'])}</b> de încasat sunt trecuți de scadență ({names}).")
    if d["low_stock"]:
        watch.append(f"{len(d['low_stock'])} produse sunt sub stocul minim: "
                     + ", ".join(x["name"] for x in d["low_stock"][:4]) + ".")
    analysis = planning.analysis(conn, ym)
    if analysis["dead_stock"]:
        watch.append(f"Marfă care stă nevândută: <b>{money(analysis['dead_stock_value'])}</b> în "
                     f"{len(analysis['dead_stock'])} produse.")
    for title, items in (("Ce a mers bine", good), ("La ce să fii atent", watch)):
        if items:
            story.append(Paragraph(title, styles["h"]))
            story += [Paragraph(item, styles["li"], bulletText="•") for item in items]

    nexts = []
    upcoming = [i for i in obligations.calendar_items(conn) if i["days_left"] >= 0 and i["kind"] == "anaf"
                and (i["amount"] or 0) > 0 and not i["paid"]][:4]
    for item in upcoming:
        nexts.append(f"Până pe {date.fromisoformat(item['date']):%d.%m}: {item['form']}, {item['title'][:1].lower() + item['title'][1:]} "
                     f"— <b>{money(item['amount'])}</b>.")
    reorder = planning.reorder(conn)
    if reorder["count"]:
        nexts.append(f"De comandat la furnizori: {reorder['count']} produse, cam <b>{money(reorder['total'])}</b> fără TVA "
                     f"(lista e în aplicație, la Stoc → Comenzi recomandate).")
    if analysis["inactive"]:
        nexts.append(f"De sunat: {', '.join(x['name'] for x in analysis['inactive'][:3])} — nu au mai cumpărat de peste "
                     f"{planning.INACTIVE_DAYS} de zile.")
    if nexts:
        story.append(Paragraph("Ce urmează", styles["h"]))
        story += [Paragraph(item, styles["li"], bulletText="•") for item in nexts]

    story += [Spacer(1, 8 * mm), Paragraph(
        "Cifrele sunt fără TVA și provin din aplicația Testify Hardware. Sunt calcule de gestiune pentru "
        "imaginea de ansamblu; situațiile oficiale rămân cele întocmite de contabil.", styles["small"])]

    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                                 bottomMargin=16 * mm, title=f"Scrisoarea lunii {c['label']}", author=d["company"])
    document.build(story)
    return buffer.getvalue()

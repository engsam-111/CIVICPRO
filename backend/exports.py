from io import BytesIO
from html import escape
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

AMBER = colors.HexColor("#d97706")
INK = colors.HexColor("#0f172a")
COLUMNS = {
    "Projects": [("code", "Code"), ("name", "Project"), ("location", "Location"), ("client", "Client"), ("start_date", "Start"), ("end_date", "Finish"), ("planned_progress", "Planned %"), ("progress", "Actual %"), ("schedule_variance", "Variance %"), ("progress_mode", "Progress basis"), ("status", "Status"), ("summary", "Summary")],
    "Activities": [("project_name", "Project"), ("name", "Activity"), ("owner", "Owner"), ("weight", "Weight"), ("progress", "Progress %"), ("status", "Status"), ("due_date", "Due")],
    "Reports": [("project_name", "Project"), ("report_date", "Date"), ("report_type", "Type"), ("title", "Title"), ("workforce", "Workforce"), ("progress", "Progress %"), ("weather", "Weather"), ("summary", "Summary"), ("next_steps", "Next steps"), ("created_by_name", "By")],
    "Issues": [("project_name", "Project"), ("title", "Title"), ("category", "Category"), ("severity", "Severity"), ("owner", "Owner"), ("due_date", "Due"), ("status", "Status"), ("description", "Description")],
}


RISKY = ("=", "+", "-", "@", "\t", "\r", "|", "%")


def _e(v):
    return escape(str(v if v is not None else "")).replace("\n", "<br/>")


def build_xlsx(data):
    wb = Workbook()
    wb.remove(wb.active)
    for sheet, cols in COLUMNS.items():
        ws = wb.create_sheet(sheet)
        ws.append([c[1] for c in cols])
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="D97706")
        for row in data[sheet.lower()]:
            ws.append([row.get(k, "") for k, _ in cols])
            for c in ws[ws.max_row]:
                if isinstance(c.value, str) and c.value[:1] in RISKY:
                    c.data_type, c.quotePrefix = "s", True
        for i, (k, label) in enumerate(cols):
            ws.column_dimensions[chr(65 + i)].width = 40 if k in ("summary", "description", "next_steps") else max(12, len(label) + 4)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _table(rows, cols, widths, cell):
    body = [[Paragraph(f"<b>{label}</b>", cell) for _, label in cols]]
    body += [[Paragraph(_e(r.get(k, "")) or "—", cell) for k, _ in cols] for r in rows]
    t = Table(body, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fef3c7")), ("LINEBELOW", (0, 0), (-1, 0), 1, AMBER),
                           ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#e2e8f0")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    return t


def build_pdf(data):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=16 * mm, bottomMargin=16 * mm, title=data["title"])
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], alignment=0, textColor=INK, fontSize=20, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=INK, fontSize=13, spaceBefore=12, spaceAfter=6)
    meta = ParagraphStyle("meta", parent=ss["Normal"], textColor=colors.HexColor("#64748b"), fontSize=9)
    cell = ParagraphStyle("cell", parent=ss["Normal"], fontSize=8, leading=10)
    story = [Paragraph("CIVICPRO · FIELD COMMAND", ParagraphStyle("brand", parent=meta, textColor=AMBER)), Paragraph(_e(data["title"]), h1),
             Paragraph(f"{data['period_label']} · Generated {data['generated_at']}", meta), Spacer(1, 8)]
    for i, p in enumerate(data["projects"]):
        if i:
            story.append(PageBreak())
        story += [Paragraph(f"{_e(p.get('code'))} — {_e(p.get('name'))}", h2),
                  Paragraph(f"{_e(p.get('location'))} · Client: {_e(p.get('client')) or '—'} · Status: {_e(p.get('status'))} · <b>{p.get('progress', 0)}% complete</b> ({p.get('progress_mode', 'manual')} basis)", meta)]
        if p.get("planned_progress") is not None:
            v = p["schedule_variance"]
            story.append(Paragraph(f"Schedule {_e(p.get('start_date'))} → {_e(p.get('end_date'))} · Planned today {p['planned_progress']}% · Actual {p['progress']}% · <b>{'+' if v >= 0 else ''}{v}% {'ahead of' if v >= 0 else 'behind'} plan</b>", meta))
        if p.get("summary"):
            story += [Spacer(1, 4), Paragraph(_e(p["summary"]), cell)]
        for key, widths in (("activities", [0, 52, 30, 14, 18, 26, 22]), ("reports", [0, 20, 14, 30, 14, 14, 0, 50, 0, 0]), ("issues", [0, 40, 18, 16, 26, 20, 18, 40])):
            cols = [c for c, w in zip(COLUMNS[key.capitalize()], widths) if w]
            rows = [r for r in data[key] if r.get("project_id") == p["id"]]
            story.append(Paragraph(f"{key.capitalize()} ({len(rows)})", h2))
            story.append(_table(rows, cols, [w * mm for w in widths if w], cell) if rows else Paragraph("No records in this period.", meta))
    if not data["projects"]:
        story.append(Paragraph("No projects to report.", meta))
    doc.build(story)
    return buf.getvalue()

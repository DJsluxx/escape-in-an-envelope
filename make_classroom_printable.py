#!/usr/bin/env python3
"""make_classroom_printable.py — build the free CLASSROOM lead-magnet PDF.

free/classroom-escape-room.pdf : a whole-class, no-locks, 45-minute escape room for
grades 3-6, run as five stations for 25-30 students. Content lives in
classroom_puzzle.json. Mirrors make_free_printable.py (same palette, same footer, same
reportlab flowable style) so the two free printables look like one product line.

The teacher audience is the one audience this company holds hard purchase evidence for,
and until this file existed every teacher who arrived from Pinterest landed on a page to
READ with nothing to take.

    python make_classroom_printable.py
"""
from __future__ import annotations
import json
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                PageBreak, HRFlowable)

ROOT = Path(__file__).resolve().parent
SHOP = "salama62.gumroad.com  ·  escapeinanenvelop.etsy.com"
PRIMARY = colors.HexColor("#3d3a5c")
ACCENT = colors.HexColor("#c9a227")
INK = colors.HexColor("#2b2740")
BAND = colors.HexColor("#e7e0cf")
PAPER = colors.HexColor("#faf7f0")
MUTED = colors.HexColor("#6b6680")

CONTENT_WIDTH = 6.3 * inch


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawCentredString(
        letter[0] / 2, 0.45 * inch,
        f"Free classroom escape room from Escape in an Envelope  ·  full themed kits at {SHOP}")
    canvas.restoreState()


def _styles():
    s = getSampleStyleSheet()
    st = {}
    st["h1"] = ParagraphStyle("h1", parent=s["Title"], textColor=PRIMARY, fontSize=27,
                              leading=32, spaceAfter=4)
    st["sub"] = ParagraphStyle("sub", parent=s["Normal"], textColor=ACCENT, fontSize=12,
                               alignment=1, spaceAfter=14, fontName="Helvetica-Bold",
                               leading=16)
    st["h2"] = ParagraphStyle("h2", parent=s["Heading2"], textColor=PRIMARY, fontSize=16,
                              spaceBefore=6, spaceAfter=6)
    st["body"] = ParagraphStyle("body", parent=s["Normal"], textColor=INK, fontSize=11,
                                leading=15.5, spaceAfter=8)
    st["read"] = ParagraphStyle("read", parent=st["body"], backColor=PAPER,
                                borderColor=BAND, borderWidth=1, borderPadding=10,
                                fontSize=11.5, leading=16)
    st["small"] = ParagraphStyle("small", parent=st["body"], fontSize=9.5, leading=13,
                                 textColor=MUTED)
    st["station_h"] = ParagraphStyle("station_h", parent=s["Title"], textColor=PRIMARY,
                                     fontSize=30, leading=34, alignment=1, spaceAfter=2)
    st["station_sub"] = ParagraphStyle("station_sub", parent=st["small"], alignment=1,
                                       fontSize=12, textColor=ACCENT,
                                       fontName="Helvetica-Bold", spaceAfter=12)
    st["task"] = ParagraphStyle("task", parent=st["body"], fontSize=13, leading=19)
    st["cert_big"] = ParagraphStyle("cert_big", parent=st["h1"], fontSize=32, alignment=1,
                                    spaceAfter=8)
    st["cert_body"] = ParagraphStyle("cert_body", parent=st["body"], alignment=1,
                                     fontSize=13, leading=19)
    return st


def _boxed(flowables, border=BAND, width=1.2, bg=colors.white, pad=14):
    t = Table([[f] for f in flowables], colWidths=[CONTENT_WIDTH])
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), width, border),
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LEFTPADDING", (0, 0), (-1, -1), pad),
        ("RIGHTPADDING", (0, 0), (-1, -1), pad),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


def build_pdf(pz: dict, out: Path) -> Path:
    st = _styles()
    doc = SimpleDocTemplate(
        str(out), pagesize=letter,
        leftMargin=0.85 * inch, rightMargin=0.85 * inch,
        topMargin=0.7 * inch, bottomMargin=0.8 * inch,
        title="Free Classroom Escape Room (Grades 3-6, No Locks)",
        author="Escape in an Envelope")
    F = []

    # ---------------- PAGE 1 — cover + timeline -----------------------------
    F.append(Paragraph("The Lost Library Code", st["h1"]))
    F.append(Paragraph(pz["subtitle"], st["sub"]))
    F.append(HRFlowable(color=BAND, thickness=1.4, spaceAfter=12))
    F.append(Paragraph(pz["premise"], st["read"]))
    F.append(Spacer(1, 14))
    F.append(Paragraph("What is in this pack", st["h2"]))
    F.append(Paragraph(
        "Everything you need is in these pages and nothing else is required. "
        "<b>Five station signs</b> (one per page, print and put one on each table), a "
        "<b>Code Tracker</b> for each group, a <b>teacher Answer Key</b> to cut into five "
        "strips, and a <b>class certificate</b>. Print on plain paper in black and white if "
        "you like. There is nothing to laminate, nothing to buy and no padlock anywhere.",
        st["body"]))
    F.append(Spacer(1, 8))
    F.append(Paragraph("The 45-minute plan", st["h2"]))
    rows = [[Paragraph(f"<b>{a}</b>", st["body"]), Paragraph(b, st["body"])]
            for a, b in pz["timeline"]]
    t = Table(rows, colWidths=[1.1 * inch, CONTENT_WIDTH - 1.1 * inch])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.6, BAND),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
    ]))
    F.append(t)
    F.append(PageBreak())

    # ---------------- PAGE 2 — teacher setup --------------------------------
    F.append(Paragraph("Teacher setup", st["h1"]))
    F.append(Paragraph("Five minutes, plain paper, no locks", st["sub"]))
    F.append(HRFlowable(color=BAND, thickness=1.4, spaceAfter=12))
    F.append(Paragraph(pz["teacher_setup"], st["body"]))
    F.append(Spacer(1, 10))
    F.append(Paragraph("Differentiation", st["h2"]))
    F.append(Paragraph(pz["differentiation"], st["body"]))
    F.append(Spacer(1, 10))
    F.append(_boxed([
        Paragraph("Resetting for the next period", ParagraphStyle(
            "rh", parent=st["h2"], fontSize=13, spaceBefore=0, spaceAfter=4)),
        Paragraph(pz["reset_note"], st["body"]),
    ], border=ACCENT, width=1.4, bg=PAPER))
    F.append(PageBreak())

    # ---------------- PAGE 3 — read aloud -----------------------------------
    F.append(Paragraph("Read this aloud to start", st["h1"]))
    F.append(Paragraph("Roughly two minutes, standing at the front", st["sub"]))
    F.append(HRFlowable(color=BAND, thickness=1.4, spaceAfter=12))
    F.append(Paragraph(pz["story_intro"], st["read"]))
    F.append(Spacer(1, 14))
    F.append(Paragraph(
        "Then hand each group a Code Tracker, point each group at a different station, and "
        "start the clock. All five stations run at the same time — no group waits.",
        st["small"]))
    F.append(PageBreak())

    # ---------------- PAGES 4-8 — station signs -----------------------------
    for s in pz["stations"]:
        F.append(Spacer(1, 0.25 * inch))
        F.append(Paragraph(f"STATION {s['n']}", st["station_sub"]))
        F.append(Paragraph(s["name"], st["station_h"]))
        F.append(Paragraph(s["subject"], st["station_sub"]))
        F.append(HRFlowable(color=ACCENT, thickness=2, width="45%", spaceBefore=4,
                            spaceAfter=16))
        F.append(_boxed([Paragraph(s["task"], st["task"])], border=BAND, width=1.4))
        F.append(Spacer(1, 16))
        F.append(_boxed([Paragraph(
            "<b>Our answer:</b> ________________________________________________"
            "<br/><br/><font color='#6b6680'>Show this to your teacher. If it is right, you "
            "will be given <b>one digit</b> — write it on your Code Tracker next to "
            f"Station {s['n']}.</font>",
            st["body"])], border=PRIMARY, width=1.2, bg=PAPER))
        F.append(Spacer(1, 14))
        F.append(Paragraph(f"<b>Finished early?</b> {s['bonus']}", st["small"]))
        F.append(PageBreak())

    # ---------------- PAGE 9 — code tracker ---------------------------------
    F.append(Paragraph("Code Tracker", st["h1"]))
    F.append(Paragraph("One per group · write each digit the moment you earn it", st["sub"]))
    F.append(HRFlowable(color=BAND, thickness=1.4, spaceAfter=14))
    F.append(Paragraph("Group name: ______________________________________", st["body"]))
    F.append(Spacer(1, 14))
    head = [Paragraph(f"<b>{h}</b>", st["body"]) for h in ("Station", "What we solved", "Digit earned")]
    trows = [head]
    for s in pz["stations"]:
        trows.append([
            Paragraph(f"<b>{s['n']}</b><br/><font size=8 color='#6b6680'>{s['name']}</font>",
                      st["body"]),
            Paragraph("", st["body"]),
            Paragraph("", st["body"]),
        ])
    t = Table(trows, colWidths=[1.7 * inch, 3.0 * inch, CONTENT_WIDTH - 4.7 * inch],
              rowHeights=[0.32 * inch] + [0.72 * inch] * len(pz["stations"]))
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.8, BAND),
        ("BACKGROUND", (0, 0), (-1, 0), PAPER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    F.append(t)
    F.append(Spacer(1, 18))
    F.append(_boxed([Paragraph(
        "<b>THE FULL CODE</b> — fill this in with the class at the end, in station order:"
        "<br/><br/><font size=22 color='#3d3a5c'><b>"
        "[ ____ ]&nbsp;&nbsp;[ ____ ]&nbsp;&nbsp;[ ____ ]&nbsp;&nbsp;[ ____ ]&nbsp;&nbsp;"
        "[ ____ ]</b></font>", st["body"])], border=ACCENT, width=1.6, bg=PAPER))
    F.append(PageBreak())

    # ---------------- PAGE 10 — answer key ----------------------------------
    F.append(Paragraph("Teacher Answer Key", st["h1"]))
    F.append(Paragraph("Cut into five strips · keep all five with you · students never see this page",
                       st["sub"]))
    F.append(HRFlowable(color=BAND, thickness=1.4, spaceAfter=14))
    for s in pz["stations"]:
        F.append(_boxed([
            Paragraph(f"<b>STATION {s['n']} — {s['name']}</b>", st["body"]),
            Paragraph(f"<b>Correct answer:</b> {s['answer']}", st["body"]),
            Paragraph(
                f"<b>Digit to give:</b> <font size=17 color='#c9a227'><b>{s['yields_digit']}"
                "</b></font>", st["body"]),
            Paragraph(s["swap"], st["small"]),
        ], border=BAND, width=1.0))
        F.append(Spacer(1, 9))
    F.append(Spacer(1, 6))
    F.append(_boxed([Paragraph(
        f"<b>FULL CODE: {pz['final_code']}</b>", ParagraphStyle(
            "fc", parent=st["body"], fontSize=17, textColor=PRIMARY)),
        Paragraph(pz["final_instruction"], st["body"]),
    ], border=ACCENT, width=1.6, bg=PAPER))
    F.append(PageBreak())

    # ---------------- PAGE 11 — certificate ---------------------------------
    F.append(Spacer(1, 0.9 * inch))
    F.append(Paragraph("The Archive Is Open", st["cert_big"]))
    F.append(HRFlowable(color=ACCENT, thickness=2, width="60%", spaceBefore=8, spaceAfter=18))
    F.append(Paragraph("This certifies that", st["cert_body"]))
    F.append(Spacer(1, 10))
    F.append(Paragraph("______________________________________________", st["cert_body"]))
    F.append(Spacer(1, 14))
    F.append(Paragraph(pz["certificate_line"], st["cert_body"]))
    F.append(Spacer(1, 26))
    F.append(Paragraph("is hereby appointed a <b>Certified Archivist</b>.", st["cert_body"]))
    F.append(Spacer(1, 30))
    F.append(Paragraph("Signed ____________________________    Date ______________",
                       st["cert_body"]))
    F.append(Spacer(1, 40))
    F.append(Paragraph(
        "Ran well? There are 13 fully illustrated themed escape rooms — dinosaurs, space, "
        "pirates, unicorns and more — each with six puzzles, station signs, a host guide and "
        "certificates, age-banded from 4 to 9.", st["small"]))
    F.append(Paragraph(f"<b>{SHOP}</b>", ParagraphStyle(
        "shop", parent=st["small"], alignment=1, textColor=PRIMARY, fontSize=11)))

    doc.build(F, onFirstPage=_footer, onLaterPages=_footer)
    return out


def main():
    pz = json.loads((ROOT / "classroom_puzzle.json").read_text(encoding="utf-8"))

    # Integrity gate: the printed final code must be exactly the station digits in order.
    digits = "".join(s["yields_digit"] for s in pz["stations"])
    if digits != pz["final_code"]:
        raise SystemExit(
            f"ABORT: station digits {digits!r} do not spell final_code {pz['final_code']!r}")

    out = ROOT / "free" / "classroom-escape-room.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    build_pdf(pz, out)
    print(f"wrote {out}  ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()

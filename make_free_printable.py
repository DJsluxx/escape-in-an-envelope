#!/usr/bin/env python3
"""make_free_printable.py — build the free lead-magnet assets for the site.

1. free/mini-escape-room.pdf : a print-at-home 3-puzzle mini escape room (the free taster
   offered on /guides/free-printable-escape-room-for-kids.html). Content from free_puzzle.json.
   Every page footers the shop URL, so each printed copy quietly markets the paid themed kits.
2. pins/free-printable-pin.png and pins/ultimate-guide-pin.png : 1000x1500 (2:3) Pinterest pins
   used as the og:image for the two pillar guide pages (Pinterest "Save from site" targets).

    python make_free_printable.py
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
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
SHOP = "salama62.gumroad.com  ·  escapeinanenvelop.etsy.com"
PRIMARY = colors.HexColor("#3d3a5c")
ACCENT = colors.HexColor("#c9a227")
INK = colors.HexColor("#2b2740")
BAND = colors.HexColor("#e7e0cf")
PAPER = colors.HexColor("#faf7f0")


# ----------------------------- PDF ------------------------------------------
def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#8a8598"))
    canvas.drawCentredString(letter[0] / 2, 0.45 * inch,
                             f"Free mini escape room from Escape in an Envelope  ·  full themed kits at {SHOP}")
    canvas.restoreState()


def build_pdf(pz: dict, out: Path):
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], textColor=PRIMARY, fontSize=30,
                        leading=34, spaceAfter=4)
    sub = ParagraphStyle("sub", parent=styles["Normal"], textColor=ACCENT, fontSize=13,
                         alignment=1, spaceAfter=14, fontName="Helvetica-Bold")
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=PRIMARY, fontSize=16,
                        spaceBefore=6, spaceAfter=6)
    body = ParagraphStyle("body", parent=styles["Normal"], textColor=INK, fontSize=11.5,
                          leading=16, spaceAfter=8)
    read = ParagraphStyle("read", parent=body, backColor=PAPER, borderColor=BAND,
                          borderWidth=1, borderPadding=10, fontSize=12)
    small = ParagraphStyle("small", parent=body, fontSize=10, textColor=colors.HexColor("#6b6680"))
    cert_big = ParagraphStyle("cert_big", parent=h1, fontSize=34, alignment=1, spaceAfter=8)
    cert_body = ParagraphStyle("cert_body", parent=body, alignment=1, fontSize=14, leading=20)

    doc = SimpleDocTemplate(str(out), pagesize=letter,
                            leftMargin=0.85 * inch, rightMargin=0.85 * inch,
                            topMargin=0.7 * inch, bottomMargin=0.8 * inch,
                            title="Free Mini Escape Room for Kids",
                            author="Escape in an Envelope")
    F = []
    F.append(Paragraph("🗝️ The 5-Minute Escape Room", h1))
    F.append(Paragraph(pz["title"], sub))
    F.append(HRFlowable(color=BAND, thickness=1.4, spaceAfter=12))
    F.append(Paragraph("<b>Read this aloud to start the adventure:</b>", body))
    F.append(Paragraph(pz["story_intro"], read))
    F.append(Spacer(1, 8))
    F.append(Paragraph("Grown-up setup (5 minutes)", h2))
    F.append(Paragraph(pz["host_setup"], body))
    F.append(Paragraph("How to play: kids solve each puzzle to earn one digit. Put the three digits "
                       "together to unlock the final treat box. That's it!", small))
    F.append(PageBreak())

    F.append(Paragraph("The three puzzles", h2))
    F.append(Paragraph("Cut these out or lay the page flat. Each puzzle reveals one digit of the code.", small))
    F.append(Spacer(1, 6))
    for p in pz["puzzles"]:
        rows = [
            [Paragraph(f'<b>Puzzle {p["n"]}: {p["name"]}</b>', ParagraphStyle(
                "pt", parent=h2, fontSize=14, textColor=PRIMARY, spaceAfter=2))],
            [Paragraph(p["instructions"], body)],
            [Paragraph(f'<b>You need:</b> {p["materials"]}', small)],
            [Paragraph(f'<b>Answer:</b> {p["answer"]} &nbsp;→&nbsp; write this digit: '
                       f'<font color="#c9a227"><b>[ &nbsp; {p["yields_digit"]} &nbsp; ]</b></font>', body)],
        ]
        t = Table(rows, colWidths=[6.3 * inch])
        t.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1.2, BAND),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        F.append(t)
        F.append(Spacer(1, 12))
    F.append(Spacer(1, 6))
    code_tbl = Table([[Paragraph(
        f'🔓 <b>Final code: {pz["final_code"]}</b> &nbsp;—&nbsp; {pz["final_instruction"]}',
        ParagraphStyle("code", parent=body, fontSize=13, textColor=PRIMARY))]], colWidths=[6.3 * inch])
    code_tbl.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1.6, ACCENT),
        ("BACKGROUND", (0, 0), (-1, -1), PAPER),
        ("LEFTPADDING", (0, 0), (-1, -1), 14), ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    F.append(code_tbl)
    F.append(PageBreak())

    # Certificate page
    F.append(Spacer(1, 1.2 * inch))
    F.append(Paragraph("🏅", cert_big))
    F.append(Paragraph("You Escaped!", cert_big))
    F.append(HRFlowable(color=ACCENT, thickness=2, width="60%", spaceBefore=8, spaceAfter=18))
    F.append(Paragraph(pz["certificate_line"], cert_body))
    F.append(Spacer(1, 24))
    F.append(Paragraph("This certifies that ______________________________ cracked the code "
                       "and completed the escape room.", cert_body))
    F.append(Spacer(1, 40))
    F.append(Paragraph("Loved it? There are 13 full illustrated escape rooms — dinosaurs, space, "
                       "pirates, unicorns and more — each with 6 puzzles, zone signs and certificates.", small))
    F.append(Paragraph(f"<b>{SHOP}</b>", ParagraphStyle("shop", parent=small, alignment=1,
                                                        textColor=PRIMARY, fontSize=11)))

    doc.build(F, onFirstPage=_footer, onLaterPages=_footer)
    return out


# ----------------------------- PINS -----------------------------------------
def _font(names, size):
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make_pin(out: Path, kicker: str, title: str, subtitle: str, emoji: str):
    W, H = 1000, 1500
    img = Image.new("RGB", (W, H), "#faf7f0")
    d = ImageDraw.Draw(img)
    # top band
    d.rectangle([0, 0, W, 300], fill="#3d3a5c")
    d.rectangle([0, 300, W, 316], fill="#c9a227")
    bold = ["arialbd.ttf", "C:/Windows/Fonts/arialbd.ttf", "Arialbd.ttf"]
    reg = ["arial.ttf", "C:/Windows/Fonts/arial.ttf", "Arial.ttf"]
    seg = ["seguiemj.ttf", "C:/Windows/Fonts/seguiemj.ttf"]
    f_kick = _font(bold, 40)
    f_title = _font(bold, 92)
    f_sub = _font(reg, 40)
    f_emoji = _font(seg + bold, 150)
    f_brand = _font(bold, 34)

    # brand in top band (plain text — Arial has no emoji glyphs)
    d.text((W / 2, 150), "ESCAPE IN AN ENVELOPE", font=f_brand, fill="#faf7f0", anchor="mm")

    # emoji medallion
    d.ellipse([W / 2 - 130, 360, W / 2 + 130, 620], fill="#ffffff", outline="#c9a227", width=6)
    d.text((W / 2, 490), emoji, font=f_emoji, fill="#3d3a5c", anchor="mm")

    # kicker
    d.text((W / 2, 700), kicker.upper(), font=f_kick, fill="#c9a227", anchor="mm")

    # title (wrapped)
    lines = _wrap(d, title, f_title, W - 120)
    y = 780
    for ln in lines:
        d.text((W / 2, y), ln, font=f_title, fill="#2b2740", anchor="mm")
        y += 104

    # subtitle
    y += 20
    for ln in _wrap(d, subtitle, f_sub, W - 160):
        d.text((W / 2, y), ln, font=f_sub, fill="#6b6680", anchor="mm")
        y += 52

    # bottom ribbon
    d.rectangle([0, H - 150, W, H], fill="#3d3a5c")
    d.text((W / 2, H - 75), "Free guide · print at home · ages 4–9", font=f_sub, fill="#faf7f0", anchor="mm")
    img.save(out, "PNG")
    return out


def main():
    pz = json.loads((ROOT / "free_puzzle.json").read_text(encoding="utf-8"))
    (ROOT / "free").mkdir(exist_ok=True)
    (ROOT / "pins").mkdir(exist_ok=True)
    build_pdf(pz, ROOT / "free" / "mini-escape-room.pdf")
    make_pin(ROOT / "pins" / "free-printable-pin.png",
             "Free printable", "Free Printable Escape Room for Kids",
             "A 5-minute, no-prep mini escape room you can run today", "🗝️")
    make_pin(ROOT / "pins" / "ultimate-guide-pin.png",
             "Step-by-step", "How to Make a Kids Escape Room at Home",
             "The complete parent's guide — puzzles, setup & timing by age", "🔐")
    print("Built free/mini-escape-room.pdf + 2 pillar pins.")


if __name__ == "__main__":
    main()

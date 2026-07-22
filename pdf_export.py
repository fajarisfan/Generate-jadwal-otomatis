"""Export jadwal ke PDF, format meniru template asli RSUD Kota Cilegon."""
import calendar
from io import BytesIO

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

from scheduler import SHIFT_COLORS, is_holiday, get_holiday_name

BULAN_ID = [
    "", "JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI",
    "JULI", "AGUSTUS", "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER",
]

def export_jadwal_pdf(year, month, staff_order, schedule, days_in_month,
                       kepala_unit_nama="ISTIQOMAH, S.Kom",
                       kepala_unit_nip="19940929 202321 2 041"):
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=10 * mm, rightMargin=10 * mm, topMargin=8 * mm, bottomMargin=8 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Normal"], alignment=TA_CENTER, fontSize=11, leading=13, fontName="Helvetica-Bold")
    sub_style = ParagraphStyle("sub", parent=styles["Normal"], alignment=TA_CENTER, fontSize=10, leading=12, fontName="Helvetica-Bold")
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=7, leading=9)
    right_style = ParagraphStyle("right", parent=styles["Normal"], alignment=TA_RIGHT, fontSize=9, leading=11)

    story = []
    story.append(Paragraph("JADWAL JAGA DI UNIT SIRS", title_style))
    story.append(Paragraph("RSUD KOTA CILEGON", sub_style))
    story.append(Paragraph(f"BULAN {BULAN_ID[month]} {year}", sub_style))
    story.append(Spacer(1, 6))

    header = ["NO", "NAMA"] + [str(d) for d in range(1, days_in_month + 1)]
    data = [header]
    for i, name in enumerate(staff_order, start=1):
        row = [str(i), name] + list(schedule[name])
        data.append(row)

    no_w = 8 * mm
    nama_w = 42 * mm
    remaining = landscape(A4)[0] - doc.leftMargin - doc.rightMargin - no_w - nama_w
    day_w = remaining / days_in_month
    col_widths = [no_w, nama_w] + [day_w] * days_in_month

    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (1, 1), (1, -1), "LEFT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]
    
    for r, name in enumerate(staff_order, start=1):
        for c, code in enumerate(schedule[name], start=2):
            day = c - 1
            if is_holiday(day, month, year):
                style.append(("BACKGROUND", (c, r), (c, r), colors.HexColor("#FF6B6B")))
                style.append(("TEXTCOLOR", (c, r), (c, r), colors.white))
            else:
                hexcolor = SHIFT_COLORS.get(code, "#FFFFFF")
                style.append(("BACKGROUND", (c, r), (c, r), colors.HexColor(hexcolor)))

    tbl.setStyle(TableStyle(style))
    story.append(tbl)
    story.append(Spacer(1, 8))

    holiday_list = []
    for day in range(1, days_in_month + 1):
        if is_holiday(day, month, year):
            nama_libur = get_holiday_name(day, month, year)
            holiday_list.append(f"{day} {BULAN_ID[month]}: {nama_libur}")
    
    if holiday_list:
        story.append(Paragraph("Tanggal Merah / Libur bulan ini:", small))
        for h in holiday_list:
            story.append(Paragraph(f"• {h}", small))
        story.append(Spacer(1, 4))

    legend_lines = [
        "Keterangan:",
        "PS : Pagi Siang ( 5 hari kerja )&nbsp;&nbsp;&nbsp;&nbsp; P : Pagi&nbsp;&nbsp;&nbsp;&nbsp; S : Siang&nbsp;&nbsp;&nbsp;&nbsp; M : Malam&nbsp;&nbsp;&nbsp;&nbsp; C : Cuti&nbsp;&nbsp;&nbsp;&nbsp; - : Lepas Malam&nbsp;&nbsp;&nbsp;&nbsp; L : Libur",
        "Jam 08.00 WIB s/d 15.00 WIB",
        "Jam 15.00 WIB s/d 22.00 WIB",
        "Jam 22.00 WIB s/d 08.00 WIB",
        "Jam 08.00 WIB s/d 16.30 WIB",
        "",
        "🔴 Kotak merah = Hari Minggu / Tanggal Merah (Libur Nasional)",
    ]
    for line in legend_lines:
        story.append(Paragraph(line, small))

    story.append(Spacer(1, 14))
    last_day = days_in_month
    story.append(Paragraph(f"Cilegon, {last_day} {BULAN_ID[month]} {year}", right_style))
    story.append(Paragraph("Kepala Unit SIRS", right_style))
    story.append(Spacer(1, 22))
    story.append(Paragraph(f"<u>{kepala_unit_nama}</u>", right_style))
    story.append(Paragraph(f"NIP. {kepala_unit_nip}", right_style))

    doc.build(story)
    buf.seek(0)
    return buf

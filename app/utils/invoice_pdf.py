import io
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT

ASPHALT = colors.HexColor("#1B1F27")
AMBER = colors.HexColor("#F5A623")
GREY = colors.HexColor("#6B7280")
LIGHT = colors.HexColor("#F1F2F4")

BUSINESS_NAME = os.environ.get("BUSINESS_NAME", "AutoLot237")
BUSINESS_ADDRESS = os.environ.get("BUSINESS_ADDRESS", "Douala, Cameroon")
BUSINESS_PHONE = os.environ.get("BUSINESS_PHONE", "+237 6XX XXX XXX")
BUSINESS_EMAIL = os.environ.get("BUSINESS_EMAIL", "sales@autolot237.com")
CURRENCY_SYMBOL = os.environ.get("CURRENCY_SYMBOL", "CFA")


def _money(amount):
    return f"{amount:,.0f} {CURRENCY_SYMBOL}"


def generate_invoice_pdf(order):
    """Returns a BytesIO buffer containing a rendered PDF invoice for the given Order."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=18 * mm, bottomMargin=18 * mm, leftMargin=18 * mm, rightMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("InvTitle", parent=styles["Title"], textColor=ASPHALT, fontSize=22, spaceAfter=0)
    label_style = ParagraphStyle("InvLabel", parent=styles["Normal"], textColor=GREY, fontSize=9)
    value_style = ParagraphStyle("InvValue", parent=styles["Normal"], textColor=ASPHALT, fontSize=11, leading=15)
    right_value = ParagraphStyle("InvValueR", parent=value_style, alignment=TA_RIGHT)
    small = ParagraphStyle("Small", parent=styles["Normal"], textColor=GREY, fontSize=8)

    story = []

    header_table = Table(
        [[
            Paragraph(f"<b>{BUSINESS_NAME}</b>", title_style),
            Paragraph(
                f"<b>INVOICE</b><br/>#{order.order_number}<br/>"
                f"{order.created_at.strftime('%d %b %Y')}",
                right_value,
            ),
        ]],
        colWidths=[100 * mm, 72 * mm],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(header_table)
    story.append(Paragraph(f"{BUSINESS_ADDRESS} &nbsp;|&nbsp; {BUSINESS_PHONE} &nbsp;|&nbsp; {BUSINESS_EMAIL}", small))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=2, color=AMBER))
    story.append(Spacer(1, 10))

    bill_to = Table(
        [[
            Paragraph(
                f"<b>BILL TO</b><br/>{order.customer.full_name}<br/>{order.customer.phone}"
                f"{'<br/>' + order.customer.email if order.customer.email else ''}",
                value_style,
            ),
            Paragraph(
                f"<b>STATUS</b><br/>{order.status_label}<br/>"
                f"<b>FULFILLMENT</b><br/>{order.fulfillment_type.title()}",
                right_value,
            ),
        ]],
        colWidths=[100 * mm, 72 * mm],
    )
    story.append(bill_to)
    story.append(Spacer(1, 14))

    rows = [["VEHICLE", "LISTING CODE", "QTY", "PRICE", "TOTAL"]]
    for item in order.items:
        rows.append([
            item.car_listing.title if item.car_listing else "Vehicle",
            item.car_listing.listing_code if item.car_listing else "-",
            str(item.quantity),
            _money(item.unit_price),
            _money(item.line_total),
        ])

    items_table = Table(rows, colWidths=[70 * mm, 30 * mm, 15 * mm, 28 * mm, 29 * mm])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ASPHALT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 9.5),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, ASPHALT),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 10))

    totals = Table(
        [
            ["Subtotal", _money(order.subtotal)],
            ["Amount Paid", _money(order.amount_paid)],
            ["Balance Due", _money(order.balance_due)],
        ],
        colWidths=[142 * mm, 30 * mm],
    )
    totals.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 2), (-1, 2), 13),
        ("TEXTCOLOR", (0, 2), (-1, 2), ASPHALT),
        ("LINEABOVE", (0, 2), (-1, 2), 1, AMBER),
        ("TOPPADDING", (0, 2), (-1, 2), 8),
    ]))
    story.append(totals)
    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GREY))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"Thank you for buying with {BUSINESS_NAME}. This invoice confirms your order; "
        f"vehicle handover happens after payment is verified. Questions? WhatsApp us at {BUSINESS_PHONE}.",
        small,
    ))

    doc.build(story)
    buf.seek(0)
    return buf

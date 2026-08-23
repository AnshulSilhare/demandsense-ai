"""
DemandSense AI — Executive PDF Report Generator
================================================
Generates publication-quality 1-page PDF executive briefs for supply chain procurement managers.

Author: Anshul Silhare
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


def generate_executive_pdf_bytes(sku_info: dict, region_name: str, impact_data: dict, winning_model: str, mape_val: float = 0.0, llm_report: dict = None, winning_mape: float = None) -> bytes:
    """
    Generate a 1-page executive PDF brief as in-memory bytes for Streamlit download.
    """
    if winning_mape is not None:
        mape_val = winning_mape
    if llm_report is None:
        llm_report = {}
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )

    story = []
    styles = getSampleStyleSheet()

    # Custom Color Palette
    primary_color = colors.HexColor("#1E3A5F")  # Navy
    secondary_color = colors.HexColor("#0D9488")  # Teal
    dark_neutral = colors.HexColor("#0F172A")
    light_bg = colors.HexColor("#F8FAFC")
    accent_border = colors.HexColor("#E2E8F0")

    p_level = llm_report.get("priority_level", "HEALTHY")
    if p_level == "CRITICAL":
        status_color = colors.HexColor("#DC2626")
        status_bg = colors.HexColor("#FEE2E2")
    elif p_level == "WARNING":
        status_color = colors.HexColor("#D97706")
        status_bg = colors.HexColor("#FEF3C7")
    else:
        status_color = colors.HexColor("#16A34A")
        status_bg = colors.HexColor("#DCFCE7")

    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=primary_color,
        spaceAfter=2
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=12
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=primary_color,
        spaceBefore=8,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=dark_neutral
    )

    badge_style = ParagraphStyle(
        'BadgeText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12,
        alignment=TA_CENTER,
        textColor=status_color
    )

    # 1. HEADER SECTION
    story.append(Paragraph("DEMANDSENSE AI — SUPPLY CHAIN CONTROL TOWER", title_style))
    story.append(Paragraph(f"EXECUTIVE PROCUREMENT BRIEF | Generated: {datetime.now().strftime('%d %b %Y, %H:%M IST')}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=secondary_color, spaceAfter=10))

    # 2. PRODUCT & STATUS METADATA TABLE
    status_paragraph = Paragraph(f"STATUS: {p_level}", badge_style)
    
    sku_title = sku_info.get('name', sku_info.get('sku_name', 'Product'))
    sku_code = sku_info.get('sku_id', 'SKU000')
    sku_cat = sku_info.get('category', 'General')
    sku_mrp = sku_info.get('base_price', 0)

    meta_data = [
        [
            Paragraph(f"<b>Product:</b> {sku_title} ({sku_code})", body_style),
            Paragraph(f"<b>Category:</b> {sku_cat}", body_style),
            Paragraph(f"<b>MRP:</b> ₹{sku_mrp}", body_style)
        ],
        [
            Paragraph(f"<b>Market Region:</b> {region_name}", body_style),
            Paragraph(f"<b>Best ML Model:</b> {winning_model} (MAPE {mape_val:.1f}%)", body_style),
            status_paragraph
        ]
    ]

    t_meta = Table(meta_data, colWidths=[200, 200, 140])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), light_bg),
        ('BOX', (0,0), (-1,-1), 1, accent_border),
        ('INNERGRID', (0,0), (-1,-1), 0.5, accent_border),
        ('BACKGROUND', (2,1), (2,1), status_bg),
        ('ALIGN', (2,1), (2,1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))

    # 3. TOP TELEMETRY KPI CARDS TABLE
    kpi_headers = [
        Paragraph("<b>30-DAY FORECAST</b>", ParagraphStyle('KPIH', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor("#64748B"), alignment=TA_CENTER)),
        Paragraph("<b>REORDER POINT (ROP)</b>", ParagraphStyle('KPIH', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor("#64748B"), alignment=TA_CENTER)),
        Paragraph("<b>PO TRIGGER DATE</b>", ParagraphStyle('KPIH', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor("#64748B"), alignment=TA_CENTER)),
        Paragraph("<b>REVENUE AT RISK</b>", ParagraphStyle('KPIH', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor("#64748B"), alignment=TA_CENTER))
    ]

    fcst_30d = impact_data.get('total_30d_forecast_units', impact_data.get('total_forecast_units_30d', 0))
    rop_units = impact_data.get('reorder_point_units', 0)
    po_date = impact_data.get('po_trigger_date', 'N/A')
    rev_risk = impact_data.get('revenue_at_risk_inr', 0.0)
    avg_daily = impact_data.get('avg_daily_forecast', impact_data.get('avg_daily_demand_units', 0))
    safety_stock = impact_data.get('safety_stock_units', 0)
    days_supply = impact_data.get('days_of_supply', 0)
    stockout_risk = impact_data.get('stockout_risk_units', 0)

    kpi_vals = [
        Paragraph(f"<font size=13 color='#1E3A5F'><b>{fcst_30d:,}</b></font><font size=8> units</font>", ParagraphStyle('KPIV', alignment=TA_CENTER)),
        Paragraph(f"<font size=13 color='#1E3A5F'><b>{rop_units:,}</b></font><font size=8> units</font>", ParagraphStyle('KPIV', alignment=TA_CENTER)),
        Paragraph(f"<font size=12 color='#0D9488'><b>{po_date}</b></font>", ParagraphStyle('KPIV', alignment=TA_CENTER)),
        Paragraph(f"<font size=13 color='#DC2626'><b>₹{rev_risk:,.0f}</b></font>", ParagraphStyle('KPIV', alignment=TA_CENTER))
    ]

    kpi_subs = [
        Paragraph(f"Avg Daily: {avg_daily:.1f} units", ParagraphStyle('KPIS', fontSize=7, leading=9, alignment=TA_CENTER, textColor=colors.HexColor("#64748B"))),
        Paragraph(f"Safety Stock: {safety_stock:,}", ParagraphStyle('KPIS', fontSize=7, leading=9, alignment=TA_CENTER, textColor=colors.HexColor("#64748B"))),
        Paragraph(f"Days of Supply: {days_supply} Days", ParagraphStyle('KPIS', fontSize=7, leading=9, alignment=TA_CENTER, textColor=colors.HexColor("#64748B"))),
        Paragraph(f"Stockout Risk: {stockout_risk:,} units", ParagraphStyle('KPIS', fontSize=7, leading=9, alignment=TA_CENTER, textColor=colors.HexColor("#64748B")))
    ]

    t_kpi = Table([kpi_headers, kpi_vals, kpi_subs], colWidths=[135, 135, 135, 135])
    t_kpi.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('BOX', (0,0), (-1,-1), 1, accent_border),
        ('INNERGRID', (0,0), (-1,-1), 0.5, accent_border),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 10))

    # 4. LLM PRESCRIPTIVE ANALYSIS SECTIONS
    story.append(Paragraph("📋 EXECUTIVE SUMMARY", section_heading))
    story.append(Paragraph(llm_report.get('executive_summary', 'N/A'), body_style))
    story.append(Spacer(1, 6))

    story.append(Paragraph("🛒 RECOMMENDED PROCUREMENT DIRECTIVE", section_heading))
    story.append(Paragraph(llm_report.get('recommended_action', llm_report.get('procurement_directive', 'N/A')), body_style))
    story.append(Spacer(1, 6))

    story.append(Paragraph("💰 FINANCIAL RISK & RUPEE IMPACT", section_heading))
    story.append(Paragraph(llm_report.get('financial_risk_narrative', llm_report.get('financial_risk', 'N/A')), body_style))
    story.append(Spacer(1, 6))

    story.append(Paragraph("🤖 AI MODEL RATIONALE", section_heading))
    story.append(Paragraph(llm_report.get('model_rationale', 'N/A'), body_style))
    story.append(Spacer(1, 12))

    # 5. FOOTER & CONFIDENTIALITY DISCLAIMER
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#CBD5E1"), spaceAfter=6))
    footer_text = "DemandSense AI Control Tower | Developed by Anshul Silhare | Welingkar Institute of Management (WeSchool)"
    story.append(Paragraph(footer_text, ParagraphStyle('Footer', fontName='Helvetica-Oblique', fontSize=7, leading=9, alignment=TA_CENTER, textColor=colors.HexColor("#94A3B8"))))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# Alias for backward compatibility across modules
generate_executive_pdf_report = generate_executive_pdf_bytes


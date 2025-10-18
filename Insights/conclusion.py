import os
import ast
import pandas as pd
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

# === Paths ===
try:
    project_root = Path(__file__).resolve().parents[1]
except NameError:
    project_root = Path.cwd()

csv_dir = project_root / "All_Analysis"
chart_dir = project_root / "Insights" / "charts"
output_path = Path.home() / "Downloads" / "Ecom_Full_Insights_Report.pdf"

# === PDF Styles ===
styles = getSampleStyleSheet()
section_style = styles['Heading2']
subsection_style = styles['Heading4']
normal_style = styles['Normal']
bullet_style = ParagraphStyle('bullet', fontSize=10, leftIndent=15, spaceAfter=6)
title_style = ParagraphStyle('Title', fontSize=24, alignment=1, spaceAfter=24)
subtitle_style = ParagraphStyle('Subtitle', fontSize=16, alignment=1, spaceAfter=12)

# === Elements container ===
elements = []

# === Helpers ===
def parse_value(value):
    if not isinstance(value, str):
        return value
    try:
        cleaned = value.replace('""', '"')
        return ast.literal_eval(cleaned)
    except:
        return value

def dict_to_table(d: dict, col_names=None):
    col_names = col_names or ["Key", "Value"]
    data = [col_names] + [[str(k), str(v)] for k,v in d.items()]
    for r in range(len(data)):
        for c in range(len(data[r])):
            data[r][c] = Paragraph(str(data[r][c]), normal_style)
    table = Table(data, hAlign='LEFT', repeatRows=1)
    table._argW = [450/len(col_names)]*len(col_names)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#d3d3d3")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
    ]))
    return table

def list_to_bullets(lst):
    bullets = []
    for item in lst:
        bullets.append(Paragraph(f"• {item}", bullet_style))
    return bullets

def add_section(title, df=None, chart_files=None, is_summary=False):
    elements.append(Paragraph(title, section_style))
    elements.append(Spacer(1,12))

    if df is not None and not df.empty:
        if is_summary:
            for _, row in df.iterrows():
                metric = row['Metric']
                value = parse_value(row['Value'])
                elements.append(Paragraph(metric, subsection_style))
                elements.append(Spacer(1,4))
                if isinstance(value, dict):
                    elements.append(dict_to_table(value))
                    elements.append(Spacer(1,6))
                elif isinstance(value, list):
                    if not value:
                        elements.append(Paragraph("No data available", normal_style))
                        elements.append(Spacer(1,6))
                    elif all(isinstance(i, dict) for i in value):
                        keys = value[0].keys()
                        table_data = [list(keys)]
                        for d in value:
                            table_data.append([str(d[k]) for k in keys])
                        for r in range(len(table_data)):
                            for c in range(len(table_data[r])):
                                table_data[r][c] = Paragraph(str(table_data[r][c]), normal_style)
                        table = Table(table_data, hAlign='LEFT', repeatRows=1)
                        table._argW = [450/len(table_data[0])]*len(table_data[0])
                        table.setStyle(TableStyle([
                            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#d3d3d3")),
                            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                            ('VALIGN',(0,0),(-1,-1),'TOP'),
                        ]))
                        elements.append(table)
                        elements.append(Spacer(1,6))
                    else:
                        elements.extend(list_to_bullets(value))
                        elements.append(Spacer(1,6))
                else:
                    elements.append(Paragraph(str(value), normal_style))
                    elements.append(Spacer(1,6))
        else:
            data = [df.columns.tolist()] + df.values.tolist()
            for r in range(len(data)):
                for c in range(len(data[r])):
                    data[r][c] = Paragraph(str(data[r][c]), normal_style)
            table = Table(data, hAlign='LEFT', repeatRows=1)
            table._argW = [450/len(data[0])]*len(data[0])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#d3d3d3")),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('ALIGN',(0,0),(-1,-1),'CENTER'),
                ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ]))
            elements.append(table)
            elements.append(Spacer(1,12))

    if chart_files:
        for chart_file in chart_files:
            chart_path = Path(chart_dir / chart_file).resolve()
            if chart_path.exists():
                elements.append(Paragraph("Related Chart:", normal_style))
                elements.append(Spacer(1,6))
                elements.append(Image(str(chart_path), width=6*inch, height=4*inch))
                elements.append(Spacer(1,12))
            else:
                elements.append(Paragraph(f"⚠️ Chart missing: {chart_file}", normal_style))
                elements.append(Spacer(1,6))

    elements.append(PageBreak())

def load_csv(file_path):
    if file_path.exists():
        return pd.read_csv(file_path)
    else:
        print(f"⚠️ File not found: {file_path}")
        return pd.DataFrame()

def main():
    # === Cover Page ===
    elements.append(Spacer(1,2*inch))
    elements.append(Paragraph("Ecommerce Analysis Report", title_style))
    elements.append(Paragraph("For", title_style))
    elements.append(Paragraph(" Muzammil Chairmen Sir", title_style))
    elements.append(Paragraph("Full Insights with Charts and Metrics", subtitle_style))
    elements.append(Spacer(1,0.5*inch))
    elements.append(Paragraph(f"Date: {datetime.today().strftime('%d-%b-%Y')}", normal_style))
    elements.append(PageBreak())

    # === Sections with charts ===
    add_section("Sales Analysis", load_csv(csv_dir / "sales_Analysis.csv"), chart_files=["sales_trend.png"])
    add_section("Customer Analysis", load_csv(csv_dir / "customer_Analysis.csv"), chart_files=["customer_insights.png","top_customers.png"], is_summary=True)
    add_section("Product Analysis", load_csv(csv_dir / "product_Analysis.csv"), chart_files=["abc_analysis.png","returns_rtos.png","top_products.png"], is_summary=True)
    add_section("Marketplace Analysis", load_csv(csv_dir / "marketplace_Analysis.csv"), chart_files=["platform_comparison.png"])
    add_section("GST Analysis", load_csv(csv_dir / "gst_Analysis.csv"), chart_files=["gst_summary.png"])
    add_section("Profit Analysis", load_csv(csv_dir / "profit_Analysis.csv"), chart_files=["pl_breakdown.png","profit_trend.png"])

    # === PDF Document Setup ===
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=30, leftMargin=30,
        topMargin=30, bottomMargin=30
    )

    # === Page Number Footer ===
    def add_page_number(canvas, doc):
        page_num = canvas.getPageNumber()
        text = f"Page {page_num}"
        canvas.setFont('Helvetica', 9)
        canvas.drawRightString(A4[0]-40, 20, text)

    # === Build PDF ===
    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)

    print(f"✅ Professional PDF generated in Downloads: {output_path}")


if __name__ == "__main__":
    main()

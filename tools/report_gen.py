from fpdf import FPDF
import datetime
import os

class AutoFlowPDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, 'STRATEGIC DATA ANALYSIS | AUTOFLOW INTELLIGENCE', 0, 1, 'R')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()} | Confidential Strategy Document', 0, 0, 'C')

def generate_pdf_report(filename, sections, stats=None):
    """
    Generate a high-quality professional PDF report.
    """
    pdf = AutoFlowPDF()
    pdf.add_page()
    
    # Hero Header Section
    pdf.set_fill_color(15, 23, 42) # slate-900 (Deep professional background)
    pdf.rect(0, 0, 210, 60, 'F')
    
    pdf.set_xy(15, 20)
    pdf.set_font('helvetica', 'B', 28)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 15, 'Data Insight Summary', 0, 1, 'L')
    
    pdf.set_font('helvetica', '', 12)
    pdf.set_text_color(56, 189, 248) # accent-blue
    pdf.cell(0, 10, 'Strategic Blueprint & Pattern Analysis', 0, 1, 'L')
    
    pdf.set_y(45)
    pdf.set_font('helvetica', 'B', 10)
    pdf.set_text_color(200, 200, 200)
    if stats:
        meta = f"SOURCE RECORDS: {stats.get('rows', 0):,} | ATTRIBUTES: {stats.get('cols', 0)} | SAMPLED: {stats.get('sampled', False)}"
        pdf.cell(0, 5, meta, 0, 1, 'L')
    
    pdf.set_y(70) # Move below hero

    for sec in sections:
        # Check for page break
        if pdf.get_y() > 240:
            pdf.add_page()
            pdf.set_y(20)

        # Section Header
        pdf.set_font('helvetica', 'B', 16)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 12, sec['title'], 0, 1, 'L')
        # Underline
        pdf.set_draw_color(56, 189, 248)
        pdf.set_line_width(0.5)
        pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 180, pdf.get_y())
        pdf.ln(8)
        
        pdf.set_text_color(50, 50, 50)
        
        if sec['type'] == 'list':
            pdf.set_font('helvetica', '', 11)
            for item in sec['content']:
                if pdf.get_y() > 260: pdf.add_page(); pdf.set_y(20)
                pdf.set_font('helvetica', 'B', 11)
                pdf.set_text_color(56, 189, 248)
                pdf.cell(5, 8, '>', 0, 0)
                pdf.set_font('helvetica', '', 11)
                pdf.set_text_color(50, 50, 50)
                pdf.multi_cell(0, 8, str(item))
        elif sec['type'] == 'image':
            if os.path.exists(sec['content']):
                try:
                    # Center image
                    image_width = 160
                    x_center = (210 - image_width) / 2
                    pdf.image(sec['content'], x=x_center, w=image_width)
                    pdf.ln(10)
                except Exception as e:
                    pdf.set_font('helvetica', 'I', 10)
                    pdf.cell(0, 10, f"[Image Error: {str(e)}]", 0, 1)
        else: # text
            pdf.set_font('helvetica', '', 12)
            pdf.multi_cell(0, 8, str(sec['content']))
        
        pdf.ln(12)
    
    output_path = f"outputs/{filename}"
    pdf.output(output_path)
    return output_path

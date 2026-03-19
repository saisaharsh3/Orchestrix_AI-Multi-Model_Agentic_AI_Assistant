"""
pdf_compare_tool.py - Compare two PDFs and generate summary reports
"""

import os
from fpdf import FPDF
from datetime import datetime

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)


# -- Text extraction ----------------------------------------------------------

def _extract_text(path: str) -> str:
    if not PYPDF_AVAILABLE:
        return ""
    try:
        reader = PdfReader(path)
        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        ).strip()
    except Exception as e:
        return f"Error reading {path}: {e}"


# -- Compare two PDFs ---------------------------------------------------------

def compare_pdfs(
    path1: str,
    path2: str,
    generate_llm_fn,
    model_type: str = "api",
) -> str:
    if not os.path.exists(path1):
        return f"Error: File not found: {path1}"
    if not os.path.exists(path2):
        return f"Error: File not found: {path2}"

    text1 = _extract_text(path1)
    text2 = _extract_text(path2)

    if text1.startswith("Error") or text2.startswith("Error"):
        return text1 if text1.startswith("Error") else text2

    # Truncate to fit in context
    text1 = text1[:3000]
    text2 = text2[:3000]

    name1 = os.path.basename(path1)
    name2 = os.path.basename(path2)

    prompt = (
        f"Compare these two documents and highlight:\n"
        f"1. Key differences in content or conclusions\n"
        f"2. Topics covered in one but not the other\n"
        f"3. Any contradictions between them\n"
        f"4. Common themes\n\n"
        f"Document 1 ({name1}):\n{text1}\n\n"
        f"Document 2 ({name2}):\n{text2}\n\n"
        f"Provide a structured comparison."
    )

    result = generate_llm_fn(prompt, model_type)
    return f"Comparison: {name1} vs {name2}\n\n{result}"


# -- Generate PDF summary report ----------------------------------------------

def generate_pdf_report(
    title: str,
    content: str,
    output_filename: str = None,
) -> str:
    try:
        from fpdf import FPDF
    except ImportError:
        return "Error: fpdf2 not installed. Run: pip install fpdf2"

    if output_filename is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"report_{ts}.pdf"

    output_path = os.path.join(REPORTS_DIR, output_filename)

    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # Title
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, title, ln=True, align="C")
        pdf.ln(4)

        # Date
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%B %d, %Y %I:%M %p')}", ln=True, align="C")
        pdf.ln(6)

        # Divider
        pdf.set_draw_color(180, 180, 180)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(6)

        # Content
        pdf.set_font("Helvetica", "", 11)
        # Handle encoding — replace non-latin chars
        safe_content = content.encode("latin-1", errors="replace").decode("latin-1")

        for line in safe_content.splitlines():
            line = line.strip()
            if not line:
                pdf.ln(3)
                continue

            # Bold for lines that look like headers (all caps or ending with :)
            if line.isupper() or (line.endswith(":") and len(line) < 60):
                pdf.set_font("Helvetica", "B", 11)
                pdf.multi_cell(0, 6, line)
                pdf.set_font("Helvetica", "", 11)
            else:
                pdf.multi_cell(0, 6, line)

        pdf.output(output_path)
        return output_path

    except Exception as e:
        return f"Error generating PDF report: {e}"


# -- Summarize a PDF and save as report ---------------------------------------

def summarize_pdf_to_report(
    pdf_path: str,
    generate_llm_fn,
    model_type: str = "api",
) -> str:
    if not os.path.exists(pdf_path):
        return f"Error: File not found: {pdf_path}"

    text = _extract_text(pdf_path)
    if text.startswith("Error"):
        return text

    text = text[:5000]
    name = os.path.basename(pdf_path)

    prompt = (
        f"Create a detailed summary report of this document.\n"
        f"Include: main topic, key sections, important findings, conclusions.\n"
        f"Format with clear section headings.\n\n"
        f"Document: {name}\n\n{text}"
    )

    summary = generate_llm_fn(prompt, model_type)
    output_path = generate_pdf_report(
        title=f"Summary Report: {name}",
        content=summary,
    )

    if output_path.startswith("Error"):
        return output_path

    return output_path
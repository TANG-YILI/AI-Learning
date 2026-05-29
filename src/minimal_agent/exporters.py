from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas


def markdown_to_pdf_bytes(markdown_text: str) -> bytes:
    """
    Render markdown-like plain text into a simple PDF.
    Keeps the export dependency lightweight and stable on Windows.
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 48
    cursor_y = height - margin

    # Built-in Chinese-capable font in ReportLab for CJK text.
    font_name = "STSong-Light"
    pdfmetrics.registerFont(UnicodeCIDFont(font_name))
    c.setFont(font_name, 11)

    lines = markdown_text.splitlines()
    max_width = width - 2 * margin
    line_height = 16

    for raw in lines:
        text_line = raw.strip() if raw.strip() else " "
        wrapped = simpleSplit(text_line, font_name, 11, max_width) or [" "]
        for piece in wrapped:
            if cursor_y < margin:
                c.showPage()
                c.setFont(font_name, 11)
                cursor_y = height - margin
            c.drawString(margin, cursor_y, piece)
            cursor_y -= line_height
        cursor_y -= 2

    c.save()
    return buffer.getvalue()

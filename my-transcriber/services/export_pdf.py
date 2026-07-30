from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

FONT_NAME = "HYSMyeongJo-Medium"
pdfmetrics.registerFont(UnicodeCIDFont(FONT_NAME))


def wrap_text_by_width(text, font_name, font_size, max_width):
    lines = []
    current_line = ""
    for char in text:
        test_line = current_line + char
        if pdfmetrics.stringWidth(test_line, font_name, font_size) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = char
    if current_line:
        lines.append(current_line)
    return lines


def export_pdf(paragraphs, output_path, title="강의 전사본"):
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    margin = 50
    max_text_width = width - (margin * 2)

    c.setFont(FONT_NAME, 16)
    c.drawString(margin, height - margin, title)

    font_size = 10.5
    c.setFont(FONT_NAME, font_size)
    y = height - margin - 45
    line_height = font_size * 1.5
    paragraph_gap = font_size * 1.0  # 단락 사이 추가 여백

    for para in paragraphs:
        wrapped_lines = wrap_text_by_width(para, FONT_NAME, font_size, max_text_width) or [""]

        for line in wrapped_lines:
            if y < margin:
                c.showPage()
                c.setFont(FONT_NAME, font_size)
                y = height - margin
            c.drawString(margin, y, line)
            y -= line_height

        y -= paragraph_gap  # 단락 끝나면 한 줄 더 띄우기

        if y < margin:
            c.showPage()
            c.setFont(FONT_NAME, font_size)
            y = height - margin

    c.save()
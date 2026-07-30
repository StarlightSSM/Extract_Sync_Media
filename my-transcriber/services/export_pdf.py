from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def export_pdf(text, output_path, title="강의 전사본"):
    # 한글 깨짐 방지를 위해 시스템 폰트 등록 (윈도우 맑은고딕 예시)
    pdfmetrics.registerFont(TTFont("Malgun", "C:/Windows/Fonts/malgun.ttf"))

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    c.setFont("Malgun", 14)
    c.drawString(50, height - 50, title)

    c.setFont("Malgun", 10)
    y = height - 90
    max_width = 90  # 줄바꿈 기준 글자 수 (대략)

    import textwrap
    for line in text.split("\n"):
        wrapped = textwrap.wrap(line, max_width) or [""]
        for wline in wrapped:
            if y < 50:
                c.showPage()
                c.setFont("Malgun", 10)
                y = height - 50
            c.drawString(50, y, wline)
            y -= 15

    c.save()
from docx import Document

def export_docx(text, output_path, title="강의 전사본"):
    doc = Document()
    doc.add_heading(title, level=1)
    doc.add_paragraph(text)
    doc.save(output_path)
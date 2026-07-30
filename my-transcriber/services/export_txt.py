def export_txt(text, output_path):
    with open(output_path, "w", encoding="utf-8-sig") as f:
        f.write(text)
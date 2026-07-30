import os
import threading
from flask import Flask, request, render_template, send_file, jsonify
from werkzeug.utils import secure_filename

from services.transcribe import transcribe_media
from services.export_txt import export_txt
from services.export_srt import export_srt
from services.export_docx import export_docx
from services.export_pdf import export_pdf

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
ALLOWED_EXTENSIONS = {"mp3", "mp4"}
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

latest_result = {"text": "", "segments": []}
progress_state = {"percent": 0, "status": "idle"}  # idle / processing / done / error


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def run_transcription(save_path):
    progress_state["status"] = "processing"
    progress_state["percent"] = 0
    try:
        def update(p):
            # 이전 값보다 클 때만 갱신 (역행 방지)
            if p > progress_state["percent"]:
                progress_state["percent"] = p

        text, segments = transcribe_media(save_path, progress_callback=update)
        latest_result["text"] = text
        latest_result["segments"] = segments
        progress_state["status"] = "done"
        progress_state["percent"] = 100
    except Exception as e:
        progress_state["status"] = "error"
        progress_state["error"] = str(e)

def group_into_paragraphs(segments, gap_threshold=2.0):
    """세그먼트 사이 침묵 간격이 gap_threshold(초) 이상이면 새 단락으로 분리"""
    if not segments:
        return []

    paragraphs = []
    current_paragraph = [segments[0]["text"]]

    for i in range(1, len(segments)):
        prev_end = segments[i - 1]["end"]
        curr_start = segments[i]["start"]
        gap = curr_start - prev_end

        if gap >= gap_threshold:
            paragraphs.append(" ".join(current_paragraph))
            current_paragraph = [segments[i]["text"]]
        else:
            current_paragraph.append(segments[i]["text"])

    if current_paragraph:
        paragraphs.append(" ".join(current_paragraph))

    return paragraphs

@app.route("/")
def home():
    paragraphs = group_into_paragraphs(latest_result["segments"])
    return render_template("index.html", text=latest_result["text"], paragraphs=paragraphs)


@app.route("/upload", methods=["POST"])
def upload():
    if "media" not in request.files:
        return "파일이 없습니다.", 400

    file = request.files["media"]

    if file.filename == "":
        return "파일을 선택하세요.", 400

    if not allowed_file(file.filename):
        return "mp3 또는 mp4 파일만 업로드 가능합니다.", 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(save_path)

    thread = threading.Thread(target=run_transcription, args=(save_path,))
    thread.start()

    return render_template("index.html", text="", paragraphs=[], processing=True)


@app.route("/progress")
def progress():
    return jsonify(progress_state)


@app.route("/download/<fmt>")
def download(fmt):
    text = latest_result["text"]
    segments = latest_result["segments"]

    if not text:
        return "먼저 전사를 진행하세요.", 400

    filename = f"result.{fmt}"
    output_path = os.path.join(OUTPUT_FOLDER, filename)

    if fmt == "txt":
        export_txt(text, output_path)
    elif fmt == "srt":
        export_srt(segments, output_path)
    elif fmt == "docx":
        paragraphs = group_into_paragraphs(segments)
        export_docx(paragraphs, output_path)
    elif fmt == "pdf":
        paragraphs = group_into_paragraphs(segments)
        export_pdf(paragraphs, output_path)
    else:
        return "지원하지 않는 형식입니다.", 400

    return send_file(output_path, as_attachment=True)


if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    app.run(debug=True)
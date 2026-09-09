import os
import threading
import atexit
import logging
from logging.handlers import RotatingFileHandler

from flask import Flask, request, render_template, send_file, jsonify
from werkzeug.utils import secure_filename

from services.transcribe import transcribe_media
from services.export_txt import export_txt
from services.export_srt import export_srt
from services.export_docx import export_docx
from services.export_pdf import export_pdf


# =========================================================
# Flask 기본 설정
# =========================================================

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "outputs")
LOG_FOLDER = os.path.join(BASE_DIR, "logs")

ALLOWED_EXTENSIONS = {"mp3", "mp4"}

# 최대 업로드 크기: 2GB
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024 * 1024

# =========================================================
# 폴더 자동 생성
# =========================================================

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(LOG_FOLDER, exist_ok=True)


# =========================================================
# Logging 설정
# =========================================================

LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | "
    "%(name)s | %(message)s"
)

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def create_logger(name, filename, level=logging.INFO):
    """
    로그 파일과 터미널에 동시에 로그를 출력하는 Logger를 생성합니다.
    로그 파일이 5MB를 넘으면 자동으로 백업합니다.
    """

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 중복 Handler 생성 방지
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        LOG_FORMAT,
        datefmt=DATE_FORMAT
    )

    # 파일 로그
    file_handler = RotatingFileHandler(
        os.path.join(LOG_FOLDER, filename),
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5,
        encoding="utf-8"
    )

    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # 터미널 로그
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# 서버 관련 로그
server_logger = create_logger(
    "server",
    "server.log",
    logging.INFO
)

# 오류 전용 로그
error_logger = create_logger(
    "error",
    "error.log",
    logging.ERROR
)

# 전사 작업 로그
transcription_logger = create_logger(
    "transcription",
    "transcription.log",
    logging.INFO
)


# =========================================================
# Flask/Werkzeug HTTP 로그도 server.log에 저장
# =========================================================

werkzeug_logger = logging.getLogger("werkzeug")

# Flask 기본 HTTP 로그가 터미널뿐 아니라 server.log에도 기록되도록 설정
if not any(
    isinstance(handler, RotatingFileHandler)
    for handler in werkzeug_logger.handlers
):
    werkzeug_handler = RotatingFileHandler(
        os.path.join(LOG_FOLDER, "server.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )

    werkzeug_handler.setFormatter(
        logging.Formatter(
            LOG_FORMAT,
            datefmt=DATE_FORMAT
        )
    )

    werkzeug_logger.addHandler(werkzeug_handler)

werkzeug_logger.setLevel(logging.INFO)


# =========================================================
# 전사 결과 상태
# =========================================================

latest_result = {
    "text": "",
    "segments": []
}

progress_state = {
    "percent": 0,
    "status": "idle",
    "error": ""
}

# 여러 스레드에서 동시에 상태를 변경할 때 충돌 방지
state_lock = threading.Lock()


# =========================================================
# 파일 확장자 확인
# =========================================================

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# =========================================================
# 전사 작업
# =========================================================

def run_transcription(save_path):
    """
    실제 음성 전사를 별도 스레드에서 실행합니다.
    """

    filename = os.path.basename(save_path)

    transcription_logger.info(
        "전사 작업 시작 | file=%s",
        filename
    )

    with state_lock:
        progress_state["status"] = "processing"
        progress_state["percent"] = 0
        progress_state["error"] = ""

    try:

        def update(p):
            """
            전사 진행률 업데이트
            """

            with state_lock:
                # 진행률이 뒤로 가지 않도록 처리
                if p > progress_state["percent"]:
                    progress_state["percent"] = p

        # 실제 전사 실행
        text, segments = transcribe_media(
            save_path,
            progress_callback=update
        )

        # 전사 결과 저장
        with state_lock:
            latest_result["text"] = text
            latest_result["segments"] = segments

            progress_state["status"] = "done"
            progress_state["percent"] = 100

        transcription_logger.info(
            "전사 작업 완료 | file=%s | segments=%d | text_length=%d",
            filename,
            len(segments),
            len(text)
        )

    except Exception as e:

        # 사용자 화면에 표시할 오류
        with state_lock:
            progress_state["status"] = "error"
            progress_state["error"] = str(e)

        # 상세 traceback까지 error.log에 기록
        error_logger.exception(
            "전사 작업 중 오류 발생 | file=%s",
            filename
        )

        transcription_logger.exception(
            "전사 작업 실패 | file=%s",
            filename
        )


# =========================================================
# 문단 분리
# =========================================================

def group_into_paragraphs(segments, gap_threshold=2.0):
    """
    세그먼트 사이 침묵 간격이 gap_threshold(초) 이상이면
    새로운 문단으로 분리합니다.
    """

    if not segments:
        return []

    paragraphs = []
    current_paragraph = [segments[0]["text"]]

    for i in range(1, len(segments)):

        prev_end = segments[i - 1]["end"]
        curr_start = segments[i]["start"]

        gap = curr_start - prev_end

        if gap >= gap_threshold:
            paragraphs.append(
                " ".join(current_paragraph)
            )

            current_paragraph = [
                segments[i]["text"]
            ]

        else:
            current_paragraph.append(
                segments[i]["text"]
            )

    if current_paragraph:
        paragraphs.append(
            " ".join(current_paragraph)
        )

    return paragraphs


# =========================================================
# 메인 페이지
# =========================================================

@app.route("/")
def home():

    try:

        with state_lock:
            segments = list(
                latest_result["segments"]
            )

            text = latest_result["text"]

        paragraphs = group_into_paragraphs(
            segments
        )

        return render_template(
            "index.html",
            text=text,
            paragraphs=paragraphs
        )

    except Exception:

        error_logger.exception(
            "메인 페이지 처리 중 오류 발생"
        )

        return "서버 오류가 발생했습니다.", 500


# =========================================================
# 파일 업로드
# =========================================================

@app.route("/upload", methods=["POST"])
def upload():

    try:

        if "media" not in request.files:

            server_logger.warning(
                "파일 업로드 실패 | 파일이 요청에 없음"
            )

            return "파일이 없습니다.", 400

        file = request.files["media"]

        if file.filename == "":

            server_logger.warning(
                "파일 업로드 실패 | 파일명이 없음"
            )

            return "파일을 선택하세요.", 400

        if not allowed_file(file.filename):

            server_logger.warning(
                "파일 업로드 실패 | 지원하지 않는 형식 | filename=%s",
                file.filename
            )

            return (
                "mp3 또는 mp4 파일만 업로드 가능합니다.",
                400
            )

        filename = secure_filename(
            file.filename
        )

        save_path = os.path.join(
            UPLOAD_FOLDER,
            filename
        )

        file.save(save_path)

        server_logger.info(
            "파일 업로드 완료 | file=%s",
            filename
        )

        # 전사 상태 초기화
        with state_lock:
            latest_result["text"] = ""
            latest_result["segments"] = []

            progress_state["percent"] = 0
            progress_state["status"] = "processing"
            progress_state["error"] = ""

        # 전사 작업을 별도 스레드에서 실행
        thread = threading.Thread(
            target=run_transcription,
            args=(save_path,),
            daemon=True
        )

        thread.start()

        return render_template(
            "index.html",
            text="",
            paragraphs=[],
            processing=True
        )

    except Exception:

        error_logger.exception(
            "파일 업로드 처리 중 오류 발생"
        )

        return "파일 업로드 중 오류가 발생했습니다.", 500


# =========================================================
# 전사 진행률
# =========================================================

@app.route("/progress")
def progress():

    try:

        with state_lock:
            return jsonify(
                progress_state.copy()
            )

    except Exception:

        error_logger.exception(
            "전사 진행률 조회 중 오류 발생"
        )

        return jsonify({
            "percent": 0,
            "status": "error",
            "error": "진행률을 가져오는 중 오류가 발생했습니다."
        }), 500


# =========================================================
# 파일 다운로드
# =========================================================

@app.route("/download/<fmt>")
def download(fmt):

    try:

        with state_lock:
            text = latest_result["text"]
            segments = list(
                latest_result["segments"]
            )

        if not text:

            server_logger.warning(
                "다운로드 실패 | 전사 결과 없음 | format=%s",
                fmt
            )

            return "먼저 전사를 진행하세요.", 400

        filename = f"result.{fmt}"

        output_path = os.path.join(
            OUTPUT_FOLDER,
            filename
        )

        if fmt == "txt":

            export_txt(
                text,
                output_path
            )

        elif fmt == "srt":

            export_srt(
                segments,
                output_path
            )

        elif fmt == "docx":

            paragraphs = group_into_paragraphs(
                segments
            )

            export_docx(
                paragraphs,
                output_path
            )

        elif fmt == "pdf":

            paragraphs = group_into_paragraphs(
                segments
            )

            export_pdf(
                paragraphs,
                output_path
            )

        else:

            server_logger.warning(
                "다운로드 실패 | 지원하지 않는 형식 | format=%s",
                fmt
            )

            return "지원하지 않는 형식입니다.", 400

        server_logger.info(
            "파일 다운로드 완료 | format=%s",
            fmt
        )

        return send_file(
            output_path,
            as_attachment=True
        )

    except Exception:

        error_logger.exception(
            "파일 다운로드 처리 중 오류 발생 | format=%s",
            fmt
        )

        return "파일 생성 중 오류가 발생했습니다.", 500


# =========================================================
# 404 처리
# =========================================================

@app.errorhandler(404)
def page_not_found(error):

    server_logger.warning(
        "404 Not Found | path=%s",
        request.path
    )

    return "페이지를 찾을 수 없습니다.", 404


# =========================================================
# 413 처리
# =========================================================

@app.errorhandler(413)
def request_entity_too_large(error):

    server_logger.warning(
        "파일 용량 초과 | path=%s",
        request.path
    )

    return (
        "파일 크기가 너무 큽니다. "
        "최대 2GB까지 업로드할 수 있습니다.",
        413
    )

# =========================================================
# 500 처리
# =========================================================

@app.errorhandler(500)
def internal_server_error(error):

    error_logger.error(
        "500 Internal Server Error | path=%s | error=%s",
        request.path,
        error
    )

    return "서버 내부 오류가 발생했습니다.", 500


# =========================================================
# 정상 종료 로그
# =========================================================

@atexit.register
def shutdown_server():

    server_logger.info("=" * 60)
    server_logger.info("SERVER_SHUTDOWN")
    server_logger.info("Flask 서버가 정상적으로 종료되었습니다.")
    server_logger.info("=" * 60)


# =========================================================
# 서버 실행
# =========================================================

if __name__ == "__main__":

    server_logger.info("=" * 60)
    server_logger.info("SERVER_START")
    server_logger.info(
        "Flask 서버를 시작합니다."
    )
    server_logger.info(
        "Upload folder: %s",
        UPLOAD_FOLDER
    )
    server_logger.info(
        "Output folder: %s",
        OUTPUT_FOLDER
    )
    server_logger.info(
        "Log folder: %s",
        LOG_FOLDER
    )
    server_logger.info("=" * 60)

    # 자동 reloader를 끄기 위해 use_reloader=False
    # 그래야 코드 변경 시 불필요한 서버 재시작 로그가 발생하지 않습니다.
    app.run(
        debug=True,
        use_reloader=False
    )
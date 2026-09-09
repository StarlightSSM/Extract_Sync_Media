my-transcriber

강의 MP3/MP4 파일을 업로드하면 자동으로 텍스트를 전사하고, TXT / SRT / PDF / DOCX 형식으로 다운로드할 수 있는 개인용 로컬 웹앱입니다.

음성 인식은 faster-whisper를 사용하며, 전사 진행률을 실시간으로 확인할 수 있습니다. 또한 서버 실행 상태, HTTP 요청, 전사 작업 및 오류를 로그 파일로 기록하여 문제 발생 시 원인을 확인할 수 있도록 구성했습니다.

A personal local web application that automatically transcribes uploaded lecture MP3/MP4 files into text and allows users to download the results in TXT, SRT, PDF, or DOCX format.

The application uses faster-whisper for speech recognition and provides real-time transcription progress. It also includes a logging system that records server activity, HTTP requests, transcription processes, and errors for easier debugging and troubleshooting.

🇰🇷 한국어

주요 기능

MP3, MP4 파일 업로드

faster-whisper 기반 한국어 음성 인식

전사 진행률(%) 실시간 표시

전사 결과 화면 확인

결과물 다운로드

TXT: 순수 텍스트

SRT: 타임코드 포함 자막 파일

PDF: 읽기 / 보관 / 제출용 문서 (한글 폰트 지원)

DOCX: Word에서 수정 가능한 문서

서버 및 전사 작업 로그 기록

오류 발생 시 상세 traceback 기록

로그 파일 자동 순환 관리(Rotating Log)

서버 시작 / 종료 상태 기록

HTTP 요청 로그 기록

기술 스택

영역

사용 기술

백엔드

Flask

프론트엔드

HTML / CSS / Vanilla JS

음성 인식

faster-whisper (CPU, int8)

DOCX 생성

python-docx

PDF 생성

ReportLab

로깅

Python logging

실행 환경

Python Virtual Environment

폴더 구조

my-transcriber/
├─ app.py                 # Flask 서버 진입점
├─ requirements.txt       # 설치 패키지 목록
├─ README.md              # 프로젝트 설명 및 사용 방법
├─ .gitignore
│
├─ uploads/               # 업로드된 원본 파일 (git 제외)
├─ outputs/               # 생성된 결과 파일 (git 제외)
├─ logs/                  # 서버 및 전사 로그 (git 제외)
│  ├─ server.log          # 서버 실행/종료 및 HTTP 요청 로그
│  ├─ error.log           # 서버 오류 및 예외 traceback 로그
│  └─ transcription.log   # 전사 작업 및 모델 관련 로그
│
├─ templates/
│  └─ index.html          # 업로드 폼 + 진행률 바 + 결과 화면
│
└─ services/
   ├─ transcribe.py       # faster-whisper 전사 로직
   ├─ export_txt.py       # TXT 생성
   ├─ export_srt.py       # SRT 생성
   ├─ export_pdf.py       # PDF 생성 (ReportLab)
   └─ export_docx.py      # DOCX 생성 (python-docx)

로그 시스템

프로젝트에서는 Python 표준 logging 모듈을 사용하여 서버와 전사 과정에서 발생하는 주요 이벤트를 기록합니다.

server.log

서버의 실행 상태와 HTTP 요청을 기록합니다.

주요 기록 내용:

서버 시작

서버 정상 종료

페이지 접속

파일 업로드 요청

진행률 요청

결과 파일 다운로드

HTTP 오류 상태

error.log

서버에서 발생하는 오류와 예외 상황을 기록합니다.

Python 예외가 발생한 경우 traceback도 함께 저장하여 오류가 발생한 코드 위치를 확인할 수 있습니다.

transcription.log

음성 전사 과정과 faster-whisper 모델 관련 작업을 기록합니다.

주요 기록 내용:

전사 작업 시작

입력 파일 확인

Whisper 모델 로딩 시작

Whisper 모델 로딩 완료

오디오 길이 확인

전사 완료

전사 중 발생한 오류

로그 파일 자동 관리

RotatingFileHandler를 사용하여 로그 파일 크기를 자동으로 관리합니다.

현재 설정:

로그 파일 최대 크기: 5 MB

백업 로그 파일: 최대 5개

참고: 컴퓨터 강제 종료, 전원 차단, 프로세스 강제 종료 등 Python이 정상적으로 종료 코드를 실행할 수 없는 상황에서는 SERVER_SHUTDOWN 로그가 남지 않을 수 있습니다.

설치 및 실행

# 1. 가상환경 생성
python -m venv .venv

# 2. 가상환경 활성화
.venv\Scripts\Activate.ps1

# 3. 패키지 설치
pip install -r requirements.txt

# 4. 서버 실행
python app.py

실행 후 브라우저에서 다음 주소로 접속합니다.

http://127.0.0.1:5000

사용 방법

MP3 또는 MP4 파일 선택

업로드 버튼 클릭

전사 진행률 확인

전사 완료 후 결과 확인

TXT / SRT / PDF / DOCX 중 원하는 형식으로 다운로드

알려진 제한 사항

전사는 로컬 서버에서 처리됩니다.

한 번에 하나의 전사 작업을 처리하는 구조입니다.

진행률(%)은 오디오 구간별 처리 속도 차이로 인해 완전히 균등하게 증가하지 않을 수 있습니다.

현재 CPU 기반으로 int8 연산을 사용합니다.

GPU(CUDA) 환경은 아직 구성되어 있지 않습니다.

최근 전사 결과 1건만 메모리에 유지됩니다.

서버를 재시작하면 기존 전사 결과는 메모리에서 초기화됩니다.

업로드된 원본 파일과 생성된 결과 파일은 프로젝트 폴더에 저장됩니다.

강제 종료나 시스템 장애가 발생한 경우 정상적인 종료 로그가 남지 않을 수 있습니다.

향후 개선 계획

전사 기능

자동 언어 감지

GPU(CUDA) 연동

음성 구간별 화자 분리

전사 정확도 개선

사용자 정의 Whisper 모델 선택

긴 파일 전사 안정성 개선

결과 관리

작업 이력 저장

여러 전사 결과 관리

전사 결과 재다운로드

전사 결과 삭제 기능

전사 결과 검색

키워드 검색

AI 기능

전사 결과 자동 요약

강의 핵심 내용 추출

주요 키워드 자동 추출

목차 / 챕터 자동 생성

질의응답 기능

사용자 편의 기능

드래그 앤 드롭 업로드

업로드 파일 크기 및 형식 안내 개선

전사 취소 기능

전사 완료 알림

다크 모드

반응형 UI 개선

서버 및 안정성

서버 실행 로그 기록

서버 종료 로그 기록

HTTP 요청 로그 기록

서버 오류 로그 기록

전사 오류 traceback 기록

로그 파일 자동 순환 관리

비정상 종료 감지 개선

작업 상태 영구 저장

서버 재시작 후 작업 복구

다중 작업 큐 지원

변경 이력

2026-09-09

영상 및 미디어 파일 업로드 용량 제한을 2GB로 확대

대용량 MP3/MP4 파일 업로드 지원 강화

🇺🇸 English

Features

Upload MP3 and MP4 files

Korean speech recognition powered by faster-whisper

Real-time transcription progress

Preview transcribed text in the browser

Download transcription results in multiple formats:

TXT: Plain text

SRT: Subtitle file with timestamps

PDF: For reading, archiving, and submission (Korean font support)

DOCX: Editable Microsoft Word document

Server and transcription activity logging

Detailed traceback logging for errors

Automatic log rotation

Server startup and shutdown logging

HTTP request logging

Changelog

2026-09-09

Increased the maximum upload size for video and media files to 2GB

Improved support for large MP3/MP4 file uploads

Tech Stack

Area

Technology

Backend

Flask

Frontend

HTML / CSS / Vanilla JS

Speech Recognition

faster-whisper (CPU, int8)

DOCX Generation

python-docx

PDF Generation

ReportLab

Logging

Python logging

Environment

Python Virtual Environment

Project Structure

my-transcriber/
├─ app.py                 # Flask server entry point
├─ requirements.txt       # Required Python packages
├─ README.md              # Project documentation
├─ .gitignore
│
├─ uploads/               # Uploaded source files (git-ignored)
├─ outputs/               # Generated output files (git-ignored)
├─ logs/                  # Server and transcription logs (git-ignored)
│  ├─ server.log          # Server startup/shutdown and HTTP request logs
│  ├─ error.log           # Server errors and exception tracebacks
│  └─ transcription.log   # Transcription and model-related logs
│
├─ templates/
│  └─ index.html          # Upload form, progress bar, and result view
│
└─ services/
   ├─ transcribe.py       # faster-whisper transcription logic
   ├─ export_txt.py       # TXT generation
   ├─ export_srt.py       # SRT generation
   ├─ export_pdf.py       # PDF generation (ReportLab)
   └─ export_docx.py      # DOCX generation (python-docx)

Logging System

The application uses Python's built-in logging module to record important events during server operation and transcription.

server.log

Records server status and HTTP requests.

Main events include:

Server startup

Normal server shutdown

Page requests

File upload requests

Progress requests

Result downloads

HTTP errors

error.log

Records server errors and exceptions.

When a Python exception occurs, the full traceback is saved to help identify where and why the error occurred.

transcription.log

Records transcription-related activities and faster-whisper model operations.

Main events include:

Transcription started

Input file validation

Whisper model loading started

Whisper model loading completed

Media duration detection

Transcription completed

Transcription errors

Automatic Log Rotation

The application uses RotatingFileHandler to prevent log files from growing indefinitely.

Current configuration:

Maximum log file size: 5 MB

Backup log files: up to 5 files

Note: If the computer loses power, the process is forcibly terminated, or the operating system crashes, Python may not have an opportunity to execute the shutdown handler. In such cases, a SERVER_SHUTDOWN entry may not be recorded.

Installation & Setup

1. Create a virtual environment

python -m venv .venv

2. Activate the virtual environment

.venv\Scripts\Activate.ps1

3. Install dependencies

pip install -r requirements.txt

4. Start the server

python app.py

Then open:

http://127.0.0.1:5000

in your web browser.

How to Use

Select an MP3 or MP4 lecture file.

Click the upload button.

Monitor the real-time transcription progress.

Review the transcription result when processing is complete.

Download the result as TXT, SRT, PDF, or DOCX.

Output Formats

TXT

Contains only the transcribed text.

Useful for simple text extraction and further processing.

SRT

Contains timestamps for each transcribed segment.

Useful for creating subtitles or working with video editing software.

PDF

Provides a document format suitable for reading, printing, archiving, or submission.

Korean characters are supported through a compatible Korean font configuration.

DOCX

Generates an editable Microsoft Word document.

Useful when the transcript needs additional editing or formatting.

Known Limitations

Transcription is processed locally on the server.

Only one transcription job is processed at a time.

Progress percentages may not increase evenly because processing time varies between audio segments.

The current implementation uses CPU-based inference with int8 computation.

GPU/CUDA support is not currently configured.

Only the most recent transcription result is kept in memory.

Transcription results stored in memory are cleared when the server restarts.

Uploaded source files and generated output files are stored in the local project directory.

Normal shutdown logs may not be recorded after forced termination or system failure.

Roadmap

Transcription

Automatic language detection

GPU (CUDA) support

Speaker diarization

Improved transcription accuracy

User-selectable Whisper models

Improved stability for long audio files

Result Management

Persistent job history

Multiple transcription result management

Re-download previous results

Delete transcription results

Transcript search

Keyword search

AI Features

Automatic transcript summarization

Lecture key-point extraction

Automatic keyword extraction

Automatic chapter / section generation

Question-answering based on transcripts

User Experience

Drag-and-drop file upload

Improved file size and format guidance

Transcription cancellation

Transcription completion notification

Dark mode

Responsive UI improvements

Server & Reliability

Server startup logging

Server shutdown logging

HTTP request logging

Server error logging

Transcription traceback logging

Automatic log rotation

Improved abnormal shutdown detection

Persistent job state

Job recovery after server restart

Multi-job queue support

Example

PS C:\Users\sumin\Desktop\Extract_Sync_Media\my-transcriber> .venv\Scripts\Activate.ps1

(.venv) PS C:\Users\sumin\Desktop\Extract_Sync_Media\my-transcriber> python app.py

 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000

Open the following address in your browser:

http://127.0.0.1:5000

To stop the server:

Ctrl + C

If the server shuts down normally, a shutdown entry will be written to:

logs/server.log

License

This project was created for personal learning, research, and local use.

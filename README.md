# my-transcriber

강의 mp3/mp4 파일을 업로드하면 자동으로 텍스트를 전사하고, TXT / SRT / PDF / DOCX 중 원하는 형식으로 다운로드할 수 있는 개인용 로컬 웹앱입니다.

## 주요 기능

- mp3, mp4 파일 업로드
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) 기반 한국어 음성 인식
- 전사 진행률(%) 실시간 표시
- 결과물 다운로드
  - **TXT**: 순수 텍스트
  - **SRT**: 타임코드 포함 자막 파일
  - **PDF**: 읽기/보관/제출용 (한글 폰트 지원)
  - **DOCX**: Word에서 수정 가능한 문서

## 기술 스택

| 영역 | 사용 기술 |
|---|---|
| 백엔드 | Flask |
| 프론트엔드 | HTML / CSS / Vanilla JS |
| 음성 인식 | faster-whisper (CPU, int8) |
| DOCX 생성 | python-docx |
| PDF 생성 | ReportLab |

## 폴더 구조

```
my-transcriber/
├─ app.py                 # Flask 서버 진입점
├─ requirements.txt        # 설치 패키지 목록
├─ .gitignore
├─ uploads/                # 업로드된 원본 파일 (git 제외)
├─ outputs/                # 생성된 결과 파일 (git 제외)
├─ templates/
│  └─ index.html           # 업로드 폼 + 진행률 바 + 결과 화면
└─ services/
   ├─ transcribe.py        # faster-whisper 전사 로직
   ├─ export_txt.py        # TXT 생성
   ├─ export_srt.py        # SRT 생성
   ├─ export_pdf.py        # PDF 생성 (ReportLab)
   └─ export_docx.py       # DOCX 생성 (python-docx)
```

## 설치 및 실행

```powershell
# 1. 가상환경 생성 및 활성화
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. 패키지 설치
pip install -r requirements.txt

# 3. 서버 실행
python app.py
```

실행 후 브라우저에서 `http://127.0.0.1:5000` 접속.

## 사용 방법

1. mp3 또는 mp4 파일 선택 후 업로드
2. 진행률 바가 100%가 될 때까지 대기 (전사 진행 중)
3. 전사 완료 후 화면에 표시된 텍스트 확인
4. 원하는 형식(TXT / SRT / PDF / DOCX) 버튼 클릭해 다운로드

## 알려진 제한 사항

- 전사는 서버 로컬에서 동기적으로 처리되며, 한 번에 한 작업만 처리 가능
- 진행률(%)은 오디오 구간별 처리 속도 차이로 인해 완전히 균등하게 올라가지 않을 수 있음
- 현재 CPU 기반 처리이며, GPU(CUDA) 환경 구성은 별도 진행 예정
- 최근 작업 1건만 메모리에 유지 (서버 재시작 시 초기화됨)

## 향후 개선 계획

- [ ] 작업 이력 목록 저장
- [ ] GPU(CUDA) 연동
- [ ] 자동 언어 감지
- [ ] 전사 결과 요약 기능
- [ ] 키워드 검색

============================================================================
# my-transcriber

A local personal web app that transcribes uploaded lecture audio/video files (mp3/mp4) into text, with download options in TXT, SRT, PDF, or DOCX format.

## Features

- Upload mp3 or mp4 files
- Korean speech recognition powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- Real-time transcription progress (%)
- Download results in multiple formats
  - **TXT**: Plain text
  - **SRT**: Subtitle file with timecodes
  - **PDF**: For reading/archiving/submission (Korean font supported)
  - **DOCX**: Editable Word document

## Tech Stack

| Area | Technology |
|---|---|
| Backend | Flask |
| Frontend | HTML / CSS / Vanilla JS |
| Speech Recognition | faster-whisper (CPU, int8) |
| DOCX generation | python-docx |
| PDF generation | ReportLab |

## Folder Structure

```
my-transcriber/
├─ app.py                 # Flask server entry point
├─ requirements.txt        # List of required packages
├─ .gitignore
├─ uploads/                # Uploaded original files (git-ignored)
├─ outputs/                # Generated result files (git-ignored)
├─ templates/
│  └─ index.html           # Upload form + progress bar + result view
└─ services/
   ├─ transcribe.py        # faster-whisper transcription logic
   ├─ export_txt.py        # TXT generation
   ├─ export_srt.py        # SRT generation
   ├─ export_pdf.py        # PDF generation (ReportLab)
   └─ export_docx.py       # DOCX generation (python-docx)
```

## Installation & Setup

```powershell
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the server
python app.py
```

Then open `http://127.0.0.1:5000` in your browser.

## How to Use

1. Select and upload an mp3 or mp4 file
2. Wait for the progress bar to reach 100% (transcription in progress)
3. Review the transcribed text once complete
4. Click the desired format (TXT / SRT / PDF / DOCX) to download

## Known Limitations

- Transcription runs synchronously on the local server and processes one job at a time
- Progress (%) may not increase perfectly evenly due to varying processing speed across audio segments
- Currently CPU-based; GPU (CUDA) support is planned separately
- Only the most recent job is kept in memory (resets on server restart)

## Roadmap

- [ ] Job history storage
- [ ] GPU (CUDA) integration
- [ ] Automatic language detection
- [ ] Transcript summarization
- [ ] Keyword search

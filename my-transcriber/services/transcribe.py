import gc
import logging
import os
import shutil
import subprocess

import numpy as np
from faster_whisper import WhisperModel
from pathlib import Path


# =========================================================
# Logger 설정
# =========================================================

logger = logging.getLogger("transcription")
error_logger = logging.getLogger("error")


# =========================================================
# 전사 설정
# =========================================================

# 한 번에 처리할 오디오 길이(초): 메모리 사용량을 줄이기 위해 2분
CHUNK_DURATION = 120

# Whisper 설정
WHISPER_MODEL_SIZE = "small"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"

# 전사 언어
TRANSCRIPTION_LANGUAGE = "ko"

# FFmpeg 실행 파일. PATH에 등록되어 있으면 "ffmpeg" 그대로 사용
FFMPEG_EXECUTABLE = "ffmpeg"


# =========================================================
# Whisper 모델
# =========================================================

_model = None


def get_model():
    """Whisper 모델을 최초 1회만 로딩합니다."""
    global _model

    if _model is None:
        logger.info(
            "Whisper 모델 로딩 시작 | model=%s | device=%s | compute_type=%s",
            WHISPER_MODEL_SIZE,
            WHISPER_DEVICE,
            WHISPER_COMPUTE_TYPE,
        )

        try:
            _model = WhisperModel(
                WHISPER_MODEL_SIZE,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE,
            )
            logger.info("Whisper 모델 로딩 완료")
        except Exception:
            error_logger.exception("Whisper 모델 로딩 실패")
            raise

    return _model


# =========================================================
# FFmpeg 확인 및 미디어 길이 확인
# =========================================================

def _ffmpeg_path():
    # 먼저 PATH에 등록된 FFmpeg 확인
    ffmpeg = shutil.which("ffmpeg")

    # PATH에서 찾지 못하면 실제 설치 경로를 직접 확인
    if not ffmpeg:
        ffmpeg = (
            r"C:\Users\sumin\AppData\Local\Microsoft\WinGet\Packages"
            r"\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe"
            r"\ffmpeg-9.0.2-full_build-shared\bin\ffmpeg.EXE"
        )

    ffmpeg_path = Path(ffmpeg)

    if not ffmpeg_path.is_file():
        raise RuntimeError(
            f"FFmpeg 실행 파일을 찾을 수 없습니다: {ffmpeg_path}"
        )

    # 현재 Python 프로세스에서도 FFmpeg를 찾을 수 있도록 설정
    ffmpeg_dir = str(ffmpeg_path.parent)
    os.environ["PATH"] = (
        ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
    )

    return str(ffmpeg_path)


def get_media_duration(file_path):
    """PyAV를 이용해 미디어 전체 길이를 초 단위로 반환합니다."""
    try:
        import av

        with av.open(file_path) as container:
            if container.duration is not None:
                # PyAV container.duration은 microseconds 단위입니다.
                return float(container.duration) / 1_000_000

            for stream in container.streams:
                if stream.type == "audio" and stream.duration is not None:
                    return float(stream.duration * stream.time_base)

        raise RuntimeError("미디어 파일의 재생 시간을 확인할 수 없습니다.")

    except ImportError as exc:
        raise RuntimeError(
            "PyAV(av)가 설치되어 있지 않습니다. 가상환경에서 "
            "'pip install av' 명령을 실행하세요."
        ) from exc
    except Exception:
        error_logger.exception(
            "미디어 길이 확인 실패 | file=%s",
            os.path.basename(file_path),
        )
        raise


def load_audio_chunk(file_path, start, duration):
    """
    FFmpeg로 지정 구간만 모노 16kHz float32 PCM으로 읽습니다.
    전체 파일을 메모리에 올리지 않습니다.
    """
    ffmpeg = _ffmpeg_path()

    command = [
        ffmpeg,
        "-nostdin",
        "-hide_banner",
        "-loglevel", "error",
        "-ss", f"{start:.3f}",
        "-i", file_path,
        "-t", f"{duration:.3f}",
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-f", "f32le",
        "pipe:1",
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if result.returncode != 0:
        error_message = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"FFmpeg 오디오 청크 추출 실패(start={start}, duration={duration}): "
            f"{error_message or '알 수 없는 FFmpeg 오류'}"
        )

    if not result.stdout:
        raise RuntimeError(
            f"추출된 오디오가 비어 있습니다(start={start}, duration={duration})."
        )

    # f32le은 float32 한 샘플이 4바이트입니다.
    if len(result.stdout) % 4 != 0:
        raise RuntimeError("FFmpeg가 반환한 오디오 데이터 크기가 float32 형식과 맞지 않습니다.")

    audio = np.frombuffer(result.stdout, dtype=np.float32).copy()

    if audio.size == 0:
        raise RuntimeError(
            f"추출된 오디오 샘플이 없습니다(start={start}, duration={duration})."
        )

    return audio


# =========================================================
# 진행률 계산
# =========================================================

def update_progress(progress_callback, current_time, total_duration):
    """전체 미디어 기준 진행률을 계산하여 callback으로 전달합니다."""
    if progress_callback and total_duration and total_duration > 0:
        percent = min(100, int((current_time / total_duration) * 100))
        progress_callback(percent)


# =========================================================
# 음성 전사
# =========================================================

def transcribe_media(file_path, progress_callback=None):
    """
    MP3/MP4 파일을 Whisper로 전사합니다.

    오디오를 CHUNK_DURATION 단위로 FFmpeg에서 추출해 처리하므로,
    전체 오디오를 한 번에 NumPy 배열로 올리지 않습니다.

    Returns
    -------
    tuple[str, list[dict]]
        전체 텍스트와 {"start": float, "end": float, "text": str} 형태의 세그먼트 목록
    """
    filename = os.path.basename(file_path)

    logger.info(
        "음성 전사 시작 | file=%s | chunk=%d초",
        filename,
        CHUNK_DURATION,
    )

    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

        # FFmpeg가 설치되어 있는지 초기에 확인합니다.
        _ffmpeg_path()

        model = get_model()
        total_duration = get_media_duration(file_path)

        if total_duration <= 0:
            raise RuntimeError("미디어 길이가 0초 이하입니다.")

        logger.info(
            "미디어 정보 확인 | file=%s | duration=%.2f초 | duration=%.2f분",
            filename,
            total_duration,
            total_duration / 60,
        )

        full_text_parts = []
        segment_list = []
        chunk_start = 0.0
        chunk_index = 0

        while chunk_start < total_duration:
            chunk_index += 1
            chunk_end = min(chunk_start + CHUNK_DURATION, total_duration)
            chunk_duration = chunk_end - chunk_start
            audio_chunk = None

            logger.info(
                "Whisper chunk 전사 시작 | file=%s | chunk=%d | "
                "start=%.2f | end=%.2f | duration=%.2f",
                filename,
                chunk_index,
                chunk_start,
                chunk_end,
                chunk_duration,
            )

            try:
                audio_chunk = load_audio_chunk(
                    file_path,
                    chunk_start,
                    chunk_duration,
                )

                logger.info(
                    "오디오 배열 점검 | shape=%s | dtype=%s | samples=%d | "
                    "duration=%.2f초 | memory=%.2fMB",
                    audio_chunk.shape,
                    audio_chunk.dtype,
                    audio_chunk.size,
                    audio_chunk.size / 16000,
                    audio_chunk.nbytes / (1024 * 1024),
                )

                # 배열을 직접 전달하므로 clip_timestamps는 사용하지 않습니다.
                segments, info = model.transcribe(
                    audio_chunk,
                    language=TRANSCRIPTION_LANGUAGE,
                    vad_filter=True,
                )

                chunk_segment_count = 0

                # faster-whisper의 segments는 generator이므로 여기서 실제 추론됩니다.
                for seg in segments:
                    text = seg.text.strip()
                    if not text:
                        continue

                    # seg.start/end는 전달한 오디오 청크 기준 시간입니다.
                    absolute_start = max(chunk_start, chunk_start + float(seg.start))
                    absolute_end = min(chunk_end, chunk_start + float(seg.end))

                    if absolute_end < absolute_start:
                        continue

                    segment_list.append(
                        {
                            "start": absolute_start,
                            "end": absolute_end,
                            "text": text,
                        }
                    )
                    full_text_parts.append(text)
                    chunk_segment_count += 1

                    update_progress(
                        progress_callback,
                        absolute_end,
                        total_duration,
                    )

                logger.info(
                    "Whisper chunk 전사 완료 | file=%s | chunk=%d | segments=%d",
                    filename,
                    chunk_index,
                    chunk_segment_count,
                )

            except Exception:
                error_logger.exception(
                    "Whisper chunk 전사 실패 | file=%s | chunk=%d | "
                    "start=%.2f | end=%.2f",
                    filename,
                    chunk_index,
                    chunk_start,
                    chunk_end,
                )
                raise

            finally:
                if audio_chunk is not None:
                    del audio_chunk
                gc.collect()

            chunk_start = chunk_end

        result_text = " ".join(full_text_parts).strip()

        if progress_callback:
            progress_callback(100)

        logger.info(
            "음성 전사 완료 | file=%s | chunks=%d | segments=%d | text_length=%d",
            filename,
            chunk_index,
            len(segment_list),
            len(result_text),
        )

        return result_text, segment_list

    except Exception:
        error_logger.exception(
            "음성 전사 중 오류 발생 | file=%s",
            filename,
        )
        logger.exception("음성 전사 실패 | file=%s", filename)
        raise

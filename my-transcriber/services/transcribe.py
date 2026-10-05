```python
import os
import gc
import logging

from faster_whisper import WhisperModel


# =========================================================
# Logger 설정
# =========================================================

logger = logging.getLogger("transcription")
error_logger = logging.getLogger("error")


# =========================================================
# 전사 설정
# =========================================================

# 한 번에 처리할 오디오 길이
# 10분 = 600초
CHUNK_DURATION = 600

# Whisper 설정
WHISPER_MODEL_SIZE = "small"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"

# 전사 언어
TRANSCRIPTION_LANGUAGE = "ko"


# =========================================================
# Whisper 모델
# =========================================================

_model = None


def get_model():
    """
    Whisper 모델을 최초 1회만 로딩합니다.

    CPU + int8 설정으로 메모리 사용량을 줄입니다.
    """

    global _model

    if _model is None:

        logger.info(
            "Whisper 모델 로딩 시작 | model=%s | device=%s | compute_type=%s",
            WHISPER_MODEL_SIZE,
            WHISPER_DEVICE,
            WHISPER_COMPUTE_TYPE
        )

        try:

            _model = WhisperModel(
                WHISPER_MODEL_SIZE,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE
            )

            logger.info(
                "Whisper 모델 로딩 완료"
            )

        except Exception:

            error_logger.exception(
                "Whisper 모델 로딩 실패"
            )

            raise

    return _model


# =========================================================
# 미디어 전체 길이 확인
# =========================================================

def get_media_duration(file_path):
    """
    미디어 파일의 전체 재생 시간을 초 단위로 반환합니다.

    faster-whisper가 전체 오디오를 NumPy 배열로 디코딩하기 전에
    컨테이너 메타데이터만 확인하기 위한 함수입니다.

    PyAV는 faster-whisper의 오디오 디코딩 환경에서 일반적으로
    함께 사용되는 라이브러리입니다.
    """

    try:

        import av

        container = av.open(file_path)

        try:

            duration = container.duration

            if duration is not None:

                # PyAV duration은 microseconds 단위입니다.
                return float(duration) / 1_000_000

            # container.duration이 없는 경우 stream metadata 확인
            for stream in container.streams:

                if stream.type == "audio":

                    if stream.duration is not None:
                        return float(
                            stream.duration * stream.time_base
                        )

            raise RuntimeError(
                "미디어 파일의 재생 시간을 확인할 수 없습니다."
            )

        finally:

            container.close()

    except ImportError:

        raise RuntimeError(
            "PyAV(av)가 설치되어 있지 않습니다. "
            "현재 가상환경에서 다음 명령을 실행하세요: "
            "pip install av"
        )

    except Exception:

        error_logger.exception(
            "미디어 길이 확인 실패 | file=%s",
            os.path.basename(file_path)
        )

        raise


# =========================================================
# 진행률 계산
# =========================================================

def update_progress(
    progress_callback,
    current_time,
    total_duration
):
    """
    전체 미디어 기준 진행률을 계산하여 callback으로 전달합니다.

    chunk 단위 전사를 하더라도 progress는
    0~100% 전체 영상 기준으로 유지합니다.
    """

    if (
        progress_callback
        and total_duration
        and total_duration > 0
    ):

        percent = min(
            100,
            int(
                (current_time / total_duration) * 100
            )
        )

        progress_callback(percent)


# =========================================================
# 음성 전사
# =========================================================

def transcribe_media(
    file_path,
    progress_callback=None
):
    """
    MP3/MP4 파일을 Whisper로 전사합니다.

    긴 파일을 한 번에 Whisper에 전달하지 않고
    10분(CHUNK_DURATION) 단위로 나누어 전사합니다.

    Parameters
    ----------
    file_path : str
        전사할 미디어 파일 경로

    progress_callback : callable, optional
        전사 진행률을 전달하는 함수.
        callback(percent) 형태로 호출됩니다.

    Returns
    -------
    tuple
        (
            전체 텍스트,
            세그먼트 리스트
        )

    Notes
    -----
    각 chunk의 Whisper timestamp는 해당 chunk 기준으로
    시작되므로 chunk_start를 더하여 원본 미디어 기준
    timestamp로 변환합니다.
    """

    filename = os.path.basename(file_path)

    logger.info(
        "음성 전사 시작 | file=%s | chunk=%d초",
        filename,
        CHUNK_DURATION
    )

    try:

        # -------------------------------------------------
        # 파일 존재 여부 확인
        # -------------------------------------------------

        if not os.path.exists(file_path):

            raise FileNotFoundError(
                f"파일을 찾을 수 없습니다: {file_path}"
            )

        # -------------------------------------------------
        # Whisper 모델 가져오기
        # -------------------------------------------------

        model = get_model()

        # -------------------------------------------------
        # 전체 미디어 길이 확인
        # -------------------------------------------------

        total_duration = get_media_duration(
            file_path
        )

        logger.info(
            "미디어 정보 확인 | file=%s | duration=%.2f초 | duration=%.2f분",
            filename,
            total_duration,
            total_duration / 60
        )

        # -------------------------------------------------
        # 결과 저장용 변수
        # -------------------------------------------------

        full_text_parts = []
        segment_list = []

        # -------------------------------------------------
        # 10분 단위 chunk 전사
        # -------------------------------------------------

        chunk_start = 0.0
        chunk_index = 0

        while chunk_start < total_duration:

            chunk_index += 1

            chunk_end = min(
                chunk_start + CHUNK_DURATION,
                total_duration
            )

            chunk_duration = chunk_end - chunk_start

            logger.info(
                "Whisper chunk 전사 시작 | "
                "file=%s | chunk=%d | start=%.2f | end=%.2f | duration=%.2f",
                filename,
                chunk_index,
                chunk_start,
                chunk_end,
                chunk_duration
            )

            try:

                # -------------------------------------------------
                # 중요:
                #
                # 전체 파일을 model.transcribe()에 전달하지 않고
                # 현재 chunk 구간만 디코딩하도록 합니다.
                #
                # 이렇게 하면 긴 강의 전체가 NumPy 배열로
                # 메모리에 올라가는 것을 방지할 수 있습니다.
                # -------------------------------------------------

                segments, info = model.transcribe(
                    file_path,
                    language=TRANSCRIPTION_LANGUAGE,
                    vad_filter=True,
                    clip_timestamps=[
                        chunk_start,
                        chunk_end
                    ]
                )

                # -------------------------------------------------
                # 현재 chunk의 세그먼트 처리
                # -------------------------------------------------

                chunk_segment_count = 0

                for seg in segments:

                    text = seg.text.strip()

                    if not text:
                        continue

                    # -------------------------------------------------
                    # Whisper의 timestamp는 chunk 기준입니다.
                    #
                    # 예:
                    # chunk 2가 600초부터 시작하고
                    # Whisper가 3.2초라고 판단했다면
                    #
                    # 실제 영상 timestamp = 603.2초
                    # -------------------------------------------------

                    absolute_start = (
                        chunk_start + seg.start
                    )

                    absolute_end = (
                        chunk_start + seg.end
                    )

                    # chunk 경계를 넘어가는 값 방지
                    absolute_start = max(
                        chunk_start,
                        absolute_start
                    )

                    absolute_end = min(
                        chunk_end,
                        absolute_end
                    )

                    # -------------------------------------------------
                    # 최종 segment 저장
                    # 기존 app.py / export_srt.py와 호환되는
                    # 동일한 데이터 구조를 유지합니다.
                    # -------------------------------------------------

                    segment_list.append({
                        "start": absolute_start,
                        "end": absolute_end,
                        "text": text
                    })

                    full_text_parts.append(text)

                    chunk_segment_count += 1

                    # -------------------------------------------------
                    # 전체 영상 기준 진행률
                    # -------------------------------------------------

                    update_progress(
                        progress_callback,
                        absolute_end,
                        total_duration
                    )

                logger.info(
                    "Whisper chunk 전사 완료 | "
                    "file=%s | chunk=%d | segments=%d",
                    filename,
                    chunk_index,
                    chunk_segment_count
                )

            except Exception:

                error_logger.exception(
                    "Whisper chunk 전사 실패 | "
                    "file=%s | chunk=%d | start=%.2f | end=%.2f",
                    filename,
                    chunk_index,
                    chunk_start,
                    chunk_end
                )

                raise

            finally:

                # -------------------------------------------------
                # chunk 처리가 끝나면 Python 객체에 대한
                # 참조를 최대한 빠르게 정리합니다.
                # -------------------------------------------------

                gc.collect()

            # -------------------------------------------------
            # 다음 chunk
            # -------------------------------------------------

            chunk_start = chunk_end

        # -------------------------------------------------
        # 전체 텍스트 생성
        # -------------------------------------------------

        result_text = " ".join(
            full_text_parts
        ).strip()

        # -------------------------------------------------
        # 진행률 100%
        # -------------------------------------------------

        if progress_callback:
            progress_callback(100)

        # -------------------------------------------------
        # 전사 완료 로그
        # -------------------------------------------------

        logger.info(
            "음성 전사 완료 | "
            "file=%s | chunks=%d | segments=%d | text_length=%d",
            filename,
            chunk_index,
            len(segment_list),
            len(result_text)
        )

        return result_text, segment_list

    except Exception:

        # -------------------------------------------------
        # 전체 전사 오류
        # -------------------------------------------------

        error_logger.exception(
            "음성 전사 중 오류 발생 | file=%s",
            filename
        )

        logger.exception(
            "음성 전사 실패 | file=%s",
            filename
        )

        raise
```

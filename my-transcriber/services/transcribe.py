import os
import logging

from faster_whisper import WhisperModel


# =========================================================
# Logger 설정
# =========================================================

logger = logging.getLogger("transcription")
error_logger = logging.getLogger("error")


# =========================================================
# Whisper 모델
# =========================================================

_model = None


def get_model():
    """
    Whisper 모델을 최초 1회만 로딩합니다.
    """

    global _model

    if _model is None:

        logger.info(
            "Whisper 모델 로딩 시작 | model=small | device=cpu"
        )

        try:

            _model = WhisperModel(
                "small",
                device="cpu",
                compute_type="int8"
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
# 음성 전사
# =========================================================

def transcribe_media(
    file_path,
    progress_callback=None
):
    """
    MP3/MP4 파일을 Whisper로 전사합니다.

    Parameters
    ----------
    file_path : str
        전사할 미디어 파일 경로

    progress_callback : callable, optional
        전사 진행률을 전달하는 함수

    Returns
    -------
    tuple
        (전체 텍스트, 세그먼트 리스트)
    """

    filename = os.path.basename(file_path)

    logger.info(
        "음성 전사 시작 | file=%s",
        filename
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
        # Whisper 전사 시작
        # -------------------------------------------------

        logger.info(
            "Whisper transcription 실행 | file=%s",
            filename
        )

        segments, info = model.transcribe(
            file_path,
            language="ko",
            vad_filter=True
        )

        total_duration = info.duration

        logger.info(
            "미디어 정보 확인 | file=%s | duration=%.2f초",
            filename,
            total_duration
        )

        full_text = ""
        segment_list = []

        # -------------------------------------------------
        # 세그먼트 처리
        # -------------------------------------------------

        for seg in segments:

            text = seg.text.strip()

            full_text += text + " "

            segment_list.append({
                "start": seg.start,
                "end": seg.end,
                "text": text
            })

            # 진행률 업데이트
            if (
                progress_callback
                and total_duration
                and total_duration > 0
            ):

                percent = min(
                    100,
                    int(
                        (seg.end / total_duration)
                        * 100
                    )
                )

                progress_callback(percent)

        # -------------------------------------------------
        # 전사 완료
        # -------------------------------------------------

        if progress_callback:
            progress_callback(100)

        result_text = full_text.strip()

        logger.info(
            "음성 전사 완료 | file=%s | segments=%d | text_length=%d",
            filename,
            len(segment_list),
            len(result_text)
        )

        return result_text, segment_list

    except Exception:

        # traceback을 error.log에 기록
        error_logger.exception(
            "음성 전사 중 오류 발생 | file=%s",
            filename
        )

        logger.exception(
            "음성 전사 실패 | file=%s",
            filename
        )

        raise
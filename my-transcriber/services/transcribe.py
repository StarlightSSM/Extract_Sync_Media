from faster_whisper import WhisperModel

_model = None

def get_model():
    global _model
    if _model is None:
        _model = WhisperModel("small", device="cpu", compute_type="int8")
    return _model

def transcribe_media(file_path, progress_callback=None):
    model = get_model()
    segments, info = model.transcribe(
        file_path,
        language="ko",
        vad_filter=True  # 무음 구간 스킵 → 속도 개선, 싱크에는 영향 없음
    )

    total_duration = info.duration
    full_text = ""
    segment_list = []

    for seg in segments:
        full_text += seg.text.strip() + " "
        segment_list.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip()
        })

        if progress_callback and total_duration > 0:
            percent = min(100, int((seg.end / total_duration) * 100))
            progress_callback(percent)

    if progress_callback:
        progress_callback(100)

    return full_text.strip(), segment_list
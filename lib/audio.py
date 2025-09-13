# lib/audio.py
import io
import os
import tempfile

def get_audio_duration_seconds(uploaded_file) -> float | None:
    """
    mutagen → wave（WAV） → audioread の順で音声長（秒）を推定。
    どれも失敗なら None。
    """
    # 1) mutagen
    try:
        from mutagen import File as MutagenFile
        f = MutagenFile(io.BytesIO(uploaded_file.getbuffer()))
        if getattr(f, "info", None) and getattr(f.info, "length", None):
            return float(f.info.length)
    except Exception:
        pass

    # 2) wave（WAVのみ）
    try:
        import wave, contextlib
        if uploaded_file.name.lower().endswith(".wav"):
            with contextlib.closing(wave.open(io.BytesIO(uploaded_file.getbuffer()))) as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    return frames / float(rate)
    except Exception:
        pass

    # 3) audioread
    try:
        import audioread
        suffix = os.path.splitext(uploaded_file.name)[1] or ".tmp"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getbuffer())
            tmp_path = tmp.name
        try:
            with audioread.audio_open(tmp_path) as af:
                if getattr(af, "duration", None):
                    return float(af.duration)
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    except Exception:
        pass

    return None

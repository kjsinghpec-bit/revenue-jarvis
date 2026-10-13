"""Free, local-first voice. Speech-to-text runs on your Mac (MLX Whisper on Apple Silicon);
text-to-speech uses free neural voices (edge-tts: British "Ryan" for English, Hindi and Punjabi
voices), falling back to the Mac's built-in voices in the browser when offline."""
from __future__ import annotations

import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path


class STTUnavailable(RuntimeError):
    pass


def _to_wav(data: bytes, suffix: str) -> Path:
    src = Path(tempfile.mkstemp(suffix=suffix)[1])
    src.write_bytes(data)
    dst = src.with_suffix(".wav")
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-ar", "16000", "-ac", "1", str(dst)],
                       capture_output=True, text=True, timeout=60, check=False)
    src.unlink(missing_ok=True)
    if r.returncode != 0:
        raise STTUnavailable(f"ffmpeg could not decode audio (brew install ffmpeg): {r.stderr[:200]}")
    return dst


@lru_cache(maxsize=1)
def _faster_whisper(model: str = "small"):
    from faster_whisper import WhisperModel  # optional dependency

    return WhisperModel(model, device="cpu", compute_type="int8")


def transcribe(data: bytes, suffix: str = ".webm", engine: str = "mlx", model: str = "mlx-community/whisper-large-v3-turbo",
               language: str | None = None) -> dict:
    wav = _to_wav(data, suffix)
    try:
        if engine == "mlx":
            try:
                import mlx_whisper  # optional dependency, Apple Silicon only
            except ImportError as e:
                raise STTUnavailable("mlx-whisper not installed: pip install 'revenue-jarvis[voice]'") from e
            res = mlx_whisper.transcribe(str(wav), path_or_hf_repo=model, language=language,
                                         initial_prompt="Punjab revenue: jamabandi, intkal, tatima, shamlat, takseem, murabbabandi, girdawari, tehsildar, patwari.")
            return {"text": res.get("text", "").strip(), "language": res.get("language")}
        if engine == "faster-whisper":
            segs, info = _faster_whisper().transcribe(str(wav), language=language)
            return {"text": " ".join(s.text for s in segs).strip(), "language": info.language}
        raise STTUnavailable(f"engine {engine!r} runs in the browser, not on the server")
    finally:
        wav.unlink(missing_ok=True)


VOICES = {"en": "en-GB-RyanNeural", "hinglish": "en-IN-PrabhatNeural", "hi": "hi-IN-MadhurNeural", "pa": "pa-IN-OjasNeural"}


def tts_mp3(text: str, lang: str, voice: str | None = None) -> bytes:
    """Free neural voice via Microsoft Edge's public read-aloud service (edge-tts). Needs internet, no account.
    The browser's built-in system voice is used automatically if this fails."""
    import asyncio

    import edge_tts

    async def _run() -> bytes:
        com = edge_tts.Communicate(text[:1500], voice or VOICES.get(lang, VOICES["en"]))
        out = bytearray()
        async for chunk in com.stream():
            if chunk["type"] == "audio":
                out += chunk["data"]
        return bytes(out)

    data = asyncio.run(_run())
    if not data:
        raise RuntimeError("no audio returned")
    return data

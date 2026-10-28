import io
import os
import re
import threading
from typing import Literal

import imageio_ffmpeg
import numpy as np
import soundfile as sf
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response
from kokoro import KPipeline
from pydantic import BaseModel, Field
from pydub import AudioSegment

AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()

API_KEY = os.getenv("KOKORO_SERVICE_API_KEY", "")
DEFAULT_VOICE = os.getenv("KOKORO_DEFAULT_VOICE", "am_michael")
MAX_TEXT_CHARS = int(os.getenv("KOKORO_MAX_TEXT_CHARS", "24000"))
MAX_SEGMENT_CHARS = 8000

app = FastAPI(title="Peniel Kokoro TTS", version="1.0.0")
pipeline: KPipeline | None = None
inference_lock = threading.Lock()


class SpeechRequest(BaseModel):
    model: str = "kokoro"
    input: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    voice: str = DEFAULT_VOICE
    response_format: Literal["mp3"] = "mp3"
    speed: float = Field(default=1.0, ge=0.7, le=1.3)


@app.on_event("startup")
def load_model() -> None:
    global pipeline
    pipeline = KPipeline(lang_code="a", device="cpu", repo_id="hexgrad/Kokoro-82M")


@app.get("/health")
def health() -> dict[str, bool | str]:
    return {"status": "ok", "modelLoaded": pipeline is not None}


def text_segments(text: str) -> list[str]:
    segments: list[str] = []
    remaining = text.strip()
    while remaining:
        if len(remaining) <= MAX_SEGMENT_CHARS:
            segments.append(remaining)
            break
        window = remaining[:MAX_SEGMENT_CHARS]
        sentence_breaks = list(re.finditer(r"[.!?][\"'\u201d\u2019]*\s+|\n\s*\n", window))
        end = sentence_breaks[-1].end() if sentence_breaks else window.rfind(" ")
        end = end if end > 0 else MAX_SEGMENT_CHARS
        segments.append(remaining[:end].strip())
        remaining = remaining[end:].lstrip()
    return segments


@app.post("/v1/audio/speech")
def synthesize_speech(
    body: SpeechRequest, authorization: str | None = Header(default=None)
) -> Response:
    if API_KEY and authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    if pipeline is None:
        raise HTTPException(status_code=503, detail="TTS model is still loading")
    if not re.fullmatch(r"[a-z]{2}_[a-z]+", body.voice):
        raise HTTPException(status_code=422, detail="unsupported voice id")

    try:
        with inference_lock:
            chunks: list[np.ndarray] = []
            for index, segment in enumerate(text_segments(body.input)):
                if index:
                    chunks.append(np.zeros(4800, dtype=np.float32))
                for _, _, audio in pipeline(segment, voice=body.voice, speed=body.speed):
                    if audio is not None:
                        samples = audio.detach().cpu().numpy() if hasattr(audio, "detach") else np.asarray(audio)
                        samples = np.asarray(samples, dtype=np.float32).reshape(-1)
                        if samples.size:
                            chunks.append(samples)
        if not chunks:
            raise HTTPException(status_code=502, detail="Kokoro produced no audio")

        waveform = np.concatenate(chunks)
        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, waveform, 24000, format="WAV")
        wav_buffer.seek(0)
        mp3_buffer = io.BytesIO()
        AudioSegment.from_wav(wav_buffer).export(mp3_buffer, format="mp3", bitrate="128k")
        return Response(
            content=mp3_buffer.getvalue(),
            media_type="audio/mpeg",
            headers={"X-Audio-Duration-Seconds": f"{len(waveform) / 24000:.3f}"},
        )
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=502, detail="Speech synthesis failed") from error

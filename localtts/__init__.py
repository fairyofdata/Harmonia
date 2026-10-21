"""LocalTTS: local text-to-speech (and Whisper speech-to-text) for any project.

Python:
    from localtts import synthesize, save_wav
    audio, sr = synthesize('こんにちは', voice='jf_alpha')
    save_wav('out.wav', audio, sr)

HTTP (OpenAI-compatible, see server.py):
    python -m localtts serve            # http://127.0.0.1:8880/v1
"""
import io

import numpy as np

try:  # torch must load its DLLs before winrt does, or c10.dll fails with WinError 1114
    import torch  # noqa: F401
except ImportError:
    pass

from . import kokoro_backend, supertonic_backend, windows_backend


def _translit(name, text, style=None):
    if not name:
        return text
    if name == 'ja_to_hangul':
        from .jp2hangul import ja_to_hangul
        return ja_to_hangul(text, style)
    raise ValueError(f'unknown transliteration: {name}')


def list_voices():
    """[{'id', 'backend', 'language', 'name'}] for every voice available on this machine."""
    return kokoro_backend.list_voices() + supertonic_backend.list_voices() + windows_backend.list_voices()


def synthesize(text, voice='jf_alpha', speed=1.0, translit=None, translit_style=None, pitch=1.0, lang=None):
    """Return (float32 mono samples in [-1, 1], sample_rate).

    translit='ja_to_hangul' reads Japanese text as Hangul (see jp2hangul for
    translit_style) and implies lang='ko'. pitch applies to Windows voices only
    (0.0-2.0); lang to Supertonic voices only (ISO code, e.g. 'ko', 'ja', 'en').
    """
    text = _translit(translit, text, translit_style)
    if translit == 'ja_to_hangul':
        lang = lang or 'ko'
    if voice.startswith(supertonic_backend.PREFIX):
        return supertonic_backend.synthesize(text, voice, speed, lang)
    if voice.startswith(windows_backend.PREFIX):
        return windows_backend.synthesize(text, voice, speed, pitch)
    return kokoro_backend.synthesize(text, voice, speed)


def to_wav_bytes(audio, sample_rate):
    import soundfile as sf
    buf = io.BytesIO()
    sf.write(buf, np.asarray(audio, dtype='float32'), sample_rate, format='WAV', subtype='PCM_16')
    return buf.getvalue()


def save_wav(path, audio, sample_rate):
    with open(path, 'wb') as f:
        f.write(to_wav_bytes(audio, sample_rate))

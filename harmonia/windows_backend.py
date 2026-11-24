"""Windows built-in voices (Windows.Media.SpeechSynthesis / OneCore), no download needed.

Voice ids are 'win_' + the short display name, e.g. win_haruka, win_heami.
Which voices exist depends on the language packs installed on this PC.
"""
import asyncio
import io
import threading

import numpy as np

PREFIX = 'win_'
_lock = threading.Lock()


def _voice_id(info):
    return PREFIX + info.display_name.replace('Microsoft ', '').split(' ')[0].lower()


def _all_voices():
    from winrt.windows.media.speechsynthesis import SpeechSynthesizer
    return list(SpeechSynthesizer.all_voices)


def list_voices():
    try:
        return [{'id': _voice_id(v), 'backend': 'windows', 'language': v.language, 'name': v.display_name}
                for v in _all_voices()]
    except Exception:
        return []


async def _synthesize(text, voice, speed, pitch):
    from winrt.windows.media.speechsynthesis import SpeechSynthesizer
    from winrt.windows.storage.streams import DataReader
    synth = SpeechSynthesizer()
    match = [v for v in _all_voices() if _voice_id(v) == voice]
    if not match:
        raise ValueError(f'unknown windows voice: {voice}')
    synth.voice = match[0]
    synth.options.speaking_rate = speed
    synth.options.audio_pitch = pitch
    stream = await synth.synthesize_text_to_stream_async(text)
    size = stream.size
    reader = DataReader(stream.get_input_stream_at(0))
    await reader.load_async(size)
    buf = bytearray(size)
    reader.read_bytes(buf)
    return bytes(buf)


def synthesize(text, voice, speed=1.0, pitch=1.0):
    import soundfile as sf
    with _lock:
        wav = asyncio.run(_synthesize(text, voice, speed, pitch))
    audio, sr = sf.read(io.BytesIO(wav), dtype='float32')
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    return np.ascontiguousarray(audio), sr

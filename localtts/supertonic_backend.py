"""Supertonic-3 (Supertone, ONNX Runtime; weights under OpenRAIL-M) multilingual TTS.

10 voice styles (M1-M5, F1-F5) usable in any of its 31 languages, including
Korean, Japanese and English. Voice ids are 'st_' + style, e.g. st_F2.
"""
import threading

import numpy as np

PREFIX = 'st_'
STYLES = [f'{g}{i}' for g in 'MF' for i in range(1, 6)]
LANGUAGES = {'ko': 'ko-KR', 'ja': 'ja-JP', 'en': 'en-US'}  # the ones listed; all 31 work

_tts = None
_styles = {}
_lock = threading.Lock()


def list_voices():
    return [{'id': PREFIX + s, 'backend': 'supertonic', 'language': 'multi (31; pass lang)', 'name': s}
            for s in STYLES]


def _engine():
    global _tts
    if _tts is None:
        from supertonic import TTS
        _tts = TTS()
    return _tts


def synthesize(text, voice, speed=1.0, lang=None):
    style_name = voice[len(PREFIX):]
    if style_name not in STYLES:
        raise ValueError(f'unknown supertonic voice: {voice}')
    with _lock:
        tts = _engine()
        if style_name not in _styles:
            _styles[style_name] = tts.get_voice_style(style_name)
        wav, _ = tts.synthesize(text, voice_style=_styles[style_name], lang=lang, speed=speed)
    return np.asarray(wav, dtype='float32').squeeze(), tts.sample_rate

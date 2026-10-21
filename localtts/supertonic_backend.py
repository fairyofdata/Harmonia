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


def _make_supported(tts, text):
    """Rewrite words with characters outside the model's vocabulary (rare kanji) as their
    UniDic kana reading; drop whatever is still unsupported."""
    proc = tts.model.text_processor
    ok, bad = proc.validate_text(text)
    if ok:
        return text
    import fugashi
    bad = set(bad)
    parts = []
    for w in fugashi.Tagger()(text):
        kana = getattr(w.feature, 'kana', None)
        parts.append(w.white_space + (kana if bad & set(w.surface) and kana and kana != '*' else w.surface))
    text = ''.join(parts)
    ok, bad = proc.validate_text(text)
    return text if ok else ''.join(c for c in text if c not in set(bad))


def synthesize(text, voice, speed=1.0, lang=None):
    style_name = voice[len(PREFIX):]
    if style_name not in STYLES:
        raise ValueError(f'unknown supertonic voice: {voice}')
    with _lock:
        tts = _engine()
        text = _make_supported(tts, text)
        if style_name not in _styles:
            _styles[style_name] = tts.get_voice_style(style_name)
        wav, _ = tts.synthesize(text, voice_style=_styles[style_name], lang=lang, speed=speed)
    return np.asarray(wav, dtype='float32').squeeze(), tts.sample_rate

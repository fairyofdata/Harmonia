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
        import onnxruntime as ort
        import supertonic.loader
        from supertonic import TTS
        if 'CUDAExecutionProvider' in ort.get_available_providers():  # onnxruntime-gpu installed
            # supertonic only lists the CPU provider; CUDA/cuDNN DLLs come from torch (imported first)
            supertonic.loader.DEFAULT_ONNX_PROVIDERS = ['CUDAExecutionProvider', 'CPUExecutionProvider']
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


MAX_CHUNK_CHARS = 80  # the vector estimator attends over at most 1000 latent frames per chunk


def _chunks(text):
    """Supertonic splits only at sentence punctuation; long unpunctuated text overflows
    its attention window (the tail comes out garbled or dropped), so split further at
    spaces -- and at characters where there are none, as in Japanese and Chinese."""
    out, cur = [], ''
    for word in text.split(' '):
        while len(word) > MAX_CHUNK_CHARS:
            if cur:
                out.append(cur)
                cur = ''
            out.append(word[:MAX_CHUNK_CHARS])
            word = word[MAX_CHUNK_CHARS:]
        if cur and len(cur) + 1 + len(word) > MAX_CHUNK_CHARS:
            out.append(cur)
            cur = word
        else:
            cur = f'{cur} {word}' if cur else word
    if cur:
        out.append(cur)
    return out


def synthesize(text, voice, speed=1.0, lang=None):
    style_name = voice[len(PREFIX):]
    if style_name not in STYLES:
        raise ValueError(f'unknown supertonic voice: {voice}')
    with _lock:
        tts = _engine()
        text = _make_supported(tts, text)
        if style_name not in _styles:
            _styles[style_name] = tts.get_voice_style(style_name)
        pieces = [tts.synthesize(chunk, voice_style=_styles[style_name], lang=lang, speed=speed)[0]
                  for chunk in _chunks(text)]
    pause = np.zeros(int(0.15 * tts.sample_rate), dtype='float32')
    audio = []
    for i, p in enumerate(pieces):
        audio.extend([np.asarray(p, dtype='float32').squeeze()] + ([pause] if i < len(pieces) - 1 else []))
    return np.concatenate(audio), tts.sample_rate

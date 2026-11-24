"""Kokoro-82M (Apache-2.0) neural TTS. Runs on CUDA when available, else CPU."""
import re
import sys
import threading

import numpy as np

SAMPLE_RATE = 24000
# voice prefix -> (KPipeline lang_code, language tag)
LANGS = {'a': ('a', 'en-US'), 'b': ('b', 'en-GB'), 'j': ('j', 'ja-JP'), 'z': ('z', 'zh-CN'),
         'e': ('e', 'es'), 'f': ('f', 'fr'), 'h': ('h', 'hi'), 'i': ('i', 'it'), 'p': ('p', 'pt-BR')}
VOICES = {
    'j': ['jf_alpha', 'jf_gongitsune', 'jf_nezumi', 'jf_tebukuro', 'jm_kumo'],
    'a': ['af_heart', 'af_bella', 'af_nicole', 'af_sarah', 'am_michael', 'am_fenrir', 'am_puck'],
    'b': ['bf_emma', 'bf_isabella', 'bm_george', 'bm_fable'],
    'z': ['zf_xiaobei', 'zf_xiaoni', 'zm_yunjian', 'zm_yunxi'],
}

_pipelines = {}
_lock = threading.Lock()


def list_voices():
    return [{'id': v, 'backend': 'kokoro', 'language': LANGS[p][1], 'name': v}
            for p, vs in VOICES.items() for v in vs]


def _stub_spacy_if_missing():
    """kokoro imports misaki.en (and so spacy) even for Japanese; spacy has no 3.14 build.
    Without spacy, English voices fail with a clear error and the rest works."""
    try:
        import spacy  # noqa: F401
    except ImportError:
        import types

        class _Missing(types.ModuleType):
            def __getattr__(self, name):
                if name.startswith('__'):  # introspection (inspect, hasattr) must see a plain module
                    raise AttributeError(name)
                raise ImportError('English Kokoro voices need spacy (pip install spacy spacy-curated-transformers)')

        sys.modules['spacy'] = _Missing('spacy')


def _pipeline(lang_code):
    if lang_code not in _pipelines:
        from . import _mojimoji_shim
        sys.modules.setdefault('mojimoji', _mojimoji_shim)  # misaki[ja] needs it; no 3.14 wheel
        _stub_spacy_if_missing()
        import torch
        from kokoro import KPipeline
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        _pipelines[lang_code] = KPipeline(lang_code=lang_code, device=device)
    return _pipelines[lang_code]


MAX_PHONEMES = 500  # model context is 512 tokens incl. start/end


def _split(text):
    """Sentence-ish pieces so each g2p call stays short."""
    parts = [p.strip() for p in re.split(r'(?<=[。！？!?\n])', text)]
    return [p for p in parts if p]


def _split_phonemes(ps):
    if len(ps) <= MAX_PHONEMES:
        return [ps] if ps.strip() else []
    out, cur = [], ''
    for seg in re.split(r'(?<=[,.;:!? ])', ps):
        if len(cur) + len(seg) > MAX_PHONEMES and cur:
            out.append(cur)
            cur = ''
        cur += seg
    if cur.strip():
        out.append(cur[:MAX_PHONEMES])
    return out


def synthesize(text, voice, speed=1.0):
    prefix = voice[:1]
    if prefix not in LANGS:
        raise ValueError(f'unknown kokoro voice: {voice}')
    with _lock:
        pipe = _pipeline(LANGS[prefix][0])
        pack = pipe.load_voice(voice)
        chunks = []
        # call g2p + model directly: misaki >= 0.9 returns (phonemes, tokens) from non-English
        # g2p, which kokoro 0.7's own loop treats as the phoneme string
        for part in _split(text):
            ps = pipe.g2p(part)
            ps = ps[0] if isinstance(ps, tuple) else ps
            for piece in _split_phonemes(ps):
                audio = pipe.model(piece, pack[len(piece) - 1], speed)
                chunks.append(np.asarray(audio, dtype='float32'))
    if not chunks:
        return np.zeros(0, dtype='float32'), SAMPLE_RATE
    return np.concatenate(chunks), SAMPLE_RATE

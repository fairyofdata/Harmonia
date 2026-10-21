"""Local Whisper speech-to-text (transformers, CUDA fp16 when available).

Clips up to 30 s (Whisper's window); longer audio is truncated.
"""
import io
import os
import threading

import numpy as np

DEFAULT_MODEL = os.getenv('LOCALTTS_WHISPER_MODEL', 'openai/whisper-large-v3')
TARGET_SR = 16000

_models = {}
_lock = threading.Lock()


def _load(model):
    if model not in _models:
        import torch
        from transformers import WhisperForConditionalGeneration, WhisperProcessor
        cuda = torch.cuda.is_available()
        dtype = torch.float16 if cuda else torch.float32
        m = WhisperForConditionalGeneration.from_pretrained(model, dtype=dtype).to('cuda' if cuda else 'cpu').eval()
        _models[model] = (WhisperProcessor.from_pretrained(model), m, dtype)
    return _models[model]


def load_audio(data):
    """bytes or path of a wav/flac/mp3/ogg file -> (16 kHz float32 mono, duration in seconds)."""
    import soundfile as sf
    from scipy.signal import resample_poly
    audio, sr = sf.read(io.BytesIO(data) if isinstance(data, (bytes, bytearray)) else data, dtype='float32')
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    duration = len(audio) / sr
    if sr != TARGET_SR:
        g = np.gcd(sr, TARGET_SR)
        audio = resample_poly(audio, TARGET_SR // g, sr // g).astype('float32')
    return audio, duration


def transcribe_many(items, language=None, model=DEFAULT_MODEL, batch_size=8):
    """List of bytes/paths -> [{'text', 'language' (ISO code), 'duration'}], same order.
    language=None lets Whisper detect it per clip."""
    import torch
    loaded = [load_audio(d) for d in items]
    results = []
    with _lock:
        proc, m, dtype = _load(model)
        for i in range(0, len(loaded), batch_size):
            batch = loaded[i:i + batch_size]
            feats = proc([a for a, _ in batch], sampling_rate=TARGET_SR, return_tensors='pt').input_features
            feats = feats.to(m.device, dtype)
            with torch.no_grad():
                if language:
                    langs = [language] * len(batch)
                else:  # same argmax generate() uses; generate() itself no longer returns the token
                    ids = m.detect_language(feats).flatten().tolist()
                    langs = [t.strip('<|>') for t in proc.tokenizer.convert_ids_to_tokens(ids)]
                seqs = m.generate(feats, task='transcribe', language=langs)
            texts = proc.batch_decode(seqs, skip_special_tokens=True)
            for text, lang, (_, duration) in zip(texts, langs, batch):
                results.append({'text': text.strip(), 'language': lang, 'duration': duration})
    return results


def transcribe(data, language=None, model=DEFAULT_MODEL):
    """Return {'text', 'language' (ISO code), 'duration'}. language=None lets Whisper detect it."""
    return transcribe_many([data], language=language, model=model)[0]

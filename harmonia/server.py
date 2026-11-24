"""OpenAI-compatible local speech server (binds 127.0.0.1 only).

    POST /v1/audio/speech           {"model", "input", "voice", "speed"?, "response_format": "wav"|"pcm",
                                     "translit"?: "ja_to_hangul", "translit_style"?: {...}, "pitch"?, "lang"?}
                                    -> audio bytes
    POST /v1/audio/transcriptions   multipart: file, model?, language?, response_format? (json|verbose_json|text)
    POST /v1/batch/transcriptions   {"files_b64": [...], "language"?, "model"?} -> {"results": [verbose_json, ...]}
                                    (not in the OpenAI API; batches clips on the GPU)
    POST /v1/translit               {"text", "translit"?, "translit_style"?} -> {"text"}
                                    (not in the OpenAI API; reading conversion alone)
    GET  /v1/voices                 -> available voices
    GET  /health

From any project:
    from openai import OpenAI
    client = OpenAI(base_url='http://127.0.0.1:8880/v1', api_key='local')
    wav = client.audio.speech.create(model='kokoro', voice='jf_alpha', input='...', response_format='wav').content
"""
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel

import harmonia
from harmonia import stt

app = FastAPI(title='Harmonia')


class SpeechRequest(BaseModel):
    input: str
    voice: str = 'jf_alpha'
    model: str = 'local'
    speed: float = 1.0
    response_format: str = 'wav'
    translit: str | None = None
    translit_style: dict | None = None
    pitch: float = 1.0
    lang: str | None = None


@app.get('/health')
def health():
    return {'ok': True}


@app.get('/v1/voices')
def voices():
    return {'voices': harmonia.list_voices()}


class TranslitRequest(BaseModel):
    text: str
    translit: str = 'ja_to_hangul'
    translit_style: dict | None = None


@app.post('/v1/translit')
def translit(req: TranslitRequest):
    """Reading conversion on its own, without synthesizing (not in the OpenAI API)."""
    try:
        return {'text': harmonia._translit(req.translit, req.text, req.translit_style)}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post('/v1/audio/speech')
def speech(req: SpeechRequest):
    if req.response_format not in ('wav', 'pcm'):
        raise HTTPException(400, 'response_format must be wav or pcm (no ffmpeg encoder here)')
    try:
        audio, sr = harmonia.synthesize(req.input, voice=req.voice, speed=req.speed, translit=req.translit,
                                        translit_style=req.translit_style, pitch=req.pitch, lang=req.lang)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if req.response_format == 'pcm':
        import numpy as np
        pcm = (np.clip(audio, -1, 1) * 32767).astype('<i2').tobytes()
        return Response(pcm, media_type='audio/pcm', headers={'X-Sample-Rate': str(sr)})
    return Response(harmonia.to_wav_bytes(audio, sr), media_type='audio/wav')


@app.post('/v1/audio/transcriptions')
async def transcriptions(file: UploadFile = File(...), model: str = Form('whisper-large-v3'),
                         language: str | None = Form(None), response_format: str = Form('json')):
    hf_model = model if '/' in model else stt.DEFAULT_MODEL
    result = stt.transcribe(await file.read(), language=language or None, model=hf_model)
    if response_format == 'text':
        return PlainTextResponse(result['text'])
    if response_format == 'verbose_json':
        return JSONResponse(result)
    return JSONResponse({'text': result['text']})


class BatchTranscriptionRequest(BaseModel):
    files_b64: list[str]
    language: str | None = None
    model: str = 'whisper-large-v3'
    batch_size: int = 8


@app.post('/v1/batch/transcriptions')
def batch_transcriptions(req: BatchTranscriptionRequest):
    import base64
    hf_model = req.model if '/' in req.model else stt.DEFAULT_MODEL
    items = [base64.b64decode(b) for b in req.files_b64]
    return {'results': stt.transcribe_many(items, language=req.language or None, model=hf_model,
                                           batch_size=req.batch_size)}


def serve(host='127.0.0.1', port=8880):
    import uvicorn
    uvicorn.run(app, host=host, port=port)

r"""MCP server for LocalTTS: this PC's speech synthesis and transcription as MCP tools,
so any project (Claude Code, an editor, your own agent) can call them.

    claude mcp add localtts -- C:\Users\fairy\gitdev\LocalTTS\venv\Scripts\python.exe -m localtts_mcp

It is a thin proxy over the HTTP server (`python -m localtts serve`): every tool is one
HTTP call, and the server is started in the background on first use if it is not already
running. The models therefore load once on this PC however many projects call in -- and
this process itself holds no model, which is why this module sits outside the `localtts`
package (importing that package imports torch).

Environment:
    LOCALTTS_URL        server base url (default http://127.0.0.1:8880)
    LOCALTTS_OUT_DIR    where synthesized wav files are written (default <temp>/localtts)
    LOCALTTS_AUTOSTART  '0' to never start the server from here
    LOCALTTS_PYTHON     python that has localtts installed (default: the one running this)
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import wave
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError   # anything else reaches the caller as
                                                        # a bare 'Error executing tool <name>'

BASE_URL = os.getenv('LOCALTTS_URL', 'http://127.0.0.1:8880').rstrip('/')
OUT_DIR = Path(os.getenv('LOCALTTS_OUT_DIR') or Path(tempfile.gettempdir()) / 'localtts')
CREATE_BREAKAWAY_FROM_JOB = 0x01000000   # not in subprocess; see _start_server
START_TIMEOUT = 90          # uvicorn comes up in a second; models load lazily per endpoint
CALL_TIMEOUT = 900          # a first call downloads model weights (Whisper large-v3 is ~3 GB)

server = MCPServer(name='localtts')


# --- the HTTP server ---------------------------------------------------------------

def _healthy(timeout=1.0):
    try:
        with urllib.request.urlopen(f'{BASE_URL}/health', timeout=timeout) as r:
            return r.status == 200
    except OSError:
        return False


def _start_server():
    """Launch `localtts serve` in the background, to be shared with every other project.

    MCP clients put their servers in a Windows job object that kills every member on
    shutdown, and breaking out of it only escapes the innermost job, so expect this
    server to go down with the MCP client that started it. The next call starts it
    again (weights come from the local Hugging Face cache, so that costs seconds).
    Run `python -m localtts serve` yourself to keep one up permanently; this never
    stops a server it did not start.
    """
    url = urllib.parse.urlsplit(BASE_URL)
    if url.hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise ToolError(f'{BASE_URL} is not local; start the server there yourself')
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log = open(OUT_DIR / 'server.log', 'ab')
    cmd = [os.getenv('LOCALTTS_PYTHON') or sys.executable, '-m', 'localtts', 'serve',
           '--port', str(url.port or 8880)]

    def spawn(flags):
        return subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                creationflags=flags, start_new_session=os.name != 'nt')

    if os.name != 'nt':
        proc = spawn(0)
    else:
        detached = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
        try:    # MCP clients run us inside a job object, which kills a merely detached
            proc = spawn(detached | CREATE_BREAKAWAY_FROM_JOB)   # child when we exit
        except OSError:   # the job forbids breaking out: the server then lives as long
            proc = spawn(detached)                               # as this MCP process
    deadline = time.monotonic() + START_TIMEOUT
    while time.monotonic() < deadline:
        if _healthy():
            return
        if proc.poll() is not None:
            tail = (OUT_DIR / 'server.log').read_text('utf-8', 'replace')[-800:]
            raise ToolError(f'localtts serve exited ({proc.returncode}):\n{tail}')
        time.sleep(0.3)
    raise ToolError(f'localtts serve did not answer on {BASE_URL} within {START_TIMEOUT}s')


def _ensure_server():
    if _healthy():
        return
    if os.getenv('LOCALTTS_AUTOSTART', '1') == '0':
        raise ToolError(f'no server on {BASE_URL} and LOCALTTS_AUTOSTART=0; '
                        f'run: python -m localtts serve')
    _start_server()


def _post(path, payload):
    _ensure_server()
    req = urllib.request.Request(BASE_URL + path, data=json.dumps(payload).encode('utf-8'),
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=CALL_TIMEOUT) as r:
            return r.read(), r.headers.get_content_type()
    except urllib.error.URLError as e:
        if not isinstance(e, urllib.error.HTTPError):
            raise ToolError(f'{BASE_URL} unreachable: {e.reason}') from None
        detail = e.read().decode('utf-8', 'replace')
        try:
            detail = json.loads(detail).get('detail', detail)
        except ValueError:
            pass
        raise ToolError(f'{path}: {detail}') from None


def _get_json(path):
    _ensure_server()
    with urllib.request.urlopen(BASE_URL + path, timeout=CALL_TIMEOUT) as r:
        return json.loads(r.read())


# --- tools -------------------------------------------------------------------------

@server.tool()
def list_voices() -> list[dict]:
    """Voices available on this PC, as [{id, backend, language, name}].

    Backends: 'supertonic' (st_*, 31 languages, needs `lang`), 'kokoro' (jf_*/jm_*
    Japanese; en/zh voices are listed but unusable on this PC), 'windows' (win_*,
    the installed Windows voices, including Korean win_heami).
    """
    return _get_json('/v1/voices')['voices']


@server.tool()
def synthesize(text: str, voice: str = 'st_F2', lang: str | None = None, speed: float = 1.0,
               out_path: str | None = None, translit: str | None = None,
               translit_style: dict | None = None, pitch: float = 1.0) -> dict:
    """Speak `text` into a wav file on this PC and return {path, seconds, sample_rate}.

    Nothing is played and no audio is returned: read or play the file at `path`.

    voice:          st_M1-st_M5 / st_F1-st_F5 (Supertonic, any of 31 languages, pass
                    `lang`), jf_alpha and other jf_*/jm_* (Kokoro, Japanese only),
                    win_haruka / win_heami etc. (Windows voices). list_voices() has all.
    lang:           ISO code for Supertonic voices: 'ko', 'ja', 'en', ... Ignored by others.
    speed:          1.0 is normal.
    out_path:       where to write; defaults to a new file under LOCALTTS_OUT_DIR.
    translit:        'ja_to_hangul' reads Japanese text as Hangul, so a Korean voice can
                    say it (implies lang='ko'). See ja_to_hangul() for translit_style.
    pitch:          Windows voices only, 0.0-2.0.
    """
    audio, _ = _post('/v1/audio/speech',
                     {'input': text, 'voice': voice, 'speed': speed, 'response_format': 'wav',
                      'lang': lang, 'translit': translit, 'translit_style': translit_style,
                      'pitch': pitch})
    if out_path:
        path = Path(out_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUT_DIR / f'{voice}-{uuid.uuid4().hex[:8]}.wav'
    path.write_bytes(audio)
    with wave.open(str(path)) as w:
        seconds, sample_rate = w.getnframes() / w.getframerate(), w.getframerate()
    return {'path': str(path), 'seconds': round(seconds, 2), 'sample_rate': sample_rate,
            'voice': voice}


@server.tool()
def transcribe(path: str, language: str | None = None) -> dict:
    """Transcribe an audio file on this PC with Whisper large-v3.

    Returns {text, language (detected ISO code), duration}. wav/flac/mp3/ogg; only the
    first 30 seconds are transcribed (Whisper's window). `language` skips detection.
    """
    return transcribe_many([path], language=language)[0]


@server.tool()
def transcribe_many(paths: list[str], language: str | None = None) -> list[dict]:
    """Transcribe several audio files in one GPU batch, in order (~0.3 s per clip).

    Same result as transcribe() per file, and much faster than calling it repeatedly.
    """
    files_b64 = []
    for p in paths:
        f = Path(p).expanduser()
        if not f.is_file():
            raise ToolError(f'no such file: {f}')
        files_b64.append(base64.b64encode(f.read_bytes()).decode('ascii'))
    body, _ = _post('/v1/batch/transcriptions', {'files_b64': files_b64, 'language': language})
    return json.loads(body)['results']


@server.tool()
def ja_to_hangul(text: str, style: dict | None = None) -> str:
    """Japanese text -> the Hangul a Korean speaker would read it as ('ありがとう' -> '아리가토').

    A phonetic approximation (not the official 외래어 표기법), for singing along or for
    reading Japanese with a Korean voice. Readings come from UniDic, so unusual lyric
    readings may differ. `style` overrides any of:

        {'tsu': 'ㅊ'|'ㅅ'|'ㅉ',  'initial': 'aspirated'|'plain',
         'long_vowel': 'drop'|'keep',  'n_assim': false|true}
    """
    body, _ = _post('/v1/translit', {'text': text, 'translit': 'ja_to_hangul',
                                     'translit_style': style})
    return json.loads(body)['text']


def main():
    server.run(transport='stdio')


if __name__ == '__main__':
    main()

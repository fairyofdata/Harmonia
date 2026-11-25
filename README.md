<!-- Source: README_KR.md (Korean is the source; English and Japanese are translations) · synced 2026-11-26 -->

# Harmonia

[English](README.md) · [한국어](README_KR.md) · [日本語](README_JP.md)

Formerly LocalTTS (renamed 2026-11-24, [ADR-0007](docs/adr/0007-rename-to-harmonia.md)).

Text-to-speech (TTS) and speech-to-text (STT) that run on this PC. No cloud calls and no cost. Other projects can use it in two ways.

- **HTTP server**: same format as the OpenAI API, so only `base_url` changes ([below](#use-as-a-server-from-other-projects)).
- **MCP server**: agents call it directly as tools ([below](#use-over-mcp-from-agents-in-other-projects)).

*Harmonia* is Latin for "harmony" (from Greek *harmonía*, "a fitting together"): text into voice and voice into text, tuned in one place.

## What is inside

| Kind | Engine | Voice ids | Languages | License |
|---|---|---|---|---|
| TTS | [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) (GPU) | `jf_alpha` `jf_gongitsune` `jf_nezumi` `jf_tebukuro` `jm_kumo` and more | Japanese (English and Chinese voices need spacy, see below) | Apache-2.0 |
| TTS | [Supertonic-3](https://github.com/supertone-inc/supertonic) (ONNX, GPU if available) | `st_M1`–`st_M5`, `st_F1`–`st_F5` | 31 languages (set with `lang`: `ko`, `ja`, `en` …) | weights OpenRAIL-M, SDK MIT |
| TTS | Windows built-in voices (OneCore) | `win_haruka` `win_ayumi` `win_ichiro` (Japanese), `win_heami` (Korean) | depends on installed language packs | Windows |
| STT | Whisper large-v3 (GPU fp16) | — | multilingual, language auto-detected or given | MIT |
| Conversion | Japanese → Hangul reading as a Korean speaker would say it (`ja_to_hangul`) | — | — | this repository |

`python -m harmonia voices` lists the voices available on this PC.

Supertonic fails on characters outside its vocabulary (rare kanji and the like). Words containing such characters are read through their kana reading from UniDic, and characters still left over are dropped. Its input length per call is also limited, so long text is synthesized in 80-character chunks with a 0.15-second pause between them (Japanese and Chinese, which have no spaces, are cut by character count).

## Use as a server (from other projects)

```bash
<Harmonia folder>\venv\Scripts\python.exe -m harmonia serve --port 8880
```

It listens on `127.0.0.1` only, so it cannot be reached from outside.

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8880/v1", api_key="local")

# TTS (wav only, no ffmpeg)
wav = client.audio.speech.create(model="local", voice="st_F2", input="안녕하세요",
                                 response_format="wav", extra_body={"lang": "ko"}).content

# Turn Japanese into a Hangul reading as a Korean speaker would read it, and read it with a Korean voice
wav = client.audio.speech.create(model="local", voice="st_M3", input="明日は晴れるといいね", response_format="wav",
                                 extra_body={"translit": "ja_to_hangul",
                                             "translit_style": {"tsu": "ㅅ", "long_vowel": "keep"}}).content

# STT
with open("clip.wav", "rb") as f:
    r = client.audio.transcriptions.create(model="whisper-large-v3", file=f, response_format="verbose_json")
print(r.text, r.language)
```

Extensions not in the OpenAI API:

| Endpoint / field | Description |
|---|---|
| `translit`, `translit_style` on `POST /v1/audio/speech` | `ja_to_hangul` reading conversion and its spelling style |
| `lang` on `POST /v1/audio/speech` | language code for Supertonic voices |
| `pitch` on `POST /v1/audio/speech` | pitch of Windows voices (0.0–2.0) |
| `POST /v1/batch/transcriptions` | `{"files_b64": [...], "language": null}` → transcribe several clips on the GPU at once (about 0.3 s per clip) |
| `POST /v1/translit` | `{"text": "...", "translit_style": {...}}` → reading conversion only, no synthesis |
| `GET /v1/voices` | list of voices |

## Use over MCP (from agents in other projects)

Put it under the top-level `mcpServers` of the Claude Code settings (`~/.claude.json`) and it shows up in every project.

```json
"harmonia": {
  "type": "stdio",
  "command": "<Harmonia folder>\\venv\\Scripts\\python.exe",
  "args": ["-m", "harmonia_mcp"],
  "env": {}
}
```

`command` must be **the python of this project's venv**. `mcp` and `harmonia` are installed only there, and the same python is used when the server is started automatically. After changing it, restart the app (or `claude`) to pick it up.

If the `claude` CLI is installed, this puts it in the same place. Without `-s user` it is visible only in the folder where the command was run.

```bash
claude mcp add harmonia -s user -- <Harmonia folder>\venv\Scripts\python.exe -m harmonia_mcp
```

Five tools are added.

| Tool | What it does |
|---|---|
| `list_voices` | voices on this PC |
| `synthesize` | text → saves a wav file and returns `{path, seconds, sample_rate}` (it does not play the sound) |
| `transcribe` | audio file → `{text, language, duration}` |
| `transcribe_many` | several files on the GPU at once (about 0.3 s per clip) |
| `ja_to_hangul` | Japanese → Hangul reading |

The MCP server is a thin proxy that only forwards requests to the HTTP server above. If the server is not running, **it starts one in the background on the first call.** So even when several projects call at once, the models are loaded once on this PC, and the MCP process itself holds no model (it does not even import torch, so it starts in 0.7 s). That is why `harmonia_mcp.py` sits outside the package — importing `harmonia` pulls in torch.

A server started automatically **may go down when the MCP client exits.** The MCP client puts the server process into a job object and cleans it up as a whole on exit (confirmed). Calling again brings it back up, and since the weights are read from the local cache it takes a few seconds. To keep it running, start `python -m harmonia serve` yourself; the MCP side never touches that server.

| Environment variable | Default |
|---|---|
| `HARMONIA_URL` | `http://127.0.0.1:8880` |
| `HARMONIA_OUT_DIR` | `<temp>/harmonia` (where synthesized wavs and server logs go) |
| `HARMONIA_AUTOSTART` | `1` (with `0` you must start the server yourself) |
| `HARMONIA_PYTHON` | the python that runs this MCP server (used to start the server) |

After a fresh server start, the first `transcribe` takes around 10 seconds to load the Whisper weights onto the GPU (the very first time it downloads about 3 GB); after that it answers right away. `synthesize` takes about a second.

## Use directly from Python

```python
import sys; sys.path.insert(0, r"<Harmonia folder>")   # or run in this venv
import harmonia
audio, sr = harmonia.synthesize("こんにちは", voice="jf_alpha")
harmonia.save_wav("out.wav", audio, sr)

from harmonia.jp2hangul import ja_to_hangul
ja_to_hangul("ありがとう")                       # '아리가토'
ja_to_hangul("ありがとう", {"long_vowel": "keep"})  # '아리가토오'
```

`jp2hangul` can be imported from another venv as long as fugashi and unidic-lite are there.

## Command line

```bash
python -m harmonia voices
python -m harmonia say "こんにちは" -o out.wav --voice jf_alpha
python -m harmonia say "こんにちは" -o out.wav --voice st_F1 --translit ja_to_hangul
python -m harmonia hangul "東京タワーで待ってる"
python -m harmonia transcribe out.wav --language ja
```

## Hangul reading (`ja_to_hangul`) rules

Kanji are read with UniDic pronunciations (fugashi + unidic-lite), then converted to how a Korean speaker reads Japanese. It is a pronunciation approximation, not the official loanword spelling.

| Item | Default | Values settable with `translit_style` |
|---|---|---|
| `tsu` (つ) | `ㅊ` → 츠 | `ㅅ` → 쓰, `ㅉ` → 쯔 |
| `initial` (voiceless word-initial) | `aspirated` → 카·타 | `plain` → 가·다 (official spelling style) |
| `long_vowel` (long vowels) | `drop` → 토 | `keep` → 토오 |
| `n_assim` (ん before ㅁ·ㅂ·ㅍ) | `false` → ㄴ | `true` → ㅁ |

Rules always applied: っ → final ㅅ, ん → final ㄴ, ス·ズ → 스·즈, the ファ row → ㅍ, spaces between word units. Latin-script spans are left as they are. Special readings as in lyrics (当て字, ruby) may differ from the dictionary reading.

## Install (Windows, Python 3.14)

```bash
py -3.14 -m venv venv
venv\Scripts\python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cu126
venv\Scripts\python -m pip install -r requirements.txt
venv\Scripts\python -m pip install --no-deps kokoro
venv\Scripts\python -m pip install --no-deps --ignore-requires-python misaki==0.9.4
venv\Scripts\python -m pip install --no-deps -e .
```

Model weights (Whisper large-v3 about 3 GB, Kokoro, Supertonic) are downloaded into the Hugging Face cache (`~/.cache/huggingface`) on first use. GPU memory with Whisper and Kokoro loaded together is about 4.5 GB (checked on an RTX 3070 8 GB).

## Tests

```bash
venv\Scripts\python -X utf8 -m unittest discover -s tests
```

33 tests, no model and no GPU, done in under 0.1 s. They check the two places where the right answer is fixed.

- **Reading rules** (`jp2hangul`): the rules always applied (っ·ん finals, ス·ズ, the ファ row, contracted sounds, spacing) and each of the four `translit_style` options at both values. For all 24 option combinations they also check that **not a single kana is left** (a new rule that drops existing kana gets caught here).
- **Long-text splitting** (`supertonic_backend._chunks`): every chunk is within the limit, no empty chunks, no characters lost, and how the boundary (79/80/81 characters) is cut.

The audio itself cannot be checked automatically. It is checked by ear, or by transcribing the synthesized wav with Whisper and comparing with the input (the 80-character limit of `_chunks` was confirmed that way).

## Decision records

Design decisions and their reasons are in [docs/adr/](docs/adr/README.md) (Korean).

## Workarounds for Python 3.14

- **kokoro** pins `numpy==1.26.4`, which has no build for 3.14, so it is installed with `--no-deps` (works with the latest numpy).
- **misaki 0.9.4** is marked for below 3.13 but is pure Python, so it is used as is.
  - Its pipeline and return format differ from kokoro 0.7, so `kokoro_backend` calls the g2p and the model directly.
- **mojimoji** (Cython, no 3.14 build) is replaced by a `jaconv`-based stand-in (`_mojimoji_shim.py`).
- **spacy** has no 3.14 build, so the English and Chinese Kokoro voices cannot be used.
  - Japanese works without spacy thanks to an empty stand-in module.
  - For English, use Supertonic (`st_*`, `lang="en"`).
- **Supertonic on GPU:** the package defaults to CPU only. If onnxruntime-gpu is installed, the backend turns on the CUDA execution provider.
  - For 9.5 s of audio, CPU 9.2 s → GPU 0.17 s.
  - onnxruntime-gpu 1.31 requires CUDA 13 DLLs (`cublasLt64_13.dll`), so it is pinned to 1.24.1, which matches torch cu126. The needed CUDA and cuDNN DLLs come from torch, which is imported first.
- **Order of torch and winrt**: importing winrt first makes torch DLL initialization fail (WinError 1114), so the package imports torch first.

## License

The code in this repository is [MIT](LICENSE). Engines and model weights follow their own licenses as listed in the "What is inside" table above (the weights are not in this repository).

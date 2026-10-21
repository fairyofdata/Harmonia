# LocalTTS

이 PC에서 돌아가는 음성 합성(TTS)·음성 인식(STT) 도구입니다. OpenAI API와 같은 형식의 HTTP 서버로 열려 있어서, 다른 프로젝트에서는 `base_url`만 바꾸면 그대로 쓸 수 있습니다. 클라우드 호출과 비용이 없습니다.

## 들어 있는 것

| 종류 | 엔진 | 목소리 id | 언어 | 라이선스 |
|---|---|---|---|---|
| TTS | [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) (GPU) | `jf_alpha` `jf_gongitsune` `jf_nezumi` `jf_tebukuro` `jm_kumo` 외 | 일본어 (영어·중국어 목소리는 spacy 필요, 아래 참고) | Apache-2.0 |
| TTS | [Supertonic-3](https://github.com/supertone-inc/supertonic) (ONNX, CPU) | `st_M1`~`st_M5`, `st_F1`~`st_F5` | 31개 언어 (`lang`으로 지정: `ko`, `ja`, `en` …) | 가중치 OpenRAIL-M, SDK MIT |
| TTS | Windows 기본 음성 (OneCore) | `win_haruka` `win_ayumi` `win_ichiro` (일본어), `win_heami` (한국어) | 설치된 언어 팩에 따름 | Windows |
| STT | Whisper large-v3 (GPU fp16) | — | 다국어, 언어 자동 감지 또는 지정 | MIT |
| 변환 | 일본어 → 한국인식 한글 독음 (`ja_to_hangul`) | — | — | 이 저장소 |

`python -m localtts voices`로 이 PC에서 쓸 수 있는 목소리 목록을 봅니다.

Supertonic은 어휘에 없는 글자(드문 한자 등)가 있으면 오류를 냅니다. 그래서 그런 글자가 든 단어는 UniDic의 가나 읽기로 바꿔 읽고, 그래도 남는 글자는 빼고 읽습니다.

## 서버로 쓰기 (다른 프로젝트에서)

```bash
C:\Users\fairy\LocalTTS\venv\Scripts\python.exe -m localtts serve --port 8880
```

`127.0.0.1`에만 열리므로 외부에서는 접근할 수 없습니다.

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8880/v1", api_key="local")

# TTS (wav만 지원, ffmpeg 없음)
wav = client.audio.speech.create(model="local", voice="st_F2", input="안녕하세요",
                                 response_format="wav", extra_body={"lang": "ko"}).content

# 일본어를 한국인이 읽듯 한글 독음으로 바꿔 한국어 목소리로 읽기
wav = client.audio.speech.create(model="local", voice="st_M3", input="明日は晴れるといいね", response_format="wav",
                                 extra_body={"translit": "ja_to_hangul",
                                             "translit_style": {"tsu": "ㅅ", "long_vowel": "keep"}}).content

# STT
with open("clip.wav", "rb") as f:
    r = client.audio.transcriptions.create(model="whisper-large-v3", file=f, response_format="verbose_json")
print(r.text, r.language)
```

OpenAI API에 없는 확장:

| 엔드포인트 / 필드 | 설명 |
|---|---|
| `POST /v1/audio/speech`의 `translit`, `translit_style` | `ja_to_hangul` 독음 변환과 그 표기 방식 |
| `POST /v1/audio/speech`의 `lang` | Supertonic 목소리의 언어 코드 |
| `POST /v1/audio/speech`의 `pitch` | Windows 목소리의 음높이 (0.0~2.0) |
| `POST /v1/batch/transcriptions` | `{"files_b64": [...], "language": null}` → 여러 클립을 GPU에서 한 번에 받아쓰기 (클립당 약 0.3초) |
| `GET /v1/voices` | 목소리 목록 |

## Python에서 바로 쓰기

```python
import sys; sys.path.insert(0, r"C:\Users\fairy\LocalTTS")   # 또는 이 venv에서 실행
import localtts
audio, sr = localtts.synthesize("こんにちは", voice="jf_alpha")
localtts.save_wav("out.wav", audio, sr)

from localtts.jp2hangul import ja_to_hangul
ja_to_hangul("ありがとう")                       # '아리가토'
ja_to_hangul("ありがとう", {"long_vowel": "keep"})  # '아리가토오'
```

`jp2hangul`은 fugashi와 unidic-lite만 있으면 다른 venv에서도 import됩니다.

## 명령줄

```bash
python -m localtts voices
python -m localtts say "こんにちは" -o out.wav --voice jf_alpha
python -m localtts say "こんにちは" -o out.wav --voice st_F1 --translit ja_to_hangul
python -m localtts hangul "東京タワーで待ってる"
python -m localtts transcribe out.wav --language ja
```

## 한글 독음 (`ja_to_hangul`) 규칙

UniDic(fugashi + unidic-lite)의 발음으로 한자를 읽은 뒤, 한국인이 일본어를 읽는 방식에 가깝게 바꿉니다. 공식 외래어 표기법이 아니라 발음 근사입니다.

| 항목 | 기본값 | `translit_style`로 바꿀 수 있는 값 |
|---|---|---|
| `tsu` (つ) | `ㅊ` → 츠 | `ㅅ` → 쓰, `ㅉ` → 쯔 |
| `initial` (어두 무성음) | `aspirated` → 카·타 | `plain` → 가·다 (표기법식) |
| `long_vowel` (장음) | `drop` → 토 | `keep` → 토오 |
| `n_assim` (ㅁ·ㅂ·ㅍ 앞 ん) | `false` → ㄴ | `true` → ㅁ |

항상 적용되는 규칙: っ → 받침 ㅅ, ん → 받침 ㄴ, ス·ズ → 스·즈, ファ행 → ㅍ, 어절 사이 띄어쓰기. 라틴 문자 구간은 그대로 둡니다. 가사처럼 특수한 읽기(当て字·루비)는 사전 읽기와 다를 수 있습니다.

## 설치 (Windows, Python 3.14)

```bash
py -3.14 -m venv venv
venv\Scripts\python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cu126
venv\Scripts\python -m pip install -r requirements.txt
venv\Scripts\python -m pip install --no-deps kokoro
venv\Scripts\python -m pip install --no-deps --ignore-requires-python misaki==0.9.4
venv\Scripts\python -m pip install --no-deps -e .
```

모델 가중치(Whisper large-v3 약 3GB, Kokoro, Supertonic)는 처음 쓸 때 Hugging Face 캐시(`~/.cache/huggingface`)로 받습니다. GPU 메모리는 Whisper와 Kokoro를 함께 올려도 약 4.5GB(RTX 3070 8GB에서 확인)입니다.

## Python 3.14에서 우회한 것

- **kokoro**는 `numpy==1.26.4`를 고정하는데 3.14용 빌드가 없습니다. 그래서 `--no-deps`로 설치합니다(최신 numpy로 동작 확인).
- **misaki 0.9.4**는 3.13 미만으로 표시돼 있지만 순수 파이썬이라 그대로 씁니다.
  - kokoro 0.7 파이프라인과 반환 형식이 달라서, `kokoro_backend`가 g2p와 모델을 직접 호출합니다.
- **mojimoji**(Cython, 3.14 빌드 없음)는 `jaconv` 기반 대체 모듈(`_mojimoji_shim.py`)로 바꿨습니다.
- **spacy**는 3.14 빌드가 없어 영어·중국어 Kokoro 목소리는 쓸 수 없습니다.
  - 일본어는 spacy 없이 동작하도록 빈 대체 모듈을 끼웁니다.
  - 영어가 필요하면 Supertonic(`st_*`, `lang="en"`)을 쓰면 됩니다.
- **torch와 winrt** 순서: winrt를 먼저 불러오면 torch DLL 초기화가 실패(WinError 1114)해서, 패키지가 torch를 먼저 불러옵니다.

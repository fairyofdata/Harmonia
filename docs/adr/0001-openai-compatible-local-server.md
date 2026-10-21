# ADR-0001: OpenAI 호환 HTTP 서버를 127.0.0.1에만 연다

- 상태: 채택
- 결정일: 2026-10-21
- 기록: 2026-10-22 소급 작성

## 맥락
여러 프로젝트(Songfinder 평가 등)가 같은 TTS·STT를 쓰려고 한다. 프로젝트마다 무거운 의존성(torch CUDA, 모델 수 GB)을 설치하고 싶지 않다. 이미 OpenAI SDK를 쓰는 코드도 많다.

## 결정
- 이 저장소의 venv 하나에 모든 엔진을 두고, FastAPI 서버로 `POST /v1/audio/speech`와 `POST /v1/audio/transcriptions`를 OpenAI와 같은 형식으로 연다.
- 클라이언트는 `OpenAI(base_url="http://127.0.0.1:8880/v1", api_key="local")`처럼 주소만 바꾸면 된다.
- OpenAI에 없는 기능은 필드와 엔드포인트를 추가해 확장한다: `translit`, `translit_style`, `lang`, `pitch`, `POST /v1/batch/transcriptions`, `GET /v1/voices`.
- 외부 접근을 막으려고 127.0.0.1에만 바인딩한다. 출력은 wav/pcm만 지원한다(ffmpeg 없음).

## 결과
- 다른 프로젝트는 HTTP만 있으면 쓸 수 있다. Python API(`import localtts`)와 CLI도 같은 기능을 제공한다.
- 서버를 띄워 두면 GPU 메모리를 약 4.5GB 차지한다.

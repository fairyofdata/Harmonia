# ADR-0006: MCP 서버는 HTTP 서버에 붙는 얇은 프록시로 둔다

- 상태: 채택
- 결정일: 2026-11-23

## 맥락
- 다른 프로젝트의 에이전트가 이 PC의 TTS·STT를 쓰려면 MCP가 가장 직접적인 통로다.
- MCP stdio 서버는 클라이언트(프로젝트)마다 프로세스가 하나씩 뜬다. 그 프로세스가 모델을 직접 들면 Whisper와 Kokoro가 프로젝트 수만큼 GPU에 올라가고, 8GB 카드에서는 두 프로젝트만 돼도 넘친다.
- `localtts` 패키지는 `__init__`에서 torch를 부른다(winrt보다 먼저 불러야 DLL 초기화가 깨지지 않는다, [ADR-0003](0003-python-314-workarounds.md)). 그래서 패키지 안에 두면 MCP 프로세스마다 torch가 같이 올라간다.
- 독음 변환(`ja_to_hangul`)은 HTTP로 쓸 방법이 없었다. CLI와 파이썬 import로만 가능했다.

## 결정
- MCP 서버는 도구 호출을 `127.0.0.1:8880`의 HTTP 서버([ADR-0001](0001-openai-compatible-local-server.md))로 전달만 한다. 모델을 직접 다루지 않는다.
- 서버가 떠 있지 않으면 첫 호출에서 `localtts serve`를 분리된(detached) 프로세스로 띄우고 `/health`를 기다린다. 사용자가 미리 서버를 띄워 둘 필요가 없다.
- 모듈은 패키지 밖 `localtts_mcp.py`에 둔다. 의존은 `mcp`와 표준 라이브러리뿐이고, torch·numpy를 부르지 않는다.
- 합성 결과는 wav 파일로 쓰고 경로만 돌려준다. 오디오를 base64로 돌려주면 부른 쪽 컨텍스트를 수백 KB씩 잡아먹는다.
- 오류는 `ToolError`로 올린다. 다른 예외는 SDK가 `Error executing tool <name>`으로 덮어 버려서 부른 쪽이 이유를 알 수 없다.
- 독음 변환용 `POST /v1/translit`을 서버에 추가한다. MCP가 이 한 가지 때문에 패키지를 import하지 않아도 된다.

## 결과
- 동시에 여러 프로젝트가 불러도 모델은 한 벌만 올라간다. MCP 프로세스는 0.7초에 뜨고 모델 메모리를 쓰지 않는다.
- 대신 HTTP 서버가 단일 실패 지점이 된다. 죽으면 다음 호출에서 다시 띄운다(매 호출 `/health` 확인).
- 합성한 음성을 들으려면 부른 쪽이 돌려받은 경로의 파일을 열어야 한다.
- **자동으로 띄운 서버는 MCP 클라이언트와 함께 내려간다.** MCP 클라이언트(SDK 포함)가 서버 프로세스를 KILL_ON_JOB_CLOSE 잡 오브젝트에 넣기 때문이다. `CREATE_BREAKAWAY_FROM_JOB`은 가장 안쪽 잡에서만 빠져나오므로 소용이 없었다(실제로 확인했다).
  - 재시작 비용은 가중치 캐시 덕에 몇 초다. 항상 띄워 두려면 `python -m localtts serve`를 직접 실행한다. 직접 띄운 서버는 MCP가 끄지 않는다.
- 로그는 `LOCALTTS_OUT_DIR/server.log`.

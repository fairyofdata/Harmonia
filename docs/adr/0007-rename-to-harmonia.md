# ADR-0007: 이름을 LocalTTS에서 Harmonia로 바꾼다

- 상태: 채택
- 결정일: 2026-11-24

## 맥락
- 처음 이름 LocalTTS는 TTS만 하던 때의 이름이다. 지금은 Whisper STT와 독음 변환도 함께 제공해서 이름이 범위를 가리키지 못한다.
- 같은 사람이 만든 다른 도구(Concordia 등)와 이름 짓는 방식을 맞춘다.

## 결정
- 레포·패키지·모듈·명령·MCP 서버 이름을 `harmonia`로 바꾼다: 패키지 `harmonia/`, MCP 모듈 `harmonia_mcp.py`, 명령 `harmonia`·`harmonia-mcp`, MCP 서버 이름 `harmonia`.
- 환경 변수도 `LOCALTTS_*` → `HARMONIA_*`로 바꾼다. 옛 이름은 받지 않는다(쓰는 사람이 만든 사람뿐이다).
- 기본 출력 폴더는 `<temp>/harmonia`.
- HTTP 포트 8880과 API는 그대로다. HTTP로만 부르는 쪽은 고칠 것이 없다.
- 0001~0006의 본문은 결정 당시 기록이라 옛 이름 그대로 둔다.

## 결과
- MCP 도구 이름이 `mcp__localtts__*`에서 `mcp__harmonia__*`로 바뀐다. MCP 설정을 바꾼 뒤 클라이언트를 다시 시작해야 한다.
- 폴더를 옮기면 편집 설치(`pip install -e .`)를 다시 해야 한다. 편집 설치는 절대 경로를 적어 두기 때문이다.
- GitHub는 옛 레포 주소를 새 주소로 넘겨 준다.

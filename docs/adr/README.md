# 아키텍처 결정 기록 (ADR)

LocalTTS를 만들며 내린 결정입니다. 0001~0005는 2026-10-21~22의 결정을 소급 작성한 것입니다.

| 번호 | 결정 | 날짜 |
|---|---|---|
| [0001](0001-openai-compatible-local-server.md) | OpenAI 호환 HTTP 서버를 127.0.0.1에만 연다 | 2026-10-21 |
| [0002](0002-tts-backends.md) | TTS 엔진은 Kokoro, Supertonic-3, Windows OneCore 음성을 함께 둔다 | 2026-10-21 |
| [0003](0003-python-314-workarounds.md) | Python 3.14에서 상위 패키지 호환 문제를 로컬 우회로 해결한다 | 2026-10-21 |
| [0004](0004-supertonic-gpu-and-text-limits.md) | Supertonic은 GPU로 돌리고, 어휘 밖 글자와 긴 글을 백엔드에서 처리한다 | 2026-10-22 |
| [0005](0005-batched-whisper-with-language.md) | Whisper는 직접 일괄 호출하고 감지 언어를 함께 반환한다 | 2026-10-21 |
| [0006](0006-mcp-server-as-a-proxy.md) | MCP 서버는 HTTP 서버에 붙는 얇은 프록시로 둔다 | 2026-11-23 |

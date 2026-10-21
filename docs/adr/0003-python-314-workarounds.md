# ADR-0003: Python 3.14에서 상위 패키지 호환 문제를 로컬 우회로 해결한다

- 상태: 채택
- 결정일: 2026-10-21
- 기록: 2026-10-22 소급 작성

## 맥락
이 PC의 Python은 3.14뿐이다. 여러 패키지에 3.14용 빌드가 없거나, 버전 고정이 맞지 않았다.

## 결정
| 문제 | 우회 |
|---|---|
| kokoro의 `numpy==1.26.4` 고정 | `--no-deps`로 설치하고 최신 numpy 사용 |
| misaki 0.9.4가 3.13 미만으로 표시 | `--ignore-requires-python`. 순수 파이썬이라 동작함 |
| misaki 0.9와 kokoro 0.7의 g2p 반환 형식 불일치 (음성이 0.35초로 잘림) | `kokoro_backend`가 g2p와 모델을 직접 호출 |
| mojimoji (Cython, 빌드 없음) | jaconv 기반 대체 모듈 `_mojimoji_shim.py` |
| spacy (빌드 없음) | spacy가 없을 때만 빈 대체 모듈을 끼움. 일본어는 동작하고, 영어 Kokoro는 명확한 오류를 냄 |
| winrt를 먼저 불러오면 torch DLL 초기화 실패 (WinError 1114) | 패키지 첫머리에서 torch를 먼저 불러옴 |
| transformers 파이프라인의 일괄 처리 + 언어 반환 버그 | Whisper `generate`를 직접 호출하고, 감지 언어는 `detect_language`로 읽음 (ADR-0005) |

## 결과
- 상위 패키지가 3.14를 정식 지원하면 대체 모듈과 직접 호출을 걷어 낼 수 있다.
- 업그레이드 때는 Kokoro 일본어 길이(문장당 수 초)와 Whisper 감지 언어를 먼저 확인한다.

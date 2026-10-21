# ADR-0002: TTS 엔진은 Kokoro, Supertonic-3, Windows OneCore 음성을 함께 둔다

- 상태: 채택
- 결정일: 2026-10-21
- 기록: 2026-10-22 소급 작성

## 맥락
- 일본어와 한국어 목소리가 여러 개 필요했다(한 목소리의 버릇이 결과를 좌우하지 않도록).
- 상업적 사용이 막힌 라이선스(XTTS-v2의 CPML 등)는 피하고 싶었다.
- Python 3.14에서 돌아야 했다.

## 결정
| 엔진 | 목소리 id | 역할 | 라이선스 |
|---|---|---|---|
| Kokoro-82M | `jf_*`, `jm_*` | 일본어 신경망 목소리 5개 | Apache-2.0 |
| Supertonic-3 | `st_M1`~`st_F5` | 31개 언어(한국어·일본어·영어 포함) × 10목소리 | 가중치 OpenRAIL-M |
| Windows OneCore | `win_*` | 설치된 언어 팩의 기본 음성, 추가 다운로드 없음 | Windows |

일본어 → 한글 독음 변환(`ja_to_hangul`)은 TTS와 분리된 모듈로 둔다. fugashi와 unidic-lite만 있으면 다른 venv에서도 import된다.

## 결과
- 한국어 11개, 일본어 18개, 영어(Supertonic) 목소리를 쓸 수 있다.
- Kokoro의 영어·중국어 목소리는 spacy가 없어 쓸 수 없다(ADR-0003).
- Windows 음성 목록은 PC에 설치된 언어 팩에 따라 다르다. 이 PC에서는 Sayaka가 레지스트리에는 있지만 API에서 보이지 않았다.

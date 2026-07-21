# Polly 한국어 음성 후보 샘플 (32-16 Task 4 — belle 청취 확정 게이트)

D-18 B안 부속 결정(32-GATE-DECISIONS §샘플 게이트): 최종 음성(voice/engine)은
구현 후 belle 청취로 확정. 세 파일 모두 **같은 코칭 문장** (32-08 샘플과 동일 —
문구집 `__common__.leg_extension` cueLine+whyLine, 수치 0 / D-09 준수):

```
발끝으로 천장을 길게 밀어낸다는 느낌으로 다리를 쭉 뻗어보세요.
다리 라인이 끝까지 뻗지 않으면 심사에서 신전 완성도로 감점되는 부분이에요.
```

## 후보 (ap-northeast-2 실계정 조회 — ko-KR 가용 전부)

| 파일 | Voice | Engine | 비고 |
|------|-------|--------|------|
| `seoyeon_neural.mp3` | Seoyeon | neural | 32-08 B안 샘플과 동일 음성 (belle 1차 청취분) — **현재 잠정 기본값** |
| `jihye_neural.mp3` | Jihye | neural | 다른 톤 후보 (미청취) |
| `seoyeon_generative.mp3` | Seoyeon | generative | 억양 더 자연 — 비용/합성 지연 상향 (ko-KR generative 는 Seoyeon 만) |

## 재생법

- Mac: Finder 에서 더블클릭 (QuickTime).
- iPhone(실기기 스피커 비교): AirDrop/카톡 전송 후 재생.

## 확정 후 반영 (재배포 불요 설계)

pipeline 의 음성은 env 우선(`POLLY_VOICE_ID` / `POLLY_ENGINE`, 기본 Seoyeon neural)
— Seoyeon neural 외 선택 시 **Pod env 2개 + Lambda env 설정만으로 스왑**되며,
코드 기본값 고정 + GATE-DECISIONS 1줄 기록은 continuation 이 수행한다.

## 재생성 커맨드

```bash
SENTENCE="발끝으로 천장을 길게 밀어낸다는 느낌으로 다리를 쭉 뻗어보세요. 다리 라인이 끝까지 뻗지 않으면 심사에서 신전 완성도로 감점되는 부분이에요."
aws polly synthesize-speech --engine neural --voice-id Seoyeon --language-code ko-KR \
  --output-format mp3 --text "$SENTENCE" --profile sunity-motion --region ap-northeast-2 seoyeon_neural.mp3
aws polly synthesize-speech --engine neural --voice-id Jihye --language-code ko-KR \
  --output-format mp3 --text "$SENTENCE" --profile sunity-motion --region ap-northeast-2 jihye_neural.mp3
aws polly synthesize-speech --engine generative --voice-id Seoyeon --language-code ko-KR \
  --output-format mp3 --text "$SENTENCE" --profile sunity-motion --region ap-northeast-2 seoyeon_generative.mp3
```

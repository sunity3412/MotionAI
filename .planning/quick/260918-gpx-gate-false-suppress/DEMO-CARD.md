# 학원 실증 점검 카드 — 2026-09-18

## 지금 상태 (기동 완료)

| | |
|---|---|
| Pod | `elevev58iv4mox` · L4 · **루마니아(RO)** · $0.49/hr |
| 서버 | `https://elevev58iv4mox-8000.proxy.runpod.net` |
| 서빙 코드 | `8c64b941` (health 의 commitSha 로 확인됨) |
| Lambda | RUNPOD_ANALYZE_URL 동기화 완료 |
| SSM | pod-expected = **up** |
| 앱 OTA | `0dddb65f` preview/1.2.4 (강사 교정 v2 포함) |
| 회전 | ROT180_INVERSION_ENABLED = **ON** |

## 실증 직전 30초 점검

```bash
curl -s https://elevev58iv4mox-8000.proxy.runpod.net/health | python3 -m json.tool
```

이 셋을 보세요:
- `"pipeline_loaded": true`
- `"poseEngine": "RTMWPoseEngine"`
- `"recognizer": "GeminiTechniqueRecognizer"`

**하나라도 빠지면 분석이 실패합니다** (폴백 없음).

## 앱에서 할 것

1. 앱 **완전 종료 후 재실행** (OTA 를 받아야 강사 교정 v2 가 보입니다)
2. 영상 업로드 → 분석
3. 결과 → 보완운동 탭 → "강사에게 확인할 점" 카드에 **입력 한 행**이 보이면 OTA 적용된 것

## 끝나면 반드시

**Pod 종료** — 안 끄면 시간당 $0.49 가 계속 나갑니다.

```bash
# Claude 에게 "Pod 종료해줘" 라고 하시면 됩니다. 수동이면 RunPod 콘솔에서 Terminate.
```
그리고 SSM `pod-expected` 를 `down` 으로.

## 알려진 제약 (실증 중 당황하지 않기)

- **Pod 이 EU, 버킷이 서울** — 영상이 크면 다운로드가 분석 시간의 상당 부분입니다.
  (오늘 실측: 88MB 가 25초 미만 — 종전 기록 752초보다 훨씬 빨랐습니다.)
- **Pod 이 없으면 분석은 그냥 실패합니다.** 폴백 경로가 없습니다.
- 확대 카드·음성은 분석 완료 **후 3~5분** 더 걸려 만들어집니다. 바로 안 보여도 정상입니다.

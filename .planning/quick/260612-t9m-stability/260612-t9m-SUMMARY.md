---
phase: quick-260612-t9m
plan: 01
subsystem: backend (analysis) + app (analysis result UI)
tags: [stability, scoring, ux-caption, tol-calibration]
requires: []
provides:
  - "_STABILITY_TOL_DEG = 25.0 (15° → 25° 완화)"
  - "결과 화면 점수 안내 캡션 (90+ 정상 인지 정합)"
affects:
  - backend/shared/python/sunity_shared/analysis/dimensions.py
  - app/src/app/analysis/result.tsx
tech-stack:
  added: []
  patterns:
    - "theme 토큰 (typography.caption + colors.textSecondary) 사용, 하드코딩 금지 정합"
key-files:
  created: []
  modified:
    - backend/shared/python/sunity_shared/analysis/dimensions.py
    - app/src/app/analysis/result.tsx
decisions:
  - "옵션 A 채택 — tol 25° 로 완화 (옵션 B noise-floor subtraction 보류). belle 결정."
  - "캡션 위치 = 점수 카드 안 LevelBenchmark 다음 (점수 영역에 시각적으로 묶임)."
  - "mode 분기 없음 (mode1/mode3 공통 노출) — 두 모드 모두 stability 차원 사용."
metrics:
  duration: "약 12분"
  completed: 2026-06-12
  tasks_executed: 2
  tasks_deferred: 1
---

# Quick 260612-t9m: stability 점수 보정 + 사용자 안내 Summary

같은 영상 self-test 시 stability 점수가 만점 안 나오던 문제를 `_STABILITY_TOL_DEG` 15° → 25° 완화로 해결하고, 결과 화면에 "90+ 정상" 한국어 안내 캡션을 추가했다.

## Completed Tasks

| Task | Name                                        | Commit  | Files                                                       |
| ---- | ------------------------------------------- | ------- | ----------------------------------------------------------- |
| 1    | dimensions.py `_STABILITY_TOL_DEG` 15→25°    | 25856bc | backend/shared/python/sunity_shared/analysis/dimensions.py  |
| 2    | result.tsx 점수 안내 캡션 추가               | 947570f | app/src/app/analysis/result.tsx                             |

## Task 1: dimensions.py diff

변경 전:
```python
_STABILITY_TOL_DEG = 15.0  # Path T1 (2026-06-05): inter-frame diff median 기준. 정은지 reference 5영상 wobble 측정 6~16° 박제 → 사용자 영상 정상 wobble 범위 박제 정신 정합 (RTMW noise + 자세 미세 변화 흡수). 진짜 떨림 (20°+) 만 FAIL.
```

변경 후:
```python
_STABILITY_TOL_DEG = 25.0  # Path T1 (2026-06-05): inter-frame diff median 기준.
# 2026-06-12 belle 결정 (옵션 A): tol 15° → 25° 완화. 정은지 reference 5영상 wobble 측정 6~16° 와
# tol 15° 가 거의 같아 reference 자체 z=0.4~1.0 → stability 68~94 (만점 X). tol 25° 면 reference
# wobble z<0.7 → 95+ 안정, 같은 영상 self-test 도 95+ 회복, "90+ 정상" 사용자 인지 임계 정합.
# RTMW noise + 자세 미세 변화 흡수 폭 확보, 진짜 떨림 (30°+) 만 stability < 70 으로 깎임.
```

- `_LINE_TOL_DEG = 20.0` 보존 확인 (scope 외)
- 주석에 (a) 측정 데이터 wobble 6~16°, (b) 보정 의도, (c) FAIL 임계 30°+, (d) 날짜·이유 모두 기록

## Task 2: result.tsx 변경

위치: `app/src/app/analysis/result.tsx:597-610` (점수 게이지 `<View style={styles.card}>` 안, `<LevelBenchmark />` 다음).

추가된 JSX:
```tsx
{/* 260612-t9m: 점수 안내 캡션 — stability tol 25° 보정과 함께 "90+ 정상" 사용자 인지 정합 */}
<Text style={styles.scoreCaption}>
  촬영 노이즈와 측정 허용 범위가 있어 100점은 잘 나오지 않아요. 90점 이상이면 정상 자세에 가깝습니다.
</Text>
```

추가된 스타일 (`styles.scoreCaption`):
```ts
scoreCaption: {
  ...typography.caption,
  color: colors.textSecondary,
  textAlign: 'center',
  marginTop: 12,
  lineHeight: 18,
  paddingHorizontal: 4,
},
```

- theme 토큰만 사용 (하드코딩 색·폰트 0)
- mode 분기 X → mode1/mode3 둘 다 노출
- `npm run typecheck` (`tsc --noEmit`) 0 errors
- 이모지 X, "박제" 단어 X, 라이트 톤 보존

### typecheck 확인 절차

worktree 에는 `node_modules` 가 없어서 메인 repo (`/Users/kimtaesung/Dev/SunityMotion/app/node_modules`) 를 임시 심볼릭 링크로 연결 후 typecheck 실행 → 0 errors 확인, 그 다음 심볼릭 링크 삭제 후 commit. 메인 repo 의 의존성과 worktree 소스가 호환되는 환경이므로 결과는 동일.

## Deferred to Orchestrator (Task 3)

Task 3 (검증 + 배포) 은 worktree 격리 환경 외부 자원 (AWS SAM, RunPod SSH, EAS CLI 인증) 이 필요하여 orchestrator (main session) 에 위임:

1. **backend self-test** — `python scripts/verify_self_comparison.py --reference scripts/reference-angles.json --out scripts/self-comparison-quick.json --quick` → 4 motion stability 90+ 확인
2. **SAM 재배포** — `sam build --use-container && sam deploy --no-confirm-changeset --no-fail-on-empty-changeset` (stack `sunity-motion-pilot`, ap-northeast-2)
3. **RunPod 재시작** — Pod ssh 접속 → `cd /workspace/SunityMotion && git pull && bash /root/launch-uvicorn.sh` → `GET /health` 200 확인
4. **EAS update** — `eas update --branch preview --message "stability tol 25° + 점수 안내 캡션"`

## Deviations from Plan

None - plan 의 Task 1/2 는 정의된 대로 실행. Task 3 는 plan 에 명시적으로 deferred 로 분류된 사항이라 deviation 아님.

## Self-Check: PASSED

- backend/shared/python/sunity_shared/analysis/dimensions.py — 변경 확인 (`_STABILITY_TOL_DEG = 25.0` line 159)
- app/src/app/analysis/result.tsx — 변경 확인 (캡션 line 607, 스타일 line 913)
- commit 25856bc — git log 확인
- commit 947570f — git log 확인
- typecheck 0 errors — 확인됨

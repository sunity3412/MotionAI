# quick-260831-gyk — 실데이터 사전 박제 검증 (파워스핀 correct/fault 페어)

수리 대상: `dimensions._select_window` — Gemini 국면 창(profile.hold_window)을
verbatim 쓰지 않고 창 내부에서 분산-최소 안정 부창을 재선택 (커밋 51ccbcef).

규율: 아래 예측 블록은 **스크립트 실행 전에** 작성·박제한다 (memory: 사전 박제 장부,
belle-eye-is-the-answer-key). 측정 블록은 스크립트 stdout 원문을 그대로 붙이고,
예측 블록은 이후 수정하지 않는다. FAIL 시 curve-fit 금지 — 원문 그대로 박제.

---

## 예측 블록 (스크립트 실행 전 작성 — 2026-08-31)

### correct (users/QAN8VPwk4Oh13FMhTenphxYPdxH2/analyses/0bc7aedf1032474280d544a3a2ad418e)

1. **기질 동일성 (수리 전 의미 재현)**: 힌트 창 (54, 90) verbatim 평균 right_knee
   ≈ 135.81° — doc 의 leg_extension 감점 record measuredValue 와 일치
   (오케스트레이터 진단 재확인 — 주장 승계 금지 규율).
2. **부창 이동**: 힌트 창 (54, 90) 내부 안정 부창이 홀드 구간(약 68 이후)으로
   이동한다 (프레임 54~67 = 스핀 진입 전환부, 68~ = 진짜 홀드 177~178° 유지).
3. **위양성 소멸 (hard assert)**:
   - 부창 right_knee 평균 >= 170
   - leg_extension deficit (max 무릎 부족분) < tol(20) → 감점 0
   - line micro-bent (부창 평균 < 160) 미발화 → line_score != 0

### fault (users/8fPsUnXWNiOW9Y6cawCMcHGVb6z1/analyses/0e53101beff4433e90159334554ba893)

4. **방향 보존 (hard assert)**: fault 의 홀드 자체가 불안정 (무릎 148~169 요동)
   → 수리 후에도 fault 의 홀드 무릎(right_knee) 평균 < correct 의 홀드 무릎 평균.
   fault 에는 split_angle·angle_vs_reference 등 다른 감점이 별도로 존재하므로
   이 수리로 fault 가 무결점이 되지 않는다.

### 힌트 창 도출 규칙 (양쪽 동일)

doc 에 저장된 gemini 캐시 필드(geminiB/geminiC 등)의 hold moments 에서
`_hold_window_from_moments` 로 도출을 시도한다. 저장 형태에서 도출 불가하면:
- correct: 역산 확정치 (54, 90) 을 사용하고 그 사실을 측정 블록에 명기.
- fault: 동일 규칙 — 도출 불가 시 자동 hold_window 경로(힌트 없음)로 측정하고
  그 사실을 명기.

---

## 측정 블록 (스크립트 stdout 원문 — 예측 블록 수정 금지)

실행: 2026-08-31, `backend/.venv/bin/python .planning/quick/260831-gyk-hold-gemini/verify_hold_subwindow.py`

```
== correct (QAN8VPwk.../0bc7aedf...) ==
  T=106 frames, J=8
  힌트 창 소스: 역산 확정치 (54,90) — doc 에서 도출 불가 → (54, 90)
  [수리 전 의미] 힌트 창 (54,90) verbatim right_knee 평균 = 135.81 deg
  doc leg_extension record measuredValue = 135.81 deg
  [수리 후] 힌트-창-내부 부창 = (80,89)
    right_knee 평균 = 173.40 deg / left_knee 평균 = 171.93 deg
    leg_extension deficit (무릎 max) = 8.07 deg (tol 20)
    line_score = 93 / micro-bent(<160) 발화 = False

== fault (8fPsUnXW.../0e53101b...) ==
  T=83 frames, J=8
  힌트 창 소스: (도출 불가) → None
  [수리 후] 자동 hold_window (힌트 없음) = (63,83)
    right_knee 평균 = 158.35 deg / left_knee 평균 = 140.95 deg
    leg_extension deficit (무릎 max) = 39.05 deg (tol 20)
    line_score = 0 / micro-bent(<160) 발화 = True

== 예측 부등식 판정 (VERIFY.md 예측 블록 순서) ==
  [1] 기질 동일성: verbatim 135.81 vs record 135.81 (|diff|=0.0036)
      PASS
  [2] 부창 이동: 힌트 (54, 90) → 부창 (80, 89) (관측)
  [3] correct: rk_mean 173.40 >= 170 / deficit 8.07 < 20 / micro-bent False
      PASS
  [4] 방향 보존: fault rk_mean 158.35 < correct rk_mean 173.40
      PASS

ALL PREDICTIONS PASS
```

### 판정 요지

- **예측 4건 전부 PASS** — 예측 블록 수정 0.
- 기질 동일성: verbatim 창 평균 135.81 = 감점 record measuredValue 135.81 (|diff| 0.0036)
  — 스크립트가 프로덕션 감점과 같은 기질을 보고 있음이 증명됨.
- 부창 이동: (54,90) → (80,89). 예측 "약 68 이후" 와 정합 (부창 폭 = 기존 규칙
  w = max(2, min(36, 36//4)) = 9, 새 튜닝 상수 0).
- correct 위양성 소멸: right_knee 173.40 >= 170, deficit 8.07 < 20 (감점 0),
  micro-bent 미발화 (line_score 93, 종전 0점 소멸).
- fault 방향 보존: 158.35 < 173.40. fault 는 힌트 창 도출 불가(도출 규칙 명기대로
  자동 hold_window 경로) — 자동 창에서도 무릎 158.35/140.95 로 deficit 39.05,
  micro-bent 발화 유지. fault 가 무결점이 되지 않음.
- 관측 노트: 양쪽 doc 모두 gemini 캐시 필드에 hold moments 미저장(도출 불가) —
  correct 는 예측 블록 규칙대로 역산 확정치 (54,90) 사용, 그 verbatim 평균이
  record measuredValue 와 일치해 (54,90) 이 실제 감점 창이었음이 교차 확인됨.


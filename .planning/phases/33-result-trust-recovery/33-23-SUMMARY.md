---
phase: 33-result-trust-recovery
plan: 23
type: execute
status: complete
verdict: PASS
tags: [wave-r, scoring-reverify, two-track, structural-invariants, shadow-candidate, no-flip]
key_files:
  created:
    - .planning/phases/33-result-trust-recovery/33-SCORING-REVERIFY.md
  evidence_pod: "b9l5gt1vpc4ho1:/workspace/eval_out_33_23/phase25/{phase25_breakdowns,phase25_sweep_report}.json"
---

# Plan 33-23: Wave R 2-트랙 채점 재검증 Summary

**2-트랙 채점 엔진(33-22)을 새 candidate 기질(`phase33-cm3-run1`) shadow 소비로 6 fixture serial 재분석 → 구조 불변식 INV-1/2/4/5/6 동시 성립 확인. Verdict PASS. flip(33-07) belle 보류 유지.**

- **Tasks:** 2 (Task 1 belle GPU greenlight = 충족 / Task 2 serial sweep + 불변식 판정 = 완료)
- **모델:** belle 요청 — fable 원했으나 크레딧 부재 → 현 모델로 fable급 엄밀도 적용(회귀 executor 주장 불신 후 baseline 직접 대조 등).

## 검증 결과 (독립 재계산 — 관측표 불신, raw JSON 직접 산술)

- **INV-6 재구성:** 채점 10/10 정확 (`final = max(25, round(100 − min(40,|exec|) − |crit|))`).
- **INV-1:** correct 5/5 = 100. **INV-2:** fault 80/86/60/60/79 — 60 미만 0 (엘보우 −111.4→바닥60 = 옛 0붕괴 복구).
- **INV-4:** 캡 아래(80/86/79) 변별 온전; 캡 도달 elbow-twist(−111)·pdshape(−57) 둘 다 60 평탄 = 의도된 트레이드오프(finding, curve-fit 안 함).
- **INV-3/7/8:** 33-22 합성 유닛테스트 증명(치명 DORMANT). 실 elbow-twist 가 앵커(−111.4→60) 재현.

## belle 요청 3 concern 해결

1. **실 fixture 검증(INV-1/2/4/5):** ✅ 위 표 — 5개 fixture 동시 성립.
2. **남은 실패 pre-existing 확인:** ✅ HEAD(ac59904) vs baseline(bdfe4a0) 동일 커맨드 대조 = **61==61 동일, 33-22 신규 실패 0**, +16 신규 통과. 채점 테스트 241 passed/0 failed. executor "45" 불일치는 무시(내 로컬 ground truth 우선).
3. **치명 트랙 DORMANT:** ✅ 발화 조건(`split_fail_threshold_deg` 보유 criterion 필요) + 켤 때 kip-up FP 재유발 위험 → 반드시 재검증 게이트 재통과(별도 gated plan) 명시.

## 정직한 맥락 (엔진과 별건)

fault 점수 상승(power-spin 57→80, kip-up 47→79)은 **2-트랙 엔진 아님**(캡 아래 = pre-33-22 동일 계산) — **새 candidate 기질**(9fps+PR인버전) 효과. "잘못된 시연=80점" 신뢰성은 기질/민감도 별건, belle 판단 필요(curve-fit 안 함).

## climb 예외

climb = `not_pole_motion` 게이트(angle 0<25) 반려, 채점 미도달 — 33-20 예고("climb mode1 substrate 결핍")와 일치. 엔진 실패 아님.

## Self-Check: PASSED

R5 일반화 게이트 PASS. 상세 = 33-SCORING-REVERIFY.md.

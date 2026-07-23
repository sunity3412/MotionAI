---
phase: 33-result-trust-recovery
plan: 06
subsystem: ml
tags: [substrate-verification, shadow-reference, data-gate, margin, inversion, m8-axis, mode1-scoring, elbow-twist, rollback]

requires:
  - phase: 33-03
    provides: candidate versions/phase33-cm3-run1 (9fps + PR 재추출)
  - phase: 33-04
    provides: candidate downstream 백필 11/11
  - phase: 33-05
    provides: M3 paired-range 정렬 substrate
  - phase: 33-17
    provides: SUNITY_SHADOW_REFERENCE_VERSION overlay (flip 없는 candidate 소비)
  - phase: 33-18
    provides: gate_check.py JSON 데이터 게이트 + /health canary
  - phase: 33-20
    provides: 33-COVERAGE-MATRIX.md (canonical 11-motion coverage)
provides:
  - "candidate phase33-cm3-run1 의 SEED 8-item 재검증 결과 (7/8 PASS, gate2 분리 미달)"
  - "여유(margin) 6/6 양수 + pdshape 음→양 전환 실측 (RTMW-deterministic)"
  - "elbow-twist 여유 +3.10 (≥+2.0 → 33-21 HALT no-op)"
  - "M8 원본-5 단일 (x,y,0) 수렴 서버측 검증 + 크롭 육안 (디바이스 육안=33-16)"
  - "롤백 트리거 4종 clear"
affects: [33-07, 33-21, 33-16]

tech-stack:
  added: []
  patterns:
    - "shadow-candidate 소비: SUNITY_SHADOW_REFERENCE_VERSION → get_reference_motion overlay, top-level write 0, anglesHash tee"
    - "여유(margin, 결정론) 를 분리(separation, Gemini 변동) 위에 둔 판정 — 디버그 doc R-6 준수"
    - "M3 발동 관측: motion_dtw ref_start/ref_end 트림 tee; M8 검증: 서버 substrate probe + 크롭 육안"

key-files:
  created:
    - .planning/phases/33-result-trust-recovery/33-S4-VERIFY-EVIDENCE.md
    - .planning/phases/33-result-trust-recovery/33-S4-VERIFY-EVIDENCE.json
    - .planning/phases/33-result-trust-recovery/33-S4-M8-crops/ (4 crop PNG, 육안 증거)
  modified: []

key-decisions:
  - "verify_self_comparison.py(NLF 의존) 대신 프로덕션 _process(RTMW) 로 self-comparison 충실 대체 (Rule 3)"
  - "M8 디바이스 육안은 canonical matrix 대로 33-16 에 귀속 (앱이 flip 전 candidate 오버레이 로드 불가) — 서버 substrate + 크롭만 33-06 에서"
  - "gate2 power-spin 분리 35<45 를 goalpost 이동 없이 FAIL 로 정직 기록 (codex concern 12); belle 판정 대상으로 라우팅"

requirements-completed: [D-18, D-19, D-23, D-25, D-27, D-28, D-30, D-31, D-32]

metrics:
  duration: ~130min
  tasks: 3
  completed: 2026-07-24
---

# Phase 33 Plan 06: S4 shadow-candidate 재검증 Summary

**candidate phase33-cm3-run1 을 33-17 shadow resolver 로 flip 없이 소비해 SEED 8-item 게이트를 JSON
데이터 게이트로 판정 — 결정론 지표 전항 통과(여유 6/6 양수·pdshape −1.2→+3.29 전환·elbow-twist
+3.10 HALT 없음·M8 (x,y,0) 수렴·2-run 0.0°·self-comparison 5/5·safety 0·refit 0·롤백 4종 clear)하되,
유일 미달 gate2 power-spin 분리 35<45(Gemini 변동 내포 score 지표)로 8-item 전항 gate_check = exit 1.**

## Performance
- **Duration:** ~130 min (sweep 20 멤버 SERIAL, 멤버당 ~90–160s + Gemini)
- **Completed:** 2026-07-24
- **Tasks:** 3 (Task 1 canary 재확인, Task 2 shadow sweep+margin, Task 3 gate+M8+rollback+route)

## Accomplishments
- **shadow 소비 증명(concern 3):** `SUNITY_SHADOW_REFERENCE_VERSION=phase33-cm3-run1` → 멤버별 소비된
  candidate anglesHash 기록(power-spin `4267fbfa` 등 5/5). production top-level `activeVersion=phase4_v1`
  무변형, `reference/_release` ABSENT 유지.
- **여유 6/6 양수 + pdshape 음→양(−1.2→+3.29):** C+M3 최소 성립 조건 충족. elbow-twist +0.2→+3.10.
- **JSON 데이터 게이트(concern 8):** `gate_check.py` — 8-item 전항 = exit 1(gate2 정직 노출), 해시11+
  롤백+상수 = exit 0. grep-for-PASS 아님.
- **M8:** 서버 substrate probe(원본-5 단일 `(x,y,0)`·finite) + fault-zoom 크롭 4/4 육안(candidate joints3d
  로 서버 렌더, garbled 0). 디바이스 육안은 canonical matrix 대로 33-16 귀속.
- **결정론:** pdshape 2-run edit 0.0°, combo 2-run drift 0.0 (P99 1.0 하회). self-comparison 5/5=100.
- **safety/refit:** 신규 FP/FN 0(candidate 0==baseline 0), live 상수==pinned(scoring-constants-match).
- **elbow-twist route:** +3.10 ≥ +2.0 → 33-21 no-op(HALT 없음, belle 질문 불요).

## Task Commits
- 코드 변경 0 (채점/스크립트 무접촉) — 산출물은 evidence 문서. per-task 커밋 없이 최종 docs 커밋 1건.

## D-19 증거 (무엇을 열어서 확인했는가)
- 여유 실측 표(candidate vs 예선), power-spin fault measuredDeviations(hip 18.06/15.80 tol 아래 강하).
- M8 크롭 4장 실제 다운로드+육안(`33-S4-M8-crops/`): 빨강 원이 joints3d 구동 영역 정위치.
- gate_check 3회 실행 종료 코드(1 / 0 / 0) 원문.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] verify_self_comparison.py NLF 의존 → _process(RTMW) 대체**
- **Found during:** Task 2 (self-comparison 준비)
- **Issue:** `verify_self_comparison.py` 는 `NlfPoseEstimator`(NLF TorchScript, `torch.jit.load`) 를 학생
  추출에 사용 — 프로젝트가 RTMW 로 pivot 했고 Pod 에 NLF 모델 부재라 실행 불가.
- **Fix:** 동일 의도(reference 영상을 학생으로 재투입 → ~100 기대)를 프로덕션 `_process`(RTMW, shadow
  candidate 소비)로 충실 재현. 5/5 만점 + maxDev≈0.003° 로 self-consistency 입증.
- **Verification:** 33-S4-VERIFY-EVIDENCE.md self-comparison 표.

**2. [Rule 3 - 범위 라우팅] M8 디바이스 Simulator 육안 → 33-16 (canonical matrix)**
- **Found during:** Task 3
- **Issue:** 앱 오버레이는 reference 골격을 top-level `reference/{id}` 에서만 읽는다(`useReferenceMotion`
  →`refDoc.joints3d`). candidate 는 `versions/` 에만 있고 flip(33-07) 은 이 플랜 범위 밖 → 앱이 flip 전
  candidate 오버레이를 로드 불가(구조적).
- **Fix:** 33-COVERAGE-MATRIX(canonical) 가 원본-5 M8 디바이스 육안을 **33-16 phase-gate device UAT**
  에 귀속. 33-06 은 flip-전 검증 가능분(서버 substrate probe + 크롭 육안)만 수행. silent skip 아님 —
  matrix 근거로 명시 라우팅.

**Total deviations:** 2 (both Rule 3). 채점 코어·임계 무접촉, scope creep 0.

## Known caveats / 판정 대상
- **gate2 power-spin 분리 35 < 예선 floor 45** — goalpost 이동 없이 FAIL 기록(codex concern 12).
  기전 = 밀도 아티팩트 감점 제거(정확도 개선)의 부수효과, fault 는 leg_extension(absolute)로 여전히
  포착. 분리 floor 자체가 소스별 불안정(kip-up 20↔53). **belle/오케스트레이터 판정 대상** — 33-07 보류.
  (33-21 elbow-twist HALT 아님, 롤백 트리거 아님.)

## Next Phase Readiness
- **33-07 flip:** gate2 분리 판정 후 진행 가능(결정론 substrate 는 전부 clear).
- **33-21:** elbow-twist 여유 +3.10 → no-op.
- **33-16:** M8 디바이스 육안(원본-5 오버레이) 소관 — flip 후 실기기 확인.

## Self-Check: PASSED
- 산출물 7/7 present: 33-S4-VERIFY-EVIDENCE.md/.json, 33-06-SUMMARY.md, M8 크롭 4 PNG.
- gate_check 재현: 8-item exit 1(gate2) / hashes11+rollback+constants exit 0 / 7-gate exit 0.
- Firestore ground truth: activeVersion=phase4_v1 무변형(shadow read-only), candidate anglesHash 5/5 기록.
- 코드/임계 무접촉: sunity_shared 채점 파일 diff 0.

---
*Phase: 33-result-trust-recovery*
*Completed: 2026-07-24*

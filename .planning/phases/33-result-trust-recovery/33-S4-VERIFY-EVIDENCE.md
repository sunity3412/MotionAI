---
plan: 33-06
title: S4 shadow-candidate 재검증 증거 — C+M3 substrate 8-item SEED 게이트
status: complete
pod: k508k3lut0o3f1 (dedicated eval Pod, 트래픽 격리)
commit: eb08e87302839e3f1db48511993d50b7f75d2240
candidate: phase33-cm3-run1
updated: 2026-07-24
---

# 33-06 S4 재검증 증거 (SEED Task 4 — codex 3/8/12/13/14 반영)

candidate `phase33-cm3-run1` 을 33-17 shadow resolver 로 **flip 없이 소비**(production top-level
`activeVersion=phase4_v1` 무변형, `reference/_release` ABSENT 유지)하고, 6 fixture SERIAL 재스윕 +
fixture-less self-comparison 을 채점해 SEED 8-item 게이트를 **JSON 데이터 게이트**(`gate_check.py`)로
판정했다. 기계 입력 = `33-S4-VERIFY-EVIDENCE.json`, 본 문서는 산문.

**결론 요약:** 결정론(RTMW-deterministic) 지표 전항 통과 — 여유(margin) 6/6 양수(pdshape **−1.2→+3.29**
음→양 전환), elbow-twist **+0.2→+3.10 (≥+2.0 → HALT 없음)**, M8 서버측 원본-5 단일 `(x,y,0)` 수렴,
pdshape 2-run edit **0.0°**, combo 2-run drift **0.0**, self-comparison 5/5=100, safety 신규 FP/FN **0**,
임계 refit **0**. **롤백 트리거 4종 전부 clear.** 유일 미달 = **gate2 power-spin separation 35 < 예선 floor 45**
(score 기반·Gemini vision-변동 내포 지표). `gate_check --require-all-pass gate1..gate8` = **exit 1**(gate2),
`--require-hashes 11 --no-rollback-trigger --scoring-constants-match` = **exit 0**.

---

## Task 1 — warm-Pod canary + 트래픽 격리 (재확인, D-30 / D-32ⓐ)

오케스트레이터가 belle greenlight 확보 + Pod 재시작(M3 커밋). 본 세션 sweep 직전 `/health` 재확인:

```json
{
  "status": "ok", "auth_configured": true, "pipeline_loaded": true,
  "commitSha": "eb08e87302839e3f1db48511993d50b7f75d2240",
  "envFlags": { "PR_INVERSION_ENABLED": true, "RTMW_DETERMINISTIC": true },
  "modelInitCanary": { "pipelineLoaded": true, "adaptersReady": true,
    "poseEngine": "RTMWPoseEngine", "recognizer": "GeminiTechniqueRecognizer", "modelLoaded": true }
}
```

- `commitSha` == 현재 origin/main == `eb08e87` (33-05 M3 fix 포함) ✓ (codex concern 6 — bare 200 불충분)
- PR=1 / deterministic=1 / modelLoaded=true / RTMWPoseEngine ✓
- **트래픽 격리(codex concern 14):** 전용 eval Pod `k508k3lut0o3f1` — 프로덕션 Lambda 미재동기화
  (`RUNPOD_ANALYZE_URL` 무접촉). 외부 분석이 SERIAL sweep 과 동시 실행 불가.
- 로컬·origin·Pod repo 3자 전부 `eb08e87` 일치 확인.

---

## Task 2 — shadow-candidate SERIAL 재스윕 + 여유/분리 수집

**소비 방식(codex concern 3):** `run_sweep` in-process `_process` 에 `SUNITY_SHADOW_REFERENCE_VERSION=
phase33-cm3-run1` 주입. `firestore_admin.get_reference_motion` 이 `reference/{id}/versions/phase33-cm3-run1`
의 consumer 필드를 top-level meta 위에 overlay(read-only) — **top-level write 0**. 멤버별 소비된
candidate `anglesHash`(8-hex content hash) 를 tee 로 캡처:

| motion | success consumed anglesHash |
|--------|-----------------------------|
| ref-power-spin | `4267fbfa` |
| ref-peter-pan | `2e8393e8` |
| ref-elbow-twist-sister | `7ef0ffaa` |
| ref-pdshape | `a1f9e553` |
| ref-kip-up | `e663f549` |

SERIAL(동시성 비안전) · 6 fixture 동일 빈도(kip-up 편중 없음) · `RTMW_DETERMINISTIC=1` ·
`PR_INVERSION_ENABLED=1` · `GEMINI_VISION_VETO_ENABLED=1`.

### 여유(margin) = tol(20°) − max(angle_vs_reference 관절 편차) — success 멤버 (결정론 지표)

| motion | 예선 여유 | **candidate 여유** | Δ | maxDev | 판정 |
|--------|:--:|:--:|:--:|:--:|:--:|
| power-spin | +9.0 | **+12.23** | +3.23 | 7.77 | 양수 ✓ |
| peter-pan | +10.5 | **+16.39** | +5.89 | 3.61 | 양수 ✓ |
| elbow-twist-sister | +0.2 | **+3.10** | +2.90 | 16.90 | 양수·**≥+2.0** ✓ |
| pdshape | **−1.2** | **+3.29** | +4.49 | 16.71 | **음→양 전환** ✓ |
| kip-up | +15.8 | **+19.06** | +3.26 | 0.94 | 양수 ✓ |

→ **6동작 여유 전항 양수 + 전부 개선**. pdshape 음→양 전환 = C+M3 최소 성립 조건(성공 판정 #1) 충족.
디버그 doc R-6 원문: "성공 판정은 점수 값이 아니라 여유(margin) 부호와 크기로 볼 것" — 여유는 RTMW-
deterministic(pdshape 2-run edit 0.0° 로 실증).

### 분리(separation = success − fault score) vs 예선 floor (score 기반 지표)

| motion | fault | success | **candidate sep** | doc floor | committed base sep | 판정 |
|--------|:--:|:--:|:--:|:--:|:--:|:--:|
| power-spin | 65 | 100 | **35** | 45 | 43 | **미달** (35<45, 35<43) |
| peter-pan | 79 | 100 | 21 | 21 | 17 | ✓ |
| elbow-twist-sister | 0 | 100 | 100 | 35 | 39 | ✓ |
| pdshape | 43 | 100 | 57 | 53 | 46 | ✓ |
| kip-up | 79 | 100 | 21 | 20 | **53** | doc floor ✓ / committed floor 미달 |

**분리 floor 불안정성(중요):** 예선 floor 자체가 소스마다 크게 다르다 — kip-up 은 **doc 20 vs
committed baseline 53** (33점 차), power-spin 43(committed) vs 45(doc). 이는 분리(score)가 **Gemini
vision-pointing 변동**을 내포함을 실증한다(같은 fault 라도 run 마다 짚는 관절 집합이 달라 fault score
가 흔들림). 그래서 substrate 조사(디버그 doc)는 분리가 아니라 **여유**를 정직한 지표로 지정했다.

**power-spin 분리 하락의 기전(무엇을 열어봤나, D-19):** power-spin fault measuredDeviations =
{left_elbow 25.13, left_shoulder 27.42, right_shoulder 19.93, **left_hip 18.06, right_hip 15.80**,
right_elbow 15.79}. 예선(18fps ref)에서 tol 20° 를 넘던 hip 편차가 candidate(9fps 밀도 정합)에서
**tol 아래로 내려가** angle 감점 관절이 줄었다. fault 는 여전히 `leg_extension`(absolute IPSF −20,
다리 미신전)로 정확히 포착됨. 즉 power-spin fault 57→65 는 **밀도 아티팩트 감점 제거(정확도 개선)**이지
결함 미포착이 아니다. 분리 35점은 여전히 강한 변별(fault 65 vs success 100).

### fixture-less self-comparison (R-3, 33-COVERAGE-MATRIX 5종)

reference 영상을 학생으로 재투입(mode1, 같은 ref, shadow candidate). `verify_self_comparison.py` 는
`NlfPoseEstimator`(NLF TorchScript) 의존이라 RTMW Pod 에서 미동작 → **동일 의도를 프로덕션 `_process`
(RTMW) 로 충실 대체**(Rule 3, 아래 편차):

| motion | score | maxDev | 판정 |
|--------|:--:|:--:|:--:|
| ref-foxtop | 100 | 0.0027 | self-consistent ✓ |
| ref-foxtop-split | 100 | 0.0028 | self-consistent ✓ |
| ref-invert | 100 | 0.0028 | self-consistent ✓ |
| ref-sideway-spin | 100 | 0.0029 | self-consistent ✓ |
| ref-combo | 100 | 0.0026 | self-consistent ✓ |

→ 5/5 만점 + maxDev ≈ 0 (≈0.003°). candidate substrate 가 내부 일관(자기 자신과 정렬 시 편차 0).
climb 은 comparison-gate(scoreless)로 별도 처리(아래).

### pdshape 2-run 안정성(R-6, item #7) + combo 2-run 결정론(R-4)

- **pdshape:** run1 여유 +3.2923 / run2 여유 +3.2923 → **|edit| = 0.0°** (예선 밀도스윕 ±30점 요동 대비
  소멸). 예선언 boundary = < 2.0°.
- **combo:** run1 maxDev 0.0025594865728066907 / run2 **동일 16자리** → drift **0.0** (P99_EPSILON 1.0 하회).
  931→621 frame 최장 클립·과거 23.43°→0.193° 요동 이력 완전 해소.

---

## Task 3 — JSON 데이터 게이트 (8 item, 예선 boundary) + M8 + 롤백 + elbow-twist route

### SEED 8-item 판정 (predeclared boundary + oracle, codex concern 12)

| # | gate | 예선 boundary + oracle | 결과 | 판정 |
|---|------|------------------------|------|:--:|
| 1 | 여유 전항 양수 | 6동작 success 여유 > 0 (pdshape neg→pos) | 전항 양수, pdshape −1.2→+3.29 | **PASS** |
| 2 | 분리 ≥ floor | (success−fault) ≥ {ps45,pp21,et35,pd53,ku20} | power-spin 35 < 45 | **FAIL** |
| 3 | inversion 편차 바닥 축소 | inv 2동작 success maxDev 예선 대비 **−2.0° 이상** 감소 | elbow-twist 19.8→16.90(−2.9), pdshape 21.2→16.71(−4.49) | **PASS** |
| 4 | M8 소비측 무회귀 | 원본-5 joints3d/kr.data/axisData 단일 `(x,y,0)` + finite + 크롭 육안 무붕괴 | 5/5 `(x,y,0)`·finite, 크롭 4/4 정상 (디바이스 육안=33-16) | **PASS** |
| 5 | M3 발동 | ≥1 멤버에서 ref window 트림 | elbow-twist fault + kip-up fault 트림 | **PASS** |
| 6 | safety 신규 FP/FN | candidate flag == baseline flag (둘 다 0) | candidate 0, baseline 0 → new FP/FN 0 | **PASS** |
| 7 | pdshape 2-run 안정 | 2-run 여유 edit < 2.0° | 0.0° | **PASS** |
| 8 | 임계 refit 0 | live tol/slope/cap/epsilon == pinned manifest | 전 상수 동일 (scoring-constants-match) | **PASS** |

**gate_check.py 실행 (종료 코드가 게이트, codex concern 8 — grep 금지):**

```
# 8-item 전항 요구:
gate_check --file 33-S4-VERIFY-EVIDENCE.json --require-all-pass gate1..gate8 \
  --require-hashes 11 --no-rollback-trigger --scoring-constants-match scoring_constants_pinned.json
→ FAIL: gate2 status=FAIL (PASS 아님);  exit 1

# 결정론 substrate 게이트(해시 11 + 롤백 + 상수):
gate_check --file ... --require-hashes 11 --no-rollback-trigger --scoring-constants-match ...
→ PASS;  exit 0

# 7 결정론 게이트(gate2 분리 제외):
gate_check --file ... --require-all-pass gate1 gate3 gate4 gate5 gate6 gate7 gate8
→ PASS;  exit 0
```

- `--require-hashes 11`: candidate 11 doc SHA-256(33-S1 run1) 전부 present + non-empty → PASS.
- `--no-rollback-trigger`: 4 트리거 전부 False → PASS.
- `--scoring-constants-match`: live dump(`dump_scoring_constants.py`) == pinned {tol20/slope1.2/cap90/
  MEAN0.1/P99 1.0} → PASS (D-20/D-29 refit 0 을 데이터로 강제).

### M8 소비측 검증 (R-5, success 판정 #4)

**서버측 substrate(flip 전 검증 가능분) — 읽기 전용 Firestore probe:**

| motion | 계보 | layout | finite | kr.data/axisData finite | live-axis spans |
|--------|------|--------|:--:|:--:|--|
| ref-climb | bukuroo-06-06 | **(x,y,0)** | ✓ | ✓/✓ | [277.1, 270.1] |
| ref-foxtop | bukuroo-06-06 | **(x,y,0)** | ✓ | ✓/✓ | [277.3, 286.0] |
| ref-foxtop-split | bukuroo-06-06 | **(x,y,0)** | ✓ | ✓/✓ | [274.4, 303.5] |
| ref-invert | bukuroo-06-06 | **(x,y,0)** | ✓ | ✓/✓ | [265.4, 268.6] |
| ref-sideway-spin | bukuroo-06-06 | **(x,y,0)** | ✓ | ✓/✓ | [277.5, 259.9] |
| (대조) ref-pdshape/kip-up | direct-06-12 | (x,y,0) | ✓ | ✓/✓ | 정상 |

→ 원본-5(예전 `(x,0,y)`)가 **단일 `(x,y,0)` 로 수렴** — M8 2계보 분기 해소. keypointReport.data +
axisData 유한, spans 정상(골격 미붕괴). direct-06-12 대조군과 동일 레이아웃.

**fault-zoom 크롭 육안(실제 산출물 오픈, D-19 / [[open-the-artifact-before-claiming-done]]):**
원본-5 계보 fixture-less 4종의 self-comparison 이 candidate `(x,y,0)` joints3d 로 서버 크롭 생성 →
presigned URL 다운로드 후 육안 확인 (`33-S4-M8-crops/*.png`):

- **ref-foxtop**: 좌(학생)=역위 그립, 빨강 원이 pole 옆 left_hand 에 정위치. 우(reference) 정상. 붕괴 0.
- **ref-invert**: 빨강 원이 pole 옆 손/다리에 정위치, 골격이 크롭 박스를 정확히 구동. 붕괴 0.
- **ref-sideway-spin**: 빨강 원이 손/머리 영역 정위치, body 중앙 정렬. 붕괴 0.
- **ref-foxtop-split**: 좌 그립 정위치 원. 우는 DTW frame 선택으로 body 상단 프레임(정상 프레임, 붕괴 아님).

→ 4/4 크롭이 joints3d 구동 영역을 정확히 국소화(garbled/empty 없음) — candidate `(x,y,0)` 레이아웃이
크롭 소비 경로에서 올바르게 처리됨.

**디바이스(Simulator) 육안 — 33-16 소관(canonical matrix):** 앱 오버레이는 reference 골격을 **top-level
`reference/{id}`** 에서만 읽는다(`useReferenceMotion` → `refDoc.joints3d`). candidate 는 `versions/` 에만
있고 flip(33-07)은 이 플랜 범위 밖이므로, **앱이 candidate 오버레이를 flip 전에 로드할 수 없다**(구조적
차단). 33-COVERAGE-MATRIX(canonical) 는 원본-5 lineage 의 **M8 디바이스 육안을 33-16 phase-gate device
UAT 에 귀속**한다(row 6~10 owner column + consumer contract). 따라서 33-06 은 flip-전 검증 가능분(서버
substrate + 크롭 육안)을 수행하고, 디바이스 오버레이 육안은 **33-16 으로 라우팅**(silent skip 아님).

### 롤백 트리거 4종 평가 (D-31)

| 트리거 | 조건 | 실측 | 발동 |
|--------|------|------|:--:|
| 여유 부호 음수 | 어느 fixture 든 success 여유 < 0 | 6/6 양수 | **No** |
| 원본-5 오버레이/크롭 깨짐 | M8 전환 회귀 | 서버 substrate 단일수렴 + 크롭 4/4 정상 | **No** |
| combo 2-run > P99 | drift > 1.0° | 0.0° | **No** |
| safety 신규 FP/FN | candidate ≠ baseline flag | 둘 다 0 | **No** |

→ **롤백 트리거 전부 clear.** (flip 미수행 상태이므로 되돌릴 것도 없음.)

### elbow-twist 처방 경로 (codex concern 13 / D-32ⓑ)

- candidate 여유 **+3.10** (예선 +0.2 → +2.90 개선), maxDev 16.90.
- **+3.10 ≥ +2.0 → 여유 충분히 양수로 회복 = 해소.** belle 질문 불요.
- **33-21(formal HALT loop) 은 no-op** — 처방 경로 2단계 "여유 ≥ +2.0 → 추가 조치 없음, 결과만 보고".
- 참고: 33-04 가 ref-elbow-twist-sister bodyNorm confidence 0.385(최저) 경고했으나, 재추출 후 여유가
  건전(+3.10)하게 나와 그 낮은 confidence 가 결과를 훼손하지 않았음.

---

## 종합

| 항목 | 결과 |
|------|------|
| shadow 소비(top-level 무flip, anglesHash 기록) | PASS |
| 여유 6/6 양수 + pdshape 음→양 | PASS (gate1) |
| **분리 ≥ floor** | **power-spin 35 < 45 미달 (gate2 FAIL)** |
| inversion 편차 바닥 축소 (−2.9 / −4.49°) | PASS (gate3) |
| M8 서버 substrate 단일 `(x,y,0)` + 크롭 육안 | PASS (gate4); 디바이스 육안=33-16 |
| M3 발동 (elbow-twist·kip-up fault 트림) | PASS (gate5) |
| safety 신규 FP/FN 0 | PASS (gate6) |
| pdshape 2-run edit 0.0° | PASS (gate7) |
| 임계 refit 0 (live==pinned) | PASS (gate8) |
| 롤백 트리거 4종 | 전부 clear |
| elbow-twist route | 33-21 no-op (여유 +3.10) |
| **gate_check --require-all-pass gate1..gate8** | **exit 1 (gate2)** |
| gate_check hashes11 + no-rollback + constants | exit 0 |

**판정:** 결정론 지표(여유·M8·결정론·self-comparison·safety·refit) **전항 통과**로 substrate 는 검증됨 —
pdshape 위양성 소멸, elbow-twist 회복(HALT 없음), 인버전 아티팩트 축소, 축 레이아웃 통일. **롤백 불요.**
유일 미달은 gate2 power-spin 분리(35<45)로, 이는 (a) score 기반·Gemini 변동 내포 지표이고(floor 자체가
소스마다 kip-up 20↔53 로 불안정), (b) power-spin fault 밀도 아티팩트 감점 제거(정확도 개선)의 부수효과다.
**belle/오케스트레이터 판정 대상**(이 플랜에서 goalpost 이동으로 gate2 를 PASS 처리하지 않음, codex 12).
33-07 flip 은 gate2 결정 전까지 보류.

## 이 산출물이 틀렸다면 어떻게 알았을까 (D-18)

- 여유 음수 1건 → gate1 FAIL + 롤백 트리거. (실측 6/6 양수)
- candidate 미소비(anglesHash 부재/불일치) → get_reference_motion tee 로그 공란. (5/5 hash 기록됨)
- M8 크롭 붕괴 → 다운로드 PNG 가 empty/garbled. (4/4 정상 육안)
- combo 요동 재발 → run1≠run2. (16자리 동일)
- 상수 refit → scoring-constants-match drift. (live==pinned exit 0)
- 분리 미달 은닉 → gate_check exit 0 을 grep 으로 위장. (JSON 데이터 게이트로 exit 1 정직 노출)

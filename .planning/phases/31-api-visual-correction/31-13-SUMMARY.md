---
phase: 31-api-visual-correction
plan: 13
subsystem: calibration-harness + threshold-gate
status: BLOCKED
tags: [calibration, judge, pose-gate, threshold, release-gate, measurement]
requires:
  - "RunPod Pod 기동 (/pose-image) — pose 축 12건 측정 재개 조건"
  - "추가 생성 예산 — PASS 표본 +1 이상 (H4-10 하한 잔여분)"
  - "belle 설계 판단 — confidence 격자 상향 또는 confidence 축 게이트 제외"
provides:
  - "backend/scripts/calibrate_visual_gates.py — 재현 가능 calibration harness (측정 재구현 0)"
  - "smoke/CALIBRATION.json — blocked=true + 사유 3종 + judge raw 12건 + confusion table"
  - "smoke/fixtures_manifest.json — wan scope 12 pair (PASS 3/FAIL 9), failure axis 7종 전부"
  - "31-ACCEPTANCE.md — Calibration 결과표 + build gate ordering + 해소 조건"
affects:
  - "31-09 / 31-10 (주입할 env 4값 없음 → VISUAL_CORRECTION_ENABLED OFF 고정)"
  - "31-12 (CALIBRATION.blocked=true → H4-09 배포 게이트에서 라이브 롤아웃 차단)"
  - "31-06 (pose gate 필요성이 실측으로 확인됨 — judge 단독으로 지배적 실패유형 미검출)"
tech-stack:
  added: []
  patterns:
    - "calibration harness 가 측정 로직을 갖지 않고 shipped 구현만 호출 (임계값 고른 코드 = 도는 코드)"
    - "측정 불가를 보간으로 메우지 않고 typed blocked 사유로 방출 (fail-closed)"
    - "적대적 유도 표본을 sampleKind 로 분리 — 검출력 검증에는 쓰되 실패 분포로는 쓰지 않음"
    - "판별력 없는 축(전 격자 동률)을 blocked 사유로 승격 — arbitrary fallback 금지의 실행"
key-files:
  created:
    - backend/scripts/calibrate_visual_gates.py
    - .planning/phases/31-api-visual-correction/smoke/CALIBRATION.json
  modified:
    - .planning/phases/31-api-visual-correction/smoke/fixtures_manifest.json
    - .planning/phases/31-api-visual-correction/31-ACCEPTANCE.md
decisions:
  - "calibration scope 를 chosen 모델(wan2.7-image-pro)로 한정 — qwen 은 B4-02 구조적 탈락이라 그 산출물 기반 임계값은 돌지 않을 코드의 근거"
  - "PASS 하한 1건 부족을 재라벨로 메우지 않고 blocked 로 박제"
  - "RESULTS.json 무수정 — blocked 는 B4-02 async-only 전용 의미이며 shipped 상수와 lockstep (계획서 지시 대비 의도적 편차)"
  - "confidence 격자 전 구간 동률을 blocked 사유로 신설 — 동률 상태의 '최소값 선택'은 무작위 선택"
metrics:
  tasks_completed: 3
  tasks_total: 2
  generation_calls: "8 / 8 (승인 상한 준수)"
  judge_calls: "12 / 24 (상한 준수, 12콜 잔여)"
  duration: "약 55분"
  completed: "2026-07-20"
---

# Phase 31 Plan 13: Display/Training 게이트 calibration Summary

31-05/31-06 의 **실제 출하 코드를 호출하는** calibration harness 를 만들고 실측했다.
결과는 **`blocked = true` — 임계값 4값 전부 미채택**이며, 이는 실패가 아니라 **측정된 결론**이다.
숫자를 하나도 지어내지 않았다.

## 작업 상태

| Task | 내용 | 상태 | 커밋 |
|------|------|------|------|
| 1 | `calibrate_visual_gates.py` harness | COMPLETE | `82be88c` |
| 1b | fixture 8건 보충 (belle 승인 추가 예산) | COMPLETE | `f94ca95` |
| 2 | calibration 실행 + CALIBRATION.json + ACCEPTANCE | **COMPLETE (blocked 박제)** | `28b6ca4` |

## 핵심 실측 — judge 는 지배적 실패 유형을 놓친다

이 plan 이 산출한 가장 중요한 사실이다.

| failure axis | 표본 | judge 검출 |
|--------------|------|-----------|
| `pole` | 1 | 1 |
| `background` | 1 | 1 |
| `extra_limbs` | 1 | 1 |
| `identity` | 1 | 1 |
| `clothing` | 1 | 1 |
| `correction_invisible` | 2 | 1 |
| **`pose_tolerance`** | **6** | **2** |

judge 는 보존 축(폴·배경·사지·인물)은 5/5 로 정확히 잡아냈다. 그러나 **production 의
지배적 실패 유형인 `pose_tolerance`(자세 전면 재생성)를 6건 중 4건 놓쳤다.**
그 4건은 7축이 **전부 true** 이고 confidence 가 **0.95 ~ 1.00** 이었다 — judge 가
**확신을 갖고 틀렸다.**

귀결: **display 게이트의 안전성은 사실상 전적으로 31-06 pose gate 에 달려 있다.**
그리고 그 pose gate 가 지금 측정 불가한 축이다. 31-06 모듈 헤더의 설계 근거
("생성형 judge 는 그럴듯한가만 판정할 뿐 기하가 맞는가를 판정하지 못한다")가 실측으로 확인됐다.

## blocked 사유 3종 (전부 측정 결과)

1. **`insufficient_pass_samples:3<4`** — wan scope PASS 3/FAIL 9. FAIL 하한은 충족, PASS 1건 부족.
2. **`pose_unmeasured_fraction:12/12`** — Pod 부재로 `/pose-image` 12건 전부 `pose_gate_unavailable`.
   **실제로 호출해서 얻은 결과**이며 "시도하지 않음"이 아니다. 격자 16조합 전부 `evaluable=0`.
3. **`confidence_axis_non_discriminating`** — confidence 격자 4값(0.6/0.7/0.8/0.85)이
   FA/FR 완전 동률(FA 4, FR 1). false accept 4건이 전부 confidence 0.95~1.00 에 몰려 있어
   **격자 상단(0.85)보다 높다 → 어떤 confidence 임계값으로도 제거되지 않는다.**
   동률 상태에서 "FA 최소" 규칙은 무작위 선택이 되고, 그것이 M4-03 이 금지한 arbitrary fallback 이다.

## fixture 보충 (승인 예산 8콜 전량 집행)

`wan2.7-image-pro` 전용 8콜 — faithful 4 + adversarial 4. **상한 준수, 초과 0.**
S3 임시 key 4건 delete + HEAD 404 검증 완료. 산출 이미지는 `/Users/Shared` 유지, git 저장 0.

| scope | 31-01 | 31-13 후 |
|-------|-------|----------|
| PASS | 2 | **3** |
| FAIL | 6 (전체 8) | **9** |
| 총 pair (wan) | 4 | **12** |
| failure axis | 3축 | **7축 전부** |

누락 4축(`pole`/`background`/`extra_limbs`/`identity`)은 적대적 프롬프트로 **전부 유도 성공**했다:
폴 완전 제거 / 배경 해변 교체 / 팔 4개 / 인물 남성 교체. 각각 judge 가 정확히 검출했다.

**신규 8건 전부 before/after 이미지를 Read 로 열어 시각 확인 후 라벨을 부여했다 — 추정 라벨 0건.**

faithful 4콜 중 PASS 는 chair-spin 1건뿐이었고 나머지 3건은 **강화된 보존 지시에도**
자세를 전면 재생성했다. **하한을 맞추려 FAIL 을 PASS 로 재라벨하지 않았다.**

## Deviations from Plan

**1. [Rule 4 → 판단] `RESULTS.json.blocked` 갱신 지시 미이행 (의도적)**

계획서 Task 2 는 "미달 시 RESULTS.json.blocked 를 true 로 갱신"을 지시한다. 이행하지 않았다:

- 그 필드는 **B4-02 async-only 릴리스 게이트** 전용 의미이며,
  `visual_gen.derive_engine_blocked` + 전사 상수 `_RESULTS_BLOCKED = False` 와 lockstep 이다.
  true 로 바꾸면 shipped 모듈과 드리프트가 생기는데, **shipped 분석 모듈은 수정 금지 범위**다.
- 31-12 는 RESULTS 와 CALIBRATION 을 **각각** 읽으므로(`H4-09`),
  `CALIBRATION.blocked=true` 만으로 "flag OFF" 목적은 **이미 달성**된다.
- 서로 다른 두 사건(벤더 async 미지원 / calibration 근거 부족)을 한 필드에 겹치면
  나중에 어느 쪽이 원인인지 복원 불가능해진다.

ACCEPTANCE 결론 절에 사유를 명시했다. 다른 판단이면 되돌리기는 1줄이다.

**2. [Rule 2] `confidence_only_table` + `confidence_axis_non_discriminating` 추가**

계획서에 없는 산출이다. pose 축을 못 잰 상태에서 "아무것도 측정 못 함"으로 끝내면
**confidence 축에 대해 말할 수 있는 것까지 버리게 된다.** pose 게이트는 통과 집합을
줄이기만 하므로 `judge 단독 FA ≥ production FA`(상한), `FR ≤ production FR`(하한)이라는
엄밀한 관계가 성립한다 — 그 범위로 한정해 기록했다. 그 결과 발견된 것이 위 blocked 사유 3이다.

**3. [계획 대비 확장] calibration scope 를 chosen 모델로 한정**

계획서는 scope 를 명시하지 않았다. `--generator` 기본값을 `wan2.7-image-pro` 로 뒀다 —
`qwen-image-edit-plus` 는 B4-02 에서 **구조적으로 탈락**했으므로 그 산출물로 고른 임계값은
**결코 실행되지 않을 코드에 대한 근거**가 된다. `--generator all` 로 전체 조회 가능.

**4. [스코프 준수] 생성 스크립트를 repo 에 남기지 않음**

fixture 보충 생성기는 세션 scratchpad 에서 실행했다 — 오케스트레이터가 지정한 소유 파일 4종에
포함되지 않기 때문이다. 재현성은 manifest 에 항목별 `generationPrompt` / `generationRun`
(model·mode·parameters·일시)을 박아 확보했다.

## Known Stubs

| 항목 | 위치 | 사유 |
|------|------|------|
| `chosen` 4값 부재 | `CALIBRATION.json` | **의도된 결론** — blocked 3종. 보간 금지 |
| `afterKeypointSource.modelVersion = null` | `fixtures_manifest.json` 16건 | Pod 부재로 RTMW 실측 미수행. `pose_model_version_set = []` 로 정직하게 빈 상태 |
| Display/Training 임계값 숫자 0개 | `31-ACCEPTANCE.md` | placeholder 아님 — 측정된 결론 |

## 해소 조건

1. **PASS +1 이상** — 추가 생성 예산 필요 (faithful 실측 PASS 율 = 4콜 중 1건).
2. **Pod 기동** — `/pose-image` 살아나면 pose 12건 측정 → 격자 16조합 성립.
   harness 재실행만 하면 되고 judge 는 캐시 재사용으로 과금 0.
3. **confidence 격자 재설계 (belle 설계 판단)** — 현행 상단 0.85 는 무의미하다.
   상향(0.9/0.95/0.98/0.99)하거나 **confidence 를 게이트 축에서 빼고 pose 축에 의존**하는
   결정이 필요하다. 이건 측정이 아니라 설계 영역이라 임의로 정하지 않았다.

## 지출

| 항목 | 사용 | 상한 | 준수 |
|------|------|------|------|
| 생성 (DashScope) | 8 | 8 | 준수 |
| judge (Gemini) | 12 | 24 | 준수 (12 잔여) |

## 위생

- 산출 JSON 서명 URL / 이미지 바이트 **0** (프로그램 검사 통과)
- 키 리터럴 **0** — 전부 SSM → env. 로그 출력 0
- `.planning` 하위 인물 이미지 **0건**, 스테이징된 PNG **0건**
- S3 임시 업로드 4건 delete + HEAD 404 검증 **4/4**
- `app/**` 무수정, `STATE.md` / `ROADMAP.md` 무수정, shipped 분석 모듈 무수정

## Self-Check: PASSED

- `backend/scripts/calibrate_visual_gates.py` — 존재, `ast.parse` OK, `--dry-run` exit 0
- `smoke/CALIBRATION.json` — 존재, 계획서 automated assert 통과(blocked 분기)
- `smoke/fixtures_manifest.json` — 16건, harness 가 before/after sha256 **32건 전건 재검증 통과**
- `31-ACCEPTANCE.md` — 존재, `Training` grep 통과, 임계값 선언 숫자 0
- 커밋 `82be88c`, `f94ca95`, `28b6ca4` — git log 확인
- harness 가 `judge_corrected_pose` / `judge_display_pass` / `joint_inner_angle_deg` /
  `measure_generated_pose` 를 import 호출 — 측정 재구현 **0**
- 신규 fixture 8건 **전건 시각 확인** 후 라벨 (Read 호출 기록)

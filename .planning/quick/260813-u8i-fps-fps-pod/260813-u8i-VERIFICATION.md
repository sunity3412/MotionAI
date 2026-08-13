---
phase: quick-260813-u8i
verified: 2026-08-13T15:20:00Z
status: passed
score: 7/7 must-haves verified
overrides_applied: 0
---

# Quick 260813-u8i: 카드 초 라벨 ÷9.0 잔존 수리 Verification Report

**Goal:** fault_zoom 확대 카드 초 라벨 ÷9.0 잔존 버그를 실효 fps 환산으로 수리 (표시 전용·채점 무접촉) + 승인 무회귀(라벨만 의도 변경)·pytest 기준선 + Pod 실증
**Verified:** 2026-08-13T15:20Z
**Status:** passed
**Re-verification:** No — initial verification

검증 방법 정본: SUMMARY 문장은 증거로 쓰지 않았다. verify_label.py 를 검증자 프로세스에서 직접 재실행(exit 0)했고, 카드 PNG 는 전부 직접 Read 로 픽셀을 읽었으며, git diff·grep·로그 대조는 전부 직접 수행했다.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence (검증자 직접 실행) |
| --- | --- | --- | --- |
| 1 | 확대 카드 초 라벨 == freeze 실초 (측별 ≤1.5프레임/eff), ÷9.0 잔존 소멸 | ✓ VERIFIED | verify_label.py 재실행 exit 0 — 라운드트립 10카드 전건 PASS (구 라벨 전건 ~1.11배 부풀림 → 신 라벨 freeze ≈일치). Pod fresh 카드 픽셀 직접 Read: left_elbow **5.3s** (freeze u5.302), left_hip **16.7s** (freeze u16.667). nh4 구 카드 직접 Read: 같은 장면 라벨 **5.9s** — 5.9→5.3 앵커 성립 |
| 2 | 표시 전용 — freeze·survivors/dropped·마크 좌표·프레임 선택·채점·records 무변경 | ✓ VERIFIED | 산식 5파일 `git diff 1eccf9cd^..f9a8f3f0` 빈 출력 (파일 5개 실존 확인). 대조 런(shim label_fps=9.0) md5Δ=0 == nh4 정본 전건 — 픽셀 변경원이 라벨뿐임의 기계 증명 재현. survivors/dropped/display_anchor == nh4 정본 (게이트 1 재실행 PASS). 코드 diff 직접 검토: 3695-3696 분모 교체만, frames_fps 프레임 선택 용처 잔류 |
| 3 | label_fps 미지정 경로 byte-동일 | ✓ VERIFIED | test_fault_zoom_label_fps.py 실물 확인 (하위호환 byte-동일 / 측별 환산 / 측별 폴백 / fail-open 4행동) + 재실행 full pytest 4167 passed (신규 실패 0). 코드: 기본 None → 양측 분모 = frames_fps (동일 산식) |
| 4 | 승인 5동작 스윕 재현 게이트 + 라벨 전/후 표 | ✓ VERIFIED | verify_label.py 검증자 재실행: cards=10 md5Δ=0, display_anchor 로그 본 런==대조 런 (8건), 표는 nh4 정본 freezes 기계 유도 (하드코딩 앵커 0 — 코드 `_crit_to_freeze` 확인). **재실행 산출 evidence 가 커밋본과 byte-동일** (50파일 md5 대조 — pytest tail 의 벽시계 시각 1줄만 차이, 결과 59f/4167p 동일) — 결정론 재현이 커밋 증거의 진위를 재확증 |
| 5 | pytest 기준선 59 failed 동일 + 신규 테스트 PASS + 리터럴 0 | ✓ VERIFIED | 재실행 결과 `59 failed, 4167 passed, 26 skipped` — 기준선 일치. 추가 라인 동작명/분석 ID 리터럴 독립 grep 0건 + 게이트 6 branchLiteralHits=[] |
| 6 | Pod mddy6gsqmt24ud 실증 — /health sha 일치 + fresh 점수 60 + 라벨 실초 일치 | ✓ VERIFIED | health.json commitSha==ebfad42c(수리 포함 HEAD, git rev-parse 대조). `_fresh_u8i_full.log` 실물: `score=60`, `card_gates verdict ... survivors=['r00:inherit@u5.302/r5.13','r03:inherit@u16.667/r15.20']`, display_anchor 좌표 — nh4 fresh 원본 로그(`_fresh_nh4_full.log`)와 라인 단위 직접 대조 전건 동일. 회수 카드 2장 픽셀 직접 Read: 5.3s/16.7s |
| 7 | 제약 — Gemini 스텁·S3 업로드 0·AWS 무변경·Pod 유지·LLM 영향 기재 | ✓ VERIFIED | 재실행 eyeStub=12 (게이트 7 PASS, 하네스 `GEMINI_API_KEY=stub` 선차단 코드 확인). 하네스 put_object = 로컬 저장 대체 (verify_local.py:190-202 직접 확인 — 업로드 0 구조적). 수리 커밋 4건 diff 에 template.yaml/SSM 무접촉. POD-VERDICT 에 터미네이트/스톱 제안 없음 명기. SUMMARY LLM 학습 영향 절 실재 |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `backend/shared/python/sunity_shared/analysis/fault_zoom.py` | keyword-only label_fps 측별 환산 + fail-open | ✓ VERIFIED | 2791 시그니처, 2928-2937 fail-open 산출, 3695-3696 분모 교체 — HEAD 실물 grep 확인 |
| `backend/functions/pipeline/app.py` | 두 경로 배선 (게이트 eff dict 재사용 + 스테이지 probe fail-open) | ✓ VERIFIED | 3416 confirmed / 3458 advisory / 4869 게이트 — 3곳 `label_fps=` 실재. 스테이지 probe try/except fail-open 코드 확인 |
| `backend/tests/test_fault_zoom_label_fps.py` | 4행동 유닛 (하위호환/측별/폴백/fail-open) | ✓ VERIFIED | 154줄 실물 — 합성 프레임 픽스처, 기대값 base 런 역산 (하드코딩 0), full pytest 통과분에 포함 |
| `docs/contract.md` | §11.8 환산 서술 실효 fps 정정 | ✓ VERIFIED | 1896 부근 userVideoSec/refVideoSec 서술 "실효 fps — quick-260813-u8i" — 필드 형태 무변경, diff 로 확인 |
| `.planning/.../verify_label.py` | 7게이트 재현 드라이버 (nh4 구조 상속) | ✓ VERIFIED | 434줄 실물 + **검증자 직접 재실행 exit 0** |
| `.planning/.../evidence/` | label_check.json + 카드 + EYE + pod/ | ✓ VERIFIED | 50파일 — 재실행으로 byte-동일 재현 (타이밍 1줄 제외) |
| `260813-u8i-SUMMARY.md` | 보고 + LLM 영향 + 한계 박제 | ✓ VERIFIED | 실재. LLM 학습 영향·한계 박제 절 포함. (PLAN/SUMMARY 는 미커밋 — 오케스트레이터 번들 커밋 대상, GSD 정상 흐름) |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| app.py 게이트 경로 (4869) | fault_zoom.build_fault_zoom_comparisons | `label_fps=(eff["user"], eff["ref"])` | ✓ WIRED | 기존 eff dict 재사용, probe 신규 0 — diff 검토로 확인. Pod fresh 로그의 라벨 변화(5.9→5.3s)가 이 배선의 운영 실행 증거 |
| fault_zoom 라벨 사이트 (3695-3696) | _stamp_time 픽셀 + userVideoSec/refVideoSec 필드 | u_video_sec/r_video_sec 단일 변수 | ✓ WIRED | F-3 단일 산출 유지 — 3721-3730 방출부 무변경 (같은 변수). Pod doc 필드값 == record atVideoSec 완전 동치 (POD-VERDICT 표) |
| verify_label.py | nh4 sweep_verdict_port.json | 정본 기계 대조 (freezes/md5/verdict) | ✓ WIRED | 정본 파일 구조 직접 확인 (freezes/pngMd5/verdict 실재) + 재실행 대조 전건 PASS |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| 카드 초 라벨 픽셀 | u_video_sec/r_video_sec | 표시 인덱스 ÷ 측별 실효 fps (probe_effective_fps) | Yes — Pod 운영 경로에서 5.302→"5.3s" 실측 | ✓ FLOWING |
| fail-open 폴백 | u/r_label_fps | None/비유한/비양수 → frames_fps | Yes — 유닛 테스트 + 코드 확인 | ✓ FLOWING |

### Behavioral Spot-Checks / Probe Execution

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| 7게이트 재현 (스윕 2회 + full pytest 포함) | `backend/.venv/bin/python .planning/quick/260813-u8i-fps-fps-pod/verify_label.py` | `LABEL GATE PASS cards=10 md5Δ=0 pytest=59f/4167p eyeStub=12`, exit 0 | ✓ PASS |
| pytest 기준선 (게이트 4 내장) | full backend/tests | `59 failed, 4167 passed, 26 skipped` | ✓ PASS |
| 산식 5파일 무접촉 | `git diff 1eccf9cd^..f9a8f3f0 -- <5파일>` | 빈 출력 | ✓ PASS |
| 추가 라인 리터럴 | 독립 grep (동작명/ID) | 0건 | ✓ PASS |
| 재현 결정론 | 재실행 전/후 evidence 50파일 md5 대조 | 벽시계 1줄 제외 byte-동일 | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| QUICK-260813-U8I | 260813-u8i-PLAN.md | 카드 초 라벨 ÷9.0 잔존 수리 (표시 전용) + 무회귀 + Pod 실증 | ✓ SATISFIED | Truths 1-7 전건 |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| — | — | 추가 라인 TBD/FIXME/XXX/HACK/PLACEHOLDER 0건 (수정 6파일 전건 clean) | — | 없음 |

### Deviation 판정 (peterpan clamp 거울 분기)

SUMMARY 기재 Deviation — verify_label.py 게이트 3 의 clamp 분기 — 를 diff 로 직접 판정:

- **운영 코드 무접촉 성립**: 해당 분기는 커밋 ebfad42c 소속이고 이 커밋은 `.planning/` 파일만 변경 (git show --stat 확인).
- **허용치 완화 아님 성립**: TOL_FRAMES=1.5 불변. 분기는 `round(freeze×eff) >= 클립 마지막 인덱스` **이고** `신 라벨 == 마지막 프레임 실초 (1e-6)` 둘 다 성립할 때만 좁게 통과 — 운영의 기존 clamp(`min(..., u_n-1)`, fault_zoom.py:3181·3205 등 수리 전부터 실존)의 거울이다. 종전 라벨 6.8s 는 6.2s 클립 밖의 불가능한 초였고 신 라벨 6.1s 는 실제 표시된 마지막 프레임의 실초 — 수리 방향과 정합.

### Human Verification Required

없음 — 픽셀 판정(카드 라벨)은 검증자가 카드 PNG 4장(신 2 + nh4 구 1 + 로컬 스윕 1)을 직접 Read 로 확인했다. PLAN 에 human-check 블록 없음. 실기기 통합 검증은 belle 방침으로 별건 (플랜 objective 명기 — 이 사이클 범위 밖).

### Gaps Summary

없음. 7/7 truths 전건 VERIFIED. 특기: 검증자 재실행이 커밋 evidence 를 byte-동일 재현 (결정론 성립 — 커밋 증거가 조작·스테일이 아님을 재확증). 참고 (info): PLAN.md/SUMMARY.md 는 미커밋 상태 — GSD 오케스트레이터가 VERIFICATION.md 와 함께 번들 커밋하는 정상 흐름.

---

_Verified: 2026-08-13T15:20Z_
_Verifier: Claude (gsd-verifier) — verify_label.py 재실행·카드 픽셀 직접 Read·로그 라인 직접 대조_

---
phase: 29-mode3-result-screen-completion
plan: 03
subsystem: pipeline-postrender (backend — mode3 fault-zoom 대상 선택)
tags: [mode3, fault-zoom, d-08, criterion-region-mapping, tdd-red-green, wave-2]
requirements: [D-08]
dependency_graph:
  requires:
    - "29-02 — mode3 deductionBreakdown 방출 (zoom 대상 선택 소스)"
  provides:
    - "D-08: mode3 zoom 카드 대상 = 이번 분석 감점 record criterion id → region 매핑 (|Δscore| top-2 소스 폐기)"
    - "improved kind 미방출 (개선 부위 축하 카드 = deferred)"
    - "감점 record 0 / 비매핑 criterion 뿐 → zoom 카드 0 (의도된 동작)"
    - "criterion→region 매핑 표 박제 — 29-04 앱 helper 매핑과 cross-side 대조용"
  affects:
    - "29-04 (앱 projectDeductionRecordKeypoints — 매핑 항목 동일해야 드릴다운 매칭 성립)"
    - "29-05 (Pod sweep — mode3 zoom PNG 실데이터 확인)"
tech_stack:
  added: []
  patterns:
    - "fault_zoom._group_fault_joints 기존 region 카드 경로 재사용 (좌+우 동일-kind 멤버 전달 → region 1장) — 렌더러 무접촉"
    - "test_pipeline_deduction_seam.py path 주입 + mock 캡처 패턴 승계 (실 S3/렌더 0)"
key_files:
  created:
    - backend/tests/test_mode3_fault_zoom_selection.py
  modified:
    - backend/functions/pipeline/app.py
decisions:
  - "region 멤버 = 앱 REGION_MEMBER_KEYPOINTS 미러 (legs: hips+knees / arms: shoulders+hands, keypointReport 8-keypoint 이름공간) — fault_zoom._REGION_JOINTS 전체가 아닌 report-실재 부분집합"
  - "_joint_scores 헬퍼 제거 — mode3 빌더 단독 사용처였고 소스 폐기로 dead code (슬롭 금지)"
  - "region dedupe = record 등장 순 유지, 카드 상한 = 현행 top-2 유지 (legs+arms 최대 2장)"
metrics:
  duration_min: 12
  tasks_completed: 2
  files_created: 1
  completed_date: 2026-07-16
---

# Phase 29 Plan 03: Mode3 확대비교 감점 부위 소스 교체 Summary

**한 줄:** `_build_mode3_fault_zoom_comparisons` 의 zoom 대상 산출을 |Δscore| top-2(improved/worsened)에서 이번 분석 deductionBreakdown 감점 record 의 criterion id → region 매핑(kind='deficit' 고정)으로 교체 — mode1 줌과 동일 개념(결함 부위만), 감점 record 없으면 카드 없음, 렌더러(fault_zoom.py)·dtw 인자(28-05/CR-01) 무접촉.

## criterion → region 매핑 표 (cross-side 정합 박제 — 29-04 SUMMARY 와 대조 필수)

| criterion id | region | 비고 |
|---|---|---|
| `leg_extension` | `legs` | ipsf_absolute measured seed |
| `split_angle` | `legs` | ipsf_absolute measured seed |
| `arm_extension` | `arms` | ipsf_absolute measured seed |
| `line` | (무투영 — zoom 미방출) | collective 전신 criterion (joint_keys 빈 튜플) — 특정 부위 카드 오도 |
| `dimension_overall_fallback` · 기타 미등록 id | (무투영 — zoom 미방출) | 29-04 앱 무투영 결정과 정합 |

region 멤버 keypoint (앱 `REGION_MEMBER_KEYPOINTS` deductionLabels.ts:90-96 미러):
- `legs` = left_hip, right_hip, left_knee, right_knee
- `arms` = left_shoulder, right_shoulder, left_hand, right_hand

**29-04 수용 기준:** 앱 helper(projectDeductionRecordKeypoints) 매핑의 id 키·region 값이 위 표와 동일해야 record 행 ↔ zoom 카드 드릴다운 매칭(result.tsx:962-974, REGION_MEMBER_KEYPOINTS 교집합)이 성립. 불일치 = D-08 실패.

## 수행 내역

### Task 1 — Wave 0 RED 테스트 (commit 639a940)

기존 mode3 zoom 테스트 확인: `grep -rln "mode3_fault_zoom\|_build_mode3_fault_zoom" backend/tests/` → **없음** (29-VALIDATION Wave 0 지시대로 확인) → `backend/tests/test_mode3_fault_zoom_selection.py` 신설 (plan files 명세와 동일 파일명, 238줄).

9 test functions, 전부 mock-based (`_render_fault_zoom` monkeypatch 캡처 + `_s3` stub + `_FRAME_EXTRACTOR` stub — 실 S3/렌더 0):

1. 케이스 1 (record→region 소스): `leg_extension`→legs 멤버 / `arm_extension`→arms 멤버 / `split_angle`→legs / 같은 region 중복 record dedupe 1장 — 4 함수
2. 케이스 2 (improved 억제): score 개선 입력에서도 kinds 값 == {'deficit'} 뿐
3. 케이스 3 (record 0 → 카드 0): breakdown 부재 / records 빈 리스트 — 2 함수 (score 변화가 있어도 미호출 = 소스 완전 폐기 단언)
4. 케이스 4 (비매핑 → 카드 0): `line` + `dimension_overall_fallback` 뿐 → 미호출
5. 케이스 5 (인자 보존): dtw_match sentinel passthrough + dtw_ref_fps == `_pipeline_frame_fps()` + cached_user_frames

RED 확인: 8 FAIL / 1 PASS (케이스 1/2/4 전부 FAIL — plan 명세 충족, pytest 종료코드 1).

### Task 2 — 대상 선택 소스 교체 (commit d431c43)

`backend/functions/pipeline/app.py`:

- 모듈 상수 `_MODE3_ZOOM_CRITERION_REGION` (위 표) + `_MODE3_ZOOM_REGION_MEMBERS` (앱 미러) 신설 — 주석에 29-PLAN-REVIEW HIGH-1 (DeductionRecord keypoint 필드 부재) + line 무투영 의도 명시
- `_build_mode3_fault_zoom_comparisons`: `curr_scores/prev_scores/common/change_joints/kinds(improved|worsened)` 산출 제거 → records criterion→region 파생 (dedupe + top-2 상한), `kinds = {j: "deficit"}`. regions 빈 리스트 → 조기 return (S3 다운로드 전) + `# 29-CONTEXT D-08 — 감점 record 없으면 zoom 카드 없음 = 의도된 동작` 주석
- `_render_fault_zoom` 호출부: 대상(fault_joints)·kinds 만 교체 — dtw_match=dtw_match / dtw_ref_fps=_pipeline_frame_fps() / cached_user_frames 등 나머지 인자 그대로 (28-05/CR-01)
- `_joint_scores` 헬퍼 제거 (mode3 빌더 단독 사용처 — dead code)
- 에러 격리: 기존 구조 유지 — 빌더 예외는 `_run_deferred_fault_zoom` 의 try/except(log.warning → failed 마킹, 분석 비차단)가 흡수 (신규 표면 0)

## 검증 결과

- `pytest tests/test_mode3_fault_zoom_selection.py -q` — **9/9 PASS** (RED→GREEN)
- fault_zoom 테스트 5파일 직접 실행 (`tests/*fault_zoom*.py`) — **82/82 PASS** (mode1 zoom·28-05 경로 무회귀). `-k fault_zoom` 전체 수집은 pre-existing collection error 12파일(imageio 등 로컬 미설치)로 Interrupted — 파일 직접 실행으로 동등 커버
- `pytest tests/pipeline -q` — 15 FAIL / 1 PASS: **base commit app.py 원복 후 동일 커맨드 실행, FAILED 세트 diff = 0 (byte-동일)** — 전부 pre-existing 환경 실패 (29-02 SUMMARY 기록과 동일 15건), 내 변경 기인 신규 실패 0
- seam 회귀: `test_pipeline_deduction_seam.py + test_mode3_tally_seam.py + test_pipeline_mode3.py` — 66/66 PASS
- `grep '"improved"' backend/functions/pipeline/app.py` — **0건** (mode3 빌더 내부 포함 파일 전체 0)
- `grep -c leg_extension backend/functions/pipeline/app.py` — 4건 (매핑 상수 + 주석)
- `git diff fault_zoom.py` — **0** (렌더러 무접촉)

## Deviations from Plan

None — plan 그대로 실행. (케이스 3 테스트에 score-변화 입력을 함께 넣어 "breakdown 부재면 score 델타가 있어도 미방출"로 단언을 강화한 것은 plan 케이스 3 의 상위집합.)

## Known Stubs

없음 — 이 plan 산출물에 stub/placeholder 0.

## Threat Flags

없음 — 신규 네트워크/인증/파일 접근 표면 0. T-29-03-01(mode1 zoom 회귀)=fault_zoom 테스트 82 green + fault_zoom.py diff 0 으로 mitigate. T-29-03-02(zoom 예외로 분석 실패)=기존 `_run_deferred_fault_zoom` graceful 격리 유지 + regions 조기 return 으로 mitigate. 패키지 설치 0.

## 참고 사항

- **production 미노출:** Pod 는 구코드 유지 — 실 PNG 재생성 확인은 29-05 Pod sweep 산출물 검사 + 29-08 HUMAN-UAT 적립 (plan verification 절).
- mode3 zoom 카드의 `z.region` 값('legs'/'arms')은 fault_zoom 기존 region 카드 경로(_group_fault_joints)가 세팅 — 앱은 `REGION_MEMBER_KEYPOINTS[z.region]` 교집합으로 매칭하므로 backend 멤버 상수와 앱 상수가 미러 관계 (본 SUMMARY 표가 대조 근거).

## Commits

| Task | Commit | 내용 |
|------|--------|------|
| 1 | 639a940 | test(29-03): add failing mode3 zoom criterion-source tests (RED) |
| 2 | d431c43 | feat(29-03): mode3 zoom source = deduction record criterion->region |

## Self-Check: PASSED

- backend/tests/test_mode3_fault_zoom_selection.py 존재 확인
- 커밋 639a940 / d431c43 존재 확인
- working tree clean (spikes __pycache__ 테스트 부산물 원복)

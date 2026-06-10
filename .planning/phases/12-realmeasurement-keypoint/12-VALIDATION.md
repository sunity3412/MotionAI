# Phase 12 — Validation Seed (Nyquist task-ID)

**Generated:** 2026-06-10 (planner)
**Status:** Seed only — verifier 가 Phase 12 종료 시 PASS / FAIL 박제.

> `workflow.nyquist_validation = true` (`.planning/config.json:20`) — 본 파일 박제 필수.
> Phase 9 의 09-VERIFICATION.md 와 동일 구조 mirror.

## Source Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | Wave |
|--------|----------|-----------|-------------------|------|
| FEED-01 | `kismam.assess(user_angles=, reference_angles=)` 3 call site wiring fix — `JointAssessment.current_angle != None` + `target_angle != None` | unit (backend) | `pytest backend/tests/phase12/test_kismam_assess_with_angles.py -x` | 0 |
| FEED-01 | `assemble.build_joints` 가 모든 8 angle key 의 currentAngle / targetAngle 채움 | unit (backend) | `pytest backend/tests/phase12/test_build_joints_with_real_angles.py -x` | 0 |
| FEED-01 | `pipeline._process` 의 3 call site (mode1/mode3_first/mode3_progress) 정합 + build_keypoint_report 호출 | integration (backend) | `pytest backend/tests/phase12/test_assemble_wiring_all_joints.py -x` | 0 |
| FEED-01 | `KeypointReport.__post_init__` validator (data length = T × J × 2 / confidence = T × J / reliability = T / reliability item ∈ {high,medium,low}) | unit (backend) | `pytest backend/tests/phase12/test_keypoint_report_dataclass.py -x` | 0 |
| FEED-01 | 3-way schema lockstep — TS interface + Python dataclass + docs §9.12 박제 | unit (backend) | `pytest backend/tests/phase12/test_keypoint_report_lockstep.py -x` | 0 |
| FEED-01 | `_dataclass_to_camel_case_dict(KeypointReport(...))` snake → camel 변환 정합 (Phase 9 패턴 mirror) | unit (backend) | `pytest backend/tests/phase12/test_dataclass_to_camel_case_dict_phase12.py -x` | 0 |
| FEED-01 | `firestore_admin._validate_keypoint_report` scoped validator 박제 + `complete_analysis(..., keypoint_report=...)` kwarg | unit (backend) | `pytest backend/tests/phase12/test_firestore_lockstep_phase12.py -x` | 0 |
| VIS-01 | `userAnalyses.ts::normalize` 가 result.keypointReport 필드 null-guard 통과 (구 doc / 신 doc) | type-check (frontend) | `cd app && npm run typecheck` | 0 |
| VIS-01 | 결과 화면 6 영역 순서 (점수 → 영상+오버레이 → 원인 카드 → 차원 → 각도 → 성장 차트) | manual UAT | belle 검수 (Figma frame01 1:1) | 1 |
| VIS-01 | ForcePatternCard 0/1/2/3 finding edge case 정확한 카드 수 렌더 | manual UAT | belle 검수 (mode1/mode3 fixture) | 1 |
| VIS-01 | ForcePatternDetailModal BottomSheet tap → open / close 정상 | manual UAT | belle 검수 | 1 |
| VIS-01 | KeypointOverlay useEvent timeUpdate 동기화 + frame index lookup | manual UAT | belle 검수 (iOS TestFlight 빌드 12) | 2 |
| VIS-01 | delta ≥ 10° joint brand 강조 + floating "N°" 라벨 | manual UAT | belle 검수 (mode1 정은지 vs 사용자 1건) | 2 |
| VIS-01 | confidence < 0.5 frame 의 "추정 N°" + ⓘ 표기 | manual UAT | belle 검수 (occlusion 영상 fixture) | 2 |
| VIS-01 | reliability == 'low' 비율 ≥ 20% 차원 카드 ⚠ amber badge | manual UAT | belle 검수 | 2 |
| VIS-01 | 토글 디폴트 ON + AsyncStorage persist + 깜빡임 0 (Pitfall 6) | manual UAT | belle 검수 (iOS TestFlight) | 2 |

## Phase 12 SC → Wave 매핑 (ROADMAP §Phase 12)

| SC ID | 박제 본문 | Wave / Task |
|---|---|---|
| SC #1 | 결과 화면 angleGuide 가 백엔드 실측 currentAngle 표시 (fixture 아님) | Wave 0A T2 (kismam wiring fix per R4) + Wave 1 T4 (enrichJoints 시뮬 주석 제거) |
| SC #2 | 각 관절이 "현재 N° → 기준 M°" 형태로 현재값 + 기준값 표시 | Wave 1 T4 (각도 가이드 영역) |
| SC #3 | 데이터 계약 (`analysis.ts` ↔ `models.py` ↔ `assemble.py`) lockstep | Wave 0B T1 (single atomic commit per D-09-U1 mirror — 9 필드 incl. axisData per R2/R10) |
| SC #4 | 영상 위 어깨/골반/무릎/손 + 중심축 오버레이 (발끝 toe v2) | Wave 0A T4 (axisData polyline via compute_axis_frames per R2) + Wave 0B T1 (axisData flat in KeypointReport) + Wave 1 T1 (KeypointOverlay 8 keypoint + axis polyline) + Wave 2 T1 (useEvent 동기화) |

## Phase 12 D-12-* Decision Coverage

| Decision | Wave / Task | Status |
|---|---|---|
| D-12-A1 | Wave 1 T4 (6 영역 순서) | Pending |
| D-12-A2 | Wave 1 T4 (779줄 구조 유지) | Pending |
| D-12-A3 | Wave 0/1/2 atomic commit per task | Pending |
| D-12-A4 | Wave 1 T1/T2/T3 (3 신영역 component 분리) | Pending |
| D-12-B1 | Wave 1 T2 (finding[0] big + finding[1..2] small) | Pending |
| D-12-B2 | Wave 1 T2 (canned KO 직접 표시) | Pending |
| D-12-B3 | Wave 1 T3 + T4 (tap → modal) | Pending |
| D-12-B4 | Wave 1 T2/T3 (mode 자동 분기, UI 분기 코드 0) | Pending |
| D-12-C1 | Wave 1 T4 (mode1 split / mode3 single) | Pending |
| D-12-C2 | Wave 0A T1 (RTMW 2D 8 body keypoint) + Wave 0A T4 (axisData polyline R2) + Wave 0B T1 (KeypointReport 8 + axisData) + Wave 1 T1 (KeypointOverlay 8 keypoint + axis polyline) | Pending |
| D-12-C3 | Wave 2 T1 (KEYPOINT_DELTA_HIGHLIGHT_DEG = 10.0 + brand 강조) | Pending |
| D-12-C4 | Wave 2 T2 (토글 디폴트 ON + AsyncStorage) | Pending |
| D-12-C5 | Wave 1 T1 (react-native-svg) + Wave 2 T1 (expo-video timeUpdate) | Pending |
| D-12-D1 | Wave 2 T3 (저신뢰 추정 N° + ⓘ) | Pending |
| D-12-D2 | Wave 2 T3 (⚠ amber badge) | Pending |
| D-12-D3 | Wave 2 T3 (finding confidence 시각 바) | Pending |
| D-12-E1 | Wave 0A T2 (kismam wiring fix R4) + Wave 0A T3 (TargetSource enum R4) + Wave 0B T1 (build_keypoint_report wiring 전수) | Pending |
| D-12-E2 | Wave 0B T1 (3-way contract lockstep + KeypointReport 9 필드 incl. axisData R10) | Pending |
| D-12-E3 | Wave 0B T1 (Firestore flat scoped validator + axisData per R2) | Pending |
| D-12-U1 | Wave 0A T6 (12-00 single atomic commit per R1/R2/R4) + Wave 0B T1 (12-01 single atomic commit per Phase 9 D-09-U1 mirror) + Wave 1 T3 (Phase 12.5 시각 언어 mirror) | Pending |
| D-12-U2 | Wave 2 T4 (manual UAT + typecheck — frontend test infra deferred per A5) | Pending |
| D-12-U3 | Wave 1 T2/T3/T4 + Wave 2 T3 (mode 분기 자동화 — UI 분기 코드 최소) | Pending |
| D-12-U4 | Wave 1 T5 + Wave 2 T4 (light theme only) | Pending |
| D-12-U5 | Wave 1 T1 + 모든 Wave (브랜드 #FF4B33 토큰 only) | Pending |
| D-12-U6 | Wave 0 T1 (build_keypoint_report None fallback) + Wave 1 T1 (KeypointOverlay null fallback) + Wave 1 T4 (placeholder) | Pending |

## Sampling Rate

- **Per task commit:** `cd app && npm run typecheck && pytest backend/tests/phase12/ -x -q`
- **Per wave merge:** `pytest backend/tests/ -x -q` (전 phase regression 0)
- **Phase gate:** 전 backend pytest green + `cd app && npm run typecheck` clean + Wave 2 T4 belle UAT approved + 12-deferred-items.md 박제

## Verification Status

| Wave | Status | Verified By | Date |
|---|---|---|---|
| 0 | Pending | — | — |
| 1 | Pending | — | — |
| 2 | Pending | — | — |
| Phase 12 종료 | Pending | — | — |

---
*Phase 12 추가: 2026-06-10 (planner) — Phase 9 09-VERIFICATION.md 패턴 mirror. 모든 D-12-* / SC 박제.*
</content>
</invoke>
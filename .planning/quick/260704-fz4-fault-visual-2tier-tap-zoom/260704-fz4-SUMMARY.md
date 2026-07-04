---
phase: quick-260704-fz4
plan: 01
subsystem: analysis-result-ui + fault-zoom-backend
tags: [2tier-visual-language, advisory-tier, fault-zoom, angle-meaning-labels, inline-zoom]
requires:
  - quick-260702-sic (fault_zoom region grouping / 프레임 override / 신뢰도 폴백 인프라)
  - quick-260702-q8q (measuredEvidence 편차표 / deductionLabels 단일 출처)
provides:
  - backend tier(confirmed/advisory) 카드 방출 + select_advisory_joints 순수 헬퍼
  - 앱 2단 시각 언어 (표 · 스켈레톤 마커 · 확대 카드 3면 동일 소스)
  - 편차행 탭 → 시트 내 인라인 부위 확대 + 8관절 각도 의미 라벨
affects:
  - result.faultZoomComparisons (tier 필드 추가 — legacy 부재=confirmed 취급)
tech-stack:
  added: []
  patterns:
    - "tier scalar 방출 (region 선례 동일 — contract.md 섹션 없음, TS 주석 + Python 방출부 주석 lockstep)"
    - "confirmed/attention keypoint set 단일 조립 (result.tsx) → 표/마커/카드 공유"
key-files:
  created: []
  modified:
    - backend/shared/python/sunity_shared/analysis/fault_zoom.py
    - backend/functions/pipeline/app.py
    - backend/tests/test_fault_zoom.py
    - app/src/types/analysis.ts
    - app/src/theme/colors.ts
    - app/src/lib/deductionLabels.ts
    - app/src/components/KeypointOverlay.tsx
    - app/src/components/FaultZoomCompare.tsx
    - app/src/components/ForcePatternDetailModal.tsx
    - app/src/app/analysis/result.tsx
decisions:
  - "주황 톤 = warnAmber(#E6A300) 계열 alias (advisoryOrange/advisoryOrangeBg) — 기존 occlusion/부상경고 amber 와 '주의' 의미론 일관 (Claude's Discretion 행사)"
  - "행 탭 인터랙션 = 시트 내 인라인 확장 (스크롤/포커스 방식 대비 컨텍스트 단절 없음, belle 아이디어에 직접 부합)"
  - "원값(내 X°/기준 Y°) 기본 노출 유지 — 측정값이 분석 시점 저장 결정 수치임을 보여주는 신뢰 장치"
  - "advisory item 은 kind 미방출 — grouping 용 내부 전달일 뿐, 캡션 소유권은 tier"
  - "highlightKeypoints 소스를 vetoFaultJoints 단독 → confirmedKeypoints(감점 records ∪ vetoFaultJoints) 로 확장 — 표·마커·카드 단일 소스 (plan key_link)"
  - "hip 각 의미 라벨 '다리 벌림' 유지 — skeleton.JOINT_ANGLES 확인 결과 어깨-엉덩이-무릎(몸통-허벅지) 각으로 스플릿 개방 의미 정합"
metrics:
  duration: ~40m
  completed: 2026-07-04
---

# Quick 260704-fz4: 결함 시각 언어 2단화 + 편차행 탭 확대 + 각도 의미 라벨 Summary

**One-liner:** backend 가 측정 초과 관절에 tier='advisory' 확대 카드(zoom_adv_ S3 키, 채점 무접촉)를 추가 방출하고, 앱이 빨강(확정 감점)/주황(측정 초과·감점 아님) 2단 시각 언어를 편차표·스켈레톤 마커·확대 카드 3면에 동일 소스(confirmedKeypoints/attentionKeypoints 단일 조립)로 적용 + 편차행 탭 인라인 부위 확대 + 8관절 의미 라벨.

## Tasks

| Task | 내용 | Commit |
|------|------|--------|
| 1 | backend advisory tier 카드 (select_advisory_joints + _render_fault_zoom tier 방출 + _attach 배선) | eb70f3e |
| 2 | app 2단 시각 언어 (tier 타입/토큰/의미사전/역매핑/마커/카드 배지) | 82fa249 |
| 3 | 편차행 tier 색 + 의미 라벨 + 행 탭 인라인 확대 | b3be3c7 |

## 검증 결과

- backend: `python3 -m pytest tests/test_fault_zoom.py -q` — **20 passed** (기존 15개 무수정 PASS + select_advisory_joints 신규 5건: 임계 strict >20°/확정 제외/내림차순+cap/음수 abs/비유한 skip).
- app: `npm run typecheck` — GREEN.
- 채점 무접촉 증명: `git diff 2be3de0..HEAD --name-only` 에 dimensions.py/kismam.py/deduction_engine/vision_veto 없음 (fault_zoom + pipeline 카드 방출부 + 앱 표시 계층만).
- 하위호환: tier/windowMedianAngleDeltas 부재 legacy → advisory 카드 0장, KeypointOverlay attentionKeypoints prop 미전달 시 렌더 diff 0, Mode3 `_attach_mode3_fault_zoom` 무수정 (tier='confirmed' scalar 만 추가 — 앱 캡션 로직 kind 우선 무변화), Phase 9 일반 finding 시트(measuredEvidence undefined) 렌더 diff 0.
- 신규 튜닝 상수 0: 20° = backend `dimensions._LINE_TOL_DEG` / 앱 `KEYPOINT_DELTA_HIGHLIGHT_DEG` 재사용 (양쪽 정합 주석). 하드코딩 색 0 (advisoryOrange/advisoryOrangeBg 토큰만, warnAmber alias).

## 구현 노트

- **advisory 선별**: `select_advisory_joints(kp_deltas, confirmed, tol, max_items=2)` — 이름공간 무지 순수 함수 (kismam→keypoint 매핑은 pipeline `_KISMAM_TO_KEYPOINT` 책임). docstring 에 위양성 교훈([[window-median-silent-seed-fp-reverted]]) 박제: 표시 전용, 채점 입력 금지.
- **advisory 카드 생성**: `_render_fault_zoom` 이 프레임 추출 1회 재사용 + `build_fault_zoom_comparisons` 2회 호출 (확정 배치 무수정 / advisory 배치 joint_kinds='deficit' 로 양어깨→arms 1장 grouping 활성). S3 키 `zoom_adv_{joint}.png` 분리. advisory 는 Mode1 + veto applied(windowMedianAngleDeltas 존재)에서만 생성.
- **단일 소스 조립** (result.tsx): `confirmedKeypoints` = deductionBreakdown records 의 `angle_vs_reference__{jk}` 관절 ∪ vetoFaultJoints. `attentionKeypoints` = wmad 초과 − confirmed. 로컬 중복 맵 `ANGLE_KEY_TO_KEYPOINT` 제거 → `KEYPOINT_FROM_ANGLE_KEY`(deductionLabels) 단일 출처로 통합.
- **의미 라벨 기하 검증**: skeleton.JOINT_ANGLES 확인 — elbow(어깨-팔꿈치-손목)=팔꿈치 굽힘, shoulder(팔꿈치-어깨-엉덩이)=겨드랑이 벌림, hip(어깨-엉덩이-무릎)=다리 벌림(몸통-허벅지 각, 스플릿 개방), knee(엉덩이-무릎-발목)=무릎 굽힘. 라벨 전부 기하 정합.

## Deviations from Plan

None — plan executed exactly as written. (Task 2.4 의 highlightKeypoints 소스 확장은 plan key_link "confirmed/attention keypoint set 단일 조립 후 highlightKeypoints/attentionKeypoints prop" 명시 사항.)

## 다음 검증 (orchestrator 몫 — Pod/SSH 본 plan 범위 외)

backend 변경분은 **pod 재기동 + 재분석**이 있어야 실카드가 생성된다 (저장된 doc 의 PNG 는 재생성 안 됨). 앱 변경은 JS-only → OTA 가능.

실기기 체크리스트 (kip-up fault 88 영상 재분석 후):
1. 스켈레톤 마커: 다리(확정)=빨강 유지 + 어깨(측정 초과)=주황 추가, 겹침 없음.
2. 확대 비교 carousel: 확정 카드(양다리) + advisory 카드(어깨, "참고 · 감점 아님" 배지 + "감점은 아니지만 확인해 보세요" 캡션).
3. 실패 원인 상세 시트 편차표: 다리 행=빨강, 어깨 행=주황 + '감점 아님' 칩, 무강조 행 정상.
4. 각 행에 의미 라벨(팔꿈치 굽힘/겨드랑이 벌림/다리 벌림/무릎 굽힘) 표시.
5. 어깨(또는 다리) 행 탭 → 행 아래 [내 영상|기준] 확대 이미지 인라인 + advisory 행은 "측정값 참고용이에요" 캡션. 재탭 닫힘.
6. legacy doc(재분석 전 기존 결과) 열람 시 기존 렌더 그대로 (advisory 0, 크래시 0).

## Self-Check: PASSED

- [x] backend/shared/python/sunity_shared/analysis/fault_zoom.py — select_advisory_joints 존재
- [x] backend/functions/pipeline/app.py — tier/advisory 방출 존재
- [x] app 6개 파일 수정 확인 (git diff --stat 10 files)
- [x] Commits eb70f3e / 82fa249 / b3be3c7 존재 (git log 확인)
- [x] pytest 20 passed / typecheck GREEN

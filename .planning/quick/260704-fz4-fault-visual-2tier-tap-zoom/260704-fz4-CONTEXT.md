# Quick Task 260704-fz4: 결함 시각 언어 2단화 + 편차행 탭 확대 + 각도 의미 라벨 - Context

**Gathered:** 2026-07-04 (belle 실기기 피드백 + 승인 "그대로 진행해줘")
**Status:** E(260704-fwb) 완료 후 착수

<domain>
## Task Boundary

belle 피드백 (TestFlight #27 + OTA, kip-up fault 88 화면):
1. 편차표 원각도(내 168.9°/기준 137.9°)가 정밀해 보이지만 무슨 각인지 이해 불가 — "오 정밀해 보이는데? 이해가 안 간다".
2. 스켈레톤 빨간 마커는 다리 4개뿐인데 텍스트는 어깨 얘기 → "어떻게 읽어야 하지?" (숫자에 약한 스포츠 사용자의 핵심 혼란). 확대 사진도 다리만.
3. belle 아이디어: 강조된 편차 행을 탭하면 그 부위 확대 비교 사진 + 각도 표기.

</domain>

<decisions>
## Implementation Decisions (belle 승인 완료 — locked)

### 2단 시각 언어
- 빨강 = 확정 결함 (감점된 것, deductionBreakdown records 근거)
- 주황/노랑 = 측정 초과·확인 권장 (windowMedianAngleDeltas 중 tol 20° 초과지만 감점 없는 관절) — "감점 아님" 명시
- 표 · 스켈레톤 마커 · 확대 카드 전부 동일 규칙 적용 (마커: 다리=빨강 유지 + 어깨=주황 추가되는 형태)

### 편차행 탭 → 부위 확대
- 확대 비교 카드를 측정 초과 관절에도 생성 (C 작업 fault_zoom 인프라 재사용, backend 카드 생성 확장 필요 — 측정 초과 관절용 카드는 "참고/확인 권장" 라벨)
- 편차표 강조 행 탭 → 해당 부위 확대 카드로 스크롤/포커스 (또는 시트 내 인라인 표시 — 플래너 판단)

### 각도 의미 라벨
- 행마다 관절 각도의 뜻 한 단어 설명 (예: 팔꿈치 굽힘, 겨드랑이 벌림, 다리 벌림)
- 원값 기본 접힘 여부는 플래너/실기기 판단 여지 (Claude's Discretion)

### Claude's Discretion
- 주황 vs 노랑 톤 선택 (theme 토큰 신설 시 정합 주석)
- 탭 인터랙션 세부 (스크롤 vs 인라인)

</decisions>

<specifics>
## Specific Ideas

- 짜맞춤 오해 방지 관점: 측정값은 분석 시점에 저장된 결정적 수치임을 UI 가 자연스럽게 보여주는 것 자체가 신뢰 장치 (2단 구분 = "시스템이 아는 것과 확신하는 것을 구분해서 말한다").
- 관련 인프라: fault_zoom.py (260702-sic 에서 region grouping/신뢰도 폴백/프레임 override 구축), windowMedianAngleDeltas, deductionBreakdown, KeypointOverlay sizeScale (260702-t0v).
- 주의: backend 카드 확장 시 채점 무접촉. "참고" 카드가 확정 결함 카드와 시각적으로 구분돼야 함.

</specifics>

<canonical_refs>
## Canonical References

- .planning/quick/260702-sic-crop-fix-reference-crop-crop/ (fault_zoom 인프라)
- .planning/quick/260702-q8q-x/ (점수 계산 내역/편차표 UI)
- 메모리 window-median-silent-seed-fp-reverted.md (측정 초과 ≠ 확정 결함인 이유 — 감점 금지 근거)

</canonical_refs>

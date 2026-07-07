# Phase 28: 동작 기반 비교 정렬 — DTW 워핑으로 크롭·싱크 해결 - Context

**Gathered:** 2026-07-07
**Status:** Ready for planning

<domain>
## Phase Boundary

두 영상(학생 vs 정은지)의 동작 기반 시간정렬 부재를 한 기능으로 해소 (시나리오 2+6). 2026-07-06 Pod 실측 규명: D2(정은지 fault_zoom 크롭이 비교부위 아닌 곳 확대 — `_matched_ref_frame` 실패 시 시간비례 근사 fallback, fault_zoom.py:850/:855)와 power-spin "자동구간맞춤 싱크 안 맞음"(VideoCompare 절대시계 동기화, drift 보정 283–322)이 **같은 뿌리**. 해법 = 백엔드에 이미 있는 **dtw_match**로 정렬 데이터를 방출하고, 앱 VideoCompare가 정은지 재생을 학생 타임라인에 워핑, fault_zoom 프레임 정합도 같은 정렬 소비. 백엔드(정렬 데이터 방출) + 앱(소비). Phase 22 v1의 시간 앵커 출력과 계약 필드 공유 설계.

</domain>

<decisions>
## Implementation Decisions

### 재생 워핑 방식 (belle 2026-07-07 확정)
- **D-01:** **전역 트림+오프셋 + 구간별 완만한 가변 재생속도** — DTW 경로를 구간별 playbackRate로 변환(스무딩), 배속 클램프 0.5~2배. 중반 템포 차이까지 따라감 (power-spin 실체: 시작점만 맞추면 중반부터 재이탈). expo-video rate API 사용. 키 모멘트 seek 점프 방식은 기각(끊김).

### 정렬 실패 폴백 — 단계형 사다리
- **D-02:** 실패 경우의 수 5가지를 **단계형**으로 수용:
  1. 전역 신뢰 높음 → 풀 워핑 (D-01)
  2. 구간 부분 붕괴(한 프레임 다수 대응 등) 또는 길이 극단 차이(클램프 초과) → **트림+오프셋만** (안전 모드, 가변속도 끔)
  3. 전역 신뢰 낮음(다른 동작/키포인트 품질 저하/반복 모호) → **"기준 동작과 차이가 커 자동 정렬을 껐어요" 안내 + 현행 절대시계** 동기화 유지
- **D-03:** 신뢰도 임계/지표(정규화 DTW distance, 경로 기울기 극단 런, kismam similarity 재사용 여부)는 Claude 재량 — 단 calibration-source-hard-gate 준수(자기 sweep 재보정 금지), 고정 밴드식 임의 수치 금지, 근거 주석 필수.

### fault_zoom 시간비례 근사 (D2 재발 방지)
- **D-04:** fault_zoom의 **시간비례 근사 fallback 제거**. dtw_match 대응 실패 시 정은지 쪽은 **전신 폴백 + "자동 대응 실패" 캡션** — 엉뚱한 부위 확대(오도) 0, 정보 보존. confidence<0.5 전신 폴백 선례(260702-sic)와 일관. 학생 쪽 카드는 유지.

### 기존 분석 소급
- **D-05:** 정렬 데이터는 새 분석부터. **legacy 결과 화면에는 재분석 유도 배너** — "다시 분석하면 자동 구간 맞춤이 적용돼요" 취지로 재업로드/재분석 유도 (Pod 비용은 사용자가 선택할 때만 발생). 배너 문구/위치는 Claude 재량.

### Claude's Discretion
- 정렬 데이터 계약 필드 설계 — 단 **Phase 22 v1 시간 앵커 출력과 상위 호환으로 공유**하도록 (ROADMAP 명시). Firestore flat 규칙(nested-array 금지) 준수.
- 신뢰도 지표/임계(D-03), 워핑 스무딩 세부, 배너 문구/위치(D-05), 안내 카피 톤(기존 "~해요" 체).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 근본 원인 규명 (이 phase의 존재 이유)
- `.planning/ROADMAP.md` Phase 28 섹션 — D2와 싱크 신고의 같은-뿌리 규명 + dtw_match 해법.
- `.planning/PILOT-FEEDBACK-2026-07-06.md` §A3/§D — power-spin 싱크(A3), 비교영상/crop(D1/D2) 원문.

### 백엔드 (정렬 소스)
- `backend/shared/python/sunity_shared/analysis/motiondtw.py` — dtw_match 정본 (Sakoe-Chiba band).
- `backend/shared/python/sunity_shared/analysis/fault_zoom.py` — `_matched_ref_frame`(:850) + 시간비례 근사(:855, D-04 제거 대상).
- `backend/shared/python/sunity_shared/firestore_admin.py` — flat 저장 규칙 (정렬 맵 방출 시).

### 앱 (정렬 소비)
- `app/src/components/VideoCompare.tsx` — 절대시계 동기화 + drift 보정(283–322, D-01 대체 대상).
- `app/src/types/analysis.ts` — 계약 (3-way lockstep).

### Phase 간 조율
- `.planning/phases/22-custom-vlm-finetune/` — Phase 22 v1 시간 앵커 출력과 계약 공유 (상위 호환 설계).
- Phase 27의 27-06(zoom 사후 분리)·27-07(앱 로딩)이 fault_zoom/result 화면을 먼저 수정 예정 — **파일 겹침 조율 필수** (fault_zoom.py, VideoCompare/result 계열, contract.md).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- dtw_match 경로가 이미 파이프라인에 존재 — kismam/temporal 계열이 소비 중. 정렬 맵 방출은 기존 산출물 재사용.
- VideoCompare의 구간맞춤/드리프트 보정 로직 — 워핑 소비의 삽입 지점.
- fault_zoom의 window/DTW 인덱스 페어 선례 (still 페어 260705-h5z — 파이프라인 9fps 인덱스가 정합의 정본).

### Established Patterns
- 계약 optional 필드 + legacy 폴백 (faultZoomStatus/tier 선례). 정렬 필드도 optional — 없으면 현행 동작.
- Firestore nested-array 금지 → 정렬 맵은 flat (예: 인덱스 쌍 평탄화 + 프레임 수 메타).
- 채점 무접촉 원칙 — 이 phase는 **표현/재생 정렬만**, 점수·verdict 절대 불변 (D-03 경계와 동일 정신).

### Integration Points
- 파이프라인 `_process` 산출 → complete_analysis (또는 Phase 27의 사후 업데이트 경로와 조율).
- 앱 result 화면 → VideoCompare props / fault_zoom 카드.

</code_context>

<specifics>
## Specific Ideas

- belle: "너무 다르면 기준 동작과 다르다고 뜨면 된다" — 실패 안내의 기본 톤. 나머지 경우의 수(부분 붕괴/품질 저하/길이 극단/반복 모호)는 단계형 사다리로 수용.
- 배속 클램프 0.5~2배 — 정은지 영상이 부자연스럽게 빨라지거나 느려지지 않는 상한.

</specifics>

<deferred>
## Deferred Ideas

- 키 모멘트 앵커 점프 방식 — 기각 (끊김). 필요 시 후속에서 하이라이트 점프 기능으로 별도 검토.
- 반복 동작(멀티 시도) 자동 분절 — 이번엔 신뢰도 사다리로 안내만, 자동 구간 선택은 후속.
- D4(가로 크게보기 비율) — 별개 실기기 튜닝 트랙 (FULLSCreen_ZOOM 1.35 belle 승인값, 감으로 변경 금지).

</deferred>

---

*Phase: 28-dtw-motion-based-alignment*
*Context gathered: 2026-07-07*

---
phase: 33-result-trust-recovery
plan: 13
subsystem: video-overlay
tags: [a-track, a-6, d-13, keypoint-overlay, voice-cue, two-way-match, phrasebook, goal-first]

# Dependency graph
requires:
  - phase: 33-result-trust-recovery (33-11, A-4)
    provides: belle 확인 ① 승인 확정 규칙 (상태전이 3단계, 항목 단위 그룹 마커, 어휘 게이트, 목표-선행 문형)
  - phase: 33-result-trust-recovery (33-12, A-5)
    provides: criterion-keyed join (projectDeductionRecordKeypoints / matchZoomForDeductionRecord 단일 출처)
  - phase: 33-result-trust-recovery (33-09, A-2)
    provides: phrasebook 동작 전용 entry 54건 (목표-선행 개정의 대상 데이터)
  - phase: 33-result-trust-recovery (33-08, A-1)
    provides: 동작별 완성 기준 검증 claim (목표 문장의 사실 원천)
provides:
  - "키포인트 스켈레톤 기본 숨김 + 옵트인 (KeypointOverlay.skeletonVisible — 마커 레이어와 분리, D-13)"
  - "영상 위 마커 양방향 대응 강제 — record 보유 doc 의 빨강 마커 = buildDeductionMarkers 투영 한정, 고아 마커 미렌더 (D-18)"
  - "항목 단위 그룹 마커 = 부위 경계 타원 (멤버 실좌표 bounding, 승인 목업 ① mkg) + 번호 배지"
  - "재생바 틱 탭 = 동기 seek + 감점 항목 열기 (VideoCompare.onTickPress — 드릴다운 진입점 4)"
  - "대표 UX 패턴: 음성 큐 시작 → 정지 + dim + 부위 경계 강조, 종료 → 재개 (기존 100ms tick 재사용, 신규 타이머 0)"
  - "phrasebook 동작 전용 cueLine 54건 목표-선행 문형 + 화면 어휘 게이트 (screenVocabularyGate 데이터 + 테스트 핀)"
affects: [33-14, 33-15, 33-16]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "스켈레톤/마커 레이어 분리 — 설명 없는 표시(추적 점)는 옵트인, 스스로 답하는 표시(record 양방향 마커)는 상시"
    - "발화-동기 재생 제어 — didJustFinish 이벤트 플래그(isCueSpeaking)를 기존 tick 이 폴링, 사용자 개입 시 홀드 즉시 해제"
    - "화면 어휘 게이트 = 어휘 목록 데이터(_meta.screenVocabularyGate) + pytest 핀 (동작·항목 무관 공통)"

key-files:
  created: []
  modified:
    - app/src/components/KeypointOverlay.tsx
    - app/src/components/VideoCompare.tsx
    - app/src/app/analysis/result.tsx
    - app/src/lib/audioCue.ts
    - backend/data/phrasebook.json
    - backend/tests/phase33/test_phrasebook_motion_specific.py

key-decisions:
  - "스켈레톤 숨김 시 저신뢰 관절 위 마커도 미렌더 — 확신 없는 표시는 긋지 않는다 (33-11 원칙 계승)"
  - "음성 큐 정지는 발화 실제 시작(started=true)일 때만 — 캐시 미스/짝 없는 큐는 자막만 (D-18 고아 가드)"
  - "정지 안전 상한 15s — mp3 종료 이벤트 유실 시 강제 재개 (영구 멈춤 차단)"
  - "phrasebook 목표-선행 개정을 Rule 2 편입으로 이 플랜에서 수행 (A-6 지시 메모 계약 — 33-12 stamp_ref 선례)"
  - "목표 문장 = 33-A1 검증 claim 만, __common__ 은 목표 문장 없음 (일반론 목표 fabrication 금지 — fail-closed)"

# Metrics
duration: 25분 (2026-07-29 02:40~03:05 UTC)
completed: 2026-07-29
---

# Phase 33 Plan 13: A-6 영상 위 표시 구현 Summary

**영상 위 모든 표시가 스스로 답하거나 사라지게 만들었다 — 키포인트 12점은 기본 숨김+옵트인, 빨강 마커는 record 양방향 대응 부위 경계(고아 미렌더), 재생바 틱은 눌러서 그 항목으로, 음성 큐는 정지+부위 강조+재개(대표 UX 패턴) — 여기에 A-6 데이터 계약(phrasebook 목표-선행 + 화면 어휘 게이트)을 편입**

## W2 표 대조 (belle 의문 3개의 해소 지점)

| 표시 | 해야 할 것 (W2) | 구현 |
|---|---|---|
| 키포인트 점 12개 | 기본 숨김 + 필요 시 켜기 | `skeletonVisible` 분리 — 흰 점·bone·축 polyline 기본 숨김, 기존 토글(AsyncStorage `'true'` 옵트인)로 켬. 감점 마커는 상시 |
| 영상 위 붉은 표시 | "여기—무엇—이렇게" 한 덩어리 | 마커 = record 투영 부위 경계(여기) + 탭 → 드릴다운 시트(무엇+이렇게, statusLine·whyLine·cueLine) + 그 순간 자막(목표-선행 cueLine). 짝 없는 마커 미렌더 |
| 재생 바 마커 ①② | 지적 항목임을 밝히고 누르면 이동 | 틱 번호 = 내역 행 번호(단일 소스). 탭 = 동기 seek + `onTickPress` → 해당 감점 항목 시트 오픈 (전체화면은 close 선행) |
| 음성 안내 | 시작 시 정지+부위 강조, 끝나면 재생 | `speakCue` 시작 성공 시 양쪽 pause + dim + record 부위 경계 강조 + "음성 중 — 잠시 멈춤" pill, `didJustFinish` 로 재개 |
| "적용 중입니다" | 멈춘 상태에서 적용 → 적용 후 재생 | `markOffsetApplying` 이 조작 시작 시 정지, 홀드 타이머 종료 시 재개 (원래 정지였으면 개입 0) |

## Task별 구현

### Task 1 — 키포인트 기본 숨김 + 마커 양방향 + 틱 점프 (`fda716d`)

- KeypointOverlay: `skeletonVisible`(default true — 기존 소비처 무회귀) 신설. false 면 축·bone·비마커 원·저신뢰 원 미렌더. 그룹 마커 = 멤버 centroid 1점 → **부위 경계 타원**(고신뢰 멤버 실좌표 bounding + 번호 배지, 승인 목업 ① mkg. 유효 멤버 0 = 자동 생략). 참고(advisory) 점 = 채움 없는 점선 원 (목업 "점선 = 참고").
- result.tsx: record 보유 doc 의 `highlightKeypoints` = `markerBackedKeypoints`(번호 점 관절 ∪ 그룹 멤버 — buildDeductionMarkers 단일 소스)로 한정. `jointAngles` 폴백 강조·`forceHighlightWorstCount` 차단 → **고아 빨강 마커 0** (legacy doc 은 기존 폴백 보존). 토글 영속 반전: 저장 `'true'` 일 때만 켬 (신규 기본 = 숨김).
- VideoCompare: 틱 탭 = `seekBoth` + `onTickPress(첫 번호)` → `openRecordByNumber` (전체화면은 `closeFullscreen` 선행 — iOS 중첩 Modal 회피, 범례 관례 동일).

### Task 2 — 음성 큐 정지 + 부위 강조 + 재개 (`780deab`)

- audioCue: `speakCue` 가 시작 여부 boolean 반환 + `playbackStatusUpdate(didJustFinish)` 이벤트 기반 `isCueSpeaking()` (버퍼링 중 `player.playing=false` 오판 관통).
- VideoCompare: 큐 전환 시 발화 시작 성공이면 양쪽 pause + `voiceCueRecordId` 를 overlay render prop opts 로 전달. 기존 100ms tick 이 종료 판정(신규 타이머 0) — 종료/15s 상한 시 자동 재개. 사용자 정지·재생·seek·scrub 개입 = 홀드 즉시 해제(자동 재개 억제). "음성 중 — 잠시 멈춤" 상태 pill 1줄 (D-05 허용 한도 내 유일한 신규 카피), 자막 3줄 허용(목표-선행 큐 잘림 방지).
- result.tsx: `focusKeypointsForRecordId` — cue recordId → `projectDeductionRecordKeypoints`(마커·크롭과 동일 규칙 1벌) → KeypointOverlay `focusKeypoints` (dim 0.34 + 부위 경계 강조, 승인 목업 ④ 컷 2). IN-01 역립 저신뢰 시 부위 단정 강조 억제.

### 편입 — A-6 데이터 수정 (`0f7cf70`, Deviations 참조)

- phrasebook 동작 전용 cueLine 54건 전부 목표-선행 문형: `"목표는 {동작별 목표}. {기존 행동 큐}"`. 목표 문장 = 33-A1 ① 완성 기준의 **검증 claim 만** (UNVERIFIED 좌우 라벨·척추 아치 곡률 미사용 — 33-09 원칙 계승). power-spin = belle 4R 승인 원문("목표는 폴을 따라 위아래 한 줄 스플릿이에요.").
- 화면 어휘 게이트: 국면·신전·재신전·완성도 → 강사 화법 풀어쓰기 (전용 23슬롯 + `__common__` 10슬롯). **방향·사실 주장 byte-불변** — 어휘만 교체 (33-09 방향 게이트 통과분 보존).
- `_meta.screenVocabularyGate`(어휘 목록 데이터 운용) + `goalFirstCueLine` 규칙 박제 + 테스트 핀 2건 (어휘 게이트 전수 + 목표-선행 전수).

## 검증 결과 (수치)

- **app**: `npm run typecheck` (tsc --noEmit) clean — Task 1·2 각각 + 최종 재확인.
- **backend pytest**: phase32 전체 **191 passed** / phase33 전체 **66 passed** (신규 게이트 2건 포함) — **신규 깨짐 0**. phase32/33 밖 phrasebook 소비 테스트 없음(grep 확인).
- **채점 무접촉 (D-20/D-29)**: 변경 파일 6개 전부 계획/편입 범위 — dimensions/kismam/motiondtw/deduction_engine/fault_zoom/technique grep 0. phrasebook.py 코드 byte-무변경(데이터+테스트만).
- **금지어·수치 게이트**: 렌더 카피 수치 0, % 0, 천장 0 (기존 게이트 전수 재통과).
- **Pod 무접촉**: 실분석/Pod 호출 0 (재검증 스위프 직렬 진행 보호 — 검증 전부 로컬).

## 10동작 일반화 성립 (blocking anti-pattern 대조)

동작명 하드코딩: **app diff 0건** (`power.spin|foxtop|kip.up|...` grep 0). 모든 신규 규칙의 키잉 데이터:

- 마커/강조 부위 = `projectDeductionRecordKeypoints(record, faultJoints)` — record criterion·source(doc 데이터) 키잉, 등재 10동작 + mode3 공통
- 그룹 경계 = 멤버 keypoint 실좌표 bounding (동작 무관 기하)
- 음성 정지/강조 = cue `recordId`(records 출생) — 짝 있는 큐만 발동
- 목표 문장 = 동작별 **데이터**(phrasebook entry 값 — 코드 분기 0), 33-A1 표 키잉. `__common__`(미등재 동작) = 목표 문장 없음(fail-closed)
- 어휘 게이트 = `_meta` 어휘 목록 데이터 (동작·항목 무관 공통)

## Deviations from Plan

**1. [Rule 2 - 승인 계약 편입] phrasebook 목표-선행 + 화면 어휘 게이트 (A-6 데이터 수정)**
- **Found during:** 플랜 로드 시 (mockups/index.html ⑤ A-6 행 + 33-11-SUMMARY A-6 입력 목록 대조)
- **Issue:** 플랜 문면은 app-only 이나, belle 확인 ① 확정 규칙이 "phrasebook cueLine 목표-선행 개정 = A-6(33-13) 데이터 수정"과 "화면 어휘 게이트"를 이 플랜 소비 항목으로 명시 — 미구현 시 승인 계약 위반 (33-12 의 stamp_ref 편입 선례와 동일 구조). 오케스트레이터 제약도 "(해당 시) backend pytest"로 데이터 수정을 상정
- **Fix:** 데이터+테스트만 수정 (phrasebook.py 코드 0, 채점 0). 방향 주장 불변·검증 claim 한정·fail-closed — 33-09 방법론 그대로. phase32/33 스위트 전수 green
- **Files modified:** backend/data/phrasebook.json, backend/tests/phase33/test_phrasebook_motion_specific.py
- **Commit:** 0f7cf70

**2. [범위 내 판단] 스켈레톤/마커 레이어 분리 해석**
- 플랜 문면 "Make KeypointOverlay hidden by default"를 문자 그대로(오버레이 전체 숨김) 적용하면 승인 목업 ①(기본 화면 = 항목 그룹 마커 3개 상시)과 모순 — 승인 설계를 상위 계약으로 보고 **스켈레톤만 기본 숨김, record 양방향 마커는 상시**로 구현. must_haves 의 "no unexplained 12 dots"(추적 점)와 "red marker answers itself or is not rendered"(마커) 분리 취지와 정합.

**Total deviations:** 1 Rule 2 편입, 1 해석 결정

## 무엇을 열어서 확인했는가 (D-19) — 33-16 시뮬레이터 예약 항목

이번 플랜에서 직접 연 것: phrasebook 개정 전/후 전 entry 값 덤프(치환 흔적 2곳 발견·교정 포함), pytest 게이트 출력, 승인 목업 ①·④ 실물(마커·상태전이 시각 규칙 원본), grep 검증 전수. **타이밍·인터랙션 동작의 실검증은 코드로 불가** — 아래 시퀀스를 33-16 페이즈 게이트에서 시뮬레이터 녹화로 확인한다 (OTA 전, D-21). "typecheck passed"는 이 확인을 대체하지 않는다:

1. **음성 큐 상태전이**: 재생 중 → 큐 시작(영상 정지 + dim + 해당 부위 경계 강조 + "음성 중 — 잠시 멈춤" pill + 목표-선행 자막) → 음성 종료(강조 해제 + 자동 재개). 오디오 토글 off 시 = 자막만·멈춤 없음.
2. **키포인트 기본 숨김**: 첫 진입 시 흰 점 12개 없음 + 항목 그룹 경계 마커만 → 토글 on 시 스켈레톤 등장 → 재진입 시 영속.
3. **그룹 경계 마커**: 다리(4관절) 그룹이 관절원 나열이 아닌 부위 경계 타원 + 번호 배지로 보이는지, 저신뢰 프레임에서 자동 생략되는지.
4. **재생바 틱 탭**: seek + 해당 감점 항목 시트 오픈 (세로 카드), 전체화면에서는 닫힘 → 시트.
5. **오프셋 "적용중입니다"**: 조작 시 멈춤 → 적용 후 재생.
6. **목표-선행 자막 3줄**: 긴 큐 잘림 없는지 (신규 mp3 는 재분석 후 — 기존 doc 은 구 음성+구 자막).

## 틀리면 걸리는 장치 (D-18)

- 고아 마커: record 보유 doc 의 highlight 소스가 markerBackedKeypoints 한정 — 짝 없는 관절은 렌더 경로 자체가 없음. 짝 없는 큐: `started=false` → 멈춤·강조 미발동.
- 어휘 재유입: `test_screen_vocabulary_gate` (entries+safetyEntries+failClosed 전수, 어휘 목록 = 데이터).
- 목표-선행 이탈: `test_motion_specific_cueline_goal_first` (전용 cueLine 전수 핀).
- 영구 멈춤: CUE_PAUSE_MAX_MS 15s 강제 재개.

## Deferred (이 플랜 밖 — 소속 명시)

- **초 표기 라벨 문형** ("감점 부분"·"(감점 유지된 채 마무리)" 계열, 괄호 보조설명 = 브랜드 컬러) — 증거 컷 스트립/상세 시트 표면은 33-15(Wave B, DeductionDetailSheet) 소관. A-6 지시 메모의 해당 행을 33-15 입력으로 이관.
- 신규 목표-선행 cueLine 의 Polly mp3 는 **재분석 시점 합성** — 기존 doc 은 구 음성·구 자막 유지 (33-09 와 동일 의도된 하위호환). 33-16 재분석 후 신형 확인.
- 시뮬레이터 렌더 확인 = 33-16 (플랜 verification 자체가 이연 명시).

## Known Stubs

없음 — placeholder/빈 데이터 배선 0. 모든 신규 표면은 기존 저장값(records·cueWindows·keypointReport)에 배선됨.

## Threat Flags

없음 — 신규 네트워크 표면·인증 경로·스키마 변경 0 (T-33-47 two-way match 완화 = 이번 구현이 강제, T-33-48 render crash = normalize+tsc 기존 장치 유지, 신규 패키지 0).

## Task Commits

1. **Task 1: 키포인트 기본 숨김 + 마커 양방향 + 틱 점프** — `fda716d` (feat)
2. **Task 2: 음성 큐 정지 + 부위 강조 + 재개** — `780deab` (feat)
3. **편입: phrasebook 목표-선행 + 어휘 게이트** — `0f7cf70` (feat, Rule 2)

## Next Phase Readiness

- **33-14 (A-7 일러스트)** — 목표-선행 cueLine 확정으로 "그림 = 교정 방향" 대조 원천 갱신됨. 음성 시점 일러스트 슬롯(④-b)은 음성 정지 상태(voiceCueRecordId)와 결합 가능.
- **33-15 (Wave B)** — 초 표기 라벨 문형 입력 이관 (위 Deferred).
- **33-16 (페이즈 게이트)** — 위 시뮬레이터 예약 6항목 + 재분석 후 신형 cueLine 음성·자막 확인 + OTA 일괄.

## Self-Check: PASSED

- 수정 파일 6개 존재 확인
- 커밋 3건 존재 확인 (fda716d, 780deab, 0f7cf70)
- 코드 앵커 존재: skeletonVisible/focusKeypoints(KeypointOverlay), onTickPress/isCueSpeaking(VideoCompare), markerBackedKeypoints(result.tsx), screenVocabularyGate(phrasebook.json)

---
*Phase: 33-result-trust-recovery*
*Completed: 2026-07-29*

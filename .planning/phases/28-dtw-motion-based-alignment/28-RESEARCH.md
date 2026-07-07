# Phase 28: 동작 기반 비교 정렬 (DTW 워핑으로 크롭·싱크 해결) - Research

**Researched:** 2026-07-07
**Domain:** 백엔드 DTW 정렬 데이터 방출 (Python/numpy) + 앱 재생 워핑 소비 (expo-video, React Native)
**Confidence:** HIGH (코드베이스 실증 기반) / MEDIUM (expo-video rate 변경 반응성 — 공식 문서에 지연 명세 없음, 실기기 검증 필요)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**재생 워핑 방식 (belle 2026-07-07 확정)**
- **D-01:** **전역 트림+오프셋 + 구간별 완만한 가변 재생속도** — DTW 경로를 구간별 playbackRate로 변환(스무딩), 배속 클램프 0.5~2배. 중반 템포 차이까지 따라감 (power-spin 실체: 시작점만 맞추면 중반부터 재이탈). expo-video rate API 사용. 키 모멘트 seek 점프 방식은 기각(끊김).

**정렬 실패 폴백 — 단계형 사다리**
- **D-02:** 실패 경우의 수 5가지를 **단계형**으로 수용:
  1. 전역 신뢰 높음 → 풀 워핑 (D-01)
  2. 구간 부분 붕괴(한 프레임 다수 대응 등) 또는 길이 극단 차이(클램프 초과) → **트림+오프셋만** (안전 모드, 가변속도 끔)
  3. 전역 신뢰 낮음(다른 동작/키포인트 품질 저하/반복 모호) → **"기준 동작과 차이가 커 자동 정렬을 껐어요" 안내 + 현행 절대시계** 동기화 유지
- **D-03:** 신뢰도 임계/지표(정규화 DTW distance, 경로 기울기 극단 런, kismam similarity 재사용 여부)는 Claude 재량 — 단 calibration-source-hard-gate 준수(자기 sweep 재보정 금지), 고정 밴드식 임의 수치 금지, 근거 주석 필수.

**fault_zoom 시간비례 근사 (D2 재발 방지)**
- **D-04:** fault_zoom의 **시간비례 근사 fallback 제거**. dtw_match 대응 실패 시 정은지 쪽은 **전신 폴백 + "자동 대응 실패" 캡션** — 엉뚱한 부위 확대(오도) 0, 정보 보존. confidence<0.5 전신 폴백 선례(260702-sic)와 일관. 학생 쪽 카드는 유지.

**기존 분석 소급**
- **D-05:** 정렬 데이터는 새 분석부터. **legacy 결과 화면에는 재분석 유도 배너** — "다시 분석하면 자동 구간 맞춤이 적용돼요" 취지로 재업로드/재분석 유도 (Pod 비용은 사용자가 선택할 때만 발생). 배너 문구/위치는 Claude 재량.

### Claude's Discretion
- 정렬 데이터 계약 필드 설계 — 단 **Phase 22 v1 시간 앵커 출력과 상위 호환으로 공유**하도록 (ROADMAP 명시). Firestore flat 규칙(nested-array 금지) 준수.
- 신뢰도 지표/임계(D-03), 워핑 스무딩 세부, 배너 문구/위치(D-05), 안내 카피 톤(기존 "~해요" 체).

### Deferred Ideas (OUT OF SCOPE)
- 키 모멘트 앵커 점프 방식 — 기각 (끊김). 필요 시 후속에서 하이라이트 점프 기능으로 별도 검토.
- 반복 동작(멀티 시도) 자동 분절 — 이번엔 신뢰도 사다리로 안내만, 자동 구간 선택은 후속.
- D4(가로 크게보기 비율) — 별개 실기기 튜닝 트랙 (FULLSCREEN_ZOOM 1.35 belle 승인값, 감으로 변경 금지).
</user_constraints>

## Summary

이 phase는 신규 알고리즘이 아니라 **이미 계산되는 산출물의 방출과 소비**다. mode1 파이프라인은 이미 `motion_dtw(user@9fps, ref)` 로 `MotionMatch(start, end, distance, path)` 를 계산해 `reference_dtw_match` 로 들고 있다 (`app.py:3307-3310`). 이걸 (a) 앱이 소비할 정렬 맵(초 단위 앵커)으로 변환해 `complete_analysis` 의 result 에 optional 필드로 방출하고, (b) 앱 VideoCompare 가 기존 100ms drift-보정 tick 의 목표값을 `cR ≈ cL` 에서 `cR ≈ warp(cL)` 로 바꾸고 정은지 player 의 playbackRate 를 구간 기울기로 설정하며, (c) fault_zoom 의 시간비례 근사(:855)를 전신 폴백+캡션으로 교체하면 된다.

**이 리서치의 최대 발견 (D2 의 추가 근본 원인, 계약 설계를 좌우함):** 사용자 angles 는 9fps(파이프라인 `FfmpegFrameExtractor` 기본값)인데, **활성 reference 11개의 angles 는 phase4_v1 재처리 때 `--target-fps 18.0` 으로 생성됐다** (`backfill_reference_downstream.py:131` 주석 명시, `reprocess_reference_motions_phase4.py:427` default 18.0). 따라서 dtw path 의 ref 인덱스는 **18fps 공간**인데, `_matched_ref_frame` 은 이를 9fps frames 배열 인덱스로 해석·클램프한다 (`fault_zoom.py:250-268` docstring 의 "ref 9fps 절대" 가정이 stale). DTW "성공" 시에도 정은지 프레임이 의도 시점의 **2배 시간**(또는 후반부 클램프)으로 잡힌다 — D2 의 "엉뚱한 부위 확대" 는 근사 폴백만의 문제가 아니다. **결론: 정렬 맵은 프레임 인덱스가 아니라 초(seconds) 로 방출하고, 변환 시 각 측의 실제 fps 메타를 명시적으로 사용해야 한다.**

신뢰도 사다리(D-03)는 새 지표를 발명할 필요가 없다. `vision_veto.assess_alignment_confidence` 가 이미 프로덕션에서 정규화 DTW distance 임계 (`_ALIGN_GLOBAL_T1=8.0`, `_ALIGN_GLOBAL_T2=25.0`) + 로컬 path 밀도로 3단 채택(single/window_union/low_alignment_confidence)을 하고 있다 (`vision_veto.py:913-983`). 이 상수를 재사용하면 자기-sweep 재보정 없이(calibration-source-hard-gate 충족) 사다리 3단을 가를 수 있고, 클램프 0.5~2배는 belle 고정값이라 구간 판정의 구조적 기준이 된다.

**Primary recommendation:** 백엔드는 `reference_dtw_match` 를 **초 단위 앵커 배열 + tier + 메타**(flat, ~수십 float)로 변환하는 순수 함수를 만들어 `complete_analysis` result 에 `motionAlignment` 로 방출 (Phase 27-06 의 "complete 후 result.* 쓰기 금지" 게이트와 충돌하지 않게 **complete 시점에 실어라**). 앱은 VideoCompare 의 기존 tick/seekBoth 를 warp 함수 경유로 바꾸고 rate 는 앵커 구간 기울기(클램프)로 설정. fault_zoom 은 fps 도메인 변환을 명시하고 근사 폴백을 전신 폴백+캡션 플래그로 교체.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| DTW 정렬 맵 산출(경로→앵커 변환, tier 판정) | Backend (pipeline `_process`, 순수 함수) | — | dtw_match 가 백엔드에만 존재. 순수 numpy — 채점 코어와 동일 규율 |
| 정렬 데이터 영속화 | Backend (firestore_admin) | Firestore | flat 규칙 + scoped validator 선례. complete_analysis 페이로드에 동승 |
| 재생 워핑(rate/seek 제어) | App (VideoCompare.tsx) | — | player 인스턴스와 tick 루프가 앱에 있음. 백엔드는 데이터만 |
| 워핑 수학(앵커 보간, 구간 rate) | App (순수 TS 모듈, 신규 `lib/alignmentWarp.ts` 권장) | Backend (앵커 생성 순수 함수) | 보간은 소비측 책임 — 백엔드는 rate 를 굽지 않는다(스무딩 정책 앱 교체 가능) |
| fault_zoom 프레임 대응(D-04) | Backend (fault_zoom.py) | — | PNG 렌더가 서버에서 일어남. 캡션 플래그만 계약으로 앱에 전달 |
| 재분석 유도 배너(D-05) | App (result.tsx) | — | legacy 판정 = 계약 필드 부재. 기존 "다시 분석하기" 라우팅 재사용 |

## Standard Stack

### Core (전부 기존 — 신규 설치 0)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | >=1.26 (기존) | 앵커 추출/기울기 계산 순수 함수 | 분석 코어 유일 의존 원칙 (`analysis/` 규율) [VERIFIED: 코드베이스 backend/requirements] |
| expo-video | ~3.0.16 (기존) | `playbackRate`(0~16 float, 재생 중 할당 가능), `currentTime` 쓰기 seek, `timeUpdateEventInterval` | 이미 VideoCompare 의 player. expo-av 는 deprecated — 사용 금지 [CITED: docs.expo.dev/versions/v54.0.0/sdk/video/] |
| firebase-admin | >=6,<7 (기존) | Firestore 저장 | 기존 complete_analysis 경로 [VERIFIED: 코드베이스] |
| pytest | >=8,<9 (기존) | 백엔드 unit | backend/requirements-dev.txt [VERIFIED: 코드베이스] |

**Installation:** 없음 — 이 phase 는 외부 패키지를 설치하지 않는다.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| playbackRate 구간 가변 | 키 모멘트 seek 점프 | **기각됨 (D-01, 끊김)** — 재검토 금지 |
| 앵커+앱측 보간 | 백엔드가 rate 세그먼트 직접 방출 | rate 를 백엔드가 구우면 스무딩 정책 변경마다 재분석 필요 + Phase 22 앵커와 계약 이질화 — 비권장 |
| 기존 tick 폴링(100ms) 확장 | `useEvent(player,'timeUpdate')` 신규 구독 | tick 이 이미 drift 보정의 단일 지점(283–350) — 새 이벤트 채널 추가는 이중 제어 위험. 기존 tick 확장 권장 |

## Package Legitimacy Audit

이 phase 는 외부 패키지를 설치하지 않는다 (기존 의존만 사용). slopcheck 대상 없음.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
[학생 영상 S3] ──> pipeline _process (RunPod GPU)
                     │  frames@9fps → RTMW → angles(user)@9fps
                     │  ref doc: angles(ref)@18fps (phase4_v1)  ←── [Firestore reference/{id}]
                     ▼
              _deviation_against ──> reference_dtw_match = MotionMatch(start,end,distance,path)
                     │                     path = [(user_local_idx@9fps, ref_idx@18fps)...]
                     ├──(기존 소비 1: per_joint_deviation → 채점 — 절대 무접촉)
                     ├──(기존 소비 2: fault_zoom._matched_ref_frame → zoom 카드 [D-04 대상])
                     ├──(기존 소비 3: assess_alignment_confidence → veto 프레임 채택 [무접촉])
                     │
                     └──[신규] build_motion_alignment(match, user_fps=9.0, ref_fps=ref_meta)
                             │   순수 함수: path → 초 단위 앵커 + tier 판정 (D-02/D-03)
                             ▼
              complete_analysis(result={..., motionAlignment})   ← 27-06 게이트: complete 후
                     │                                              result.* 추가 write 금지 →
                     ▼                                              반드시 complete 에 동승
              [Firestore users/{uid}/analyses/{id}]
                     │ onSnapshot
                     ▼
              result.tsx ──motionAlignment──> VideoCompare
                     │                          ├─ tier=warped: rightPlayer.playbackRate=구간기울기(클램프)
                     │                          │   + tick: |cR − warp(cL)| > 0.2s → 보정 seek
                     │                          ├─ tier=trim_only: rate=1, warp=전역 오프셋만
                     │                          └─ tier=disabled/부재: 현행 절대시계 + 안내/배너(D-05)
                     └─ legacy(필드 부재) → 재분석 유도 배너 → router.replace('/(tabs)/analyze')
```

### Recommended Project Structure (신규/수정 파일)
```
backend/shared/python/sunity_shared/analysis/
├── motion_alignment.py      # [신규] 순수 함수: match→앵커/tier (numpy only, 채점 무접촉)
├── fault_zoom.py            # [수정] _matched_ref_frame fps 도메인 명시 + :855 근사 제거(D-04)
backend/functions/pipeline/app.py         # [수정] EXPERT 분기에서 build_motion_alignment 호출 + result 주입
backend/shared/python/sunity_shared/firestore_admin.py  # [수정] scoped validator (선례 패턴)
backend/tests/test_motion_alignment.py    # [신규] Wave 0
app/src/lib/alignmentWarp.ts              # [신규] 순수 TS: 앵커 보간 warp(t), 구간 rate, 클램프
app/src/components/VideoCompare.tsx       # [수정] alignment prop + tick/seek/rate 워핑
app/src/app/analysis/result.tsx           # [수정] alignment 전달 + legacy 배너(D-05)
app/src/types/analysis.ts + backend models.py + docs/contract.md   # 3-way lockstep
```

### Pattern 1: 정렬 맵 계약 — 초 단위 앵커 + tier (권장안, RQ2 답)

**What:** `result.motionAlignment` (optional) — flat dict:

```
motionAlignment: {
  version: "ma-v1",
  source: "dtw",                      // Phase 22 v1 이 "vlm" 으로 대체/보강 가능 (상위 호환 축)
  tier: "warped" | "trim_only" | "disabled",   // D-02 사다리
  reason?: string,                    // tier 강등 사유 enum (예: "rate_clamp_exceeded" | "low_global_confidence" | "length_extreme")
  anchors: number[],                  // flat [u0,r0, u1,r1, ...] 초 단위 float 쌍. 단조 증가 보장
  anchorCount: number,                // len(anchors)/2 (reshape 메타 — anglesFrames 선례)
  distance: number,                   // 정규화 DTW distance (배지 수치용, Phase 20 A4 TODO 해소)
}
```

**Why seconds, not frame indices (핵심 근거):**
1. **fps 도메인 함정 차단** — user angles 9fps vs ref angles 18fps (아래 Pitfall 1). 인덱스로 방출하면 소비자 전원이 양측 fps 를 알아야 함. 초로 방출하면 `player.currentTime`(초) 와 도메인 일치 — 앱 소비 즉시 가능.
2. **Firestore 40k index-entry 안전** — 앵커를 학생 타임라인 0.5s 간격으로 다운샘플하면 10~30s 영상에서 40~120 float (~240 index entries). 전체 path 평탄화(≤ (n+m)×2 ≈ 1,000+ float)와 달리 **index 면제 운영 작업이 불필요** ([[analyses-index-exemption-fix]]: analyses 에 새 대형 배열 추가 시 gcloud 면제를 owner 계정으로 별도 실행해야 하는 repo-외부 운영 스텝이 생김 — 회피가 정답).
3. **Phase 22 v1 상위 호환** — 22-01 의 REPORT_KEYS 에 `time_anchors`(결함 프레임/타임스탬프) + `segments`(sub-action 구간) 가 이미 확정 (22-01-PLAN.md:83). VLM 산출 시간 앵커도 (학생초, 기준초) 쌍으로 사상 가능 → `source: "vlm"` 교체만으로 같은 계약 소비. rate 세그먼트 방출(옵션 c)은 VLM 앵커와 이질적이라 탈락.
4. **nested-array 금지 자동 충족** — flat float 배열 + scalar 메타 ([[firestore-nested-array-flat]]).

**옵션 비교 (RQ2):**
| 옵션 | 크기 (20s 영상) | index 면제 | 앱 소비 | Phase 22 호환 | 판정 |
|------|----------------|-----------|---------|--------------|------|
| (a) 전체 쌍 평탄화 | ~1,000-1,800 float | **필요 (운영 스텝)** | reshape+fps 지식 필요 | 낮음 (raw path) | 탈락 |
| (b) 앵커 N개 + 선형보간 | 40~120 float | 불필요 | interp 한 함수 | **높음 (time_anchors 동형)** | **채택** |
| (c) rate 세그먼트 | ~30 float | 불필요 | 최소 | 낮음 (rate 는 파생물) | 탈락 (스무딩 정책 소성) |

**앵커 생성 규칙 (백엔드 순수 함수):** path 를 학생초 균일 간격(예: 0.5s)으로 샘플 — 각 학생 시각에서 대응 ref 인덱스들의 **median** (1:N 안정화 — `_matched_ref_frame` 의 기존 median 선례 재사용) → `rSec = median_ref_idx / ref_fps`. 전역 트림 = 첫/끝 앵커가 내장 (match.start/end 반영). 앵커 단조성 강제(비단조 쌍 제거) — warp 역전 방지.

### Pattern 2: D-03 신뢰도 사다리 — 기존 산출물만으로 (RQ4 답)

**새 계산 없이 가능한 지표 (전부 이미 존재):**

| 지표 | 출처 | 상태 |
|------|------|------|
| 정규화 DTW distance | `match.distance` (`motiondtw.py:69` — 누적비용/(n+m)) | 이미 계산됨 |
| 경로 기울기 극단 런 (1:N 대응) | `match.path` 에서 순수 함수로 도출 (같은 u 에 연속 대응된 r 개수 최대 런) | path 이미 존재, O(len(path)) 파생 |
| 구간 기울기 vs 클램프 | 앵커 쌍 차분: (rᵢ₊₁−rᵢ)/(uᵢ₊₁−uᵢ) ∈ [0.5, 2.0]? | 앵커에서 파생 |
| kismam similarity (angle_dim) | mode1 에서 이미 계산, <25 는 `NotPoleMotionError` 로 분석 자체가 실패 (`models.py:372`) | 정렬 코드에 도달하는 doc 은 전부 ≥25 — **추가 게이트로서의 정보량 낮음, 미채용 권장** |

**임계 근거 (calibration-source-hard-gate 준수 방법):**
- **재사용:** `vision_veto.py:913-916` 의 `_ALIGN_GLOBAL_T1 = 8.0` / `_ALIGN_GLOBAL_T2 = 25.0` — 이미 프로덕션에서 같은 `match.distance` 로 프레임 채택 3단(single/window_union/low_alignment_confidence)을 가르는 검증된 상수. **자기 sweep 재보정이 아니라 기존 프로덕션 임계의 재사용**이므로 게이트 통과. 주석에 출처(vision_veto H4) 명시 필수.
- **구조적 기준:** 클램프 0.5~2.0 은 belle 고정값(specifics) — "스무딩 후 어떤 구간 기울기라도 클램프 밖" = tier 2 강등은 임의 수치가 아니라 D-01 의 논리적 귀결.
- **사다리 매핑 (권장):**
  - `tier=warped`: distance ≤ 8.0 AND 전 구간 기울기 ∈ [0.5, 2.0] (스무딩 후)
  - `tier=trim_only`: distance ≤ 25.0 이지만 (기울기 클램프 위반 OR 극단 런 존재 OR 전체 길이비 클램프 밖)
  - `tier=disabled`: distance > 25.0 → "기준 동작과 차이가 커 자동 정렬을 껐어요" + 현행 절대시계
- 기존 fixture (정은지 성공/실패 페어, power-spin)로 **관찰 검증**(threshold 이동 금지)만 수행 — sweep 결과로 임계를 움직이면 circular (금지).

### Pattern 3: VideoCompare 워핑 — master-slave + 기존 tick 확장 (RQ3 답)

**현행 구조 (실측):** 두 `useVideoPlayer` 인스턴스(left=학생, right=정은지), 100ms `setInterval` tick 이 (1) currentTime 폴링, (2) `|cL−cR| > 0.2s` 면 느린 쪽 시각으로 back-seek (283–325), (3) 짧은 쪽 종료 시 동시 pause. `seekBoth(t)` 는 양쪽 동일 시각 seek, `togglePlay` 는 시작 강제 sync. 전부 **절대시계 전제** — 이것이 A3 싱크 신고의 원인.

**최소 변경 워핑 설계 (권장):**
1. **학생(left) = master, 시계 불변** — 타임라인/틱/스크럽 전부 현행 그대로 학생 기준. timelineTicks 의 frame 도메인도 학생이라 무변경.
2. `warp(tStudent) → tRef`: `alignmentWarp.ts` 순수 함수 — 앵커 이진탐색 + 구간 선형보간, 범위 밖은 기울기 1.0 연장(오프셋 연속) — 특수분기 없이 매끄러움.
3. **rate = feedforward, seek = feedback (이중 제어):** 구간 진입 시 `rightPlayer.playbackRate = clamp(구간기울기, 0.5, 2.0)`, tick 마다 `|cR − warp(cL)| > 0.2s` 면 `rightPlayer.currentTime = warp(cL)` — 기존 DRIFT_CORRECT_THRESHOLD_S 재사용. **expo-video 가 rate 변경 지연을 문서화하지 않으므로**(아래 State of the Art) rate 만 믿지 말고 기존 보정 seek 을 안전망으로 유지 — 이 조합이면 rate 반응이 늦어도 동기는 지켜진다.
4. `seekBoth(t)`: left=t, right=warp(t). `togglePlay` 시작 sync 도 warp 경유. 종료 판정: 비교 기준 = 학생 duration 과 warp 정의역의 min.
5. tier=trim_only: 앵커를 [첫 앵커, 끝 앵커] 2개로 축약 소비 (rate=전역 단일값 또는 1.0 + 오프셋) — 같은 warp 코드 경로. tier=disabled/필드 부재: 현행 코드 그대로 (optional prop, faultZoomStatus/tier 선례의 legacy 폴백 패턴).
6. 스무딩: 백엔드 앵커 간격(0.5s)이 이미 1차 스무딩. 앱에서 rate 를 앵커 구간 단위로만 바꾸면(초당 최대 2회) "완만한 가변"(D-01) 충족. rate 변경 빈도를 더 낮추려면 인접 구간 기울기 차 < ε 이면 rate 유지 (Claude 재량 세부).

**expo-video 확인 사항 (SDK 54 공식 docs):**
- `playbackRate`: "Float value between 0 and 16.0", 기본 1.0, 직접 할당 가능, 변경 시 `playbackRateChange` 이벤트. Android/iOS/tvOS/Web 지원 [CITED: docs.expo.dev/versions/v54.0.0/sdk/video/].
- `preservesPitch` 기본 true — **본 앱 player 는 `muted=true`** 라 피치 무관 [VERIFIED: VideoCompare.tsx:212].
- `currentTime` 쓰기 = seek, "frame accurate seeking may incur additional decoding delay" — 잦은 보정 seek 은 stutter 위험 → threshold 0.2s 유지가 적절 [CITED: 동일 docs].
- rate 변경의 지연/플랫폼 차는 **문서에 없음** → 실기기 manual 검증 항목 (Validation Architecture).

### Pattern 4: D-04 — fault_zoom 근사 제거 + fps 정합 (RQ1/RQ5 답)

**dtw_match 산출물 실체 (RQ1):** `MotionMatch` frozen dataclass — `start`/`end`(학생 9fps angles 구간), `distance`(정규화), `path`([(user_local, ref_idx)] — user_local 은 구간-로컬, ref_idx 는 **ref angles 인덱스 = 18fps 공간**). mode1 에서 `_deviation_against` (app.py:3307) 1회 계산 후 `reference_dtw_match` 로 4곳에 전달: per_joint_deviation(채점), segments(technique extension), `_build_selected_frame_pair`(veto still, app.py:1720), `_attach_fault_zoom_comparisons`(app.py:4005). **정렬 맵 재사용에 추가 DTW 계산 불필요** — 변환(인덱스→초)만 필요.

**`_matched_ref_frame` 실패 조건 (실측):**
1. `dtw_match is None` — mode3 전체, 또는 EXPERT 분기 예외 시.
2. `user_frame` 이 `[start, end)` 밖 — DTW path 는 구간 내 모든 user 인덱스를 커버하므로(경로 연속성), **js 가 비는 유일한 실질 조건은 worst 프레임이 매칭 구간 밖**일 때. 단 mode1 은 현재 user 9fps 프레임 수 ≤ ref 18fps 프레임 수인 경우가 대부분이라 `find_action_segment` 가 (0, nu) 전체를 반환 → start=0, end=nu → **구간 밖 실패는 드묾**.
3. **"성공"이 틀리는 경우 (진짜 D2 메커니즘):** 반환된 ref_idx 는 18fps 공간인데 9fps frames 배열에 그대로 인덱싱 → 시간 2배 오독, `ref_n-1` 클램프로 후반부는 마지막 프레임 고정. — **D-04 작업 시 근사 제거만으로는 D2 가 안 잡힌다. fps 변환(ref_idx / ref_fps × frames_fps)을 함께 명시해야 한다.**

**전신 폴백 재사용 가능성:** `_side_crop` 3단 강하(신뢰 crop → relaxed → **좌표 결측=전신 폴백**)가 이미 존재 (fault_zoom.py 819-821 주석, Phase 25-03). D-04 는 대응 실패 시 ref 측을 전신 경로로 강제 + item dict 에 scalar 플래그(예: `refMatch: "failed"`) 추가 → 앱이 "자동 대응 실패" 캡션 렌더 (PNG 에 굽지 말고 계약 필드로 — 카피 수정에 재분석 불필요).

**경계 주의 (채점 무접촉):** `_build_selected_frame_pair`(app.py:1720-1749) 도 `_matched_ref_frame` + ratio 폴백을 쓰지만 이는 **Gemini veto still 입력 = 채점 인접 경로**이고 `ref_match_source: "dtw"|"ratio"` provenance 로 이미 게이트됨 (quick 260705-h5z). **D-04 의 근사 제거는 fault_zoom 표시 경로만** — veto pair 의 ratio 폴백을 건드리면 점수가 움직인다. fps 변환 fix 를 `_matched_ref_frame` 본체에 넣으면 veto still 입력도 바뀜(점수 이동 가능) → **표시 경로 전용 helper 로 분리하거나, 본체 수정 시 Pod eval + belle 통지를 별도 게이트로** (Open Question 2).

### Pattern 5: 방출 지점 — complete_analysis 동승 (Phase 27 조율, RQ6 답)

27-06 Task 2 가 명시 게이트를 박는다: **"complete_analysis 호출 이후 어떤 `result.*` 필드도 write 금지 — `update_analysis_fault_zoom` 만 허용"** (grep 게이트). 정렬 맵은 zoom 렌더와 달리 계산이 즉시(match 변환뿐)이므로 **complete 페이로드에 동승**이 정답 — 사후 업데이트 경로 신설 금지. 앱도 result 도착 즉시 VideoCompare 가 워핑 가능(zoom pending 과 무관).

**파일 겹침 매트릭스 (RQ6):**

| 파일 | Phase 27 | Phase 28 | 충돌 성격 |
|------|----------|----------|----------|
| `backend/functions/pipeline/app.py` | 27-01~06 (4개 plan) — zoom 호출부 이동, Gemini 병렬화, complete 재배열 | EXPERT 분기 alignment 방출 (3310 부근 + complete 직전 result 주입) | **높음** — 27 이 `_process` 후반을 재배열 |
| `app/src/types/analysis.ts` | 27-06 (faultZoomStatus) | motionAlignment + FaultZoomComparison.refMatch | 낮음 (다른 심볼, 인접 영역) |
| `docs/contract.md` | 27-06 | motionAlignment 절 | 낮음 (절 추가) |
| `backend/shared/.../firestore_admin.py` | 27-06 (update_analysis_fault_zoom 신설) | scoped validator 추가 | 낮음 (함수 추가) |
| `app/src/app/analysis/result.tsx` | 27-07 (zoom pending placeholder) + **26-02 (wrapper/child 분리)** | alignment 전달 + 배너 | **중간** — 26-02 분리 시 라인 이동 |
| `backend/shared/.../analysis/fault_zoom.py` | **안 건드림** (27-06 은 app.py 호출부만) | D-04 본체 | 없음 |
| `app/src/components/VideoCompare.tsx` | 안 건드림 | 워핑 본체 | 없음 |

**안전한 착수 순서:** ROADMAP 상 Phase 28 은 "Depends on: 없음"이지만 **app.py/result.tsx 겹침 때문에 Phase 27 (최소 27-06/27-07) 실행 후 착수가 안전**. 병렬 강행 시 27-07 의 선례 패턴 적용: plan 에 "선행 확인" 스텝 — 라인 번호가 아닌 **심볼 기준**(`reference_dtw_match`, `complete_analysis(` 호출부, `selectedZoom`) 재탐색 + 미실행 상태면 orchestrator 보고. fault_zoom.py/VideoCompare.tsx (각 phase 의 본체 작업)는 완전 독립.

### Pattern 6: D-05 legacy 배너 (RQ7 답)

- **legacy 판정:** `result.motionAlignment === undefined` (optional 필드 부재 = legacy — faultZoomStatus/tier 하위호환 선례와 동일 규칙). 두 영상이 모두 있는 비교 카드에서만 의미.
- **삽입 지점:** VideoCompare 에 이미 "자동 구간 맞춤" 정적 배지가 있고 그 주석이 정확히 이 phase 를 예고함 — "실 정렬 신뢰도(DTW 매칭 품질)를 백엔드가 내려주면 배지에 수치/강도 표시. 현재 contract 에 필드 없어 정적" (VideoCompare.tsx:735-757). **alignment 있으면 배지가 tier 별 정직한 카피**(warped/trim_only/disabled 3종, "~해요" 체), **legacy 면 result.tsx 쪽에서 배너** "다시 분석하면 자동 구간 맞춤이 적용돼요" — 배지(컴포넌트 내부)와 배너(재분석 CTA, 화면 레벨)는 책임 분리.
- **재분석 플로우 재사용:** result.tsx:1673-1679 의 "다시 분석하기" 가 이미 `router.replace('/(tabs)/analyze')` — 배너 CTA 도 동일 라우팅. 신규 플로우 0. (Pod 비용은 사용자가 업로드를 선택할 때만 발생 — D-05 정합.)
- **가짜 수치 금지 규율 유지:** 배지에 표기할 수치는 `motionAlignment.distance` 실데이터만 (Phase 20 A4 LIGHT 버전의 "가짜 수치 금지" 주석 준수).

### Anti-Patterns to Avoid
- **프레임 인덱스로 계약 방출** — fps 도메인 함정 (Pitfall 1). 초 단위 강제.
- **complete 후 alignment 사후 write** — 27-06 grep 게이트 위반.
- **rate 만으로 동기 신뢰** — expo-video rate 지연 미문서화. 보정 seek 안전망 필수.
- **매 tick rate 재설정** — playbackRate 를 100ms 마다 쓰면 플랫폼별 재버퍼 위험. 구간 경계에서만 변경.
- **veto still 경로(`_build_selected_frame_pair`) 동시 수정** — 채점 인접. Phase 28 은 표현/재생만 (CONTEXT "채점 무접촉 원칙").
- **자기 sweep 으로 임계 재보정** — calibration-source-hard-gate. vision_veto 상수 재사용 + 관찰 검증만.
- **하드코딩 색/간격으로 배너 구현** — theme 토큰만 (프로젝트 불변).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 두 영상 시간 대응 | 새 정렬 알고리즘/재계산 | `reference_dtw_match` (이미 mode1 에서 계산) | CONTEXT 잠금. 채점과 동일 소스 = 표시-점수 정합 (Phase 19 TRUST-01 정신) |
| 신뢰도 임계 | 새 밴드/수치 발명 | `vision_veto._ALIGN_GLOBAL_T1/T2` (8.0/25.0) 재사용 | 프로덕션 검증 완료 + calibration gate 충족 |
| 1:N path 대응 안정화 | 새 선택 규칙 | median 규칙 (`_matched_ref_frame` 기존) | 검증된 선례, 결정론 |
| 앱 동기 제어 루프 | 새 sync 엔진/이벤트 채널 | 기존 100ms tick + DRIFT_CORRECT_THRESHOLD_S(0.2)/REPLAY_SEEK_DELAY_MS(200) | Build 14→16 에서 UAT 로 다듬어진 상수들 — 교훈 재학습 금지 |
| ref 측 crop 실패 렌더 | 새 폴백 렌더 | `_side_crop` 전신 폴백 (Phase 25-03 3단 강하) | 260702-sic 선례와 일관 (D-04 명시) |
| 재분석 진입 | 새 업로드 플로우 | `router.replace('/(tabs)/analyze')` (result.tsx:1674) | 기존 플로우 재사용 (D-05) |

**Key insight:** 이 phase 의 모든 구성요소(정렬·임계·폴백·동기 루프·재분석)는 코드베이스에 검증된 선례가 있다. 신규성은 오직 "방출 계약 + warp 소비" 두 이음새뿐.

## Common Pitfalls

### Pitfall 1: user 9fps vs reference 18fps — dtw path 의 ref 인덱스 도메인 (최대 함정)
**What goes wrong:** path 의 ref_idx 를 9fps 로 해석하면 정은지 시각이 2배로 튀거나 끝프레임 클램프 — D2 그 자체. 정렬 맵을 인덱스로 방출하면 앱에서도 재발.
**Why it happens:** 파이프라인 학생 추출 = `FfmpegFrameExtractor()` 기본 9fps (frame_extractor.py:20); reference phase4_v1 재처리 = `--target-fps 18.0` 기본값으로 실행됨 (backfill_reference_downstream.py:131 주석 "reprocess... --target-fps 18.0 ('pipeline 정합') 로 생성"; REFERENCE_TARGET_FPS=18.0). `_matched_ref_frame` docstring 의 "ref 9fps 절대" 가정이 stale.
**How to avoid:** (1) 방출은 초 단위 — `rSec = ref_idx / ref_fps`, ref_fps 는 ref doc 의 `keypointReport.fps` (top-level mirror 존재) 또는 `anglesFrames`/영상길이에서 도출, 하드코딩 금지. (2) fault_zoom 은 `ref_idx@ref_fps → 9fps frames idx` 변환을 `_to_rep_idx` 계열 단일 공식으로 명시. (3) **Wave 0 검증:** 실 reference doc 하나의 `anglesFrames / keypointReport.fps ≈ 영상 길이(초)` 확인으로 18fps 가정 실측 (Assumption A1).
**Warning signs:** 정은지 워핑 재생이 학생보다 항상 ~2배 빠름 / 앵커 rSec 이 영상 길이 초과.

### Pitfall 2: analyses 문서에 대형 배열 추가 → 40k index-entry + 면제 운영 스텝
**What goes wrong:** 전체 path 평탄화 방출 시 `complete_analysis` 가 `INDEX_ENTRIES_COUNT_LIMIT_EXCEEDED` 로 실패할 수 있고, 면제는 repo 밖(gcloud, owner 계정 sunity3412) 운영 작업 ([[analyses-index-exemption-fix]]).
**How to avoid:** 앵커 다운샘플 (~120 float 상한) — 면제 불필요 규모. plan 에 앵커 수 상한 명시 + validator 에서 길이 가드.
**Warning signs:** 긴 영상(>60s)에서 저장 실패 로그.

### Pitfall 3: expo-video rate 변경 반응성 미문서화
**What goes wrong:** 구간 경계에서 rate 를 바꿔도 적용 지연이 있으면 그 사이 drift 누적. iOS AVPlayer/Android ExoPlayer 의 rate 적용 시점 차이는 SDK 54 공식 문서에 명세가 없다 [CITED: docs.expo.dev/versions/v54.0.0/sdk/video/ — "No documentation addresses rate change latency"].
**How to avoid:** rate = feedforward + tick 보정 seek = feedback 이중 제어 (Pattern 3). rate 미적용이어도 seek 이 0.2s 내로 잡는다. 실기기 검증 항목으로 승격 (iOS 우선 — TestFlight 파일럿 타깃).
**Warning signs:** 실기기에서 구간 경계마다 화면 순간 점프(=rate 미반영, seek 만 동작).

### Pitfall 4: 근사 폴백 제거 ≠ D2 종결
**What goes wrong:** :855 근사만 지우고 fps 변환을 안 고치면, DTW "성공" 경로가 계속 엉뚱한 프레임을 잡는다 (Pitfall 1의 3번 조건). "D-04 완료" 인데 D2 재발.
**How to avoid:** D-04 plan 에 (a) 근사 제거 + 전신 폴백 + 캡션 플래그, (b) fps 변환 명시 — 두 작업을 한 몸으로. 검증 = power-spin 실페어에서 [학생 worst | 정은지 대응] PNG 육안 (같은 pose 인지).
**Warning signs:** 카드에서 정은지 측이 여전히 다른 동작 순간.

### Pitfall 5: Phase 27 재배열과의 착수 순서
**What goes wrong:** 27-06 이 `_process` 후반(zoom 호출/complete/unlink 순서)을 재배열 — Phase 28 이 라인 번호 기준으로 먼저 들어가면 rebase 충돌 + "complete 후 result.* 금지" 게이트를 모르고 위반 가능.
**How to avoid:** Phase 27 실행 후 착수 (권장). plan 에 27-07 식 "선행 확인" 스텝 + 심볼 기준 탐색. alignment 는 complete 페이로드 동승으로 설계하면 27-06 게이트와 무충돌.

### Pitfall 6: mode3 도메인은 9fps/9fps — mode1 과 변환 규칙이 다름
**What goes wrong:** mode3 second+ 의 prev 비교는 양쪽 다 자기 분석의 9fps angles (`complete_analysis(angles=...)` 저장분) — mode1 용 18fps 변환을 무조건 적용하면 mode3 에서 역으로 틀어짐.
**How to avoid:** 변환 함수가 양측 fps 를 **인자로** 받게 (하드코딩 0). mode3 방출 여부 자체는 Open Question 1.

### Pitfall 7: 스크럽/재시작 경로의 warp 누락
**What goes wrong:** tick 보정만 warp 로 바꾸고 `seekBoth`/`togglePlay` 시작 sync/`restart` 를 절대시계로 남기면, 스크럽 직후 0.2s 초과 drift 로 매 tick 보정 seek 연발 → stutter (Build 16 이 제거한 hysteresis 문제의 재림).
**How to avoid:** right 의 목표 시각을 계산하는 지점을 warp 한 곳으로 단일화 (`targetRefTime(t)` 헬퍼) — tick/seekBoth/togglePlay/restart 전부 경유. 코드리뷰 grep: `rightPlayer.currentTime =` 가 warp 경유 아닌 곳 0.

## Code Examples

### 백엔드 — 앵커 방출 순수 함수 (스케치)
```python
# backend/shared/python/sunity_shared/analysis/motion_alignment.py
# Source: motiondtw.MotionMatch 실계약 + vision_veto._ALIGN_GLOBAL_T1/T2 재사용
# 임계 출처 주석 필수 (D-03 calibration-source-hard-gate):
#   distance 임계 = vision_veto H4 프로덕션 상수 재사용 (자기 sweep 재보정 아님)
#   rate 클램프 = belle 고정 0.5~2.0 (28-CONTEXT specifics)
RATE_MIN, RATE_MAX = 0.5, 2.0
ANCHOR_STEP_S = 0.5          # 학생 타임라인 앵커 간격 — Firestore 크기 상한 근거

def build_motion_alignment(match, *, user_fps: float, ref_fps: float) -> dict | None:
    """MotionMatch → motionAlignment dict (초 단위 앵커 + tier). 순수, 채점 무접촉.
    match None / path 빈 경우 None (필드 미방출 = legacy 동작)."""
    # 1) 학생초 그리드마다 대응 ref_idx 들의 median → rSec = median / ref_fps
    # 2) 단조성 강제 (비단조 앵커 제거)
    # 3) tier: distance ≤ 8.0 AND 전 구간 기울기 ∈ [0.5,2.0] → "warped"
    #          distance ≤ 25.0 → "trim_only" (reason 부여)
    #          else → "disabled"
    ...
```

### 앱 — warp 순수 모듈 (스케치)
```typescript
// app/src/lib/alignmentWarp.ts — 순수 함수만 (player 의존 0, typecheck 가능)
export type MotionAlignment = {
  version: string; source: 'dtw' | 'vlm';
  tier: 'warped' | 'trim_only' | 'disabled';
  reason?: string; anchors: number[]; anchorCount: number; distance: number;
};
export function warpTime(a: MotionAlignment, tStudent: number): number {
  // anchors = [u0,r0,u1,r1,...] 단조. 이진탐색 + 구간 선형보간.
  // 범위 밖은 기울기 1.0 연장 (경계 특수분기 0).
}
export function segmentRate(a: MotionAlignment, tStudent: number): number {
  // 현재 구간 기울기, clamp(0.5, 2.0). tier==='trim_only' 면 1.0 고정.
}
```

### 앱 — VideoCompare tick 수정 지점 (개념)
```typescript
// VideoCompare.tsx tick (현행 315-324 의 |cL-cR| 보정을 대체)
// alignment 없으면(레거시/disabled) 현행 코드 100% 보존 — optional prop 폴백 선례.
const targetR = alignment && alignment.tier !== 'disabled'
  ? warpTime(alignment, cL) : cL;
if (Math.abs(cR - targetR) > DRIFT_CORRECT_THRESHOLD_S) {
  rightPlayer.currentTime = targetR;   // feedback (안전망)
}
// rate 는 tick 아닌 구간 경계에서만: rightPlayer.playbackRate = segmentRate(alignment, cL)
```
[VERIFIED: expo-video SDK 54 — playbackRate 직접 할당·currentTime 쓰기 seek 지원, docs.expo.dev/versions/v54.0.0/sdk/video/]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| expo-av `setRateAsync(rate, shouldCorrectPitch)` | expo-video `player.playbackRate` 직접 할당 + `preservesPitch` prop | expo-av deprecated, SDK 52+ expo-video 안정화 | 2024년 expo-av 자료의 rate API 는 이 앱과 무관 — 사용 금지 (recency mandate) |
| VideoCompare 절대시계 drift 보정 (Build 16) | 동작 기반 warp 목표값 보정 (이 phase) | Phase 28 | 보정 인프라(tick/threshold/seek-delay)는 그대로, 목표값만 교체 |
| fault_zoom 시간비례 근사 (:855, "DTW 미threading MVP" 주석) | DTW 대응 + 실패 시 전신 폴백 (D-04) | Phase 28 | 근사 주석 자체가 "held pose 가정 MVP" 임을 자인 — 설계 의도대로의 승격 |
| 정적 "자동 구간 맞춤" 배지 (Phase 20 A4 LIGHT) | tier/distance 실데이터 배지 | Phase 28 | 배지 TODO(deferred-backend) 의 예정된 해소 |

**Deprecated/outdated:**
- `expo-av`: deprecated — 이 앱은 expo-video ~3.0.16 사용. 웹 검색 시 2024 expo-av 예제 혼입 주의.
- `_matched_ref_frame` docstring 의 "ref_idx = 기준 angles 9fps 절대": phase4_v1 (2026-06-14~15) 18fps 재처리 이후 stale — 이 phase 에서 정정 대상.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 활성 reference 11개의 angles 가 전부 18fps (phase4_v1 기본값 실행) [ASSUMED — 코드/주석 근거는 강하나 live doc 미확인] | Pitfall 1 | 일부가 9fps 면 ref_fps 하드코딩 시 해당 동작만 워핑 틀어짐 → **fps 를 doc 메타에서 읽는 설계면 위험 소멸** (권장안이 이미 방어). Wave 0 에서 1개 doc 실측 |
| A2 | expo-video playbackRate 변경이 iOS/Android 재생 중 유의미한 지연 없이 적용 [ASSUMED — 문서에 지연 명세 부재] | Pattern 3 | 지연 커도 보정 seek 안전망이 동기 유지 — 품질(부드러움)만 저하. 실기기 manual 항목 |
| A3 | 학생 9fps 추출 인덱스/9.0 ≈ 원본 영상 초 (ffmpeg 솎음 근사) [ASSUMED — frame_extractor step 방식상 ±1프레임 오차] | Pattern 1 | 오차 ≤ 0.11s < DRIFT threshold 0.2s — 실질 무해 |
| A4 | power-spin 등 기존 fixture 로 tier 관찰 검증 가능 (Pod 접근 전제) [ASSUMED] | Validation | Pod 불가 시 unit + 실기기만으로 검증 — tier 임계의 실측 근거 약화 (임계 자체는 재사용 상수라 차단 아님) |

## Open Questions (RESOLVED)

1. **mode3 second+ 에도 정렬 방출?** — **RESOLVED: 포함** (28-04 Task 2 — 양측 9fps 저비용 + Phase 29 D1 의존)
   - What we know: CONTEXT 경계는 "학생 vs 정은지"(mode1). 그러나 mode3 도 VideoCompare 로 prev 영상과 비교하고(result.tsx:1291-1295), `_deviation_against` 로 match 를 이미 계산하며(양쪽 9fps — 변환 단순), Phase 29 가 "Mode3 에도 비교영상"(D1) 을 이 phase 산출물에 의존.
   - What's unclear: 이번 scope 포함 여부 (belle 의도는 mode1 우선).
   - Recommendation: 계약/함수는 모드 무관으로 설계(fps 인자화)하되, 방출 배선은 mode1 필수 + mode3 는 저비용이면 동승 — planner 가 plan 분리로 판단. 점수 무접촉이라 리스크 낮음.

2. **`_matched_ref_frame` fps 변환 fix 의 적용 범위** — **RESOLVED: 표시 경로 전용, veto still 경로 제외** (28-05 + 28-VALIDATION 불변 제약, belle 통지 완료 2026-07-07)
   - What we know: 표시(fault_zoom) 경로와 채점 인접(veto still pair, app.py:1720) 경로가 같은 함수를 공유. fps fix 를 본체에 넣으면 veto still 입력이 바뀌어 점수 이동 가능 (Phase 28 은 "점수·verdict 절대 불변").
   - What's unclear: veto still 의 wrong-moment ref 프레임을 알고도 두는 것의 정당성 (별도 정합성 이슈).
   - Recommendation: 이번 phase 는 표시 경로 전용으로 fps 정합 적용(별도 helper 또는 인자). veto 경로 fix 는 발견사항으로 박제하고 belle 에게 별도 트랙(quick/후속) 제안 — silent 점수 변경 금지.

3. **앵커 간격/스무딩 파라미터 (0.5s 권장)** — **RESOLVED: ANCHOR_STEP_S=0.5 상수 확정** (28-02 — 실기기 조정 루프는 28-08 manual 항목)
   - What we know: 간격이 좁을수록 충실, 넓을수록 rate 변경 빈도 감소 + 크기 절감. 0.5s 면 20s 영상 ~80 float.
   - Recommendation: 0.5s 로 시작, 상수화 + 근거 주석. 실기기에서 부자연스러우면 조정 (belle 승인 루프).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 + pytest | 백엔드 unit | ✓ (backend/requirements-dev.txt 관례) | pytest >=8 | — |
| Node/npm + tsc | 앱 typecheck | ✓ (`npm run typecheck` 유일 게이트) | TS ~5.9 | — |
| RunPod Pod (GPU) | 실분석 재실행(관찰 검증, power-spin 페어) | ✓ (Pod svn31pzja7uay0, 2026-07-05 기준 — 재생성 시 proxy URL/Lambda env 동기화 필요) | — | unit fixture 로 대체 (임계 재사용이라 필수 아님) |
| TestFlight 실기기 | 워핑 체감/rate 반응성 manual | ✓ (iOS Build #27 선례, 이번 변경은 OTA 가능 — 신규 native 모듈 0) | — | — |
| 신규 EAS native build | 불필요 | — | — | expo-video 기존 설치분으로 충분 (OTA 배포 가능) |

**Missing dependencies with no fallback:** 없음.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8 (backend) / tsc --noEmit (app — JS 테스트 러너 없음, 프로젝트 관례) |
| Config file | 없음 (관례 실행) |
| Quick run command | `cd /Users/kimtaesung/Dev/SunityMotion/backend && PYTHONPATH=shared/python:. python3 -m pytest tests/test_motion_alignment.py -q` |
| Full suite command | `cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/ -q` (주의: full-suite 에 pre-existing failure ~54건 존재 — STATE.md 박제. affected-tests 스코프 비교로 판정) + `cd app && npm run typecheck` |

### Phase Requirements → Test Map
(공식 REQ ID 미발급 — ROADMAP "Requirements: TBD". 결정 ID 기준 매핑)

| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|-------------|
| D-01/계약 | build_motion_alignment: 앵커 단조·초 단위·결정론(동일 입력 2회 동일 출력)·identity path→기울기 1.0 | unit (순수) | `pytest tests/test_motion_alignment.py -q` | ❌ Wave 0 |
| D-01 fps | user 9fps/ref 18fps 합성 path → rSec = idx/18 정확 (Pitfall 1 회귀 가드) | unit | 동일 파일 | ❌ Wave 0 |
| D-02/D-03 | tier 사다리: distance 8.0/25.0 경계 + 기울기 클램프 위반 → trim_only 강등 (임계 출처 주석 존재 grep) | unit | 동일 파일 + `grep -c "vision_veto\|_ALIGN_GLOBAL" motion_alignment.py` ≥1 | ❌ Wave 0 |
| D-04 | fault_zoom: 시간비례 근사 코드 제거(grep 0) + 대응 실패 시 전신 폴백 + `refMatch` 플래그 방출 | unit | `pytest tests/test_fault_zoom*.py -q -k match` | 기존 파일 확장 |
| 채점 무접촉 | alignment 방출 유무와 무관하게 overallScore/deductionBreakdown 동일 (diff 0) | unit (pipeline mock) | `pytest tests/ -q -k "alignment and score"` | ❌ Wave 0 |
| 계약 | validator: 앵커 길이 상한·flat scalar 강제·3-way lockstep 존재 grep | unit + grep | `grep -c motionAlignment analysis.ts models.py docs/contract.md` 각 ≥1 | ❌ Wave 0 |
| 워핑 수학(앱) | warpTime/segmentRate 순수 함수 — typecheck + (선택) node 스크립트 단언 | typecheck | `cd app && npm run typecheck` | ✓ 명령 존재 |
| D-01 체감 | 실기기: power-spin 페어 워핑 재생 — 중반 템포 추종, rate 경계 stutter 없음, 스크럽 후 동기 유지 | **manual-only** (rate 반응성은 기기 의존 — A2) | — | belle 실기기 |
| D-05 | legacy doc → 배너 노출 + CTA 라우팅 / 신규 doc → 배지 tier 카피 | manual (+typecheck) | — | belle 실기기 |

### Sampling Rate
- **Per task commit:** 해당 신규 테스트 파일 quick run + `npm run typecheck`
- **Per wave merge:** `pytest tests/ -q -k "alignment or fault_zoom or pipeline"` (affected 스코프, 신규 FAILED 0)
- **Phase gate:** affected 스코프 green + typecheck green + 실기기 manual 항목 belle 확인 (human_verify_mode: end-of-phase)

### Wave 0 Gaps
- [ ] `backend/tests/test_motion_alignment.py` — 앵커/tier/fps/결정론/채점무접촉
- [ ] `backend/tests/test_fault_zoom_deferred.py` 또는 신규 — D-04 회귀 가드 (27-06 실행 시 같은 파일 존재 — 조율)
- [ ] reference doc 1개 실측: `anglesFrames / keypointReport.fps ≈ 영상초` (A1 해소 — 스크립트 1회성, Firebase Admin SA 읽기)
- [ ] `app/src/lib/alignmentWarp.ts` 골격 (typecheck 대상 진입)

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | 변경 없음 (기존 Firebase 토큰 경로 그대로) |
| V3 Session Management | no | — |
| V4 Access Control | no | Firestore rules 무변경 — motionAlignment 는 본인 doc result 내부 |
| V5 Input Validation | yes | firestore_admin scoped validator (앵커 길이 상한 + scalar-only + 단조성) — 기존 `_validate_*` 선례 패턴. 앱은 `normalize()` 방어적 소비 (userAnalyses 선례): anchors 비단조/NaN → alignment 무시(legacy 폴백) |
| V6 Cryptography | no | — |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 조작/파손된 alignment 데이터로 앱 크래시 | Tampering/DoS | 앱측 defensive normalize — 형식 위반 시 필드 무시 후 현행 절대시계 폴백 (graceful, 크래시 0) |
| 초대형 anchors 배열 저장 (자원 소모) | DoS | validator 길이 상한 (예: ≤ 512 float) — 백엔드가 유일 writer 라 위험 낮음, 그래도 가드 |

## Project Constraints (from CLAUDE.md)

- 기술 스택 변경 금지 — 신규 라이브러리 도입 없음 (본 리서치 정합).
- Firestore nested-array 금지 → flat + reshape 메타 (계약 설계 반영).
- 시크릿 하드코딩 금지 — 이 phase 는 시크릿 무접촉.
- 브랜드 컬러 #FF4B33/토큰만 — 배너/배지는 theme 토큰 (brandTint 배지 선례).
- 라이트 전용 — 배너는 라이트 (전체화면 dark 는 기존 의도적 예외 영역만).
- 이모지 금지, 한국어 사용자 카피("~해요" 체), 주석에 spec 인용 (`contract.md §`, `28-CONTEXT D-0x`).
- 작은 단위 작업 / 의미있는 테스트만 — 수치 채우기 테스트 금지.
- 계약 3-way lockstep: analysis.ts + models.py(or validator) + docs/contract.md 동시 수정.
- GSD 워크플로 준수, plan.md 업데이트 (작업 완료 시).

## Sources

### Primary (HIGH confidence)
- 코드베이스 실측: `motiondtw.py` (MotionMatch/정규화 distance), `fault_zoom.py:177-268, 772-936` (_to_rep_idx/_matched_ref_frame/근사 폴백/3단 강하), `app.py:1590-1755, 2857-2869, 3160-3340, 3990-4030` (dtw 생산·소비 4경로), `vision_veto.py:913-983` (_ALIGN_* 임계 + 3단 채택), `firestore_admin.py:858-1023` (complete_analysis flat 규율), `VideoCompare.tsx` 전문 (tick/drift/seekBoth/배지), `result.tsx:1286-1295, 1673-1679`, `frame_extractor.py:20` (9fps 기본), `reprocess_reference_motions_phase4.py:427` + `backfill_reference_downstream.py:131,138` (reference 18fps)
- docs.expo.dev/versions/v54.0.0/sdk/video/ — playbackRate/preservesPitch/currentTime/timeUpdateEventInterval (2026-07-07 fetch)
- `.planning/phases/27-1-gemini-analysis-speed-1min/27-06-PLAN.md` / `27-07-PLAN.md` — complete-후 write 금지 게이트, 파일 겹침
- `.planning/phases/22-custom-vlm-finetune/22-01-PLAN.md:83,92` — REPORT_KEYS time_anchors/segments (상위 호환 근거)
- 프로젝트 메모리: [[analyses-index-exemption-fix]], [[firestore-index-entry-limit]], [[d2-crop-and-sync-one-root-motion-alignment]], [[calibration-source-hard-gate]]

### Secondary (MEDIUM confidence)
- `.planning/PILOT-FEEDBACK-2026-07-06.md` §A3/§D — 신고 원문 (belle 전언 기반)

### Tertiary (LOW confidence)
- expo-video rate 변경의 플랫폼별 지연 — 공식 문서 무명세 (실기기 검증으로 해소)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 신규 의존 0, 전부 기존 검증분
- Architecture: HIGH — 모든 이음새가 코드 실측 기반, 선례 존재
- Pitfalls: HIGH (fps 도메인 — 코드/주석 이중 근거) / MEDIUM (A1 live doc 미실측, A2 rate 지연)
- D-03 임계: HIGH — 프로덕션 상수 재사용 (gate 충족 경로 명확)

**Research date:** 2026-07-07
**Valid until:** ~2026-08-06 (안정 영역 — 단 Phase 27 실행 후 app.py/result.tsx 라인 참조는 심볼 기준 재탐색 필요)

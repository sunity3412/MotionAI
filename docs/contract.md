# docs/contract.md — 데이터 계약 (앱 ↔ 백엔드)

> 앱과 백엔드가 주고받는 데이터의 **단일 진실**. 이 문서와 어긋나게 구현 금지.
> 코드 타입(앱): `app/src/types/analysis.ts` — 이 문서와 항상 동기화.
> 근거: backend/CLAUDE.md, ml/CLAUDE.md, design.md §6·§8, 배포된 Firestore 보안 규칙.

---

## 0. 핵심 원칙

```
- 영상은 Lambda를 거치지 않는다. 앱이 S3에 직접 PUT (presigned URL).
- 분석은 비동기. 결과는 Firestore 문서로 전달, 앱이 구독(onSnapshot)한다.
- 사용자 데이터는 users/{uid} 하위로 격리 (배포된 보안 규칙과 일치).
- 모든 점수는 0~100 정수 (KISMAM 정규화, ml/CLAUDE.md).
```

---

## 1. 전체 흐름

```
[앱]  분석할 영상 선택 (mp4/mov, ≤100MB) — analyze 화면(#4)
  │
  │  POST /upload-url  { mode, fileName, fileSizeBytes, format, referenceMotionId? }
  ▼
[백엔드] analysisId 생성 + S3 presigned PUT URL 발급
  │  → { analysisId, uploadUrl, s3Key, expiresInSec }
  ▼
[앱]  Firestore users/{uid}/analyses/{analysisId} 문서 생성 (status='uploading')
  │  S3 uploadUrl 로 영상 직접 PUT
  │  로딩 화면(#5)에서 위 문서 onSnapshot 구독 시작
  ▼
[S3]  업로드 완료 이벤트 → Lambda 파이프라인 트리거
  ▼
[백엔드] (Admin SDK 로 문서 갱신)
  status: queued → frame_extraction → pose_analysis → comparison → done
  YOLO11 → ViTPose-S → MotionDTW → KISMAM → Cerebras
  실패 시 status='failed' + error{code,message}
  완료 시 status='done' + result{...}
  ▼
[앱]  status='done' → 결과 화면(#8 Mode3 / #10 Mode1)
      status='failed' → 오류 화면 (error.code 별 메시지)
```

---

## 2. 엔드포인트

### POST /upload-url
S3 presigned PUT URL 발급. (인증: Firebase Auth UID, 익명 포함)

요청 `UploadUrlRequest`
```
mode               'mode1' | 'mode3'
fileName           string
fileSizeBytes      number          (서버도 100MB 재검증)
format             'mp4' | 'mov'
referenceMotionId  string?         mode1 필수 (비교할 정은지 동작)
```

응답 `UploadUrlResponse`
```
analysisId    string   분석 건 ID = Firestore 문서 ID
uploadUrl     string   S3 presigned PUT URL
s3Key         string   업로드될 S3 객체 키
expiresInSec  number   URL 만료(초)
```

### GET /reference
기준 모션(정은지) 목록. 응답: `ReferenceMotion[]`. (앱: 기준 모션 선택 화면 #9)

> 참고: backend/CLAUDE.md 의 `POST /analyze`, `GET /history/{userId}` 는
> 본 계약에선 각각 "S3 트리거 자동 실행", "Firestore 직접 쿼리"로 대체한다
> (앱은 분석 트리거 API를 직접 호출하지 않고, 기록은 users/{uid}/analyses 쿼리).

---

## 3. Firestore 문서

```
users/{uid}/analyses/{analysisId}   AnalysisDoc   분석 진행/결과
reference/{motionId}        ReferenceMotion  기준 모션 (읽기 전용)
```

`AnalysisDoc`
```
analysisId  string
mode        'mode1' | 'mode3'
status      'uploading'|'queued'|'frame_extraction'|'pose_analysis'
            |'comparison'|'done'|'failed'
fileName    string
createdAt   number (epoch ms)
updatedAt   number (epoch ms)
error?      { code, message }      status='failed' 일 때
result?     AnalysisResult         status='done' 일 때
learningOptIn? boolean             학습활용 동의값 (Phase 26, D-08/D-09).
                                   기록 주체 = 앱 loading.tsx (문서 생성 시 항상 boolean).
                                   opt-out (belle 결정 2026-07-08, 26-06): 앱 UI 기본값 =
                                   동의(체크 ON), 사용자가 해제하면 false 기록.
                                   부재(Phase 26 이전 문서)/param 유실 = 미동의(false)
                                   해석 — fail-safe 방향은 미동의로 불변.
                                   라우트 param 도 동일 명칭 learningOptIn ('1' | 미포함,
                                   analyze→reference→loading), 계약 필드와 단일 네이밍 (리뷰 LOW-1).
                                   소비 예정: Phase 22 manifest 게이트가 learningOptIn===true
                                   인 분석의 영상만 학습 후보로 삼아야 함 — 게이트측 필터는
                                   Phase 22 후속 반영 필요 (현 22-04 는 아직 미집행).
```

> Phase 26 (Plan 26-03) — learningOptIn 신설. app 이 기록만 하고 backend 파이프라인/
> 게이트는 무접촉 (models.py 는 주석-only 계약 미러). 3-way lockstep:
> 본 §3 + app/src/types/analysis.ts AnalysisDoc.learningOptIn +
> backend/shared/python/sunity_shared/models.py 주석 미러. 세 곳 동시 갱신 필수.

쓰기 권한
```
앱   : 문서 생성 + status='uploading' 까지만 (보안 규칙: 본인 uid 하위)
백엔드: 그 이후 모든 status/result/error 갱신 (Admin SDK, 규칙 우회)
```

`ReferenceMotion` (스키마 단일 진실: docs/reference-motions.md §3)
```
motionId           string
name               string                 동작명
athleteName        string                 '정은지'
level              'basic'|'intermediate'|'advanced'
entryType?         'step_entry'|'jump_entry'|'swing_entry'
                   |'lift_entry'|'invert_entry'|'combo_entry'
entryDescription?  string                 진입 방식 상세 (사용자 안내)
description?       string
videoUrl?          string                 HTTPS presigned URL (S3, 7일 서명) — 앱 동작 비교 영상 재생
videoUrlExpiresAt? number (epoch ms)      위 URL 만료 시각 (재시드 시점 추정)
videoS3Key?        string                 'reference/{motionId}.mp4' — 백엔드 pipeline mode1 비교 영상 서명 URL 발급에 사용
thumbnailUrl?      string
clipRange?         ClipRange              구간 시점(초)
checkpoints?       Checkpoint[]           KISMAM 가중 관절 (weight 합 1.0)
sharedBaseMotionId? string                공유 베이스 — 베이스 제공 기술 ID
baseUntilS?        number                 공유 베이스가 끝나는 시점(초)
angles?            number[]               flat 시퀀스 — Firestore nested array 금지 회피. 길이 = anglesFrames × anglesJointKeys.length. 읽는 쪽이 reshape (T, J). (M-5 정정)
anglesJointKeys?   string[]               angles 의 J 축 순서 (방어적 명시, backend skeleton.JOINT_KEYS 와 일치)
anglesFrames?      number                 angles 의 T (검증·디버깅용)
anglesUpdatedAt?   number (epoch ms)      angles 재추출 시점
meanAngles?        Record<string,number>  관절 평균 각도(deg). 결과 화면 targetAngle. 시드/derive (Phase 6)
bodyNormalizationProfile? BodyNormalizationProfile  체형 정규화 (Phase 6 백필, §8). nullable
techniqueProfile?  { name, category, jointExpectations } EXTEND joint_expectations (FallbackRecognizer 산출). Phase 14 백필. nullable (D-01/SC#2)
forceDirectionPattern? ForcePatternInference  힘 방향 패턴 (§9.11 shape). Phase 14 백필. nullable (D-01/SC#2)
captureViews?      number                 단일시점 v1 = 1 (D-03/SC#4). 다각도 부재 시 confidence 낮춤 (RESEARCH A5)
updatedAt?         number (epoch ms)
```

> Phase 14 (Plan 14-01) — techniqueProfile / forceDirectionPattern / captureViews
> 신설. meanAngles / bodyNormalizationProfile 도 §3 에 명시 (Open-Q3 contract gap
> 해소). 모두 OPTIONAL/nullable — 백필 미완 reference 정합. 백필(14-02/14-03)은 학생
> _process 와 SAME sunity_shared 함수를 REFERENCE_V1_FORCE_CONFIG (pinned) 로 거침
> (D-01). 3-way lockstep: 본 §3 + app/src/types/analysis.ts ReferenceMotion +
> Python source shapes (force_pattern.ForcePatternInference / technique.TechniqueProfile).
> 단일시점 캡처 프로토콜은 촬영 가이드 문서로만 (D-03).
`ClipRange` = { prepStartS, execStartS, execPeakS, landEndS, recommendedRecordS }
  → 분석 런타임은 execStartS~landEndS 만 사용 (reference-motions.md §4).
`Checkpoint` = { joint, weight, note? }

> 공유 베이스: ref-invert → ref-foxtop(baseUntilS:6)
> → ref-foxtop-split(baseUntilS:18). 베이스 공유 기술의 mode1 분석 시
> 베이스/확장 구간을 나눠 부분 점수 산출 → Mode1Comparison.segmentScores (§4).

> ⚠️ backend/CLAUDE.md 는 `analyses/{analysisId}`(최상위), `reference_motions/{id}`
> 로 적혀 있으나, **배포된 보안 규칙이 users/{uid} 격리**라 본 계약은
> `users/{uid}/analyses/{analysisId}`, `reference/{motionId}` 를 사용한다.
> → backend/CLAUDE.md 의 컬렉션 항목은 추후 본 계약에 맞춰 갱신 필요 (미결 항목).

---

## 4. 분석 결과 `AnalysisResult`

design.md §8 결과 화면이 그리는 데이터.
```
overallScore   number              0~100 종합 = core 차원(angle/line)의 min (min-of-core).
                                   stability 는 종합 입력에서 제외(보조 지표). core 부재 시 절대트랙 단독.
dimensionScores { angle?, line?, stability } 각 0~100  ← IPSF 실행 차원 (3차원)
dimensionExplanation { [dim]: DimensionExplanation } optional  ← Phase 12.5 (2026-06-07)
recommendedExercises RecommendedExercise[] optional  ← Phase 13 (2026-06-16, PERS-03)
joints         JointScore[]        관절별 (8 — 평가 관절). 코칭 팁 근거
tips           CoachingTip[]       상위 3개 (KISMAM Top-3 + Cerebras 문장)
comparison     Mode1 | Mode3       아래
myVideoUrl     string              내 영상 재생 서명 URL (좌)
referenceVideoUrl string?          mode1: 정은지 영상 (우)
visionVeto     { status, severity?, tallyFinal? } optional  ← Phase 20 SCORE-08 / Phase 24 (밴드 제거)
scoreSuppressed bool? + scoreSuppressedReason? enum         ← Phase 20 TRUST-07
scoreSuppressionAudit { recognizerCategory, branchReferenceFree, resolvedReason } optional ← Phase 20 iter5
```

`visionVeto` (Phase 20 SCORE-08 / TRUST-08 + Phase 24 ND-01 — 비전 채점 audit, 밴드 제거)
```
status      'applied' | 'not_applicable' | 'disabled' | 'skipped_error' | 'missing_local_video' | 'mode3_held' | 'missing_reference' | 'low_alignment_confidence' | 'resource_limited'
severity?   'minor' | 'moderate' | 'major'   (applied 시에만 동반)
tallyFinal? number  적용된 감점 tally 최종 점수  (applied 시에만 동반 — 점수는 §10 deductionBreakdown.final, tallyFinal 은 그 audit mirror)
primaryFault? string  지배적 결함 DESCRIPTION   (applied 시에만 동반, UI B1 — "왜 내려갔는지")
telemetry?  { completedCalls?, plannedCalls?, samplingComplete? }  (resource_limited 시에만)
quantificationStatus? 'available' | 'unavailable'   (applied 시에만 동반 — 필수, Phase 23-02)
angleDeltas? [{ joint, student_deg, reference_deg, delta_deg, direction, source:'geometry' }]  (applied+available 시)
bodyRelativeNotches? [{ keypoint, student_notches, reference_notches, delta_notches, baseline_kind, source:'geometry' }]  (applied+available)
windowMedianAngleDeltas? { deltas[], sourceFrameIndices, windowPolicy }  (still 정확 각도 아님 — 별도 키, D-10 HIGH-3)
rootCauseHypotheses? [{ text, faultKey, supportCount }]  (applied + cap_would_apply 시, source=vision_hypothesis)
```
  - Phase 23-02 정량화 DESCRIPTIVE 필드 (3-way lockstep, D-02/D-04/D-11 MED-1/D-12 HIGH-1):
    - **applied 시에만** 동반 (discriminated — not_applicable/보류/disabled 분기엔 부재).
    - `quantificationStatus` 는 applied audit 에 **필수**. same-frame 정량화 입력 결측 시
      `'unavailable'` 로 신호하고 `angleDeltas`/`bodyRelativeNotches` 는 부재하되
      `status='applied'`+`tallyFinal`+`rootCauseHypotheses` 는 **유지**한다(not_applicable
      강등 금지, crash 금지). geometry 는 `VisionQuantificationResult`(post-geometry)가
      소유하고 apply 의 deduction tally 후 `to_audit_dict(quantification=)` 로만 주입(D-12 HIGH-1).
    - `angleDeltas` 는 verdict 프레임 쌍(user/ref_frame_idx)의 **frame-specific** 각도 —
      DTW window median 아님. median 은 `windowMedianAngleDeltas` 로 별도 키(D-10 HIGH-3).
    - 칸(`bodyRelativeNotches`)은 keypoint+baseline 결정적 기하 산출(Gemini 미산출, H2).
    - **score/0-100/percent 타입 절대 0** — 각도(도)/칸/text + source enum DESCRIPTIVE(D-06/D-08).
  - Phase 23-01 신규 score-free status (3-way lockstep):
    - `low_alignment_confidence` — 글로벌+로컬 DTW 정렬 신뢰도가 낮아 거짓결함을 fabricate
      하지 않고 보류 (점수 불변, 채점 미적용). severity/tallyFinal 없음 (D-03/H4).
    - `resource_limited` — planned call 전부 완료 전 예산(호출/upload/wall-clock) 소진 →
      fail-closed 보류 (부분 샘플 verdict 비결정성 차단, 점수 불변). severity/tallyFinal/
      primaryFault 없음, telemetry(completedCalls/plannedCalls/samplingComplete) 만 동반
      가능 (D-09 MED-1 / D-13 HIGH-2 Option A).
  - **status 가 채점 실행을 증명한다 (부재 ≠ 실행, HIGH-1).** status='applied' 로 채점
    실행을 검증한다. 부재가 '채점이 돔'으로 읽히지 않는다.
  - 밴드 제거 — applied 시 tallyFinal(감점 합산 최종) 동반; severity 도 함께 강제
    (analysis.ts VisionVeto discriminated union; status:'applied' without tallyFinal 는 tsc 에러).
    not_applicable/disabled/skipped_error/missing_local_video → severity/tallyFinal 없음.
  - applied → primaryFault(결함 DESCRIPTION, 자연어) optional 동반 (UI B1 — "왜 점수가 내려갔는지"
    노출용). 점수/숫자 라벨 금지(객관성). legacy doc 호환 위해 optional(없어도 렌더).
  - 객관성: visionVeto 에 사람/AI **점수 라벨 0** — status/severity enum + tallyFinal(측정규칙
    산출 정수)만 ([[analysis-objectivity-no-human-scores]]).
  - Phase 24: 점수 자체는 §10 `deductionBreakdown.final`(투명 감점-합산). visionVeto.tallyFinal
    은 그 audit mirror — severity→고정천장 밴드는 제거됐다.
  - 3-way lockstep: `app/src/types/analysis.ts VisionVeto` ↔ `models.py VISION_VETO_STATUSES`
    ↔ 본 §4. 세 곳 동시 갱신 필수.

`scoreSuppressed` + `scoreSuppressedReason` (Phase 20 TRUST-07 — Mode3 미보유/저신뢰 억제)
```
scoreSuppressed       bool?   true 면 점수카드 전체('기준 없음' state)로 대체
scoreSuppressedReason 'unheld' | 'recognition_low_confidence'
```
  - Mode3 미보유(branch-3) confident 점수 차단 (D-08 — confident 97 금지). 점수는 산출하되
    화면이 점수카드 전체(octagon + grade + summary + benchmark + caption + 헤더 카피)를 억제.
  - **불변식 (iter4 MEDIUM-1, producer-contract): scoreSuppressed=true → scoreSuppressedReason
    REQUIRED.** producer 가 reference_free_absolute 인데 scoreSuppressed 누락 = producer-contract
    FAILURE; scoreSuppressed=true 인데 reason 누락 = producer-contract FAILURE (fail-loud, UI
    silent 추론 / default 카피 금지 — iter3 HIGH-2 / iter4 MEDIUM-1).
  - **프런트 억제 판정은 이 플래그 단독** (scoringBasis 폴백 금지 — scoringBasis 는 source
    라벨, suppression 은 display/trust 정책).
  - 사유 분리 (iter3 MEDIUM-1):
    - `unheld` = 미보유 (is_reference_free branch metadata) → '기준 없음' 카피.
    - `recognition_low_confidence` = recognizer 신뢰도 낮음 (동작은 알 수 있어도 분류 불확실)
      → '동작 인식 신뢰도가 낮아 기준을 확정할 수 없어요' 카피. 미보유 아님.
  - **iter5 HIGH-2 (reason-owns-copy): suppression reason 이 모든 visible suppressed-state
    카피(헤더 + scoringBasisLabel)를 소유한다. recognition_low_confidence 의 scoringBasisLabel
    은 '기준 동작 없음'/'기준 없음' 미포함** (두 번째 UI 필드 reason leak 차단).
  - 3-way lockstep: `app/src/types/analysis.ts ScoreSuppression` ↔ `models.py
    SCORE_SUPPRESSED_REASONS` ↔ 본 §4.

`scoreSuppressionAudit` (Phase 20 iter5 MEDIUM-2 — A2 reconcile 단일 structured sink)
```
recognizerCategory   string   recognizer category (provenance)
branchReferenceFree  bool     is_reference_free_motion(branch_info) 결과
resolvedReason       'unheld' | 'recognition_low_confidence'   resolver 최종 reason
```
  - recognizer category 와 branch is_reference_free 출처가 다름. resolver 가 category
    provenance 로 단일 reason 결정하면서, 불일치 시 정확히 이 필드로 reconcile 관측
    (log.warning '또는' 대안 폐기 — log 는 additive only never alternative).
  - 3-way lockstep: `app/src/types/analysis.ts ScoreSuppressionAudit` ↔ `models.py
    SCORE_SUPPRESSION_AUDIT_KEYS` ↔ 본 §4.
  - Firestore flat 정합: visionVeto = scalar dict, scoreSuppressed = bool,
    scoreSuppressedReason = str, scoreSuppressionAudit = scalar dict (nested-array 0,
    [[firestore-nested-array-flat]] 보존).

`timingsMs` (Phase 27 SPD-01 — 단계별 소요 계측, D-01 before/after 근거)
```
timingsMs   { [stage: string]: number }   optional  ← 단계별 소요(ms), flat dict[str,int]
```
  - **backend/audit 전용 · 사용자 비노출** — UI 는 이 필드를 절대 소비하지 않는다(점수/코칭
    surface 0). D-01 정확도 무회귀 게이트의 before/after stage-timing 표 + D-02 진행률
    재배분의 실측 기반으로만 사용.
  - flat `dict[str, int]` (nested list/dict 금지 — [[firestore-nested-array-flat]] 보존).
    값은 정수 ms.
  - 단계 키는 **예시**(비고정 — 키 추가는 비파괴): `s3_download`, `frame_extract`, `rtmw`,
    `scene_finder`, `recognizer`, `ref_fetch_download`, `dtw_scoring`, `veto_collect`,
    `coach_dual`, `assemble_misc`, `fault_zoom`. `firestore_complete` 는 저장 dict 에는
    미포함(complete_analysis 호출 자체를 감싸 직렬화 이후 기록 — 로그 라인으로만 방출).
  - **부재 = 계측 이전(legacy) doc** — optional, migration 없음.
  - Python 정본: pipeline `app.py` `_stage` contextmanager 주석 (자유 키 dict — status
    enum 아님, models.py 상수 불필요). lockstep: `app/src/types/analysis.ts
    AnalysisResult.timingsMs?` ↔ pipeline `_stage`/`result["timingsMs"]` ↔ 본 §4.

`dimensionScores` = IPSF 폴스포츠 실행 심사기준 (docs/research/폴스포츠-지식.md).
  신체 부위가 아니라 심판이 보는 실행 차원. **3차원** (2026-05-29 balance 차원 제거 —
  IPSF 근거 없음, 의도적 비대칭 동작 위양성 제거).
  - angle     각도 정확도 (관절각 vs 기준). reference 필요 → mode1 항상, mode3 second+.
  - line      라인·확장 (사지 신전 완성도). 절대 지표. 신전 요구 관절 없으면 생략.
  - stability 안정성·홀딩 (피크 구간 떨림). 절대 지표.
  절대 차원 (line/stability) 은 기준 없이 산출 → mode3 세션 간 발전 델타가 같은 척도.
  mode1 = 3키, mode3 first = 2키 (line/stability — line 생략 가능 시 1키 stability),
  mode3 second+ = 3키.

`DimensionExplanation` (Phase 12.5, 2026-06-07 추가)
```
weightPercent  int    각 차원이 overall 에 기여하는 비중 (%). 기여 차원(angle/line)의
                      합 = 100. Phase 19 D-01: stability 는 종합 비기여 → weightPercent=0.
                      Largest Remainder Method (기여 차원 한정): 2차원=[50,50], 1차원=[100].
baseline       string mode-aware 기준 카피. mode1 = 정은지 측정값 참조,
                      mode3 = 절대 지표 기반 (정은지 비교 X).
deficitSummary string 점수 산출과 동일 source 의 deficit 한 줄 카피.
                      angle ← kismam.top_issues worst 관절,
                      line  ← dimensions.line_deficits_by_joint (EXTEND 관절만),
                      stability ← dimensions.stability_wobble_by_joint (inter-frame diff).
                      양호 점수 (≥ 80) 시 수치 X 카피 ("안정").
contributesToOverall bool (optional, Phase 19 D-01) 해당 차원이 종합점수에 기여하는지.
                      overall_from_dimensions = min-of-core(angle/line) 이므로 core 차원
                      = true, stability = false (+ weightPercent 0). 옛 doc 미보유 →
                      UI default true (옛 overall 은 stability 포함). 신 backend 항상 emit.
```
  - 결과 화면 "왜 이 점수인지" 가시화 용도. 점수 산식 source 와 동일 windowing 사용
    (`dimensions._select_window` 공유) — drift 0 보장.
  - 이전 빌드 doc 호환: 옵셔널 필드. 키 부재 시 frontend 추가 라인 표시 X.
  - 신 backend 는 빈 `{}` 라도 항상 emit (호환성).

`RecommendedExercise[]` (Phase 13, 2026-06-16 추가 — PERS-03)
```
name        string 운동명 (예: "Farmer's Walk")
setsReps    string 세트/반복 (예: "왕복", "8~12회")
purpose     string 한 줄 목적 (왜 이 운동인지)
sourceRef   string? 출처 cite (예: "NotebookLM e688fb4e [1]"). 옵셔널.
```
  - 분석 결과(실패 원인 후보 + 통증부위)에 맞춘 보완 운동 3~5개 개인화 subset.
  - 생산자 = `analysis/exercise_map.map_exercises(forcePatternInference.findings,
    bodyProfile.painAreas, motion_id)` — pure fn. painAreas 는 매핑 출력에만
    흐르고 점수/차원 경로 미진입 (D-05).
  - 검증 = `firestore_admin._validate_recommended_exercises` (len <= 5 cap + 각
    item flat scalar — [[firestore-nested-array-flat]] 보존).
  - 옵셔널 필드 — 빈/부재 시 result.tsx 는 전체 라이브러리 모달 browse entry 만
    유지 (MEDIUM-1). 전체 라이브러리는 `app/src/data/correctiveExercises.ts`
    (backend/data/corrective_exercises.json byte-copy mirror).
  - 3-way lockstep: `app/src/types/analysis.ts:RecommendedExercise` ↔ `models.py
    RECOMMENDED_EXERCISE_KEYS` ↔ 본 §4. 세 곳 동시 갱신 필수.

`JointScore`
```
key, labelKo, score(0~100)
currentAngle? targetAngle? deltaDeg?(signed) direction?  ← 구조화 가이드 (옵셔널)
targetSource?                                            ← target 산출 출처 (Phase 12)
issue?                                                    ← 사람 가독 폴백
```
`direction` = 'extend' | 'flex' | 'raise' | 'lower' | 'open' | 'close'
  → UI 가 "현재 145° → 기준 168° · 더 펴주세요" 형태로 표시. 구조화 필드가
  없으면 issue 텍스트로 폴백. 동적 큐(회전력·반동)는 CoachingTip.detail
  자연어로 노출(LLM 출력) — 별도 필드 만들지 않음.

`targetSource` = 'reference_motion' | 'previous_analysis' | 'extension_requirement' | 'unavailable'
  Phase 12 Wave 0A (Codex 직접 리뷰 2026-06-10 R2/R4) 신설. target 산출 출처:
    - reference_motion       mode1 — 정은지 measured angle
    - previous_analysis      mode3_progress — 이전 분석 measured angle
    - extension_requirement  mode3_first 의 extension-required joint = IPSF 180°
    - unavailable            mode3_first 의 extension 불필요 관절 (targetAngle 없음)
  UI 의 "기준 N°" prefix 분기 source (정은지 / 지난 영상 / IPSF 180° / 기준 없음).
  옵셔널 — 이전 빌드 doc 호환 (없으면 targetAngle 자체로 판단).

`CoachingTip` = { joint?, title, detail }

`Mode1Comparison` (전문가 비교)
```
mode='mode1', referenceMotionId, referenceMotionName, athleteName, similarity(0~100)
segmentScores?         베이스 공유 기술 분석 시에만
scoringBasis?          'reference_motion'   (Phase 19 — Mode1 전용, build_mode1 always-emit)
scoringBasisLabel?     사용자 표시용 한국어 라벨
```
  scoringBasis (Phase 19 ITER-4) = Mode1 은 정은지 reference 각도와 실제 비교하므로 항상
  `reference_motion`. OPTIONAL (legacy doc 호환) — 신규 doc 은 항상 채움. **Mode1 전용 —
  Mode3 comparison 에는 이 값이 없음** (first 는 reference motion 비교가 아님).
`SegmentScores` = { base(0~100), extension(0~100), baseMotionId, baseMotionName }
  → 베이스 공유 reference 시퀀스를 baseUntilS 기준 베이스/확장으로 분리 후 각 KISMAM 점수.
  단일 모션은 segmentScores 없음.
`Mode3Comparison` (자기 성장)
```
mode='mode3', isFirst(bool),
previousAnalysisId?, deltaFromPrevious?{line?,stability,angle?}  (isFirst면 없음)
scoringBasis?          실제 채점 SOURCE (Phase 19, Mode3 = 정확히 4 값)
scoringBasisLabel?     사용자 표시용 한국어 라벨
```
  deltaFromPrevious = 발전(progress). '몇 % 일치'가 아니라 절대 차원(라인/안정성)의
  이전 분석 대비 증감(±). 절대 지표라 세션 간 같은 척도. 첫 분석이면 없음.
  키는 양쪽 분석 공통 차원만 (line 이 한쪽에 없으면 stability 만).

  scoringBasis (Phase 19 TRUST-03) = 거짓 confident 점수 차단을 위해 실제 채점 source 를
  화면에 노출. Mode3 허용값 = **정확히 4 값** (reference_motion 은 Mode1 전용이라 Mode3 에 없음):

  | scoringBasis                                   | 의미 |
  |------------------------------------------------|------|
  | reference_free_absolute                        | first + 미보유 동작 → 절대트랙(line+stability) |
  | recognized_motion_absolute                     | first + 등재 동작 → 절대트랙 (first 는 reference 각도 미사용) |
  | previous_analysis_plus_absolute                | progress + 등재 → 이전 영상 각도 일관성 + 절대트랙 |
  | previous_analysis_plus_reference_free_absolute | progress + 미보유 → composite (이전 일관성 + 절대트랙, lossy 금지) |

  미보유 first = reference_free_absolute, progress 미보유 = composite. **Mode3 에 reference_motion
  없음** (Mode1 전용). 거짓 "% 일치" / "정은지와 거의 같음" 프레이밍 금지.

추출된 관절각은 done 문서 top-level 에 flat 저장 (백엔드 전용, mode3 가 '이전 영상'
기준 DTW 비교에 사용). `angles`(number[]), `anglesJointKeys`(string[] 길이 J),
`anglesFrames`(T). Firestore nested-array 금지 회피로 flat — 읽는 쪽 reshape.

---

## 5. 상태/오류 메시지 (UI 고정 문구)

`STATUS_MESSAGE` (design.md §5-9 단계별)
```
uploading        영상을 올리는 중...
queued           분석을 준비하는 중...
frame_extraction 영상 프레임 추출 중...
pose_analysis    포즈 데이터 분석 중...
comparison       기준 모션과 비교 중...
done             분석이 완료되었어요!
```

`ERROR_MESSAGE` (ml/CLAUDE.md = design.md §6 오류 4종 + 비폴 차단 안전망)
```
no_human            영상에서 사람을 찾지 못했어요. 전신이 보이게 다시 촬영해주세요.
size_exceeded       100MB 이하 영상만 분석할 수 있어요.
unsupported_format  mp4, mov 형식의 영상만 분석할 수 있어요.
server_error        분석 중 문제가 발생했어요. 잠시 후 다시 시도해주세요.
not_pole_motion     선택한 기준 동작과 너무 달라요. 폴스포츠 동작이 맞는지 확인하고 다시 시도해주세요.
```

`not_pole_motion` — mode1 비교 시 KISMAM similarity 가 `models.NOT_POLE_SIMILARITY_THRESHOLD`(현재 25) 미만이면 백엔드 pipeline 이 `NotPoleMotionError` 로 분기. mode3 는 reference 가 없어 적용 불가.

---

---

## §6. PoseFrame + PoleAxis (Phase 1 신규 — D-04/D-05/D-11/D-12)

> **변경 시 lockstep 경고**: 아래 3 파일 동시 갱신 필수.
>   - `app/src/types/analysis.ts` (TS interface)
>   - `backend/shared/python/sunity_shared/analysis/pose_frame.py` (Python dataclass)
>   - 이 문서 §6 (docs/contract.md)

### Type aliases

| alias | 값 | 용도 |
|-------|----|------|
| `ConfidenceLevel` | `'high' \| 'medium' \| 'low'` | M-2 D-11 — PoleAxis.confidenceLevel, reliability 둘 다 사용 |
| `ReliabilityLevel` | `'high' \| 'medium' \| 'low'` | H-4 — frame-level 신뢰 게이트 |
| `PoleAxisSource` | `'detected' \| 'vertical_fallback'` | D-09/D-11 — Hough 검출 성공/실패 |

### PoseFrame (영상 한 프레임 포즈 계약)

| TS 필드 (camelCase) | Python 필드 (snake_case) | TS 타입 | D-NN | 설명 |
|---------------------|--------------------------|---------|------|------|
| `frameIndex` | `frame_index` | `number` | — | 프레임 인덱스 |
| `timestampMs` | `timestamp_ms` | `number` | — | 타임스탬프 (ms) |
| `rawLandmarks33?` | `raw_landmarks_33` | `Record<string, Landmark3D>` | D-04 | MediaPipe 33 원본 보존 |
| `keypoints3D` | `keypoints_3d` | `Record<string, Keypoint3D>` | D-04 | COCO-17 분석용 |
| `keypoints3DPoleAligned` | `keypoints_3d_pole_aligned` | `Record<string, Keypoint3DAligned>` | D-12 | 폴 축 정렬 좌표 |
| `keypoints2D?` | `keypoints_2d` | `Record<string, Keypoint2D> \| null` | D-03 | UI 오버레이용 image normalized |
| `poleExtensionLandmarks?` | `pole_extension_landmarks` | `Record<string, PoleExtensionLandmark> \| null` | D-04 | 폴 확장 (toe/heel/grip) |
| `poleAxis` | `pole_axis` | `PoleAxis \| null` | D-12, H-3 | video-level PoleAxis 메타 (모든 frame 공유) |
| `reliability` | `reliability` | `ReliabilityLevel` | D-05, H-4 | frame-level 신뢰 게이트 |
| `bodyShape` | `body_shape` | `BodyNormalizationProfile \| null` | D-21 | 체형 정규화 (RTMW=null, NLF_SMPLX=β path). Plan 01-19 추가. |

### PoleAxis (폴 축 메타)

| TS 필드 | Python 필드 | TS 타입 | D-NN | 설명 |
|---------|------------|---------|------|------|
| `axisVector` | `axis_vector` | `{x,y,z}` | D-12 | 3D 단위 벡터 |
| `confidenceLevel` | `confidence_level` | `ConfidenceLevel` | M-2, D-11 | 검출 실패 시 'low' |
| `source` | `source` | `PoleAxisSource` | D-09, D-11 | 'detected' \| 'vertical_fallback' |
| `frameIndex?` | `frame_index` | `number \| null` | D-10 | null = video-level (영상 전체 평균 축 1개) |

### Landmark3D (MediaPipe 33 raw landmark)

| 필드 | 타입 | 설명 |
|------|------|------|
| `x, y, z` | `number/float` | 3D metric 좌표 |
| `rawVisibility` / `raw_visibility` | `number/float` | M-1 D-05 — MediaPipe API visibility. range [0,1] |
| `rawPresence` / `raw_presence` | `number/float` | M-1 D-05 — MediaPipe API presence. range [0,1] |

### Keypoint3D (COCO-17 분석용)

| 필드 | 타입 | 설명 |
|------|------|------|
| `confidence` / `confidence` | `number/float` | D-05: visibility × presence (둘 다 있을 때) 또는 visibility. range [0,1] |
| `uncertaintyProxy` / `uncertainty_proxy` | `number/float` | D-05: 1 - confidence |

### D-결정 요약 (CONTEXT.md 인용)

- **D-04**: 원본 저장 = MediaPipe 33 전체. 스코어링 계약 = COCO-17 + 폴 확장(toe/heel/grip).
- **D-05**: confidence = visibility × presence (둘 다 있을 때) 또는 visibility. raw_visibility / raw_presence 모두 별도 저장. 저신뢰 각도는 low_reliability 마킹 — 단정형 코멘트 금지.
- **D-11**: PoleAxis 검출 실패 → 수직 가정 + confidence_level='low'. 리포트에 "카메라 기울어짐 주의" 안내.
- **D-12**: PoseFrame 에 raw(keypoints_3d) + pole-aligned(keypoints_3d_pole_aligned) + pole_axis(PoleAxis) 메타 모두 저장. poleAxis / pole_axis 필드는 video-level (D-10).

### NOTE (H-4 D-05 박제)

> **reliability='low' 또는 low_reliability=True 마킹된 각도는 coach_writer/dimensions 단정형 코멘트 금지.**
> 후속 phase 가 본 정책을 import 해 enforce — Phase 1 은 NOTE 로 명시.
> 관련 코드: `backend/shared/python/sunity_shared/analysis/reliability.py::compute_angle_with_reliability`

### Firestore 저장 정책

Phase 1 에서 PoseFrame 은 RunPod 메모리 전용. Firestore 저장은 기존 angles flat 패턴 유지.
키포인트 오버레이 저장은 Phase 12 결정.

---

## §7. BodyNormalizationProfile (Plan 01-19 신설 — D-19/D-21 RTMW pivot)

> **2026-06-02 RTMW pivot 박제**: 체형 정규화는 **SMPL-X β 없이 세그먼트 길이 비율** 만으로
> 표현 (D-19). SMPL-X / shape_params / betas 필드는 **영구히 도입하지 않는다**.
> NLF_SMPLX R&D path 에서 β 가 필요하면 R&D 전용 별도 타입을 둘 것 — 본 contract 아님.
>
> **변경 시 lockstep 경고**: 아래 3 파일 동시 갱신 필수 (CLAUDE.md Cross-cutting).
>   - `app/src/types/analysis.ts` `BodyNormalizationProfile` interface
>   - `backend/shared/python/sunity_shared/analysis/body_normalization.py` dataclass
>   - 이 문서 §7

### BodyNormalizationProfile (체형 정규화 프로파일)

| TS 필드 (camelCase) | Python 필드 (snake_case) | TS 타입 | D-NN | 설명 |
|---------------------|--------------------------|---------|------|------|
| `estimatedHeightScale` | `estimated_height_scale` | `number` | D-19 | torso-relative proportion heuristic — 절대 키가 아니라 torso 길이 대비 사지 비율 (`(armScale + legScale + 1.0) / 3`). Phase 6 coarse normalizer hint 로만 사용. **Contract: finite (no NaN/inf) + strictly positive (> 0). 위반 시 dataclass `__post_init__` ValueError (MEDIUM-2 v5).** |
| `armScale` | `arm_scale` | `number` | D-19 | torso-relative proportion heuristic — torso 길이 대비 팔 segment 비율 (1.0 = torso 와 동일 길이). Phase 6 coarse normalizer hint 로만 사용. **Contract: finite (no NaN/inf) + strictly positive (> 0). 위반 시 dataclass `__post_init__` ValueError (MEDIUM-2 v5).** |
| `legScale` | `leg_scale` | `number` | D-19 | torso-relative proportion heuristic — torso 길이 대비 다리 segment 비율. Phase 6 coarse normalizer hint 로만 사용. **Contract: finite (no NaN/inf) + strictly positive (> 0). 위반 시 dataclass `__post_init__` ValueError (MEDIUM-2 v5).** |
| `torsoScale` | `torso_scale` | `number` | D-19 | 몸통 정규화 단위 (self-reference 1.0). **Contract: finite (no NaN/inf) + strictly positive (> 0). 위반 시 dataclass `__post_init__` ValueError (MEDIUM-2 v5).** |
| `shoulderHipRatio` | `shoulder_hip_ratio` | `number` | D-19 | 어깨너비 / 골반너비 비율 (체형 분류 단서). **Contract: finite (no NaN/inf) + strictly positive (> 0). 위반 시 dataclass `__post_init__` ValueError (MEDIUM-2 v5).** |
| `confidence` | `confidence` | `number` | D-19 | 측정 신뢰도 `[0.0, 1.0]`. RTMW score 또는 측정기 자체 신뢰도. fallback path 는 0.0. |
| `warnings` | `warnings` | `string[]` | D-19 | 측정 품질 이슈 enum (아래 5종). Phase 11 coach_writer 가 한국어 카피로 번역. 기본값 `[]`. |

### warnings enum (5종, Phase 2 BODY-01 박제)

| Enum 값 | 의미 |
|---------|------|
| `low_keypoint_confidence` | 전체 키포인트 평균 confidence 가 임계값 (0.4) 미만 — 영상 품질 / 조명 부족. |
| `occluded_endpoint` | 한쪽 endpoint (shoulder / hip / knee / ankle / wrist) 의 confidence < 0.5 가 frame 60% 초과 — 가림. |
| `insufficient_frames` | 분석 frame 수가 30 미만 — 짧은 클립. measurer fallback path 진입 신호. |
| `asymmetric_landmark_count` | 좌우 endpoint valid frame 차이가 30% 초과 — 한쪽 가림 추정. |
| `pose_too_inverted` | 인버트 자세가 50% 초과 — image y-down 좌표 직접 비교 (mean shoulder.y vs mean hip.y). PoleAxis.axisVector 부호와 독립적 (MEDIUM-3 v5). |

### D-결정 요약 (CONTEXT.md 인용)

- **D-19**: 체형 정규화 = SMPL-X 없이 **세그먼트 길이 비율**. 파라미터형 메시 의존 영구 제거.
- **D-21**: `PoseFrame.bodyShape` 필드 **nullable** — RTMW 운영 path = `null`,
  NLF_SMPLX R&D path = `BodyNormalizationProfile` 채움. 양쪽 호환.

### Consumer 예고 (Phase 2 BODY-01)

Phase 1 (Plan 01-19 ~ 01-25) 단계는 **contract 박제만**. 본 dataclass 를 채우는
실제 segment-ratio 측정기는 **Phase 2 BODY-01** 에서 구현. 그 시점에 RTMW
어댑터가 `PoseFrame.bodyShape` 에 측정값을 주입한다.

### 향후 재도입 절차 (NLF_SMPLX path)

NLF/SMPL-X 의 상업 라이선스가 클리어되고 매출이 정당화되는 시점에 `POSE_ENGINE`
config 플래그를 `NLF_SMPLX` 로 swap. 이 path 에서는 SMPL-X β 가 자체적으로
필요할 수 있으나 **본 contract 에는 들어오지 않는다** — R&D 전용 어댑터 내부에서만
사용하고, 다운스트림에 노출되는 정규화 표현은 항상 `BodyNormalizationProfile`
(segment 비율) 형식으로 변환되어야 한다. 다운스트림 무수정 (D-24) 약속의 핵심.

---

## BodyProfile (자가입력) (Phase 3, Plan 03-01 신설 — BODY-02)

> **2026-06-15 박제**: 게스트가 직접 입력하는 신체 프로필. **자가입력 보조
> 데이터** — 분석 단정·점수 가중에 사용하지 않는다. 미입력/부분/잘못된 값에도
> pipeline 은 crash 없이 graceful 진행 (SC#4).
>
> **변경 시 lockstep 경고**: 아래 3 곳 동시 갱신 필수 (CLAUDE.md Cross-cutting).
>   - `app/src/types/analysis.ts` `BodyProfile` interface + 3 union (ExperienceLevel / DominantHand / PainArea)
>   - `backend/shared/python/sunity_shared/models.py` `EXPERIENCE_LEVELS` / `DOMINANT_HANDS` / `PAIN_AREAS` + `normalize_body_profile`
>   - 이 섹션

### 필드

| TS 필드 (camelCase) | TS 타입 | nullable | 설명 |
|---------------------|---------|----------|------|
| `heightCm` | `number` | ✓ | 키 (cm). 90~250 범위 밖 → null (graceful). |
| `weightKg` | `number` | ✓ | 몸무게 (kg). 25~200 범위 밖 → null. **D-05: 보조 ONLY — 점수/분석 단정·scoring 모듈 유입 금지.** |
| `experience` | `ExperienceLevel` (`beginner`/`intermediate`/`advanced`) | ✓ | 폴스포츠 경력. 알 수 없는 값 → null. |
| `painAreas` | `PainArea[]` | (빈 배열 가능) | 통증부위 다중선택. PainArea 멤버 string 만 유지 (비-string·비-멤버 제거). flat scalar array (Firestore nested-array 안전). |
| `dominantHand` | `DominantHand` (`left`/`right`/`both`) | ✓ | 우세손. 알 수 없는 값 → null. |
| `updatedAt` | `number` | (옵셔널) | 마지막 저장 epoch ms (saveBodyProfile merge). |
| `promptDismissedAt` | `number` | (옵셔널) | 첫 분석 권유 모달 once-flag (03-03). |

`PainArea` 멤버: `shoulder` / `wrist` / `lower_back` / `knee` / `ankle` / `neck` / `hip` / `elbow` (폴스포츠 고하중 관절, `docs/research/폴스포츠-지식.md` 정합).

### 저장 위치

- **라이브**: `users/{uid}.bodyProfile` — 마이페이지에서 읽고/쓰는 현재 프로필.
- **per-analysis SNAPSHOT**: `users/{uid}/analyses/{id}.bodyProfile` — 분석 시작
  시점(`loading.tsx`)에 `getBodyProfileOnce()`(client normalize)로 복사. 결과
  화면은 **snapshot 을 source-of-truth** 로 읽는다 (분석-당시 값 재현성, R1 —
  이후 라이브 프로필이 바뀌어도 과거 분석 결과는 당시 값 유지).

### graceful / 보안 제약

- **graceful-missing (SC#4)**: 미입력/부분/잘못된 enum/범위 밖 값에도 pipeline
  crash 없음. 전 필드 None/빈이면 snapshot 자체를 생략 (all-empty → omit).
- **이중 정규화**: client `normalizeBodyProfile` (getBodyProfileOnce) +
  server `normalize_body_profile` (pipeline) 둘 다 unknown enum/범위 밖 → None.
- **D-05 (weightKg 보조-only)**: 어떤 프로필 값도 scoring 경로에 유입 금지 —
  위조된 height/weight 로 점수 game 불가. coach context(D-04)에만 전달.
- **owner-only**: `users/{uid}/{**}` Firestore 규칙으로 본인 doc 한정 (rules 변경 불필요).

---

## §8. BodyComparisonReport (Plan 06-01 신설 — D-06-B3 confidence-tiered hybrid + W1 + C14 IPSF divergence + R8 extra_warnings + R2 source pose)

> **2026-06-08 박제**: Phase 6 의 체형 정규화 비교 출력. mode1 / mode3_first /
> mode3_progress 3 케이스 통합 schema (W1 — 4번째 fallback 변형 케이스 금지.
> Gemini fallback 신호는 sibling boolean `usedReferenceFallback`).
>
> **변경 시 lockstep 경고**: 아래 3 파일 동시 갱신 필수 (CLAUDE.md Cross-cutting).
>   - `app/src/types/analysis.ts` `BodyComparisonReport` interface
>   - `backend/shared/python/sunity_shared/analysis/body_normalizer.py` dataclass
>   - 이 문서 §8 (+ §8.2 BodyComparisonSourcePose, R2 fix)

### ComparisonType union

```typescript
type ComparisonType = 'mode1' | 'mode3_first' | 'mode3_progress';
```

3 케이스만 — W1 박제. mode3_first + Gemini fallback 매칭 시 `usedReferenceFallback: true` 로
표현하며 comparisonType 자체는 `'mode3_first'` 유지.

### ScaleProfile (D-06-A3 5 필드 + apply 플래그)

| TS 필드 (camelCase) | Python 필드 (snake_case) | TS 타입 | 설명 |
|---|---|---|---|
| `estimatedHeightScale` | `estimated_height_scale` | `number` | 전체 키 비율 (target/source). finite + strictly positive. |
| `armScale` | `arm_scale` | `number` | 팔 길이 비율. finite + strictly positive. |
| `legScale` | `leg_scale` | `number` | 다리 길이 비율. finite + strictly positive. |
| `torsoScale` | `torso_scale` | `number` | 몸통 길이 비율. finite + strictly positive. |
| `shoulderHipRatio` | `shoulder_hip_ratio` | `number` | 어깨너비/골반너비 비율. 점수 차원 미적용 (D-06-A3, [[scoring-dimensions-ipsf]]). |
| `shoulderHipRatioApplied` | `shoulder_hip_ratio_applied` | `boolean` | 폭 보정 적용 여부 (foreshortening 시 false, W6). |

### BodyComparisonFinding (R9 fix: 5 IPSF + Sunity pose_reliability_low — 6 enum + Phase 7 신설 4 필드)

| TS 필드 | Python 필드 | TS 타입 | 설명 |
|---|---|---|---|
| `deficitCode` | `deficit_code` | `string` | 6 enum 중 하나 (아래 표). |
| `jointKey` | `joint_key` | `string \| null` | finding 이 단일 관절에 귀속될 때만. |
| `measuredValue` | `measured_value` | `number` | 측정값 (각도 deg / 거리 px). |
| `deductionScore` | `deduction_score` | `number` | IPSF Page 21 절대 감점 (-0.2, -0.5). 체형 ratio 곱하지 않음 (Notebook §3.3). |
| `confidence` | `confidence` | `number` | 0~1. |
| `bodyTypeAdjusted` | `body_type_adjusted` | `boolean` | true = 정규화 좌표에서 측정, false = raw 좌표. |
| `category` | `category` | `'body_type_allowed' \| 'needs_adjustment' \| 'uncertain'` | **Phase 7 신설 (Plan 07-01).** D-07-A1 분류. iteration 2 WR-01 fix: backend 의 6 emit 위치 placeholder `"uncertain"` (fail-safe). Plan 02 classify_findings 재할당. |
| `phase` | `phase` | `string \| null` | **Phase 7 신설 (Plan 07-01).** v1 = 'hold' 단일 (D-07-C1). v2 (Phase 8 또는 Plan 13 Gemini key_moments) 에서 entry/lock/transition/final_shape/release 확장. |
| `bodyTypeInterpretation` | `body_type_interpretation` | `string \| null` | **Phase 7 신설 (Plan 07-01).** Korean canned interpretation — Phase 11 LLM 풍부화 입력 source. CR-01 fix fallback path 시 null. |
| `recommendation` | `recommendation` | `string \| null` | **Phase 7 신설 (Plan 07-01).** Korean canned recommendation — mode prefix prepended. CR-01 fix fallback path 시 unprefixed 단일 문장. |

#### deficitCode enum (6종 — R9 fix: '7 deficits' 옛 표현 금지. poor_transitions v1.5 deferred)

| Enum | 감점 | 설명 |
|---|---|---|
| `knee_toe_alignment` | -0.2 | kneecap → toe 180° 직선 정렬 실패 (IPSF Page 21). |
| `clean_lines` | -0.2 | technique_profile.expects_extension 관절들이 180°-LINE_TOL_DEG 미달. |
| `extension` | -0.2 | 척추/목 라인 평균 각도 < 160° (rounded). |
| `posture` | -0.2 | 좌우 어깨 z 깊이 차이 > shoulder_width × 0.3 (rounded shoulders). |
| `body_placement` | -0.2 | mid_hip 의 폴 축 대비 수평 거리 > shoulder_width × 0.5. |
| `pose_reliability_low` | -0.5 | **C14 fix — 구 `bad_angle` rename.** §8.1 IPSF divergence note 참조. |

### §8.1 IPSF divergence note (C14 fix)

본 시스템의 `pose_reliability_low` deficit code 는 **IPSF Page 21 의 'bad_angle'
judge-observation deduction 과 의미가 다르다.**

- **IPSF 'bad angle'** (Page 21): 심판이 카메라 가림 / 시야 차단으로 인해 선수의
  실행 각도를 **관찰하지 못함**. Judge-observation deduction.
- **Sunity `pose_reliability_low`**: 본 시스템의 RTMW pose-estimation 결과의
  평균 keypoint confidence < `POSE_RELIABILITY_LOW_CONF_THRESHOLD` (0.4) 인 frame 의
  비율 > `POSE_RELIABILITY_LOW_FRAME_RATIO` (0.5) 일 때 emit. Pose-estimator
  reliability metric.

이름 충돌을 피하기 위해 C14 fix (2026-06-08 cross-AI review) 에서 `bad_angle` →
`pose_reliability_low` 로 rename. v1.5 에서 judge-observation 모드 plumbing 시 별도
`bad_angle` enum 신설 가능.

### BodyComparisonReport (W1 — 3 ComparisonType + usedReferenceFallback)

| TS 필드 | Python 필드 | TS 타입 | 설명 |
|---|---|---|---|
| `comparisonType` | `comparison_type` | `ComparisonType` | 'mode1' / 'mode3_first' / 'mode3_progress' (W1 — 3 cases). |
| `bodyNormalizationConfidence` | `body_normalization_confidence` | `number` | 0~1. D-06-U1 confidence-tiered hybrid 게이트. **항상 emit**. |
| `scaleProfile` | `scale_profile` | `ScaleProfile \| null` | 정규화 OFF 시 null. |
| `findings` | `findings` | `BodyComparisonFinding[]` | IPSF 절대 deficit list. |
| `warnings` | `warnings` | `string[]` | 8 enum 중 (아래 표). frozen set 검증 (R8). |
| `referenceMotionId` | `reference_motion_id` | `string \| null` | mode1 + mode3 fallback. |
| `referenceAthleteName` | `reference_athlete_name` | `string \| null` | mode1. |
| `previousAnalysisId` | `previous_analysis_id` | `string \| null` | mode3_progress 일 때 필수 (None → backend ValueError). |
| `usedReferenceFallback` | `used_reference_fallback` | `boolean` | **W1 — Gemini fallback 신호. mode3_first 에서만 true 허용. default false.** |
| `doNotOverCorrect` | `do_not_over_correct` | `string[]` | **Phase 7 신설 (Plan 07-01, D-07-B3).** body_type_allowed 분류 finding 의 카피 aggregate. 결과 화면 "체형 허용 차이" 박스 source. |
| `recommendedFocus` | `recommended_focus` | `string[]` | **Phase 7 신설 (Plan 07-01, D-07-B3).** needs_adjustment + uncertain 분류 finding 의 카피 aggregate. 결과 화면 "개선 필요" 박스 source (Decision 1 — uncertain 통합). |
| `recommendedFocusFallback` | `recommended_focus_fallback` | `string \| null` | **Phase 7 신설 (Plan 07-01, WR-03 fix).** recommendedFocus[] 가 빈 list 일 때 단일 fallback 카피. Phase 12 가 빈 박스 회피용으로 활용. backend `copy_templates._EMPTY_FOCUS_FALLBACK` 박제. |
| `coachCommentHook` | `coach_comment_hook` | `CoachCommentHook \| null` | **Phase 11 신설 (Plan 11-00, COACH-01 / D-02).** 리포트별 LLM 코칭 코멘트 hook. v1 nullable (백필 전/미생성). shape 은 §9.11.7 참조. |

### warnings enum (WR-02 fix — 9종, target_torso_px_missing 신규 추가)

| Enum | 의미 |
|---|---|
| `low_confidence_normalization_off` | confidence < 0.5 시 정규화 OFF (D-06-A4 gate). |
| `foreshortening_off` | foreshortening 감지 시 shoulderHipRatio 폭 보정 OFF (W6). |
| `shoulder_hip_ratio_off` | shoulderHipRatio 폭 보정 OFF (foreshortening 동반). |
| `temporal_variance_high` | 5 핵심 segment temporal variance > 10% (Notebook §4.2). |
| `spatial_dispersion_high` | spatial dispersion > 1.0 penalty (R5 fix 자연 산식). |
| `reference_profile_missing` | reference_profile=None + comparison_type != 'mode3_first'. |
| `fallback_reference_not_found` | mode3_first Gemini fallback 매칭 실패 (caller-injected, R8). |
| `reference_source_pose_missing` | source_keypoints=None — 백필 미완 reference (caller-injected, R2 fix). |
| `target_torso_px_missing` | target_torso_px=None — _extract_target_torso_px 가 측정 실패. 정규화 OFF (WR-02 fix — magic-number fallback 폐기). |

### Universal Principle (D-06-U1) — confidence-tiered hybrid

- **confidence < 0.5** → 안전 fallback: 정규화 OFF + raw 비교 + warning emit +
  mode3_first 도 Page 9 단독.
- **confidence ≥ 0.5** → 분석 가능한 모든 path 활성화: 5 필드 정규화 +
  매칭 reference fallback + 모든 deficit 출력.

---

## §8.2 BodyComparisonSourcePose (Plan 06-01 신설, R2 fix 2026-06-08 round-2 reviews) — Reference 측 대표 hold frame keypoints flat 영속

### 목적

Phase 6 의 `normalize_pose_by_segments` 가 reference 측 keypoints 를 source 로
받아 student 의 target_profile 비율로 reproject. reference 영상을 매 분석마다
재실행하지 않고 백필된 대표 frame 을 영속해 분석 latency 와 비용을 줄임.

### 필드

| TS 필드 | Python 필드 | TS 타입 | 설명 |
|---|---|---|---|
| `jointKeys` | `joint_keys` | `string[]` | RTMW COCO-17 joint 이름 17개. |
| `values` | `values` | `number[]` | **flat float array. length = 4 × jointKeys.length** (COCO-17 의 경우 68). 순서 `[x_0, y_0, z_0, c_0, x_1, y_1, z_1, c_1, ...]`. |
| `frameIndex` | `frame_index` | `number` | 대표 frame 의 원본 index (디버깅용). |
| `torsoPx` | `torso_px` | `number` | mid_shoulder ↔ mid_hip 픽셀 거리 (scale anchor). |
| `confidence` | `confidence` | `number` | 0~1 — 대표 frame 의 평균 keypoint confidence. |
| `measuredAt` | `measured_at` | `number` | unix ms timestamp. |

### Firestore 저장 path

`reference/{motionId}.bodyComparisonSourcePose` (top-level 필드).

### Firestore nested-array 회피 ([[firestore-nested-array-flat]] 박제)

`values` 는 flat float array (nested-array 금지). reshape 책임은 backend
`BodyComparisonSourcePose.to_keypoints_array()` — `(J, 4)` ndarray 반환.

### 백필 procedure

Plan 06-03 Task 2 + Task 3:
- `extract_reference_body_profiles.py` (RunPod GPU 직접 실행) — RTMW 결과의 대표
  hold frame (hold_window 중앙 또는 confidence 최고 frame) 을 추출.
- `seed-reference-body-profile.mjs` (Firebase Admin SDK) — Firestore reference 컬렉션의
  `bodyNormalizationProfile` + `bodyComparisonSourcePose` 두 필드 atomic merge.

### Read 경로 (Plan 06-02 wiring)

`mode1` + `mode3 fallback` path 모두 reference 의 `bodyComparisonSourcePose` 를
fetch 해서 `BodyComparisonSourcePose.to_keypoints_array()` 로 reshape 후
`compare_body_profiles(..., source_keypoints=...)` 인자로 전달.

R2 fix 직접 효과: source_keypoints=None 시 `compare_body_profiles` 는
`'reference_source_pose_missing'` warning 을 emit + `bodyNormalizationConfidence`
하향 + 정규화 OFF (silently 처리 X).

---

## §8.3 Phase 7 분류 룰 (Plan 07-01 신설 — D-07-A1 + D-07-A2 + D-07-U1)

> **2026-06-08 박제 (iteration 2)**: Phase 7 의 차이 분류 (category) 룰 + canned
> copy 매핑 명세. backend `body_normalizer.py` 의 module-level 상수 +
> `copy_templates.py` 33 canned 매핑 + Plan 02 의 `classify_findings()` 진입점.

### Module-level 임계 상수 (backend `body_normalizer.py`)

| 상수 | 값 | 근거 |
|---|---|---|
| `CATEGORY_GATE` | `0.2` | D-07-A1: `abs(deduction_score)` 이 본 값 이하 + `body_type_adjusted=True` → `body_type_allowed`. 초과 시 `needs_adjustment` (D-07-A2 gate 미진입 시). IPSF Page 21 표준 감점 단위 정합. |
| `CATEGORY_CONF_GATE` | `0.5` | D-07-A2 + D-07-U1: `confidence` 또는 `bodyNormalizationConfidence` 가 본 값 미만 → `uncertain` 강제 demotion. Phase 6 D-06-U1 confidence-tiered hybrid 게이트 재사용. |

### 분류 결정 룰 (D-07-A1 + D-07-A2)

| 조건 | category |
|---|---|
| `body_normalization_confidence < 0.5` (global) | `uncertain` (모든 finding 강제 demotion) |
| `finding.confidence < 0.5` (per-finding) | `uncertain` |
| `body_type_adjusted == false` (raw 좌표) | `uncertain` (정규화 안 됨 → 키 차이 섞임) |
| mode3_first + `used_reference_fallback == true` (Decision 1, CR-01 fix) | `uncertain` + 단일 fallback recommendation |
| `body_type_adjusted == true` + `abs(deduction_score) <= CATEGORY_GATE` | `body_type_allowed` |
| `body_type_adjusted == true` + `abs(deduction_score) > CATEGORY_GATE` | `needs_adjustment` |

**fail-safe (WR-01 fix, iteration 2)**: `measure_ipsf_absolute_deficits` 의 6
emit 위치는 모두 `category="uncertain"` placeholder 박제. Plan 02 의
`classify_findings()` 가 본 룰로 재할당. Plan 01 단독 deploy 시에도 모든 finding
이 "AI 확신 부족" 으로 표시 → 사용자가 보정 가이드로 오해할 위험 0.

### 카피 분배 룰 (D-07-B3, Decision 1)

| category | 박스 |
|---|---|
| `body_type_allowed` | `doNotOverCorrect[]` 에 append |
| `needs_adjustment` | `recommendedFocus[]` 에 append |
| `uncertain` | `recommendedFocus[]` 에 append (강사 확인 권유 톤) |

`recommendedFocus[]` 가 빈 list 인 경우 (WR-03 fix): `recommendedFocusFallback` 에
단일 fallback 카피 박제 — Phase 12 가 빈 박스 회피용으로 활용.

### 33 canned coverage 표 (CR-02 fix)

backend `copy_templates._COPY_TEMPLATES` dict literal — `(deficit_code, category,
joint_group)` 3-tuple key → `(interpretation, recommendation)` 2-tuple value.

| deficit_code | joint_group | × category | 합계 |
|---|---|---|---|
| `knee_toe_alignment` | `leg` | 3 | 3 |
| `clean_lines` | `arm` | 3 | 3 |
| `clean_lines` | `leg` | 3 | 3 |
| `clean_lines` | `global` (CR-02 fix) | 3 | 3 |
| `extension` | `torso` | 3 | 3 |
| `extension` | `global` (CR-02 fix) | 3 | 3 |
| `posture` | `arm` | 3 | 3 |
| `posture` | `global` (CR-02 fix) | 3 | 3 |
| `body_placement` | `pole_axis` | 3 | 3 |
| `body_placement` | `global` (CR-02 fix) | 3 | 3 |
| `pose_reliability_low` | `global` | 3 | 3 |
| **합계** | | | **33 카피** |

신규 12 global keys (CR-02 fix path) — Phase 6 의 `joint_key=None` 으로 emit 되는
4 deficit (`clean_lines` / `extension` / `posture` / `body_placement`) 가 Plan 02
의 `_resolve_joint_group` 에서 `"global"` 그룹으로 fallback 되어도 카피 미발견
path 진입 빈도 0 보장.

추가로 `_MODE_PREFIX` (3 항: mode1 / mode3_first / mode3_progress) 는
`recommendation` 에만 prepend. `interpretation` 은 mode 무관 (D-07-D3).

### CR-01 fix — used_reference_fallback path

`render_finding_copy(used_reference_fallback=True)` 호출 시 deficit / category /
joint_group / comparison_type 입력 무관 단일 unprefixed 카피 반환:

```
("이 동작은 기준 영상이 없어, AI 가 IPSF 절대 기준만으로 분석했어요. "
 "강사와 함께 확인 권유드려요.")
```

mode prefix 결합 X (정직성 우위 — Page 9 절대 트랙 단독 적용 상황 명시).

### 카피 톤 룰 (D-07-D1) + 금지 표현 grep gate (D-07-D2)

backend `copy_templates.py` 의 `FORBIDDEN_PHRASES` (research §10.3, 6종) +
`FORBIDDEN_PHRASES_SUNITY` (memory 박제, 3종) AST 기반 grep gate test
(`test_copy_templates_no_forbidden.py`).

| 금지 표현 | 출처 |
|---|---|
| `프로보다 못합` | research §10.3 |
| `정답 자세가 아닙` | research §10.3 |
| `근육량이 부족` | research §10.3 |
| `체형이 안 맞` | research §10.3 |
| `대회 총점` | research §10.3 |
| `감점입니다` | research §10.3 |
| `박제` | memory [[no-baekje-filler]] |
| `%일치` | memory [[mode3-progress-not-similarity]] |
| `유사도` | memory [[mode3-progress-not-similarity]] |

권장 톤 (D-07-D1):
- (a) 가능성 언어 — "~로 보이네요" / "~일 가능성이 있어요" — [[analysis-objectivity-no-human-scores]]
- (b) AI = 강사 보조 도구 — "강사와 함께 확인 권유" — [[feedback-no-echo-confirm]]
- (c) 부위별 원인 — 고관절·후굴·코어·내전근·전완근·광배·흉곽·골반·견갑 — [[feedback-analysis-first]]

---

## §9.0. Coordinate/Scale Contract (Plan 08-00 신설 — Phase 8 pre-contract)

> **2026-06-09 박제 (REVIEWS Cycle 1 R1 + R2 + R3 + R4 blocker 해소)**:
> Phase 8 의 axis distance / contact distance metric 의 좌표공간 + observed
> length denominator + 12 contact primitive 분류 + Layer-1 pre-flight label
> gate 박제. Phase 1 PoleAxis (direction-only) 한계 보강 + Phase 2
> BodyNormalizationProfile.torso_scale (ratio self-reference) 사용 영구 금지.
> Plan 08-01 의 ForceSignalsReport (§9 예정) 는 본 §9.0 contract 위에 박제.

### §9.0.1 CoordinateSpace enum (R1 + Suggestions §1)

| 값 | 의미 |
|---|---|
| `image_2d` | image 평면 normalized 0~1 좌표 (Phase 1 HoughPoleDetector 검출 공간) |
| `pole_aligned` | PoleAxis 정렬 3D 좌표 (PoseFrame.keypoints_3d_pole_aligned) |
| `world_3d` | metric world 3D 좌표 (PoseFrame.keypoints_3d) |
| `unavailable` | 계산 불가 — caller 가 numeric 필드 null + warning 박제 |

모든 distance metric (axis distance / contact distance) 은 `coordinateSpace` 필드를
**필수로 동행**. `'unavailable'` 시 numeric 필드 null + warning
`'pole_line_missing'` 또는 `'scale_unavailable'` 박제.

### §9.0.2 ContactPrimitiveKind enum (R3)

| 값 | 의미 |
|---|---|
| `keypoint` | COCO-17 직접 가용 keypoint (10 point) |
| `segment` | 두 keypoint 의 mid-segment 거리로 산출 (2 point: inner_thigh) |
| `region_proxy` | 다중 keypoint midpoint region proxy (1 point: hip = 좌우 hip midpoint) |

§9.0.7 의 12 contact 분류 표가 각 entry 의 kind 필드 결정 source.

### §9.0.3 PoleLine2D (R1)

image 평면 (normalized 0~1) 의 폴 축 직선. Phase 1 HoughPoleDetector 의 image-평면
검출 결과 표현 contract.

| 필드 | 타입 | 의미 |
|---|---|---|
| `pointImage` / `point_image` | `[number, number]` / `tuple[float, float]` | 직선 위의 한 점 (x, y), normalized 0~1 |
| `directionImage` / `direction_image` | `[number, number]` / `tuple[float, float]` | 방향 단위벡터 (dx, dy), norm ≈ 1.0 |
| `confidence` | `number` / `float` | 검출 신뢰도 [0.0, 1.0] |
| `source` | `'detected' \| 'vertical_fallback'` | 'detected' = Hough 성공, 'vertical_fallback' = 수직 가정 |

박제 위치:
- TS: `app/src/types/analysis.ts` PoleLine2D interface (Plan 08-00).
- Python: `backend/shared/python/sunity_shared/analysis/pole_geometry.py` PoleLine2D
  (frozen dataclass).

### §9.0.4 PoleAxisMeasurement (R1 blocker 해소)

axis_3d (PoleAxis, direction-only) + line (image 2D position) 묶음.
PoleAxis 의 direction-only 한계를 image 평면 line 정보로 보강.

| 필드 | 타입 | 의미 |
|---|---|---|
| `axis3d` / `axis_3d` | `PoleAxis` | Phase 1 박제 본체 (direction-only). 본체 변경 0 |
| `line` | `PoleLine2D \| null` | image 2D 선 (fallback 시 null) |
| `coordinateSpace` / `coordinate_space` | `CoordinateSpace` | distance 산출 공간. line=null ↔ 'unavailable' 강제 invariant |
| `frameIndex` / `frame_index` | `number \| null` / `int \| None` | video-level (Phase 1 D-10) 시 null |

**invariant (Python `__post_init__` 강제)**: `line=None` ↔ `coordinate_space='unavailable'`.
위반 시 ValueError raise. caller 가 line None 시 axis distance 필드 null +
warning `'pole_line_missing'` 박제 강제.

helper:
- `build_pole_axis_measurement(axis_3d, line, *, frame_index=None)` — line 가용
  여부로 coordinate_space 자동 결정.
- `point_to_pole_line_distance_2d(point, line)` — image 2D 점-직선 수직거리.

### §9.0.5 median_torso_length helper (R2 blocker 해소)

observed shoulder-hip midpoint Euclidean distance median.

```python
def median_torso_length(
    pose_frames: list[PoseFrame],
    *,
    space: Literal["image_2d", "pole_aligned", "world_3d"],
) -> float | None: ...
```

space 분기:
- `'image_2d'`     → `PoseFrame.keypoints_2d` (Keypoint2D)
- `'pole_aligned'` → `PoseFrame.keypoints_3d_pole_aligned` (Keypoint3DAligned)
- `'world_3d'`     → `PoseFrame.keypoints_3d` (Keypoint3D)

각 frame 별 산출:
```
shoulder_mid = (left_shoulder + right_shoulder) / 2
hip_mid      = (left_hip + right_hip) / 2
torso_length = euclidean(shoulder_mid, hip_mid)
```

valid frame (4 required keypoint 모두 존재 + finite length) < 5 시 None 반환 —
caller 가 warning `'scale_unavailable'` 박제.

**CRITICAL drift defense (R2)**: `BodyNormalizationProfile.torso_scale` 은 segment
비율 (1.0 self-reference) — observed length 가 아니다. distance metric 의
denominator 로 사용 **영구 금지**. `body_scale.py` 본체는
`BodyNormalizationProfile` 을 영구 import 하지 않는다 — AST gate test 가 검증.

### §9.0.6 Pre-flight 25-timestamp label gate (R4 blocker 해소)

Layer-1 motion-agnostic 휴리스틱의 5 phase boundary 검증 gate.

| 항목 | 값 |
|---|---|
| 라벨링 범위 | 5 reference 영상 × 5 phase boundary = 25 timestamp |
| 5 영상 | ref-invert / ref-foxtop / ref-foxtop-split / ref-climb / ref-sideway-spin |
| 5 phase boundary | entry_start / lock_start / transition_start / final_shape_start / hold_start |
| 일치 기준 | delta_ms = abs(belle - layer1) ≤ 200ms |
| PASS 기준 | 25 timestamp 중 ≥ 80% (20/25 이상) 일치 |
| PASS → | Layer 1 confidence='medium' 승급 |
| FAIL → | Layer 1 confidence='low' 강제 + warning 'preflight_label_gate_failed' |

박제:
- spec: `.planning/phases/08-jerk-jitter/preflight/PREFLIGHT-LABEL-SPEC.md`
- template: `.planning/phases/08-jerk-jitter/preflight/preflight_label_template.csv`

FAIL 시 unwind path = Plan 08-03 의 `RECOGNIZER_BACKEND` env unset +
`FORCE_SIGNALS_LAYER2_ENABLED` env unset (D-08-E3 정합). 분석 pipeline 자체는
영향 0 (Layer 1 confidence='low' 박제로 downstream 가 보수적 추론).

### §9.0.7 12 contact point × ContactPrimitiveKind 분류 표 (R3)

Plan 08-01 의 expected_contact_points yaml 박제 시 본 표가 kind 필드 source.

| Contact Point | Kind | 산출 방식 |
|---|---|---|
| `left_hand` | `keypoint` | COCO-17 left_wrist 직접 |
| `right_hand` | `keypoint` | COCO-17 right_wrist 직접 |
| `left_ankle` | `keypoint` | COCO-17 left_ankle 직접 |
| `right_ankle` | `keypoint` | COCO-17 right_ankle 직접 |
| `left_foot` | `keypoint` | pole_extension_landmarks left_toe 또는 left_ankle |
| `right_foot` | `keypoint` | pole_extension_landmarks right_toe 또는 right_ankle |
| `left_knee` | `keypoint` | COCO-17 left_knee 직접 |
| `right_knee` | `keypoint` | COCO-17 right_knee 직접 |
| `left_inner_thigh` | `segment` | left_hip ↔ left_knee 의 mid-segment 거리 |
| `right_inner_thigh` | `segment` | right_hip ↔ right_knee 의 mid-segment 거리 |
| `hip` | `region_proxy` | left_hip + right_hip midpoint |
| `unknown` | `keypoint` | motion_id 미인식 fallback (Phase 5 unrecognized) — keypoint 무관 |

박제 메모:
- [[single-camera-first-multi-view-last]] — coordinateSpace='image_2d' 우선 박제.
- [[mvp-simple-pilot-quality]] — line 미가용 시 distance=null + warning (graceful).
- [[scoring-dimensions-ipsf]] — pre-flight label = phase boundary 시각 박제
  (수치 score 아님, [[analysis-objectivity-no-human-scores]] 정합).

---

## §9. ForceSignalsReport (Plan 08-01 revised — REVIEWS Cycle 1 반영 — FORCE-01 신호 layer)

Phase 8 의 산출 = Phase 9 의 `inferForceDirectionPattern` 신호 layer + 5단계
motion-phase 분할 + 가림 스무딩 + confidence 가중 처리. **Plan 08-00 §9.0
contract 위에 박제** — `CoordinateSpace` / `ContactPrimitiveKind` /
`PoleAxisMeasurement` / `median_torso_length` helper 의존.

3-way lockstep:
- TS: `app/src/types/analysis.ts` (ForceSignalsReport + 4 metric interface +
  PhaseBoundary + ContactPoint enum + MotionPhase enum)
- Python placeholder: `backend/shared/python/sunity_shared/models.py` (Plan 08-02
  신설 force_signals.py import 활성화)
- 본 문서 §9 — 단일 atomic commit 박제.

REVIEWS Cycle 1 반영 5 schema 변경:
- **R1**: PoleAxis position 부재 → PoleAxisMeasurement 박제 (Plan 08-00) +
  BodyLineTiltMetric distance 필드 nullable.
- **R2**: BodyNormalizationProfile.torso_scale 오용 → observed median_torso_length
  helper + BodyLineTiltMetric.scaleDenominator 동행.
- **R3**: ContactStabilityMetric = evidence-with-confidence (boolean truth X).
- **R4**: PhaseBoundary.preflightLabelGatePassed nullable 신설.
- **R5**: StabilityMetric.jerkUnit='deg_per_sec_cubed' — FPS 정규화 박제.

### §9.1 Enum / Type Alias

| 타입 | 값 | 의미 |
|---|---|---|
| `MotionPhase` | `'entry' \| 'lock' \| 'transition' \| 'final_shape' \| 'hold'` | 5단계 motion-phase (research 02 §6/§7) |
| `DeviationDirection` | `'up' \| 'down' \| 'left' \| 'right' \| 'outward' \| 'inward' \| 'unknown'` | 이탈 방향 (좌표공간 기준) |
| `SeverityLevel` | `'low' \| 'medium' \| 'high'` | 측정값 자체 크기 |
| `MetricConfidence` | `'low' \| 'medium' \| 'high'` | 측정값 신뢰도 (severity 와 별 차원) |
| `ContactPoint` | 12 분류 — `left_hand` / `right_hand` / `left_inner_thigh` / `right_inner_thigh` / `left_knee` / `right_knee` / `left_foot` / `right_foot` / `left_ankle` / `right_ankle` / `hip` / `unknown` | docs §9.0.7 12 분류 표 정합 |

### §9.2 PhaseBoundary

5단계 motion-phase 경계 (Layer 1 휴리스틱 + Layer 2 Gemini key_moments 합성).

| 필드 (TS / Python) | 타입 | 의미 |
|---|---|---|
| `phase` | `MotionPhase` | 어느 단계 |
| `startFrameIdx` / `start_frame_idx` | `number` / `int` | 시작 frame index |
| `endFrameIdx` / `end_frame_idx` | `number` / `int` | 종료 frame index (exclusive) |
| `startMs` / `start_ms` | `number` / `int` | 시작 timestamp ms |
| `endMs` / `end_ms` | `number` / `int` | 종료 timestamp ms |
| `confidence` | `MetricConfidence` | 경계 신뢰도 |
| `source` | `'heuristic' \| 'gemini_assisted' \| 'heuristic_fallback'` | Layer 1 단독 / Layer 2 합성 / motion_id=None fallback |
| `preflightLabelGatePassed` / `preflight_label_gate_passed` | `boolean \| null` | **REVIEWS R4 신설** — pre-flight 25-timestamp label gate 결과. `null` = gate 미실행 (default), `true` = PASS (≥80%, Layer 1 confidence='medium' 승급), `false` = FAIL (Layer 1 confidence='low' 강제 + warning `preflight_label_gate_failed`). |

### §9.3 BodyLineTiltMetric

중심축 이탈 metric — phase 별 측정. **Phase 8.1 박제 (2026-06-09)**: distance 차원
hard break (IPSF Code of Points 글로벌 distance 항목 부재, NotebookLM citation 9).
tilt-only metric.

| 필드 (TS / Python) | 타입 | 의미 |
|---|---|---|
| `phase` / `phase` | `MotionPhase` | 어느 단계 |
| `shoulderTilt` / `shoulder_tilt` | `number \| null` | degrees, rotation-only, pole_aligned 좌표계 |
| `hipTilt` / `hip_tilt` | `number \| null` | degrees, rotation-only, pole_aligned 좌표계 |
| `severity` / `severity` | `SeverityLevel` | max(shoulderTilt severity, hipTilt severity) |
| `confidence` / `confidence` | `MetricConfidence` | phase frame reliability ratio |
| `warnings` / `warnings` | `string[]` / `list[str]` | e.g. `'tilt_unavailable'`, `'tilt_thresholds_fallback'`, `'phase_8_1_wave_0_transitional'` |

**박제 메모 (Phase 8.1)**: tilt 값은 rotation-only / origin-invariant (RESEARCH §4.3).
shoulderTilt / hipTilt = arcsin(|Δz|/||Δ||) (pole_aligned 좌표계). 미가용 시 두 tilt
모두 null + severity='low' + warning `'tilt_unavailable'`. per RESEARCH §4 α-4 +
IPSF NotebookLM citation 9.

### §9.4 StabilityMetric

흔들림 metric — phase 별 측정. REVIEWS R5 박제.

| 필드 (TS / Python) | 타입 | 의미 |
|---|---|---|
| `phase` | `MotionPhase` | 어느 단계 |
| `jitterScore` / `jitter_score` | `number` / `float` | degrees (frame inter median wobble). `dimensions.stability_wobble()` helper 박제. |
| `jerkScore` / `jerk_score` | `number` / `float` | **deg/sec^3** (FPS-normalized 3차 미분). |
| `jerkUnit` / `jerk_unit` | `'deg_per_sec_cubed'` (literal) | **REVIEWS R5 신설** — 단위 contract. |
| `holdStabilityScore` / `hold_stability_score` | `number \| null` | hold phase 안 stability score (0~100). hold 외 phase 시 null. |
| `unstableBodyParts` / `unstable_body_parts` | `string[]` / `list[str]` | `stability_wobble_by_joint` 임계 초과 관절 list |
| `severity` | `SeverityLevel` | 측정값 크기 |
| `confidence` | `MetricConfidence` | 신뢰도 |
| `warnings` | `string[]` / `list[str]` | warning code |

**박제 메모 (R5)**: `jerkScore` 단위 = `deg/sec^3` (NOT `deg/frame^3`). Plan
08-02 의 `_compute_jerk` 가 `dt=1/fps` 정규화 박제 — 9 fps vs 18 fps 동일 값 강제.
정규화 적용 시 warning `fps_normalization_applied` emit.

### §9.5 ContactStabilityMetric

접촉점 안정성 metric — (contact_point, phase) 별 측정. REVIEWS R3 박제
(evidence-with-confidence, NOT boolean truth).

| 필드 (TS / Python) | 타입 | 의미 |
|---|---|---|
| `phase` | `MotionPhase` | 어느 단계 |
| `contactPoint` / `contact_point` | `ContactPoint` | 12 분류 (docs §9.0.7) |
| `measurementKind` / `measurement_kind` | `ContactPrimitiveKind \| null` | **REVIEWS R3 신설** — Plan 08-00 §9.0.2 (keypoint / segment / region_proxy). motion_id 미인식 시 null. |
| `estimatedStable` / `estimated_stable` | `boolean \| null` | **REVIEWS R3 변경** — evidence 부족 시 null (v1 boolean truth X). |
| `distanceToPoleNorm` / `distance_to_pole_norm` | `number \| null` | **REVIEWS R3 신설** — observed_torso_length 정규화. line 미가용 시 null. |
| `nearPoleRatio` / `near_pole_ratio` | `number \| null` | **REVIEWS R3 신설** — phase 안 frame 중 distance <= threshold 비율. |
| `lostNearPoleAtMs` / `lost_near_pole_at_ms` | `number \| null` | **REVIEWS R3 변경** — v1 의 `lostContactAtMs` 명칭 변경 (boolean truth 가 아닌 distance evidence 박제 정합). |
| `coordinateSpace` / `coordinate_space` | `CoordinateSpace` | distance 산출 좌표공간 |
| `severity` | `SeverityLevel` | 측정값 크기 |
| `confidence` | `MetricConfidence` | 신뢰도 |
| `warnings` | `string[]` / `list[str]` | warning code |

**박제 메모 (R3)**: v1 = evidence-with-confidence (NOT boolean truth).
- `estimatedStable=null` → evidence 부족 (line 미가용 / motion_id 미인식 등).
- `measurementKind=null` → motion_id 미인식 fallback (Phase 5 unrecognized).
- distance evidence 만 emit 시 warning `contact_evidence_only`.

### §9.6 ForceSignalsReport

Phase 8 산출 umbrella — `AnalysisResult.forceSignalsReport` 로 저장.

| 필드 (TS / Python) | 타입 | 의미 |
|---|---|---|
| `version` | `string` / `str` | schema 버전 (v1 = "1.0") |
| `overallConfidence` / `overall_confidence` | `MetricConfidence` | 전체 신뢰도 (4 metric confidence 조합) |
| `warnings` | `string[]` / `list[str]` | top-level warning code |
| `phaseBoundaries` / `phase_boundaries` | `PhaseBoundary[]` | 5단계 경계 |
| `axisMetrics` / `axis_metrics` | `BodyLineTiltMetric[]` | phase × 1 |
| `stabilityMetrics` / `stability_metrics` | `StabilityMetric[]` | phase × 1 |
| `contactMetrics` / `contact_metrics` | `ContactStabilityMetric[]` | (contact_point × phase) cross product |

### §9.7 AnalysisResult.forceSignalsReport

`AnalysisResult` 에 `forceSignalsReport?: ForceSignalsReport | null` 추가 박제.
Plan 08-02 wiring 에서 backend pipeline 이 채움. nullable — Phase 6/7 path 회귀 0.

### §9.8 Warning Code Enum (20)

ForceSignalsReport 의 `warnings` + 각 metric 의 `warnings` 가 공유하는 enum.

| 그룹 | Code | 의미 |
|---|---|---|
| **기존 13 (Plan 08-01 v1)** | | |
| | `occlusion_high_in_phase` | phase 안 가림 frame > 50% |
| | `layer2_unavailable` | Gemini Layer 2 사용 불가 (env unset) |
| | `layer_disagreement_minor` | Layer 1 vs 2 시간 차이 200~500ms |
| | `layer_disagreement_major` | Layer 1 vs 2 시간 차이 > 500ms |
| | `layer2_call_failed` | Gemini 호출 실패 (timeout/error) |
| | `motion_unrecognized` | Phase 5 motion_id=None |
| | `motion_unrecognized_layer1_only` | motion_id=None + Layer 1 단독 confidence='low' |
| | `abnormal_release_during_hold` | hold 구간 안 contact 풀림 |
| | `partial_motion_video` | 5단계 중 일부만 검출 |
| | `video_too_short` | 분석 frame < 최소 임계 |
| | `heavy_occlusion` | 영상 전체 가림 > 50% |
| | `entry_not_detected` | entry phase 검출 실패 |
| | `all_frames_unreliable` | reliability='low' frame 비율 압도 |
| **Cycle 1 신설 6 (REVIEWS R1~R5)** | | |
| | `pole_line_missing` | **R1** — PoleLine2D 미가용 (axis distance null) |
| | `scale_unavailable` | **R2** — median_torso_length 미가용 (denominator null) |
| | `preflight_label_gate_failed` | **R4** — gate FAIL (Layer 1 confidence='low' 강제) |
| | `fps_normalization_applied` | **R5** — jerk_score FPS-normalized 적용 |
| | `contact_evidence_only` | **R3** — distance evidence 만 emit (estimatedStable=null) |
| | `coordinate_space_unavailable` | **R1/R2** — coordinateSpace='unavailable' |
| **Cycle 2 신설 1** | | |
| | `preflight_gate_pending` | **Cycle 2 §3 MEDIUM** — pre-flight gate 미실행 default (preflight CSV 채워지지 전) |
| **Phase 4 신설 2 (Plan 04-01, POSE-03 D-08)** | | |
| | `ai_synthesis_failed` | 합성 어댑터 실패 → graceful degrade 발동 (1차 RTMW 결과 유지) |
| | `ai_synthesis_partial` | 일부 frame/joint 만 합성 성공 (indeterminate 응답 다수) |

### §9.8.1 AiSynthesisMeta (Phase 4 신설)

Plan 04-01 (POSE-03 D-08 / R3 / R5 fix) — `AnalysisResult.aiSynthesisMeta?` 옵셔널 필드.
사용자에겐 블랙박스 (D-05). UI 는 `hasSynthesisWarning(result)` 로 warnings 만 surface.

Public warning surface (canonical, BLOCKER-3):
  · `aiSynthesisMeta.warnings: SynthesisWarningCode[]` — `ai_synthesis_failed` /
    `ai_synthesis_partial` 두 enum 만 박힘.
  · `aiSynthesisMeta.debugWarnings: string[]` — adapter 의 raw reason
    (`gemini_api_error` / `gemini_parse_error` / `g4_reference_guard` /
    `exception` / `invalid_input_shape` / `model_resolve_failed` 등) 보존. UI
    노출 금지 — 회귀 추적 + audit 전용.

| Field (camelCase) | Type | Notes |
|---|---|---|
| `synthesizedFrameCount` | `number` | 합성 시도/적용한 frame 수 (T 인덱스 list 크기) |
| `synthesizedJointKeys` | `string[]` | 합성 대상 COCO-17 keypoint 이름 부분집합 |
| `synthesisPath` | `'gemini_view' \| 'cylindrical_mesh' \| 'none'` | D-18 PRIMARY/SECONDARY/skipped |
| `degraded` | `boolean` | true 시 1차 RTMW 결과 그대로 (graceful degrade) |
| `modelId` | `string` | 예: `gemini-3.5-flash` / `gemini-3.1-pro-preview` |
| `modelVersion` | `string` | 예: `v1` (Phase 4 박제 시점 버전 tag) |
| `promptHash` | `string` | `OCCLUDED_JOINT_REASONING_PROMPT` sha256 앞 16자 |
| `framesConsidered` | `number` | 합성 대상 후보 frame 수 |
| `framesSynthesized` | `number` | 실제 합성된 frame 수 |
| `geminiCalls` | `number` | Gemini 호출 횟수 |
| `framesSkipped` | `number` | skip 된 frame 수 |
| `framesFailed` | `number` | 실패 frame 수 |
| `estCostUsd` | `number` | 추정 비용 (USD) |
| `warnings` | `SynthesisWarningCode[]` | public enum — UI surface |
| `debugWarnings` | `string[]` | raw reason — audit only |

3-way lockstep:
  · `backend/shared/python/sunity_shared/models.py` — `SYNTHESIS_WARNING_CODES` frozenset.
  · `app/src/types/analysis.ts` — `SynthesisWarningCode` union + `AiSynthesisMeta` interface.
  · 본 §9.8.1 표.

### §9.8.2 joints3d flat 저장 (Phase 4 신설)

Plan 04-01 (R3 fix) — `AnalysisResult.joints3d?` 옵셔널 필드. 04-02 가
`doc.result.joints3d` 를 `reshapePose3dData` 로 읽어 3D PoseViewer 가 소비한다.
`angles` (관절각, `AnalysisDoc` top-level quirk) 와 별개로 `result` 내부 박제.

| Field (camelCase) | Type | Notes |
|---|---|---|
| `joints3d` | `number[]` | flat — 길이 = `joints3dFrames * 17 * 3` |
| `joints3dKeys` | `string[]` | COCO-17 17 keypoint 이름 (length 17) |
| `joints3dFrames` | `number` | T |
| `coordDim` | `number` | =3 (명시적 저장) |
| `space` | `'rtmw3d' \| 'pole_aligned'` | `to_coco17_array` 산출 → `pole_aligned` |

Firestore 저장 제약 ([[firestore-nested-array-flat]]):
  · 모든 필드는 flat — nested list 금지.
  · `firestore_admin.complete_analysis` 가 `_validate_joints3d_payload` 통과 강제
    (flat length == frames\*len(keys)\*coord_dim / finite only / coord_dim==3 /
    space in {"rtmw3d","pole_aligned"} — BLOCKER-4).

### §9.9 D-결정 요약

본 §9 박제 = 08-CONTEXT.md 의 D-08-A1~D-08-U3 + D-08-E1~D-08-E4 + Plan 08-00 의
R1~R4 정합. 핵심:

- **D-08-A1**: 5단계 분할 (hold 단일 거부 — 분석 정확도).
- **D-08-A2 + D-08-E4**: Layer 1 (baseline) + Layer 2 (Gemini) 하이브리드.
  motion_id=None 시 Layer 1 단독 confidence='low'.
- **D-08-B1~B5**: Proximity + 시간 패턴 + motion_id 별 yaml. Plan 08-01 contact_points.yaml.
- **D-08-C1~C4**: 기존 dimensions helper 재사용 + jerk 신설 + force_signals.py 모듈.
- **D-08-D1~D4**: body-scale 정규화 + 도메인 룰 fixed 임계 (정은지 분포 X).
- **D-08-U1~U3**: 가림 스무딩 + 모든 metric 에 confidence + 3-way lockstep.
- **D-08-E1**: `_validate_dict_only_scalars` Option A (list[scalar] 허용) —
  Plan 08-03 박제.
- **D-08-E2**: `keep_local_video` = helper `_should_keep_local_video()` —
  Plan 08-03 박제.
- **D-08-E3**: Layer 2 wiring + pre-flight gate unwind path.

### §9.10 Plan 08-00 contract dependency

본 §9 의 모든 distance/scale metric 은 **Plan 08-00 §9.0** contract 위에 박제:

- `CoordinateSpace` (§9.0.1) — distance metric 의 `coordinateSpace` 필드.
- `ContactPrimitiveKind` (§9.0.2) — ContactStabilityMetric 의 `measurementKind`.
- `PoleAxisMeasurement` (§9.0.4) — axis distance 산출 source. line=null ↔
  coordinate_space='unavailable' invariant 강제.
- `median_torso_length` helper (§9.0.5) — `scaleDenominator='observed_torso_length'`
  의 산출 source. `BodyNormalizationProfile.torsoScale` 영구 사용 금지 (R2 drift
  defense).
- Pre-flight 25-timestamp label gate (§9.0.6) — `preflightLabelGatePassed`
  필드 source.
- 12 contact 분류 표 (§9.0.7) — `ContactPoint` enum + `measurementKind` 분류 source.

### §9.11 ForcePatternInference (Phase 9 신설)

본 섹션은 Phase 9 (`ForceDirectionPattern + 실패 원인 후보 3개`) 가 산출하는 추론 layer 의 contract.

#### §9.11.1 Enum

| Alias | Values |
|-------|--------|
| `ForceDirectionPattern` | `pull` / `push` / `brace` / `rotate` / `release` / `unknown` (`rotate` = v2 deferred, Phase 9 backend emit 0 — Open Q 1) |
| `ForceSourceSignal` | `axis_tilt` / `pelvis_drop` / `late_contact` / `high_jitter` / `high_jerk` / `abnormal_release` |
| `ModeContext` | `mode1` / `mode3_first` / `mode3_progress` |

#### §9.11.2 ForcePatternFinding (8 필드)

| Field (camelCase / snake_case) | Type | Notes |
|--------------------------------|------|-------|
| `pattern` | `ForceDirectionPattern` | D-09-A1 매핑 |
| `phase` | `MotionPhase` | §9.2 PhaseBoundary 정합 |
| `sourceSignal` / `source_signal` | `ForceSourceSignal` | D-09-A1 6 종 |
| `reason` | `string` (EN) | LLM input 용 1 sentence — D-09-D1 |
| `interpretation` | `string` (KO canned) | D-09-D2 18 canned mapping, "가능성" 언어 (D-09-D3 grep gate) |
| `confidence` | `number` ∈ [0, 1] | D-09-A5 산식 |
| `jointHint` / `joint_hint` | `string \| null` | 부위 키워드 (코어 / 고관절 / 광배 / 내전근 / null) — D-09-D1 / Assumption A3 |
| `warnings` | `string[]` | signal-specific (예: `axis_signal_unavailable`) — list[str] (Firestore scalar list OK) |

#### §9.11.3 ForcePatternInference (5 필드)

| Field | Type | Notes |
|-------|------|-------|
| `version` | `string` | "1.0" 초기 (non-empty) |
| `findings` | `ForcePatternFinding[]` | 길이 [0, 3] — D-09-B4 fabrication 금지 |
| `overallConfidence` / `overall_confidence` | `MetricConfidence` (`low`/`medium`/`high`) | 0 finding 시 `'low'` + warning |
| `modeContext` / `mode_context` | `ModeContext` | pipeline `_process` 가 산출 (D-09-D6) |
| `warnings` | `string[]` | umbrella (예: `no_significant_force_pattern_signal`, `phase_unavailable_for_inference`, `axis_signal_unavailable`) — Python dataclass field 순서상 마지막 (default_factory=list, R1 정합) |

#### §9.11.4 Firestore 저장 위치

- `users/{uid}/analyses/{analysisId}.result.forcePatternInference` — `_validate_force_pattern_inference` scoped validator 박제 ([[firestore-nested-array-flat]] 정합).
- `complete_analysis(..., force_pattern_inference=...)` kwarg 로 write (Wave 1 Plan 09-02 wiring).

#### §9.11.5 Phase 책임 경계

- Phase 9 = canned KO interpretation 단독 (Layer 2 / Gemini 영구 차단 — D-09-C1).
- Phase 11 (CoachCommentHook) = `findings[].interpretation` 위 LLM 자연어 풍부화 (Gemini 자연어 번역만).
- Phase 12 = `confidence` / raw 수치 (예: `shoulder_tilt 87°`) UI 노출 책임.
- Phase 9 자체는 UI hint 없음 (D-09-D5).

#### §9.11.6 Warning Code (Phase 9 신설)

| Code | Trigger |
|------|---------|
| `phase_unavailable_for_inference` | phaseBoundaries 에 해당 phase 없음 (D-09-A4) |
| `axis_signal_unavailable` | top-level `forceSignalsReport.warnings` ∋ `axis_metric_transitional` (R4 report tier) OR axisMetric.warnings ∈ {`phase_8_1_wave_0_transitional`, `tilt_unavailable`, `tilt_thresholds_fallback`} (R4 per-metric tier) (D-09-A2 / RESEARCH Pitfall 2) |
| `no_significant_force_pattern_signal` | 6 signal 모두 detection 미통과 (D-09-B4) — fabrication 금지 |

*Phase 9 추가: 2026-06-10 — ForcePatternInference + ForcePatternFinding 신설. D-09-A1~U6 박제. 본 contract = TS `analysis.ts` + Python `force_pattern.py` 와 atomic commit lockstep (D-09-U1).*

#### §9.11.7 CoachCommentHook (Phase 11 신설 — COACH-01)

Phase 11 이 신설한 per-report LLM 코칭 코멘트 hook (D-02). `ForcePatternInference` 와 `BodyComparisonReport` 각각에 `coachCommentHook?` 로 부착 (v1 nullable — 백필 전/미생성).

| TS 필드 | Python 필드 | TS 타입 | 설명 |
|---|---|---|---|
| `autoFindingsSummary` | `auto_findings_summary` | `string` | LLM 자연어 요약 (findings interpretation 번역). non-empty. |
| `openQuestionsForCoach` | `open_questions_for_coach` | `string[]` | 강사에게 던지는 질문. **list[str] 전용** (nested array 금지). 빈 list 허용. |
| `suggestedCues` | `suggested_cues` | `string[]` | 수강생용 큐. **list[str] 전용** (nested array 금지). 빈 list 허용. |
| `coachComment` | `coach_comment` | `string \| null` | **v2 강사 콘솔 입력 — v1 항상 null (D-06).** |
| `reviewedBy` | `reviewed_by` | `string \| null` | **v2 리뷰어 — v1 항상 null (D-06).** |
| `sourceReport` | `source_report` | `string \| null` | provenance scalar (`forcePatternInference` / `bodyComparisonReport`) — v2 콘솔 집계 (D-02). |

- **부착 위치:** `forcePatternInference.coachCommentHook` + `bodyComparisonReport.coachCommentHook` (per-report 단위, D-02).
- **Firestore 저장:** Wave 1 (Plan 11-01) 이 전용 `_validate_coach_comment_hook` scoped validator 박제 — list[str] 전용 게이트 (force path + body precheck). `coachCommentHook` 안 `openQuestionsForCoach` / `suggestedCues` 의 list[dict] / nested list reject ([[firestore-nested-array-flat]] 정합).
- **모듈 분리 (HIGH-3):** `coach_hook.py` = frozen dataclass + pure validator only (finding 클래스 import 0 — 순환 차단). canned/builder 로직은 `coach_hook_builder.py`.
- **책임 경계:** Phase 11 = `findings[].interpretation` 위 LLM 자연어 풍부화 (Gemini 자연어 번역만 — 점수/좌표/판정/도(degree)/% mint 금지, D-04/D-05). coach_comment/reviewed_by UI/입력은 v2 강사 콘솔.

*Phase 11 추가: 2026-06-17 — CoachCommentHook 신설 (Wave 0 = TS interface + Python frozen dataclass + models.py re-export + docs §9.11.7/§8 단일 atomic commit). COACH-01 SC#1 / D-02 / D-06. Wave 1 (Plan 11-01) 이 GeminiCoachHookWriter + builder + Firestore 전용 validator + pipeline wiring 박제.*

### §9.12 KeypointReport (Phase 12 / FEED-01 + VIS-01)

본 섹션은 Phase 12 Wave 0B (Plan 12-01) 가 신설한 KeypointOverlay 소비 schema. Phase 9 §9.11 mirror — single atomic commit (D-12-U1 / D-09-U1).

- **TS source:** `app/src/types/analysis.ts::KeypointReport` (10 필드, R10 + R7 iter-2 정합)
- **Python source:** `backend/shared/python/sunity_shared/analysis/keypoint_frame.py::KeypointReport` (frozen dataclass + `__post_init__` validator)
- **Firestore 저장 경로:** `users/{uid}/analyses/{analysisId}.result.keypointReport` — `_validate_keypoint_report` scoped validator 박제 ([[firestore-nested-array-flat]] 정합)
- **camelCase 변환:** `_dataclass_to_camel_case_dict` (pipeline/app.py) 가 `axis_data` → `axisData`, `axis_mask` → `axisMask` 자동 변환

#### §9.12.1 KeypointName Literal (R11 — 8 body keypoint, axis 제외)

`left_shoulder` / `right_shoulder` / `left_hip` / `right_hip` / `left_knee` / `right_knee` / `left_hand` / `right_hand`

- `left_hand` / `right_hand` 는 COCO-17 의 `left_wrist` / `right_wrist` 매핑 (loose hand 박제, v2 wrist 신설은 후속 plan).
- axis 는 별도 `axisData` field (R2 정합 — UI 자체 계산 차단, A7 해소).

#### §9.12.2 KeypointReport (10 필드)

| Field (camelCase / snake_case) | Type | Notes |
|--------------------------------|------|-------|
| `version` | `string` | "1.0" 초기 (non-empty) |
| `joints` | `KeypointName[]` | length = J = 8 (`_KEYPOINT_NAMES` tuple) — R11 |
| `frames` | `number` | T (>= 0) |
| `fps` | `number` | > 0 — R3 정합, default 제거 (운영 값 9.0) |
| `data` | `number[]` | flat T × J × 2 — H3 iter-4 finite only (NaN/Inf reject) |
| `confidence` | `number[]` | flat T × J — R6 visibility source, H3 iter-4 finite + [0, 1] |
| `reliability` | `('high'/'medium'/'low')[]` | length T, item enum |
| `axisData` / `axis_data` | `number[]` | R2 + R7 iter-2 — flat T × 3 × 2 polyline (shoulder_mid / hip_mid / knee_mid?). **finite only — NaN/Inf 영구 0회**. knee_mid 미가용 frame 은 (0.0, 0.0) placeholder |
| `axisMask` / `axis_mask` | `boolean[]` | R7 iter-2 신설 — flat T × 3 strict bool (int 0/1 reject). knee_mid 미가용 frame 은 mask[2] = false. UI 가 mask 참조해서 polyline 2-point or 3-point 분기 |
| `warnings` | `string[]` | non-empty str only |

#### §9.12.3 axisData polyline + axisMask 산출 (R2 + R7 iter-2)

- 산출 위치: `backend/shared/python/sunity_shared/analysis/dimensions.py::compute_axis_frames` (Wave 0A T4 박제).
- 입력: `pose_frames` 의 각 `keypoints_2d` dict.
- 출력 형식 (frame i):
  - `axisData[i*6 .. i*6+5]` = `(shoulder_mid.x, shoulder_mid.y, hip_mid.x, hip_mid.y, knee_mid.x or 0.0, knee_mid.y or 0.0)`
  - `axisMask[i*3 .. i*3+2]` = `(True, True, knee_mid is not None)`
- 어깨 또는 골반 keypoint 누락 시 `axisData = (0.0)*6` + `axisMask = (False, False, False)` (전 frame 누락 의미).
- **NaN 영구 0회** — JSON / Firestore / SVG NaN edge case 우회 (R7 iter-2).

#### §9.12.4 frame index lookup

Wave 1 UI 가 `currentTime` (영상 재생 위치, 초) → frame index 변환:

```ts
const frameIdx = Math.floor(currentTime * report.fps);
// data[i] = report.data[frameIdx * joints.length * 2 + i * 2]
// axis[k] = report.axisData[frameIdx * 3 * 2 + k * 2]
// mask[k] = report.axisMask[frameIdx * 3 + k]
```

#### §9.12.5 Phase 책임 경계

- **Wave 0B (Plan 12-01) = schema only.** 3-way atomic commit (TS + Python + docs §9.12 + Firestore validator + frontend null-guard).
- **Wave 1 (Plan 12-02+)** = KeypointOverlay 컴포넌트 + `result.keypointReport` 소비. mask 참조해서 polyline 2-point or 3-point 분기.
- **mode1 split overlay** = `useReferenceMotion(motionId)` 가 반환하는 `refMotion.referenceKeypointReport` (별도 `ReferenceMotion` 필드) 직접 read. analysis doc 에 mirror 안 함 (H2 iter-4 — Firestore 1 MiB 안전 마진 + single source-of-truth).
- **reference seed** = `app/scripts/seed-reference-motions.mjs` 가 정은지 영상 분석 결과의 `referenceKeypointReport` 박제 (Wave 0B close-out 직후 production 1 회 실 분석으로 채움).

#### §9.12.6 Warning Code (Phase 12 신설)

| Code | Trigger |
|------|---------|
| `pose_reliability_low_all_frames` | 모든 frame 의 reliability 가 "low" — 영상 품질 한계 |
| `axis_polyline_unavailable` | `compute_axis_frames` 가 모든 frame 에서 None 반환 (어깨/골반 keypoint 누락) |

*Phase 12 Wave 0B 추가: 2026-06-10 — KeypointReport 신설 (Wave 0B = TS interface + Python frozen dataclass + Firestore scoped validator + frontend null-guard + reference seed 확장 단일 atomic commit). D-12-E2 / D-12-U1 (3-way atomic lockstep) / D-12-E3. Wave 1 (Plan 12-02+) 가 KeypointOverlay 컴포넌트 + UI wiring 박제.*

---

### §9.13 SafetyFlag (Phase 10 신설 — D-01 / SAFE-01)

본 섹션은 Phase 10 (injury-risk-flags) Wave 0 (Plan 10-01) 가 신설한 **결정론(LLM 무관) 부상 위험 신호** schema. CONTEXT D-01 — 기존 LLM `CoachingTipDetail.injuryRisk` 프로즈와 **독립**이다 (대체/입력 주입 X). 발화 규칙(D-02): 각 신호는 **(극단/과신전/비대칭 자세 조건) AND (통제 상실 지표)** 의 조합으로만 발화 — 자세 단독 플래그 금지 (정은지 위양성 방어). 3-way lockstep: `app/src/types/analysis.ts` `SafetyFlag`/`SafetyFlagType` ↔ `models.py` `SAFETY_FLAG_TYPES`/`SAFETY_FLAG_MODE_SCOPES` + `safety_flags.SafetyFlag` re-export ↔ 본 §9.13.

#### §9.13.1 SafetyFlag (7 필드, scalar-only)

| 필드 (camel) | 필드 (snake) | type | cardinality | 설명 |
|---|---|---|---|---|
| `flagType` | `flag_type` | `'asymmetry' \| 'trunk_hyperextension' \| 'joint_hyperextension' \| 'level_mismatch'` | required | 신호 종류 (SafetyFlagType) |
| `bodyRegion` | `body_region` | `string` | required | 코칭 카피용 KO 부위 (예: '무릎·팔꿈치', '허리') |
| `severity` | `severity` | `SeverityLevel ('low'\|'medium'\|'high')` | required | 측정값 크기 (force_signals SeverityLevel 재사용) |
| `confidence` | `confidence` | `MetricConfidence ('low'\|'medium'\|'high')` | required | 측정 신뢰도 |
| `modeScope` | `mode_scope` | `'both' \| 'mode1_only'` | required | 적용 모드 (D-06 level_mismatch = mode1_only) |
| `postureCondition` | `posture_condition` | `string` | required | 충족된 기하 조건 audit 문자열 |
| `controlLossSignal` | `control_loss_signal` | `string` | required | 발화한 통제 상실 audit 문자열 (D-02 partner) |

모든 필드는 scalar — nested array 금지 (Firestore nested-array ban, Pitfall 1).

#### §9.13.2 AnalysisResult.safetyFlags

`AnalysisResult.safetyFlags?: SafetyFlag[] | null` — **옵셔널/nullable**. 이전 빌드 doc 호환 + graceful-omit (legacy 안전). Wave 0 = schema only. 10-02/03/04 가 firing rule 산출 후 pipeline `_process` 가 채운다. 빈/부재 시 result.tsx 는 경고 배너를 렌더하지 않는다.

*Phase 10 Wave 0 추가: 2026-06-30 — SafetyFlag 신설 (Wave 0 = TS interface + Python frozen dataclass + models.py re-export + warnAmberBg 토큰 + docs §9.13 단일 atomic commit). D-01 (LLM injuryRisk 와 독립) / D-02 (자세 AND 통제 상실) / SAFE-01. Wave 1+ (Plan 10-02/03/04) 가 compute_safety_flags firing rule + pipeline wiring + result.tsx 경고 배너 박제.*

---

## §10. DeductionBreakdown (Phase 24 신설 — ND-01/ND-07 투명 감점-합산)

점수 = `baseline(100) − Σ(criterion별 측정편차 × 명시규칙 감점)`. Phase 20 의 severity→고정천장 밴드를 **제거·교체**한다. 결과 숫자(50이든 70이든)는 tally 출력일 뿐 **범위가 아니다** — 보고서가 감점 내역("−X −Y −Z = 점수")을 명명백백하게 노출하는 게 핵심 ([[scoring-must-be-transparent-deduction-tally]]). 3-way lockstep: `app/src/types/analysis.ts` `DeductionRecord`/`DeductionBreakdown` ↔ `models.py` `DEDUCTION_RECORD_KEYS`/`DEDUCTION_BREAKDOWN_KEYS` ↔ 본 §10.

### §10.1 OBJECT shape (HIGH-1)

`deductionBreakdown` 은 **객체** `{ baseline, records, final, coverageGaps?, fallback? }` 이다(bare list 아님). consumers 는 `result.deductionBreakdown?.final` 을 읽는다. `records`/`coverageGaps` 는 **flat dict 의 list** (Firestore nested-array 금지 — `angleDeltas`/`bodyRelativeNotches` 와 동일 형식).

- `baseline: 100` — 점수 baseline(미감점 천장). **재-floor 금지** — final 의 상한 밴드가 아니다.
- `final: number` — `max(0, round(100 + Σ record.points))`. **final 단위 유일 clamp 은 `max(0,…)`** (NO `min(100,…)`, NO severity ceiling — ND-01). record 단위로는 관절당 감점 상한 −20(`PER_RECORD_DEDUCTION_CAP`, quick-260705-k8h, belle 승인 2026-07-05)이 `points` 에 이미 적용돼 있다 — 클램프된 record 는 §10.2 `rawPoints`/`capApplied` 로 원 감점을 투명 노출(밴드 아님 — record 단위 명시 규칙 클램프, final 밴드 없음 그대로).
- `records: DeductionRecord[]`
- `coverageGaps?` / `fallback?` — breakdown-level 에서만 optional(legacy-compat).

### §10.2 DeductionRecord (필수 11 필드 + optional 2)

| 필드 | 타입 | 의미 |
|------|------|------|
| `criterion` | string | criterion id (leg_extension / arm_extension / split_angle / line / body_relative_reach / dimension_overall_fallback / `angle_vs_reference__{joint}` — quick-260626-jwu 신설, JOINT_KEYS 별 reference_relative 각도 criterion) |
| `measuredValue` | number | 학생 측정값 (각도 deg 또는 notch) |
| `baselineValue` | number | **수치 측정 기준** (180/160/reference_notches/100). REQUIRED. HIGH-3 — breakdown-level `baseline=100` 과 다름. |
| `baselineKind` | 'floor'\|'pole_vertical'\|'hip_line'\|null | per-move baseline(reach criterion 만; 그 외 null). **항상 방출**(present-but-nullable, MEDIUM-2). |
| `deviation` | number | over/shortfall (tolerance 차감 후 감점 입력) |
| `ruleId` | string | 명명 규칙 id (예: leg_extension_over_tol_linear) |
| `points` | number | **SIGNED NEGATIVE** 감점 (UX −X, HIGH-2) |
| `unit` | 'deg'\|'notch'\|'score_delta' | 측정 단위 (score_delta = fallback record) |
| `ipsfAnchor` | string | IPSF CoP 인용 또는 engineering_interpretation. REQUIRED(추적성 게이트). |
| `source` | 'geometry'\|'vision' | 측정 provenance. 'vision' = geometric 측정 불가 결함(split — kip-up keypoint saturate)의 vision-측정 편차로 점수화된 record(belle 2026-06-29 결정 A). 점수 산식은 동일 명시 규칙(tol×slope) — Gemini 점수 아님(ND-02 유지) |
| `deviationSource` | 'ipsf_absolute'\|'reference_relative'\|'dimension_overall' | per-criterion 편차 출처 |
| `rawPoints?` | number | **optional** — 관절당 상한(−20, `PER_RECORD_DEDUCTION_CAP`) 적용 전 원 감점(SIGNED NEGATIVE). **상한이 적용된 record 에만 방출** — 미적용 record 는 키 자체 생략(기존 11필드 byte-호환). 투명 감점-합산 내역 보존. |
| `capApplied?` | true | **optional** — 이 record 의 감점이 관절당 상한 −20 으로 클램프됨(quick-260705-k8h, belle 승인 2026-07-05). `rawPoints` 와 반드시 쌍으로 방출. fallback record(`dimension_overall_fallback`)는 클램프 비대상(§10.5 `final == dimension_overall` 불변식 보존). |

**deviationSource 의미:** 각도/라인 criterion(leg_extension/arm_extension/line)은 학생-각도-vs-IPSF-절대-기준(180°/160°) → `ipsf_absolute`. `body_relative_reach` 는 `bodyRelativeNotches[].delta_notches`(학생−코치, baseline-relative) → `reference_relative`. `angle_vs_reference__{joint}` 는 정은지(reference) 대비 per-joint median |Δ각도| 편차(24-07 §3-1), `split_angle` 은 정은지 대비 split 부족분(geometric md 부재 시 vision-측정 편차 주입 → 그 record 는 `source='vision'`) — 둘 다 `reference_relative`. fallback record → `dimension_overall`.

### §10.3 line/leg profile-gated + no-double-count

- **profile-gated (ND-06 honest 0):** `line`/`leg_extension` 의 편차는 `dimensions.line_score`/`extension_deviation` 에서 오며 이는 `profile.expects_extension` 에 게이트된다. `joint_expectations` 가 빈 profile(미등재/미상/저신뢰 동작)이면 `line_score` 가 None → 그 criterion 0 기여(진짜 0, 밴드도 거짓감점도 아님). 미등재 결함은 `dimension_overall` fallback + Gemini-located criteria 로 방어.
- **no-double-count (HIGH-5):** `line` 은 keypoint_set=='line' 또는 line-dominant fault 에서만 활성화되고, 활성화된 `leg_extension`/`arm_extension` 이 이미 claim 한 joint substrate 는 제외한다. 단일 굽은 무릎은 leg_extension record OR line record 하나만 방출(둘 다 아님).

### §10.4 insufficient-reach 방향 + baseline (HIGH-2 / ND-05)

`body_relative_reach` 는 INSUFFICIENT-reach 만 감점한다: `shortfall = max(0, reference_notches − student_notches − tolerance)`. SHORT reach 만 감점, OVER-reach 는 0 (abs() 아님). per-move `baseline_kind`(floor/pole_vertical/hip_line)가 notch 환산을 바꾸므로 **측정 substrate** 이고 점수를 바꾼다(audit label 아님, ND-05). hand/knee reach(`_NOTCH_REACH_KEYPOINTS`) 만 활성화; grip/head/torso 는 coverage gap.

### §10.5 fallback (MEDIUM-1 — traceable)

`quantificationStatus=='unavailable'` → `final = dimension_overall`(**100 으로 리셋 금지** — Phase 20 위양성 방어 보존) + record 1개(`criterion='dimension_overall_fallback'`, `ruleId='quantification_unavailable_dimension_overall'`, `baselineValue=100`, `points=round(dimension_overall−100,1)` signed-negative, `unit='score_delta'`, `deviationSource='dimension_overall'`)로 `100 + Σ points == final` 유지. `fallback='gemini_silent'` 은 Gemini 무지목인데 measured 감점이 적용된 관측 마커(final 은 여전히 기하 반영, 100 아님).

### §10.6 strictness + coverageGaps provenance

- **MEDIUM-2:** record 내부는 STRICT — `baselineKind` present-but-nullable(optional 아님, Python 이 항상 키 방출), `ipsfAnchor`+`baselineValue` 는 모든 record 에 REQUIRED. legacy-compat 는 whole `deductionBreakdown?` 필드 + breakdown-level `coverageGaps?`/`fallback?` 에서만. (예외: record-level `rawPoints?`/`capApplied?` — §10.2, 상한 적용 record 에만 방출되는 additive optional, quick-260705-k8h.)
- **MEDIUM-3:** `coverageGaps` entry 는 flat-scalar provenance(`bodyPart`/`faultState`/`keypointSet`/`ruleId`, optional scalar — Firestore nested-array 금지)를 supported_difference 에서 채운다 → 보이지만-0감점 gap 추적가능.

---

*최초 작성: 2026-05-19 — #5 착수 전 계약 확정. 변경 시 app/src/types/analysis.ts 동기화 필수.*
*Phase 1 §6 추가: 2026-05-31 — PoseFrame/PoleAxis 3-way lockstep (H-3/H-4/M-1/M-2/M-5 REVIEWS 박제).*
*Plan 01-19 §7 추가: 2026-06-02 — BodyNormalizationProfile (D-19 segment 비율, D-21 nullable). RTMW pivot 박제.*
*Plan 06-01 §8 + §8.2 추가: 2026-06-08 — BodyComparisonReport (D-06-B3 + W1 + C14) + BodyComparisonSourcePose (R2 round-2 reviews).*
*Plan 07-01 §8.3 추가: 2026-06-08 — Phase 7 차이 분류 룰 (D-07-A1 + D-07-A2 + D-07-U1) + 33 canned coverage (CR-02 fix) + CR-01 fallback path + WR-01/WR-03/WR-04 iteration 2.*
*Plan 08-00 §9.0 추가: 2026-06-09 — Coordinate/Scale Contract (PoleLine2D + PoleAxisMeasurement + CoordinateSpace + ContactPrimitiveKind + median_torso_length + preflight label gate). REVIEWS Cycle 1 R1 + R2 + R3 + R4 blocker 해소.*
*Plan 08-01 §9 추가: 2026-06-09 — ForceSignalsReport (PhaseBoundary + BodyLineTiltMetric + StabilityMetric + ContactStabilityMetric + 20 warning code enum). REVIEWS Cycle 1 R1/R2/R3/R4/R5 + Cycle 2 §3 MEDIUM (preflight_gate_pending) 박제.*
*Plan 08.1-00 §9.3 변경: 2026-06-09 — BodyLineTiltMetric distance 차원 hard break. 5 필드 (pelvisDistanceFromPoleAxis / chestDistanceFromPoleAxis / scaleDenominator / coordinateSpace / deviationDirection) 제거 + tilt-only. Wave 0 = transitional stub. IPSF Code of Points NotebookLM citation 9 (Page 87 Glossary — 'Tilt' / 'Lean' / 'Off-axis' 용어 부재) 정합. RESEARCH §4 α-4 + CONTEXT D-01.*
*Plan 09-01 §9.11 추가: 2026-06-10 — ForcePatternInference + ForcePatternFinding 신설 (Wave 0 = TS interface + Python frozen dataclass + Firestore scoped validator + frontend null-guard 단일 atomic commit). D-09-D1 / D-09-U1 (3-way atomic lockstep) / D-09-U3 / D-09-U4 / D-09-U5. Wave 1 (Plan 09-02) 가 본체 함수 + 18 canned + pipeline wiring 박제.*
*quick-260705-k8h §10 갱신: 2026-07-05 — 관절(criterion record)당 감점 상한 −20 (belle 승인). §10.2 optional 2필드(`rawPoints`/`capApplied`) 신설 — 상한 적용 record 에만 방출, 미적용 record byte-호환. final 밴드/severity 밴드 없음 유지 (record 단위 명시 규칙 클램프).*

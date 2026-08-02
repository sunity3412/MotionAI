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

### POST /playback-url
영상 재생용 S3 presigned GET URL 재발급. (인증: Firebase Auth UID, 익명 포함)
서명 URL 은 7일 TTL — 만료 시 앱이 이 endpoint 로 재발급 (TTL 연장 금지, 재발급이 정답).

요청 — 두 변형 상호 배타 (동시 제공 시 400):
```
(1) 본인 업로드 영상 (mode3 prev 등)
analysisId  string            uid-scoped: uploads/{uid}/{analysisId}.{ext} 만 서명
ext         'mp4' | 'mov'     기본 'mp4'

(2) 기준 모션 영상 (mode1 우측 — 29-CONTEXT D-09, D1 fix)
referenceMotionId  string     영숫자·하이픈만. Firestore reference/{id} doc 의
                              videoS3Key 화이트리스트 경유로만 서명.
```

referenceMotionId 변형 경계 가드 4종 — 하나라도 실패 시 동일 `404 not_found`
(inactive/부재/무영상 케이스가 응답으로 구분되지 않음 — 숨김 doc 존재 leak 0,
29-PLAN-REVIEW HIGH-2):
1. doc 존재
2. `isActive`가 false 아님 (미승인/reject 자동등록 doc 재서명 거부)
3. `videoS3Key` 존재
4. `videoS3Key`가 `reference/` prefix (allowlist — 그 외 키는 doc 에 있어도 거부)

클라이언트가 임의 S3 키를 서명시킬 수 없다 — body 의 s3Key 류 파라미터는 무시.

응답 `PlaybackUrlResponse` (두 변형 동일 — 스키마 불변)
```
playbackUrl   string   S3 presigned GET URL
expiresInSec  number   URL 만료(초) = 604800 (7일)
```

#### POST /playback-url — `asset` 확장 (Phase 31, 리뷰 H-02)

기존 body 에 optional 필드 하나를 추가한다. **`asset` 미지정 = 기존 동작 100% 보존**
(하위호환 — 기존 두 변형과 응답 스키마 모두 불변).

```
asset  'correctedPose' | 'rotation'   optional  ← 지정 시 analysisId 와 함께 사용
```

`asset` 지정 시 서버는 **토큰 uid 로 스코프된 분석 문서**에서 해당 asset 의 key
(`correctedPoseKey` / `rotationVideoKey`)를 읽고, `results/{uid}/{analysisId}/` prefix
정확 일치를 검증한 뒤 **1시간 presign** 을 발급한다.

- **클라이언트 임의 key 없음** — 요청에 S3 key 를 실어 보내는 파라미터가 계약에 존재하지
  않는다. 클라이언트는 asset **종류**만 고르고, 실제 key 선택은 전적으로 서버 몫이다
  (server-selected asset type, 리뷰 H-02/H-05). referenceMotionId 변형의 allowlist
  가드와 동일 철학.
- 필드 부재(아직 생성 안 됨) / 상태 미완료(`!= 'done'`) / prefix 불일치 = **전부 동일한
  `404 not_found`** — 어느 단계에서 걸렸는지 응답으로 구분되지 않는다 (leak 0,
  referenceMotionId 4종 가드 선례).
- 응답: `{playbackUrl, expiresInSec: 3600}`. 영상 재생용 7일 TTL 과 달리 **1시간**인 이유는
  이 URL 이 화면 표시 즉시 소비되고 재방문 시 재발급되기 때문이다.

#### POST /playback-url — `asset: 'coachAudio'` 확장 (Phase 32 Plan 32-16, D-18 B안)

재생 중 큐 오디오 mp3(§12.7) 재서명. Phase 31 asset 확장과 동일 철학(H-02) —
**`asset` 미지정/기존 종류 요청의 동작은 바이트 불변**이다.

```
asset     'coachAudio'   analysisId 와 함께 사용
recordId  string         §12.3 recordId (형식 r{2자리}:{criterion} — 영숫자·언더스코어).
                         형식 위반 = 400 bad_request (path injection 차단)
```

- 서버가 `results/{uid}/{analysisId}/coach_audio_{recordId}.mp3` canonical key 를
  **서버 측에서 구성**(`s3keys.build_coach_audio_key` — 저장 측과 단일 출처)하고,
  `result.coachAudio.items` 중 같은 `recordId` 항목의 저장 key 와 **전체 문자열
  exact 비교** 후에만 1시간 presign 을 발급한다 (prefix/basename 부분일치 불가 —
  타 객체 열람 차단). 클라이언트는 recordId 만 지정 — S3 key 를 실어 보내는
  파라미터는 계약에 없다 (server-selected, H-02/H-05).
- `coachAudio.status != 'done'` / 항목 부재 / key 불일치 = **전부 동일한
  `404 not_found`** (leak 0 — Phase 31 asset 가드 선례).
- 응답: `{playbackUrl, expiresInSec: 3600}` (`ResponseContentType: audio/mpeg`).

#### POST /visual/rotation (Phase 31 — D-06)

카메라앵글 회전 참고 영상 **온디맨드 생성 요청**. (인증: Firebase ID token 필수)
건당 수분·과금이라 자동 생성하지 않는다 — 버튼 → 백그라운드 생성 → 카드 갱신.

요청
```
analysisId  string   본인 소유 분석 건
```

응답
```
202  {"rotationStatus": "pending"}   신규 접수 / 재시도 수락
200  {"rotationStatus": "done"}      이미 완료 — URL 미포함(표시 URL 은 playback-url asset)
400  code 'bad_request'              analysisId 누락·형식 오류
401  code 'unauthorized'             토큰 부재/검증 실패
404  code 'not_found'                존재·소유·상태 가드 합산 단일 응답
429  code 'daily_limit'              일일 생성 한도 초과
503  code 'feature_disabled'         VisualJobsEnabled flag OFF
```

- **404 단일 응답:** 문서 부재 / 타인 소유 / 생성 불가 상태를 하나의 404 로 합산한다 —
  타인의 analysisId 를 넣어 존재 여부를 떠보는 경로가 없다 (playback-url `guards_ok`
  선례, leak 0).
- **200 에 URL 을 담지 않는다** — 이미 `done` 이어도 표시 URL 은 `POST /playback-url`
  의 `asset: 'rotation'` 재서명으로만 얻는다 (URL 비저장 원칙, 리뷰 H-02).
- **`daily_limit` 한도 명세 (리뷰 M-06):** 사용자당 **3건/일** + 전역 **30건/일**.
  **일 경계 = KST(UTC+9) 자정 리셋** — 파일럿 사용자가 전원 한국이라 UTC 자정 리셋은
  한국 시간 오전 9시에 한도가 풀리는 혼란을 준다. 서버가 KST 기준 날짜 키
  (`quotaDateKey`)로 집계한다. 파일럿 규모에서는 사실상 무제한이되 남용만 막는 수준(D-07).
- **`feature_disabled` 는 조용히 처리:** flag OFF 응답을 받으면 앱은 에러를 띄우지 않고
  버튼을 비활성화한다 (D-08 조용한 폴백). R3F 뷰어는 그대로 표시된다.

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
attributionReliability { unreliable, geminiSilent, overTolJointCount, visibility, dtwDistance, aggregateStatement? } optional ← IN-01 / quick-260802-nfd
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

`attributionReliability` (IN-01 quick-260724-q6b — per-joint 귀속 신뢰도 마커 / quick-260802-nfd — 게이트 입력 상시 기록)
```
unreliable          bool     per-joint 귀속(어느 관절이 틀렸는지)이 신뢰 불가한가
geminiSilent        bool     게이트 입력 ①: Gemini 가 결함 관절을 하나도 못 짚음(pointed=∅)
overTolJointCount   number   게이트 입력 ②: tol(IPSF 20°) 초과 angle_vs_reference 관절 수
visibility          number|null  게이트 입력 ③-a: 정렬 window keypoint 가시성(0~1). 미측정 = null
dtwDistance         number|null  게이트 입력 ③-b: 정규화 DTW 거리. 미보유 = null
aggregateStatement? string   unreliable=true 시에만 동반 — 관절명 없는 집계 문장
```
  - **발화 조건 (3-조건 AND)**: `geminiSilent` AND `overTolJointCount >= 5` AND
    (`visibility < 0.70` OR `dtwDistance > 60.0`). 역립/자기가림 자세에서 keypoint 신뢰도가
    급락하면 해부학적으로 무관한 관절까지 tol 위로 균일 부양돼 "엉뚱한 관절을 짚는" 귀속이
    발생하는데, 그때만 per-joint 단정을 회피시키기 위한 마커다.
  - **점수 무접촉 (magnitude-neutral)**: `overallScore` / `deductionBreakdown.final` /
    `records` 는 이 마커와 무관하게 불변. 마커는 **표현 강등 전용**이다.
  - **quick-260802-nfd — 발화 여부와 무관하게 항상 방출**한다. 이전에는 `unreliable=true`
    일 때만 실려서 안 걸린 doc 의 게이트 입력이 어디에도 남지 않았고, "발화해야 하는데 안
    했나"를 원리적으로 검증할 수 없었다(done 분석 925건 전수: 발화 18건 중 17건이
    elbow-twist 한 동작, 안 걸린 907건의 visibility 기록 0). 이제 게이트 입력을 상시 기록해
    임계 재조정 판단의 근거를 만든다 — **임계값 자체는 이 사이클에서 무변경**.
  - **소비 규칙 (하드)**: 강등 여부는 **필드 존재가 아니라 `unreliable` 값**으로만 판단할 것.
    앱은 `result.attributionReliability?.unreliable === true` 엄격 비교(result.tsx),
    백엔드는 `assemble.rebuild_tips_for_vision_fault` 의 `attr.get("unreliable")` falsy 검사다.
    `aggregateStatement` 는 `unreliable=true` 시에만 실린다 — reliable 마커에 이 키가 있으면
    강등 문구가 정상 doc 에 새는 회귀다.
  - **부재 = legacy doc 또는 vision 컨텍스트 미산출(레거시 폴백) 경로** — optional, migration 없음.
  - Firestore flat 정합: 전 필드 스칼라(또는 null) — nested list/dict 0
    ([[firestore-nested-array-flat]] 보존).
  - lockstep: `app/src/types/analysis.ts` `AttributionReliability` ↔ pipeline `app.py`
    `_assess_attribution_reliability`(방출 형상) + `_attach_attribution_marker`(부착) ↔ 본 §4.
    (models.py 상수 불필요 — status enum 아님, timingsMs 선례.)

`faultZoomStatus` (Phase 27 SPD-04 — fault_zoom 사후 분리, D-06)
```
faultZoomStatus   'pending' | 'done' | 'failed'   optional  ← zoom 렌더 진행 상태
```
  - fault_zoom 확대비교 PNG 는 **점수가 아니라 표현물**이다. 점수/verdict/감점 내역은
    `status='done'`(complete) 시점에 확정되고(D-03 "사후 변경 금지" 경계), zoom PNG 는
    렌더가 오래 걸려(후처리 주요분) **complete 이후 부분 업데이트로 도착**한다 →
    사용자 체감 완료 시점을 앞당긴다.
  - 의미: `pending`=렌더 중(앱은 확대카드 자리에 로딩 placeholder) / `done`=도착
    (`result.faultZoomComparisons` 유효, 앱 rerender) / `failed`=렌더 실패(카드 숨김 —
    무한 pending 고아 방지).
  - **부재 = 사후 분리 이전(legacy) doc** — optional, migration 없음. 앱은 필드 부재 시
    `faultZoomComparisons` 유무로 판정(하위호환).
  - **사후 변경 경계(D-03/D-06):** complete 이후 write 는 `result.faultZoomComparisons`
    + `result.faultZoomStatus` **두 필드뿐**이다. zoom 외 어떤 `result.*` 필드도 사후
    변경 금지 (`firestore_admin.update_analysis_fault_zoom` 단일 경로 + field-path 게이트).
  - **status 머신과 독립:** `faultZoomStatus` 는 §3 `AnalysisStatus`(PIPELINE_SEQUENCE)에
    넣지 않는다 — status enum 확장 3-way 비용 회피. result 내부 scalar 필드로만 존재.
  - Python 정본: `models.py FAULT_ZOOM_STATUSES` + `firestore_admin.update_analysis_fault_zoom`.
    lockstep: `app/src/types/analysis.ts AnalysisResult.faultZoomStatus?` ↔ models.py ↔ 본 §4.

`visual 교정 시각물 필드` (Phase 31 — D-05/D-06/D-08)
```
correctedPoseStatus       'pending' | 'done' | 'failed'   optional  ← 교정 자세 이미지 상태
correctedPoseKey          string                          optional  ← S3 key (URL 아님)
correctedPoseJoint        string                          optional  ← 교정 대상 top-1 결함 keypoint
correctedPoseUpdatedAtMs  number                          optional  ← epoch ms, 이 필드 전용
rotationStatus            'pending' | 'done' | 'failed'   optional  ← 회전 참고 영상 상태
rotationVideoKey          string                          optional  ← S3 key (URL 아님)
rotationUpdatedAtMs       number                          optional  ← epoch ms, 이 필드 전용
```
  - **두 산출물의 생성 시점이 다르다.** `correctedPose*`(D-05)는 **분석 완료 시 자동
    생성**(결함 top-1 부위만) — 첫 분석의 "전문가 수준" 인상이 core value 라서 무조건
    만든다. `rotation*`(D-06)은 건당 수분·과금이라 **온디맨드**(`POST /visual/rotation`)
    로만 생성되고, 대기 중에는 R3F 수학 3D 뷰어가 즉시 대체재로 표시된다.
  - 상태 의미(양쪽 동일): `pending`=생성 중(카드 자리 placeholder) / `done`=도착(카드
    표시) / `failed`=생성 실패(카드 숨김).
  - **부재 = legacy doc** — optional, migration 없음. `failed` 와 부재는 앱에서 동일하게
    "카드 숨김"으로 처리된다 — 모더레이션 차단(실측 ~10%)을 사용자에게 에러로 노출하지
    않는 **조용한 폴백**(D-08). 실패를 강조하면 "기능이 불안하다"는 인상만 남는다.
  - **URL 비저장 원칙 (리뷰 H-02):** 문서에는 presigned URL 을 **저장하지 않는다**. key
    만 두고, 표시 URL 은 `POST /playback-url` 의 `asset` 확장으로 매번 재서명한다. 문서에
    URL 을 박제하면 (a) TTL 만료 후 죽은 URL 이 남고 (b) 클라이언트가 임의 key 를
    서명시킬 여지가 생긴다. 서버가 asset 종류로 key 를 **선택**하는 형태만 허용.
  - **전용 timestamp (리뷰 H-06):** pending 타임아웃/dedupe 판정은 각 필드의
    `*UpdatedAtMs` 로만 한다 — 공용 `updatedAt` 은 무관한 write 로도 갱신돼 pending
    수명을 잘못 늘린다.
  - **점수 비반영 invariant:** 두 산출물 모두 채점에 들어가지 않는다 (카메라앵글 stretch
    게이트 미통과). 결과 화면에서도 점수 내역 **아래** "참고하세요" 섹션에 분리 배치한다
    (D-09) — 점수 비반영이 레이아웃으로 드러나야 한다.
  - **내부 구현 노트 (앱 비노출):** 생성 작업은 백엔드 전용 `visualJobs` 컬렉션으로
    관리하고, 일일 한도는 job 문서의 `quotaDateKey`(KST 일 경계) 로 집계한다. 앱은 이
    컬렉션을 읽지 않으며 계약에도 포함되지 않는다 — 위 7필드가 앱이 보는 전부다.
  - Python 정본: `models.py VISUAL_STATUSES` + `firestore_admin.update_analysis_visual`.
    lockstep: `app/src/types/analysis.ts AnalysisResult.correctedPoseStatus?`/`rotationStatus?`
    ↔ models.py ↔ 본 §4.

`FaultZoomComparison` 뷰어 프레임 소스 (Phase 31 — D-10)
```
userFrameIdx  number   optional  ← 학생 측 대응 프레임 인덱스
refFrameIdx   number   optional  ← 기준(정은지) 측 대응 프레임 인덱스
refMatched    boolean  optional  ← 기준 측 대응 성공 여부
atMatched     boolean  optional  ← 표시 프레임 == 그 record 의 측정 프레임
refMarked     boolean  optional  ← 기준 패널에 표시가 그려졌는가 (§11.9)
```
  - DTW 대응 프레임 쌍이며 **`keypointReport` 프레임 공간(9fps angles 도메인)**의 정수
    인덱스다 (18fps 업샘플 공간 아님 — §11 fps 도메인 주의 동일).
  - crop PNG(`imageUrl`)와 달리 2D 비교 뷰어는 좌표를 직접 렌더하므로 "이 카드가 가리키는
    순간"의 프레임 인덱스가 필요하다. `refMatched=false` 면 뷰어가 학생 단독 렌더
    (`refMatch: 'failed'` 와 정합).
  - **부재(legacy) = 뷰어 프레임 동기화 없음** — optional, migration 없음
    (`tier?`/`refMatch?` 선례). 31-03 이 방출.
  - **`atMatched` (quick-260801-gbk)** — 이 카드가 최종 채택한 학생 프레임이 그 감점
    record 의 `atFrameIdx`(§10.2)와 **정확히 같을 때만** `true`. 앵커가 없었거나(순간
    미확정 criterion) 앵커 창 안에서 다른 프레임이 선택되면 키 자체를 생략한다.
    앱은 이 값이 `true` 일 때만 "위 사진은 그 값을 잰 순간" 절을 낸다.
    **앱이 두 초를 빼서 추정하지 말 것** — 그러려면 앱이 fps 와 프레임 공간을 알아야
    하고 그 구조가 정확히 §11.8 F-3 을 만들었다. 프레임을 실제로 고른 코드만 이 인증을
    낼 수 있다(`refMatched` 와 동형·동의미).

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
recognizedMotionId?    인식기가 알아낸 동작 canonical id (Phase 30 D-04)
recognizedMotionName?  인식기가 알아낸 동작 표시명 (Phase 30 D-04)
```
  recognizedMotionId / recognizedMotionName (Phase 30 Plan 30-02, D-04) = mode3
  파이프라인이 이미 인식 중이던 동작 id/명(`TechniqueProfile.motion_id`/`name`)을
  comparison 에 적립. OPTIONAL (legacy doc 호환) — 부재 시(legacy doc / 인식 실패
  FallbackRecognizer) 앱은 '내 기록' 단일 그룹. 인식 성공(motion_id 존재) 시
  첫 분석(isFirst=True)부터 방출. **이번 phase 화면 미소비 — Phase 16(학원 명칭
  카테고리 체계) 소비 예정**. 3-way lockstep: `app/src/types/analysis.ts`
  Mode3Comparison + `models.py` (Phase 30 주석 명세) + `assemble.build_mode3`
  (recognized_motion_id/name kwargs). 세 곳 동시 갱신 필수.
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
- **validator 길이 정합 (32-14 신설):** joints 길이 ∈ {8, 12} + (frames 스칼라 존재 시) `data` 길이 == frames×J×2, `confidence` 길이 == frames×J. frames 부재 legacy 형상은 기존 그대로 통과 (T-32-36 하위호환).
- **camelCase 변환:** `_dataclass_to_camel_case_dict` (pipeline/app.py) 가 `axis_data` → `axisData`, `axis_mask` → `axisMask` 자동 변환

#### §9.12.1 KeypointName Literal (R11 + 32-14 확장 — 12 body keypoint, axis 제외)

`left_shoulder` / `right_shoulder` / `left_hip` / `right_hip` / `left_knee` / `right_knee` / `left_hand` / `right_hand` + **(32-14 D-22 1단)** `left_ankle` / `right_ankle` / `left_elbow` / `right_elbow`

- `left_hand` / `right_hand` 는 COCO-17 의 `left_wrist` / `right_wrist` 매핑 (loose hand 박제, v2 wrist 신설은 후속 plan). ankle/elbow 는 COCO-17 동명 키 1:1 (32-14).
- axis 는 별도 `axisData` field (R2 정합 — UI 자체 계산 차단, A7 해소).
- **하위호환 (32-14): `joints` 배열이 capability source** — 무엇이 측정됐는지의 단일 판별 기준은 doc 의 joints 배열(길이·이름)이다. legacy doc(joints 8)과 신규 doc(joints 12)을 소비처가 배열 길이로 자연 분기 — 하드코딩 8 금지, `version` 필드는 참고용.
- **감점 무유입 (32-14 1단):** 신규 4관절은 표시·측정 승격만 — 각도층(`skeleton.JOINT_ANGLES`)·감점 모듈(kismam/dimensions) 무접촉. 감점 편입(2단)은 관절별 신뢰도 실측 게이트 뒤 별도 plan.

#### §9.12.2 KeypointReport (10 필드)

| Field (camelCase / snake_case) | Type | Notes |
|--------------------------------|------|-------|
| `version` | `string` | "1.0" = legacy 8관절 방출분 / "1.1" = 32-14 12관절 방출분 (non-empty, 참고용 — 판별은 joints 길이) |
| `joints` | `KeypointName[]` | length = J = 8(legacy) \| 12(32-14, `_KEYPOINT_NAMES` tuple) — **capability source** |
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

*Phase 32 (32-14) 확장: 2026-07-22 — D-22 1단: joints 8→12 (+left/right_ankle, +left/right_elbow), version "1.0"→"1.1" bump, validator 길이 정합 신설(joints ∈ {8,12} + data/confidence frames×J 정합), 하위호환 = joints 배열이 capability source. 감점 반영(2단)은 관절별 신뢰도 실측 게이트 뒤 별도 plan. 3면 lockstep 동시 수정 (analysis.ts + keypoint_frame.py/models.py + 본 §9.12).*

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
- `final: number` — **Wave R 2트랙 산식(33-SPEC.md R1/R2, D-34/D-36):** `max(25, round(100 − min(40, Σ|execution points|) − Σ|critical points|))`. 실행 트랙(`track` 부재/`'execution'`, 라인/각도 편차)은 합산 후 −40 집계캡(`executionCap`) → 바닥 60; 치명 트랙(`track='critical'`, 필수 완전신전 미달 = 요소 미인정)은 −40 집계캡 + −20 per-record 캡 둘 다 우회해 바닥 60 아래로 끌어내리고, 최종은 절대 바닥 25(`scoreFloor`)로 clamp. **severity→고정천장 밴드는 여전히 없음**(NO `min(100,…)`, NO severity ceiling — ND-01; 집계캡은 밴드가 아니라 IPSF 실행-감점 총합상한의 비례환산). record 단위로는 관절당 감점 상한 −20(`PER_RECORD_DEDUCTION_CAP`, quick-260705-k8h)이 실행 record 의 `points` 에 이미 적용돼 있다 — 클램프된 record 는 §10.2 `rawPoints`/`capApplied` 로 원 감점을 투명 노출(치명 record 는 −20 캡 비대상). **치명 트랙은 현재 DORMANT**(활성 criterion 0 — split_fail_threshold_deg 보유 criterion 없음, D-35): 실 doc 은 전부 실행-only, 치명 하강은 합성 단위테스트로만 검증(D-38).
- `records: DeductionRecord[]`
- `coverageGaps?` / `fallback?` — breakdown-level 에서만 optional(legacy-compat).
- **Wave R 2트랙 재구성 집계(additive-optional, D-37, INV-6):** two-track tally 경로에서만 방출(dimension_overall fallback 조기 return 경로는 부재 — 그 경로 재구성은 §10.5). 구 doc/앱 하위호환(부재 = 재설계 이전 doc). Python lockstep = `models.DEDUCTION_BREAKDOWN_OPTIONAL_KEYS`, TS = `DeductionBreakdown` 의 동명 optional. **INV-6 재구성:** `final == max(scoreFloor, round(100 + executionCappedTotal + criticalTotal))`.
  - `executionRawTotal?: number` — 실행 record `points` 원합(SIGNED NEGATIVE, 캡 전).
  - `executionCappedTotal?: number` — `-min(executionCap, |executionRawTotal|)` (집계캡 적용값).
  - `criticalTotal?: number` — 치명 record `points` 합(집계캡·관절캡 우회, SIGNED NEGATIVE).
  - `executionCap?: number` — `40`(실행 감점 집계 상한, 단일 project-level 상수 — fixture별 re-fit 금지).
  - `scoreFloor?: number` — `25`(채점 도달 영상 절대 점수 바닥).
- **측정 오차 미만 감점 억제(additive-optional, quick-260802-nse):** `suppressedRecords?` — 아래 §10.8. 억제가 실제로 일어난 doc 에만 실린다.

### §10.2 DeductionRecord (필수 11 필드 + optional 3)

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
| `capApplied?` | true | **optional** — 이 record 의 감점이 관절당 상한 −20 으로 클램프됨(quick-260705-k8h, belle 승인 2026-07-05). `rawPoints` 와 반드시 쌍으로 방출. fallback record(`dimension_overall_fallback`)는 클램프 비대상(§10.5 참조). |
| `track?` | 'execution'\|'critical' | **optional** (Wave R, 33-SPEC.md R4, D-37) — 2트랙 분류. `'critical'` record 에만 방출; `'execution'`(기본)은 키 생략(기존 11필드 byte-호환, legacy doc 부재 안전). 실행 트랙은 −40 집계캡 대상, 치명 트랙(필수 완전신전 미달 = 요소 미인정)은 집계캡·관절캡 우회(§10.1). **현재 DORMANT** — 활성 criterion 0(D-35). |
| `atFrameIdx?` | number | **optional** (quick-260801-gbk) — 이 감점을 **잰 학생 프레임**. 도메인은 학생 **9fps angles 행 인덱스**(keypointReport rep 인덱스 아님 — §11.8 F-3 과 다른 축). 순간을 신뢰 있게 정할 수 있는 criterion 에만 방출. |
| `atVideoSec?` | number | **optional** — `atFrameIdx / 파이프라인 frames fps`. 백엔드가 나눠서 준다 — **앱이 rep fps 로 재계산 금지**(그 재계산이 §11.8 F-3 의 근본원인). fps 를 못 구하면 `atFrameIdx` 만 방출. |

#### §10.2.1 측정 순간 산출 규칙 (quick-260801-gbk)

`atFrameIdx` 는 **그 record 가 실제로 보고한 집계값에, 자기 per-frame 값이 가장 가까운 프레임**이다. **argmax(최대 편차 프레임)를 쓰지 않는다** — 각도 시계열은 인접 프레임 jitter 가 크고 상위 백분위 outlier 가 흔해서(motiondtw `per_joint_deviation` docstring 198-209행), 최대 편차 프레임을 "여기가 감점 부분"이라며 확대하면 지금보다 나빠진다.

| criterion | 집계 (record 가 보고하는 값) | 순간 |
|---|---|---|
| `angle_vs_reference__{jk}` — Gemini pointed | `windowMedianAngleDeltas.deltas[].student_deg` = worst-window 안 학생 각도의 median | `sourceFrameIndices.user` **안에서** `abs(angles[t][j] − student_deg)` 최소 프레임. median 재계산 없음 — `features._delta_entry` 가 emit 한 값을 그대로 읽으므로 drift 가 원리적으로 불가능 |
| `angle_vs_reference__{jk}` — Gemini silent | `per_joint_deviation` = DTW path 전체 median of `abs(Δ)` | `match.start + path[k*][0]`, `k*` = `abs(diffs[k][j] − median_j)` 최소 |
| `leg_extension` / `arm_extension` | 관절쌍 중 max 인 관절의 `max(0, 180 − mean_over_window)` | 그 **argmax 관절**에 대해 `_select_window` 구간 안에서 per-frame 부족분이 집계값에 가장 가까운 프레임. (시간축 집계는 **mean** 이다 — "max" 는 좌/우 관절쌍 축) |
| `line` | 양수 부족분 EXTEND 관절들의 평균 | 같은 관절 집합의 per-frame 평균 부족분이 집계값에 가장 가까운 프레임 |
| `body_relative_reach` | notch 부족분 | **fail-closed — 필드 없음.** notches 에 시계열이 없다 |
| `dimension_overall_fallback` | whole-score passthrough | **fail-closed — 필드 없음.** 특정 순간이 없는 record |
| `split_angle` | vision 주입 편차 | **fail-closed — 필드 없음.** 아래 참조 |

**`split_angle` 이 fail-closed 인 이유:** 생산자가 둘인데 프로덕션에서 사는 쪽은 시계열이 없는 쪽이다. ① 기하 빌더 경로는 `profile.required_split_deg` 게이트가 필요한데 **어떤 recognizer 도 이 값을 설정하지 않는다** → 사문. ② vision 주입(`deduction_engine`, `source='vision'`)이 **유일한 실동작 경로**이고, 그 `measuredValue` 는 Gemini 추정이라 **우리가 어느 프레임에서 잰 값이 아니다.** 기하에서 뽑은 프레임을 "여기서 쟀다" 계약 아래 붙이면 앱이 다시 "위 사진은 그 값을 잰 순간이에요"라고 말하게 되고, 그것이 이 필드가 없애려는 거짓과 같은 종류다. 재지 않았으면 "쟀다"고 쓸 수 없다.

**채점 무접촉:** 이 두 필드는 `deduction_engine.tally` 가 **끝난 뒤** `_attach_translation_emission` 이 `setdefault` 로 각인한다. 점수를 계산하는 코드는 이 값을 볼 수 없다 — 불변식이 테스트가 아니라 구조로 보장된다.

**deviationSource 의미:** 각도/라인 criterion(leg_extension/arm_extension/line)은 학생-각도-vs-IPSF-절대-기준(180°/160°) → `ipsf_absolute`. `body_relative_reach` 는 `bodyRelativeNotches[].delta_notches`(학생−코치, baseline-relative) → `reference_relative`. `angle_vs_reference__{joint}` 는 정은지(reference) 대비 per-joint median |Δ각도| 편차(24-07 §3-1), `split_angle` 은 정은지 대비 split 부족분(geometric md 부재 시 vision-측정 편차 주입 → 그 record 는 `source='vision'`) — 둘 다 `reference_relative`. fallback record → `dimension_overall`.

### §10.3 line/leg profile-gated + no-double-count

- **profile-gated (ND-06 honest 0):** `line`/`leg_extension` 의 편차는 `dimensions.line_score`/`extension_deviation` 에서 오며 이는 `profile.expects_extension` 에 게이트된다. `joint_expectations` 가 빈 profile(미등재/미상/저신뢰 동작)이면 `line_score` 가 None → 그 criterion 0 기여(진짜 0, 밴드도 거짓감점도 아님). 미등재 결함은 `dimension_overall` fallback + Gemini-located criteria 로 방어.
- **no-double-count (HIGH-5):** `line` 은 keypoint_set=='line' 또는 line-dominant fault 에서만 활성화되고, 활성화된 `leg_extension`/`arm_extension` 이 이미 claim 한 joint substrate 는 제외한다. 단일 굽은 무릎은 leg_extension record OR line record 하나만 방출(둘 다 아님).

### §10.4 insufficient-reach 방향 + baseline (HIGH-2 / ND-05)

`body_relative_reach` 는 INSUFFICIENT-reach 만 감점한다: `shortfall = max(0, reference_notches − student_notches − tolerance)`. SHORT reach 만 감점, OVER-reach 는 0 (abs() 아님). per-move `baseline_kind`(floor/pole_vertical/hip_line)가 notch 환산을 바꾸므로 **측정 substrate** 이고 점수를 바꾼다(audit label 아님, ND-05). hand/knee reach(`_NOTCH_REACH_KEYPOINTS`) 만 활성화; grip/head/torso 는 coverage gap.

### §10.5 fallback (MEDIUM-1 — traceable)

`quantificationStatus=='unavailable'` → `final = max(SCORE_FLOOR, round(dimension_overall))`(**100 으로 리셋 금지** — Phase 20 위양성 방어 보존; **Wave R 절대 바닥 25 적용** — 채점 도달 = not_pole_motion/no_human 게이트 통과했으므로 sub-25 부당, INV-8/D-36, 경로 무관) + record 1개(`criterion='dimension_overall_fallback'`, `ruleId='quantification_unavailable_dimension_overall'`, `baselineValue=100`, `points=round(dimension_overall−100,1)` signed-negative, `unit='score_delta'`, `deviationSource='dimension_overall'`). 이 fallback passthrough 는 2트랙 산식이 아니므로 §10.1 집계 필드(`executionCap` 등)를 방출하지 않는다 — 재구성 불변식은 `final == max(SCORE_FLOOR, round(dimension_overall))`. `fallback='gemini_silent'` 은 Gemini 무지목인데 measured 감점이 적용된 관측 마커(final 은 여전히 기하 반영, 100 아님).

### §10.6 strictness + coverageGaps provenance

- **MEDIUM-2:** record 내부는 STRICT — `baselineKind` present-but-nullable(optional 아님, Python 이 항상 키 방출), `ipsfAnchor`+`baselineValue` 는 모든 record 에 REQUIRED. legacy-compat 는 whole `deductionBreakdown?` 필드 + breakdown-level `coverageGaps?`/`fallback?` 에서만. (예외: record-level `rawPoints?`/`capApplied?` — §10.2, 상한 적용 record 에만 방출되는 additive optional, quick-260705-k8h.)
- **MEDIUM-3:** `coverageGaps` entry 는 flat-scalar provenance(`bodyPart`/`faultState`/`keypointSet`/`ruleId`, optional scalar — Firestore nested-array 금지)를 supported_difference 에서 채운다 → 보이지만-0감점 gap 추적가능.

### §10.7 mode3 방출 조건 (Phase 29 신설 — D-01/D-02/D-03, 신규 필드 0)

`deductionBreakdown` 은 mode 무관 optional 그대로다 — mode3 를 위한 계약 필드 신설 0. mode3 의 방출 **조건**만 다음과 같이 서술한다:

- **방출 조건 (D-01):** mode3 는 등록 동작의 ipsf_absolute measured seed(md — RTMW 절대 각도, profile-gated) 보유 시에만 방출. Gemini 추가 호출 0 (vision 비교는 계속 보류).
- **status 불변 (D-01):** 방출 doc 의 `visionVeto.status` 는 `'mode3_held'` 유지 — `'applied'` 아님. mode3 에서 breakdown 존재 ≠ vision veto 실행 (앱의 vetoApplied 파생은 mode1 의미 그대로).
- **항등 (D-02):** 방출 doc 의 `overallScore == deductionBreakdown.final` (100−Σ감점, §10.1 산술 그대로). 성장 델타 소스는 저장 `overallScore` 단일 — pre-tally 점수를 나르는 별도 필드 없음.
- **미방출 (D-03):** md 빈 dict(미등록 동작 + 빈 criteria 동작)는 breakdown 미방출 + `overallScore` 불변 — 기준 없는 감점 0=100 위양성 차단. legacy mode3 doc(breakdown 부재)은 그대로 유효.
- production 노출은 29-05 sweep 게이트(정은지 페어셋 mode3) 통과 후 Pod 재기동 시점.

### §10.8 측정 오차 미만 감점 억제 + `suppressedRecords` (quick-260802-nse 신설)

감점 record 가 하는 주장은 하나다 — **"이 관절의 편차가 허용치를 넘는다."** 그 주장은 점추정(`measuredValue` = 정렬 경로 스텝별 `|Δ각도|` 의 median)에 기대고 있고, 점추정에는 불확실도가 따라붙는다. 그 불확실도 안에서 주장이 성립하지 않으면 record 를 **방출하지 않는다**.

**억제 규칙.** 그 값을 만든 바로 그 표본에서 median 의 양측 95% 분포무관(부호검정, 순서통계) 신뢰구간 `(L, U)` 를 유도한다(`analysis/measurement_error.py`, `CI_ALPHA=0.05`). `L <= tolerance` 면 그 record 를 방출하지 않는다. `L > tolerance` 면 종전과 **완전히 같은** `points` 로 방출한다.

**밴드가 아니다.** 살아남는 record 의 `points` 는 byte-불변이다 — 문턱은 감점의 크기를 깎지 않고 오직 **방출 여부**만 가른다. 판정은 엔진의 `records.append` **직전**(dead-zone `over<=0` 다음)에서만 일어나므로 `activated` 집합과 cross-exclusion(§10.3) 결과도 byte-불변이다. 따라서 억제는 record 를 지울 뿐 만들지 않고, **점수는 오직 올라가거나 그대로다.**

**fail-closed 6갈래.** 구간을 못 구하면 종전대로 감점한다 — "못 구했다"를 "감점 0"으로 번역하지 않는다.

| criterion / 경로 | 표본 | 처분 |
|---|---|---|
| `angle_vs_reference__{joint}` — DTW 경로 | 정렬 스텝 `\|Δ\|` 열 | **적용** |
| `angle_vs_reference__{joint}` — window 경로 | 최대 `2*window+1` 프레임 | **fail-closed.** (a) 추정량이 다르다 — 학생 window median 과 기준 window median 의 *차*이지 차이의 median 이 아니다. (b) 표본이 분포무관 구간의 최소표본(`ceil(log2(2/alpha))`)에 **구조적으로** 미달한다 |
| `split_angle` | 없음(vision 주입 추정 또는 peak) | **fail-closed** |
| `leg_extension` / `arm_extension` / `line` | 다른 추정량(`dimensions._select_window` 창 집계) | **fail-closed** — 별도 유도 필요, 범위 밖 |
| `body_relative_reach` | 시계열 없음 | **fail-closed** |
| `dimension_overall_fallback` | 편차가 아니라 whole-score | **fail-closed** |

**`suppressedRecords?`** — 지워진 감점은 사라지지 않는다. 얼마를 왜 빼지 않았는지가 남아야 점수 이동을 산술로 되짚을 수 있다(투명 합산). 억제가 실제로 일어난 doc 에만 실리는 breakdown-level additive optional(빈 경우 키 생략 — `rawPoints`/`capApplied`/`executionCap` 패턴 계승). 항목은 전부 flat scalar(`[[firestore-nested-array-flat]]`). Python lockstep = `models.SUPPRESSED_RECORD_KEYS`, TS = `SuppressedDeductionRecord`.

| 필드 | 타입 | 의미 |
|------|------|------|
| `criterion` | string | 억제된 criterion id |
| `measuredValue` | number | 그 record 가 주장하던 값 (deg) |
| `tolerance` | number | 허용치 (deg) |
| `intervalLow` | number | median 신뢰구간 하한 — 억제 판정은 `intervalLow <= tolerance` |
| `intervalHigh` | number | median 신뢰구간 상한 |
| `sampleSize` | number | 구간을 만든 표본수(관측치 — 판정에 쓰이지 않음, `0`=미제공) |
| `wouldBePoints` | number | 방출됐다면 들어갔을 감점 (SIGNED NEGATIVE, per-record 상한 적용 후) |
| `ruleId` | string | `'deviation_within_measurement_error'` |

**재구성 항등식.** `Σ wouldBePoints == executionRawTotal(억제 없음) − executionRawTotal(억제)`. `final` 산식(§10.1)은 **바뀌지 않는다** — 억제된 record 는 애초에 `records` 에 없으므로 `final == max(scoreFloor, round(100 + executionCappedTotal + criticalTotal))` 이 그대로 성립한다.

**알려진 한계(숨기지 않는다).** 부호검정 피복확률은 표본 독립을 가정한다. DTW 경로 스텝은 독립이 아니므로(같은 학생 프레임을 여러 스텝이 가리키고 인접 프레임 상관이 크다) 유효 표본수가 `n` 보다 작고 구간은 참 구간보다 **좁다** → 하한이 높다 → 억제가 **덜** 걸린다 = 종전대로 감점하는 쪽. 편향이 fail-closed 방향이다.

---

## §11. MotionAlignment (Phase 28 신설 — ALGN-01 동작 기반 비교 정렬)

`result.motionAlignment` 은 학생(left)=master 로 시계 불변, 정은지(right)만 `warp(tStudent)→tRef` 로 따라가게 하는 **동작 기반 정렬 맵**이다. VideoCompare 가 소비하며(앱 순수 함수 `alignmentWarp.ts` `warpTime`/`segmentRate`), 두 영상의 절대시계 동기화가 만드는 스크럽 drift(28-RESEARCH Pitfall 7)를 없앤다. 3-way lockstep: `app/src/types/analysis.ts` `MotionAlignment` ↔ `models.py` `MOTION_ALIGNMENT_KEYS`/`MOTION_ALIGNMENT_TIERS`/`MOTION_ALIGNMENT_SOURCES` ↔ 본 §11.

### §11.1 필드

| 필드 | 타입 | 의미 |
|------|------|------|
| `version` | string | 정렬 계약/알고리즘 버전 (예: `ma-v1`) |
| `source` | 'dtw'\|'vlm' | 정렬 출처. `dtw`=Phase 28 MotionDTW / `vlm`=Phase 22 v1 time_anchors 상위 호환 축(22-01 REPORT_KEYS time_anchors 동형) |
| `tier` | 'warped'\|'trim_only'\|'disabled' | 정렬 사다리 3단(D-02, §11.2) |
| `reason?` | string | disabled/degenerate 사유(예: `empty_path`/`invalid_fps`/`insufficient_anchors`/`rate_clamp_exceeded`). optional |
| `anchors` | number[] | **flat** `[u0,r0, u1,r1, ...]` 학생초(u)/기준초(r) 쌍. 초 단위(§11.3). u 단조 증가·r 비감소. `[[firestore-nested-array-flat]]` — nested list 금지, flat scalar 만. 상한 512(§11.4) |
| `anchorCount` | number | `len(anchors)//2` (reshape 메타 — anglesFrames 선례) |
| `distance` | number | DTW 총 정렬 거리(품질 지표) |

### §11.2 tier 사다리 3단 (D-02)

- `warped` = 구간 가변속도 (구간 기울기 clamp `[RATE_MIN=0.5, RATE_MAX=2.0]` — belle 고정값 28-CONTEXT D-01, `alignmentWarp.ts` `clampRate` + W4 lockstep 테스트).
- `trim_only` = 트림+오프셋만 (가변속도 끔 — 첫 앵커 기준 평행이동 `warp(t)=t-u0+r0`).
- `disabled` = 현행 절대시계 (워핑 없음, identity). degenerate 방출(정렬 불가/무의미)도 여기로 방출해 legacy **필드 부재**와 구별한다(과약속 배너 루프 차단, 28-01 W3).

### §11.3 초 단위 근거 (fps 도메인)

학생 영상은 9fps, reference 는 18fps 로 프레임률이 다르다(28-01 실측: 활성 reference 11 doc 전부 `keypointReport.fps=18.0`). 프레임 인덱스로 정렬하면 도메인 불일치가 생기므로(28-RESEARCH Pitfall 1), anchors 는 **초 단위**로 방출하고 fps 는 doc 메타(`keypointReport.fps`)에서 읽는다(18.0 하드코딩 금지 — 재처리 방어).

### §11.4 anchors flat 규칙 + 상한 + 역불변식 (MEDIUM-3)

- **flat 짝수 길이**: `[u0,r0, u1,r1, ...]` — 홀수 길이 무효. `anchorCount == len(anchors)//2`.
- **상한 512** (`MOTION_ALIGNMENT_MAX_ANCHOR_FLOATS`): Firestore 40k index-entry 방어(`[[firestore-index-entry-limit]]`, T-28-05). `motion_alignment.MAX_ANCHOR_FLOATS` 와 lockstep.
- **역불변식 (MEDIUM-3)**: `anchors==[]` 는 **tier 'disabled' 에서만** 유효(degenerate 방출 형상). `'warped'`/`'trim_only'` 는 **최소 2쌍(4 float) AND `anchorCount>=2`**. "warped 인데 anchors 빈" 모순 데이터를 저장 전에 거부한다(`firestore_admin._validate_motion_alignment`) — 앱 normalizer(`alignmentWarp.normalizeMotionAlignment`, 같은 규칙으로 null 폴백)와 대칭 유지 + malformed Firestore 상태 진단 가능.

### §11.5 legacy 하위호환 + Phase 22 상위 호환

- **부재(legacy doc) = 현행 절대시계 동작** (optional, no migration — `faultZoomStatus?`/`tier?` 서술 모범 준수). 앱은 필드 부재 시 워핑 없이 절대시계로 재생.
- **Phase 22 상위 호환**: `source:'vlm'` 축은 Phase 22 v1 이 방출할 time_anchors(22-01 REPORT_KEYS time_anchors 동형)를 같은 계약으로 소비하기 위한 자리 — Phase 28 은 `dtw` 만 방출, `vlm` 은 상위 호환 예약.

### §11.6 FaultZoomComparison.refMatch (D-04)

`FaultZoomComparison` 에 `refMatch?: 'dtw' | 'failed'` scalar 를 추가한다 — 기준(정은지) 측 프레임 대응 provenance. `'failed'`=DTW 대응 실패로 전신 폴백(앱이 "동작 대응 실패 — 전신 비교" 캡션 렌더), **부재(legacy)**=캡션 없음(하위호환). 동작 기반 정렬로 부위-정합 crop 을 시도했으나 실패한 케이스를 사용자에게 조용히 숨기지 않고 명시(analysis.ts `FaultZoomComparison` 주석 + Python 방출부 주석 lockstep — region/tier 선례와 동일).

### §11.7 FaultZoomComparison.criterion (33-12 A-5 — seam #1, D-12)

`FaultZoomComparison` 에 `criterion?: string` scalar 를 추가한다 — 이 crop 을 낳은 감점 record 의 criterion id (예: `angle_vs_reference__left_knee`, `split_angle`).

- **출생 정합 (33-A3 §4 확정):** crop 단위는 `visionVeto.faultJoints` 단독이 아니라 **`deductionBreakdown.records[]`(화면 표시 항목)가 가리키는 관절 집합**에서 파생한다 (`fault_zoom.criterion_units_from_records`). vision record 는 faultJoints ∩ criterion 부위로 좁힌다 (전체 투영 금지 — "다리 스플릿 항목에 어깨 crop" defect 근본 수리).
- **join 규칙:** 앱은 criterion 키 일치를 1차로 조인한다 (`deductionLabels.matchZoomForDeductionRecord`). criterion 보유 카드는 keypoint 교집합 추측 조인 대상이 아니다. **부재(legacy doc·advisory)** = 기존 교집합 폴백 (하위호환, `tier?` 서술 모범 — no migration).
- **D-12 카드 불변식 (criterion 카드 한정):** 같은 순간(기준 프레임 대응 실패)·같은 배율(한 측 전신 폴백)이 성립하지 않으면 그 카드는 방출하지 않는다 (drop — 불일치 쌍 미노출). legacy 경로는 §11.6 의 D-04 정직 폴백을 유지한다. 같은 표시 — criterion 카드는 기준(정은지) 측도 학생과 같은 시각 언어(원 마커, legs 사이각은 양측 모두 가능할 때만 둘 다)로 그린다.
- **S3 키:** criterion 카드는 `zoom_{criterion}.png` (record 별 유일 — 대표 관절 충돌 방지). legacy/advisory 는 종전 `zoom_{joint}.png`/`zoom_adv_{joint}.png`.
- **provenance 내부 전용 (D-06/D-05):** crop 의 criterion·관절·프레임 provenance 는 서버 구조 로그(`fault_zoom_crop`)에만 기록한다 — 화면 라벨로 렌더하지 않는다.
- 3-way lockstep: `analysis.ts FaultZoomComparison.criterion?` ↔ `fault_zoom.py`/`pipeline _render_fault_zoom` 방출부 ↔ 본 절 (models.py 는 status 만 소유 — §11.6 선례).

### §11.8 FaultZoomComparison.userVideoSec / refVideoSec (33-G F-3 — quick-260730-l7t)

`FaultZoomComparison` 에 `userVideoSec?: number` · `refVideoSec?: number` scalar 2개를 추가한다 — 이 카드가 가리키는 **두 패널 각각의 실영상 초**.

```
userVideoSec  number  optional  ← 학생 패널 실영상 초 (9fps 프레임 인덱스 / fps)
refVideoSec   number  optional  ← 기준 패널 실영상 초 (타임베이스 보정 후 인덱스 / fps)
```

- **값의 출처:** 백엔드가 crop PNG 좌하단에 베이크하는 타임스탬프(`fault_zoom._stamp_time`)와 **동일 산출**이다. 기준측은 `ref_display_frame_index`(rep→비디오 타임베이스 보정)를 거친 비디오 배열 인덱스에서 온다.
- **fps 도메인 주의 (F-3 근본원인):** 이 두 필드는 **비디오 9fps 공간**이고, §11 의 `userFrameIdx`/`refFrameIdx` 는 **rep(각도/keypointReport) 프레임 공간**이다. 앱이 `refFrameIdx / keypointReport.fps` 로 초를 추정해 rep(예: 18fps 329프레임) ↔ video(9fps 220프레임) 불일치를 그대로 먹은 것이 "자세 비교(참고하세요) 페어가 crop 과 다른 순간"(§9-2 F-3)의 실 원인이다. **앱은 rep 인덱스로 초를 재계산하지 않는다** — 이 필드를 그대로 쓴다.
- **용도:** 부위 상세 시트 paircap 초 표기(S6 — 승인 목업 6R "기준측 초 필수") + 참고코너/자세 비교 페어의 순간 정합(F-3).
- **`refVideoSec` 부재 조건:** 기준 프레임 대응 실패(`refMatched=false` / `refMatch='failed'`) — 전신 폴백의 중앙 프레임이라 "같은 순간"의 근거가 없다. `frames_fps<=0` 이면 양쪽 모두 부재.
- **부재(legacy doc) = 초 캡션 미렌더** (optional, migration 없음 — `tier?`/`refMatch?`/`criterion?` 선례).
- 3-way lockstep: `analysis.ts FaultZoomComparison.userVideoSec?/refVideoSec?` ↔ `fault_zoom.py` 방출부 + `pipeline _render_fault_zoom` 매퍼 ↔ 본 절.

### §11.9 FaultZoomComparison.refMarked (quick-260802-tie)

`FaultZoomComparison` 에 `refMarked?: boolean` scalar 를 추가한다 — 기준(정은지) 패널에 **표시가 하나라도 그려졌는지**를 렌더 코드가 인증한 값.

```
refMarked  boolean  optional  ← 기준 패널에 마킹(원/사이각/각도)이 그려졌는가
```

- **왜 필요한가:** 확대비교 카드의 기준 패널이 비어 있는데(오버레이 0) 아무 말 없이 나가고 있었다. 원인은 keypoint 신뢰도 게이트(`fault_zoom._KP_CONF_MIN`)·crop 포함 게이트(`_pt_in_crop`)·기준 앵커 미선언이 fail-closed 로 닫힌 **정상 동작**이지만, 비교 카드인데 비교 대상 표시가 없는 채로 침묵하는 것은 틀린 출력이다. 이 필드는 그 사실을 말하기 위한 것이지 게이트를 여는 것이 아니다 — 임계값은 무변경.
- **값의 출처:** 그리는 코드가 인증한다. `_draw_side_leg_angle`(다리 사이각, both-or-neither) · `_draw_side_joint_angle`(관절 각도 베이크, 양측 대칭) · `_mark(circle=True)`(원 마커) 중 하나라도 기준 패널에 그렸으면 `true`. **앱이 PNG 픽셀을 보고 추측하지 않는다** — 그러면 판정이 렌더 배경에 의존한다(`refMatched`/`atMatched` 와 동형·동의미).
- **방출 범위:** `criterion` 보유 카드만. legacy/advisory 카드는 게이트 B(quick-260705-wbs)로 기준측을 애초에 마킹하지 않는 **정책**이라 판정 대상이 아니다 — `false` 를 실으면 앱이 "게이트가 닫혔다"는 없는 이유를 말하게 된다.
- **부재(legacy doc·advisory·criterion 부재) = 앱 종전대로**(문구 없음). optional, migration 없음 (`tier?`/`refMatch?`/`criterion?`/`atMatched?` 선례).
- **`false` 일 때 앱 동작:** 카드를 숨기지 않고 짧은 한 줄을 덧붙인다(정보 보존). `refMatch='failed'` 캡션과 **자리를 나눠 쓴다** — 그쪽은 "같은 순간을 못 찾음"(프레임 대응 실패), 이쪽은 "순간은 맞췄는데 표시를 못 그림"(좌표 신뢰도)이다.
- 3-way lockstep: `analysis.ts FaultZoomComparison.refMarked?` ↔ `fault_zoom.py` 방출부 + `pipeline _render_fault_zoom` 매퍼 ↔ 본 절.

---

## §12. 미션 루프 + 번역 레이어 방출 (Phase 32 Plan 32-06 신설 — D-08/D-19/D-26/D-27/D-28/D-29/D-14)

미션→연습→확인 루프(D-19/D-26/D-27)와 감점 카드 번역 레이어(D-08)의 데이터 계약. 전부 `result` 안으로 흐르며(`complete_analysis` 신규 kwarg 0 — safetyFlags 선례), `firestore_admin` scoped validator(`_validate_mission`/`_validate_mission_outcome`/`_validate_summary_praise`/`_validate_coach_questions`)로만 검증한다. **방출은 32-09 파이프라인 배선부터** — 이전 doc 은 전 필드 부재(legacy 하위호환, `tier?` 서술 모범, no migration). 3-way lockstep: `app/src/types/analysis.ts` `Mission`/`MissionOutcome`/`SummaryPraise`/`CoachQuestion` + `DeductionRecord` 확장 ↔ `models.py` `MISSION_KEYS` 블록 ↔ 본 §12.

### §12.1 Mission (`result.mission`)

`analysis/mission.py` 순수 함수 `select_mission` 산출 — D-19 우선순위 **① 위험 결함(안전 안내) > ② 반복 미개선(faultKey 동일성) > ③ 감점 최대**. 결함 0 분석은 미션 없음(키 생략 — fabrication 금지).

| 필드 | 타입 | 의미 |
|------|------|------|
| `faultKey` | string | 안정 결함 판별 키 — `{motionId}::{ruleId}::{criterion}` 결정적 조합(`build_fault_key`). criterion 이 좌우 관절을 내장(`angle_vs_reference__left_knee`)해 좌우 구분이 승계된다(리뷰 blocker 1 — criterion 단독 판별은 좌우·동작을 병합). motion/rule 부재 = `unknown`/`na` 고정 폴백 |
| `criterion` | string | 선정 결함의 criterion (안전 미션은 safetyFlag `flagType`) |
| `ruleId` | string\|null | 선정 record 의 ruleId (안전 미션 null) |
| `recordId` | string\|null | 선정 record 의 안정 조인 키(§12.3) — record 에 부재 시 null |
| `selectedBy` | 'safety'\|'repeat'\|'max_deduction' | D-19 우선순위 ①②③ 중 발동 항목 |
| `streak` | number | 같은 faultKey 미개선 연속 회차 (1..99). **직전 doc 의 `mission.streak`+1 로 doc 체인 전파** — N개 문서 쿼리 없이 직전 1건으로 D-27 판정. `prev.motionId != 현재 motionId` 면 체인 리셋(다른 동작 오염 0 — `get_previous_analysis` 가 motion 을 필터하지 않는 실측 사실의 순수 함수 측 방어) |
| `isSafety` | boolean | true = 안전 미션 (D-14 해석: **streak 1 고정 + escalation 'none' 강제** — 안전은 안내·코치 유도 전용, 게임·streak·에스컬레이션 제외) |
| `escalation` | 'none'\|'exercise_detour'\|'coach_card' | D-27 — streak 2 = 보완 운동 우회, streak ≥3 = 코치 카드 전면 승격 |
| `motionId` | string\|null | 현재 분석 인식 동작 id (체인 가드 기준) |
| `baselinePoints` | number | 선정 record 의 \|points\| (≥0) — **다음 분석이 개선량을 계산하는 baseline** (D-26, 리뷰 blocker 1). 안전 미션은 0 |
| `baselineDeviation` | number\|null | \|measuredValue−baselineValue\| — 둘 다 있을 때만 |
| `targetValue` | number\|null | 선정 record 의 `baselineValue` (수치 측정 기준) |
| `unit` | string\|null | 선정 record 의 unit (`deg`/`notch`/`score_delta`) |

### §12.2 MissionOutcome (`result.missionOutcome`)

`derive_mission_outcome(prev_mission, current_records, mode, motion_id)` 산출 — **mode3 전용**(mode1/prev 부재/motionId 불일치/prev 안전 미션/prev baseline 부재 = 키 생략). **수치·bool·키만** — 사람 문장(deltaSummary 류)은 만들지 않는다(문장은 32-09 phrasebook·summaryPraise 조립 + 앱 렌더 소관 — 계산/카피 책임 분리). 수치 렌더는 D-09 invariant(헤드라인 금지, 소형 보조만).

| 필드 | 타입 | 의미 |
|------|------|------|
| `improved` | boolean | 소멸 또는 `currentPoints < baselinePoints − 0.01`(부동소수 여유) |
| `faultKey`/`criterion` | string | 추적한 지난 미션의 결함 identity |
| `baselinePoints` | number | prev mission 저장값 |
| `currentPoints` | number | 잔존 시 \|points\|, 소멸 시 0 |
| `deltaPoints` | number | baseline − current (양수=개선, 음수=악화 — 수치 진실 그대로) |
| `baselineDeviation`/`currentDeviation`/`deltaDeviation` | number\|null | 편차 트랙 (측정 쌍 있을 때만) |

### §12.3 DeductionRecord 확장 — recordId·3단 문구·tolerance

§10.2 record 에 **additive optional** 확장 (부재 = legacy doc, 기존 11+2 키 byte-호환). record 는 flat scalar dict 그대로라 기존 `_validate_dict_only_scalars` 검증 경로를 자동 통과한다(validator 본체 무변경).

- `recordId?: string` — **방출 시 1회 각인되는 안정 조인 키** (형식 `r{index:02d}:{criterion}`, 32-09 각인). 정렬·필터·숨김(32-13 스팟체크 `hiddenRecordIds`)·코치 질문 점프에 **index 대신 사용**한다(리뷰 blocker 5 — index 는 정렬/필터에 불안정).
- 3단 문구 슬롯 (D-08 상태→왜→행동, phrasebook 32-05 골격 산출): `statusLine?`(몸 말 상태) / `whyLine?`(감점·위험 이유 1줄) / `cueLine?`(외부 큐 행동) / `coachQuestion?`(강사 질문 완성문) / `exerciseId?`+`exerciseReason?`(결함→운동 연결, D-13). fail-closed 조합은 `cueLine`/`exerciseId`/`exerciseReason` 을 **생략**(일반론 조언 fabrication 차단).
- `tolerance?: number` — 규칙 상수 유래 허용 오차(게이지 스케일 재료, D-10). **자의적 수치 아님** — 32-09 가 실존 규칙 상수에서만 방출(있을 때만).

### §12.4 SummaryPraise (`result.summaryPraise`)

잘한 점 후보의 **단일 원천 = 백엔드 산출**(리뷰 blocker 5). 앱은 이 값을 그대로 소비하고, legacy doc(필드 부재)에서만 로컬 폴백을 파생한다(32-07 summarySource) — 스팟체크(32-13)가 교차검증하는 문장과 화면 문장이 동일해진다.

| 필드 | 타입 | 의미 |
|------|------|------|
| `source` | 'mission_improved'\|'clean_dimension'\|'criteria_met' | 근거 소스 (D-06 — 측정 근거에서만, 근거 없는 칭찬 금지) |
| `headline` | string (1..200자) | 사람 말 헤드라인 — **수치 미포함** (D-09 invariant: % 환산·수치 헤드라인 금지) |
| `evidenceValue` | number\|null | 근거 수치 (예: deltaPoints) — 소형 보조 표기 전용 재료 |
| `evidenceUnit` | string\|null | 근거 수치 단위 |

### §12.5 coachQuestions (`result.coachQuestions`)

코치 질문 자동 등재 목록 (D-28/D-29) — `{text, source, recordId?}` scalar dict 의 list(≤10, safetyFlags list[dict] 선례 — nested array 아님). 자동 수집 = 위험 결함 항상(`safety`) + 3회 미개선 미션(`mission_stuck`) + 이번에 못 잰 것(`unmeasured`). `recordId` 조인으로 해당 감점 카드 점프(부재 = 점프 없음).

- `text: string` (1..200자) — 문구집 스타일 완성문.
- `source: 'safety'|'mission_stuck'|'unmeasured'|'user'`. **`'user'` 는 클라이언트 로컬 전용**('강사님께 물어보기' 담기) — 백엔드 방출·validator 에 도달하지 않으며, validator 는 백엔드 방출값에서 `'user'` 를 거부한다.

### §12.6 검증 규칙 (scoped validator)

- `_validate_mission`: 키 화이트리스트(`MISSION_KEYS`) + `selectedBy`/`escalation` enum + `streak` int 1..99 + `baselinePoints` finite ≥0 + `faultKey`/`criterion` 비어있지 않은 str + nullable 필드 타입 강제. None graceful(legacy/미산출).
- `_validate_mission_outcome`: 키 화이트리스트(`MISSION_OUTCOME_KEYS`) + `improved` bool + 수치 전부 finite(NaN/inf 거부) + nullable 편차 트랙.
- `_validate_summary_praise`: 키 화이트리스트 + `source` enum + `headline` 비어있지 않은 str ≤200자 + `evidenceValue` finite\|None.
- `_validate_coach_questions`: list ≤10 + 각 항목 scalar-only dict(`_validate_dict_only_scalars` 라우팅) + `text` 1..200자 + `source` 백엔드 enum(`'user'` 거부) + `recordId` str\|None.

### §12.7 coachAudio (`result.coachAudio`) — 재생 중 큐 오디오 (Phase 32 Plan 32-16, D-18 B안)

records 의 `cueLine`(§12.3 — 승인 문구집 32-05 골격, D-09 무수치, **문구 변경 금지** = 텍스트 그대로 합성)을 백엔드가 분석 **사후** 스테이지(`coach_audio`)에서 AWS Polly(neural)로 사전 합성해 S3 `results/{uid}/{analysisId}/coach_audio_{recordId}.mp3` (canonical key 단일 출처 = `s3keys.build_coach_audio_key`)로 저장하고, `firestore_admin.update_analysis_coach_audio` 가 `result.coachAudio` **단일 field-path** 를 부분 갱신한다 (`faultZoomStatus` 사후 분리 선례 — complete(status='done') 이후 표현물 도착, 채점·verdict 무접촉). **부재(legacy doc) = 오디오 표면 미렌더** (하위호환, `tier?` 서술 모범, no migration). 합성 실패는 graceful — status done 유지, 자막 경로 무영향 (SP-3).

> **런타임 생성 예외 각주:** 클라우드 TTS 는 **분석 시점 사전 생성**으로, 32-CONTEXT 의 "런타임 신규 생성 AI 0" 은 시각 생성(교정 이미지·회전 영상) OFF 를 지칭한다 — belle 이 D-18 에서 명시 승인한 음성 합성 예외 (32-GATE-DECISIONS §샘플 게이트).

| 필드 | 타입 | 의미 |
|------|------|------|
| `status` | 'done'\|'failed' | `done` = 합성 완료 (`items` 유효 — 빈 리스트 = 재생할 큐 없음, 고아 아님) / `failed` = 스테이지 실패 (자막만 — 조용한 폴백) |
| `items` | `{recordId, key}[]` | scalar dict 배열 (safetyFlags 선례 — nested array 아님). `recordId` = §12.3 recordId — **32-12 audioCue prefetch 의 cueId(=recordId) 조인 키**. `key` = canonical S3 키(`results/` prefix). **URL 비저장** — 재생 URL 은 `POST /playback-url` `asset: 'coachAudio'` 재서명으로만 (리뷰 H-02) |

- 검증: `_validate_coach_audio` — 키 화이트리스트(`COACH_AUDIO_KEYS`/`COACH_AUDIO_ITEM_KEYS` 정확히) + `status` enum + 각 item scalar-only dict(`_validate_dict_only_scalars` 라우팅) + `recordId` 비어있지 않은 str + `key` `results/` prefix.
- 3-way lockstep: `app/src/types/analysis.ts` `CoachAudio`/`CoachAudioItem` ↔ `models.py` `COACH_AUDIO_KEYS` 블록 ↔ 본 §12.7.

### §12.8 spotCheck (`result.spotCheck`) — 문장↔영상 일치 스팟체크 (Phase 32 Plan 32-13, D-22/D-23)

감점 카드 문장(§12.3 `statusLine`/`cueLine` — 승인 문구집 골격)과 `summaryPraise.headline`(§12.4 — **백엔드 방출 단일 원천, 앱이 렌더하는 바로 그 문장**)을 백엔드가 분석 **사후** 스테이지(`spot_check`)에서 분석에 이미 쓰인 9fps 프레임 서브셋과 대조 판정하고, `firestore_admin.update_analysis_spot_check` 가 `result.spotCheck` **단일 field-path** 를 부분 갱신한다 (`faultZoomStatus`/`coachAudio` 사후 분리 선례 — complete(status='done') 이후 도착, 채점·verdict·감점 tally 무접촉). 명백 불일치(`mismatch`) 판정 record 만 `hiddenRecordIds` 로 방출 — 앱은 해당 감점 카드를 **표면에서만** 숨긴다 ("틀린 말을 내보내느니 안 보여줌", D-23). **점수 계산 내역(투명 감점 tally, §10)은 절대 필터하지 않는다** — 채점 불변 ([[scoring-must-be-transparent-deduction-tally]]).

> **표시 정책 (명문):**
> ① **spotCheck 부재(legacy doc)·미도착(pending)** = **전 카드 표시** — 현행 프로덕션과 동일. D-23 의 숨김 규칙은 '확정 불일치'에만 적용되고, 검수는 비차단 부가 레이어이므로 사전 숨김은 하지 않는다. `onSnapshot` 실시간 구독이라 늦은 숨김은 자연 반영 — **짧은 노출 후 숨김은 수용하는 트레이드오프**임을 명기한다.
> ② **`status='skipped'`(키/입력 부재)·`status='failed'`(호출/파싱 실패)** = **fail-open (전 카드 표시) + 백엔드 로그** — 근거: 검수 레이어 장애가 제품 전체를 비우는 것은 '비차단 부가 기능' 원칙 위반이며, **숨김 권한은 '명백 불일치 판정'에만** 있다 (uncertain = 표시 — 과숨김 방지, T-32-30).
> ③ `status='done'` 일 때만 `hiddenRecordIds` 를 적용한다. recordId 없는 legacy record 는 조인 불가 = 표시 유지 (fail-open 정합).

| 필드 | 타입 | 의미 |
|------|------|------|
| `status` | 'done'\|'skipped'\|'failed' | `done` = 검수 수행 (빈 `hiddenRecordIds` = 숨길 것 없음) / `skipped` = 키·프레임 부재로 미수행 / `failed` = 호출·파싱 실패 (둘 다 fail-open) |
| `hiddenRecordIds` | string[] | 명백 불일치 판정 record 의 §12.3 recordId (≤8). 카드 **표면** 숨김 전용 — tally·드릴다운 내역 미필터 |
| `verdicts` | `{recordId, verdict, reason}[]` | 감사 저장 (**사용자 비노출** — reason ≤120자, scalar dict 배열 ≤8). `verdict` ∈ 'match'\|'mismatch'\|'uncertain'. 판정 상한 8 초과 record 는 미포함(= uncertain 취급 = 표시) |
| `praiseMismatch` | boolean | `summaryPraise.headline` 교차검증 불일치 — true 면 앱이 praise 를 로컬 폴백 체인의 다음 소스로 강등 (32-07 `summarySource` 경로 — 근거 미검증 칭찬 노출 방지) |
| `model` | string | 판정 모델 id (env `GEMINI_SPOTCHECK_MODEL` 주입 — 감사) |
| `promptVersion` | string | 스팟체크 프롬프트 버전 (변경 시 bump — 판정 분포의 버전 경계 감사) |

- 검증: `_validate_spot_check` — 키 화이트리스트(`SPOT_CHECK_KEYS` 정확히) + `status`/`verdict` enum + `hiddenRecordIds` str 검증 + verdicts scalar-only dict(≤8, reason ≤120자) + **숨김-정합 불변식**(hiddenRecordIds 의 모든 id 는 verdicts 에 verdict='mismatch' 로 존재 — 숨김 권한은 명백 불일치 판정에만, T-32-30).
- 3-way lockstep: `app/src/types/analysis.ts` `SpotCheck`/`SpotCheckVerdict` ↔ `models.py` `SPOT_CHECK_KEYS` 블록 ↔ 본 §12.8.

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
*Plan 28-03 §11 추가: 2026-07-08 — MotionAlignment (ALGN-01 동작 기반 비교 정렬) 3-way lockstep (TS interface + Python MOTION_ALIGNMENT_KEYS + 본 §11). tier 3단(warped/trim_only/disabled, D-02) + 초 단위 fps 도메인(9fps vs 18fps) + anchors flat 상한 512 + tier↔anchors 역불변식(MEDIUM-3, disabled 만 빈 anchors) + legacy 하위호환 + Phase 22 source:'vlm' 상위 호환 + FaultZoomComparison.refMatch(D-04) 신설.*
*Plan 31-04 §2 + §4 추가: 2026-07-20 — Phase 31 visual 교정 시각물 3-way lockstep (TS optional 필드 + Python VISUAL_STATUSES + 본 절). correctedPose* 4 + rotation* 3 필드(URL 비저장 — 표시 URL 은 playback-url asset 재서명, 리뷰 H-02 / pending 타임아웃은 전용 *UpdatedAtMs, 리뷰 H-06) + FaultZoomComparison 뷰어 프레임 소스 3필드(D-10) + POST /visual/rotation 신설(429 daily_limit = 사용자 3건·전역 30건/일, KST 자정 리셋 명시 — 리뷰 M-06 / 503 feature_disabled 조용한 폴백 — D-08) + POST /playback-url asset 확장(server-selected key, 1시간 presign, 미지정 시 기존 동작 보존).*
*Plan 32-06 §12 추가: 2026-07-21 — 미션 루프 + 번역 레이어 방출 3-way lockstep (TS Mission/MissionOutcome/SummaryPraise/CoachQuestion + DeductionRecord 확장 ↔ models.py MISSION_KEYS 블록 ↔ 본 §12). faultKey(motionId::ruleId::criterion — 리뷰 blocker 1)·baseline 저장(D-26)·streak doc 체인+motionId 가드·에스컬레이션(D-27)·D-14 정합(안전=streak 1·escalation none 강제)·recordId 안정 조인 키+summaryPraise 단일 원천(리뷰 blocker 5)·3단 문구 슬롯(D-08)·tolerance(D-10)·coachQuestions(D-28/D-29, 'user'=클라이언트 로컬 전용). 방출은 32-09 부터 — legacy doc 부재 하위호환.*
*Plan 32-16 §12.7 + playback-url coachAudio 확장 추가: 2026-07-22 — 재생 중 큐 오디오 (D-18 B안, 32-GATE-DECISIONS §샘플 게이트 확정) 3-way lockstep (TS CoachAudio/CoachAudioItem ↔ models.py COACH_AUDIO_KEYS 블록 ↔ §12.7). Polly(neural) 사후 합성(fault_zoom 사후 분리 선례 — 채점 무접촉)·cueId(=recordId) 조인·canonical key 단일 출처(s3keys.build_coach_audio_key)·asset 'coachAudio' 재서명(recordId 형식 가드 + 서버 구성 canonical + exact 비교, H-02)·런타임 생성 예외 각주(사전 생성 — belle D-18 명시 승인). 방출은 32-16 배포부터 — legacy doc 부재 하위호환.*
*Plan 32-13 §12.8 추가: 2026-07-22 — 문장↔영상 스팟체크 (D-22/D-23) 3-way lockstep (TS SpotCheck/SpotCheckVerdict ↔ models.py SPOT_CHECK_KEYS 블록 ↔ §12.8). 사후 스테이지 판정(동기 경로 신규 외부 호출 0 — 속도 예산 구조 보호)·recordId 기반 카드 표면 숨김(tally 미필터 — 채점 불변)·praise 교차검증 동일 호출(단일 원천 = summaryPraise.headline, 리뷰 blocker 5)·표시 정책 명문(부재/pending/skipped/failed = 전 카드 표시 fail-open — 숨김 권한은 명백 mismatch 에만, uncertain = 표시)·숨김-정합 불변식. 방출은 32-13 배포부터 — legacy doc 부재 하위호환.*

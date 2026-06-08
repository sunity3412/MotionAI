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
```

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
updatedAt?         number (epoch ms)
```
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
overallScore   number              0~100 종합 (mode1=3차원 평균, mode3=절대 차원 평균)
dimensionScores { angle?, line?, stability } 각 0~100  ← IPSF 실행 차원 (3차원)
dimensionExplanation { [dim]: DimensionExplanation } optional  ← Phase 12.5 (2026-06-07)
joints         JointScore[]        관절별 (8 — 평가 관절). 코칭 팁 근거
tips           CoachingTip[]       상위 3개 (KISMAM Top-3 + Cerebras 문장)
comparison     Mode1 | Mode3       아래
myVideoUrl     string              내 영상 재생 서명 URL (좌)
referenceVideoUrl string?          mode1: 정은지 영상 (우)
```
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
weightPercent  int    각 차원이 overall 에 기여하는 비중 (%). 모든 차원의 합 = 100.
                      Largest Remainder Method: 3차원=[34,33,33], 2차원=[50,50], 1차원=[100].
baseline       string mode-aware 기준 카피. mode1 = 정은지 측정값 참조,
                      mode3 = 절대 지표 기반 (정은지 비교 X).
deficitSummary string 점수 산출과 동일 source 의 deficit 한 줄 카피.
                      angle ← kismam.top_issues worst 관절,
                      line  ← dimensions.line_deficits_by_joint (EXTEND 관절만),
                      stability ← dimensions.stability_wobble_by_joint (inter-frame diff).
                      양호 점수 (≥ 80) 시 수치 X 카피 ("안정").
```
  - 결과 화면 "왜 이 점수인지" 가시화 용도. 점수 산식 source 와 동일 windowing 사용
    (`dimensions._select_window` 공유) — drift 0 보장.
  - 이전 빌드 doc 호환: 옵셔널 필드. 키 부재 시 frontend 추가 라인 표시 X.
  - 신 backend 는 빈 `{}` 라도 항상 emit (호환성).

`JointScore`
```
key, labelKo, score(0~100)
currentAngle? targetAngle? deltaDeg?(signed) direction?  ← 구조화 가이드 (옵셔널)
issue?                                                    ← 사람 가독 폴백
```
`direction` = 'extend' | 'flex' | 'raise' | 'lower' | 'open' | 'close'
  → UI 가 "현재 145° → 기준 168° · 더 펴주세요" 형태로 표시. 구조화 필드가
  없으면 issue 텍스트로 폴백. 동적 큐(회전력·반동)는 CoachingTip.detail
  자연어로 노출(LLM 출력) — 별도 필드 만들지 않음.

`CoachingTip` = { joint?, title, detail }

`Mode1Comparison` (전문가 비교)
```
mode='mode1', referenceMotionId, referenceMotionName, athleteName, similarity(0~100)
segmentScores?   베이스 공유 기술 분석 시에만
```
`SegmentScores` = { base(0~100), extension(0~100), baseMotionId, baseMotionName }
  → 베이스 공유 reference 시퀀스를 baseUntilS 기준 베이스/확장으로 분리 후 각 KISMAM 점수.
  단일 모션은 segmentScores 없음.
`Mode3Comparison` (자기 성장)
```
mode='mode3', isFirst(bool),
previousAnalysisId?, deltaFromPrevious?{line?,stability,angle?}  (isFirst면 없음)
```
  deltaFromPrevious = 발전(progress). '몇 % 일치'가 아니라 절대 차원(라인/안정성)의
  이전 분석 대비 증감(±). 절대 지표라 세션 간 같은 척도. 첫 분석이면 없음.
  키는 양쪽 분석 공통 차원만 (line 이 한쪽에 없으면 stability 만).

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

### BodyComparisonFinding (R9 fix: 5 IPSF + Sunity pose_reliability_low — 6 enum)

| TS 필드 | Python 필드 | TS 타입 | 설명 |
|---|---|---|---|
| `deficitCode` | `deficit_code` | `string` | 6 enum 중 하나 (아래 표). |
| `jointKey` | `joint_key` | `string \| null` | finding 이 단일 관절에 귀속될 때만. |
| `measuredValue` | `measured_value` | `number` | 측정값 (각도 deg / 거리 px). |
| `deductionScore` | `deduction_score` | `number` | IPSF Page 21 절대 감점 (-0.2, -0.5). 체형 ratio 곱하지 않음 (Notebook §3.3). |
| `confidence` | `confidence` | `number` | 0~1. |
| `bodyTypeAdjusted` | `body_type_adjusted` | `boolean` | true = 정규화 좌표에서 측정, false = raw 좌표. |

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

### warnings enum (R2 fix — 8종, reference_source_pose_missing 신규 추가)

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

*최초 작성: 2026-05-19 — #5 착수 전 계약 확정. 변경 시 app/src/types/analysis.ts 동기화 필수.*
*Phase 1 §6 추가: 2026-05-31 — PoseFrame/PoleAxis 3-way lockstep (H-3/H-4/M-1/M-2/M-5 REVIEWS 박제).*
*Plan 01-19 §7 추가: 2026-06-02 — BodyNormalizationProfile (D-19 segment 비율, D-21 nullable). RTMW pivot 박제.*
*Plan 06-01 §8 + §8.2 추가: 2026-06-08 — BodyComparisonReport (D-06-B3 + W1 + C14) + BodyComparisonSourcePose (R2 round-2 reviews).*

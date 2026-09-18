# reference-motions.md — 기준 모션 카탈로그

> 정은지 선수 기준 모션의 단일 진실(source of truth).
> 영상 분석 결과 + 개발 통합 지시 + 런타임 추출 규칙이 모두 여기에 있다.
> 새 영상 추가 시 §6 절차(잠정 — Phase 21 이 자동화 대상)를 따른다.

---

## 1. 이 파일의 역할

```
영상 1개 등록 = 다음 세 곳이 동시에 일관돼야 함
  ① Firestore reference/{motionId}      (앱이 구독)
  ② S3 sunity-motion-pilot-videos/      (영상 본체 + 썸네일)
  ③ docs/contract.md §3 스키마          (앱 ↔ 백엔드 계약)

이 파일이 ①②③ 모두의 단일 출처. Claude Code는 이 파일만 읽고도
세 곳을 정합성 있게 갱신할 수 있어야 한다.
```

---

## 2. 등록 규칙

```
motionId : ref-{기술명-소문자-하이픈}  (예: ref-sideway-spin)
           → S3 키, Firestore 문서 ID 동일. 로컬 영상 작업본 파일명은
             업로드 시 S3 키로 매핑되므로 달라도 무방.

level    : basic | intermediate | advanced

entryType : step_entry | jump_entry | swing_entry | lift_entry | invert_entry | combo_entry

videoUrl : s3://sunity-motion-pilot-videos/reference/{motionId}.mp4

clipRange : 영상 전체를 1회 연속 사이클로 가정.

athleteName : 현재는 '정은지' 고정 (파일럿)
```

---

## 3. 데이터 스키마

정본 = `app/src/types/analysis.ts` 의 `ReferenceMotion` (`docs/contract.md` §3 와 동기).
Firestore 실제 키는 camelCase 다 (`app/scripts/seed-reference-motions.mjs:473-499`).
주석의 seed / reprocess / backfill 은 그 필드를 채우는 스크립트다.

```typescript
interface ReferenceMotion {
  motionId: string;
  name: string;                 // seed
  athleteName: string;          // seed — 현재 '정은지' 고정
  level: 'basic' | 'intermediate' | 'advanced';  // seed
  entryType?: EntryType;        // seed
  entryDescription?: string;    // seed
  description?: string;         // seed
  videoUrl?: string;            // seed — 7일 presigned HTTPS URL
  videoUrlExpiresAt?: number;   // seed — epoch ms (앱 만료 안내용)
  videoS3Key?: string;          // seed — 백엔드가 비교 영상 재서명에 사용
  thumbnailUrl?: string;        // 미사용 — 자동 생성은 §7 미결
  clipRange?: ClipRange;        // seed
  checkpoints?: Checkpoint[];   // seed
  sharedBaseMotionId?: string;  // seed(조건부) — 공유 베이스 체인
  baseUntilS?: number;          // seed(조건부)
  isActive: boolean;            // seed
  updatedAt?: number;           // seed — epoch ms

  // reprocess_reference_motions_phase4.py (Pod GPU) 산출.
  // Firestore 는 nested array 를 금지하므로 (T, J) 행렬을 flat 으로 저장하고
  // anglesJointKeys 길이로 reshape 한다.
  angles?: number[];            // reprocess — 길이 = anglesFrames * anglesJointKeys.length
  anglesJointKeys?: string[];   // reprocess — 길이 J (보통 8, skeleton.JOINT_KEYS)
  anglesFrames?: number;        // reprocess — T
  referenceKeypointReport?: KeypointReport | null;  // reprocess

  // backfill_reference_downstream.py --write-candidate 산출
  meanAngles?: Record<string, number>;   // backfill (없으면 앱이 angles 에서 derive)
  bodyNormalizationProfile?: BodyNormalizationProfile | null;  // backfill
  bodyComparisonSourcePose?: BodyComparisonSourcePose | null;  // backfill
  techniqueProfile?: {                    // backfill
    name: string;
    category: string;
    jointExpectations: Record<string, string>;
  } | null;
  forceDirectionPattern?: ForcePatternInference | null;        // backfill
  captureViews?: number;                  // backfill — v1 단일시점은 전부 1
}

type EntryType =
  | 'step_entry' | 'jump_entry' | 'swing_entry'
  | 'lift_entry' | 'invert_entry' | 'combo_entry';

interface ClipRange {
  prepStartS: number;
  execStartS: number;
  execPeakS: number;        // 시각적 피크
  landEndS: number;
  recommendedRecordS: number;
}

interface Checkpoint {
  joint: string;
  weight: number;
  note?: string;
}
```

체크포인트 weight 합 = 1.0 (문서 규약 — 채점은 이 weight 를 읽지 않는다, §4).

---

## 4. 런타임 추출 규칙

```
1. clipRange 의 실제 소비처는 공유 베이스 경계 한 곳이다.
   · backend/functions/pipeline/app.py:7989-7993 — segments.ref_boundary_frame
   · app/src/lib/referenceMotions.ts:178 (정규화) · app/src/types/analysis.ts:1217 (타입)
   기준 angles 는 영상 전체 프레임에서 추출된다 — extract_reference_angles.py 와
   reprocess_reference_motions_phase4.py 에 clipRange 참조 0건.

2. 사용자 영상은 전체 프레임 추출
   → MotionDTW subsequence matching 으로 자동 정렬
```

(2026-09-18 정정) 실제 채점 관절은
`backend/shared/python/sunity_shared/analysis/skeleton.py` 의 JOINT_KEYS 8개
(elbow·shoulder·hip·knee 좌우) 고정이다. `checkpoints[].weight` 는 채점에 쓰이지 않고
`spine_mid` 는 이 집합에 없다. 옛 규칙 3(weight 가중평균)은 그래서 삭제했고,
옛 규칙 4(exec 피크 프레임을 결과 hero 프레임 URL 로 저장)도 리포 전체 참조 0이라 삭제했다.

`prepStartS` 는 런타임 분석엔 안 쓰임 — 사용자 UX 가이드용.

---

## 5. 등록된 모션

11편 (2026-09-18). 메타의 문서 정본은 여기지만 Firestore 반영은
`app/scripts/seed-reference-motions.mjs` 의 MOTIONS 배열을 통해서만 일어난다 —
두 곳이 어긋나면 앱이 보는 값은 Firestore 라이브(= seed 결과)다.
활성 버전 포인터 = `reference/_release.activeCandidate` (2026-09-18 현재 `rot180_v1`).

---

### ref-sideway-spin

```yaml
motionId:    ref-sideway-spin
name:        사이드웨이 스핀
athleteName: 정은지
level:       intermediate
entryType:  swing_entry
entryDescription: |
  폴 옆에서 오른팔 상단 그립을 잡은 뒤 다리 스윙으로 회전력을 만들어 진입.
  점프보다 스윙으로 만든 각운동량으로 폴을 감아오르며 시계 방향 회전 시작.
description: |
  상단 그립을 잡고 몸을 뒤로 아치한 채 한 다리를 연장한 자세로
  연속 회전하는 중급 기술. 하나의 자세를 유지하는 것이 아니라
  회전 중 백 아치 라인과 다리 라인이 자연스럽게 변형되며 이어진다.
videoUrl:    s3://sunity-motion-pilot-videos/reference/ref-sideway-spin.mp4
```

**원본 영상 분석**

```
영상 길이        : 19.79초
영상 내 반복     : 없음 — 1회 연속 회전
회전 방향        : 시계 방향
주 그립 손       : 오른손 상단 그립
```

**clipRange**

```yaml
clipRange:
  prepStartS:         0
  execStartS:         2
  execPeakS:          9      # 주의 — 기본값 (6s/12s 둘 다 깔끔, 중간값)
  landEndS:           18
  recommendedRecordS: 22
```

**채점 체크포인트**

```yaml
checkpoints:
  - joint:  right_shoulder
    weight: 0.20
    note:   주 지지 팔(오른손 상단 그립)의 견갑 안정성.
            어깨가 올라가면 회전축이 흔들려 백 아치 라인이 흐트러짐
  - joint:  spine_mid
    weight: 0.25
    note:   척추 아치 곡률. 허리만 꺾이지 않고 흉추까지 함께 열려야 발레 라인이 살아남
  - joint:  left_hip
    weight: 0.20
    note:   ⚠ 자유 다리 좌우는 추정 (왼쪽 가능성).
            자유 다리 측 고관절 신전. 신전 부족하면 아치가 얕아짐
  - joint:  left_knee
    weight: 0.20
    note:   ⚠ 자유 다리 좌우 추정. 자유 다리 신전.
            무릎 굽으면 발레 라인이 무너지고 chair spin처럼 보임
  - joint:  right_hip
    weight: 0.15
    note:   폴 측 고관절 정렬. 회전 중 골반이 닫히면 백 아치가 깊어지지 못함
```

---

### ref-climb

```yaml
motionId:    ref-climb
name:        클라임
athleteName: 정은지
level:       basic
entryType:  swing_entry
entryDescription: |
  폴 옆에서 오른팔 상단 그립을 잡은 뒤 다리 스윙으로 반동을 만들어
  몸을 띄우며 양 무릎을 X자 형태로 폴에 건다.
description: |
  상단 그립을 잡고 양 무릎을 폴 앞뒤에 X자로 걸어 연속 회전하는
  기초 스핀. 왼쪽 무릎이 폴 앞, 오른쪽 무릎이 폴 뒤를 잡아 두
  무릎이 폴을 사이에 두고 교차한다. 두 무릎의 접촉 안정성이
  체공 시간과 회전 매끄러움을 결정한다.
videoUrl:    s3://sunity-motion-pilot-videos/reference/ref-climb.mp4
```

**원본 영상 분석**

```
영상 길이        : 17.08초
영상 내 반복     : 없음 — 1회 연속 회전
회전 방향        : 시계 방향
주 그립 손       : 오른손 상단 그립
훅 구조          : 양 무릎 X자 — 왼쪽 무릎 폴 앞, 오른쪽 무릎 폴 뒤
```

**clipRange**

```yaml
clipRange:
  prepStartS:         0
  execStartS:         1.5
  execPeakS:          5
  landEndS:           15
  recommendedRecordS: 18
```

**채점 체크포인트**

```yaml
checkpoints:
  - joint:  left_knee
    weight: 0.25
    note:   폴 앞쪽 훅 다리. 두 무릎 중 먼저 걸리는 쪽이라 진입 안정성 핵심.
            앞 무릎이 폴에 깊게 닿지 않으면 X자 잠금이 약해져 미끄러짐
  - joint:  right_knee
    weight: 0.20
    note:   폴 뒤쪽 훅 다리. 앞 무릎과 X자로 폴을 잠금 완성.
            뒤 무릎 풀리면 회전이 점점 느려지며 떨어짐
  - joint:  right_shoulder
    weight: 0.20
    note:   주 지지 팔(오른손 상단 그립) 견갑 안정성.
            어깨가 으쓱하면 회전축이 흔들려 X자 훅이 풀리기 쉬움
  - joint:  left_hip
    weight: 0.15
    note:   앞 다리 측 골반 외전. 골반 닫히면 앞 무릎이 폴에서 떨어짐
  - joint:  right_hip
    weight: 0.10
    note:   뒤 다리 측 골반 정렬. X자 형태가 한쪽으로 기울지 않게 받쳐줌
  - joint:  spine_mid
    weight: 0.10
    note:   측면 자세 유지. 상체 기울면 chair spin처럼 보이며 라인 무너짐
```

---

### ref-invert

```yaml
motionId:    ref-invert
name:        인버트
athleteName: 정은지
level:       intermediate          # ⚠ advanced일 가능성
entryType:  lift_entry
entryDescription: |
  폴 옆에서 양손 그립을 잡은 뒤 팔을 굽혀(리프트) 몸을 끌어올리며
  돌아 진입. 팔 근력으로 가슴을 폴에 붙이며 측면 자세로 올라감.
description: |
  양손 그립 유지한 채 두 단계로 회전.
  1단계(전반): 가슴을 폴에 붙이고 머리는 다리 위로,
              왼발 굽힘 + 오른발 신전으로 측면 플랭크 라인
  2단계(후반): 머리를 아래로 떨어뜨려 인버트 전환,
              양 다리를 일자로 찢어 스플릿 라인 완성
  리프트 안정성, 단계 전환의 매끄러움, 인버트 스플릿 좌우 대칭이 채점 핵심.
videoUrl:    s3://sunity-motion-pilot-videos/reference/ref-invert.mp4
```

**원본 영상 분석**

```
영상 길이        : 17.25초
영상 내 반복     : 없음 — 1회 연속 회전, 두 단계 자세 전환
회전 방향        : 시계 방향
주 그립 손       : 왼손 상단 + 오른손 보조, 양손 그립 유지
자세 전환 시점   : 5~6초 (측면 플랭크 → 인버트 스플릿)
```

**clipRange**

```yaml
clipRange:
  prepStartS:         0
  execStartS:         1
  execPeakS:          7
  landEndS:           15
  recommendedRecordS: 18
```

**구간별 동작**

| 구간 | 시점 | 동작 |
|---|---|---|
| prep | 0~1s | 양손 그립 확보 |
| entry | 1~3s | 팔 굽혀 리프트 — 가슴을 폴에 붙이며 끌어올림 |
| execution-A | 3~5s | 측면 플랭크 라인 — 가슴 폴 접촉, 머리 다리 위, 왼발 굽힘 + 오른발 신전 |
| transition | 5~6s | 머리 아래로 떨어뜨리며 인버트 전환 |
| execution-B | 6~10s | 인버트 스플릿 — 머리 아래, 양 다리 일자 찢기 (피크 7초) |
| landing | 10~15s | 다리 회수, 회전 감속, 폴 옆 착지 |

**채점 체크포인트**

```yaml
checkpoints:
  - joint:  left_shoulder
    weight: 0.20
    note:   주 지지 팔(왼손 상단 그립) 견갑 안정성.
            리프트 진입과 인버트 전환 모두에서 가장 중요한 지지점
  - joint:  right_shoulder
    weight: 0.15
    note:   보조 지지 팔. 회전 중 양 어깨 균형 깨지면 회전축이 흔들림
  - joint:  left_hip
    weight: 0.20
    note:   인버트 스플릿 시 왼다리 측 골반 외전 각도.
            골반 닫히면 다리 일자 찢기가 짧아져 스플릿 라인 손상
  - joint:  right_hip
    weight: 0.20
    note:   인버트 스플릿 시 오른다리 측 골반 외전.
            좌우 비대칭이면 다리 찢기가 한쪽으로 기울어 보임
  - joint:  right_knee
    weight: 0.10
    note:   1단계 신전 다리 + 2단계 스플릿 한쪽 다리. 무릎 굽으면 라인 흐려짐
  - joint:  spine_mid
    weight: 0.15
    note:   측면 → 인버트 전환 시 몸통 정렬.
            허리 꺾이면 단계 연결이 거칠어 보임
```

---

### ref-foxtop

```yaml
motionId:    ref-foxtop
name:        폭스탑
athleteName: 정은지
level:       advanced
entryType:  lift_entry
entryDescription: |
  인버트와 동일한 리프트 진입을 사용. 측면 플랭크 → 인버트
  다리 찢기까지가 공유 베이스. 이후 다리 교환과 수직 스플릿으로 이어짐.
description: |
  앞 6초까지는 인버트와 완전 동일 (측면 플랭크 → 인버트 다리 찢기).
  이후 다리 교환(왼 무릎 hook ↔ 오른 무릎 hook)과 수직 스플릿
  (다리 일자 찢기를 수직 자세로 유지)으로 확장되며, 마지막에 폴 감싸기로
  회전 종료. 다리 교환 매끄러움과 수직 스플릿 좌우 대칭이 채점 핵심.
videoUrl:    s3://sunity-motion-pilot-videos/reference/ref-foxtop.mp4
```

**원본 영상 분석**

```
영상 길이        : 28.31초
영상 내 반복     : 없음 — 1회 연속 동작
회전 방향        : 시계 방향
주 그립 손       : 왼손 상단 + 오른손 보조, 양손 그립 유지
인버트와 관계     : 0~6초 구간 동일 (같은 베이스 공유)
```

**clipRange**

```yaml
clipRange:
  prepStartS:         0
  execStartS:         1
  execPeakS:          18    # 수직 스플릿 구간(15~21초) 중간
  landEndS:           27
  recommendedRecordS: 30
```

**구간별 동작**

| 구간 | 시점 | 동작 |
|---|---|---|
| prep | 0~1s | 양손 그립 확보 |
| entry | 1~3s | 리프트 — 팔 굽혀 가슴을 폴에 붙이며 끌어올림 |
| plank-base | 3~6s | 인버트와 동일 — 측면 플랭크 → 인버트 + 다리 찢기 |
| leg-hook-A | 6~9s | 왼쪽 무릎으로 폴 감싸기, 오른쪽 다리 펼침 |
| leg-exchange | 9~12s | 다리 교환 — 오른쪽 무릎으로 폴 감싸기, 왼쪽 다리 펼침 |
| leg-hook-B | 12~15s | 교환 자세 유지 회전 |
| vertical-split | 15~21s | 수직 스플릿 — 다리 일자 찢기, 인버트 유지, 왼쪽 다리 위. 시각적 피크 |
| wind-down | 21~22s | 왼쪽으로 다시 폴 감싸며 회전 감속 |
| landing | 22~27s | 폴 잡고 위로 올라오며 폴 옆 착지 |

**채점 체크포인트**

```yaml
checkpoints:
  - joint:  left_shoulder
    weight: 0.20
    note:   주 지지 팔(왼손 상단 그립) 견갑 안정성. 전 구간 주 지지점.
            견갑 무너지면 다리 교환과 수직 스플릿 모두 진입 불가
  - joint:  right_shoulder
    weight: 0.15
    note:   보조 지지 팔. 다리 교환 순간 양 어깨 균형 깨지면 회전축 흔들림
  - joint:  left_hip
    weight: 0.15
    note:   다리 교환 시 왼쪽 무릎 감싸기 측 골반 외전.
            수직 스플릿 시 위로 가는 다리(왼쪽)의 신전 시작점
  - joint:  right_hip
    weight: 0.15
    note:   다리 교환 시 오른쪽 무릎 감싸기 측 골반 외전.
            좌우 비대칭이면 수직 스플릿 라인이 한쪽으로 기울어짐
  - joint:  left_knee
    weight: 0.10
    note:   왼 무릎 감싸기(6~9초) + 수직 스플릿 시 위 다리 무릎 신전
  - joint:  right_knee
    weight: 0.10
    note:   오른 무릎 감싸기(9~12초) + 수직 스플릿 시 아래 다리 무릎 신전
  - joint:  spine_mid
    weight: 0.15
    note:   전 구간 인버트 정렬. 다리 교환과 수직 스플릿 전환 중
            허리 꺾이면 단계 연결이 어색해 보임
```

---

### ref-foxtop-split

```yaml
motionId:    ref-foxtop-split
name:        폭스탑 스플릿
athleteName: 정은지
level:       advanced
entryType:  lift_entry
entryDescription: |
  인버트 / 폭스탑과 동일한 리프트 진입.
  팔을 굽혀 가슴을 폴에 붙이며 측면 플랭크 라인으로 끌어올림.
description: |
  앞 18초까지는 폭스탑과 동일 흐름
  (측면 플랭크 → 인버트 → 다리 교환 → 스플릿). 이후 자세 전환 후
  양팔 펼침 / 수평 라인 자세를 슬로우 로테이션으로 유지하며 마무리.
  마무리 직전(약 30초)에 그립을 왼손→오른손으로 교체하며 폴 옆 착지.
  채점 피크는 11~13초의 양 다리 좌우 펼침(스플릿) 자세.
videoUrl:    s3://sunity-motion-pilot-videos/reference/ref-foxtop-split.mp4
```

**원본 영상 분석**

```
영상 길이        : 32.30초  (등록된 모션 중 최장)
영상 내 반복     : 없음 — 1회 연속 동작
회전 방향        : 시계 방향
주 그립 손       : 왼손 상단 + 오른손 보조, 양손 그립 유지
그립 교체        : 약 30초 — 마무리 직전에 오른손이 위로 (이전 4개 모션엔 없는 특징)
폭스탑과 관계      : 0~18초 베이스 공유 (정은지 선수 확정)
```

**clipRange**

```yaml
clipRange:
  prepStartS:         0
  execStartS:         1
  execPeakS:          12      # 양 다리 좌우 펼침(스플릿) 구간 — 정은지 선수 확정
  landEndS:           30
  recommendedRecordS: 35
```

**구간별 동작**

| 구간 | 시점 | 동작 |
|---|---|---|
| prep | 0~1s | 양손 그립 확보, 한 다리 들어올리기 시작 |
| entry | 1~3s | 리프트 — 팔 굽혀 가슴을 폴에 붙이며 끌어올림 |
| plank-base | 3~6s | 측면 플랭크 → 인버트 전환 (ref-invert / ref-foxtop 공유 베이스) |
| pose-A | 6~10s | 한 다리 폴 감싸기 + 다른 다리 펼침. 인버트 상태 두 다리 분리 |
| pose-B — 채점 피크 | 11~13s | 양 다리 좌우 펼침(스플릿). 시각적 피크 (정은지 선수 확정) |
| pose-transition | 14~17s | 다리 모양 변형, 자세 이행 |
| foxtop-tail | 17~18s | 폭스탑 흐름 마무리 (정은지 선수 기준점) |
| extended-pose | 18~22s | 양팔 펼침 + 수평 라인 + 다리 펼침 — 폭스탑엔 없는 추가 자세 |
| slow-rotation | 22~26s | 자세 유지하며 회전 감속. 회전 모멘텀 떨어진 상태로 자세 안정성 시험 |
| recover | 27~28s | 인버트 해제, 폴 잡고 내려옴 |
| grip-shift | ~30s | 그립 교체 — 왼손 → 오른손 상단으로 전환 |
| landing | 28~31s | 폴 옆 한 다리 디딤, 마무리 포즈 |

**채점 체크포인트**

```yaml
checkpoints:
  - joint:  left_shoulder
    weight: 0.20
    note:   주 지지 팔(왼손 상단 그립). 0~26초 거의 전 구간 주 지지점.
            특히 18~26초 추가 자세 + 슬로우 로테이션 구간에서
            견갑 무너지면 양팔 펼침 라인이 즉시 흐트러짐
  - joint:  right_shoulder
    weight: 0.15
    note:   보조 지지 팔. 다리 교환 + 추가 자세 + 30초 그립 교체에서 핵심.
            슬로우 로테이션 시 양 어깨 균형 깨지면 수평 라인이 한쪽으로 기움
  - joint:  spine_mid
    weight: 0.20
    note:   인버트 정렬 + 슬로우 로테이션 자세 유지의 핵심.
            회전 모멘텀이 줄어드는 22~26초 구간에서 가장 먼저 무너지는 지점
  - joint:  left_hip
    weight: 0.15
    note:   ⚠ 자세별 다리 좌우는 추정.
            스플릿 피크(11~13초) 좌우 대칭 + 추가 자세 다리 신전 시작점
  - joint:  right_hip
    weight: 0.15
    note:   ⚠ 자세별 다리 좌우는 추정.
            스플릿 피크 좌우 대칭. 비대칭이면 채점 피크 라인이 한쪽으로 기울어짐
  - joint:  left_knee
    weight: 0.08
    note:   다리 hook + 펼침 시 무릎 신전. 굽으면 라인이 흐려져 자세가 흐트러짐
  - joint:  right_knee
    weight: 0.07
    note:   다리 hook + 펼침 시 무릎 신전. 굽으면 라인이 흐려져 자세가 흐트러짐
```

---

### ref-kip-up

(원값 = seed-reference-motions.mjs, 2026-06-12 belle 결정)

```yaml
motionId:    ref-kip-up
name:        킵업
athleteName: 정은지
level:       basic
entryType:   swing_entry
entryDescription: |
  폴 옆에서 양손 그립 셋업 후 점프 이륙. 다리 사이드 스윕 후방 통과 시 와이드 스트래들로 진입.
description: |
  폴에 양손으로 매달려 다리 반동으로 회전을 만드는 동적 entry 스킬. 인버전 (머리 골반 아래)
  없이 머리 위·발 아래 자세 유지하며 약 3-3.5회전 (1080-1260°). 콤보 연결기 또는
  코어/팔 근력 트레이닝용. IPSF 미등재 dynamic transition.
videoUrl:    s3://sunity-motion-pilot-videos/reference/ref-kip-up.mp4
```

**clipRange**

```yaml
clipRange:
  prepStartS:         0
  execStartS:         1
  execPeakS:          4
  landEndS:           7.2
  recommendedRecordS: 10
```

**채점 체크포인트**

```yaml
checkpoints:
  - joint:  left_shoulder
    weight: 0.2
    note:   풀업 그립 측 견갑 안정성. 어깨 처지면 다리 스윙 추진력 손실
  - joint:  right_shoulder
    weight: 0.2
    note:   푸시 그립 측 견갑 안정성. 보조 지지 약하면 회전축 흔들림
  - joint:  left_hip
    weight: 0.15
    note:   스윙 추진력 핵심. 후방 통과 시 와이드 스트래들 폭 결정
  - joint:  right_hip
    weight: 0.15
    note:   좌우 대칭 스트래들. 비대칭이면 회전이 한쪽으로 기울어짐
  - joint:  left_knee
    weight: 0.1
    note:   스윙 시 무릎 신전. 굽으면 추진 모멘트 작아짐
  - joint:  right_knee
    weight: 0.1
    note:   좌우 무릎 신전 대칭. 짧아지면 다리 라인 흐트러짐
  - joint:  spine_mid
    weight: 0.1
    note:   상체 후굴 + 다리 모음 사이클. 흉추 안 열리면 회전이 끊김
```

---

### ref-peter-pan

(원값 = seed-reference-motions.mjs, 2026-06-12 belle 결정)

```yaml
motionId:    ref-peter-pan
name:        피터팬
athleteName: 정은지
level:       basic
entryType:   swing_entry
entryDescription: |
  폴 옆에서 상하 스플릿 그립(위쪽 손 head 위, 아래 손 가슴~골반 높이) 셋업 후
  공중에 매달려 셰이프 정리.
description: |
  상하 스플릿 그립으로 매달린 채 한 다리 무릎을 폴에 hook, 다른 다리는 뒤로 길게 펴는
  스태그(stag) 셰이프. 약 4회전 연속 hold-in-rotation. 하늘을 나는 피터팬 실루엣 닮음.
  한국/세계 학원 통용 기초 스핀. IPSF 미등재.
videoUrl:    s3://sunity-motion-pilot-videos/reference/ref-peter-pan.mp4
```

**clipRange**

```yaml
clipRange:
  prepStartS:         0
  execStartS:         0.7
  execPeakS:          4
  landEndS:           7.4
  recommendedRecordS: 10
```

**채점 체크포인트**

```yaml
checkpoints:
  - joint:  left_shoulder
    weight: 0.2
    note:   위쪽 그립 측 견갑. 회전 중 어깨 떨어지면 셰이프 라인 무너짐
  - joint:  right_shoulder
    weight: 0.15
    note:   아래 보조 그립. 두 손 거리 유지 안 되면 셰이프 불안정
  - joint:  left_hip
    weight: 0.2
    note:   폴 hook 측 골반 외전. 깊게 접혀야 hook 안정
  - joint:  right_hip
    weight: 0.2
    note:   뒤로 펴는 자유 다리 측 고관절 신전. 신전 부족하면 피터팬 실루엣 안 나옴
  - joint:  left_knee
    weight: 0.1
    note:   hook 측 무릎 굽힘 각도. 너무 펴면 hook 풀림
  - joint:  right_knee
    weight: 0.1
    note:   자유 다리 무릎 신전. 굽으면 라인 짧아짐
  - joint:  spine_mid
    weight: 0.05
    note:   척추 정렬. 측면 plank 라인 유지
```

---

### ref-power-spin

(원값 = seed-reference-motions.mjs, 2026-06-12 belle 결정)

```yaml
motionId:    ref-power-spin
name:        파워스핀
athleteName: 정은지
level:       intermediate
entryType:   swing_entry
entryDescription: |
  폴 옆에서 양손 스플릿 그립(오른손 위·왼손 아래) 셋업 후 푸시오프로 공중 진입.
  다리 턱(tuck)으로 회전력 만들기.
description: |
  스플릿 그립으로 양손 매달려 다리를 턱↔extension 으로 반복(펌핑)하며 약 3.5-4회전.
  후반(약 6.6s 이후)에 오른다리 폴 따라 수직 위로, 왼다리 아래로 펴는 vertical split
  자세로 약 2.5회전 hold. 강한 원심력을 버티는 split 그립 dynamic 회전. IPSF 미등재.
videoUrl:    s3://sunity-motion-pilot-videos/reference/ref-power-spin.mp4
```

**clipRange**

```yaml
clipRange:
  prepStartS:         0
  execStartS:         0.5
  execPeakS:          7
  landEndS:           9.9
  recommendedRecordS: 12
```

**채점 체크포인트**

```yaml
checkpoints:
  - joint:  left_shoulder
    weight: 0.2
    note:   아래 푸시 그립 측 견갑. 강한 원심력을 버티는 핵심 — 무너지면 split 라인 불안정
  - joint:  right_shoulder
    weight: 0.2
    note:   위쪽 풀업 그립 측 견갑. 회전축 기준 — 떨어지면 vertical split 한쪽으로 기울어짐
  - joint:  left_hip
    weight: 0.15
    note:   아래 다리 측 고관절. 펌핑 시 신전→굴곡 부드러움이 회전 모멘텀 결정
  - joint:  right_hip
    weight: 0.15
    note:   위 다리(폴 따라 수직) 측 고관절. 후반 split 의 vertical alignment
  - joint:  left_knee
    weight: 0.1
    note:   아래 다리 무릎 신전. 굽으면 split 라인 짧아짐
  - joint:  right_knee
    weight: 0.1
    note:   위 다리 무릎 신전. 굽으면 수직 라인 무너짐
  - joint:  spine_mid
    weight: 0.1
    note:   몸통 정렬. 펌핑 ↔ split 전환 사이 흉추 안정성
```

---

### ref-elbow-twist-sister

(원값 = seed-reference-motions.mjs, 2026-06-12 belle 결정)

```yaml
motionId:    ref-elbow-twist-sister
name:        엘보 트위스트 시스터
athleteName: 정은지
level:       advanced
entryType:   lift_entry
entryDescription: |
  공중에서 양손 그립 + 다리 셰이프 변화로 진입. 1.5~5.5s 사이 다리를 폴에 hook 하며
  상체 뒤로 젖혀 점진적 도립.
description: |
  인버트 + 무릎 hook + 엘보 백 그립 + 윗다리 수직 익스텐션의 결합.
  5.5~9.5s 빌드업(프리암 → 엘보 그립 → 다리 익스텐션) 후 9.5~17.5s 메인 hold 약 8초 —
  도립 + 백벤드 + 트위스트 + 수직 익스텐션 유지하며 회전 지속. 17.5s 이후 릴리즈→ 직립 복귀.
  IPSF 미등재 (Inverted Inner Thigh Hook/Scorpio + Elbow back grip + split 결합 변형).
videoUrl:    s3://sunity-motion-pilot-videos/reference/ref-elbow-twist-sister.mp4
```

**clipRange**

```yaml
clipRange:
  prepStartS:         0
  execStartS:         5.5
  execPeakS:          13
  landEndS:           21.9
  recommendedRecordS: 25
```

**채점 체크포인트**

```yaml
checkpoints:
  - joint:  left_shoulder
    weight: 0.15
    note:   엘보 백 그립 측 견갑. 등 뒤로 돌린 팔의 안정성 — hold 8초 핵심
  - joint:  right_shoulder
    weight: 0.15
    note:   폴 그립 측 견갑. 도립+트위스트 유지의 주 지지점
  - joint:  left_hip
    weight: 0.15
    note:   무릎 hook 측 고관절. 도립 자세 잠금
  - joint:  right_hip
    weight: 0.2
    note:   윗다리(수직 익스텐션) 측 고관절 신전. Pencil/Vertical 라인 결정
  - joint:  left_knee
    weight: 0.1
    note:   hook 무릎 굽힘 깊이. 풀리면 도립 자세 무너짐
  - joint:  right_knee
    weight: 0.15
    note:   윗다리 무릎 완전 신전. 굽으면 vertical 라인 손상 — 채점 핵심
  - joint:  spine_mid
    weight: 0.1
    note:   백벤드 곡률. 흉추까지 열려야 트위스트 깊이 살아남
```

---

### ref-pdshape

(원값 = seed-reference-motions.mjs, 2026-06-12 belle 결정)

```yaml
motionId:    ref-pdshape
name:        pdshape
athleteName: 정은지
level:       advanced
entryType:   lift_entry
entryDescription: |
  영상 시작 시점에 이미 인버전 + 회전 상태 (지면→공중 entry 영상 밖).
  다리 셰이프 정리(턱 → 신전 → 스트래들 경유)로 hold 진입.
description: |
  정식 명칭 없는 연계 동작 — 학원에서 "pdshape" 로 통용. 0~3.5s 인버전 셰이프 정리 후
  3.5~11.5s 메인 클로즈드 셰이프 hold 약 8초 — 한 다리 hip-knee hook + 다른 다리
  굽힘(folded) + 양손 폴 + 비대칭 inverted hold + 회전 유지.
  11.5~13.7s 오픈 레그 라인 변형 (시저→수평 신전). 12회전+ 등속.
  IPSF 미등재 (Inverted Torso Hook/Butterfly + Scorpio variation 결합).
videoUrl:    s3://sunity-motion-pilot-videos/reference/ref-pdshape.mp4
```

**clipRange**

```yaml
clipRange:
  prepStartS:         0
  execStartS:         3.5
  execPeakS:          8
  landEndS:           15
  recommendedRecordS: 18
```

**채점 체크포인트**

```yaml
checkpoints:
  - joint:  left_shoulder
    weight: 0.2
    note:   한쪽 폴 그립 측 견갑. 메인 hold 8초 동안 비대칭 체중 받치는 핵심
  - joint:  right_shoulder
    weight: 0.15
    note:   보조 폴 그립 측 견갑. 비대칭 안정성
  - joint:  left_hip
    weight: 0.2
    note:   hook 측 고관절. 한 다리 hook 깊이 — 클로즈드 셰이프 잠금
  - joint:  right_hip
    weight: 0.15
    note:   굽힌 다리 측 고관절. folded position 의 좌우 균형
  - joint:  left_knee
    weight: 0.1
    note:   hook 측 무릎. 풀리면 hold 무너짐
  - joint:  right_knee
    weight: 0.1
    note:   굽힌 다리 무릎 각도. 너무 펴거나 굽으면 셰이프 흐트러짐
  - joint:  spine_mid
    weight: 0.1
    note:   척추 비대칭 정렬. 회전 중 라인 변형 (오픈 레그) 시 흉추 안정성
```

---

### ref-combo

(원값 = seed-reference-motions.mjs, 2026-06-12 belle 결정)

```yaml
motionId:    ref-combo
name:        콤보
athleteName: 정은지
level:       advanced
entryType:   swing_entry
entryDescription: |
  스탠딩 준비(0~1.5s) → 워크어라운드(팔 벌려 진입) → 스핀 콤보 시작.
  약 62초 multi-segment 연계.
description: |
  여러 IPSF 등재/미등재 기술을 끊김 없이 연결한 콤보. 10 segment 박힘:
  Spin sequence(1.5~13.5s, 5-6개 다리 셰이프 변경) → Climb(13.5~18.5s) →
  Inverted entry V/chopper(18.5~20.5s) → Leg Hang hold + 익스텐션(28~37.5s,
  33s 아웃사이드 레그 행 명확) → Butterfly 계열(37.5~44s, 익스텐디드 버터플라이) →
  인버티드 셰이프 전환(44~53s) → Finale display(53~57.5s) → Dismount(57.5~62s).
  IPSF Dynamic Combinations 카테고리 + Outside Leg Hang + Butterfly 등 등재 카테고리 mix.
videoUrl:    s3://sunity-motion-pilot-videos/reference/ref-combo.mp4
```

**clipRange**

```yaml
clipRange:
  prepStartS:         0
  execStartS:         1.5
  execPeakS:          33
  landEndS:           57.5
  recommendedRecordS: 65
```

**채점 체크포인트**

```yaml
checkpoints:
  - joint:  left_shoulder
    weight: 0.15
    note:   주 그립 측 견갑. 62초 multi-segment 전체에 걸친 지지점. 클라임~버터플라이 전환 핵심
  - joint:  right_shoulder
    weight: 0.15
    note:   보조 그립 측 견갑. 다양한 그립 전환(스플릿/엘보/하이 그립) 안정성
  - joint:  left_hip
    weight: 0.15
    note:   레그 행 + 버터플라이 + 셰이프 전환의 좌측 골반. 다양한 hook 깊이 변동 큰 구간
  - joint:  right_hip
    weight: 0.15
    note:   우측 골반. 좌우 다리 교대 hook 시 비대칭 변화 큼
  - joint:  left_knee
    weight: 0.1
    note:   훅/익스텐션 사이 무릎 변화량 큰 segment 마다 신전
  - joint:  right_knee
    weight: 0.1
    note:   우측 무릎. 다리 교대 시 풀림→hook 부드러움
  - joint:  spine_mid
    weight: 0.2
    note:   척추 정렬. 직립→인버트→백벤드 등 다양한 정렬 변화 — 콤보 흐름의 핵심 신호
```

---

## 6. 새 모션 등록 절차

잠정 절차 (2026-09-18). 이 수동 런북은 Phase 21(프로 셀프서비스 기준 등록,
belle 2026-08-30 요구사항 — 파일럿 Step 2 직결)이 없애려는 대상이다.
Phase 21 이 살아 있는 동안 이 절차를 정본으로 고착시키지 말 것.

이미 배포된 `POST /reference/auto-register`
(`backend/functions/reference-auto-register/app.py`, `backend/template.yaml` 라우트)는
Gemini A 로 메타(motionId / clipRange / checkpointJoints)를 자동 생성해 upsert 한다.
그러나 `name`·`athleteName`·`level` 을 쓰지 않아 앱 선택 화면에 뜨지 않고 `angles` 도
만들지 않는다 — 이것만으로 등록이 완결되지 않으므로 아래 [0]~[7] 이 전부 필요하다.

```
[0] 활성 버전 확인
    Firestore reference/_release.activeCandidate 를 읽어 그 이름을 <활성버전> 으로 쓴다.
    (2026-09-18 현재 rot180_v1)

[1] 영상 분석 + §5 블록 확정 → 이 파일 §5 에 append (키는 camelCase).

[2] aws s3 cp {파일}.mp4 s3://sunity-motion-pilot-videos/reference/{motionId}.mp4

[3] seed-reference-motions.mjs 의 MOTIONS 에 블록 추가 → cd app && npm run seed:reference
    (메타·presigned URL·isActive 만 쓴다. angles 는 여기서 안 쓴다.)

[4] Pod GPU 에서 (CUDA 필수, 기동은 /start)
    ROT180_INVERSION_ENABLED=1 python backend/scripts/reprocess_reference_motions_phase4.py --version <활성버전> --no-flip --motions {motionId}
    # ROT180_INVERSION_ENABLED=1 필수. RTMW 엔진은 이 플래그를 런타임 env 로만 읽고
    # 코드 기본은 off 다 (rtmw_engine.py:62-66). 활성 기질 rot180_v1 은 이 플래그를 켠
    # 상태로 추출됐다 — 안 켜면 신규 1편만 비회전 각도로 들어가 11편과 기질이 섞이고,
    # 그 비대칭의 실측 결과가 정은지 자기비교 100 -> 60 이다
    # (start_server.sh:24 가 같은 경고를 적어놨다).
    → reference/{motionId}/versions/<활성버전> 에 angles·joints3d·keypointReport 생성.

[5] Pod GPU 에서
    python backend/scripts/backfill_reference_downstream.py --reference-version <활성버전> --bucket sunity-motion-pilot-videos --write-candidate --motions {motionId}
    # 이 스크립트의 --motions 는 쉼표 분리 목록이다 ([4] reprocess 의 --motions 는 공백
    # 분리 — 두 스크립트가 서로 다르다). --bucket 은 candidate 백필에 필요하다.
    → meanAngles·techniqueProfile·bodyNormalizationProfile·forceDirectionPattern·
      bodyComparisonSourcePose·captureViews 백필.

[6] FIREBASE_SA_PATH=firebase-sa.json python backend/scripts/promote_reference_version.py --version <활성버전> --motions <기존 11편 + 신규> --dry-run
    이상 없으면 --dry-run 을 빼고 다시 실행한다.
    → _release.activeCandidate flip + top-level 미러 + 해시 검증.

[7] 검수 — 새 모션으로 mode1 분석 1건을 완주시켜 status=done 을 확인한다.
```

주의

```
(a) [4][5] 를 Pod 밖 CPU 에서 돌리지 말 것.
(b) mode1 파이프라인은 angles 없는 기준 doc 을 만나면
    RuntimeError("기준 모션 또는 keyframe 데이터 없음") 으로 끝난다
    (backend/functions/pipeline/app.py:7896-7898).
    [3] 까지만 하면 등록된 것처럼 보이고 분석만 실패한다.
(c) ref-combo 의 top-level doc 은 1013KB 로 Firestore 1MB 한도의 99% 다.
    콤보보다 긴 모션을 넣으면 한도에 걸린다.
```

**선수 사전 검증 (최소)**

```
사전에 카톡으로 확인할 것은 motionId 한국어 이름 + level 뿐.
체크포인트 가중치, peak 시점, 자유 다리 좌우 등 세부 사항은
MVP 완성 후 실제 분석 결과를 함께 보며 정은지 선수와 수정.
추상적 데이터를 사전 검증받는 것보다 결과를 보고 수정하는 게
정보 밀도가 훨씬 높음.
```

---

## 7. 미결 / 추후 결정

```
- 비전 AI 통합 시 신뢰 데이터 검증 트리거 (MVP 개발 단계 필수):
  도메인 데이터(가중치 등)는 MVP 후 일괄 검증이지만, 시스템 신뢰성은
  개발 단계에서 반드시 확보 — 신뢰 데이터로 개발돼야 실증이 의미를 가짐.

  · (2026-09-18 정정: 구 2D 백본 joint 매핑 항목과 reference 영상 overlay
    시각 검증 항목 2개는 백본이 RTMW 로 바뀌어 영구 미실행 — 삭제.
    spine_mid 는 JOINT_KEYS 8개에 없어 채점에 닿지 않는다.)

  · MotionDTW sanity check: ref ↔ ref 자가 매칭 시 distance ≈ 0,
    서로 다른 모션 간엔 명확히 분리되는지 확인. 분리 안 되면 특징
    벡터 구성(각도/각속도/각가속도 비율) 재검토.

  · clipRange 시각 검증: 각 모션의 execStartS ~ landEndS 구간
    에서 DTW 가 의도한 자세 시점에 정렬되는지 확인. 어긋나면 reference
    측 clipRange 조정.

- 모든 ⚠ 인라인 항목 (가중치, peak, 좌우 등):
  MVP 시연 시 정은지 선수와 분석 결과 함께 보며 일괄 수정.
  사전 추정값은 시스템 작동에 문제 없음.
  점수가 어색하게 나오는 부분이 자연스럽게 버그 리포트가 됨.

- thumbnailUrl 자동 생성 (execPeakS 프레임 ffmpeg 추출)
- 좌우 대칭 기술: motionId 에 -mirror 접미사 별도 등록

★ 공유 베이스 모션 (sharedBaseMotionId 필드) — 우선순위 상향:
    현재 발견된 베이스 공유 체인:
      ref-invert        (~17s)
        └─ 0~6s 공유 ─┐
      ref-foxtop        (~28s)
        └─ 0~18s 공유 ─┐
      ref-foxtop-split  (~32s)

    세 모션이 단일 계층 트리(L1→L2→L3)를 이룸.
    스키마 확장 검토 항목:
      · sharedBaseMotionId: string (어느 모션의 베이스를 공유하는지)
      · baseUntilS: number (몇 초까지 공유 베이스인지)
      · 부분 점수: 베이스 구간 점수 + 확장 구간 점수 분리 평가
      · 학생 학습 경로: L1(인버트) → L2(폭스탑) → L3(폭스탑 스플릿) 순서 가이드

- 체크포인트 정답: 정은지 선수 시연 후 코칭 우선순위 반영
- entryType 자동 판별 (포즈 시퀀스 기반)
```

---

## 8. 외부 근거 — IPSF Code of Points

> 출처: `docs/research/pole-aerial-sports.md` (NotebookLM 폴/에어리얼 스포츠
> 리서치, 2026-05-21). §5 의 ⚠ 추정값 일부가 이 자료로 뒷받침·조정됨.
> 도메인 정답은 여전히 정은지 선수 검토가 최종 — 이 섹션은 "추정의 근거"를 기록할 뿐.

### 8-1. 허용 오차 20도 → KISMAM 반영 완료

```
IPSF 공식 채점은 관절 각도·스플릿에 20도 허용 오차를 적용.
백엔드 kismam.DEFAULT_TOLERANCE_DEG 가 관절별 12~15도였던 것을
20도 단일 기준으로 조정함 (관절별 중요도 차등은 checkpoint weight 가 담당).
→ 같은 자세에 대해 점수가 덜 박하게 나옴.
```

### 8-2. 체크포인트 표현이 IPSF 감점 기준과 일치 (추정 검증)

§5 체크포인트의 추정 note 들이 IPSF 정식 기준과 부합 — 방향은 맞았음.

| §5 체크포인트 표현 | IPSF 근거 |
|---|---|
| 어깨 "견갑 안정성" | 견갑 하강(scapular depression)은 IPSF 초급 핵심 역량 |
| 무릎/팔꿈치 "신전" | 신전 불량·발끝 안쪽 굽음(sickled feet) 각 −0.1 감점 |
| "완전히 펴야 하는 자세" | 사지 굽으면 해당 요소 0점 (Fully Extended 규정) |

### 8-3. 난이도 분류 근거 (§5 level 의 ⚠ 일부 해소)

```
IPSF LTAD 트레이닝 단계:
  초급 : 그립 컨디셔닝, 기본 클라임, 정지 스핀, 견갑 하강
  중급 : 점프 모멘텀이 아닌 코어 근력으로 하는 공중 인버트
  고급 : 폭발적 다이내믹 플립, 복합 리그립
```

→ `ref-invert` 의 "intermediate ⚠ advanced 가능성": 공중 인버트
자체는 중급선이므로 intermediate 유지가 타당. 다리 찢기(스플릿)는 고급
유연성 요소이나 단계 분류의 기준 동작은 인버트 — 최종은 정은지 선수 확인.

### 8-4. 구간 분리 채점 — 부분 점수 방향 뒷받침

```
IPSF 는 복합 동작에 기술 보너스를 준다:
  다이내믹 콤비네이션(DC) : 신체가 폴에서 분리되는 고속 결합, 최대 +3.0
  부실한 전환(흐름 부족)   : −0.5 감점
```

→ 한 기술을 베이스/확장 구간으로 나눠 점수화하는 §7 방향과 부합.
단계 "전환"의 매끄러움 자체를 점수화하는 것은 여전히 §7 미결 항목.

### 8-5. 우리 범위 밖

자료의 의상·음악·반도핑·무대 규격·심사 행정은 경기 운영 규정 —
자세 분석 파이프라인과 무관. 참고만.

---

*v1 (2026-05-20): 발레리나 스핀 분석*
*v2: 발레리나 + 프론트 훅 스핀*
*v3: + 플랭크 스핀, 인버트 버터플라이 콤보, 제미니 에이샤 콤보 (영상 미본 추측 포함)*
*v4: 4개 모션 영상 검증 완료 — 발레리나 / 프론트 훅 / 플랭크 / 인버트 버터플라이*
*v5: ref-gemini-to-ayesha-combo 추가 — 0~18s 베이스 공유 인사이트 확정, §7 shared_base_motion_id 우선순위 상향*
*v4.2: 개발 집중형 정리 — 사전 검증은 명칭/난이도만,
        세부는 MVP 후 일괄 수정 방향*
*v4.3: §7 비전 AI 통합 시 신뢰 데이터 검증 트리거 추가 (joint 매핑 / ViTPose 시각 검증 / DTW sanity / clip_range 정합)*
*v4.4: §8 외부 근거(IPSF Code of Points) 추가 — 허용 오차 20도
              KISMAM 반영, 체크포인트·난이도·콤보 채점 근거 정리*
*v7 (2026-09-18, quick-260918-qm2): §3 camelCase + 실사용 필드 · §4 소비처 실측 정정(clipRange 는 공유 베이스 경계만, 가중평균·hero 프레임 규칙 삭제) · §5 11편 · §6 잠정 절차(ROT180_INVERSION_ENABLED=1 명시, auto-register 한계, Phase 21 이 자동화 대상) · §7 구 2D 백본 검증 2항목 삭제*
*v6 (2026-05-22): 정은지 선수 명칭 확정 —
       발레리나 스핀→사이드웨이 스핀, 프론트 훅 스핀→클라임,
       플랭크 스핀→인버트, 인버트 버터플라이 콤보→폭스탑,
       제미니 투 에이샤 콤보→폭스탑 스플릿. motionId·S3 키 동일 갱신.
       '연속 동작=하나의 기술' — 콤보 용어 제거, 베이스/확장 구간 점수
       구조는 유지. 난이도 불변. 명칭은 브라우저 검증 완료.*

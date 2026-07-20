---
phase: 31-api-visual-correction
plan: 08
subsystem: app-ui
tags: [visual-correction, reference-corner, pose-compare, 2d-viewer, firestore-hook]
requires:
  - 31-04 (TS 계약 — FaultZoomComparison.userFrameIdx/refFrameIdx/refMatched, correctedPose*/rotation*)
  - 31-03 (DTW 대응 프레임 쌍 방출)
provides:
  - useReferenceMotionDoc (reference/{id} 단일 문서 joints3d 구독)
  - PoseCompareViewer (카메라 평면 고정 2D 중첩 뷰어, react-native-svg)
  - ReferenceCornerSection ("참고하세요" 섹션 — 상태 구동, 조용한 폴백)
affects:
  - 31-11 (result.tsx 통합 + playback-url 재서명 배선 — 본 컴포넌트 소비처)
tech-stack:
  added: []
  patterns:
    - "단일 문서 구독으로 대형 배열 격리 (컬렉션 구독 확장 금지)"
    - "렌더 가드는 caller 소유 (ScoreBreakdownSection 선례)"
    - "네트워크는 caller 소유 — 컴포넌트는 콜백만 노출"
key-files:
  created:
    - app/src/components/PoseCompareViewer.tsx
    - app/src/components/ReferenceCornerSection.tsx
  modified:
    - app/src/lib/referenceMotions.ts
decisions:
  - "교정 자세 카드 = 참고코너 소속 (option-a, belle 승인)"
  - "'회전' 문구는 Wan2.7 영상 카드에서만 허용, 뷰어에서는 금지"
  - "투영축 = x(가로)/z(세로), 깊이축 폐기"
metrics:
  duration: 1 session
  tasks: 3
  completed: 2026-07-20
---

# Phase 31 Plan 08: 2D 자세 비교 뷰어 + 참고코너 Summary

amended D-10 의 정직한 계약을 구현했다 — 회전 없는 2D 중첩 뷰어(react-native-svg),
저비용 단일 문서 reference 로드, 그리고 실패를 에러로 노출하지 않는 상태 구동
"참고하세요" 섹션.

## What Was Built

### Task 1 — 목업 선제시 + 카드 위치 확정 (checkpoint:decision)

belle 승인 결과:

- **option-a 확정** — 교정 자세 카드는 참고코너 소속. 배치는 `보완 운동` 아래,
  `참고 지표` 근처.
- **목업 5종 전부 무수정 승인** (correctedPose failed / mode3 / rotation pending /
  만료 URL / refMatched false).
- **문구 규칙 스코핑 확정** — "회전"은 Wan2.7 영상 카드에서만 허용(산출물이 실제
  회전 영상이므로 정직), `PoseCompareViewer` 에서는 금지.
- **Figma** — 코디네이터가 fileKey `jrdI7kp245HkPfLB0nclsz` 를 직접 조회. 결과
  화면 프레임은 mode1/mode3 first/mode3 progress/자세히 모달까지만 존재하고
  참고코너·교정된 자세·회전 영상 프레임은 **없음** → CLAUDE.md §4 "미설계 화면도
  멈추지 말 것"에 해당하는 자체 구성. 기존 결과 화면 카드 스타일·타이포 위계를
  그대로 따르고 새 시각 언어를 만들지 않았다.

option-b 전제 오류를 실행 전에 잡아 보고했다: 독립 결함 줌 캐러셀은 존재하지
않고 `faultZoomComparisons` 는 `result.tsx:1036-1050` 드릴다운 시트 안에서
소비된다. 따라서 "캐러셀 옆" 배치는 성립하지 않으며 채점 드릴다운에 비채점
생성물을 섞게 된다. 이 정정이 option-a 선택의 근거가 됐다.

### Task 2 — `useReferenceMotionDoc` + `PoseCompareViewer` (`d2a53a9`)

**`app/src/lib/referenceMotions.ts`** — `doc(db, 'reference', id)` 단일 문서
`onSnapshot` 훅 신설. 기존 `useReferenceMotions` 컬렉션 구독은 손대지 않았다
(리뷰 M-02). `joints3d` 는 T×17×3 flat 배열이라 컬렉션 구독에 실으면 reference
전 건의 대형 배열을 매 구독마다 내려받게 된다.

`reshapeJoints3d` 는 flat 길이 / 키 개수(17) / `coordDim`(3) / `joints3dFrames`
메타를 교차 검증하고 하나라도 어긋나면 `null` 로 강등한다. **부분 복구를 시도하지
않는다** — 어긋난 배열을 잘라 쓰면 엉뚱한 관절이 이어진 스켈레톤을 자신있게
보여주는 최악의 실패가 된다. 비수치/NaN/inf 좌표는 NaN 으로 통일해 뷰어가 유한값
검사 한 번으로 건너뛴다. reference 문서 write 0 (읽기 전용, 40k index-entry).

**`app/src/components/PoseCompareViewer.tsx`** — `react-native-svg` 만 사용
(`three`/`@react-three` import 0). 렌더 파이프라인:

1. 투영 = 축 0(x, 가로) + 축 2(z, 세로), 깊이축 폐기. 근거는 구 R3F 뷰어의 축
   분산 분석(z~235, x~95, y≈0) — y≈0 축을 세로로 쓰면 스켈레톤이 한 줄로 깔린다.
2. 자세별 독립 정규화 — 고관절 중점 원점 이동 + 몸통(어깨중점~고관절중점) 길이
   스케일. 체격 차이가 아니라 형태를 비교하게 된다.
3. COCO-17 인접 bone 12개를 **이름으로 선언하고 `jointKeys` 로 인덱스 해석** —
   배열 순서를 맹신하면 키 순서가 다른 문서에서 엉뚱한 관절이 이어진다.
4. 내 자세 = `colors.brand` 실선 / 목표 자세 = `colors.neutralDark` opacity 0.4.
5. 기준점 부재 또는 몸통 길이 ≈0 이면 `null` — 축척을 정할 수 없는 자세를 억지로
   그리지 않는다.

### Task 3 — `ReferenceCornerSection` (`5739af2`)

`ScoreBreakdownSection` 표준형(named export + inline prop 타입 + 헤더 주석 +
StyleSheet 하단 + 토큰만)으로 신설. 카드 3종을 상태로 구동한다:

| 카드 | 상태 | 'hidden' 처리 |
|------|------|---------------|
| 교정된 자세 | hidden / pending / loading / ready | 카드 미렌더 |
| 자세 비교 뷰어 | userPose·refPose 유효 시만 | 렌더 생략 |
| 회전 참고 영상 | hidden / pending / ready / requestable | 카드 미렌더 |

- `Alert`/`Toast`/에러 배너 호출 0 (D-08 조용한 폴백). `Alert` import 자체가 없다.
- 만료 URL 복구는 `Image onError` → `onCorrectedPoseImageError` **콜백 노출까지만**.
  `POST /playback-url` 재서명은 31-11 소유이므로 직접 호출하지 않는다 (리뷰 H-02).
- 회전 pending 카피는 "만들고 있어요. 몇 분 걸려요" — 진행률/남은시간 수치 없음.
- 3종 전부 숨김이면 섹션 자체를 렌더하지 않는다 (헤더만 남는 빈 껍데기 방지).
- 점수 수치 0, 다각도 촬영 유도 0, 하드코딩 색상 0, 이모지 0.

## Key Decisions

**투영축을 데이터 근거로 골랐다.** RTMW `pole_aligned` 좌표의 수직 분산은 Z 축에
있다. 관례적으로 y 를 세로로 쓰면 y≈0 이라 스켈레톤이 납작해진다.

**세로 부호를 가정하지 않고 데이터로 결정했다.** z 의 증가 방향이 위인지 아래인지
문서화된 보장이 없어, 어깨 중점이 고관절 중점보다 항상 화면 위에 오도록 부호를
런타임에 정한다. 좌표계 부호가 바뀌어도 뒤집힌 사람이 그려지지 않는다.

**mode3/refMatched=false 는 학생 단독 렌더가 아니라 숨김이다.** DTW 대응은 mode1
reference 에만 성립한다(Pitfall 6). 한쪽 자세만 그려놓고 "비교"라 부르는 것보다
숨기는 편이 정직하다. 구현상 caller 가 `refPose=null` 을 내리면 자연히 숨겨진다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 한국어 조사(을/를) 하드코딩 제거**

- **Found during:** Task 3
- **Issue:** 교정 자세 캡션을 `${관절라벨}를 고친 자세예요` 로 썼는데, 조사는
  받침 유무로 갈린다 ('왼쪽 무릎'→을, '어깨'→를). 관절 라벨이 늘어날 때마다
  틀린 조사가 새고 컴파일로 못 잡는다.
- **Fix:** 조사가 필요 없는 형태로 변경 — 캡션 `교정한 부위 · ${라벨}`,
  accessibilityLabel `${라벨} 교정된 자세 이미지`.
- **Files modified:** `app/src/components/ReferenceCornerSection.tsx`
- **Commit:** `5739af2`

**2. [Rule 2 - 계약 준수] 회전 요청 카피에서 재촬영 함의 제거**

- **Found during:** Task 3
- **Issue:** "여러 방향에서 돌려 보는 참고 영상을 만들 수 있어요" 가 사용자에게
  다각도 재촬영을 요구하는 것으로 읽힐 여지가 있었다 (단일 카메라 invariant
  [[single-camera-first-multi-view-last]] 저촉 위험).
- **Fix:** "내 동작을 여러 방향에서 본 참고 영상을 **만들어 드려요**" — 생성 주체가
  앱임을 명시.
- **Files modified:** `app/src/components/ReferenceCornerSection.tsx`
- **Commit:** `5739af2`

### 계약 마찰 (기록용, 코드 변경 아님)

Task 2 acceptance 의 `"3D" 문구 0` 게이트는 **주석까지 포함**하므로, 제거된 구
뷰어를 컴포넌트 이름(`PoseViewer3D`)으로 인용할 수 없다. 초안은 그 이름으로 출처를
달았다가 게이트에 걸려 "구 R3F 뷰어" + `result.tsx:1191` 행 참조로 바꿨다.
추적성은 행 번호로 유지된다. 게이트는 대소문자 구분으로 판정했다 — 계약 필드명
`joints3d`(소문자)는 사용자 문구가 아니라 스키마 키라 대상이 아니다.

## Known Stubs

없음. 세 산출물 모두 완결 상태이며, 남은 것은 31-11 의 배선(실제 `userPose`/
`refPose` 프레임 추출, 재서명 호출, `result.tsx` 섹션 삽입)이다 — 이는 본 플랜
범위 밖으로 명시돼 있다.

## Verification

- `cd app && npm run typecheck` → exit 0 (심볼릭 링크 절차, 링크 제거 후 커밋)
- `PoseCompareViewer.tsx`: `3D|회전` 매치 0, `three`/`@react-three` import 0,
  `react-native-svg` 사용 확인
- `ReferenceCornerSection.tsx`: 하드코딩 hex 0, `Alert`/`Toast` 호출 0
  (헤더 주석의 금지 선언 1건만), 이모지 0, named export 확인
- `referenceMotions.ts`: `collection(db` 1건(기존 `useReferenceMotions`) —
  신규 컬렉션 구독 0, `doc(db, 'reference'` 1건
- artifact 최소 줄수: viewer 225 (≥80), section 287 (≥120)
- `git status` 에 `?? node_modules` 없음 — 커밋 전 매회 확인
- backend/ 무접촉, `result.tsx`·`api.ts` 무접촉, STATE.md/ROADMAP.md 무접촉

## Self-Check: PASSED

- `app/src/components/PoseCompareViewer.tsx` FOUND
- `app/src/components/ReferenceCornerSection.tsx` FOUND
- `app/src/lib/referenceMotions.ts` FOUND (modified)
- commit `d2a53a9` FOUND
- commit `5739af2` FOUND

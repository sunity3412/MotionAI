---
phase: 31-api-visual-correction
plan: 11
subsystem: app-integration
tags: [visual-correction, reference-corner, api-client, typed-error, resign-url]
requires:
  - 31-04 (TS 계약 — correctedPose*/rotation*, FaultZoomComparison idx 필드)
  - 31-08 (PoseCompareViewer / ReferenceCornerSection / useReferenceMotionDoc)
provides:
  - ApiError (status + 계약 code 보존)
  - requestRotationVideo / fetchVisualAssetUrl
  - visualCards.ts (카드 상태 파생 순수 로직 — import 0)
  - result.tsx 참고코너 통합
affects:
  - 31-12 (실기기 HUMAN-UAT 적립 대상)
tech-stack:
  added: []
  patterns:
    - "순수 모듈은 import 0 으로 유지 — plain-node 검증 가능성이 설계 제약"
    - "오류 분기는 계약 code 로만 (message 문자열 파싱 금지)"
    - "표시 URL 은 저장하지 않고 매 표시마다 재서명"
key-files:
  created:
    - app/src/lib/visualCards.ts
    - app/src/lib/__tests__/visualCards.test.mjs
  modified:
    - app/src/lib/api.ts
    - app/src/app/analysis/result.tsx
    - .planning/phases/31-api-visual-correction/31-CONTEXT.md
decisions:
  - "D-06 = option B (화면 열림 중 실시간 갱신), 푸시 알림 미구현"
  - "jest-expo 도입 철회 — 의존성 1,120개 대비 파일럿 가치 낮음 (belle)"
  - "rotation pending 타임아웃은 'hidden' 이 아니라 'requestable' 로 복구"
metrics:
  duration: 1 session
  tasks: 4
  completed: 2026-07-20
---

# Phase 31 Plan 11: 앱 통합 (참고코너 배선) Summary

typed `ApiError` 로 오류 분기를 문자열 파싱에서 계약 `code` 로 옮기고, 표시 URL 을
매번 재서명으로 발급하며, 31-08 이 만든 무동작(inert) 컴포넌트를 실제 데이터에 배선했다.
테스트 러너 승인이 중간에 철회되면서 검증 전략을 신규 의존성 0 으로 다시 짰다.

## What Was Built

### Task 1 — 테스트 러너 (설치 → 철회)

패키지 정당성 게이트에서 플랜 원문 명령의 결함 두 가지를 먼저 잡아 보고했다:

1. 플랜은 `npm install --save-dev jest-expo jest @testing-library/react-native` 를
   **무핀**으로 지시했다. 무핀 해석 결과는 `jest-expo@57`(Expo SDK 57) + `jest@30` 인데
   이 앱은 **SDK 54** 다. `jest-expo@54` 는 jest **29** 생태계(`babel-jest@^29`,
   `@jest/globals@^29`, `jest-environment-jsdom@^29`)에 묶여 있어 원문 명령은 깨진
   조합을 만든다.
2. RNTL `14.0.1` 은 peer 로 `test-renderer@^1.0.0` 이라는 **네 번째** 신규 패키지를
   요구한다. `13.3.3` 은 `jest-expo@54` 가 이미 벤더링한 `react-test-renderer@19.1.0`
   을 그대로 쓴다.

belle 는 정정된 핀 세트(`jest-expo@~54.0.17` / `jest@~29.7.0` / RNTL `~13.3.3`)로
승인했고 설치·검증까지 마쳤으나(`2fb00fd`), **transitive 1,120개를 보고 승인을
철회**했다. `a56cb89` 에서 `package.json`/`package-lock.json` 을 설치 이전으로 복원하고
`npm ci` 로 트리를 되돌렸다.

### Task 1c — D-06 실체 결정 (`9d2bb92`)

belle **option B**: "완료 알림" = 결과 화면이 열려 있는 동안의 `onSnapshot` 실시간
갱신. 푸시 인프라(`expo-notifications`)는 이번 phase 밖. `31-CONTEXT.md` D-06 에
`[AMENDED]` 로 사유·사용자 영향·범위 경계를 박제했다.

범위 경계를 CONTEXT 에 명시한 이유: Figma 에 이미 `알림` 프레임과 "분석 결과를
알림으로 알려드려요" 카피가 있어, 알림은 회전 영상만의 문제가 아니라 **분석 완료
알림까지 아우르는 독립 기능**이다. 후속 작업자가 31 안에서 이걸 넓히지 않도록 적었다.

### Task 2 — `ApiError` + 클라이언트 2종 + `visualCards.ts` (`f56e560`)

**`api.ts`** — `ApiError extends Error { status, code }` 신설. 오류 봉투
`{error:{code,message}}` 에서 `code` 를 뽑아 보존하고, 파싱 실패 시 `'unknown'`.
`message` 포맷은 기존과 **글자 단위로 동일**하게 유지해 기존 소비처를 건드리지 않았다.
`requestRotationVideo` / `fetchVisualAssetUrl` 은 200/202 라도 계약 필드가 없으면
`malformed_response` 로 던진다 — 빈 응답이 `'pending'` 으로 흘러가면 카드가 영원히
로딩으로 남는다.

**`visualCards.ts`** — `visualCardState` / `mapFrameIdx` / `pickCompareFrames` /
`isDailyLimit` / `isFeatureDisabled`. 타임아웃 상수에 "**서버 잡을 취소하지 않는
표시 폴백**"임을 주석으로 명시했다 (리뷰 L-04).

### Task 3 — `result.tsx` 통합 (`3d3c580`)

참고하세요 섹션을 **보완 운동 아래 / 참고 지표 위**에 삽입했다 (line 2043, D-09
option-a). 채점 표면을 전부 지난 뒤에 오므로 "점수 비반영"이 레이아웃만으로 드러난다.

- 카드 상태는 전용 `correctedPoseUpdatedAtMs` / `rotationUpdatedAtMs` 로만 판정 (H-06).
- 표시 URL 은 mount 시 재서명 발급, `Image onError` 시 **1회만** 재발급 (무한 루프 방지).
  **Firestore URL/key 필드 소비 0** — grep 으로 확인 (H-02).
- 훅은 전부 무조건 호출. mode 분기는 `targetRefId = mode1 ? id : null` 인자로만 표현 (M-04).
- 회전 요청은 busy 가드 + `daily_limit` 만 인라인 고지, 나머지는 조용히 원복 (D-08).
- **신규 `setInterval` 0** — 갱신은 `onSnapshot` 재렌더가 전담.

## Key Decisions

**`visualCards.ts` 의 import 0 은 스타일이 아니라 검증 가능성 요건이 됐다.** jest 철회
후 이 모듈의 유일한 검증 수단은 plain-node 다. `./api` 를 import 하면 firebase 런타임이
딸려 들어와 `node --test` 로 로드조차 못 한다. 그래서 오류 판별을 `instanceof ApiError`
에서 **구조적 `code` 검사**로 바꿨다 (트레이드오프는 아래 편차에 기록).

**rotation pending 타임아웃은 `hidden` 이 아니라 `requestable` 로 복구한다.** 플랜은
타임아웃을 일괄 `hidden` 으로 규정했지만, rotation 에 그대로 적용하면 잡이 유실됐을 때
해당 분석 건에서 회전 영상 기능이 **영구히 사라진다**. `failed`(모더레이션 차단, 재시도해도
대개 다시 막히고 과금만 발생)와 타임아웃(잡 유실)은 원인이 다르므로 분기했다. 서버가
dedupe 하므로 중복 과금 위험은 낮다.

**keypoint 순서 교차 검증을 추가했다.** 사용자/reference 의 `jointKeys` 순서가 다르면
같은 인덱스가 다른 관절을 가리켜 뼈대가 엉뚱하게 이어진다. 순서가 어긋나면 뷰어를
숨긴다 — 31-08 의 `reshapeJoints3d` 가 부분 복구를 거부한 것과 같은 철학이다.

## Deviations from Plan

### 1. [지시 변경] jest-expo 도입 철회 — M-03 컴포넌트 층 미충족

- **사유:** devDependency transitive **1,120개** 유입 대비 파일럿 단계 가치가 낮다는
  belle 판단 (승인 후 철회).
- **결과:** 리뷰 M-03 이 요구한 "typecheck 이상의 검증"은 **컴포넌트 층에서 미충족**
  상태로 남는다. `ReferenceCornerSection.test.tsx` 는 생성하지 않았다.
- **대체:** `visualCards.ts` 순수 로직을 **plain-node(`node --test`, 신규 의존성 0)**
  로 21케이스 고정. 상태 전이표(부재/failed/pending 신선/pending 만료/done),
  타임아웃 경계값, `mapFrameIdx` 비율·clamp·비정상, `pickCompareFrames` refMatched
  게이트, code 분기를 커버한다.
- **미검증으로 남는 것:** 카드 렌더 분기, `onError` → 재서명 콜백 배선, 버튼
  disabled 상태, 문구 부재 검사. → 31-12 HUMAN-UAT 로 넘어간다.
- **커밋:** `2fb00fd`(설치) → `a56cb89`(복원)

### 2. [플랜 명령 정정] 무핀 설치 명령 → SDK 54 호환 핀 세트

설치 단계에서 플랜 원문 명령을 그대로 쓰지 않았다. 상세 근거는 위 Task 1. 철회로 최종
설치물은 없지만, 재도입 시 동일한 핀이 필요하므로 기록한다.

### 3. [Rule 3 - 블로킹] `isDailyLimit`/`isFeatureDisabled` 를 구조적 검사로 변경

- **원안:** `e instanceof ApiError && e.code === '...'`
- **문제:** `instanceof` 를 쓰려면 `visualCards.ts` 가 `api.ts` 를 import 해야 하고,
  그러면 firebase 런타임이 딸려 들어와 plain-node 검증이 **불가능**해진다. jest 철회로
  plain-node 가 유일한 검증 수단이 된 상황에서 이는 블로킹 이슈였다.
- **해결:** `apiErrorCode(e)` 구조적 추출 후 code 비교.
- **트레이드오프(명시):** `{code:'daily_limit'}` 형태의 임의 객체도 통과한다. 실제
  값은 전부 `api.ts` 의 `ApiError` 에서만 오므로 파일럿 범위 위험은 낮으나,
  `instanceof` 대비 약한 보장이다. 테스트 러너 복원 시 되돌릴 것 (코드 주석에도 기록).

### 4. [Rule 3 - 블로킹] 테스트 파일 확장자 `.ts` → `.mjs`

node 로 `.ts` 를 import 하려면 확장자를 명시해야 하는데(`../visualCards.ts`), `tsc` 는
`allowImportingTsExtensions` 없이 이를 **TS5097** 로 거부한다. `tsconfig.json` 은 이
플랜의 소유 범위 밖이라 수정하지 않고, 검증 대상 모듈은 완전히 타입 검사되는 `.ts` 로
두고 **테스트 하네스만** `.mjs` 로 뺐다.

### 5. [Rule 2] rotation 타임아웃 → `requestable`

위 Key Decisions 참조. 플랜의 일괄 `hidden` 규정을 rotation 에 한해 분기했다.

## 후속 정정 필요 (본 플랜 소유 범위 밖)

**`app/src/types/analysis.ts:479` 주석이 구현과 모순된다.** 해당 주석(31-04 작성)은
`refMatched=false` 를 "뷰어가 학생 단독 렌더"로 서술하지만, 31-08 과 본 플랜은 모두
**숨김**으로 확정했다 (한쪽 자세만 그려놓고 "비교"라 부르지 않는다). 구현 정본은
`visualCards.pickCompareFrames` 이며 해당 함수 주석에도 이 불일치를 적어뒀다.
`analysis.ts` 는 소유 파일 목록 밖이라 편집하지 않았다 — **주석 전용 정정 필요**.

## Known Stubs

없음. 다만 위 편차 1 에 따라 컴포넌트 층 자동 검증이 부재하며, 이는 스텁이 아니라
**검증 공백**으로 31-12 HUMAN-UAT 에 넘긴다.

## 보안/의존성 기록

`npm audit` 이 32건(critical 2, high 5)을 보고했으나 전부 **devDependency 계열
transitive**(`firebase-admin` 의 `@grpc/grpc-js`·`protobufjs`, babel/js-yaml 등)로
앱 번들에 포함되지 않는다. 다수가 설치 이전부터 존재한 pre-existing 항목이라
SCOPE BOUNDARY 에 따라 수정하지 않고 기록만 남긴다. jest 철회 후 `npm ci` 로 트리를
복원했으므로 현재 lockfile 은 base 와 동일하다.

## Verification

- `cd app && npm run typecheck` → **exit 0**
- `cd app && node --test src/lib/__tests__/visualCards.test.mjs` → **21/21 pass**
- `npm ci --dry-run` → lockfile 정합 (설치 시점 확인, 이후 base 로 복원)
- `result.tsx` 신규 `setInterval` **0** (유일 매치는 금지를 선언한 주석 문자열)
- Firestore URL/key 필드 소비 **0** (`result.rotationVideoUrl`/`silhouetteImageUrl`/
  `correctedPoseKey`/`rotationVideoKey` 매치 0) — 표시 URL 은 `fetchVisualAssetUrl` 3곳
- 조건부 훅 호출 **0** (`useDiagnosis` 는 boolean 변수, 훅 아님)
- 진행률/ETA 수치 문구 **0** (pending 카피는 31-08 소유, 수치 없음)
- 배치 확인: `ReferenceCornerSection` line 2043 → `참고 지표` line 2064 (보완 운동 아래)
- 31-08 산출물 3종 **무접촉**, `backend/**` 무접촉, `smoke/**` 무접촉,
  `STATE.md`/`ROADMAP.md` 무접촉
- `git status` 에 `node_modules` 없음 — 매 커밋 전 확인 (실디렉터리, gitignore 적용)

## Self-Check: PASSED

- `app/src/lib/visualCards.ts` FOUND
- `app/src/lib/__tests__/visualCards.test.mjs` FOUND
- `app/src/lib/api.ts` FOUND (modified)
- `app/src/app/analysis/result.tsx` FOUND (modified)
- `.planning/phases/31-api-visual-correction/31-CONTEXT.md` FOUND (modified)
- commits `2fb00fd` / `9d2bb92` / `a56cb89` / `f56e560` / `3d3c580` FOUND
- `app/jest.config.js` 부재 확인 (철회 반영)
- `app/src/components/__tests__/ReferenceCornerSection.test.tsx` 부재 확인 (드롭 반영)

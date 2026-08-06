---
phase: quick-260806-sjt
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/src/app/analysis/result.tsx
autonomous: true
requirements: [260806-sjt]

must_haves:
  truths:
    - "비정식 videoKey doc(fixtures/... 등)에서 재발급 요청(POST /playback-url)이 아예 발생하지 않는다"
    - "비정식 videoKey doc 은 doc 에 저장된 myVideoUrl 로 내 영상이 재생된다 (404 URL 이 유효 URL 을 덮어쓰지 않는다)"
    - "정식 업로드 doc(uploads/ 키)은 6일 초과 시 재발급이 그대로 동작한다 — 기존 동작 무변경"
    - "myVideoKey 가 아예 없는 구 doc 은 현행 재발급 경로를 그대로 유지한다"
    - "mode3 지난 영상(prev) 슬롯도 같은 규칙으로 보호된다"
  artifacts:
    - path: "app/src/app/analysis/result.tsx"
      provides: "freshMyUrl / freshPrevUrl 재발급 훅의 videoKey 형상 가드"
      contains: "startsWith('uploads/')"
  key_links:
    - from: "freshMyUrl useEffect (result.tsx ~955)"
      to: "leftUrl={freshMyUrl || result.myVideoUrl} (result.tsx ~2460)"
      via: "가드 성립 시 setFreshMyUrl(null) → 기존 폴백 체인이 doc 저장 URL 선택"
      pattern: "setFreshMyUrl\\(null\\)"
    - from: "freshPrevUrl useEffect (result.tsx ~921)"
      to: "rightUrl={freshPrevUrl || prevDoc?.result?.myVideoUrl} (result.tsx ~2470)"
      via: "가드 성립 시 setFreshPrevUrl(null) → prev doc 저장 URL 선택"
      pattern: "setFreshPrevUrl\\(null\\)"
---

<objective>
결과 화면에서 내 영상(좌측 슬롯)이 재생되지 않는 회귀를 수리한다.

presigned URL 7일 만료 대비 재발급 훅(`freshMyUrl` / `freshPrevUrl`)이, 실제 영상이 canonical
업로드 키에 없는 doc 에서도 재발급을 강행해 **존재하지 않는 객체를 서명한 URL(GET 404)로 doc 의
유효 URL을 덮어쓴다.** 두 훅에 videoKey 형상 가드를 넣어, 비정식 키 doc 은 재발급을 생략하고
doc 저장 URL을 그대로 쓰게 한다.

Purpose: belle 실기기에서 내 영상 duration 0:00 로 재현된 결함 해소. 파일럿 시연 경로 복구.
Output: `app/src/app/analysis/result.tsx` 두 useEffect 에 가드 추가. 커밋 1개(fix).
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@app/CLAUDE.md
@app/src/app/analysis/result.tsx

수리 대상 좌표 (실측, 2026-08-06 HEAD 56823215):
- `freshPrevUrl` 훅 = `result.tsx` 921~946 (WR-02). effect 본문 첫 줄이 `if (!prevDoc) return;`.
- `freshMyUrl` 훅 = `result.tsx` 955~974 (WR-03). effect 본문 첫 줄이 `const SAFE_TTL_MS = ...`.
- 소비처 3곳 = 2460 `leftUrl={freshMyUrl || result.myVideoUrl || undefined}`,
  2470 `freshPrevUrl || prevDoc?.result?.myVideoUrl || undefined`,
  3235 `url: freshMyUrl || result.myVideoUrl || undefined`.
  **세 곳 모두 이미 `|| 저장 URL` 폴백 체인이므로 소비처는 손대지 않는다** — 훅이 null 을
  내면 폴백이 자동으로 doc 저장 URL을 고른다.
- canonical 업로드 키 형상 = `backend/shared/python/sunity_shared/s3keys.py:18`
  `^uploads/(?P<uid>[^/]+)/(?P<analysis_id>[A-Za-z0-9]+)\.(?P<ext>mp4|mov)$`
- 같은 판단의 백엔드 선례 = `backend/functions/visual-worker/app.py:565` `_create_rotation`
  ("myVideoKey 를 canonical upload key 후보와 대조한 뒤에만 presign", H-05).
</context>

<diagnosis_given>
아래 5항은 오케스트레이터가 이미 실측 완료했다. **재조사 금지 — 전제로 쓴다.**

1. `result.tsx` 에 presigned 7일 만료 대비 재발급 훅이 2개 있다 (`freshMyUrl` WR-03, `freshPrevUrl` WR-02).
   각각 `createdAt` 이 6일 넘으면 `requestPlaybackUrl(analysisId, ext)` 를 호출한다.
2. 백엔드 `POST /playback-url` 기본 분기는 canonical 키 `uploads/{uid}/{analysisId}.{ext}` 를
   **객체 존재 확인 없이** 서명해 200 을 반환한다.
3. 파일럿 fixture doc 4건은 실제 영상이 `fixtures/phase15/...` 키에 있어 canonical 키 객체가 없다
   → 재발급 URL GET = **404** (실측). doc 저장 `myVideoUrl` GET = **206** (실측).
4. 앱이 `freshMyUrl || result.myVideoUrl` 로 재발급 URL 을 우선하므로 깨진 URL 이 유효 URL 을
   덮어쓴다 → belle 실기기 재현, duration 0:00.
5. `result.myVideoKey` 는 백엔드가 항상 기록하는 실측 키다 (WR-02 가 이미 ext 파생에 사용 중 —
   같은 필드로 형상 판정이 가능하다).
</diagnosis_given>

<tasks>

<task type="auto">
  <name>Task 1: 두 재발급 훅에 videoKey 형상 가드 추가</name>
  <files>app/src/app/analysis/result.tsx</files>
  <action>
`freshMyUrl` 훅(~955)과 `freshPrevUrl` 훅(~921) **두 곳에만** 가드를 추가한다.

가드 규칙 (양쪽 동일):
- 해당 doc 의 videoKey 를 읽는다. `freshMyUrl` 은 `result.myVideoKey`, `freshPrevUrl` 은
  `prevDoc.result?.myVideoKey`.
- 키가 **존재하고** `'uploads/'` prefix 로 시작하지 **않으면** → `setFreshMyUrl(null)` /
  `setFreshPrevUrl(null)` 을 호출하고 즉시 `return` 한다. 처리는 기존 "만료 X" 분기와 동일
  (state 를 비워 소비처 폴백 체인이 doc 저장 URL 을 고르게 한다).
- 키가 `'uploads/'` 로 시작하면 → 아무것도 하지 않고 기존 코드 경로 그대로 진행 (재발급 유지).
- 키가 **undefined/빈 문자열**이면 → 아무것도 하지 않고 기존 재발급 유지. 구버전 doc 은
  canonical 키가 맞을 가능성이 높은 실사용자 doc 이라 여기서 막으면 회귀가 된다.
  따라서 조건은 반드시 `key && !key.startsWith('uploads/')` 형태의 **양항 조건**이어야 한다
  (`!key?.startsWith(...)` 같은 단항 형태는 undefined 를 잡아버리므로 금지).

배치:
- `freshMyUrl`: effect 본문 **맨 앞**, `SAFE_TTL_MS` 계산 이전.
- `freshPrevUrl`: 기존 `if (!prevDoc) return;` **바로 다음**, `SAFE_TTL_MS` 계산 이전.
  (`!prevDoc` early return 은 현행 그대로 — state 를 건드리지 않는 기존 동작 유지.)
- 이유: doc 형상 전제 조건이지 신선도 판단이 아니다. TTL 계산보다 앞이 읽기도 싸고 의도도 명확하다.

주석 (각 가드 위 1~3줄, 프로젝트 관용 = 왜-주석 + 출처 인용). 예시 문안:
  `260806-sjt — 비정식 videoKey(fixtures/... 등) doc 은 canonical 재발급 키`
  `uploads/{uid}/{analysisId}.{ext} 에 객체가 없다. 백엔드는 존재 확인 없이 서명해 200 을`
  `주므로(GET 404) 재발급 URL 이 doc 의 유효 URL 을 덮어썼다. 키 부재 구 doc 은 현행 유지.`
  두 번째 가드는 첫 가드를 가리키는 짧은 1~2줄로 충분하다 (동일 문단 복붙 금지).
  이모지 금지, 과잉 주석 금지.

건드리지 말 것 (범위 봉인):
- `freshRefUrl` 훅(~985)은 **대상 아님.** `requestReferencePlaybackUrl(referenceMotionId)` 는
  reference doc 의 실제 키를 서버가 해석하는 별개 경로라 canonical uploads/ 전제가 없다.
  일반화해서 같이 고치지 말 것 ([[dont-over-generalize-into-breaking-approved-items]]).
- 소비처 3곳(2460 / 2470 / 3235) 무변경. 폴백 체인이 이미 있어 훅 반환값만 바꾸면 된다.
- 두 effect 의 deps 배열 무변경. `freshMyUrl` deps 는 이미 `result.myVideoKey`,
  `freshPrevUrl` deps 는 이미 `prevDoc?.result?.myVideoKey` 를 포함한다 — **읽어서 확인만 하고
  손대지 않는다.** 확인 결과(포함/미포함)를 SUMMARY 에 한 줄로 적는다.
- `requestPlaybackUrl`, `app/src/lib/api.ts`, 백엔드, 타입 계약(`types/analysis.ts`) 전부 무접촉.
  백엔드 존재 확인 추가는 이번 스코프가 아니다.
  </action>
  <verify>
    <automated>npm --prefix /Users/kimtaesung/Dev/SunityMotion/app run typecheck</automated>
    <automated>git -C /Users/kimtaesung/Dev/SunityMotion diff --stat -- app backend</automated>
    <automated>git -C /Users/kimtaesung/Dev/SunityMotion diff -U0 -- app/src/app/analysis/result.tsx | grep -c "^@@"</automated>
  </verify>
  <done>
- `npm run typecheck` 통과 (이 프로젝트의 유일한 정적 게이트).
- `git diff --stat` 이 `app/src/app/analysis/result.tsx` **1파일만** 보고한다.
- `git diff -U0` hunk 가 **2개**이고, 두 hunk 헤더 행번호가 모두 900~990 범위 안이다
  (= 두 훅 내부에만 변경. 소비처·freshRefUrl 무변경의 기계적 증명).
- 코드 판독으로 확인: `uploads/` 키 doc 과 키 부재 doc 은 가드 조건이 false 라 기존 실행
  경로가 byte-동일하다.
  </done>
</task>

<task type="auto">
  <name>Task 2: 커밋 + 검증 한계 박제</name>
  <files>app/src/app/analysis/result.tsx</files>
  <action>
Task 1 의 diff 게이트를 **`git add` 이전에** 모두 실행한 뒤 커밋한다
(`git add` 는 `git diff` 계열을 무력화한다 — 순서 역전 금지).

커밋 1개, 이모지 금지. 메시지 예:
  `fix(quick-260806-sjt): 비정식 videoKey doc 에서 presigned 재발급 생략`
  본문 2~4줄에 근본원인 1줄(백엔드가 객체 존재 확인 없이 canonical 키를 서명 → 404 URL 이
  유효 URL 을 덮어씀) + 범위 1줄(정식 uploads/ 키·키 부재 doc 무변경).

EAS OTA 발행은 **하지 않는다** — 오케스트레이터가 머지 후 직접 수행한다.

SUMMARY 에 검증 한계를 [[state-evidence-act-or-mark-unverified]] 형식으로 정직하게 적는다.
쟀다/봤다/해봤다를 구분해 쓰고, 안 한 것은 안 했다고 적는다:
- **한 것**: typecheck 돌렸다 / diff hunk 범위 세어봤다 / 코드 판독으로 정식 경로 무변경 논증했다.
- **안 한 것 (이유 포함)**: 시뮬레이터 렌더 확인 **불가 — 개발 빌드 부재**. 따라서
  "fixture doc 에서 내 영상이 실제로 재생된다"는 **미검증**이다. 앱 JS 테스트 러너가 없어
  (`app/package.json` 에 test 스크립트 0) 가드 분기의 런타임 실행도 자동 검증되지 않았다.
  실동작 확인은 OTA 발행 후 belle 실기기 리포트가 유일한 증거 경로다.
- SUMMARY 에 belle 확인 체크리스트 3줄: (a) fixture doc 결과 화면에서 내 영상이 재생되고
  duration 이 0:00 이 아닌지, (b) mode3 지난 영상 슬롯도 뜨는지, (c) 최근 정식 업로드 분석에서
  내 영상이 여전히 정상인지(회귀 확인).
  </action>
  <verify>
    <automated>git -C /Users/kimtaesung/Dev/SunityMotion show --stat --oneline HEAD | tail -5</automated>
  </verify>
  <done>
- 커밋 1개가 `app/src/app/analysis/result.tsx` 단일 파일만 담고 있다.
- 커밋 메시지에 이모지 0.
- SUMMARY 에 "시뮬 렌더 미검증(개발 빌드 부재)" 과 belle 확인 체크리스트가 기록됐다.
- OTA 발행 흔적 없음(오케스트레이터 소관).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| 앱 → `POST /playback-url` | 클라이언트가 재발급을 요청하는 지점. 서명 대상 키는 **서버가** 호출자 uid + analysisId 로 만든다 (클라이언트 키 주입 없음). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-260806-01 | Information Disclosure | `POST /playback-url` canonical 서명 | accept | 이번 변경은 **요청을 생략만** 한다. 서명 권한·키 파생 로직 무접촉이라 노출면이 늘지 않는다(순감소). 백엔드의 "존재 확인 없이 서명" 자체는 별건(권한 문제 아님 — 호출자 자기 uid 경로만 서명). |
| T-260806-02 | Tampering | `result.myVideoKey` (Firestore doc 필드) | accept | 이 필드는 백엔드 pipeline 이 쓰고 클라이언트는 읽기 전용(Firestore rules). 가드는 이 값으로 **네트워크 요청을 줄이는 판단만** 하고, 이 값을 서명 키로 백엔드에 보내지 않는다. 조작돼도 최악은 "재발급 생략" → 만료 URL 표시(가용성 저하)이지 타인 객체 접근이 아니다. 남의 객체를 서명 대상으로 삼는 경로는 백엔드 `visual-worker` H-05 candidate 대조가 이미 봉인. |
| T-260806-SC | Tampering | npm/pip 설치 | n/a | **패키지 설치 0** — 신규 의존성 없음, `app/package.json` / lockfile 무접촉. 공급망 표면 변화 없음. |
</threat_model>

<verification>
1. `npm --prefix app run typecheck` — 통과. (이 프로젝트의 **유일한** 정적 게이트)
   기준선 = HEAD 56823215 에서 **이미 GREEN** (2026-08-06 계획 시점 실행 확인).
   즉 새 오류가 1건이라도 뜨면 이번 변경이 원인이다 — pre-existing 으로 처분 금지.
2. `git diff --stat` (커밋 전) — 변경 파일 1개(`app/src/app/analysis/result.tsx`)뿐.
3. `git diff -U0 app/src/app/analysis/result.tsx` — hunk 2개, 둘 다 900~990 행 범위.
   소비처(2460/2470/3235)·`freshRefUrl`(985~1004) 무변경의 기계적 증명.
4. 코드 판독 논증 — 가드 조건이 `key && !key.startsWith('uploads/')` 양항이므로
   (a) `uploads/` 키, (b) 키 부재 두 경우 모두 조건 false → 기존 경로 byte-동일.

**검증 불가 항목 (계획 시점에 이미 확정된 제약, 실행자가 우회 시도 금지):**
- 시뮬레이터 렌더 확인 = **불가**. 개발 빌드가 없다. 실제 재생 여부는 이 계획으로 증명되지 않는다.
- 앱 JS 테스트 러너 부재(`app/package.json` test 스크립트 0) + 가드가 컴포넌트 effect 내부라
  순수 함수 추출 없이는 단위 검증 불가. **파일 1개 제약을 지키기 위해 추출하지 않는다.**
- 따라서 "fixture doc 에서 영상이 실제로 뜬다"는 belle 실기기 확인까지 **UNVERIFIED** 로 남는다.
  SUMMARY 에 그렇게 적을 것 — 통과했다고 쓰지 말 것.
</verification>

<success_criteria>
- 두 재발급 훅(`freshMyUrl`, `freshPrevUrl`)에 videoKey 형상 가드가 들어갔다.
- 가드 조건이 양항(`key && !key.startsWith('uploads/')`)이라 키 부재 구 doc 은 현행 재발급 유지.
- `freshRefUrl` 훅·소비처 3곳·deps 배열·api.ts·백엔드·타입 계약 전부 무변경.
- `npm run typecheck` 통과, 변경 파일 1개, hunk 2개.
- 커밋 1개(fix), 이모지 0, OTA 미발행.
- SUMMARY 에 검증한 것/못 한 것이 이유와 함께 구분 기록됐다.
</success_criteria>

<output>
Create `.planning/quick/260806-sjt-videokey-doc-presigned-url/260806-sjt-SUMMARY.md` when done
</output>

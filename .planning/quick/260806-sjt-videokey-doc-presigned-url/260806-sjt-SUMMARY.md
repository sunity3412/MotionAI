---
phase: quick-260806-sjt
plan: 01
subsystem: app
tags: [result-screen, presigned-url, playback, regression-fix]
requires:
  - "result.myVideoKey (백엔드 pipeline complete_analysis 가 항상 기록)"
provides:
  - "freshMyUrl / freshPrevUrl 재발급 훅의 videoKey 형상 가드"
affects:
  - "app/src/app/analysis/result.tsx (결과 화면 좌측 내 영상 슬롯 · mode3 지난 영상 슬롯)"
tech-stack:
  added: []
  patterns:
    - "fail-safe 가드: 양항 조건으로 미지(undefined) 케이스는 현행 유지"
key-files:
  created: []
  modified:
    - app/src/app/analysis/result.tsx
decisions:
  - "가드 조건은 양항(key && !key.startsWith('uploads/')) — 단항(!key?.startsWith)은 키 부재 구 doc 을 잡아 회귀가 되므로 금지"
  - "백엔드 객체 존재 확인 추가는 이번 스코프 아님 — 앱측 요청 생략만"
metrics:
  duration: "약 12분"
  completed: 2026-08-06
---

# Quick 260806-sjt: 비정식 videoKey doc presigned 재발급 가드 Summary

결과 화면에서 재발급 URL(GET 404)이 doc 의 유효한 `myVideoUrl` 을 덮어쓰던 회귀를, 두 재발급 훅에 videoKey 형상 가드를 넣어 차단했다.

## 무엇을 했나

`app/src/app/analysis/result.tsx` 의 재발급 훅 2개에 가드를 추가했다. 순수 추가 17줄, 삭제 0줄.

| 훅 | 위치(변경 후) | 가드 |
|---|---|---|
| `freshPrevUrl` | `if (!prevDoc) return;` 직후 (923~929) | `prevVideoKey && !prevVideoKey.startsWith('uploads/')` → `setFreshPrevUrl(null)` + `return` |
| `freshMyUrl` | effect 본문 맨 앞, `SAFE_TTL_MS` 이전 (963~972) | `myVideoKey && !myVideoKey.startsWith('uploads/')` → `setFreshMyUrl(null)` + `return` |

가드가 성립하면 state 를 비우고 즉시 빠진다. 소비처 3곳이 이미 `freshXUrl || doc저장URL` 폴백 체인이라, 훅이 null 을 내면 doc 에 저장된 URL 이 자동으로 선택된다 — 소비처는 손대지 않았다.

**근본원인**: 백엔드 `POST /playback-url` 기본 분기가 canonical 키 `uploads/{uid}/{analysisId}.{ext}` (`s3keys.py:18`) 를 **객체 존재 확인 없이** 서명해 200 을 반환한다. 실제 영상이 `fixtures/phase15/...` 에 있는 파일럿 doc 에서는 그 URL 이 GET 404 인데, 앱이 `freshMyUrl || result.myVideoUrl` 로 재발급본을 우선해 유효 URL 을 덮어썼다.

## 계획 대비 이탈

없음 — 계획대로 실행했다. 다만 실행 환경에서 1건 처리:

**[Rule 3 - 블로킹] worktree 에 `app/node_modules` 부재로 `tsc: command not found`**
- 발생: Task 1 verify (`npm run typecheck`)
- 조치: 메인 저장소의 `app/node_modules` 를 worktree 로 심볼릭 링크 → typecheck 실행 → 검증 후 링크 제거.
- 패키지 설치 0건. `package.json` / lockfile 무접촉. 커밋에 흔적 없음(`app/node_modules` 는 `.git/info/exclude:18` 로 무시됨, 커밋 후 `git status --short` 공백 확인).

## 검증 — 잰 것 / 안 잰 것

[[state-evidence-act-or-mark-unverified]] 형식. 동사는 실제로 한 행위다.

### 한 것 (증거 있음)

| 항목 | 무엇을 했나 | 결과 |
|---|---|---|
| 정적 게이트 | `npm --prefix app run typecheck` **돌렸다** | GREEN (출력 0, exit 0). 이 프로젝트의 유일한 정적 게이트 |
| 변경 범위 | `git diff --stat -- app backend` **찍어봤다** | `app/src/app/analysis/result.tsx` **1파일**, 17 insertions / 0 deletions |
| hunk 위치 | `git diff -U0 \| grep "^@@"` **세어봤다** | hunk **2개** — `@@ -922,0 +923,7 @@`, `@@ -955,0 +963,10 @@`. 둘 다 900~990 범위 = 두 훅 내부에만 변경 |
| 소비처 무변경 | 위 hunk 2개가 전부인 것으로 **기계적으로 증명됨** + `grep` 으로 폴백 체인 3곳 **직접 확인** | 2477 `leftUrl={freshMyUrl \|\| result.myVideoUrl \|\| undefined}` / 2487 `freshPrevUrl \|\| prevDoc?.result?.myVideoUrl` / 3252 `url: freshMyUrl \|\| result.myVideoUrl` — 전부 원문 유지(행번호만 +17 이동) |
| `freshRefUrl` 무변경 | 같은 hunk 증명 + `grep` 으로 훅 선언 위치(1001) **확인** | 손대지 않음. 범위 봉인 지켜짐 |
| deps 배열 | **읽어서 확인만 했다 (손대지 않음)** | `freshMyUrl` deps = `[analysisId, createdAt, result.myVideoKey]` — `result.myVideoKey` **포함됨**. `freshPrevUrl` deps = `[prevDoc?.analysisId, prevDoc?.createdAt, prevDoc?.result?.myVideoKey]` — **포함됨**. 즉 가드가 읽는 값이 모두 deps 에 있어 추가 변경 불필요 |
| 정식 경로 무변경 | 코드 **판독으로 논증했다** | 조건이 양항이라 (a) `uploads/` 키 → `!startsWith` false, (b) 키 undefined/`''` → 첫 항 falsy. 두 경우 모두 가드 false → 기존 실행 경로 byte-동일 |
| 커밋 위생 | `git show --stat` **확인**, 삭제 파일 `git diff --diff-filter=D` **확인** | 커밋 1개 단일 파일, 삭제 0, 이모지 0 |

### 안 한 것 (UNVERIFIED — 이유 포함)

- **시뮬레이터 렌더 확인 = 하지 않았다. 불가 — 개발 빌드가 없다.** 따라서 **"fixture doc 에서 내 영상이 실제로 재생된다"는 미검증이다.** 이 커밋은 "재발급 요청이 발생하지 않는다"를 코드로 보장할 뿐, 화면에 영상이 뜨는 것을 증명하지 않는다.
- **가드 분기의 런타임 실행도 자동 검증되지 않았다.** 앱에 JS 테스트 러너가 없다(`app/package.json` test 스크립트 0). 가드가 컴포넌트 effect 내부라 순수 함수 추출 없이는 단위 검증 불가이고, "파일 1개" 제약을 지키기 위해 추출하지 않았다(계획이 명시한 제약).
- **belle 실기기 확인 전까지 실동작 증거는 0이다.** OTA 발행 후 belle 리포트가 유일한 증거 경로다.
- **OTA 발행은 하지 않았다** — 오케스트레이터 소관(계획 지시).

## belle 확인 체크리스트 (OTA 발행 후)

1. **fixture doc 결과 화면에서 내 영상(좌측)이 재생되고 duration 이 0:00 이 아닌지** — 이번 수리의 직접 대상.
2. **mode3 "지난 영상"(우측) 슬롯도 뜨는지** — 같은 가드를 prev 훅에도 넣었으므로 함께 확인.
3. **최근 정식 업로드 분석에서 내 영상이 여전히 정상인지 (회귀 확인)** — `uploads/` 키 doc 은 재발급 경로가 그대로여야 한다. 여기서 깨지면 가드 조건이 잘못 걸린 것.

## 알려진 한계 / 남은 것

- **백엔드는 여전히 객체 존재 확인 없이 서명한다.** 이번 변경은 앱이 그 경로를 안 부르게 했을 뿐 뿌리를 막지 않았다. 별건(계획이 스코프 밖으로 명시).
- `myVideoKey` 가 없는 구 doc 은 현행 재발급 경로 유지 — canonical 키가 맞다는 **가정**에 의존한다. 이 가정이 틀린 구 doc 이 있다면 같은 증상이 남는다(실측하지 않았다).

## Self-Check: PASSED

- `app/src/app/analysis/result.tsx` — 존재 확인
- `.planning/quick/260806-sjt-videokey-doc-presigned-url/260806-sjt-SUMMARY.md` — 존재 확인
- 커밋 `4b755efa` — `git show --stat` 으로 존재·내용 확인

---

## 오케스트레이터 부록 (실행자 종료 후)

- 머지 = fast-forward → 본 repo 해시도 `4b755efa` 그대로 (실행자 우려 해소, `git log` 대조).
- **OTA 발행됨** (2026-08-06, runtime 1.1.0): production `2904b667-698c-49d0-ae3f-fc5c4ffeff01` /
  preview `0f294446-ca7d-46e1-8927-d33f88dfb4af` / development `1de9e449-cc2f-4729-89f4-93eda6248825`.
  롤백 그룹 = `.planning/CONTINUE-2026-08-01.md` 08-06 절 참조.
- 위 "안 한 것" 표의 "OTA 미발행" 행은 실행자 시점 기준 — 발행 후에도 런타임 재생
  UNVERIFIED 는 그대로다 (belle 실기기 확인이 유일한 증거 경로).

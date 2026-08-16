---
phase: quick-260816-ill2
plan: 01
subsystem: illustration-generation
tags: [gemini-3-pro-image, gemini-3.5-flash, prompt-wiring, gate-defect, crop-aware-judging, json-parsing]

# Dependency graph
requires: []
provides:
  - "generate.py::build_prompt() 가 cropBox/cropNote/orientation 을 FRAMING/POSE FIDELITY 문단에 반영 — 부분 클로즈업·방위 지시와 고정 'FILL the frame' 문구의 모순을 해소"
  - "targets.json 반려 10장의 inputFrame 재확보(소스 영상에서 t/cropBox 그대로 재추출) + sourceVideo/t 백필 + cropNote 2건/orientation 1건 신설"
  - "regenerate_gated.py — 게이트 내장 재생성 드라이버(재시도 상한 3) + --rejudge 재판정 모드(이미지 생성 0)"
  - "9항목 게이트 자체의 결함 2건 발견·수리(크롭맹 n/a 분리, 응답잘림 gate_error 분리) — quick-260816-e26 과 같은 계열의 계측 결함"
  - "board.html + /Users/Shared 한글 재료 + 판정요청.md — belle 판정용 이전/이후 대조 + 게이트 판정 원문"
affects: ["다음 사이클: belle 판정 승인분의 app/assets/illustrations/ 반영 + VERIFIED_ILLUSTRATIONS/ILLUSTRATION_SCENES 배선"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "FRAMING_FULL/FRAMING_PARTIAL 이원화 — cropBox/cropNote 유무(데이터)로만 분기, 동작명 조건 분기 0"
    - "게이트 응답 파싱은 그리디 정규식 대신 json.JSONDecoder.raw_decode — 트레일링/잘린 응답에 안전(schema.py::extract_report_json 관례와 같은 원리, 독립 적용)"
    - "게이트 overall 은 모델 자기신고를 신뢰하지 않고 items 에서 결정론적으로 재계산 — n/a 항목은 집계에서 제외"
    - "재판정(--rejudge)은 크롭 신호 + still_failing 자산만 대상 — 무관 자산 재호출 생략으로 예산 절약"

key-files:
  created:
    - .planning/quick/260816-ill2-illustration-framing-wiring/extract_inputs.py
    - .planning/quick/260816-ill2-illustration-framing-wiring/regenerate_gated.py
    - .planning/quick/260816-ill2-illustration-framing-wiring/regen_verdicts.json
    - .planning/quick/260816-ill2-illustration-framing-wiring/board.html
    - .planning/quick/260816-ill2-illustration-framing-wiring/.gitignore
  modified:
    - .planning/quick/260809-ill-missing-illustrations/generate.py
    - .planning/quick/260809-ill-missing-illustrations/targets.json

key-decisions:
  - "Task1 검증 스크립트의 신규-import 정규식이 SCENE 잠금 문단('from any edge.')에서 위양성('any')을 내는 것을 git show HEAD 로 편집 전부터 존재함을 확인 — baseline diff 로 동등 불변식(신규 import 0)을 재검증하고 통과"
  - "반려 10장의 재추출 원본 프레임(실사 인물 사진)은 /Users/Shared/sunity-motion-260816-ill2-cache/ 에 저장(레포 밖, 스크래치패드 아님) — PII 컨벤션(home-dir-is-git-repo-pii-hazard)과 이번 verification_notes의 '레포 또는 /Users/Shared' 요구를 동시 충족"
  - "생성 라운드 완주 후 발견한 게이트 결함 2건(크롭맹·응답잘림 오집계)을 coordinator 지시로 수리 — CROP_AWARE_ADDENDUM(데이터 기반 n/a) + raw_decode 파싱 + gate_error/fail 분리. 9개 항목 원문은 한 글자도 안 바꿈"
  - "재판정은 --rejudge 모드로 기존 이미지 재사용(이미지 생성 호출 0), 크롭 신호 없는 자산(kip-up 계열)은 고친 게이트와 결과가 같을 수밖에 없어 재판정 대상에서 제외"

patterns-established:
  - "부분 크롭 프롬프트 안내문은 cropBox/cropNote 데이터 신호로만 첨부 — 이미지를 보고 크롭 여부를 추측하지 않는다"

requirements-completed: [QUICK-260816-ILL2]

# Metrics
duration: 55min
completed: 2026-08-16
---

# Quick 260816-ill2: 일러스트 크롭·방위 배선 수리 + 재판정 Summary

**generate.py 의 FRAMING/POSE FIDELITY 문단에 cropBox/cropNote/orientation 배선을 추가하고, 반려 10장을 소스 영상에서 재확보해 같은 9항목 게이트로 재생성한 결과 5장 통과(19장 전체 14/19) — 재생성 완주 직후 게이트 자체의 크롭맹·응답잘림 결함을 발견해 수리, 3/10 → 5/10 으로 재검증**

## Performance

- **Duration:** 약 55분 (Task1 커밋 20:49 ~ Task4 커밋 21:39)
- **Started:** 2026-08-16T11:49:40Z (Task1 커밋 기준)
- **Completed:** 2026-08-16T12:39:31Z (Task4 커밋 기준)
- **Tasks:** 4/4
- **Files modified:** 7 (레포 기준 — generate.py·targets.json 수정 2, extract_inputs.py·regenerate_gated.py·regen_verdicts.json·board.html·.gitignore 신설 5) + gen/ 하위 신규 이미지 28장

## Accomplishments

- `build_prompt()` 가 cropBox/cropNote 유무로 FRAMING 문구를(무신호=원문 바이트 동일), orientation 접두(도립/직립)로 POSE FIDELITY 단언 문장을 독립적으로 삽입 — API 호출 0인 순수함수 검증으로 증명(9개 assert 전부 통과)
- 반려 10장 전부 소실된 입력 프레임을 소스 영상에서 근거 있게(sourceVideo/t/cropBox, 지어낸 값 0) 재확보 — 1차 후보 3장(pdshape_full/peterpan_full/elbowtwist_shoulder_full)은 Read 로 육안 확인 후 확정
- 반려 10장을 새 배선으로 재생성(재시도 상한 3) → 최초 라운드에서 3장 통과로 오집계됐던 것을 게이트 자체의 결함 2건(크롭맹·응답잘림) 수리 후 재판정해 **5장 통과**로 확정(19장 전체 14/19)
- 게이트 결함 수리: (1) cropBox/cropNote 로 의도적으로 프레임 밖에 둔 신체 부위를 요구하는 항목(①④⑤⑥⑧)이 "안 보이니 fail" 로 오판정되던 크롭맹을 데이터 기반 n/a 분리로 해소, (2) 판정 응답 잘림(JSONDecodeError)이 자산 실패로 오집계되던 것을 `json.JSONDecoder.raw_decode` + `gate_error` 상태 분리로 해소
- 통과 9장(app/assets/illustrations) sha256 9/9 무변경, pytest 4398 passed/59 failed/26 skipped(기준선 정확히 일치), 금지 디렉터리(backend/shared·backend/functions·app/src·app/assets/illustrations) git status 전부 clean

## Task Commits

Each task was committed atomically:

1. **Task 1: FRAMING/POSE FIDELITY 배선 수리** - `a15506e` (feat)
2. **Task 2: 반려 10장 입력 프레임 재확보 + targets.json 보강** - `68c3712` (feat)
3. **Task 3: 게이트 내장 재생성 드라이버 + 반려 10장 실행 및 게이트 결함 수리** - `2525623` (feat)
4. **Task 4: belle 판정 재료 board.html** - `8c96445` (docs)

_계획 문서(PLAN.md)·STATE.md·SUMMARY.md 는 사용자 지시에 따라 이 실행자가 커밋하지 않음 — 문서 커밋은 별도 처리._

## Files Created/Modified

- `.planning/quick/260809-ill-missing-illustrations/generate.py` - FRAMING_FULL/FRAMING_PARTIAL/ORIENTATION_SENTENCE 상수 + `_orientation_hint()`/`_framing_block()` 헬퍼, `build_prompt()` 2개 인자 추가
- `.planning/quick/260809-ill-missing-illustrations/targets.json` - 반려 10장 inputFrame 재확보 경로 + sourceVideo/t 백필 + cropNote 2건 + orientation 1건 + note10
- `.planning/quick/260816-ill2-illustration-framing-wiring/extract_inputs.py` - S3 read-only 다운로드(discover_sweep.py 재사용) + 원본 해상도 프레임 추출 + 창 재추출 옵션
- `.planning/quick/260816-ill2-illustration-framing-wiring/regenerate_gated.py` - 게이트 내장 재생성 드라이버 + 게이트 결함 수리(CROP_AWARE_ADDENDUM·raw_decode 파싱·gate_error 분리) + `--rejudge` 모드
- `.planning/quick/260816-ill2-illustration-framing-wiring/regen_verdicts.json` - 10 자산 × attempt 별 원 게이트 응답(수리 전/후 모두 gatePreFix 로 보존)
- `.planning/quick/260816-ill2-illustration-framing-wiring/board.html` - 10 자산 이전/이후 base64 embed + 게이트 판정 원문(게이트 수리 반영 최종본)
- `.planning/quick/260816-ill2-illustration-framing-wiring/.gitignore` - `.cache/`(입력 프레임 기본 캐시, PII) + `__pycache__/` 제외
- `/Users/Shared/sunity-illustration-260816-ill2/` - belle 열람용 한글 파일명 이전/이후 자료 + 판정요청.md (레포 밖, 미커밋)
- `.planning/quick/260809-ill-missing-illustrations/gen/*.jpg` - 재생성 시도 이미지 28장(try901~903)

## Decisions Made

- **Task1 검증 스크립트 위양성 처리**: 계획 원문의 신규-패키지 정규식이 SCENE 잠금 문단("from any edge.")에서 `any` 를 패키지로 오탐지 — git show HEAD 로 이 텍스트가 이번 편집 이전부터 존재함을 확인하고, baseline diff(편집 전/후 import 루트 집합 완전 동일) 로 "신규 패키지 0" 불변식을 등가 재검증. 계획 스크립트 자체를 수정하지 않고 그 의도(신규 import 0)를 더 정확히 검증하는 보강 체크를 추가 실행.
- **PII 저장 위치**: 반려 10장의 재추출 원본(실사 인물 사진, 익명화 전)은 `/Users/Shared/sunity-motion-260816-ill2-cache/` 에 저장 — 레포 안 스크립트-상대 `.cache/` 는 기본값으로만 남기고(제네릭 도구 관례, `.gitignore` 처리) 실제 사용은 레포 밖 경로로 명시 지정. targets.json 의 `inputFrame` 도 이 경로를 가리키도록 갱신.
- **게이트 결함 수리 범위**: coordinator 가 지적한 ④·⑥ 뿐 아니라 실측 데이터(`ref-peter-pan--leg try902`: 머리 크롭으로 ①⑤⑧ 도 동일하게 오판정)를 근거로 크롭맹 수리를 9개 항목 전체에 일반화 — 특정 항목 하드코딩 대신 "그 항목이 묻는 신체 부위가 의도된 크롭으로 프레임 밖이면 n/a" 원칙을 프롬프트에 명시. item2(포즈/구도 충실도)는 수리 대상에서 제외 — 구도 자체가 지켜졌는지는 여전히 실제 결함 판정 대상.
- **재판정 대상 축소**: 크롭 신호(cropBox/cropNote) 없는 자산(kip-up--leg/shoulder, 순수 그립 문제)은 고친 게이트와 원본 게이트가 동일하게 동작하므로 재판정 API 호출을 생략 — 예산 절약 + 정직한 스코프.
- **pdshape--leg 경계선 케이스 처리**: 동일 이미지(try901)를 두 차례 재판정한 결과 1회는 완전한 pass, 1회는 응답 잘림(gate_error, 단 보이는 부분 응답은 item1·item2 모두 pass 로 앞선 결과와 모순되지 않음)이 나왔다. 유리한 쪽을 임의로 택하지 않고, 내 알고리즘이 실제로 마지막에 산출한 값(still_failing)을 그대로 최종 기록으로 채택 — 대신 이 경계선 성격을 SUMMARY 와 board.html 에 정직하게 남긴다(억지 통과 금지).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking, 검증 스크립트 결함] Task1 신규-패키지 정규식 위양성 우회**
- **Found during:** Task 1 검증
- **Issue:** 계획의 `<automated>` 검증 스크립트가 `r'^(?:import|from)\s+([A-Za-z_]...)'` 로 소스 전체(트리플쿼트 문자열 내부 포함)를 스캔해, SCENE 문단의 "from any edge." 를 `import any` 로 오탐지해 매번 `AssertionError` 로 실패한다. `git show HEAD:generate.py` 로 이 텍스트가 이번 편집 이전부터 있었음을 확인(위양성이 내 변경과 무관).
- **Fix:** 계획의 나머지 assert 는 전부 원문 그대로 실행해 통과 확인 후, 신규-패키지 검증만 baseline diff(편집 전/후 import 루트 집합 완전 일치, `{'any'} = 예상된 유일한 초과분`) 방식으로 대체 실행 — 동일한 "신규 import 0" 불변식을 더 정확하게 증명.
- **Files modified:** 없음(검증 방법만 보강, 소스 무변경)
- **Verification:** `new_roots == old_roots` 확인, 실행 로그에 "TASK1 WIRING GATE PASS" + "FORBIDDEN DIR CLEAN" 출력
- **Committed in:** `a15506e` (Task 1 커밋 — 검증은 커밋 전 실행, 소스 diff 자체는 계획 그대로)

**2. [Rule 1 - Bug, 계획 코드 스니펫 오류] extract_inputs.py sys.path 계산 수정**
- **Found during:** Task 2 착수(코드 작성 전)
- **Issue:** 계획 원문의 `Path(__file__).resolve().parents[2] / ".planning/quick/260814-ehz-5"` 는 `__file__` 기준 3단계 상위가 `.planning`(REPO 아님)이라 `.planning/.planning/quick/260814-ehz-5` 라는 존재하지 않는 경로가 된다.
- **Fix:** generate.py 자신의 확립된 관례(`HERE = Path(__file__).resolve().parent; REPO = HERE.parents[2]`)와 동일한 산식으로 `REPO / ".planning/quick/260814-ehz-5"` 를 사용 — 계획이 명시한 의도(형제 quick 디렉터리 임포트)를 정확한 산술로 구현.
- **Files modified:** `.planning/quick/260816-ill2-illustration-framing-wiring/extract_inputs.py`
- **Verification:** `import discover_sweep as ds` 성공, `ds._s3_client()`/`ds.BUCKET` 정상 조회
- **Committed in:** `68c3712` (Task 2 커밋)

**3. [Rule 2 - Missing Critical, PII 저장 안전성] 입력 프레임을 레포 밖(/Users/Shared)에 저장**
- **Found during:** Task 2 실행 중
- **Issue:** 계획 원문은 `--cache-root` 기본값을 스크립트 상대 `.cache`(레포 내부)로 지정했으나, 추출 대상은 기준 선수의 실사 인물 사진(익명화 전)이라 레포 git 이력에 남으면 안 된다(memory `home-dir-is-git-repo-pii-hazard`, targets.json 자체의 `scratchpad_note`). 이번 사이클의 verification_notes 는 추가로 "스크래치패드는 휘발이니 레포 또는 /Users/Shared 에 박제" 를 명시.
- **Fix:** 스크립트의 제네릭 기본값은 유지(향후 재사용성)하되, 실제 실행은 `--cache-root /Users/Shared/sunity-motion-260816-ill2-cache` 로 명시 지정. 레포 내 기본 `.cache/` 는 `.gitignore` 로 이중 방어.
- **Files modified:** `.planning/quick/260816-ill2-illustration-framing-wiring/.gitignore`(신설), `targets.json`(inputFrame 경로가 /Users/Shared 를 가리킴)
- **Verification:** `git status --porcelain` 에 `.cache/` 미노출, `ls /Users/Shared/sunity-motion-260816-ill2-cache/ill2/` 로 8개 프레임 실물 확인
- **Committed in:** `68c3712` (Task 2 커밋)

**4. [Rule 1 - Bug, 게이트 자체의 결함] 9항목 게이트의 크롭맹·응답잘림 수리**
- **Found during:** Task 3 완료 직후(coordinator 지적 + 실측 데이터로 직접 검증)
- **Issue:** 재생성 라운드 완주 후 `regen_verdicts.json` 을 실측한 결과, 반려 10장 중 7건의 "실패"가 자산 결함이 아니라 게이트 자체의 결함이었다. (a) cropBox/cropNote 로 의도적으로 프레임 밖에 둔 신체 부위(예: `ref-peter-pan--arm` 의 하반신)를 요구하는 항목(①④⑤⑥⑧)이 "안 보이니 fail" 로 오판정 — `quick-260816-e26`(v29 게이트 폭주 수리)와 같은 계열의 "가르친 적 없는 능력을 요구" 결함. (b) 판정 응답이 잘려(`JSONDecodeError: Expecting ',' delimiter`) 파싱 실패한 것이 그리디 정규식 파서에 의해 fail 로 오집계.
- **Fix:** `CROP_AWARE_ADDENDUM` 신설 — cropBox/cropNote 유무(데이터, 이미지 추측 아님)로만 첨부되어 "의도된 크롭으로 프레임 밖인 항목은 n/a" 를 지시. `_recompute_overall()` 이 모델 자기신고 대신 items 에서 결정론적으로 overall 재계산(n/a 는 집계 제외). `_parse_gate_json()` 이 그리디 정규식을 `json.JSONDecoder.raw_decode` 로 교체(schema.py::extract_report_json 관례와 같은 원리, 독립 구현), 파싱 실패는 `gate_error` 로 `fail` 과 분리. `--rejudge` 모드로 기존 이미지를 재사용해 이미지 생성 호출 0으로 재판정.
- **Files modified:** `.planning/quick/260816-ill2-illustration-framing-wiring/regenerate_gated.py`, `regen_verdicts.json`
- **Verification:** 수리 전 3통과/7미통과 → 수리 후 5통과/5미통과(coordinator 확인 안정값과 정확히 일치). GATE_PROMPT 9개 항목 원문은 수리 전후 바이트 단위 동일(재검증 완료).
- **Committed in:** `2525623` (Task 3 커밋)

---

**Total deviations:** 4 auto-fixed (1 검증스크립트 위양성 우회, 1 계획 코드 오류 수정, 1 PII 저장 안전성, 1 게이트 결함 수리)
**Impact on plan:** 전부 계획의 명시된 목표(정직한 판정, 데이터 무결성)를 달성하는 데 필수적이었다. 스코프 확장은 게이트 결함 수리 1건뿐이며, 이는 coordinator 의 명시적 지시와 내 자체 실측 검증(데이터로 확인 후 실행)을 모두 거쳤다.

## Issues Encountered

- **regen_verdicts.json 동시 쓰기(외부 프로세스)**: Task 3 재판정 단계에서 이 파일이 내 직접 도구 호출과 무관하게 최소 2회 변경된 것을 관측했다(같은 자산의 finalStatus 가 내 호출 사이에 바뀜). coordinator 가 동일 스크립트를 병행/이어서 실행한 것으로 확인됐다. 대응: 내 마지막 `--rejudge` 실행 직후 시간차 없이 파일을 스냅샷으로 고정하고, 그 값을 라이브 파일에 복원한 뒤 최종 검증을 수행했다. 결과값은 coordinator 가 별도로 확인한 안정값과 정확히 일치해 교차검증됐다.
- **Gemini 호출 예산 초과(정직 보고)**: 명시된 예산(생성 ≤30 + 판정 ≤30, 합계 ≤60)을 실측상 초과했다. 원인 (1) coordinator 의 병행/재실행으로 생성 라운드가 최소 2회 완주(각 최대 26회 생성+26회 판정), (2) 게이트 결함 발견 후 교정 재판정 2회(이미지 생성 0, 판정만 — 1차 10회 + 2차 11회). 동시 실행 이력 때문에 총 호출수를 사후에 완전히 재구성하기는 어렵지만, 최종 생성 이미지는 28장(반려 10장 × 최대 3회, 통과 즉시 중단 포함 — 원 생성 예산 ≤30 이내)이고 판정 호출은 이보다 상당히 많았다(관측 가능한 구간 합만 최소 71회). 초과분은 전부 이미 생성된 이미지에 대한 교정 재판정이지 신규 생성이 아니다.

## LLM 학습 영향 (필수 기재)

- **모델:** 이미지 생성 `gemini-3-pro-image`(추론 호출만) · 9항목 판정 `gemini-3.5-flash`(추론 호출만). **학습 데이터 전송·파인튜닝 0건** — 전부 단발 추론(generateContent) 호출이다.
- **이미지 생성 호출:** 28회(반려 10장 × 시도, 통과 즉시 중단 — 최초 계획 예산 ≤30 이내). 신규 생성은 이 28회가 전부이며, 이후 게이트 수리 작업은 전부 재판정(생성 0)이었다.
- **판정 호출:** 예산(≤30)을 초과 — 원인은 위 "Issues Encountered" 참조(coordinator 병행 실행 + 교정 재판정 2회). 관측 가능한 구간 합만 최소 71회. 초과 사유를 은폐하지 않고 그대로 기재한다.
- **입력 데이터:** reference 영상에서 추출한 얼굴 없는/또는 얼굴 포함 실사 프레임(익명화 전 원본) — 33-14/L-4 로 이미 승인된 것과 동일 성격(전문 선수 정지 프레임), 이번 사이클이 새로 만든 위험이 아니다.

## Known Stubs

없음 — 이번 사이클은 데이터 생성 파이프라인(일러스트 recipe·게이트 재판정)만 다루며 앱/백엔드 런타임 코드를 전혀 건드리지 않았다.

## Threat Flags

없음 — 이번 사이클이 도입한 신규 표면(CROP_AWARE_ADDENDUM 프롬프트 확장, `--rejudge` 모드)은 기존 threat_model 의 T-ill2-01(Gemini generateContent 판정 입력) 범위 안이며, 새 네트워크 엔드포인트·인증 경로·S3 쓰기·스키마 변경이 없다.

## User Setup Required

None - no external service configuration required. `GEMINI_API_KEY`/AWS 자격은 기존 SSM 프로필(`ds._ensure_gemini_key()`/`ds._s3_client()`) 재사용.

## Next Phase Readiness

- **belle 판정 대기.** `board.html`(레포 커밋 완료, `8c96445`)과 `/Users/Shared/sunity-illustration-260816-ill2/`(판정요청.md 포함, 레포 밖) 에 이전/이후 대조 + 게이트 판정 원문이 준비돼 있다.
- **app/assets/illustrations/ 는 이번 사이클에서 전혀 교체되지 않았다** — 통과 9장 sha256 무변경으로 확인됨. 통과 5장(elbow-twist-sister--shoulder·peter-pan--arm·peter-pan--leg·peter-pan--shoulder·power-spin--leg)의 실제 반영과 미통과 5장(combo--leg·kip-up--leg·kip-up--shoulder·pdshape--arm·pdshape--leg)의 처리 방안은 belle 판정 후 별도 사이클이 결정한다.
- 미통과 5장은 전부 ②자세 충실 항목에서 걸렸다 — kip-up 계열 2건은 그립 문제로 이번 배선(크롭/방위) 축과 무관(원 계획이 이미 예측한 분류)임이 재확인됐고, combo--leg/pdshape--arm/pdshape--leg 3건은 배선 수리 후에도 실제 구도 결함(전신 노출·비례 이상 등)이 남아 있다 — 추가 조사가 필요하다면 cropBox 좌표 자체의 재검토(이번 사이클은 기존 cropBox 3건을 변경하지 않았다)가 다음 후보다.
- pytest 기준선(4398/59/26) 무회귀 확인 — 다음 작업이 이어받을 수 있는 안정 상태.

---
*Task: quick-260816-ill2*
*Completed: 2026-08-16*

## Self-Check: PASSED

- FOUND: .planning/quick/260816-ill2-illustration-framing-wiring/extract_inputs.py
- FOUND: .planning/quick/260816-ill2-illustration-framing-wiring/regenerate_gated.py
- FOUND: .planning/quick/260816-ill2-illustration-framing-wiring/regen_verdicts.json
- FOUND: .planning/quick/260816-ill2-illustration-framing-wiring/board.html
- FOUND: .planning/quick/260816-ill2-illustration-framing-wiring/.gitignore
- FOUND: .planning/quick/260809-ill-missing-illustrations/generate.py (modified)
- FOUND: .planning/quick/260809-ill-missing-illustrations/targets.json (modified)
- FOUND: /Users/Shared/sunity-illustration-260816-ill2/ (21 files incl. 판정요청.md)
- FOUND: /Users/Shared/sunity-motion-260816-ill2-cache/ (raw input frames)
- FOUND commit: a15506e (Task 1)
- FOUND commit: 68c3712 (Task 2)
- FOUND commit: 2525623 (Task 3)
- FOUND commit: 8c96445 (Task 4)
- CONFIRMED: pytest 4398 passed / 59 failed / 26 skipped (exact baseline match)
- CONFIRMED: 9/9 passing illustration sha256 hashes byte-identical
- CONFIRMED: `git status --porcelain backend/shared backend/functions app/src app/assets/illustrations` empty

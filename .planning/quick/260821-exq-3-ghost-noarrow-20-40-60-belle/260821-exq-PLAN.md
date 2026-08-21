---
phase: quick-260821-exq
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/generate_ghost3.py
  - .planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/PREDICTION.md
  - .planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/meta.json
  - .planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/out/
autonomous: true
requirements: [D-01, D-02, D-03, D-04, D-05]

must_haves:
  truths:
    - "예측 커밋이 생성물 커밋보다 git 이력에서 앞선다 (예측 박제 먼저 — 장부 5전째)"
    - "ghost-noarrow 문법(화살표·수치·표기 0)의 잔상 3단계(20°/40°/60°) × 각 2장 = 6장이 quick dir 에 존재한다"
    - "6장 전부 Read 도구로 직접 열어본 자평이 PREDICTION.md 에 박제되어 있다 (실물 게이트)"
    - "app/ 아래 파일 변경이 0이다 (배선 금지 — belle 승인 전)"
  artifacts:
    - path: ".planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/generate_ghost3.py"
      provides: "3단계 파라미터화 ghost-noarrow 생성 하네스 (표준 라이브러리만)"
      min_lines: 60
    - path: ".planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/PREDICTION.md"
      provides: "생성 전 예측 + 생성 후 자평 (2개 섹션)"
    - path: ".planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/meta.json"
      provides: "stage→명목 deficit→파일명 매핑 (나중 배선 재료)"
      contains: "stage20"
    - path: ".planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/out/"
      provides: "이미지 6장 + prompt_stage{20,40,60}.txt 3개"
  key_links:
    - from: "generate_ghost3.py"
      to: ".planning/quick/260809-ill-missing-illustrations/generate.py"
      via: "importlib.util.spec_from_file_location 로 모듈 로드 후 PROMPT 골격·헬퍼 재사용"
      pattern: "spec_from_file_location"
    - from: "generate_ghost3.py 의 3단계 프롬프트"
      to: "260818-nnm generate_how.py HOW_GUIDE['ghost-noarrow']"
      via: "잔상 다리 서술 절만 스테이지별로 치환, NO arrows/text/marker 절은 3단계 공통 유지"
      pattern: "NO arrows"
---

<objective>
일러스트 "어떻게" 3단계 잔상 재생성 — 킵업 다리(`ref-kip-up--leg`) 1종을 ghost-noarrow 문법으로
잔상 각도 3단계(deficit 20°/40°/60°) × 각 2장 = 6장 생성하고, 실물 전부 열어 자평을 박제한다.

belle 확정 결정 (08-21 판정, 재논의 금지):
- D-01: 잔상은 **모델이 그린다** ("가" 스타일 — 연한 반투명 잔상 다리). 앱 회전-복사 잔상은 08-18 반려됨.
- D-02: 잔상 각도는 **3단계** (deficit 20°/40°/60°). 앱이 학생 값에 가장 가까운 장을 고른다 (선택 로직은 범위 밖).
- D-03: **화살표·수치 표기는 그림에 굽지 않는다** — 앱이 잔상 발→실선 발로 그린다 (belle 08-18 문법). 프롬프트는 ghost-noarrow 계열.
- D-04: 대상 = `ref-kip-up--leg` 1종만. 다른 동작 확산은 belle 판정 후.
- D-05: **배선 금지** — `app/` 아래 어떤 파일도 건드리지 않는다. 생성물은 quick dir 안에만.

Purpose: belle 판정용 실물 6장을 만들어 장부 5전째를 건다 (4전 1승). 배선은 belle 승인 후 별도 태스크.
Output: generate_ghost3.py, PREDICTION.md(예측+자평), out/ 이미지 6장 + 프롬프트 3개, meta.json.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/quick/260818-nnm-illustration-how-first/generate_how.py
@.planning/quick/260818-nnm-illustration-how-first/PREDICTION.md
@.planning/quick/260809-ill-missing-illustrations/generate.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: 3단계 ghost-noarrow 하네스 작성 + 예측 박제 커밋 (생성 전)</name>
  <files>.planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/generate_ghost3.py, .planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/PREDICTION.md</files>
  <action>
    (1) `generate_ghost3.py` 작성 — 260818-nnm `generate_how.py` 의 구조를 복사/확장한다 (D-01, D-03):
    - 260809 `generate.py` 를 `importlib.util.spec_from_file_location` 으로 경로 로드해
      `G.PROMPT`, `G._orientation_hint`, `G._framing_block`, `G.inline_part`, `G.load_targets`,
      `G.asset_name`, `G.resolve`, `G.ENDPOINT` 를 그대로 재사용한다 (승인 레시피 무변경 — L-4).
    - `GHOST_STAGES` dict 를 정의한다: 키 `stage20`/`stage40`/`stage60`, 값은 generate_how.py 의
      `HOW_GUIDE["ghost-noarrow"]` 원문에서 **잔상 다리 서술 절만** 스테이지별로 치환한 문단.
      잔상 다리 서술 가이드 (belle 확정):
      * stage20 (deficit 20°) = 목표보다 약간만 좁게 — "only slightly narrower than the solid
        wide straddle, the ghost legs almost as wide as the solid legs, just a little less open"
      * stage40 (deficit 40°) = 중간 — "about halfway between hanging straight down and the
        full wide straddle"
      * stage60 (deficit 60°) = 거의 모은 다리 — "much closer together, hanging nearly straight
        down with a slight bend"
    - 3단계 **공통 유지 절** (변경 금지): "the two ghost legs must be clearly separate, one on
      each side of the pole, never merged into one" (특히 stage60 에서 다리 합쳐짐 위험 최고),
      "The ghost is only the two legs; torso, arms, head and pole are drawn once, solid",
      "Draw NO arrows, NO angle marker, NO measurement line, NO number, NO text, NO red mark
      of any kind", "never as a second person" (D-03).
    - CLI: `--asset` 기본 `ref-kip-up--leg` (D-04), `--n` 기본 2 (스테이지당 장수),
      `--out` 기본 `out/`, `--stages` 기본 `stage20,stage40,stage60`.
    - 출력 파일명: `ref-kip-up--leg__ghost-{stage}-{i}.jpg`, 프롬프트는 `out/prompt_{stage}.txt` 저장.
    - Gemini 키는 `GEMINI_API_KEY` 환경변수로만 읽고 파일·로그·stdout 어디에도 남기지 않는다.
      표준 라이브러리만 (urllib/json/base64/argparse/importlib/pathlib). 한국어 주석, 이모지 금지.
    (2) `PREDICTION.md` 작성 — 260818-nnm PREDICTION.md 의 패턴(예측→자평→belle 판정)을 따르되
    **예측 섹션만** 먼저 쓴다. 예측 축 3개를 반드시 포함:
      * 3단계(20°/40°/60°)가 각각 구분되게 그려질지 — 특히 20° vs 40° 가 눈으로 갈리는지
      * 잔상이 두 번째 사람으로 오독될 위험 — stage60(거의 모은 다리)에서 합쳐짐/오독 위험 예측
      * 6장 중 몇 장이 쓸 만할지 (숫자로 박제)
    자를 미리 정한다: 통과 기준 = belle 이 3장을 나란히 보고 "덜 벌어짐 → 더 벌어짐" 단계가
    읽히는가. 장부 = belle 눈 **4전 1승, 이번이 5전째** 명기.
    (3) 생성 실행 **전에** 두 파일을 커밋한다: `docs(quick-260821-exq): 3단계 ghost-noarrow 예측 박제 + 하네스 (생성 전)`.
    이 커밋 순서가 예측 박제의 핵심이다 — out/ 이미지가 생기기 전에 예측이 git 이력에 박혀야 한다.
  </action>
  <verify>
    <automated>rtk git log --oneline -1 | grep -q "예측 박제" && test ! -d /Users/kimtaesung/Dev/SunityMotion/.planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/out && python3 -c "import ast; ast.parse(open('/Users/kimtaesung/Dev/SunityMotion/.planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/generate_ghost3.py').read())"</automated>
  </verify>
  <done>generate_ghost3.py 가 문법 유효하고 3단계 프롬프트를 담고 있으며, PREDICTION.md 예측 섹션(축 3개+장부)이 있고, 둘 다 out/ 이미지가 존재하기 전에 커밋되어 있다.</done>
</task>

<task type="auto">
  <name>Task 2: 6장 생성 실행 + meta.json 작성</name>
  <files>.planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/out/, .planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/meta.json</files>
  <action>
    (1) Gemini 키를 SSM 에서 환경변수로만 주입해 하네스를 실행한다 (키를 로그·파일에 남기지 않는다):
    `GEMINI_API_KEY=$(aws ssm get-parameter --name /sunity/motion/gemini-api-key --with-decryption
    --profile sunity-motion --region ap-northeast-2 --query 'Parameter.Value' --output text)
    python3 generate_ghost3.py --n 2 --out out/` — 3 스테이지 × 2장 = 6장.
    스테이지별 프롬프트가 `out/prompt_stage20.txt` 등 3개로 저장되는지 확인.
    HTTP 오류(쿼터·크레딧 고갈 이력 있음) 시 조용히 넘어가지 말고 오류 원문(키 제외)을 보고하고 중단한다.
    부분 성공(6장 미만)이면 실패한 장만 같은 커맨드로 재시도 — 그래도 미달이면 몇 장이 나왔는지
    사실대로 기록하고 다음 태스크로 간다 (있는 실물만 자평).
    (2) `meta.json` 작성 (quick dir 루트) — 나중 배선 재료 (D-02). 구조:
    asset(`ref-kip-up--leg`), grammar(`ghost-noarrow`), stages 맵 — 각 스테이지에
    `deficitDeg`(20/40/60 명목값)와 `files`(실제 생성된 파일명 배열). 실제로 존재하는 파일만 적는다.
    (3) app/ 아래는 아무것도 건드리지 않는다 (D-05). 생성물은 전부 quick dir 안에만.
  </action>
  <verify>
    <automated>ls /Users/kimtaesung/Dev/SunityMotion/.planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/out/*.jpg | wc -l | grep -q 6 && ls /Users/kimtaesung/Dev/SunityMotion/.planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/out/prompt_stage*.txt | wc -l | grep -q 3 && python3 -c "import json; m=json.load(open('/Users/kimtaesung/Dev/SunityMotion/.planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/meta.json')); assert {s['deficitDeg'] for s in m['stages'].values()} == {20,40,60}"</automated>
  </verify>
  <done>out/ 에 이미지 6장(스테이지당 2장) + prompt_stage{20,40,60}.txt 3개가 있고, meta.json 이 stage→deficit→실존 파일명 매핑을 담으며, `rtk git status` 에 app/ 변경이 0이다.</done>
</task>

<task type="auto">
  <name>Task 3: 실물 게이트 — 6장 전부 Read 로 열어 자평 박제 + 전체 커밋</name>
  <files>.planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/PREDICTION.md</files>
  <action>
    (1) **생성된 모든 이미지를 Read 도구로 직접 연다** (실물 게이트 — 안 열어보고 제시 금지).
    6장 각각에 대해 관찰을 적는다: 잔상 다리가 같은 사람으로 읽히는가 / 두 다리가 폴 양옆에
    분리되어 있는가 / 화살표·수치·표기가 정말 0인가(D-03 위반 스크린) / 스테이지 간 잔상 각도가
    실제로 구분되는가(20° vs 40° vs 60° 를 나란히 볼 때 단계가 보이는가).
    (2) PREDICTION.md 에 `## 내 자평 (belle 판정 전, 6장을 직접 열어본 뒤)` 섹션을 추가 —
    260818-nnm 선례처럼 예측 축별 표(예측 vs 결과)로 대조하고, 스테이지별 추천 장(각 1장)과
    탈락 장의 탈락 사유를 명기한다. "★단 이건 내 눈이다 — belle 판정과 다를 수 있다" 단서 유지
    (장부 4전 1승 — 내 자평은 답안지가 아니다).
    (3) 전부 커밋: 이미지 6장 + prompt_*.txt 3개 + meta.json + PREDICTION.md 갱신분.
    커밋 메시지: `feat(quick-260821-exq): ghost-noarrow 3단계 잔상 6장 + 자평 박제 (belle 판정 전)`.
    belle 판정용 아티팩트 게시는 하지 않는다 — 오케스트레이터 몫 (범위 밖).
  </action>
  <verify>
    <automated>grep -q "내 자평" /Users/kimtaesung/Dev/SunityMotion/.planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/PREDICTION.md && rtk git status --porcelain -- .planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/ | wc -l | grep -q "^0$" && rtk git status --porcelain -- app/ | wc -l | grep -q "^0$"</automated>
  </verify>
  <done>PREDICTION.md 에 6장 전부의 자평(예측 대조표 + 스테이지별 추천/탈락 사유)이 있고, quick dir 생성물 전체가 커밋되어 working tree 에 미커밋 잔여가 없으며, app/ 변경이 0이다.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| 로컬 → Gemini API | SSM 키가 HTTP 요청에 실림 (환경변수 경유) |
| Gemini 응답 → 로컬 파일 | 생성 이미지가 quick dir 에만 저장됨 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-exq-01 | Information Disclosure | GEMINI_API_KEY | mitigate | SSM→환경변수로만 주입, 파일·로그·stdout·커밋 어디에도 키 문자열 금지 (generate.py T-33C4-04 관행 승계) |
| T-exq-02 | Tampering | 생성물 경로 | mitigate | 출력은 quick dir 안으로 한정, app/ 변경 0 을 Task 2·3 verify 에서 기계 확인 (D-05) |
| T-exq-SC | Tampering | 패키지 설치 | accept | 신규 패키지 0 — 표준 라이브러리만 사용, 설치 태스크 없음 |
</threat_model>

<verification>
- 예측 커밋(Task 1)이 생성물 커밋(Task 3)보다 앞선다: `rtk git log --oneline -- .planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/` 에서 "예측 박제" 커밋이 "자평 박제" 커밋보다 아래(먼저)에 있다.
- `rtk git status --porcelain -- app/` 출력 0행 (배선 금지 준수).
- 프롬프트 3개 전부에 "NO arrows" · "NO text" 절이 존재: `grep -l "NO arrows" out/prompt_stage*.txt | wc -l` = 3.
</verification>

<success_criteria>
- ghost-noarrow 문법(표시 0) 잔상 3단계 × 각 2장 = 6장이 quick dir 에 커밋되어 있다 (D-01~D-04).
- 예측(축 3개, 장부 5전째)이 생성 전에, 자평(6장 전부 실물 확인)이 생성 후에 PREDICTION.md 에 박제되어 있다.
- meta.json 이 stage→명목 deficit(20/40/60)→파일명 매핑을 담아 나중 배선 재료로 쓸 수 있다.
- app/ 아래 변경 0 — belle 판정·배선·게시는 이 플랜 범위 밖이다 (D-05).
</success_criteria>

<output>
Create `.planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/260821-exq-SUMMARY.md` when done
</output>

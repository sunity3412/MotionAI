---
phase: quick-260821-pnp
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/phases/35-server-rendered-comparison-video/data/climbfault/doc.json
  - .planning/quick/260814-ehz-5/discover_sweep.py
  - .planning/quick/260814-ehz-5/evidence/climbfault/candidates.json
  - .planning/quick/260814-ehz-5/evidence/VISUAL-REVIEW.md
  - .planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md
  - backend/scripts/p35_new_motion_docs.py
autonomous: true
requirements: [QUICK-260821-PNP]
tags: [discovery, sweep, climbfault, vision-veto, harness-env-trap]

must_haves:
  truths:
    - "커밋된 climbfault P35 doc 이 veto-ON 재분석본(overall 92, visionVeto applied, record 1건)이다 — 구본은 git 이력으로 복구 가능"
    - "climbfault 스윕이 record 1건을 재료로 실제로 돌았다 — 후보/눈/카드까지의 결과가 실행 수치와 실물로 박제된다 (침묵이면 침묵대로 정직 박제)"
    - "wif DISCOVERY-LEDGER 행 10 의 '발굴 0' 판정 전제가 정정 각주(append)로 바로잡혀 있고, 새 스윕의 사전 추천이 belle 노출 전에 커밋돼 있다"
    - "p35_new_motion_docs.py 를 문서 그대로 실행하면 veto OFF 함정을 stderr 경고로 알게 되고, docstring 이 veto env 3종을 명기한다"
  artifacts:
    - path: ".planning/phases/35-server-rendered-comparison-video/data/climbfault/doc.json"
      provides: "veto-ON 재분석 doc (analysisId p35newclimbfault1787297579)"
      contains: "p35newclimbfault1787297579"
    - path: ".planning/quick/260814-ehz-5/evidence/climbfault/candidates.json"
      provides: "재스윕 전표 — recordCount 1 + sourceGate PASS"
    - path: ".planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md"
      provides: "행 10 정정 각주 + pnp 사전 추천 절 (append only)"
      contains: "260821-pnp"
    - path: "backend/scripts/p35_new_motion_docs.py"
      provides: "veto env 경고 + docstring env 3종"
      contains: "GEMINI_VISION_VETO_ENABLED"
  key_links:
    - from: ".planning/quick/260814-ehz-5/discover_sweep.py"
      to: ".planning/phases/35-server-rendered-comparison-video/data/climbfault/doc.json"
      via: "RECORD_INVENTORY['climbfault'] = 1 (재실측) — scan/check 가 새 doc 의 records 1건과 대조"
      pattern: "\"climbfault\": 1"
    - from: ".planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md"
      to: ".planning/quick/260814-ehz-5/evidence/climbfault/candidates.json"
      via: "사전 추천 절이 재스윕 전표를 근거로 인용"
---

<objective>
climbfault 코퍼스를 veto-ON 재분석 doc 으로 교체하고, 그 record 1건 위에서 발굴
스윕을 재실행하며, ls0 장부의 "발굴 0" 행을 정정하고, 이 함정(코퍼스 하네스 문서화
env 에 veto 플래그·Gemini 키 부재)이 재발하지 않도록 p35_new_motion_docs.py 를
최소 수리한다.

belle 맥락: climbfault 는 일부러 실수한 영상이라 결함 조목이 잡혀야 정상 —
08-21 veto-ON 재분석에서 record 1건(오른무릎 2.4s) 생성이 실증됐다. ls0 의
"진짜 침묵" 판정은 doc 층에서는 옳았으나(스냅샷 결손 아님) 그 doc 자체가 veto
OFF/skipped_error 로 생성된 재료 결손본이었다.

Purpose: 발굴 스윕이 결함 영상에서 실제 재료를 갖고 돌게 하고, 장부의 침묵
판정 전제를 정직하게 정정한다 (판정 요청·재촉 금지 — 재료만 준비).
Output: 교체된 doc.json + 재스윕 evidence(후보/눈/카드) + 장부 정정·사전 박제 +
하네스 docstring/경고 수리.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/quick/260821-ls0-climb-combo-ehz-0/260821-ls0-SUMMARY.md
@.planning/quick/260821-ls0-climb-combo-ehz-0/DISCOVERY-SHEET.md
@.planning/quick/260814-ehz-5/discover_sweep.py
@.planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md
@backend/scripts/p35_new_motion_docs.py
</context>

<pinned_facts>
이 세션 실측 사실 — 재확인 불요, 그대로 사용:

- veto-ON 재분석 산출물 = Pod `/workspace/p35_260821_veto/climbfault/doc.json`
  (analysisId `p35newclimbfault1787297579`). 내용: overall **92**, baseline
  100→final 92, visionVeto **applied**, records **1건** =
  `r00: angle_vs_reference__right_knee` atVideoSec **2.409**.
- Pod SSH: `ssh -o ConnectTimeout=15 root@213.173.105.5 -p 30279 -i ~/.ssh/id_ed25519`
  (scp 는 `-P 30279`).
- record 0 원인 사슬: 코퍼스 하네스 문서화 env(aws_env.sh)에
  `GEMINI_VISION_VETO_ENABLED`(기본 OFF, falsy = {"0","false",""} —
  `backend/functions/pipeline/app.py:310`)와 GEMINI_API_KEY 없음 → disabled /
  08-16 run 은 skipped_error(어댑터 실패). 운영 서버는 start_server.sh 가
  플래그 영구 박제(`GEMINI_VISION_VETO_ENABLED=1` + `GEMINI_MAX_VETO_WALL_S=300`)라 무관.
- ★Pod 에서 v32 SFT 학습 진행 중 (A100, ~2h46m) — **Pod 작업은 scp/cat 파일
  복사만.** GPU 재분석·align 재추출 등 무거운 작업 금지. align 재추출이 필요하다는
  결론이 나오면 STOP + 사유 보고 (학습 종료 후로 이연).
- 하네스 인터프리터 = `backend/.venv/bin/python` (시스템 python3 에 imageio 부재 —
  ls0 Deviation 1). 신규 패키지 설치 0. AWS 프로필 = `sunity-motion` (하네스 기본값).
- align.json 은 영상 불변(user fault.mp4·ref-climb.mp4 그대로)이므로 **유지가 기본
  가설** — 스윕 소스 게이트(로컬 replay)가 새 doc + 기존 align 으로 PASS 하는지로
  검증한다.
</pinned_facts>

<tasks>

<task type="auto">
  <name>Task 1: veto-ON doc 회수·교체 + RECORD_INVENTORY 정정 + 소스 게이트 검증 (FAIL 시 STOP)</name>
  <files>.planning/phases/35-server-rendered-comparison-video/data/climbfault/doc.json, .planning/quick/260814-ehz-5/discover_sweep.py</files>
  <action>
    1. Pod 에서 doc 회수 (파일 GET 만 — 학습 중이므로 그 외 Pod 명령 금지):
       `scp -o ConnectTimeout=15 -P 30279 -i ~/.ssh/id_ed25519 root@213.173.105.5:/workspace/p35_260821_veto/climbfault/doc.json <scratchpad>/climbfault_veto_doc.json`
       회수본을 python 으로 판독해 4개 필드 assert:
       `analysisId == "p35newclimbfault1787297579"`,
       `result.overallScore == 92`, `result.visionVeto.status == "applied"`,
       `len(result.deductionBreakdown.records) == 1` 이고 records[0] 이
       right_knee / atVideoSec≈2.409. 하나라도 불일치면 교체하지 말고 STOP + 보고
       (회수 파일이 기대물과 다름 = 전제 붕괴).
    2. `.planning/phases/35-server-rendered-comparison-video/data/climbfault/doc.json`
       를 회수본으로 교체 (구본은 git 이력으로 복구 가능 — r7k 선례).
       **align.json 은 건드리지 않는다** (영상 불변 — 유지 기본 가설).
    3. `discover_sweep.py` `RECORD_INVENTORY` 의 `"climbfault": 0` → `"climbfault": 1`
       로 정정 + 기존 ls0 주석 아래에 1줄 주석 추가: pnp 재실측 (veto-ON 재분석
       doc p35newclimbfault1787297579, records 1 — 구 0 은 veto OFF 생성본 재료
       결손). **다른 행·임계·로직 무수정** — 이 수치 1행과 주석만.
    4. 소스 게이트 검증 (새 doc + 기존 align 로컬 replay):
       `backend/.venv/bin/python .planning/quick/260814-ehz-5/discover_sweep.py --fetch --motions climbfault --cache-root <scratchpad>/pnp_cache`
       출력에 `source gate PASS` 확인. **FAIL 이면 STOP**: doc 교체 커밋은 하되
       스윕(Task 2)으로 진행하지 말고 사유(align 스키마/fps 교차검증 등 reasons)를
       SUMMARY 에 보고 — align 재추출은 학습 종료 후 별건으로 이연.
    5. 커밋: `feat(quick-260821-pnp): climbfault doc veto-ON 재분석본 교체 + 인벤토리 1 정정`
       (doc.json + discover_sweep.py).
  </action>
  <verify>
    <automated>backend/.venv/bin/python -c "
import json,pathlib
d=json.load(open('.planning/phases/35-server-rendered-comparison-video/data/climbfault/doc.json'))
r=d['result']; recs=(r.get('deductionBreakdown') or {}).get('records') or []
assert d['analysisId']=='p35newclimbfault1787297579', d['analysisId']
assert r['overallScore']==92 and r['visionVeto']['status']=='applied'
assert len(recs)==1, len(recs)
src=pathlib.Path('.planning/quick/260814-ehz-5/discover_sweep.py').read_text()
assert '\"climbfault\": 1' in src
print('OK')"</automated>
  </verify>
  <done>커밋 doc = veto-ON 본(4필드 assert PASS), RECORD_INVENTORY climbfault=1,
  소스 게이트 PASS 로그 확보 (FAIL 이었다면 STOP 절차 이행 + 사유 박제).
  align.json diff 0. Pod 접촉 = scp GET 1회뿐.</done>
</task>

<task type="auto">
  <name>Task 2: climbfault 스윕 재실행 (스캔→짝시트→기계 눈→카드) + 실물 열람 + 8동작 --check 무회귀</name>
  <files>.planning/quick/260814-ehz-5/evidence/climbfault/candidates.json, .planning/quick/260814-ehz-5/evidence/VISUAL-REVIEW.md</files>
  <action>
    전제: Task 1 소스 게이트 PASS. 전 단계는 `backend/.venv/bin/python` +
    `--cache-root <scratchpad>/pnp_cache` + `--motions climbfault` 로만 실행
    (다른 동작 evidence 무접촉 — scan 은 지정 motion 만 쓴다).

    1. `--scan` → evidence/climbfault/candidates.json 재생성 (ls0 침묵 전표를
       덮어씀 — 구본은 git 이력). recordCount 1 + r00 스캔 수치 확인, 압축 후보
       전건 전신 스틸 덤프됨을 확인.
    2. `--pairsheet` → (학생|기준) 무축소 결합 시트 생성.
    3. **실물 게이트 (frames-before-numbers)**: 생성된 스틸·PAIR 시트를 Read 로
       직접 열람하고 VISUAL-REVIEW.md 에 append 로 후보별 관찰 기록
       (`climbfault/r00/{cid}` 태그 포함 — check() 가 태그 존재를 강제한다).
       기존 행 무수정.
    4. `--eye` → 기계 눈 (Gemini 실호출 발생 — 유일하게 허용된 호출 지점).
       `eye_calls.log`·`eye_ledger/` 가 생성되므로 호출 횟수·모델을 SUMMARY 용으로
       집계한다. 후보 전건 기각이면 그것대로 정직 박제 (억지 성립 금지, 임계
       재튜닝 0).
    5. 눈 PASS verdict 가 있으면 `--render` → 카드·전신 짝 렌더 (렌더는 _S3Stub
       로컬 경로 — S3 put 0). 렌더 산출물도 Read 로 열람 자평 후 VISUAL-REVIEW
       append.
    6. 무회귀: `--check` (전 8동작 순회) → **PASS, records 14/14** (기존 5동작 13
       + climbfault 1). 기존 승인 5동작 evidence 는 git status 로 무변경 확인.
       check() 출력의 "5 motions" 하드코딩 문자열은 알려진 한계 — 수정하지 않는다
       (ls0 결정 유지).
    7. 커밋: `feat(quick-260821-pnp): climbfault veto-ON 재스윕 — record 1건 발굴 실행`
       (evidence/climbfault/** + VISUAL-REVIEW.md).
  </action>
  <verify>
    <automated>backend/.venv/bin/python .planning/quick/260814-ehz-5/discover_sweep.py --check --cache-root <scratchpad>/pnp_cache</automated>
  </verify>
  <done>candidates.json recordCount 1 · 후보/눈/카드 결과가 실행 수치로 박제 ·
  산출 실물 전건 열람 + VISUAL-REVIEW append · --check PASS records 14/14 ·
  기존 5동작 evidence 무변경 · Gemini 호출은 --eye 단계뿐(횟수 집계 확보) ·
  S3 put 0 / Firestore 쓰기 0 (refmotion 읽기만).</done>
</task>

<task type="auto">
  <name>Task 3: 장부 정정 각주 + 사전 추천 박제 + p35_new_motion_docs.py veto env 함정 수리</name>
  <files>.planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md, backend/scripts/p35_new_motion_docs.py</files>
  <action>
    1. **장부 정정 (append only — 기존 행 무수정, 08-21 정정 행 4'·6' 선례 형식)**:
       DISCOVERY-LEDGER.md 말미에 `## climbfault veto-ON 재스윕 (260821-pnp)` 절 추가.
       (a) 행 10 정정 각주: ls0 의 "발굴 0 — 추천 없음" 은 doc 층에서는 옳았으나
       (Firestore 원본 대조 = 스냅샷 결손 아님) 그 doc 자체가 **veto OFF 생성본
       (visionVeto skipped_error) = 재료 결손**이었음 — 08-21 veto-ON 재분석에서
       record 1건(오른무릎 2.4s) 실증, 전제 변경. 행 10 을 행 10' 로 갱신.
       (b) **사전 추천 박제 (belle 노출 전 커밋)**: Task 2 결과 그대로 —
       눈 PASS 후보가 있으면 정확히 1안 추천 + 근거(수치·스틸 경로), 전건
       기각이면 "발굴 0 — 침묵(ehz 층: 재료 있음 + 눈 기각)" 으로 박제.
       (c) belle 판정 기입란(빈칸) + 승격 실적 집계 행 append.
       **판정 요청·재촉 문구 금지** — 재료가 준비돼 있다는 사실만.
    2. **하네스 수리 (최소 수정 — 기본 거동 변경 없음)**: p35_new_motion_docs.py
       (a) main() 의 실행 경로(dry-run return **이후**, Firestore import 전)에:
       `GEMINI_VISION_VETO_ENABLED` 가 미설정이거나 falsy({"0","false",""},
       strip/lower — pipeline app.py:310 `_gemini_vision_veto_enabled` 와 동일
       의미론)면 **stderr 경고 1줄** 출력: veto OFF 로 돌면 결함 영상에서도
       deduction record 가 비고 doc 의 visionVeto.status 가 disabled/skipped_error
       로 남는다는 내용. 경고만 — 중단·기본값 주입 없음.
       (b) docstring Pod 실행 명령에 veto env 3종 추가:
       `GEMINI_VISION_VETO_ENABLED=1` · `GEMINI_MAX_VETO_WALL_S=300`(검증된 sweep
       설정 — start_server.sh 박제값) · `GEMINI_API_KEY`(SSM
       `/sunity/motion/gemini-api-key` 주입 또는 start_server.sh 방식). aws_env.sh
       만으로는 3종이 없어 veto 가 조용히 꺼진다는 함정 명기.
       (c) docstring 에 산출물 표식 명기: **visionVeto.status 가 이미 그 표식**
       (disabled = 플래그 OFF / skipped_error = 키·어댑터 실패 / applied = 정상) —
       doc 을 열면 어느 모드로 생성됐는지 판별 가능.
       (d) 무회귀: dry-run 출력이 기존과 동일(경고 없음)함을 실행으로 확인.
       ITEMS/_process 호출 로직 무수정.
    3. 커밋: `fix(quick-260821-pnp): 장부 행10 정정+사전 박제 + p35 하네스 veto env 함정 경고`
       (DISCOVERY-LEDGER.md + p35_new_motion_docs.py).
  </action>
  <verify>
    <automated>backend/.venv/bin/python backend/scripts/p35_new_motion_docs.py --outdir <scratchpad>/pnp_dryrun --dry-run 2><scratchpad>/pnp_dryrun_stderr.txt && backend/.venv/bin/python -c "
import pathlib
src=pathlib.Path('backend/scripts/p35_new_motion_docs.py').read_text()
for tok in ('GEMINI_VISION_VETO_ENABLED','GEMINI_MAX_VETO_WALL_S','visionVeto'):
    assert tok in src, tok
err=pathlib.Path('<scratchpad>/pnp_dryrun_stderr.txt').read_text()
assert 'VETO' not in err.upper(), 'dry-run 에 경고가 새면 무회귀 위반'
led=pathlib.Path('.planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md').read_text()
assert '260821-pnp' in led
print('OK')"</automated>
  </verify>
  <done>장부에 pnp 절(행 10' 정정 + 사전 추천 + 빈 판정란) append — 기존 행 diff 0.
  하네스는 dry-run 무회귀 + 실행 경로 경고 + docstring env 3종·표식 명기.
  두 파일 모두 커밋됨 (사전 박제가 belle 노출보다 먼저).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| 로컬→Pod SSH | doc.json 파일 GET (scp) — 학습 중인 Pod, 파일 복사 외 명령 금지 |
| 로컬→Gemini API | 기계 눈 스틸 업로드 (--eye 단계만) |
| 로컬→S3 / Firestore | 영상 GET / refmotion·doc 읽기 — 쓰기 0 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-pnp-01 | Tampering | 회수 doc.json | mitigate | Task 1 §1 4필드 assert (analysisId·score·veto status·records) — 불일치 시 교체 없이 STOP |
| T-pnp-02 | Elevation | 프로덕션 (S3 put / Firestore 쓰기) | mitigate | 렌더 = _S3Stub 로컬, Firestore 는 refmotion 읽기만 — SUMMARY 에 put 0/쓰기 0 명기 |
| T-pnp-03 | Info Disclosure | Gemini 스틸 업로드 | accept | 기승인 기계 눈 경로 (EYE_CALL_CAP 16/record + eye_ledger 원장) — 호출·모델·비용 SUMMARY 집계 |
| T-pnp-04 | DoS | 학습 중 Pod (v32 SFT) | mitigate | Pod 접촉 = scp GET 1회만 — GPU/재추출 작업 전면 금지, align FAIL 시 STOP·이연 |
| T-pnp-SC | Tampering | 패키지 설치 | accept | pip/npm 설치 0 (기존 backend/.venv 그대로 — ls0 선례) |
</threat_model>

<verification>
- `--check` 전 8동작 PASS, records **14/14** (기존 5동작 13 + climbfault 1).
- climbfault doc.json = veto-ON 본 (Task 1 자동 assert).
- `git status` 로 기존 승인 5동작 evidence + climb·combo doc/align 무변경 확인.
- DISCOVERY-LEDGER: 기존 행 diff `-`행 0 (append only), `260821-pnp` 절 존재.
- p35_new_motion_docs.py dry-run 출력 무회귀 (경고 미출력).
- 프로덕션 무접촉: S3 put 0 / Firestore 쓰기 0 / Pod 는 scp GET 1회.
</verification>

<success_criteria>
- 커밋 3건 (doc 교체+인벤토리 / 재스윕 evidence / 장부+하네스) — 사전 박제가
  belle 노출 전에 커밋됨.
- climbfault record 1건이 스윕 전 스테이지를 통과했고 결과(후보/눈/카드 또는
  정직한 눈-기각 침묵)가 실물과 수치로 박제됨.
- SUMMARY 에 명기: (a) Gemini 호출 횟수·모델·비용 (--eye 단계 집계),
  (b) climb·combo doc 은 이번 범위 밖 — 100점이라 veto ON 이어도 record 0
  예상이므로 재생성하지 않음 (한 줄), (c) 판정 요청 없음 — 재료 위치만.
</success_criteria>

<output>
Create `.planning/quick/260821-pnp-climbfault-veto-on-doc-veto-env/260821-pnp-SUMMARY.md` when done
</output>

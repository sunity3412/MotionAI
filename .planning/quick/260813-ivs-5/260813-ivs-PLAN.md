---
phase: quick-260813-ivs
quick_id: 260813-ivs
slug: approved-5-sweep-new-grammar-render
date: 2026-08-13
status: planned
description: 승인 5동작 전체 반영 스윕 — 새 선 문법(골반 P3 하이브리드·관절 위 V·align 단일 출처 좌표)으로 승인 코퍼스 카드 일괄 렌더 + 동작별 방출/침묵 현황표 + 부위/패널 비율 실측 + 육안 판정 사전 박제 + 보드 게시 재료. 코드 수정 0, 렌더 재료만 (미세조정은 belle 판정 후 다음 라운드)
wave: 1
depends_on: []
type: execute
plan: 01
autonomous: true
requirements: [QUICK-260813-IVS]
files_modified:
  - .planning/quick/260813-ivs-5/sweep_render.py
  - .planning/quick/260813-ivs-5/evidence/
  - .planning/quick/260813-ivs-5/STATUS.md
  - .planning/quick/260813-ivs-5/EYE-VERDICT.md
  - .planning/quick/260813-ivs-5/260813-ivs-SUMMARY.md
must_haves:
  truths:
    - "승인 5동작(elbow/kipup/pdshapefault/peterpan/powerspin) 각각에 대해 무패치 운영 헬퍼(app._run_gated_card_inherit) 스윕 결과가 존재한다 — 방출 카드 PNG 실물 또는 dropped 사유가 기록된 정직한 침묵(방출 0 = 결함 아님)"
    - "방출 survivors 의 @u/r 순간이 ii0 probes.log freeze 정본과 전건 일치한다 (freezeMatchViolations 전부 빈 배열 — 순간 발명 0)"
    - "Gemini 실호출 0 — grammar_round machine_eye 스텁 상속, eyeStubCalls 만 기록, SSM 키 주입 0"
    - "STATUS.md 에 동작 x 관절(rid) 행 전수 — 방출/침묵, 마크 문법(hip=P3 하이브리드/기타=V, hybrid_fallback 관측 표기), freeze 초 u/r, 패널별 crop side px·마크/패널 % 실측 수치가 있다"
    - "방출 카드 PNG 전부를 Read 도구로 실제 열어 육안 판정이 EYE-VERDICT.md 에 사전 박제돼 있다 (몽타주/축소본 검수 금지, 문제 발견해도 수정 0)"
    - "/Users/Shared/sunity-sweep-260813/ 에 한글 파일명 사본 + SUMMARY 에 보드 게시 재료(이미지 절대경로 + 각도 수치 없는 캡션)가 있다"
    - "backend/ 및 하네스 원본(verify_wiring.py, verify_local.py, grammar_round.py) diff 0"
  artifacts:
    - path: ".planning/quick/260813-ivs-5/sweep_render.py"
      provides: "ivs 신설 스윕 드라이버 — grammar_round importlib 상속 + 관찰 래퍼 + vl.sweep() 구동"
    - path: ".planning/quick/260813-ivs-5/evidence/sweep_verdict.json"
      provides: "5동작 방출/침묵/freeze-match 기계 판정"
    - path: ".planning/quick/260813-ivs-5/evidence/sweep_cards/"
      provides: "동작별 확정 카드 PNG 실물 (운영 렌더 산출)"
    - path: ".planning/quick/260813-ivs-5/evidence/measure.json"
      provides: "display_anchor 로그 args + crop box/spec 스프레드 + draw 문법 관측 + s3 키 분류"
    - path: ".planning/quick/260813-ivs-5/STATUS.md"
      provides: "동작 x 관절 현황표 (미세조정 판정 재료)"
    - path: ".planning/quick/260813-ivs-5/EYE-VERDICT.md"
      provides: "카드 전수 육안 판정 사전 박제"
    - path: ".planning/quick/260813-ivs-5/260813-ivs-SUMMARY.md"
      provides: "보드 게시 재료 + LLM 학습 영향 + 커밋 기록"
  key_links:
    - from: ".planning/quick/260813-ivs-5/sweep_render.py"
      to: ".planning/quick/260811-xa1-mark-grammar-round-ufb-freeze-2-belle/grammar_round.py"
      via: "importlib 로드 (machine_eye 스텁·더미 키·backend sys.path 상속)"
      pattern: "grammar_round"
    - from: ".planning/quick/260813-ivs-5/sweep_render.py"
      to: "backend/functions/pipeline/app.py"
      via: "vl.sweep() -> 무패치 app._run_gated_card_inherit (운영 렌더 경로)"
      pattern: "sweep\\(\\)"
    - from: ".planning/quick/260813-ivs-5/STATUS.md"
      to: ".planning/quick/260813-ivs-5/evidence/measure.json"
      via: "비율/문법/앵커 수치 전부 관측 산출물 출처 (손 재유도 금지)"
      pattern: "measure\\.json"
---

<objective>
승인 5동작 코퍼스에 새 선 문법(골반 P3 하이브리드 + 그 외 관절 위 V + 게이트
freeze 순간 align 단일 출처 좌표 — fxx 배선 완료본)을 전체 반영한 실물 카드를
일괄 렌더하고, 동작별 방출/침묵 현황·부위/패널 비율 실측·육안 판정 사전 박제·
보드 게시 재료를 만든다.

belle 08-13 방침 (locked): "길이라던가 위치라던가는 영상별 동작별로 다를테니
전체 반영한 다음에 조정하자" — 이 사이클 = 전체 반영 실물 만들기.
**마크 튜닝·코드 수정 금지** (미세조정은 다음 라운드, belle 판정 후).

Purpose: 마크 미세조정 라운드의 판정 재료 — belle 이 5동작 실물을 놓고 길이·
위치를 조정할 수 있도록 방출 전수 + 근거 수치 + 내 사전 판정을 한 상에 올린다.
Output: 카드 PNG 실물 + sweep_verdict.json + measure.json + STATUS.md +
EYE-VERDICT.md + /Users/Shared 한글 사본 + SUMMARY 보드 재료.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/quick/260813-fxx-belle-3-p3r1-pass-v-p3-align-fps-5-pytes/260813-fxx-SUMMARY.md
@.planning/quick/260813-fxx-belle-3-p3r1-pass-v-p3-align-fps-5-pytes/verify_wiring.py
@.planning/quick/260811-ufb-freeze-only/verify_local.py

사전 확인된 사실 (플래너 실측 — 재조사 불요):
- `verify_local.sweep()` (ufb 418-553행)이 이미 승인 5동작 SWEEP_JOBS 에
  **무패치 운영 헬퍼** `app._run_gated_card_inherit` 를 돌린다: P35
  `data/{m}/doc.json + align.json` + ii0 `probes.log` freeze 정본 + ii0
  `poles.json` + S3 lazy 영상 fetch + Firestore lazy refmotion fetch.
  fxx 배선(display_anchor + HYBRID_ANGLE_SUFFIXES)이 운영 코드에 있으므로
  지금 sweep() 을 돌리면 새 문법 카드가 자동으로 나온다 — 렌더 신설 코드 0.
- `grammar_round.py` 는 import 시점에 machine_eye 스텁 + `GEMINI_API_KEY`
  더미("xa1-stub") + 인터프리터 승격 + backend sys.path 를 깐다.
  `_require_cache()` 는 `baseline()` 안에서만 호출 — import 는 캐시 무관.
  `gr._guard_ev` 는 "260811-xa1" 전제이므로 vl.EV 재지정 후 gr 의 EV-가드
  함수(baseline 등) 호출 금지 — 스텁 상속만 쓴다.
- 캐시 실측 (2026-08-13): ufb fresh 캐시(pdshapefault doc/영상) = 생존.
  `approved_sweep` 캐시 = 사망 → 스윕 영상 6편 S3 재fetch + refmotion
  Firestore 재fetch 발생. `FIREBASE_SA_PATH=/Users/kimtaesung/Dev/SunityMotion/firebase-sa.json`
  env (라운드 3 선례) + `AWS_PROFILE=sunity-motion`.
- `fault_zoom_crop` 로그 args (fault_zoom.py 3334-3340): user_side_px /
  ref_side_px / shared_frac / vertex_centered — 비율 실측의 1차 출처.
- 문법 함수: `fz._draw_hybrid_joint_angle` (1856행, hip 전용) /
  `fz._draw_joint_angle` (1765행, 기존 V) / `HYBRID_ANGLE_SUFFIXES` (1832행).
- sweep() 은 카드를 `vl.EV / "sweep_cards" / {motion}` 에 쓰고, `_S3Stub` 이
  /eye/ 키(눈 원장 스텁 산출물)도 같은 디렉터리에 섞는다 — 카드/눈 구분은
  S3 키 관측으로.
</context>

<tasks>

<task type="auto">
  <name>Task 1: ivs 스윕 드라이버 신설 + 승인 5동작 운영 렌더 실행</name>
  <files>.planning/quick/260813-ivs-5/sweep_render.py, .planning/quick/260813-ivs-5/evidence/</files>
  <action>
    `.planning/quick/260813-ivs-5/sweep_render.py` 신설 (backend/ 및 하네스
    원본 verify_wiring.py·verify_local.py·grammar_round.py 는 무수정 — 제약
    locked). verify_wiring.py 의 구조를 따르되 이번 목적(승인 5동작 렌더
    재료)에 맞게 작성한다:

    1) importlib 로 xa1 `grammar_round.py` 로드 (verify_wiring 53-63행
       `_load_module` 패턴) → machine_eye 스텁(Gemini 실호출 0)·더미 키
       (`_ensure_gemini_key` early-return, SSM 무접촉)·인터프리터 승격·
       backend sys.path 전부 상속. `vl = gr.vl` (= ufb verify_local 모듈).
    2) 재지정 (실행 전 필수): `vl.EV = <ivs>/evidence` + 자체 `_guard_ev` 로
       "260813-ivs" 포함 assert (verify_wiring 79-82행 패턴 — ufb/xa1
       evidence 파괴 금지). `vl.SPA = <현 세션 scratchpad>/approved_sweep`
       (죽은 구세션 경로 부활 금지 — 캐시는 휘발 OK, 보존은 evidence/ 리포만.
       scratchpad 경로는 이 플랜 환경의 세션 scratchpad 디렉터리 사용).
       gr 쪽 EV-가드 함수(baseline 등) 호출 금지.
    3) 관찰 래퍼 (산출 무변경 — 관찰만, verify_wiring `_ShiftObserver`
       111-158행 복제·확장을 ivs 파일 안에 신설): `fz.build_fault_zoom_comparisons`
       (criterion 스택) / `fz.shift_bake_spec` (spec0·anchor 짝) /
       `fz._side_crop` (frame shape·box) / `fz._draw_hybrid_joint_angle` 와
       `fz._draw_joint_angle` (호출 여부 = 카드별 문법 실측) /
       `vl._S3Stub.put_object` (키 기록 — "/eye/" 키 vs 카드 키 분류).
       root logger 캡처로 `display_anchor` args·`fault_zoom_crop` 라인
       (user_side_px/ref_side_px/shared_frac/vertex_centered)·
       `hybrid_fallback` 표기 수집.
    4) `vl.sweep()` 1회 구동 — 렌더는 무패치 운영 함수 호출 그대로 (하네스
       자체 그리기 0, 마크 튜닝 0, 임계 변경 0). env:
       `AWS_PROFILE=sunity-motion` + `FIREBASE_SA_PATH=<repo>/firebase-sa.json`
       (approved_sweep 캐시 사망 실측 → 영상 6편 S3 재fetch + refmotion
       Firestore 재fetch 발생. 결정론은 fxx 가 이미 2회 증명 — 이번 사이클
       재증명 불요, 1회 + freeze-match 게이트로 충분).
    5) 관측 산출물을 `evidence/measure.json` 으로 박제: displayAnchors /
       displayAnchorDrops / shifts / crops / drawCalls(카드별 hybrid·V) /
       cropLines / s3Keys(eye·card 분류) / eyeStubCalls. 카드 PNG 는
       sweep() 이 `evidence/sweep_cards/{motion}/` 에 쓴다.

    실패 처리 (무리한 추측 금지): S3/Firestore 접근 실패 또는 P35 data·ii0
    정본 재료 부재 시 — 빠진 목록을 evidence/BLOCKER.md 에 명기하고 blocker
    보고 (대체 재료 발명 금지). 게이트 미달로 침묵하는 동작은 결함이 아니라
    "정직한 침묵" — dropped 사유 그대로 기록.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && AWS_PROFILE=sunity-motion FIREBASE_SA_PATH=$PWD/firebase-sa.json python3 .planning/quick/260813-ivs-5/sweep_render.py --sweep && python3 -c "
import json,sys
r=json.load(open('.planning/quick/260813-ivs-5/evidence/sweep_verdict.json'))
assert sorted(r)==['elbow','kipup','pdshapefault','peterpan','powerspin'], sorted(r)
assert all(not m['freezeMatchViolations'] for m in r.values()), 'freeze 위반'
m=json.load(open('.planning/quick/260813-ivs-5/evidence/measure.json'))
assert m.get('eyeStubCalls',-1)>=0 and not m.get('displayAnchorDrops'), 'stub/drop'
print('SWEEP-VERIFY PASS')" && git diff --stat --exit-code backend/ .planning/quick/260813-fxx-belle-3-p3r1-pass-v-p3-align-fps-5-pytes/verify_wiring.py .planning/quick/260811-ufb-freeze-only/verify_local.py .planning/quick/260811-xa1-mark-grammar-round-ufb-freeze-2-belle/grammar_round.py</automated>
  </verify>
  <done>승인 5동작 전부 운영 경로 스윕 완료 — sweep_verdict.json 5동작 + freeze-match 위반 0 + 방출 카드 PNG 실물(sweep_cards/) + measure.json(앵커·crop·문법·키 분류) 존재, Gemini 실호출 0(스텁 calls 만), backend/·하네스 원본 diff 0.</done>
</task>

<task type="auto">
  <name>Task 2: 현황표 + 육안 판정 사전 박제 (frames-before-numbers)</name>
  <files>.planning/quick/260813-ivs-5/STATUS.md, .planning/quick/260813-ivs-5/EYE-VERDICT.md</files>
  <action>
    코드 실행 없음 — Task 1 산출물만 출처로 문서 2건 작성 (수치 손 재유도·
    발명 금지, 전부 sweep_verdict.json / measure.json / probes.log 정본 인용).

    STATUS.md — 동작 x 관절(rid) 전수 표:
    - 방출/침묵: survivors 는 카드 파일명과 함께, dropped 는 사유 문자열
      그대로 ("정직한 침묵 — 방출 0 = 결함 아님" 명기).
    - 마크 문법: drawCalls 실측으로 hip=P3 하이브리드 / 기타=V 표기,
      `hybrid_fallback` 관측 시 그대로 표기 (접미사 규칙 추정이 아니라 호출
      실측이 출처).
    - freeze 초: survivors @u/r 값 (probes.log 정본과 일치 — Task 1 게이트가
      이미 증명).
    - 부위/패널 비율 실측 (마크 크기 체감의 근거 수치 — 미세조정 판정 재료):
      패널별 crop side px(fault_zoom_crop args)·frame dims(crops 관측)·
      spec 3점 스프레드 px(shifts 관측)로 마크/패널 % 와 크롭/원본 % 를 계산.
      계산식을 표 하단에 1줄 명기 (재현 가능하게).
    - 각도 수치 미노출 관례: 표·문서에 도(degree) 수치 금지 — 사이각 문제는
      "저각(선 하나로 읽힘)" 같은 범주 표현만.

    EYE-VERDICT.md — 방출 카드 PNG **전부**를 Read 도구로 실제 열어 (몽타주/
    축소본 검수 금지, 카드/눈 원장 구분은 measure.json s3Keys 분류 사용)
    카드별 사전 박제:
    - 마크가 관절 위에 앉았는가 (align 단일 출처 좌표 실물 확인)
    - 얼굴/머리/폴 관통·가림 여부
    - V 저사이각으로 선 하나로 읽히는 케이스
    - belle 이 지적할 만한 "길이·위치 어색" 케이스 — 내 판정을 먼저 기록
      (frames-before-numbers 게이트: 근거 프레임 눈 확인 후에만 제시).
    문제를 발견해도 수정 금지 — 다음 미세조정 라운드 판정 재료로만 박제
    (belle 08-13 방침 locked). 기결론 재질문 금지: user 패널 V 가닥이 역립
    얼굴 위를 지나는 것은 fxx 에서 belle 판정으로 현행 유지가 스펙 — 신규
    쟁점이 아니라 기존 판정 인용으로만 표기.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/.planning/quick/260813-ivs-5 && python3 -c "
import json,re,pathlib
sv=json.load(open('evidence/sweep_verdict.json'))
m=json.load(open('evidence/measure.json'))
st=pathlib.Path('STATUS.md').read_text(); ey=pathlib.Path('EYE-VERDICT.md').read_text()
for mo in ['elbow','kipup','pdshapefault','peterpan','powerspin']: assert mo in st, mo
n_cards=len([k for k in m['s3Keys'] if '/eye/' not in k and k.endswith('.png')])
n_eye=len(re.findall(r'^#{2,3} .*카드', ey, flags=re.M))
assert n_eye>=n_cards>0, f'육안 {n_eye} < 카드 {n_cards}'
assert not re.search(r'\d+\s*도[^달]', st+ey), '각도 수치 노출'
print(f'DOCS PASS cards={n_cards} eye={n_eye}')"</automated>
  </verify>
  <done>STATUS.md 에 5동작 x 관절 전수 행(방출/침묵·문법 실측·freeze 초·비율 수치·계산식) + EYE-VERDICT.md 에 방출 카드 전수 육안 판정(관통/가림/저각/길이·위치 사전 박제) 존재, 도 수치 0.</done>
</task>

<task type="auto">
  <name>Task 3: /Users/Shared 한글 사본 + SUMMARY 보드 재료 + 커밋</name>
  <files>/Users/Shared/sunity-sweep-260813/, .planning/quick/260813-ivs-5/260813-ivs-SUMMARY.md</files>
  <action>
    1) `/Users/Shared/sunity-sweep-260813/` 생성 후 방출 카드 PNG 전부를
       한글 파일명으로 복사 — `{동작한글}_{관절한글}_u{초}s.png` 형식
       (예: `피디쉐입_왼골반_u16.7s.png`). 동작한글 매핑: elbow=엘보트위스트,
       kipup=킵업, pdshapefault=피디쉐입, peterpan=피터팬, powerspin=파워스핀.
       눈 원장 스텁 산출물은 복사하지 않는다 (카드만 — measure.json s3Keys
       분류 기준).
    2) `260813-ivs-SUMMARY.md` 작성 (quick summary 템플릿):
       - 한 줄 요약 + 동작별 방출/침묵 집계 (emitted/silenced 수)
       - 보드 게시 재료 절: 카드별 [이미지 절대경로(/Users/Shared 사본),
         캡션(동작·관절·freeze 초·문법 — 각도 수치 금지, 이모지 금지)] 목록
         — 게시는 오케스트레이터 몫, 이 사이클은 재료까지만.
       - STATUS/EYE-VERDICT 요지 + 내가 사전 박제한 어색 케이스 목록
       - LLM 학습 영향 절 (필수): Gemini 실호출 0 — machine_eye 스텁,
         학습 전송 0, 눈 원장 신규 적재 0 (스텁 산출물은 evidence 한정)
       - 한계 박제: 마크 튜닝·코드 수정 0 (belle 방침), 침묵 동작 = 정직한
         침묵, Pod 실증은 이 사이클 범위 밖
    3) 커밋: `gsd-sdk query commit "docs(quick-260813-ivs): 승인 5동작 새 문법 스윕 렌더 + 현황표 + 육안 박제" --files .planning/quick/260813-ivs-5`
       (/Users/Shared 는 리포 밖 — 커밋 대상 아님. evidence PNG 는 ufb/fxx
       선례대로 커밋 대상, 휘발 scratchpad 캐시는 커밋 금지).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && python3 -c "
import json,pathlib
m=json.load(open('.planning/quick/260813-ivs-5/evidence/measure.json'))
n_cards=len([k for k in m['s3Keys'] if '/eye/' not in k and k.endswith('.png')])
shared=list(pathlib.Path('/Users/Shared/sunity-sweep-260813').glob('*.png'))
assert len(shared)==n_cards>0, f'{len(shared)} != {n_cards}'
s=pathlib.Path('.planning/quick/260813-ivs-5/260813-ivs-SUMMARY.md').read_text()
assert '/Users/Shared/sunity-sweep-260813' in s and 'LLM 학습' in s
print(f'SHARE PASS {len(shared)} cards')" && git log --oneline -1 | grep -q "quick-260813-ivs"</automated>
  </verify>
  <done>/Users/Shared/sunity-sweep-260813/ 한글 사본 수 == 방출 카드 수, SUMMARY 에 보드 게시 재료(절대경로+캡션)·LLM 학습 영향·한계 박제 존재, ivs 디렉터리 커밋 완료.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| 로컬 드라이버 -> S3/Firestore | 승인 코퍼스 영상·refmotion 읽기 (읽기 전용 자격) |
| 로컬 드라이버 -> Gemini | 경계 자체를 스텁으로 차단 (실호출 0) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-ivs-01 | Information Disclosure | AWS/Firebase 자격 | mitigate | env 주입만, 키 값 로그·커밋 금지 (verify_local T-ufb-01 선례), firebase-sa.json 은 기존 리포 위치 참조만 |
| T-ivs-02 | Tampering | ufb/xa1 evidence | mitigate | vl.EV 재지정 + "260813-ivs" assert 가드 (실행 전 필수) — 타 사이클 evidence 파괴 fail-closed |
| T-ivs-03 | Spoofing | Gemini 호출 | mitigate | grammar_round machine_eye 스텁 + 더미 키 상속 — 네트워크 자체 차단, eyeStubCalls 로 기계 확인 |
| T-ivs-SC | Tampering | 패키지 설치 | accept | 신규 설치 0 (기존 backend venv/의존만 사용) |
</threat_model>

<verification>
- `sweep_render.py --sweep` exit 0, sweep_verdict.json = 5동작 전수 +
  freezeMatchViolations 전부 빈 배열 (순간 발명 0).
- Gemini 실호출 0: eyeStubCalls 기록 + SSM 키 주입 코드 경로 미진입
  (더미 키 상속).
- `git diff --stat backend/` + 하네스 원본 3파일 = 빈 출력 (코드 수정 0).
- STATUS.md / EYE-VERDICT.md / SUMMARY 자동 게이트 (Task 2·3 verify) PASS.
- 카드 전수 Read 육안 — 관통/가림/저각/길이·위치 사전 박제 완료.
</verification>

<success_criteria>
- 승인 5동작 각각: 새 문법 확정 카드 실물 렌더 또는 "정직한 침묵" 현황표 명기.
- 현황표: 동작 x 관절 — 방출/침묵, 문법(하이브리드/V 실측), freeze 초,
  부위/패널 비율 실측 수치 (미세조정 판정 재료).
- 육안 판정 기록: 카드 전부 Read 로 열어 자평 사전 박제 (belle 지적 예상
  케이스 포함).
- /Users/Shared/sunity-sweep-260813/ 한글 사본 + SUMMARY 보드 게시 재료
  (게시는 오케스트레이터).
- Gemini 실호출 0, 코드 수정 0, 커밋 완료.
</success_criteria>

<output>
Create `.planning/quick/260813-ivs-5/260813-ivs-SUMMARY.md` when done (Task 3 산출물이 곧 SUMMARY).
</output>

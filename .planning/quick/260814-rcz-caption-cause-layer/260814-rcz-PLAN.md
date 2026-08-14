---
phase: quick-260814-rcz
quick_id: 260814-rcz
slug: caption-cause-layer
date: 2026-08-14
status: planned
description: 캡션 원인 절 배선 + 각도 표기 적용 조건 — belle 08-14 발굴 판정("발굴은 성립, 설명이 미달")의 처방. 캡션을 증상+원인+행동 3절로 확장(원인 없으면 기존 2문장 byte-동일), 음성=자막 lockstep 을 양엔진 실행으로 증명, 각도 V 마크를 그릴지 말지의 조건을 실측 후 결정. 승인 카드 무회귀 1급.
wave: 1
depends_on: []
type: execute
plan: 01
autonomous: true
requirements: [BELLE-PD-CAPTION, BELLE-PS-MARKCOND]
files_modified:
  - backend/shared/python/sunity_shared/analysis/cue_text.py
  - backend/shared/python/sunity_shared/analysis/phrasebook.py
  - backend/shared/python/sunity_shared/models.py
  - backend/data/phrasebook.json
  - backend/shared/python/sunity_shared/analysis/fault_zoom.py
  - app/src/lib/deductionSheet.ts
  - app/src/types/analysis.ts
  - docs/contract.md
  - backend/tests/test_caption_cause_layer.py
  - backend/tests/test_fault_zoom_angle_admissible.py
  - backend/tests/phase32/compose_cue_probe.mjs
  - backend/tests/phase32/test_mission_contract_lockstep.py
  - .planning/quick/260814-rcz-caption-cause-layer/mark_gate_sweep.py
  - .planning/quick/260814-rcz-caption-cause-layer/candidate_render.py
  - .planning/quick/260814-rcz-caption-cause-layer/MEASURE.md
  - .planning/quick/260814-rcz-caption-cause-layer/CAPTION-SHEET.md
  - .planning/quick/260814-rcz-caption-cause-layer/evidence/
  - .planning/quick/260814-rcz-caption-cause-layer/260814-rcz-SUMMARY.md

must_haves:
  truths:
    - "캡션이 3절(증상 statusLine → 원인 causeLine → 행동 actionLine)로 조립되고, causeLine 이 없는 record 는 오늘과 **문자 단위 동일**한 2문장을 낸다 — 무회귀 1급"
    - "음성(cue_text.coach_audio_speech_text)과 앱 자막(composeCueSubtitleKo)이 같은 fixture 에서 **양엔진 실행 비교로** 문자 단위 동일함이 증명된다 (소스 눈대조 아님 — node 로 TS 를 실제 실행한 로그가 증인)"
    - "원인 문구는 승인 문구집(phrasebook.json)이 소유한다 — LLM 생성 경로 0 (D-11 골격 소유 원칙). 시드는 belle 08-14 원문 2건의 전사이며 새 사실 발명 0"
    - "원인 문구는 전부 가설 어투('~일 수 있어요'/'~로 보여요')이고 수치·각도·퍼센트·단정 0 — 측정 안 된 원인을 측정된 것처럼 말하지 않는다(1급 불변식). 기존 금지어 게이트가 자동으로 이 문구를 스캔한다"
    - "새 캡션이 **구운 자막 3줄 상한**(compare_render.py:1661 `wrap_text(...)[:3]`)을 넘지 않음이 운영 폰트·폭으로 실측된다 — 넘으면 행동절이 조용히 잘려 08-01 반려가 재발한다"
    - "각도 V 마크의 적용 조건은 **먼저 재고 나서** 정한다 — 승인 V 카드 전건 + belle 채택 후보(cand17B) + belle 반려 후보(cand01E)의 px 사이각을 실측표로 박제한 뒤 임계를 고른다. 어떤 축도 갈리지 않으면 임계를 지어내지 않고 '축 미발견 — 선언 억제'로 정직 보고한다 (curve-fit 금지, 표본 1 명기)"
    - "마크 조건 미충족 시 V 만 억제되고 기존 원 마커 폴백으로 떨어진다 — 새 표면 발명 0. 사이각이 계산 불가면 fail-open(오늘 그대로 그림) — 무회귀 우선"
    - "승인 카드 무회귀 = 패치 전/후 승인 5동작 스윕 카드 md5 **전건 동일** + belle 채택 후보 카드(cand17B) md5 동일. 변하는 것은 belle 이 반려한 cand01E 한 장뿐이고 그 변화는 V 소멸로 육안 확인된다"
    - "belle 비교 재료 = 2건의 구/신 캡션 원문 대조 + 카드 실물 + 판정란. 실행자는 카드 PNG 를 Read 로 직접 열어 확인한 뒤에만 게재한다 (frames-before-numbers)"
    - "제약 준수 — 채점 산식 5파일(deduction_engine/dimensions/kismam/motiondtw/assemble) diff 0, pytest 기준선 무회귀(59 failed 동일), app typecheck PASS, S3 read-only(업로드 0), Firestore 읽기만(쓰기 0), Pod 무접촉, Gemini 실호출 0, 이모지 0"
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/cue_text.py"
      provides: "3절 캡션 조립 단일 출처 — causeLine 선택 절 삽입 + 문장 경계 규칙"
      contains: "causeLine"
    - path: "app/src/lib/deductionSheet.ts"
      provides: "앱 자막 조립 lockstep 미러 (composeCueSubtitleKo)"
      contains: "causeLine"
    - path: "backend/data/phrasebook.json"
      provides: "원인 문구 시드 2건 (ref-pdshape.angle_vs_reference__left_elbow / ref-power-spin.angle_vs_reference__left_shoulder)"
      contains: "causeLine"
    - path: "backend/shared/python/sunity_shared/analysis/fault_zoom.py"
      provides: "각도 V 마크 적용 조건 게이트 (순수 함수 + 드로잉 진입점 배선, fail-open)"
    - path: "backend/tests/test_caption_cause_layer.py"
      provides: "3절 조립 계약 + 무회귀 + 양엔진 lockstep + 자막 3줄 실측 + 가설 어투/무수치 게이트"
    - path: "backend/tests/phase32/compose_cue_probe.mjs"
      provides: "node 로 deductionSheet.ts 를 직접 실행해 fixture 캡션을 stdout JSON 으로 내는 프로브 (양엔진 비교의 TS 측)"
    - path: ".planning/quick/260814-rcz-caption-cause-layer/MEASURE.md"
      provides: "마크 조건 실측표 (승인 V 카드 + 후보 2건 × 축 A1~A6) + 채택/기각 판정 + 표본 한계 박제"
    - path: ".planning/quick/260814-rcz-caption-cause-layer/CAPTION-SHEET.md"
      provides: "belle 판정 재료 — 구/신 캡션 대조 2건, 카드 실물 대조, 판정란(선기입 금지)"
  key_links:
    - from: "backend/shared/python/sunity_shared/analysis/cue_text.py"
      to: "app/src/lib/deductionSheet.ts"
      via: "양엔진 fixture 실행 비교 (node 프로브)"
      pattern: "compose_cue_probe"
    - from: "backend/data/phrasebook.json"
      to: "backend/functions/pipeline/app.py `_attach_translation_emission`"
      via: "models.DEDUCTION_PHRASE_KEYS 병합 루프"
      pattern: "DEDUCTION_PHRASE_KEYS"
    - from: "backend/shared/python/sunity_shared/analysis/fault_zoom.py"
      to: ".planning/quick/260814-rcz-caption-cause-layer/mark_gate_sweep.py"
      via: "승인 5동작 스윕 카드 md5 전/후 대조"
      pattern: "sweep_verdict"
---

<objective>
belle 08-14 발굴 판정의 처방 두 가지를 배선한다.

판정 원문(요지): 두 발굴 모두 **결함 성립은 인정**됐고("두 부분다 이유있게 잡은건
확실하구만 좋네"), 미달은 **설명 층**이다 — (1) pdshapefault 왼팔꿈치는 "앞뒤로
설명이 필요… 캡션이 중요", (2) powerspin 왼어깨는 "각도 표기가 필요한 부분인진
모르겠음… 잘한 영상쪽 각도가 좀 애매해".

Purpose: 지금 캡션은 `statusLine`(증상) + 행동절 **2문장 고정**이라 원인이 들어갈
자리가 구조적으로 없다. 원인 사슬 기계(coach_writer `rootCauseHypotheses`)는
있지만 분석 전체 수준이라 record 에 귀속되지 않고 카드까지 오지도 않는다. 이번
사이클은 **자리를 만들고, 승인 문구로 채우고, 마크를 그릴지 말지의 조건을 실측으로
정하는 것**까지다.

★이번 사이클의 성격 명기: belle 이 말한 원인(회전력·올라오는 타이밍)은 **현
데이터로 측정 불가**다(오케스트레이터 실측: 어깨폭 회전 위상은 1초 평활 후에도
부호전환 13~22회 = keypoint 잡음, "손 뻗어 잡는 시점"은 두 클립 모두 첫 프레임부터
손이 폴에 있어 진입 구간 부재). 그러므로 이 작업은 "측정해서 근거로 대기"가 아니라
**"코칭 지식을 가설 어투로 담기"** 다. 측정 안 된 것을 측정된 것처럼 쓰면 이
프로젝트의 1급 불변식 위반이다 — 수치 0, 단정 0, 가설 어미만.

Output: 3절 캡션 조립(무회귀 폴백 포함) · 원인 문구 시드 2건 · 양엔진 lockstep
실행 증거 · 마크 적용 조건 실측표와 게이트 · 승인 무회귀 md5 증명 · belle 비교 재료.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md

판정 원문 (이번 요구의 출처):
@.planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md  ← §"belle 판정 기입란"(197~215행) + 총평. 인용 시 이 표의 원문을 그대로 쓸 것

캡션 조립 (이번 수정 대상 — 두 파일은 **문자 단위 동일**이 계약):
@backend/shared/python/sunity_shared/analysis/cue_text.py
@app/src/lib/deductionSheet.ts  ← `splitGoalClause`(375행) / `composeCueSubtitleKo`(418행)

문구 소유 구조 (원인 절의 출처가 여기여야 하는 이유 = D-11):
@backend/shared/python/sunity_shared/analysis/phrasebook.py  ← `_ENTRY_SLOTS`(42행) / `assemble_phrases`(118행) / `rendered_copy_strings`(246행)
@backend/shared/python/sunity_shared/analysis/coach_writer.py  ← `_SYSTEM` "가변부 슬롯 한정 — 문구집 골격 보호" 절. **LLM 은 골격을 만들지 않는다**

계약 lockstep 4곳 (하나라도 빠지면 테스트가 잡는다):
@backend/shared/python/sunity_shared/models.py  ← `DEDUCTION_PHRASE_KEYS`(275행)
@app/src/types/analysis.ts  ← `DeductionRecord`(781~786행)
@docs/contract.md  ← §12.3 (1961~1966행)
@backend/tests/phase32/test_mission_contract_lockstep.py  ← 51/76~79행이 tuple 을 정확히 핀

마크 드로잉 게이트 (각도 표기 조건이 들어갈 자리):
@backend/shared/python/sunity_shared/analysis/fault_zoom.py  ← 3508~3631행 각도 베이크 블록(`angle_reason` 사슬 / `_spec_inner_deg_px`(2094행) / `HYBRID_ANGLE_SUFFIXES`(1833행) / both-or-neither copy-then-commit)

재사용 하네스 (사본만 만들고 원본 무수정):
@.planning/quick/260813-nh4-2-b-ref-v-pdshape-pair-override-pod/verify_port.py  ← 승인 5동작 운영 카드 스윕(현 HEAD 정본, 카드 md5 게이트)
@.planning/quick/260814-ehz-5/discover_sweep.py  ← 후보 렌더 경로(`app._run_gated_card_inherit`), 후보 좌표는 evidence/{motion}/candidates.json
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 캡션 원인 절 자리 신설 + 승인 문구 시드 2건 + 양엔진 lockstep</name>
  <files>backend/shared/python/sunity_shared/analysis/cue_text.py, app/src/lib/deductionSheet.ts, backend/shared/python/sunity_shared/analysis/phrasebook.py, backend/shared/python/sunity_shared/models.py, backend/data/phrasebook.json, app/src/types/analysis.ts, docs/contract.md, backend/tests/phase32/test_mission_contract_lockstep.py, backend/tests/test_caption_cause_layer.py, backend/tests/phase32/compose_cue_probe.mjs</files>

  <behavior>
    - T1: causeLine 부재 → 오늘과 문자 단위 동일 (status + ". " + action). 이 케이스가 무회귀 1급.
    - T2: causeLine 있음 → status + ". " + cause + ". " + action (3절, 순서 고정 증상→원인→행동).
    - T3: causeLine 이 이미 문장부호(.!?)로 끝나면 마침표 중복 0 (statusLine 과 같은 규칙).
    - T4: statusLine 부재 + causeLine 있음 → cause + ". " + action.
    - T5: causeLine 이 빈 문자열/비문자열/None → 기존 2문장 경로 (fail-closed, 조립에 끼어들지 않음).
    - T6: 양엔진 동일 — 같은 fixture 행 전건에서 python 산출 == node 로 실행한 TS 산출 (문자 단위).
    - T7: 시드 문구 2건이 가설 어미로 끝나고 숫자/도/%/단정 어미가 0이며 기존 금지어 게이트를 통과.
    - T8: 시드 2건이 붙은 캡션이 운영 폰트·폭에서 `wrap_text(...)` 3줄 이내.
  </behavior>

  <action>
    **① 캡션 조립 3절화 (backend).** `cue_text.coach_audio_speech_text(rec)` 에 선택적
    원인 절을 넣는다. 규칙 = `statusLine` → `causeLine` → `goal_clause_action_line(cueLine)`
    순서로 이어 붙이고, 각 절 사이는 **문장 경계(마침표 + 공백 한 칸)**. 이미 `.!?` 로
    끝나는 절은 마침표를 중복하지 않는다(현행 status 규칙을 절 공용 헬퍼로 승격 —
    분기 복제 금지). `causeLine` 이 str 이 아니거나 빈 문자열이면 **아예 없는 것처럼**
    동작해 오늘 산출과 byte-동일해야 한다. Polly run-on 방지 규칙(belle 08-07 반려)이
    새 절 경계에도 그대로 적용됨을 docstring 에 명기.

    **② 앱 자막 lockstep (app).** `composeCueSubtitleKo` 를 같은 규칙으로 갱신한다 —
    `record.causeLine` 을 읽고 동일 순서·동일 구분자·동일 fail-closed. 기존 docstring 의
    "Python lockstep" 절에 원인 절도 함께 바꿔야 한다는 문장을 추가. **앱 카드 UI 는
    무변경** — causeLine 은 자막 조립에서만 소비되고 3단 카드(statusLine/whyLine/cueLine)
    렌더에는 손대지 않는다. (`result.tsx` 2013행 호출부 시그니처 변경 0.)

    **③ 원인 문구의 출처 = 승인 문구집 (설계 결정, 근거 명기).** `causeLine` 을
    phrasebook 슬롯으로 신설한다: `phrasebook._ENTRY_SLOTS` + `models.DEDUCTION_PHRASE_KEYS`
    끝에 `"causeLine"` 추가 → `_attach_translation_emission`(app.py 6437행) 의 기존
    병합 루프가 **코드 변경 없이** record 에 각인한다(값이 str 이고 비어있지 않을 때만).
    LLM 생성 경로를 쓰지 않는 이유를 cue_text/phrasebook docstring 에 1줄 박제: 카드 3단
    골격은 문구집이 소유하고 LLM 은 가변부만 소유한다(D-11) — 음성·자막은 가장 하중이
    큰 표면이라 골격 소유 원칙이 여기서 완화될 수 없다. `rootCauseHypotheses`(분석 전체
    수준, record 미귀속) 재활용은 이번 스코프 밖으로 두고 SUMMARY 에 이월 사유를 적는다.

    **④ 계약 lockstep 4곳 동시 갱신.** `app/src/types/analysis.ts` DeductionRecord 에
    `causeLine?: string;` (주석: 원인 가설 1줄 — 측정 아님, 자막 조립 전용) ·
    `docs/contract.md` §12.3 3단 문구 슬롯 문장에 causeLine 추가(가설 어투·무수치·
    부재 허용 명기) · `backend/tests/phase32/test_mission_contract_lockstep.py` 의 tuple
    핀(51행) 갱신. `test_deduction_engine.test_contract_lockstep` 이 TS 인터페이스 필드
    집합과 4-set 합집합 동등을 강제하므로 한 곳만 빠져도 실패한다 — 이것이 배선 증인.

    **⑤ 시드 2건만 (belle 원문 전사, 새 사실 발명 0).** `backend/data/phrasebook.json` 의
    **이미 존재하는** 두 entry 에 `causeLine` 키만 추가한다 (신규 entry 생성 금지 —
    `assemble_phrases` 는 entry 단위 매칭이라 골격 없는 신규 entry 를 만들면 statusLine/
    cueLine 이 통째로 사라진다):
      · `ref-pdshape.angle_vs_reference__left_elbow` ← belle: "회전력, 올라오는 타이밍이
        좀 더 돌고 올려와야 팔을 뻗어 편하게 올라왔는데 좀 빠르게 손을 뻗어 잡아서 이런
        현상이 발생되기도 하고, 회전력이 좀 약한 이유일 수 있음". 예: "조금 더 돌고
        올라와야 팔을 편하게 뻗는데, 회전이 덜 된 상태에서 손을 먼저 뻗어 잡아 생긴
        모습일 수 있어요"
      · `ref-power-spin.angle_vs_reference__left_shoulder` ← belle: "안정적인 위치를
        만들기위해 기준 영상은 팔을 굽혀 더 들어올린 거긴하지". 예: "기준 영상은 시작에서
        힘을 실어 높은 지점에서 돌려고 팔을 굽혀 더 끌어올린 것으로 보여요"
    두 문장 다 belle 원문의 전사이며 **가설 어미**로 끝나야 한다. 수치·각도·퍼센트·
    "~때문입니다" 류 단정 금지. 다른 65개 entry 는 손대지 않는다(= 그 record 들의 캡션은
    byte-동일). ★동작 키는 doc 의 `motionId` 정본을 열어 확인하고 쓸 것 — 발굴 시트의
    표기(pdshapefault/powerspin)는 하네스 마운트 이름이고 문구집 키는 `ref-pdshape`/
    `ref-power-spin` 이다. `_meta` 에 출처(belle 2026-08-14 판정 원문, quick-260814-rcz)를
    기록한다. 기존 금지어 게이트(`rendered_copy_strings` → `test_phrasebook_forbidden`)가
    entries 전체를 재귀 수집하므로 새 문구도 자동으로 스캔된다 — 별도 게이트 신설 불요.

    **⑥ 양엔진 lockstep 프로브.** `backend/tests/phase32/compose_cue_probe.mjs` 를
    만든다: stdin 으로 record dict 배열(JSON)을 받아 `app/src/lib/deductionSheet.ts` 의
    `composeCueSubtitleKo` 를 호출하고 결과 배열을 **stdout 에 JSON 한 줄**로 출력.
    Node 24 는 확장자 명시 import 로 TS 를 그대로 실행한다(실측 확인됨 — MODULE_TYPELESS
    경고는 stderr 로 나가므로 stdout 만 파싱할 것).

    **⑦ 테스트 (backend/tests/test_caption_cause_layer.py).** behavior T1~T8 을 덮는다.
    T6 은 fixture 행(무-cause / 정상 3절 / 문장부호 중복 / status 부재 / 빈 cause /
    시드 2건 실제 문구)을 **python 이 단일 소유**하고, 같은 배열을 프로브에 파이프해
    산출을 문자 비교. node 부재 환경은 skipif 하되 **이번 실행에서는 skip 이 아니라
    실제 통과해야 한다**(SUMMARY 에 실행 로그 인용). T8 은 `compare_render` 자막 블록
    (1661행)이 쓰는 font/W/pad 계산을 그대로 불러 `wrap_text(...)` 줄수를 재고 3 이하를
    단언 — `[:3]` 이 4번째 줄을 조용히 버려 행동절이 사라지는 경로를 막는다. 3줄을
    넘으면 문구를 belle 원문 의미 안에서 줄이고, 줄인 사실과 최종 문자수를 MEASURE.md 에
    기록한다(의미 축소·"일단 v1" 금지).

    금지: LLM 로 원인 문장 생성, `whyLine` 재활용(그건 감점 이유 = 심사 언어이지 원인이
    아니다), 신규 phrasebook entry 생성, 앱 카드 UI 변경, 채점 산식 5파일 접촉.
  </action>

  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests/test_caption_cause_layer.py backend/tests/phase32/test_coach_audio.py backend/tests/phase32/test_mission_contract_lockstep.py backend/tests/phase32/test_phrasebook_assembly.py backend/tests/phase32/test_phrasebook_forbidden.py backend/tests/test_deduction_engine.py backend/tests/test_phrasebook_cause_grouping.py 2>&1 | tail -20 && cd app && npm run typecheck</automated>
  </verify>

  <done>새 테스트 전건 PASS(양엔진 비교 테스트가 skip 아님) · 기존 캡션 계약 테스트 무회귀 · typecheck PASS · causeLine 없는 record 의 조립 산출이 오늘과 문자 단위 동일함이 테스트로 단언됨 · 시드는 정확히 2건이고 둘 다 가설 어미 + 무수치 · 자막 3줄 실측 기록됨.</done>
</task>

<task type="auto">
  <name>Task 2: 각도 표기 적용 조건 — 실측 먼저 (운영 코드 diff 0)</name>
  <files>.planning/quick/260814-rcz-caption-cause-layer/mark_gate_sweep.py, .planning/quick/260814-rcz-caption-cause-layer/candidate_render.py, .planning/quick/260814-rcz-caption-cause-layer/MEASURE.md, .planning/quick/260814-rcz-caption-cause-layer/evidence/</files>

  <action>
    이 Task 는 **재는 것만** 한다 — `backend/` diff 0 으로 끝나야 하고, 임계는 이 Task
    끝에서 MEASURE.md 에 박제된 뒤 Task 3 에서 구현된다. (이 프로젝트 규칙: 권장은 재고
    나서. 안 쟀으면 "권장 없음, 이걸 재야 답이 나온다"고 적는다.)

    **① 하네스 사본 2개 (원본 무수정).**
      · `mark_gate_sweep.py` = nh4 `verify_port.py` 사본. 승인 5동작 운영 카드를
        `app._run_gated_card_inherit` 그대로 렌더하고 카드 md5 를 기록하는 현 HEAD
        정본이다. 여기에 **관찰 필드만** 추가: 카드별 `criterion` / V 드로잉 여부 /
        user·ref 패널 **px 사이각**(운영 `_spec_inner_deg_px` 를 그대로 호출 — 새 산식
        발명 0, 실제로 그려지는 spec·box 로 계산) / `deficitDeg` / `tolerance` /
        `angle_reason` 로그 라인. 하네스가 직접 그리거나 임계를 만드는 일 0.
      · `candidate_render.py` = ehz `discover_sweep.py` 사본을 **render-only** 로 축약.
        `evidence/{motion}/candidates.json` 에 기록된 후보 좌표를 그대로 읽어
        `--fetch` 로 소스만 마운트한 뒤 렌더한다 — **스캔·기계 눈 재실행 금지**
        (Gemini 실호출 0 이 이 사이클의 제약). 대상은 정확히 2건: pdshapefault
        cand17B(u16.47/r15.13) · powerspin cand01E(u0.47/r0.73). 같은 관찰 필드를 기록.
      · 경로 재지정 필수: evidence 는 이 quick 디렉터리 아래, 캐시는 현 세션 scratchpad.
        남의 evidence 를 덮어쓰면 안 된다(nh4/ehz 원본 보존).
      · 소스 정본: P35 `.planning/phases/35-server-rendered-comparison-video/data/{motion}/`
        (doc.json/align.json) + ii0 `sweep_out/poles.json` + S3 영상(read-only) +
        Firestore refmotion(읽기만). 소스 부재로 재현 불가한 동작이 있으면 지어내지 말고
        BLOCKER 로 명기하고 그 동작을 표에서 "측정 불가"로 남긴다.

    **② 자기검증(하네스가 옳다는 증거를 먼저).** 패치 없는 HEAD 에서 돌린 결과가 기존
    정본과 일치해야 측정값을 믿을 수 있다: 승인 스윕 카드 md5 == nh4 `evidence/
    sweep_verdict_port.json` 계열 정본, cand17B 카드 md5 == ehz 채택 카드
    `e891e7ae...` 계열 정본(ehz evidence 의 해당 md5). 불일치하면 원인을 실측해 적고,
    측정을 밀어붙이지 말 것.

    **③ 실측표 (MEASURE.md).** 행 = V 가 실제로 그려지는 승인 카드 전건 + cand17B +
    cand01E. 열 = A1 ref 패널 사이각 / A2 user 패널 사이각 / A3 |A1−A2| 양측 대조 /
    A4 각 측의 직선 근접도 min(inner, 180−inner) / A5 deficitDeg 및 tolerance 대비 /
    A6 대조 방향(학생·기준 중 어느 쪽이 더 굽었는가 — belle 이 "방향 반대"라 지적한 축).
    ★참고 실측: 08-13 ivs 시점엔 V 가 실제로 그려진 승인 카드가 2장뿐이었고(pdshape
    오른팔꿈치·피터팬 왼어깨) nh4 의 B 스펙 이식 뒤 카드가 8→10 으로 늘었다 — 현재 V
    보유 카드 집합은 **이번 실행 로그로 확정**할 것(과거 숫자 인용 금지).

    **④ 판정 규칙 (표를 보기 전에 MEASURE.md 에 먼저 적고, 그 다음 채우기).**
      · 통과 집합 P = belle 이 통과시킨 V 카드 전건 ∪ {cand17B}. 반려 집합 N = {cand01E}.
      · 어떤 축에서 P 전건이 한쪽에, N 이 반대쪽에 떨어지고 그 분리 마진이 P 관측 산포의
        20% 이상이면 그 축을 채택하고 임계를 마진 중앙에 둔다.
      · 갈리지 않으면 **임계를 지어내지 않는다**. "측정 축 미발견"으로 적고 대안 =
        (motionId, criterion) 선언 억제 표(reference_anchor_overrides 선례의 데이터
        선언 — 코드 분기 0)를 Task 3 안으로 제시한다. 이것은 실패가 아니라 정직한 결과다.
      · 채택하든 선언하든 **N 의 표본이 1건**임을 표 아래에 박제한다 — 과적합 위험을
        belle 이 보고 판정할 수 있어야 한다.

    금지: 운영 코드 수정(이 Task 는 `git status --porcelain backend/ app/` 이 비어야
    한다), 임계 튜닝을 통과할 때까지 반복, 후보 좌표 재탐색(발굴은 이미 끝났다),
    Gemini 실호출, S3 업로드, Firestore 쓰기, Pod 접촉.
  </action>

  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && test -s .planning/quick/260814-rcz-caption-cause-layer/MEASURE.md && python3 -c "
import pathlib,sys
m=pathlib.Path('.planning/quick/260814-rcz-caption-cause-layer/MEASURE.md').read_text(encoding='utf-8')
need=['A1','A2','A3','A4','A5','A6','cand17B','cand01E','표본','판정 규칙']
miss=[t for t in need if t not in m]
print('MISSING',miss); sys.exit(1 if miss else 0)" && git status --porcelain backend/ app/ | tee /dev/stderr | grep -q . && echo "FAIL: 운영 코드 변경됨" && exit 1 || echo "OK: 운영 코드 diff 0"</automated>
  </verify>

  <done>승인 스윕과 후보 2건이 HEAD 에서 재현(자기검증 md5 일치) · 실측표가 축 A1~A6 전건 채워짐 · 판정 규칙이 표보다 먼저 기록됨 · 채택 축과 임계(또는 "축 미발견 — 선언 억제") 결론이 표본 한계와 함께 박제됨 · backend/app diff 0.</done>
</task>

<task type="auto">
  <name>Task 3: 마크 게이트 배선 + 승인 무회귀 md5 + belle 비교 재료</name>
  <files>backend/shared/python/sunity_shared/analysis/fault_zoom.py, backend/tests/test_fault_zoom_angle_admissible.py, .planning/quick/260814-rcz-caption-cause-layer/CAPTION-SHEET.md, .planning/quick/260814-rcz-caption-cause-layer/evidence/</files>

  <action>
    **① 게이트 구현 (순수 함수 + 진입점 1곳).** `fault_zoom.py` 에 순수 판정 함수를
    신설한다 — 입력은 양 패널 px 사이각(및 Task 2 가 채택한 축의 값), 출력은
    (그릴지 여부, 사유 문자열). 모듈 상수로 임계를 선언하고 주석에 **어떤 카드
    집합에서 어떻게 재서 정했는지**(MEASURE.md 참조 + 표본 1)를 박제한다. Task 2 가
    "축 미발견"으로 끝났으면 대신 (motionId, criterion) 선언 억제 표를 모듈 상수로
    두고 같은 함수 시그니처로 판정한다 — 동작명 코드 분기 0, 데이터 선언만.

    배선 위치 = 3536~3624행 각도 베이크 블록. `u_spec`/`r_spec` 이 둘 다 성립하고
    `shift_bake_spec` 적용이 끝난 **직후**(= 실제로 그려질 좌표 기준)에 판정하고,
    미충족이면 `angle_reason` 에 전용 사유를 넣고 드로잉을 건너뛴다 → 기존 원 마커
    폴백으로 자연히 떨어진다(3635행 분기 무변경, 새 표면 0). 하이브리드 경로가 이미
    부르는 `_spec_inner_deg_px(r_frame, r_spec, r_box)` 결과를 재사용해 **중복 계산
    0**. ★fail-open 필수: 사이각이 None/비유한이면 오늘과 동일하게 그린다 — 무회귀가
    우선이다. `fault_zoom_angle_bake` 로그에 새 사유가 찍히게 해 운영에서 판정을
    사후 추적할 수 있게 한다(로그가 배선의 증인).

    **② 단위 테스트 (backend/tests/test_fault_zoom_angle_admissible.py).** 순수 함수의
    통과/억제/fail-open 3분기 + Task 2 실측표의 P 전건이 통과, N 이 억제됨을 표 값
    그대로 넣어 단언(테이블 주도). 임계를 테스트에 맞춰 움직이지 말 것 — 임계는
    MEASURE.md 가 소유하고 테스트는 그것을 고정한다.

    **③ 무회귀 재렌더 (실행 로그가 증인).** Task 2 하네스 2개를 **패치 후** 그대로 다시
    돌린다. 게이트:
      · 승인 5동작 스윕 카드 md5 **전건 동일** (V 유지 카드가 하나라도 사라지면 실패)
      · cand17B 카드 md5 동일 (belle 채택분 무손상)
      · cand01E 카드는 **변경되고**, 변경 내용이 V 소멸임을 실행자가 PNG 를 Read 로
        열어 육안 확인 (frames-before-numbers — 로그만으로 통과 선언 금지)
      · `fault_zoom_angle_bake` 로그에 새 사유가 cand01E 에서 실제로 찍힘
    승인 카드가 하나라도 변하면 게이트 실패로 보고하고 임계를 되돌린다(통과할 때까지
    임계 조정 금지).

    **④ belle 비교 재료 (CAPTION-SHEET.md + /Users/Shared/sunity-caption-cause-260814/).**
      · 판정 2건 각각에 대해 **구 캡션 / 신 캡션 원문 전문**을 나란히. 신 캡션은
        Task 1 조립기의 실제 산출 문자열이어야 하고, 같은 문자열이 node 프로브에서도
        나왔음을 실행 로그로 병기(음성=자막 lockstep 증명).
      · 카드 실물: cand17B(무변경 확인) · cand01E(V 소멸 전/후 2장).
      · 캡션은 카드 이미지에 굽지 않는다 — 캡션이 실제로 나가는 자리는 합성 영상의
        정지 자막과 Polly 음성이며, 그 재렌더는 별건(chd 선례)임을 시트에 1줄 명기.
        자막 3줄 실측(Task 1 T8)의 줄수·문자수를 함께 적어 클립 위험을 보고.
      · 판정란 3항 (실행자 선기입 금지): (a) 원인 문구 2건의 문면 승인 여부,
        (b) 원인 문구를 **동작×관절 전형 설명**으로 일반화해도 되는지(같은 동작·같은
        관절의 다른 순간에도 이 문장이 나간다), (c) 마크 억제 시 원 마커 폴백이
        맞는지 아니면 완전 무마크가 맞는지.
      · 실행자 추천은 belle 판정 **전에** 커밋한다(사전 박제 규율) — 다만 이번 사이클은
        발굴 추천이 아니므로 DISCOVERY-LEDGER 승격 실적표에는 행을 추가하지 않고,
        시트 안에만 추천/근거를 적는다.

    **⑤ 전체 게이트.** pytest 기준선 무회귀(59 failed 동일) · app typecheck PASS ·
    채점 산식 5파일 diff 0 · S3 업로드 0 / Firestore 쓰기 0 / Pod 무접촉 / Gemini
    실호출 0 을 실행 로그로 확인해 SUMMARY 에 적는다. SUMMARY 에는 LLM 학습 영향
    (이번 사이클: 추론 호출 유무·학습 전송 0)을 반드시 기재.
  </action>

  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests 2>&1 | tail -5 && git diff --stat HEAD -- backend/shared/python/sunity_shared/analysis/deduction_engine.py backend/shared/python/sunity_shared/analysis/dimensions.py backend/shared/python/sunity_shared/analysis/kismam.py backend/shared/python/sunity_shared/analysis/motiondtw.py backend/shared/python/sunity_shared/analysis/assemble.py | tee /dev/stderr | grep -q . && echo "FAIL: 채점 산식 변경" && exit 1 || echo "OK: 산식 diff 0"</automated>
  </verify>

  <done>게이트가 순수 함수 + 진입점 1곳으로 배선되고 fail-open 확인 · 신규 테스트 PASS · pytest 기준선 59 failed 동일 · 승인 스윕 카드 md5 전건 동일 + cand17B 동일 + cand01E 만 변경(V 소멸 육안 확인) · CAPTION-SHEET.md 에 구/신 캡션 2건 + 카드 실물 + 판정란 3항 게재 · /Users/Shared/ 확인 재료 배치 · 산식 5파일 diff 0.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| phrasebook.json → 사용자 자막·Polly 음성 | 승인 문구가 그대로 낭독·표시된다. 문구 결함 = 신뢰 결함 |
| fault_zoom 마크 게이트 → 카드 표시 | 표시 억제가 과하면 승인 카드가 조용히 사라진다 |
| 로컬 하네스 → S3 / Firestore | 읽기 전용 경계. 쓰기가 새면 프로덕션 오염 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-rcz-01 | Information Disclosure | causeLine 문구 | mitigate | 측정 안 된 원인을 단정으로 말하지 않는다 — 가설 어미 + 무수치를 테스트로 강제, 기존 금지어 게이트가 entries 전체 재귀 스캔 |
| T-rcz-02 | Tampering | 캡션 조립 양쪽 갈라짐 | mitigate | node 로 TS 를 실제 실행해 같은 fixture 문자 비교 (소스 눈대조 금지) |
| T-rcz-03 | Denial of Service | 자막 3줄 상한 초과로 행동절 소실 | mitigate | 운영 폰트·폭으로 `wrap_text` 줄수 ≤3 을 테스트로 못 박음 |
| T-rcz-04 | Tampering | 마크 게이트가 승인 카드 마크 제거 | mitigate | 패치 전/후 승인 5동작 카드 md5 전건 동일 게이트 + fail-open 설계 |
| T-rcz-05 | Elevation of Privilege | 하네스가 프로덕션에 쓰기 | mitigate | S3 read-only · Firestore 읽기만 · Pod 무접촉을 SUMMARY 실행 로그로 확인 |
| T-rcz-06 | Repudiation | "배선했다" 주장에 실행 증거 부재 | mitigate | 운영 로그(`fault_zoom_angle_bake` 새 사유) + 재렌더 md5 + PNG 육안 확인 |
| T-rcz-SC | Tampering | 패키지 설치 | accept | 신규 의존성 설치 0 (node/pytest 는 기존 환경) |
</threat_model>

<verification>
- causeLine 없는 record 캡션 = 오늘과 문자 단위 동일 (테스트 단언)
- python 산출 == node 로 실행한 TS 산출 (fixture 전건, skip 아닌 실행)
- 시드 2건: 가설 어미 · 수치 0 · 금지어 게이트 통과 · 자막 ≤3줄
- 계약 4곳(models/analysis.ts/contract.md/pin 테스트) 동시 갱신 — lockstep 테스트가 증인
- 마크 조건: 실측표 → 판정 규칙 → 임계(또는 선언 억제) 순서, 표본 1 박제
- 승인 5동작 카드 md5 전건 동일 + cand17B 동일 + cand01E 만 V 소멸(육안)
- pytest 기준선 59 failed 동일 · typecheck PASS · 산식 5파일 diff 0
- S3 업로드 0 · Firestore 쓰기 0 · Pod 무접촉 · Gemini 실호출 0 · 이모지 0
</verification>

<success_criteria>
1. 원인 절이 붙은 캡션 **실물 문자열** 2건이 나오고, 그 문자열이 음성 경로와 자막 경로에서 동일함이 양엔진 실행으로 증명된다.
2. 원인 없는 record 는 오늘과 byte-동일한 캡션을 낸다.
3. 각도 표기 적용 조건이 **실측 뒤에** 정해지고, 갈리지 않으면 지어내지 않고 정직하게 보고된다.
4. 승인 카드의 마크가 하나도 사라지지 않고, belle 이 반려한 카드 한 장만 마크 없이 나간다(육안 확인).
5. belle 이 판정할 수 있는 비교 재료(구/신 캡션 + 카드 실물 + 판정란 3항)가 열어볼 수 있는 물건으로 존재한다.
</success_criteria>

<output>
Create `.planning/quick/260814-rcz-caption-cause-layer/260814-rcz-SUMMARY.md` when done
</output>

---
phase: quick-260813-ebd
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/quick/260811-xa1-mark-grammar-round-ufb-freeze-2-belle/JUDGMENT.md
  - .planning/quick/260813-ebd-xa1-3-belle-08-13-p3-v/round3.py
  - .planning/quick/260813-ebd-xa1-3-belle-08-13-p3-v/.gitignore
  - .planning/quick/260813-ebd-xa1-3-belle-08-13-p3-v/out/candidates/
  - .planning/quick/260813-ebd-xa1-3-belle-08-13-p3-v/260813-ebd-SUMMARY.md
autonomous: true
requirements: []

must_haves:
  truths:
    - "JUDGMENT.md 에 belle 08-13 번복 판정(스포트라이트 철회 D-01 / 골반 P3 채택 D-02 / 팔꿈치 V 위치보정 D-03)이 기존 장부 형식으로 append 되어 있다"
    - "팔꿈치 V 얼굴회피 변형안 2~3장이 belle 이 반려한 그 freeze 실물에서 렌더되어 있다 (베이스라인 md5 게이트 PASS 선행)"
    - "골반 P3 재렌더 1장이 align 게이트 순간 단일 출처 좌표로 존재한다 (fps 라벨 사슬 skew 재도입 0)"
    - "변형안 각각의 얼굴·머리 관통 여부가 개별 PNG 육안 판정으로 기록되어 있다 (frames-before-numbers)"
    - "belle 제시 전 내 추천 1안 + 근거가 JUDGMENT.md 에 사전 박제되어 있다"
    - "/Users/Shared/sunity-mark-candidates-260813/ 에 한글 파일명 사본이 있다"
    - "backend/ 운영 코드 diff 0, Gemini 실호출 0"
  artifacts:
    - path: ".planning/quick/260813-ebd-xa1-3-belle-08-13-p3-v/round3.py"
      provides: "라운드 3 하네스 (베이스라인 게이트 + P3r1/EV 변형안 렌더)"
    - path: ".planning/quick/260813-ebd-xa1-3-belle-08-13-p3-v/out/candidates/render_summary_round3.json"
      provides: "후보별 기계 판정 (md5 무누출 / survivors / targetChanged / notes)"
    - path: ".planning/quick/260813-ebd-xa1-3-belle-08-13-p3-v/out/candidates/P3r1/zoom_angle_vs_reference__left_hip.png"
      provides: "골반 P3 재렌더 (align 단일 출처)"
    - path: ".planning/quick/260811-xa1-mark-grammar-round-ufb-freeze-2-belle/JUDGMENT.md"
      provides: "08-13 번복 판정 박제 + 라운드 3 사전 박제"
      contains: "2026-08-13"
    - path: ".planning/quick/260813-ebd-xa1-3-belle-08-13-p3-v/260813-ebd-SUMMARY.md"
      provides: "변형안별 자평 + 보드 라운드 3 게시 재료 (이미지 목록·캡션)"
  key_links:
    - from: ".planning/quick/260813-ebd-xa1-3-belle-08-13-p3-v/round3.py"
      to: ".planning/quick/260811-xa1-mark-grammar-round-ufb-freeze-2-belle/grammar_round.py"
      via: "importlib 로드 (refine_round 경유) — 베이스라인 게이트·스텁·EV 가드 전부 상속"
      pattern: "grammar_round|refine_round"
    - from: ".planning/quick/260813-ebd-xa1-3-belle-08-13-p3-v/round3.py"
      to: "align 17-kp 게이트 freeze 순간 좌표"
      via: "_R2Patch._gate_moment_px 공식 재사용: round(freeze_sec x align_fps), conf>=fz._KP_CONF_MIN, fail-closed"
      pattern: "_gate_moment|align"
---

<objective>
xa1 마크 문법 라운드 3 — belle 08-13 번복 판정을 장부에 박제하고, 채택된 선(V)
문법의 판정 재료를 산출한다.

**확정 판정 (belle 08-13, locked — 재질문 금지):**
- **D-01**: 스포트라이트(E3/E3-r1/P4) 채택 철회. 사유 = 주변 검증 결과 모두가
  선(line) 문법 선호. 코드는 하네스에 보존 — 폐기 커밋 불필요.
- **D-02**: 골반 = **P3 채택** (기존 V자: 흰 코어 + 꼭짓점 화살촉). belle 선택
  이미지 실물 = `out/candidates/P3/zoom_angle_vs_reference__left_hip.png` 와
  픽셀 일치 (오케스트레이터 대조 완료).
- **D-03**: 팔꿈치 = belle 선택 이미지 실물은 **베이스라인**(현 운영 기존 V자)
  이었음. belle 답변: "V자 문법 채택하되 얼굴·머리 관통하지 않게 위치 보정.
  E1보다 좀 더 길어지는 건 상관없음. 네가 가장 표현 잘하는 방향으로 추천"
  → 얼굴회피 V 변형안 2~3개 렌더 라운드 1회 후 belle 판정.

Purpose: belle 판정 사이클 지속 — 채택 문법(V자)의 얼굴회피 변형안 + 채택본
P3 의 좌표 수리본을 같은 반려 freeze 실물에서 산출해 라운드 3 판정 재료를 낸다.
운영 배선은 belle 판정 통과 후 별도 사이클.

Output: JUDGMENT.md 라운드 3 절(번복 박제 + 사전 박제) / round3.py /
P3r1 + EV 변형안 PNG + render_summary_round3.json / /Users/Shared 한글 사본 /
SUMMARY(보드 게시 재료 포함).
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/CONTINUE-2026-08-12.md
@.planning/quick/260811-xa1-mark-grammar-round-ufb-freeze-2-belle/JUDGMENT.md
@.planning/quick/260811-xa1-mark-grammar-round-ufb-freeze-2-belle/refine_round.py
@.planning/quick/260811-xa1-mark-grammar-round-ufb-freeze-2-belle/grammar_round.py
@.planning/quick/260811-xa1-mark-grammar-round-ufb-freeze-2-belle/260811-xa1-SUMMARY.md

**플래너 사전 실측 (2026-08-13, 재조사 불필요):**
- ufb 캐시 사망 확인: `/private/tmp/claude-501/.../8a8d6013-*/scratchpad/fresh/`
  부재 → Task 2 는 `verify_local.py --fetch` 재수화가 선행 조건이다.
- 라운드 1 P3 의 vertex = `spec[0]` = 12관절 report 좌표 (수리 전, fps 라벨
  사슬) — 라운드 2 진단 실측으로 align 단일 출처와 user 1.6px / ref 8.7px
  차이. **좌표가 동일하지 않으므로 P3 재렌더 필요** (재사용 아님).
- 수리된 좌표 공식의 정본 = `refine_round._R2Patch._gate_moment_px`:
  align 17-kp 트랙 @ `round(freeze_sec x align_fps)`, conf >= `fz._KP_CONF_MIN`,
  미달 시 미방출 (fail-closed). 이 공식만 쓴다 — `_to_rep_idx` fps 라벨 사슬
  경유 금지.
- 한글 export 관례 실물 = `/Users/Shared/sunity-mark-candidates-260812/`
  (`골반-P2-선+쐐기-추천.png` 형식, 추천안에 `-추천` 접미).
- xa1 `.gitignore` = `out/_ev/` + `__pycache__/` 제외, `out/baseline/` +
  `out/candidates/` 는 커밋 보존 대상.
</context>

<tasks>

<task type="auto">
  <name>Task 1: JUDGMENT.md 라운드 3 절 — belle 08-13 번복 판정 박제</name>
  <files>.planning/quick/260811-xa1-mark-grammar-round-ufb-freeze-2-belle/JUDGMENT.md</files>
  <action>
    JUDGMENT.md 말미에 라운드 3 절을 append 한다 (기존 장부 형식: `---` 구분 +
    `# 라운드 3 — ...` 헤더 + belle 원문 인용 + 판정·대조 소절). 내용:

    1. **번복 판정 3항목** (objective 의 D-01/D-02/D-03 그대로, belle 원문 인용
       포함): 스포트라이트 채택 철회(사유 = 주변 검증 선 문법 선호, 코드 보존),
       골반 = P3 채택, 팔꿈치 = V 문법 채택 + 얼굴회피 위치 보정(E1보다 길어도
       됨, 추천 위임).
    2. **이미지-후보 대조 결과** (오케스트레이터 확인 완료분 기록): 골반 선택
       이미지 = `out/candidates/P3/zoom_angle_vs_reference__left_hip.png` 픽셀
       일치 / 팔꿈치 선택 이미지 = `out/baseline/zoom_angle_vs_reference__left_elbow.png`
       (베이스라인 실물) — 확인 질문으로 D-03 스펙 확정.
    3. **사전 박제 장부 갱신**: 라운드 1 "E3 채택"은 08-13 철회로 번복됨을
       명기. 라운드 2 E3-r1/P4 는 개별 판정 없이 문법 축 자체가 바뀌어 철회
       종결 (좌표 수리 실측 자체는 유효 — D-02/D-03 렌더가 그 공식을 상속).
    4. 다음 = 라운드 3 렌더 (P3r1 + 팔꿈치 EV 변형안) 예고 1줄.

    이모지 금지, 각도 수치 캡션 금지 (기결론). 기존 절 본문 수정 금지 —
    append only.
  </action>
  <verify>
    <automated>grep -c "2026-08-13" .planning/quick/260811-xa1-mark-grammar-round-ufb-freeze-2-belle/JUDGMENT.md | awk '{exit ($1>=1)?0:1}' && grep -q "철회" .planning/quick/260811-xa1-mark-grammar-round-ufb-freeze-2-belle/JUDGMENT.md</automated>
  </verify>
  <done>JUDGMENT.md 에 라운드 3 절이 append 되어 D-01~D-03 + 이미지 대조 + 장부 번복 기록이 실려 있고, 기존 절은 byte 무변경이다.</done>
</task>

<task type="auto">
  <name>Task 2: round3.py — 캐시 재수화 + 베이스라인 게이트 + P3r1/EV 변형안 렌더</name>
  <files>.planning/quick/260813-ebd-xa1-3-belle-08-13-p3-v/round3.py, .planning/quick/260813-ebd-xa1-3-belle-08-13-p3-v/.gitignore, .planning/quick/260813-ebd-xa1-3-belle-08-13-p3-v/out/candidates/</files>
  <action>
    **선행 — 캐시 재수화** (플래너 실측: scratchpad fresh/ 사망):
    `AWS_PROFILE=sunity-motion backend/.venv/bin/python
    .planning/quick/260811-ufb-freeze-only/verify_local.py --fetch`
    (Firestore doc + S3 영상 읽기 전용 fetch — Pod 불필요, 쓰기 0).

    **round3.py 작성** (새 quick 디렉터리, 라운드 2 refine_round.py 패턴):
    - xa1 디렉터리의 `refine_round.py` 를 importlib 로 로드 (내부에서
      grammar_round 가 인터프리터 자동 승격·Gemini 스텁·EV 리다이렉트·
      `_guard_ev` 가드를 전부 상속). `vl.EV` 리다이렉트는 xa1 쪽 그대로 둔다 —
      재지정 금지 (`_guard_ev` 가 "260811-xa1" 포함을 assert).
    - `--baseline`: `gr.baseline()` 위임 — md5 2/2 == CERT_MD5 + survivors ==
      CERT_SURVIVORS. **FAIL 이면 박제 후 정지, 후보 렌더 진입 금지** (bz5 규율).
    - `--candidates`: 모드 = P3r1(left_hip) + 팔꿈치 EV 변형안 2~3개
      (EV1/EV2[/EV3], left_elbow). 후보별 vl.run() 1회, 라운드 2 게이트 동일:
      대상 카드 방출 + targetChanged + 비대상 카드 md5 == 인증값(무누출) +
      survivors 불변. 결과 카드는 새 디렉터리
      `out/candidates/{mode}/` 로 복사, `out/candidates/render_summary_round3.json`
      박제 (notes 에 좌표 px·이동량·eye 스텁 카운트 포함).

    **좌표 규율 (전 후보 공통 — fps 라벨 사슬 skew 재도입 금지):**
    vertex = `_R2Patch._gate_moment_px` 공식 재사용 (align 17-kp @
    round(freeze_sec x align_fps), conf >= `fz._KP_CONF_MIN`, 미달 = 미방출
    fail-closed). limb/torso 방향점은 bake spec 값을 **vertex 이동 델타만큼
    평행이동** — V 사이각·방향 보존, 앵커만 수리. `_R2Patch` 를 서브클래스해
    `_gate_moment_px` 를 그대로 상속하는 구현을 권장.

    **P3r1 (D-02 채택본의 좌표 수리 재렌더):** 드로잉은 라운드 1 P3 경로
    그대로 — user 패널 = `bz._draw_candidate(img, v, l, t, ref_deg, "hybrid")`
    (ref_deg = xa1 `out/baseline/gate.json` recordedAngles.left_hip.refDeg),
    ref 패널 = 평행이동한 spec 으로 `_orig_side` 호출 (원본 문법 유지). 예상
    이동 = user ~1.6px / ref ~8.7px (라운드 2 진단 실측) — notes 에 실측 기록.

    **팔꿈치 EV 변형안 (D-03):** V 2가닥 문법 유지 + 얼굴·머리 관통 0. 머리
    원반 = `_head_disc_align` (옵션 ①, align 17-kp nose/eyes/ears 투영) 재사용.
    마크 픽셀의 원반 진입 금지, 원반 뒤 재개 금지 (라운드 1 박제 원칙). E1보다
    길어지는 것 허용 (belle 명시). 설계 후보 — `out/diagnose/diagnose.json` 과
    라운드 2 진단("선이 관절에 닿지 않는다 / 사이각이 좁아 V 가 선 하나로
    읽힘")을 읽고 2~3개 확정 (executor 재량, 근거 1줄씩 summary notes 박제):
    ① 관절 도달 선 — 스텁 대신 팔꿈치에서 실측 손목·어깨 keypoint(같은 align
      게이트 순간)까지 선을 잇고, 원반 통과 구간은 진입 전 클리핑.
    ② 팔길이 비례 — 스텁 길이를 실측 전완 px 길이 비례로 (고정 프랙션 폐기),
      원반 진입 전 종료.
    ③ E1 연장 — 클리핑 유지 + 기본 길이 증가 + 호(사이각 시각 재료) 복원 조건
      완화.
    변형안 간에는 좌표 출처·원반 규칙이 동일해야 한다 — 차이는 선의 길이·
    도달점 문법뿐.

    `.gitignore` 는 xa1 관례 미러 (`__pycache__/` — 이 디렉터리엔 `_ev` 없음).
    운영 코드(backend/) 수정 금지 — monkeypatch 는 프로세스 내에서만.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && python3 .planning/quick/260813-ebd-xa1-3-belle-08-13-p3-v/round3.py --baseline --candidates 2>&1 | grep -E "BASELINE GATE PASS|CANDIDATES-R3 PASS" | wc -l | awk '{exit ($1>=2)?0:1}' && ls .planning/quick/260813-ebd-xa1-3-belle-08-13-p3-v/out/candidates/P3r1/zoom_angle_vs_reference__left_hip.png && test -z "$(git status --porcelain -- backend/)"</automated>
  </verify>
  <done>베이스라인 게이트 PASS(md5 2/2 + survivors — "반려한 그 freeze 실물" 기계 증명) 후 P3r1 1장 + EV 변형안 2~3장이 방출되고, 후보별 무누출·survivors 불변이 render_summary_round3.json 에 박제되며, backend/ diff 0 · Gemini 실호출 0 (스텁 카운트 출력).</done>
</task>

<task type="auto">
  <name>Task 3: 육안 판정 + 사전 박제 + /Users/Shared export + SUMMARY(보드 재료)</name>
  <files>.planning/quick/260811-xa1-mark-grammar-round-ufb-freeze-2-belle/JUDGMENT.md, .planning/quick/260813-ebd-xa1-3-belle-08-13-p3-v/260813-ebd-SUMMARY.md</files>
  <action>
    **육안 판정 (frames-before-numbers — 몽타주 금지):** P3r1 + EV 변형안
    각각을 Read 로 **개별 원본 1장씩** 연다. 팔꿈치 변형안은 얼굴 영역 확대
    크롭을 추가 생성해 Read (라운드 1 관례). 기록 항목(변형안별):
    ① 얼굴·머리 관통 여부 (마크 픽셀 원반 진입 0 인가) ② 마크가 관절 실물
    위에 앉는가 ③ V(2가닥+사이각)가 그림에서 읽히는가. 관통이 발견되면 해당
    변형안을 수리·재렌더하거나 (Task 2 하네스 재실행, 게이트 재통과) 미성립
    판정으로 박제하고 export·추천에서 제외 — 관통 실물을 belle 재료로 내지
    않는다.

    **사전 박제 (belle 제시 전):** JUDGMENT.md 라운드 3 절에 append —
    팔꿈치 추천 1안 + 근거 (실물 관찰만, 실측 없는 단정 금지) + P3r1 육안
    결과 (채택 문법 유지 + 앵커 이동 실측 px, belle 재확인 대상임을 명기).

    **export:** `/Users/Shared/sunity-mark-candidates-260813/` 생성 후 한글
    파일명 사본 복사 (260812 관례): `골반-P3r1-기존V자-좌표수리.png`,
    `팔꿈치-EV1-{설명}.png`, `팔꿈치-EV2-{설명}.png` [, EV3] — 추천안에
    `-추천` 접미.

    **SUMMARY (260813-ebd-SUMMARY.md, quick summary 형식):**
    - 기계 판정 절 (베이스라인 게이트·후보 게이트·backend diff 0)
    - 육안 판정 절 (변형안별 3항목 기록)
    - **변형안별 자평** (오케스트레이터가 belle 제시 전 참조하는 사전 박제
      재료 — 각 안의 강점·한계 1~2줄, 추천과 근거)
    - **보드 라운드 3 게시 재료**: 이미지 절대경로 목록 + 캡션 텍스트 (각도
      수치 미노출·이모지 금지·신뢰 표기 관례). 게시 자체는 오케스트레이터가
      Artifact 도구로 수행 — executor 는 재료만 정리.
    - LLM 학습 영향 절 (Gemini 실호출 0 — machine_eye 스텁, 눈 원장 신규 0)
    - Deviations / Self-Check
  </action>
  <verify>
    <automated>ls /Users/Shared/sunity-mark-candidates-260813/ | grep -c "png" | awk '{exit ($1>=3)?0:1}' && grep -q "보드" .planning/quick/260813-ebd-xa1-3-belle-08-13-p3-v/260813-ebd-SUMMARY.md && grep -q "추천" .planning/quick/260811-xa1-mark-grammar-round-ufb-freeze-2-belle/JUDGMENT.md</automated>
  </verify>
  <done>변형안 전부 개별 육안 판정 기록 완료(관통 실물 0 또는 미성립 박제), 추천 1안 + 근거가 JUDGMENT.md 에 belle 제시 전 박제, /Users/Shared/sunity-mark-candidates-260813/ 에 한글 사본 3장 이상, SUMMARY 에 자평 + 보드 게시 재료 정리.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| 하네스 → ufb evidence | vl.run() 이 EV 하위를 비움 — 리다이렉트 실패 시 반려 증거 정본 파괴 |
| 하네스 → backend/ 운영 코드 | monkeypatch 가 프로세스 밖으로 새면 운영 오염 |
| 로컬 → AWS (fetch) | 읽기 전용 재수화 — 쓰기 경로 없음 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-ebd-01 | Tampering | ufb evidence/ 정본 | mitigate | `_guard_ev` assert 상속 (vl.EV 에 "260811-xa1" 포함 필수) — round3.py 는 EV 재지정 금지 |
| T-ebd-02 | Tampering | backend/ 운영 코드 | mitigate | Task 2 verify 에 `git status --porcelain -- backend/` 빈 출력 게이트 |
| T-ebd-03 | Information Disclosure | 인물 이미지 export | mitigate | 홈디렉터리(~) 금지 — /Users/Shared/ 관례 경로만 (기존 박제 규칙) |
| T-ebd-SC | Tampering | 패키지 설치 | accept | 신규 설치 0 — backend/.venv 기존 의존성만 (grammar_round 인터프리터 자동 승격) |
</threat_model>

<verification>
- 베이스라인 md5 게이트: 무패치 렌더 md5 2/2 == ufb 인증값 + survivors 일치 (실행 로그로 증명 — 커밋 메시지·주장 아님)
- 후보별: 방출 + targetChanged + 비대상 카드 무누출 + survivors 불변 (render_summary_round3.json)
- 좌표: 전 후보 vertex 가 align 게이트 순간 공식 단일 출처 (`_gate_moment_px` 상속) — fps 라벨 사슬(`_to_rep_idx`) 경유 0
- 육안: 변형안 개별 Read, 관통 실물 0
- 무접촉: `git status --porcelain -- backend/` 빈 출력, Gemini 실호출 0 (스텁 카운트)
</verification>

<success_criteria>
- JUDGMENT.md 라운드 3 절 = 번복 판정 3항목(D-01~D-03) + 이미지 대조 + 장부 번복 기록 + 사전 박제(추천 1안·근거)
- P3r1 1장 + 팔꿈치 EV 변형안 2~3장, 전부 반려 freeze 실물(md5 게이트 PASS)에서 align 단일 출처 좌표로 렌더
- 얼굴·머리 관통 0 육안 성립 (또는 미성립 박제 + 제외)
- /Users/Shared/sunity-mark-candidates-260813/ 한글 사본 + SUMMARY 보드 게시 재료
- 운영 코드 diff 0, pytest 불필요 (운영 무변경 — md5 게이트·눈 확인이 이 사이클의 검증 사다리)
</success_criteria>

<output>
Create `.planning/quick/260813-ebd-xa1-3-belle-08-13-p3-v/260813-ebd-SUMMARY.md` when done
</output>

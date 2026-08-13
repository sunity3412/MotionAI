---
quick_id: 260813-fxx
slug: belle-3-p3r1-pass-v-p3-align-fps-5-pytes
date: 2026-08-13
status: planned
description: 선 문법 운영 배선 — belle 라운드 3 최종 판정 박제(P3r1 PASS·팔꿈치 오프셋 반려) + 골반 P3 문법 운영 이식 + 확정 카드 표시 좌표 align 단일 출처 근본 수리(fps 라벨 사슬 제거) + 승인 무회귀·pytest 59·분기 0 검증 사다리
wave: 1
depends_on: []
autonomous: true
requirements: [QUICK-260813-FXX]
files_modified:
  - .planning/quick/260811-xa1-mark-grammar-round-ufb-freeze-2-belle/JUDGMENT.md
  - backend/shared/python/sunity_shared/analysis/fault_zoom.py
  - backend/functions/pipeline/app.py
  - backend/tests/test_fault_zoom_display_repair.py
  - .planning/quick/260813-fxx-belle-3-p3r1-pass-v-p3-align-fps-5-pytes/verify_wiring.py
  - .planning/quick/260813-fxx-belle-3-p3r1-pass-v-p3-align-fps-5-pytes/evidence/
must_haves:
  truths:
    - "확정(single-joint angle) 카드의 크롭 중심·원 앵커·V 꼭짓점이 게이트 freeze 순간 align 17-kp 단일 출처에서 나온다 — round(freeze_sec x align_fps), conf>=0.5, fps 라벨 사슬(_to_rep_idx) 경유 0, 미달 = 카드 미방출(fail-closed)"
    - "골반(hip) 각도 카드 user 패널 = P3 하이브리드 문법(V 2가닥 + 쐐기·화살촉 상시 + 고스트 점선 델타>=8도), ref 패널 = 기존 V — round3.py P3r1 이 인증한 그 문법. 팔꿈치 카드 문법 = 현행 V 무변경 (belle 판정 2 — EV4/EV5 오프셋 반려)"
    - "마크 위치 미세조정 상수 신설 0 (belle 판정 3 — 이연). 얼굴 원반 클리핑·오프셋 배치 코드 미이식"
    - "채점 무접촉 — 점수·records·freeze 선정·survivors 판정 로직 불변, 산식 5파일(deduction_engine/dimensions/kismam/motiondtw/assemble) diff 0"
    - "ufb fresh doc 재렌더: freeze 전건 일치(순간 발명 0) + 별도 프로세스 2회 결정론 + 승인 코퍼스 hold/pair 9/9 + 비대상 산출물(advisory·verdict survivors) 불변 + 대상 카드 2장만 md5 변경(의도 변경) + display_anchor 실행 로그 = align 재계산과 일치"
    - "pytest 기준선 59 failed 동일, 신규 실패 0. Gemini 실호출 0 (검증 전 구간 스텁)"
    - "JUDGMENT.md 에 belle 라운드 3 최종 판정(원문 인용) + 사전 박제 대조(P3r1 일치 / EV5 추천 불일치) append — 기존 바이트 무변경"
    - "수리 후 카드 2장(왼팔꿈치·왼골반)을 Read 로 실물 열어 육안 판정 기록 (frames-before-numbers)"
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/fault_zoom.py"
      provides: "display_anchor 좌표 교체(스펙 평행이동, V 사이각 보존) + P3 하이브리드 드로잉(_draw_hybrid_joint_angle 계열, hip suffix 선언 맵)"
      contains: "display_anchor"
    - path: "backend/functions/pipeline/app.py"
      provides: "_run_gated_card_inherit 가 unit 별 align 게이트 순간 좌표를 산출해 display_anchor 로 전달 (fail-closed 드랍 + 실행 로그)"
      contains: "display_anchor"
    - path: "backend/tests/test_fault_zoom_display_repair.py"
      provides: "평행이동 사이각 보존·하이브리드 ghost 게이팅·display_anchor 하위호환(None=무변경) 순수 테스트"
    - path: ".planning/quick/260813-fxx-belle-3-p3r1-pass-v-p3-align-fps-5-pytes/verify_wiring.py"
      provides: "grammar_round 스텁 상속 재렌더 드라이버 — 의도-변경-국한 diff·결정론·align 예측 대조"
    - path: ".planning/quick/260811-xa1-mark-grammar-round-ufb-freeze-2-belle/JUDGMENT.md"
      provides: "라운드 3 최종 판정 절 (append-only)"
      contains: "라운드 3 최종 판정"
  key_links:
    - from: "backend/functions/pipeline/app.py (_run_gated_card_inherit units 루프)"
      to: "fault_zoom.build_fault_zoom_comparisons"
      via: "display_anchor kwarg — cg.kp(urep15/rrep15, round(sec*afps), joint, conf_min=_fz._KP_CONF_MIN)"
      pattern: "display_anchor"
    - from: "fault_zoom.py vertex 경로 (criterion_vertex_xy/_side_crop/build_angle_bake_spec)"
      to: "align 게이트 순간 좌표"
      via: "크롭 중심·원 앵커 = display_anchor 값, 스펙 = vertex 델타 평행이동 (사이각 보존)"
      pattern: "display_anchor"
    - from: "verify_wiring.py"
      to: "ufb verify_local.run() + grammar_round 스텁/인증값"
      via: "importlib 로드 (round3.py 선례) — CERT_MD5/CERT_SURVIVORS/FREEZE_SEC 재사용"
      pattern: "grammar_round"
---

# 선 문법 운영 배선 — P3 골반 이식 + 표시 좌표 align 단일 출처 근본 수리

<objective>
belle 라운드 3 최종 판정(08-13, locked — 재질문 금지)을 장부에 박제하고, 3라운드
하네스가 인증한 것을 운영 코드로 옮긴다:

1. **판정 박제**: P3r1 PASS("일단 P3r1 확인") / 팔꿈치 = 기존 관절 위 V 유지
   ("팔꿈치는 그냥 그 팔꿈치 위에 한걸 말하는거지 따로 각도 표기를 빼라는게 아님
   더 햇깔림" — EV4/EV5 오프셋 반려) / 위치 미세조정 이연("각도 부분 위치 조정은
   일단 다 진행되면 미세조종 하도록 하고"). 내 사전 박제 EV5 추천 = **불일치**
   (철회 장부 규율 — freeze-inherit 승격 경로 = 일치 실적 추적).
2. **표시 좌표 단일 출처 수리**: 확정 angle 카드의 크롭 중심·원 앵커·V 꼭짓점을
   rep-공간 인덱스 ÷ 라벨 fps 사슬(1프레임 이른 좌표 — 라운드 2 실측 skew)에서
   **게이트 freeze 순간의 align 17-kp 좌표**로 교체. 정본 = refine_round
   `_R2Patch._gate_moment_px` 공식 (round(freeze_sec x align_fps), conf>=0.5,
   fail-closed). 동작명·영상 ID 분기 0 — 어느 분석에도 같은 공식.
3. **골반 P3 이식**: round3.py `_P3R1Patch` 가 렌더한 문법 그대로 — user 패널 =
   bz5 hybrid(쐐기+화살촉 상시, 고스트 델타>=8도), ref 패널 = 기존 V, 방향점 =
   스펙 평행이동(V 사이각·방향 보존). 팔꿈치는 문법 무변경 — 좌표만 공통 수리.

Purpose: 카드 마크가 "어디를 집는지"를 좌표 층에서 끝낸다 — fps 라벨 사슬 skew
의 구조 제거 (같은 서브시스템 반복 수리의 뿌리, escape-plan 규율).
Output: JUDGMENT append + fault_zoom/app.py 배선 + 테스트 + 로컬 기계 증명 +
카드 실물 육안 기록. Pod 실증은 범위 밖 (Pod 터미네이트 상태 — 완료 보고에
"Pod 실증 별도" 명시, 무인 실행 약속 금지).
</objective>

<context>
읽을 것 (착수 즉시 실물 대조 — verify-the-target-before-touching-it):
@.planning/quick/260813-ebd-xa1-3-belle-08-13-p3-v/260813-ebd-SUMMARY.md
@.planning/quick/260813-ebd-xa1-3-belle-08-13-p3-v/round3.py (P3r1 = _P3R1Patch/_R3Patch._repaired_pts — 이식 대상 문법·평행이동 로직)
@.planning/quick/260811-xa1-mark-grammar-round-ufb-freeze-2-belle/refine_round.py (_R2Patch._gate_moment_px — 좌표 정본 공식 + docstring 근거)
@.planning/quick/260811-bz5-mark-grammar/render_harness.py (207-313행 — _unit_vec/_inner_deg/_rotate/_dashed_line/_draw_candidate hybrid + 상수 _GHOST_DASH 9/_WEDGE_ALPHA 88/_WEDGE_R_FRAC 0.42/_ARROW_HEAD_PX 13/_GHOST_MIN_DELTA_DEG 8.0 — 운영 이식 원본)
@backend/shared/python/sunity_shared/analysis/fault_zoom.py (2985-3060 crop 중심 vertex 경로 / 3150-3269 angle bake 드로잉·copy-then-commit / 1765-1898 _draw_joint_angle·ANGLE_BAKE_MAP·build_angle_bake_spec·_draw_side_joint_angle)
@backend/functions/pipeline/app.py (4367-4790 _run_gated_card_inherit — freeze 루프 u_idx/r_idx 공식 4612-4613, units 렌더 루프 4717-4767)
@.planning/quick/260811-xa1-mark-grammar-round-ufb-freeze-2-belle/grammar_round.py (스텁·CERT_MD5·CERT_SURVIVORS·FREEZE_SEC·EV 리다이렉트 — verify_wiring 이 importlib 로 상속)

주의 (실측 근거 — 재조사 금지):
- 좌표 수리로 대상 카드 픽셀이 바뀌는 것은 **의도된 변경**. 무회귀의 정의 =
  freeze 순간·점수·survivors·비대상 산출물 불변 + 좌표 변경이 align 단일 출처
  예측과 일치. P3r1 실측 이동 = user 1.6px / ref 8.7px (좌표 검산 기준점).
- 운영 크롭 중심도 이번에 align 출처로 간다 (라운드 3 은 승인 장면 유지로 크롭
  무변경이었음 — "원만 align 출처면 출처 2벌" 미결을 단일 출처로 종결. 배선
  스펙이 "마크 앵커·크롭 중심" 둘 다 명시).
- card_gates 가 fault_zoom 을 import 한다 — fault_zoom 에서 card_gates import
  금지(순환). align 좌표 산출은 app.py 몫 (cg.kp 이미 import 됨).
- ufb 캐시는 라운드 3(260813-ebd)에서 재수화됨. 캐시 부재 시에만
  FIREBASE_SA_PATH=<리포 루트>/firebase-sa.json backend/.venv/bin/python
  .planning/quick/260811-ufb-freeze-only/verify_local.py --fetch (읽기 전용).
- Gemini 실호출 금지 — verify_wiring 은 grammar_round import 로 machine_eye
  스텁 + env 더미 키를 상속한다 (스텁이 ufb 인증 md5 를 재현함이 이미 증명됨).
- ÷9.0 카드 초 표기 잔존(kpo 유보)·advisory 링 위치·legs/split 카드 좌표는
  범위 밖 — 손대지 않는다.
</context>

<tasks>

<task type="auto">
  <name>Task 1: JUDGMENT.md 라운드 3 최종 판정 박제 (append-only)</name>
  <files>.planning/quick/260811-xa1-mark-grammar-round-ufb-freeze-2-belle/JUDGMENT.md</files>
  <action>
    파일 말미에 새 절 "## 라운드 3 최종 판정 (belle 08-13 — locked, 재질문 금지)"
    append. 내용 4항목: ① 골반 P3r1 = PASS, belle 원문 "일단 P3r1 확인" — 운영
    카드 골반 마크 = P3 문법 확정 (D-02 계보). ② 팔꿈치 = 기존 관절 위 V 유지,
    belle 원문 "팔꿈치는 그냥 그 팔꿈치 위에 한걸 말하는거지 따로 각도 표기를
    빼라는게 아님 더 햇깔림" — EV4/EV5 오프셋 V 반려, 팔꿈치 문법 변경 없음
    (D-03 의 "위치 보정"은 이연으로 흡수). ③ 위치 미세조정 이연, belle 원문
    "각도 부분 위치 조정은 일단 다 진행되면 미세조종 하도록 하고" — 배선 완료 후
    별도 미세조종 라운드. ④ 사전 박제 대조 장부 갱신: P3r1 재확인 = **일치** /
    EV5 추천 = **불일치(기각)** — 추천 대조 누적 (라운드 1 E3 적중 후 번복 기각,
    P2 기각, P3r1 일치, EV5 불일치). 이어서 "다음 = 운영 배선 (이 사이클
    260813-fxx)" 1줄. 기존 절 바이트 무변경 — append 외 편집 금지. 이모지 금지.
    커밋 1: docs(quick-260813-fxx) JUDGMENT 라운드 3 최종 판정 박제.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && grep -q "라운드 3 최종 판정" .planning/quick/260811-xa1-mark-grammar-round-ufb-freeze-2-belle/JUDGMENT.md && test "$(git diff HEAD~1..HEAD -- .planning/quick/260811-xa1-mark-grammar-round-ufb-freeze-2-belle/JUDGMENT.md | grep -c '^-[^-]')" = "0"</automated>
  </verify>
  <done>새 절이 존재하고, 직전 커밋 diff 에 삭제 라인 0 (append-only 증명). belle 원문 3건 + 불일치 기록 포함.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: 운영 배선 — display_anchor 단일 출처 + 골반 P3 하이브리드</name>
  <files>backend/shared/python/sunity_shared/analysis/fault_zoom.py, backend/functions/pipeline/app.py, backend/tests/test_fault_zoom_display_repair.py</files>
  <behavior>
    - 스펙 평행이동은 V 사이각을 보존한다: 임의 스펙 (v,l,t)와 새 vertex v' 에
      대해 이동 후 px-공간 내각 == 이동 전 (부동소수 허용오차)
    - 하이브리드 ghost 게이팅: 델타 >= 8.0 도일 때만 고스트 점선 (경계 7.9 미방,
      8.0 방출) — bz5 _GHOST_MIN_DELTA_DEG 이식값
    - display_anchor=None 하위호환: 기존 시그니처 호출은 산출 경로 무변경
      (기존 fault_zoom 테스트 전부 그대로 PASS 가 그 증명 — 새 kwarg 기본값 None)
    - _draw_hybrid_joint_angle 은 합성 이미지에서 True 반환 + degenerate 방향
      벡터(len < _MIN_LEG_VEC_PX)면 False
  </behavior>
  <action>
    **fault_zoom.py** (표시 계층만 — 채점 산식 5파일 무접촉):

    1. bz5 render_harness.py 207-313행을 운영 이식: `_rotate`, `_dashed_line`,
       내각 계산 헬퍼, `_draw_hybrid_joint_angle(img, vertex_px, limb_dir_px,
       torso_dir_px, ref_inner_deg) -> bool` = `_draw_candidate` mode="hybrid"
       그대로 (기존 V 2가닥 halo/core + 반투명 쐐기 pieslice 상시 + 쐐기 호 끝
       화살촉 + 델타>=8도만 고스트 점선(흰 halo + (60,60,60) 코어), 카이럴리티 =
       학생 패널 cross 부호). 상수 4종(_GHOST_DASH 9, _WEDGE_ALPHA 88,
       _WEDGE_R_FRAC 0.42, _ARROW_HEAD_PX 13, _GHOST_MIN_DELTA_DEG 8.0) 값
       그대로 — 신규 튜닝 금지 (belle 판정 3: 위치 미세조정 이연). 기하 상수는
       기존 _ANGLE_LIMB_LEN_FRAC/_ANGLE_TORSO_LEN_FRAC/_ANGLE_ARC_R_FRAC 재사용.
    2. 선언 맵 `HYBRID_ANGLE_SUFFIXES = frozenset({"hip"})` — ANGLE_BAKE_MAP 과
       같은 관절명-접미사 선언 패턴 (D-41: 좌우 접두 런타임 파생, 동작명 분기 0).
       팔꿈치/무릎/어깨는 미등재 = 기존 V 그대로 (과잉 일반화로 승인 깨기 금지).
    3. `build_fault_zoom_comparisons` 에 keyword-only `display_anchor: dict |
       None = None` 추가 — {"user": (x,y), "ref": (x,y)} 정규화 프레임 좌표
       (호출측이 align 게이트 순간에서 conf 게이트 통과시킨 값만 넘긴다).
       None(default) = 전 경로 byte-동일 (advisory/mode3/legacy/기존 테스트
       하위호환 — criterion_units 선례).
    4. display_anchor 적용 지점 (vertex 경로가 성립한 single-joint criterion
       카드에서만 — 경로 진입 조건·폴백 구조는 무변경, **값만 교체**):
       · 크롭 중심: u_vertex/r_vertex 성립 시 `_side_crop(center=...)` 에
         display_anchor 값 사용.
       · 원 앵커: 같은 카드의 `_side_crop(anchor=...)` 도 display_anchor 값
         (마커·크롭 중심 = 같은 단일 출처, 승인 4R#1 유지).
       · V 스펙: build_angle_bake_spec 결과(rep12 기하)를 정규화 공간에서
         delta = display_anchor − spec[0] 만큼 3점 전부 평행이동 — round3
         _R3Patch._repaired_pts 와 동치 (V 사이각·방향 보존, 방향점 재측정
         금지). criterion_crop_frac 입력도 이동본 사용 (평행이동 불변이라 값
         동일 — 단일 출처 일관).
       display_anchor 미지정 카드(legacy/advisory)는 종전 그대로. vertex 경로
       미성립 카드(relaxed 등)는 이번 수리 범위 밖 — 기존 동작 보존 (한계 박제).
    5. 드로잉 분기 (3200-3214 copy-then-commit 블록): vertex 관절 접미사가
       HYBRID_ANGLE_SUFFIXES 에 있으면 — ref 패널 px 스펙에서 내각(ref_inner_deg)
       을 먼저 계산(패널 px 공간 — 정규화 공간 각도는 종횡비로 왜곡) 후 user
       패널 = _draw_hybrid_joint_angle, ref 패널 = 기존 _draw_side_joint_angle.
       ref_inner_deg 비유한/스펙 부재 = 기존 V 양 패널 폴백 (graceful — kpo
       "실패 전량 기존 카드" 선례, 로그 fault_zoom_angle_bake 사유에 hybrid
       폴백 표기). both-or-neither·원 생략(u_drew_angle)·타임스탬프 로직 무변경.

    **app.py `_run_gated_card_inherit`** (units 렌더 루프, 4717 부근):
    unit 의 crit 이 `_fz.ANGLE_VS_REFERENCE_PREFIX` 로 시작할 때만(게이트 루프의
    is_angle_claim 과 같은 술어) — joint = cg.crit_joint(crit.split("__")[-1]),
    u_ai = clamp(round(u_sec*afps)), r_ai = clamp(round(r_sec*afps)) (4612-4613
    게이트 인덱스와 동일 공식), uxy = cg.kp(urep15, u_ai, joint,
    conf_min=_fz._KP_CONF_MIN), rxy = 동일(rrep15, r_ai). 한쪽이라도 None →
    **그 unit 카드 미방출**(continue) + log.info "display_anchor drop rid=…
    joint=… side=…" (fail-closed — 엉뚱한 rep12 좌표 폴백 금지, refine_round
    docstring 근거). 둘 다 성립 → build_fault_zoom_comparisons 에
    display_anchor={"user": uxy, "ref": rxy} 전달 + log.info
    "display_anchor rid=%s joint=%s u_ai=%d r_ai=%d user=(%.4f,%.4f)
    ref=(%.4f,%.4f)" (배선 실행 로그 증거 — wiring-claims-need-log-evidence).
    비-angle unit(peak pass-through) 은 display_anchor=None 종전 그대로.

    **테스트** backend/tests/test_fault_zoom_display_repair.py (behavior 4건,
    순수 — AWS/네트워크 0, 기존 fault_zoom 테스트 파일의 픽스처 관례 참조).
    RED(테스트 먼저, 실패 확인) → GREEN(구현) → 커밋 2:
    feat(quick-260813-fxx) 확정 카드 표시 좌표 align 단일 출처 + 골반 P3
    하이브리드 이식.

    금지: 채점 산식 5파일·records·freeze 선정·card_gates 임계 접촉, 마크 위치
    튜닝 상수 신설, 얼굴 원반 클리핑/오프셋 이식(반려됨), 동작명·분석 ID 리터럴,
    캡션/문구 신설(앱 무접촉 — 카드에 수치 배지 0 유지), 이모지.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests/test_fault_zoom_display_repair.py && git diff HEAD~1..HEAD --name-only | grep -cE "analysis/(deduction_engine|dimensions|kismam|motiondtw|assemble)\.py" | grep -qx 0 && ! git diff HEAD~1..HEAD -- backend | grep -iE "ref-pdshape|peter-pan|power-spin|kip-up|ref-combo|p34fresh"</automated>
  </verify>
  <done>신규 테스트 전부 PASS. 산식 5파일 diff 0. 배선 diff 에 동작/분석 ID 리터럴 0. display_anchor 기본값 None 하위호환 (기존 테스트 무접촉 확인은 Task 3 전체 pytest 가 최종 판정).</done>
</task>

<task type="auto">
  <name>Task 3: 검증 사다리 — 재렌더 기계 증명 + pytest 기준선 + 카드 실물 육안</name>
  <files>.planning/quick/260813-fxx-belle-3-p3r1-pass-v-p3-align-fps-5-pytes/verify_wiring.py, .planning/quick/260813-fxx-belle-3-p3r1-pass-v-p3-align-fps-5-pytes/evidence/</files>
  <action>
    verify_wiring.py 작성 — round3.py 의 importlib 패턴 그대로 grammar_round 를
    로드해 스텁(machine_eye/Gemini 더미 키/EV 리다이렉트, 단 EV 는 이 사이클
    evidence/ 로 재지정)·vl(ufb verify_local)·인증값(gr.CERT_MD5/CERT_SURVIVORS/
    FREEZE_SEC/CARD_NAME)을 상속한다. ufb 원본 파일 무접촉 (kpo 선례 — 과거
    quick 은 기록). 캐시 부재 시에만 --fetch (FIREBASE_SA_PATH 주입, 읽기 전용).

    스테이지:
    · --once: vl.run() 1회 → {pngMd5, survivors, dropped, display_anchor 로그
      라인} JSON stdout (root 로거 핸들러로 "display_anchor" 라인 캡처).
    · --check: --once 를 **별도 프로세스 2회** subprocess 실행 후 판정 —
      (1) 결정론: 두 실행의 pngMd5/survivors/dropped 완전 동일.
      (2) freeze 전건 일치: survivors 원소의 @u/r == gr.FREEZE_SEC 값 그대로
          (순간 발명 0 — ufb 불변식 유지).
      (3) 의도-변경-국한: 대상 2카드(zoom_angle_vs_reference__left_hip/
          left_elbow) md5 != gr.CERT_MD5 (변경됨 = 의도) AND survivors ==
          gr.CERT_SURVIVORS AND dropped 목록에 display_anchor drop 0건.
      (4) align 예측 대조: 캡처한 display_anchor 로그의 (u_ai, r_ai, 좌표)를
          캐시 align 에서 cg.align_to_report + cg.kp(conf_min=0.5)로 독립
          재계산해 일치 판정 + hip vertex px 이동량을 P3r1 실측(user 1.6px /
          ref 8.7px)과 대조 기록 (evidence/wiring_check.json 박제).
      (5) vl --approved 위임: 승인 코퍼스 hold 9/9 + pair 9/9 (ii0 정본,
          오프라인 — Gemini 0회).
      전 판정 PASS 시 "WIRING-CHECK PASS" 출력, 하나라도 FAIL 이면 박제 후
      비零 종료 (bz5 규율 — FAIL 은 그대로 남긴다).

    실행 순서: verify_wiring.py --check → 전체 pytest (기준선 59 failed 동일
    — verify 커맨드의 tail 로 기계 확인) → **카드 실물 육안** (frames-before-
    numbers): evidence/ 에 복사된 수리 후 카드 2장을 Read 도구로 열어 ① 골반 =
    P3 하이브리드(쐐기+화살촉, 고스트는 델타에 따름) + 양 패널 마크가 왼골반
    위 ② 팔꿈치 = 기존 V 문법 그대로 + 원/꼭짓점이 관절 위(align 수리 반영)를
    확인하고 evidence/EYE-VERDICT.md 에 판정 기록 (몽타주 금지 — 개별 원본).
    커밋 3: test(quick-260813-fxx) 배선 검증 사다리 + 기계 증명 + 육안 기록.

    완료 보고에 명시: Pod 실증 미수행 (Pod 터미네이트 — 재개 시
    current-pod-cv8poc707mqtxh.md 6단계 재진입 후 별도 사이클), LLM 학습 영향
    없음 (Gemini 실호출 0 — 스텁, 학습 전송 0).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && backend/.venv/bin/python .planning/quick/260813-fxx-belle-3-p3r1-pass-v-p3-align-fps-5-pytes/verify_wiring.py --check 2>&1 | grep -q "WIRING-CHECK PASS" && PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests 2>&1 | tail -1 | grep -o "59 failed" && test -f .planning/quick/260813-fxx-belle-3-p3r1-pass-v-p3-align-fps-5-pytes/evidence/EYE-VERDICT.md</automated>
  </verify>
  <done>WIRING-CHECK PASS (결정론 2회 + freeze 일치 + 의도-변경-국한 + align 예측 대조 + 승인 9/9) + pytest 59 failed 기준선 동일(신규 실패 0) + 카드 2장 육안 판정이 EYE-VERDICT.md 에 실물 기록.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| 없음(신규) | 네트워크 신규 0 — Gemini 는 검증 전 구간 스텁, Firestore/S3 는 캐시 부재 시 읽기 전용 fetch 만 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-fxx-01 | Tampering | display 좌표 (표시 계층) | mitigate | conf>=0.5 fail-closed — 미달 카드 미방출, 엉뚱한 좌표 폴백 경로 부재 |
| T-fxx-02 | Info Disclosure | display_anchor 로그 | accept | 정규화 좌표·인덱스만 — PII/시크릿 0, 키 값 로그 금지 관례 유지 |
| T-fxx-03 | DoS | 렌더 경로 예외 | mitigate | _run_gated_card_inherit graceful 관례 유지 (재raise 0 — 기존 카드 폴백) |
| T-fxx-SC | Tampering | 패키지 설치 | accept | 신규 설치 0 (기존 venv 만) — legitimacy 게이트 해당 없음 |
</threat_model>

<verification>
- 채점 무접촉: 산식 5파일 diff 0 (Task 2 게이트) + freeze/survivors 불변 (Task 3)
- 결정론: 별도 프로세스 2회 완전 동일 (Task 3)
- 분기 0: 배선 diff 에 동작명/분석 ID 리터럴 0 (Task 2 게이트) — 좌표 공식은
  전 관절·전 분석 단일 공식, 문법 선택만 D-41 접미사 선언 데이터
- pytest 기준선 59 failed 동일, 신규 실패 0
- frames-before-numbers: 카드 2장 실물 Read 육안 후에만 완료 선언
</verification>

<success_criteria>
- belle 라운드 3 최종 판정이 JUDGMENT.md 에 원문 인용 + 불일치 장부로 박제됨
- 확정 angle 카드의 크롭 중심·앵커·꼭짓점 = align 게이트 순간 단일 출처 (실행 로그로 증명)
- 골반 카드 = P3 하이브리드 / 팔꿈치 = 기존 V — 하네스 인증 문법과 실물 일치
- WIRING-CHECK PASS + pytest 59 + 육안 기록 — 커밋 3개 (docs/feat/test)
- Pod 실증·마크 미세조정·오프셋 규칙은 명시적 범위 밖으로 보고
</success_criteria>

<output>
완료 시 `.planning/quick/260813-fxx-belle-3-p3r1-pass-v-p3-align-fps-5-pytes/260813-fxx-SUMMARY.md` 작성 —
기계 판정 결과(WIRING-CHECK 각 항목), 육안 판정, 한계 박제(vertex 경로 미성립
카드 범위 밖·advisory 좌표 종전·÷9.0 표기 잔존), LLM 학습 영향(없음 — 스텁),
다음(= Pod 재진입 후 운영 실증 + belle 카드 실물 판정 + 미세조종 라운드).
</output>

---
quick_id: 260813-fxx
slug: belle-3-p3r1-pass-v-p3-align-fps-5-pytes
completed: 2026-08-13
commits:
  - 4c29ada0 docs(quick-260813-fxx) JUDGMENT 라운드 3 최종 판정 박제
  - 31d6a82d feat(quick-260813-fxx) 확정 카드 표시 좌표 align 단일 출처 + 골반 P3 하이브리드 이식
  - b686fbbb test(quick-260813-fxx) 배선 검증 사다리 + 기계 증명 + 육안 기록
---

# 260813-fxx Summary — 선 문법 운영 배선 (P3 골반 이식 + 표시 좌표 align 단일 출처)

**한 줄**: belle 라운드 3 최종 판정(P3r1 PASS·팔꿈치 오프셋 반려·미세조정 이연)을
장부에 박제하고, 3라운드 하네스가 인증한 것을 운영 코드로 이식 — 확정 angle
카드의 크롭 중심·원 앵커·V 꼭짓점이 fps 라벨 사슬(`_to_rep_idx`) 대신 게이트
freeze 순간의 align 17-kp 단일 출처(display_anchor, conf>=0.5 fail-closed)에서
나오고, 골반 카드 user 패널은 bz5 하이브리드(쐐기+화살촉 상시, 고스트 델타>=8도)
문법으로 방출된다. 채점 무접촉·분기 0·Gemini 실호출 0.

## 기계 판정 (WIRING-CHECK — evidence/wiring_check.json)

- **결정론 PASS**: 별도 프로세스 2회 — pngMd5/survivors/dropped 완전 동일.
- **freeze 전건 일치 PASS**: survivors `['r03:inherit@u16.667/r15.20',
  'r00:inherit@u5.302/r5.13']` == gr.FREEZE_SEC 포맷 그대로 (순간 발명 0,
  ufb 불변식 유지).
- **의도-변경-국한 PASS**: 대상 2카드만 md5 변경 (left_elbow `9891d281…` →
  `4bbb688d…`, left_hip `8e147209…` → `ece60417…`) + survivors/dropped/advisory
  전부 ufb 인증값과 일치 + manifest 키셋 동일 + display_anchor drop 0건.
- **align 예측 대조 PASS**: 실행 로그의 (u_ai, r_ai, 좌표)를 --check 프로세스가
  align 독립 재구축 + `cg.align_to_report` + `cg.kp(conf_min=0.5)`로 재계산해
  전건 일치. **hip vertex 이동 실측 = user 1.65px / ref 8.67px** — P3r1 실측
  (user 1.6 / ref 8.7) 적중 (현행 크롭 박스 px 환산이라 근사 대조, 기록 전용).
- **승인 무회귀 PASS**: vl.approved() 위임 — joint-scope hold 9/9 + pair 9/9
  (ii0 정본, 오프라인).
- **pytest 기준선 동일**: 59 failed / 4157 passed — 신규 실패 0 (신규 테스트
  8건 전부 PASS 포함).
- **분기 0**: 배선 diff 추가 라인에 동작명/분석 ID 리터럴 0 (기계 grep). 좌표
  공식은 전 관절·전 분석 단일 공식, 문법 선택만 `HYBRID_ANGLE_SUFFIXES={"hip"}`
  접미사 선언 데이터 (D-41).
- **채점 무접촉**: 산식 5파일(deduction_engine/dimensions/kismam/motiondtw/
  assemble) diff 0 (기계 게이트) + records/freeze 선정/게이트 임계 무변경 —
  survivors/dropped 불변이 그 증거.

## 육안 판정 (frames-before-numbers — evidence/EYE-VERDICT.md)

- **골반 카드 PASS**: user 패널 = P3 하이브리드 실물 확인 (실선 V + 반투명
  쐐기 + 화살촉 + 고스트 점선 — 델타 8도 이상이라 방출), ref 패널 = 기존 V.
  양 패널 마크가 왼골반 위 (3배 크롭 확인).
- **팔꿈치 카드 PASS**: 양 패널 기존 V 문법 그대로 (하이브리드/오프셋 요소 0),
  꼭짓점 = align 수리 좌표 — ref 꼭짓점이 팔꿈치 점 위에 앉음 (라운드 2
  1프레임 skew 소멸 자리, E3r1 belle 육안 PASS 좌표와 같은 출처). user 패널
  V 가닥이 역립 얼굴 위를 지나는 것은 belle 판정 ②③으로 현행 유지가 스펙
  (미세조정 이연).

## 구현 (커밋 31d6a82d)

- `fault_zoom.build_fault_zoom_comparisons(display_anchor=None)` keyword-only
  신설 — None(default) = 전 경로 byte-동일 (신규 테스트 + 기존 fault_zoom
  테스트 178건 무접촉 PASS 가 증명). 지정 시 vertex 경로 성립 카드에서만 값
  교체: 크롭 중심(`_side_crop` center)·원 앵커(정중앙 경로 center 파생)·V
  스펙(`shift_bake_spec` 3점 평행이동 — 사이각·방향 보존, round3
  `_R3Patch._repaired_pts` 동치).
- `app.py _run_gated_card_inherit` units 루프: angle unit 만
  `cg.kp(urep15/rrep15, round(sec*afps), joint, conf_min=0.5)` 산출 — 한쪽이라도
  미달 = 그 unit 카드 미방출 + drop 로그 (fail-closed, rep12 폴백 금지). 성립 =
  display_anchor 실행 로그 (wiring-claims-need-log-evidence).
- 골반 하이브리드: bz5 `_draw_candidate(hybrid)` 운영 이식
  (`_draw_hybrid_joint_angle` + 상수 5종 이식값 그대로 — 신규 튜닝 0). ref 내각은
  패널 px 공간 측정(`_spec_inner_deg_px`), 비유한 = 기존 V 양 패널 폴백 + 로그
  `hybrid_fallback` 표기. both-or-neither·원 생략·타임스탬프 로직 무변경.
- 테스트 8건 (test_fault_zoom_display_repair.py): 평행이동 px-내각 보존 /
  ghost 경계 게이팅 (7.9 미방·8.0 방출) / display_anchor None byte-동일 +
  지정 시 실변경 / hybrid True·degenerate False (부분 드로잉 0).

## 한계 박제 (수리 범위 밖 — 재조사 금지)

- vertex 경로 미성립 카드(relaxed/전신 폴백 등)는 display_anchor 미적용 —
  기존 동작 보존 (이번 수리는 확정 single-joint angle 카드 한정).
- advisory 카드 좌표·링 위치는 종전 그대로 (pass-through — 게이트 대상 아님).
- 카드 초 표기 ÷9.0 잔존 (kpo 유보 — 별건 유지).
- 오프셋/제자리 전환 규칙(비역립 국면)은 결정 사항으로 남음 — 이번엔 팔꿈치
  문법 무변경이라 미결이 소비되지 않음.
- hip 이동량 px 대조는 근사 (P3r1 은 크롭 무변경 박스 측정, 운영은 크롭도
  이동) — 기록 전용, 게이트 아님.

## Deviations

없음 — 플랜 그대로 실행 (plan-checker 노트 3건 반영: W-1 추가 라인만 리터럴
검사, I-1 survivors 포맷 `u{:.3f}/r{:.2f}`, I-2 manifest 키셋 + 비대상
md5/advisory/dropped 인증값 대조).

## LLM 학습 영향

**없음.** Gemini 실호출 0 — grammar_round machine_eye 스텁 + env 더미 키 상속
(run 당 eye stub calls 2, 전부 스텁), 학습 전송 0, 눈 원장 신규 적재 0 (스텁
산출물은 evidence/_ev 비커밋 영역 한정).

## 다음 (이 사이클 완료 정의 아님)

- **Pod 실증 미수행 (별도 사이클)** — Pod 터미네이트 상태. 재개 시
  current-pod-cv8poc707mqtxh.md 6단계 재진입 후 실분석으로 display_anchor
  로그 + 카드 실물 확인 (무인 실행 약속 아님).
- belle 카드 실물 최종 판정 (수리 후 골반 하이브리드 + 팔꿈치 좌표 수리 실물).
- 마크 위치 미세조종 라운드 (belle 판정 3 — 배선 완료 후).

## Self-Check: PASSED

- 산출물 존재: fault_zoom.py display_anchor/HYBRID 배선 + app.py 배선 +
  test_fault_zoom_display_repair.py(8 pass) + verify_wiring.py +
  evidence/{wiring_check.json, once1.json, once2.json, cards 2장, crops 4장,
  EYE-VERDICT.md, .gitignore} + JUDGMENT.md 라운드 3 최종 판정 절(append-only,
  삭제 라인 0)
- 커밋 존재: 4c29ada0 / 31d6a82d / b686fbbb — 파일 삭제 0 (diff-filter=D 빈 출력)
- 게이트: WIRING-CHECK PASS 2회 실행 로그 + pytest 59 failed 기준선 동일 +
  산식 5파일 diff 0 + 리터럴 grep 0

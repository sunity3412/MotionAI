---
quick_id: 260811-kpo
slug: gate-wiring-3-pod
date: 2026-08-11
status: planned
description: 운영 배선 — ii0 성립 게이트(홀드/짝정합/기계눈)를 카드 생산 경로에 심고 Pod 재분석으로 왼골반 소멸 + 왼무릎 방출 실증
files_modified:
  - backend/shared/python/sunity_shared/analysis/card_gates.py
  - backend/functions/pipeline/app.py
  - backend/tests/test_card_gates.py
  - .planning/quick/260811-kpo-gate-wiring-3-pod/verify_local.py
autonomous: true
must_haves:
  truths:
    - "운영 재분석(Pod)에서 왼골반(left_hip) 카드가 방출되지 않는다"
    - "운영 재분석에서 왼무릎(left_knee) 카드가 홀드 성립 + 같은 국면 짝으로 방출된다"
    - "승인 코퍼스 joint-scope 정지 9/9 생존 + align-peak 3건 비구속 (무회귀)"
    - "게이트가 운영 경로에서 실제 호출됐음이 실행 로그 라인으로 증명된다"
    - "재분석 점수는 60점 그대로 (채점 무접촉 — 재현성 보존)"
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/card_gates.py"
      provides: "hold_gate / pair_gate / detect_pole_x / machine_eye + 확정 임계 (ii0 이식)"
    - path: "backend/functions/pipeline/app.py"
      provides: "compare_render 스테이지 뒤 게이트-상속 카드 빌더 + verdict 로그"
    - path: "backend/tests/test_card_gates.py"
      provides: "게이트 순수 함수 단위 테스트 (합성 트랙)"
    - path: ".planning/quick/260811-kpo-gate-wiring-3-pod/verify_local.py"
      provides: "fresh doc 정답표 대조 + 승인 무회귀 로컬 드라이버"
  key_links:
    - from: "backend/functions/pipeline/app.py (_run_deferred_compare_render)"
      to: "card_gates"
      via: "리그 PASS 후 freeze 게이트 판정 + 카드 상속 렌더"
      pattern: "card_gates"
    - from: "게이트 판정 트랙"
      to: "align (compare_align.build_align 산출, 15fps RTMW17)"
      via: "card_gates.align_to_report — doc keypointReport 사용 금지 (fps 라벨 오차)"
    - from: "상속 카드"
      to: "fault_zoom.build_fault_zoom_comparisons"
      via: "dtw_match=None + user_frame_idx/ref_frame_idx override (bz5 하네스 실증 경로)"
---

# 성립 게이트 운영 배선 + Pod 실증

<objective>
260811-ii0 에서 완성·스윕 검증된 성립 게이트 3종(홀드/짝정합/기계눈)을 실제 카드 생산
경로에 심는다. 카드는 그 분석의 합성 비교 영상 정지(freeze)에서 상속하고, 게이트
생존자만 dev 내림차순으로 카드를 받는다 (record 순서 상한 구조 제거). Pod 재분석으로
"왼골반 카드 소멸 + 왼무릎 카드 방출"을 실증한다.

Purpose: 같은 영상이 분석마다 다른 감점 카드를 내고, 환각 순간(전환 111도/초,
221도/초)이 카드가 되는 병의 운영 수리. ii0 는 게이트가 판별함을 기계 증명했고
(승인 9/9 생존 + 왼골반 이중 기각 + 왼무릎 r03 상속 성립), 이번은 그 배선이다.
Output: card_gates.py(운영 모듈) + app.py 배선 + 로컬 정답표 검증 + Pod 실증 + SUMMARY.
</objective>

<context>

## 필독 (이 순서로)

1. `.planning/CONTINUE-2026-08-11.md` — 방법의 기초(영상이 정답표다)·프로세스 0~6·규율
2. `.planning/quick/260811-ii0-card-gates-5/260811-ii0-SWEEP-REPORT.md` — 확정 임계 +
   게이트 적용 범위(src 기준) + 신규 발굴 한계(kneepath) + 미달 박제
3. `.planning/quick/260811-ii0-card-gates-5/gates.py` — 이식 원본 (순수 함수 3종)
4. `.planning/quick/260811-bz5-mark-grammar/render_harness.py` — 지정 순간 카드 렌더의
   운영 함수 호출 패턴 (fetch / native_provider / round-trip 인증)
5. `.planning/quick/260811-bz5-mark-grammar/260811-UNIFY-FINDINGS.md` — 정답표·수리 스펙 v1

## 실물 좌표 (플랜 조사 확정 — 재탐색 불요)

- 카드 운영 경로: `backend/functions/pipeline/app.py` 스테이지 순서 =
  complete → coach_audio → **fault_zoom(카드, 7289)** → spot_check →
  **compare_render(영상, 7348)**. 영상 freeze 는 `compare_render.build_timeline`
  (compare_render.py 1123-1321, `pair_src` 가 src 구분), 리그 PASS 후 report 에
  `freezes[]` (rid/userSec/refSec/pairSrc) 박제.
- record 순서 상한: `fault_zoom.criterion_units_from_records(max_units=4)` —
  records 순서대로 4개에서 break. **정렬을 바꿔 넣으면 fault_zoom 무접촉으로 해결.**
- 지정 순간 카드 렌더: `fault_zoom.build_fault_zoom_comparisons(dtw_match=None,
  user_frame_idx=, ref_frame_idx=, criterion_units=, native_frame_at=)` — bz5 하네스가
  round-trip 인증까지 실증한 운영 함수 경로 (fault_zoom.py 2640-2709). 초→9fps 인덱스
  환산은 **실효 rate** (`probe_effective_fps`, ÷9.0 금지 — 08-10 뿌리 원인).
- 카드 사후 부착: `firestore_admin.update_analysis_fault_zoom` (app.py 3845) —
  부분 갱신이라 compare_render 스테이지 뒤에서 대체 부착 가능.
- 폴 축: compare_render 는 render() 진입 시 `_detect_pole` 결과(poles dict)를 이미
  가진다 — 재검출 대신 재사용. 몸통 단위 환산은 card_gates.torso_px_median.
- Gemini 운영 조건: Pod `backend/runpod_inference/start_server.sh` 32-33행이 SSM
  `/sunity/motion/gemini-api-key` → `GEMINI_API_KEY` export. compare_render 스테이지는
  Pod 에서만 돈다 (Lambda 는 capability 프로브 스킵) — Lambda 무부담.
- fresh doc: uid `fvcNXzEqKjgqVxRPVSj1iwFnIpn2` / `p34fresh1786363530` (60점, record
  5종). bz5 scratchpad 캐시는 다른 세션 디렉터리라 **휘발 — fetch 재실행 필요**.
- 승인 코퍼스 데이터: `.planning/phases/35-server-rendered-comparison-video/data/*/`
  (align.json + doc.json 7건) + ii0 `sweep_gates.py` / `run_probes.sh`.
- 인증: `FIREBASE_SA_PATH=firebase-sa.json`(리포 루트) · `AWS_PROFILE=sunity-motion` ·
  Gemini 키 = SSM `/sunity/motion/gemini-api-key` · python = `backend/.venv/bin/python`.

## 확정 사항 (belle — 재질문·재해석 금지)

- 영상이 정답표: 카드는 영상 정지에서 상속. 조정은 영상보다 나아질 때만(게이트 전건
  통과), 실패 시 영상 정지 그대로 = fail-closed. 영상에 없는 결함 추가는 풀 게이트로만.
- 임계 (ii0 확정, 튜닝 금지): hold < 60도/초(3창 Theil-Sen 최소) · pose < 0.85(가중
  모드) · poleDiff < 0.375 몸통. 동작명 분기 0 (D-41).
- 카드 배정 = 게이트 생존자 dev 내림차순 (상한 4장은 유지, 순서 상한만 제거).
- 채점 무접촉: deduction_engine/dimensions/kismam/motiondtw/assemble diff 0.
  B1(측정창 홀드 제한)은 범위 밖.
- 기계 눈: 관절 마킹 크롭 Gemini 판정, 좌우 해부학 이름 금지. 감점 주장과 일치할
  때만 방출.
- 귀속 표현: 각도 편차 + 폴거리 차 동시 발생 → 폴 이탈 계열 (r03 문법 재사용).
  각도 문구는 홀드 성립 시에만. 기결론(왼팔꿈치=폴 이탈·각도 수치 미노출) 재질문 금지.
- 통과 무접촉 보존: 승인 합성 영상 5편(P35 v7) 정지·표시·문구, 채점 재현성(60점),
  ms2 크롭 품질.
- 게이트 판정 트랙 = align(재추출 정본) 고정. doc keypointReport 는 fps 라벨 오차
  (라벨 18 vs 실효 20.1)로 게이트 판정에 부적합 (ii0 발견 4).

</context>

<tasks>

<task type="auto">
  <name>Task 1: card_gates 이식 + compare_render 스테이지 카드 상속 배선</name>
  <files>backend/shared/python/sunity_shared/analysis/card_gates.py, backend/functions/pipeline/app.py, backend/tests/test_card_gates.py</files>
  <action>
(1) **이식**: ii0 `gates.py` 를 `sunity_shared/analysis/card_gates.py` 로 이식.
hold_gate(3창 최소 Theil-Sen) / pair_gate(가중 포즈거리 + 폴 parity, 폴 미검출은
비차단) / detect_pole_x / machine_eye / align_to_report / torso_px_median /
body_pole_dist. 임계는 확정값 상수(HOLD_MAX_DPS=60, PAIR_POSE_MAX=0.85,
POLE_DIFF_MAX=0.375)로 박고 근거를 docstring 에 ii0 스윕 보고서 좌표로 인용.
sys.path 조작 제거, 상대 import (`from . import fault_zoom as fz`). fail-closed
의미론(측정불가=FAIL, eye 네트워크 실패=match False) 그대로. machine_eye 는 ii0
미달 3의 지정 수리를 반영해 **2단 판정**으로 확장: 응답 스키마에 "원 안의 관절이
어느 사지 종류(팔/다리)인지"를 함께 받고, 부위 종류가 claim 의 사지와 다르면
불일치 처리 (마크-전위 구멍 — kneepath 실측. 좌/우 이름 금지는 유지).

(2) **배선**: `_run_deferred_compare_render` 의 리그 PASS 분기(업로드·done 부착
이후)에서 새 헬퍼 `_run_gated_card_inherit(...)` 호출. 헬퍼 동작:
  a. report["freezes"] 를 pairSrc 로 분류 — `align-peak` = 절정 표시 축이라
     홀드/포즈 parity **비구속**(ii0 발견 1, 그대로 통과), 그 외 joint-scope = 게이트.
  b. joint-scope freeze 마다 align 트랙(card_gates.align_to_report)에서 (userSec,
     refSec)→15fps 인덱스로 hold_gate + pair_gate. 폴 x 는 render 가 이미 계산한
     poles 재사용 (부재 시 비차단). 기계 눈 claim 은 트랙 각도 이분 판정
     (ii0 sweep_gates 방식 — 중간각은 eye 미적용, hold/pair 만).
  c. PASS freeze → 카드 순간 = freeze 그대로 (±0.4s 급 소폭 보정은 게이트 전건
     통과 + 포즈거리 개선 시에만, 아니면 freeze 유지 — fail-closed).
  d. FAIL freeze → 재정박: 그 관절의 홀드 성립 순간들(hold_gate PASS)에서 ref 후보
     (align curve 근방)와 풀 게이트(홀드+짝+기계 눈 **양측**) 통과 후보 중
     **포즈거리 최소** 선택. 탐욕 최대편차 선택 금지 — ii0 kneepath(16.33s, d=0.81
     수치 통과·육안 다른 국면) 실측이 근거. 후보 0 = 그 record 카드 미방출
     (정직한 침묵 — 왼골반 기대 경로). eye 호출은 최종 후보에만 (카드당 ≤2회).
  e. 배정: 생존 record 를 |dev|(deficitDeg/delta) 내림차순 정렬 후
     `criterion_units_from_records(max_units=4)` 에 그 순서로 전달 — fault_zoom
     무접촉으로 순서 상한 제거.
  f. 렌더: `fault_zoom.build_fault_zoom_comparisons(dtw_match=None,
     user_frame_idx=, ref_frame_idx=, criterion_units=, native_frame_at=)` —
     bz5 하네스 실증 경로. 초→9fps 인덱스 = 실효 rate 환산. S3 업로드는 기존 키
     규칙(zoom_ prefix, _render_fault_zoom 후반 로직 재사용 또는 추출) →
     `update_analysis_fault_zoom` 로 기존 카드 **대체 부착**.
  g. 귀속 표현(additive): 방출 카드가 각도 편차 축이고 pair_gate 가 잰 폴거리 차가
     성립하면 item 에 `attribution: "pole_proximity"` 필드 추가 (r03 문법 계열 문구는
     표현 레이어 소비 — records cueLine/statusLine 무접촉, 승인 5편 문구 불변).
     각도 문구/사이각 표시는 홀드 성립 카드에만 (b~d 구조가 이미 보장).
  h. **실행 로그 = 배선 증거**: `log.info("card_gates verdict analysis_id=%s
     total=%d survivors=%s dropped=%s reanchored=%s eye_calls=%d", ...)` 1줄 필수
     — 커밋·테스트 통과만으로 배선 단정 금지 (wiring-claims-need-log-evidence).
  i. Fail-closed 층위: 헬퍼 내부 어떤 실패도 재raise 0 (graceful) — fault_zoom
     스테이지 카드가 이미 도착해 있어 자연 폴백. mode3/Lambda/비기준 경로는
     compare_render 스킵이라 기존 카드 그대로 (blast radius 0).

(3) **테스트**: `backend/tests/test_card_gates.py` — 합성 트랙으로 hold 안정 PASS /
전환 3창 전부 높음 FAIL / 측정불가 FAIL(fail-closed) / pair 원거리 포즈 FAIL /
폴 미검출 비차단, 총 5케이스 내외 (수치 채우기 금지 — 판별 경계만).

금지: 채점 5파일 접촉, 동작명 리터럴 분기, 임계 재튜닝, heredoc 파일 생성.
커밋 2개 분리: card_gates 모듈+테스트 / app.py 배선.
  </action>
  <verify>
    <automated>PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests/test_card_gates.py && git diff HEAD~2..HEAD --name-only | grep -vE "card_gates|test_card_gates|app\.py" | grep -c "analysis/(deduction_engine|dimensions|kismam|motiondtw|assemble)\.py" | grep -qx 0 && grep -q "card_gates verdict" backend/functions/pipeline/app.py && echo WIRED</automated>
  </verify>
  <done>card_gates.py 가 확정 임계로 존재, app.py compare_render 스테이지가 게이트 판정 후 상속 카드를 대체 부착, verdict 로그 라인 존재, 신규 단위 테스트 통과, 채점 5파일 diff 0.</done>
</task>

<task type="auto">
  <name>Task 2: 로컬 검증 사다리 — fresh doc 정답표 + 승인 무회귀 + pytest 기준선</name>
  <files>.planning/quick/260811-kpo-gate-wiring-3-pod/verify_local.py, .planning/quick/260811-kpo-gate-wiring-3-pod/evidence/</files>
  <action>
(1) **로컬 드라이버** `verify_local.py`: bz5 render_harness 의 fetch/native_provider
패턴 재사용 (캐시는 이 세션 scratchpad 로 새로 fetch — 구 캐시 휘발). fresh doc
(uid fvcNXzEqKjgqVxRPVSj1iwFnIpn2 / p34fresh1786363530) + S3 원본 영상 2편으로
**배선한 운영 함수를 그대로** 구동: compare_align.build_align → build_timeline
freezes → `_run_gated_card_inherit` 와 동일 경로(같은 헬퍼를 import 하거나 S3/Firestore
부착만 스텁) → 카드 PNG 를 out/ 에 산출. 하네스가 다른 함수를 부르면 배선 검증이
아니다 (U6 교훈 — 운영 경로 호출 증거 필수).

(2) **정답표 대조 (사전 박제 → 프레임 실물)**: 내 판정을 먼저 기록한 뒤 카드 PNG
전부 직접 열어 확인 (frames-before-numbers):
  - 왼무릎 카드 **존재** + 홀드 성립 순간 + 같은 국면 짝 (ii0
    evidence/r03inherit_*.png 와 대조 — u≈3.667s/r≈2.4s 계열이면 그대로 인증,
    다른 홀드 순간이면 양 패널 프레임을 열어 같은 국면인지 육안 판정 후 박제).
  - 왼골반 카드 **없음**.
  - 왼팔꿈치 카드 생존 (기결론 축 — attribution=pole_proximity 부착 확인, 각도 수치
    미노출 유지).
  - 근거 프레임·카드를 evidence/ 에 저장.

(3) **승인 무회귀**: P35 `data/*/` 7건의 승인 정지(ii0 run_probes 정본 + r01
오버라이드)에 card_gates 를 적용해 ii0 스윕 결과 재현 — joint-scope 9/9 생존 +
align-peak 3건 비구속 = 이식 등가성 증명. 승인 정지가 하나라도 죽으면 이식 결함
(임계 완화 금지 — 이식 코드를 의심할 것).

(4) **pytest 전체**: `PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q
backend/tests` — 실패 집합이 기준선 59건과 **동일**해야 함 (신규 실패 0,
phase35 픽스처 포함. ms2 선례: "59 failed IDENTICAL / 4141 passed").

미달 시: 어디까지 왔고 무엇이 막았는지 evidence 와 함께 박제하고 멈춘다 —
정답표를 맞추려 임계·선택 규칙을 fixture 에 맞춰 조정하는 것 금지 (curve-fit 금지).
  </action>
  <verify>
    <automated>backend/.venv/bin/python .planning/quick/260811-kpo-gate-wiring-3-pod/verify_local.py --check 2>&1 | grep -E "left_knee CARD|left_hip ABSENT|approved 9/9" && PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests 2>&1 | tail -1</automated>
  </verify>
  <done>정답표 3항(왼무릎 카드 홀드 국면 / 왼골반 카드 0 / 왼팔꿈치 생존+귀속) 충족을 카드 실물로 확인, 승인 정지 9/9 생존 재현, pytest 실패 집합 기준선 59건 동일.</done>
</task>

<task type="auto">
  <name>Task 3: Pod 실증 — push → 재기동 → 재분석 → 로그·카드 실물 + SUMMARY</name>
  <files>.planning/quick/260811-kpo-gate-wiring-3-pod/260811-kpo-SUMMARY.md</files>
  <action>
순서 고정 (current-pod-cv8poc707mqtxh 재진입 절차):
1. 커밋 **push 먼저** (gsd-pod-work-push-first).
2. `ssh root@213.173.110.74 -p 11638 -i ~/.ssh/id_ed25519` → /workspace 리포
   `git fetch && git merge --ff-only`.
3. **FastAPI 서버 재기동 필수** — 옛 모듈을 물고 있다 (8커밋 뒤처짐 실측 이력).
   `start_server.sh` 로 재기동 (GEMINI_API_KEY SSM 주입 포함 — 기계 눈 운영 조건).
   기동 파일은 md5 로 리포 정본과 대조 (start_p15_server.sh 함정).
4. `/health` 의 commitSha == 로컬 HEAD 확인.
5. 재분석: 프로덕션 env 그대로 — `source /workspace/aws_env.sh && source <(sed -n
   '3,34p' /workspace/start_server.sh)` 후 belle pdshape 영상 재분석 (기존 p34fresh
   재분석 드라이버 경로, 새 analysis_id).
6. 실증 수집 (전부 SUMMARY 에 박제):
   a. 서버 로그의 `card_gates verdict` 라인 실물 (survivors/dropped/reanchored) —
      이것이 배선 증거. 없으면 배선 실패로 판정하고 원인 추적.
   b. 새 doc `faultZoomComparisons` — left_hip 항목 없음 + left_knee 항목 있음.
   c. 카드 PNG 를 S3 에서 내려받아 **직접 열어** 프레임 확인 (frames-before-numbers)
      — 왼무릎 카드가 홀드/같은 국면인지 육안 판정 박제.
   d. 새 doc 점수 == 60 (채점 무접촉·재현성 보존 증거).
   e. renderedCompare 상태 done (영상 스테이지 무회귀).
7. SUMMARY.md: 기계 판정 한 줄(왼골반 소멸 + 왼무릎 방출 + 승인 무회귀 + 로그 증거)
   + 커밋 목록 + 미달/유보 정직 박제 + LLM 학습 영향(추론 호출만이면 "없음") 명기.
   SSM runpod-analyze-url 은 Pod 동일·주소 불변이라 갱신 불필요.

주의: Pod 는 스톱 말고 그대로 둔다 (종료 제안 금지 — 메모리 규율). 재분석 실패 시
서버 로그·verdict 라인까지 수집한 상태로 박제하고 멈춘다.
  </action>
  <verify>
    <automated>ssh -p 11638 -i ~/.ssh/id_ed25519 root@213.173.110.74 "curl -s localhost:8000/health" | grep -o "\"commitSha\":\"[a-f0-9]*\"" && git rev-parse --short HEAD</automated>
  </verify>
  <done>Pod /health commitSha == HEAD, 재분석 새 doc 에서 왼골반 카드 부재 + 왼무릎 카드 존재를 doc·PNG 실물로 확인, card_gates verdict 로그 라인 수집, 점수 60 유지, SUMMARY 커밋 완료.</done>
</task>

</tasks>

<threat_model>
| Threat ID | Category | Component | Disposition | Mitigation |
|-----------|----------|-----------|-------------|------------|
| T-kpo-01 | Information Disclosure | machine_eye Gemini 호출 | mitigate | GEMINI_API_KEY 는 env 로만 (로그·커밋 금지), 크롭 이미지 외 개인정보 미전송, 추론 호출만 (학습 재료 무접촉) |
| T-kpo-02 | Tampering | S3 카드 대체 부착 | mitigate | 기존 키 규칙(results/{uid}/{aid}/zoom_*) 유지 — 신규 네임스페이스 0, 실패 시 재raise 0 으로 기존 카드 보존 |
| T-kpo-03 | DoS (비용) | 기계 눈 호출 폭주 | mitigate | eye 호출은 최종 후보에만, 카드당 ≤2회 상한 (구독료 하한 내 — UNIFY 스펙 4) |
| T-kpo-SC | Tampering | 패키지 설치 | accept | 신규 패키지 0 (표준 lib + 기존 의존만) — 설치 태스크 없음 |
</threat_model>

<verification>
- 배선 주장은 실행 로그로: Pod 서버 로그의 card_gates verdict 라인이 최종 증거.
- 카드·판정은 근거 프레임 실물 확인 후에만 제시 (frames-before-numbers).
- 승인 코퍼스 무회귀: joint-scope 9/9 생존 + align-peak 비구속 + pytest 기준선 59
  동일 + 승인 5편 렌더 산출 불변.
- 채점 무접촉: 채점 5파일 diff 0 + 재분석 점수 60 동일.
</verification>

<success_criteria>
- [ ] card_gates.py 운영 모듈 (확정 임계, 동작명 분기 0, fail-closed) + 단위 테스트
- [ ] compare_render 스테이지 뒤 게이트-상속 카드 대체 부착 + verdict 로그
- [ ] 로컬 정답표: 왼무릎 카드(홀드/같은 국면) + 왼골반 카드 0 + 왼팔꿈치 생존·귀속
- [ ] 승인 정지 9/9 생존 재현 + pytest 기준선 59 동일
- [ ] Pod 실증: /health HEAD 일치 → 재분석 → doc·PNG·로그 실물 3종 + 점수 60
- [ ] SUMMARY.md (기계 판정 한 줄 + 증거 + 미달 정직 박제 + LLM 학습 영향)
</success_criteria>

<output>
완료 시 `.planning/quick/260811-kpo-gate-wiring-3-pod/260811-kpo-SUMMARY.md` 작성.
커밋: conventional commits 한국어 요약 (예: `feat(quick-260811-kpo): 성립 게이트 운영
배선 — 카드 = 영상 정지 상속 + 게이트 생존자 dev 순`).
</output>

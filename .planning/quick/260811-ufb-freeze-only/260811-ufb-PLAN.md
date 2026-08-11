---
quick_id: 260811-ufb
slug: freeze-only
date: 2026-08-11
status: planned
description: 수리(260811-kpo 반려) — 확대 비교 카드 = 승인 영상 freeze 순수 상속 + 확대만. 재정박(새 순간 탐색)·절정 재배치 제거, 게이트는 방출 게이트로 축소
files_modified:
  - backend/functions/pipeline/app.py
  - .planning/quick/260811-ufb-freeze-only/verify_local.py
autonomous: true
must_haves:
  truths:
    - "방출된 모든 카드의 순간(u_sec, r_sec)이 그 분석 영상 freezes[] 의 (userSec, refSec)와 전건 일치 — 순간 발명 0"
    - "같은 입력 2회 연속 실행 결과 동일 (카드 목록·순간·PNG 해시) — 재정박 비결정 소멸"
    - "게이트 실패 freeze 는 그 카드 미방출 (정직한 침묵) — 대체 순간 탐색 코드·로그 0"
    - "승인 코퍼스 joint-scope 9/9 생존 + pytest 기준선 59 동일 + 재분석 점수 60 (채점 무접촉)"
    - "Pod verdict 로그가 상속/미방출만 보고 — reanchor 경로 부재가 운영 로그로 증명"
  artifacts:
    - path: "backend/functions/pipeline/app.py"
      provides: "_run_gated_card_inherit 방출 게이트 전용판 (재정박/절정 재배치/±조정 부재, verdict 로그에 방출 순간 포함)"
    - path: ".planning/quick/260811-ufb-freeze-only/verify_local.py"
      provides: "freeze 전건 일치 + 2회 결정론 + 승인 무회귀 드라이버 (kpo 드라이버 적응)"
    - path: ".planning/quick/260811-ufb-freeze-only/evidence/"
      provides: "카드 실물 PNG + 크롭 재측정 + 사전/사후 판정 + 0장 거동 관찰"
  key_links:
    - from: "backend/functions/pipeline/app.py (_run_gated_card_inherit)"
      to: "report['freezes']"
      via: "u_sec/r_sec = freeze 값 그대로 (변형 연산 0)"
      pattern: "emitted.append\\(\\(rec, u_sec, r_sec"
    - from: "card_gates verdict 로그"
      to: "방출 순간 (rid@u/r)"
      via: "배선·불변식 증거 (wiring-claims-need-log-evidence)"
      pattern: "card_gates verdict"
    - from: "_run_gated_card_inherit"
      to: "fault_zoom.build_fault_zoom_comparisons"
      via: "_override_idx rep9 역변환 유지 (kpo 편차 2 — 무접촉)"
      pattern: "_override_idx"
---

# 확대 비교 카드 = 영상 freeze 순수 상속 + 확대만 (재정박 제거)

<objective>
260811-kpo 배선의 belle 반려 수리. 반려 원문이 스펙이다: "영상이라는 기본 승인
틀이 있는데 왜 자꾸 다르게 하는건지", "하다못해 확대를 해도 되겠구만", "조정을
좋은쪽으로 하라고 했지 이상한대를 비교하라고 하질 않았는데".

수리 = `_run_gated_card_inherit` 에서 **순간을 고르는 능력을 전부 제거**한다:
- 재정박(`_reanchor` — FAIL freeze 에 새 순간 탐색) 제거. kpo 실측: 12.8s 카드가
  재실행 시 10.5s 로 바뀌는 비결정 + freeze 에서 먼 순간 방출이 반려의 실체.
- 절정 재배치(각도-주장 align-peak freeze 를 측정 짝 순간으로 옮기는 블록) 제거.
  게이트는 이제 순간을 옮기지 않는다 — freeze 그 자리에서 판정만 한다.
- 게이트 = 방출 게이트만: freeze 가 홀드/짝정합/기계 눈을 통과하면 그 freeze 를
  확대한 카드 방출, 실패하면 그 freeze 카드 미방출 (정직한 침묵). ±0.4s 급
  소폭 조정도 제거 대상 — 현 구현에 없음을 실물로 확인하고 박제한다.

Purpose: 카드가 영상(승인 틀)과 다른 순간을 보여주는 병의 구조 제거. 순간 발명이
코드에서 사라지면 비결정도 구조적으로 사라진다 (escape-plan-fail-replan-treadmill
— 같은 서브시스템 3회째 수리, 구조 제거가 맞다: ms2 → kpo → 이번).
Output: app.py 수술 + 로컬 기계 증명(freeze 일치·결정론) + Pod 실증 + SUMMARY.
</objective>

<context>

## 필독 (이 순서로)

1. `.planning/quick/260811-kpo-gate-wiring-3-pod/260811-kpo-PLAN.md` — 직전 배선 구조
2. `.planning/quick/260811-kpo-gate-wiring-3-pod/260811-kpo-SUMMARY.md` — 편차 4건
   (특히 편차 1 절정 재배치, 편차 3 눈 상한 완화 — 둘 다 이번에 제거되는 경로)
3. `backend/functions/pipeline/app.py` 4367~4954 — `_run_gated_card_inherit` 실물
4. `.planning/quick/260811-kpo-gate-wiring-3-pod/verify_local.py` — 검증 드라이버 원본

## 확정 사항 (belle 반려 = 스펙, 재논의·재해석 금지)

- **LD-1 카드 순간 = 그 분석의 합성 비교 영상 freeze 그대로. 순간 발명 금지.**
  게이트 실패여도 다른 순간을 찾지 않는다 — 방출하지 않을 뿐.
- **LD-2 재정박 경로 제거.** (locked 는 "제거 또는 기본 OFF" — 이 플랜은 **제거**를
  택한다: 3회째 수리라 구조 제거가 규율이고, 코드는 git 이력(kpo 커밋 84dedb47/
  e1b0df81)에 보존된다. 미래 신규 발굴 사이클은 별도 설계 + belle 사전 대조.)
- **LD-3 게이트 역할 축소 = 방출 게이트만.** 홀드/짝정합/기계 눈 판정은 freeze
  그 순간에서. ±0.4s 소폭 조정 코드도 남기지 않는다.
- **LD-4 배정 = 생존 freeze 를 |dev| 내림차순, 상한 4장 유지** (kpo 와 동일 — 무접촉).
- **LD-5 카드 0장이어도 그대로 박제.** 단 이때 기존 fault_zoom 선착 카드가 남는지/
  남아야 하는지 **실물로 확인해 보고** (belle 결정 항목으로 SUMMARY 에).
- **LD-6 왼무릎 카드가 freeze 부재/게이트 실패로 안 나오면 그대로 보고.** 되살리려고
  재정박을 남기지 말 것.
- **LD-7 채점 무접촉.** 승인 5편 정지·표시·문구 불변. 임계 재튜닝 금지
  (hold<60도/초 · pose<0.85 · poleDiff<0.375 그대로).
- **LD-8 눈 원장 보존 유지** — 방출 게이트로 쓰인 판정도 S3 `eye/` 원장에 쌓인다.

## 실물 좌표 (플랜 조사 확정 — 재탐색 불요)

- 수리 대상: `app.py` 4367 `_run_gated_card_inherit`. 제거 대상 실물 =
  ① 절정 재배치 블록(4714~4737, `src == "align-peak"` 분기 안의 각도-주장 reroute
  — `align.get("pairs")` / `atVideoSec` 로 u_sec/r_sec 를 덮어쓰는 부분)
  ② `_reanchor`(4609~4687) + 호출부(4753~4758) ③ 재정박 전용 부속 =
  `_hold_angles`/`_hold_cache`(4588~4600), `_EYE_MAX_PER_RECORD`(4506~4514 주석
  포함), `reanchored_rids`. `_fz._POSE_SEARCH_SECONDS` 참조도 app.py 에서 소멸
  (fault_zoom.py 자체 상수는 무접촉).
- 유지 대상: `_eye_check`(상속 경로도 사용) + eye ledger(LD-8) + `_pair_at` +
  `_override_idx` rep9 역변환(kpo 편차 2 — 표시 정합, 무접촉) + peak pass-through
  (비-각도주장 align-peak freeze 는 절정 축이라 비구속 그대로 — 승인 무회귀 전제) +
  `moment_by_crit`/배정/렌더/부착/graceful 층위 전부.
- ±0.4s 조정: 현 구현의 상속 경로(4746~4751)에 조정 코드 **없음** (freeze 그대로
  emit). 실물 확인 후 "이미 부재"로 박제 — 새로 지울 것이 없으면 없다고 쓴다.
- 상속 경로 눈 판정 = user 측만(4748) — kpo 그대로 유지, 범위 확장 금지.
- 0장 경로 실물: 현 코드는 survivors=0 이어도 `update_analysis_fault_zoom` 을
  호출해 confirmed 를 빈 목록으로 **대체**(advisory 만 잔존) — 선착 confirmed
  카드는 지워진다. 이 semantics 는 kpo 승인 배선 그대로 두고(변경 금지),
  LD-5 관찰 항목으로 실물 확인·보고만 한다.
- fresh doc: uid `fvcNXzEqKjgqVxRPVSj1iwFnIpn2` / `p34fresh1786363530` (60점,
  record 5종 r00~r04 = left_elbow/right_elbow/right_shoulder/left_hip/left_knee).
- 승인 코퍼스: `.planning/phases/35-server-rendered-comparison-video/data/*/` +
  ii0 `probes.log`/`sweep_out/poles.json` (kpo verify_local `approved()` 그대로).
- 인증: `FIREBASE_SA_PATH=firebase-sa.json` · `AWS_PROFILE=sunity-motion` ·
  Gemini 키 = SSM `/sunity/motion/gemini-api-key` · python = `backend/.venv/bin/python`.
- Pod: cv8poc707mqtxh — `ssh root@213.173.110.74 -p 11638 -i ~/.ssh/id_ed25519`.
  재분석 env = `source /workspace/aws_env.sh && source <(sed -n '3,34p'
  /workspace/start_server.sh)`. 서버 재기동 필수(옛 모듈 물기 — 8커밋 실측 이력).
  스톱/터미네이트 제안 금지.

## 예상 결과 (사전 박제용 예측 — 정답표 아님, 구조 불변식이 정답표다)

kpo 실측 기반 예측 (Task 2 에서 카드를 열기 **전에** pre-judgment 로 기록):
- r00 left_elbow (freeze 5.3s): kpo 에서 inherit PASS — 이번에도 상속 방출 예상.
- r03 left_hip (freeze = align-peak 16.7s, 각도-주장): 이제 **freeze 순간에서**
  게이트 — kpo 실측 hold+pair 는 16.7s 통과, 눈 판정 미지. 통과 시 16.7s 확대
  카드(영상이 보여준 그 장면), 실패 시 미방출. 어느 쪽이든 스펙 충족 — 실측 보고.
- r04 left_knee: kpo 에서 freeze FAIL → 재정박이었으므로 이번엔 **미방출** 예상
  (LD-6 — 그대로 보고).
- 개별 관절의 방출 여부는 check 실패 조건이 **아니다**. 기계 실패 조건 =
  freeze 불일치 / 2회 비결정 / 승인 무회귀 깨짐 / pytest 기준선 이탈 만.

</context>

<tasks>

<task type="auto">
  <name>Task 1: _run_gated_card_inherit 수술 — 순간 선택 능력 전부 제거 (방출 게이트 전용)</name>
  <files>backend/functions/pipeline/app.py</files>
  <action>
`_run_gated_card_inherit` 를 방출 게이트 전용으로 좁힌다 (LD-1/2/3):

(1) **절정 재배치 제거**: freeze 루프에서 각도-주장 + align-peak reroute 블록
(4714~4737)을 삭제. 새 분기 규칙 = `src == "align-peak" and not is_angle_claim`
→ 기존 "peak" pass-through(비구속, freeze 그대로 방출 — 절정 축 criterion 은
잰 값 자체가 벌림이라 홀드가 원리적으로 성립 안 함, ii0 발견 1 + 승인 무회귀
전제). **그 외 전부**(각도-주장은 pairSrc 무관 포함) → freeze 의 (userSec,
refSec) 그 순간에서 hold_gate + pair_gate + 기계 눈(user 측, kpo 상속 경로
그대로) 판정. u_sec/r_sec 을 덮어쓰는 연산은 함수 전체에서 0 이어야 한다.

(2) **재정박 제거**: `_reanchor` 함수 + 호출부(`re_hit = _reanchor(...)` 분기)
+ 전용 부속(`_hold_angles`/`_hold_cache`/`_EYE_MAX_PER_RECORD`/`reanchored_rids`)
삭제. FAIL freeze → `dropped.append((rid, why))` 만 (정직한 침묵). app.py 에서
`_fz._POSE_SEARCH_SECONDS` 참조 소멸 확인 (fault_zoom.py 상수 자체는 무접촉).
±0.4s 급 조정 코드가 상속 경로에 없음을 실물로 확인 (현재 없음 — 커밋 메시지에
"조정 코드 부재 확인" 한 줄 박제).

(3) **docstring·주석 갱신**: 함수 docstring 을 ufb 의미론으로 재작성 — "카드
순간 = freeze 그대로, 게이트는 방출만 결정, 순간 발명 금지 (belle 08-11 반려
= 스펙)". kpo 재정박 서술을 살아있는 동작처럼 남기지 말 것 (제거 이력은 git).

(4) **verdict 로그 확장 (배선·불변식 증거)**: 기존 1줄을 유지하되 survivors 에
방출 순간을 포함 — 예:
`card_gates verdict analysis_id=%s total=%d survivors=%s dropped=%s eye_calls=%d`
에서 survivors 원소 = `"{rid}:{path}@u{u_sec:.3f}/r{r_sec:.2f}"`.
`reanchored=` 필드는 제거 (경로가 없으므로 필드도 없다 — 로그가 구조를 증언).
접두 `card_gates verdict` 는 불변 (Pod grep 대상).

(5) 유지 (무접촉): 눈 원장 적재·S3 보존(LD-8), |dev| 내림차순 배정 +
`criterion_units_from_records(max_units=4)`(LD-4), `_override_idx` rep9 역변환,
attribution=pole_proximity(상속 pair 성립 시), advisory 보존, graceful 층위
(재raise 0), 0장 시 대체 부착 semantics (LD-5 — 변경 금지, 관찰만 Task 2).
card_gates.py·fault_zoom.py·compare_render.py·채점 5파일 접촉 금지. 임계 상수
접촉 금지 (LD-7). `backend/tests/test_card_gates.py` 는 순수 함수 대상이라
원칙 무접촉 — 만약 재정박 동작을 단정하는 테스트가 있으면 삭제로 정합 (완화된
기대치로 고쳐두기 금지).

커밋 1개: `fix(quick-260811-ufb): 카드 = 영상 freeze 순수 상속 — 재정박·절정
재배치 제거, 게이트는 방출만` (heredoc 파일 생성 금지, Write/Edit 도구만).
  </action>
  <verify>
    <automated>! grep -qE "def _reanchor|_hold_angles|_EYE_MAX_PER_RECORD|_POSE_SEARCH_SECONDS|reanchored" backend/functions/pipeline/app.py && grep -q "card_gates verdict" backend/functions/pipeline/app.py && PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests/test_card_gates.py && git diff HEAD~1..HEAD --name-only | grep -cE "analysis/(deduction_engine|dimensions|kismam|motiondtw|assemble)\.py" | grep -qx 0</automated>
  </verify>
  <done>app.py 에 재정박·절정 재배치·조정 식별자 0, verdict 로그가 방출 순간 포함 + reanchored 필드 부재, card_gates 테스트 통과, 채점 5파일 diff 0, u_sec/r_sec 덮어쓰기 연산 0 (freeze 값 그대로 emit).</done>
</task>

<task type="auto">
  <name>Task 2: 로컬 기계 증명 — freeze 전건 일치 + 2회 결정론 + 승인 무회귀 + 카드 실물</name>
  <files>.planning/quick/260811-ufb-freeze-only/verify_local.py, .planning/quick/260811-ufb-freeze-only/evidence/</files>
  <action>
kpo `verify_local.py` 를 이 디렉터리로 적응 이식 (kpo 원본은 kpo 기록이라 무접촉).
fetch/replay/S3·Firestore 스텁/approved 스테이지는 그대로, `check()` 만 ufb
불변식으로 교체:

(1) **freeze 전건 일치 (LD-1 기계 증명)**: run() 이 캡처한 부착 카드 전부에
대해 — 방출 근거 순간(emitted (u_sec, r_sec), verdict 로그 또는 캡처)이
`report["freezes"]` 의 (userSec, refSec)와 **전건 정확 일치**(같은 float —
변형 연산이 없으므로 등호 성립이 구조 증명). peak pass-through 카드 포함.
주의: 카드 doc 의 `userVideoSec` 표기는 ÷9.0 라벨 잔존(kpo 유보 3, 무접촉)으로
freeze 실초와 어긋날 수 있다 — **판정 seam 은 helper 가 먹인 순간**이지 doc
표기가 아니다. doc 표기 값은 기록만 (수리 금지, 범위 밖).

(2) **2회 결정론**: `--run` 을 **별도 프로세스로 2회** 실행, (a) 카드 목록
(joint/tier) (b) 방출 순간 (c) 카드 PNG md5 전부 동일 확인. 눈 판정이 고정
freeze 프레임에서 flip 해 생존 집합이 달라지면 — 임계·판정 튜닝 금지, 어느
freeze 의 눈이 흔들렸는지 원장으로 박제하고 DETERMINISM FAIL 보고 후 멈춘다
(순간 비결정은 구조상 불가능해졌어야 한다 — 순간이 다르면 Task 1 수술 미완).

(3) **사전 판정 → 카드 실물 (frames-before-numbers)**: 카드 열기 전
`evidence/pre-judgment.md` 에 예측(플랜 "예상 결과" 절 + 내 판단) 기록 → 카드
PNG 전부 직접 열어 육안 판정 → `evidence/post-judgment.md`. 왼무릎 미방출이면
사유(rid, hold/pair/eye why)와 함께 그대로 박제 (LD-6 — 되살리기 금지).
left_hip 이 16.7s 로 방출되면 그 프레임이 영상 freeze 와 같은 장면인지 영상
정지와 대조 박제.

(4) **크롭 재측정 (반려 스펙 잔여 관찰)**: run() 중 `fault_zoom_crop` 로그
라인을 캡처해 방출 카드의 부위/패널 비율을 evidence 에 박제 — freeze 복귀 후
"멀어 보임"이 재는 만큼인지 수치만 남긴다. **크롭 알고리즘 수리는 범위 밖.**

(5) **0장 거동 관찰 (LD-5)**: 드라이버 한정 실험 — 드라이버 프로세스 안에서만
hold_gate 를 전부 FAIL 로 monkeypatch(운영 코드 무접촉) 하고 부착 캡처 확인:
confirmed 0 + advisory 만으로 `update_analysis_fault_zoom` 이 호출돼 선착
confirmed 카드가 **대체 소거**됨을 실물 기록. "남아야 하는가"는 belle 결정
항목으로 SUMMARY 에 올린다 (이번 변경 금지).

(6) **승인 무회귀 + pytest**: `--approved` 재실행 — joint-scope hold 9/9 +
pair 9/9 + align-peak 비구속 동일 (수술은 판정 함수 무접촉이라 동일해야 함,
다르면 수술이 판정에 샌 것). 전체 pytest 실패 집합 기준선 **59건 동일**.

check() 실패 조건 = freeze 불일치 / 결정론 깨짐 / 승인 회귀 / pytest 이탈.
개별 관절 방출 여부는 실패 조건이 아니다 (kpo check 의 정답표 3항과 다른 점 —
이번 정답표는 구조 불변식). 미달 시 evidence 박제 후 멈춘다 (curve-fit 금지).

커밋 1개: `feat(quick-260811-ufb): freeze 일치·결정론 검증 드라이버 + evidence`.
  </action>
  <verify>
    <automated>backend/.venv/bin/python .planning/quick/260811-ufb-freeze-only/verify_local.py --check 2>&1 | grep -E "FREEZE-MATCH ALL|DETERMINISM PASS|approved 9/9" && PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests 2>&1 | tail -1</automated>
  </verify>
  <done>방출 카드 순간 == freezes[] 전건 일치, 2회 실행 카드 목록·순간·PNG 해시 동일, 승인 9/9 재현, pytest 기준선 59 동일, 카드 실물 육안 판정 + 크롭 비율 + 0장 거동이 evidence 로 박제.</done>
</task>

<task type="auto">
  <name>Task 3: Pod 실증 — push → 재기동 → 재분석 → 로그·카드 실물 + SUMMARY</name>
  <files>.planning/quick/260811-ufb-freeze-only/260811-ufb-SUMMARY.md</files>
  <action>
순서 고정 (current-pod-cv8poc707mqtxh 재진입 절차):
1. 커밋 **push 먼저** (gsd-pod-work-push-first).
2. `ssh root@213.173.110.74 -p 11638 -i ~/.ssh/id_ed25519` → /workspace 리포
   `git fetch && git merge --ff-only`.
3. **서버 재기동 필수** — `start_server.sh` 로 (GEMINI_API_KEY SSM 주입 포함).
   기동 파일 md5 를 리포 정본과 대조 (start_p15_server.sh 함정).
4. `/health` commitSha == 로컬 HEAD.
5. 재분석: `source /workspace/aws_env.sh && source <(sed -n '3,34p'
   /workspace/start_server.sh)` 후 belle pdshape 영상 재분석 (새 analysis_id).
6. 실증 수집 (전부 SUMMARY 박제):
   a. `card_gates verdict` 로그 실물 — survivors 의 `@u/r` 순간이 같은 로그의
      freeze 순간들과 일치 + `reanchored` 필드 **부재** (경로 소멸의 운영 증거).
   b. 새 doc `faultZoomComparisons` — 방출 카드 목록 + 각 카드가 어느 freeze
      상속인지. 왼무릎 부재면 사유와 함께 그대로 (LD-6).
   c. 카드 PNG S3 에서 내려받아 **직접 열어** 확인 (frames-before-numbers) —
      각 카드 프레임이 영상 정지 장면과 같은지 대조. 카드 0장이면 doc 실물로
      선착 카드 거동 확인 (LD-5).
   d. 점수 == 60 (채점 무접촉·재현성) + renderedCompare done (영상 무회귀).
7. SUMMARY.md: 기계 판정 한 줄(freeze 일치 + 결정론 + 승인 무회귀 + reanchor
   부재 로그) + 커밋 목록 + belle 결정 대기 항목(0장 시 선착 카드 정책, 왼무릎
   신규 발굴 별도 사이클) + 미달/유보 정직 박제(카드 초 표기 ÷9.0 잔존, 크롭
   원인 3겹 중 이번에 풀린/남은 것) + LLM 학습 영향(눈 추론 호출만이면 "추론만,
   학습 전송 0" + 원장 신규 적재 건수) 명기.

주의: Pod 스톱/터미네이트 제안 금지. 재분석 실패 시 서버 로그·verdict 라인까지
수집한 상태로 박제하고 멈춘다. SSM runpod-analyze-url 은 Pod 동일 시 갱신 불필요
(주소 변동 시에만 belle `!` 실행 항목으로 보고).
  </action>
  <verify>
    <automated>ssh -p 11638 -i ~/.ssh/id_ed25519 root@213.173.110.74 "curl -s localhost:8000/health" | grep -o "\"commitSha\":\"[a-f0-9]*\"" && git rev-parse --short HEAD</automated>
  </verify>
  <done>Pod /health commitSha == HEAD, 재분석 verdict 로그에 reanchored 부재 + 방출 순간 == freeze, doc·PNG 실물 확인, 점수 60 유지, SUMMARY 커밋 완료.</done>
</task>

</tasks>

<threat_model>
| Threat ID | Category | Component | Disposition | Mitigation |
|-----------|----------|-----------|-------------|------------|
| T-ufb-01 | Information Disclosure | 기계 눈 Gemini 호출 | mitigate | GEMINI_API_KEY env 로만 (로그·커밋 금지), 크롭 이미지 외 미전송, 추론 호출만 (kpo T-kpo-01 승계) |
| T-ufb-02 | Tampering | S3 카드 대체 부착 | mitigate | 기존 키 규칙(zoom_/eye/) 무변경, graceful 재raise 0 — 실패 시 기존 카드 보존 |
| T-ufb-03 | DoS (비용) | 눈 호출 | mitigate | 재정박 소멸로 호출이 freeze 게이트 건수(≤5/분석)+캐시로 축소 — kpo 40~46회 대비 감소 |
| T-ufb-SC | Tampering | 패키지 설치 | accept | 신규 패키지 0 — 설치 태스크 없음 |
</threat_model>

<verification>
- 순간 발명 0 은 코드 부재(grep) + freeze 전건 일치(기계) + Pod verdict 로그
  (운영) 3층으로 증명 — 커밋·테스트 통과만으로 단정 금지.
- 카드·판정은 근거 프레임 실물 확인 후에만 제시 (frames-before-numbers).
- 무회귀 = 승인 joint-scope 9/9 + align-peak 비구속 + pytest 59 + 점수 60 +
  renderedCompare done + 채점 5파일 diff 0.
- 개별 관절 방출 여부는 판정 조건 아님 — 예측과 다르면 다르다고 박제 (LD-5/6).
</verification>

<success_criteria>
- [ ] app.py: 재정박·절정 재배치·±조정 부재 (grep 0) + 방출 게이트 전용 docstring
- [ ] verdict 로그: 방출 순간 포함 + reanchored 필드 부재
- [ ] 로컬: freeze 전건 일치 + 2회 결정론(목록·순간·해시) + 승인 9/9 + pytest 59
- [ ] 카드 실물 육안 + 크롭 비율 재측정 + 0장 거동 관찰 evidence 박제
- [ ] Pod: /health HEAD 일치 → 재분석 → verdict 로그·doc·PNG 실물 + 점수 60
- [ ] SUMMARY (기계 판정 한 줄 + belle 결정 대기 2건 + 유보 정직 박제 + LLM 학습 영향)
</success_criteria>

<output>
완료 시 `.planning/quick/260811-ufb-freeze-only/260811-ufb-SUMMARY.md` 작성.
커밋: conventional commits 한국어 요약 (이모지 금지).
</output>

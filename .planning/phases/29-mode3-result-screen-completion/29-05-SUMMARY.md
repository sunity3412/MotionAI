---
phase: 29-mode3-result-screen-completion
plan: 05
subsystem: eval-gate (backend evals — D-02 mode3 tally 전환 sweep 게이트)
tags: [mode3, d-02, sweep-gate, pod-ops, score-switch, wave-3]
requirements: [D-02]
dependency_graph:
  requires:
    - "29-02 — mode3_held tally seam (검증 대상)"
    - "29-03 — mode3 zoom criterion→region 소스 (검증 대상)"
  provides:
    - "evals/phase29 하네스 (run_sweep SERIAL mode3 단독 + assert_gates 5종, phase25 계보 3대째)"
    - "D-02 sweep 게이트 PASS 증거 (정은지 페어셋 12키, cold==warm 결정성 포함)"
    - "score-switch 키별 old/new 대조표 (29-PLAN-REVIEW MEDIUM-1)"
  affects:
    - "production 전환 완료 — Pod olnrvtj0f80pl4 신코드(129d529) 서빙 + Lambda RUNPOD_ANALYZE_URL 동기화 (belle 결정 A 후)"
tech_stack:
  added: []
  patterns:
    - "phase25 sweep 규율 승계: SERIAL / EVAL_OUT_DIR repo-밖 / baseline read-only / cold·warm / env setdefault mirror"
    - "read-only pre-seam tee = mode3 '기존 점수' 소스 (seam 이 종단 in-place 교체뿐이므로 pre-seam == 구코드 저장값)"
    - "멤버별 고유 uid = prev-free mode3 첫 분석 보장 (get_previous_analysis 는 uid-scoped)"
key_files:
  created:
    - backend/evals/phase29/run_sweep.py
    - backend/evals/phase29/assert_gates.py
    - backend/evals/phase29/eval_keys.json
    - backend/evals/phase29/README.md
  modified: []
decisions:
  - "mode3 '기존 baseline' = run_sweep pre-seam tee 캡처 (커밋 baseline artifact 부재 — 자기 sweep 재보정 아님: 비교 기준은 seam 이전 단계 = 구코드 동일 경로 값)"
  - "climb 은 하드 게이트 제외 (not_pole 은 mode3 미적용, plan 명시) — gate 1(success)·4(결정론)에만 자연 포함"
  - "정지 조건 발동 → Pod 재기동 보류 + checkpoint:decision (무음 ship 금지, MEDIUM-1) → belle 결정 A 로 해소"
  - "belle 결정 A (2026-07-17, 수용+전환): power-spin success 100 / fault 80 최종 수용 — '감점이 논리적으로 적용돼 80점이 되는 것이 정도. 잘못된 동작 무조건 50점 미만 같은 일괄 상한/스탬프식 설계 반대, 무조건 객관적이어야 한다.' 산식 재논의·후속 조정 플랜 불필요 — 이 결정으로 종결"
metrics:
  duration_min: 135
  tasks_completed: 2
  files_created: 4
  completed_date: 2026-07-17
---

# Phase 29 Plan 05: D-02 검증 게이트 — 정은지 페어셋 mode3 Pod sweep Summary

**한 줄:** evals/phase29 하네스(phase25 복제-확장, mode3 단독 분석 + pre-seam tee)로 정은지 페어셋 12키를 Pod 에서 SERIAL cold/warm 실측 — **게이트 5종+보조 전부 PASS** (power-spin fault 만 leg_extension 변별, 4동작+climb fallback byte-항등, cold==warm 완전 결정성) → score-switch 정지 조건 발동(power-spin success 91→100)에 checkpoint:decision 으로 belle 즉시 결정(A 수용) 경유 → **Pod 신코드 재기동 + Lambda 동기화 + production 체인 E2E 실측까지 완료, D-02 전환 종결** (무음 ship 0).

## 게이트 판정: PASS (exit 0)

Pod olnrvtj0f80pl4 (RTX PRO 6000 Blackwell), 코드 129d529 (== origin/main HEAD, 29-02/29-03 포함), cold 12멤버 → warm 12멤버 → assert. 실행 로그에 동시 실행 0 (nohup 단일 프로세스 순차).

```
Phase 29 gates PASS — D-02 게이트 5종 + mode3_held 보조 green.
GATE_EXIT=0
```

| 게이트 | 판정 | 근거 |
|---|---|---|
| 1. success 무감점 + 비하락 | PASS | 6 success 전원 records 0, overallScore >= 기존 (power-spin 만 91→100 상승, 나머지 항등) |
| 2. power-spin fault leg_extension | PASS | record 1건: criterion=leg_extension, measured 140.85°, deviation 19.15° over-tol, raw −23.0 → cap −20 |
| 3. fallback 4동작 항등 | PASS | kip-up/peter-pan/elbow-twist-sister/pdshape fault 전부 breakdown 미방출 + 점수 byte-항등 |
| 4. cold == warm 결정성 | PASS | 12키 전부 status/errorCode/overallScore/records 동일 (RTMW_DETERMINISTIC=1 + TechniqueCache Firestore hit) |
| 5. D-02 항등 | PASS | 방출 2키 overallScore == final == max(0, round(100+Σpoints)) + phase24 traceability 구조 검증 green |
| 보조. mode3_held | PASS | done 12멤버 전원 visionVeto.status == 'mode3_held' ('applied' 오염 0) |

## Score-switch 대조표 (29-PLAN-REVIEW MEDIUM-1 — 키별 old/new)

기존(old) = pre-seam tee 캡처(구코드가 저장했을 값). 신(new) = 저장된 overallScore.

| 키 | 기존 | 신(tally.final) | records | criterion id | coverage/fallback | visionVeto | cold==warm |
|---|---|---|---|---|---|---|---|
| power-spin/fault | **0** | **80** | 1 | leg_extension | md={leg_extension,line}, fallback=gemini_silent, gaps 0 | mode3_held | O |
| power-spin/success | **91** | **100** | 0 | (clean) | md={leg_extension,line}, fallback=null, gaps 0 | mode3_held | O |
| peter-pan/fault | 98 | 98 | 미방출 | - | md 빈 dict (빈 criteria) | mode3_held | O |
| peter-pan/success | 98 | 98 | 미방출 | - | md 빈 dict | mode3_held | O |
| elbow-twist-sister/fault | 78 | 78 | 미방출 | - | md 빈 dict | mode3_held | O |
| elbow-twist-sister/success | 83 | 83 | 미방출 | - | md 빈 dict | mode3_held | O |
| pdshape/fault | 88 | 88 | 미방출 | - | md 빈 dict | mode3_held | O |
| pdshape/success | 58 | 58 | 미방출 | - | md 빈 dict | mode3_held | O |
| kip-up/fault | 98 | 98 | 미방출 | - | md 빈 dict | mode3_held | O |
| kip-up/success | 97 | 97 | 미방출 | - | md 빈 dict | mode3_held | O |
| climb/fault | 86 | 86 | 미방출 | - | md 빈 dict | mode3_held | O |
| climb/success | 95 | 95 | 미방출 | - | md 빈 dict | mode3_held | O |

## 정지 조건 판정: 발동 → belle 결정 A (수용+전환) 로 해소

**발동 키: power-spin/success 91 → 100.** clean(무감점) doc 의 final 이 단일 협소 criterion(leg_extension — 이번 phase 유일한 유효 criteria) 통과 근거만으로 100 으로 승격 — 게이트로는 정당(">= 기존" 허용)하나 "criterion-clean = 100 수용" 여부는 제품 결정 (29-PLAN-REVIEW MEDIUM-1). plan 지시대로 Pod 재기동 전 **checkpoint:decision 으로 belle 에 즉시 제시** (2026-07-16). 함께 보고: power-spin/fault **0 → 80** (관절당 감점 상한 −20 산술, 25-A belle 승인값의 귀결) + Lambda 가 죽은 구 4090 pod(hibluobp71cuy8)를 가리켜 production 이 이미 분석 불능이던 현황.

**belle 결정 (2026-07-17): 옵션 A — 수용 + 전환.** 승인 취지: "저렇게 의미가 논리적으로 적용해서 80점 되는 게 좋다. 잘못된 동작이 무조건 50점 미만인 게 어딨나 — 무조건 객관적이어야 한다. 일괄 상한/스탬프식 설계 반대." power-spin success 100 / fault 80 둘 다 최종 수용, 산식 재논의·후속 조정 플랜 불필요 — 이 결정으로 종결. 승인 후에만 아래 4~5단계 진행 (무음 ship 0).

## E2E addendum 결과 (belle 명시 요청 — 전 단계 완료)

| 단계 | 결과 |
|---|---|
| 1. Pod 준비 (pull → 129d529) | 완료 — bootstrap_full.sh 재실행 포함 (pod 재생성으로 pip 소실, PEP 668 은 PIP_BREAK_SYSTEM_PACKAGES=1) |
| 2. 환경 함정 재점검 | VETO env 2종 start_server.sh 박제 확인 (grep 2건). 재기동 후 `/health` 200 `{status:ok, auth_configured:true, pipeline_loaded:true}` + X-RunPod-Token 스모크: 무인증 401 / 정상토큰 key-only body 422 |
| 3. Sweep 게이트 | **PASS** (본 문서) |
| 4. Lambda RUNPOD_ANALYZE_URL 동기화 | **완료** — live 재확인(구 pod hibluobp71cuy8 확인) 후 boto3 in-process get→patch→update (디스크 미경유, ResourceConflict 재시도 루프). E2E 후 최종 재검증에서도 `https://olnrvtj0f80pl4-8000.proxy.runpod.net/analyze` 유지 (29-06 sam deploy 덮어쓰기 0) |
| 5. E2E 실측 1건 | **PASS (95초)** — power-spin fault 영상을 `uploads/phase29e2e/e2epowerspin1784218122.mp4` 로 S3 copy → ObjectCreated → SQS → pipeline Lambda → Pod /analyze → Firestore `done`. 결과: overallScore **80** == breakdown.final **80**, records `[{leg_extension, -20.0}]`, visionVeto `mode3_held` — **sweep 과 완전 일치, mode3 deductionBreakdown production 실방출 확인 (D-02 전환 종결)** |

재기동은 `bash /workspace/start_server.sh` (VETO 함정 영구 fix 경로, 임의 uvicorn 직기동 0) 사용. 서빙 커밋 = 129d529 == origin/main HEAD, Pod repo clean.

## 수행 내역

### Task 1 — evals/phase29 하네스 (commit 11fdaae)

- `run_sweep.py` (383줄): phase25 골격 승계 — module-level env setdefault(RTMW_DETERMINISTIC/GEMINI_VISION_VETO_ENABLED/GEMINI_MAX_VETO_WALL_S + prefetch/moment mirror), EVAL_OUT_DIR repo-안 즉시 중단 가드, `--tag warm`. mode3 조정: eval_keys 12멤버 mode3 단독, **멤버별 고유 uid**(get_previous_analysis 가 uid-scoped 라 prev-free 첫 분석 보장), read-only tee 2종(preSeamOverall + mdKeys).
- `assert_gates.py` (352줄): 게이트 5종+보조, 전부 방향/구조/항등 비교 — 점수 리터럴 비교 0 (grep 검증, 100/0 은 항등식 상수만), phase24 `check_traceability` importlib 재사용, artifact 부재=SKIPPED exit 0 (로컬 검증 통과).
- `eval_keys.json`: phase24 6페어의 mode3 변형 12키. `README.md`: SERIAL 실행 블록 + 정지 조건 절차.
- 합성 fixture 로 게이트 6종 PASS/FAIL 양방향 로직 검증 완료 (실행 증거는 세션 로그).

### Task 2 — Pod sweep 실행 → 게이트 PASS → belle 결정 A → production 전환

1. push: 워크트리 에이전트 제약(main 은 오케스트레이터 merge 소유)으로 **에이전트 브랜치를 origin 에 push** 하고 Pod 에서 `git checkout FETCH_HEAD -- backend/evals/phase29/` 로 하네스만 구체화 (서버 코드는 origin/main 129d529 pull). 실행 후 Pod repo 원상복구 (unstage + 파일 제거 — 하네스는 wave merge 후 main 으로 도착).
2. Gemini 크레딧 스모크: generateContent 200 OK. 실제 sweep 은 TechniqueCache Firestore hit 로 recognizer 호출 0 (mode3 는 애초에 recognizer 1회뿐).
3. ORT CUDA 스모크: Blackwell sm_120 JIT 28s 후 CUDAExecutionProvider 확정 (무음 CPU 폴백 배제).
4. cold(12/12 done, 멤버당 56~119s) → warm(12/12 done) → assert exit 0. 전 과정 SERIAL.
5. baseline 오염 0: `git status/diff backend/evals/` 빈 출력. 산출물은 /tmp/sunity_eval_out/phase29 + **영속 볼륨 /workspace/phase29_eval_out_20260716** (report/breakdowns cold·warm 4종 + cold/warm 로그) 에 보존.
6. 정지 조건 발동 → checkpoint:decision → belle 결정 A 승인 후 재기동: `/health` 200 + 토큰 스모크 401/422 + Lambda 동기화 + E2E PASS (위 "E2E addendum 결과" 표).

## D-08 zoom 관찰 (게이트 외, plan step 8)

12멤버 전부 `faultZoomComparisons` 미방출 — **정상**: mode3 zoom 은 "현재 vs 지난 영상" 비교물이라 prev 필요(app.py:4677 — first/prev 부재 = prev_dtw_match None → 미방출), 이번 sweep 은 전 키 prev-free 첫 분석. 29-03 의 criterion→region 선택 로직 자체는 단위테스트 9/9 로 검증됨. 실 PNG 확인은 second+ 분석이 생기는 29-08 HUMAN-UAT 적립분으로 이월.

## Deviations from Plan

**1. [Rule 3 - Blocking] Pod 환경 부재 — bootstrap 재실행 (PEP 668 우회 포함)**
- **Found during:** Task 2 (SSH 후 boto3 ModuleNotFoundError)
- **Issue:** plan/RESEARCH 이 가정한 Pod(s7gyvvlc6u7ktz, 4090)는 죽고 현 Pod(olnrvtj0f80pl4)는 phase22 학습용 재생성분 — pip 패키지 전멸 + Ubuntu 24.04 python3.12 의 PEP 668 이 시스템 pip 차단.
- **Fix:** `PIP_BREAK_SYSTEM_PACKAGES=1 bash /workspace/bootstrap_full.sh` (기존 스크립트 그대로, env 플래그만 추가). onnxruntime-gpu 1.19.2 CUDA EP Blackwell 동작 스모크로 확인.
- **Files modified:** 없음 (Pod 런타임만)

**2. [Rule 3 - Blocking] push-first 를 에이전트 브랜치 push 로 적용**
- **Issue:** gsd-pod-work-push-first 는 main push 를 상정하나 워크트리 에이전트는 main 을 소유하지 않음 (orchestrator merge 소유).
- **Fix:** `worktree-agent-ae78bb44ccad9940f` 브랜치를 origin 에 push (커밋 11fdaae 증거 보존) 후 Pod 에서 해당 ref 의 evals/phase29 만 구체화. 서버 코드는 main(129d529) 그대로.

**3. [설계 확정] mode3 "기존 baseline" = pre-seam tee**
- **Issue:** 게이트 1/3 의 "기존 baseline 점수" 소스가 mode3 에는 존재하지 않음 (phase24 baseline 은 mode1).
- **Fix:** run_sweep 이 `_apply_vision_veto_from_context` 진입 시점 overallScore 를 read-only 캡처 — 29-02 seam 은 종단 in-place 교체/byte-불변 passthrough 뿐이므로 이 값 == 구코드 저장값 (자기 sweep 재보정 아님: 기준은 이번 run 산출값이 아니라 seam 이전 단계 값). gate 3 이 4동작에서 항등을 실증해 캡처 정합성을 교차 확인.

기타: plan 그대로. FAIL 시 재보정 0 프로토콜은 발동 기회 없음 (전 게이트 PASS).

## 참고 사항

- **Pod 서버는 도착 시점부터 미기동** (belle Start 는 Pod 컨테이너만) — 게이트 전 어떤 코드도 서빙된 적 없음 (T-29-05-04 불변식 자연 충족). 재기동은 게이트 PASS + belle 결정 A 이후에만 수행.
- **E2E 부산물**: `users/phase29e2e/analyses/e2epowerspin1784218122` (Firestore) + `uploads/phase29e2e/e2epowerspin1784218122.mp4` (S3) — 실측 증거로 보존 (테스트 uid, 실사용자 무접촉).
- backend full suite 는 wave merge 시 실행 (29-VALIDATION sampling rate) — 이 plan 은 backend 소스 무접촉 (evals/ 신설만).
- 시크릿 로그 0 (T-29-05-01): 로그/SUMMARY 에 키 값 미출력, Lambda env 는 boto3 in-process 로만 읽음.

## Known Stubs

없음.

## Threat Flags

없음 — 신규 표면 0 (evals 하네스는 기존 in-process 경로 재사용). T-29-05-02(baseline 오염)=EVAL_OUT_DIR 가드+diff 0 실증, T-29-05-03(동시 실행)=단일 nohup 순차 실증, T-29-05-04(미검증 코드 노출)=게이트 PASS + belle 승인 후에만 재기동으로 mitigate. 패키지 설치는 Pod 런타임 bootstrap(기존 스크립트 고정 목록)뿐 — repo 의존성 추가 0.

## Commits

| Task | Commit | 내용 |
|------|--------|------|
| 1 | 11fdaae | feat(29-05): evals/phase29 D-02 mode3 sweep 하네스 |
| 2 | 76bc7a0 | docs(29-05): sweep PASS 증거 + score-switch 대조표 + 정지 조건 발동 기록 |
| 2 (전환) | (본 갱신 commit) | belle 결정 A + 재기동/Lambda 동기화/E2E PASS 증거 |

## Self-Check: PASSED

- backend/evals/phase29/{run_sweep.py,assert_gates.py,eval_keys.json,README.md} 존재 확인
- 커밋 11fdaae / 76bc7a0 존재 확인
- Pod assert_gates exit 0 로그 + /workspace/phase29_eval_out_20260716 아티팩트 보존 확인
- Pod repo clean (evals staged 원복 + baseline diff 0), 서빙 HEAD 129d529 == origin/main
- `/health` 200 + Lambda RUNPOD_ANALYZE_URL 최종 재검증 SYNC_OK + E2E doc `done`/breakdown 방출 확인

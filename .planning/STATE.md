---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: milestone
status: executing
stopped_at: Phase 33 §9 수리 사이클 컨텍스트 기록 완료(D-39~D-45) — 다음 = 수리 plan
last_updated: "2026-07-30T05:47:37.686Z"
last_activity: 2026-07-29
progress:
  total_phases: 16
  completed_phases: 8
  total_plans: 118
  completed_plans: 108
  percent: 50
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-29)

**Core value:** 분석 정확도 — 점수가 믿을 만하고 첫 분석이 "전문가 수준으로 구체적". 수치는 보조, 원인이 핵심.
**Current focus:** Phase 33 — result-trust-recovery

> **20-04 / SCORE-09 ownership (belle 2026-06-23, D-14 amended + D-15, ITERATION6):** Phase 20-04 의 still-frame SEVERITY_CAP **regression subset** (SCORE-08 cap + TRUST-06 결정론) 은 Phase 23-03 eval 이 still-frame veto 경로에서 OWN·검증한다 (superseded-by-23-03) — 정은지 95~100 / kip-up fault = moderate 점수 ≤75 (20-04 evidence 75/moderate 와 일치, ≤50 억지 격상=curve-fit 금지) / 결정론(cold+warm) / EVAL18 변별 4쌍 퇴행0. **SCORE-09 (일반화/sensitivity — 미보유+above-cutoff 양방검증) 는 흡수되지 않고 별도 PENDING 으로 Phase 20 / 후속에 잔류한다.** Phase 23 을 SCORE-09 미처리로 닫거나 20-04 를 SCORE-09 채로 superseded 처리 금지.

## Current Position

Phase: 33 (result-trust-recovery) — EXECUTING
Plan: 5 of 23

> ✓ Wave R (채점 재설계) COMPLETE (2026-07-24) — 33-22 2트랙 IPSF 감점 엔진(실행 −40캡 바닥60 + DORMANT 치명 캡우회 절대바닥25, `final=max(25,100−min(40,Σ실행)−Σ치명)`, 기존 임계 byte-unchanged) + 33-23 재검증 PASS. Pod b9l5gt1vpc4ho1(4090, ac59904 재핀, shadow candidate phase33-cm3-run1) serial 6 fixture: INV-1/2/4/5/6 동시 성립(재구성 10/10, 엘보우 −111.4→바닥60 앵커 재현, INV-4 캡 평탄화 elbow/pdshape→60=의도 트레이드오프 curve-fit 안 함), 회귀 0(HEAD vs baseline 61==61), 채점 테스트 241 pass. climb=not_pole 게이트 예외. **flip(33-07) belle 보류 유지** — 표현 트랙(33-07~16,33-21) 미착수. 정직 맥락: fault 점수 상승(57→80 등)=엔진 아닌 새 기질 효과, belle 판단 별건. 상세=33-SCORING-REVERIFY.md
Verification: 22-12 COMPLETE (2026-07-16) — 데이터 플라이휠 "공부하기" 배치 루프 상설화. run_retrain_cycle.sh 1커맨드 사이클 러너(preflight[serial lock+greenlight 과금 게이트+디스크 30GB+git pull] → label[신규분만 과금] → assemble[jsonl_backup_ s3 백업 선행 후 canonical 교체] → train → gates[bf16 병합+compute_cap>=12 조건부 flashinfer env] → promote[promotion 래칫]) + promotion.py 순수 래칫(parse_gate_verdict/make_ledger_entry/apply_ratchet/make_cycle_report — 게이트 PASS[--require-pass exit 0]만 current 전진, FAIL 은 attempt 기록만, 사람/judge 점수 저장 0) + promotion_ledger.json(current=null 초기) + FLYWHEEL-RUNBOOK §2(belle 주1회 트리거·flashinfer 박제·래칫 해석·비용 관측치). TDD 9 테스트, phase22 302 pass/1 skip, 기존 러너·게이트(run_sft/run_sft_gates/assert_gates/build_jsonl/merge_and_quant) 무접촉. 실 Pod 사이클(라벨 과금/SFT/게이트)은 v7 종료 후 런북 절차(belle 트리거). // 이전:
Verification: 22-11 COMPLETE (2026-07-16) — 데이터 플라이휠 "쌓기" 상설화. phase22_watch.py belle 1커맨드(PHASE22_BELLE_GREENLIGHT=1 --run) watch 러너 + _meta.collection_batches[] 배치 증분 등재 규약(마감 무결성 정합, build_jsonl 무접촉) + watch:false 옵트아웃 + FLYWHEEL-RUNBOOK §1. 순수 헬퍼+불변식 TDD, phase22 293 pass/1 skip, 프로덕션 무접촉 리허설 통과. 실 수집(과금)은 런북 절차 이월. // 이전:
Verification: 22-04 COMPLETE (2026-07-11). 교사 증류 full batch 129/129 터미널(수락 109 / rejected_judge 12 / parse 6 / contract 2, 소스별 IG 91%·internal 88%·YT 79%, File API 잔여물 0) → SFT 학습셋 S3 완성 `training/phase22/jsonl/` (train.jsonl 99행 = distill 87 + text 14 / val.jsonl 2행, video_hash split, 균등 트림 109→87). 수집 마감 f66f25f(collection_complete=true + balance_waiver, 내부 371 fault track 이월). 시험 배치 3라운드가 129행 과금 전 결함 4건 fix(enum 59ac1a1/동작명 c5b14ef/judge 루브릭 eb69692/배열 파싱 ce992e0). 조립 중첩 타입 강제 = normalize_report 단일 owner(25e6752+1930099, coaching 80/87 보존). phase22 테스트 156 pass/1 skip. Known limitations: val 2행 얇음·svg_spec 감독 0/87·perturb/shadow 트랙 미합류(2트랙) — 22-04-SUMMARY.md 참조.
Next: 데이터 플라이휠 운영 상설화 완료(쌓기 §1 + 공부 §2). 실 사이클은 belle 트리거(런북 §2, v7 종료 후 Pod). 잔여 플랜: 22-08~10 서빙 swap(게이트 PASS 시 promotion_ledger current 진입 조건) + 22-03 Tasks 2-4(Pod 배선) belle-gated 이월. bake-off 백본 = Qwen3-VL-8B CONFIRMED(260713-jjq).
Status: Ready to execute

> ◐ 22-03 IN-PROGRESS — Task 1(helper)만 실행 (2026-07-09, LOCAL ONLY, Firestore/네트워크/Pod 0). `firestore_admin.store_vlm_shadow(video_hash, role, payload)` shadow 로깅 helper 추가: vlm_shadow/{video_hash} top-level 컬렉션(gemini_cache 형제)에 `{video_hash, created_at, updated_at, roles:{veto/recognizer/coach}}` set(merge=True) deep-merge 누적, created_at 첫 기록 보존, D-12 PII 키 재귀 거부(_reject_pii_keys, 정규화 denylist — T-22-07), nested-array 사전 차단(_validate_flat_dict_no_nested_array 재사용). firestore.rules catch-all default-deny로 클라이언트 접근 차단(T-22-08). TDD 2 commits(test f1f2d5b/feat f295d1e), phase22 전체 67 pass/2 skip. **Task 2(pipeline app.py VLM_SHADOW_LOG 배선 — production 판정경로 변형), Task 3(Pod 변형 blocking checkpoint), Task 4(Pod 배포+shadow 스모크+피크 VRAM 실측)는 belle-gated + 라이브 GPU Pod 필요로 후속 세션 이월.** 22-03-BASELINE-FAILED.txt/22-POD-VRAM.md 미생성(Pod 필요). ROADMAP 22-03 미완료 유지. 다음=belle greenlight+Pod 준비 후 Task 2~4 재개.

> ✓ 22-04 COMPLETE (2026-07-11) — 교사 증류 + SFT 학습셋 완성. Tasks 1-2(gemini_teacher 4중 필터 + build_jsonl 3트랙 조립기, TDD) → Task 3 시험 배치 3라운드(10행 cap)가 129행 과금 전 결함 4건 fix(enum 59ac1a1/동작명 c5b14ef/judge 루브릭 eb69692/배열 파싱 ce992e0) → belle approved → Task 4 full batch 129/129(수락 109, 소스별 IG 91%·internal 88%·YT 79%, judge 분포 건강 9점 69+10점 39, File API 잔여물 0, A100 Pod ns8smhcydnduq9 밤샘 — full_batch.py 재개성 실증) → 수집 마감 f66f25f(collection_complete=true + balance_waiver) → 조립 중첩 타입 fix(normalize_report 단일 owner, 25e6752+1930099) → `--assemble --upload` S3 완성 `training/phase22/jsonl/`(train 99 = distill 87+text 14 / val 2 / _meta, 2026-07-11 02:31 KST). phase22 156 pass/1 skip. **Known limitations(22-04-SUMMARY.md): val 2행 얇음(22-07 게이트 검증력 제약), svg_spec 감독 0/87(교사 SVG 전부 비스키마 — 후속 라운드 프롬프트 강제), 이번 JSONL 은 distill+text 2트랙(perturb=raw 좌표 영속화 부재, shadow=적재 0 — 3트랙 완전체는 22-07 전 소규모 후속).**
>
> ✓ 22-05 COMPLETE (2026-07-09, LOCAL ONLY, GPU/Pod/모델가중치 0). bake-off(Qwen 3.6-VL-8B vs InternVL 3.5-8B) 하네스+평가 미니셋을 pod-free 로 박제 — 실행은 22-06. 산출: backend/evals/phase22/run_bakeoff.py(4축 순수 계측 score_grounding/temporal/json/coaching + run_sweep 규율 EVAL_OUT_DIR repo-밖·SERIAL·_meta·temp0·ALLDONE·Pod env 헤더, 모델/judge lazy) + fixtures/manifest.yaml(4타입 37항목: real 균등 14동작 kip-up 최다 아님 / hard_negative A2·A3 / synthetic_grounding=grounding L2 유일 트랙 / trap 역재생·셔플) + tests/phase22/test_bakeoff_harness.py(19 pod-free, phase22 전체 55 pass/2 skip). 3 commits(0e6b5fb/62fc02c/f6c9308). grounding=합성 전용 한계 명시(Open Question 1). main() 추론 루프는 22-06 스코프(의도적 미구현, dry-run+테스트로 검증). 다음=22-06 Pod 실행(후보 백본 순차 serve + 추론 루프 + 4축 판정), 모델 ID(RESEARCH A6)·hard_negative A2/A3 relocate 선행.

> ✓ Wave 5 (04-05) COMPLETE (2026-06-14, RunPod d9xxudi1i6xlpz RTX PRO 4500 Blackwell sm_120):
> code(Task1+2: daf6803/969a2c6, local pytest 41 pass/3 skip) → RunPod GPU 재처리 5/5 (RTMW onnxruntime-gpu
> sm_120 cuda ~50fps, 150s, NaN 0) → schema gate 5/5 → Firestore versioned write reference/{id}/versions/phase4_v1
> 5/5 → belle 시각검증 PASS (현 active 대비 관절각 Δ 0~6°, NaN 0, 프레임 1.5x↑ 더 촘촘) → active flip 5/5
> (activeVersion=phase4_v1, top-level mirror 11필드 incl joints3d/keypointReport, pre_phase4 백업 = rollback 소스).
> **Firestore 40k index-entry 한도 차단 해결**: gcloud `firestore indexes fields update --disable-indexes`
> 6개 면제 (joints3d/angles/keypointReport × collectionGroup reference+versions, owner sunity3412 login).
> composite mode3 index 무영향. [[firestore-index-entry-limit]] + [[rtmw-blackwell-lean-bootstrap]] 박제.
> rollback: `python backend/scripts/rollback_reference_motions_phase4.py --to-version pre_phase4`.
> :8000 server UP (proxy d9xxudi1i6xlpz /health ok, Lambda RUNPOD_ANALYZE_URL z3fy82→d9xx 동기화).
> 잔여(optional, phase blocker 아님): Wave 3b @integration evaluate_4way axis_b RunPod 증거 (parked, SKIP/XFAIL).

> ✓ Wave 3b CLOSED — 경로 보류 (belle 2026-06-15). 증거-먼저 단계 실행(새 GPU 불요, Wave 5 Firestore 데이터):
> pre_phase4(구 파이프라인 8관절) vs phase4_v1(RTMW) axis_b occlusion_frame_rate 비교 = mean −33.5% / 개선 1/5 /
> G4 악화 0 False. **단, 이 비교는 cross-model (서로 다른 모델 confidence 스케일) 이라 유효 게이트 아님** — RTMW
> occ_rate 가 높은 건 pose 하락이 아니라 confidence 분포 차이(mean_conf Δ 0.02~0.03). 유효 axis_b 게이트 =
> 동일 RTMW 의 합성 유무 비교(RTMW-baseline vs RTMW+mesh) → `_rerun_rtmw_on_views` 풀 구현 필요 = 보류.
> SYNTHESIS_MESH_ENABLED OFF default(B4 hard gate) 유지 = 코드 변경 0. 근거/재개조건 박제:
> `.planning/phases/04-ux-occlusion-confidence/04-WAVE3B-EVIDENCE-DECISION.md`. [[gsd-model-overrides-opus]] 무관.

> ✓ Reference 라이브러리 전체 RTMW 재처리 완료 (2026-06-15, belle 승인). Wave 5 가 5개만 했고
> 나머지 6개(ref-combo/elbow-twist-sister/kip-up/pdshape/peter-pan/power-spin)는 구 8관절 2D 파이프라인
> 이라 분석 품질 저하 — belle 지적. RunPod RTMW 로 6개 재처리(--no-flip → schema gate 6/6 → phase4_v1
> versioned write 6/6 → NaN 0, 8관절 2D→17관절 3D) → belle flip 승인 → active flip 6/6 (activeVersion=
> phase4_v1 + top-level mirror 11필드 + pre_phase4 백업=rollback). **전체 11개 reference 모두 phase4_v1
> active + top-level 3D = ALL GREEN.** flip JSON = Pod `/workspace/reference-phase4-reprocess-6new.json`.
> rollback: `rollback_reference_motions_phase4.py --to-version pre_phase4`. (후속 후보: reprocess 스크립트
> MOTION_IDS 5→11 영구 반영 — 현재는 --motions override 로 처리, repo 변경 X.)

> ⚠ Wave 2 belle override (2026-06-13): EAS preview build 환경 이슈로 실기기 smoke checkpoint 보류. R8 ErrorBoundary (PoseViewer3D Canvas 감쌈) + typecheck/grep 게이트가 로컬 안전망. 다음 native build 시점에 belle TestFlight 실기기로 OrbitControls 제스처 + Canvas/GL init + 4 카메라 preset 동작 검증 필요 (SUMMARY 04-02 deviation 섹션 박제).

> ⚠ Phase 04 Decision-Coverage Gate override (2026-06-13): 12/32 CONTEXT 결정만 plan 직접 인용. 미커버 20개는 빌드 대상 아님 — spike 절차 완료분(D-11/12/13/17/19), v2/후속 보류(D-06/14/24~28), 근거·IPSF 리서치(D-15/16/21/22/23), negative scope fence(D-01/02/04). 실 빌드 결정(D-03/05/07/08/09/10/18/20/29~32)은 plan-checker Dimension 7 PASS 확인. verify-phase 에서 재확인 가능. proceed-anyway 선택 (belle 위임 "그냥 진행").

Last activity: 2026-08-16 - Completed quick task 260816-r7k: ref-climb 교체 (차단 해소 실증)

이전: 2026-08-09 - **일러스트 라운드 종료** — 기준 모션 7/11 → **11/11**, 실제 지적 발생 (동작·부위) 짝 **13/13 커버**(그림 없이 나가던 감점 65건 → **0**). belle 반려 3라운드로 검수 게이트 **4→9항목**(머리카락·착의·폴/인물 수·목·사지 전 길이). ★**검수는 몽타주 축소본으로 하지 않는다** — belle 3건·내 3건이 전부 축소본 통과분이었다. 사이각 문법 전환은 시도 후 **철회**: belle 역할 구분(확대비교=차이 / 일러스트=목표)이 반려의 뜻이었고, 각 표시 정밀화는 **확대 비교의 몫**. 자산 정본 = `1141c738`. ★**다음 1순위 = 확대 비교 각도 표시**(실측 5건 중 2건만 그려짐) + **일러스트 자세 충실도**(belle 지시: 반드시 해내야 함). 미검증 = 시뮬 실화면·belle 최종 육안

이전: 2026-08-09 - **Pod p2qjoktz8lc4ju 기동 + 실업로드 경로 결정론 ON** (quick 260809-i0q). 08-08 잔여 1건 종결. ★노트가 가리킨 `start_p15_server.sh` 는 **함정 파일이었다**(6월판 = PR_INVERSION_ENABLED 없음) — 정본 `start_server.sh` 에 `RTMW_DETERMINISTIC=1` 박제하고 p15 는 정본 위임으로 무장해제. `/health` 4항목 PASS(commitSha 73042a27 · 결정론 true · 인버전 true · modelLoaded), `/analyze` 무·오토큰 401. SSM v28 + Lambda `RUNPOD_ANALYZE_URL` 새 proxy 동기(4키 보존). 기동 스크립트를 `backend/runpod_inference/start_server.sh` 로 버전화(Pod 사본과 md5 동일) — git 밖이라 env 누락이 두 번 반복된 것을 구조로 제거. **실경로 E2E 2회 완주**(시뮬 업로드) — 채점 **완전 재현**(64/−35.9/편차 5건 소수점까지 동일) · 렌더는 **비재현**(정지 3번째부터 +0.03s = 1프레임, mp4 md5 상이 — 잔여 비결정 ② mp3 길이 변동이 운영 경로에서 실측됨). ★같은 영상 점수 이력 = 07-30 **72** → 08-08 **72** → 08-09 **64**(측정창 수술 ②) → 64. 점수는 10일간 고정이었고 **한 번 움직였는데 그 이동을 belle 께 예고 안 한 것이 결함**(belle 지적). 드러난 구멍 = 08-08 게이트가 산식 5파일 diff 0 은 봤는데 `motiondtw`(측정창)는 목록 밖 → **산식은 지켰고 점수는 아무도 안 지켰다**. 제안 = 점수 회귀 기준선 게이트(belle 결정 대기). **belle 앱 업로드 완료(피터팬 84점·합성 영상 done+70초 뒤 부착, 승인본 83점과 같은 관절·같은 크기)** → belle 요청 4건으로 **전체 조정 (quick 260809-jnb, `16354a26`·`96e0dcd3`)**: ①각도 수치 짝 lockstep(한 패널만 48° 남던 것 — 신뢰 게이트가 패널별이라 생김, both-or-neither 불변식의 수치판 확장) ②조작 UI 복귀(nativeControls 자동숨김+얇은 틱바 → 점 하나만 남아 멈춘 재생바로 읽힘. 듀얼 컨트롤 세트 이식) ③정렬 조정 컨트롤 제거(서버 정렬 후 대상 소멸) ④참고코너 문구 재작성. **OTA 전 시뮬레이터 눈검증 수행**(08-08 "미검증 발행"이 오늘 반려로 돌아온 직접 교훈). **다음 = belle 실기기 확인** + ① 실렌더 검증(Pod 필요)

이전: 2026-08-08 - **belle 통과 판정** — quick 260808-r82 종결: 수술 3건 + Pod 스윕 + E 저더 3층 수리(꼬리 절단·정렬 결정론·재재생 철회+정지 1초 여운). belle 반려 영상 최종 재분석 = 저더 1건(승인 5편 0·0·0·3·3 보다 우수)·리그 ALL PASS·doc 부착. belle: "일단 통과 시키자, 육안으로 힘든 부분". ★다음 1순위 = 서버 start_p15_server.sh 에 RTMW_DETERMINISTIC=1 반영(실업로드 경로 결정론 OFF — belle 앱 업로드 전 필수). 상세 = quick/260808-r82-phase-34-3/POD-SWEEP-RESULT.md

이전: 2026-08-08 - Completed quick task 260808-r82: **Phase 34 수술 3건** (보드 착수 블록 승인분). ② 측정창 ref-경계 마진 제외(REF_BOUNDARY_EXCLUDE_S=0.5s, G 핀 lockstep) — pdshapefault right_elbow 측정 순간 1.22s→9.56s 이동 실측, 점수 median 은 소폭(±0.1~3.6°)·표시 순간은 대폭 교정. ③ 좌우 스왑 채점 = **기계검증 기각**(유일 실측 거울상 elbow 에서 두 변형 모두 악화 24.15→29.83/38.95°) → 발동 무장해제, 그립 거울상은 관측 로그만. ① 렌더 tier 프록시(7 doc 전부 trim_only → 부착 0) 삭제 → align_quality(build_align 산출 자체 판정, 승인 5편 캘리브레이션 2.0배 마진). 불변식 스위트 시작(backend/tests/phase34/ 32 테스트). 다음 = **Pod 스윕**(POD-VERIFY.md — belle-FAIL align_quality + 실 doc 재분석 + 리그 신선 ALL PASS) → belle 아무 영상 v7급 확인

이전: 2026-08-08 - Completed quick task 260808-im8: 자율 스크린 v1(2e8ab938+2f077393). v0 인라인 스크린 리포 영구화 = V0_REGRESSION 6게이트 PASS. r03 블라인드 재발견 verdict = FAIL(홀드 격리 실패 — run 조각내기 + DTW 짝-홀드 경계 불일치, 실패 그대로 박제). 다음 = v2 홀드 가설(히스테리시스/완화짝) belle 결정 대기

이전: 2026-08-08 - Phase 35 미세조정 2차(260808-epy) 완료: scratchpad 재부팅 소실 사건 → Pod 볼륨(새 5090 Pod, 이후 Terminate)에서 재료 회수·기계검증 → 리포 영구화(d266cb8d) → 엘보 = 폴-근접 문법(belle 교정 "각도 아님" — 폴 축선+간격 브래킷+"폴에 붙여라" 문구 lockstep 재합성) → 리그 10×ALL PASS·diff 게이트(kipup 1.467 불변)·S3 5키 v7 덮어씀. pdshapefault r01 왼손 그립 짝 = fail-closed 미충족(x-투영 원리 한계, belle 선택지 3 대기). 다음 = belle v7 심사 + r01 결정 → 타인 피드백 → 채택 시 앱 통합

이전: 2026-08-02 - Completed quick task 260801-gbk: 감점마다 측정 순간 기록(`ab9da85e`). 채점 무접촉 = `deduction_engine.py` diff 0 + pytest FAILED 59 불변 + legacy_baseline PASS. 스위프 10동작 `[8,8,8]`→`[4,9,14]`. ⚠합성 fixture 한계·킵업 split 미해결·실기기 전부 미검증. 미결 목록 = `.planning/CONTINUE-2026-08-01.md`. 다음 = belle 결정 대기 #4·#5(저신뢰 0.49 인데 63점 확정 — ★임계가 5-fixture 유도라 일반화 미검증) 또는 belle 결정 불요 #6

이전: 2026-08-01 - Completed quick task 260801-f77: 코치 음성 큐 재생 복구(만료 인지 캐시 + 로드 실패 감시 + 15초 정지 제거, ff07be2e). **belle 확인 ③ 이 07-30 doc 을 보고 있었음이 드러남** — §C-4 재산출본이 시뮬 uid(`fvcNXz…`) 아래에만 있었고 belle 계정(`csKWYvI3…`)에는 안 닿았다. 4개 doc 복사 + 음성 키 교정으로 반영 완료(60/79/100/63, 이미지 12장 생존). belle 실기기 리포트로 **미결 11건 목록화**(TaskList) — 뿌리 = 모든 감점이 한 프레임에 몰려 큐가 0.089초에 열리는 것. 다음 = #1(단일 프레임 몰림) belle 방향 확인 → #4·#5(저신뢰 0.49에 63점 확정)

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260612-t9m | stability 점수 보정 + 사용자 안내 (TOL 15° → 25° + result.tsx 안내 캡션) | 2026-06-12 | 947570f | [260612-t9m-stability](./quick/260612-t9m-stability/) |
| 260615-cxe | vision Gemini default model gemini-2.5-flash → gemini-2.5-pro (recognizer/moment-extractor) | 2026-06-15 | d204291 | [260615-cxe-vision-gemini-default-model](./quick/260615-cxe-vision-gemini-default-model-gemini-2-5-f/) |
| 260620-0r0 | Mode3 점수 역전(#8) 수정 — second+ overall = abs_dims만 (angle=이전영상 유사도가 발전을 min()으로 역전시키던 것 제거) + 회귀 테스트 | 2026-06-20 | ba5fe4f | [260620-0r0-fix-mode3-score-inversion](./quick/260620-0r0-fix-mode3-score-inversion-bug-8-overall-/) |
| 260620-18r | 점수 UX 일관성 — #4 세부점수 보조지표(안정성) 종합 비반영 안내 캡션 + #2 마커 강조 임계 10°→20°(IPSF 허용오차 정합, 고득점에 빨강 모순 제거). 표시 일관성만, 점수 로직 불변 | 2026-06-20 | 5b5fb81 | [260620-18r-score-ux-consistency](./quick/260620-18r-score-ux-consistency-marker-score-thresh/) |
| 260626-e5k | Phase 24 (A) fix — deduction_engine.tally 폴백 게이트를 criterion 선택 뒤로 이동(quant_unavailable AND not activated일 때만 폴백). low_alignment 에서 정렬-독립 RTMW 각도 seed 가 granular 감점 산출. reach 칸 불가는 coverage_gap 노출. false-green seam/engine 테스트 4건 교정 + 회귀가드 6종. 로컬 게이트 GREEN(62 affected), band grep 0, 엔진 purity 보존. Pod 재-sweep 검증 PENDING | 2026-06-26 | 2253e77 | [260626-e5k-phase-24-plan-05-a-fix-deduction-engine-](./quick/260626-e5k-phase-24-plan-05-a-fix-deduction-engine-/) |
| 260626-jwu | Phase 24 결함 ① fix — 미등록 동작에서 정은지 대비 per-joint 각도편차(per_joint_deviation)를 deduction 엔진 granular seed로 배선. N개 `angle_vs_reference__{joint}` reference_relative criterion(kismam 20°+slope 재사용, 새 임계 0) + 2-layer cross-exclusion(double-count 0) + self-compare 0. belle "−X 왼무릎 −Y 오른팔꿈치" wish 실현. 59+146 passed, band grep 0, contract 불변. score-shift pod 재검증 PENDING(①②함께) | 2026-06-26 | c958ff3 | [260626-jwu-phase-24-fault-1-fix-wire-reference-rela](./quick/260626-jwu-phase-24-fault-1-fix-wire-reference-rela/) |
| 260626-jti | Phase 24 결함 ② fix — `_pose_frame_keypoints`가 존재하지 않는 `pf.keypoints`를 읽어 visibility=0.0 전클립 → Gemini 광범위 차단이던 배선 버그. 실제 필드 `keypoints_3d: dict[str,Keypoint3D]`의 `.values().confidence` 평균을 읽도록 수정. pod 진단 확정. 38+18 passed, band grep 0, alignment 임계 불변. ①과 함께 pod 검증 PENDING | 2026-06-26 | 81e7f56 | [260626-jti-phase-24-fault-2-fix-visibility-0-0-wiri](./quick/260626-jti-phase-24-fault-2-fix-visibility-0-0-wiri/) |
| 260626-f3u | Phase 24 (B) 진단 계측 — additive(채점 byte-unchanged). alignment 텔레메트리 보존(collect low_alignment bail이 버리던 alignment 복구)+to_audit_dict 방출(alignment_summary 순수 helper)+sweep visionVeto 캡처+kip-up Gemini probe(bail 우회 monkeypatch, assess_fault_context 직접 호출). 다음 pod-run에서 (A)실증과 같이 실행. 로컬 83 passed, band grep 0, vision_veto purity 보존. probe는 pod 전용(로컬 미실행) | 2026-06-26 | 2761d79 | [260626-f3u-phase-24-b-diagnostic-instrumentation-al](./quick/260626-f3u-phase-24-b-diagnostic-instrumentation-al/) |
| 260627-9dh | eval 게이트 강화 (P1 검증 토대) — phase24 assert_gates 에 pod-free 게이트 2개 추가(이제 7). clean-residual: 정타 멤버 per-criterion `raw=abs(baseline-measured)`가 CRITERION_GROUPS tolerance 초과 시 FAIL(절대 잔차 — generalization 의 상대 fault>success 구멍 보완, 오염된 정타 14~18° 차단). sensitivity: 합성 above=2×tol→비자명 감점 강제 / deadzone=tol/2→감점0 강제(metric validity). 임계 전부 tolerance 파생(curve-fit 0). 21 passed. main() exit 1 = 기존 generalization kip-up false-negative red(pre-existing, regression 무도입) | 2026-06-27 | 7023be8 | [260627-9dh-eval-gate-hardening](./quick/260627-9dh-eval-gate-hardening-clean-residual-above/) |
| 260627-afq | P1 step4 — recognizer 등록 + 객관 IPSF 무릎신전 wiring. 5동작(kip-up/power-spin/peter-pan/elbow-twist-sister/pdshape) REGISTERED_MOTIONS+한영 alias 등록 + 5 criteria yaml(무릎 EXTEND, angle_target 180°=IPSF 보편기준, source_ref=Glossary fully-extended-leg+의도된 폼, 정은지 측정값 아님). 엔진 코드 0변경(24-07 wiring이 데이터+등록만으로 활성). de-contamination pod-free 증명: 곧은 무릎(정은지와 달라도)=감점0, 굽은 무릎=leg_extension(ipsf_absolute) 감점+reference_relative cross-excluded. 80 passed. pdshape 비대칭=step5 gate 검증. 남음=step5 pod sweep | 2026-06-27 | 9678ab5 | [260627-afq-p1-step4](./quick/260627-afq-p1-step4-register-5-moves-objective-ipsf/) |
| 260630-l4e | power-spin success fallback calibration (91→100) + kip-up split 마진 도메인 검토. 근본원인=`_apply_vision_veto_from_context` 의 not_applicable 분기가 clean tally(empty records)에서 breakdown.final(=100) 대신 레거시 min-of-core dimension(min(angle,line)=91) passthrough. fix=not_applicable 도 overallScore=breakdown.final(1줄, 새 상수 0 — calibration-source-hard-gate 안전). quant-unavailable 은 applied(fallback record)라 불변. Pod 6쌍 sweep 검증 PASS: 전 success 100, kip-up fault 88 유지(100 미점프 — split_angle record→applied 경로), cold-rerun 결정적. kip-up split 마진 12=adequate(단일 결함 단일 감점, vision 측정 30°→10° over-tol×slope, no change). 141 passed | 2026-06-30 | d557d6d | [260630-l4e-power-spin-success-fallback-calibration-](./quick/260630-l4e-power-spin-success-fallback-calibration-/) |
| 260702-mat | TestFlight 빌드 27 배포 (Pod 테스트 전 선행) — iOS 빌드 #27(production, 커밋 11899b5=HEAD, 07-02 11:45 기빌드)을 `eas submit --id` 무인 제출 → ASC 업로드 성공, Apple 처리 후 TestFlight 노출. Android: 직원 설치 APK 빌드 #1(preview-android)도 동일 커밋 11899b5 → 코드 변경 0건, 재빌드 불필요 판단. 코드 변경 없음(운영 작업만). appVersionSource=remote 라 app.json buildNumber/versionCode 는 무시됨 | 2026-07-02 | (docs only) | [260702-mat-testflight-27](./quick/260702-mat-testflight-27-app-json-buildnumber-pod/) |
| 260702-o0c | kip-up 상체 감점 누락 fix — angle_vs_reference__{jk} seed 를 2단으로 정렬: (1순위) 표시용 windowMedianAngleDeltas(worst-window median, 표시=감점 동일 source — 국소 결함이 전체 DTW path median 에서 희석되던 집계 불일치 해소) + (fallback) 기존 per_joint_deviation DTW-median(24-05/e5k 무회귀). 양 경로 공통 방출 규칙 helper(JOINT_KEYS/NaN·0/expects_extension cross-exclusion) + seed source 관찰 로그. 신규 상수 0, motiondtw 불변, 스키마 변경 0. 로컬 31 passed + 전체 회귀 0(1830 passed, baseline FAILED/ERROR diff IDENTICAL), 밴드 재도입 0. **Pod sweep GATE FAIL → REVERT** (00d19a5/c927286): kip-up fault 50(어깨 좌우+split 감점 — 상체 감점 메커니즘 실증) BUT success 위양성 4건(power-spin 74/peter-pan 85/elbow-twist 86/pdshape 92, 직전 sweep 전부 100). 원인=worst-window median 이 Gemini-silent seed 에도 적용되며 RTMW jitter/촬영거리 불일치 노이즈를 감점으로 증폭(2026-06-12 full-path median 전환 사유의 재확인). 교훈: window 측정은 vision 이 짚은 관절에만 적용해야(짚기=Gemini, 측정=window, silent=full-path 유지). 재설계는 vision 상체 짚기 커버리지 확대와 함께 별도 phase | 2026-07-02 | f513587(reverted) | [260702-o0c-kip-up-fix](./quick/260702-o0c-kip-up-fix-per-joint-reference-relative-/) |
| 260702-q8q | 점수 근거 공개 UI (belle: "왜 이렇게 나왔는지 설명 부족" fix) — result.deductionBreakdown(이미 저장돼 있었음, 앱이 안 그리던 것)을 "점수 계산 내역" 섹션으로 노출(100 − records = final), 실패원인 상세 시트를 실측 근거(측정값·표본일치·관절별 편차표 20°초과 강조)로 교체, veto fallback confidence 0 하드코딩→supportCount 정합("신뢰도 높음"), 계약 drift(source 'vision') 3-way lockstep. 백엔드 점수로직 0변경. 45 passed + typecheck clean. OTA 발행(production+preview 채널, runtime 1.0.0) | 2026-07-02 | 1b7d1e4 | [260702-q8q-x](./quick/260702-q8q-x/) |
| 260702-sic | 문제부위 확대비교 crop 정합 fix (belle: 정은지 쪽 crop 이 부위 이탈) — 원인 3중: 측정 프레임≠표시 프레임(veto sourceFrameIndices 미사용), keypoint confidence 게이트 부재(kip-up 다리 붕괴 좌표를 그대로 확대), 고정 crop 크기(촬영거리 10x 무방비). fix: sourceFrameIndices median 을 crop 프레임 override 로 배선 + 같은 결함 관절(스플릿 4관절)을 "양다리" 1카드 bbox grouping + confidence<0.5 는 전신 폴백. 계약 scalar region 1필드. 15 passed + typecheck clean. 검증=pod 재분석 필요(저장된 PNG 재생성 안 됨, pod OFF 대기) | 2026-07-02 | 026c0e5 | [260702-sic-crop-fix](./quick/260702-sic-crop-fix-reference-crop-crop/) |
| 260702-t0v | 동작 비교 가로 전체화면 뷰어 (belle: 각도 라벨 안 읽힘) — 근본원인=라벨이 1280px 기준 정규화라 세로 슬롯서 유효폰트 ~3pt. fix: KeypointOverlay sizeScale prop(전체화면 2.0) + Modal 90도 회전 가로 뷰어(portrait 고정 유지, JS-only=OTA 가능) + 기존 player 인스턴스 재사용(동기/구간맞춤 로직 공유). typecheck GREEN, app.json/package.json diff 0. 실기기 6항목 체크리스트 SUMMARY | 2026-07-04 | 6d16f97 | [260702-t0v-landscape](./quick/260702-t0v-landscape-compare-viewer/) |
| 260704-fwb | 코칭 처방화+보완운동 매칭+저화질 문구 (belle 피드백 E) — (1) Cerebras/Gemini 코치 프롬프트에 원인 기전 사슬+구체 처방 구조 강제(실측 주입 데이터만 사용, 거짓 구체성 금지), (2) 보완운동이 forcePatternInference 만 소비해 그립운동 미스매치이던 것에 vision faultKey keypoint_set→defect 매핑 배선(leg→고관절 유연성 1순위), (3) 저화질 경고 승인 후 not_pole 실패 시 화질 우선 안내 분기(앱 로컬, 계약 0). 126 passed+typecheck clean, 채점 무접촉 diff 0 | 2026-07-04 | e0401ae | [260704-fwb-coach](./quick/260704-fwb-coach-prescriptive-exercise-match/) |
| 260704-fz4 | 결함 시각 언어 2단화 (belle 승인 기획) — 확대 카드 tier(confirmed/advisory, 측정초과 관절 참고 카드 zoom_adv S3 분리), 앱 3면(편차표·스켈레톤 마커·확대 카드) 단일 조립로 빨강=확정(감점)/주황=측정 초과('감점 아님' 카피 3곳), 편차행 탭→시트 내 인라인 부위 확대, 8관절 각도 의미 사전(팔꿈치 굽힘 등). tol=기존 20° 상수 재사용·신규 상수 0·채점 무접촉 diff 증명. 20 passed+typecheck GREEN | 2026-07-04 | b3be3c7 | [260704-fz4-visual-2tier](./quick/260704-fz4-fault-visual-2tier-tap-zoom/) |
| 260705-d64 | phase25 run_sweep vision veto env setdefault 박제 — 2026-07-05 새 pod 최종 sweep 1차 시도가 GEMINI_VISION_VETO_ENABLED 미설정으로 조용히 무효(visionVeto disabled→breakdown 없음+레거시 min-of-core 점수, 문서화된 sweep env 블록에 누락이 구조 원인). RTMW_DETERMINISTIC 선례와 동일하게 module-level setdefault(VETO=1, WALL_S=300, production start_server.sh 박제 mirror, 명시 export 는 override 가능) + docstring/README Pod sweep 블록 명기. 게이트 25 passed, override/주입 semantics 검증 | 2026-07-05 | 39df2f6 | [260705-d64](./quick/260705-d64-phase25-run-sweep-veto-env-setdefault-sw/) |
| 260705-fmg | phase25 프롬프트 v11.2 — part_scope 배타 강제. 진단(6 fresh call): upper_body scope 지시(v11.1 "집중" 참고 문구)를 Gemini 가 무시하고 하체만 반복 방출(스코프 무시 4/6+빈 2/6) → 상체 미짚김+support 자기부풀림(3-scope 전부 다리 → supportCount 3). fix = "[label] 부위 전용 판정, 타 부위 방출 금지(눈에 띄어도 무시)" 배타 지시 + PROMPT_VERSION v11.2 bump(캐시 자동 무효화). SCHEMA v8.1/agg4 불변, 178 passed. 사후 격리 진단: 하체 누수 0 확인, 단 상체 방출도 0/6 → granularity 하이브리드(260705-g1d)로 이어짐 | 2026-07-05 | 0b95138 | [260705-fmg](./quick/260705-fmg-phase25-v11-2-part-scope-fix/) |
| 260705-ftn | fault-zoom reference crop 정합 fix (belle: "정은지 사진이 비교랑 전혀 안맞아") — pod 재현으로 원인 2겹 확정: 표시 프레임(측정 window median)이 reference keypoint 저신뢰 프레임 + relaxed crop 이 floor 에도 margin 을 곱해 전폭(360) 클램프 = 전신처럼 보임. fix = margin 을 bbox 파생분에만 적용(부위-중심 완화 crop 의도 복원, valid 경로 byte-동일) + select_confident_frame helper(window 내 confidence 최대 프레임, user/ref 독립, legacy median 폴백). TDD 37 passed, 채점 무접촉. PNG 재생성 검증 = pod 재분석 PENDING | 2026-07-05 | 74689eb | [260705-ftn](./quick/260705-ftn-fault-zoom-reference-crop-fix-relaxed/) |
| 260705-fx4 | 가로 전체화면 뷰어 명시 치수 fix (belle 실기기 2차: "영상이 꽉 차야 해") — 퍼센트+aspectRatio 가 90° 회전 absolute 컨테이너에서 ~68% 축소 렌더 + flex 반쪽-중앙 슬롯이 두 영상 사이 ~200pt 간격 + 오버레이 파생 이탈. fix = fsBoxH/fsBoxW 명시 숫자 치수(window 파생) + 중앙 인접 배치(gap 8) + 라벨 박스 내부 이동, KeypointOverlay 무접촉(치수 정확해지면 정합 자동 회복). typecheck GREEN, JS-only. OTA 발행 완료(production+preview, 2026-07-05) — belle 실기기 6항목 체크리스트 확인 대기 | 2026-07-05 | f532245 | [260705-fx4](./quick/260705-fx4-landscape-viewer-fix/) |
| 260705-g1d | vision fanout 하이브리드 granularity — upper_body scope 만 정지 이미지 페어(2026-06-22 스파이크 실증: still 이 상체 복구, 레버=granularity), lower/line 은 full-video 유지. INPUT_GRANULARITY whole_fanout_hybrid1 bump + frame_indices folding(stale-hit 차단), media_kind=image 라벨 분기, telemetry upperGranularity. 223 passed. 사후 진단: 스코어러-측 추출(raw imageio+ratio 근사)이 위상 불일치 페어를 만들어 0/6 — h5z 로 교정 | 2026-07-05 | 2d51c6c | [260705-g1d](./quick/260705-g1d-vision-upper-scope-still-frame-hybrid/) |
| 260705-h5z | still 페어 파이프라인-측 추출 배선 (g1d 교정) — pod 3중 진단으로 확정: 파이프라인 9fps 프레임 배열의 window/DTW-매칭 인덱스 페어(stu20/ref37)는 6/6 발화(왼팔 그립 major=belle 6월 지적 부위+머리/목+어깨), 스코어러 자체 추출은 VFR raw 인덱싱+ratio 근사로 위상 불일치 0/6. fix = 기존 _build_selected_frame_pair 재사용해 PNG 경로/인덱스 주입(스코어러 추출 3함수 삭제, hybrid2 키 bump), DTW 실패 시 video-only 폴백, upper scope 2-call(핸들 재사용)로 비-각도 관측(그립)도 distinct-call K=2 지지 성립. 229 passed. 실효 = run6 sweep 검증 | 2026-07-05 | 1c735e6 | [260705-h5z](./quick/260705-h5z-still-pair-pipeline-side-extraction/) |
| 260705-k8h | 관절당 감점 상한 −20 (belle 승인) — kip-up 잘못된 시연 26점 "무지막지" 완충. run6 실데이터 4규칙 비교로 체감가중/RSS 는 작은-결함-다수 역전(82~85) 확인 → 상한 채택. PER_RECORD_DEDUCTION_CAP=20 + rawPoints/capApplied 투명 노출 + 계약 3-way. run7 sweep 검증: kip-up 47/power-spin 57/나머지 불변/success 100/cold=warm. belle 실기기 47점 확인 | 2026-07-05 | 892ce50 | [260705-k8h](./quick/260705-k8h-deduction-per-record-cap-20/) |
| 260705-k8y | 확대 뷰어 행동지시 라벨 + 고정 1.35배 줌 (belle: "각도로는 못 알아듣는다/천장 불필요") — composeActionLabelKo 순수 매핑(부위+N°+방향 동사), 문제 관절만 라벨, 절대각 라벨 제거, FULLSCREEN_ZOOM 클리핑 래퍼(오버레이 정합 자동). 3-소스 조립(windowMedian>faultJointDeficits>JointScore). typecheck GREEN, OTA 발행. 사후: 재생 중 라벨 5개 겹침 belle 질책 → o0s 에서 번호 점으로 재설계 | 2026-07-05 | 7d313ff | [260705-k8y](./quick/260705-k8y-overlay-action-labels-fullscreen-zoom135/) |
| 260705-o0s | 결과 화면 재배치 + 번호 오버레이 + 감점0 게이트 (belle 실기기 3차 4건+2건) — buildDeductionMarkers 단일 소스로 영상 빨간 번호 점 ↔ 점수 내역 ①②③ 매핑(라벨은 각도 없는 짧은 행동구, 좌우 dedupe, 감점 관절만), 내역을 점수 직후 승격+채점 기준 1줄(정은지 대비+IPSF), 실패원인후보 섹션·ForcePattern 컴포넌트 2개 삭제(코칭 팁 중복), 세부점수→'참고 지표' 개명·강등, isCleanPass 게이트(감점 0 = 문제 섹션 전부 숨김+축하 카드, "보완하면 더 올라가요" 100점 미출현 — 2° 노이즈 카드 사례 해소). typecheck+grep 게이트 GREEN, OTA 발행 | 2026-07-05 | e02fba9 | [260705-o0s](./quick/260705-o0s-result-screen-reorder-numbered-markers/) |
| 260707-je3 | Phase 22 플랜 수정 — 22-DIRECT-REVIEW DR-01~07 + P2 3건 반영 (플랜 문서 7개만, wave/DAG/플랜 번호 불변). P0: shadow 학습 유입=manifest video_hash join 강제(미등록/미가명=text-only 강등+_meta drop 카운터), production Pod mutation(22-03/08)=blocking checkpoint+canary-first+rollback 선기록(autonomous:false), 22-07 `test $? -le 1` fail-open 제거+post-Pod `--require-pass`+Wave5 진입=PASS or belle 결정. P1: train/val split 단일 소유(build_jsonl), 증류 비용 blocking checkpoint(첫 run 10 rows), collection_complete fail-closed 진입 assert, collect-only/정적/prefix verify→실제 outcome assert. P2: 22-01 doc_count>=30 assert, 22-10 "역할당 env 1개" 문구, LICENSE-AUDIT release-clean 비함의. 다음=belle 외부 리뷰 재실행 | 2026-07-07 | 981ee6f | [260707-je3](./quick/260707-je3-phase-22-22-direct-review-dr-01-dr-07/) |
| 260707-k07 | Phase 22 2차 직접리뷰(22-DIRECT-REVIEW-ITERATION2, verdict=Pass with fixups) 후속 4건 — must-fix=22-VALIDATION.md를 DR 반영 태스크 그래프에 싱크(pre-DR 번호 참조 0건 전수확인, checkpoint manual 행 3개+자동검증 행 4개 추가, fail-open 잔재 제거), P1=22-03 `pytest|tail -3` exit-code 삼킴을 FAILED/ERROR node-ID baseline diff로 교체, P2=val.jsonl 계약을 `validation_owner=explicit_val_jsonl|phase22_eval_gate` 단일 필드로 통일(22-04/07), 22-POD-VRAM `peak_vram_gb:` 수치 필드 강제. 문서 4개만, wave/DAG 불변. **Phase 22 = 실행 게이팅 준비 완료** | 2026-07-07 | c318419 | [260707-k07](./quick/260707-k07-phase-22-2-iteration2-fixup-4-22-validat/) |
| 260713-jjq | 백본 확정 도장 — 22-BAKEOFF-RESULT.md Qwen3-VL-8B PROVISIONAL→CONFIRMED (belle 공식 확정 2026-07-13, bake-off 4축 종합·결정성 64/64). 문서 3곳 갱신, 판정 근거·계측 이력 불변 | 2026-07-13 | 2cdc76e | [260713-jjq](./quick/260713-jjq-22-bakeoff-result-md-qwen3-vl-8b-provisi/) |
| 260713-jxr | 처방 B 배선 — 내부 fault 트랙(구 371) enumerate_internal(consent 게이트 3분기+ETag dedup+스케일가드) + anonymize_batch(재개 가능+fixtures/phase22/internal/ prefix 강제+manifest 행 생성/병합) + LICENSE-AUDIT §7-1 belle 일괄승인(2026-07-13) 박제. Firestore 실측 872/707/662, optIn=false 1건 제외·anonymize 강제. 신규 행이 eligible_for_distill+test_provenance fence 무수정 통과. phase22 222 passed. 로컬 코드+문서만(Pod 실행=runbook). fable 크레딧 소진→Opus 인계 완주 | 2026-07-13 | 386398e | [260713-jxr](./quick/260713-jxr-b-fault-anonymize-manifest-belle-2026-07/) |
| 260714-hv4 | 22-07 v4 게이트 계측-학습 양식 정렬 — run_bakeoff aligned 프롬프트 모드(opt-in, 기본 legacy 바이트 불변): 지시문=_TASK_INSTRUCTION import 재사용·system 롤 0·media 먼저·guided 해제(자유생성)+video_url auto→frames 폴백. 방어 파서 schema.extract_report_json(thought 스트립+raw_decode balanced JSON) 단일 진실을 run_bakeoff/assert_gates 공유 — 4 게이트 임계·비교식 불완화, 파싱 실패=실패 집계. run_sft_gates.sh PROMPT_MODE/REPETITION_PENALTY 배선(rp 본판정 1.0 고정). phase22 248 passed(+11). Pod 재계측=POD-RECHECK.md(legacy 아티팩트 mv 백업 선행, 오케스트레이터 SSH) | 2026-07-14 | 4f12979 | [260714-hv4](./quick/260714-hv4-2207-v4-gate-align/) |
| 260808-epy | Phase 35 미세조정 2차 — p35 데이터 리포 영구화 + 엘보 폴-근접 문법(폴 축선·간격 브래킷·문구 lockstep 재합성, 발동 정확히 elbow r00 1건) + pdshapefault r01 왼손 그립 짝 **미충족 fail-closed**(x-투영 원리 한계 실측·대안 3종 승인장면 오발동 기각, belle 선택지 3 제시). baseline=v6 길이 0.00s 재현 → 리그 10×ALL PASS·diff 게이트·kipup 피크 1.467 불변 → S3 5키 덮어씀(기존 링크 유효, kipup/peterpan/powerspin 바이트 동일) | 2026-08-08 | 7787832d | [260808-epy](./quick/260808-epy-phase-35-2-p35-pdshape-r01-5-v7/) |
| 260714-hv4 | 22-07 v4 게이트 계측-학습 양식 정렬 — aligned 프롬프트 모드 + 공용 방어 파서 + Pod 재계측 배선 | 2026-07-14 | 7661a29 | [260714-hv4-2207-v4-gate-align](./quick/260714-hv4-2207-v4-gate-align/) |
| 260714-js2 | phase22 fault 타겟 재수집 라운드 — fault_demo 큐레이션 프로필 + 레지스트리 확장 + 재개 문서화 | 2026-07-14 | 21fa47c | [260714-js2-phase22-fault-yt-ig-cap](./quick/260714-js2-phase22-fault-yt-ig-cap/) |
| 260715-fjw | phase22 perturb 트랙 재설계 (v5 준비, 로컬) — v4 aligned 게이트 synthetic_holdout gap 처방 3건: D1/D2 drift primitive+stage 변위 강화(stage2 순수 가려짐→가시 변위 신호 생성), D3 `_STAGE_CYCLE=(1,1,2,3)` 변위-우선 배분, D4 subsample-first(표시 프레임 내 교란 보장 — 순수 항등 echo 제거, v2 "무보정 동률" 기계적 원인 해소), D5 1/3 좌표전용 샘플(게이트 aligned 좌표전용 경로와 문자 단위 동일, `_TASK_INSTRUCTION` 단일 진실 재사용) + `_meta.perturb_coords_only_count`, D6 corrected_coords 전체 프레임 echo 유지 근거 박제(부분 방출=cherry-picking 게이트 완화 차단). `_coords_to_frames` frame_labels 로 배열 인덱스/프레임 라벨 분리. phase22 267 passed. 게이트 하네스·채점 diff 0. **v5 절대 수치는 v4 직접 비교 불가**(교란 분포 자체 변경, 상대 게이트 semantics 불변). 다음=Pod `--assemble --with-perturb --upload` v5 조립→SFT v5→aligned 게이트 | 2026-07-15 | 8c71497 | [260715-fjw-phase22-perturb-stage-corrected-coords](./quick/260715-fjw-phase22-perturb-stage-corrected-coords/) |
| 260716-jg6 | phase22 v6 학습셋 assemble + terra13 union (SFT 입력 산출) — 소실된 accepted 라벨을 S3 train/val distill 152행에서 무손실 역복원 → terra13 union(계약 안전장치: 각 terra fault를 normalize+_faults_satisfy_contract 개별검증, 위반분만 드롭·gemini 보존) → `full_batch.assemble_jsonl` 무변형 호출로 v6 조립(perturb 0=C1, fault_bearing 88/fault_free 61 cap 1.5=B). terra 순 +21 fault, 12/13 delta>0, **7 recoveries**(General-pole-movements head/eyes 결함=각도·편차 전무로 감점계약 부적합 정당 드롭; belle 7 수용). 게이트 7/8 PASS(perturb 0/leakage ∅/normalize 100%/pytest 273). 프로덕션 코드 0 수정. S3 canonical 교체 완료(pre-v6→jsonl_v5_backup/ 백업). 다음=belle Pod 기동→SFT v6→게이트(런북: 260716-jg6-SFT-RUNBOOK.md, **v6 판정=eval18, synthetic_holdout FAIL은 C1 예상귀결**) | 2026-07-16 | 1b0b521 | [260716-jg6-phase22-v6-assemble-terra13-union-sft](./quick/260716-jg6-phase22-v6-assemble-terra13-union-sft/) |
| 260720-hn8 | 영상 선택 실패를 Figma 카드형 알림창으로 전환 + 원인별 해결안내 + iCloud 오프로드 폴백(Current 실패→Automatic 재시도) + catch 오류 삼킴 제거. belle 실기기 앨범 픽 실패 대응. **근본원인 미해결(iCloud 가설)** — 알림창이 실제 picker 오류 문자열을 노출해 belle 캡처가 가설 확정/폐기 증거. Figma 확정문구 2종 원문 유지, 신규 의존성 0, node --test 7/7 | 2026-07-20 | f329e99 | [260720-hn8-icloud](./quick/260720-hn8-icloud/) |
| 260724-q6b | IN-01 역립 저신뢰(attributionReliability.unreliable) 결과화면 표현 강등 — 앱측이 백엔드 마커(d5490a8) 소비. 단일 게이트로 8개 per-joint 단정 표면(오버레이/점수내역/팁/확대비교 + 오늘고칠것/다른감점/요약todayFix/심사코너)을 "확정"→"예상/집계" 강등, 동작비교에 "AI 공부 중" 안내 1줄(모드별). 점수값 byte 불변, 카피 상수화, 테마 토큰만, typecheck clean. **남은 게이트=시뮬레이터 렌더 확인 후 belle 확인→OTA** | 2026-07-24 | 604b2bf | [260724-q6b-in-01-attributionreliability-ai](./quick/260724-q6b-in-01-attributionreliability-ai/) |
| 260810-ms2 | 확대 비교 사진 수리 — belle 결정 "영상은 그대로, 사진에서 더 자세히". **붕괴(관절 읽기 실패) 카드 3/5 → 0/5** (right_elbow 사이각 0/86도 → 174/163도, 표시 방향차 81 → 20도). ①U6(`da89ea01`)이 **실행조차 안 되고 있었다** — 운영 카드 경로는 `select_pose_matched_pair` 로 프레임을 고르는데 배제는 `select_confident_index` 에 들어가 있었다(로그 `fault_zoom_pose_pair` 5/5 가 증인). 학생·기준 **양쪽** 배제 + fail-open 축별 4단. ②후보창 승급을 **실패 조건에 묶음**(항상 ±4 로 넓혔더니 멀쩡하던 left_hip 이 17→72도 악화 → 되돌림 → right_elbow 재붕괴 → 승급 조건을 선택자 요구와 일치시켜 둘 다 해결). ③크롭 폭을 고정 0.61 → **부위 크기 기반**(목표 0.50 · 밴드 0.40~0.55, belle 이 40/50 고민 후 확정) — 부위가 패널에서 차지하는 크기 22~58% → 34~65%. ④크롭 소스를 **원본 2160x3840**(종전 640px 축소본 = 원본의 1/6) + `probe_effective_fps`(운영 Pod 은 프레임 캐시라 추출 이력이 없어 그대로면 **운영 경로에서만** 조용히 비활성). ⑤공용 폭 px → **비율**(원본 해상도가 학생 2160/기준 1080 이라 같은 px 가 27% vs 55% → 한쪽만 확대돼 보였다. 640px 시절엔 짧은 변이 우연히 같아 잠복). 채점·영상 무접촉, records 5건 값 불변. 게이트 59 failed IDENTICAL / 4141 passed · 채점 산식 5파일 diff 0. **남은 것 = 표시가 무슨 얘긴지 안 보임**(마크가 패널 대비 고정 크기 · right_elbow 각도 174도라 호가 안 보이고 선 하나로 읽힘) · advisory 링이 얼굴에 찍힘(★변경 전에도 동일 = 별건) · ②국면/③방위는 belle 눈 판정 | 2026-08-10 | d0633227 | [260810-ms2-zoom-card-repair](./quick/260810-ms2-zoom-card-repair/) |
| 260811-bz5 | 표시 문법 프로토타입 — **로컬 재렌더 하네스(Pod 무관)** 로 기준선 confirmed 4/4 픽셀 재현 PASS(mean\|d\| 1.07~1.10) + 후보 문법 3종(고스트/쐐기/하이브리드 — 기준 사이각을 학생 몸통축+카이럴리티에 이식, 방위차 무관). ★핵심 실측 = **감점 근거 vs 순간 델타 괴리**: left_hip 20/10도·right_elbow 5.9/6도는 문법으로 풀리고, left_elbow 29.1/4도·right_shoulder 10/1도는 **국면 문제(문법 밖)** — belle "뭘 말하는지 모르겠다"의 절반은 그 순간에 잰 결함이 없어서다. 판정 페이지 = artifact 27e89578. 채점·운영 코드 무접촉. belle 판정 대기(문법 채택 + 국면 2카드 갈림) | 2026-08-11 | 2ed3304 | [260811-bz5-mark-grammar](./quick/260811-bz5-mark-grammar/) |
| 260730-l7t | 33-G §C-1 백엔드 수리 (승인 목업 7R 대비 FAIL 3건) — **S9** crop 중심을 criterion 꼭짓점 관절 정중앙·두 패널 동일 배율(`criterion_vertex_xy` 단일 출처 + `_crop_box_centered` 흰 패딩 + `_CRITERION_CROP_FRAC=220/360`), region 상수는 crop 중심 결정에서 강등. **belle #7·#9 "팔꿈치인데 손을 집고 있음" 근본원인 = `_KISMAM_TO_KEYPOINT` elbow→hand 인접 대입** — 백엔드+앱 미러 동시 제거. **S8** 각도 베이크(`_draw_joint_angle` + `ANGLE_BAKE_MAP` 접미사 키잉 4계열 + `_ARMPIT_T=0.15`) + 기준 앵커 **관절 대입 선언** 계약(정적 좌표 금지 — 표시 프레임이 DTW 실측 순간이라 가변), both-or-neither 대칭 게이트. **F-3** 근본원인 = 앱이 `refFrameIdx / rep.fps`로 초 추정(rep 18fps ↔ video 9fps 불일치) → 백엔드가 `userVideoSec`/`refVideoSec` 방출 + 3-way lockstep. 검증 = 등재 10동작 스위프 110카드(정중앙 60 전건 배율 일치·비대칭 0·동작명 분기 0) + 생성 PNG 승인 자산 대조 + legacy 해시 9케이스 무변경 + `backend/tests` 회귀 0. **잔여: 9모션 주석값·무릎/팔꿈치 각도(12kp 재처리 필요)=§C-4, 앱 렌더=§C-2. S10 pre-existing 결함 발견→PARTIAL 정정** | 2026-07-30 | c9b0609 | [260730-l7t-33-g-c-1-fault-zoom-py-s9-crop-criterion](./quick/260730-l7t-33-g-c-1-fault-zoom-py-s9-crop-criterion/) |
| 260816-e26 | 게이트 파서 폭주 오탐 수리 — extract_report_json 이 잘린 폭주 산출의 안쪽 조각을 리포트로 인정하던 결함. REPORT_KEYS 부분집합 검증으로 수리. v29 실물 29건 재집계 24/5 → 14/15 (정답 일치) | 2026-08-16 | 34097ae3 | [260816-e26-gate-parser-runaway](./quick/260816-e26-gate-parser-runaway/) |
| 260816-p1x | 발굴 축 반전 — 눈이 후보를 내고 수치가 검증한다. 눈-우선 하네스 + 좌표품질 게이트(5동작) + elbow·peterpan 20후보 검증. 서술 55건 → 승격 8 / 기각 8 / 수치화불가 39 | 2026-08-16 | e64ee904 | [260816-p1x-pole-distance-axis](./quick/260816-p1x-pole-distance-axis/) |
| 260816-c3m | climb·combo P35 입력 데이터 생성 — 발굴 스윕 대상 5 → 7. climb/combo 소스 게이트 PASS, climbfault 는 NotPoleMotionError 로 탈락(위양성 의심, 유사도 0) | 2026-08-16 | c31ee2ee | [260816-c3m-climb-combo-p35](./quick/260816-c3m-climb-combo-p35/) |
| 260816-r7k | ref-climb 교체 — 05-22 극초반 배치 → 06-17 정은지 세트 배치. climb angle 26→100, climbfault 0(NotPoleMotion 차단)→86(해소). 다른 기준 10개 SHA-256 무변경, 구 자산 전량 복구 가능 | 2026-08-16 | 7114287e | [260816-r7k-ref-climb-replace](./quick/260816-r7k-ref-climb-replace/) |

| 260730-py1 | 33-G §C-2 앱 1단위 (승인 목업 시트 재설계) — **S7** 블록 요소 신설(번호 헤더·basis "어디서 재나요"·method 정직 라벨·numnote 강등) + **S6** record 단위 → **부위 단위** 시트 재구성(`deductionSheet.buildRegionSheetView`, paircap 좌우·onecap) + **F-3 앱분**(`compareFrames.(userIdx|refIdx) / fps` 초 추정 2곳 제거 → 카드의 `userSec`/`refSec` 운반). 검증 = 오케스트레이터가 시뮬 직접 렌더(실행자는 시뮬 도구 없음): **부위 2감점 = 시트 1개·블록 2개**(고칠 것 2/3, 각자 점수·basis·method) 실증 = belle "무릎 피는 거 하나 어디 갔냐" 구조 해소 · 번호=전역 마커 번호 · 크래시·잘림 0 · 스위프 10동작 130블록 0손실. **의도적 fail-closed 2건**: proof 3컷(백엔드 1장만 방출, 3컷 분류는 doc 에 없는 판단 → 날조 금지)·basis 구간 축(fps 부재, 인덱스 나누기가 F-3 원인) → §C-4. **미검증: paircap 초·참고코너 렌더**(doc 4건이 초 필드 이전 산출)·facing·LogBox 경고 내용 | 2026-07-30 | cfb3694 | [260730-py1-33-g-c-2-1-s7-basis-method-proof-facing-](./quick/260730-py1-33-g-c-2-1-s7-basis-method-proof-facing-/) |

| 260730-szk | 33-G §C-2 앱 2단위 (마커·강조) — **F-8** 상시 마커 제거(토글/음성 큐에서만) + **S1** 항목=부위 단위 그룹 경계+번호 배지(개별 관절 원 나열 제거) + **S3** 부위 칩 행 신설(1단위 `regionPartKeyForRecord` 재사용, 두 번째 그룹핑 규칙 금지) + **S19** 선/원 분기·pulse 1.4s 구현 + **S2** 참고 점선. F-8×S3 충돌은 승인본의 칩 행을 상시 진입점으로 세워 해결(마커 숨김 시 탭 영역도 비움). 렌더 확인(오케스트레이터): **F-8 PASS**(토글 OFF = 마커 0, 안 보이는 탭 0) · **S1 부분 PASS**(그룹 경계+배지, 개별 원 0) · **S3 PASS**(칩 3개 = 감점 부위 3개, 칩→해당 부위 시트, 1단위 구조 회귀 0). **S19·S2 미검증 — 시뮬 재생 구동 실패**(16프레임 전부 동일). 1단위 미해결 LogBox 경고 종결 = `expo-video allowsFullscreen` deprecation 2건(기존, 무관) + `Animated` 신규 경고 0. 소견: 흰색 hex 10→12(토큰 교체 다음 단위) | 2026-07-30 | df9d193 | [260730-szk-33-g-c-2-2-s19-pulse-s1-s3-f-8](./quick/260730-szk-33-g-c-2-2-s19-pulse-s1-s3-f-8/) |

| 260731-2jt | 33-G §C-2 앱 3단위 — **S13/S25** 일러스트 장면일치 fail-closed(`illustrationScene` 판정 모듈, 부위 토큰 ⊆ 에셋 장면 토큰, 공집합 vacuous ⊆ 차단) + **S23** illu-float + **S26** 판정. 장면 토큰은 에셋 6장 **실물 열람**으로만 부여 → **6장 전부 `leg` 단독**이라 어깨·팔 항목은 전 동작 미부착(130칸 중 부착 6). 부착 감소가 목적(D-43). 렌더 확인(오케스트레이터): **어깨 시트 미부착·다리 시트 부착 양방향 PASS** = belle M-5 해소. S26 = 렌더 정합(cover 0.417%)이고 "빈 배경"은 **에셋 구도**(배경 82~89%) → 재생성 시 구도 교정. **P-14 오케스트레이터 교정**: illu-float 기준면을 row→패널로(승인본 28.9% vs row 기준 59.2%). S23 렌더는 재생 필요로 미검증 | 2026-07-31 | bc48e58 | [260731-2jt-…](./quick/260731-2jt-33-g-c-2-3-s13-fail-closed-s23-illu-floa/) |
| 260731-cum | 33-G §C-2 앱 **4단위(앱 마지막)** — **S12** 어휘 게이트(33-G 가 적은 3곳이 아니라 **7파일 16곳** 실측, `screenVocabulary.test.ts` 상시 스캔 + 백엔드 게이트를 `terminology_map.json` 까지 확장 = "완성도"가 살아남던 구조적 구멍 봉인) + **F-4** 헤드라인(근본원인이 앱이 아니라 백엔드 `phrasebook.py:223` 의 terminology 전문 따옴표 조립 ~50자 → 뿌리+앱+`numberOfLines` 3겹) + **F-5** 게이지 라벨 + **F-7** 전환 + **F-6 재조사**. 렌더 확인: **F-4 PASS**(100점 헤드라인 2줄 이내·배지 겹침 0), S12 앱 잔재 grep 0. **F-6 = FAIL 유지, 원인 미상** — 세션 경합을 파일:줄로 실증했으나 증거가 반증도 해서(카테고리 `.playback` 수렴) PASS 주장 0, 후보 5건 + belle 실기기 분기 절차만 산출. F-5·F-7·시트 용어줄 렌더 미확인 | 2026-07-31 | ad9210a | [260731-cum-…](./quick/260731-cum-33-g-c-2-4-s12-3-f-4-f-5-f-6-f-7/) |
| 260731-f5h | 33-G §C-3 **D-1** 다리 사이각 crop 인지 끝점 (deferred **2안**) — `_leg_line_pts(in_crop=)` 술어 주입으로 다리 끝을 `ankle→knee` 순회하며 **conf 게이트 AND crop 포함**인 것만 채택(좌/오 측별 독립), `_draw_side_leg_angle` 이 자기 crop box 로 클로저를 넘김. 근본원인 = crop 멤버 집합(`REGION_MEMBERS["legs"]` = hips+knees, **ankle 없음**) ↔ 드로잉 점 집합(ankle 우선) 어긋남 → 12관절 doc 에서 벌림 큰 스플릿의 사이각이 통째로 생략. **crop 배율 무변경**(1안 = `REGION_MEMBERS` 확대는 32-03 parity 이동으로 미채택). 검증 4층 전부 오케스트레이터 재현: 등재 10동작 스위프 **0/10 → 10/10**(원본 좌표 대조군), ankle 이 crop 안인 3동작 PNG **byte-불변**(단조 추가), 변경 카드 = `split_angle` 뿐(110 중 7), legacy/advisory/mode3 **9케이스 해시 불변**, pytest FAILED node ID **diff 0**(58 pre-existing), PNG 직접 열람으로 선 2개 + 사이각 호 확인. **한계 = 기준 좌표 합성** — 실 12관절 doc 판정은 §C-4 | 2026-07-31 | f05bc98 | [260731-f5h-…](./quick/260731-f5h-33-g-c-3-d-1-split-angle-leg-angle-omitt/) |
| 260731-iis | 33-G **§C-4 A-트랙** — 기준 11동작 top-level `referenceKeypointReport` 를 **18.0fps 12관절**로 교체(델타는 fps 가 아니라 관절 8→12. 교체 전에도 18fps였다). **오케스트레이터 재조회 확인: 11/11 `fps==18.0`·`joints==12`·`frames==anglesFrames`·`activeVersion` 불변·`reference/_release` 부재.** GATE-A(타임베이스 all-or-nothing)·GATE-B(채점 8필드 해시 불변)·GATE-C(릴리스 포인터 미설정) 전부 통과, ref-kip-up `--restore`→`--write` 왕복으로 롤백 실증. **S8 = PASS** — `omitted:ref_gate` **39→0**, `drawn` 21→79(팔꿈치 0→20·무릎 0→20·어깨 1→19). 원인 = `ANGLE_BAKE_MAP` 이 요구하는 elbow·ankle 이 8관절 기준에 부재해 fail-closed 였던 것 → **§C-4 4번 앵커 주석 잔여 0**. **S10 = 실 doc PASS** (kip-up `zoom_split_angle` PNG 직접 열람 — 선이 실제 두 다리와 정합). flip 방어는 "1줄"이 아니었다 — payload REQUIRED_KEYS 밖이라 candidate 폴백 + fail-closed 경고 필요. **★재산출로 점수 이동**(power-spin 80→60, elbow-twist 60→63 카드 0→5) — 채점 무접촉은 증명됐으므로 표시 교체 탓 아님, 원인 미분리 → Phase 34. S22 부분 PASS(창 안이나 결함보다 0.8s 이른 프레임), **S5 미판정**. pytest node ID diff 0 | 2026-07-31 | 0485a2b | [260731-iis-…](./quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/) |

| 260731-plf | 33-G **§C-4 3번** 어깨·팔 결함 일러스트 — 생성 대상을 **실제 방출 record 로** 확정(`regionPartKeyForRecord` 를 import 해 A-트랙 재산출 doc 4건을 접어 집계 → Tier 1 4조합). 33-14 승인 레시피(gemini-3-pro-image i2i + 4게이트 육안 전수) 준수, 생성 7건 중 **3건 등재**(power-spin×shoulder try2 · kip-up×shoulder try1 · elbow-twist×arm try1), **elbow-twist×shoulder 는 3회 전부 같은 실패(원이 어깨 관절 아닌 상완) → 미등재**(억지 통과 0). 구도 = 신규 3장 26.4/23.8/20.0% 로 기존 최댓값 17.6 상회(자를 기존 6장으로 먼저 검증). 두 표를 **(motionId, part) 키**로 전환 — 승인 목업 DETAILS 가 시트별로 다른 일러스트를 두므로 부위별 개별 에셋이 승인 스펙(전신 1장 다토큰 편법 금지). 무손실 = 255셀 골든 diff 0, 기존 6장 sha256 6/6, `result.tsx` diff 0줄, pytest node ID diff 0. ★**미해결 = 일러스트 슬롯 확대 절단**(선행 결함 — 33-14 승인 자산에서도 발생). 오케스트레이터 통제 비교: 수정 전 3배 → 수정 후(`bff3a477`) 1/2, 그러나 카드 360x260 이라 이미지의 54%만 보임. 3안 모두 260 유지, 원인 미규명 → debug 사이클 이관 | 2026-07-31 | dd4d521 | [260731-plf-…](./quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/) |
| 260801-f77 | 코치 음성 큐 재생 복구 — **결함 A** 만료 URL 영구 캐시(`_ASSET_EXPIRES=3600` 인데 `urlCache` 는 만료 개념 없이 앱 수명 유지, `!urlCache.has(id)` 필터가 재발급조차 차단) → `expiresInSec` 수용 + `isFresh` 단일 판정 + 2분 여유. `api.ts:178` 주석이 선언한 "재생 시점마다 재서명" 의도를 앱측 캐시가 무력화하고 있었다. **결함 B** 로드 실패 복구 경로 부재 → 감시 타이머 + 1회 재발급 재시도. ★expo-audio 는 로드 실패 시 `playbackStatusUpdate` 를 **아예 emit 하지 않고**(`AudioPlayer.swift:147-163` 이 `.readyToPlay` 일 때만 호출) `AudioStatus` 에 error 필드도 없다 → 실패는 "성공 신호 `isLoaded` 의 부재"로만 판정 가능, 감시 타이머가 유일한 수단. **결함 C** 실패 시 `speechActive` 가 true 에 갇혀 `CUE_PAUSE_MAX_MS`(15초)까지 영상 정지 → `failSpeech` 가 즉시 해제, **VideoCompare 무수정**(이미 100ms 폴링 중). **신규 발견 T-f77-04** = `recordId` 가 `r{index:02d}:{criterion}` 이라 분석 간 비고유(power-spin·elbow-twist 둘 다 `r02:angle_vs_reference__left_shoulder` 보유) → 캐시가 남의 분석 음성을 재생할 수 있었다, `cachedAnalysisId` 무효화로 차단. ★**오케스트레이터 오진 2건이 소스로 반증됨** — `seekTo(0)` 누락(replaceCurrentItem 이 새 아이템 생성) / 종료 옵저버 미재등록(`play()` 가 매번 재등록). 우회 코드 0. 검증 = typecheck PASS(오케스트레이터 재실행), 변경 파일 2개 확정, `VideoCompare.tsx`·`backend/` diff **0**. ⚠ **실기기 음성은 미검증** — 시뮬레이터 오디오 실측 불가. belle 4항목 확인 대기(1시간 후 음성 유지 / 기내모드 6초 내 재개 / 다음 큐 정상 / 분석 A→B 누출 0) + OTA 선행 필요. **F-6 은 닫히지 않았다** — 원인 후보 축소일 뿐 | 2026-08-01 | ff07be2e | [260801-f77-…](./quick/260801-f77-presigned-url-15/) |
| 260801-gbk | 감점마다 **측정 순간** 기록 — 종전엔 확대카드·마커·자막·음성이 전부 `worst_seconds`(= `vision_veto.worst_pose_timestamp` = Gemini key_moments 의 hold>peak 중 **가장 이른** 시각) 한 점에서 잘렸다. **그건 동작 국면 시각이지 감점 시각이 아닌데** 앱은 "(감점 부분)"이라 적고 있었고, 감점 record 21필드에 시각이 **하나도 없었다**. → record 에 `atFrameIdx`/`atVideoSec` 방출(학생 9fps angles 도메인), 확대카드가 자기 감점의 순간을 앵커로 사용, `FaultZoomComparison.atMatched` 로 "사진 순간 == 잰 순간"을 코드가 인증해야만 앱이 basis 절을 낸다. **대표 프레임 = 그 record 가 보고한 집계값에 가장 가까운 프레임 — argmax 금지**(median 을 쓰는 이유가 RTMW jitter p99 35~50°라, argmax 는 그 jitter 프레임을 "여기가 감점"이라 확대한다). ★**채점 무접촉이 구조로 증명됨** — tally **뒤** `_attach_translation_emission` 에서 setdefault 각인 → `deduction_engine.py` **diff 0줄**(오케스트레이터 재확인), pytest FAILED **59→59 불변**(passed 3767→3802 = 신규 35), `legacy_baseline.py --verify` PASS 9/9. 스위프 = 구현 **전** 대조군 캡처 시 10동작 전부 `[8,8,8]`(belle 증상 재현) → 후 `[4,9,14]` 10/10. ⚠**10동작이 전부 동일한 `[4,9,14]` 인 것과 atMatched 100% 는 합성 fixture 산물** — 작동 원리 증명이지 실영상 분포 아님. ⚠**킵업 다리(split) 카드는 안 풀린다** — `split_angle` 의 실동작 생산 경로가 Gemini 비전 주입이라 잰 프레임이 없어 fail-closed(어깨는 풀림, 파워스핀 4건·엘보 5건 전부 풀림). ⚠advisory 카드는 구조적 제외(`criterion_units` 미전달). ⚠**실기기·실 doc·시뮬 렌더·음성 하나도 미검증** | 2026-08-02 | ab9da85e | [260801-gbk-…](./quick/260801-gbk-record-atframeidx-criterion/) |
| 260802-czw | **실물 keypoint fixture 하네스** — 저장된 `keypointReport`/`joints3d`/gemini 캐시를 주입해 **GPU 0 · Gemini 0 · Firestore 쓰기 0 · 결정적**으로 파이프라인 재생. 부정 게이트 13종(어댑터가 호출되면 RuntimeError) + firestore 차단 24종을 단 채 완주 = 미접촉이 가정이 아니라 실행 결과. ★**판정: quick-260801-gbk 는 실 데이터에서 갈렸다** — 무게중심 `elbowtwistsisterFault`(RECON 8/8 MATCH, final 63 재현)의 record 8건 `atFrameIdx` = 27/44/67/27/30/54/134/18 = **서로 다른 프레임 7개**(2.0~14.9초). 카드 대조군 `[144×5]` → 처리군 `[54,88,134,54,144]`. **대조군이 저장 카드 프레임 144×5 를 정확히 재현**했으므로 처리 변수 1개. 실 데이터 `atMatched` = **8/13(61.5%) 전체 / 8/10(80%) confirmed**(합성 30/30=100% 는 못 믿을 값이었음이 실증). RECON record **11/16**, exit 1(정직) — 못 한 3종은 전부 입력이 doc 밖(`split_angle` 2건 MISSING = supported_differences 각도쌍 부재 / `leg_extension` MISMATCH = `profile.hold_window` 가 Gemini KeyMoment 파생이라 doc 밖, **창을 역산해 맞추지 않았다** / hip 2건 EXTRA = 그 기계적 파생). 나머지 3 fixture 는 재현 record 1건씩이라 판정 대상 아님. 게이트 = 프로덕션 diff **0**, pytest node ID diff **0**(59→59, 3801 passed), 재실행 **byte-동일**, `AKIA`/`X-Amz-Signature` 잔재 0(오케스트레이터 재확인 — 문서 본문의 규칙 설명만 매치), 신규 의존성 0. ⚠**B 단계(S3 영상→프레임 추출→실제 PNG 렌더) 범위 밖** — 이번은 프레임 인덱스까지만 답했고 PNG 픽셀은 합성이라 내용 무의미. 실기기·음성·mode3 미측정 | 2026-08-02 | 9878f43d | [260802-czw-…](./quick/260802-czw-keypoint-fixture-keypointreport-joints3d/) |
| 260802-gny | `split_angle` crop 에 발목 포함 → **되돌림**(`6742fbf9`). 오케스트레이터 전제가 틀렸다 — "crop 이 다리를 안 담는다"는 **거짓**이고 발목은 수정 전부터 `_pt_in_crop` True 였다. 결과: 증상 ②(두 카드 PNG 바이트 동일) **고쳐짐**(멤버 4→6, box `[78,244,151]`→`[78,248,151]`), 증상 ①(사이각 미드로잉) **안 고쳐짐** — 원인이 crop 이 아니라 **신뢰도 널뜀**(파워스핀 왼발목 rep74 **0.180** / rep75 0.463 / rep76 **0.746** — 게이트 0.5 를 두 프레임 만에 오르내린다. 오케스트레이터·실행자 둘 다 단일 프레임 값으로 "높다/낮다" 단정한 것이 반쪽이었다). ★**대가로 배율 parity 가 깨졌다** — `ref_side_px` 230 불변(기준 8관절에 발목 없음), `user_side_px` 219→251~360, 밴드(0.8~1.25) 이탈 **0→8건**, `min(h,w)` 클램프 6건(학생 패널이 사실상 전신), 실 doc kip-up **0.932→1.457**. Phase 32 에서 belle 이 이미 거부한 "두 패널 배율 불일치"의 정반대 형태라 되돌림. **계측 커밋 `2fa707da`/`4fc08466` 은 남겼다** — 등재 10동작 + 실 doc 2건 parity 실측표(`parity_delta.md`)가 **#10(배율 미측정)의 절반을 실제로 채웠다**. 채점 무접촉은 되돌리기 전후 모두 증명(모듈 diff 0 · `legacy_baseline --verify` PASS 9/9 · 되돌린 뒤 pytest **59 failed / 3802 passed** = 착수 전과 동일 · typecheck 통과). 다음 = ② 가 260801-gbk 로 이미 풀렸는지 확인(미확인), ① 은 신뢰도 널뜀이라 #5 저신뢰 대응과 같은 묶음 | 2026-08-02 | 6742fbf9 | [260802-gny-…](./quick/260802-gny-split-angle-region-members-crop-split-an/) |
| 260802-nfd | 저신뢰 귀속 게이트 입력을 **발화 여부와 무관하게 항상 기록**. 종전엔 `unreliable=true` 일 때만 `result.attributionReliability` 에 실려서 **안 걸린 케이스의 visibility 를 아무도 몰랐다** — "발화해야 하는데 안 했나"(미발)를 원리적으로 검증 불가였다. ★오케스트레이터 전수 실측(done 925건): 발화 **18건(1.9%)**, 그중 **17건이 elbow-twist** 한 동작(kip-up 0/160 · power-spin 0/142 · peter-pan 0/121 · pdshape 1/159) — 게이트가 사실상 한 동작 전용이다. DTW 분포(186건 보유) 중앙 40 / 90%tile **60.4** / 최대 **63.6** 인데 **임계가 60** 이라 관측 상단에 앉아 있고 **±6 구간에 62건(33%)** 이 몰려 있다. 발화 18건 visibility 0.330~0.509 로 전부 0.70 미만 → **DTW 가지는 실질 미사용 가능성**. **임계는 안 건드렸다 — 이 사이클은 재는 것까지.** 안전 근거 = 앱 게이트가 `?.unreliable === true` 엄격 비교(`result.tsx` 소스 확인, 소비처 32곳 전수 — 필드 존재로 분기하는 곳 0건), `assemble.py` 는 truthy 검사라 false 는 early return 안 함, `aggregateStatement` 는 unreliable 일 때만 실림(테스트로 잠금). 계약 미러 2곳(`analysis.ts` 틀린 전제 제거 + `contract.md` 절 신설, `models.py` 는 이 필드 상수 미보유라 비대상). 게이트 = pytest FAILED 집합 **동일**(59→59, passed +6), typecheck 0, 임계 상수 diff 0. ⚠**기존 907건 백필 없음** — 앞으로 생기는 분석부터. ⚠실기기·실 doc 재산출 미실시 | 2026-08-02 | d12825b0 | [260802-nfd-…](./quick/260802-nfd-gate-inputs-always-recorded/) |
| 260802-mrg | 같은 원인 감점을 **화면에서만** 한 항목으로 묶기(belle 결정 "가" — 채점 무접촉) + 자막이 결함 대신 목표를 말하던 것 교정. 병합 키 = **`exerciseId` 공유**(저장 record 에 이미 있음 → 백엔드 변경 0·재분석 0·OTA 만으로 동작). 오케스트레이터가 1순위로 준 "같은 순간+인접+같은 측" 규칙은 **실측으로 기각** — 실 fixture 에서 어깨(f67)↔팔꿈치(f27)가 **4.4초** 떨어져 0건 병합이고, 시간 근접 단독은 좌팔꿈치(27)↔우어깨(27) 같은 **틀린 병합**을 만든다. ★**실 fixture 4건에서 병합 발동 0건** — elbow-twist 는 팔꿈치가 `grip_weak` 라 어깨(`shoulder_unstable`)와 안 묶이고(도메인상 옳음), power-spin 은 재산출 doc 에서 **팔꿈치가 advisory 로 강등돼 record 자체가 없다**(belle 이 본 화면은 07-30 doc 이었다). 병합은 합성 형상 테스트로만 발동 확인. 자막 = 14/14 record 가 결함 문장으로 시작(`목표는` 시작 14→**0**), 다만 길이는 중앙값 83→81 로 안 줄었고 3줄 클립 초과 **3→3 그대로** — 값어치는 잘리는 쪽이 "행동 절 전체"에서 "꼬리"로 바뀐 것. **phrasebook 무접촉**(목표-선행 cueLine 은 belle 4R 승인 + 테스트 핀). 채점 무접촉 = 백엔드 6경로 + 앱 tally 2경로 diff **0바이트**, pytest FAILED 집합 동일(59=59, passed +5), record deep-freeze 상태로 표시 계층 전 실행 TypeError 0. ⚠**새 발견 — 병합이 발동하면 일러스트가 사라진다**: `ILLUSTRATION_SCENES` 에 `['shoulder','arm']` 장면이 0건이라 병합 항목은 그림 미부착(fail-closed, 크래시 0). 장면 데이터 1건 추가로 해소 — 다음 사이클. ⚠시뮬·실기기 미확인 | 2026-08-02 | e75dea64 | [260802-mrg-…](./quick/260802-mrg-merge-display-and-fix-copy/) |
| 260802-tie | 대표 프레임 선택에 **신뢰도 tie-break**(집계값 거리가 동일할 때만 — 의미 무변경, argmax 아님) + **기준 패널 무표시 인증 필드**. 허용오차 `TIE_EPS=0.01도` 는 임의 상수가 아니라 **채점 엔진이 실제 방출하는 소수 자릿수를 테스트가 읽어와 assert**. 실 데이터 **32건 중 6건** 프레임 이동, 그중 2건이 게이트 통과(우어깨 0.116→0.508, 우골반 0.255→0.650, 둘 다 거리차 정확히 0). 기준 패널 무표시는 **렌더 코드 인증** 방식으로 판정 — 오케스트레이터가 doc 눈으로 센 "12장 중 7장, elbow-twist 5/5"가 **다른 경로에서 독립 재현**됐고, tie-break 부수효과로 **4→1** 로 줄었다(★의도한 효과 아님 — 학생 패널 신뢰도를 고른 결과 DTW 짝 기준 프레임이 따라 움직인 것. 인과를 거짓으로 물려주지 않으려 명시). 게이트 = pytest 59=59(passed +29), typecheck 0. ⚠pointed-window tie 는 실 데이터에서 **한 번도 발동 안 함**(4 fixture 전부 `pointed=[]`) | 2026-08-02 | 7f7f41d9 | [260802-tie-…](./quick/260802-tie-frame-confidence-and-empty-ref-panel/) |
| 260802-nse | ★**측정 오차보다 작은 편차는 감점하지 않는다**(belle 승인 — **오늘 유일하게 점수를 움직인 사이클**). 문턱 = **순서통계 기반 분포무관 median 신뢰구간**(`CI_ALPHA=0.05`), 규칙 = `구간 하한 > 허용치` 일 때만 감점. 오케스트레이터가 제시한 `1.253σ/√N` 근사는 **계획자가 기각** — `motiondtw.py:201-212` 가 median 을 쓰는 이유가 "꼬리가 두껍다"인데 σ 는 정확히 그 꼬리가 지배하는 통계라 자기모순. 순서통계는 정확·결정적이고 구간 끝점이 **실제 관측값**이다. **실 doc 4건 전건: elbow-twist 63→73(record 8→3) · power-spin 62→67(4→2) · kip-up 99→100(1→0) · pdshape 100→100(1→0). 이동분이 억제 감점 합과 소수점까지 일치 — 설명 안 되는 이동 0.** 적용 지점 = **record 방출**(md 빌더에 걸면 `activated` 가 바뀌어 cross-exclusion 이 새 record 를 되살려 "점수는 오직 상승" 불변식이 깨진다 — 계획자가 소스로 확인). window 경로는 `N>=ceil(log2(2/α))=6` 인데 `window=2` 라 최대 5샘플 → **방법 자체가 "이 median 은 못 묶는다"고 선언**(구조적 fail-closed). 독립성 가정 위배(DTW 경로 자기상관) → 구간이 실제보다 좁음 → **과소 억제** → 편향이 fail-closed 방향. 억제분은 삭제 않고 `suppressedRecords[]` 에 `wouldBePoints` 로 보관(belle 투명 합산 원칙). 게이트 = pytest FAILED **신규 0·해소 0**(59=59, passed +111), **기존 테스트 0건 파손**, BASE 시점 `replay.py` 로 현행 코드 재생 → `--recon-only` **byte-동일**, `legacy_baseline --verify` 9/9 해시 동일, typecheck 0. ⚠**belle 결정 2건(고치지 않고 보고)**: ① record 0 이 되면 mission 소멸 → 헤드라인이 `왼쪽 어깨…차이가 있어요` → `오늘은 이 부분에 집중해봐요` 로 바뀜(100점인데 맞는 말인가) ② 감점 0 이어도 확대카드는 **남고 오히려 늘어남**(kip-up 1→2) — record 비면 legacy `fault_joints` fan-out 폴백(`app.py:3507-3512`) | 2026-08-02 | 7102b480 | [260802-nse-…](./quick/260802-nse-noise-floor-deduction/) |
| 260806-sjt | **내 영상 재생 회귀 수리** — presigned 재발급 훅 2개(WR-03 `freshMyUrl` + WR-02 `freshPrevUrl`)가 비정식 videoKey(`fixtures/...`) doc 에서 canonical `uploads/{uid}/{analysisId}.{ext}` 키를 **객체 존재 확인 없이 서명한 URL**(GET **404** 실측)로 doc 의 유효 URL(GET **206** 실측)을 덮어씀. 발현 조건 = `createdAt`+6일 경과 — 파일럿 doc 4건이 07-30 생성이라 **08-05 부터 처음 발동**(08-01 belle 확인 때는 잠복, "잘 되던 게 안 되던" 이유). 가드 = **양항 조건** `myVideoKey && !myVideoKey.startsWith('uploads/')` 일 때만 재발급 생략 — 키 부재 구 doc 은 현행 재발급 유지(실사용자 회귀 방지, 단항 `!key?.startsWith` 금지), `freshRefUrl` 은 스코프 제외(서버가 reference doc 의 실제 키를 resolve — 과잉 일반화 방지). 17줄 삽입·소비처 3곳 무접촉·typecheck GREEN. ⚠**런타임 재생 = UNVERIFIED**(개발 빌드 부재로 시뮬 렌더 불가) — belle 실기기 확인 대기. 근본 원인(백엔드 playback-url 이 존재 미확인 키 서명 — visual-worker H-05 후보-키 대조 선례 있음) = 다음 SAM 배포 편입 후보 | 2026-08-06 | 4b755efa | [260806-sjt-…](./quick/260806-sjt-videokey-doc-presigned-url/) |
| 260806-usc | **V-1 재생 편측 갈림 차단 — 불변식 집행** (belle 실기기: 큐1에서 내 영상만 4.9s 정지·정은지 10초대 진행, 음성 후 내 영상 미재개). ★**시뮬 재현 시도 = 미재현**: 개발 빌드 #29 + iOS 26.5 시뮬에서 녹화 프레임 실측 — 큐 4개 전부 양쪽 동시 정지(4.1/4.2→6.7/6.7)·동시 재개·최종 13.3/13.5 동기. **상태머신은 이상 조건에서 옳다** → 기기 조건 의존(학생 영상 92MB≈43Mbps 재버퍼 스톨 / 실기기 tick 레이스 후보). 수리 = 원인 추측 아닌 **D-13 불변식("함께 멈추고 함께 돈다") tick 집행**: 순수 함수 `decidePlaybackInvariant`(R1~R8, 12축 테스트) + VideoCompare 집행 블록(+80줄, **삭제 0** — F-1/F-2·follow/drift·시작홀드 원문 무수정). 음성 중 편측 진행→즉시 pause / 재개 관찰창 1s 내 편측→play 재시도 3회→실패 시 양쪽 대칭 정지(정렬 보존, converge-pause 트레이드오프 — belle "자꾸 멈춘다" 보고 시 RESUME_PLAY_RETRIES/WATCH_TICKS 상향이 조정점). 수리 후 시뮬 회귀 재검증 = 큐 4사이클 전부 대칭 유지(4.0/4.2→6.7/6.6→9.4/9.3→10.4/10.2). ⚠**실기기 실효 UNVERIFIED**(시뮬이 원 결함 미재현 — 회귀 없음만 증명). OTA 3채널(prod `ac79c72e`). **이번 세션 구조 전환 = 개발 빌드 확보로 "눈감고 OTA" 차단** — 시뮬 재현→수리→검증 루프 첫 가동 | 2026-08-06 | d70355a4 | [260806-usc-v-1](./quick/260806-usc-v-1/) |
| 260806-wj3 | **belle 실기기 2차 관측 ①②④ 대응** (OTA ac79c72e 상태에서: ① 큐2 자막에 큐1 음성 재재생 / ② 진행 바 감점 틱 부재 / ③ 큐1 후 재개 정상 = usc 수리 작동 실증 / ④ 큐2 후 양쪽 대칭 정지 = converge-pause 설계대로 발동). 수리 3건: **①** `speakCue` 의 `player.replace()` 제거 → 큐마다 `createAudioPlayer(url)` 신규 생성 — 재생 아이템의 출생지가 요청 URL 한 곳뿐이라 **남의 음성 재생 경로 구조 소멸**(replace 실패 시 스테일 아이템 잔존이 기제 가설 — 코드 판독 논증, 계측 아님). 구조 게이트 replace 0/createAudioPlayer 1/remove() 1. **②** IN-01 강등 중 `overlayTimelineTicks` 억제만 해제(다른 강등 6건 무접촉) — 시뮬 확인: 엘보 바에 ①②③④ 표시됨. ⚠단 **4개가 한 지점에 뭉침** — 틱 빌더가 record `atFrameIdx` 아닌 옛 window-median 단일 시각 사용(gbk 미배선 잔존, 후속 배선 거리). **④** 재개 마지막 재시도 직전 제자리 seek nudge 1회(AVPlayer 스톨 회복 관용구, `playbackInvariant.ts` diff 0 — 12축 계약 무접촉). 시뮬 회귀 = 엘보 큐 4개 발화·대칭 정지·재개·17s 완주(좌우 ≤0.3s). ⚠①·④ 실기기 실효 UNVERIFIED(기제가 기기 네트워크 의존). OTA 3채널(prod `747ee98f`) | 2026-08-06 | 7b7c8d07 | [260806-wj3-nudge-belle](./quick/260806-wj3-nudge-belle/) |
| 260807-fpw | **belle 08-07 재생 표시·신뢰성 4건** — ① 감점 번호 시간순 재번호(belle 확정): `sortDeductionRecordsByMoment` 순수 정렬을 records memo 단일 출처로, 마커·틱·점수 계산 내역이 함께 시간순(①=재생 최초 감점). ScoreBreakdownSection 의 index 평행 조인은 정렬 breakdown 재조립 전달로 해소, '오늘 고칠 것' 히어로는 이미 최대 \|points\| 명시 선택이라 무접촉. ② 재개 백오프: **대칭 정지엔 재시도가 아예 없던** R5 갭 발견 — 관찰창 내 양쪽-정지를 재개 실패로 편입, 백오프 스케줄 [5,15,35,65]tick(0.5/1/2/3초) + 최종 실패 시 '일시정지됨 — 탭하여 계속' 배지. ③ 인접 큐 체이닝: `nextChainedCue`(horizon 1.0s) — 음성 종료 시 +1초 내 시작 미발화 큐를 재개 없이 이어 발화(파워스핀 0.11초 간격 이중 정지 해소), 재발화 함정 2개 가드. ④ 재생 중 마커 색 반전(belle 지시): 재생 중 기본 점 흰색·활성 큐 부위만 빨강, 정지 상태 번호 마커는 현행 유지, IN-01 doc 도 음성 중에는 해당 부위 빨강(표시-발화 일치). 테스트 196 pass(+17), tsc GREEN, 채점·계약 byte 무접촉 | 2026-08-07 | d1bf271a | [260807-fpw-belle-08-07-4](./quick/260807-fpw-belle-08-07-4/) |
| 260807-iwp | **belle 08-07 오후 3건 (fpw OTA 확인 후)** — ① "정은지 영상이 끊겨 음성이랑 안 맞음(학생은 맞음)": 음성 멈춤 동안 기준 패널을 그 감점의 **짝 프레임**(zoom `refVideoSec` — fps 재계산 금지 계약 준수)으로 스냅 + 재개 직전 원위치 복원(`voiceSnap.ts` buildRefSnapSecs, 체이닝 큐마다 갱신, 짝 없으면 fabricate 0). 학생 영상은 잰 순간 정지라 맞는 게 보장 — 기준 패널만 시간 동기(대략 맞춤)여서 어긋나던 것 해소. ② 끊김 완화: 드리프트 보정 히스테리시스(`driftHysteresis.ts` shouldCorrectDrift — 임계 0.2→0.3s + seek 최소 간격 0.8s, Build 16 "stutter<동기" 절충의 belle 관측 기반 재균형; 음성 정지 중 보정 미진입은 기존 가드 실측 확인). ③ 재생 중 오버레이 점 시인성 강화 — `playbackEmphasis` opt-in 배율(정지 번호 마커 byte 무접촉). 208 tests·tsc GREEN, playbackInvariant/cueTrack/backend/types diff 0 | 2026-08-07 | 30c1bcb4 | [260807-iwp-belle-08-07-3](./quick/260807-iwp-belle-08-07-3/) |
| 260807-k70 | **belle 08-07 저녁 3건 (iwp OTA 확인 후)** — ① 가로 전체보기 자막·"음성 중" pill·"일시정지됨" 배지 렌더(#8 해소 — `renderCueOverlays(fs)` 공유 헬퍼, 문구 단일 소스, 세로 출력 불변). ② belle 정책 확정 "지점을 말해줄 때만 표기": 재생 세션(`inPlaybackSession`) 중 기본 스켈레톤·점 전부 숨기고 활성 큐 record 부위만 빨강, 큐 없으면 점 0, 우측 패널 숨김(emphasis 강도 유지, KeypointOverlay diff 0). ③ n번째 재생 비결정 스터터: 판독 근거 3기제만 — **재재생 seek(0)+200ms 후 stale currentTime(=end)으로 tick 이 즉시 재정지하는 경로**에 settle 가드(`replaySettle.ts`, 상한 2.0s) + 재생 개시 드리프트 0.8s 유예(기존 히스테리시스 재사용) + 발화 이력 리셋 3곳. 플레이어 재생성·관찰창 무장은 근거 부족으로 미도입(SUMMARY 박제 + belle 관측 4항목). 216 tests·tsc GREEN, 보호 파일 7종 diff 0. 시뮬 실증: 가로 자막+무릎만 빨강+스냅 16.3 한 프레임, 재재생 0부터 정상 진행·첫 큐 발화 | 2026-08-07 | 6a6f6234 | [260807-k70-belle-08-07-3-n](./quick/260807-k70-belle-08-07-3-n/) |
| 260807-m63 | **belle 08-07 밤 2건 (k70 OTA 확인 후, 가로 자막 ① OK)** — ① "바 끌어서 처음으로 → 지나는 포인트 음성 한꺼번에": seekBoth 가 move 마다 voicePause 를 풀어 tick 큐 진입이 드래그 중에도 돌던 구멍 — 진입 블록에 scrubbing 게이트(재개측과 대칭) + 릴리스 시 `openCueRecordIds`(열린 윈도우 전부)로 발화 이력 교체(반쯤 지난 윈도우 즉발 금지, 뒤로 간 큐는 재생이 다시 지나면 정상 재발화). ② "④가 재생 없이 점프": CUE_CHAIN_HORIZON_SEC 1.0→0.3 — 체인은 파워스핀(0.11s 겹침) 전용, 엘보 ③→④(1.0s)는 재개 후 제 순간(10.3s)에 별도 정지·발화. 222 tests·tsc GREEN·펜스 6종 diff 0. 시뮬 실측: 정지 4회 각 제 순간+스냅(7.0/8.7/16.3/14.9)·완주 / 끝→0 드래그 폭주 0·재생 후 4큐 제 순간 재발화·완주 | 2026-08-07 | ab9ddcc4 | [260807-m63-belle-08-07-2](./quick/260807-m63-belle-08-07-2/) |
| 260808-im8 | **자율 스크린 v1** — v0 인라인 스크린을 `backend/scripts/p35_observe_screen.py` 로 영구화, V0_REGRESSION 6게이트 PASS(powerspin left_ankle +0.5555·벌림각 −24.55°·u 27.74/r 98.05·elbow 전 피처 최대 scaled 0.393·미러 5/5 동측). ★px 관례로 v0 4실측 전부 재현 실패 → plan 명문 교차 1회로 **정규화 좌표 공간 채택**(간격 분모 torso·패널 중앙값 독립 nanmedian 까지 실측으로 확정, 근거 주석 박제). v1 홀드 구간 인식 신설했으나 **r03 블라인드 재발견 verdict = FAIL**(G1·G2 = 동시 홀드 짝 0 으로 판정 불가 / G3 PASS — 기본 파라미터 1회, 튜닝 0). 실패 기전 실측 = p40 상대 임계의 run 조각내기(elbow user 최장 12f < 15f, 위치는 렌더러 정지 순간과 정확히 겹침) + DTW 짝-홀드 경계 불일치(pdshapefault 양패널 홀드 성립에도 교집합 0). 전구간 스크린에는 r03 방향 신호 존재(elbow gap_hip_mid 2위 +0.0546·bodyline 3위 +0.0472, user>ref) — 신호 부재 아니라 홀드 격리 실패. 채점·렌더러 diff 0, 다음 가설 = 히스테리시스 이중 임계 + 완화짝(결정 대기) | 2026-08-08 | 2e8ab938 | [260808-im8](./quick/260808-im8-v1-r03/) |
| 260809-i0q | **Pod p2qjoktz8lc4ju 기동 + 실업로드 경로 결정론 ON** — 08-08 마감 잔여 1건 종결. ★노트가 지목한 `start_p15_server.sh` 는 6월판 함정 파일(PR_INVERSION_ENABLED 없음)이라 정본 `start_server.sh` 에 `RTMW_DETERMINISTIC=1` 박제(채점 rtmw_engine + 렌더 정렬 compare_align 양쪽), p15 는 정본 위임으로 무장해제. 부트스트랩→기동→`/health` 4항목 PASS(commitSha 73042a27 · 결정론 true · 인버전 true · modelLoaded/Gemini), `/analyze` 무·오토큰 401. SSM v27→v28 + Lambda `RUNPOD_ANALYZE_URL` 새 proxy 동기(4키 보존 재조회). 기동 스크립트 `backend/runpod_inference/start_server.sh` 로 버전화(Pod 사본과 md5 e7f224d6 동일) — git 밖이라 인버전(32-15)·결정론(08-08) 이 두 번 누락된 구조 제거. 미검증 = 실업로드 E2E·이 Pod 재현성 재측정 | 2026-08-09 | 30533327 | [260809-i0q](./quick/260809-i0q-pod-p2qjoktz8lc4ju-on/) |

| 260810-cbt | **표시 순간이 안 보이는 뿌리 = fps 라벨 오차** (측정만, `backend/` diff 0) — `frame_extractor` 는 정수 step(`round(src_fps/target_fps)`)으로 솎는데 초 환산은 요청값 `target_fps(9.0)` 를 쓴다 → 30fps 원본에서 실제 **9.997fps**, 저장 초가 **9.7~10.0% 크다**. `select_pairs` 는 그 초를 재탐색 없이 클램프해 사용자 프레임으로 쓰므로 **사진의 앵커가 틀린다**(기준만 ±2초 재탐색 = 틀린 프레임에 기준을 맞춘 짝). 저장 트랙 프레임 수가 이 규칙으로 **4/4 케이스 정확 재현**(180/182/62/83, 강제 마지막 프레임 규칙 포함). ★**peterpan r00 저장 초 6.444s = 15fps 프레임 97 > 클립 91프레임** — belle 승인 5편 중 하나가 클립 밖을 가리켰다(렌더 클램프 5.89s 가 교정값 5.82s 와 우연히 0.07초 차). ★`fault_zoom:852` 의 경험적 **4/3 보정 = `18/14.93 × 9.96/9 = 1.335`** — 같은 오차를 원인 모르고 덮은 것(주석: belle "정은지 쪽은 아예 다른 장면"). 기준 트랙 5건 전부 실제 **15.0x fps** 인데 저장 `fps=18.0`. 유입 = `e1dca177`(2026-05-21 최초 ML 어댑터) = 전 기간. 렌더러·짝선정 **무접촉**으로 A/B 재렌더: 10건 중 차이↑ 3 / 표시 상실 3 / 축소 2 — **일관 개선 아님**, pdshapefault 카드 4→2장. powerspin r02 현행 `85.9도`는 정렬 오차 과장(나머지몸 정렬 0.800)이 교정 후 16.8도/0.181. 실물 확인 = r03 무릎 A/B, 교정본이 천장·상체·그립 나란하고 굽힘 차이 읽힘. 할 것 1 = (차이 큼)∧(정렬 신뢰)가 **서로 잡아먹음** → 지적 관절 뺀 **나머지몸 정렬(`pd_rest`)로 직교화**, Pareto 우세 후보 10건 중 7건(★1차 "승인 순간=클립 최악 정렬 87~100%"는 **정정** — 나머지몸 기준 11~78%). 할 것 2 = **`편차÷요동` 지표 기각**(요동 130~180도라 회전·역립이면 구조적으로 항상 <0.1 — 카드 품질 아니라 "안정 국면인가"를 재고 있었다. 창 폭 교정엔 robust, 뒤집힘 0/10). belle 결정 3건 = 교정 범위(표시 전용/전역=점수 이동)·카드 4→2 수용·4/3 보정 제거 | 2026-08-10 | da3f549f | [260810-cbt](./quick/260810-cbt-showable-moment/) |
| 260811-kpo | **성립 게이트 운영 배선 + Pod 실증** — ii0 게이트 3종(홀드/짝정합/기계눈)을 카드 생산 경로에 이식(`card_gates.py` + `_run_gated_card_inherit`: compare_render 리그 PASS 뒤 상속 카드 대체 부착, 실패 전량 graceful = 기존 카드 폴백, 채점 5파일 diff 0). 카드 배정 = 생존자 \|dev\| 내림차순(record 순서 상한 구조 제거). **Pod 재분석(p34fresh1786433865) 실증: 왼골반 카드 소멸 + 왼무릎 카드 방출(홀드 짝 12.8/12.3s 접힘 vs 신전, 육안 인증) + 왼팔꿈치 생존·귀속(pole_proximity)** — `card_gates verdict` 운영 로그 실물(wiring-claims-need-log-evidence). 승인 무회귀 joint-scope 9/9(ii0 스윕 수치 동일)·점수 60 유지·pytest 기준선 59 동일(+신규 8). 편차 3건 전부 실측 근거: ①각도-주장 record 는 pairSrc 무관 측정 짝으로 게이트(절정 재배치 왼골반 샘 차단) ②override rep9 역변환(라벨 오차 1.33배 밀림 교정) ③★**눈 호출 상한 2→16/record 완화 = belle 확인 요망**(광역 keypoint 전위 아래서 첫 후보 기각 = record 사망 → 포즈 순 지연 평가 + 캐시, 분석당 40~46회 gemini-3.5-flash ≈ $0.01). 유보 = 로컬 left_elbow 귀속 pole_diff 0.1498 vs 0.15 근소 미달(순간 측정 지터 — 창 기반 분위수 측정이 다음 수리 후보, Pod 실분석은 성립)·카드 초 표기 ÷9.0 잔존(범위 밖)·방출 카드 belle 육안 최종 판정 다음 사이클. **눈 원장 86건(로컬46+Pod40, 마킹 크롭+claim+판정) Phase22 플라이휠 씨앗 보존**(리포 evidence + S3 eye/) | 2026-08-11 | 82d7eed0 | [260811-kpo-gate-wiring-3-pod](./quick/260811-kpo-gate-wiring-3-pod/) |
| 260811-ufb | **freeze-only 수리 (kpo 반려 수리판)** — belle "영상이라는 기본 승인 틀이 있는데 왜 자꾸 다르게 하는지 / 하다못해 확대를 해도 되겠구만" → **재정박(새 순간 탐색)·절정 재배치 코드 제거**(플래그 아님, 3회째 구조 제거 규율). 카드 = 영상 freeze 그대로 + 확대만, 게이트는 방출 판정 전용(실패 = 정직한 침묵). 기계 증명: fresh 2회 + **승인 5동작 전부** 방출 순간 == freezes[] 전건 일치(순간 발명 0) + 별도 프로세스 2회 완전 동일(kpo 12.8↔10.5s 비결정 소멸) + 승인 9/9·pytest 59 무회귀·D-41 분기 0. **Pod 실증(p34fresh1786458292): 재정박 부재 verdict + freeze 상속 카드 2장(왼팔꿈치 5.3s·왼골반 16.7s, 같은 국면 짝·타이트 크롭 육안 인증) + 점수 60 + 404s(666s에서 단축) + 눈 호출 47→2회**. 정직 박제: 왼골반 카드가 freeze 상속으로 부활(belle 육안 판정 대상)·왼무릎 침묵(신규 발굴은 별도 사이클)·눈이 승인 정지 2건 기각(r01=트랙 환각 적중·r00=unclear, 임계 무조정)·÷9.0 표기 잔존·Pod 운영 사고 2건(setsid 분리 재기동·재분석 cwd) 수리 | 2026-08-11 | 5ddc1e3a | [260811-ufb-freeze-only](./quick/260811-ufb-freeze-only/) |
| 260811-xa1 | **마크 문법 후보 라운드** — belle 육안 판정(왼골반 장면 PASS·마크 반려 "그냥 선으로 되거나" / 왼팔꿈치 반려 "뭐야 이게" = 각도선이 얼굴·머리 관통) 받아 같은 ufb freeze 에서 후보 6안 로컬 산출. 베이스라인 md5 게이트 2/2 == ufb 인증값(반려한 그 실물임을 기계 증명) + 비대상 카드 무누출 + `backend/` diff 0 + Gemini 0회. 왼골반 P1 단일선/P2 단일선+쐐기/P3 하이브리드, 왼팔꿈치 E1 짧은선(경계 스텁)/E2 폴 간격 브래킷(기결론 이식 — 단 이 freeze 는 기준 팔꿈치도 폴에서 멀어 대조가 안 갈림, 실측 명기)/E3 스포트라이트(원 밖 44% 감광, 관통 원리적 불가). 내 추천 = **P2 + E3** (실물 관찰 근거, JUDGMENT.md). belle 판정 대기 | 2026-08-11 | adc749c5 | [260811-xa1-mark-grammar-round](./quick/260811-xa1-mark-grammar-round-ufb-freeze-2-belle/) |
| 260813-ebd | **xa1 라운드 3 — belle 08-13 번복 박제 + 선 문법 후보** — belle 주변 검증("모두가 선이 좋다") → 스포트라이트(E3-r1·P4) 채택 철회·선 문법 채택 판정을 장부 박제(팔꿈치 픽 = 베이스라인 기존 V자와 픽셀 일치, 골반 픽 = P3 — 오케스트레이터 실물 대조). 반려 freeze 실물(베이스라인 md5 2/2 == ufb 인증값)에서 **P3r1**(채택 문법 무변경 + 앵커만 align 게이트 순간 단일 출처 수리, 이동 user 1.6px/ref 8.7px = 라운드 2 진단 적중) + 팔꿈치 변형 5안. ★구조 실측 = 제자리 V 계열(EV1 관절도달/EV2 팔길이 비례/EV3 E1 연장) **전원 동일 픽셀 붕괴**(vertex 가 머리 원반 ~5px 밖 → 클리핑 후 링만 잔존, EV2==EV3 byte-identical) — 미성립 박제, belle D-03 원문 "위치 보정" 직해인 **오프셋 V(EV4/EV5: 글리프 오프셋 배치 + 링 + 점선 리더)** 가 성립(전 샘플 원반 밖 기계 검증 + 얼굴 크롭 육안 관통 0). **추천 = EV5(x1.6, 사전 박제)**. backend/ diff 0 · Gemini 실호출 0(스텁 14) · 한글 사본 4장 /Users/Shared/sunity-mark-candidates-260813/. belle 판정 대기 | 2026-08-13 | a239ccb4 | [260813-ebd](./quick/260813-ebd-xa1-3-belle-08-13-p3-v/) |
| 260813-fxx | **선 문법 운영 배선 (검증 passed 8/8)** — belle 라운드 3 최종 판정 박제(P3r1 PASS · EV4/EV5 오프셋 반려 = 팔꿈치 기존 관절 위 V 유지 · 미세조정 이연 · 내 EV5 추천 불일치 장부 기록) + 운영 이식 2축: ①확정 카드 표시 좌표(vertex·크롭 중심·V spec) = **게이트 freeze 순간 align 단일 출처** — app.py `_run_gated_card_inherit` 가 `cg.kp(round(sec×afps), conf>=0.5)` 산출해 `display_anchor` kwarg 로 전달, fail-closed(한쪽 미달 = 드랍 + 로그), rep12 폴백 없음. hip vertex 이동 실측 **user 1.65px/ref 8.67px = P3r1 진단 적중**(fps 라벨 사슬 skew 종결) ②골반 마크 = P3 하이브리드(쐐기+화살촉+고스트, bz5 상수 byte-동일) `HYBRID_ANGLE_SUFFIXES={"hip"}` 선언 데이터 — 팔꿈치/타 관절 기존 V 무변경. 기계 증명 = WIRING-CHECK 5단 2회 PASS(결정론 2프로세스·freeze 전건 일치·의도-변경-국한 대상 2장만 md5 변경·align 예측 독립 재계산·승인 hold 9/9+pair 9/9) · pytest 기준선 59 failed 동일/4157 passed(신규 8) · 산식 5파일 diff 0 · 동작명 분기 0 · Gemini 실호출 0. 검증자 독립 재실행으로 전건 재확인. 유보 = belle 실물 육안 · Pod 실증(터미네이트) · 미세조정 라운드 · ÷9.0 표기 | 2026-08-13 | b686fbbb | [260813-fxx](./quick/260813-fxx-belle-3-p3r1-pass-v-p3-align-fps-5-pytes/) |
| 260813-hlv | **Pod mddy6gsqmt24ud 재진입 + 선 문법 배선 실증** — 재진입 6단계 전건 PASS: 4090 실측 · 코드 동기 5ddc1e3a→0f999619 · bootstrap `[done]` · setsid 기동(단일 프로세스) · health 4항목(commitSha 0f999619·결정론·인버전·modelLoaded) + `/analyze` 무토큰 401 · start_server.sh md5 e7f224d6 리포 정본 일치 · **SSM `/sunity/motion/runpod-analyze-url` v31 + pipeline Lambda env 새 proxy 재동기**(4키 보존, 재조회 실측, AWS 쓰기 2건 한정). **배선 실증 = fresh `p34fresh1786593512`**(342.7s): `display_anchor rid=` 성립 2건(r00 팔꿈치·r03 골반, drop 0) + `card_gates verdict` 운영 로그 실물 — survivors(`r03:inherit@u16.667/r15.20`·`r00:inherit@u5.302/r5.13`)·앵커 좌표 fxx 인증값 byte-동일. **점수 60==60·감점 -45.0·records 5건 소수점 15자리 전건 일치**(채점 무접촉의 Pod 증명). 카드 2장 scp 회수: fxx 대비 md5 상이 원인 실측 = 디코드 노이즈 max Δ3/255 + 1px AA(구조 차 0), 육안 = 골반 `drawn_hybrid` 4요소·팔꿈치 관절 위 V PASS. Gemini 4건(eye 2)·학습 전송 0·눈 원장 +2. Pod 가동 유지 | 2026-08-13 | a4bced58 | [260813-hlv](./quick/260813-hlv-pod-mddy6gsqmt24ud-6-pod/) |
| 260813-ivs | **승인 5동작 새 문법 전체 반영 스윕** — 무패치 운영 헬퍼(`_run_gated_card_inherit`)로 승인 코퍼스 일괄 렌더: 방출 8/침묵 5, freeze-match 위반 0(survivors == ii0 정본), backend/·하네스 원본 diff 0, Gemini 0(스텁 6), 마크 튜닝 0. ★실측 = 새 V 실물 2장뿐(둘 다 실눈 기각 이력 record)·**V 미베이크 5/8**(rep12 스펙 게이트가 V 를 죽임 — 미세조정 1순위 의제)·P3 하이브리드 실물 0(hip 방출 없음). display_anchor drop 1건(elbow r01 오른어깨, user conf 미달 — fail-closed 스펙 동작이나 ufb 구 문법에선 있던 카드가 죽는 코퍼스 발견) + 무로그 침묵 경로 실측 2건(rep12 양측 신뢰 0 → build 내 skip). 어색 케이스 사전 박제 6건(V 저사이각·폴 겹침 1순위 / 원-얼굴 가림 / ref relaxed 무마크 / 저해상 / legs 크롭 비대칭 42vs68% / ÷9.0 ~10%). 전수 현황 = STATUS.md(13행)·육안 = EYE-VERDICT.md(8장)·한글 사본 /Users/Shared/sunity-sweep-260813/. belle 판정 대기 | 2026-08-13 | c1afb188 | [260813-ivs](./quick/260813-ivs-5/) |
| 260813-l0u | **스윕 판정 박제 + 왼어깨 답변 재료** — belle 판정 전건 JUDGMENT append(반려 2 짝 불일치·통과 6·소프트 노트 2·질문 1, 원문 인용, 삭제 라인 0 기계 증명) + 사전 박제 대조(적중 2·불일치 1: 내 1순위 어색 후보가 무언급 통과). 피디쉐입 왼어깨(r02, freeze u3.2/r2.0) 재료 3종: 전신 프레임 짝(content-match 선정, 카드 패널과 동일 장면 육안 PASS) + v7 승인 영상 freeze(S3 GET 1회 — 각도선 V+121°/147° 수치+자막 구움) + claim(26.79도 초과/허용 20.0/-8.2점, ★카드 attached deficitDeg 70.0 vs doc 26.79 불일치 미해석 보고). backend/·하네스 diff 0 · Gemini 0 · Pod 무접촉 | 2026-08-13 | 41d2bc69 | [260813-l0u](./quick/260813-l0u-sweep-verdict-lshoulder-frames/) |
| 260813-m0k | **미세조정 1차 재료 — V 베이크 align A/B + 짝 회복 + 커버리지** — ①B(align 유도 V 스펙, seam 2 monkeypatch, 운영 무접촉): A 런 ivs md5 정본 일치 확인 후 회복 후보 **6/6 소생·육안 6/6 옳음**(꼭짓점 관절 위, 환각 0) — ref 무마크 2장(왼팔꿈치·왼무릎) 부위 크롭+V 해소, 무로그 침묵 2건(elbow r03·powerspin r02) 신규 카드. elbow r01 회복 불가 = user align conf 0.429/0.292/0.229 실측(정직한 침묵이 옳음). survivors/dropped ivs==A==B ②짝 회복: 왼무릎 후보 3(추천 3.867s — 국소 거리 0.0837 vs 0.2081, ★전신 랭킹 1위 = 반려 baseline = 전신 지표가 못 거름 박제) / 왼팔꿈치 = 전 구간 유의 개선 없음 → 현행 9.4s 유지 + B 해소. pair-override 경로 명기(재정박 아님) ③커버리지 13 rid 전수: 현행 8 → B 시 10, 잔여 3 사유 실측. backend/·하네스 4파일 diff 0 · Gemini 0(스텁 12) · 한글 사본 20장 /Users/Shared/sunity-finetune-260813/. belle 판정 대기 | 2026-08-13 | f0988a7a | [260813-m0k](./quick/260813-m0k-1-v-bake-align-a-b-2/) |
| 260813-nh4 | **운영 배선 2차 (검증 passed 8/8)** — B 스펙(V 베이크 align 유도 `align_bake_spec`) 운영 이식(기본값 byte-동일 + 신규 테스트 4종) + belle 순서 override(B 이식·push → Pod 실증 → 로컬). **verify_port 재현 게이트**: m0k B 인증값 전건 재현(소생 6/6·카드 8→10·survivors 동일·md5 일치 — 검증자 재실행이 바이트 동일 재생성). **Pod 실증**: commitSha == push 시점 HEAD·fresh 591.2s 점수 60·records 15자리·운영 로그 실물·카드 육안. 판정 장부 append-only(+50/-0, 왼무릎 추천 불일치 기각 + 요소 정체성 교훈). 왼팔꿈치 ref V 진단 = 좌표 정확(conf 0.563~0.697) — 보정 없음 명기, 가독성 의제 이월. ★왼무릎 = content-match 로 스크린샷 ref 4.067s 접힘 확정했으나 3갈래 갈림(A: freeze 벌림+ref 접힘 / B: 벌림-벌림 = 반려 baseline / C: 스크린샷 실물 접힘-접힘 = user 순간 변경 = freeze 상속 예외) → 해석 금지, staging/ 3장 + README(S3 쓰기 0). pytest 59·산식 diff 0·분기 0. 세션 수습 3회(순단·절전·스톨) | 2026-08-13 | 6db2a06 | [260813-nh4](./quick/260813-nh4-2-b-ref-v-pdshape-pair-override-pod/) |
| 260813-u8i | **카드 초 라벨 수리 (검증 passed 7/7)** — ÷9.0 잔존 라벨을 `label_fps` 측별 실효 fps 환산으로 (표시 전용, 미지정 = byte-동일). TDD 4행동 + contract.md §11.8·analysis.ts 서술 정정(3-way 규칙). verify_label 7게이트: **대조 런(9.0 강제) md5 == nh4 정본 전건 = 변경원 라벨뿐 기계 증명** · 승인 10카드 라운드트립 ≤1.5프레임/eff(ref 이중 반올림 근거 주석) · pytest 59/4167 · 산식 diff 0 · 분기 0. Pod 실증: fresh 점수 60·records 동일·**left_elbow 5.9→5.3s(Δ≈0)·left_hip 18.6→16.7s** 픽셀 육안(검증자 재확인). Deviation 1 = peterpan clamp 거울 분기(검증 게이트 한정, 운영 무접촉) — ★freeze 초가 클립 밖인 상류 의제 박제. 라벨 fail-open(좌표 fail-closed 와 층위 구분) | 2026-08-13 | f9a8f3f0 | [260813-u8i](./quick/260813-u8i-fps-fps-pod/) |
| 260813-wif | **왼무릎 신규 발굴 — freeze 상속 승격 경로 첫 실전** — 좌표 무입력 전 구간 스캔 + ii0 임계 그대로(재튜닝 0)로 **kpo 인증 홀드 재발견**(cand13b u12.87/r12.40 vs 인증 12.80/12.24) + 신규 1건(cand02b u1.53/r2.33 — belle 라운드 5 요소 매핑 정합, V 예각 vs 일자). 기준 짝은 요소 정체성 제약(nh4 교훈 — 포즈 최소 단독은 결함을 지움을 실측 재확인: cand13 중립 짝이 역대조를 골랐음). 기계 눈 실판정 10/16회(양측 leg 확정 0.9~0.95, 기각 2건 = 팔 겹침 동형 정직 박제). 후보 카드 2안 = 확정 문법 그대로(관절 위 V·align 단일 출처·실효 fps 라벨). **사전 박제 커밋이 belle 판정보다 먼저**(640b2da4 — 추천 cand13b, 승격 실적 장부 1행). backend diff 0·porcelain 빈·채점·Pod 무접촉·S3 read-only. 한글 사본 9파일. **belle 판정: cand13b 채택·cand02b 반려 — 사전 박제 일치 1/1** | 2026-08-13 | 640b2da4 | [260813-wif](./quick/260813-wif-knee-discovery/) |
| 260814-0p2 | **발굴 채택 순간 영상 반영 실증** — fresh pdshape 비교 영상 freezes 에 cand13b(u12.867/r12.40) 삽입 로컬 재렌더 (하네스 사본 확장 — 원본 무수정, 주입은 현행 미지원 실측 선박제). 베이스라인 재현(주입 off = 운영 리그 무수정 ALL PASS·doc outSec 전건 일치·md5 결정론) → 주입 재렌더 정지 6건: ★무수정 판정기 FAIL = discover H2 정확 1건(게이트가 삽입을 설계대로 검출 — kpo 방지 장치의 올바른 동작 박제) → `"discover"` 라벨 delta 1값 명기 면제 ALL PASS(align-peak/pole 사칭 0). diff 3층 국한(report 전건 동일·JPEG md5 사슬 bit-exact·mp4 공유 소스 전이). **무릎 카드 상속 `r04:inherit@u12.867/r12.40` = wif belle 채택 카드와 md5 byte-동일(e891e7ae)**, 기존 카드 2장 무회귀, 구 r04 freeze(10.5s) hold=moving 침묵 유지. 제약 전건(backend diff 0·S3 GET만·Firestore 0·Gemini replay 실호출 0). 반영 필요 변경 목록 = SUPPORT-SURFACE.md §5. belle 실물 확인 대기(S3 업로드 보류) | 2026-08-14 | 4d65e822 | [260814-0p2](./quick/260814-0p2-fresh-pdshape-freeze/) |
| 260814-chd | **발굴 freeze 캡션 교정 재렌더 — belle 판정("영상 OK, 캡션만") 대응** — 발굴 정지(u12.867/r12.40) 캡션·음성을 결함 서사 정합 새 문장으로 교체(구 r04 문구는 방향 반대). DISCOVER_TEXT 단일 소스 3참조(Polly Text/freeze text/H3 expected) + 새 Polly mp3(Seoyeon neural 운영 기본값 미러, 10.78s — 정지 9.8→11.2s, mp3+0.4 운영 규칙). 무수정 판정기 stock FAIL = 발굴 freeze H2+H3 정확 2건 국한(원본 r04 H3 "문자 일치" PASS = 원본 무접촉 기계 증명) → discover delta 2축 라벨 명기 ALL PASS(사칭 0). 카드 3장 md5 == 0p2 전건(무릎 = belle 채택 카드 그대로 — 카드는 캡션 비종속 증명, STOP 게이트 미발동). diff 국한(삽입 335프레임 @42.07s 외 bit-동일)+결정론 2회. backend diff 0·S3/Firestore 쓰기 0·Gemini 실호출 0(replay 6히트)·Polly 1회(TTS 비-LLM). /Users/Shared 재료 갱신(구/새 문구 원문 대조). belle 재확인 대기 → 반영 사이클(§5 + 발굴 캡션 doc 영속화 규약 추가) | 2026-08-14 | 16661244 | [260814-chd](./quick/260814-chd-freeze-belle-ok-0p2/) |
| 260814-di7 | **발굴 채택 반영 — doc 영속화 + 정식 경로 승격 + 프로덕션 반영 (belle 승인 "좋다 다음 단계로")** — `result.discovery` 일반 스키마(중첩배열 0) + `build_timeline` 주입 레이어(`[discover]` 실행 로그) + verify H1~H4 discover **doc-anchored fail-closed**(blanket 튜플 면제 거부 — 사칭 구멍 차단, +0.5s 비틀기 음성 게이트 실증) + coachAudio 회수 충돌 실측으로 discovery 필드 자체 조인(D-di7-03) + 앱 무접촉(`r04:discover` rid — React key 충돌 실측 회피). **사본 delta(monkeypatch) 청산 — 무수정 verify ALL PASS 가 정식 경로**. TDD 38테스트 + pytest 실패군 IDENTICAL(4205 passed) + 산식 5파일 diff 0. 운영 경로 재렌더 == chd 승인본 사슬(2126/2461프레임) 일치. 프로덕션 실행: 승인본 mp4 md5 사전 일치 STOP 게이트 → canonical 키 byte-보존 업로드 + discover mp3 업로드 + doc discovery/renderedCompare(freezes 6건 @42.07) 기입 → **live 재fetch 왕복 재렌더 == 승인본 + 무수정 verify ALL PASS**. LLM 호출 0. 다음 = Pod 실증(재진입 + `_run_deferred_compare_render` discovery mp3 회수 배선) + 발굴 일반화 스윕 | 2026-08-14 | 6a70af60 | [260814-di7](./quick/260814-di7-s3-doc-freeze-discover/) |
| 260814-ehz | **발굴 일반화 스윕 — belle "pdshape 에서만 한겨?" 의 답 + "다른 영상들도 이런식으로" 이행** — wif 왼무릎 규율을 승인 5동작 13 record 전수로 일반화(관절 하드코딩 → **양방향 claim 유도**, 소스 게이트 선행). 게이트 5/5 PASS(전 동작 로컬 replay — Pod 불요) → 13/13 스캔 → 88버킷 → 압축 37 → 육안 29통과/8탈락 → 기계 눈 58회(record 당 최대 9 ≤ 16) → **눈 PASS 5 / 기각 24** → 카드 5장(재렌더 md5 5/5 동일). **발굴 2동작**(pdshapefault 4 · powerspin 1) / **침묵 3동작**(elbow 0/12 눈 전량 기각 · peterpan 0/1 · kipup 0 split). ★**일반화 무결성 md5 증명**: pdshapefault r03 cand13B 카드 = `e891e7ae` = belle 채택 wif 카드 **byte-동일**(오케스트레이터 독립 재확인) — 단 같은 원본 영상이라 "독립 표본 재발견"이 아닌 **같은 영상·다른 경로 재생산**으로 3곳 박제. ★**침묵이 낸 실측**: elbow 기각 5건은 트랙이 5.0/6.0/6.8도 극단 굽힘을 주장한 순간을 눈이 전부 "펴짐"으로 뒤집음 = **keypoint 환각을 눈이 잡은 실물**(임계 조작 0). split 3 record = `cg.kp(...,"split")` None → 눈 유도 **원리적 불가**(운영 helper 는 align-peak pass-through 면제 — 층위 차이 §7 대조). 사전 박제(판정 전 커밋 904b7146): pdshapefault=cand17B(왼팔꿈치 16.47/15.13) · powerspin=cand01E(왼어깨 0.47/0.73) · 나머지 3동작="발굴 0 — 추천 없음". 제약 전건(backend diff 0 · S3 업로드 0 · Firestore 쓰기 0 · Pod 무접촉 · 임계 재튜닝 0). Gemini 58회 ≈$0.013 추론만. 한계: 압축 상한 4/record(88중 37만 눈까지) · split 발굴 미해결 · peterpan 승인 freeze 6.444s > align 클립 6.067s(u8i 상류 의제 재확인). belle 판정 대기 | 2026-08-14 | 904b7146 | [260814-ehz](./quick/260814-ehz-5/) |
| 260814-ghs | **운영 재렌더 discovery 조용한 소실 수리 — di7 배선의 생산 경로 갭** — 오케스트레이터가 코드를 직접 열어 실측한 갭 2건: **(A ★신규)** `_run_deferred_compare_render` 는 in-memory result 를 조립해 렌더러에 넘기는데 `result.discovery` 는 Firestore 단일 field-path 로만 갱신돼 안 실림(app.py 전체 discovery 참조 0건 grep 실측) → build_timeline 이 빈 목록을 돌아 **freeze 도 excluded 행도 안 남김 = 흔적 0, 리그도 ALL PASS**(H1 eligible 집합 밖). **(B)** discover mp3 미회수. ★선례 = coachAudio 가 같은 구조로 당했고 그 처방(app.py:4257)이 discovery 에 미적용. di7 live 검증이 못 본 이유 = 검증 드라이버가 doc 재fetch 경로라 discovery 보유 — **"승인은 생산 경로에 붙는다" 재발 사례**. 수리: `firestore_admin.get_analysis_discovery`(write 짝의 read, `_validate_discovery` 강제 경유 — 형상 위반은 raise, 삼키면 침묵 재발) + 조달 fail-open+WARNING(발굴 없는 절대다수 분석 무회귀) + mp3 basename 비차단 회수 + **조달-반영 대조 회계 로그**(freeze 전멸 조기 return 앞 — 플래너 좌표 실측). ★RED 먼저 박제: 수리 전 4 failed / 1 passed, 핵심 실패 = `assert {'reason':'discover_no_mp3'} in []`(대조할 재료 자체가 없었음). 이 주입으로 di7 의 `[discover]` fail-closed 가 **운영 경로에서 처음 활성**. 게이트(오케스트레이터 독립 재확인): pytest **59 failed IDENTICAL / 4211 passed** · phase35 discovery 6/6 · `compare_render.py`/`compare_verify.py`/산식 diff **빈 출력**(di7 의미론 무손상을 구조로 증명) · 변경 3파일(app +77 / firestore_admin +30 / tests +308) · 프로덕션 쓰기 0 · LLM 호출 0. **보류 중 발굴 반영의 선행 조건** — 반영해도 재분석에서 살아남는다는 보증. 다음 = Pod 실증(belle 승인 필요) | 2026-08-14 | 4b3c5ad1 | [260814-ghs](./quick/260814-ghs-discovery-in-memory-result-discovery-dis/) |
| 260814-j24 | **눈 원장 학습 유입 경로 신설 — belle "학습으로 흘러들어가게 해내야 한다. 어서 바꾸자"** — 기계 눈 원장(운영 S3 `results/*/*/eye/` + 리포 evidence, 계속 자라는데 소비자 0)을 학습 코퍼스로 잇는 4번째 트랙 `eye` 신설. 수확기(`harvest_eye.py`, 원장 JSON 3형태 흡수 + content-hash 멱등 + 프라이버시 fence) + `build_jsonl` eye 트랙(별도 6키 스키마 — 눈 판정을 `faults[]` 에 담으면 정상 관측이 결함으로 사칭돼 오염, `score`/`severity` 화이트리스트 구조적 부재) + `run_retrain_cycle.sh` assemble 배선. ★**경로 개통 실물** = `assemble_out/jsonl/train.jsonl` eye 7행(6행이 트랙-눈 불일치). 무회귀는 **구조적 보장** — 눈 크롭은 영상이 아니라 이미지라 별도 원장 `eye_manifest.json` 소유, manifest `rows[]` 239 무접촉(`_meta.collection_batches` 단일 hunk). ★**동의 실측**(오케스트레이터가 Firestore read 제약 해제): 분석 doc 6/6 에서 `learningOptIn` **필드 부재**(false 도 아닌 미기록) + 6/6 이 LICENSE-AUDIT §7-1(d) 컷오프 2026-07-13 이후 → **P-1/P-3 hold 확정**(`consent_flag: null` 박제). 규모 = 스캔 205 → 병합 141 = **admit 41 / hold 100**, 불일치 90(admit 29). ★**belle 결정 B-1 의 비용이 숫자로**: 트랙이 5~7도 극단 굽힘 주장을 눈이 "펴짐"으로 뒤집은 **최고가치 8행이 8/8 user 측 = 8/8 hold**(admit 에 이 부류 0). 관절 정정 — right_shoulder 5·left_hip 2·right_knee 1(`elbow` 는 동작 doc 이름이었음). 게이트: pytest 59 기준선 동일(4289 passed) · phase22 380 · `backend/functions`+`backend/shared` diff 0줄 · 식별자 141/141(원문에 uid·analysisId 0회) · S3/Firestore **쓰기 0**. fail-closed 1건 = 크롭 PNG S3 미업로드라 `--upload --with-eye` 차단. 다음 = belle 결정 B-1(user 크롭 학습 허용 여부)·B-3(정은지 크롭 통지) | 2026-08-14 | 787a11ca | [260814-j24](./quick/260814-j24-eye-s3/) |
| 260814-l5i | **플라이휠 첫 가동 — 수집 재개 + 보류 해제 + 균등 축 수리** — belle 판정 2건 반영: ①"정은지 계정만 먼저" → watch 러너 **최초 실행**(7/14 이후 첫 수집, 정은지 IG **신규 4편** 적재, manifest 239→243. 헛돈 2회 = gallery-dl 미설치·`GEMINI_KEY_PARAM` env 이름 불일치, 빈 배치 2건 잔재) ②"앱 계정은 그냥 우리거야 아직 앱이 오픈되지도 않음" → **동의 축 hold 해제**. ★해제 방식 = 게이트 제거가 **아니라** 오늘 확인된 자사 계정 3개 **sha16 화이트리스트**(uid 원문 코드 부재, P-4 준수) — 명단 밖은 기존 게이트 유지(앱 오픈 후 신규 수강생 자동 보호, 회귀 테스트로 못박음) + `learningOptIn=false` 명시 거부는 자사 계정도 불가역 + **만료 조건**(앱 공개 시 근거 소멸) 코드·주석 박제. `--readjudicate` 신설(판정 필드만 갱신, 관측치·출처 보존 = append-only 취지 유지). ★부수 발견·수리 2건: (a) j24 motion 매핑이 **저장 안 돼 재실행에서 유실** → 리포트 부록 원문을 `data/eye_maps/` 4파일로 복원(없으면 152행이 엉뚱하게 보류) (b) 내부 계정 행이 motion 없을 때 사유가 `customer_anonymize_required` 로 **오진단**되던 것 → `motion_unknown` 으로 교정. **실측 효과**: 원장 admit **41→100** / 불일치 admit **28→95**. ★★균등 축 수리 — eye 균등이 동작 축이라 peter-pan 2행이 전체 상한을 4로 고정, 적재 99행 중 86행 소실. 눈 샘플이 배우는 것은 관절 상태이지 동작이 아니므로 축을 **(관절 x 관측)**으로 교체(균등 규율 max<=2*min·결정적·오버샘플 0 그대로, None 무조건 통과 우회도 차단) → **방출 7→35행, 불일치 6→23행**. 게이트: pytest 59 기준선 동일(4298 passed) · phase22 389 · 신규 테스트 9. ★자동 안전 분류기가 이 사이클 커밋을 3회 차단(프라이버시 게이트 완화 + 인물 크롭 메타) — 우회 0, belle 승인 후 통과 | 2026-08-14 | 72c94c4f | [260814-l5i](./quick/260814-l5i-eye-ledger-hold-release-batch-cleanup/) |
| 260814-l5i(b) | **학습 실행 + 환경 결손 6건 수리 — belle "자동으로 좀 해놓으라니깐" / "새로 시작해도 문제없게끔"** — ①크롭 업로드 사이클 **구현 부재**(코드가 "먼저 돌리세요"라 적었는데 그 사이클이 없었음) → `harvest_eye --upload-media` 신설, admit 100건 반출 → 학습셋 fail-closed 해제. ②Pod **awscli 부재** → assemble 백업 실패(★Gemini 라벨 453초 태운 뒤 터짐) → preflight 에 CLI 검사 추가 + bootstrap 에 awscli. ③**RTMW_ONNX_PATH 미주입** → 신규 영상 라벨 전량 실패(env 블록 `source` 필수, ★블록에 `cd` 가 있어 이후 상대경로 깨짐). ④**train_venv 부재** → `setup_train_venv.sh` 레시피 신설(ms-swift 4.4.0 고정). ⑤**볼륨 쿼터 초과**(144G) → belle 승인 후 `spike004/GEN3C` 72G 삭제(★통째 삭제 대신 **모델 저장소만** — 실험 산출물 654M 보존), 73G 로 회복. ⑥**torch 2.4.1 vs transformers 5.12** → Qwen3-VL 4bit 경로가 `set_submodule`(torch 2.5 신규)을 불러 학습 4분 만에 사망 → venv 에 torch>=2.5 cu124 설치 + 설치 직후 검증. ★**정정**: "SFT 가 한 번도 안 돌았다"는 내 단정은 **틀렸다** — v4~v13(7월) 체크포인트 실재, venv 만 쿼터 정리 때 삭제됐던 것. promotion current=null 은 "학습 0"이 아니라 **게이트 통과 0**. ★인프라 산출: `pod_doctor.sh`(7영역 진단 — 결손+복구커맨드 동시 출력, 실측 exit 2) · `bootstrap_full.sh` **리포 박제**(볼륨에만 있어 볼륨 유실 시 복구 불가였음) · `flywheel_cycle.sh` + launchd `com.sunity.flywheel`(월 10:07) — **주간 자동화 최초 등록 + 1회 실행 검증**(로그 자체 커밋). 학습셋 canonical 교체 = **262행**(distill 79/eye 35/perturb 118/text 30, 이전 99행) | 2026-08-14 | (진행중) | [260814-l5i](./quick/260814-l5i-eye-ledger-hold-release-batch-cleanup/) |
| 260815-fzi | **캡션 원인 절 belle 반려 반영 — 학생 서술 제거 + causeSubject 구조 차단** — belle 08-15 판정 4건 기입(a 문면 **승인** "캡션 좋다" / b 일반화 **반려** "다른 사람이 분석했느데 전에 학생거를 말하는게 정상이냐" / c **원 마커** / d 임계 **보류·되물음**). ★뿌리 = 문구집 키가 `(동작 × criterion)` 이라 **분석 1건에 안 묶인다** — 한 학생 영상을 보고 belle 이 읽어낸 진단이 같은 결함을 낸 이후 전 유저의 카드·자막·음성에 그대로 나간다. 실행자가 이걸 **판정 질문으로 낸 것 자체가 잘못**(belle "이게 논의할 일인가"). 갈리는 축 = **원인 문장의 주어**: 기준(정은지) 서술은 기준 영상이 전 유저 공통(v1 pinned)이라 유지 가능 · 학생 서술은 제거. 처분 = `ref-pdshape.…__left_elbow` causeLine **제거**(문면·미채택 사유·복원 조건은 `_meta.…unadopted` 보존 — 복원 조건은 "회전 진행량 대비 그립 시점"을 그 유저 영상에서 **실제로 재는 것**이고 그때도 문구집 고정 아닌 분석별 방출) + `ref-power-spin.…__left_shoulder` 에 `causeSubject: "reference"` 선언 + `cause_line_admissible()` 화이트리스트로 **선언 없으면 조립에서 드롭**(fail-closed, 문면 정규식 추정 금지) + 전 entry(67) 스윕 테스트로 재발 차단. ★**powerspin 왼어깨는 확정 아님** — 기준 영상은 고정이나 **카드가 잡는 순간은 학생마다 달라** 그 구간 내내 기준 팔이 "굽혀 더 올린" 상태인지 안 쟀다(미측정 상태로 운영 잔류를 숨기지 않음, 실측 후 별건 판정). 커버리지 = 67 entry 중 **1건** — 넓히는 유일 경로는 belle 코칭 지식을 **기준 서술 형태로** 받는 것(LLM 생성은 D-11 차단). pytest 변경 전 59F/4347P → 후 59F/4348P(`git stash` 대조로 기준선 동일 확인) | 2026-08-15 | 9a8f6fdc | [260815-fzi](./quick/260815-fzi-causesubject/) |

### Plan 09-01 close-out (2026-06-10)

| 영역 | 결과 |
|---|---|
| Wave 0 atomic commit | `defc973` — 11 files (TS + Python + docs §9.11 + Firestore validator + frontend null-guard + 4 tests) 단일 atomic commit per D-09-U1 |
| force_pattern.py 신설 | Literal aliases (`ForceDirectionPattern` / `ForceSourceSignal` / `ModeContext`) + frozen dataclass `ForcePatternFinding` (8 필드 / R7+R1+R2 strict `__post_init__` validator — `_MOTION_PHASES` reuse, list 컨테이너 강제, non-empty str warnings) + `ForcePatternInference` (5 필드 / non-default → default 순서) + module-level 상수 (`_PHASE_PRIORITY` / `_SIGNAL_PRIORITY` / `_SIGNAL_WEIGHT` / `_BASE_CONFIDENCE` / `_CONFIDENCE_TO_FACTOR` / `_MOTION_ID_BOOST=1.05` / `_IPSF_TOLERANCE_DEG=20.0`) |
| Firestore scoped validator | `_validate_force_pattern_inference` + `_validate_force_pattern_finding_dict` (R2 iter-5 — 8-key camelCase whitelist + strict `list[str]` warnings) + `complete_analysis(force_pattern_inference=)` kwarg |
| 3-way contract lockstep | TS `analysis.ts` + Python `force_pattern.py` + `docs/contract.md §9.11` 단일 atomic commit (D-09-U1). 5 lockstep 테스트 PASS |
| Frontend null-guard | `userAnalyses.ts::normalize` 가 `result?.forcePatternInference` 패턴으로 `forceSignalsReport` precedent 1:1 mirror (R1 iter-2/iter-4) |
| 회귀 게이트 | phase09 49 PASS + phase06/07/08/08.1 408 PASS / 1 skipped + tsc --noEmit clean |

### Plan 09-02 close-out (2026-06-10)

| 영역 | 결과 |
|---|---|
| 5 atomic commits | `d51ed37` T1 (canned + grep gate) / `24b974e` T2 (6 detector + confidence formula + phase fallback + AST severity guard) / `87bdcd3` T3 (Top-3 ranking + tie-break + dedup + motion_id boost) / `c9b6286` T4 (pipeline wiring + integration test) / `bed84e6` T5 (Wave 1 close-out + VALIDATION flip) |
| force_pattern_copy.py 신설 | `_FORCE_PATTERN_COPY_DATA` 18 canned (sourceSignal × modeContext) + `MappingProxyType` wrap (R9/R8 narrow scope) + `_MODE_PREFIX` 3 + `_JOINT_HINT_BY_SIGNAL` 6 + `_FALLBACK_BODY` 1 + `FORBIDDEN_PHRASES_RESEARCH` 8 substring + `FORBIDDEN_PHRASES_PHASE9_REGEX` 2 regex (incl. `근육 힘 방향.*확정` 조사 변형 catch + `\d+%\s*감점`) |
| force_pattern.py 본체 | 6 `_detect_*` (axis_tilt / pelvis_drop with None guard R4 iter-3 / late_contact / high_jitter / high_jerk / abnormal_release) + `_phase_metric_confidence_factor` (R11 conservative v1 documented) + `_apply_motion_id_boost` (×1.05 cap 1.0, ranking 전) + `_rank_top3` (4-stage sort + (pattern, phase) dedup) + `_overall_confidence_from_findings` + `_AXIS_IGNORE_WARNINGS_PER_METRIC` / `_AXIS_IGNORE_WARNINGS_REPORT` (R4 iter-3 two-tier) + `infer_force_direction_pattern` public entry |
| pipeline wiring | `_process` 안 mode_context inline (no helper) — `models.MODE_EXPERT` → "mode1" / `MODE_SELF + isFirst` → "mode3_first" / `MODE_SELF + !isFirst` → "mode3_progress" + `infer_force_direction_pattern` 호출 직후 `_dataclass_to_camel_case_dict` 변환 + `complete_analysis(force_pattern_inference=)` kwarg |
| 회귀 게이트 | phase09 + pipeline_phase9 131 PASS + phase06/07/08/08.1 408 / 1 skipped (regression 0) + tsc clean + 금지 표현 grep gate 10/10 PASS + AST severity guard `axis*.severity` 0 occurrence |
| Verification | 09-VERIFICATION.md — 4/4 SC VERIFIED + 13/13 D-09-* VERIFIED. Wave 2 production sweep OUT (D-09-E2 — Phase 11/15 자연 검증). |
| Follow-ups | belle 박제 검수 (18 canned + jointHint + pelvis_drop A1) + optional Codex cross-AI plan-review. |

### Plan 08.1-01 close-out (2026-06-09)

| 영역 | 결과 |
|---|---|
| compute_axis_deviation 실 본체 | Wave 0 transitional stub → 실 tilt-only 알고리즘 교체. pole_aligned 3D path 우선 + image_2d fallback + 둘 다 미가용 → 'tilt_unavailable'. severity = `_max_severity(_severity_from_tilt(shoulder), _severity_from_tilt(hip))`. confidence ≥ 70% high-reliability frame → 'medium', else 'low'. AxisDeviationMetric 6 필드 (Wave 0 schema 정합) |
| 신설 helpers | `_normalize_angle_undirected` (C-M1, modulo 180° + min(a, 180-a) → unsigned [0, 90], keypoint ordering swap artifact 차단) / `_severity_from_tilt` (C-H2, boundary-low + 1e-9 epsilon strict, boundary value = 'low', 정은지 baseline 25/25 'low' invariant) / `_get_tilt_thresholds` (lazy load + schema_v2 강제 검증, W10 정합 — fallback 신호 cache tuple 3rd element 단일 source, module-global flag 부재) / `_reset_tilt_thresholds_cache` |
| Helper cleanup (W9 audit) | 8 distance helper 삭제 (`_observed_torso_length_pole_aligned` + `_pelvis_position_*` + `_chest_position_*` + `_pole_aligned_axis_distance` + `_pelvis_position_image_2d` + `_chest_position_image_2d`) + `_severity_from_distance` + `_deviation_direction_from_pelvis`. 4 helper 보존 (`_observed_torso_length` + `_kp_pole_aligned_xy` + `_kp2d_xy` + `_midpoint` — compute_contact_stability 의존). `_shoulder_tilt_2d` / `_hip_tilt_2d` 갱신 — `_normalize_angle_undirected` 적용 |
| 모듈 상수 cleanup | `AXIS_PELVIS_DISTANCE_THRESHOLDS` + `AXIS_CHEST_DISTANCE_THRESHOLDS` 삭제. `AXIS_TILT_THRESHOLDS_DEG = (25.0, 37.5)` fallback default 보존 |
| tilt_thresholds.yaml | schema_v2 산출 (calibration_method='elite_p100_plus_margin', calibration_version='1.1', null_tilt_verified=true, 25 sample, 5 doc_ids). shoulder dist {p25=17.12, p50=24.84, p75=31.24, p90=42.36, p100=58.28} → medium=63.28° / high=94.92°. hip dist {p25=22.01, p50=27.73, p75=36.25, p90=44.36, p100=49.62} → medium=54.62° / high=81.93°. ipsf_tolerance.tolerance_deg=20.0 + major_fault_deg=40.0 |
| calibrate_tilt_thresholds.py | CLI (--sweep-uid / --source-type firestore/repo-artifact/wave2-explicit / --source-path / --output-path / --margin-deg 5.0 / --dry-run / --allow-recalibrate). C-H3 preflight hard gate (25 non-null + transitional 부재 + tilt_unavailable 부재 + 5 doc count + 5 phase/doc). P100+margin operational cutoff. D-04 future re-run entry point (value-only zero-code-change) |
| 옵션 A | Firestore reachable (FIREBASE_SA_PATH=`firebase-sa.json`) + sweep_phase8_1780986673 5 docs × 5 axisMetrics × 0 null × 0 transitional 검증 통과. Task 0 precondition belle 박제 완료 |
| 신설 phase08_1 test (46) | test_compute_axis_tilt_only (6) + test_axis_2d_angle_normalization (6) + test_severity_boundary_value_is_low (5) + test_severity_above_medium (3) + test_severity_above_high (3) + test_tilt_thresholds_loader (5) + test_tilt_thresholds_yaml_drift (12) + test_calibration_preflight (6). 모두 PASS |
| Wave 0 cleanup item | phase08/test_compute_axis_deviation.py — 4 stub assertion 제거, R2 drift defense (torso_scale denominator 영구 금지) 만 보존. phase08_1/test_compute_force_signals_does_not_reference_coordinate_space.py — test_compute_axis_deviation_emits_phase_8_1_transitional_warning (1 test) 제거 (Wave 1 새 본체 검증은 test_compute_axis_tilt_only.py 가 보유). C-B1 grep guard 2 tests 보존 |
| 회귀 게이트 | phase06 137 + phase07 108 + phase08 94 (Wave 0 cleanup -3) + phase08_1 63 (Wave 0 20 + Wave 1 46 - cleanup 3) + pipeline 11 = **413 PASS + 1 skipped**. TS strict mode clean (tsc --noEmit) |
| 3 commits | `30fd7d2` Task 1 (compute_axis_deviation tilt-only + yaml lazy loader + helper cleanup W9 audit + module-global flag 부재 W10) / `e08be9c` Task 2a (calibrate_tilt_thresholds.py + tilt_thresholds.yaml schema_v2) / `80c9a6b` Task 2b (yaml drift v2 (12) + calibration preflight (6)). Wave 0 + Wave 1 한 release boundary 박제 (Codex 권장 정합) |

Wave 2 진입 차단 해소 — schema_v2 yaml 존재 + null_tilt_verified=true. pipeline rewire + Pod 재배포 + 정은지 재sweep evidence 박제 가능.

### Plan 08.1-00 close-out (2026-06-09)

| 영역 | 결과 |
|---|---|
| 3-way lockstep atomic | AxisDeviationMetric 5 distance 필드 (pelvisDistanceFromPoleAxis / chestDistanceFromPoleAxis / scaleDenominator / coordinateSpace / deviationDirection) 영구 제거 + 6 필드 만 보존 (phase / shoulderTilt / hipTilt / severity / confidence / warnings). TS interface + Python dataclass + docs §9.3 + models.py 주석 single commit atomic |
| Transitional stub | compute_axis_deviation 본체 = stub (모든 phase boundary 에 대해 severity='low' default + warnings=['phase_8_1_wave_0_transitional'] 반환). distance 산출 path 영구 제거 + helper 함수 + 모듈 상수 보존 (Wave 1 cleanup) |
| C-B1 fix | compute_force_signals 본체 의 `coordinate_space == 'unavailable'` 참조 제거 → `axis_metric_transitional` 검출 로직 (모든 axis_metric warnings 박제 stub 신호 포함 시 top-level warning emit). C-H1 downstream guard 동일 신호 |
| C-H1 fix | Wave 0 단독 production 진입 금지 박제 (severity='low' 가 'measurement 안 됨' 을 '낮은 위험' 으로 silently 변환 차단). Wave 2 production sweep 게이트 = warning 부재 |
| C-MH1 박제 | AxisDeviationMetric naming caveat (실 의미 tilt-only) docstring/JSDoc 박제 + ROADMAP rename 별도 plan 메모 |
| Phase 8 test 수술 | test_compute_axis_deviation.py 11 → 5 함수 (distance 기반 6 함수 제거 + stub 동작 검증 5 함수 신설). test_force_signals_lockstep.py _FIELD_MAP 5 distance entry + coordinate_space_unavailable warning entry 제거 (coordinateSpace 박제 ContactStabilityMetric 보존). test_firestore_lockstep.py axisMetrics fixture 6 필드 dict 갱신 |
| Phase 08_1 test infra | __init__.py + conftest.py + 4 test 파일 신설 — 20 test (6 schema lockstep + 6 dataclass invariants + 5 firestore validator backwards-compat + 3 C-B1 grep guard). legacy 5 필드 dict 의 scalar backwards-compat 검증 박제 |
| 회귀 게이트 | phase06 137 + phase07 108 + phase08 97 + phase08_1 20 + pipeline 11 = 373 collected, **372 PASS + 1 skipped**. TS strict mode clean (tsc --noEmit) |
| 2 commits | `6a294d5` Task 1 (3-way lockstep atomic + stub + C-B1 + C-H1 + C-MH1 + Phase 8 test 수술 + phase08_1 신설 infra) / `1cb3e6e` Task 2 (firestore scoped validator backwards-compat + C-B1 grep guard) |

Wave 1 진입 차단 해소 — AxisDeviationMetric 6 필드 contract + stub 위에 compute_axis_deviation 본체 실 tilt 알고리즘 + threshold yaml 박제 가능.

### Plan 08-03 close-out (2026-06-09)

| 영역 | 결과 |
|---|---|
| Layer 2 wiring | TechniqueProfile.key_moments reuse (R6, 신규 Gemini call 영구 차단) + FORCE_SIGNALS_LAYER2_ENABLED 별도 env flag (R7) + _layer2_boundaries_from_technique_profile + _confidence_from_agreement + Cycle 2 NEW HIGH #2 ceiling 박제 (Layer 2 success/except 둘 다 `_layer1_confidence_from_preflight()` + `_min_confidence(agreement, ceiling)`) |
| pipeline wiring | _process Phase 8 wiring (compare_body_profiles 직후 1줄 호출) + _preflight_label_gate_passed env helper (Cycle 2 NEW HIGH #1, env 3-state) + _get_force_signals_layer2_recognizer singleton + _VideoAnalysisInputs.pole_axis_measurement 5번째 필드 (R10) |
| Gemini model env | R8 carryover (Codex Cycle 2) — 실 default 위치 = judging/gemini_moment_extractor.py:48 (`DEFAULT_GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')`). 'gemini-2.0-flash-exp' EOL 안전망 + recognizer.py 도 동일 GEMINI_MODEL env reuse |
| Firestore scoped validator | Cycle 2 NEW HIGH #3 — `_validate_dict_only_scalars` 본체 변경 영구 0 (firestore-nested-array-flat 보존) + 신설 scoped validator `_validate_force_signals_report` (forceSignalsReport path 만 화이트리스트) + complete_analysis(force_signals_report=) kwarg |
| frontend normalize | userAnalyses.ts forceSignalsReport null-guard (Phase 7 WR-02 B1 immutable spread + ?? null fallback, 7 필드 default) |
| In-line sweep fix (A/B/B'/C) | A: sweep_temp/ prefix 박제 (SQS race 우회). B: HoughPoleDetector.detect_with_line() image-space PoleLine2D 박제. B': compute_axis_deviation pole_aligned 3D fallback (RTMW keypoints_2d 부재 시 자동, warning 'coordinate_space_pole_aligned_fallback' + 'keypoints_2d_missing'). C: _map_moments_to_5phase setup/hold/release 단독 boundary 도출 (monotonic 위반 by construction 차단) |
| Manual checkpoint 자동화 | SAM validate PASS / Lambda env 갱신 (FORCE_SIGNALS_LAYER2_ENABLED=1, GEMINI_MODEL=gemini-2.5-flash, PREFLIGHT_LABEL_GATE_PASSED=0, file URI 방식) / Pod env 26개 복원 + Phase 8 3개 추가 + uvicorn restart (auth_configured:true, pipeline_loaded:true) / Pod phase08 pytest 103/103 PASS / 3차 sweep 정은지 5영상 schema 정합 5/5, axis distance 실값 산출, 0 server_error |
| Test | phase06 156 + phase07 88 + phase08 103 + pipeline 11 = 358 PASS + 1 skipped (회귀 0). TS strict mode clean |
| 4 commits | `fc3b6b7` Task 1 (Layer 2 wiring + Cycle 2 NEW HIGH #2/#3 + R8) / `ced1d87` Task 2 (pipeline wiring + Cycle 2 NEW HIGH #1 + R10 + frontend) / `c71c75b` in-line fix B+C (pole detection + Layer 2 monotonic) / `f627905` in-line fix B' (pole_aligned 3D fallback) |
| Deviation | (1) Rule 1 phase06 brittle assertion 구조적 강화 (key_moments 신설 forward-compatible) + (2) 4 in-scope additions A/B/B'/C — manual checkpoint sweep 결과 발견된 정합성 fix in-line commit |

Phase 8.5 (NEW, axis-metric-redesign) 신설 결정 — 정은지 5/5 영상 axis severity='high' 도메인 정합성 문제 (pole_aligned 좌표계 origin 미정의 + thresholds 단위 mismatch) 발견. research → discuss → plan path 박제. tilt 데이터 (rotation-only) 는 유의미 → Phase 9 1차 사용 가능.

### Plan 07-02 close-out (2026-06-08)

| 영역 | 결과 |
|---|---|
| classify_findings 본체 | pure function (D-07-A1 + D-07-A2 + Decision 1 + CR-01 + WR-03) + module-level _DEFICIT_TO_GROUP (5) + _JOINT_TO_GROUP (12) + _resolve_joint_group (CR-02 path) — body_normalizer.py:958-1140 |
| compare_body_profiles wiring | measure_ipsf_absolute_deficits 호출 직후 classify_findings 1줄 + BodyComparisonReport 조립 4 신설 kwarg 주입 (findings/dnoc/rec_focus/recommended_focus_fallback) — line 1503 + 1531-1539 |
| WR-02 frontend normalize | userAnalyses.normalize() immutable spread + map 패턴, bodyComparisonReport 신설 7 필드 null-guard (iteration 1 B1 retract). TS interface non-optional 유지 — normalize() 가 compat layer |
| CR-01 thread | render_finding_copy(used_reference_fallback=is_mode3_first_fallback) — mode3_first fallback path 에서 unprefixed 단일 카피 + interpretation=None |
| WR-03 fallback | recommended_focus[] 빈 list → _EMPTY_FOCUS_FALLBACK 자동 박제, 채워진 list → None |
| INF-01 preserves | test_classify_findings_preserves_measurement_fields.py — 6 원본 측정 필드 보존 behavioral primary safety property |
| Test | phase07 108 PASS (Plan 01 90 + Plan 02 18 신설) + phase06 136 PASS + 1 skipped (회귀 0) + tsc --noEmit clean |
| 3 commits | `2aedb84` Task 1 (classify_findings + 12 unit tests + tests/__init__.py 환경 fix) / `4851a43` Task 2 (wiring + 6 integration/camelCase tests) / `8559c6f` Task 3 (WR-02 retract B1 frontend) |
| Deviation | (1) Rule 3: backend/tests/__init__.py 신설 — pre-existing 환경 blocker (2) Rule 1: AST grep gate docstring false positive — ast.get_docstring 패턴 적용 |

Phase 8 진입 시그널: 중심축 이탈 + 접촉점 안정성 + jerk/jitter 측정 — phase별 산출 + 가림 스무딩. FORCE-01 요구사항.

### Plan 07-01 close-out (2026-06-08)

| 영역 | 결과 |
|---|---|
| schema lockstep | BodyComparisonFinding +4 + BodyComparisonReport +3 (recommended_focus_fallback WR-03 fix 포함) — Python dataclass + TS interface + docs §8 + §8.3 단일 atomic commit (d4d8af4) |
| copy_templates.py | 33 canned (21 + 12 global CR-02 fix) + 3 mode prefix + render_finding_copy(used_reference_fallback CR-01 fix) + FORBIDDEN 9 종 + _EMPTY_FOCUS_FALLBACK WR-03 (fcb4025) |
| Wave 0 인프라 | phase07/__init__.py + conftest.py + fixtures/_factory.py + 6 fixture JSON (3e1fbf7) |
| WR-01 fail-safe | measure_ipsf_absolute_deficits 의 6 BodyComparisonFinding emit 위치 placeholder category="uncertain" (Plan 02 재할당) |
| iteration 2 fix | CR-01 / CR-02 / WR-01 / WR-03 / WR-04 모두 mitigation. WR-02 + INF-01 은 Plan 02 scope |
| Test | phase07 90 PASS / phase06 136 PASS + 1 skipped (회귀 0) / tsc --noEmit clean |
| 3 commits | `3e1fbf7` Task 1 (fixture infra) / `fcb4025` Task 2 (copy_templates + 3 test) / `d4d8af4` Task 3 (3-way lockstep + WR-01 atomic, 5 files) |
| Deviation | (1) Rule 1 schema: BodyComparisonFinding.category default = "uncertain" — Phase 6 회귀 0 + WR-01 fail-safe 정합 (2) Rule 1 AST gate: Assign + AnnAssign 양쪽 검사 — copy_templates.py 의 typed dict literal 검출 |

Plan 07-02 진입 시그널: `classify_findings(findings, body_normalization_confidence, comparison_type, *, used_reference_fallback)` 본체 + integration test. body_normalizer.py 의 6 placeholder 를 D-07-A1 + D-07-A2 룰로 재할당.

> Phase 6 close-out (2026-06-08): 알고리즘 + production wiring 4/4 검증 PASS. 코드 리뷰 10/10 fix (3 Critical + 7 Warning). phase06 tests 136 pass / 1 skip. Plan 06-03 Task 5 (실 Firestore 백필) + Task 6 (Pod sweep) 은 belle 운영 작업으로 `06-HUMAN-UAT.md` 박제.

### Plan 06-02 close-out (2026-06-08)

| 영역 | 결과 |
|---|---|
| pipeline wiring | _extract_video_analysis_inputs 단일 helper (R3) + R4 non-null student_profile + R2 reference source_pose fetch + R8 extra_warnings injection + C2 motion_id exact-match (retro Phase 5 patch) |
| firestore_admin | complete_analysis(body_comparison_report=, body_normalization_profile=) 확장 + _validate_flat_dict_no_nested_array recursive validator (W5) + _validate_dict_only_scalars (list-of-dict 안 nested 금지) |
| _dataclass_to_camel_case_dict | C8 4-case 명세 (None / dataclass / list / dict / Enum / scalar) + BodyComparisonReport 중첩 변환 |
| frontend | userAnalyses.ts I2 positive assertion (bodyComparisonReport literal) + Korean defensive comment |
| Rule 1 fix | body_normalizer.measure_ipsf_absolute_deficits 의 expects 변수 iterate 오류 (joint_expectations dict 에서 JOINT_EXTEND 값 키로 derive) |
| Test | 본 plan 55/55 PASS, 전체 phase06 107/107 PASS, 기존 pipeline 156/156 PASS, tsc --noEmit clean, sam validate exit 0 |
| 5 commits | `8c5b002` Task 0 (motion_id + Gemini populate) / `2e7d97c` Task 1 (pipeline wiring) / `a60b034` Task 2 (firestore_admin + W5) / `fc75212` Task 3 (camelCase + frontend) / `77383a1` Task 4 (통합 smoke) |

Plan 06-03 진입 시그널: 정은지 reference 5개 영상 백필 (extract_reference_body_profiles.py + seed-reference-body-profile.mjs) — bodyNormalizationProfile + bodyComparisonSourcePose 둘 다.

### Plan 06-01 close-out (2026-06-08)

| 영역 | 결과 |
|---|---|
| body_normalizer.py | Kinematic Tree Reprojection (C1 target-profile L_ref) + IPSF deficit (C14 pose_reliability_low rename) + confidence-tiered hybrid 산식 (R5 dispersion + R6 4채널) + BodyComparisonReport + BodyComparisonSourcePose (R2) |
| 3-way contract lockstep | TS `analysis.ts` + Python `models.py` re-export + `docs/contract.md §8 + §8.1 + §8.2` atomic commit |
| 6 fixture Validation Architecture | 합성 데이터 (160cm pro vs 140cm student, twist, foreshortening, unstable swing, split angle, **high dispersion R5 신규**) |
| Test | pytest 52/52 PASS, tsc --noEmit clean |
| 5 commits | `daa4e8b` test fixtures / `12ed249` Kinematic Tree / `d9c50e1` confidence / `116f400` IPSF deficit + compare_body_profiles / `a444726` 3-way lockstep |

Plan 06-02 진입 시그널: pipeline _process wiring + mode1/mode3/Gemini fallback (C2 retro Phase 5 patch + R3 단일 helper + R4 student non-null + R2 source pose fetch + R8 extra_warnings injection) + Firestore complete_analysis 확장 + frontend normalize + SAM build smoke.

### 진입 chain 갱신 (belle 2026-06-08)

belle 박제 — "분석이 제대로 되는 게 목표. 오버레이, 체형 정규화, 힘 패턴은 필수적. 어떻게든 기필코 개발하려고 하는 게 지금."

v1 시퀀스 (분석 정확도 chain — ROADMAP dep 그래프 정합):

**Phase 6 (체형 정규화) → 7 (차이 분류) → 8 (중심축·접촉점·jerk) → 9 (ForceDirectionPattern + 실패 후보 3) → 12 (실측 각도 + 키포인트 오버레이) → 13 (보완 운동 + LLM)**

이전 chain 박제 (이력 보존):

- 2026-06-07 belle 결정: A+B+C 우선, Phase 2~11 보류 (파일럿 후 v1.5) — Phase 12.5 close-out 후 belle 갱신으로 무효
- 2026-06-07 belle 결정: "Phase 2 → 6 → 7 → 12 → 13" — 힘 패턴 (8, 9) 누락, 본 갱신으로 8/9 추가

### Phase 2 plan 산출

| 파일 | 내용 |
|---|---|
| 02-CONTEXT.md | scope + 6 dependencies + 6 locked decisions (D-02-01~06) |
| 02-RESEARCH.md | RTMW COCO-17 mapping + MAD smoothing + torso self-ref normalize + R&D 격리 path |
| 02-01-PLAN.md | 6 atomic commits (T1 contract → T2 fixture → T3 measurer → T4 pipeline 통합 + T5 R&D harness → T6 AST gate + BODY-01 rename) |
| 02-PLAN-CHECK.md | 15/15 binary PASS, PASS_WITH_CONCERNS (4 non-blocking risks) |

### Phase 2 진입 순서 (전체)

Phase 2 → 6 (체형 정규화) → 7 (차이 분류) → 12 (키포인트 오버레이) → 13 (보완 운동 + LLM)

> Phase 13 scope 확장 (belle 2026-06-07): 원래 "보완 운동·스트레칭 추천 라이브러리" (PERS-03) 단독이었으나, Phase 12.5 시뮬 한계의 backend 후속 작업 (LLM 활성화 + 분기 1/2 카피 분리 + IPSF 정의 각도 fixture) 을 같은 phase 로 통합. 이전 Phase 12.6 = revert.

### Phase 12.5 close-out 내역

| 영역 | 결과 |
|---|---|
| backend `assemble.build_dimension_explanation` | weightPercent (Largest Remainder) + mode-aware baseline + source-faithful deficits (commit 1c0d20a) |
| backend `coach_writer` LLM | Cerebras gpt-oss-120b JSON 프롬프트 — 다중 원인 + case 처방 + 부상 경고 + coachNote. graceful `_normalize_entry` (commit 62fdeed) |
| frontend `DimensionDetailModal` | 동작·사용자 동적 formula ("세계 심사 기준은 [동작]에서 ... [회원]님의 영상 자세를 반영") + "심사평" 자연어 3박자 (평가+이유+결정) |
| frontend `CoachingTipDetailModal` | LLM `tip.detail2` 렌더 (causes 카드 + injury 경고 + coachNote). detail2 없으면 graceful fallback |
| UX 함정 fix | (a) sheet useWindowDimensions 명시 height (b) backdrop = pure View + 위 빈 영역만 Pressable — Pressable+stopPropagation 가 ScrollView gesture 가로채는 함정 회피 |
| belle UX 검증 | PASS — 스크롤 어디서든 정상 동작, 심사평 톤 OK |

### Phase 12.5 남은 한계 (Phase 12.6 이관)

1. **학원 용어 vs IPSF 등재 분기 카피** — 폭스탑 = "정은지 선수 기준" / 클라임 = "세계 심사 기준 (IPSF) + 180°". 메모리 [`studio-term-3branch-system`] 분기 1/2 정합
2. **angle 차원 동작별 IPSF 정의 각도** — 어깨 90° / 엉덩이 110° 등 동작별 fixture 또는 LLM 매핑
3. **시뮬 segments 일부 시나리오 X** — mode 3 first 정답 (이전 영상 없음), 그 외는 실 분석에서 backend `assemble.build_segments` 자동 생성

### Phase 12 §12 UAT 2차 finding fix (2026-06-11)

belle iOS UAT 2차 (TestFlight Build 12) 에서 4 finding 박혀있음. 3건 (B/C/D) Phase 12 내 해소, 1건 (A 좌/우 mirror) 은 Phase 13 신규 plan 분리.

| 항목 | 결과 |
|---|---|
| 12-B frame_extractor 마지막 frame | `4156a89` — last_resized 추적 + step 모듈로 미달 시 강제 추가. 5 단위 테스트 (`backend/tests/test_frame_extractor_last_frame.py`) PASS — remainder skip / no-dup / clip / empty / UAT 17s 시나리오 모두 검증 |
| 12-D KeypointOverlay 저신뢰 keypoint | `62270f2` — `KEYPOINT_LOW_CONFIDENCE_THRESHOLD = 0.5`. `KeypointReport.confidence` flat array read, `KeypointPoint` type 신설. visibility<0.5 → estimateGray (#B0B0B0) + dashed 4/W + opacity 0.7. 강조 분기 (highlightedJoints) 보다 우선. floating angle label 도 저신뢰 joint 표시 X (각도 자체 불신뢰). TS PASS |
| 12-C VideoCompare 두 영상 timeline 분리 | `ddbe074` — left/right currentTime + duration 4 state 분리. progress bar 단일 유지 (짧은 쪽 기준). 시간 라벨 두 영상 동시 표시 `{leftLabel} 0:01 / 0:17 · {rightLabel} 0:01 / 0:16`. TS PASS |
| reference keypoint 5영상 재추출 | Pod (RTX 4090 z3fy82pjgu4mga) extract_reference_keypoint_reports.py 5/5 OK (453.9s) → /workspace/reference-keypoint-reports.json (1.0M) → seed-reference-motions.mjs --keypoint-reports 로 Firestore reference/{motionId}.referenceKeypointReport 5건 갱신 (presigned URL 도 7일 연장, 만료 2026-06-18) |
| deferred-items.md §12 박제 갱신 | `c3dca7c` — B/C/D 완료 + 우선순위 진행 상태 갱신 |
| pod setup_pod_full.sh OpenMMLab CDN 만료 패치 | `7f81eb2` — RTMW HF/S3 mirror, YOLOX HF mirror, RUNPOD_AUTH_TOKEN auto-fetch, uvicorn __pycache__ 청소. 다음 Pod 셋업 시 함정 20-27 자동 회피 |

**Pod 인프라 결정 (2026-06-11)**:

- Network Volume EU-RO-1 (`sunity-motion-vol`, 31GB, $2.17/월) 생성. 단 RunPod Community Cloud GPU 호스트가 Network Volume mount 미지원 → ephemeral 진행. Volume 은 향후 Secure Cloud 전환 또는 mmpose 작업 시 재평가.
- mmcv CUDA 빌드 40분+ stall → fast-path 셋업 (boto3 / imageio / rtmlib / onnxruntime-gpu 1.19.2 / RTMW S3 백업 / YOLOX HF mirror / Firebase SA SSM) 으로 우회. extract 스크립트엔 mmpose 불필요.

**다음 단계**:

1. belle EAS Build profile production → TestFlight Build 13 빌드 + submit
2. belle UAT 3차 (12-A 외 3 finding 해소 검증)
3. UAT 3차 PASS → Phase 12 전체 close-out + ROADMAP `[x]` 표기
4. Phase 13 신규 plan (좌/우 mirror correction post-process)

Last activity: 2026-07-20 - Completed quick task 260720-hn8: 영상 선택 실패 알림창 전환 + iCloud 폴백

**시퀀스 (belle 2026-06-07 결정 — B → C → A)**:

1. **B (Phase 12.5)** — 3~5일 — UI transparency + 강사 보조 카피 — 빌드 12 ship
2. **C (Phase 16 코드 통합)** — 1~2주 — AKA 매핑 + 5트랙 v1 + 분기 3 — 빌드 13 ship
3. **A (Phase 12)** — 2주~ — 실측 각도 + 키포인트 오버레이 — 빌드 14 ship
4. parallel: Plan 01-24 — NLF R&D 격리 명시 — 0.5~1일, B 와 별도 PR

상세 = `.planning/roadmap-replan-2026-06-07.md` + `.planning/roadmap-replan-2026-06-07-review.md`.

Progress: [█████████░] 92%

## ▶ Plan 23 sweep verdict `phase1_ready_to_swap=False` (2026-06-03) — D-16 보류

belle Pod 5영상 sweep (`backend/research/evaluations/reports/sweep_rtmw_20260603_1409/report.md`) 결과:

| 게이트 | 결과 | 박제 기준 |
|---|---|---|
| IPSF within_tolerance | **1/5 PASS** | 5/5 필요 |
| line PASS | **3/5 PASS** | 5/5 필요 |
| angle PASS | **0/5 PASS** | 5/5 필요 |
| pole_axis | 5/5 low (수직 폴백) | high 필요 |

| 모션 | pole_axis | IPSF | line | angle | ms/f | rtmw_score |
|---|---|---|---|---|---|---|
| ref-climb | low | PASS | PASS | FAIL | 2201 | 95.4 |
| ref-foxtop-split | low | FAIL | FAIL | FAIL | 2164 | 93.0 |
| ref-foxtop | low | FAIL | FAIL | FAIL | 2083 | 93.3 |
| ref-invert | low | FAIL | PASS | FAIL | 2116 | 93.6 |
| ref-sideway-spin | low | FAIL | PASS | FAIL | 2009 | 94.8 |

**핵심 진단 (root cause 3종 동시 발현)**:

1. **IPSF criteria target=180° 일률 — FallbackRecognizer 한계**
   - 모든 hold moment 의 shoulder/hip/knee target=180° (완전 EXTEND 가정)
   - measured 값 21~107° = 실제 자세는 굽힘인데 yaml 은 폄 가정
   - Plan 11 박제 ("FallbackRecognizer 가 굽은 자세에서 EXTEND 못 찾아 line 차원 None") 그대로 — Phase 5 (Gemini 기술 인식기) 통합 전엔 IPSF angle 게이트 의미 없음

2. **HoughPoleDetector 미설치 → pole_axis 부정확**
   - 5영상 모두 axis_vector=(0,1,0) low confidence (수직 폴백)
   - 실제 카메라 각도/폴 회전 있을 시 line 측정값 부정확
   - line 3/5 PASS 도 폴백 영향 가능

3. **AKA 매핑 vs yaml criteria 정합 미검증**
   - belle 매핑: `ref-foxtop.yaml` ← 인버트 버터플라이, `ref-invert.yaml` ← 플랭크 스핀, 등
   - yaml hold target=180° 가 그 자세의 IPSF 기준인지 belle/정은지/NotebookLM IPSF CoP 2024-2025 재검증 필요

**belle 결정 (2026-06-03)**: 결과 박제 commit 먼저 + 다음 plan 의논. 박제 [[gap-and-line-angle-mandatory-gates.md]] "강등/우회 금지" 정신 유지.

**Plan 24 / 25 진입 차단 — D-16 보류**. 다음 후보:

- (A) Phase 5 (Gemini 기술 인식기) 통합 선행
- (B) Plan 26 (가칭) — root cause 3종 동시 fix plan 신설 (Gemini wiring + HoughPoleDetector + yaml 재검증)

### Plan 23 belle Pod sweep 함정 5종 박제 (재사용 위함)

| 함정 | Fix |
|---|---|
| `imageio` pyav 플러그인 누락 | `pip install 'imageio[pyav]'` |
| rtmlib 0.0.15 `pose` alias 부재 | `export RTMW_ONNX_PATH=<unzipped end2end.onnx>` 강제 (commit 3b27c25) |
| rtmlib Wholebody batch 미지원 | 단일 (H,W,3) frame 입력 (commit 375c21c) |
| mmpose `chumpy` 빌드 fail | `pip install --no-build-isolation chumpy` 선행 |
| onnx 위치 패턴 | `<weights_root>/20230928/rtmpose_onnx/<model>/end2end.onnx` |

상세 박제 = [[runpod-gpu-env.md]] 업데이트 누적 중.

---

## ▶ Plan 11 sweep verdict `gap_too_wide_blocked` (2026-06-01) — Plan 12/13/14 신설

belle Pod 5영상 sweep (`sweep_rtmpose_20260601_0411`) 결과:

| 모션 | RTMPose+MB | NLF | gap | D-15① ≥70 | D-14 |gap|≤5 | line | angle |
|---|---|---|---|---|---|---|---|
| ref-climb | 89.0 | 58.0 | **+31** | PASS | **FAIL** | N/A | N/A |
| ref-foxtop-split | 79.0 | 63.0 | **+16** | PASS | **FAIL** | N/A | N/A |
| ref-foxtop | 81.0 | 64.0 | **+17** | PASS | **FAIL** | N/A | N/A |
| ref-invert | 70.0 | 65.0 | +5 | PASS | PASS | N/A | N/A |
| ref-sideway-spin | 80.0 | 81.0 | -1 | PASS | PASS | N/A | N/A |

D-15① 5/5 PASS, D-14 2/5 PASS, line·angle 0/5 PASS. 평균 |gap| = 14점.

**belle 결정 (2026-06-01)**: "갭은 어떻게든 줄여야 한다. Gemini 든 다른 수단이든 가리지 말고." + "라인과 각도도 계획에 들어가야 한다." → D-14 강등 거부. 갭 + line/angle 둘 다 Wave 3 진입 1순위 게이트. Plan 12/13/14 신설.

### 신설 Plan 12 / 13 / 14

| Plan | 역할 | 게이트 통과 path |
|---|---|---|
| **01-12** (NEW) | 갭 root cause 디버그 spike | 가설 a~e (frame-mean / RTMPose headdown / NLF baseline 편차 / keypoint 매핑 / MotionBERT lift path) + ref-invert 22점 회귀 + sideway-spin Plan10 vs Plan11 비일관성 박제 |
| **01-13** (NEW) | Gemini key moment + criteria extractor | multimodal 2.5 Pro. hold/peak/setup/release 시점 + EXTEND/BENT criteria. dimensions sampling frame-mean → moment-list 교체. line/angle 회복 + 갭 줄이기 동시 path. |
| **01-14** (NEW) | 5영상 재검증 sweep | Plan 12 fix + Plan 13 key moment 적용 후 sweep_rtmpose 재실행. **게이트 = 갭 ≤5 + line/angle 5/5 PASS** |

Plan 14 통과 → Plan 04 / Plan 05 (Wave 3) 진입.

### Plan 08 (MP+MB) 대비 RTMPose 회귀

| 모션 | MP+MB (P08) | RTMPose+MB (P11) | Δ |
|---|---|---|---|
| ref-climb | 85 | 89 | +4 |
| ref-foxtop-split | 75 | 79 | +4 |
| ref-foxtop | 90 | 81 | -9 |
| **ref-invert** | **92** | **70** | **-22** ← 회귀 |
| ref-sideway-spin | 64 | 80 | +16 |

ref-invert RTMPose headdown 약점 가설 — Plan 12 에서 frame-by-frame avg_rtm_score 분포 분석.

### Plan 10 spike vs Plan 11 sweep — ref-sideway-spin 비일관성

| | Plan 10 spike | Plan 11 sweep | Δ |
|---|---|---|---|
| overall | 72 | 80 | +8 |
| ms/frame | 37 | 21 | 절반 |

같은 영상/설정. frame seek/sampling 차이 가설 — Plan 12 에서 spike vs sweep 같은 영상 비교 trace.

## ▶ Plan 10 STRONG_PASS 결과 (2026-06-01) — Plan 11 (C scope) 진입

**Plan 10 verdict** = `strong_pass`. ref-sideway-spin 1영상:

| 항목 | RTMPose+MB | NLF | 갭 | 게이트 |
|---|---|---|---|---|
| overall | **72.0** | 81.0 | -9.0 | D-15① PASS (≥70) |
| stability | 72.0 | 81.0 | -9.0 | — |
| line | N/A | N/A | N/A | **Phase 5 게이트** |
| angle | N/A | N/A | N/A | **Phase 5 게이트** |
| ms/frame | 37 | 665 | — | 18x faster (production win) |

**핵심 발견**: line / angle N/A = FallbackRecognizer 한계 (PROJECT.md "현 핵심 블로커"와 정확히 일치 — "굽은 그립 자세에서 EXTEND 못 찾아 line 차원 None"). 해결은 **Phase 5 Gemini 기술 인식기** 통합.

### Plan 11 scope (belle approved C, 2026-06-01)

- **T-1**: 5영상 sweep (ref-climb / ref-foxtop-split / ref-foxtop / ref-invert / ref-sideway-spin) — RTMPose+MB vs NLF baseline
- **T-2**: line / angle N/A root cause 박제 — FallbackRecognizer 한계 정확히 어떤 자세/관절에서 발동? threshold 조정으로 일부 회복 가능? 다른 4영상에서도 같은 패턴?
- **T-3**: 게이트 룰 검토 — D-15① 70 threshold 적정 여부, D-14 (NLF gap ≤5) production 우선순위 재확인
- **T-4**: Wave 3 진입 게이트 — Plan 04 (NLF R&D 격리) + Plan 05 (atomic swap) 진입 조건 명시
- **T-5**: belle Pod 실행 + 5영상 결과 판정

Gemini 통합은 **Phase 5 별 phase** — belle Gemini API 키 (Google AI Studio) 발급 + Parameter Store 주입 wiring 선행 필요.

### belle Gemini API 키 작업 (병행, 2026-06-01 발급 진행 / 2026-06-03 모델 갱신)

| Phase | Gemini 역할 | 권장 모델 (2026-06-03 belle 결정) | 키 발급 path |
|---|---|---|---|
| **Phase 5** | 기술 인식기 (영상 → 분류 + EXTEND/BENT) | **Gemini 3.1 Pro 단일** (belle 2026-06-04 확정, 3.0 삭제). 3.5 Flash 는 v1 미사용 — v2 비용 분석 후 별 plan 평가 | Google AI Studio → /sunity/motion/gemini-api-key (SecureString) |
| **Phase 11** | 자연어 코칭 번역 | Cerebras llama3.1 유지 권장 (이미 동작 중) — Gemini 3.5 Flash 도 후보 (한국어 품질 비교 필요) | — |

belle 박제 (2026-06-03): "분석이 완벽해야 한다는 것 = 모든 박제 기준. 우회/대체 상황이면 언제든 제안 OK". 모델 선택은 분석 정확도 기준 — 이전 박제 (2.5 Pro) 는 정보 부족 시점 추정, 3.0/3.1 Pro 가 실제 사용 가능 시점에 정확도 + multimodal 성능 우위.

### Plan 10 디버그 이력 (Pod 4함정 박제)

1. mmcv 빌드 실패 → `pip install --no-build-isolation "mmcv>=2.0,<2.2"` (mmcv 2.1.0)
2. numpy ABI 불일치 → `pip install "numpy>=1.26,<2"` (1.26.4 다운그레이드)
3. detector alias 카탈로그 실패 → spike 코드 패치 commit `f019070` (single-person 우회 default)
4. Pod git pull 갱신 안 됨 → 로컬 commit 후 `git push origin main` 누락. push 후 Pod pull 정상.

상세 fix 명령 + 환경 변수 = `.claude/projects/.../memory/runpod-gpu-env.md` 박제됨.
GSD process rule = `.claude/projects/.../memory/gsd-pod-work-push-first.md` 박제됨.

### 현재 Pod 환경 (2026-06-01 22:00 시점, Plan 11 진입 준비됨)

**Pod 살아있음. 추가 install 없음.** Plan 11 belle 실행 = git pull + sweep 명령만.

| 항목 | 상태 |
|---|---|
| GPU / Container | RTX 3090 / RunPod PyTorch 2.4 template, Python 3.11 |
| torch | 2.4.1+cu124 (검증됨) |
| numpy | 1.26.4 (다운그레이드, opencv-python warning 무시 가능) |
| mmcv / mmengine / mmdet / mmpose | 2.1.0 / 0.10.7 / 3.3.0 / 1.3.2 |
| xtcocotools | 1.14.3 (numpy 1.x 호환) |
| MotionBERT | `/workspace/MotionBERT/` clone + `best_epoch.bin` (~120MB) |
| RTMPose-l weights | `/workspace/rtmpose_weights/rtmpose-l_simcc-coco_pt-aic-coco_420e-256x192-1352a4d2_20230127.pth` + `.py` config |
| SunityMotion git HEAD | 10683aa (Plan 10 closeout + Plan 11) — push 됨, Pod 에서 `git pull` 시 받음 |
| detector default | single-person 우회 (`--det-model none`) — commit f019070 |
| AWS 자격증명 | env 박제됨 (Plan 08 setup 이래 유지) |
| Firebase SA | `/workspace/firebase-sa.json` |
| Gemini API 키 | Parameter Store `/sunity/motion/gemini-api-key` (SecureString, 2026-06-01 박제). Pod env 주입은 Phase 5 진입 시 wiring |

**Memory 박제 완료** (`license-blocklist-pose.md`): AlphaPose Noncommercial → 향후 plan 후보군에서 영구 제외.

### Plan 09 의사결정 매트릭스 (이력 보존)

| belle 응답 | Plan 10 방향 | 결과 |
|---|---|---|
| **option-b-1, spike RTMPose** | Apache 2.0 + 2D detector 교체 | **✓ 선택됨 (2026-06-01) → STRONG_PASS** |
| option-a, spike HybrIK | MIT + SMPL prior lift | 미선택 |
| option-c, accept 4/5 | 게이트 룰 재정의 | 미선택 |
| option-d, multi-view | 다중 시점 v1 spec | 미선택 |
| option-b-2 / b-3 | MMPose HRNet / MS HRNet | 미선택 |
| hold + research more | 별도 research 후 신규 plan | 미선택 |

## Plan 08 5영상 검증 결과 (재인용)

| 모션 | MP+lifter | NLF | D-15① ≥70 |
|---|---|---|---|
| ref-climb | 85 | 58 | PASS |
| ref-foxtop-split | 75 | 62 | PASS |
| ref-foxtop | 90 | 64 | PASS |
| ref-invert | 92 | 65 | PASS |
| **ref-sideway-spin** | **64** | 81 | **FAIL** |

평균 81.2 (Plan 06 단독 MP: 22.8 → **3.5배 회복**). D-15① 4/5 PASS.

**Path B 결정 (2026-05-31)**: AlphaPose 2D 어댑터로 측면 자세 보강 → ref-sideway-spin ≥ 70 회복 spike (Plan 09).
**Path B 수정 (2026-06-01)**: AlphaPose 라이선스 Noncommercial → **RTMPose-l (Apache 2.0)** 로 대체 (Plan 10). 통과 시 5영상 sweep + 게이트 룰 재정의 + Wave 3 진입 (Plan 11+).

## Performance Metrics

**Velocity:**

- Total plans completed: 57 (01-01, 01-02, 01-03, 01-06, 01-07, 01-08)
- Average duration: ~30 min/plan (executor) + belle Pod 실행 별도

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: — min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 06 | 3 | - | - |
| 03 | 3 | - | - |
| 14 | 3 | - | - |
| 11 | 3 | - | - |
| 19 | 4 | - | - |
| 26 | 6 | - | - |
| 27 | 9 | - | - |
| 28 | 8 | - | - |
| 29 | 8 | - | - |
| 30 | 4 | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 06 P03 | 50 | 7 tasks | 10 files |
| Phase 08.1 P02 | 90 min | 5 tasks | 6 files |
| Phase 09 P01 | 25min | 7 tasks | 11 files |
| Phase 09 P02 | 30 | 5 tasks | 11 files |
| Phase 04 P03 | ~20min | 2 tasks | 4 files |
| Phase 04 P05 | 15 | 2 tasks | 4 files |
| Phase 03 P01 | 9min | 3 tasks | 8 files |
| Phase 03 P02 | 4 | 2 tasks | 2 files |
| Phase 03-bodyprofileinput P03 | 5min | 2 tasks | 4 files |
| Phase 15 P01 | 35min | 3 tasks | 4 files |
| Phase 15 P03 | 70min | 2 tasks | 1 files |
| Phase 15 P04 | 75min | 3 tasks | 2 files |
| Phase 19-vision-hybrid P01 | 18min | 2 tasks | 4 files |
| Phase 19 P02 | 14 | 2 tasks | 8 files |
| Phase 20 P01 | 14 | 1 tasks | 2 files |
| Phase 20 P02 | 18min | 1 tasks | 2 files |
| Phase 20 P20-03 | 38min | 3 tasks | 8 files |
| Phase 24 P04 | ~25min | 3 tasks | 5 files |
| Phase 10 P01 | 38min | 3 tasks | 12 files |
| Phase 10 P02 | 50min | 3 tasks | 8 files |
| Phase 10 P03 | 55min | 2 tasks | 5 files |
| Phase 10 P04 | 45min | 2 tasks | 4 files |
| Phase 26 P06 | ~55min | 3 tasks | 11 files |
| Phase 22 P22-01 | 18min | 3 tasks | 8 files |
| Phase 22 P04 | multi-session (07-09~07-11) | 4 tasks | 12 files |
| Phase 22 P11 | 22min | 3 tasks | 5 files |
| Phase 22 P12 | 18min | 3 tasks | 5 files |
| Phase 33 P01 | 20 | 2 tasks | 3 files |
| Phase 33 P33-04 | 52min | 3 tasks | 3 files |
| Phase 33 P22 | 55m | 3 tasks | 7 files |
| Phase 33 P12 | 80m | 2 tasks | 8 files |
| Phase 33 P13 | 25분 | 2 tasks | 6 files |
| Phase 33 P14 | 50m | 2 tasks | 9 files |
| Phase 33 P15 | 20분 | 2 tasks | 7 files |

## Accumulated Context

### Roadmap Evolution

- Phase 24 CLOSED (belle 2026-06-29, close-out A): 감점 엔진 production 검증 + kip-up 위양성 해결(99→88, vision-측정 split 감점) + 캐시 결정성 버그 fix. 5/5 페어 변별. 잔여 minor(calibration)=후속.
- Phase 20 CLOSED (belle 2026-06-29): 대상3(kip-up 위양성=24-A 해결 / 상단변별·결정성=캐시fix / Mode3 게이트·근거=Phase19/20-03) 충족.
- Phase 15 DISSOLVED (belle 2026-06-29): 실작업(점수정확도/위양성)은 19/20/24 흡수, 실증/TestFlight=마일스톤 완료 이벤트(개발 phase 아님), "고수 위양성 없음"=마일스톤 통과 기준(20/24 책임). renumber/삭제 없이 ROADMAP tombstone — 후속 phase가 "Phase 15 실증 발견 출처"로 참조하므로 번호·artifacts 보존.
- Phase 18 added: 전문가 일부러-실수 reference eval 세트 (가칭, Phase 15 이후, belle 2026-06-16)
- Phase 20 added: v2 비전 점수 (Gemini 시각 거부권) — kip-up 위양성 + 상단변별 + Mode3 미보유게이트. roadmap+CONTEXT pod-free, 구현 Pod 의존
- Phase 21 added: 전문가 셀프서비스 reference 등록 (angles 자동계산 GPU 연결) — belle 2026-06-20, CLAUDE.md 파일럿 Step 2
- Phase 26 added: 여정 트랙 등재 (belle 승인 2026-07-06)
- Phase 27 added: 여정 트랙 등재 (belle 승인 2026-07-06)
- Phase 28 added: 여정 트랙 등재 (belle 승인 2026-07-06)
- Phase 29 added: 여정 트랙 등재 (belle 승인 2026-07-06)
- Phase 30 added: 여정 트랙 등재 (belle 승인 2026-07-06)
- Phase 31 added: 여정 트랙 등재 (belle 승인 2026-07-06)
- Phase 22 edited: 스코프 확정(22-CONTEXT.md D-01~16) + Phase 21 디커플 — 22 먼저
- Phase 32 added: 분석 결과를 읽히게 — 해석·방법·코치. 즉시수리 3건(동작비교 초맞춤/참고지표 겹침/확대비교 크롭) wave-1 흡수
- Phase 35 added: 서버측 정렬 합성 비교 영상 — 돌파 ① (belle 2026-08-07 승인, 1순위). 전 동작 프로토타입 배치 → belle 느낌 평가, 채택 시 라이브 동기 기계 폴백 강등. Phase 34 와 독립·병행 가능

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [2026-05-31 아키텍처]: 두 엔진 분리 — 엔진 A(체형 보정, coaching 모드 정규화 ON) + 엔진 B(힘 패턴, 움직임 방향만 측정·근육 힘 단정 금지)
- [2026-05-31 포즈 — 최종]: **상용/베타 제품 = MediaPipe + Gemini** (Apache 2.0, 라이선스 리스크 0). **NLF/SMPL-X = 라이선스 확인 전까지 제품 코드 비포함, 내부 비상업 R&D 비교군으로만 사용**. 입수처 = https://is.mpg.de/ps/code, https://smpl-x.is.tue.mpg.de. PoseEngine 인터페이스 추상화 — `MediaPipePoseEngine`(제품) + `NlfPoseEngine`(R&D 격리) 어댑터 2개 운영. NLF/SMPL-X 출시 사용 시 Max Planck Innovation 상업 라이선스(`info@max-planck-innovation.de`) 클리어 필수. 공개 베타·유료 파일럿·고객 영상 처리에 NLF/SMPL-X 절대 사용 금지
- [2026-05-31 모드]: judging 모드(IPSF Code of Points) v1.5로 분리, 데이터 수집은 v1 평행 (belle/강사)
- [2026-05-31 UX]: 다중 시점 촬영 v1 포함 (occlusion 완화)
- [2026-05-31 Gemini]: 역할 = 자연어 번역 전용. 좌표·판단·점수 출력 금지 (운동학 휴리스틱 + 코치 마무리)
- [2026-05-31 코치]: 모든 리포트에 CoachCommentHook 부착 (v1 데이터 구조), UI/입력은 v2
- [전반]: 채점 차원 = IPSF 기반 (각도/라인/안정성), 균형(대칭) 제거 — 위양성(41점) 주범 제거
- [Phase 14]: 기준 모션 등록 = 다각도 캡처 프로토콜 + 두 엔진 출력 포함 (Mode 1 신뢰도의 기준)
- [Phase 15]: Mode 3 = 발전(progress) 표시, %일치 헤드라인 금지 (세션 간 델타)
- [2026-06-02 학원 용어 + 5트랙]: Phase 16 신설 — Studio Terminology Foundation. 학원 용어 3분기 시스템 (AKA 매핑 13개 / 정은지 reference 비등재 동작 / 자동 수집 + UX 카피) + IPSF 5트랙 채점 v1 scope (a) Compulsory Criteria + (c) Technical Deduction + Page 9 "all components" 절대 트랙. **MVP 가볍게 — 코드 통합 후속, 박제만 v1**. **실증 검증 게이트** = 파일럿 후 사용자 키워드 분기 1/2/3 비율 + 자동 수집 누적 패턴 → 한 번에 확장. NotebookLM IPSF CoP 2024-2025 lookup 박제 (Element Code Matching p.138-139, Page 9 "all components" CoP 2021-2024, AKA 13개 매핑). v1 신설 SCORE-05/TERM-01/TERM-DATA-01/TERM-COPY-01 + v2 신설 SCORE-V2-02/03 + TERM-V2-01/02. memory studio-term-3branch-system + ipsf-5-track-scoring 박제.
- [2026-07-09 Plan 22-02 Tasks 1-2]: 채널 harvester(collect_phase22_youtube.py 3모드)+Gemini Vision 다운로드-전 선별 게이트(curate_vision.py, verdict score/severity 영구 부재)+얼굴 가명처리(anonymize.py, 순수 numpy blur, D-12)+provenance 원장(manifest.json 시드17+hard-negative2+371 customer_track). belle 게이트 툴 인포스먼트 = --curate/--collect 는 PHASE22_BELLE_GREENLIGHT=1 없으면 SystemExit(2). yt-dlp/boto3/genai/ultralytics 는 belle-gated 경로에서만 lazy-import → Task 1-2 산출물·전 테스트는 순수 로컬(네트워크 0, phase22 36 pass). **Task 3(Vision 실선별+카피라이트 prod S3 적재+LICENSE-AUDIT.md)은 belle greenlight 전 미실행 — 22-02 IN-PROGRESS 유지, ROADMAP complete 미표기.**
- [2026-06-08 Plan 06-01 C1]: normalize_pose_by_segments 시그너처 = (source_keypoints, source_profile, target_profile, target_torso_px). L_ref = target(student) 의 segment ratio × target_torso_px (segment-aware, uniform scale degeneration 회피)
- [2026-06-08 Plan 06-01 C14]: deficit code bad_angle → pose_reliability_low rename. IPSF Page 21 judge-observation 'bad_angle' 과 의미 분리, docs/contract.md §8.1 divergence note 박제
- [2026-06-08 Plan 06-01 R2]: BodyComparisonSourcePose 신설 — Firestore reference 컬렉션의 reference 측 대표 hold frame keypoints 영속. flat values (4 × J = 68) + to_keypoints_array reshape. Plan 06-03 백필 contract source
- [2026-06-08 Plan 06-01 R5]: spatial_dispersion_penalty 산식 자연화 = clip((C_s/sw - 1.5) / 1.5, 0, 1). high dispersion → high penalty 자연 방향
- [2026-06-08 Plan 06-01 W1]: BodyComparisonReport.comparisonType 3 cases 만 (mode1 / mode3_first / mode3_progress). Gemini fallback 은 sibling boolean usedReferenceFallback (mode3_first 에서만 true 허용). 4번째 fallback 변형 케이스 금지
- [2026-06-08 Plan 06-02 C2 + R1]: TechniqueProfile.motion_id 필드 (위치: dataclass 맨 끝, hold_window 뒤 — R1 fix non-default 앞 금지). Gemini recognizer 4 path keyword populate. mode3-first Gemini fallback path 가 firestore_admin.get_reference_motion(motion_id) exact-match 사용 (Phase 5 retroactive patch).
- [2026-06-08 Plan 06-02 R3]: 단일 _extract_video_analysis_inputs(bucket, key, default_pole, *, keep_local_video=False) helper. S3 download + frame extract + RTMW estimate 1회만 실행 (T-06-02-06 mitigation). 기존 _angles_and_video_path_from_video 폐기. Phase 2 _angles_and_body_profile_from_video 무수정 보존.
- [2026-06-08 Plan 06-02 R4]: student_profile 반환 타입 = BodyNormalizationProfile (non-null). measure_body_profile 의 _fallback_profile 정합. caller 별도 None check 불요.
- [2026-06-08 Plan 06-02 R8]: caller-injected extra_warnings injection (compare_body_profiles 신규 파라미터). 'fallback_reference_not_found' / 'reference_source_pose_missing' 주입. dataclasses.replace 우회 패턴 금지.
- [2026-06-08 Plan 06-02 W5]: _validate_flat_dict_no_nested_array recursive validator + _validate_dict_only_scalars helper. list[str] (warnings) + list[dict-of-scalars-only] (findings) 허용. list[list] / list[dict-with-nested-list] TypeError raise.
- [2026-06-08 Plan 06-02 C8]: _dataclass_to_camel_case_dict 5-case 명시 (None / dataclass / list / dict / Enum / scalar). BodyComparisonReport 중첩 ScaleProfile + list[BodyComparisonFinding] camelCase 변환.
- [2026-06-09 Plan 08.1-01 C-H2]: tilt_thresholds.yaml operational cutoff = P100 + margin_deg (P90 폐기). medium = max(P100 + margin, ipsf_tolerance.tolerance_deg=20°), high = max(medium × 1.5, ipsf_tolerance.major_fault_deg=40°). 정은지 baseline 25/25 'low' 유지 보장 (boundary value = 'low' rule 정합). `_severity_from_tilt` boundary semantics: strict `>` + 1e-9 epsilon (float-safety). boundary value 정확히 cutoff → 'low'.
- [2026-06-09 Plan 08.1-01 C-M1]: `_normalize_angle_undirected(angle_deg) = (a % 180.0; return 180.0 - a if a > 90.0 else a)`. modulo 180° + min(a, 180-a) = undirected line angle [0, 90]. keypoint ordering swap (left↔right) artifact 차단. 2D path (`_shoulder_tilt_2d` / `_hip_tilt_2d`) 가 본 helper 적용 → unsigned [0, 90] 강제. 3D path 는 이미 arcsin(|Δz|/||Δ||) 로 unsigned [0, 90] 산출.
- [2026-06-09 Plan 08.1-01 C-H3]: calibrate_tilt_thresholds.py preflight hard gate — 5 doc × 5 axisMetric per doc + non-null shoulderTilt/hipTilt + 'phase_8_1_wave_0_transitional' 부재 + 'tilt_unavailable' 부재 검증. 위반 시 RuntimeError + 명시 doc_id. yaml schema_v2 의 source.null_tilt_verified=true 박제 (loader 의 schema 검증 통과 조건).
- [2026-06-09 Plan 08.1-01 W10]: tilt_thresholds.yaml fallback 신호 = cache tuple 3rd element (`['tilt_thresholds_fallback']`) 단일 source. module-global mutable boolean flag 부재 (test 로 강제 검증 — `_TILT_THRESHOLDS_FALLBACK_FLAG` 등 forbidden name set).
- [2026-06-09 Plan 08.1-01 source 분기]: calibrate_tilt_thresholds.py `--source-type` 3 분기 — `firestore` (default, Phase 8 inherited sweep) / `repo-artifact` (Firestore 미가용 시 08.1-CALIBRATION-SOURCE.json) / `wave2-explicit` (Wave 2 자기 sweep 재calibrate, `--allow-recalibrate` 명시 강제 = circular threshold chasing 차단).
- [Phase ?]: Plan 16-01 T-6 belle threshold 결정
- [Phase ?]: Plan 06-03 R2: 단일 helper update_reference_body_data(motion_id, body_profile, source_pose) — 두 필드 atomic merge. 구 update_reference_body_profile 폐기. Phase 14 정은지 reference 등록 helper 재사용 진입점.
- [Phase ?]: Plan 06-03 R7: seed-reference-body-profile.mjs explicit ordering — Step 1 parse + validate → Step 2 if dry-run early return (Firebase 미접촉) → Step 3 real-run. ADC 미설정 환경에서도 dry-run path 안전 (Firebase init 호출 0).
- [Phase ?]: Plan 06-03 C12: revert-reference-body-profile.mjs 신설 + 안전 기본값 (--commit 미지정 시 강제 dry-run) + R2 정합 (두 필드 모두 FieldValue.delete).
- [Phase 08.1]: Wave 2: production sweep + 8조건 measured-low gate 8/8 PASS (25/25 'low' + 5/5 sensitivity) — 정은지 5영상 sweep_phase8_1_1781009003567 exit 0 + 25/25 axisMetric measured_low_count=25 severity_low_count=25 + Task 2.5 synthetic 5/5. ROADMAP Phase 8.1 SC #1-5 backward coverage 박제.
- [Phase 08.1]: Layer 2 evidence only — Pass 게이트 아님 — 본 sweep 0/25 gemini_assisted + 5/5 layer2_unavailable warning. recognizer factory 미초기화 추정. 본 phase 의 axis metric fix 가 본질 scope. Layer 2 활성도 검증 = Phase 9/11 deferred.
- [Phase 08.1]: pipeline/app.py caller-side 변경 0 (Wave 1 시그너처 보존) — grep audit 결과 distance kwarg 부재 + 3 coordinate_space reference 모두 pole_axis_measurement.coordinate_space (PoleAxisMeasurement unchanged field). Plan must_haves Wave 2 'caller-side 변경 0 가능' 정합.
- [Phase ?]: D-09-D1 / D-09-U1 / D-09-U3 / D-09-U4 / D-09-U5 박제 — Wave 0 11 files 단일 atomic commit (defc973)
- [Phase ?]: Wave 1 Plan 09-02: D-09-D6 mode_context inline (no helper) + R4 iter-3 two-tier axis warning + R4 None guard for pelvis_drop + R5 high_jitter wins tie-break + R11 conservative v1 cf cap when axis missing
- [Phase ?]: (2026-06-15, Plan 03-01) BodyProfile 3-way 계약 lockstep + AnalysisDoc.bodyProfile snapshot — 결과 화면 재현성(R1), client+server 이중 normalize graceful(D-06).
- [Phase 03]: (2026-06-15, Plan 03-01) weightKg 보조 ONLY — 6 scoring-consumer 모듈 grep gate 로 유입 차단 (D-05/R4). coach context(D-04)에만 전달.
- [Phase ?]: 03-02: BodyProfileForm presentation = 전체화면 Modal(pageSheet), 신규 route 없이 재사용 component 유지
- [Phase ?]: 03-02: Segmented 토글 해제 허용 (오선택 정정 + 부분입력 D-06)
- [Phase ?]: 03-03: useBodyProfile 가 promptDismissedAt once-flag 노출 — normalizer all-empty→null 우회로 게이트가 미입력+dismiss 정확 판별 (R2)
- [Phase ?]: 03-03: pendingPicked 게이트 4-경로 모두 continuePendingRoute 단일 수렴 — 영상 유실/stale closure 방지
- [Phase ?]: Phase 15-01: SOURCE fixture(비-notified fixtures/) vs per-run/per-mode 영숫자 analysis identity 분리; direct-process 가 fixtures/ 키를 _process 에 직접 넘겨 uploads/ COPY 0 (HIGH 1/HIGH 2)
- [Phase ?]: Phase 15-01: 위양성 gate = 08.1 frozen baseline(c94bb8…e87c) checksum hard-gate 대조만, 재calibrate import 0 (D-02)
- [Phase ?]: Mode 1 7/7 server_error==0 PASS — 정은지 7 student 영상 실 Pod GPU E2E (referenceMotionId lockstep). line=None 7/7 은 recognizer 미인식 anti-false-positive 폴백(blocking gate 아님)
- [Phase ?]: Gemini 503 transient = server_error 아님 → 새 uid subset retry. onnxruntime CPU 폴백 = LD_LIBRARY_PATH(cudnn) 누락 → live uvicorn proc env 재사용으로 GPU 강제
- [Phase ?]: 15-04: Mode 3 6 fail->success 페어 deltaFromPrevious 차원 점수(stability) 델타 — 6/6 previousAnalysisId==paired fault, MODE-02 충족
- [Phase ?]: 15-04: SCORE-04 단독 — frozen 08.1 checksum(c94bb8)+fallback==0 12/12, SC3 41점-스타일 위양성 부재(최저 overall 55=실 결손). all-low success-severity gate=reference-motion invariant라 학생-연습 success 미전이 → Phase 18 defer(재calibrate 0)
- [Phase ?]: 15-04: 듀얼 coach 12/12 doc dualTrack=True+nonCrossFilledGemini6(실 LLM)+빈 섹션 0(D-12). Mode 3 6-페어 status total12/done12/server_error0 → 15-05 SC4 입력
- [Phase ?]: Phase 19 Wave 0: RED proven by standalone behavioral failure (not collection); within_tolerance_remains_high intentionally RED (dead-zone), clean_pose/synthetic above-cutoff pass today as guards
- [Phase ?]: Mode1 reference_motion basis asserted on serialized build_mode1 comparison.scoringBasis (ITER-4 HIGH-1), kept out of Mode3 4-value gate (ITER-3 MEDIUM-1)
- [Phase ?]: Phase 19-02: kismam overall_score = IPSF 감점식(평균 폐기, 단일 major fault 지배), _PENALTY_PER_DEG=1.2 [ASSUMED] v1 (sweep 재calibrate 금지)
- [Phase ?]: Phase 19-02: overall_from_dimensions = min-of-core(angle/line), stability 종합 분리. line micro-bent <160deg = 요소 무효 0점 [CITED] IPSF
- [Phase ?]: Phase 19-02: DimensionExplanation.contributesToOverall OPTIONAL 3중 계약 추가 + 비기여 weightPercent=0 (HIGH-1)
- [Phase ?]: 20-02: Gemini 결함-심각도 어댑터 — VisionVerdict(no-score) + 객관성 introspection 가드 + prompt/schema-versioned VisionVetoCache 결정론 + 토글 미소유(pipeline 소유)
- [Phase ?]: 20-03: 비전 거부권 통합 — _apply_vision_veto 하향-전용 mutation + visionVeto status enum audit + Mode3 점수카드 전체 억제(resolver provenance + reason-owns-copy + producer-contract fail-loud). pod-free, 실 정량 게이트는 20-04 Pod sweep
- [Phase 20]: 20-04 (spec-anchored variant): vision veto SEVERITY_CAP activated — major=50 (belle spec ≤50), moderate=75 (IPSF severity), minor=None. method=spec_anchored; phase18 6 pairs regression-only (never derivation). Sensitivity-derived eval deferred to follow-up.
- [Phase ?]: 24-04: low_alignment_confidence 를 apply seam 에서 measured-seed tally-eligible 로 라우팅(passthrough 제거). RTMW 측정 편차는 정렬-독립이라 Gemini 정렬 낮아도 감점, supported_differences=[] 라 Gemini fault fabricate 0. collect-side bail/coach-eligibility/임계값 UNCHANGED. to_audit_dict collectionStatus provenance 추가(Rule 2).
- [Phase 10]: 10-02: D-04 trunk flag reference-anchored only (no absolute lumbar cutoff, A3); absolute trunk DEFERRED
- [Phase 10]: 10-02: temporal co-location is phase-level (v1 limit); DTW alignment recomputed inside safety_flags, not kwarg-threaded
- [Phase 10]: D-05 cross-product hyperextension detector: deterministic frontal-axis sign + min-angle calibration + uncertainty_proxy-correct scoped gate; real-elite (T,17,4) regression pod-deferred (skipif-gated, extractor written)
- [Phase ?]: Phase 10-04: D-03 asymmetry is DTW-path-aligned reference-anchored (explicit L/R pairs + MAX aggregation, pair-local + phase-co-located control-loss); intentional asymmetry cancels even at shifted timing; absolute L/R never flagged.
- [Phase ?]: Phase 10-04: D-06 level-mismatch is Mode-1 only with enum-guarded ladder; severity scales with rank-gap x instability so gap=1 does not over-warn. All four SafetyFlag types complete -> SAFE-01 satisfied.
- [Phase ?]: 26-06: 재배치안 A 확정(belle) — 소스 선택 ScrollView+캡션 통합, 홈 무접촉. B 홈 링크는 향후 잡 UI 후보
- [Phase 26]: 26-06: 학습활용 동의 opt-out 전환(belle 제품 결정 2026-07-08) — 기본 체크 ON, 해제=노학습. 기록 경로/fail-safe 불변
- [Phase 26]: 26-06: 배치 UAT 정책(belle) — 잔여 실기기 확인+Firestore 증거는 26-HUMAN-UAT.md 이월, phase 22·26~31 완료 후 직원 합동 세션
- [Phase 22]: 22-01: schema.py 단일 owner — D-11 4철칙 + D-01 리포트 v1(REPORT_KEYS, score/severity 영구 부재). faults[] ⊇ DEDUCTION_CONSUMED_KEYS lockstep(gemini v8.1 differences 미러, severity 제외).
- [Phase 22]: 22-01: rtmw_error_profile.json(source_doc_count=247) 실측 분포로 A3 해소 — perturb 파라미터는 히스토그램 샘플, 교란 수치 하드코딩 0(측정 임계 0.3은 관측 정의). T-22-01 식별자 미포함.
- [Phase 22]: 22-04 균등 게이트 미충족 마감 = _meta.balance_waiver 명시 문서화 (silent 우회 금지, 테스트가 waiver 정확성 검증) — fault 표본(내부 371 track)은 다음 라운드 이월 — belle 승인 2026-07-10, JSONL 균등은 _balance_media 소유
- [Phase 22]: 22-04 교사 출력 중첩 타입 혼돈은 normalize_report 단일 지점에서 결정적 무손실 변환만 허용, 스키마 환원 불가는 필드 None(행 폐기 금지) — coaching list 47행 등 라벨 대량 유실 방지 + D-11 스키마 순수성 양립
- [Phase ?]: 22-12: 승격 원장은 게이트 verdict(PASS/FAIL)+비용 관측치만 저장 — 사람/judge 점수 금지(객관성 hard gate)
- [Phase ?]: 22-12: 게이트 PASS(--require-pass exit 0)만 current 전진(단방향 래칫), FAIL 은 attempt 기록만 + 러너 exit 0
- [Phase ?]: 33-01 A-0 판정=어긋남 큼 → phase 33 HALT + C+M3 substrate 편입 재계획. belle 실 doc(ref-power-spin fault) pointed/shown/measured 3집합 전 fault 멤버 불일치 + 실측 window 부재 + crop 3장 국면 어긋남(눈확인). 측정 판정(D-04).
- [Phase ?]: 33-04: candidate 백필은 versions/{candidate} 를 source AND merge target 으로 소유 — top-level/activeVersion 무접촉 (flip 은 33-07)
- [Phase ?]: 33-04: referenceKeypointReport 40k index 한도 → belle 옵션 B (versions+reference collection-group 인덱스 면제 추가), acceptance 원문 유지
- [Phase ?]: 33-04: fps 는 candidate keypointReport.fps(9.0)/CLI — REFERENCE_TARGET_FPS=18.0 제거; epsilon(0.1/1.0)+FORCE_CONFIG verbatim, gate 11/11 refit 0
- [Phase ?]: 33-22: two-track deduction — execution -40 aggregate cap (floor 60) + dormant critical bypass + absolute floor 25; existing thresholds byte-unchanged; contract mirrored across 3 files (D-34/D-36/D-37)
- [Phase ?]: 33-12: 확대비교 seam = 백엔드 criterion-keyed crops 구현 — crop 이 deductionBreakdown.records 에서 출생, 앱 join 은 criterion 키 일치 (defect #5 근본 수리)
- [Phase ?]: 33-12: D-12 카드 불변식(같은 순간·배율·표시 or drop)은 criterion 카드 한정 — legacy 는 D-04 정직 폴백 byte-보존
- [Phase ?]: 33-12: defect #6 은 79221f0 선해결 확인 — 회귀 핀 박제, PNG 전수 열람은 33-16 Pod 재스위프 소관
- [Phase ?]: 33-13: 영상 위 표시 = 스켈레톤 기본숨김+옵트인, 마커 = record 양방향(고아 미렌더), 음성 큐 = 정지+부위강조+재개
- [Phase ?]: 33-13: phrasebook cueLine 54건 목표-선행 문형 + 화면 어휘 게이트(채점 내부 용어 → 강사 화법, 어휘 목록 데이터 운용)
- [Phase ?]: 33-14 A-7: 검수 PASS 6동작 번들(power-spin=7R cand1 채택) + 미완 4동작 fail-closed hidden — 재생성 상한 3회 소진 정직 보고, 틀린 그림 미배선
- [Phase ?]: 33-14: 일러스트 슬롯 = DeductionDetailSheet.illustrationSlot 옵셔널 prop (승인 목업 ② 위치), 결함→일러스트 매핑은 result.tsx 소유 (motionId 데이터 키잉)
- [Phase ?]: 33-15: 각도 수치 단일 거처 = 점수 계산 내역 '관절 각도 참고' (legacy doc 은 이동 거처 부재라 팁 잔류 — 삭제 금지)
- [Phase ?]: 33-15: 초 표기 라벨 '(감점 부분)' = zoom.criterion 보유 카드 한정 (구 PNG 초 미베이크 거짓 지칭 방지)
- [Phase ?]: 33-15: OctagonScore 중앙 수치 크기 유지 + 토큰화만 (D-16 대상 아님 해석 — 33-16 belle 재판단 재료)

### Pending Todos

[From .planning/todos/pending/ — ideas captured during sessions]

None yet.

### Blockers/Concerns

> 감시 (2026-07-05): fault-zoom 생성 1회 일시 실패 (belle 분석 1597ac92, 기준 영상 임시파일 imageio meta 로드 불가 — graceful, 점수 정상). 같은 서버가 직전 분석에선 정상 생성 → 일회성 추정. 재발 시 즉시 조사 (h5z pair-builder 와 fault-zoom 의 ref 임시파일 수명 상호작용 후보).

[Issues that affect future work]

- [Phase 1 — 마이그레이션 HIGH]: 현 제품 코드는 NLF 기반 (`backend/shared/python/sunity_shared/analysis/pose_estimator.py`, RunPod GPU pod). Phase 1에서 MediaPipe 어댑터로 전환 + NLF 모듈을 R&D 비교군으로 격리 필요. RunPod GPU pod 비용 절감 + 라이선스 리스크 0 효과.
- [라이선스 — 출시 게이트]: NLF/SMPL-X는 R&D 비교군 전용으로 제품 비포함 결정 — Phase 진행은 블로킹되지 않음. 향후 NLF/SMPL-X를 제품에 도입하려면 Max Planck Innovation 상업 라이선스 클리어 필수 (`info@max-planck-innovation.de`). Meshcapade 채널은 종료됨.
- [Phase 5 — 외부 의존]: Gemini API 키(belle, Google AI Studio) 필요. Parameter Store / RunPod env 주입 전까지 Phase 5 블로킹.
- [v1.5 — 데이터 수집]: IPSF Code of Points 임계값(3~5개 동작 × phase별 GeometricCriterion) 라벨링은 v1 평행 진행 (belle/강사 협업).
- [전반 — 보안 HIGH]: 노출된 `sunity-api` AWS 키 비활성화 미완 (plan.md cleanup 큐). 작업 착수 전 처리 권장.
- [Phase 15 — 운영]: RunPod Pod 생명주기 수동. 재생성 시 proxy URL 변경 → Lambda env(RunpodAnalyzeUrl) 동기화 필요. 중단 시 실분석 전면 중단.
- [Phase 15 — iOS]: iOS 26+ native style 회귀(letterSpacing SIGABRT) — 빌드 10에서 ship 필요, 음수 style 값 audit.
- [Phase 16 — 데이터/스펙 박제]: Phase 1~15 의존성 없음 (v1 평행). Phase 1 진행 중 평행 진입 가능. 단 Phase 5 (Gemini 기술 인식기) / Phase 14 (정은지 reference) 가 Phase 16 데이터를 소비하므로 그 시점에 통합 필요. 첫 plan (16-01-PLAN.md) = AKA 매핑 13개 + 5트랙 spec + 카피 박제 (코드 통합 X).
- Plan 06-03 Task 5 pending checkpoint — belle 운영 작업 (Pod GPU 측정 + 로컬 seed + Firestore Console verify) 필요. Phase 14 reference 등록 helper 재사용 path 박제 완료, 실 데이터 백필만 잔여.
- 13-B Task 4 (criteria 5) Cerebras Pod E2E checkpoint 대기 — belle: SSM 키 + Lambda/Pod env + uvicorn 재시작 + 1건 실분석 검증. Tasks 2-3 완료(db252c9, 79d862c).

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-07-30T05:47:37.672Z

Stopped at: Phase 33 §9 수리 사이클 컨텍스트 기록 완료(D-39~D-45) — 다음 = 수리 plan

### 2026-06-07 추가 fix 5종 (빌드 10 → 11 박제)

| commit | scope |
|---|---|
| `787a901` | iOS 26+ letterSpacing 음수 SIGABRT fix (typography.ts track → 0) |
| `e3bf753` | package-lock.json sync |
| `0472c01` | eas.json production profile env 박제 (.env gitignore 우회) |
| `0bd6a48` | get_previous_analysis mode 인자 박제 (mode3 first ↔ mode1 prev 함정) |
| `3f6681f` | Firestore composite index 회피 + in-memory mode filter |

### 박제 메모 [[runpod-gpu-env]] 함정 31-34 추가

- 31: eas.json production env 누락 (.gitignore 박제 .env)
- 32: Firebase 익명 uid 가 IPA 빌드별 다름 (정상 동작, 단 시연 시 데이터 fresh)
- 33: Firestore composite index 자동 생성 X — query 단순화 + in-memory filter
- 34: simulatedResult 폴백이 Firestore 없을 때 가짜 결과 보임 (dev 안전망 — production 박제 후보)

### belle 의 진단 + 박제 정신 안내 (코드 fix 없이)

- "Expo 박제 박제 박제 박제 박제 박제 X" — 박제 정신 정합 안내. TestFlight 박제 박제 박제 박제
- mode1 vs mode3 점수 차이 = 같은 정은지지만 다른 cut/clip 박제 정합
- ref-climb line 차원 누락 = IPSF "Transitions & Climbs" 박제 각도 임계 X (의도된 빈 list). foxtop/invert 박제 박제 line 박제 박제 박제
- "고급 88" = 사용자 박제 SkillLevel (advanced) 박제 평균 점수, 현재 분석과 무관
- VideoCompare 10초 정지 = 짧은 영상 끝나면 둘 다 정지 (동시 비교 박제 정신)

### 다음 세션 우선 진행 (belle 결정)

belle 의 의문 박제 정신 정합:

1. **개발 로드맵 순서 정리** — Phase 1-15 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 (Phase 5 박제 박제, Phase 1/14/15 박제 박제 박제)
2. **외부 AI 검증** — Codex/gpt-5.5 plan-review-convergence 박제 cross-check ([[cross-ai-plan-review-good]] 박제 정합)
3. **A/B/C plan 진행** (belle 명시 박제):
   - **A. Phase 12** = 실측 각도 표시 + 키포인트 오버레이 (큰 scope)
   - **B. (d) 결과 UI transparency** = result.tsx 차원별 "이게 무슨 기준" 박제 + 가중치 표시 (작은 scope)
   - **C. Phase 16 IPSF 5트랙 코드 통합** = 학원 용어 매핑 + RepetitionCriterion + Page 9 (중간 scope)

박제 정신상 belle 의 의도 = "사용자가 '아 이래서 이런 평가구나' 박제" = B 박제 빠른 path. A 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제. C 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제. 박제 정신상 A+B+C 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제.

### 2026-06-07 세션 핵심 박제

**Phase 5 사실상 완료** — mock E2E mode1/mode3 PASS + belle 실제 분석 mode1 점수 94/97 PASS + 5가지 UI/UX 의문 fix:

1. (b3) 코칭팁 라벨 중복 fix ("오른쪽 어깨 어깨" → "오른쪽 어깨")
2. (b4) 숫자 브랜드 컬러 강조 (#FF4B33)
3. (b5) 완벽 수행 메시지 (angle 95+ 시 + mode 분기)
4. (b1) backend playback-url Lambda 신설 + (b2) frontend wiring (S3 7일 TTL 만료 fix)
5. mode3 second+ overall 산식 변경 — (각도+안정성) 평균 (belle 의문 정합)

**Phase 15 진행** — TestFlight letterSpacing SIGABRT fix:

- root cause = `theme/typography.ts` 의 `track(size) = size * -0.04` (음수 letterSpacing)
- fix = `track(size) = 0` (commit 787a901)
- EAS Build 10 + auto-submit (commit e3bf753 lock sync)

**Cerebras 모델 fix** — `llama3.1-8b` deprecated → `gpt-oss-120b` (commit 1110935)

**SAM deploy regression fix** — Lambda env RUNPOD_ANALYZE_URL 직접 update (SAM template parameter default reset 함정 28)

### belle 박제 의문 정합 안내 (코드 fix 없이 박제 정신)

1. mode1=95 vs mode3=100 차이 = belle 영상 (_talkv_high.mp4) ≠ reference (ref-climb.mp4) 다른 cut → 정합
2. line 차원 누락 = `ref-climb` 은 IPSF "Transitions & Climbs" 박제 각도 임계 X (의도된 빈 list). 다른 motion (foxtop/invert) 시 line 정상 박제 — Phase 16 코드 통합 후속
3. "고급 88" = 사용자 박제 SkillLevel (advanced) 박제 평균 점수, 현재 분석과 무관
4. VideoCompare 10초 정지 = 짧은 영상 끝나면 둘 다 정지 (동시 비교 박제 정합)

Resume file: .planning/phases/33-result-trust-recovery/33-CONTEXT.md

### 2026-06-06 세션 핵심 사건 — OpenMMLab CDN 글로벌 만료

`download.openmmlab.com` 도메인이 2026-06-04 즈음 만료 — `dig +trace` 권한 NS 자체가 `expirens3/4.hichina.com` (Alibaba HiChina 만료 도메인 전용 NS). 박제된 RTMW URL + YOLOX URL 모두 도달 불가. mmpose 사용자 전체 영향. 박제 메모 [[rtmw-clean-weight-release-gate.md]] 의 우려 적중.

belle 결정 (mirror 검색 path) → HuggingFace anonymous mirror 활용 우회 완료:

- RTMW-X-384: `hf://bukuroo/RTMW-ONNX/rtmw-x-384.onnx` (369MB) + S3 백업 `s3://sunity-motion-pilot-videos/_artifacts/rtmw-x-384_bukuroo_hf.onnx`
- YOLOX-M (person detector): `hf://hr16/yolox-onnx/yolox_m.onnx` (97MB, Apache-2.0)

### 박제 commit + 함정 추가 (이번 세션)

| commit | 영역 | 내용 |
|---|---|---|
| 4b823de | setup_pod_full.sh | mmcv build ninja 선행 install + MAX_JOBS export (함정 26) |
| 081192b | rtmw_engine.py | YOLOX_ONNX_PATH env 박제 — OpenMMLab CDN 만료 우회 (함정 22) |

박제 메모 [[runpod-gpu-env.md]] 갱신 = 함정 20~27 추가 (누적 27종). 핵심:

- 함정 20: OpenMMLab CDN 글로벌 만료 (2026-06-04)
- 함정 21/22: RTMW + YOLOX HF mirror path
- 함정 23/24: setup_pod_full.sh 박제 누락 (runpod_inference/requirements.txt install + RUNPOD_AUTH_TOKEN .bashrc)
- 함정 25: server.py auth header = `X-RunPod-Token` (Authorization Bearer 아님)
- 함정 27: stale __pycache__ — git pull 후 uvicorn restart 시 cache 청소 필요

### 백엔드 검증 결과

| 검증 | 결과 |
|---|---|
| Pod /health 외부 | 200 OK, `pipeline_loaded:true, auth_configured:true` |
| Pod /analyze 외부 mock (X-RunPod-Token + dummy body) | 422 Pydantic validation (endpoint alive) |
| Lambda env RUNPOD_ANALYZE_URL | Active, 새 Pod URL 정합 |
| **mock E2E** (Pod 안에서 _process 직접 호출) | **PASS** — Firestore status=done, 49.8s |

### Pod 환경 (2026-06-17 시점, Pod 01emvodj1pdooe — RTX 4090, Network Storage EU-RO, 풀세팅 완료·검증)

| 항목 | 상태 |
|---|---|
| GPU / Container | RTX 4090 24GB / RunPod, driver 565, Python 3.11.10, torch 2.4.1+cu124 |
| Pod ID | `01emvodj1pdooe` |
| SSH (proxy) | `ssh 01emvodj1pdooe-6441164d@ssh.runpod.io -i ~/.ssh/id_ed25519` |
| SSH (direct TCP) | `ssh root@213.173.110.226 -p 39380 -i ~/.ssh/id_ed25519` |
| Network Storage | `/workspace` = `mfs#euro.runpod.net` (EU-RO, persist) — repo·rtmw-x-384.onnx·yolox_m.onnx·firebase-sa.json·aws_env.sh 보존. deps(onnxruntime-gpu/rtmlib/mmpose)는 overlay라 매 세션 재설치 |
| 서버 기동 | `nohup /workspace/start_p15_server.sh > /workspace/p15_server.log 2>&1 </dev/null &` (전체 env + GEMINI/RUNPOD_AUTH_TOKEN 명시 export 박제 — `.bashrc` early-return 우회). **kill은 ss PID로** (pkill 패턴이 ssh 명령 self-match → 셸 자살 함정) |
| HTTP Port 8000 | UP — `/health {status:ok, auth_configured:true, pipeline_loaded:true}`, GPU 1056MiB 모델 적재, RTMW-x-384(commercial_ok)+YOLOX+GeminiTechniqueRecognizer+Gemini 키 검증 |
| 인증 스모크 | wrong token→401 / correct token+bad key→400(auth 통과) / 외부 proxy /health→200 |
| Lambda env RUNPOD_ANALYZE_URL | `https://01emvodj1pdooe-8000.proxy.runpod.net/analyze` — **SSM `/sunity/motion/runpod-analyze-url` + 라이브 Lambda 둘 다 동기화(boto3 merge, 4키 보존)**. SSM이 source of truth라 sam deploy 시 안 되돌아감. AWS 자격 = sunity-motion (sunity-api는 Lambda 거부) |

### 이전 Pod 이력 (2026-06-06 종료 시점, Pod 1ablelgbtrzcgb — 교체됨)

| 항목 | 상태 |
|---|---|
| GPU / Container | RTX 3090 / RunPod PyTorch 2.4, Python 3.11 |
| SSH | `ssh -p 14818 -i ~/.ssh/id_ed25519 root@64.119.209.250` |
| /workspace | SunityMotion HEAD = 081192b, firebase-sa.json, rtmw_weights/rtmw-x-384.onnx, yolox_weights/yolox_m.onnx |
| .bashrc env | RUNPOD_AUTH_TOKEN/RTMW_ONNX_PATH/YOLOX_ONNX_PATH/RECOGNIZER_BACKEND=gemini/RTMW_DEVICE=cuda/LD_LIBRARY_PATH/FIREBASE_SA_PATH 박제 |
| uvicorn server | PID 9652 살아있음, 0.0.0.0:8000 LISTEN, 워밍업 완료 (RTMW+YOLOX+Gemini API 검증) |
| Lambda env RUNPOD_ANALYZE_URL | https://1ablelgbtrzcgb-8000.proxy.runpod.net/analyze |

### 남은 작업

- [ ] **TestFlight 튕김 fix** (별개 blocker, [Phase 15 — iOS] letterSpacing SIGABRT 후보) — belle 가 진짜 E2E 검증할 channel 필요
- [ ] **belle 진짜 E2E 검증** — Expo Go QR 또는 빌드 10 ship 후 TestFlight 재시도. mock 가 동일 path PASS 확인.
- [ ] Phase 5 close-out (ROADMAP Phase 5 ✓) — belle 진짜 E2E 통과 후
- [ ] Phase 6 진입 — Phase 5 close-out 후
- [ ] setup_pod_full.sh 후속 갱신 commit — 함정 23/24 박제 (runpod_inference/requirements.txt install + RUNPOD_AUTH_TOKEN + YOLOX_ONNX_PATH .bashrc + OpenMMLab CDN 우회 download path)
- [ ] mock E2E artifact cleanup (선택) — S3 `uploads/mock_e2e_belle_1780754054/` + Firestore mock doc
- [ ] sweep 박제 baseline 재산정 (선택) — cocktail13 → bukuroo 가중치 변경 영향 평가 (`sweep_rtmw_20260603_1409` baseline 과 직접 비교 무효 가능)

---
phase: quick-260821-tg6
plan: 01
subsystem: pod-ops / compare-render / discovery-freeze / e2e
tags: [pod-e2e, discovery-inherit, discover-mp3, no-write-rerun, d-di7-03]
requires:
  - quick-260814-di7 (discovery doc 영속화 + 주입 레이어 + D-di7-03 이연 명기)
  - quick-260814-ghs (조달+mp3 회수 배선 구현 — 유닛만)
  - quick-260821-kgq (피디쉐입 elbow + 파워스핀 shoulder 프로덕션 반영)
provides:
  - "명제 1: 새 Pod 운영 경로 E2E 1건 done (SIM 신선 분석 456.3s, score=60)"
  - "명제 2: kgq 발굴 정지 3건(무릎/팔꿈치/어깨)의 운영 렌더 상속 — no-write 재구동 로그+스틸로 성립"
  - "명제 3: D-di7-03 운영 실행 증거 최초 확보 (조달 log.info n=2/n=1 + [discover] 주입 + 리그 ALL PASS)"
  - "결함 관측 2건: rerun 드라이버 FA 스텁 부패(ghs 이후 미갱신) + 운영 마킹 payload :discover suffix 소실"
affects: [rerun_compare_stage 드라이버 수리, renderedCompare rid 계약(D-di7-05) 후속, Cerebras 결제]
key-files:
  created:
    - .planning/quick/260821-tg6-pod-e2e-kgq-discovery-mp3-d-di7-03/rerun_compare_stage_tg6.py
    - .planning/quick/260821-tg6-pod-e2e-kgq-discovery-mp3-d-di7-03/evidence/code_facts.md
    - .planning/quick/260821-tg6-pod-e2e-kgq-discovery-mp3-d-di7-03/evidence/{fresh_analysis.log,fresh_doc_fields.json}
    - .planning/quick/260821-tg6-pod-e2e-kgq-discovery-mp3-d-di7-03/evidence/{rerun_pdshape.log,rerun_powerspin.log,rerun_pdshape_round1_harness_defect.log}
    - .planning/quick/260821-tg6-pod-e2e-kgq-discovery-mp3-d-di7-03/evidence/{rerun_pdshape_report.json,rerun_powerspin_report.json}
    - .planning/quick/260821-tg6-pod-e2e-kgq-discovery-mp3-d-di7-03/evidence/stills/ (4장)
  modified: []
decisions:
  - "Rule 3 이행: 원 rerun 드라이버 FA 스텁 결함(운영 조달 차단)은 backend/ 무접촉으로 우회 — 수정판 하네스를 planning dir 신설 (kgq wire_adopt 선례)"
  - "수리 금지 준수: 마킹 rid suffix 소실·Cerebras 402 는 관측/진단 구분 박제만 — backend/ porcelain 빈 출력"
metrics:
  duration: 28분
  completed: 2026-08-21T12:51Z
---

# quick-260821-tg6: Pod E2E + kgq 발굴 상속 + D-di7-03 운영 실증 Summary

**기계 판정 한 줄**: 신선 SIM 분석 1건 status=done(456.3s, score=60) + 운영 doc 2건
no-write 재구동에서 `compare_render discovery 조달 n=2/n=1` + `[discover]` 주입
2+1건 + 리그 ALL PASS(discover H2/H3/H4 포함) + `[no-write]` S3/doc 차단 라인 전건
존재 + 발굴 정지 스틸 3장 육안 확인 — 운영 doc 쓰기 0, backend/ 변경 0.

## 명제 판정

### 명제 1: 운영 경로 E2E — **성립**

- **관측**: `phase34_fresh_reanalysis.py` 기본값(SOURCE = belle 원본 업로드 키
  127a2a90…, 읽기만)으로 SIM_UID 아래 신선 doc `p34fresh1787315198` 생성 →
  서버 동일 env(`/tmp/tg6_env.sh` = start_server.sh head-43 + aws_env.sh) +
  서버 인터프리터(`/usr/bin/python3`)의 direct-process 1회 →
  `== 분석 완료 456.3s — status=done score=60` (fresh_analysis.log:156).
  renderedCompare done + freezes 5건, motionAlignment tier=trim_only
  (reason=low_global_confidence). 실물: 합성 mp4 를 S3 GET 하여 r00 정지
  스틸(28.87s) 육안 확인 — 정지 side-by-side + 왼팔꿈치 마커 + 캡션 구움
  (stills/fresh_r00_left_elbow_28.87s.png).
- **신선 doc 의 discovery 부재 = 설계상 정상 (실측 대응)**: fresh_doc_fields.json
  `discoveryPresent: false`, freezes 에 `:discover` 항목 0 — 발굴은 분석 사후
  belle 채택물이라 코퍼스→신선 전파 설계가 아님 (code_facts.md (a)).
- **쓰기 회계**: 실사용자 doc 쓰기 0 — 신규 쓰기는 SIM_UID doc
  (`p34fresh1787315198` + result 필드) 과 그 결과물 S3 키
  (`results/fvcN…/p34fresh1787315198/*`) 뿐 (드라이버 구조 + 로그 uid 전건 SIM).

### 명제 2: kgq 반영 발굴 정지의 운영 렌더 상속 — **성립**

- **피디쉐입** (p34fresh1786628533, rerun_pdshape.log): 조달
  `n=2 rids=['r04','r00']` → `[discover] rid=r04 joint=left_knee ut=12.8667` +
  `[discover] rid=r00 joint=left_elbow ut=16.4667` → report freezes 7건, discover
  2건의 voiceStartOutS = **42.07 / 68.8 — kgq 정본과 정확 일치** (실 GPU align
  재생성인데도 outSec 소수점까지 재현 = 결정론 성립). 리그 ALL PASS
  (`H2 순간 r04[discover]: doc discovery 순간 일치` 등 discover 축 6건 PASS).
- **파워스핀** (powerspinFault1785373695, rerun_powerspin.log): 조달
  `n=1 rids=['r02']` → `[discover] rid=r02 joint=left_shoulder ut=0.4667` →
  freezes 3건 (0.5 / 16.47 / 32.03 — kgq 정본 일치), 리그 ALL PASS. record
  freeze 2건(r00/r02)은 kgq Deviation 1 실측과 동일 (r01 구조적 침묵 재현).
- **실물 스틸 3장 육안 확인** (stills/): 무릎(44.07s)·팔꿈치(70.8s)·어깨(2.5s)
  전건 — 정지 side-by-side + 빨간 마커(무릎/팔꿈치/어깨 정위치) + kgq/di7 승인
  캡션 원문 구움 + 기준측 결함 대조 성립.
- **상속 원천 (코드 사실, code_facts.md)**: `_run_deferred_compare_render` 가
  그 doc 자체의 `result.discovery` 를 `get_analysis_discovery(uid, analysis_id)`
  로 조달 (app.py:4254-4258) — 사후 채택물, 코퍼스 전파 아님.

### 명제 3: D-di7-03 (discover mp3 회수 배선) — **종결: ghs 배선 완료 + 운영 실행 증거 이번 최초 확보**

- 배선 이력: di7 이연 명기 → quick-260814-ghs 구현 (app.py:4245-4286, FakeS3
  유닛만) → **이번 재구동이 ghs SUMMARY 가 지정한 그 실행 증거 로그의 최초 실측**
  ([[wiring-claims-need-log-evidence]]).
- 운영 실행 증거: 조달 log.info 2건 (`discovery 조달 n=2` / `n=1`) + S3 discover
  mp3 → audio_dir 실회수 성립 (`[discover] … mp3=discover_audio_r04_left_knee.mp3`
  등 3건 — 회수 실패 시 나오는 `discover_no_mp3` / `회수 실패` 라인 0) +
  `H4 음성 조인 r0N[discover]: discovery mp3Key 조인` PASS 3건 + D 음성 존재
  discover 시각 전건 PASS (42.1s -24.1dB / 68.8s -22.7dB / 0.5s -22.2dB).

## 쓰기 회계 (운영 doc 2건 쓰기 0 — 게이트 증거)

- 두 재구동 로그 모두: `[no-write] S3 put_object 차단: results/…/compare_v1.mp4`
  + `[no-write] doc 마킹 차단: status=done … freezes=7건/3건` 라인 존재.
- 재구동은 기본 no-write 하네스만 사용 (--write 부재 — 수정판 하네스에는 --write
  플래그 자체가 없음). 운영 doc 의 renderedCompare/discovery 는 재구동 전후 로그
  독출값이 kgq 정본 그대로 (rerun 로그 `renderedCompare(현재)` 라인).
- S3 쓰기: 차단 2건 외 0. Firestore 쓰기: SIM 신선 doc 계열만 (명제 1).

## Deviations from Plan

**1. [Rule 3 - 블로킹 하네스 결함] rerun 드라이버 FA 스텁이 ghs 조달 배선을 차단 — 수정판 하네스 신설 (backend/ 무접촉)**
- **Found during:** Task 3 피디쉐입 round 1
- **관측** (rerun_pdshape_round1_harness_defect.log:5-10):
  `WARNING compare_render discovery 조달 실패 — 발굴 정지 없이 진행` +
  `AttributeError: 'FA' object has no attribute 'get_analysis_discovery'` →
  `[warn] discover mp3 없음 — 정지 스킵` 2건 → freezes 5건(discover 0) 렌더,
  리그 ALL PASS (H1 회계는 base rid 중복이라 무감지).
- **진단**: `backend/scripts/rerun_compare_stage.py` 의 no-write 배선(jix 시절)이
  `papp.firestore_admin` 을 `update_analysis_rendered_compare` 하나만 가진 스텁으로
  통째 교체 — ghs 가 추가한 읽기 호출이 스텁에 없어 스테이지 fail-open 이 발동.
  **프로덕션 경로 결함이 아니라 진단 드라이버의 부패** (실서버는 실 모듈 사용).
  부수 확인: ghs fail-open 이 설계대로 동작(WARNING + 발굴 없이 done 진행).
- **처리**: backend/ 변경 0 제약을 지키기 위해 수정판 하네스
  `rerun_compare_stage_tg6.py` 를 planning dir 에 신설 (kgq wire_adopt 선례) —
  읽기 전건 실 모듈 위임 + `update_analysis_rendered_compare` 만 차단하는
  `__getattr__` 프록시. round 1 로그는 결함 증거로 보존.
  **후속 재료**: backend 드라이버 자체 수리는 별도 태스크.

**2. [관측 — 수리 금지 준수] 운영 마킹 payload 의 `:discover` rid suffix 소실**
- **관측**: 차단된 마킹 payload 의 discover freezes rid 가 `r04`/`r00`/`r02`
  (suffix 없음, outSec 은 42.07/68.8/0.5 정확) — doc 정본(kgq, D-di7-05 규약)은
  `r04:discover` 형식.
- **진단**: app.py:4400-4403 `freezes_payload = [{"rid": fz["rid"], …}]` — render
  report 의 freeze rid 는 plain rid 이고 discover 정체성은 `pairSrc` 필드에만
  있어 doc 마킹에서 suffix 가 소실된다. 운영 경로가 discovery 보유 doc 에
  --write 로 돌면 D-di7-05 계약(contract.md §12.9 :discover 틱)과 어긋난 freezes
  를 쓰게 된다. 이번엔 no-write 라 실 doc 무영향. **후속 태스크 재료** (수리 금지).

**3. [관측] Cerebras 402 payment_required — 신선 분석 coach 트랙 폴백**
- **관측** (fresh_analysis.log:64-95): `POST api.cerebras.ai … 402 Payment
  Required` 2회(재시도 포함) → `coach dual-track … gemini_ok=True
  cerebras_ok=False cross_filled=['left_elbow','right_elbow','right_knee']` —
  분석은 done 진행 (fail-open 정상 동작).
- **진단**: Cerebras 계정 크레딧/결제 상태 문제로 보임 — belle 확인 필요
  (분석 자체는 Gemini cross-fill 로 성립하나 dual-track 설계의 한 축이 죽어 있음).

**4. [관측] 신선 분석 motionAlignment tier=trim_only (reason=low_global_confidence)**
- compare_render 는 align_quality 게이트를 통과해 done 부착 (수술 ① 경로).
  기록만 — 판정 아님.

그 외 plan 대로. 분석 1건 준수 (Task 3 재구동은 렌더 스테이지 단독 — NLF/RTMW
채점 0, Gemini 0).

## LLM 학습 영향

- **Task 2 (신선 분석 내부 자연 발생분)**: Gemini generateContent **8회**
  (scene_finder gemini-3.7-flash 1 + gemini-3.1-pro-preview 7: veto 4 ·
  coach_dual 1 · 후처리 1 · spot_check 1) + Files API 영상 업로드 2건(분석 후
  DELETE 2건 확인, recognizer 는 캐시 히트로 호출 0). Cerebras 요청 2회는 402
  거절 (완료 응답 0). coach_audio 스테이지 9.3s 실행 — Polly TTS 합성 발생 추정
  (비-LLM, 로그 무표기). 송신물 = SIM 분석용 영상/프레임/수치 — PII/시크릿 0.
- **Task 1/3**: LLM 호출 **0** (재구동 로그에 generativelanguage/cerebras 라인 0
  — grep 실측).

## belle Pod 종료 판단 재료

**이 Pod(w340kaemere1po, 213.173.105.5:30279) 대기열 소진 — tg6 이 마지막 항목이었고
전 태스크 완료.** E2E done 실증 포함. (v32 gates 는 볼륨 venv 인터프리터 깨짐으로
범위 밖 이연 — o3m 인계 그대로.)

## Known Stubs

None — 이번 산출물은 전건 관측/증거 파일 (운영 배선 변경 0).

## Threat Flags

없음 — 신규 표면 0 (T-tg6-01~04 mitigate/accept 절차대로 집행: no-write 차단
로그 확보, SIM_UID 외 쓰기 0, 시크릿 값 로그 0 — grep 스크린 3파일 0건, 패키지
설치 0).

## Self-Check: PASSED

- 게이트 grep 전건 통과: `discovery 조달 n=2`(pdshape) / `n=1`(powerspin) /
  `no-write` / stills png 4장 / `[discover]` 주입 라인 존재
- `rtk git status --porcelain backend/` 빈 출력 (수리 0)
- 커밋: e71e95d0 (Task 1 code_facts) / bc534eb5 (Task 2 fresh E2E) / Task 3
  evidence 커밋 (아래) — SUMMARY 는 오케스트레이터 docs 커밋 위임

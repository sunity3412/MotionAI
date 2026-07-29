# 33-A4-FIX-NOTE — recognizer 캐시 히트 경로 hold_window 소실 수리

- 근거 문서: `33-A4-PHASE-EVIDENCE.md` §5 (끊긴 지점 1)
- 작업 성격: A/B 결정에 따른 A 트랙 삽입 quick fix (넘버드 플랜 아님 — SUMMARY 없음)
- 커밋: `b5cce33` (fix) + `69b03cb` (test), 브랜치 `worktree-agent-ac067349411b72f27`

---

## 1. 결함 요약

yaml `hold_moment:` 스코프(감점을 "완성 국면에서 잰다")를 시간축에 구현하는 유일한
장치는 `TechniqueProfile.hold_window`다. 신선 경로(`_build_profile`)는 Gemini
KeyMoments[hold] timestamp 로 이 창을 계산하지만, 캐시 히트 경로
(`gemini_technique_recognizer.py::_profile_from_cache`)는 `hold_window=` 를
복원하지 않았다(필드 자체 부재). 결과:

- 캐시 히트 시 `dimensions._select_window` 가 **국면 무관 분산 최소 자동 창**으로 폴백.
- 같은 영상이라도 캐시 히트/미스에 따라 감점 측정 창이 달라짐 (경로 비결정성).
- 33-A4 실증 doc(power-spin 51점)은 캐시 히트 + 자동 창이 **우연히** 옳은 국면에
  앉아 국면 정합이 보장 없이 성립했었다.

## 2. 수정 diff 요지

파일: `backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py`

1. **`_hold_window_from_moments(moments)` 공통 함수 신설** — hold moment 필터 →
   timestamp 정렬 → 2개 이상 = 첫/마지막, 1개 = ±2초 창, 0개 = None, fps 9.0.
   종전 `_build_profile` 인라인 로직과 의미 동일 (순수 추출, 산식 변경 0).
2. **`_build_profile` 이 공통 함수 호출** — 인라인 창 계산 제거.
3. **`_profile_from_cache` 가 동일 함수로 `hold_window=` 복원** — `cached["moments"]`
   raw dict 에서 직접 산출. KeyMoment dataclass 복원(Layer 2) 실패와 독립적으로
   국면 게이트가 살아남도록 결합 차단.
4. `_moment_field` accessor — KeyMoment 객체(신선)와 cache dict(캐시)를 같은 코드로
   읽음. 비수치 timestamp 는 warning + None(자동 창 폴백) graceful.

수리 원칙 준수: 특정 동작(motion) 이름 분기 0 — 전 동작 공통 구조 수정.
신선/캐시 profile 구성의 창 계산이 "분기 0, 코드 1벌"로 합쳐짐.

## 3. 로컬 테스트 결과 (2026-07-29)

- 신규 회귀 테스트 4건 (`backend/tests/test_gemini_technique_recognizer.py::TestCacheHoldWindowRestore`):
  - 캐시 히트 시 hold_window 복원 (단일 hold 7.0s → 창 (45, 81))
  - 신선 경로 store payload round-trip → 캐시 profile 과 hold_window 동일 (핵심 불변식)
  - hold moment 부재 시 None 유지 (가짜 창 생성 금지)
  - KeyMoment 복원 실패(Layer 2 비활성) 시에도 hold_window 는 복원 (독립성)
- **RED 실증**: 수정 전(HEAD) 소스로 실행 시 4건 중 3건 실패(None 유지 테스트만 통과)
  — 테스트가 실제 결함을 잡음을 확인 후 수정 적용 → 4건 전부 GREEN.
- backend 전체 (`PYTHONPATH=backend/tests python3 -m pytest backend/tests -q`):
  **3688 passed, 58 failed, 27 skipped.** 실패 58건은 수정 전/후 **집합 diff 0**
  (전부 사전 존재, 로컬 환경 의존 — 예: `GEMINI_MODEL` env 미설정으로
  `DEFAULT_GEMINI_MODEL` 상수 불일치, yaml/judging_data 로컬 경로 의존,
  vision scorer 캐시 결정성 테스트의 env 의존 등). 본 수정이 새로 깨뜨린 테스트 0건.

## 4. 행동 변화 예고 (Pod 검증 세션 필독)

이 수정으로 캐시 히트 경로가 신선 경로와 **동일하게 Gemini hold 창을 존중**한다.
33-A4 실증이 보인 대로 Gemini hold timestamp 자체가 부정확한 영상
(power-spin 실증 doc: hold=2.1s, 실제 완성 국면은 6.3~8.2s — 4초 이상 오차)에서는:

- 종전 캐시 히트: 자동 분산최소 창(우연히 6.31~8.18s) → left_knee 평균 141°, r00 −20
- 수정 후 캐시 히트: Gemini hold 창 (2.1±2)s = frames [1,37) → right_knee 평균 약 78°
  (33-A4 §5-1 반증 계산) — **tuck 한복판을 "무릎 안 폈음"으로 재는 값**

즉 본 수정은 끊긴 지점 1(경로 비결정성)만 고친다. 끊긴 지점 2(Gemini hold
timestamp 불신뢰)와 지점 3(자동 창의 국면 무관성)은 **별도 플랜 소관**이며, 이
수정으로 지점 2의 영향이 캐시 경로에도 일관되게 드러난다. 점수 이동이 관찰되면
그것은 회귀가 아니라 결함 노출이다 — 판정은 fixture 기대치 기준으로 하되, 지점 2
수리 필요성의 증거로 기록할 것.

## 5. Pod 재검증 체크리스트 (2026-07-29 수행 완료 — 결과는 §6)

로컬은 순수 함수 단위 검증까지. 실분석 검증은 Pod(RTX 4090, **s5jtnzs9q9oalf** —
구 8hrks3hrxmtgw6 대체 신규 Pod)에서 2026-07-29 수행. **상태: 수행 완료.**

- [x] 6 fixture 전체 (phase25 success+fault 페어, 산식 `final=max(25,100−min(40,Σ실행)−Σ치명)` 기대치 기준): **전 항목 33-23 기대치 일치 (execRaw 소수점까지 동일)**
  - [x] ref-kip-up — fault 79 / correct 100 (기대 79/100)
  - [x] ref-peter-pan — fault 86 / correct 100 (기대 86/100)
  - [x] ref-power-spin — fault 80 / correct 100 (기대 80/100). §4 행동 변화는 Gemini
        recognizer 경로에서 별도 관찰(§6-3) — fixture 스위프는 Fallback recognizer
        (33-23 절차 정합)라 이동 없음(예상대로)
  - [x] ref-pdshape — fault 60 / correct 100 + 2-run(cold-rerun) 100/100, criteria
        선택 동일 (R-6 PASS)
  - [x] ref-elbow-twist-sister — fault 60 / correct 100 (기대 60/100)
  - [x] ref-climb — fault/success 모두 `NotPoleMotionError`(angle 0<25 / 3<25) 게이트
        반려, 채점 미도달 — 33-23 과 동일 (게이트 오동작 없음)
- [x] 비-fixture 4종 대체 검증 — `verify_self_comparison.py` 는 NLF 의존이라 RTMW Pod
      미동작(33-S4 와 동일) → 33-S4 확립 대체 절차(reference 영상을 학생으로 재투입,
      shadow candidate) 재사용: **4/4 = 100점, maxDev 0.0027~0.0029 (S4 기준 일치)**
  - [x] ref-foxtop — 100 / maxDev 0.0027 / hold_window (207,243) 복원
  - [x] ref-foxtop-split — 100 / maxDev 0.0028 / hold_window (162,198) 복원
  - [x] ref-invert — 100 / maxDev 0.0028 / hold_window (36,72) 복원
  - [x] ref-sideway-spin — 100 / maxDev 0.0029 / hold_window (81,117) 복원
- [x] 캐시 경로 동일성 실증 (부분) — 동일 영상(§4 실증 영상과 fixture fault.mp4 는
      **동일 바이트**, video_hash `574a774c…` 공유) 반복 분석 3회에서 hold_window
      (1,37) 과 r00 measuredValue 78.27 이 회차 간 완전 동일 (캐시 히트 경로 결정론).
      단 **진짜 미스(신선 Gemini) 1회차는 Pod→S3 경로 저하로 차단 → 33-16 이월**
      (§6-4 — 대신 로컬 회귀 테스트의 round-trip 불변식이 신선↔캐시 동일성을 증명)
- [x] 점수 이동 기록 — §4 예고대로 Gemini 경로 재분석에서 관찰·박제(§6-3). fixture
      기대치 위반 0건. 끊긴 지점 2 수리 플랜 입력 = §6-3 실측값

## 6. Pod 재검증 결과 (2026-07-29)

### 6-0. 실행 환경

- Pod: `s5jtnzs9q9oalf` (RTX 4090 24GB, EU-RO — belle 신규 생성, Network Volume 계보 유지)
- 코드: main `6137631` (본 수리 머지 커밋). 서버 `/health` commitSha 동일 확인 (내부+프록시)
- SSM `/sunity/motion/runpod-analyze-url` + Lambda `sunity-motion-pilot-pipeline`
  env `RUNPOD_ANALYZE_URL` → `https://s5jtnzs9q9oalf-8000.proxy.runpod.net/analyze` 동기화
  (Lambda 는 기존 env 4종 병합 갱신, RUNPOD_AUTH_TOKEN 무변경)
- 스위프: 33-23 절차 그대로 (`run_33_23_sweep.sh` 복제 = `evals/phase25/run_sweep.py
  --reference-version phase33-cm3-run1 --tag cold`, SERIAL, RTMW_DETERMINISTIC=1,
  PR_INVERSION_ENABLED=1, recognizer=Fallback, vision-veto ON, EVAL_OUT_DIR=/workspace/eval_out_33_a4)
- §4 관찰·캐시 실증: production substrate(shadow 없음, phase4_v1) + `RECOGNIZER_BACKEND=gemini`
  — 실증 doc 과 동일 조건. 산출은 eval uid(`phase25eval`) 신규 doc, belle production doc 무접촉

### 6-1. 6 fixture (기대 = 33-23 / 33-SCORING-REVERIFY)

| motion | kind | 기대 | 실측 | execRaw 기대/실측 | 판정 |
|---|---|---:|---:|---|:---:|
| power-spin | fault | 80 | **80** | −20.2 / −20.2 | PASS |
| power-spin | correct | 100 | **100** | 0 / 0 | PASS |
| peter-pan | fault | 86 | **86** | −14.1 / −14.1 | PASS |
| peter-pan | correct | 100 | **100** | 0 / 0 | PASS |
| elbow-twist-sister | fault | 60 | **60** | −111.4 / −111.4 | PASS |
| elbow-twist-sister | correct | 100 | **100** | 0 / 0 | PASS |
| pdshape | fault | 60 | **60** | −57.1 / −57.1 | PASS |
| pdshape | correct | 100 | **100** (2-run 100, criteria 동일) | 0 / 0 | PASS |
| kip-up | fault | 79 | **79** | −20.6 / −20.6 | PASS |
| kip-up | correct | 100 | **100** | 0 / 0 | PASS |
| climb | fault/correct | 게이트 반려 | NotPoleMotionError angle 0<25 / 3<25 | — | PASS |

INV-6 재구성(`final=max(25,round(100+execCap+crit))`) 채점 도달 10/10 정확.
**본 수리는 Fallback recognizer 스위프 경로에 접촉하지 않으며, 실측이 이를 실증
(전 멤버 byte-수준 동일).**

### 6-2. 비-fixture 4종 (33-S4 대체 절차, shadow phase33-cm3-run1, RECOGNIZER_BACKEND=gemini)

| motion | score (기대 100) | maxDev (기대 ~0.003) | hold_window 복원 | 판정 |
|---|---:|---:|---|:---:|
| ref-foxtop | 100 | 0.0027 | (207,243) | PASS |
| ref-foxtop-split | 100 | 0.0028 | (162,198) | PASS |
| ref-invert | 100 | 0.0028 | (36,72) | PASS |
| ref-sideway-spin | 100 | 0.0029 | (81,117) | PASS |

수리 전 캐시 히트는 hold_window=None(자동 창)이었을 경로 — 수리 후 4/4 에서 Gemini
hold 창이 복원됐고 self-comparison 100점·감점 레코드 0 은 유지(복원이 자기일관성을
깨지 않음).

### 6-3. power-spin §4 행동 변화 실측 (끊긴 지점 2 증거 — 수리 플랜 입력)

실증 doc 영상(`uploads/csKW…/071df9f….mp4`, 원 51점)을 production substrate +
Gemini recognizer 로 재분석 (기존 gemini_cache `574a774c…` hold=2.1s **히트**):

| 항목 | 원 doc (수리 전 캐시 히트) | 재분석 (수리 후 캐시 히트) |
|---|---|---|
| hold_window | 소실 → 자동 분산최소 창 frames [63,83) (실시간 6.31~8.18s) | **Gemini hold 창 frames [1,37)** (2.1±2s — tuck 한복판) |
| r00 leg_extension measuredValue | 140.86° (마무리 국면 평균) | **78.27°** (§5-1 반증 계산 78.25° 재현) |
| r00 points | −20.0 (per-record 클램프) | −20.0 (동일 — 부족분 39→102° 지만 클램프 동일) |
| r01 split_angle | 30.0 → −12.0 | 30.0 → −12.0 (동일 — 비전, 프레임 미고정) |
| r02 left_shoulder | 34.49° → −17.4 | 33.16° → −15.8 (RTMW 재추출 편차) |
| overall | 51 | **60** |

**점수 이동 51→60 분해 (회귀 아님):**
1. **엔진 세대차**: 원 doc 는 33-22 이전 무캡 산식(100−49.4=51). 현행 2-트랙에서는
   Σ실행 47.8 > 40 캡 → 60. 수리와 무관 (재분석 시점의 정당한 산식).
2. **수리 효과 = 측정 국면 이동**: r00 이 이제 Gemini hold 창(1,37)=tuck 한복판을
   측정 → 78.27°. §4 예고("tuck 한복판을 무릎 안 폈음으로 재는 값") 그대로 실측.
   points 는 클램프 동일(−20)이라 점수엔 중립이나, **measuredValue·표시 앵커가
   틀린 국면을 가리키게 됨** — 끊긴 지점 2(Gemini hold=2.1s vs 실제 완성 6.3~8.2s,
   4초+ 오차)가 캐시 경로에도 일관 노출된 것. 수리 플랜(끊긴 지점 2·3)의 입력 증거.
3. r02 소폭 이동(34.49→33.16)은 RTMW 재추출 편차(창과 무관, 전 경로 median).

### 6-4. 캐시 미스→히트 동일성 실증

fixture `fixtures/phase15/power-spin/fault.mp4` 는 실증 업로드 영상과 **동일 바이트**
(video_hash `574a774c7d19…` 동일)임을 해시로 확인 — §4 관찰과 동일성 실증이 같은
영상에서 수행됨.

- 1차 실증(동일 프로세스 3회 분석: 실증 재분석 + run1 + run2): 3회 전부
  hold_window **(1,37)**, measuredValue 3종(leg_extension **78.27** / split_angle
  30.0 / left_shoulder 33.16), overall **60** 이 완전 동일 — 캐시 히트 경로 결정론.
  단, run1 은 설계와 달리 **in-memory 레이어 히트**였다(동일 프로세스 선행 분석이
  같은 해시를 적재; Firestore doc 삭제는 in-memory 를 비우지 못함 — TechniqueCache
  2단 구조의 정직한 기록). Firestore 원본 doc 백업:
  `/workspace/_a4_cache_backup_574a774c7d19.json` (hold=2.1s 원본 moments 보존).
- 2차 실증(신선 프로세스, Firestore doc 부재 확인 후 run1=진짜 미스(신선 Gemini)
  → run2=히트): **Pod↔AWS 데이터플레인 저하로 차단, belle 지시로 종결 — 33-16
  재스위프에 편승 예정.** 실측: 2026-07-29 ~12:00Z 부터 Pod→S3 서울 전송이
  6~12KB/s 로 붕괴 (1KB GET 3.0s / 64KB 10.4s / 256KB 22.1s / 43MB 사실상 불가),
  반면 Cloudflare 10MB 0.32s(31MB/s)·Mac→S3 즉시 성공 = AWS 측·Pod 회선 자체는
  정상, EU-RO→ap-northeast-2 경로만 저하. S3 엔드포인트 IP 8개 전부 동일 증상.
  faulthandler 스택덤프로 `boto3 download_file` 내 ssl.read 무한대기 실증. S3
  1MB 프리체크 게이트 워치독으로 자동 재시도 대기 후 종결. **잔여 리스크 낮음**:
  신선/캐시 경로가 같은 함수(`_hold_window_from_moments`) 하나를 쓰는 "코드
  1벌" 구조 + store→lookup round-trip 동일성은 로컬 회귀 테스트(§3 핵심
  불변식)가 증명, 캐시 히트 경로의 라이브 복원은 §6-2·§6-3 에서 6회 실증됨.

### 6-5. 운영 특이사항 (판정 무관, 기록)

- 원 스위프가 kip-up fault 초입에서 hang (전 스레드 futex, S3 소켓 CLOSE-WAIT —
  faulthandler 스택덤프로 `boto3 download_file` 내 ssl.read 무한대기 실증) → kill 후
  잔여 멤버(kip-up·climb 페어 + pdshape cold-rerun)를 동일 절차 resume 드라이버로
  완주. 값 영향 0 (완료분은 Firestore 박제, 재실행 없음).
- 이후 Pod→S3 **데이터플레인 저하** 재발 (컨트롤 플레인은 정상, 데이터 GET 정체;
  상세 수치 §6-4). 2차 캐시 실증이 이에 걸려 belle 지시로 종결(33-16 이월).
  **저하가 지속되는 동안 belle 앱 테스트의 분석이 영상 다운로드 단계에서 hang
  될 수 있음 — 앱/채점 문제가 아니라 Pod 네트워크 이슈로 인지할 것.**
- Cerebras coach JSON 파싱 실패 4건 → "수치 폴백 사용" graceful (채점 무관, 기존 경로).
- gemini_cache `574a774c…` 원본 doc 는 미스 실증용 삭제 후 **백업에서 원상복구
  완료** (hold=2.1s·model·yaml_version 원본 그대로 — 복원 후 exists/내용 검증).
  production 캐시 상태는 검증 전과 동일.

### 6-6. 사용 명령어 (Pod /workspace)

- 셋업: `bash bootstrap_full.sh` → `source aws_env.sh && bash start_server.sh`
- 6 fixture: `run_33_a4_sweep.sh` (= run_33_23_sweep.sh 에서 EVAL_OUT_DIR 만
  `/workspace/eval_out_33_a4` 로 변경) → hang 후 `_a4_resume.py` (잔여 멤버 동일 절차)
- 비-fixture 4종: `_a4_selfcompare.py` (`_a4_launch_selfcompare.sh`)
- §4 관찰 + 1차 동일성: `_a4_cachecheck.py` / 2차: `_a4_cachecheck2.py`
  (`_a4_cc2_watchdog2.sh` — S3 프리체크 게이트)
- 산출물: `eval_out_33_a4/phase25/phase25_resume_report.json`,
  `_a4_selfcompare_out.json`, `_a4_cachecheck_out.json`, `_a4_cachecheck2_out.json`,
  `_a4_cache_backup_574a774c7d19.json`

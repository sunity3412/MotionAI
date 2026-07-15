---
phase: quick-260715-fjw
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/training/datagen/perturb.py
  - backend/training/datagen/build_jsonl.py
  - backend/tests/phase22/test_perturb.py
  - backend/tests/phase22/test_build_jsonl.py
autonomous: true
requirements: [QUICK-260715-FJW]
must_haves:
  truths:
    - "perturb 트랙 샘플의 user-표시 프레임에 교란이 반드시 반영된다 (표시 밖 교란으로 인한 순수 항등 echo 샘플 0)"
    - "perturb stage 1/2 에 가시(visible) 변위 교란이 존재한다 — 가려짐(NaN) 단독이 아님"
    - "perturb 트랙에 좌표전용(비디오 없음) 샘플이 결정적 비율로 혼합되고, user 텍스트가 게이트 aligned 좌표전용 양식과 문자 단위 동일하다"
    - "distill corrected_coords=None / perturb corrected_coords=원좌표 소유 구조(v4)가 그대로 유지된다"
    - "backend/tests/phase22 전체 GREEN (기존 258 pass + 신규 테스트)"
  artifacts:
    - path: "backend/training/datagen/perturb.py"
      provides: "_apply_drift 변위 primitive + stage 1/2/3 변위 강화 (기존 stage 계약 보존)"
    - path: "backend/training/datagen/build_jsonl.py"
      provides: "subsample-first 교란 + 좌표전용 샘플 혼합 + 변위 위주 stage cycle + cc 전체 프레임 유지 근거 주석"
    - path: "backend/tests/phase22/test_perturb.py"
      provides: "drift/변위 커버리지 신규 테스트 (기존 7개 계약 불변)"
    - path: "backend/tests/phase22/test_build_jsonl.py"
      provides: "좌표전용 양식·subsample-first·cc 계약 신규 테스트 (기존 계약 불변)"
  key_links:
    - from: "backend/training/datagen/build_jsonl.py 좌표전용 샘플"
      to: "backend/evals/phase22/run_bakeoff.py::build_aligned_report_messages"
      via: "_TASK_INSTRUCTION / _rtmw_text import 재사용 (단일 진실, 복사 금지)"
      pattern: "_rtmw_text\\(.*\\) \\+ _TASK_INSTRUCTION"
    - from: "backend/training/datagen/perturb.py drift 파라미터"
      to: "backend/training/datagen/rtmw_error_profile.json"
      via: "per_joint_jump_deg(크기) + confidence_drop_run_length(run 길이) 히스토그램 샘플"
      pattern: "_sample_histogram|_sample_run_length"
---

<objective>
Phase 22 SFT v5 를 위한 perturb 트랙 재설계 3처방을 로컬 코드로 구현한다:
(1) 변위(displacement) 위주 stage 비중 확대, (2) 좌표전용 샘플 양식 추가(게이트
synthetic_holdout 분포 정합), (3) corrected_coords 출력 양식 재고(전체 프레임 유지
+ 근거 박제).

Purpose: v4 aligned 게이트 재계측(2026-07-14)의 잔여 gap — synthetic_holdout 에서
모델이 corrected_coords=[] 전량 방출(학습=전부 video+coords vs 게이트=좌표전용 분포
불일치) + v2 진단 "perturb 가 변위 보정을 못 가르침"(holdout ≈ 무보정 기준선) — 을
학습 데이터 측에서 처방한다. 이 작업 완료 후 Pod 에서 `--assemble --with-perturb
--upload` v5 조립 → SFT v5 → aligned 게이트 재판정.

Output: perturb.py / build_jsonl.py 코드 + phase22 테스트. 조립 실행/S3/Pod 은 스코프 밖.
</objective>

<context>
@backend/training/datagen/perturb.py
@backend/training/datagen/build_jsonl.py
@backend/training/datagen/measure_error_profile.py  (분포 근거 — 수정 금지)
@backend/tests/phase22/test_perturb.py
@backend/tests/phase22/test_build_jsonl.py
@backend/evals/phase22/run_bakeoff.py  (게이트 하네스 — 수정 금지, 정합 확인용)
@backend/evals/phase22/assert_gates.py  (check_synthetic_holdout — 수정 금지)

## 설계 결정 (executor 는 이 결정을 그대로 구현한다)

**D1 — drift primitive 신설 (perturb.py `_apply_drift`)**
지속 변위 = [start,end) run 동안 관절 좌표에 **일정한**(프레임 간 동일) 오프셋 벡터를
더한다. 프레임별 독립 노이즈인 `_apply_jitter` 와 구분되는, RTMW 지속 오추적 모방.
- 크기: `per_joint_jump_deg` 집계 히스토그램 샘플(도) / 90.0 (기존 jitter 와 동일 환산
  — 신규 매직 상수 0).
- run 길이: `confidence_drop_run_length` 히스토그램 샘플(`_sample_run_length` 재사용),
  최소 2 프레임. 근거 주석 필수: "지속 오류 지속시간의 실측 대리 분포 — profile 이
  보유한 유일한 시간 길이 분포(proxy 임을 명시)".
- 방향: rng 단위 벡터(x,y), run 내 고정. confidence 채널 불변(가시 오류 — 모델이
  영상/궤적으로 잡아내야 함).
- 대상 셀은 `perturbed_joints`/`perturbed_frames` 에 등재 (기존 계약).

**D2 — stage 재구성 (기존 test_perturb.py stage 계약 보존)**
- stage1 (변위 우선, 비핵심 관절만 — 계약: names ⊆ noncore 유지): 기존 jitter 2관절
  + **drift run 1~2관절 추가** + 기존 단발 가려짐 1건 유지(Null 규격 확립).
- stage2 (핵심 관절 — 계약: names ∩ core ≠ ∅, 연속 ≥2 프레임 유지): 기존 가려짐 run
  + **핵심 관절 drift run 1건 추가** (stage2 가 순수 가려짐이라 변위 감독 0 이던 것 해소
  — 가려짐 셀은 게이트 가시 마스크에서 제외되므로 stage2 는 지금까지 게이트 대상
  변위 신호를 전혀 못 만들었다).
- stage3 (복합 — 계약: L/R 스왑 유지): 기존 스왑+가려짐+jitter 에 drift 1건 추가.

**D3 — stage 배분 변위 가중 (build_jsonl.py)**
`stage = (i % 3) + 1` 균등 배분을 `_STAGE_CYCLE = (1, 1, 2, 3)` 결정적 cycle 로 교체
(`stage = _STAGE_CYCLE[i % len(_STAGE_CYCLE)]`). 근거 주석 필수: "게이트
synthetic_holdout 은 가시 셀 변위 보정 L2 만 판정(가려짐 복원은 비게이트 관찰치
grounding_occluded_restored) — 변위-순수 stage1 을 2배 가중. 수치는 ablation 축".

**D4 — subsample-first 교란 (build_jsonl.py `_build_perturb_samples`)**
현행: 전체 (T,J,C) 교란 후 select_frame_indices(≤64) 서브샘플 → 교란 프레임 다수가
표시 프레임 밖 → user 는 무교란 좌표를 보는데 corrected=원좌표 = 순수 항등 echo 샘플
양산 (v2 "무보정 동률" 의 기계적 원인). 교정: **먼저 `coords[idxs]` 로 서브샘플한
(≤64,J,C) 배열에 perturb_sequence 를 적용** → 모든 교란이 표시 프레임에 반드시 반영.
frame 라벨은 원본 영상 프레임 번호(idxs)를 유지한다 (`_coords_to_frames` 에 라벨과
배열 인덱스를 분리 전달하거나 산출 행의 frame 값을 idxs 로 재기입 — 구현 방식은
executor 재량, user 행과 corrected_coords 행의 frame 라벨 일치가 계약).

**D5 — 좌표전용 샘플 혼합 (build_jsonl.py)**
eligible perturb 행 i 에 대해 `i % 3 == 2` 인 행은 video 파트 없이 좌표전용으로 방출
(결정적 cycle, 비율 1/3). user 메시지 = `{"role":"user","content":[{"type":"text",
"text": _rtmw_text(user_frames) + _TASK_INSTRUCTION}]}` — **게이트
`build_aligned_report_messages(rows, [])` 좌표전용 경로와 문자 단위 동일**.
`_TASK_INSTRUCTION` 은 기존 모듈 상수 재사용(단일 진실 — 신규 변형 문구 작성 금지.
지시문의 "위 영상과" 표현이 좌표전용에 어색해도 게이트가 동일 문구를 쓰므로 분포
일치가 우선). 비율 근거 주석 필수: "게이트 synth=좌표전용 / 프로덕션 추론=video+
coords — 다수(2/3)는 video 유지로 시각 grounding 보존, 1/3 로 좌표전용 분포 커버.
수치는 ablation 축". 샘플에 `_coords_only: True` 마킹 + `_meta` 에
`perturb_coords_only_count` 카운터 방출. `_track` 은 "perturb" 유지 — video_hash
단위 split 이 좌표전용/video 두 양식을 같은 쪽(train 또는 val)에 두어 leakage 0.

**D6 — corrected_coords 전체 프레임 echo 유지 (변경 관절/프레임만 방출 채택 안 함)**
근거를 `_build_perturb_samples` 주석으로 박제:
- 게이트 공정성: `parse_corrected_coords` 는 미방출 프레임=NaN 제외 — 부분 방출을
  학습시키면 모델이 쉬운(무교란) 프레임만 골라 방출해 상대 게이트(보정<무보정)를
  뒷문으로 무력화(cherry-picking = 게이트 완화)할 수 있다. 전체 방출은 계측 마스크
  ≈ 무보정 기준선 마스크로 비교가 공정하다.
- 무교란 셀의 "입력 그대로 출력" 은 보정 함수의 올바른 항등 구간이지 v3 distill 의
  독(무의미 echo 가 의미 필드를 익사)과 다르다 — v4 에서 distill cc=None 으로 익사
  원인은 이미 제거됐고, perturb 내부의 항등 비중은 D1/D2/D4 의 변위 밀도 확대로
  실질 신호 비율을 올려 해소한다.

**게이트 영향 명시(문서화만, 하네스 무수정):** run_bakeoff synth 항목은
perturb.perturb_sequence 를 직접 호출하므로 D1/D2 로 v5 게이트의 교란 자체가 달라진다
— grounding_uncorrected 기준선도 매 run 재계산되므로 상대 게이트 semantics 불변
(완화 아님). 단 v4 절대 수치와의 직접 비교는 불가함을 SUMMARY 에 기록할 것.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: perturb.py — drift primitive + stage 변위 강화 (D1, D2)</name>
  <files>backend/training/datagen/perturb.py, backend/tests/phase22/test_perturb.py</files>
  <behavior>
    신규 테스트 (기존 7개 계약 불변 유지):
    - Test A (drift primitive): `_apply_drift` 적용 run 구간의 대상 관절 x,y 가 원본과
      다르고 전부 finite(NaN 0), 오프셋이 run 내 프레임 간 동일(상수 벡터), confidence
      채널 불변, run 길이 >= 2.
    - Test B (stage 변위 커버리지): stage 1/2/3 각각에 대해 perturb_sequence 결과에
      "가시 변위 셀"(perturbed 값이 finite 이면서 original 과 다른 (frame,joint) 셀)이
      1개 이상 존재. 특히 stage2 — 순수 가려짐이 아님을 고정.
    - Test C (기존 계약 회귀): stage1 은 여전히 noncore 만, stage2 는 core 포함 +
      연속 >=2 프레임, stage3 스왑, 재현성(같은 seed = 같은 출력), profile=None
      TypeError — 기존 테스트가 이 계약을 이미 고정하므로 기존 테스트 GREEN 이 곧 검증.
  </behavior>
  <action>
    RED: 위 Test A/B 를 test_perturb.py 에 추가, 실패 확인 → commit
    `test(quick-260715-fjw): add failing drift + stage displacement tests`.
    GREEN: perturb.py 에 `_apply_drift(out, ji, start, end, jump_hist, rng)` 구현
    (D1 스펙: 크기=per_joint_jump_deg 샘플/90.0, 방향=rng 단위벡터 run 내 고정,
    confidence 불변) + perturb_sequence stage 1/2/3 에 D2 대로 drift 배선
    (perturbed_joints/perturbed_frames 등재 포함). 모든 신규 수치는 profile 분포
    샘플 — 하드코딩 교란 수치 금지(A3), 신규 상수는 근거 주석 필수.
    numpy 단독 순수성 유지(boto3/requests/urllib import 금지 — 기존 테스트가 grep 고정).
    commit `feat(quick-260715-fjw): displacement-first perturb stages via _apply_drift`.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && python3 -m pytest tests/phase22/test_perturb.py -q</automated>
  </verify>
  <done>기존 7 테스트 + 신규 drift/변위 테스트 전부 PASS. stage 계약(비핵심/핵심/스왑) 불변. 교란 수치 하드코딩 0.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: build_jsonl.py — subsample-first + 좌표전용 혼합 + stage cycle + cc 근거 박제 (D3, D4, D5, D6)</name>
  <files>backend/training/datagen/build_jsonl.py, backend/tests/phase22/test_build_jsonl.py</files>
  <behavior>
    신규 테스트 (기존 계약 불변 유지):
    - Test D (좌표전용 양식): perturb 트랙에 `sample_has_video(s) == False` 인 샘플이
      존재하고, 그 user content 는 text 단일 파트이며 텍스트가
      `build_jsonl._rtmw_text(<해당 frames>) + build_jsonl._TASK_INSTRUCTION` 과
      문자 단위 동일 (게이트 aligned 좌표전용 경로 정합 — _TASK_INSTRUCTION import
      단일 진실, 사본 문자열 비교가 아닌 모듈 상수 참조로 조립됨을 확인).
    - Test E (혼합 비율): eligible perturb 행 대비 좌표전용 비율이 결정적 cycle(1/3)
      과 일치 + `_meta.perturb_coords_only_count` 방출 + video 양식이 다수 유지.
    - Test F (subsample-first): 모든 perturb 샘플에서 user 표시 frames 와 원좌표
      frames 가 최소 1개 (frame,joint) 셀에서 상이 (표시 프레임 내 교란 보장 —
      순수 항등 echo 샘플 0). user 행과 corrected_coords 행의 frame 라벨 집합 동일.
    - Test G (stage cycle): 조립 시 stage 배분이 `_STAGE_CYCLE = (1,1,2,3)` 을 따름
      (perturb_loader 를 4행 이상 fixture 로 호출해 결정적 확인 — perturb_sequence 를
      monkeypatch 하여 전달된 stage 인자를 캡처하는 방식 허용).
    - Test H (cc 계약 유지): perturb corrected_coords = 표시 프레임 전체 행
      (행 수 == len(idxs)) + truthy — D6 결정 고정. distill corrected_coords=None
      기존 테스트 GREEN 유지.
    - Test I (leakage): 같은 video_hash 의 좌표전용/video 샘플이 train/val 로
      갈라지지 않음 (hash split 이 양식 무관하게 동작).
  </behavior>
  <action>
    RED: Test D~I 를 test_build_jsonl.py 에 추가, 실패 확인 → commit
    `test(quick-260715-fjw): add failing coords-only + subsample-first tests`.
    GREEN: `_build_perturb_samples` 를 D3/D4/D5/D6 대로 개편 —
    (1) `coords[idxs]` 서브샘플 후 perturb_sequence 적용, frame 라벨은 원본 idxs 유지;
    (2) `_STAGE_CYCLE = (1, 1, 2, 3)` 상수 + 근거 주석(D3 문구);
    (3) `i % 3 == 2` 행은 좌표전용 user 메시지(text 단일 파트,
    `_rtmw_text(user_frames) + _TASK_INSTRUCTION` — 기존 상수 재사용, 신규 지시문
    작성 금지) + `_coords_only: True` 마킹, 나머지는 기존 `_user_media_msg` 유지;
    (4) `_meta` 에 `perturb_coords_only_count` 추가;
    (5) corrected_coords 전체 프레임 유지 + D6 근거 주석 박제.
    _eligible_media_row / holdout / anonymized 게이트, _balance_media, video_hash
    split, distill/shadow/text 트랙 로직은 무접촉. schema.normalize_report 통과
    구조(REPORT_KEYS)도 불변 — run_bakeoff·assert_gates 는 수정하지 않는다.
    commit `feat(quick-260715-fjw): coords-only perturb samples + subsample-first + stage weighting`.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && python3 -m pytest tests/phase22 -q</automated>
  </verify>
  <done>backend/tests/phase22 전체 GREEN (기존 258 pass 기준선 + 신규, FAILED/ERROR 0). test_bakeoff_harness 의 aligned 정렬 테스트(_TASK_INSTRUCTION import 동일성) 포함 무회귀. run_bakeoff.py / assert_gates.py diff 0.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| manifest 행 → 학습 JSONL | holdout/미가명 고객 행이 media 로 유입되면 안 됨 (기존 게이트) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-fjw-01 | Info Disclosure | _build_perturb_samples 좌표전용 신규 경로 | mitigate | 좌표전용 샘플도 기존 `_eligible_media_row` 게이트 뒤에서만 생성 (holdout/hard-negative/미가명 고객 유입 0 — 기존 Test 3 이 커버, 신규 경로도 동일 루프 내) |
| T-fjw-02 | Tampering | 게이트 판정 (assert_gates) | accept | 하네스/게이트 파일 무수정 (diff 0 을 Task 2 done 에 고정). perturb 내부 변경으로 v5 절대 수치 비교 불가는 SUMMARY 문서화 |
</threat_model>

<verification>
- `cd backend && python3 -m pytest tests/phase22 -q` — 전체 GREEN, FAILED/ERROR 0.
- `rtk git diff --stat` — 변경 파일이 frontmatter files_modified 4개뿐 (run_bakeoff.py,
  assert_gates.py, sunity_shared/analysis 무접촉).
- grep 게이트: perturb.py 에 `import boto3|import requests|import urllib` 0 (기존 테스트가 고정).
- _TASK_INSTRUCTION 정의가 build_jsonl.py 1곳뿐: `grep -rn "위 영상과 RTMW" backend/ --include='*.py' | grep -v test` → build_jsonl.py 단일.
</verification>

<success_criteria>
- perturb stage 1/2/3 전부 가시 변위 셀 생성 + stage1 가중(1,1,2,3 cycle) — 변위 보정
  학습 신호 강화 (처방 1).
- perturb 트랙 1/3 좌표전용 샘플, 게이트 aligned 좌표전용 입력과 문자 단위 동일 양식
  (처방 2 — synthetic_holdout 분포 불일치 해소).
- corrected_coords 전체 프레임 유지 결정 + 근거 코드 주석 박제, 항등 echo 밀도는
  subsample-first + drift 로 실질 개선 (처방 3).
- 기존 v4 처방(distill cc=None, _TASK_INSTRUCTION 단일 진실) 무회귀. 게이트 완화 0.
- phase22 스위트 전체 GREEN. Pod 후속(v5 조립·SFT·게이트 재판정)은 스코프 밖.
</success_criteria>

<output>
Create `.planning/quick/260715-fjw-phase22-perturb-stage-corrected-coords/260715-fjw-SUMMARY.md` when done.
SUMMARY 에 반드시 기록: v5 게이트 절대 수치는 v4 와 직접 비교 불가(교란 분포 자체 변경 — 상대 게이트 semantics 는 불변), 좌표전용 1/3 · stage cycle (1,1,2,3) 은 ablation 축.
</output>

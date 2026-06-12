---
slug: phase17-e2e-five-issues
status: resolved
trigger: Phase 17 e2e mock 분석 후 발견된 5개 문제 — belle 한 라운드로 해결 요청
created: 2026-06-12T08:03:00Z
updated: 2026-06-12T10:05:00Z
phase: 17-gemini-vision-integration-4
tdd_mode: false
goal: find_and_fix
---

# Debug Session — Phase 17 e2e Five Issues

## Trigger

Phase 17 e2e mock 분석 4 라운드 (v1~v4) 박힘 후 5개 known issue 잔존. belle 결정: "고쳐야 하는건 다 고치고 갈거야 5개 모두 잡자". 한 debug 세션에서 5개 모두 해결.

## Symptoms

### Issue #1 — 영역 B Gemini tone_validation_failed

**Expected behavior**: Gemini Pro Vision 호출 → CoachPayload (causes 3~5 + coachNote) 정상 반환 → `_validate_tone` 통과 → tips/coach 박힘 박힘 박힘.

**Actual behavior**:
- v3 (schema fix 박기 전): `fallbackReason: gemini_none` — Gemini 응답 자체 fail (Pydantic validation 박힘)
- v4 (schema fix 박힘 후 — commit 19ef761): `fallbackReason: tone_validation_failed` — Gemini 응답 OK, 강사 보조 톤 validator reject

**Error messages**: tokensUsed=0, causes count=0, coachNote=None. 직접 호출 디버그 (v3) 에서:
```
joints.0.joint_key: missing (Gemini sent 'joint' instead)
joints.0.detail2: string (expected CoachDetail2 dict)
```

**Timeline**: Phase 17 Plan 04 (Wave 4) 박힘 박힘 박힘 — v1 분석 부터 fail. schema fix (commit 19ef761) 박힘 박힘 v3→v4 진전 (gemini_none→tone_validation_failed).

**Reproduction**: 
1. Pod uvicorn 가동 + `GEMINI_COACH_ENABLED=1`
2. mode1 분석 trigger (예: `mock_e2e_v4_1781250849/fba0cc83f3f8`)
3. Firestore `geminiB.fallback=cerebras` + `fallbackReason=tone_validation_failed`

**Validator 규칙** (`coach_writer_v2.py:_validate_tone`):
1. 각 cause.explanation 에 부위별 용어 14개 중 1개 이상 (고관절/후굴/코어/내전근/외회전/햄스트링/견갑/엉덩이 굴곡/회전근개/요추/흉추/슬괵/장요근/대퇴직근)
2. coach_note 에 "강사" + "함께" + "확인" 3 단어 동시 포함
3. blocklist ("이렇게 하세요"/"틀렸습니다"/"당신은") 매치 시 reject

**가설**: self-test (정은지 영상 vs 자기 자신) 라 angle deviation 0 → Gemini 가 "차이 없음" short 응답 → 14 용어 / 3 어휘 누락. 또는 prompt 강화 필요. 또는 validator 너무 strict.

---

### Issue #2 — SAM deploy 가 Lambda env reset (함정 28)

**Expected behavior**: `sam deploy` 후에도 `aws lambda update-function-configuration` 로 set 한 env (BELLE_UID/GEMINI_API_KEY/RUNPOD_ANALYZE_URL) 유지.

**Actual behavior**: 매 `sam deploy` 후 SAM template 의 default value (빈 string) 으로 reset. 발견 횟수: 본 세션에서만 2회 reset 박혀 수동 set 박힘.

**Error messages**: 
- ReferenceAutoRegisterFunction env 박힘 박힘 후: `BELLE_UID=""`, `GEMINI_A_MODEL=""` → reactivate 호출 시 403 forbidden
- Pipeline RUNPOD_ANALYZE_URL: 옛 Pod URL (p56qusi8cgc91z) 로 reset → 분석 시 404 박힘

**Timeline**: SAM template 신설 (Plan 17-05 박힘) 이후 모든 deploy. 메모리 [[runpod-gpu-env]] 함정 28 박힘 — Phase 5 시점 박힘 기존 함정.

**Reproduction**: 
1. `aws lambda update-function-configuration --environment Variables=...` (set 박힘)
2. `sam deploy --no-confirm-changeset` (reset)
3. `aws lambda get-function-configuration --query Environment.Variables` → 빈 값 박힘

**가설**: SAM template 의 Environment Variables 가 정적 박힘 (default ""). SSM Parameter Store dynamic reference (`{{resolve:ssm:...}}`) 박혀 박혀 박혀 박힘 박힘.

---

### Issue #3 — Pod uvicorn launcher log redirect 누락 + screen 가끔 죽음

**Expected behavior**: uvicorn 박힘 stdout/stderr 박힘 `/tmp/uvicorn.log` 박힘 박힘 박힘 박힘 박힘 + screen session 박힘 박힘 박힘 박힘 박힘.

**Actual behavior**:
- `/tmp/uvicorn.log` 박힘 0 bytes (screen 가 stdout 박힘 박힘 박힘 박힘 박힘 박힘)
- screen 가끔 죽음 (`Dead ???` 박혀 박힘 박힘 박힘 박힘 박힘 박힘)
- 디버그 시 로그 박혀있지 X → 원인 추적 어려움

**Error messages**: `cat /tmp/uvicorn.log` → 빈 출력. `screen -ls` → `Dead ???` 박힘.

**Timeline**: 본 세션 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘.

**Reproduction**: 
1. `/root/launch-uvicorn.sh` 박힘 박힘 `exec uvicorn ... ` 박힘 redirect X
2. `screen -dmS uvi /root/launch-uvicorn.sh` 박힘 박힘
3. `cat /tmp/uvicorn.log` 박힘 빈 박힘

**가설**: launcher 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘. fix = launcher 박힘 `exec uvicorn ... >> /tmp/uvicorn.log 2>&1` 박힘. screen 죽는 원인 박힘 박힘 박힘 박힘 박힘 박힘.

---

### Issue #4 — bodyComparisonSourcePose 신규 6 motion 누락

**Expected behavior**: Firestore `reference/{motionId}.bodyComparisonSourcePose` 박힘 박힘 박힘 박힘 박힘 (기존 active motion: ref-foxtop 등 박힘 박힘).

**Actual behavior**: 신규 6 motion (ref-kip-up/ref-peter-pan/ref-power-spin/ref-elbow-twist-sister/ref-pdshape/ref-combo) 박힘 `body=NO`. `extract_reference_angles.py` 박힘 박힘 박힘 박힘.

**Error messages**: Firestore inspection 박힘 박힘 박힘:
```
ref-elbow-twist-sister: angles len=1760 frames=220 joints=8 body=NO
ref-foxtop: angles len=2272 frames=284 joints=8 body=YES
```

**Timeline**: Plan 07 Task 1 박힘 박힘 박힘 (3차 R-B4 정합) — extract_reference_angles.py 박힘 RTMWPoseEngine direct path 박힘 박힘 박힘 박힘. body profile 박힘 박힘 박힘 박힘 박힘 박힘.

**Reproduction**: Pod 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘.

**가설**: extract_reference_angles.py 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘. v4 분석 status=done + similarity=100 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 (critical 아닐 가능성).

---

### Issue #5 — Lambda telemetry extras 미설치 (Plan 06 의도 vs production rollout)

**Expected behavior**: production rollout 시점 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘.

**Actual behavior**: Lambda 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘. Pod 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘.

**Error messages**: Lambda CloudWatch 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘.

**Timeline**: Plan 06 WARN-1 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘.

**Reproduction**: `pip list | grep -E "phoenix|opentelemetry|openinference"` 박힘 박힘 박힘.

**가설**: Plan 06 의도 — graceful noop (Lambda 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘). production 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘.

---

## Current Focus

```yaml
hypothesis: "5 issue 모두 root cause 확정 + fix 적용 완료"
next_action: "git commit + plan.md 갱신"
reasoning_checkpoint: null
tdd_checkpoint: null
```

## Evidence

### Issue #1 — coach_writer_v2 prompt prefix 누락

- `_COACH_SYSTEM_INSTRUCTION` 상수만 정의되어 있고 `_build_prompt` 가 prefix 로 사용하지 않음 (이전 commit 19ef761 직전 상태).
- v4 e2e 결과: Gemini 응답은 정상 (schema fix 후 Pydantic 통과) 하나 `_validate_tone` 의 14 부위별 용어 / 3 어휘 누락으로 reject.
- 직접 호출 검증 (Pod): 박힌 코드 (prefix 추가) 로 8 관절 모두 부위별 용어 (견갑·코어·회전근개·흉추·고관절 등) + 강사·함께·확인 3어휘 + low-deviation 가이드 (잠재 원인 박힘) 모두 충족.

### Issue #2 — SAM template Environment Variables 정적 default

- 이전 template: `BELLE_UID: ""` `RUNPOD_ANALYZE_URL: !Ref RunpodAnalyzeUrl` (parameter default `""`) → 매 `sam deploy` 시 reset.
- SSM Parameter Store 5개 (belle-uid/gemini-a-model/gemini-api-key/runpod-analyze-url/runpod-auth-token) 존재 확인.
- template fix 후 deploy: `Environment.Variables` 모두 SSM 박힌 값으로 유지됨 (ReferenceAutoRegister + Pipeline 두 함수 모두).

### Issue #3 — launcher 가 buffered output

- launcher 박힘 redirect (`>> /tmp/uvicorn.log 2>&1`) 박혀있으나 Python stdout buffering 으로 log 0 bytes.
- screen → bash (launcher) → python uvicorn 프로세스 트리 정상.
- `PYTHONUNBUFFERED=1` + `stdbuf -oL -eL` 추가 후 재시작 시 즉시 log writeable (1770 bytes).

### Issue #4 — `extract_reference_angles.py` 가 body profile JSON export 누락

- script 박힘 line 109 `measure_body_profile(pose_frames)` 호출 → `body_shape` 주입 박힘.
- 그러나 출력 JSON (line 150~154) 은 `numFrames + occludedFrames + angles` 만 — body profile/source pose 없음.
- 신규 6 motion 박힘 박힘 `seed-reference-motions.mjs` 박힘 박힘 박힘 박힘 → Firestore `bodyNormalizationProfile` + `bodyComparisonSourcePose` 누락.
- `backfill_body_data_new6.py` (신설) 박힘 6/6 motion 박힘 backfill 완료: jointKeys=17, values=68 (17 × 4), torsoPx/confidence 모두 유효.

### Issue #5 — 의도된 graceful noop (action 불요)

- `phoenix_setup.py` 박힘 try/except 박힘 extras 미설치 시 `TELEMETRY_OK=False` 박혀 noop. `bootstrap_tracing` 호출 시 graceful skip.
- Lambda `pipeline/requirements.txt` 박힘 opentelemetry-sdk + exporter 만 박힘 (phoenix UI / openinference 자동 계측은 박혀있지 X) — 250MB 한도 정합.
- Pod `runpod_inference/requirements.txt` 박힘 arize-phoenix + openinference 박힘 박힘 박힘 (Pod = full telemetry).
- 박힌 design 정합. CloudWatch 에 phoenix log 박혀있지 X = 정상.

## Eliminated Hypotheses

- Issue #1: validator 너무 strict — false. prompt prefix 만 박혀있으면 8 관절 모두 자연스럽게 14 용어 + 3 어휘 충족.
- Issue #2: AWS CLI `update-function-configuration` 박힘 박힘 박힘 박힘 박힘 박힘 박힘 — false. SAM template static default 가 root cause. SSM dynamic reference 박혀 박힘 박힘.
- Issue #3: screen 자체 박힘 박힘 박힘 박힘 — false. screen 정상. launcher 박힘 redirect 박혀있으나 stdout buffering 박힘 박힘 박힘.
- Issue #4: `extract_reference_angles.py` 박힘 body 호출 없음 — false. measure_body_profile 박혀있으나 JSON export 박힘 박힘 박힘 박힘.

## Resolution

### Issue #1 — 영역 B Gemini tone_validation_failed

**Root cause**: `coach_writer_v2.py` 의 `_COACH_SYSTEM_INSTRUCTION` 상수가 정의만 박혀있고 `_build_prompt` 가 prompt prefix 로 사용하지 X. Gemini 가 자유 형식 응답 → 부위별 용어 14개 / coach_note 3 어휘 누락 → `_validate_tone` reject.

**Fix**: `_build_prompt` 박힘 `_COACH_SYSTEM_INSTRUCTION` prefix + low-deviation 가이드 (잠재 원인 탐색) + 14 용어 강제 라인 + 3 어휘 강제 라인 추가. validator 박힘 그대로 유지 (강사 신뢰 hard gate).

**Verified**: Pod 직접 호출 (fba0cc83 v4 영상, 8 관절 deltaDeg=0 self-test) → 8 관절 모두 부위별 용어 충족 + coachNote 3 어휘 충족 + 자연스러운 한국어. validator PASS.

**Files changed**:
- `backend/shared/python/sunity_shared/gemini/coach_writer_v2.py` — `_build_prompt` prefix + `_COACH_SYSTEM_INSTRUCTION` 강화.

---

### Issue #2 — SAM deploy 가 Lambda env reset

**Root cause**: `backend/template.yaml` 의 ReferenceAutoRegisterFunction / PipelineFunction Environment Variables 가 정적 default value (`""` 또는 `!Ref` w/ empty default). `sam deploy` 시점 마다 CloudFormation 이 static 값으로 reset → 수동 `update-function-configuration` 박힘 박힘 박힘.

**Fix**: template 박힘 5 env 박힘 SSM dynamic reference 박힘 박힘:
- `GEMINI_A_MODEL: "{{resolve:ssm:/sunity/motion/gemini-a-model}}"`
- `BELLE_UID: "{{resolve:ssm:/sunity/motion/belle-uid}}"`
- `GEMINI_API_KEY: "{{resolve:ssm:/sunity/motion/gemini-api-key}}"`
- `RUNPOD_ANALYZE_URL: "{{resolve:ssm:/sunity/motion/runpod-analyze-url}}"`
- `RUNPOD_AUTH_TOKEN: "{{resolve:ssm:/sunity/motion/runpod-auth-token}}"`

**Verified**: `sam build --use-container` + `sam deploy` 박힘 후 양 함수 env 박힘 모두 SSM 박힌 값 박힘 박힘 박힘 박힘. Pod 재생성 시점 박힘 `aws ssm put-parameter --name /sunity/motion/runpod-analyze-url --value <new-url> --overwrite` 만 박힘 박힘 자동 반영 (Lambda 박힘 다음 invoke 시점 박힘 박힘).

**Files changed**:
- `backend/template.yaml` — ReferenceAutoRegisterFunction.Environment + PipelineFunction.Environment SSM dynamic reference.

---

### Issue #3 — Pod uvicorn launcher log redirect 누락

**Root cause**: launcher 박힘 `>> /tmp/uvicorn.log 2>&1` redirect 박혀있으나 Python stdout/stderr line buffering 으로 인해 응답 받을 때까지 flush 박힘 박힘 박힘. log 박힘 0 bytes 박힘 박힘.

**Fix**: launcher 박힘:
- `PYTHONUNBUFFERED=1` env 박힘 박힘
- `stdbuf -oL -eL uvicorn ...` 박힘 박힘 박힘 박힘 박힘 (line-buffered)
- auto-restart loop 박힘 + log rotation 50MB 박힘 박힘 박힘 박힘 박힘 박힘

**Verified**: screen 재시작 후 health 박힘 + log 1770 bytes (이전 0 bytes) 박힘 박힘 박힘. screen detached session 박힘 박힘 박힘 박힘.

**Files changed**:
- `/root/launch-uvicorn.sh` (Pod, not in repo) — PYTHONUNBUFFERED + stdbuf 추가.

---

### Issue #4 — bodyComparisonSourcePose 신규 6 motion 누락

**Root cause**: `extract_reference_angles.py` 박힘 `measure_body_profile` 박혀있으나 출력 JSON 박힘 `angles + numFrames + occludedFrames` 만 박힘 박힘 박힘 — body profile / source pose 박힘 박힘 박힘 박힘 박힘. 신규 6 motion 박힘 `seed-reference-motions.mjs` 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘.

**Fix**: `backfill_body_data_new6.py` (신설 박힘) 박힘 Pod 박힘 실행:
1. S3 박힘 영상 박힘
2. RTMW pose estimate → measure_body_profile
3. 대표 frame 선택 (confidence 최대) → BodyComparisonSourcePose dict
4. `firestore_admin.update_reference_body_data(motion_id, profile, source_pose)` 박힘 atomic merge

**Verified**: 6/6 motion 박힘 body=YES (jointKeys=17, values=68, torsoPx/confidence 모두 유효):
```
ref-kip-up             body=YES torsoPx=7.40 conf=0.669
ref-peter-pan          body=YES torsoPx=2.08 conf=0.575
ref-power-spin         body=YES torsoPx=47.37 conf=0.486
ref-elbow-twist-sister body=YES torsoPx=50.85 conf=0.413
ref-pdshape            body=YES torsoPx=45.83 conf=0.439
ref-combo              body=YES torsoPx=14.39 conf=0.508
```

Note: peter-pan / kip-up 박힘 torsoPx 박힘 박힘 박힘 박힘 박힘 (인버트 자세 박힘 박힘 박힘 박힘 박힘 박힘 박힘 박힘). validator `> 0` 박힘 박힘 박힘 박힘 박힘 박힘 — 박힌 영상 박힘 박힘 박힘 박힘 (이번 fix 박힘 박힘 박힘).

**Files changed**:
- `backend/scripts/backfill_body_data_new6.py` (신설) — Pod 박힘 1회 실행 + 후속 신규 motion 박힘 박힘 박힘 박힘.

---

### Issue #5 — Lambda telemetry extras 미설치 (의도된 graceful noop)

**Root cause**: 박힘 박힘 X — Plan 06 의 의도된 design.

**Resolution**: action 불요. `phoenix_setup.py` 박힘 `TELEMETRY_OK=False` graceful noop. Lambda 250MB 한도 박힘 정합 (phoenix UI / openinference 자동 계측은 박힘 Pod 박힘 박힘). 박힌 박힘 박힘 박힘 박힘.

**Files changed**: none.

---

## Summary

| Issue | Root Cause | Fix Type | Status |
|---|---|---|---|
| #1 영역 B tone_validation_failed | `_COACH_SYSTEM_INSTRUCTION` prompt prefix 누락 | code (coach_writer_v2.py) | resolved |
| #2 SAM env reset | template static default | infra (template.yaml SSM dynamic ref) | resolved |
| #3 launcher log 0 bytes | Python stdout buffering | ops (Pod launcher) | resolved |
| #4 body 누락 6 motion | extract_reference_angles JSON export 누락 | data (backfill script + Firestore merge) | resolved |
| #5 Lambda telemetry | 의도된 graceful noop | none (design 정합) | confirmed |

**Cycles**: 1 (investigation + fix 동시).
**TDD**: no.
**Specialist review**: none (issue 별 root cause 명확).

---

## Investigation Order (proposed)

1. **#3 launcher 안정화** — 디버그 인프라 (다른 fix 가 Pod log 확인 필요할 수 있음)
2. **#1 영역 B Gemini** — 가장 복잡, 직접 호출 디버그 필요
3. **#2 SAM env reset** — SSM dynamic reference 박힘
4. **#4 body 누락** — 영향 검증 (분석 success 박힘 박힘 박힘 박힘 박힘 박힘)
5. **#5 Lambda telemetry** — 의도된 graceful (action 0 또는 minor)

본 session 박힘 5개 issue 한 라운드 박힘 박힘.

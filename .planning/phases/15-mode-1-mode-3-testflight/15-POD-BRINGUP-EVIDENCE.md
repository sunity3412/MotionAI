# Phase 15-02: Pod Bring-up Evidence

**Generated:** 2026-06-17T08:42:50Z
**Plan:** 15-02 (신규 RunPod Pod bring-up + SSM/Lambda 동기화 + 실 LLM smoke)
**Executor:** parallel worktree (wave 1)

> 보안: 이 문서는 키 NAME / presence(SET/UNSET)만 기록한다. 어떤 secret 값도 포함하지 않는다 (T-15.02-02, RESEARCH V6).

---

## Pod Identity

| Field | Value |
|-------|-------|
| Pod id | `01emvodj1pdooe` |
| Proxy base | `https://01emvodj1pdooe-8000.proxy.runpod.net` |
| /health | `https://01emvodj1pdooe-8000.proxy.runpod.net/health` |
| /analyze | `https://01emvodj1pdooe-8000.proxy.runpod.net/analyze` |
| SSH (TCP, used for ops) | `root@213.173.110.226 -p 39380` |
| GPU host | `1cbf9337c67c` (uptime 446d) |

이 Pod 는 직전(pre-/clear) 세션에서 full-setup + Lambda/SSM URL sync 가 이미 적용된 상태였다 (git: "docs(state): new Pod 01emvodj1pdooe full-setup done"). 따라서 본 plan 의 Task 1 은 from-scratch bootstrap 이 아니라 **verify-and-repair** 로 수행했다 — healthy server 를 불필요하게 tear down 하지 않고, 실제 누락분(Cerebras param)만 복구했다.

---

## Task 1 — Pod /health 200 + env 복원

### /health (external proxy)

```
$ curl -s -w "HTTP %{http_code}" https://01emvodj1pdooe-8000.proxy.runpod.net/health
HTTP 200
{"status":"ok","auth_configured":true,"pipeline_loaded":true}
```

- `pipeline_loaded: true` — RTMW/NLF pipeline 모듈 로드됨 (CPU NaN 아님, GPU)
- `auth_configured: true` — `RUNPOD_AUTH_TOKEN` 설정됨 (server.py:99 비공개 모드 503 회피)

### weights (Pod)

| File | Size |
|------|------|
| `/workspace/rtmw_weights/rtmw-x-384.onnx` | 352M |
| `/workspace/yolox_weights/yolox_m.onnx` | 97M |
| `/workspace/firebase-sa.json` | 2385 bytes (present) |

### env 복원 체크리스트 (uvicorn proc env — name/presence only)

| Key | State | Note |
|-----|-------|------|
| `RECOGNIZER_BACKEND` | `gemini` | Gemini recognizer ON (값 비-secret) |
| `GEMINI_COACH_ENABLED` | `1` | 듀얼 coach 영역 B ON (재시작으로 명시 박제) |
| `RTMW_ONNX_PATH` | `/workspace/rtmw_weights/rtmw-x-384.onnx` | (값 비-secret) |
| `YOLOX_ONNX_PATH` | `/workspace/yolox_weights/yolox_m.onnx` | (값 비-secret) |
| `RTMW_DEVICE` | `cuda` | GPU 강제 (값 비-secret) |
| `FIREBASE_SA_PATH` | `/workspace/firebase-sa.json` | (값 비-secret) |
| `AWS_DEFAULT_REGION` | `ap-northeast-2` | (값 비-secret) |
| `GEMINI_API_KEY` | SET | (값 비노출) |
| `RUNPOD_AUTH_TOKEN` | SET | (값 비노출) |
| `CEREBRAS_KEY_PARAM` | `/sunity/motion/cerebras-api-key` | **복구됨** (아래 deviation 참조) |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | SET | (값 비노출) |

### Deviation (Rule 2 — 누락 critical config 자동 복구)

직전 세션 부트스트랩의 running uvicorn proc env 에 **`CEREBRAS_KEY_PARAM` 가 누락**되어 있었다. 이 env 가 없으면 `coach_writer._load_api_key()` 가 `None` 을 반환 → Cerebras 측 듀얼 coach 가 silent drop 된다 (D-12 cross-fill 로 PASS 는 되지만 best-case dual-coach 검증 불가). Plan Task 1 의 env 복원 체크리스트가 "Cerebras key" 를 명시하므로 복구가 필요했다.

조치:
1. SSM `/sunity/motion/cerebras-api-key` 존재 확인 (PRESENT, len 52 — 값 비노출).
2. uvicorn 을 전체 env 보존(AWS/Gemini/RTMW/RUNPOD_AUTH_TOKEN) + `CEREBRAS_KEY_PARAM=/sunity/motion/cerebras-api-key` + `GEMINI_COACH_ENABLED=1` 추가로 재시작 (pitfall 27: `__pycache__` 청소 후).
3. `/root/.bashrc` 에 `CEREBRAS_KEY_PARAM` / `GEMINI_COACH_ENABLED` 영구 박제 (idempotent).
4. 재시작 후 /health 200 재확인 (pipeline_loaded:true + auth_configured:true 유지).

코드/로그/commit 에 키 값 하드코딩 0. 이 복구는 Pod env 한정 (repo 파일 변경 없음).

### auth gate probe (no real analysis, no uploads/ 객체 — HIGH 2 준수)

```
$ curl -X POST .../analyze -H "X-RunPod-Token: <invalid>" -d '{"bucket":"x","key":"y"}'
HTTP 401  {"detail":"invalid token"}
```

잘못된 토큰 → 401. 이 프로브는 uploads/ 객체를 만들지 않아 notification 경로와 충돌하지 않는다.

---

## Task 2 — SSM/Lambda 동기화 + 4-key 보존 + notification-only 실 LLM smoke

### Resolved pipeline function name (MEDIUM 3)

`PIPELINE_FN = sunity-motion-pilot-pipeline` (template.yaml + setup_pod_full.sh 일치, region ap-northeast-2). verify 명령에서 `${PIPELINE_FN:-sunity-motion-pilot-pipeline}` 로 자기-완결(빈 변수 false-blocker 방지).

### AWS 자격증명

`sunity-motion` 프로필 사용 (Account 976369350031, user `sunity-motion`). `sunity-api` 는 Lambda AccessDenied — 사용 안 함 (RESEARCH Pitfall 2).

### SSM source-of-truth 갱신 (R2)

`aws ssm put-parameter --name /sunity/motion/runpod-analyze-url --value https://01emvodj1pdooe-8000.proxy.runpod.net/analyze --type String --overwrite` (sunity-motion). 현재 Version = 4. template.yaml:269 가 이 param 을 resolve 하므로 다음 sam deploy 무회귀.

### Lambda env 갱신 = MERGE not REPLACE (MEDIUM 4)

`get-function-configuration` 으로 현재 Environment.Variables 전체 map 을 읽어 `RUNPOD_ANALYZE_URL` 한 키만 신규 Pod /analyze 로 교체 후 전체 map 을 `update-function-configuration --environment file://...` 로 되썼다. 부분 CLI JSON 으로 전체 map REPLACE 하지 않음. 갱신에 사용한 임시 payload(토큰 값 포함)는 즉시 삭제.

### §lambda-env-preservation — post-update machine assertion

plan `<automated>` verify 실행 결과:

```
ALL_PRESENT_AND_SSM_EQ_LAMBDA https://01emvodj1pdooe-8000.proxy.runpod.net/analyze
verify exit: 0
```

| Check | Result |
|-------|--------|
| 4-key presence (`RUNPOD_ANALYZE_URL`, `RUNPOD_AUTH_TOKEN`, `VIDEO_BUCKET`, `FIREBASE_SA_PARAM`) | ALL_PRESENT (키 이름만, 값 비노출) |
| SSM `/sunity/motion/runpod-analyze-url` == live Lambda `RUNPOD_ANALYZE_URL` | EQUAL = `https://01emvodj1pdooe-8000.proxy.runpod.net/analyze` |
| 두 값 비어있음 | 아님 (둘 다 non-empty) |

두 검사(4-key presence / SSM==Lambda equality)는 별개이며 둘 다 PASS.

### §notification-only delegate smoke (HIGH 1/HIGH 2 — Plan 01 미의존)

자체-완결 smoke: 임시 Firestore doc(`users/phase15_smoke_<runId>/analyses/<analysisId>`, mode=mode3, status=uploading, createdAt/updatedAt) 생성 → 기존 S3 객체 `reference/ref-pdshape.mp4` 를 `uploads/{uid}/{analysisId}.mp4` 로 S3-to-S3 COPY(ContentType=video/mp4) → S3 ObjectCreated notification 이 **유일 trigger**(직접 /analyze POST 없음). Plan 01 의 fixtures/sweep_phase15.py/phase15_keys.json 미참조 (depends_on:[] 보존).

status 전이 (doc 폴링):
```
uploading -> queued -> pose_analysis -> comparison -> done
```

| Assertion | Result |
|-----------|--------|
| DELEGATE_RAN (S3→SQS→Lambda→RunPod delegate 실행) | **True** (status 전이 + done) |
| FINAL_STATUS | `done` |
| 임시 doc/uploads 객체 cleanup | 완료 (uploads/ 잔여 0 확인) |
| 직접 /analyze 이중 트리거 | 없음 (notification 단일 경로) |

Pod 로그 (`coach dual-track 섹션 조립`):
```
coach dual-track 섹션 조립 — gemini_ok=True cerebras_ok=True joints=3 cross_filled=[]
audit: left_elbow/right_elbow/left_shoulder = {causes:gemini, fix:cerebras, coachNote:gemini, injuryRisk:cerebras, crossFilled:[]}
```

| 실 LLM 발화 assertion | Result |
|----------------------|--------|
| 듀얼 coach delegate 실행 발생 | YES (위 로그 라인) |
| `gemini_ok` | **True** (실 Gemini 발화, heuristic-only 아님) |
| `cerebras_ok` | **True** (실 Cerebras 발화) |
| 빈 섹션(empty sections) | **0** (cross_filled=[], 4 섹션 모두 실 출처 태깅) |
| Recognizer | `GeminiTechniqueRecognizer (env switch ON)` — FallbackRecognizer 아님 |

### line dimension (RESEARCH Open Question 3)

`result.dimensionScores keys=['stability']`, `line=None` (LINE_NON_NONE=False).

원인: pdshape 영상이 Gemini recognizer 에서 `motion 미등록='auto'` 로 해소됨 → Page 9 단독 트랙(보편 채점) + 자동 수집 trigger. line dimension 은 인식된 동작의 EXTEND/BENT joint expectation 에 의존하므로, 'auto' 폴백 동작에서는 line 이 채워지지 않는 것이 **설계상 정상 동작**이다 (위양성 방지 — 가짜 line 점수 생성 안 함). recognizer 자체는 실제 Gemini 호출로 발화했고(silent fallback 아님), stability(Page 9 보편 트랙)는 정상 산출. 등록 동작(11 reference)에 대한 line non-None 검증은 Wave 2 Mode 1 E2E 에서 등록 reference 와의 비교로 수행 예정.

> 판정: 이 smoke 의 목적(실 LLM/듀얼 coach 가 silent fallback 이 아니라 실제 발화함)은 `gemini_ok=True AND cerebras_ok=True AND empty_sections=0` 으로 **충족**. line=None 은 미등록 동작의 정상 폴백이며 본 plan 의 게이트 실패가 아니다.

### §LLM-key-liveness (W-3 escalation gate)

| Key | Liveness (this 1 delegate call) |
|-----|--------------------------------|
| Gemini | LIVE (`gemini_ok=True`, recognizer + coach 모두 실 발화) |
| Cerebras | LIVE (`cerebras_ok=True`, fix/injuryRisk 섹션 실 출처) |

`gemini_ok=False AND cerebras_ok=False` 조건 **미충족** → W-3 blocking escalation **불필요**. 두 키 모두 live 이므로 정상 진행 (D-03 실 LLM 발화 확인 + D-12 best-case). belle escalation 발동 안 함.

---

## Success Criteria Summary

- [x] /health 200 + pipeline_loaded:true + auth_configured:true (신규 Pod, external proxy)
- [x] env 복원 (RTMW/YOLOX/Gemini/Cerebras/RUNPOD_AUTH_TOKEN/GEMINI_COACH_ENABLED) — verify + Cerebras param 복구
- [x] SSM == live Lambda RUNPOD_ANALYZE_URL == 신규 Pod /analyze (machine verify, PIPELINE_FN=sunity-motion-pilot-pipeline)
- [x] Lambda env merge-update; read-back 4-key presence assert (ALL_PRESENT)
- [x] 자체-완결 notification-only 실 LLM smoke — delegate 실행 + 듀얼 coach 빈 섹션 0 (gemini_ok=True, cerebras_ok=True)
- [x] LLM 키 양쪽 live → W-3 escalation 불필요
- [x] 이 evidence 문서 작성 (secret 값 노출 0)

**Open item (Wave 2 로 이월, 본 plan 게이트 아님):** 등록 동작에 대한 line dimension non-None 은 Mode 1 E2E(등록 11 reference 비교)에서 검증. 미등록 'auto' 동작의 line=None 은 정상 폴백.

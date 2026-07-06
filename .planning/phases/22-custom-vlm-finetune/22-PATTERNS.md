# Phase 22: 자체 비전 모델 파인튜닝 (오픈 모델 전환) - Pattern Map

**Mapped:** 2026-07-06
**Files analyzed:** 13 (수정 4 + 신규 9)
**Analogs found:** 12 / 13 (SFT 학습 스크립트만 analog 부재)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/shared/python/sunity_shared/analysis/interfaces.py` (수정: VLM judge Protocol 추가) | interface/contract | request-response | 같은 파일의 `PoseEngine` Protocol 추가 이력 | exact |
| `backend/functions/pipeline/app.py` (수정: shadow 배선 + env-switch) | pipeline orchestrator | event-driven | 같은 파일의 `_ensure_recognizer` + `_apply_vision_veto` seam | exact |
| `backend/runpod_inference/server.py` (수정: vLLM co-serving warmup/health) | GPU server | request-response | 같은 파일 (startup warmup / token auth / BackgroundTasks) | exact |
| `backend/shared/python/sunity_shared/firestore_admin.py` (수정: shadow verdict 로깅 helper 추가) | data access | CRUD write | 같은 파일의 `store_gemini_cache` / `record_unregistered_keyword` | exact |
| 신규: 자체 VLM judge 어댑터 (예: `sunity_shared/analysis/vlm_judge.py`) | adapter (외부모델 경계) | request-response | `analysis/gemini_vision_scorer.py` + `analysis/coach_writer.py` | exact (role+flow) |
| 신규: shadow 비교기 (Gemini vs 자체모델 병행 + verdict diff 로그) | service | event-driven | `pipeline/app.py::_apply_vision_veto` (seam + status enum) | role-match |
| 신규: `backend/evals/phase22/run_bakeoff.py` (Wave 1 bake-off 하네스) | eval script | batch | `backend/evals/phase24/run_sweep.py` | exact |
| 신규: `backend/evals/phase22/assert_gates.py` (D-15 출하 게이트) | eval gate | batch | `backend/evals/phase24/assert_gates.py` | exact |
| 신규: eval fixture 매니페스트 (pairs/dataset) | config/data | file-I/O | `backend/evals/phase18/` (pairs.yaml + assert_baseline.py) | exact |
| 신규: 수집 스크립트 (유튜브/보유자산 → S3 + provenance 로그, D-09) | script | file-I/O | `backend/scripts/upload_phase15_dataset.py` | role-match |
| 신규: 합성 교란 라벨 생성기 (D-10a, 좌표 교란 주입) | pure function module | transform | `analysis/` 순수 모듈 규율 + `evals/phase24/assert_gates.py` 합성 fixture 독트린 | role-match |
| 신규: Gemini 교사 증류 라벨러 (D-10b/c) | adapter script | batch | `analysis/gemini_vision_scorer.py` (File API 업로드/삭제/schema/버전) | exact |
| 신규: Pod vLLM 셋업 스크립트 | infra script | file-I/O | `backend/runpod_inference/setup.sh` | exact |

**No analog:** ms-swift/Unsloth SFT 학습 스크립트 (D-06) — 코드베이스에 학습 코드 0. NotebookLM belle 노트(canonical_refs)의 JSONL 예시가 데이터 포맷 원형. 단 실행 스크립트의 *형태*는 아래 eval 스크립트 패턴(Pod 실행 헤더 docstring + EVAL_OUT_DIR 규율)을 따를 것.

---

## Pattern Assignments

### 1. `interfaces.py` 수정 — VLM judge Protocol 추가 (interface, request-response)

**Analog:** `backend/shared/python/sunity_shared/analysis/interfaces.py` 의 `PoseEngine` Protocol (RTMW pivot 때 백본-무관 Protocol 을 추가한 전례가 그대로 이번 swap 의 본보기)

**Protocol 정의 패턴** (interfaces.py:42-82) — 결정 근거를 docstring 에 박고, 구현체 위치를 명시하고, 백본 direct-import 금지를 선언한다:
```python
class PoseEngine(Protocol):
    """프레임 시퀀스 → PoseFrame 리스트. 미감지 시 NoHumanError.

    RTMW pivot 박제 (2026-06-02, Plan 01-19 / D-17~D-25):
      D-24: 본 모듈은 어떤 백본 구현체(rtmlib/mediapipe/torch/ultralytics) 도
            직접 import 하지 않는다. 다운스트림 분석 레이어는 본 Protocol 에만
            의존하며, 백본 변경 시 재작성 금지.
    구현체 위치:
      backend/shared/python/sunity_shared/analysis/pose_engines/  (운영)
    """
    def estimate(self, frames: np.ndarray, pole_axis: "PoleAxis") -> "list[PoseFrame]": ...
```

**graceful 폴백 구현체 동봉 패턴** (interfaces.py:101-105):
```python
class FallbackCoachWriter:
    """Cerebras 미연결 시의 무해한 폴백 — 문장 생성을 assemble 폴백에 위임."""
    def write(self, context: dict) -> dict:
        return {}
```

적용: 새 VLM judge Protocol (영상+좌표JSON → 통합 리포트) 을 이 파일에 추가. `TYPE_CHECKING` lazy import (interfaces.py:25-26), 무거운 SDK top-level import 0, Gemini/자체모델 양쪽 구현체가 만족해야 함을 D-13 인용으로 명시. `technique.py:77-80` 의 `TechniqueRecognizer` Protocol + `FallbackRecognizer` ("모르면 깎지 않는다") 도 동일 패턴 — recognizer 역할 swap 은 이 Protocol 을 그대로 재사용한다(신규 Protocol 불필요).

---

### 2. `pipeline/app.py` 수정 — shadow 배선 + env-switch 어댑터 선택 (orchestrator, event-driven)

**Analog:** 같은 파일의 recognizer env-switch 와 vision-veto seam. **동시성 주의:** RunPod BackgroundTasks 에서 글로벌 싱글톤 공유 — mutable 사이드카 금지, local-return 만 (app.py:1124-1151 `estimate_with_profile` HIGH-1 v4 박제 참조).

**env-switch + double-checked lock 싱글톤 패턴** (app.py:1058-1090) — shadow/swap 토글의 원형:
```python
_RECOGNIZER: technique.TechniqueRecognizer | None = None
_RECOGNIZER_LOCK = threading.Lock()

def _ensure_recognizer():
    global _RECOGNIZER
    if _RECOGNIZER is not None:
        return _RECOGNIZER
    with _RECOGNIZER_LOCK:
        if _RECOGNIZER is not None:
            return _RECOGNIZER
        if _gemini_enabled():
            # D-16 lazy import — Gemini 모드 진입 시점에만 import.
            from sunity_shared.analysis.gemini_technique_recognizer import (
                GeminiTechniqueRecognizer,
            )
            _RECOGNIZER = GeminiTechniqueRecognizer(cache=cache, ...)
            log.info("Recognizer = GeminiTechniqueRecognizer (env switch ON)")
        else:
            _RECOGNIZER = technique.FallbackRecognizer()
            log.info("Recognizer = Fallback (env switch OFF — default)")
        return _RECOGNIZER
```
토글 규율 (app.py:244-248 주석): "토글은 **pipeline(app.py) 단독 소유** — 어댑터는 토글을 정의/복제하지 않는다(drift → no-op 버그 재발 차단)". 새 `VLM_JUDGE_SHADOW=1` / `VLM_JUDGE_BACKEND=own|gemini` 류 env 도 pipeline 단독 소유로.

**무음실패 금지 status enum 패턴** (app.py:2276-2311, `_apply_vision_veto`) — shadow 비교기의 상태 신호는 이 enum 규율을 복사:
```python
    # status enum (TRUST-08, 무음실패 방지 — Pitfall 5):
    #   · disabled / mode3_held / missing_local_video / missing_reference
    #   · skipped_error — adapter None(키부재/실패) → graceful + WARNING
    #   · not_applicable — 돌았으나 산출 0 (점수 불변)
    #   · applied — 적용
    if not _gemini_vision_veto_enabled():
        return _veto_passthrough(score_result, "disabled")
    if local_video_path is None:
        return _veto_passthrough(score_result, "missing_local_video")
```

**HTTP 위임 패턴 (urllib, requests 의존 0)** (app.py:122-148) — Lambda → Pod vLLM 호출이 필요해지면 이 패턴 복사:
```python
def _delegate_to_runpod(bucket: str, key: str) -> None:
    payload = json.dumps({"bucket": bucket, "key": key}).encode("utf-8")
    req = urllib.request.Request(
        _RUNPOD_URL, method="POST", data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "sunity-motion-pilot/1.0 (+aws-lambda)",  # Cloudflare 봇차단(1010) 회피
            "X-RunPod-Token": _RUNPOD_TOKEN,
        },
    )
    with urllib.request.urlopen(req, timeout=_RUNPOD_TIMEOUT_S) as resp:
        if resp.status not in (200, 202):
            raise RuntimeError(f"runpod {resp.status}: ...")
```

배선 지점: `_apply_vision_veto` (veto 역할, D-13 1순위), `_ensure_recognizer` (recognizer 역할, 2순위), `_call_coach_writer_with_retry`/`_ensure_gemini_coach_writer` (coach 역할, app.py:747-762, D-02 게이트 후). shadow 는 기존 Gemini 호출 결과에 **부가 로깅만** — 판정 경로 무변경이 원칙.

---

### 3. 신규: 자체 VLM judge 어댑터 (adapter, request-response)

**Analog A (구조화 출력 계약):** `backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py`

**frozen dataclass verdict 값객체 + 객관성 명시** (gemini_vision_scorer.py:166-185) — 자체 모델 출력도 동일 계약(점수 필드 영구 부재)으로:
```python
@dataclass(frozen=True)
class VisionVerdict:
    """Gemini 결함-짚기 verdict (객관성 — score 필드 영구 부재).
    ...사람/AI 점수 라벨을 ground truth 로 두는 것은 영구 금지..."""
    primary_fault: str
    severity: str
    differences: tuple   # nested-array 회피로 tuple
```

**response_schema + 고정 enum 단일 owner** (gemini_vision_scorer.py:191-232) — D-01 통합 리포트 JSON 스키마의 시드. 어휘 드리프트 3연속을 enum 강제로 봉인한 이력이 핵심 교훈:
```python
"fault_category": {
    "type": "string",
    "enum": list(FAULT_CATEGORIES),  # vision_veto.FAULT_CATEGORIES 단일 owner — 새 분류 발명 금지
},
```

**프롬프트/스키마 버전 상수** (gemini_vision_scorer.py:75-76) — 학습 데이터 provenance 에도 그대로 필요:
```python
PROMPT_VERSION = "v11.2"  # 변경 이유를 상수 옆 주석에 날짜와 함께 기록
SCHEMA_VERSION = "v8.1"
```

**Analog B (graceful LLM 어댑터 골격):** `analysis/coach_writer.py::CerebrasCoachWriter` (coach_writer.py:213-279)
```python
class CerebrasCoachWriter:
    def __init__(self, model: str = "gpt-oss-120b") -> None:
        self._client = None
        api_key = _load_api_key()
        if not api_key:
            return  # graceful — write() 가 {} 반환, assemble 폴백 사용
        try:
            from cerebras.cloud.sdk import Cerebras  # lazy import
            self._client = Cerebras(api_key=api_key)
        except Exception:  # noqa: BLE001
            log.exception("Cerebras 클라이언트 초기화 실패")

    def write(self, context: dict) -> dict:
        if self._client is None:
            return {}
        try:
            resp = self._client.chat.completions.create(
                ..., response_format={"type": "json_object"}, temperature=0.4,
            )
            data = json.loads(resp.choices[0].message.content)
            return {k: _normalize_entry(v) for k, v in data.items() if isinstance(v, (str, dict))}
        except Exception:  # noqa: BLE001
            log.exception("Cerebras 코칭 생성 실패 — 수치 폴백 사용")
            return {}
```
+ 방어적 응답 정규화 `_normalize_entry` (coach_writer.py:282-320): LLM 이 다른 키를 내도 지원 키만 추출, 나머지 무시. 자체 8B 모델 출력 파서는 반드시 이 수준의 방어를 복사.

**SSM 키 로딩 (env 우선 → SSM)** (gemini_vision_scorer.py:744-758):
```python
def _load_api_key() -> str:
    """env GEMINI_API_KEY 우선, 미설정 시 SSM. 키는 절대 로그 금지(T-20-06)."""
    inline = os.environ.get("GEMINI_API_KEY")
    if inline:
        return inline
    import boto3  # lazy
    param = os.environ.get("GEMINI_API_KEY_PARAM_NAME", "/sunity/motion/gemini-api-key")
    ssm = boto3.client("ssm", region_name="ap-northeast-2")
    return ssm.get_parameter(Name=param, WithDecryption=True)["Parameter"]["Value"]
```
vLLM endpoint URL/토큰도 동일 방식 (`RUNPOD_ANALYZE_URL`/`RUNPOD_AUTH_TOKEN` env 체계 재사용, D-14).

---

### 4. `firestore_admin.py` 수정 — shadow verdict 로깅 helper (data access, CRUD)

**Analog:** 같은 파일의 `store_gemini_cache` (firestore_admin.py:1423-1460) — top-level 컬렉션 + hash 키 + created/updated ms 타임스탬프 + nested-array 사전검증:
```python
_GEMINI_CACHE_COLLECTION = "gemini_cache"  # top-level, uid 비의존 전역 공유

def store_gemini_cache(video_hash: str, payload: dict) -> None:
    # nested-array 정합 검증 ([[firestore-nested-array-flat]])
    if "moments" in payload and payload["moments"]:
        for i, m in enumerate(payload["moments"]):
            if not isinstance(m, dict):
                raise TypeError(f"moments[{i}] must be flat dict ...")
            for k, v in m.items():
                if isinstance(v, (list, tuple)):
                    raise TypeError(f"moments[{i}][{k}] must be scalar ...")
    now_ms = int(time.time() * 1000)
    doc = {**payload, "video_hash": video_hash,
           "created_at": payload.get("created_at", now_ms),  # 첫 기록 시각 보존
           "updated_at": now_ms}
    _doc(f"{_GEMINI_CACHE_COLLECTION}/{video_hash}").set(doc)
```

**멱등 누적 카운트 패턴** (firestore_admin.py:1479-1494, `record_unregistered_keyword`) — shadow 일치/불일치 누적 통계에 그대로:
```python
ref.set({
    "count": _firestore.Increment(1),
    "unique_users": _firestore.ArrayUnion([uid]),   # 멱등 set
    "updated_at": now_ms,
    "created_at": now_ms,  # merge=True 가 첫 기록만 사용
}, merge=True)
```

적용: shadow verdict 비교 로그는 `vlm_shadow/{video_hash}` 류 top-level 컬렉션 (gemini_cache 형제) 또는 `users/{uid}/analyses/{id}` merge — 어느 쪽이든 `set(merge=True)` + flat-dict 검증 + ms 타임스탬프 규율 복사. **(T,J) 행렬류는 반드시 flat 저장** (`complete_analysis` firestore_admin.py:858 이하 참조).

---

### 5. 신규: `backend/evals/phase22/run_bakeoff.py` (eval script, batch)

**Analog:** `backend/evals/phase24/run_sweep.py` — 그대로 복사할 골격.

**repo-오염 방지 산출 경로** (run_sweep.py:46-66):
```python
_EVAL_OUT_ENV = "EVAL_OUT_DIR"
_EVAL_OUT_DEFAULT = "/tmp/sunity_eval_out"

def _resolve_out_dir() -> Path:
    """출력 디렉토리 확정 — repo 안이면 즉시 중단 (baseline 오염 차단)."""
    out = _eval_out_dir()
    repo_root = BACKEND.parent.resolve()
    if out == repo_root or repo_root in out.parents:
        raise SystemExit("[eval-out] ... repo 밖 경로로 설정하라 ...")
    return out
```

**pipeline 동적 로드 + SERIAL 실행** (run_sweep.py:19-20, 77-84, 92-107):
```python
# 동시성 ([[pipeline-not-concurrency-safe-eval-serial]]): _process 는 동시성 비안전 — SERIAL.
def _load_pipeline():
    spec = importlib.util.spec_from_file_location(
        "sunity_pipeline_app", str(BACKEND / "functions" / "pipeline" / "app.py"))
    pipeline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pipeline)
    pipeline._ensure_adapters()
    return pipeline
# fixture 키 스킴: f"fixtures/phase15/{motion}/{fixture}.mp4"
# analysisId 는 영숫자만 — 하이픈 슬러그 금지 (s3keys 정합)
```

**결과 리포트 `_meta` provenance 블록** (run_sweep.py:195-207) — bake-off 리포트/학습셋 매니페스트 공통 양식:
```python
"_meta": {
    "phase": "24", "runId": RUNID, "uid": UID,
    "captured_epoch": int(time.time()),
    "scorer": "phase24_transparent_deduction_tally",
    "run": "serial in-process _process (pipeline-not-concurrency-safe-eval-serial)",
    "objectivity": "fault 라벨=영상 파생. 점수=채점기 결정론 출력 스냅샷(라벨 아님).",
},
```

**cold re-run 결정성 검증** (run_sweep.py:165-186): 같은 입력 2회 실행 → activated set 동일성 비교. bake-off 에서 모델별 결정성(D-15 결정성 게이트) 검증에 동일 구조 사용. 관찰 요약 테이블 + `ALLDONE` 마커 (run_sweep.py:221-236) 도 유지 — Pod 원격 실행 시 완료 감지용.

**Pod 실행 헤더 docstring** (run_sweep.py:22-29): 필요한 env 전체(`RTMW_ONNX_PATH`, `GEMINI_API_KEY` SSM fetch 한 줄 포함)를 모듈 docstring 에 복붙 가능한 형태로 기록. 학습/bake-off 스크립트도 동일하게.

---

### 6. 신규: `backend/evals/phase22/assert_gates.py` (eval gate, batch)

**Analog:** `backend/evals/phase24/assert_gates.py` (D-15 가 이 4종 게이트를 직접 인용 — 확장이지 재발명 아님)

**게이트 파일 골격** (assert_gates.py:1-70):
```python
#!/usr/bin/env python3
"""Phase 24 투명 감점-합산 채점 ND-07 게이트 (pod-free, exit 0 = PASS).

게이트 (importable 함수 — unit-test 가 직접 호출 가능):
  1. check_traceability(breakdowns) — 모든 −point 역산가능...
  2. check_monotonicity() — 합성 편차 sweep → final 비증가...
  5. check_generalization(pairs, breakdowns) — ARTIFACT-GATED.
     실 Pod-생성 artifact 가 있을 때만 실행, 없으면 SKIPPED(실패 아님).
"""
_LAYER = _HERE.parents[1] / "shared" / "python"
if str(_LAYER) not in sys.path:
    sys.path.insert(0, str(_LAYER))
```
핵심 독트린 (docstring 에서 승계할 것): (a) 사람 점수 라벨 금지 — 합성 fixture 는 엔지니어링 기하일 뿐 보유 영상 curve-fit 아님, (b) determinism scope 정직성 — MATH-determinism 과 (V)LM 샘플링 결정성을 명시 분리, (c) ARTIFACT-GATED — Pod artifact 없으면 SKIPPED ≠ FAIL, (d) 수치 밴드 미단언.

Phase 22 추가 게이트: EVAL18 6페어 무회귀(phase18 pairs.yaml 재사용), 전 동작 균등(+미보유 동작), shadow 대비 "Gemini 이상" 증명 — 모두 같은 `check_*` importable 함수 + exit 코드 규약으로.

**fixture self-consistency 패턴:** `backend/evals/phase18/assert_baseline.py:42-92` — pairs.yaml ↔ baseline.json 셋 일치 + known_issue 라벨의 silent-통과 금지. 학습셋 매니페스트 ↔ 실제 적재분 정합 검사에 동일 구조.

---

### 7. 신규: 수집 스크립트 + provenance 로그 (script, file-I/O) — D-09/D-12

**Analog:** `backend/scripts/upload_phase15_dataset.py`

**핵심 규율** (upload_phase15_dataset.py:1-53):
```python
"""Phase 15 dataset 업로드 — ... 비-notified fixtures/ SOURCE 키.

fixtures/ 프리픽스는 uploads/ ObjectCreated notification·lifecycle 대상이 아니므로
업로드 즉시 production S3→SQS→pipeline 트리거가 발화하지 않고 영구 SOURCE 로 보존된다.

CLI:
    python backend/scripts/upload_phase15_dataset.py --dry-run   # 매핑·정규화·스킴 self-check
    python backend/scripts/upload_phase15_dataset.py             # 실 PUT (sunity-motion creds)
"""
BUCKET = "sunity-motion-pilot-videos"
FIXTURES_PREFIX = "fixtures/phase15"
CONTENT_TYPE = "video/mp4"   # 누락 시 octet-stream 저장 (s3-presigned-video-playback 함정)
KEYS_OUT = BACKEND / "scripts" / "phase15_keys.json"  # 산출 매니페스트 → 후속 sweep 이 직접 소비
```
적용: 유튜브 수집분도 **비-notified prefix** (예: `fixtures/phase22/` 또는 `training/`) 로 적재 — production 트리거 미발화. `--dry-run` self-check 필수. 산출 = JSON 매니페스트(키/motion/버킷(label bucket: 정타·fault)/**출처 URL·라이선스 근거 = D-09 provenance**) — `_meta` 블록(analog 5)과 결합. AWS 자격증명 = sunity-motion 키.

---

### 8. 신규: 합성 교란 라벨 생성기 (pure function, transform) — D-10a

**Analog (규율):** `analysis/` 순수 모듈 설계 — numpy 단독 의존, boto3/네트워크 0, `(T, J)` shape 계약 명시 (`validation.py` 의 "순수 함수(boto3/네트워크 무관)" 선언, `_as_tj` 의 shape ValueError). 합성 데이터의 정당성 논리는 phase24 assert_gates docstring:9-10 승계: "합성 fixture 는 엔지니어링 기하(합성 각/notch)일 뿐 보유 영상에 curve-fit 한 타깃이 아니다" — overfit 금지 메모리와 정합.

배치: 알고리즘(교란 주입 수학)은 순수 모듈로 두고, 파일 I/O(JSONL 쓰기)는 스크립트 껍데기로 분리 — `frame_extractor`/`pose_estimator` 어댑터 경계 구조와 동일. `<loc_NNN>` 이산화·키 알파벳 정렬·Null 고정(D-11)은 이 순수 모듈이 단일 owner (enum 단일-owner 규율과 동일 정신, analog 3).

---

### 9. 신규: Gemini shadow 로깅 / 교사 증류 (adapter+script, batch) — D-10b/c, D-13

**Analog:** `gemini_vision_scorer.py` File API 생명주기 (업로드→ACTIVE 폴링→호출→**삭제**)

**업로드+ACTIVE 대기** (gemini_vision_scorer.py:815-843):
```python
def _upload_video(client, local_video_path: str, _hint=None):
    upload_path, tmp_path = _ascii_safe_path(local_video_path)  # 한글 파일명 → ASCII 임시복사
    uploaded = client.files.upload(
        file=upload_path,
        config=genai_types.UploadFileConfig(mime_type=_mime(local_video_path)),
    )
    start = time.monotonic()
    while _state_name(uploaded) == "PROCESSING":
        if time.monotonic() - start > _FILES_TIMEOUT_S:   # 180s
            raise TimeoutError(...)
        time.sleep(_FILES_POLL_S)
        uploaded = client.files.get(name=uploaded.name)
```
**업로드 후 반드시 `client.files.delete(name=...)`** (gemini_vision_scorer.py:1004, 1128, 1332 — 20GB 적체 누수 fix 이력, quick-260706-sis). 증류 배치가 대량 업로드하므로 이 삭제 규율이 필수.

**클라이언트 싱글톤** (gemini_vision_scorer.py:761-780): `_ensure_client()` — lazy import + 모듈 캐시, 실패는 RuntimeError 로 올리고 호출자가 graceful None 변환.

shadow 로깅 배선: 기존 `_apply_vision_veto` 가 이미 만든 verdict 를 **소비 지점에서 복제 저장** (analog 4 의 Firestore helper) — Gemini 재호출 0. 캐시 재사용은 `technique_cache.py`/`VisionVetoCache` (gemini_vision_scorer.py:474) 참조.

---

### 10. `runpod_inference/server.py` 수정 + 신규 vLLM 셋업 (GPU server + infra script)

**Analog:** 같은 파일 + `setup.sh`.

**startup warmup + fail-loud 키 검증** (server.py:139-182):
```python
@app.on_event("startup")
def _warmup() -> None:
    """모델/어댑터 미리 GPU 메모리 로드. 실패해도 첫 /analyze 에서 재시도."""
    try:
        mod = _load_pipeline_module()
        mod._ensure_adapters()
        recognizer = mod._ensure_recognizer()
        if mod._gemini_enabled():
            _load_api_key()  # 키 값 자체는 버림 (검증만 — 로그에 키 노출 X)
    except Exception:  # noqa: BLE001
        log.exception("워밍업 실패 — 첫 요청 처리 시 재시도")
```
vLLM 추가 시: `--workers 1` 유지 (VRAM 점유), health 에 `vllm_loaded` 류 필드 추가 (server.py:185-192 패턴), shared-secret 헤더 인증 (server.py:94-102 `_verify_token` — 토큰 미설정 = 503 비공개 모드).

**setup.sh 멱등 패턴** (setup.sh:23, 57-65): `set -euo pipefail` + "이미 존재하면 skip, 없으면 다운로드" + 마지막에 필요한 env export 전체를 echo 로 안내. vLLM/AWQ 가중치 셋업 스크립트도 동일 골격. **주의:** Pod 재생성 시 start_server.sh 영구 fix 함정 (메모리 [[current-pod-hbpvhedq2bu01i]]) — 기동 스크립트 수정 시 Volume 쪽에 반영.

---

## Shared Patterns

### 어댑터 lazy-import + 캐시 싱글톤
**Source:** `pipeline/app.py:1154-1176` (`_ensure_adapters`), `gemini_vision_scorer.py:761-780`
**Apply to:** 모든 신규 어댑터 (VLM judge, vLLM client, 증류 라벨러)
```python
if _COACH_WRITER is None:
    from sunity_shared.analysis.coach_writer import CerebrasCoachWriter  # lazy
    _COACH_WRITER = CerebrasCoachWriter()
```
top-level 에서 무거운 SDK import 금지 (Lambda 250MB 한도 + 콜드스타트, app.py:89-100 주석).

### 에러 매핑 (경계에서만 broad except)
**Source:** `runpod_inference/server.py:105-136` (`_process_in_background`)
**Apply to:** shadow 비교기, 파이프라인 배선부
```python
except NoHumanError:
    firestore_admin.fail_analysis(uid, analysis_id, models.ERR_NO_HUMAN, ...)
except Exception:  # noqa: BLE001
    log.exception("분석 실패 uid=%s analysisId=%s", uid, analysis_id)
    firestore_admin.fail_analysis(uid, analysis_id, models.ERR_SERVER_ERROR, ...)
```
**shadow 는 절대 분석을 실패시키지 않는다** — coach hook 의 "cosmetic, 분석 절대 실패 안 함" 규율 (app.py:3841 주석) 적용: shadow 예외는 삼키고 log.exception + status 필드 기록.

### 로깅
**Source:** 전 backend 공통
**Apply to:** 모든 신규 Python 파일
```python
log = logging.getLogger()
log.setLevel(logging.INFO)
log.info("upload-url ok uid=%s analysis_id=%s mode=%s", uid, analysis_id, req.mode)  # key=value
log.exception("...")  # except 안에서만. 시크릿 절대 로그 금지.
```

### 모듈/함수 docstring 규율
**Source:** 전 모듈 공통 (`technique.py:1-11`, `run_sweep.py:1-30` 등)
**Apply to:** 모든 신규 파일 — 한국어 docstring 으로 목적 + 결정 근거(D-번호/메모리 [[...]] 인용) + 함정을 모듈 헤더에 기록. `from __future__ import annotations` 첫 줄. 이모지 금지.

### Firestore 쓰기
**Source:** `firestore_admin.py:37-42, 1453-1460`
**Apply to:** shadow verdict 로깅, 학습셋 메타 적재
- `set(payload, merge=True)` + ms epoch 타임스탬프 (`int(time.time() * 1000)`)
- nested array 금지 → flat + 별도 shape 키, 저장 전 `_validate_flat_dict_no_nested_array` 류 사전검증
- 대형 배열 컬렉션 신설 시 index 면제 필요 (메모리 [[firestore-index-entry-limit]])

### eval 실행 규율
**Source:** `evals/phase24/run_sweep.py`, `evals/phase24/assert_gates.py`
**Apply to:** bake-off, SFT 게이트, shadow 비교 리포트
- SERIAL 실행 (동시성 오염 금지), `EVAL_OUT_DIR` repo-밖 강제, ARTIFACT-GATED SKIPPED 의미론, exit 0 = PASS, `_meta` provenance 블록, 사람 점수 라벨 금지 명문화

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| SFT 학습 스크립트 (ms-swift/Unsloth 호출, D-06) | training script | batch | 코드베이스에 모델 학습 코드 0. 데이터 포맷 원형 = NotebookLM belle 노트 JSONL 예시 (CONTEXT canonical_refs). 스크립트 외형(docstring 헤더/env 안내/멱등)은 run_sweep.py + setup.sh 패턴 준용 |

신규 학습 코드 배치 제안: `backend/training/` (backend 하위 — `sunity_shared` import 경로 재사용 가능, `sys.path.insert(0, str(BACKEND / "shared" / "python"))` 패턴 그대로). `/ml` 은 문서 전용 컨벤션이므로 코드 배치 금지.

## Metadata

**Analog search scope:** `backend/shared/python/sunity_shared/{analysis,gemini,judging}/`, `backend/functions/pipeline/`, `backend/runpod_inference/`, `backend/evals/phase18|24|25/`, `backend/scripts/`
**Files scanned:** ~60 listed, 12 read (targeted offsets for >1,000-line files)
**Pattern extraction date:** 2026-07-06

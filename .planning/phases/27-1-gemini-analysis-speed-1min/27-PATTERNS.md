# Phase 27: 분석 속도 개선 (Gemini 라운드트립·후처리 축소) - Pattern Map

**Mapped:** 2026-07-07
**Files analyzed:** 15 (수정 11 + 신규 4)
**Analogs found:** 14 / 15 (production ThreadPoolExecutor 병렬화만 no-analog — 테스트 선례만 존재)

## File Classification

| New/Modified File | New? | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|------|-----------|----------------|---------------|
| `backend/shared/python/sunity_shared/gemini/file_session.py` | NEW | service (세션 객체) | file-I/O + request-response | `gemini/client.py` `GeminiVisionCall.call` (업로드/폴링/delete) + `gemini_vision_scorer.py:1283-1336` (핸들 finally delete) | exact |
| `backend/functions/pipeline/app.py` | modify | pipeline orchestrator | batch | 자기 자신 (`_process` 토폴로지 재배열) + `run_sweep.py` env setdefault | exact (in-place) |
| `backend/shared/python/sunity_shared/gemini/client.py` | modify | adapter | request-response | 자기 자신 (`call()` 시그니처에 preuploaded handle optional 추가) | exact |
| `backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py` | modify | adapter | request-response fan-out | 자기 자신 (`_run_part_frame_fanout` 순차 루프 → 병렬) + still inline (`Part.from_bytes`, RESEARCH Pattern 3) | exact |
| `backend/shared/python/sunity_shared/gemini/coach_writer_v2.py` | modify | adapter | request-response | 자기 자신 (`write()` retry loop — 핸들 주입으로 재업로드 제거) | exact |
| `backend/shared/python/sunity_shared/gemini/scene_finder.py` | modify | adapter | request-response | 자기 자신 (`GeminiVisionCall` 인스턴스화 지점) | exact |
| `backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py` | modify | adapter | request-response | scene_finder 와 동일 핸들 주입 패턴 | role-match |
| `backend/shared/python/sunity_shared/firestore_admin.py` | modify | persistence | CRUD (부분 update) | 자기 자신: `update_analysis_status` (37-42) + `complete_analysis` (858-) + `_validate_dict_only_scalars` (104-128) | exact |
| `backend/shared/python/sunity_shared/models.py` | modify | data contract | — | 자기 자신: `STATUS_*` 상수 블록 (325-339), `VISION_VETO_STATUSES` (76) | exact |
| `app/src/types/analysis.ts` | modify | data contract (TS) | — | 자기 자신: `faultZoomComparisons?` optional (525), `bodyProfile?` (609) — Phase 3/26 optional 필드 선례 | exact |
| `docs/contract.md` | modify | data contract (문서) | — | 3-way lockstep 규율 (analysis.ts 주석이 인용) | exact |
| `app/src/app/analysis/loading.tsx` | modify | screen component | event-driven (onSnapshot) | 자기 자신: `REASSURANCE_COPIES` 로테이터 (51-56, 362-369) + `PROGRESS_PCT/CEIL` (62-86) | exact |
| `app/src/app/analysis/result.tsx` | modify | screen component | event-driven (onSnapshot) | 자기 자신: `selectedZoom` useMemo (905-917) — pending placeholder 분기 추가 지점 | exact |
| `backend/tests/test_stage_timing.py` + `backend/tests/test_fault_zoom_deferred.py` | NEW | test | — | `backend/tests/gemini/test_client.py` fake genai stub (38-100) | exact |
| fake genai session fixture (핸들 카운트/순서 결정론) | NEW | test fixture | — | `test_client.py` `_FakeFiles`/`_FakeModels`/`_patch_genai` | exact |

**핵심 통찰 (RESEARCH 정합):** 이 phase 의 신규 파일은 사실상 `file_session.py` 와 테스트 2~3개뿐. 나머지는 전부 기존 파일의 **자기-analog 재배열** — 각 파일 안에 이미 검증된 패턴(업로드/폴링/delete/graceful/캐시 키/로테이터)이 있고, 그 패턴을 유지한 채 호출 토폴로지만 바꾼다.

---

## Pattern Assignments

### `gemini/file_session.py` — NEW (GeminiFileSession)

**Analog 1:** `backend/shared/python/sunity_shared/gemini/client.py` — 업로드→ACTIVE 폴링→finally delete 의 정본.

업로드 + UploadFileConfig + TypeError stub 폴백 (client.py:210-219):
```python
try:
    uploaded = client.files.upload(
        file=video_path,
        config=genai_types.UploadFileConfig(mime_type=mime_type),
    )
except TypeError:
    # 일부 stub 환경에서 UploadFileConfig 미지원 — kwargs file 단독 호출 박제.
    uploaded = client.files.upload(file=video_path)
except genai_errors.APIError as exc:
    return self._handle_api_error_first(exc, label="files.upload")
```

ACTIVE 폴링 state machine (client.py:246-279, 상수 56-58: `_FILES_PROCESSING_TIMEOUT_S=120.0`, `_FILES_POLL_INTERVAL_S=2.0`):
```python
start = time.monotonic()
state_name = _state_name(uploaded)
while state_name == "PROCESSING":
    if time.monotonic() - start > _FILES_PROCESSING_TIMEOUT_S:
        log.warning("Gemini Files API processing > %ds — graceful skip (model=%s).", ...)
        return None
    time.sleep(_FILES_POLL_INTERVAL_S)
    uploaded = client.files.get(name=uploaded.name)
    state_name = _state_name(uploaded)
if state_name == "FAILED":
    ...return None
```

delete 규율 + 20GB 적체 근거 주석 — **주석까지 복사할 것** (client.py:221-242):
```python
# ── Step 3~4: ... 완료(성공/실패/예외) 후
#    Gemini File API 업로드본을 반드시 삭제한다 — 안 지우면 프로젝트 저장소
#    (file_storage_bytes ~20GB)에 분석 영상이 쌓여, 한도 초과 시 이후
#    files.upload 가 RESOURCE_EXHAUSTED 로 실패한다(실증 2026-07-06 20GB 적체
#    → 분석 간헐 실패). ... 삭제 실패는 best-effort.
try:
    ...
finally:
    _name = getattr(uploaded, "name", None)
    if _name:
        try:
            client.files.delete(name=_name)
        except Exception:  # noqa: BLE001 - 정리 실패는 분석을 막지 않는다
            log.warning("Gemini 업로드 파일 삭제 실패 (graceful): %s", _name)
```

**Analog 2:** `gemini_vision_scorer.py:1283-1336` — 다중 핸들 일괄 finally delete (세션 close() 의 정본):
```python
finally:
    for _handle in (student_uploaded, ref_uploaded, *image_handles):
        _name = getattr(_handle, "name", None)
        if not _name:
            continue
        try:
            client.files.delete(name=_name)
        except Exception:  # noqa: BLE001 - 정리 실패는 분석을 막지 않는다
            log.warning("Gemini 업로드 파일 삭제 실패 (graceful): %s", _name)
```

**Analog 3:** `gemini_vision_scorer.py:815-843` `_upload_video` — 예외-raise 형 업로드 변형 (`_ascii_safe_path` 한글 파일명 처리 포함, 797-812). 세션 내부 업로드는 이 함수를 **재사용**하는 게 정답 (신규 업로드 루프 발명 금지 — RESEARCH "Don't Hand-Roll").

**모듈 헤더/스타일:** `from __future__ import annotations` + 모듈 docstring 에 목적·근거 인용 (client.py:1-15 스타일). lazy import (`from google import genai` 함수 안, D-16 규율 — vision_scorer.py:772 참조).

---

### `backend/functions/pipeline/app.py` (orchestrator 재배열)

**(a) stage-timing 계측** — analog: 기존 key=value 구조 로그 + latency 계측 관례.

구조 로그 (app.py:4154):
```python
log.info("분석 완료 uid=%s analysis_id=%s mode=%s", uid, analysis_id, mode)
```

latency 계측 try/finally (scene_finder.py:171-175 — 동일 패턴이 coach_writer_v2.py:472-483 에도):
```python
start = time.monotonic()
try:
    parsed = call.call(video_path)
finally:
    latency_ms = int((time.monotonic() - start) * 1000)
```

telemetry dict 방출 (vision_scorer `_run_part_frame_fanout` 1685-1692 — `timingsMs` flat dict 의 형태 선례):
```python
duration_ms = int((_now() - start) * 1000)
telemetry = {
    "completedCalls": completed,
    "plannedCalls": planned,
    "uploadCount": 4 if upper_still_handles is not None else 2,
    "durationMs": duration_ms,
    "samplingComplete": completed >= planned,
}
```

**(b) status 갱신 시점 교정** — 현재 연속 write 가 문제의 원점 (app.py:3088-3093, 실제 작업 전에 frame_extraction/pose_analysis 를 연달아 write):
```python
firestore_admin.update_analysis_status(uid, analysis_id, models.STATUS_FRAME_EXTRACTION)
firestore_admin.update_analysis_status(uid, analysis_id, models.STATUS_POSE_ANALYSIS)
```
갱신 함수 자체는 그대로 재사용 (firestore_admin.py:37-42, `set(merge=True)`) — **호출 위치만** 실제 단계 경계(추출 후 / RTMW 후)로 이동. STATUS_COMPARISON write 는 app.py:3172-3174.

**(c) prefetch 겹치기 (D-03)** — 순서 제약의 정본 = WR-07 rebind 주석 (app.py:3142-3152):
```python
# WR-07 (2026-06-08 review): module-global singleton (_RECOGNIZER) 가 SQS
# 메시지 / BackgroundTask 간 공유됨. ... **항상** rebind (None 또는 새 motion_id).
ref_motion_id = meta.get("referenceMotionId")
if hasattr(recognizer, "motion_query_hint"):
    recognizer.motion_query_hint = (
        str(ref_motion_id) if mode == models.MODE_EXPERT and ref_motion_id else None
    )
```
→ recognize future submit 은 이 rebind **이후**여야 함. prefetch 시작점 = `_extract_video_analysis_inputs` 반환 직후 (app.py:3111-3123, `local_video_path` 확보 지점). scene_finder 현행 순차 호출부 = app.py:3132-3135 (`_call_wave1_scene_finder`).

**(d) temp 파일 생명주기** — outer finally 의 unlink (app.py:4155-4166):
```python
finally:
    _safe_unlink_local_video(local_video_path)
    # Phase 20 — Mode1 기준 영상 임시 파일 안전망 cleanup. ... (outer 초기화 → 항상 bound).
    _safe_unlink_local_video(reference_local_video_path)
```
`_safe_unlink_local_video` 정의 = app.py:263. D-06 zoom 사후 렌더 + prefetch future 도입 시 이 finally 에 "future join 후 unlink" + "zoom 렌더 후 unlink" 순서 재배치 (RESEARCH Pitfall 3).

**(e) fault_zoom 사후 분리 (D-06)** — 이동 대상 호출부: `_attach_fault_zoom_comparisons` (정의 app.py:2648, 호출 app.py:3995), `complete_analysis` 호출 (app.py:4131-4153). `_attach_fault_zoom_comparisons` 의 graceful 가드 (2665-2666: 입력 없으면 result 그대로 반환) 의미론을 사후 경로에서도 보존.

**(f) coach B∥Cerebras 동시화** — 현행 순차 호출부 (app.py:3534-3539):
```python
gemini_result = _call_coach_writer_with_retry(
    "gemini", _ensure_gemini_coach_writer().write, coach_context
)
cerebras_result = _call_coach_writer_with_retry(
    "cerebras", _COACH_WRITER.write, coach_context
)
```
둘 다 같은 immutable `coach_context` dict 읽기만 (B3) — 한쪽을 future 로.

---

### `gemini_vision_scorer.py` — fan-out 병렬화 + still PNG inline

**fan-out 순차 루프 (병렬화 대상)** — `_run_part_frame_fanout` (1659-1683). 보존해야 할 의미론이 코드에 전부 명시돼 있음:
```python
for idx in range(planned):
    # wall-clock budget 가드 — 호출 전 elapsed 확인 (fail-closed).
    if _now() - start > wall_budget_s:
        break
    scope = call_plan[idx]
    ...raw_text = _call_gemini_comparison(client, ref_uploaded, student_uploaded, at_seconds, part_scope=scope)
    completed += 1
    if _SCORE_PATTERN.search(raw_text or ""):
        continue  # 점수 누출 샘플 폐기(객관성).
    v = _parse_verdict(raw_text)
    ...
    per_call.append(list(v.differences or ()))
```
불변 계약: (1) fail-closed `completed < planned → resource_limited` (1700-1708), (2) `per_call`/`parsed_verdicts` 순서 = call_plan 인덱스 순서 (`primary = parsed_verdicts[0]` 1720 — as_completed 금지, 인덱스 순 join), (3) `clock=None` 주입 인자 (1614 — 테스트가 clock 을 fake 함, 병렬화 후에도 유지). 병렬 골격은 RESEARCH.md Code Examples "fan-out 병렬 (순서 결정론 보존)" 그대로.

**핸들 주입 kwargs 선례** — `assess_fault_context_video` 시그니처 (1167-1176): `still_student_png`/`still_reference_png`/`still_frame_indices` keyword-only optional, "셋 다 제공될 때만 활성, 일부만 = 미제공 취급" (1239-1251) — `preuploaded_student_handle`/`preuploaded_reference_handle` 추가 시 동일 계약 스타일로.

**캐시 키 버전링 (신규 캐시/키 변경 시)** — `_build_fanout_key` (1253-1266): `VisionVetoCache.build_key(video_hash, model_name, input_granularity, at_seconds, reference_hash, frame_indices)` + 90d038f stale-hit 재발 금지 주석. `PROMPT_VERSION` 은 모듈 globals 에서 lookup (527). inline/handle 전환은 픽셀 불변 → granularity bump 불필요 (RESEARCH Pattern 3 판단 — EVAL18 이 최종 방어).

**still PNG inline (Pattern 3)** — 대체 대상 = `_upload_image` (846-) 호출부 (1294-1298). 신규 코드는 RESEARCH 인용 그대로:
```python
from google.genai import types
still_part = types.Part.from_bytes(data=png_bytes, mime_type="image/png")
```
lazy import 스타일은 기존 `from google.genai import types as genai_types  # lazy` (822, 856) 를 따를 것.

**Client 싱글톤** — `_ensure_client` (761-780, 모듈 전역 `_CLIENT`). 스레드 안전성 미문서 (RESEARCH A1) — 핸들은 `files/...` name 문자열이라 Client 공유 불필요. 병렬 태스크에서 산발 오류 시 스레드별 Client 폴백.

---

### `gemini/client.py` — preuploaded handle optional 인자

수정 지점 = `call()` (167-242). 현행: 업로드(Step 2) → 폴링(Step 3) → generate(Step 4) → finally delete. 핸들 주입 시 Step 2~3 skip + **finally delete 도 skip** (소유권 = 세션). 기존 시그니처 default 무변경 유지 (RunPod server.py 무수정 원칙 — RESEARCH Pattern 1). generate 부 (`_generate_with_retry` 306-417) 는 `contents=[active_file, self.prompt]` (321) 에 핸들 객체가 그대로 들어가므로 무수정.

### `gemini/coach_writer_v2.py` — retry 재업로드 제거

수정 지점 = `write()` retry loop (466-490): attempt 마다 `self._build_call()` 로 1회용 `GeminiVisionCall` 생성 → `call.call(video_path)` 가 매번 재업로드. 핸들 주입 시 retry 는 generate 만 반복 (RESEARCH Pitfall 8). `_build_call` 은 415-429.

### `gemini/scene_finder.py` — 핸들 주입

수정 지점 = `GeminiVisionCall` 인스턴스화 + `call.call(video_path)` (160-175). latency_ms try/finally 와 graceful None 분기 (177-184) 는 무변경.

### `judging/gemini_moment_extractor.py` — 핸들 주입

scene_finder 와 동일 방식. 주의: `TechniqueCache` 키에 model 명 포함 (RESEARCH Flash 표) — D-05 Flash 실험은 `GEMINI_*_MODEL` env override 기존 패턴으로, 캐시 오염 0.

---

### `firestore_admin.py` — `update_analysis_fault_zoom` 신규 함수

**Analog 1 (부분 update 의 정본):** `update_analysis_status` (37-42):
```python
def update_analysis_status(uid: str, analysis_id: str, status: str) -> None:
    """진행 단계 갱신. status 는 models.PIPELINE_SEQUENCE 중 하나."""
    _doc(models.analysis_doc_path(uid, analysis_id)).set(
        {"status": status, "updatedAt": int(time.time() * 1000)},
        merge=True,
    )
```
신규 함수는 `.update({"result.faultZoomComparisons": [...], "result.faultZoomStatus": status, "updatedAt": ...})` field-path 형 (RESEARCH 골격) — `updatedAt` epoch ms 규약 동일.

**Analog 2 (item 검증):** `_validate_dict_only_scalars` (104-128) — zoom comparison item (FaultZoomComparison, flat scalar dict) 검증에 그대로 재사용. **본체 변경 영구 0** (110-113 주석 박제):
```python
for k, v in d.items():
    sub_path = f"{path}.{k}"
    if v is None or isinstance(v, (str, int, float, bool)):
        continue
    raise TypeError(f"{sub_path} must be scalar (firestore-nested-array-flat ...)")
```

**Analog 3 (list[dict] scoped 검증 선례):** `_validate_safety_flags` (288-305) — "각 item 을 `_validate_dict_only_scalars` 로 루프" 형태가 zoom comparisons list 검증과 1:1.

**complete_analysis 수정 (pending 마커):** `payload` 조립부 (914-918) — `result.faultZoomStatus="pending"` 은 result dict 안 scalar 라 기존 검증 통과. faultZoomComparisons 를 complete 시점에 넣지 않는 변경은 호출자(app.py) 쪽.

---

### `models.py` — faultZoomStatus 상수

**Analog:** 상태 문자열 tuple 선례 — `VISION_VETO_STATUSES` (76) / `STATUS_*` 상수 블록 (325-339):
```python
STATUS_UPLOADING = "uploading"
STATUS_QUEUED = "queued"
...
```
`FAULT_ZOOM_STATUS_PENDING/DONE/FAILED = "pending"/"done"/"failed"` + tuple. **status enum(PIPELINE_SEQUENCE) 에는 절대 추가 금지** — 3-way lockstep 비용 (RESEARCH Alternatives 표).

### `app/src/types/analysis.ts` — faultZoomStatus optional 필드

**Analog:** `AnalysisResult` 안 optional 필드 + Python lockstep 주석 선례 (515-525):
```typescript
export type AnalysisResult = ScoreSuppression & {
  ...
  // 문제 부위 확대 비교 carousel (belle 2026-06-21). OPTIONAL (Mode1 + 결함 있을 때만).
  faultZoomComparisons?: FaultZoomComparison[];
```
신규 필드도 같은 자리에 `faultZoomStatus?: 'pending' | 'done' | 'failed'` (string-literal union 관례) + "Python lockstep: models.py + contract.md §" 주석. `tier?` 필드 주석 (451-459) 이 "legacy doc 부재 = 하위호환 처리" 서술의 모범 — 부재 doc 은 comparisons 유무로 판정하는 하위호환 규칙을 주석에 명시할 것.

### `docs/contract.md`

FaultZoomComparison `tier`/`region` 선례: "contract.md 섹션 없음, TS 주석 + Python 방출부 주석 lockstep" (analysis.ts:456-457) — faultZoomStatus 도 동일 저비용 경로 허용. 단 CONTEXT 가 3-way lockstep 를 명시했으므로 planner 가 contract.md 수정 여부를 태스크로 확정할 것.

---

### `app/src/app/analysis/loading.tsx` — 재미 요소 + 진행률 재배분 (D-02/D-07)

**텍스트 로테이션의 정본 (그대로 복제):** `REASSURANCE_COPIES` 상수 (51-56) + 로테이터 hook (362-369):
```typescript
const REASSURANCE_COPIES: readonly string[] = [
  '분석 중이에요',
  '화면을 닫지 마세요',
  '조금만 기다려주세요',
] as const;
const COPY_ROTATE_MS = 4000;
...
const [copyIdx, setCopyIdx] = useState(0);
useEffect(() => {
  const t = setInterval(
    () => setCopyIdx((i) => (i + 1) % REASSURANCE_COPIES.length),
    COPY_ROTATE_MS,
  );
  return () => clearInterval(t);
}, []);
```
D-07 폴스포츠 팁 로테이터 = 이 패턴의 두 번째 인스턴스 (별도 상수 배열 + 별도 interval). 삽입 지점 = 분석 중 렌더 (507-519, `stepLine` 아래). **hook 규칙 주의** — 기존 주석 (360-361): "모든 early return 이전에 호출돼야 React Hook 규칙(같은 순서) 유지".

**진행률 재배분:** `PROGRESS_PCT`/`PROGRESS_CEIL`/`PROGRESS_CREEP_MS` (62-86) — 값만 실측 타이밍에 맞춰 조정, `Math.max` 단조 로직 (374-388) 무변경 (RESEARCH Pitfall 5):
```typescript
setDisplayPct((p) => Math.max(p, base));
const t = setInterval(() => {
  setDisplayPct((p) => (p < ceil ? p + 1 : p));
}, PROGRESS_CREEP_MS);
```

**스타일 제약 (파일 내 실증):** navy 예외 화면 (`NAVY_TOP/NAVY_BOT` 40-41), 음수 letterSpacing 금지 (556-557 iOS SIGABRT 주석), theme 토큰만 사용.

### `app/src/app/analysis/result.tsx` — zoom pending placeholder

**Analog:** `selectedZoom` useMemo (905-917) — `result.faultZoomComparisons ?? []` graceful 소비:
```typescript
const selectedZoom = useMemo<FaultZoomComparison | null>(() => {
  if (!selectedRecord) return null;
  ...
  for (const z of result.faultZoomComparisons ?? []) {
    if (z.tier === 'advisory') continue;
    ...
  }
  return null;
}, [selectedRecord, vetoFaultJoints, result.faultZoomComparisons]);
```
pending 분기 = `result.faultZoomStatus === 'pending'` 일 때 확대카드 자리에 로딩 placeholder (zoom 소비처 = 1716 `zoom={selectedZoom}`). onSnapshot 구독 (`useAnalysisDoc`) 이라 도착 시 자동 rerender — 추가 폴링 0. **파일 겹침 주의:** Phase 26 의 26-02 wrapper/child 분리와 같은 파일 — 실행 순서 조율 (CONTEXT canonical_refs).

---

### 테스트 신규 파일들

**fake genai client 의 정본:** `backend/tests/gemini/test_client.py` (38-100) — 그대로 확장:
```python
class _FakeFiles:
    """Files API stub — upload + get."""
    def __init__(self, *, upload_state="ACTIVE", get_sequence=None):
        self.upload_calls = 0
        self.get_calls = 0
    def upload(self, *, file): self.upload_calls += 1; return _FakeFile(...)
    def get(self, *, name): self.get_calls += 1; ...

def _patch_genai(monkeypatch, files, models):
    monkeypatch.setattr(client_mod.genai, "Client", _fake_client_ctor)
    monkeypatch.setattr(client_mod.time, "sleep", lambda _s: None)  # 폴링 sleep 박제
```
세션 테스트 (D-04 업로드/삭제 카운트) = `_FakeFiles` 에 `delete_calls` 카운터 추가. fan-out 순서 결정론 테스트 = `_run_part_frame_fanout(clock=...)` 주입 인자 활용 (vision_scorer.py:1614 — 이미 테스트용 주입점 존재). timeout fake 는 test_client.py:190 `monkeypatch.setattr(client_mod.time, "monotonic", lambda: next(seq))` 패턴.

**병렬 실행 테스트 선례:** `backend/tests/test_pipeline_body_profile_injection.py:218` — `concurrent.futures.ThreadPoolExecutor(max_workers=2)` 사용 (코드베이스 유일한 ThreadPoolExecutor).

**stage-timing 로그 테스트:** pytest `caplog` 로 `stage_timing ... stage=%s elapsed_s=` 라인 assert (RESEARCH Wave 0 gap 명세).

---

## Shared Patterns

### 1. Gemini graceful degradation (모든 Gemini 수정 파일에 적용)
**Source:** `gemini/client.py:194-205`, `gemini_vision_scorer.py:1218-1234`
```python
except Exception as exc:  # noqa: BLE001 - Pitfall 5 graceful
    log.warning("Gemini client 사용 불가 — video 비교 skipped (graceful): %s", exc)
    return _skipped()
```
규칙: 부가 기능 실패는 분석 비차단. `# noqa: BLE001 - 이유` 주석 필수. prefetch future 예외도 이 규율로 흡수.

### 2. File API delete 규율 (세션/inline 도입 후에도 불변)
**Source:** `client.py:236-242`, `vision_scorer.py:1326-1336` (위 발췌). 세션 도입 = delete 가 "호출마다"→"분석마다"로 바뀔 뿐 누수 0. `_process` outer finally 배치 + NoHuman/NotPole 조기 raise 경로 finally 도달 확인 (RESEARCH Pitfall 2).

### 3. 구조 로그 key=value (신규 계측 전체)
**Source:** `app.py:4154`, `scene_finder.py:179-184`
```python
log.info("분석 완료 uid=%s analysis_id=%s mode=%s", uid, analysis_id, mode)
```
%-lazy 포맷, f-string 금지, 시크릿/영상 바이트 로그 금지.

### 4. Firestore flat/scalar 검증 (D-06 신규 persistence)
**Source:** `firestore_admin.py:45-128` — `_validate_flat_dict_no_nested_array` + `_validate_dict_only_scalars`. 본체 변경 영구 0 — 완화 필요 시 scoped validator 신설 (`_validate_safety_flags` 288-305 가 모범).

### 5. env setdefault 박제 (신규 env 도입 시)
**Source:** `backend/evals/phase25/run_sweep.py:79-93`
```python
# setdefault 이므로 운영자가 명시적으로 export 하면 그 값이 우선한다 ...
# pipeline 로드(_load_pipeline → functions/pipeline/app.py 가 env 소비) 전에
# 설정돼야 하므로 module-level 주입 — RTMW_DETERMINISTIC 과 동일 패턴.
os.environ.setdefault("GEMINI_VISION_VETO_ENABLED", "1")
os.environ.setdefault("GEMINI_MAX_VETO_WALL_S", "300")
```
신규 env (예: `GEMINI_UPLOAD_PREFETCH`) 는 eval 하니스 setdefault + Pod `start_server.sh` 갱신을 **별도 명시 태스크**로 (start_server.sh 는 git 밖 — RESEARCH Pitfall 6).

### 6. 3-way 계약 lockstep
**Source:** `analysis.ts` 주석 관례 (434-459) ↔ `models.py` ↔ `contract.md`. 신규 필드마다 양쪽 주석에 상호 인용 ("Python lockstep: ...").

---

## No Analog Found

| 대상 | Role | Data Flow | 사유 / 대체 근거 |
|------|------|-----------|------------------|
| production 코드의 ThreadPoolExecutor 병렬화 (`_process` 내부) | orchestrator 내 병렬 실행 | fan-out | 코드베이스에 production 선례 0 (유일한 사용 = `tests/test_pipeline_body_profile_injection.py:218`, 테스트 목적). RunPod server 는 `threading.Lock` + BackgroundTasks 만 (`server.py:35,59`). → RESEARCH.md "Code Examples" 의 prefetch/fan-out 골격이 설계 정본. `with ThreadPoolExecutor(...) as pool` 컨텍스트 매니저 + 인덱스 순 join + finally 전 join 을 신규 확립 — 확립 후 이 파일이 향후 analog 가 됨 |

부분-무선례 메모: `firestore_admin` 에 field-path `.update()` 호출 선례가 없음 (전부 `set(merge=True)` 또는 문서 단위) — `.update({"result.faultZoomComparisons": ...})` 는 신규지만 firebase-admin 표준 API 라 리스크 낮음. `set(merge=True)` 는 dict 병합이라 `result` 내부 병합에도 사용 가능 — planner 재량 (merge=True 가 기존 관례에 더 가깝고, 둘 다 nested-array 검증 선행은 동일).

---

## Metadata

**Analog search scope:** `backend/functions/pipeline/`, `backend/shared/python/sunity_shared/{gemini,analysis,judging}/`, `backend/shared/python/sunity_shared/firestore_admin.py`, `backend/tests/`, `backend/evals/phase25/`, `app/src/{app/analysis,types}/`
**Files scanned:** 16 (targeted read) + 3 (grep-only)
**Pattern extraction date:** 2026-07-07
**근거 계보:** 27-CONTEXT.md D-01~D-07 + 27-RESEARCH.md (라인 인용 재검증 완료 — 인용 라인 전부 실코드와 일치 확인)

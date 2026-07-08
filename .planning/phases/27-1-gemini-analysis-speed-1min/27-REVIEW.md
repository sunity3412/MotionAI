---
phase: 27-1-gemini-analysis-speed-1min
reviewed: 2026-07-08T10:48:26Z
depth: standard
files_reviewed: 27
files_reviewed_list:
  - app/src/app/analysis/loading.tsx
  - app/src/app/analysis/result.tsx
  - app/src/components/DeductionDetailSheet.tsx
  - app/src/types/analysis.ts
  - backend/evals/phase25/run_sweep.py
  - backend/functions/pipeline/app.py
  - backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py
  - backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py
  - backend/shared/python/sunity_shared/analysis/technique.py
  - backend/shared/python/sunity_shared/firestore_admin.py
  - backend/shared/python/sunity_shared/gemini/client.py
  - backend/shared/python/sunity_shared/gemini/coach_writer_v2.py
  - backend/shared/python/sunity_shared/gemini/file_session.py
  - backend/shared/python/sunity_shared/gemini/scene_finder.py
  - backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py
  - backend/shared/python/sunity_shared/models.py
  - backend/tests/gemini/fake_genai.py
  - backend/tests/gemini/test_file_session.py
  - backend/tests/gemini/test_session_wiring.py
  - backend/tests/pipeline/test_pipeline_phase8.py
  - backend/tests/pipeline/test_pipeline_phase9.py
  - backend/tests/test_fault_zoom_deferred.py
  - backend/tests/test_pipeline_gemini_integration.py
  - backend/tests/test_pipeline_geminic_wiring.py
  - backend/tests/test_stage_timing.py
  - backend/tests/test_vision_fanout_parallel.py
  - docs/contract.md
findings:
  critical: 2
  warning: 4
  info: 5
  total: 11
status: issues_found
---

# Phase 27: Code Review Report

**Reviewed:** 2026-07-08T10:48:26Z
**Depth:** standard
**Files Reviewed:** 27
**Status:** issues_found

## Summary

Phase 27 (Gemini 분석 속도 1분) 구현을 적대적 관점으로 검토했다. 검증된 것: veto fan-out 은 index-순 join 으로 결정론을 보존한다(테스트가 as_completed 회귀를 잡는 구조 포함); 분석 간 SERIAL 불변(executor 전부 분석-로컬, 모듈 전역 없음); deferred fault_zoom 은 어떤 경로도 재raise 하지 않아 이미 done 인 분석을 failed 로 뒤집을 수 없음; `update_analysis_fault_zoom` 은 field-path 로 zoom 2필드만 갱신; timingsMs/faultZoomStatus 3-way lockstep(analysis.ts ↔ models.py ↔ contract.md) 일치; 앱 normalize() 는 result 를 spread 기반으로 보존해 신규 필드 드롭 없음; legacy doc(faultZoomStatus 부재)은 graceful-hide 유지; pending 고아는 앱 180s 상한 폴백으로 방어됨.

발견된 결함: (1) 새 세션 업로드 경로(`GeminiFileSession.get_or_upload`)가 APIError 외 예외(httpx 전송 오류, OSError)를 전파해 **분석 전체를 server_error 로 죽인다** — "Gemini 오류는 graceful degrade" 불변 위반이자 27 이전 대비 실패 표면 확대. (2) `assess_fault_context_video` 의 self-upload 폴백에서 두 번째 업로드 실패 시 첫 번째 핸들이 orphan 으로 남는 **T-27-06 누수-0 불변 회귀** (구 코드는 부분-업로드도 delete 했음). 그 외 fan-out 병렬화가 wall-budget 을 soft 하게 만든 지연/비용 회귀, prefetch 조기실패 경로의 unlink-while-upload 레이스, eval 하니스의 errorCode 키 불일치 등.

## Critical Issues

### CR-01: 세션 업로드의 비-APIError 예외가 분석 전체를 실패시킨다 (graceful degrade 불변 위반)

**File:** `backend/shared/python/sunity_shared/gemini/file_session.py:137-177` / `backend/functions/pipeline/app.py:3449-3454, 3836-3840`
**Issue:** `GeminiFileSession._upload_and_wait_active` 는 client 생성 실패와 `genai_errors.APIError` 만 graceful(None) 처리한다. 다음은 전부 전파된다:
- `client.files.upload(...)` 의 httpx 전송 계열 예외 (`httpx.ConnectError`, `httpx.ReadTimeout` 등 — google-genai 는 HTTP status 오류만 APIError 로 감싼다)
- `_ascii_safe_path` 의 `shutil.copyfile` OSError (디스크/파일 소실)
- `except TypeError:` 폴백 안의 재-upload 호출에서 발생하는 모든 예외 (이 두 번째 호출은 어떤 except 로도 감싸이지 않음)

`get_or_upload` 는 try/finally 만 있고 except 가 없어 이 예외가 그대로 나간다. `_process` 의 소비 지점 3곳(prefetch join `student_handle_future.result()` app.py:3450, 동기 폴백 3453, 기준 영상 3836)은 전부 무가드 — 예외가 outer 로 전파되어 `lambda_handler` 가 `fail_analysis(server_error)` 를 기록한다. 즉 Gemini File API 로의 일시적 네트워크 블립 하나가 **사용자 분석 전체를 실패**시킨다. Phase 27 이전에는 업로드가 각 모듈(catch-all 보유: scene_finder/veto/coach) 내부에 있어 대부분 graceful 이었다. docstring(file_session.py:107 "타임아웃/FAILED/APIError → None (graceful — 분석 비차단)")이 약속한 계약과 구현이 불일치한다.
**Fix:**
```python
def _upload_and_wait_active(self, video_path: str, mime_type: str) -> Any | None:
    ...
    try:
        client = self._get_client()
    except Exception as exc:
        ...
        return None
    upload_path, tmp_path = _ascii_safe_path(video_path)  # 이 줄도 try 안으로
    try:
        try:
            uploaded = client.files.upload(file=upload_path, config=...)
        except TypeError:
            uploaded = client.files.upload(file=upload_path)
        return self._wait_for_active(client, uploaded)
    except Exception as exc:  # noqa: BLE001 - 업로드 실패는 graceful None (소비처 자체-업로드 폴백)
        log.warning("GeminiFileSession upload 실패 — graceful skip: %s", exc)
        return None
    finally:
        if tmp_path is not None:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
```
(APIError 분기는 broad except 로 흡수돼도 로그 의미 동일. 회귀 테스트: FakeFiles.upload 가 `ConnectionError` 를 raise 할 때 `get_or_upload` 가 None 을 반환하고 `_process` 가 완주하는지.)

### CR-02: assess_fault_context_video self-upload 부분 실패 시 File API orphan — T-27-06(누수 0) 회귀

**File:** `backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py:1334-1337, 1373-1382`
**Issue:** 27-04 리팩토링이 finally delete 대상을 `(student_uploaded, ref_uploaded, *image_handles)` 에서 `self_uploaded` 리스트로 바꿨는데, 리스트 확장이 **두 업로드가 모두 성공한 뒤** 한 번에 일어난다:
```python
student_uploaded = _upload_video(client, student_video_path)
ref_uploaded = _upload_video(client, reference_video_path)   # ← 여기서 raise 하면
self_uploaded.extend([student_uploaded, ref_uploaded])       # ← 도달 못 함
```
`_upload_video` 는 TimeoutError/RuntimeError/APIError 를 흔히 던진다(폴링 실패·FAILED state). 두 번째 업로드가 실패하면 첫 번째(학생 영상) 핸들이 File API 에 orphan 으로 남고, finally 는 빈 `self_uploaded` 만 순회한다. 구 코드는 None-초기화된 두 변수를 직접 순회해 부분-업로드도 정리했다 — 명백한 회귀. 이 경로는 세션 핸들이 None 일 때(=세션 업로드가 이미 flaky 해서 실패한 상황) 발동하므로, 정확히 API 가 불안정할 때마다 orphan 이 쌓인다. 20GB 적체 → RESOURCE_EXHAUSTED → 간헐 분석 실패의 재발 계보(2026-07-06 실증)와 동일 유형이며, Phase 27 자신의 hard invariant(T-27-06 누수 0)를 위반한다.
**Fix:**
```python
student_uploaded = _upload_video(client, student_video_path)
self_uploaded.append(student_uploaded)
ref_uploaded = _upload_video(client, reference_video_path)
self_uploaded.append(ref_uploaded)
```

## Warnings

### WR-01: fan-out 병렬화 후 wall-clock budget 이 soft bound 로 약화 (지연·쿼터 회귀)

**File:** `backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py:1741-1753`
**Issue:** 순차 구현에서는 budget 초과 시 `break` 가 곧바로 반환이었다. 병렬 구현은 (a) budget 초과/`FuturesTimeoutError` 로 `break` 해도 `with ThreadPoolExecutor` 종료가 `shutdown(wait=True)` — `cancel_futures` 없음 — 라서 **큐에 있던 미시작 future 까지 전부 실행·완료를 기다린다** (call 당 HTTP timeout 180s, MAX_VETO_WALL_S=120s 를 수 분 초과 가능). 분석이 SERIAL 이므로 한 건의 지연이 뒤 분석 전체를 밀어낸다 — Phase 27 의 목적(속도)과 정면 배치. (b) 결과가 폐기될 콜이 Gemini 쿼터/비용을 계속 소모한다(D-09 MED-1 의 비용 bound 의도 약화). (c) `fut.result()` 가 APIError 를 재raise 하면 나머지 in-flight 콜도 완주 후 결과 폐기(skipped_error). fail-closed **status** 는 보존되지만 자원 bound 자체가 무력화됐다.
**Fix:** with-block 대신 명시적 executor 관리로 break 경로에서 `pool.shutdown(wait=False, cancel_futures=True)` 호출 (Python 3.9+). in-flight 콜은 어차피 취소 불가하지만 미시작 콜 실행과 반환 지연을 제거한다. 회귀 테스트: budget 소진 시 반환까지의 벽시계가 느린 콜 완료를 기다리지 않는지.

### WR-02: prefetch 조기실패 경로 — 업로드 스레드 생존 중 학생 temp 영상 unlink (불변 주석과 모순)

**File:** `backend/functions/pipeline/app.py:1441-1444, 3468-3486`
**Issue:** app.py:3481-3482 주석은 "temp unlink 는 outer finally — future 생존 중 unlink 0" 을 불변으로 선언하지만, `_extract_video_analysis_inputs_from_local` 이 추출/RTMW 실패(NoHumanError 포함) 시 자신의 except 에서 `local_video_path` 를 **즉시 unlink** 한다(1443). 이 시점은 3468 except 의 `executor.shutdown(wait=True)` 이전 — prefetch 업로드 스레드가 같은 파일을 읽는 중이거나 아직 열기 전일 수 있다. Linux 에선 열린 fd 는 생존하지만, 아직 열지 않은 업로드는 FileNotFoundError → CR-01 경로로 전파되며(future 미회수라 조용히 소멸), 파일을 절반쯤 연 상태의 업로드는 세션에 orphan 시도로 이어질 수 있다. 분석이 어차피 실패하는 경로라 사용자 영향은 낮지만, 선언된 스레드-안전 불변이 실제로 깨져 있어 후속 수정 시 함정이 된다.
**Fix:** `_process` 조기실패 except(3468)에서 `executor.shutdown(wait=True)` 를 **먼저** 보장할 수 있도록, 추출 실패 unlink 를 `_extract_video_analysis_inputs_from_local` 밖으로 옮기거나(예: keep-file-on-error 플래그 후 _process except 에서 join → unlink), 최소한 3481 불변 주석을 실제 동작(추출 실패 시 예외적 unlink 존재)에 맞게 수정.

### WR-03: Mode1 기준 영상 다운로드 실패 시 빈 temp 파일 누수

**File:** `backend/functions/pipeline/app.py:3703-3719`
**Issue:** `ref_tmp` 생성(3706) 후 `_s3.download_file` 이 raise 하면 except 는 `_safe_unlink_local_video(reference_local_video_path)` 를 부르는데, `reference_local_video_path` 는 성공 시(3711)에만 대입되므로 그 시점엔 아직 None — no-op. `ref_tmp.name` 의 빈/부분 파일이 /tmp 에 남는다. 장수명 RunPod Pod 에서 반복 실패 시 적체. (Phase 20 기존 코드 — 이번 diff 밖이지만 검토 대상 파일 내 결함.)
**Fix:**
```python
except Exception:
    log.warning(...)
    _safe_unlink_local_video(ref_tmp.name)  # 생성된 temp 자체를 지운다
    reference_local_video_path = None
```

### WR-04: run_sweep 이 존재하지 않는 `errorCode` 키를 읽어 실패 사유가 리포트에서 소실

**File:** `backend/evals/phase25/run_sweep.py:259-268, 425-427`
**Issue:** `fail_analysis` 는 doc 에 `error: {code, message}` 로 저장한다(firestore_admin.py:1377-1387). `_run_member` 는 `d.get("errorCode")` 를 읽으므로 항상 None — sweep 리포트의 `errorCode` 필드가 영구 None 이고, 관찰 요약 verdict 라인(`f.get('errorCode') or f.get('status')`)은 climb 의 known not_pole 게이트를 `not_pole_motion` 대신 `failed` 로만 표기한다. 게이트 판정 근거(어떤 오류로 막혔는지)가 증빙 아티팩트에서 사라진다.
**Fix:**
```python
err_obj = d.get("error")
rec["errorCode"] = err_obj.get("code") if isinstance(err_obj, dict) else None
```

## Info

### IN-01: GeminiFileSession.close() 가 in-flight 업로드와 미조율 (잠재 누수)

**File:** `backend/shared/python/sunity_shared/gemini/file_session.py:248-268`
**Issue:** `close()` 는 `_handles` 만 비우고 `_inflight` 는 무시한다. close 이후 완료되는 업로드는 `_handles` 에 기록만 되고 아무도 delete 하지 않는다. 현 `_process` 배선은 항상 `shutdown(wait=True)` 후 close 라 미도달이지만, 클래스는 "동시 호출 가능" 을 공표하므로 방어가 없다.
**Fix:** close() 에서 closed 플래그를 세우고, in-flight 완료 시 closed 면 즉시 best-effort delete 하도록 `get_or_upload` finally 에 분기 추가.

### IN-02: `_upload_video`/`_upload_image` — 폴링 TimeoutError 시 ascii-safe temp 복사본 누수

**File:** `backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py:817-884`
**Issue:** `_ascii_safe_path` 복사본 unlink 가 PROCESSING 폴링 루프 **뒤**에 있어, 루프 안 `raise TimeoutError` 경로에서 복사본이 남는다(비-ASCII 파일명 업로드에서만 발동). 기존 코드.
**Fix:** unlink 를 try/finally 로 감싸 폴링 예외 경로 포함 정리.

### IN-03: moment extractor 최종 fallback 모델이 `gemini-2.5-pro` — 운영 규칙(2.5 금지)과 충돌

**File:** `backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py:55-63`
**Issue:** 27-09 가 `GEMINI_MOMENT_MODEL` 우선 체인을 추가하면서 최종 default 를 `"gemini-2.5-pro"` 로 유지했다. 운영 규칙([[gemini-latest-model-versions]] — 2.5 금지)과 어긋나는 stale default. env 미설정 환경(새 Pod 부트스트랩 실수)에서 조용히 구모델로 호출된다.
**Fix:** default 를 `gemini-3.1-pro-preview` 로 갱신하거나 미설정 시 명시 경고 로그.

### IN-04: `_collect_vision_fault_context` — pair 생성 직후 예외 시 still PNG 2장 미정리 창

**File:** `backend/functions/pipeline/app.py:1999-2086, 2117-2119`
**Issue:** `pair.cleanup_paths` unlink 는 2081 finally(assess 호출을 감싼 try)에만 있다. `_build_selected_frame_pair` 성공 후 2011~2047 사이에서 예외가 나면 outer except(2117)가 skipped_error 를 반환하며 PNG 2장이 /tmp 에 남는다. 좁은 창이지만 정리 규율("정리는 생성처와 짝")의 공백.
**Fix:** pair 생성 직후부터를 try/finally 로 감싸 cleanup_paths unlink 를 outer except 경로에도 보장.

### IN-05: zoom pending 타임아웃이 디바이스 시계 vs 서버 updatedAt 차이에 민감

**File:** `app/src/app/analysis/result.tsx:989-1002`
**Issue:** `elapsed = Date.now() - updatedAt` 에서 updatedAt 은 서버(Pod) epoch, Date.now() 는 디바이스 시계. 디바이스가 3분 이상 빠르면 정상 pending 이 즉시 숨김 폴백되고, 느리면 상한이 늘어난다. 180s 보수값이 대부분 흡수하지만 알려진 한계로 기록.
**Fix:** (선택) pending 관측 시각(컴포넌트 마운트 시 Date.now())을 기준으로 한 로컬 타이머와 병용해 skew 영향 제거.

---

_Reviewed: 2026-07-08T10:48:26Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

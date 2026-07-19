# Phase 31: api-visual-correction - Pattern Map

**Mapped:** 2026-07-19
**Files analyzed:** 16 (신규 7 / 수정 9)
**Analogs found:** 15 / 16 (일일 한도 transaction counter 만 부분-무선례)

## File Classification

| New/Modified File | New? | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|------|-----------|----------------|---------------|
| `backend/shared/python/sunity_shared/analysis/visual_gen.py` | 신규 | adapter/service | request-response (외부 HTTP) | `analysis/interfaces.py` + spike `wan_gate_batch.py` | exact (Protocol + HTTP 실증 코드 결합) |
| `backend/functions/visual-request/app.py` | 신규 | controller (HTTP Lambda) | request-response | `functions/playback-url/app.py` | exact |
| `backend/functions/visual-worker/app.py` | 신규 | worker (SQS Lambda) | event-driven | `functions/pipeline/app.py::lambda_handler` + `wan_gate_batch.py` | role-match |
| `backend/functions/pipeline/app.py` | 수정 | pipeline orchestrator | batch (사후 단계 훅) | 자기 자신 `_run_deferred_fault_zoom` (line 3116) | exact |
| `backend/shared/.../analysis/fault_zoom.py` | 수정 | renderer (PIL) | transform | 자기 자신 `_draw_leg_angle`/`_mark`/`_to_crop_px` | exact |
| `backend/shared/.../firestore_admin.py` | 수정 | DB admin | CRUD (partial update) | 자기 자신 `update_analysis_fault_zoom` (line 1138) | exact |
| `backend/shared/.../models.py` | 수정 | contract constants | — | 자기 자신 `FAULT_ZOOM_STATUS_*` (line 402) | exact |
| 페어 적재 helper (visual_gen.py 내 or 형제 모듈) | 신규 | service | file-I/O (S3) | `training/datagen/enumerate_internal.py::consent_allows` + `build_jsonl.py` prefix | exact |
| 실루엣 품질 judge (visual_gen.py 내) | 신규 | adapter | request-response | `sunity_shared/gemini/client.py::GeminiVisionCall` | role-match |
| `backend/template.yaml` | 수정 | IaC | — | 자기 자신 `PlaybackUrlFunction`/`AnalysisQueue`/`PipelineFunction` | exact |
| `backend/tests/phase31/` (conftest + 4 파일) | 신규 | test | — | `backend/tests/phase22/conftest.py` + `test_shadow_wiring.py` | exact |
| `app/src/components/ReferenceCornerSection.tsx` | 신규 | component (섹션) | request-response (props) | `components/ScoreBreakdownSection.tsx` | exact |
| `app/src/components/PoseViewer3D.tsx` | 수정 | component (3D) | transform | 자기 자신 (예약 prop `referenceJoints` line 360) | exact |
| `app/src/lib/referenceMotions.ts` | 수정 | data-source hook | CRUD (onSnapshot) | 자기 자신 `normalize()` + `referenceKeypointReport` guard (line 103) | exact |
| `app/src/app/analysis/result.tsx` | 수정 | screen | request-response | 자기 자신 zoom pending effect (1066) + 섹션 삽입 (1419) | exact |
| `app/src/types/analysis.ts` + `docs/contract.md` | 수정 | contract (TS) | — | 자기 자신 `faultZoomStatus?` (line 572) + `FaultZoomComparison` (439) | exact |

## Pattern Assignments

### `backend/shared/.../analysis/visual_gen.py` (adapter/service, 외부 HTTP)

**Analog 1 — Protocol 경계:** `backend/shared/python/sunity_shared/analysis/interfaces.py`

Protocol 선언 패턴 (lines 19-33, 85-105). VisualGenEngine 은 CoachWriter 와 동형으로 작성 — graceful 폴백 구현체까지 포함:

```python
from __future__ import annotations
from typing import Protocol

class CoachWriter(Protocol):
    def write(self, context: dict) -> dict:
        """{joint_key: 코칭문장}. 키 미설정/실패 시 {} 반환 허용."""
        ...

class FallbackCoachWriter:
    """Cerebras 미연결 시의 무해한 폴백 — 문장 생성을 assemble 폴백에 위임."""
    def write(self, context: dict) -> dict:
        return {}
```

주의: interfaces.py 모듈 docstring 은 "구현은 같은 디렉터리 형제 모듈" 규칙을 명시 (FrameExtractor → frame_extractor.py). VisualGenEngine Protocol 도 interfaces.py 스타일 docstring(결정 근거 D-02 인용)으로 선언하고, Wan 어댑터 구현은 visual_gen.py 에 둔다. 백본 직접 import 금지 규칙(D-24 스타일)을 미러 — 파이프라인은 Protocol 에만 의존.

**Analog 2 — DashScope HTTP 형상:** `.planning/spikes/004-gemini-omni-view-editing/wan_gate_batch.py` (lines 24-56, 87-128 — 2026-07-17 실측)

```python
BASE = "https://dashscope-intl.aliyuncs.com"
CREATE = f"{BASE}/api/v1/services/aigc/video-generation/video-synthesis"
TASK = f"{BASE}/api/v1/tasks/{{task_id}}"

def http_json(url: str, key: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if body else "GET")
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    if body is not None:
        req.add_header("X-DashScope-Async", "enable")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

# create body (검증된 파라미터 — watermark:False 유지):
body = {
    "model": "wan2.7-videoedit",
    "input": {"prompt": PROMPT, "media": [{"type": "video", "url": presigned_url}]},
    "parameters": {"resolution": "720P", "watermark": False,
                   "prompt_extend": False, "seed": 42},
}
# task_id 즉답 → GET TASK 15s 폴링 → "SUCCEEDED" 시 output.video_url (24h 유효 — 즉시 다운로드)
# FAILED/CANCELED/UNKNOWN = 종료 상태. journal 에 task_id 저장 → 크래시 시 재과금 0 재개.
```

stdlib urllib 만 사용 (`requests` 금지 — 프로젝트 관례, pipeline RunPod 위임과 동일). 멱등은 spike 의 journal.json 대신 **Firestore 에 task_id 저장** (RESEARCH Don't Hand-Roll).

**Analog 3 — 품질 judge:** `backend/shared/python/sunity_shared/gemini/client.py::GeminiVisionCall` (line 137~)
구조화 스키마(Pydantic response_schema) + `_generate_with_retry`(line 319) + 실패 시 `None` 반환 계약. 실루엣 judge 는 이 클래스/스타일 재사용 — 자체 CV 코드 금지. 모델 string 은 `gemini-3.5-flash` ([[gemini-latest-model-versions]] — 2.5 금지).

---

### `backend/functions/visual-request/app.py` (controller, request-response)

**Analog:** `backend/functions/playback-url/app.py` — upload-url 보다 근접 (Firestore doc read + 소유/형식 가드 + path-injection 방어까지 포함).

**Imports + module setup 패턴** (lines 26-49):

```python
from __future__ import annotations
import logging, os, re
import boto3
from sunity_shared import firestore_admin, responses
from sunity_shared.auth import AuthError, verify_request
from sunity_shared.s3keys import build_upload_key

log = logging.getLogger()
log.setLevel(logging.INFO)
_BUCKET = os.environ["VIDEO_BUCKET"]
```

**Auth → 파싱 → 검증 → 응답 골격** (lines 97-136):

```python
def lambda_handler(event: dict, _context) -> dict:
    try:
        uid = verify_request(event)
    except AuthError as e:
        return responses.error("unauthorized", e.message, status=401)
    body = responses.parse_json_body(event)
    analysis_id = body.get("analysisId", "")
    if not analysis_id or not isinstance(analysis_id, str):
        return responses.error("bad_request", "analysisId 필수", status=400)
    # analysisId 정합 (uuid hex) — path injection 방지
    if not (analysis_id.isalnum() and len(analysis_id) >= 16):
        return responses.error("bad_request", "analysisId 형식 오류", status=400)
    ...
    log.info("playback-url 발급 uid=%s analysis_id=%s ext=%s", uid, analysis_id, ext)
    return responses.ok({"playbackUrl": url, "expiresInSec": _PLAYBACK_EXPIRES})
```

**소유/존재 가드 → 동일 404 (leak 0)** (lines 65-94 `_handle_reference`): 가드 여러 개를 `guards_ok` 하나로 합쳐 어느 가드가 실패해도 응답 구분 불가하게 — visual-request 의 "analysisId 존재+소유" 검증에 그대로 적용 (uid 는 token 박제라 자기 문서만).

visual-request 고유분: SQS 발행(boto3 `sqs.send_message`) 후 **202 즉답** — API GW 30s 한도 (RESEARCH Pitfall 1). 일일 한도는 아래 `## No Analog Found` 참조.

---

### `backend/functions/visual-worker/app.py` (worker, event-driven)

**Analog:** `backend/functions/pipeline/app.py::lambda_handler` (lines 4816-4867) — SQS 레코드 루프 + 예외→Firestore fail 매핑:

```python
def lambda_handler(event: dict, _context) -> dict:
    processed = 0
    for bucket, key in iter_s3_keys_from_sqs(event):   # worker 는 자체 메시지 파싱으로 대체
        ...
        try:
            _process(bucket, key, uid, analysis_id)
            processed += 1
        except NoHumanError:
            log.info("인체 미감지 uid=%s analysis_id=%s", uid, analysis_id)
            firestore_admin.fail_analysis(uid, analysis_id, models.ERR_NO_HUMAN, ...)
        except Exception:  # noqa: BLE001
            log.exception("분석 실패 analysis_id=%s", analysis_id)
            firestore_admin.fail_analysis(uid, analysis_id, models.ERR_SERVER_ERROR, ...)
    return {"processed": processed}
```

차이점 (RESEARCH 정합): worker 의 실패는 `fail_analysis`(분석 전체 실패) 가 아니라 **`update_analysis_rotation(status='failed')` 부분 업데이트** — 분석 문서는 이미 done, 조용한 폴백 (D-08). 폴링/다운로드 본체는 wan_gate_batch.py 패턴 (위 visual_gen 절). 24h URL 은 즉시 S3 다운로드 후 `_signed_get` 스타일 자체 presign (pipeline line 1258-1263):

```python
def _signed_get(bucket: str, key: str) -> str:
    return _s3.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key},
        ExpiresIn=_PLAYBACK_EXPIRES,   # 7일 — playback-url 재발급 경로와 정합, S3 key 도 저장
    )
```

**모더레이션 재시도 상한 1회** 후 failed 확정 (RESEARCH 안티패턴 — 결정적 차단은 재시도 무의미).

---

### `backend/functions/pipeline/app.py` — 실루엣 사후 단계 훅 (수정)

**Analog:** 같은 파일 `_run_deferred_fault_zoom` (lines 3116-3158) — 사후 단계의 정확한 골격. 실루엣용 `_run_deferred_silhouette` 는 이 함수를 이름만 바꿔 복제:

```python
def _run_deferred_fault_zoom(*, render, uid: str, analysis_id: str) -> None:
    """complete_analysis 이후 zoom 렌더 → update_analysis_fault_zoom 부분 업데이트.
    분석은 이미 complete 이므로 어떤 경로도 재raise 하지 않는다(부가 기능 비차단 규율)"""
    try:
        comparisons = render()
        firestore_admin.update_analysis_fault_zoom(
            uid, analysis_id, comparisons or [],
            status=models.FAULT_ZOOM_STATUS_DONE,
        )
    except Exception:  # noqa: BLE001 - 부가 기능 실패는 분석 비차단 (graceful)
        log.warning("fault-zoom 사후 렌더 실패 — failed 마킹 시도 ... uid=%s analysis_id=%s",
                    uid, analysis_id)
        try:
            firestore_admin.update_analysis_fault_zoom(
                uid, analysis_id, [], status=models.FAULT_ZOOM_STATUS_FAILED,
            )
        except Exception:  # noqa: BLE001 - failed write 실패 = pending 고아 가능
            log.exception("... — pending 고아 가능 (앱 시간 상한 폴백 방어) uid=%s ...")
```

**S3 put + item 방출 패턴:** `_render_fault_zoom` (lines 2851-2879) — key 네이밍/ContentType/flat scalar 주석 스타일:

```python
skey = f"results/{uid}/{analysis_id}/{key_prefix}{c['joint']}.png"
_s3.put_object(Bucket=bucket, Key=skey, Body=c["png"], ContentType="image/png")
item = {
    "joint": c["joint"],
    "imageUrl": _signed_get(bucket, skey),
    # scalar str 이라 _validate_dict_only_scalars flat 제약 통과. TS lockstep: ...
    "tier": tier,
}
```

실루엣 S3 key = `results/{uid}/{analysis_id}/silhouette_{joint}.png` (동일 prefix — Firestore rules/S3 정책 경계 재사용). 프레임 소스는 `cached_user_frames` 파라미터 선례 (line 2764, 2798-2801) — 재추출 금지.

---

### `backend/shared/.../analysis/fault_zoom.py` — 목표각 화살표 (수정)

**Analog:** 같은 파일의 드로잉 3종. 화살표 함수는 `_draw_leg_angle` 을 모델로 신설 (`_draw_target_arrow` 류).

**좌표 변환 단일 출처** — `_to_crop_px` (lines 468-484). 신규 드로잉도 반드시 이 함수 경유 (중복 공식 금지):

```python
def _to_crop_px(xy, left, top, side, w, h) -> tuple[int, int]:
    """정규화 좌표 → crop 박스 내 출력 픽셀 변환 단일 출처.
    [0,_OUT-1] clamp — 캔버스 밖 좌표 방어."""
    s = max(1, int(side))
    ax = int(round((xy[0] * w - left) / s * _OUT))
    ay = int(round((xy[1] * h - top) / s * _OUT))
    return max(0, min(_OUT - 1, ax)), max(0, min(_OUT - 1, ay))
```

**드로잉 함수 계약** — `_draw_leg_angle` (lines 615-664): in-place PIL draw, `_BRAND` 색·width 4 선, degenerate 좌표 가드 후 **성공 여부 bool 반환** (실패 시 드로잉 생략 — 오인 방지), 한글 금지(숫자/기호만 — 폰트 회피), 채점 무접촉 명시:

```python
def _draw_leg_angle(img, pelvis_px, left_px, right_px, angle_deg) -> bool:
    """... 성공 여부를 반환 — display 전용, 채점 무접촉. 한글 없음(선/호/숫자만)."""
    if (math.hypot(lx - px, ly - py) < _MIN_LEG_VEC_PX
            or math.hypot(rx - px, ry - py) < _MIN_LEG_VEC_PX):
        return False
    draw = ImageDraw.Draw(img)
    draw.line([pelvis_px, left_px], fill=_BRAND, width=4)
    ...
    draw.arc([px - r, py - r, px + r, py + r], start=a1, end=a2, fill=_BRAND, width=3)
```

**수치 배지 스타일** — `_mark` (lines 605-611): `_BRAND` 사각 배경 + 흰 텍스트, 폭 추정 8px/글자. 화살표의 목표각 라벨도 `_deficit_label` 재사용.

**화살표 데이터 소스 (신규 산출 0):** DeductionRecord 의 `measuredValue`(현재)/`baselineValue`(목표 180/160/reference)/`unit='deg'` + `JointScore.direction`('extend'|'flex'|'raise'|'lower'|'open'|'close') — fault_zoom 은 이미 `deficits: dict[str, float]` 를 받는다 (RESEARCH Code Examples).

---

### `backend/shared/.../firestore_admin.py` — 부분 업데이트 함수 2종 (수정)

**Analog:** `update_analysis_fault_zoom` (lines 1138-1187) — 시그니처·검증·field-path update 전부 복제:

```python
def update_analysis_fault_zoom(uid, analysis_id, comparisons: list[dict], status: str) -> None:
    """... result.faultZoom* **두 필드만** field-path 로 부분 갱신 — zoom 외 어떤
    result.* 필드도 사후 변경 금지. merge 는 배열 교체 의미가 모호 → 명시적 field-path
    `.update()` 채택."""
    if status not in models.FAULT_ZOOM_STATUSES:
        raise ValueError(f"faultZoomStatus must be one of {list(models.FAULT_ZOOM_STATUSES)}, got {status!r}")
    _comparisons = list(comparisons or [])
    for i, c in enumerate(_comparisons):
        _validate_dict_only_scalars(c, path=f"faultZoomComparisons[{i}]")
    _doc(models.analysis_doc_path(uid, analysis_id)).update({
        "result.faultZoomComparisons": _comparisons,
        "result.faultZoomStatus": status,
        "updatedAt": int(time.time() * 1000),
    })
```

신규 `update_analysis_silhouette` / `update_analysis_rotation` 은 동형: (1) status 를 models 상수 tuple 로 강제, (2) dict payload 는 `_validate_dict_only_scalars` (lines 104-128 — **validator 본체 무수정 재사용**, nested list/dict 전면 거부), (3) `.update()` field-path + `updatedAt` ms epoch 갱신, (4) rotation 은 `task_id`/`s3Key` scalar 도 함께 저장 (멱등 journal + 7일 후 재서명 경로).

**models.py 상수 선례** (lines 402-408):

```python
FAULT_ZOOM_STATUS_PENDING = "pending"
FAULT_ZOOM_STATUS_DONE = "done"
FAULT_ZOOM_STATUS_FAILED = "failed"
FAULT_ZOOM_STATUSES = (FAULT_ZOOM_STATUS_PENDING, FAULT_ZOOM_STATUS_DONE, FAULT_ZOOM_STATUS_FAILED)
```

`SILHOUETTE_STATUSES`/`ROTATION_STATUSES` 동형 신설 + 3-way lockstep 주석 (models.py line 399-401 주석 스타일 그대로).

---

### 페어 적재 helper (신규, file-I/O)

**Analog 1 — 동의 게이트:** `backend/training/datagen/enumerate_internal.py::consent_allows` (lines 87-110):

```python
def consent_allows(doc, *, bulk_approval, cutoff_ms=BELLE_BULK_APPROVAL_CUTOFF_MS) -> bool:
    opt = (doc or {}).get("learningOptIn")
    if opt is False:
        return False
    if opt is True:
        return True
    # 부재(None) — strict 기본.
    if not bulk_approval:
        return False
    created = _created_at_ms(doc)
    return created is not None and created < cutoff_ms
```

Phase 31 페어는 전부 신규 생성물 → **`bulk_approval=False` 경로만** (learningOptIn===True 엄격, CONTEXT canonical ref). 이 함수를 import 재사용하거나 동형 strict 검사 + 단위 테스트 고정 (RESEARCH Security — 동의 우회 방지).

**Analog 2 — S3 레이아웃:** `backend/training/datagen/build_jsonl.py` (lines 40-41):

```python
CANONICAL_PREFIX = "training/phase22/jsonl/"
PARTIAL_PREFIX = "training/phase22/jsonl_partial/"
```

Phase 31 = `training/phase31/pairs/` + manifest 에 consent provenance 기록 (RESEARCH Open Q2 — 얼굴 블러 여부는 checkpoint:decision).

---

### `backend/template.yaml` — 신규 Lambda 2 + SQS (수정)

**Analog:** 같은 파일 3개 리소스 조합.

- **visual-request 함수** ← `PlaybackUrlFunction` (lines 161-185): Timeout 10, s3/ssm 명시 Statement, HttpApi POST 이벤트. SSM 정책은 반드시 명시 Statement (lines 140-146 주석 — SAM `SSMParameterReadPolicy` leading-slash 버그).
- **visual-worker 함수** ← `PipelineFunction` (lines 259-294): Timeout 900, SSM dynamic reference env (`"{{resolve:ssm:/sunity/motion/dashscope-api-key}}"` — line 274 `RUNPOD_ANALYZE_URL` 스타일), SQS 이벤트 `BatchSize: 1`.
- **visual 큐** ← `AnalysisQueue` + `AnalysisDLQ` (lines 83-97): `VisibilityTimeout: 960` (worker Timeout 900 보다 길게 — line 87 주석), DLQ `maxReceiveCount: 3`. S3 QueuePolicy 는 불필요 (발행자가 Lambda — `sqs:SendMessage` 를 request 함수 Policies 에 추가).
- **LogGroup 30일** ← lines 297-324 선례 (WR-05 교훈 — 신규 함수마다 LogGroup 누락 금지).

---

### `backend/tests/phase31/` (신규, test)

**Analog 1 — conftest:** `backend/tests/phase22/conftest.py` (19줄 전체) — sys.path 주입 패턴:

```python
import sys
from pathlib import Path
_BACKEND = Path(__file__).resolve().parents[2]
_LAYER = _BACKEND / "shared" / "python"
for _p in (_LAYER, ...):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
```

**Analog 2 — Firestore/네트워크 mock:** `backend/tests/phase22/test_shadow_wiring.py` (lines 18-57) — `_FakeSnapshot`/`_FakeDoc` registry stub, "실 Firestore/네트워크/Pod 미접촉 (LOCAL ONLY)" docstring 관례. DashScope mock 은 urllib 레벨 monkeypatch (visual_gen 이 순수 stdlib 라 용이 — RESEARCH Wave 0).

테스트 4파일 = `test_visual_gen.py` / `test_silhouette_flow.py` / `test_visual_request.py` / `test_pair_store.py` (RESEARCH Validation Architecture 표 그대로).

---

### `app/src/components/ReferenceCornerSection.tsx` (신규, component)

**Analog:** `app/src/components/ScoreBreakdownSection.tsx` (lines 1-75) — 결과 화면 섹션 컴포넌트의 표준형:

```tsx
// 헤더 주석: 근거 결정/피드백 인용 + "토큰만 사용 (CLAUDE.md §4). 이모지 0. 라이트 전용."
import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, layout, radius, spacing, typography } from '../theme';
import type { DeductionBreakdown } from '../types/analysis';

export function ScoreBreakdownSection({
  breakdown,
  limitNotice,
  onRecordPress,
}: {
  breakdown: DeductionBreakdown;
  /** 미전달 시 렌더 diff 0 (다른 소비처/legacy 무회귀). */
  limitNotice?: string;
  onRecordPress?: (recordIndex: number) => void;
}) {
  return (
    <View style={styles.card}>
      ...
```

named export + inline prop 타입 + "미전달 시 렌더 diff 0" optional prop 서술 + `styles.card` 하단 StyleSheet.create. 렌더 가드는 caller(result.tsx) 소유 (line 6 주석 관례). 빈/실패 상태는 PoseViewer3D 빈 상태 패턴 (아래) — **에러 배너/토스트 금지 (D-08)**, failed 는 카드 자체 숨김.

---

### `app/src/components/PoseViewer3D.tsx` — referenceJoints 활성화 (수정)

**Analog:** 같은 파일 예약석 (lines 356-373) — 활성화 지점이 이미 표시돼 있음:

```tsx
interface PoseViewer3DProps {
  joints: number[][][] | null; // (T, J, 3) — reshapePose3dData 결과
  // Wave 2 = user-only viewer (HIGH-3). caller 가 omit. 예약 prop.
  referenceJoints?: number[][][] | null;
  ...
}
export function PoseViewer3D({
  joints,
  // referenceJoints: 본 wave 미사용 (HIGH-3). 의도적으로 destructure 만.
  referenceJoints: _referenceJoints,
  ...
```

`_referenceJoints` → 실사용으로 전환 + 반투명 중첩 SkeletonMesh 2벌 (line 182 `SkeletonMeshProps` 재사용). **빈 상태 패턴** (lines 379-401): 데이터 부재 시 return null 이 아니라 섹션 내 친절한 안내 문구 (빈 회색 박스 금지 — belle 디바이스 finding #3 박제). mode3 reference 부재 시 "내 자세 단독 뷰어 강등" 도 이 관례 (조용한 강등, RESEARCH Pitfall 6). 파일 상단 line 77 주석 주의: RTMW joints3d 는 y≈0 (수직 분산이 Z 축) — reference 중첩 시 동일 축 재매핑 적용.

---

### `app/src/lib/referenceMotions.ts` — joints3d normalize (수정)

**Analog:** 같은 파일 `referenceKeypointReport` null-guard idiom (lines 103-130) — 신규 필드 방어 파싱의 모범:

```tsx
// Phase 12 Wave 0B — referenceKeypointReport null-guard.
// 누락 시 undefined 유지 (구 doc 호환).
const refKpRaw = raw.referenceKeypointReport;
let referenceKeypointReport: KeypointReport | null | undefined;
if (refKpRaw && typeof refKpRaw === 'object') {
  const kr = refKpRaw as Record<string, unknown>;
  referenceKeypointReport = {
    version: typeof kr.version === 'string' ? kr.version : '1.0',
    data: Array.isArray(kr.data) ? (kr.data as number[]) : [],
    ...
  };
} else if (refKpRaw === null) {
  referenceKeypointReport = null;
}
```

flat 배열 reshape 선례는 `deriveMeanAngles` (lines 42-68) — 길이가 J 배수 아니면 undefined (조용한 강등). joints3d 도 flat + jointKeys + frames 메타로 저장돼 있으므로 동일 검증 후 흘린다. 주의 (line 137 주석): T-scaled per-frame array 를 reference doc 에 **추가하지 않는다** (40k index-entry 한도) — 읽기만.

---

### `app/src/app/analysis/result.tsx` — 참고코너 삽입 + 상태 소비 (수정)

**Analog 1 — 사후 상태 소비 + pending 고아 방어** (lines 1056-1083). silhouetteStatus/rotationStatus 도 이 effect 를 복제:

```tsx
// 'pending' = 렌더 중 → placeholder / 'done' = 카드 표시 / 'failed'/부재(legacy) = 숨김.
const [zoomPendingTimedOut, setZoomPendingTimedOut] = useState(false);
useEffect(() => {
  setZoomPendingTimedOut(false);
  if (result.faultZoomStatus !== 'pending') return;
  const elapsed = Date.now() - (updatedAt ?? 0);
  const remaining = FAULT_ZOOM_PENDING_TIMEOUT_MS - elapsed;
  if (remaining <= 0) { setZoomPendingTimedOut(true); return; }
  const t = setTimeout(() => setZoomPendingTimedOut(true), remaining);
  return () => clearTimeout(t);
}, [result.faultZoomStatus, updatedAt]);
const zoomPending = result.faultZoomStatus === 'pending' && !zoomPendingTimedOut;
```

onSnapshot 구독으로 자동 rerender — **추가 폴링 0** (안티패턴, line 1059 주석). D-06 "완료 알림" = 이 onSnapshot 카드 갱신이 전부 (push 인프라 없음).

**Analog 2 — 섹션 삽입 지점** (lines 1419-1432): `showBreakdownSection` 렌더 직후가 "점수 내역 아래" (D-09). 삽입 형식:

```tsx
{showBreakdownSection && result.deductionBreakdown != null && (
  <>
    <Text style={styles.sectionTitle}>점수 계산 내역</Text>
    <ScoreBreakdownSection breakdown={result.deductionBreakdown} ... />
  </>
)}
{/* 신규 참고코너는 이 아래 — 조건부 렌더 + sectionTitle + 근거 주석 블록 */}
```

주의: 실제 순서는 콤보 부분 점수(line 1436)·참고 지표(line 1811) 등 후속 섹션과의 관계를 planner 가 결정 — "채점과 시각적 분리" (D-09) 가 레이아웃 기준.

---

### `app/src/types/analysis.ts` + `docs/contract.md` (수정 — 계약 3면)

**Analog 1 — 상태 필드 선언** (lines 563-572). 신규 `silhouetteStatus?`/`rotationStatus?` 는 이 주석 형식(값 의미/부재=legacy/Python lockstep 명시)을 그대로:

```tsx
// Phase 27 SPD-04 (D-06) — zoom 사후 분리 로딩 상태. ...
// 'pending'=렌더 중(카드 자리 placeholder) / 'done'=도착(faultZoomComparisons 유효)
// / 'failed'=실패(카드 숨김 — pending 고아 방지). 부재(legacy doc)=... 하위호환.
// Python lockstep: models.py FAULT_ZOOM_STATUSES + firestore_admin.update_analysis_fault_zoom
// + contract.md faultZoomStatus 절.
faultZoomStatus?: 'pending' | 'done' | 'failed';
```

**Analog 2 — item 인터페이스** — `FaultZoomComparison` (lines 439-473): 실루엣 카드 item(imageUrl/joint/상태) 타입은 이 인터페이스의 필드별 JSDoc + "list 필드 금지(Firestore flat 제약)" 서술을 미러. contract.md 는 faultZoomStatus 절을 선례로 신규 절 작성.

## Shared Patterns

### 인증 (전 신규 HTTP Lambda)
**Source:** `backend/functions/upload-url/app.py` lines 33-38 / `playback-url/app.py` lines 97-102
```python
try:
    uid = verify_request(event)
except AuthError as e:
    return responses.error("unauthorized", e.message, status=401)
```

### 응답 봉투 + 에러 매핑
**Source:** `sunity_shared/responses.py` 사용례 (upload-url lines 40-71)
성공 `responses.ok(payload)` / 실패 `responses.error(code, 한국어_message, status=...)`. ValidationError 는 `e.code/e.message/e.http_status` 를 그대로 매핑. 경계에서만 `except Exception: # noqa: BLE001` + `log.exception` → server_error 500.

### Firestore flat scalar 강제
**Source:** `firestore_admin.py::_validate_dict_only_scalars` (lines 104-128)
신규 방출 dict 전부 이 validator 라우팅 — **validator 본체 무수정** ([[firestore-nested-array-flat]] 영구). nested 필요 시 flat 배열 + 메타(count) 분리 (`anchors`+`anchorCount` 선례, analysis.ts lines 491-492).

### 조용한 폴백 (D-08 — backend/app 양면)
**Backend source:** `pipeline/app.py::_run_deferred_fault_zoom` (lines 3137-3158) — 사후 실패는 재raise 0, failed 마킹만.
**App source:** `result.tsx` lines 1060-1083 — failed/legacy = 숨김, pending 은 updatedAt 기준 시간 상한 폴백.

### Presign + 24h 만료 방어
**Source:** `pipeline/app.py::_signed_get` (1258-1263) + `playback-url/app.py::_sign_get` (52-62)
외부 벤더 URL 은 Firestore 저장 금지 — 즉시 S3 다운로드 후 자체 presign(7일) + **S3 key 동시 저장** (myVideoKey 선례 — 만료 후 playback-url 재발급 경로 재사용).

### 시크릿 주입
**Source:** `template.yaml` lines 271-275 — SSM dynamic reference env:
```yaml
Environment:
  Variables:
    RUNPOD_ANALYZE_URL: "{{resolve:ssm:/sunity/motion/runpod-analyze-url}}"
```
DashScope 키 = `"{{resolve:ssm:/sunity/motion/dashscope-api-key}}"`. 하드코딩·로그 노출 금지.

### 학습 동의 게이트
**Source:** `enumerate_internal.py::consent_allows` (87-110) — Phase 31 은 strict 분기만 (learningOptIn===True).

### 로깅
**Source:** 전 handler 공통 — `log = logging.getLogger(); log.setLevel(logging.INFO)`, key=value 구조 (`log.info("... uid=%s analysis_id=%s", uid, analysis_id)`), `log.exception` 은 except 내부만, 시크릿 로깅 금지.

### 주석/사양 인용 관례
전 파일 공통 — 모듈 docstring 에 계약 절 인용(`contract.md §2`), 결정 근거 인용(`D-08`, `31-CONTEXT`, 메모리 `[[...]]`), 한국어 why-주석. 계약 필드엔 3면 lockstep 명시 주석 필수.

## No Analog Found

| File/Feature | Role | Data Flow | Reason |
|------|------|-----------|--------|
| 일일 생성 한도 counter (D-07, visual-request 내) | service | CRUD (transaction) | firestore_admin 에 transaction 선례 없음 (기존은 전부 `.set(merge)`/`.update()`). firebase-admin 표준 `firestore.transactional` 로 신설 — `_doc()` 헬퍼/`models.*_path` 경로 규칙과 ms-epoch `updatedAt` 관례는 update_analysis_fault_zoom 에서 차용. 파일럿 규모라 정합성 요구 낮음 — planner 재량으로 transaction 없이 read-increment 허용 판단 가능 |

부분-무선례 메모: 이미지 편집 모델(`wan2.7-image-pro`) 파라미터는 미실측 (RESEARCH A1) — wan_gate_batch.py 는 **영상** endpoint 실증. plan 첫 태스크 스모크로 해소 (RESEARCH 권고와 정합).

## Metadata

**Analog search scope:** `backend/functions/`, `backend/shared/python/sunity_shared/`, `backend/training/datagen/`, `backend/tests/phase22/`, `app/src/{components,lib,app/analysis,types}/`, `.planning/spikes/004-gemini-omni-view-editing/`
**Files scanned:** 20 (targeted read 15 + grep survey 5)
**Pattern extraction date:** 2026-07-19

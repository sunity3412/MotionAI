"""동시 분석 오염 회귀 — 분석별 값이 공유 싱글턴을 통과하지 않는다 (2026-09-20).

## 무엇을 지키는 테스트인가

`_RECOGNIZER`(pipeline/app.py)는 모듈 전역 싱글턴이고, 그것이 물고 있는
`GeminiMomentExtractor` 도 프로세스에 1개뿐이다. 2026-09-20 이전에는 분석별 값을
그 공유 객체의 **속성에 써 두고** 나중에 되읽었다:

    app.py       recognizer.motion_query_hint = "ref-invert"    # 쓰기
      ...        프레임 추출 + RTMW 추론 (실측 warm 51.3초 / cold 176.6초)
    recognizer   motion_query = self.motion_query_hint or "auto" # 읽기

그 51~177초 창에서 다른 분석이 같은 속성을 덮어쓰면, 앞 분석이 **뒤 분석의 동작 이름으로**
채점된다. 예외도 로그도 남지 않고 숫자만 그럴듯하게 나온다. 창이 실제로 열린다는 근거:
Pod 은 `uvicorn --workers 1` + FastAPI `BackgroundTasks`(= Starlette 스레드풀)이고,
Lambda 쪽 pipeline 함수에는 `ReservedConcurrentExecutions` 가 없다. 학원은 정의상
동시 업로드다.

WR-07(2026-06-08)은 이 값을 **항상 rebind** 하게 해서 *직렬* 누수(앞 분석 hint 상속)만
막았다. 쓰기와 소비 사이의 창은 그대로였다.

수리: 분석별 값은 전부 `recognize()` 의 키워드 인자다. 값이 호출 스택을 벗어나지 않으므로
직렬 누수도 동시 오염도 **구조적으로** 불가능하다.

## 이 파일이 필요한 이유

수리 시점에 리포에는 "분석 2건이 같은 전역 객체를 동시에 만진다"를 태우는 테스트가
**0건**이었다. 이름이 비슷한 test_pipeline_body_profile_injection.py 조차 두 worker 가
각자 별개 인스턴스를 만들어서, 사이드카가 되살아나도 통과한다. 그래서 다음 세션이
"방어선 있음"으로 오독했다. 여기서는 **하나의 인스턴스를 두 스레드가 공유**한다.
"""

from __future__ import annotations

import ast
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from sunity_shared.analysis.gemini_technique_recognizer import (
    GeminiTechniqueRecognizer,
)
from sunity_shared.analysis.skeleton import JOINT_KEYS


_REPO = Path(__file__).resolve().parents[2]
_PIPELINE_APP = _REPO / "backend" / "functions" / "pipeline" / "app.py"

# 두 스레드가 창 안에서 확실히 겹치도록 하는 상한. 겹치지 못하면 테스트는
# 통과가 아니라 timeout 으로 실패해야 한다 (조용한 위음성 차단).
_BARRIER_TIMEOUT_S = 10.0


def _angles() -> np.ndarray:
    """(T, 8) 관절각. 값은 채점이 아니라 경로만 태우므로 상수면 충분하다."""
    return np.full((12, len(JOINT_KEYS)), 165.0, dtype=float)


@dataclass
class _StubMoment:
    moment_key: str
    timestamp_seconds: float
    confidence: float
    frame_index: int = 0


class _OverlappingExtractor:
    """호출 두 건을 창 한가운데서 반드시 겹치게 만드는 extractor 스텁.

    실제 파이프라인에서 이 자리는 Gemini File API 왕복이고, 그 앞에는 프레임 추출 +
    RTMW 추론이 있다. 수리 전에는 바로 이 구간이 '쓰기와 읽기 사이'였다.
    """

    def __init__(self, barrier: threading.Barrier, raw_response: str) -> None:
        self._barrier = barrier
        self._raw_response = raw_response
        self._lock = threading.Lock()
        self.seen: list[tuple[str, str]] = []  # (thread_name, motion)

    def extract_key_moments_with_response(
        self, video_uri: str, motion: str, *, preuploaded_handle=None
    ) -> tuple[list, str]:
        with self._lock:
            self.seen.append((threading.current_thread().name, motion))
        # 여기서 두 분석이 만난다. 수리 전이라면 이 지점 이후에 상대가 덮어쓴
        # 공유 속성을 읽게 된다.
        self._barrier.wait(timeout=_BARRIER_TIMEOUT_S)
        return [_StubMoment("hold", 1.0, 0.9)], self._raw_response


def _run_two_analyses(target) -> list:
    """서로 다른 분석 2건을 진짜 스레드 2개로 동시에 돌린다."""
    results: dict[str, object] = {}
    errors: dict[str, BaseException] = {}

    def _worker(tag: str) -> None:
        try:
            results[tag] = target(tag)
        except BaseException as exc:  # noqa: BLE001 - 스레드 예외를 본 스레드로 옮긴다
            errors[tag] = exc

    threads = [
        threading.Thread(target=_worker, args=(tag,), name=f"analysis-{tag}")
        for tag in ("A", "B")
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=_BARRIER_TIMEOUT_S + 5.0)
        assert not t.is_alive(), f"{t.name} 가 끝나지 않았다 — 창에서 겹치지 못했다"
    assert not errors, f"스레드 예외: {errors}"
    return [results["A"], results["B"]]


# ─────────────────────────────────────────────────────────────────────────────
# 1. 살아 있는 동시성 — 한 인스턴스를 두 스레드가 공유한다
# ─────────────────────────────────────────────────────────────────────────────


def test_concurrent_analyses_keep_their_own_motion_hint() -> None:
    """분석 A 와 B 가 같은 recognizer 싱글턴을 동시에 써도 서로의 동작 이름을 받지 않는다.

    수리 전 구조(`recognizer.motion_query_hint` 속성)였다면, 창 안에서 나중 쓰기가
    이긴 값 하나를 두 분석이 함께 읽어 **둘 중 하나가 남의 동작으로 채점**된다.
    """
    barrier = threading.Barrier(2)
    extractor = _OverlappingExtractor(barrier, '{"moments": []}')
    # ★ 인스턴스는 하나다. 이것이 이 테스트의 전부다.
    recognizer = GeminiTechniqueRecognizer(extractor=extractor, cache=None)

    # ref-power-spin 만 EXTEND 관절을 가진다(criteria yaml 실측: 무릎 2개). 짝을 이렇게
    # 고른 이유 = 오염되면 **채점 기준 자체가** 달라지는 쌍이라야 회귀가 눈에 보인다.
    hints = {"A": "ref-power-spin", "B": "ref-climb"}

    def _analyze(tag: str):
        return recognizer.recognize(
            _angles(), frames=f"/tmp/does-not-exist-{tag}.mp4", motion_hint=hints[tag]
        )

    profile_a, profile_b = _run_two_analyses(_analyze)

    # 각 분석이 자기 동작으로 확정됐는가.
    assert profile_a.motion_id == "ref-power-spin", (
        f"분석 A 가 motion_id={profile_a.motion_id!r} 로 확정됐다 — "
        "동시 분석 B 의 동작 이름에 오염됐다."
    )
    assert profile_b.motion_id == "ref-climb", (
        f"분석 B 가 motion_id={profile_b.motion_id!r} 로 확정됐다 — "
        "동시 분석 A 의 동작 이름에 오염됐다."
    )
    # joint_expectations 는 동작별 criteria yaml 에서 온다 — 여기가 채점에 닿는 자리다
    # (dimensions.line_score 가 profile.expects_extension 을 읽는다).
    extend_a = {k for k, v in profile_a.joint_expectations.items() if v == "extend"}
    extend_b = {k for k, v in profile_b.joint_expectations.items() if v == "extend"}
    assert extend_a, "ref-power-spin 은 EXTEND 관절을 가져야 한다 (yaml 전제 확인)"
    assert not extend_b, "ref-climb 은 EXTEND 관절이 없어야 한다 (yaml 전제 확인)"

    # extractor 가 본 질의도 스레드별로 자기 것이어야 한다 (= Gemini 프롬프트가 안 섞였다).
    seen = dict(extractor.seen)
    assert seen == {"analysis-A": "ref-power-spin", "analysis-B": "ref-climb"}, seen


def test_concurrent_analyses_keep_their_own_unregistered_hook() -> None:
    """미등록 수집 콜백도 분석별이다 — 원장에 남의 uid 가 찍히면 안 된다.

    이 hook 은 caller uid 를 클로저로 물고 있다. 오염되면 TERM-DATA-01 의
    unique_users promotion 임계가 다른 학생의 uid 로 왜곡된다.
    """
    barrier = threading.Barrier(2)
    extractor = _OverlappingExtractor(barrier, '{"moments": []}')
    recognizer = GeminiTechniqueRecognizer(extractor=extractor, cache=None)

    recorded: dict[str, list[str]] = {"A": [], "B": []}
    rec_lock = threading.Lock()

    def _make_hook(tag: str):
        def _hook(keyword: str, video_hash: str) -> None:
            with rec_lock:
                recorded[tag].append(keyword)

        return _hook

    # 두 분석 모두 미등록 동작이라 case 3 (수집) 경로를 탄다.
    keywords = {"A": "우리학원-A동작", "B": "우리학원-B동작"}

    def _analyze(tag: str):
        return recognizer.recognize(
            _angles(),
            frames=f"/tmp/does-not-exist-{tag}.mp4",
            motion_hint=keywords[tag],
            unregistered_hook=_make_hook(tag),
        )

    profile_a, profile_b = _run_two_analyses(_analyze)

    assert profile_a.category == "unregistered"
    assert profile_b.category == "unregistered"
    assert recorded["A"] == ["우리학원-A동작"], recorded
    assert recorded["B"] == ["우리학원-B동작"], recorded


def test_concurrent_analyses_keep_their_own_raw_response() -> None:
    """객관성 2차 가드가 검사하는 raw 응답도 분석별이다.

    수리 전에는 `extractor._last_raw_response` 사이드카를 Gemini 왕복 **뒤에** 되읽었다.
    그 창에서 남의 더러운 응답을 읽으면 내 분석이 ValueError 로 죽는다(가드는 Step 4 의
    try 바깥이라 예외가 그대로 전파된다). 반대로 내 더러운 응답이 남의 가드를 통과해
    빠져나갈 수도 있다.
    """
    barrier = threading.Barrier(2)
    # A 는 깨끗한 응답, B 는 좌표가 섞인 응답 — 가드가 B 만 거절해야 한다.
    dirty = '{"moments": [], "note": "left_knee at x=120.5, y=430.2"}'

    class _PerThreadExtractor(_OverlappingExtractor):
        def extract_key_moments_with_response(
            self, video_uri: str, motion: str, *, preuploaded_handle=None
        ):
            with self._lock:
                self.seen.append((threading.current_thread().name, motion))
            self._barrier.wait(timeout=_BARRIER_TIMEOUT_S)
            raw = dirty if motion == "ref-climb" else '{"moments": []}'
            return [_StubMoment("hold", 1.0, 0.9)], raw

    extractor = _PerThreadExtractor(barrier, "")
    recognizer = GeminiTechniqueRecognizer(extractor=extractor, cache=None)
    hints = {"A": "ref-invert", "B": "ref-climb"}

    outcomes: dict[str, str] = {}
    lock = threading.Lock()

    def _analyze(tag: str):
        try:
            profile = recognizer.recognize(
                _angles(),
                frames=f"/tmp/does-not-exist-{tag}.mp4",
                motion_hint=hints[tag],
            )
        except ValueError:
            with lock:
                outcomes[tag] = "rejected"
            return None
        with lock:
            outcomes[tag] = "passed"
        return profile

    _run_two_analyses(_analyze)

    assert outcomes == {"A": "passed", "B": "rejected"}, (
        f"가드 판정이 분석별로 갈리지 않았다: {outcomes} — "
        "raw 응답이 두 분석 사이에서 섞였다는 뜻이다."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. 구조 가드 — 같은 모양이 다시 들어오면 즉시 깨진다
# ─────────────────────────────────────────────────────────────────────────────


def test_pipeline_never_writes_attributes_on_objects_it_does_not_own() -> None:
    """pipeline/app.py 는 self 가 아닌 객체의 속성에 대입하지 않는다.

    이 파일이 만지는 객체(recognizer / extractor / 어댑터)는 전부 모듈 전역 싱글턴이다.
    `<이름>.<속성> = ...` 이 한 줄 들어오는 순간 이 결함이 그대로 재생된다 —
    2026-09-20 에 없앤 두 줄이 정확히 그 모양이었다
    (`recognizer.motion_query_hint = ...`, `recognizer.unregistered_hook = ...`).

    분석별 값은 **인자로** 넘겨라. 선례 = `preuploaded_handle`(27-04), `timings_ms`.
    """
    tree = ast.parse(_PIPELINE_APP.read_text(encoding="utf-8"))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            targets = [node.target]
        else:
            continue
        for target in targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id != "self"
            ):
                offenders.append(
                    f"app.py:{node.lineno} — {target.value.id}.{target.attr} = ..."
                )
    assert not offenders, (
        "공유 객체의 속성에 대입하고 있다 (동시 분석 오염 재발):\n  "
        + "\n  ".join(offenders)
        + "\n분석별 값은 함수 인자로 넘겨라."
    )


def test_retired_motion_hint_attribute_cannot_be_assigned() -> None:
    """생성 이후 `motion_query_hint` 대입은 조용한 no-op 이 아니라 AttributeError 다.

    비-frozen dataclass 는 선언되지 않은 이름에도 대입이 **성공**한다. 필드를 그냥
    지우면 옛 호출자가 말없이 아무 일도 안 하게 되는데, 그건 이 수리가 없앤 고장과
    같은 종류다 (조용히 틀린 분석).
    """
    recognizer = GeminiTechniqueRecognizer(cache=None)
    with pytest.raises(AttributeError) as exc:
        recognizer.motion_query_hint = "ref-invert"
    assert "motion_hint" in str(exc.value), "에러 메시지가 대체 경로를 알려줘야 한다"


def test_unregistered_hook_is_write_once() -> None:
    """hook 은 '합성 시점 상수'로는 정당하고, '분석마다 갈아끼우기'로는 금지다."""
    def _hook(keyword: str, video_hash: str) -> None:  # pragma: no cover - 호출 안 함
        raise AssertionError("이 테스트는 hook 을 호출하지 않는다")

    # 생성 시점 주입은 허용 (pipeline/app.py 의 _ensure_recognizer 가 이 경로를 쓴다).
    recognizer = GeminiTechniqueRecognizer(cache=None, unregistered_hook=_hook)
    assert recognizer.unregistered_hook is _hook

    # 생성 이후 대입은 금지.
    with pytest.raises(AttributeError):
        recognizer.unregistered_hook = _hook


def test_recognizer_never_reads_retired_sidecars() -> None:
    """읽기측 부활 차단 — 인식기가 extractor 의 '마지막 것 기억' 속성을 되읽지 않는다.

    쓰기측 부활은 아래 test_extractor_has_no_last_call_sidecars 가, pipeline 의 공유객체
    속성 대입은 test_pipeline_never_writes_attributes_on_shared_objects 가 막는다.
    남는 구멍이 **읽기측**이었다 — `getattr(self.extractor, "_last_motion_name", "")` 를
    되돌려 놓아도 스텁에 그 속성이 없어 폴백이 먹으므로 단위 테스트가 전부 통과한다
    (2026-09-20 변이 검증에서 실제로 확인됐다). 그래서 소스를 직접 본다.

    주석/docstring 의 언급은 허용한다 — 왜 없앴는지는 남아야 한다. 코드에서의 접근만 막는다.
    """
    retired = {"_last_raw_response", "_last_motion_name"}
    targets = [
        _REPO / "backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py",
        _REPO / "backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py",
    ]
    offenders: list[str] = []
    for path in targets:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            # obj._last_xxx  형태의 직접 접근
            if isinstance(node, ast.Attribute) and node.attr in retired:
                offenders.append(f"{path.name}:{node.lineno} — .{node.attr}")
            # getattr(obj, "_last_xxx", ...) 형태
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "getattr"
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and node.args[1].value in retired
            ):
                offenders.append(
                    f"{path.name}:{node.lineno} — getattr(..., {node.args[1].value!r})"
                )
    assert not offenders, (
        "폐기된 사이드카 속성을 코드에서 접근하고 있다 (동시 분석 오염 재발):\n  "
        + "\n  ".join(offenders)
        + "\n값은 extract_key_moments_with_response 의 반환값으로 받아라."
    )


def test_extractor_has_no_last_call_sidecars() -> None:
    """GeminiMomentExtractor 에 '마지막 호출 기억' 필드가 없다.

    `_last_raw_response` / `_last_motion_name` 은 프로세스에 1개뿐인 인스턴스에
    호출마다 값을 덮어쓰고 나중에 getattr 로 되읽는 구조였다. 되읽는 쪽이
    `extract_key_moments_with_response` 의 반환값을 쓰도록 바뀌었으므로 필드도 없다.
    """
    from sunity_shared.judging.gemini_moment_extractor import GeminiMomentExtractor

    extractor = GeminiMomentExtractor()
    for retired in ("_last_raw_response", "_last_motion_name"):
        assert not hasattr(extractor, retired), (
            f"{retired} 가 살아 있다 — 분석 간 공유 사이드카가 되돌아왔다."
        )
    assert hasattr(extractor, "extract_key_moments_with_response")

"""quick-260808-jix — compare_align 순수부 리팩터 회귀 게이트 (GPU 없음, elbow 픽스처).

픽스처 align.json(.planning p35 data — Pod RTMW 15fps 산출 영구본)의 저장 kp/score
에서 정렬 곡선·짝 재선정을 **재계산**해 라이브러리 이동이 알고리즘을 바꾸지
않았음을 고정한다.

실측 근거 (2026-08-08, 리팩터 직후 캘리브레이션 — 실측 > 이전 결정):
  · curveRefSec 재계산 = 저장값과 max|Δ| 0.0000s (4자리 반올림 kp 로도 DTW 곡선
    완전 재현 — plan 의 0.2s 허용치를 큰 마진으로 통과).
  · pairs 재선정 = r00/r02/r03 저장값과 **정확히 일치** (0.000s). r01 만 2.133s
    이동 — 저장 kp 반올림(4자리)·score 반올림(3자리)이 자세거리를 ~10% 흔들어
    min*1.15 밴드 소속(이산 선택)을 뒤집는 케이스. **리팩터 전 원본 코드도 같은
    rounded 입력에서 동일하게 10.200 을 산출함을 실측** (git 503a5f8~1 원본 재실행
    — 이동 코드 ≡ 원본 코드, 차이는 순수 양자화 유래). 따라서 r01 은 저장값
    비교가 아니라 **재계산 결정값 핀**(10.200)으로 회귀를 고정한다.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from sunity_shared.analysis import compare_align as ca

_REPO = Path(__file__).resolve().parents[3]
_FIXTURE_DIR = _REPO / ".planning" / "phases" / "35-server-rendered-comparison-video" / "data" / "elbow"


@pytest.fixture(scope="module")
def elbow():
    align = json.load(open(_FIXTURE_DIR / "align.json"))
    doc = json.load(open(_FIXTURE_DIR / "doc.json"))
    Fu, Fr = align["userFrames"], align["refFrames"]
    ukn = np.asarray(align["userKp"], dtype=float).reshape(Fu, 17, 2)
    usc = np.asarray(align["userScore"], dtype=float)
    rkn = np.asarray(align["refKp"], dtype=float).reshape(Fr, 17, 2)
    rsc = np.asarray(align["refScore"], dtype=float)
    fu = ca.pose_feature(ukn, usc)
    fr = ca.pose_feature(rkn, rsc)
    D = np.linalg.norm(fu[:, None, :] - fr[None, :, :], axis=2)
    curve = ca.smooth_curve(ca.dtw_path(D), len(fu))
    return {
        "align": align, "doc": doc, "D": D, "curve": curve,
        "ukn": ukn, "usc": usc, "rsc": rsc,
    }


def test_curve_recompute_matches_stored(elbow):
    """pose_feature→D→dtw_path→smooth_curve 재계산 == 저장 curveRefSec (≤0.2s).

    실측 0.0000s — 반올림 kp 로도 곡선 완전 재현. 0.2s 는 plan 허용치 유지."""
    stored = np.asarray(elbow["align"]["curveRefSec"], dtype=float)
    recomputed = elbow["curve"] / ca.FPS
    assert recomputed.shape == stored.shape
    assert float(np.abs(recomputed - stored).max()) <= 0.2


def test_pairs_recompute_stable_minima_match_stored(elbow):
    """짝 재선정 재실행 — 안정 최소값 3건(r00/r02/r03)은 저장값과 ≤0.2s.

    r01 은 양자화 민감 케이스 (모듈 docstring) — 별도 핀 테스트."""
    records = elbow["doc"]["result"]["deductionBreakdown"]["records"]
    pairs = ca.select_pairs(
        records, elbow["D"], elbow["curve"],
        elbow["ukn"], elbow["usc"], elbow["rsc"],
    )
    assert set(pairs) == {"r00", "r01", "r02", "r03"}
    stored = elbow["align"]["pairs"]
    for rid in ("r00", "r02", "r03"):
        d = abs(pairs[rid]["refVideoSec"] - stored[rid]["refVideoSec"])
        assert d <= 0.2, f"{rid}: |Δ|={d:.3f}s"
        # atVideoSec 는 doc record 그대로 각인.
        assert pairs[rid]["atVideoSec"] == pytest.approx(stored[rid]["atVideoSec"])


def test_pair_r01_quantization_pin_and_selection_invariant(elbow):
    """r01 — 이동 코드 ≡ 원본 코드 실측 핀(10.200) + 선택 불변식.

    저장값(8.067, Pod full-precision)과 다른 것은 양자화 유래 (원본 코드도 rounded
    입력에서 10.200 산출 실측). 재계산 결정값을 핀해 향후 알고리즘 변형을 잡는다.
    선택 불변식: 선정 프레임은 정렬창 안 + 자세거리 min*1.15 밴드 안."""
    records = elbow["doc"]["result"]["deductionBreakdown"]["records"]
    pairs = ca.select_pairs(
        records, elbow["D"], elbow["curve"],
        elbow["ukn"], elbow["usc"], elbow["rsc"],
    )
    assert pairs["r01"]["refVideoSec"] == pytest.approx(10.2, abs=1e-9)

    # 선택 불변식 — 전 pair 공통 (밴드/창 이탈 = 알고리즘 훼손 신호).
    D, curve = elbow["D"], elbow["curve"]
    fu_len, fr_len = D.shape
    for rid, p in pairs.items():
        ui = int(np.clip(round(p["atVideoSec"] * ca.FPS), 0, fu_len - 1))
        center = int(round(curve[ui]))
        lo, hi = max(0, center - int(2 * ca.FPS)), min(fr_len, center + int(2 * ca.FPS) + 1)
        ri = int(round(p["refVideoSec"] * ca.FPS))
        assert lo <= ri < hi, f"{rid}: 짝 프레임이 정렬창 밖"
        window = D[ui, lo:hi]
        dmin = float(window.min())
        assert D[ui, ri] <= dmin * 1.15 + 1e-9, f"{rid}: min*1.15 밴드 밖"


def test_select_pairs_skips_records_without_moment(elbow):
    """atVideoSec 없는 record = 스킵 (fail-closed — p35 현행), moments 주입 시 포함."""
    no_moment = [{"recordId": "r90:split_angle", "criterion": "split_angle"}]
    assert ca.select_pairs(
        no_moment, elbow["D"], elbow["curve"],
        elbow["ukn"], elbow["usc"], elbow["rsc"],
    ) == {}

    injected = ca.select_pairs(
        no_moment, elbow["D"], elbow["curve"],
        elbow["ukn"], elbow["usc"], elbow["rsc"],
        moments={"r90": {"atVideoSec": 1.0}},
    )
    assert set(injected) == {"r90"}
    assert injected["r90"]["atVideoSec"] == 1.0

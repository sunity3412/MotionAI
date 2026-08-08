"""Phase 34 수술 ① — align_quality 승인 코퍼스 캘리브레이션 게이트 (quick-260808-r82).

승인 5편 align.json(GPU 산출 실물, .planning/phases/35-server-rendered-comparison-
video/data — 리포 커밋본)이 **전건 PASS** 임을 릴리스 조건으로 고정한다(T-34-02:
FAIL 남발 → 렌더 부착 소멸 방어). 임계를 조이는 어떤 변경도 이 게이트를 먼저
통과해야 한다.

구버전 포맷 벤치 슬롯(pdshape/realupload — refKp 없음)은 대상 외: 운영 스테이지의
build_align 은 항상 신포맷을 생산한다 (data/README.md 실측). belle-FAIL 측(doc
127a2a90) 검증은 GPU 전용이라 Pod 스윕 명시 이월 (POD-VERIFY.md).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sunity_shared.analysis import compare_align

_REPO = Path(__file__).resolve().parents[3]
_DATA = _REPO / ".planning" / "phases" / "35-server-rendered-comparison-video" / "data"
# 승인 5편 (활성 렌더 슬롯) — 신포맷 보유 실측 (README "검증 결과" 절).
_APPROVED = ("elbow", "kipup", "pdshapefault", "peterpan", "powerspin")


def _approved_aligns() -> list[tuple[str, dict]]:
    out = []
    for m in _APPROVED:
        p = _DATA / m / "align.json"
        if p.exists():
            out.append((m, json.loads(p.read_text(encoding="utf-8"))))
    return out


def test_approved_corpus_all_pass():
    aligns = _approved_aligns()
    if not aligns:
        pytest.skip("승인 align.json 부재 (리포 데이터 미체크아웃 환경)")
    for name, align in aligns:
        ok, lines = compare_align.align_quality(align)
        assert ok, f"승인 {name} 이 align_quality FAIL — 임계 회귀:\n" + "\n".join(lines)


# ── 합성 FAIL 2형상 (게이트가 실제로 잡는지 — 흡수 아님 확인) ─────────────────

def _pose_row(shift_limbs: float = 0.0) -> list[float]:
    """정적 17-keypoint 정규화 좌표 1행 flat. shift_limbs 로 사지만 x 이동."""
    pts = {
        "nose": [0.5, 0.1], "left_eye": [0.48, 0.09], "right_eye": [0.52, 0.09],
        "left_ear": [0.46, 0.1], "right_ear": [0.54, 0.1],
        "left_shoulder": [0.42, 0.25], "right_shoulder": [0.58, 0.25],
        "left_elbow": [0.38, 0.4], "right_elbow": [0.62, 0.4],
        "left_wrist": [0.36, 0.55], "right_wrist": [0.64, 0.55],
        "left_hip": [0.45, 0.55], "right_hip": [0.55, 0.55],
        "left_knee": [0.44, 0.75], "right_knee": [0.56, 0.75],
        "left_ankle": [0.44, 0.92], "right_ankle": [0.56, 0.92],
    }
    limbs = {"left_elbow", "right_elbow", "left_wrist", "right_wrist",
             "left_knee", "right_knee", "left_ankle", "right_ankle"}
    row: list[float] = []
    for j in compare_align.J17:
        x, y = pts[j]
        if j in limbs:
            x += shift_limbs
        row.extend([x, y])
    return row


def _synthetic_align(tu=30, tr=40, conf=0.9, ref_limb_shift=0.0) -> dict:
    fps = 15.0
    return {
        "fps": fps,
        "userFrames": tu, "refFrames": tr,
        "userKp": [_pose_row() for _ in range(tu)],
        "refKp": [_pose_row(shift_limbs=ref_limb_shift) for _ in range(tr)],
        "userScore": [[conf] * 17 for _ in range(tu)],
        "refScore": [[conf] * 17 for _ in range(tr)],
        "curveRefSec": [round(min(t / fps, (tr - 1) / fps), 4) for t in range(tu)],
        "pairs": {},
        "joints17": compare_align.J17,
    }


def test_synthetic_zero_confidence_fails_coverage():
    """전 관절 conf 0 → 커버리지 FAIL (Q 신뢰 커버리지 라인)."""
    ok, lines = compare_align.align_quality(_synthetic_align(conf=0.0))
    assert not ok
    assert any("신뢰 커버리지" in ln and "[FAIL]" in ln for ln in lines)


def test_synthetic_unrelated_pose_fails_distance():
    """무관 좌표(사지 대이동 — 정렬이 딴 동작을 붙인 형상) → 자세거리 FAIL."""
    ok, lines = compare_align.align_quality(_synthetic_align(ref_limb_shift=2.0))
    assert not ok
    assert any("자세거리" in ln and "[FAIL]" in ln for ln in lines)
    # 커버리지는 PASS — 실패 축이 정확히 거리 축임을 고정.
    assert all("[PASS]" in ln for ln in lines if "신뢰 커버리지" in ln)


def test_malformed_align_fails_closed():
    """필수 필드 결측(구버전 포맷 형상) = 판정 불가 → FAIL fail-closed."""
    ok, lines = compare_align.align_quality({"fps": 15.0})
    assert not ok
    assert any("Q0" in ln for ln in lines)


def test_quality_align_shape_passes():
    """합성 양품(고신뢰 + 동일 자세) PASS — 스테이지 테스트 스텁의 전제 고정."""
    ok, lines = compare_align.align_quality(_synthetic_align())
    assert ok, "\n".join(lines)

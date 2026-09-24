"""quick-260924-vw2 — 게이트 상속 단계의 잰 값 조건부 카드(_measured_pattern_card) → 종전 업로드 매퍼 통과.

단언: (1) 카드 dict 가 종전 계약 키로 업로드 매퍼(_fault_zoom_upload_items)를 통과한다(표식 판·표시 없는 판 둘 다)
(2) 순간 = freeze 초 그대로, atMatched = 카드 학생 프레임 == record.atFrameIdx
(3) 게이트가 학생 표시를 막으면 원 양쪽 생략(userMarked=refMarked=False) — 카드는 남는다
(4) 프레임이 없으면 None(호출측이 종전 카드 경로로)
S3 는 가짜. Gemini/Pod/Firestore 호출 0.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
for _p in (_PIPELINE, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import app  # noqa: E402

_J17 = (
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
)


def _align(frames=90):
    kp = np.full((frames, len(_J17), 2), 0.5, dtype=float)
    for n, xy in {"left_shoulder": (0.45, 0.40), "left_elbow": (0.50, 0.46), "left_wrist": (0.55, 0.40),
                  "left_ankle": (0.30, 0.85), "right_ankle": (0.45, 0.80), "nose": (0.44, 0.33)}.items():
        kp[:, _J17.index(n)] = xy
    sc = np.full((frames, len(_J17)), 0.9)
    return {"fps": 15.0, "joints17": list(_J17), "userFrames": frames, "refFrames": frames,
            "userKp": kp.tolist(), "userScore": sc.tolist(), "refKp": kp.tolist(), "refScore": sc.tolist()}


def _rec():
    return {"recordId": "r00:angle_vs_reference__left_shoulder", "criterion": "angle_vs_reference__left_shoulder",
            "measuredPattern": "body_low_arm_open", "atFrameIdx": 21, "atVideoSec": 2.106, "atRefVideoSec": 2.533}


def _decision(draw=True):
    return SimpleNamespace(draw_user_marks=draw, hold_state="moving", pair_state="match", eye_state="skip")


def _frame_at(side, sec):
    return np.full((1080, 608, 3), 180 if side == "user" else 120, dtype=np.uint8)


def _card(**over):
    kw = dict(rec=_rec(), u_sec=2.106, r_sec=2.533, align=_align(), frame_at=_frame_at,
              deficits={"left_shoulder": 23.0}, decision=_decision(), u9=21, r9=38,
              user_report={"fps": 18.0, "frames": 136}, ref_report={"fps": 18.0, "frames": 118},
              analysis_id="a")
    kw.update(over)
    return app._measured_pattern_card(**kw)


def test_card_passes_the_existing_upload_mapper(monkeypatch):
    puts = []
    monkeypatch.setattr(app._s3, "put_object", lambda **kw: puts.append(kw))
    monkeypatch.setattr(app, "_signed_get", lambda bucket, key: f"https://signed/{key}")
    card = _card()
    assert card["png"] and card["pngPlain"] and card["png"] != card["pngPlain"]
    (item,) = app._fault_zoom_upload_items([card], "confirmed", "u", "a", "b")
    assert item["criterion"] == "angle_vs_reference__left_shoulder" and item["tier"] == "confirmed"
    assert item["imageKey"].endswith("zoom_angle_vs_reference__left_shoulder.png")
    assert item["imageKeyPlain"].endswith("zoom_angle_vs_reference__left_shoulder__plain.png")
    assert (item["userVideoSec"], item["refVideoSec"]) == (2.106, 2.533)
    assert item["atMatched"] is True and item["userMarked"] is True and item["refMarked"] is True
    assert item["refMatch"] == "dtw" and item["kind"] == "deficit"
    assert len(puts) == 2


def test_blocked_user_marks_drop_both_circles_but_keep_the_card():
    card = _card(decision=_decision(draw=False))
    assert card is not None and card["userMarked"] is False and card["refMarked"] is False


def test_card_moment_not_matching_the_record_is_reported_honestly():
    assert _card(u9=22)["atMatched"] is False


def test_missing_frame_falls_back_to_the_old_card_path():
    assert _card(frame_at=lambda side, sec: None) is None

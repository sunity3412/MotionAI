#!/usr/bin/env python3
"""확대 비교 카드 로컬 재렌더 하네스 (quick-260811-bz5) — Pod 무관.

belle 08-10: "저길 잡으면 뭘 말하는지 모를것 같은데" — 표시 문법 별건의 실증 도구.
Firestore 에 저장된 keypointReport(user/ref) + faultZoomComparisons 의 프레임 쌍
+ S3 원본 영상만으로 실제 카드 5장을 로컬 재현하고, drawing 함수를 교체해
후보 문법을 같은 데이터로 렌더한다.

운영 경로 정합 (배선 주장은 로그로 — memory 규율):
  · 렌더 본체 = 운영과 같은 `fault_zoom.build_fault_zoom_comparisons` 호출.
    dtw_match=None + user/ref_frame_idx override → unit 선택 로직이 전부
    비활성화되고 저장된 프레임 쌍이 그대로 쓰인다 (fault_zoom.py 2640-2709).
  · 저장 doc 의 userFrameIdx/refFrameIdx 는 **rep 공간(18fps)** 이고 override 는
    **frames 배열 공간(9fps)** 이다 (fault_zoom.py 3300 — u_kp_idx_unit 방출).
    변환 = round(stored * frames_fps / rep_fps). 재현 후 방출 item 의
    userFrameIdx == stored 로 round-trip 인증한다.
  · 원본 해상도 공급자 = pipeline._build_native_frame_provider 미러
    (compare_render._native_frame + probe_effective_fps — app.py 3235).

usage:
  python3 render_harness.py --fetch            # Firestore doc → 캐시 JSON
  python3 render_harness.py --render current   # 기준선 재현 → out/current/
  python3 render_harness.py --check            # 기준선 vs 08-10 S3 실물 diff
  python3 render_harness.py --render ghost     # 후보 A: 고스트+쐐기
  python3 render_harness.py --render wedge     # 후보 B: 쐐기+화살촉
프로덕션 코드 아님 — quick 디렉터리 로컬 하네스. 채점 무접촉.
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import math
import pathlib
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw

_HERE = pathlib.Path(__file__).resolve().parent
_REPO = _HERE.parents[2]
sys.path.insert(0, str(_REPO / "backend" / "shared" / "python"))

from sunity_shared.analysis import fault_zoom as fz  # noqa: E402
from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor  # noqa: E402

log = logging.getLogger("harness")

# ── 대상 식별자 (PLAN.md 조사 근거) ──────────────────────────────────────────
UID = "fvcNXzEqKjgqVxRPVSj1iwFnIpn2"
AID = "p34fresh1786363530"
MOTION_ID = "ref-pdshape"
FRAMES_FPS = 9.0  # 운영 호출값 (app.py 3378) — 실효 rate 와 다르다 (라벨)

_SCRATCH = pathlib.Path(
    "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/"
    "4ecaa5a2-717b-43a6-a9c5-e152a330b7a3/scratchpad"
)
VIDEOS = {"user": _SCRATCH / "videos" / "user.mp4", "ref": _SCRATCH / "videos" / "ref.mp4"}
CACHE = _SCRATCH / "doc_cache.json"
FRAMES_NPZ = _SCRATCH / "frames_cache.npz"
CARDS_0810 = _SCRATCH / "cards_0810"
OUT = _HERE / "out"

# 08-10 S3 실물 파일명 매핑 (tier + criterion → S3 키 규칙, app.py 3455-3456)
S3_NAME = {
    ("confirmed", "left_elbow"): "zoom_angle_vs_reference__left_elbow.png",
    ("confirmed", "right_elbow"): "zoom_angle_vs_reference__right_elbow.png",
    ("confirmed", "right_shoulder"): "zoom_angle_vs_reference__right_shoulder.png",
    ("confirmed", "left_hip"): "zoom_angle_vs_reference__left_hip.png",
    ("advisory", "left_shoulder"): "zoom_adv_left_shoulder.png",
}


def fetch() -> dict:
    """Firestore → 캐시 JSON. FIREBASE_SA_PATH 필요 (로컬 = 리포 루트 SA 파일)."""
    from sunity_shared import firestore_admin as fa

    doc = (
        fa._db().collection("users").document(UID)  # noqa: SLF001
        .collection("analyses").document(AID).get().to_dict()
    )
    res = doc["result"]
    ref = fa.get_reference_motion(res["comparison"]["referenceMotionId"])
    payload = {
        "userReport": res["keypointReport"],
        "refReport": ref["referenceKeypointReport"],
        "cards": res["faultZoomComparisons"],
    }
    CACHE.write_text(json.dumps(payload))
    print(f"cached: {CACHE} cards={len(payload['cards'])}")
    return payload


def load_cache() -> dict:
    if not CACHE.exists():
        return fetch()
    return json.loads(CACHE.read_text())


def load_frames(ext: FfmpegFrameExtractor) -> tuple[np.ndarray, np.ndarray]:
    """9fps/640px 추출 (운영 파라미터). npz 캐시 — 추출 이력은 probe 가 메타로 보완."""
    if FRAMES_NPZ.exists():
        z = np.load(FRAMES_NPZ)
        return z["user"], z["ref"]
    uf = ext.extract(str(VIDEOS["user"]))
    rf = ext.extract(str(VIDEOS["ref"]))
    np.savez_compressed(FRAMES_NPZ, user=uf, ref=rf)
    return uf, rf


def native_provider(ext: FfmpegFrameExtractor):
    """pipeline._build_native_frame_provider 미러 (app.py 3235 — 동작 동일)."""
    from sunity_shared.analysis import compare_render as _cr

    fps: dict[str, float] = {}
    for which, p in VIDEOS.items():
        eff = ext.probe_effective_fps(str(p))
        if eff and eff > 0:
            fps[which] = float(eff)
        else:
            print(f"WARN native 비활성 ({which} 실효 rate 판정 불가)")
    if not fps:
        return None
    workdir = pathlib.Path(tempfile.mkdtemp(prefix="fz_native_", dir=_SCRATCH))
    cache: dict[tuple[str, int], object] = {}

    def _at(which: str, idx: int):
        if which not in fps:
            return None
        key = (which, int(idx))
        if key not in cache:
            try:
                cache[key] = _cr._native_frame(  # noqa: SLF001
                    VIDEOS[which], int(idx) / fps[which], workdir
                )
            except Exception:  # noqa: BLE001
                cache[key] = None
        got = cache[key]
        return None if got is None else np.asarray(got)

    return _at


def render_card(card: dict, urep: dict, rrep: dict, uf, rf, native_at) -> dict | None:
    """저장 카드 1장을 운영 함수로 재현. 반환 item 에 round-trip 인증 포함."""
    joint, tier = card["joint"], card["tier"]
    u_rep_fps = float(urep.get("fps") or FRAMES_FPS)
    r_rep_fps = float(rrep.get("fps") or FRAMES_FPS)
    u9 = int(round(card["userFrameIdx"] * FRAMES_FPS / u_rep_fps))
    r9 = int(round(card["refFrameIdx"] * FRAMES_FPS / r_rep_fps))
    deltas = {}
    if card.get("deficitDeg") is not None:
        deltas[joint] = float(card["deficitDeg"])
    if tier == "confirmed":
        items = fz.build_fault_zoom_comparisons(
            uf, rf, urep, rrep, None, [joint], deltas,
            frames_fps=FRAMES_FPS, dtw_match=None,
            user_frame_idx=u9, ref_frame_idx=r9,
            draw_arrows=True,
            criterion_units=[{
                "criterion": card.get("criterion"),
                "joints": (joint,), "region": None, "at_frame_idx": None,
            }],
            stamp_ref=False, motion_id=MOTION_ID,
            analysis_id=f"bz5-{joint}", native_frame_at=native_at,
        )
    else:
        items = fz.build_fault_zoom_comparisons(
            uf, rf, urep, rrep, None, [joint], deltas,
            frames_fps=FRAMES_FPS, joint_kinds={joint: "deficit"},
            dtw_match=None, user_frame_idx=u9, ref_frame_idx=r9,
            draw_arrows=False, stamp_ref=False,
            analysis_id=f"bz5-{joint}", native_frame_at=native_at,
        )
    if not items:
        print(f"  DROP {joint} ({tier}) — 카드 미방출")
        return None
    item = items[0]
    rt = (item.get("userFrameIdx"), item.get("refFrameIdx"))
    want = (card["userFrameIdx"], card["refFrameIdx"])
    item["_roundtrip_ok"] = rt == want
    if not item["_roundtrip_ok"]:
        print(f"  WARN {joint} round-trip 불일치: 재현 {rt} != 저장 {want}")
    return item


# ── 후보 문법 (drawing 교체 — 운영 코드 무접촉, 하네스 안에서만 patch) ──────────
#
# 핵심: 결함은 '차이'다. 현재 문법은 한 패널의 절대 자세(선 2 + 사이각 호)만 그려
# 174° vs 163° 의 11° 를 두 패널 육안 대조로 읽으라 한다 — 불가능 (belle 08-10).
# 후보는 학생 패널에 "기준이라면 사지가 여기"를 직접 얹는다. 기준 사이각을 학생
# 자신의 몸통 축 + 회전 방향(카이럴리티)에 이식하므로 두 패널의 방위 차이(카메라
# 1대 한계, right_shoulder 51°)에도 영향받지 않는다.
#
# 승인 시각 언어 유지: 수치 배지 0 · 브랜드/흰 halo · 선 기하(64/85px @ _OUT=360).

_GHOST_DASH = 9          # 고스트 점선 마디 px
_WEDGE_ALPHA = 88        # 쐐기 채움 알파 (0-255)
_WEDGE_R_FRAC = 0.42     # 쐐기 반경 (패널 대비) — 호 r16 보다 크게, 델타를 면적으로
_ARROW_HEAD_PX = 13


def _unit_vec(vertex, p):
    dx, dy = p[0] - vertex[0], p[1] - vertex[1]
    n = math.hypot(dx, dy)
    return (dx / n, dy / n) if n > 1e-9 else None


def _inner_deg(vertex, limb, torso):
    ul, ut = _unit_vec(vertex, limb), _unit_vec(vertex, torso)
    if ul is None or ut is None:
        return None
    d = max(-1.0, min(1.0, ul[0] * ut[0] + ul[1] * ut[1]))
    return math.degrees(math.acos(d))


def _rotate(v, rad):
    c, s = math.cos(rad), math.sin(rad)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c)


def _dashed_line(draw, a, b, fill, width, dash=_GHOST_DASH):
    n = math.hypot(b[0] - a[0], b[1] - a[1])
    if n < 1e-6:
        return
    steps = max(1, int(n // dash))
    for i in range(0, steps, 2):
        t0, t1 = i / steps, min(1.0, (i + 1) / steps)
        draw.line(
            [(a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0),
             (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)],
            fill=fill, width=width,
        )


def _draw_candidate(img, vertex_px, limb_dir_px, torso_dir_px,
                    ref_inner_deg: float, mode: str) -> bool:
    """학생 패널 후보 문법. mode='ghost'(고스트 선+쐐기) | 'wedge'(쐐기+화살촉).

    고스트 방향 = 학생 몸통 축에서, 학생 사지와 **같은 회전 방향**으로 기준
    사이각만큼 연 방향 — "정은지 각도라면 사지가 여기". 카이럴리티는 학생 패널
    자신의 것(cross 부호)을 쓴다 (방위 이식 아님 — 각도만 이식).
    """
    v = (float(vertex_px[0]), float(vertex_px[1]))
    ul = _unit_vec(v, limb_dir_px)
    ut = _unit_vec(v, torso_dir_px)
    if ul is None or ut is None:
        return False
    side = _OUT_OF(img)
    limb_len = fz._ANGLE_LIMB_LEN_FRAC * side
    torso_len = fz._ANGLE_TORSO_LEN_FRAC * side
    cross = ut[0] * ul[1] - ut[1] * ul[0]
    sgn = 1.0 if cross >= 0 else -1.0
    ghost = _rotate(ut, sgn * math.radians(ref_inner_deg))
    limb_end = (v[0] + ul[0] * limb_len, v[1] + ul[1] * limb_len)
    torso_end = (v[0] + ut[0] * torso_len, v[1] + ut[1] * torso_len)
    ghost_end = (v[0] + ghost[0] * limb_len, v[1] + ghost[1] * limb_len)

    # 쐐기(반투명 브랜드) — 학생 사지 방향 ↔ 고스트 방향 사이. RGBA 오버레이 후 합성.
    r = _WEDGE_R_FRAC * side
    a_limb = math.degrees(math.atan2(ul[1], ul[0]))
    a_ghost = math.degrees(math.atan2(ghost[1], ghost[0]))
    d = (a_ghost - a_limb) % 360
    start, end = (a_limb, a_limb + d) if d <= 180 else (a_ghost, a_ghost + (360 - d))
    base = img.convert("RGBA")
    ov = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).pieslice(
        [v[0] - r, v[1] - r, v[0] + r, v[1] + r],
        start=start, end=end, fill=(*fz._BRAND, _WEDGE_ALPHA),
    )
    img.paste(Image.alpha_composite(base, ov).convert("RGB"), (0, 0))

    draw = ImageDraw.Draw(img)
    # 기존 선 2개 (승인 기하 그대로 — halo 아래 / 코어 위)
    for w_ in (fz._ANGLE_HALO_W, fz._ANGLE_CORE_W):
        fill = fz._HALO if w_ == fz._ANGLE_HALO_W else fz._BRAND
        draw.line([v, limb_end], fill=fill, width=w_)
        draw.line([v, torso_end], fill=fill, width=w_)
    if mode == "ghost":
        # 고스트 = 흰 halo 점선 + 어두운 코어 점선 ("여기가 기준")
        _dashed_line(draw, v, ghost_end, fz._HALO, fz._ANGLE_HALO_W)
        _dashed_line(draw, v, ghost_end, (60, 60, 60), fz._ANGLE_CORE_W)
    else:  # wedge — 쐐기 바깥 호에 교정 방향 화살촉
        mid_r = r
        a0, a1 = math.radians(a_limb), math.radians(a_ghost)
        # 화살촉: 쐐기 호의 고스트 쪽 끝, 사지→고스트 진행 방향
        tip = (v[0] + math.cos(a1) * mid_r, v[1] + math.sin(a1) * mid_r)
        step = 1.0 if (a_ghost - a_limb) % 360 <= 180 else -1.0
        tang = (-math.sin(a1) * step, math.cos(a1) * step)
        nrm = (math.cos(a1), math.sin(a1))
        p1 = (tip[0] - tang[0] * _ARROW_HEAD_PX + nrm[0] * _ARROW_HEAD_PX * 0.6,
              tip[1] - tang[1] * _ARROW_HEAD_PX + nrm[1] * _ARROW_HEAD_PX * 0.6)
        p2 = (tip[0] - tang[0] * _ARROW_HEAD_PX - nrm[0] * _ARROW_HEAD_PX * 0.6,
              tip[1] - tang[1] * _ARROW_HEAD_PX - nrm[1] * _ARROW_HEAD_PX * 0.6)
        draw.polygon([tip, p1, p2], fill=fz._BRAND, outline=fz._HALO)
    return True


def _OUT_OF(img: Image.Image) -> int:
    return min(img.size)


class _GrammarPatch:
    """fz._draw_joint_angle 2-pass patch. pass1 기록(원본 드로잉) → pass2 후보.

    렌더러는 카드당 user → ref 순서로 정확히 2회 호출한다 (fault_zoom.py 3205-3208,
    ref 는 user 성공 시에만). 기록된 각 패널의 사이각으로 pass2 에서 학생 패널에만
    후보 문법을 그리고 기준 패널은 원본 문법을 유지한다.
    """

    def __init__(self, mode: str):
        self.mode = mode
        self.recorded: list[float] = []
        self.calls = 0
        self._orig = fz._draw_joint_angle

    def record(self, img, vertex, limb, torso):
        deg = _inner_deg(vertex, limb, torso)
        self.recorded.append(deg if deg is not None else float("nan"))
        return self._orig(img, vertex, limb, torso)

    def candidate(self, img, vertex, limb, torso):
        i = self.calls
        self.calls += 1
        if i == 0:  # 학생 패널 — 기준(두 번째 기록) 사이각 이식
            ref_deg = self.recorded[1] if len(self.recorded) > 1 else float("nan")
            if not math.isfinite(ref_deg):
                return self._orig(img, vertex, limb, torso)
            return _draw_candidate(img, vertex, limb, torso, ref_deg, self.mode)
        return self._orig(img, vertex, limb, torso)


def render_all(grammar: str, data: dict, uf, rf, native_at) -> None:
    out_dir = OUT / grammar
    out_dir.mkdir(parents=True, exist_ok=True)
    urep, rrep = data["userReport"], data["refReport"]
    for card in data["cards"]:
        joint, tier = card["joint"], card["tier"]
        patch = None
        if grammar != "current" and tier == "confirmed":
            patch = _GrammarPatch(grammar)
            fz._draw_joint_angle = patch.record
            try:
                render_card(card, urep, rrep, uf, rf, native_at)  # pass1 기록
            finally:
                fz._draw_joint_angle = patch._orig
            if len(patch.recorded) < 2:
                print(f"  {joint}: 각도 베이크 미진입 — 후보 적용 불가, 원본 유지")
                patch = None
        if patch is not None:
            fz._draw_joint_angle = patch.candidate
        try:
            item = render_card(card, urep, rrep, uf, rf, native_at)
        finally:
            fz._draw_joint_angle = patch._orig if patch else fz._draw_joint_angle
        if item is None:
            continue
        p = out_dir / f"{joint}_{tier}.png"
        p.write_bytes(item["png"])
        extra = ""
        if patch is not None and len(patch.recorded) >= 2:
            extra = (f" user={patch.recorded[0]:.0f}도 ref={patch.recorded[1]:.0f}도"
                     f" 델타={abs(patch.recorded[0]-patch.recorded[1]):.0f}도")
        print(f"  {p.name} roundtrip={'OK' if item['_roundtrip_ok'] else 'FAIL'}{extra}")


def check() -> int:
    """기준선(current) vs 08-10 S3 실물 — 픽셀 diff 게이트.

    게이트 대상 = **confirmed 4장** (표시 문법의 대상 = 각도 베이크 카드).
    advisory 는 INFO 강등: 운영 배치는 region='arms' 그룹 unit 인데 그 멤버 구성
    (select_advisory_joints 입력 kp_deltas)이 doc 에 저장되지 않아 단일 재현이
    프레이밍만 어긋난다 (같은 8.0s 프레임·같은 링-얼굴 결함은 재현됨 — 실물 육안
    대조 08-11). 정확 재현은 결함 ②(legacy 마커 경로) 별건에서.
    """
    fails = 0
    for (tier, joint), name in S3_NAME.items():
        mine = OUT / "current" / f"{joint}_{tier}.png"
        theirs = CARDS_0810 / name
        gate = tier == "confirmed"
        if not mine.exists() or not theirs.exists():
            print(f"MISS {joint}: mine={mine.exists()} s3={theirs.exists()}")
            fails += 1 if gate else 0
            continue
        a = np.asarray(Image.open(mine).convert("RGB"), dtype=np.int16)
        b = np.asarray(Image.open(theirs).convert("RGB"), dtype=np.int16)
        if a.shape != b.shape:
            print(f"{'FAIL' if gate else 'INFO'} {joint}: 크기 불일치 {a.shape} vs {b.shape}")
            fails += 1 if gate else 0
            continue
        diff = np.abs(a - b)
        mean = float(diff.mean())
        frac16 = float((diff.max(axis=2) > 16).mean())
        ok = mean < 3.0 and frac16 < 0.02
        tag = ("PASS" if ok else "FAIL") if gate else "INFO"
        print(f"{tag} {joint}: mean|d|={mean:.2f} frac>16={frac16:.4f}")
        fails += 0 if (ok or not gate) else 1
    return fails


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--render", choices=["current", "ghost", "wedge"])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if args.fetch:
        fetch()
    if args.render:
        data = load_cache()
        ext = FfmpegFrameExtractor(target_fps=FRAMES_FPS, max_side=640)
        uf, rf = load_frames(ext)
        native_at = native_provider(ext)
        print(f"frames: user={uf.shape} ref={rf.shape}")
        render_all(args.render, data, uf, rf, native_at)
    if args.check:
        return check()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

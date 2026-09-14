#!/usr/bin/env python3
"""폴 계기를 영상 여러 개에 돌려 일반화되는지 본다 (스파이크 2, 2026-09-14).

스파이크 1(`pole_probe.py`)은 영상 **2개**에서만 확인했다. 표본 2로 "된다"고
말할 수 없어서 기준 모션 11편 전수로 넓힌다.

스파이크 1 대비 강건화 두 가지:
  1) '사람은 위쪽 5~35% 에 없다'는 가정을 뺐다. 동작마다 사람 위치가 다르다.
     대신 **폴 기둥의 x 를 먼저 찾는다** — 행마다 '어두운 좁은 세로 띠' 후보를
     모아 x 히스토그램의 최빈값을 폴로 본다. 폴은 모든 행에 같은 x 로 나오고
     배경 엣지는 흩어지므로 이것만으로 갈린다.
  2) 그 x 근처(±6px)에서만 폭을 재고, 행별 값의 **trimmed median** 을 쓴다.

검산 (이게 핵심):
  폴 지름 45mm 로 만든 자로 **저장된 기준 모션의 몸통 길이**를 재서
  해부학적 범위(성인 어깨↔골반 대략 40~55cm)에 들어오는지 본다.
  11편이 독립적으로 그 범위에 들어오면 계기가 일반화된다는 뜻이다.

읽기 전용 — 운영 코드·문서 무접촉.
"""
from __future__ import annotations

import argparse
import math

import cv2
import numpy as np

IPSF_DIAMETER_MM = 45.0
TORSO_MIN_CM, TORSO_MAX_CM = 40.0, 55.0


def load_frames(path: str, n: int = 40, stride: int = 5, long_side: int = 640) -> np.ndarray:
    cap = cv2.VideoCapture(path)
    out, i = [], 0
    while len(out) < n:
        ok, fr = cap.read()
        if not ok:
            break
        if i % stride == 0:
            h, w = fr.shape[:2]
            s = long_side / max(h, w)
            out.append(cv2.resize(fr, (int(w * s), int(h * s))))
        i += 1
    cap.release()
    return np.stack(out) if out else np.zeros((0, 0, 0, 3), np.uint8)


def _strip_candidates(g: np.ndarray, grad: float, max_w: int) -> list[tuple[int, float, float]]:
    """(row, center_x, width) — '강한 하강 엣지 → 오른쪽 강한 상승 엣지' 쌍 전부."""
    h, w = g.shape
    out = []
    for y in range(h):
        d = np.gradient(g[y])
        x = 1
        while x < w - 2:
            if d[x] < -grad:
                for x2 in range(x + 2, min(x + max_w, w - 1)):
                    if d[x2] > grad:
                        out.append((y, (x + x2) / 2.0, float(x2 - x)))
                        x = x2
                        break
                else:
                    x += 1
            x += 1
    return out


def measure_pole_profile(frames: np.ndarray, *, band: int = 40,
                         min_depth: float = 6.0) -> dict | None:
    """폴 폭을 **밝기 프로파일의 반치폭(FWHM)** 으로 잰다 — 해상도에 안 흔들린다.

    ★ 왜 엣지 쌍 방식을 버렸나 (2026-09-14 실측):
      `measure_pole` 의 '하강 엣지 → 상승 엣지' 방식은 **해상도를 바꾸면 답이 바뀐다.**
      장변 640 에서 6px 을 낸 영상이 장변 1920 에서는 3px 을 냈다(3배 굵어져야 하는데).
      고해상도에서는 엣지가 여러 픽셀에 퍼져 픽셀당 기울기가 작아지고, 임계를 낮추면
      노이즈의 좁은 띠를 잡는다. 임계 하나로 두 해상도를 다 맞출 수 없다.

    이 방식: 폴 기둥 x 주변 밴드에서 **여러 행의 밝기를 평균**해 프로파일 한 줄을 만들고,
    배경 대비 파인 골의 **반 깊이 지점 두 곳**을 선형보간으로 찾는다(서브픽셀).
    임계값이 '절대 밝기'가 아니라 '골 깊이의 절반'이라 해상도·조명에 불변이다.
    """
    if frames.shape[0] < 3:
        return None
    bg = np.median(frames, axis=0).astype(np.uint8)
    g = cv2.cvtColor(bg, cv2.COLOR_BGR2GRAY).astype(float)
    h, w = g.shape

    # 1) 폴 기둥 x — 행 평균 프로파일에서 가장 깊고 좁은 골
    prof_all = g.mean(axis=0)
    smooth = np.convolve(prof_all, np.ones(3) / 3, mode="same")
    # 배경 추세 제거 (넓은 이동평균)
    k = max(31, (w // 8) | 1)
    base = np.convolve(smooth, np.ones(k) / k, mode="same")
    dip = base - smooth
    x0 = int(np.argmax(dip[int(w * 0.2):int(w * 0.8)])) + int(w * 0.2)

    # 2) 그 기둥에서 반치폭
    # ★ 배경선을 이동평균으로 만들면 안 된다 — 골 폭과 창 크기가 비슷하면
    #   배경선이 골 속으로 끌려 들어가 깊이가 반토막 나고 폭이 절반으로 나온다
    #   (2026-09-14 에 이 버그로 20px 짜리 폴을 8.3px 으로 쟀다).
    #   밴드의 상위 백분위를 배경 밝기로 쓴다 — 골이 밴드의 일부일 때 안정적이다.
    lo, hi = max(0, x0 - band), min(w, x0 + band + 1)
    prof = g[:int(h * 0.25), lo:hi].mean(axis=0)   # 사람 없는 위쪽만
    if prof.size < 9:
        return None
    bg_level = float(np.percentile(prof, 85))
    c = int(np.argmin(prof))
    depth = bg_level - float(prof[c])
    if depth < min_depth:
        return None
    half_level = bg_level - depth / 2.0            # 반 깊이의 '밝기' 값

    def cross(step: int) -> float | None:
        i = c
        while 0 < i < len(prof) - 1:
            nxt = i + step
            if prof[nxt] >= half_level:            # 골을 빠져나가는 지점
                a, b = float(prof[i]), float(prof[nxt])
                if b == a:
                    return float(nxt)
                return i + step * (half_level - a) / (b - a)   # 선형보간
            i = nxt
        return None

    left, right = cross(-1), cross(1)
    if left is None or right is None:
        return None
    width = abs(right - left)
    return {
        "width_px": float(width),
        "x_center": float(lo + c),
        "depth": depth,
        "angle_deg": float("nan"),
        "n_rows": int(h),
        "row_span": 1.0,
        "p10_p90": (width, width),
    }


def measure_pole(frames: np.ndarray, *, grad: float = 6.0, max_w: int = 30,
                 x_tol: float = 6.0) -> dict | None:
    """폴 기둥 x 를 먼저 찾고, 거기서만 폭을 잰다.

    ★ 해상도 의존이 있다 — `measure_pole_profile` 을 쓸 것. 기록용으로만 남긴다.
    """
    if frames.shape[0] < 3:
        return None
    bg = np.median(frames, axis=0).astype(np.uint8)
    g = cv2.cvtColor(bg, cv2.COLOR_BGR2GRAY).astype(float)
    h, w = g.shape
    cands = _strip_candidates(g, grad, max_w)
    if len(cands) < 20:
        return None

    xs = np.array([c[1] for c in cands])
    # x 히스토그램 최빈 구간 = 폴 기둥 (모든 행에 같은 x 로 나오는 유일한 구조)
    hist, edges = np.histogram(xs, bins=np.arange(0, w + 4, 4))
    peak = edges[int(np.argmax(hist))] + 2.0
    sel = [c for c in cands if abs(c[1] - peak) <= x_tol]
    if len(sel) < 15:
        return None

    widths = np.array([c[2] for c in sel])
    rows = np.array([c[0] for c in sel])
    centers = np.array([c[1] for c in sel])
    lo, hi = np.percentile(widths, [20, 80])
    trimmed = widths[(widths >= lo) & (widths <= hi)]
    width = float(np.median(trimmed)) if len(trimmed) else float(np.median(widths))

    # 폴 축 기울기 = 행에 따른 중심 x 의 회귀 기울기
    angle = float("nan")
    if len(rows) >= 10 and np.ptp(rows) > h * 0.15:
        slope = np.polyfit(rows, centers, 1)[0]
        angle = math.degrees(math.atan(slope))

    return {
        "width_px": width,
        "x_center": float(np.median(centers)),
        "angle_deg": angle,
        "n_rows": int(len(sel)),
        "row_span": float(np.ptp(rows) / h),
        "p10_p90": (float(np.percentile(widths, 10)), float(np.percentile(widths, 90))),
    }


def torso_px_from_ref(motion_id: str) -> float | None:
    """저장된 기준 모션의 joints3d 에서 어깨중점↔골반중점 중앙 길이(px)."""
    import sys, pathlib
    repo = pathlib.Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(repo / "backend" / "scripts"))
    import e2e_app_path as e2e
    db = e2e.firestore_client()
    d = db.document(f"reference/{motion_id}").get().to_dict() or {}
    flat = d.get("joints3d")
    if not flat:
        return None
    t = int(d["joints3dFrames"])
    a = np.asarray(flat, float).reshape(t, len(d["joints3dKeys"]), 3)[:, :, :2]
    sh = a[:, [5, 6], :].mean(1)
    hp = a[:, [11, 12], :].mean(1)
    return float(np.nanmedian(np.linalg.norm(sh - hp, axis=-1)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--diameter", type=float, default=IPSF_DIAMETER_MM)
    ap.add_argument("--cross-check", action="store_true",
                    help="저장된 기준 모션 몸통 길이로 검산 (Firestore 읽기)")
    a = ap.parse_args()

    print(f"{'영상':<26}{'폭px':>7}{'x':>6}{'기울기':>8}{'행':>6}{'세로범위':>9}"
          f"{'1cm=px':>9}{'몸통cm':>8}  판정")
    ok_n = tot = 0
    for path in a.videos:
        name = path.rsplit("/", 1)[-1].replace(".mp4", "")
        r = measure_pole(load_frames(path))
        if r is None:
            print(f"{name:<26}{'폴 미검출':>40}")
            continue
        pxmm = r["width_px"] / a.diameter
        torso_cm = None
        if a.cross_check:
            tp = torso_px_from_ref(name)
            if tp:
                torso_cm = tp / (pxmm * 10)
        tot += 1
        verdict = "-"
        if torso_cm is not None:
            good = TORSO_MIN_CM <= torso_cm <= TORSO_MAX_CM
            ok_n += good
            verdict = "OK" if good else "벗어남"
        ang = f"{r['angle_deg']:+.2f}°" if not math.isnan(r["angle_deg"]) else "  n/a"
        tc = f"{torso_cm:.1f}" if torso_cm is not None else "  -"
        print(f"{name:<26}{r['width_px']:>7.1f}{r['x_center']:>6.0f}{ang:>8}"
              f"{r['n_rows']:>6}{r['row_span']:>8.0%}{pxmm*10:>9.2f}{tc:>8}  {verdict}")
    if a.cross_check and tot:
        print(f"\n검산: 몸통이 {TORSO_MIN_CM:.0f}~{TORSO_MAX_CM:.0f}cm 범위에 "
              f"{ok_n}/{tot} 편")


if __name__ == "__main__":
    main()

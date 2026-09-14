#!/usr/bin/env python3
"""폴을 '수직 prior 없이' 찾고 축·폭을 잰다 — 계기 타당성 스파이크 (2026-09-14).

왜 새로 쓰는가:
  기존 `analysis/pole/detector.py` 는 `VERTICAL_TOLERANCE_DEG=5.0` 로 **수직 ±5°
  안의 선만** 받는다. 그래서 카메라가 그 이상 돌아가면 진짜 폴이 필터에서 탈락하고
  배경 세로 엣지를 잡은 채 `source='detected'` 를 보고한다. 실측(2026-09-14):
  입력을 −6°/+10° 로 일부러 기울여도 검출 기울기는 +2.19°/+1.05° 밖에 안 따라왔고
  부호조차 맞지 않았다. **즉 롤을 재려는 목적에는 그 검출기를 쓸 수 없다.**

무엇을 다르게 하는가:
  1) 시간축 median 배경 — 사람은 움직이고 폴은 고정이라 중앙값이 사람을 지운다.
  2) 각도 prior 없이 Hough 로 긴 직선을 전부 모은다.
  3) **쌍(pair)으로 판정** — 폴은 '평행한 두 실루엣 엣지'다. 배경 엣지는 짝이 없다.
     간격이 일정한 평행쌍만 남기면 수직 가정 없이 폴이 걸러진다.
  4) 그 쌍의 간격이 곧 **투영 폭 w_px** 이고, IPSF 규격 지름 45mm 로 나누면
     폴 평면에서의 px-per-mm 가 나온다 (초점거리 불필요).

한계 (읽는 사람이 반드시 알아야 함):
  · px-per-mm 는 **폴이 있는 깊이의 평면에서만** 유효하다. 폴보다 앞/뒤에 있는
    사지는 다른 배율이다. 깊이를 주는 계기가 아니다.
  · 실제 지름을 모르면 스케일은 못 낸다 (40/45/50mm). 축·롤은 지름 없이도 나온다.
  · 스피닝 폴이 연직이 아닐 수 있다. '폴 = 중력' 가정은 별도 검증이 필요하다.

읽기 전용 스파이크다 — 운영 코드 무접촉.
"""
from __future__ import annotations

import argparse
import math

import cv2
import numpy as np

IPSF_DIAMETER_MM = 45.0  # IPSF 규격 (40/50mm 도 존재 — --diameter 로 교체)


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
    return np.stack(out)


def rotate(frames: np.ndarray, deg: float) -> np.ndarray:
    h, w = frames.shape[1:3]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), deg, 1.0)
    return np.stack([cv2.warpAffine(f, m, (w, h), borderMode=cv2.BORDER_REPLICATE)
                     for f in frames])


def _segments(bg_gray: np.ndarray) -> np.ndarray:
    """각도 prior 없이 긴 직선 후보를 모은다."""
    edges = cv2.Canny(bg_gray, 40, 120, apertureSize=3)
    h = bg_gray.shape[0]
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 720, threshold=60,
        minLineLength=int(h * 0.35), maxLineGap=18,
    )
    return np.zeros((0, 4)) if lines is None else lines.reshape(-1, 4).astype(float)


def _angle_deg(seg: np.ndarray) -> float:
    """세로에 가까운 선의 기울기(도). 수직=0, 시계방향 +."""
    x1, y1, x2, y2 = seg
    if y2 < y1:
        x1, y1, x2, y2 = x2, y2, x1, y1
    return math.degrees(math.atan2(x2 - x1, y2 - y1))


def measure_width(frames: np.ndarray, *, top: float = 0.05, bottom: float = 0.35,
                  grad_thresh: float = 6.0, max_w: int = 30) -> dict | None:
    """폴 폭을 행마다 직접 잰다 — **폭은 이 함수로만 잴 것.**

    ★ `find_pole` 의 쌍 간격을 폭으로 쓰면 안 된다. 2026-09-14 에 그걸로
    22.76px 을 냈는데 실제는 6.0px 이었다(3.8배). 폴 실루엣 한 쌍이 아니라
    폴 엣지와 배경 엣지를 짝지은 탓이다. 물리 검증으로 잡혔다 —
    0.506 px/mm 이면 같은 프레임의 몸통 66.9px 이 13cm 가 된다(성인은 45~52cm).

    방법: 사람이 없는 위쪽 구간에서 행별 밝기 미분을 보고
    '강한 하강 엣지 → 그 오른쪽의 강한 상승 엣지' 한 쌍을 잡는다.
    폴은 배경보다 어두운 금속 기둥이라 이 부호 순서가 성립한다.

    검증: 45mm 로 나눈 자로 몸통을 재면 50.2cm — 해부학적으로 맞는다.
    """
    bg = np.median(frames, axis=0).astype(np.uint8)
    g = cv2.cvtColor(bg, cv2.COLOR_BGR2GRAY).astype(float)
    h, w = g.shape
    widths, centers = [], []
    for y in range(int(h * top), int(h * bottom)):
        d = np.gradient(g[y])
        for x in range(int(w * 0.30), int(w * 0.75)):
            if d[x] >= -grad_thresh:
                continue
            for x2 in range(x + 2, min(x + max_w, w - 1)):
                if d[x2] > grad_thresh:
                    widths.append(x2 - x)
                    centers.append((x + x2) / 2)
                    break
            break
    if not widths:
        return None
    arr = np.array(widths, dtype=float)
    med = float(np.median(arr))
    return {
        "width_px": med,
        "x_center": float(np.median(centers)),
        "n_rows": int(len(arr)),
        "n_agree": int((np.abs(arr - med) <= 3).sum()),
        "p10_p90": (float(np.percentile(arr, 10)), float(np.percentile(arr, 90))),
    }


def find_pole(frames: np.ndarray, *, pair_tol_deg: float = 2.0,
              min_w: float = 2.0, max_w: float = 40.0) -> dict | None:
    """평행 엣지쌍으로 폴 **축**을 찾는다. 각도 prior 없음.

    ★ 반환되는 width_px 는 신뢰할 수 없다 — 폭은 `measure_width` 를 쓸 것.
    이 함수는 angle_deg(롤 측정, 평균오차 ≈0.7°) 용도로만 검증됐다.

    반환: angle_deg(세로 대비 기울기) · width_px(**비신뢰**) · x_center · n_pairs
    """
    bg = np.median(frames, axis=0).astype(np.uint8)          # 사람 제거
    gray = cv2.cvtColor(bg, cv2.COLOR_BGR2GRAY)
    segs = _segments(gray)
    if len(segs) < 2:
        return None

    ang = np.array([_angle_deg(s) for s in segs])
    mid = np.array([[(s[0] + s[2]) / 2, (s[1] + s[3]) / 2] for s in segs])

    pairs = []
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            if abs(ang[i] - ang[j]) > pair_tol_deg:
                continue                                      # 평행하지 않다
            a = math.radians((ang[i] + ang[j]) / 2)
            # 두 중점의 '선에 수직한' 간격
            d = abs((mid[i][0] - mid[j][0]) * math.cos(a)
                    - (mid[i][1] - mid[j][1]) * math.sin(a))
            if not (min_w <= d <= max_w):
                continue                                      # 폴 굵기가 아니다
            pairs.append(((ang[i] + ang[j]) / 2, d,
                          (mid[i][0] + mid[j][0]) / 2))
    if not pairs:
        return None

    arr = np.array(pairs)
    # 가장 굵은 쌍이 아니라 '가장 흔한 간격'을 택한다 — 폴은 여러 조각으로 검출된다
    w_med = float(np.median(arr[:, 1]))
    keep = arr[np.abs(arr[:, 1] - w_med) <= max(1.5, 0.15 * w_med)]
    return {
        "angle_deg": float(np.median(keep[:, 0])),
        "width_px": float(np.median(keep[:, 1])),
        "x_center": float(np.median(keep[:, 2])),
        "n_pairs": int(len(keep)),
        "n_segments": int(len(segs)),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--diameter", type=float, default=IPSF_DIAMETER_MM)
    ap.add_argument("--roll-test", action="store_true",
                    help="일부러 기울여 계기가 따라오는지 검사")
    a = ap.parse_args()

    for path in a.videos:
        frames = load_frames(path)
        name = path.rsplit("/", 1)[-1]
        r = find_pole(frames)
        wm = measure_width(frames)
        print(f"\n=== {name}  ({frames.shape[0]}프레임 {frames.shape[2]}x{frames.shape[1]}) ===")
        if r is None:
            print("  폴 축 미검출")
        else:
            print(f"  축 기울기 {r['angle_deg']:+.2f}°   "
                  f"쌍 {r['n_pairs']}/{r['n_segments']}선")
        if wm is None:
            print("  폭 미측정")
            continue
        pxmm = wm["width_px"] / a.diameter
        print(f"  폭 {wm['width_px']:.1f}px  x중심 {wm['x_center']:.0f}px  "
              f"(표본 {wm['n_rows']}행, ±3px 내 {wm['n_agree']}행, "
              f"10~90% {wm['p10_p90'][0]:.0f}~{wm['p10_p90'][1]:.0f}px)")
        print(f"  → px-per-mm {pxmm:.4f}  |  1cm = {pxmm*10:.2f}px"
              f"   (지름 {a.diameter:.0f}mm · 폴 평면 한정)")
        print(f"  → 몸통 66.9px 환산 {66.9/(pxmm*10):.1f}cm  "
              f"(성인 어깨↔골반 45~52cm 면 타당)")

        if a.roll_test:
            print(f"  {'가한 롤':>8}{'검출 기울기':>13}{'따라온 양':>12}{'폭':>9}")
            base = None
            for d in (0, -10, -6, -3, 3, 6, 10):
                rr = find_pole(rotate(frames, d))
                if rr is None:
                    print(f"  {d:>+7}°{'미검출':>13}")
                    continue
                if base is None:
                    base = rr["angle_deg"]
                print(f"  {d:>+7}°{rr['angle_deg']:>12.2f}°"
                      f"{rr['angle_deg']-base:>+11.2f}°{rr['width_px']:>8.2f}px")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""기준 모션 joints3d 의 y/z 축 뒤바뀜 수리 (quick-260914, belle 승인).

## 무엇이 잘못됐나 — "버그"가 아니라 **좌표계 두 종류가 섞여 있다**

기준 모션 11편이 **서로 다른 좌표계**로 저장돼 있다.

    ref-foxtop         x 39.3~305.8   y ~1e-13        z 249.2~552.1   ← 폴정렬 좌표
    ref-foxtop-split   x 45.7~307.3   y ~1e-13        z 251.0~554.6
    ref-invert         x 59.2~294.8   y ~1e-13        z 289.4~553.4
    ref-sideway-spin   x 37.0~328.4   y ~1e-13        z 292.9~554.5
    ─────────────────────────────────────────────────────────────────
    ref-pdshape        x 16.2~315.9   y 195.9~515.4   z 0 (정확)      ← 이미지 좌표
    (나머지 6편 동일)

★ **y 가 정확한 0 이 아니라 ~1e-13 인 것이 결정적 단서다.** 회전행렬을 실제로
곱한 부동소수점 잔여값이다. 즉 저 4편은 **정렬이 실제로 돌아간** 편이고, 정렬은
설계대로 폴 축을 z 로 보냈다(x축 90° 회전). 반대로 z 가 **정확히 0** 인 7편은
`rtmw_133_to_coco17.py:253-256` 의 scipy ImportError 폴백이 **원본 xyz 를 그대로
복사**한 것이다.

그러므로 진짜 불일치는 **`space='pole_aligned'` 를 11편이 모두 주장하는데 실제로
참인 것은 4편뿐**이라는 점이다.

## 왜 '이미지 좌표'로 통일하는가

소비처가 그쪽을 기대하고, 다수가 이미 그쪽이다:

- 기준 11편 중 **7편이 이미지 좌표**
- **오늘 생성되는 모든 분석 문서가 이미지 좌표**다 (z 전부 0 — scipy 가 여전히 없다)
- 앱의 `reshapePose3dData` 등 소비처는 y 를 세로로 읽는다

즉 소수(4편)를 다수 규약에 맞춘다. 폴정렬 좌표계를 살리는 것은 scipy 설치와
`has_pole_aligned` 게이트를 함께 다루는 별개 결정이다(POLE-AS-INSTRUMENT 스파이크 3).

## 왜 스왑이 옳은 수리인가 (2026-09-14 실측)

폴 지름(45mm)으로 만든 자로 몸통 길이를 재서 확인했다:

    편              현재 몸통px   y/z 스왑 후
    망가진 4편      14.9~20.6    → 55.9~59.5   (정상군 범위로 들어옴)
    정상 7편        50.8~72.9    → 7.0~51.8    (스왑하면 깨짐)

## 채점 영향 = 없다

y↔z 스왑은 평면 반사라 **관절 각도가 불변**이다. 저장된 `angles` 를 원본/스왑본으로
각각 재계산해 대조한 결과 MAE 가 완전히 동일했다. mode1 채점은 `angles` 를 읽으므로
영향이 없다. 깨지는 것은 `joints3d` 소비처다 — 앱 자세 뷰어(reshapePose3dData),
그립 파생, 체형 파생.

`keypointReport` / `referenceKeypointReport` 는 2채널 정규화 좌표라 무관하다(확인함).

## 안전장치

- 결함 게이트: y 가 **좌표 스케일 대비 무시할 수준**(회전 잔여값)이고 z 가 유의미할
  때만 손댄다 → **멱등**하다. 이미 고쳐진 문서를 다시 돌려도 아무 일도 안 일어난다.
  ★ `y != 0` 로 게이트하면 안 된다 — 잔여값이 1e-13 이라 0 이 아니다(실제로 처음에
  이 게이트가 수리를 거부해서 진단이 틀렸음을 잡아냈다).
- `--apply` 없이는 읽기만 한다.
- 쓰기 전 원본 joints3d 를 `--backup-dir` 에 통째로 떨군다.
- 쓰기는 `joints3d` 한 필드만 merge — 다른 필드 무접촉.

사용:
    FIREBASE_SA_PATH=firebase-sa.json backend/.venv/bin/python \\
        backend/scripts/repair_reference_joints3d_axis.py            # dry-run
    ... --apply --backup-dir .planning/quick/260914-.../evidence/ref_backup
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

_HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent))

TARGETS = ["ref-foxtop", "ref-foxtop-split", "ref-invert", "ref-sideway-spin"]
# 해부학적 타당 범위 — 픽셀이 아니라 '정상군과 같은 자릿수인가'를 본다
TORSO_MIN_PX, TORSO_MAX_PX = 35.0, 90.0


def _torso_px(a: np.ndarray) -> float:
    sh = a[:, [5, 6], :2].mean(1)
    hp = a[:, [11, 12], :2].mean(1)
    return float(np.nanmedian(np.linalg.norm(sh - hp, axis=-1)))


def _load(doc: dict) -> np.ndarray:
    t = int(doc["joints3dFrames"])
    j = len(doc["joints3dKeys"])
    return np.asarray(doc["joints3d"], dtype=float).reshape(t, j, 3)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--motions", nargs="*", default=TARGETS)
    ap.add_argument("--apply", action="store_true", help="실제로 쓴다 (없으면 dry-run)")
    ap.add_argument("--backup-dir", default=None)
    a = ap.parse_args()

    import e2e_app_path as e2e  # noqa: PLC0415 - 경로 세팅 후 import
    db = e2e.firestore_client()

    backup_dir = pathlib.Path(a.backup_dir) if a.backup_dir else None
    if a.apply and backup_dir is None:
        raise SystemExit("--apply 는 --backup-dir 이 필요하다")
    if backup_dir:
        backup_dir.mkdir(parents=True, exist_ok=True)

    print(f"{'기준':<22}{'y크기':>8}{'z크기':>8}{'몸통 현재':>10}{'몸통 수리후':>12}  판정")
    repaired = 0
    for m in a.motions:
        ref = db.document(f"reference/{m}")
        doc = ref.get().to_dict() or {}
        if not doc.get("joints3d"):
            print(f"{m:<22}{'joints3d 없음':>40}")
            continue
        arr = _load(doc)
        # 절대 0 이 아니라 '좌표 스케일 대비 무시할 수준'으로 판정한다.
        # 회전 잔여값은 1e-13 이라 `!= 0` 게이트는 통과해 버린다.
        scale = float(np.nanmax(np.abs(arr))) or 1.0
        y_mag = float(np.nanmax(np.abs(arr[:, :, 1]))) / scale
        z_mag = float(np.nanmax(np.abs(arr[:, :, 2]))) / scale
        NEGLIGIBLE = 1e-6

        # ── 결함 게이트 (멱등) ─────────────────────────────────────────
        if not (y_mag < NEGLIGIBLE and z_mag > NEGLIGIBLE):
            print(f"{m:<22}{y_mag:>8.1e}{z_mag:>8.1e}"
                  f"{_torso_px(arr):>10.1f}{'-':>12}  이미지 좌표 — 건너뜀")
            continue

        fixed = arr.copy()
        fixed[:, :, [1, 2]] = fixed[:, :, [2, 1]]
        before, after = _torso_px(arr), _torso_px(fixed)
        sane = TORSO_MIN_PX <= after <= TORSO_MAX_PX
        verdict = "수리 대상" if sane else "★ 수리후도 비정상 — 중단"
        print(f"{m:<22}{y_mag:>8.1e}{z_mag:>8.1e}{before:>10.1f}{after:>12.1f}  {verdict}")
        if not sane:
            raise SystemExit(f"{m}: 스왑해도 몸통이 {after:.1f}px — 가정이 틀렸다. 중단한다.")

        if not a.apply:
            continue

        if backup_dir:
            (backup_dir / f"{m}.joints3d.json").write_text(
                json.dumps({
                    "motionId": m,
                    "joints3dFrames": doc["joints3dFrames"],
                    "joints3dKeys": doc["joints3dKeys"],
                    "joints3d": doc["joints3d"],
                    "reprocessedAt": str(doc.get("reprocessedAt")),
                }, ensure_ascii=False),
                encoding="utf-8",
            )
        ref.set({"joints3d": [float(v) for v in fixed.reshape(-1)]}, merge=True)
        repaired += 1

    print(f"\n{'적용' if a.apply else 'dry-run'} — 수리 {repaired}편")
    if not a.apply:
        print("실제로 쓰려면 --apply --backup-dir <경로>")


if __name__ == "__main__":
    main()

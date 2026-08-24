"""8라운드 — belle 캡처 두 프레임을 각각 '그대로' 일러스트화 (quick-260824-gt1).

belle 08-24: "내가 캡쳐한 거 그대로 좀 안 되나. 원본 다리도 짝짝이고."
교훈: 다리만 잔상으로 떼는 문법은 파워스핀엔 부적합 — 오류 순간은 몸 전체가
다른 자세다. 그래서 (1) 왼쪽 프레임(스윙 중 = before)과 (2) 오른쪽 프레임
(스플릿 = after)을 각각 단일 인물 일러스트로 충실히 뜨고, 합성은 코드가 한다
(왼쪽 = 통째 흐린 잔상). 단일 자세 충실 재현은 이 파이프라인의 검증된 강점.

실행:
    GEMINI_API_KEY=... python3 generate_faithful_r8.py \
        --left <belle4_left.jpg> --right <belle4_right.jpg> --n 2
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
GEN_PY = REPO / ".planning/quick/260809-ill-missing-illustrations/generate.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


G = _load("ill_generate", GEN_PY)
R1 = _load("ghost_r1", HERE / "generate_ghost_powerspin.py")

# 단일 인물, 잔상 없음 — 자세는 FIRST 사진 그대로
SINGLE_GUIDE = (
    "Draw exactly ONE figure in exactly the pose of the FIRST image - reproduce "
    "every limb angle faithfully, including any bent knee or incomplete split; do "
    "NOT idealise, straighten or 'correct' the pose. No ghost, no second figure, "
    "no motion trail. Draw NO arrows, NO angle marker, NO measurement line, NO "
    "number, NO text, NO red mark of any kind - the body only."
)

POSES = {
    "before": (
        "captured mid-swing on a single vertical pole, seen from the side: one hand "
        "gripping the pole high overhead, the other hand gripping the pole low, the "
        "torso folded down and tilted with the head below the shoulders, both legs "
        "swung out to the right side - the upper leg reaching up-and-right above "
        "horizontal, the lower leg reaching down-and-right below horizontal, the "
        "split clearly incomplete"
    ),
    "after": (
        "spinning on a single vertical pole, seen from the side: one hand gripping "
        "the pole high overhead, the other hand gripping the pole at hip height, "
        "hips close to the pole, torso upright leaning slightly away from the pole, "
        "the raised leg extended up alongside the pole and the lower leg extended "
        "down and slightly forward"
    ),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--left", required=True, help="before 프레임 (리포 밖)")
    ap.add_argument("--right", required=True, help="after 프레임 (리포 밖)")
    ap.add_argument("--n", type=int, default=2)
    ap.add_argument("--out", default=str(HERE / "out_r8"))
    args = ap.parse_args()

    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        sys.exit("GEMINI_API_KEY 미설정")

    rows = {G.asset_name(r): r for r in G.load_targets()}
    row = dict(rows["ref-power-spin--leg"])
    anchor = G.resolve(row["anchor"])
    frames = {"before": Path(args.left), "after": Path(args.right)}
    for p in list(frames.values()) + [anchor]:
        if not p.exists():
            sys.exit(f"입력 없음: {p}")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    api_calls = 0
    for kind, frame in frames.items():
        prompt = G.PROMPT.format(
            pose=POSES[kind],
            guide=SINGLE_GUIDE,
            orientation=G._orientation_hint(row.get("orientation")),
            framing=G._framing_block(row),
        )
        (out_dir / f"prompt_{kind}.txt").write_text(prompt)
        for i in range(1, args.n + 1):
            out = out_dir / f"powerspin_{kind}-{i}.jpg"
            if out.exists():
                print(f"[{kind}-{i}] 이미 존재 — 건너뜀")
                continue
            print(f"[{kind}-{i}] 생성 중…")
            parts = [{"text": prompt}, G.inline_part(frame), G.inline_part(anchor)]
            api_calls += 1
            if R1.save_image(R1.call(parts, key), out):
                print(f"  saved {out.name}")
    print(f"API calls this run: {api_calls} (model={G.MODEL})")


if __name__ == "__main__":
    main()

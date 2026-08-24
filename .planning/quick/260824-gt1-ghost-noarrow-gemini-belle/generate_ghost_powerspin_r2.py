"""파워스핀 다리 ghost-noarrow 2라운드 (quick-260824-gt1, belle 지시 08-24).

1라운드와의 차이 (PREDICTION.md 2라운드 절이 스펙):
  - 자세 앵커(FIRST) = belle 제공 실촬영 프레임 (후면 뷰, 덜 벌려진 스플릿).
    경로는 --frame 으로 주입 — 실촬영 인물이라 리포에 커밋하지 않는다 (PII).
  - 잔상 = FIRST 프레임의 실제 다리 위치 그대로 (창작 0).
  - 실선 = 같은 몸에서 다리만 한 줄 수직 스플릿으로 교정.
  - 스타일 앵커(SECOND)·PROMPT 골격·익명·의상 절은 1라운드와 동일 (D-02, D-03).

실행:
    GEMINI_API_KEY=$(aws ssm get-parameter --name /sunity/motion/gemini-api-key \
        --with-decryption --profile sunity-motion --region ap-northeast-2 \
        --query 'Parameter.Value' --output text) \
    python3 generate_ghost_powerspin_r2.py --frame <belle_scene_right.jpg> --n 3
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

# 자세 절 — belle 옆모습 프레임(08-24 2차 제공) 관측에서 서술.
POSE_R2 = (
    "side view, spinning on a single vertical pole: one hand gripping the pole high "
    "overhead, the other hand gripping the pole at hip height, hips close to the "
    "pole, torso upright and leaning slightly away from the pole, hair tied back. "
    "Keep the torso, arms, grips, camera angle and pole exactly as in the FIRST "
    "image; only the SOLID figure's legs are corrected into a full vertical split "
    "as described in the guide"
)

# 잔상 = FIRST 실프레임 다리 그대로 / 실선 = 한 줄 수직 스플릿 교정.
GUIDE_R2 = (
    "Show HOW to finish this position, not just the position. Draw the SAME figure "
    "twice, superimposed in the SAME place: (1) a faint, very light, semi-transparent "
    "'before' ghost of the two legs kept EXACTLY where they are in the FIRST image - "
    "the raised ghost leg staying CLOSE to the pole, tilted only slightly away from "
    "it with a softly bent knee, its foot no more than one foot-length away from the "
    "pole, and the lower ghost leg reaching down and forward at a diagonal with its "
    "softly bent knee - the ghost split must be clearly NARROWER than the solid "
    "split and NEVER wider than the legs in the FIRST image - do not invent new "
    "ghost leg positions, trace the FIRST image's legs - the two ghost legs must be "
    "clearly separate, never merged into one, and each ghost leg must stay clearly "
    "distinct from the pole, never blending into the pole or doubling the pole "
    "line; and (2) the solid, fully drawn 'after' legs corrected into ONE straight "
    "vertical line along the pole - the raised leg fully straightened up alongside "
    "the pole and the lower leg pressed straight down so its foot points at the "
    "floor directly beneath the hips, both knees fully extended, clearly MORE open "
    "than the ghost legs. The ghost is only the two legs; torso, arms, head and pole are drawn "
    "once, solid. Draw NO arrows, NO angle marker, NO measurement line, NO number, "
    "NO text, NO red mark of any kind - the body only. The ghost must read as a "
    "motion trail of the same person, never as a second person."
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frame", required=True, help="belle 실촬영 앵커 (리포 밖 경로)")
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--out", default=str(HERE / "out_r2"))
    args = ap.parse_args()

    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        sys.exit("GEMINI_API_KEY 미설정 (SSM 에서 환경변수로만)")

    frame = Path(args.frame)
    rows = {G.asset_name(r): r for r in G.load_targets()}
    row = dict(rows["ref-power-spin--leg"])
    anchor = G.resolve(row["anchor"])  # 스타일 앵커는 1라운드와 동일
    for p in (frame, anchor):
        if not p.exists():
            sys.exit(f"입력 없음: {p}")

    prompt = G.PROMPT.format(
        pose=POSE_R2,
        guide=GUIDE_R2,
        orientation=G._orientation_hint(row.get("orientation")),
        framing=G._framing_block(row),
    )
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "prompt_r2.txt").write_text(prompt)

    api_calls = 0
    for i in range(1, args.n + 1):
        out = out_dir / f"ref-power-spin--leg__ghost-r2-{i}.jpg"
        if out.exists():
            print(f"[r2-{i}] 이미 존재 — 건너뜀")
            continue
        print(f"[r2-{i}] 생성 중…")
        parts = [{"text": prompt}, G.inline_part(frame), G.inline_part(anchor)]
        api_calls += 1
        if R1.save_image(R1.call(parts, key), out):
            print(f"  saved {out.name} ({out.stat().st_size} bytes)")
    print(f"API calls this run: {api_calls} (model={G.MODEL})")


if __name__ == "__main__":
    main()

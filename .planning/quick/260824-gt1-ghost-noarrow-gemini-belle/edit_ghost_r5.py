"""5라운드 — 기존 후보(r2-3)의 잔상 다리만 좁히는 편집 (quick-260824-gt1).

belle 08-24: "잔상의 다리벌림(학생 다리)만 좁히면 되는데" — 신규 생성 중단,
2라운드 belle 가 "그나마 맞다" 한 본을 베이스로 잔상만 편집한다.
크기 제어 실패 4라운드의 교훈: 새 그림 = 모델이 크기를 매번 재량으로 정함.
편집 = 베이스가 크기의 기준점을 고정함.

실행:
    GEMINI_API_KEY=$(aws ssm get-parameter --name /sunity/motion/gemini-api-key \
        --with-decryption --profile sunity-motion --region ap-northeast-2 \
        --query 'Parameter.Value' --output text) \
    python3 edit_ghost_r5.py --n 3
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

BASE = HERE / "out_r2" / "ref-power-spin--leg__ghost-r2-3.jpg"

EDIT_PROMPT = (
    "Edit this instructional illustration. Change ONLY the two faint, "
    "semi-transparent ghost legs (the light 'before' motion-trail legs) - nothing "
    "else. Narrow the ghost split: move the raised ghost leg so it lies almost "
    "along the pole, tilted only slightly away from it, its foot close to the "
    "pole; and move the lower ghost leg closer to the pole line so its foot ends "
    "nearly beneath the hips, with a softly bent knee. After the edit the ghost "
    "split must look clearly much NARROWER than the solid legs' split - the ghost "
    "must never look like a wide split. Do NOT move, redraw or restyle the solid "
    "figure, the pole, the arms, the head, the torso, the clothing or the "
    "background. Keep the line quality, palette, shading and composition "
    "identical to the input image. Keep the ghost faint and semi-transparent. "
    "Draw NO arrows, NO angle marker, NO number, NO text, NO red mark of any "
    "kind."
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--out", default=str(HERE / "out_r5"))
    ap.add_argument("--base", default=str(BASE))
    args = ap.parse_args()

    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        sys.exit("GEMINI_API_KEY 미설정 (SSM 에서 환경변수로만)")
    base = Path(args.base)
    if not base.exists():
        sys.exit(f"베이스 없음: {base}")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "prompt_r5_edit.txt").write_text(EDIT_PROMPT)

    api_calls = 0
    for i in range(1, args.n + 1):
        out = out_dir / f"ref-power-spin--leg__ghost-r5-{i}.jpg"
        if out.exists():
            print(f"[r5-{i}] 이미 존재 — 건너뜀")
            continue
        print(f"[r5-{i}] 편집 중…")
        parts = [{"text": EDIT_PROMPT}, G.inline_part(base)]
        api_calls += 1
        if R1.save_image(R1.call(parts, key), out):
            print(f"  saved {out.name} ({out.stat().st_size} bytes)")
    print(f"API calls this run: {api_calls} (model={G.MODEL})")


if __name__ == "__main__":
    main()

"""일러스트 A(어떻게) 첫 장 — 킵업 다리 (quick-260818-nnm).

belle 2026-08-18: 일러스트는 확대 비교(사진)를 다시 그리는 것이 아니라 **방법**을 보여준다.
승인 레시피(익명·의상·배경·스타일·프레이밍)는 generate.py 의 것을 그대로 쓰고,
**GUIDE 문단만** 각도 마커 → "가는 길"(잔상 + 방향 화살표)로 바꾼다.

실행:
    GEMINI_API_KEY=$(aws ssm get-parameter --name /sunity/motion/gemini-api-key \
        --with-decryption --profile sunity-motion --region ap-northeast-2 \
        --query 'Parameter.Value' --output text) \
    python3 generate_how.py --n 4 --out out/

키는 환경변수로만. 표준 라이브러리만. 동작명 분기 0 (targets.json + phrasebook 재사용).
"""
from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
GEN_PY = REPO / ".planning/quick/260809-ill-missing-illustrations/generate.py"


def _load_generate_module():
    spec = importlib.util.spec_from_file_location("ill_generate", GEN_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


G = _load_generate_module()

# "어떻게" 표시 문단 — 두 변형. 어느 쪽이 읽히는지 belle 판정으로 가른다.
#   ghost : 좁은 다리 잔상(연하게) → 활짝 벌린 다리(실선) + 바깥 방향 화살표
#   arrow : 잔상 없이 활짝 벌린 다리 + 바깥 방향 화살표만 (안전한 절반)
HOW_GUIDE = {
    "ghost": (
        "Show HOW to get into this position, not just the position. Draw the SAME figure "
        "twice, superimposed in the SAME place: (1) a faint, very light, semi-transparent "
        "'before' ghost of the two legs hanging closer together and slightly bent, and "
        "(2) the solid, fully drawn 'after' legs straight and spread wide - exactly as in "
        "the FIRST image. The ghost is only the two legs; torso, arms, head and pole are "
        "drawn once, solid. Then overlay TWO coral-red curved arrows, one per leg, each "
        "starting at the ghost foot and sweeping outward to the solid foot, showing the "
        "legs opening apart. Arrow heads must be clear. Draw NO angle marker, NO straight "
        "measurement line, NO number, NO text. The ghost must read as a motion trail of "
        "the same person, never as a second person."
    ),
    "arrow": (
        "Show HOW to get into this position. Overlay TWO coral-red curved arrows, one per "
        "leg, each starting near the inner thigh close to the pole and sweeping outward "
        "along the leg toward the foot, showing the legs opening apart into the wide "
        "straddle. Arrow heads must be clear and point outward. Draw NO angle marker, NO "
        "straight measurement line, NO number, NO text, no red mark on any other body part."
    ),
}


def build_prompt_how(row: dict, variant: str) -> str:
    """generate.py 의 PROMPT 골격에 GUIDE 만 교체 — 나머지 문단은 바이트 동일."""
    return G.PROMPT.format(
        pose=row["promptPose"],
        guide=HOW_GUIDE[variant],
        orientation=G._orientation_hint(row.get("orientation")),
        framing=G._framing_block(row),
    )


def call(parts: list[dict], key: str) -> dict:
    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }
    req = urllib.request.Request(
        f"{G.ENDPOINT}?key={key}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:  # 키는 절대 로그에 남기지 않는다
        sys.exit(f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:400]}")


def save_image(payload: dict, out: Path) -> bool:
    for cand in payload.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            blob = part.get("inlineData") or part.get("inline_data")
            if blob and blob.get("data"):
                out.write_bytes(base64.b64decode(blob["data"]))
                return True
            if part.get("text"):
                print(f"  [text] {part['text'][:200]}")
    print(f"  이미지 없음 — finishReason={payload.get('candidates', [{}])[0].get('finishReason')}")
    return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset", default="ref-kip-up--leg")
    ap.add_argument("--n", type=int, default=2, help="변형당 장수")
    ap.add_argument("--out", default=str(HERE / "out"))
    args = ap.parse_args()

    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        sys.exit("GEMINI_API_KEY 미설정")

    rows = {G.asset_name(r): r for r in G.load_targets()}
    row = dict(rows[args.asset])
    frame = G.resolve(row["inputFrame"])
    anchor = G.resolve(row["anchor"])
    for p in (frame, anchor):
        if not p.exists():
            sys.exit(f"입력 없음: {p}")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for variant in ("ghost", "arrow"):
        prompt = build_prompt_how(row, variant)
        (out_dir / f"prompt_{variant}.txt").write_text(prompt)
        for i in range(1, args.n + 1):
            out = out_dir / f"{args.asset}__how-{variant}{i}.jpg"
            print(f"[{variant}{i}] 생성 중…")
            parts = [{"text": prompt}, G.inline_part(frame), G.inline_part(anchor)]
            if save_image(call(parts, key), out):
                print(f"  saved {out.name} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

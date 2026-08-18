"""골격 조건부 A/B 생성 (quick-260818-muy).

    A = 현행 generate.py 와 바이트 동일한 프롬프트·입력 (프레임 + 스타일 앵커)
    B = A + 뼈대 이미지 1장 + 그것을 따르라는 한 문단 (SKELETON 블록)

그 외 전부 동일 — 모델·해상도·앵커·프레임·GUIDE·FRAMING·STYLE. 차이는 골격뿐이어야
결과 차이를 골격 탓으로 돌릴 수 있다.

실행:
    GEMINI_API_KEY=$(aws ssm get-parameter --name /sunity/motion/gemini-api-key \
        --with-decryption --profile sunity-motion --region ap-northeast-2 \
        --query 'Parameter.Value' --output text) \
    python3 generate_ab.py --asset ref-pdshape--leg \
        --frame <크롭 프레임.jpg> --skel <뼈대.png> --out out/

키는 환경변수로만. 표준 라이브러리만. 동작명 분기 0 (targets.json 재사용).
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
    """현행 generate.py 를 그대로 import — 프롬프트 조립 함수를 재사용한다(복제 금지)."""
    spec = importlib.util.spec_from_file_location("ill_generate", GEN_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


G = _load_generate_module()

# B 팔에만 들어가는 한 문단. POSE FIDELITY 바로 뒤에 붙는다.
SKELETON_BLOCK = """
SKELETON (binding):
The THIRD reference image is a stick-figure skeleton extracted from the FIRST image: white bones on black, red dots at the joints, in the SAME pixel frame as the FIRST image. Treat it as the ground truth for WHERE every joint is and WHICH body parts are inside the frame. Every limb you draw must lie on top of its bone in the skeleton; every joint must sit on its red dot; body parts that have NO bone in the skeleton are OUTSIDE the frame and must not be drawn. Do NOT show the skeleton itself - it only tells you the layout. If the pose description above ever disagrees with the skeleton, follow the skeleton.
"""


def build_prompt_b(row: dict) -> str:
    """A 프롬프트에 SKELETON 블록만 삽입 — 나머지 바이트 동일."""
    a = G.build_prompt(row)
    marker = "\nANONYMISATION:"
    assert marker in a, "PROMPT 구조 변경됨 — 삽입 위치 재확인"
    return a.replace(marker, SKELETON_BLOCK + marker, 1)


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
    ap.add_argument("--asset", required=True)
    ap.add_argument("--frame", required=True, help="크롭 적용 입력 프레임 (A/B 공통)")
    ap.add_argument("--skel", required=True, help="같은 크롭의 뼈대 PNG (B 전용)")
    ap.add_argument("--out", default=str(HERE / "out"))
    ap.add_argument("--n", type=int, default=1, help="팔당 생성 장수")
    args = ap.parse_args()

    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        sys.exit("GEMINI_API_KEY 미설정")

    rows = {G.asset_name(r): r for r in G.load_targets()}
    row = dict(rows[args.asset])
    frame, skel = Path(args.frame), Path(args.skel)
    anchor = G.resolve(row["anchor"])
    for p in (frame, skel, anchor):
        if not p.exists():
            sys.exit(f"입력 없음: {p}")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    prompt_a = G.build_prompt(row)
    prompt_b = build_prompt_b(row)
    (out_dir / "prompt_A.txt").write_text(prompt_a)
    (out_dir / "prompt_B.txt").write_text(prompt_b)

    for i in range(1, args.n + 1):
        parts_a = [{"text": prompt_a}, G.inline_part(frame), G.inline_part(anchor)]
        parts_b = [{"text": prompt_b}, G.inline_part(frame), G.inline_part(anchor),
                   G.inline_part(skel)]
        for tag, parts in (("A", parts_a), ("B", parts_b)):
            out = out_dir / f"{args.asset}__{tag}{i}.jpg"
            print(f"[{tag}{i}] 생성 중…")
            if save_image(call(parts, key), out):
                print(f"  saved {out.name} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

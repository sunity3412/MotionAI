"""일러스트 "어떻게" 화살표 — 킵업 다리, 20 계열 A 길(그림에 굽기) (quick-260821-fe9).

belle 2026-08-21 판정 (재논의 금지):
  D-01 3단계 세트 기각 — stage40/60 절대 불가, exq out/ 아카이브 무변경
  D-02 채택 계열 = 20 종류 (잔상이 실선보다 약간만 좁음)
  D-03 화살표 필요 — A(그림에 굽기, 이 스크립트) vs B(앱 오버레이 합성) 실물 대조
  D-04 화살표 문법: 시작점 = 반드시 잔상의 발. 폴 가운데 출발 금지. A 는 표기 0 (표기는 B 만)

승인 레시피(익명·의상·배경·스타일·프레이밍)는 260809 generate.py 의 것을 그대로 쓰고
(무변경), GUIDE 문단은 260818-nnm generate_how.py 의 HOW_GUIDE["ghost"](08-18 belle
"가" 통과 변형)에서 3가지만 수정:
  a. 잔상 다리 서술 -> exq stage20 서술 (실선보다 약간만 좁게) — D-02
  b. exq 라운드에서 일을 한 분리 절 추가 (두 잔상 다리는 폴 양옆에 분명히 분리)
  c. 화살표 절 강화 — 잔상 발에서 정확히 출발, 폴/몸 중앙 출발 명시 금지("NEVER"),
     "짧아도 맞다" 절 (08-18 4장 전부 폴 가운데 출발 반려 전례), NO text 절 유지

실행:
    GEMINI_API_KEY=$(aws ssm get-parameter --name /sunity/motion/gemini-api-key \
        --with-decryption --profile sunity-motion --region ap-northeast-2 \
        --query 'Parameter.Value' --output text) \
    python3 generate_arrow20.py --n 2 --out out/

키는 환경변수로만 — 파일·로그·stdout 어디에도 남기지 않는다 (T-fe9-01).
표준 라이브러리만 — 신규 패키지 0 (T-fe9-SC). 이미 존재하는 출력 파일은
건너뛰므로, 부분 실패 시 같은 커맨드 재실행이 곧 재시도다.
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

# HOW_GUIDE["ghost"] (08-18 belle "가" 통과 변형) 기반 단일 문단.
# 수정 3가지(a 잔상 20 수준, b 분리 절, c 화살표 절 강화) 외에는 원문 유지.
ARROW20_GUIDE = (
    "Show HOW to get into this position, not just the position. Draw the SAME figure "
    "twice, superimposed in the SAME place: (1) a faint, very light, semi-transparent "
    "'before' ghost of the two legs only slightly narrower than the solid wide straddle, "
    "the ghost legs almost as wide as the solid legs, just a little less open - "
    "the two ghost legs must be clearly separate, one on each side of the pole, never "
    "merged into one; and (2) the solid, fully drawn 'after' legs straight and spread "
    "wide - exactly as in the FIRST image. The ghost is only the two legs; torso, arms, "
    "head and pole are drawn once, solid. Then overlay TWO coral-red curved arrows, one "
    "per leg, each starting exactly at the ghost foot and sweeping outward to the solid "
    "foot on the same side, showing the legs opening apart. Arrow heads must be clear. "
    "The arrows must NEVER start at the pole or the center of the body. Because the "
    "ghost legs are close to the solid legs, the arrows may be short - that is correct; "
    "do not enlarge the arrows or move their start points to make them longer. Draw NO "
    "angle marker, NO straight measurement line, NO number, NO text. The ghost must "
    "read as a motion trail of the same person, never as a second person."
)


def build_prompt(row: dict) -> str:
    """generate.py 의 PROMPT 골격에 GUIDE 만 교체 — 나머지 문단은 바이트 동일."""
    return G.PROMPT.format(
        pose=row["promptPose"],
        guide=ARROW20_GUIDE,
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
    ap.add_argument("--asset", default="ref-kip-up--leg")  # D-04 대상 1종
    ap.add_argument("--n", type=int, default=2, help="장수")
    ap.add_argument("--out", default=str(HERE / "out"))
    args = ap.parse_args()

    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        sys.exit("GEMINI_API_KEY 미설정 (SSM 에서 읽어 환경변수로만 전달할 것)")

    rows = {G.asset_name(r): r for r in G.load_targets()}
    if args.asset not in rows:
        sys.exit(f"미등록 asset: {args.asset} (가능: {', '.join(sorted(rows))})")
    row = dict(rows[args.asset])
    frame = G.resolve(row["inputFrame"])
    anchor = G.resolve(row["anchor"])
    for p in (frame, anchor):
        if not p.exists():
            sys.exit(f"입력 없음: {p}")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    prompt = build_prompt(row)
    (out_dir / "prompt_A_arrow20.txt").write_text(prompt)
    for i in range(1, args.n + 1):
        out = out_dir / f"{args.asset}__A-arrow20-{i}.jpg"
        if out.exists():  # 부분 실패 재실행 시 기존 성공분은 건너뛴다
            print(f"[A-arrow20-{i}] 이미 존재 — 건너뜀")
            continue
        print(f"[A-arrow20-{i}] 생성 중…")
        parts = [{"text": prompt}, G.inline_part(frame), G.inline_part(anchor)]
        if save_image(call(parts, key), out):
            print(f"  saved {out.name} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

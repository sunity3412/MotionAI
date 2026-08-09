"""어깨·팔 결함 일러스트 생성 (quick-260731-plf Task 3 — 33-14 승인 레시피 그대로).

실행:
    GEMINI_API_KEY=$(aws ssm get-parameter --name /sunity/motion/gemini-api-key \
        --with-decryption --profile sunity-motion --region ap-northeast-2 \
        --query 'Parameter.Value' --output text) \
    python3 generate.py --asset ref-power-spin--shoulder --try 1

레시피 (33-14, L-4 — 개선 금지. S24 는 이미 PASS):
    입력 1 = 그 동작 기준 영상의 국면 완성 프레임(33-A1 국면 데이터 키잉, 대상 부위 중심 크롭)
    입력 2 = 스타일 앵커(같은 동작 통과본 > 같은 방위 통과본)
    프롬프트 = 자세 충실 + 익명화 + 가이드 표시

동작명 조건 분기 **0** — 프롬프트의 모든 가변부(`promptPose`·`promptTarget`·`guideType`)는
`targets.json` 에서 읽는다. 새 동작을 추가할 때 이 파일은 손대지 않는다.

키 취급: 환경변수로만 읽고 파일·로그·stdout 어디에도 문자열로 남기지 않는다 (T-33C4-04).
표준 라이브러리만 사용 — 신규 패키지 0 (T-33C4-SC).
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TARGETS = HERE / "targets.json"
GEN_DIR = HERE / "gen"
MODEL = "gemini-3-pro-image"
ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{MODEL}:generateContent"
)

# 가이드 표시 문장 — `guideType` 데이터로만 갈린다 (동작명 분기 아님).
# line = 신전·라인 계열 / circle = hook·잠금 계열. 굽힘이 정답인 부위에 직선 금지(L-4).
GUIDE_SENTENCE = {
    "line": (
        "Overlay ONE single perfectly straight coral-red line (solid, even thickness) "
        "running along {target}. The line must stay on the body only - it must not "
        "extend past the limb, cross the face, or curve."
    ),
    "circle": (
        "Overlay ONE coral-red open ring (a clean circle outline, even thickness, "
        "nothing filled in) centred exactly on {target}. Draw no other marks. "
        "Do NOT draw any straight line anywhere in the image - this body part is "
        "correct while bent or locked, so a straight line would teach the wrong thing."
    ),
}

PROMPT = """Redraw the FIRST reference image as a clean instructional illustration, using the SECOND reference image only as a style reference.

POSE FIDELITY (most important):
Reproduce the exact pose, orientation and camera viewpoint of the FIRST image: {pose}. Keep the pole in the same position and angle as in the FIRST image. Do NOT copy the pose, orientation or limb arrangement from the SECOND image - the SECOND image is ONLY for drawing style (line quality, palette, shading, background tone).

ANONYMISATION:
The figure must have NO facial features at all - no eyes, no nose, no mouth, no eyebrows. Leave the face as blank, smooth, unmarked skin. Do not draw a portrait.
The figure MUST still have hair - dark hair tied back in a bun or ponytail, like the SECOND
reference image. Never draw a bald or hairless head: anonymise the face only, keep the hair.

CLOTHING (never bare):
The figure always wears a dark taupe sports bra AND matching shorts, exactly like the SECOND
reference image. The torso is never bare, never topless, never in underwear.

SCENE:
Exactly ONE vertical pole in the image. Never draw a second pole, a doubled pole line, a
mirror, or a reflection. Exactly ONE person - no second figure, no stray extra limb entering
from any edge.

GUIDE MARK:
{guide}

ANATOMY:
Exactly two arms and two legs, five fingers per hand, five toes per foot, joints bending only in anatomically possible directions.
Exactly ONE head. The head must be attached to the neck and clearly separated from the hips
and thighs - never fused into the pelvis, buttock or torso, and never duplicated anywhere in
the image. The head sits on the neck in its natural direction - never twisted round backwards
or rotated away from the spine.
Where limbs overlap or the body is folded, keep every limb readable as a separate outline:
draw the contour where one body part passes in front of another so the viewer can count two
arms and two legs without ambiguity.
Every limb must be anatomically plausible along its whole length - a calf must not bend where
there is no joint, a foot must join the ankle in a natural direction, and no limb may taper
into a shapeless mass. If a body part would be ambiguous, place it outside the frame instead
of drawing it wrong.

FRAMING:
Portrait 3:4. The figure must FILL the frame - crop in close so the body occupies most of the image. Avoid large empty background areas; leave only a small margin around the figure.

STYLE:
Soft pencil-and-watercolour illustration on a plain warm off-white background, muted warm skin tones, dark taupe activewear, no text, no logos, no watermark, no border.
"""


def load_targets() -> list[dict]:
    data = json.loads(TARGETS.read_text(encoding="utf-8"))
    return data["targets"] if isinstance(data, dict) else data


def asset_name(row: dict) -> str:
    """장면 표의 `asset` 규칙과 문자 동일 — {motionId}--{parts를 '-' 로 이은 것}."""
    return f"{row['motionId']}--{row['part'].replace('+', '-')}"


def inline_part(path: Path) -> dict:
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    return {
        "inlineData": {
            "mimeType": mime,
            "data": base64.b64encode(path.read_bytes()).decode("ascii"),
        }
    }


def build_prompt(row: dict) -> str:
    guide_tpl = GUIDE_SENTENCE[row["guideType"]]
    return PROMPT.format(
        pose=row["promptPose"],
        guide=guide_tpl.format(target=row["promptTarget"]),
    )


def resolve(p: str) -> Path:
    path = Path(p)
    return path if path.is_absolute() else (REPO / p)


def generate(row: dict, attempt: int, anchor_override: str | None) -> Path:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        sys.exit("GEMINI_API_KEY 미설정 (SSM 에서 읽어 환경변수로만 전달할 것)")

    input_frame = resolve(row["inputFrame"])
    anchor = resolve(anchor_override or row["anchor"])
    for p in (input_frame, anchor):
        if not p.exists():
            sys.exit(f"입력 없음: {p}")

    body = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": build_prompt(row)},
                    inline_part(input_frame),
                    inline_part(anchor),
                ],
            }
        ],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }

    req = urllib.request.Request(
        f"{ENDPOINT}?key={key}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:  # 키는 절대 로그에 넣지 않는다
        sys.exit(f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:400]}")

    GEN_DIR.mkdir(parents=True, exist_ok=True)
    out = GEN_DIR / f"{asset_name(row)}__try{attempt}.jpg"
    for cand in payload.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            blob = part.get("inlineData") or part.get("inline_data")
            if blob and blob.get("data"):
                out.write_bytes(base64.b64decode(blob["data"]))
                print(f"saved {out.relative_to(REPO)} ({out.stat().st_size} bytes)")
                return out
            if part.get("text"):
                print(f"[text] {part['text'][:300]}")
    sys.exit(f"이미지 파트 없음 — finishReason={payload.get('candidates', [{}])[0].get('finishReason')}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset", required=True, help="asset 키 (예: ref-power-spin--shoulder)")
    ap.add_argument("--try", dest="attempt", type=int, default=1)
    ap.add_argument("--anchor", default=None, help="스타일 앵커 교체 (L-6 실패 대응)")
    ap.add_argument("--input", default=None, help="입력 프레임 교체 (크롭 재조정)")
    args = ap.parse_args()

    rows = {asset_name(r): r for r in load_targets()}
    if args.asset not in rows:
        sys.exit(f"미등록 asset: {args.asset} (가능: {', '.join(sorted(rows))})")
    row = dict(rows[args.asset])
    if args.input:
        row["inputFrame"] = args.input
    generate(row, args.attempt, args.anchor)


if __name__ == "__main__":
    main()

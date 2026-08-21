"""일러스트 "어떻게" 3단계 잔상 — 킵업 다리 ghost-noarrow (quick-260821-exq).

belle 2026-08-21 확정 (재논의 금지):
  D-01 잔상은 모델이 그린다 ("가" 스타일 — 연한 반투명 잔상 다리)
  D-02 잔상 각도 3단계 (deficit 20/40/60) — 앱이 학생 값에 가장 가까운 장을 고른다
  D-03 화살표·수치·표기는 그림에 굽지 않는다 — 앱이 잔상 발 -> 실선 발로 그린다
  D-04 대상 = ref-kip-up--leg 1종만

승인 레시피(익명·의상·배경·스타일·프레이밍)는 260809 generate.py 의 것을 그대로 쓰고
(L-4 무변경), 260818-nnm generate_how.py 의 HOW_GUIDE["ghost-noarrow"] 원문에서
**잔상 다리 서술 절만** 스테이지별로 치환한다. NO arrows/text/marker 절과
"다리 분리·모션 트레일" 절은 3단계 공통 유지.

실행:
    GEMINI_API_KEY=$(aws ssm get-parameter --name /sunity/motion/gemini-api-key \
        --with-decryption --profile sunity-motion --region ap-northeast-2 \
        --query 'Parameter.Value' --output text) \
    python3 generate_ghost3.py --n 2 --out out/

키는 환경변수로만 — 파일·로그·stdout 어디에도 남기지 않는다 (T-exq-01).
표준 라이브러리만 — 신규 패키지 0 (T-exq-SC). 이미 존재하는 출력 파일은
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

# generate_how.py HOW_GUIDE["ghost-noarrow"] 원문 골격 — {ghost_legs} 자리만
# 스테이지별로 치환된다. 그 외 모든 절은 3단계 공통(변경 금지):
#   - "clearly separate, one on each side of the pole, never merged into one"
#     (특히 stage60 에서 다리 합쳐짐 위험 최고)
#   - "The ghost is only the two legs; torso, arms, head and pole are drawn once, solid"
#   - "Draw NO arrows, NO angle marker, NO measurement line, NO number, NO text,
#      NO red mark of any kind" (D-03)
#   - "never as a second person"
_GHOST_TEMPLATE = (
    "Show HOW to get into this position, not just the position. Draw the SAME figure "
    "twice, superimposed in the SAME place: (1) a faint, very light, semi-transparent "
    "'before' ghost of the two legs {ghost_legs} - "
    "the two ghost legs must be clearly separate, one on each side of the pole, never "
    "merged into one; and (2) the solid, fully drawn 'after' legs straight and spread "
    "wide - exactly as in the FIRST image. The ghost is only the two legs; torso, arms, "
    "head and pole are drawn once, solid. Draw NO arrows, NO angle marker, NO "
    "measurement line, NO number, NO text, NO red mark of any kind - the body only. "
    "The ghost must read as a motion trail of the same person, never as a second person."
)

# 잔상 다리 서술 절 — belle 확정 가이드 (deficit 는 명목값, meta.json 에 실림).
_GHOST_LEGS = {
    # deficit 20도: 목표보다 약간만 좁게
    "stage20": (
        "only slightly narrower than the solid wide straddle, the ghost legs almost "
        "as wide as the solid legs, just a little less open"
    ),
    # deficit 40도: 중간
    "stage40": (
        "about halfway between hanging straight down and the full wide straddle"
    ),
    # deficit 60도: 거의 모은 다리
    "stage60": (
        "much closer together, hanging nearly straight down with a slight bend"
    ),
}

# 스테이지별 완성 문단 — 값이 곧 최종 GUIDE 문단이다.
GHOST_STAGES = {
    stage: _GHOST_TEMPLATE.format(ghost_legs=legs)
    for stage, legs in _GHOST_LEGS.items()
}


def build_prompt_stage(row: dict, stage: str) -> str:
    """generate.py 의 PROMPT 골격에 GUIDE 만 교체 — 나머지 문단은 바이트 동일."""
    return G.PROMPT.format(
        pose=row["promptPose"],
        guide=GHOST_STAGES[stage],
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
    ap.add_argument("--asset", default="ref-kip-up--leg")  # D-04: 확산은 belle 판정 후
    ap.add_argument("--n", type=int, default=2, help="스테이지당 장수")
    ap.add_argument("--out", default=str(HERE / "out"))
    ap.add_argument("--stages", default="stage20,stage40,stage60", help="쉼표 구분")
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
    for stage in args.stages.split(","):
        if stage not in GHOST_STAGES:
            sys.exit(f"미등록 stage: {stage} (가능: {', '.join(GHOST_STAGES)})")
        prompt = build_prompt_stage(row, stage)
        (out_dir / f"prompt_{stage}.txt").write_text(prompt)
        for i in range(1, args.n + 1):
            out = out_dir / f"{args.asset}__ghost-{stage}-{i}.jpg"
            if out.exists():  # 부분 실패 재실행 시 기존 성공분은 건너뛴다
                print(f"[{stage}-{i}] 이미 존재 — 건너뜀")
                continue
            print(f"[{stage}-{i}] 생성 중…")
            parts = [{"text": prompt}, G.inline_part(frame), G.inline_part(anchor)]
            if save_image(call(parts, key), out):
                print(f"  saved {out.name} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

"""파워스핀 다리 ghost-noarrow 잔상 후보 생성 (quick-260824-gt1).

이 태스크의 잠긴 결정 (재논의 금지):
  D-01 잔상(오류) 자세 = Task 1 실측 유래만 — leg_extension(무릎 약 39° 굽음,
       10건 전건 부족 방향) / split_angle(스플릿 약 30° 좁음, 9건 전건 동일).
       실측에 없는 오류 자세를 창작하지 않는다. 수치 문자열은 프롬프트에 넣지
       않는다 — 그림에 숫자가 새는 것을 원천 차단.
  D-02 승인 레시피 재사용 — 260809 generate.py 의 PROMPT 골격(익명·의상·SCENE·
       ANATOMY·STYLE·프레이밍)을 importlib 로 바이트 무변경 로드 (L-4).
  D-03 화살표·수치·텍스트·빨간 표시 0 (ghost-noarrow 승인 문법, belle 08-18).
  D-04 대상 = ref-power-spin--leg 1종만.
  D-05 배선 금지 — 출력은 quick dir 안으로만.

exq generate_ghost3.py 구조 승계. 260818-nnm HOW_GUIDE["ghost-noarrow"] 원문에서
잔상 다리 서술 절만 오류 유형별로 치환하고, NO arrows/text/marker 절과
"같은 사람의 모션 트레일" 절은 공통 유지. 킵업 전용 절("one on each side of the
pole", "spread wide")은 파워스핀 수직 스플릿 기하(윗다리 폴 따라 위로 곧게,
아랫다리 아래로 곧게)로 고쳐 썼다. 도립이라 잔상 윗다리가 폴과 평행한 신규
위험 축에는 잔상-폴 분리 절을 추가했다.

실행:
    GEMINI_API_KEY=$(aws ssm get-parameter --name /sunity/motion/gemini-api-key \
        --with-decryption --profile sunity-motion --region ap-northeast-2 \
        --query 'Parameter.Value' --output text) \
    python3 generate_ghost_powerspin.py --out out/

키는 환경변수로만 — 파일·로그·stdout 어디에도 남기지 않는다 (T-gt1-03).
표준 라이브러리만 — 신규 패키지 0 (T-gt1-SC). 이미 존재하는 출력 파일은
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

# generate_how.py HOW_GUIDE["ghost-noarrow"] 골격 — {ghost_legs} 자리만 오류
# 유형별로 치환된다. 공통 유지 절(의도 불변):
#   - "The ghost is only the two legs; torso, arms, head and pole are drawn once, solid"
#   - "Draw NO arrows, NO angle marker, NO measurement line, NO number, NO text,
#      NO red mark of any kind" (D-03, 문자 그대로)
#   - "The ghost must read as a motion trail of the same person, never as a second person"
#   - 잔상 두 다리는 각각 별개 윤곽 ("clearly separate ... never merged into one")
# 파워스핀으로 고쳐 쓴 절:
#   - 분리 방향: "one on each side of the pole"(킵업) -> "one raised and one
#     lowered"(수직 스플릿)
#   - 실선 after: "straight and spread wide"(킵업) -> row promptPose 의 수직
#     스플릿 그대로
#   - 신규 위험 축 방어: 잔상 윗다리가 폴과 평행(도립) -> 잔상-폴 분리 절
_GHOST_TEMPLATE = (
    "Show HOW to get into this position, not just the position. Draw the SAME figure "
    "twice, superimposed in the SAME place: (1) a faint, very light, semi-transparent "
    "'before' ghost of the two legs {ghost_legs} - "
    "the two ghost legs must be clearly separate, one raised and one lowered, never "
    "merged into one, and each ghost leg must stay clearly distinct from the pole, "
    "never blending into the pole or doubling the pole line; and (2) the solid, fully "
    "drawn 'after' legs in the full vertical split - one leg extended straight up "
    "alongside the pole and the other extended straight down - exactly as in the FIRST "
    "image. The ghost is only the two legs; torso, arms, head and pole are drawn once, "
    "solid. Draw NO arrows, NO angle marker, NO measurement line, NO number, NO text, "
    "NO red mark of any kind - the body only. The ghost must read as a motion trail of "
    "the same person, never as a second person."
)

# 잔상 다리 서술 절 — Task 1 실측의 "전형 오류 자세"에서 영역 (D-01).
# 크기감은 정성 표현만, 수치 문자열 0 (그림에 숫자가 새는 것을 원천 차단).
_GHOST_LEGS = {
    # leg_extension: 무릎 굽음 — 실측 median 약 39° (10건 전건 부족 방향).
    # "clearly bent"(뚜렷이 굽음, 접힘 아님) = 39° 크기감의 정성 표현.
    "leg_extension": (
        "in the same raised-and-lowered arrangement as the solid legs but with both "
        "knees clearly bent, the shin of each ghost leg folding at the knee so that "
        "neither ghost leg is straight"
    ),
    # split_angle: 스플릿 좁음 — 실측 30° 부족 (9건 전건 동일, 앱 발화 문구
    # 기준 좁음 방향). "visibly less open ... shallow bend"(눈에 띄게 덜 벌어짐,
    # 반쯤 접힘 아님) = 30° 크기감의 정성 표현.
    "split_angle": (
        "in a visibly less open vertical split - the raised ghost leg stopping short "
        "of vertical, leaning off the pole, and the lowered ghost leg not yet pointing "
        "straight down, so the two ghost legs form a shallow bend instead of one "
        "straight vertical line"
    ),
}

# 유형별 완성 문단 — 값이 곧 최종 GUIDE 문단이다.
GHOST_TYPES = {
    err_type: _GHOST_TEMPLATE.format(ghost_legs=legs)
    for err_type, legs in _GHOST_LEGS.items()
}


def build_prompt_type(row: dict, err_type: str) -> str:
    """generate.py 의 PROMPT 골격에 GUIDE 만 교체 — 나머지 문단은 바이트 동일."""
    return G.PROMPT.format(
        pose=row["promptPose"],
        guide=GHOST_TYPES[err_type],
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
    ap.add_argument("--asset", default="ref-power-spin--leg")  # D-04: 확산은 belle 판정 후
    ap.add_argument("--n", type=int, default=2, help="오류 유형당 장수")
    ap.add_argument("--out", default=str(HERE / "out"))
    ap.add_argument(
        "--types",
        default="leg_extension,split_angle",  # 실측이 가른 2개 유형 (Task 1)
        help="쉼표 구분 오류 유형",
    )
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
    api_calls = 0
    for err_type in args.types.split(","):
        if err_type not in GHOST_TYPES:
            sys.exit(f"미등록 type: {err_type} (가능: {', '.join(GHOST_TYPES)})")
        prompt = build_prompt_type(row, err_type)
        (out_dir / f"prompt_{err_type}.txt").write_text(prompt)
        for i in range(1, args.n + 1):
            out = out_dir / f"{args.asset}__ghost-{err_type}-{i}.jpg"
            if out.exists():  # 부분 실패 재실행 시 기존 성공분은 건너뛴다
                print(f"[{err_type}-{i}] 이미 존재 — 건너뜀")
                continue
            print(f"[{err_type}-{i}] 생성 중…")
            parts = [{"text": prompt}, G.inline_part(frame), G.inline_part(anchor)]
            api_calls += 1
            if save_image(call(parts, key), out):
                print(f"  saved {out.name} ({out.stat().st_size} bytes)")
    print(f"API calls this run: {api_calls} (model={G.MODEL})")


if __name__ == "__main__":
    main()

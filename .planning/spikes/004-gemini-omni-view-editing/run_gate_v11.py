"""Spike 004 재게이트 — gemini-omni-1.1-flash 로 7월과 동일 프로토콜 재측정.

belle 2026-09-18: "omni 모델이 업데이트 되서 나왔고 지금 다시 시도해보려고 하는거야."

7월(`run_gate_batch.py`, gemini-omni-flash-preview)에서 굴곡각 MAE 중앙 22.8° 로
떨어졌다. 이 러너는 **같은 자**를 유지한다 — 입력·프롬프트·호출 shape 전부 7월과
동일하고, 바뀌는 것은 모델 문자열과 n 반복뿐이다. 새로 짜면 숫자가 비교 불가해진다.

7월 산출물(gate_out/)은 건드리지 않는다. 출력은 gate_out_v11/ 로 분리.

n 반복의 이유: belle 이 7월에 "클립당 n=1 이라 비결정성 배제 불가" 로 닫았다.
실측 단가가 $0.82/8초라 같은 예산으로 그 숙제를 없앨 수 있다.

★ 전송 = stdlib urllib (google-genai SDK 아님). 2026-09-18 실측: SDK 1.75.0 이
보내는 스키마를 서버가 "The legacy Interactions API schema is no longer supported.
Please upgrade your google-genai Python SDK to version >= 2" 로 400 거부했다.
SDK 를 올리면 backend/.venv 전체가 흔들리므로 REST 로 간다 — visual_gen.py 가
같은 이유(google-genai transitive ~100MB)로 이미 stdlib urllib 을 쓴다.

사용:
  python3 run_gate_v11.py --dry-run              # 호출 0, 계획만
  python3 run_gate_v11.py --clips power-spin     # 단계 A (스모크 1건)
  python3 run_gate_v11.py --reps 1               # 단계 B (10건 x n=1)
  python3 run_gate_v11.py --reps 3               # 단계 C (n=3 까지 채움)
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"
_HTTP_TIMEOUT_S = 900

HERE = Path(__file__).parent
GATE_IN = HERE / "gate_in"
GATE_OUT = HERE / "gate_out_v11"
JOURNAL = GATE_OUT / "journal_v11.json"

MODEL = "gemini-omni-1.1-flash"

# 카드 표시가 Video output $17.50 는 **100만 토큰 단가**다 (영상 1편 값이 아니다).
# 7월 실측 교차검증: 8.17s 출력 = 47,302 video-out 토큰 x $17.50/1M = $0.83
#                   journal 기록 cost_usd = 0.82  -> 일치
VIDEO_OUT_USD_PER_1M = 17.50

# 과금 DoS 방어 (T-31-19 동형). 상한을 넘으면 즉시 멈춘다.
MAX_CALLS = 40

# 회전이 실제로 일어났다고 볼 최소 픽셀차 (rotation_delta 참조).
# 7월 진짜 회전 38.7 / 오늘 1.1 원본통과 2.4 사이. 보수적으로 10 에 둔다.
ROTATION_MIN_DELTA = 10.0

# ★ 7월 러너의 PROMPT 상수 그대로 — 한 글자도 바꾸지 않는다.
PROMPT = (
    "Rotate the camera 90 degrees to view the performer from her left side. "
    "Keep the performer's pose, body positions, motion and timing exactly identical "
    "to the original video. Do not change the speed, the pole position, or the room. "
    "Only the camera viewpoint changes."
)

# 7월과 동일 10건 (회전5 / 역수직3 / spin2).
CLIPS = [
    "power-spin",          # spin  (7월 스모크 대상)
    "sideway-spin",        # spin
    "peter-pan",           # 회전
    "elbow-twist-sister",  # 회전
    "Chair-spin",          # 회전
    "Diamond-Spin",        # 회전
    "sliding-spin",        # 회전
    "invert",              # 역수직
    "kip-up",              # 역수직
    "straddle-invert",     # 역수직 (7월 2/2 영구 차단)
]


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_journal() -> dict:
    if JOURNAL.exists():
        return json.loads(JOURNAL.read_text())
    return {}


def save_journal(j: dict) -> None:
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    JOURNAL.write_text(json.dumps(j, ensure_ascii=False, indent=1))


def video_out_tokens(interaction) -> int:
    """usage 에서 video 출력 토큰만 뽑는다 — 과금은 modality 별이다."""
    usage = getattr(interaction, "usage", None)
    if usage is None:
        return 0
    raw = usage.model_dump() if hasattr(usage, "model_dump") else dict(usage)
    for inv in raw.get("model_invocation_token_counts") or []:
        for det in inv.get("candidates_tokens_details") or []:
            if det.get("modality", "").lower() == "video":
                return int(det.get("tokens") or 0)
    # 폴백: 총 출력 토큰 (텍스트 몇 토큰이 섞이나 오차는 무시 가능)
    return int(raw.get("total_output_tokens") or 0)


def is_moderation_block(err: Exception) -> bool:
    s = str(err).lower()
    return "prohibited" in s or "blocked" in s or "safety" in s or "moderation" in s


def _post(body: dict, key: str) -> dict:
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body).encode(),
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_S) as r:
        return json.loads(r.read())


def _output_video_uri(d: dict) -> str | None:
    for step in d.get("steps") or []:
        if step.get("type") != "model_output":
            continue
        for c in step.get("content") or []:
            if c.get("type") == "video" and c.get("uri"):
                return c["uri"]
    return None


def _video_out_tokens(d: dict) -> int:
    for m in (d.get("usage") or {}).get("output_tokens_by_modality") or []:
        if str(m.get("modality", "")).lower() == "video":
            return int(m.get("tokens") or 0)
    return int((d.get("usage") or {}).get("total_output_tokens") or 0)


def rotation_delta(src: Path, out: Path) -> float | None:
    """★ 앵글이 실제로 돌았는지 — 원본과의 평균 픽셀차 (0~255).

    2026-09-18 실측으로 드러난 7월 게이트의 맹점: 벤더가 **원본을 그대로
    재인코딩해 돌려주면** RTMW 재추론이 원본과 같은 관절을 뽑아 굴곡각 MAE 가
    0° 에 수렴한다. 즉 아무것도 안 한 출력이 자세 충실도 만점으로 "통과"한다.
    값어치는 0 인데 계기가 최고점을 준다.

    그래서 자세를 재기 **전에** 이 관문을 먼저 통과해야 한다. 앵글을 실제로
    돌리면 배경이 통째로 바뀌므로 큰 값이 나온다.

    실측 기준선 (power-spin 8초, 같은 시각 5프레임 평균):
      7월 gemini-omni-flash-preview  = 38.7  (진짜 회전)
      2026-09-18 gemini-omni-1.1-flash = 2.4  (원본 그대로 — 재인코딩 잡음 수준)
    """
    try:
        import imageio.v3 as iio
        import imageio_ffmpeg
        import numpy as np
    except ImportError:
        return None

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    tmp = GATE_OUT / "_rotcheck"
    tmp.mkdir(parents=True, exist_ok=True)
    diffs = []
    for t in ("0.5", "2.0", "4.0", "6.0", "7.5"):
        frames = []
        for tag, path in (("a", src), ("b", out)):
            fp = tmp / f"{tag}.png"
            subprocess.run(
                [ff, "-y", "-loglevel", "error", "-ss", t, "-i", str(path),
                 "-frames:v", "1", "-vf", "scale=-1:420", str(fp)],
                check=False, capture_output=True,
            )
            if not fp.exists():
                break
            frames.append(iio.imread(fp).astype("float32")[..., :3])
        if len(frames) != 2:
            continue
        a, b = frames
        h = min(a.shape[0], b.shape[0]); w = min(a.shape[1], b.shape[1])
        diffs.append(float(np.abs(a[:h, :w] - b[:h, :w]).mean()))
    return round(sum(diffs) / len(diffs), 2) if diffs else None


def run_one(key_api: str, name: str, rep: int, journal: dict, b64cache: dict) -> bool:
    """클립 1회분 생성. True = 이번 호출에서 과금이 발생했다."""
    key = f"{name}__r{rep}"
    entry = journal.get(key, {})
    out_path = GATE_OUT / f"{key}.mp4"

    if entry.get("status") == "done" and out_path.exists():
        log(f"{key}: skip (done)")
        return False
    if entry.get("status") == "blocked_permanent":
        log(f"{key}: skip (모더레이션 영구 차단)")
        return False

    src = GATE_IN / f"{name}.mp4"
    if not src.exists():
        journal[key] = {"status": "error", "error": f"입력 없음: {src}"}
        save_journal(journal)
        log(f"{key}: ERROR 입력 없음")
        return False

    t0 = time.time()
    billed = False
    try:
        if name not in b64cache:
            b64cache[name] = base64.b64encode(src.read_bytes()).decode()
        log(f"{key}: generate ...")
        billed = True
        d = _post(
            {
                "model": MODEL,
                "input": [
                    {"type": "video", "mime_type": "video/mp4", "data": b64cache[name]},
                    {"type": "text", "text": PROMPT},
                ],
                "response_format": {"type": "video", "delivery": "uri", "aspect_ratio": "9:16"},
            },
            key_api,
        )
        journal[key] = {"status": "created", "interaction_id": d.get("id")}
        save_journal(journal)

        uri = _output_video_uri(d)
        if not uri:
            raise RuntimeError(f"출력에 video 없음 — status={d.get('status')}")
        GATE_OUT.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(uri, headers={"x-goog-api-key": key_api})
        with urllib.request.urlopen(req, timeout=300) as r:
            out_path.write_bytes(r.read())

        tok = _video_out_tokens(d)
        delta = rotation_delta(src, out_path)
        journal[key] = {
            "status": "done",
            "model": MODEL,
            "interaction_id": d.get("id"),
            "elapsed_s": round(time.time() - t0, 1),
            "out_mb": round(out_path.stat().st_size / 1e6, 2),
            "video_out_tokens": tok,
            "cost_usd": round(tok * VIDEO_OUT_USD_PER_1M / 1e6, 3),
            "rotation_delta": delta,
            "rotated": None if delta is None else bool(delta >= ROTATION_MIN_DELTA),
        }
        save_journal(journal)
        e = journal[key]
        log(f"{key}: done {e['out_mb']}MB {e['elapsed_s']}s ${e['cost_usd']}  회전델타={delta} rotated={e['rotated']}")
    except urllib.error.HTTPError as he:
        msg = he.read().decode()[:300]
        prior = journal.get(key, {})
        blocked = is_moderation_block(Exception(msg))
        status = "blocked_permanent" if (blocked and prior.get("status") == "blocked") else (
            "blocked" if blocked else "error")
        journal[key] = {**prior, "status": status, "error": f"HTTP {he.code} {msg}"}
        save_journal(journal)
        log(f"{key}: {status.upper()} HTTP {he.code} {msg[:140]}")
    except Exception as e:  # noqa: BLE001 - 배치는 항목 단위 실패 기록 후 계속
        prior = journal.get(key, {})
        blocked = is_moderation_block(e)
        status = "blocked_permanent" if (blocked and prior.get("status") == "blocked") else (
            "blocked" if blocked else "error")
        journal[key] = {**prior, "status": status, "error": str(e)[:300]}
        save_journal(journal)
        log(f"{key}: {status.upper()} {str(e)[:160]}")
    return billed


def summarize(journal: dict) -> None:
    done = [k for k, v in journal.items() if v.get("status") == "done"]
    blocked = [k for k, v in journal.items() if str(v.get("status", "")).startswith("blocked")]
    err = [k for k, v in journal.items() if v.get("status") == "error"]
    spent = sum(v.get("cost_usd", 0) for v in journal.values())
    rotated = [k for k in done if journal[k].get("rotated") is True]
    passthru = [k for k in done if journal[k].get("rotated") is False]
    log(f"done={len(done)} blocked={len(blocked)} error={len(err)}  누적 ${spent:.2f}")
    log(f"  회전 관문: 실제회전 {len(rotated)} / 원본통과 {len(passthru)}")
    if passthru:
        log(f"  ★ 원본통과(자세 측정 무의미): {sorted(passthru)}")
    if blocked:
        log(f"  차단: {sorted(blocked)}")
    if err:
        log(f"  오류: {sorted(err)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=1, help="클립당 반복 횟수 (n)")
    ap.add_argument("--clips", nargs="*", default=None, help="특정 클립만 (기본 10건 전부)")
    ap.add_argument("--dry-run", action="store_true", help="호출 0 — 계획만 출력")
    args = ap.parse_args()

    clips = args.clips if args.clips else CLIPS
    unknown = [c for c in clips if c not in CLIPS]
    if unknown:
        raise SystemExit(f"알 수 없는 클립: {unknown}\n유효: {CLIPS}")

    journal = load_journal()
    planned = [
        f"{c}__r{r}"
        for c in clips
        for r in range(1, args.reps + 1)
        if journal.get(f"{c}__r{r}", {}).get("status") not in ("done", "blocked_permanent")
    ]

    log(f"model={MODEL}  clips={len(clips)}  reps={args.reps}")
    log(f"신규 호출 예정 {len(planned)}건  예상 ~${len(planned) * 0.82:.2f}")
    if args.dry_run:
        for p in planned:
            print(f"  would call: {p}")
        summarize(journal)
        return

    if len(planned) > MAX_CALLS:
        raise SystemExit(f"호출 {len(planned)}건 > MAX_CALLS={MAX_CALLS} — 과금 상한 초과. 범위를 좁혀라.")

    key_api = os.environ.get("GEMINI_API_KEY", "")
    if not key_api:
        raise SystemExit("GEMINI_API_KEY 미설정. SSM: aws ssm get-parameter --name /sunity/motion/gemini-api-key --with-decryption --profile sunity-motion")
    b64cache: dict[str, str] = {}
    calls = 0
    for rep in range(1, args.reps + 1):
        for name in clips:
            if calls >= MAX_CALLS:
                log(f"MAX_CALLS={MAX_CALLS} 도달 — 중단")
                summarize(journal)
                return
            if run_one(key_api, name, rep, journal, b64cache):
                calls += 1

    summarize(journal)


if __name__ == "__main__":
    main()

"""Spike 004 재게이트 — gemini-omni-1.1-flash 로 7월과 동일 프로토콜 재측정.

belle 2026-09-18: "omni 모델이 업데이트 되서 나왔고 지금 다시 시도해보려고 하는거야."

7월(`run_gate_batch.py`, gemini-omni-flash-preview)에서 굴곡각 MAE 중앙 22.8° 로
떨어졌다. 이 러너는 **같은 자**를 유지한다 — 입력·프롬프트·호출 shape 전부 7월과
동일하고, 바뀌는 것은 모델 문자열과 n 반복뿐이다. 새로 짜면 숫자가 비교 불가해진다.

7월 산출물(gate_out/)은 건드리지 않는다. 출력은 gate_out_v11/ 로 분리.

n 반복의 이유: belle 이 7월에 "클립당 n=1 이라 비결정성 배제 불가" 로 닫았다.
실측 단가가 $0.82/8초라 같은 예산으로 그 숙제를 없앨 수 있다.

사용:
  python3 run_gate_v11.py --dry-run              # 호출 0, 계획만
  python3 run_gate_v11.py --clips power-spin     # 단계 A (스모크 1건)
  python3 run_gate_v11.py --reps 1               # 단계 B (10건 x n=1)
  python3 run_gate_v11.py --reps 3               # 단계 C (n=3 까지 채움)
"""
from __future__ import annotations

import argparse
import json
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

from google import genai  # noqa: E402

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


def run_one(client, name: str, rep: int, journal: dict, uploaded: dict) -> bool:
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
        # 크래시 후 재개: interaction id 가 있으면 재과금 없이 회수 (7월 실증).
        interaction = None
        if entry.get("interaction_id"):
            try:
                interaction = client.interactions.get(entry["interaction_id"])
                log(f"{key}: 기존 interaction 회수 status={interaction.status}")
            except Exception:
                interaction = None

        if interaction is None:
            # 업로드는 클립당 1회만 — 반복 호출에서 재사용한다.
            if name not in uploaded:
                log(f"{key}: upload {src.stat().st_size / 1e6:.1f}MB")
                vf = client.files.upload(file=str(src))
                while getattr(vf.state, "name", str(vf.state)) == "PROCESSING":
                    time.sleep(5)
                    vf = client.files.get(name=vf.name)
                if getattr(vf.state, "name", str(vf.state)) == "FAILED":
                    raise RuntimeError("file upload FAILED")
                uploaded[name] = vf.uri
            log(f"{key}: generate ...")
            billed = True
            interaction = client.interactions.create(
                model=MODEL,
                input=[
                    {"type": "document", "uri": uploaded[name]},
                    {"type": "text", "text": PROMPT},
                ],
                response_format={"type": "video", "delivery": "uri", "aspect_ratio": "9:16"},
            )
            journal[key] = {"status": "created", "interaction_id": interaction.id}
            save_journal(journal)

        waited = 0
        while str(getattr(interaction, "status", "")) not in ("completed", "InteractionStatus.COMPLETED"):
            if waited > 600:
                raise TimeoutError(f"generation timeout status={interaction.status}")
            time.sleep(10)
            waited += 10
            interaction = client.interactions.get(interaction.id)

        ov = interaction.output_video
        if ov is None:
            raise RuntimeError("output_video is None")
        GATE_OUT.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(client.files.download(file=ov.uri))

        tok = video_out_tokens(interaction)
        journal[key] = {
            "status": "done",
            "model": MODEL,
            "interaction_id": interaction.id,
            "elapsed_s": round(time.time() - t0, 1),
            "out_mb": round(out_path.stat().st_size / 1e6, 2),
            "video_out_tokens": tok,
            "cost_usd": round(tok * VIDEO_OUT_USD_PER_1M / 1e6, 3),
        }
        save_journal(journal)
        log(f"{key}: done {journal[key]['out_mb']}MB  {journal[key]['elapsed_s']}s  ${journal[key]['cost_usd']}")
    except Exception as e:  # noqa: BLE001 - 배치는 항목 단위 실패 기록 후 계속
        prior = journal.get(key, {})
        blocked = is_moderation_block(e)
        # 7월 실측: 차단은 확률적이라 1회 재시도로 통과하기도 한다. 2연속이면 영구.
        status = "blocked_permanent" if (blocked and prior.get("status") == "blocked") else (
            "blocked" if blocked else "error"
        )
        journal[key] = {**prior, "status": status, "error": str(e)[:300]}
        save_journal(journal)
        log(f"{key}: {status.upper()} {str(e)[:160]}")
    return billed


def summarize(journal: dict) -> None:
    done = [k for k, v in journal.items() if v.get("status") == "done"]
    blocked = [k for k, v in journal.items() if str(v.get("status", "")).startswith("blocked")]
    err = [k for k, v in journal.items() if v.get("status") == "error"]
    spent = sum(v.get("cost_usd", 0) for v in journal.values())
    log(f"done={len(done)} blocked={len(blocked)} error={len(err)}  누적 ${spent:.2f}")
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

    client = genai.Client()
    uploaded: dict[str, str] = {}
    calls = 0
    for rep in range(1, args.reps + 1):
        for name in clips:
            if calls >= MAX_CALLS:
                log(f"MAX_CALLS={MAX_CALLS} 도달 — 중단")
                summarize(journal)
                return
            if run_one(client, name, rep, journal, uploaded):
                calls += 1

    summarize(journal)


if __name__ == "__main__":
    main()

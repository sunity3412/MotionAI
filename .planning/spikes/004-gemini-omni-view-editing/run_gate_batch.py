"""Spike 004-iii-b — Omni 10건 pose-consistency 게이트: 생성 배치.

gate_in/*.mp4 (8초 트림, 10건) → gemini-omni-flash-preview 앵글 회전 → gate_out/<name>.mp4
journal(gate_out/journal.json) 로 멱등 재개 — 이미 done 인 항목 스킵, interaction id 기록으로
크래시 시 재과금 없이 회수 (interactions.get).

power-spin 은 스모크 출력 재사용 (배치에서 스킵, 복사로 처리).
비용: 9건 × ~$0.82 ≈ $7.4 (belle 승인 2026-07-17).
"""
from __future__ import annotations

import json
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

from google import genai  # noqa: E402

HERE = Path(__file__).parent
GATE_IN = HERE / "gate_in"
GATE_OUT = HERE / "gate_out"
JOURNAL = GATE_OUT / "journal.json"

PROMPT = (
    "Rotate the camera 90 degrees to view the performer from her left side. "
    "Keep the performer's pose, body positions, motion and timing exactly identical "
    "to the original video. Do not change the speed, the pole position, or the room. "
    "Only the camera viewpoint changes."
)

CLIPS = [
    "sideway-spin",       # spin
    "peter-pan",          # 회전
    "elbow-twist-sister", # 회전
    "Chair-spin",         # 회전
    "Diamond-Spin",       # 회전
    "sliding-spin",       # 회전
    "invert",             # 역수직
    "kip-up",             # 역수직
    "straddle-invert",    # 역수직
]


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_journal() -> dict:
    if JOURNAL.exists():
        return json.loads(JOURNAL.read_text())
    return {}


def save_journal(j: dict) -> None:
    JOURNAL.write_text(json.dumps(j, ensure_ascii=False, indent=1))


def main() -> None:
    GATE_OUT.mkdir(exist_ok=True)
    client = genai.Client()
    journal = load_journal()

    # power-spin: 스모크 출력 재사용
    smoke = HERE / "smoke_out" / "power_spin_side_view.mp4"
    ps_out = GATE_OUT / "power-spin.mp4"
    if smoke.exists() and not ps_out.exists():
        ps_out.write_bytes(smoke.read_bytes())
        journal["power-spin"] = {"status": "done", "source": "smoke_reuse", "cost_usd": 0.82}
        save_journal(journal)
        log("power-spin: smoke 출력 재사용")

    for name in CLIPS:
        entry = journal.get(name, {})
        out_path = GATE_OUT / f"{name}.mp4"
        if entry.get("status") == "done" and out_path.exists():
            log(f"{name}: skip (done)")
            continue

        src = GATE_IN / f"{name}.mp4"
        t0 = time.time()
        try:
            # 크래시 후 재개: interaction id 있으면 재과금 없이 회수 시도
            interaction = None
            if entry.get("interaction_id"):
                try:
                    interaction = client.interactions.get(entry["interaction_id"])
                    log(f"{name}: 기존 interaction 회수 status={interaction.status}")
                except Exception:
                    interaction = None

            if interaction is None or str(interaction.status) not in ("completed", "InteractionStatus.COMPLETED"):
                if interaction is None:
                    log(f"{name}: upload {src.stat().st_size/1e6:.1f}MB")
                    vf = client.files.upload(file=str(src))
                    while getattr(vf.state, "name", str(vf.state)) == "PROCESSING":
                        time.sleep(5)
                        vf = client.files.get(name=vf.name)
                    if getattr(vf.state, "name", str(vf.state)) == "FAILED":
                        raise RuntimeError("file upload FAILED")
                    log(f"{name}: generate ...")
                    interaction = client.interactions.create(
                        model="gemini-omni-flash-preview",
                        input=[
                            {"type": "document", "uri": vf.uri},
                            {"type": "text", "text": PROMPT},
                        ],
                        response_format={"type": "video", "delivery": "uri", "aspect_ratio": "9:16"},
                    )
                journal[name] = {"status": "created", "interaction_id": interaction.id}
                save_journal(journal)
                # completed 대기
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
            video_bytes = client.files.download(file=ov.uri)
            out_path.write_bytes(video_bytes)
            elapsed = time.time() - t0
            journal[name] = {
                "status": "done",
                "interaction_id": interaction.id,
                "elapsed_s": round(elapsed, 1),
                "out_mb": round(out_path.stat().st_size / 1e6, 2),
            }
            save_journal(journal)
            log(f"{name}: done {out_path.stat().st_size/1e6:.1f}MB elapsed={elapsed:.0f}s")
        except Exception as e:  # noqa: BLE001 - 배치는 항목 단위 실패 기록 후 계속
            journal[name] = {**journal.get(name, {}), "status": "error", "error": str(e)[:300]}
            save_journal(journal)
            log(f"{name}: ERROR {e}")

    done = [k for k, v in journal.items() if v.get("status") == "done"]
    log(f"batch finished: {len(done)}/10 done -> {sorted(done)}")


if __name__ == "__main__":
    main()

"""반려 10장 입력 프레임 재확보 (quick-260816-ill2 Task 2).

08-16 게이트 반려 10장이 참조하던 inputFrame 은 전부 지난 세션
scratchpad(session 6d09763a-...)에 있었는데 그 디렉터리 자체가 통째로 사라졌다
(scratchpad = 휘발, memory feedback-scratchpad-volatile-never-claim-preserved).
재현 정보는 targets.json 의 sourceVideo/t/cropBox 뿐이라, 그 값 그대로 소스 영상
에서 프레임을 재추출한다 — 지어낸 값 0(PLAN §Context 표 그대로).

S3 read-only 다운로드는 discover_sweep.py::_s3_client() 를 재사용한다(다운로드
로직 신규 작성 0). 데이터는 동작명 리터럴 분기 없이 딕셔너리 3개(RAW_FRAMES/
OUTPUTS/TARGET_MAP)만 순회한다.

PII 취급: 추출되는 프레임은 기준 선수 실사 인물 사진이다(익명화된 일러스트가
아니다). 리포 git 이력에 절대 올리지 않는다 — 기본 --cache-root 는 이 스크립트
기준 상대 .cache/(로컬 디스크에만 존재, .gitignore 로 git 추적 제외) 이지만,
실사용은 /Users/Shared/ 하위처럼 git 저장소 완전히 밖인 경로를 --cache-root 로
명시 지정해 스크래치패드보다 내구성 있게 보존한다(memory
home-dir-is-git-repo-pii-hazard, verification_notes "레포 또는 /Users/Shared").

실행 예:
    python3 extract_inputs.py --cache-root /Users/Shared/sunity-motion-260816-ill2-cache
    python3 extract_inputs.py --cache-root ... --window ref-pdshape --center 5.0 --span 1.5 --step 0.5
    python3 extract_inputs.py --cache-root ... --apply-targets
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / ".planning/quick/260814-ehz-5"))
import discover_sweep as ds  # noqa: E402 - sys.path 삽입 후 임포트

BUCKET = getattr(ds, "BUCKET", "sunity-motion-pilot-videos")
TARGETS_JSON = REPO / ".planning/quick/260809-ill-missing-illustrations/targets.json"

# RAW_FRAMES: motionId -> (S3 키, t초). PLAN §Context 표 그대로 — 지어낸 값 0.
RAW_FRAMES: dict[str, tuple[str, float]] = {
    "ref-combo": ("reference/ref-combo.mp4", 33.0),
    "ref-peter-pan": ("reference/ref-peter-pan.mp4", 2.4),
    "ref-pdshape": ("reference/ref-pdshape.mp4", 5.0),
    "ref-kip-up": ("reference/ref-kip-up.mp4", 3.75),
    "ref-power-spin": ("reference/ref-power-spin.mp4", 8.5),
    "ref-elbow-twist-sister": ("reference/ref-elbow-twist-sister.mp4", 13.0),
}

# OUTPUTS: 산출 파일 스텀 -> (RAW_FRAMES 키, cropBox 또는 None).
OUTPUTS: dict[str, tuple[str, list[int] | None]] = {
    "combo_leg": ("ref-combo", [180, 620, 740, 1320]),
    "peterpan_leg": ("ref-peter-pan", [300, 700, 820, 1340]),
    "peterpan_full": ("ref-peter-pan", None),
    "pdshape_leg": ("ref-pdshape", [360, 400, 780, 920]),
    "pdshape_full": ("ref-pdshape", None),
    "kipup_full": ("ref-kip-up", None),
    "powerspin_full": ("ref-power-spin", None),
    "elbowtwist_shoulder_full": ("ref-elbow-twist-sister", None),
}

# TARGET_MAP: (motionId, part) -> OUTPUTS 스텀.
TARGET_MAP: dict[tuple[str, str], str] = {
    ("ref-combo", "leg"): "combo_leg",
    ("ref-peter-pan", "leg"): "peterpan_leg",
    ("ref-peter-pan", "arm"): "peterpan_full",
    ("ref-peter-pan", "shoulder"): "peterpan_full",
    ("ref-pdshape", "leg"): "pdshape_leg",
    ("ref-pdshape", "arm"): "pdshape_full",
    ("ref-kip-up", "leg"): "kipup_full",
    ("ref-kip-up", "shoulder"): "kipup_full",
    ("ref-power-spin", "leg"): "powerspin_full",
    ("ref-elbow-twist-sister", "shoulder"): "elbowtwist_shoulder_full",
}

# 창 재추출 clamp 범위(§Context) — pdshape/peter-pan 1차 후보가 눈으로 안 맞을 때만 사용.
_WINDOW_CLAMP: dict[str, tuple[float, float]] = {
    "ref-pdshape": (3.5, 11.5),
    "ref-peter-pan": (2.0, 6.0),
}

_CACHE_ROOT: Path | None = None


def _cache_root() -> Path:
    assert _CACHE_ROOT is not None, "--cache-root 미설정"
    _CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    return _CACHE_ROOT


def _videos_dir() -> Path:
    d = _cache_root() / "ill2" / "videos"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _crop_dir() -> Path:
    d = _cache_root() / "ill2" / "crop"
    d.mkdir(parents=True, exist_ok=True)
    return d


def download_video(motion_id: str, s3_key: str) -> Path:
    out = _videos_dir() / f"{motion_id}.mp4"
    if out.exists():
        print(f"[{motion_id}] cached {out} ({out.stat().st_size}B)")
        return out
    s3 = ds._s3_client()
    s3.download_file(BUCKET, s3_key, str(out))
    print(f"[{motion_id}] downloaded {s3_key} -> {out} ({out.stat().st_size}B)")
    return out


def extract_frame(video_path: Path, t: float, crop_box: list[int] | None,
                   out_path: Path, *, tag: str) -> Path:
    """원본 해상도 단일 프레임 추출 — 9fps 솎음 파이프라인(frame_extractor.py)의
    effective_fps 트랩과 무관하다. 이 추출은 원본 영상을 그대로 열어 단일 순간을
    집는 것이라 디시메이션 로직을 재사용하지 않는다(quick-260816-ill2)."""
    import imageio
    from PIL import Image

    reader = imageio.get_reader(str(video_path))
    try:
        fps = float(reader.get_meta_data()["fps"])
        frame_idx = round(t * fps)
        data = reader.get_data(frame_idx)
    finally:
        reader.close()
    img = Image.fromarray(data)
    if crop_box:
        img = img.crop(tuple(crop_box))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, quality=92)
    print(f"[{tag}] t={t}s frame_idx={frame_idx} fps={fps:.2f} size={img.size} -> {out_path}")
    return out_path


def run_outputs(stems: list[str] | None = None) -> dict[str, Path]:
    stems = stems or list(OUTPUTS.keys())
    needed_motions = sorted({OUTPUTS[s][0] for s in stems})
    video_paths: dict[str, Path] = {}
    for motion_id in needed_motions:
        s3_key, _t = RAW_FRAMES[motion_id]
        video_paths[motion_id] = download_video(motion_id, s3_key)
    results: dict[str, Path] = {}
    for stem in stems:
        motion_id, crop_box = OUTPUTS[stem]
        _s3_key, t = RAW_FRAMES[motion_id]
        out = _crop_dir() / f"{stem}.jpg"
        results[stem] = extract_frame(video_paths[motion_id], t, crop_box, out, tag=stem)
    return results


def window_extract(motion_id: str, center: float, span: float, step: float) -> list[Path]:
    """창 안 후보 재추출 — pdshape/peter-pan 1차 후보가 promptPose 와 안 맞을 때만
    (frames-before-numbers gate — 반드시 Read 로 눈으로 확인 후 재선정)."""
    s3_key, _t = RAW_FRAMES[motion_id]
    video_path = download_video(motion_id, s3_key)
    lo, hi = _WINDOW_CLAMP.get(motion_id, (0.0, float("inf")))
    n_steps = max(1, int(round(span / step)))
    seen: set[float] = set()
    outs: list[Path] = []
    for i in range(-n_steps, n_steps + 1):
        t = round(center + i * step, 3)
        t = max(lo, min(hi, t))
        if t < 0 or t in seen:
            continue
        seen.add(t)
        out = _crop_dir() / f"{motion_id}_window_t{t}.jpg"
        outs.append(extract_frame(video_path, t, None, out, tag=f"{motion_id}@{t}s"))
    return outs


# ── targets.json 반영 (Read 로 눈 확인 후 최종 t/사유가 정해진 다음 --apply-targets
#    로 호출) — 값은 PLAN §Context 표를 그대로 옮긴다, 지어낸 값 0.
_CROPNOTE_PDSHAPE_ARM = (
    "quick-260816-ill2 — 08-16 게이트 fail(② 몸통·머리 노출): promptPose 가 이미 "
    "'어깨는 프레임 가장자리, 나머지 몸은 프레임 밖'을 지시하는데 generate.py 의 "
    "FRAMING 고정문(fill the frame)이 모순돼 매 생성마다 전신이 그려졌다. 별도 "
    "pixel cropBox 는 없음 — 부분 프레이밍은 이제 FRAMING_PARTIAL 문장으로 전달."
)
_CROPNOTE_PETERPAN_ARM = (
    "quick-260816-ill2 — 08-16 게이트 fail(② 몸통·머리 노출): promptPose 가 이미 "
    "'한 팔만 프레임에, 다른 사지 없음'을 지시하는데 generate.py 의 FRAMING 고정문"
    "(fill the frame)이 모순돼 매 생성마다 전신이 그려졌다. 별도 pixel cropBox 는 "
    "없음 — 부분 프레이밍은 이제 FRAMING_PARTIAL 문장으로 전달."
)
_ORIENTATION_ELBOWTWIST_SHOULDER = (
    "도립(등 뒤에서 본 두 견갑 — elbow-twist-sister--arm 과 동일 순간 t=13.0 재사용, "
    "clipRange.execPeakS=13/checkpoints 양쪽 어깨 weight 0.15 로 grounding, "
    "quick-260816-ill2)"
)

# (motionId, part) -> (최종 t, note10, cropNote 또는 None, orientation 또는 None)
FINAL_ROWS: dict[tuple[str, str], dict] = {
    ("ref-combo", "leg"): {
        "t": 33.0,
        "note10": ("quick-260816-ill2 — inputFrame 소실로 소스 영상에서 t=33.0 "
                   "(기존 기록 그대로) 재추출·재확인. cropBox/t 변경 없음."),
    },
    ("ref-peter-pan", "leg"): {
        "t": 2.4,
        "note10": ("quick-260816-ill2 — inputFrame 소실로 소스 영상에서 t=2.4 "
                   "(기존 기록 그대로) 재추출·재확인. cropBox/t 변경 없음."),
    },
    ("ref-pdshape", "leg"): {
        "t": 5.0,
        "note10": ("quick-260816-ill2 — inputFrame 소실로 소스 영상에서 t=5.0 "
                   "(기존 기록 그대로) 재추출·재확인. cropBox/t 변경 없음."),
    },
    ("ref-kip-up", "leg"): {
        "t": 3.75,
        "sourceVideo": "s3://sunity-motion-pilot-videos/reference/ref-kip-up.mp4",
        "note10": ("quick-260816-ill2 — inputFrame 소실. t=3.75 는 기존 기록 그대로, "
                   "sourceVideo 는 4건 기존 기록과 동일한 reference/{motionId}.mp4 "
                   "패턴으로 파생(예외 0)."),
    },
    ("ref-kip-up", "shoulder"): {
        "t": 3.75,
        "sourceVideo": "s3://sunity-motion-pilot-videos/reference/ref-kip-up.mp4",
        "note10": ("quick-260816-ill2 — inputFrame 소실. leg 항목과 동일 t=3.75 "
                   "프레임 재사용(크롭도 없음 — 완전히 같은 소스 프레임)."),
    },
    ("ref-power-spin", "leg"): {
        "t": 8.5,
        "sourceVideo": "s3://sunity-motion-pilot-videos/reference/ref-power-spin.mp4",
        "note10": ("quick-260816-ill2 — inputFrame 소실. t=8.5 는 기존 기록 그대로, "
                   "sourceVideo 는 패턴 파생(reference/{motionId}.mp4)."),
    },
    ("ref-elbow-twist-sister", "shoulder"): {
        "t": 13.0,
        "sourceVideo": "s3://sunity-motion-pilot-videos/reference/ref-elbow-twist-sister.mp4",
        "orientation": _ORIENTATION_ELBOWTWIST_SHOULDER,
        "note10": ("quick-260816-ill2 — inputFrame 소실. ref-elbow-twist-sister--arm "
                   "(오늘 게이트 pass)이 쓰는 바로 그 t=13.0 재사용 — "
                   "clipRange.execPeakS=13, checkpoints 양쪽 어깨 weight 0.15 로 "
                   "grounding. Read 로 elbowtwist_shoulder_full.jpg 확인: 도립으로 "
                   "매달려 한 팔이 몸 뒤로 폴을 훅 잡은 자세가 뚜렷함(08-16 반려 사유 "
                   "'직립으로 서 있음'과 정반대 — 도립 원인 해소 근거). 변경 없이 "
                   "확정, 이 행에만 orientation 신설(자세 실패 중 방위 축)."),
    },
    ("ref-pdshape", "arm"): {
        "t": 5.0,
        "sourceVideo": "s3://sunity-motion-pilot-videos/reference/ref-pdshape.mp4",
        "cropNote": _CROPNOTE_PDSHAPE_ARM,
        "note10": ("quick-260816-ill2 — inputFrame 소실. 같은 동작 같은 hold 인 "
                   "ref-pdshape--leg 와 동일 순간 t=5.0 재사용(1차 후보). Read 로 "
                   "pdshape_full.jpg 확인: 도립 비대칭 클로즈드 셰이프, 한 손이 폴을 "
                   "팔꿈치 굽혀 허리께에서 붙잡은 모습이 선명해 변경 없이 확정."),
    },
    ("ref-peter-pan", "arm"): {
        "t": 2.4,
        "sourceVideo": "s3://sunity-motion-pilot-videos/reference/ref-peter-pan.mp4",
        "cropNote": _CROPNOTE_PETERPAN_ARM,
        "note10": ("quick-260816-ill2 — inputFrame 소실. ref-peter-pan--leg 와 동일 "
                   "순간 t=2.4 재사용(1차 후보). Read 로 peterpan_full.jpg 확인: "
                   "등 뒤 시점, 한 팔이 천장 쪽 폴을 곧게 뻗어 붙잡은 모습이 선명해 "
                   "변경 없이 확정."),
    },
    ("ref-peter-pan", "shoulder"): {
        "t": 2.4,
        "sourceVideo": "s3://sunity-motion-pilot-videos/reference/ref-peter-pan.mp4",
        "note10": ("quick-260816-ill2 — inputFrame 소실. ref-peter-pan--leg 와 동일 "
                   "순간 t=2.4 재사용(1차 후보). Read 로 peterpan_full.jpg 확인: 등 뒤 "
                   "시점의 어깨·견갑 + 스택(stag) 다리 모양이 함께 보여 변경 없이 "
                   "확정. 자세 실패 원인이 행잉 vs 직립이지 프레이밍이 아니므로 "
                   "cropNote 신설 없음."),
    },
}


def update_targets_json(results: dict[str, Path], *,
                         overrides: dict[tuple[str, str], Path] | None = None) -> None:
    """반려 10장의 inputFrame/sourceVideo/t/note10(+cropNote/orientation 신설분)을
    targets.json 에 반영한다. overrides 는 window_extract 재선정으로 1차 후보가
    바뀐 (motionId, part) -> 최종 파일 경로."""
    overrides = overrides or {}
    data = json.loads(TARGETS_JSON.read_text(encoding="utf-8"))
    rows = data["targets"] if isinstance(data, dict) else data
    by_key = {(r["motionId"], r["part"]): r for r in rows}
    touched = []
    for key, spec in FINAL_ROWS.items():
        row = by_key.get(key)
        if row is None:
            raise SystemExit(f"targets.json 에 행 없음: {key}")
        stem = TARGET_MAP[key]
        chosen = overrides.get(key, results.get(stem))
        if chosen is None:
            raise SystemExit(f"{key} 산출 프레임 없음(run_outputs 먼저 실행)")
        row["inputFrame"] = str(chosen.resolve())
        row["sourceVideo"] = spec.get(
            "sourceVideo",
            row.get("sourceVideo") or f"s3://sunity-motion-pilot-videos/reference/{key[0]}.mp4",
        )
        row["t"] = spec["t"]
        row["note10"] = spec["note10"]
        if "cropNote" in spec:
            row["cropNote"] = spec["cropNote"]
        if "orientation" in spec:
            row["orientation"] = spec["orientation"]
        touched.append(key)
    TARGETS_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"targets.json 갱신 완료: {len(touched)}행 — {touched}")


def main() -> None:
    global _CACHE_ROOT
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-root", default=str(HERE / ".cache"),
                     help="입력 프레임 캐시 루트(기본=스크립트 상대 .cache, "
                          "git 추적 제외). PII/휘발성 고려 시 /Users/Shared/... 등 "
                          "레포 밖 경로를 명시 권장(이전 세션 UUID 하드코딩 금지).")
    ap.add_argument("--window", default=None, help="motionId — 창 재추출 대상")
    ap.add_argument("--center", type=float, default=None)
    ap.add_argument("--span", type=float, default=None)
    ap.add_argument("--step", type=float, default=None)
    ap.add_argument("--apply-targets", action="store_true",
                     help="targets.json 의 반려 10장 inputFrame/sourceVideo/t/note10 갱신")
    args = ap.parse_args()

    _CACHE_ROOT = Path(args.cache_root)
    _CACHE_ROOT.mkdir(parents=True, exist_ok=True)

    if args.window:
        if args.center is None or args.span is None or args.step is None:
            sys.exit("--window 사용 시 --center/--span/--step 전부 필요")
        for p in window_extract(args.window, args.center, args.span, args.step):
            print(p)
        return

    results = run_outputs()
    if args.apply_targets:
        update_targets_json(results)


if __name__ == "__main__":
    main()

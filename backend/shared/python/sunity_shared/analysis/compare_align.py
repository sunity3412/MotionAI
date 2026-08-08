"""Phase 35 — 합성 비교 영상 정렬 라이브러리: 재추출 + 자세거리 DTW + 짝 재선정.

기원: backend/scripts/p35_extract_align.py 의 **순수 이동** (quick-260808-jix).
belle 반려(08-07 "재생 중 딴 동작 · 마커 전부 엉뚱 · 짝 장면 불신")의 뿌리 수리 —
렌더의 세 입력을 낡은 doc 리포트 대신 여기서 전부 재생성한다:

  1. 재추출 — user·ref 영상을 rtmlib RTMW(GPU)로 15fps 재추출. 좌표는 **픽셀 →
     x/W·y/H 정규화를 이 모듈이 직접** 수행(해석 모호성 0).
  2. 정렬 — 프레임별 정규화 자세(힙 중심·몸통 스케일)를 특징으로 한 자세거리 DTW
     → 단조·슬로프 제한·이동평균 스무딩 → user_sec→ref_sec 곡선 (재생 트랙).
  3. 짝 재선정 — 각 감점 순간(atVideoSec)에서 정렬 곡선 ±2s 창의 자세거리 argmin
     → 정지 장면의 ref 프레임 (정지 트랙).
  4. 마커 — 감점 관절의 재추출 좌표+신뢰도 (정지 마커).

소비자: pipeline `_run_deferred_compare_render` 사후 스테이지(운영, GPU Pod) +
p35_extract_align.py CLI 래퍼(프로토/재현). rtmlib/cv2 는 **함수 내부 lazy import**
— Lambda 레이어 import 안전 (numpy 만 모듈 레벨). `infer_fn` 주입 파라미터로
로컬/테스트에서 GPU 없이 대체 가능 (verify_compare_stage_local.py 스텁 경로).
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import numpy as np

FPS = 15.0
# COCO-17 인덱스 (rtmlib wholebody 앞 17개 = COCO body)
J17 = ["nose", "left_eye", "right_eye", "left_ear", "right_ear",
       "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
       "left_wrist", "right_wrist", "left_hip", "right_hip",
       "left_knee", "right_knee", "left_ankle", "right_ankle"]
BODY12 = ["left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
          "left_wrist", "right_wrist", "left_hip", "right_hip",
          "left_knee", "right_knee", "left_ankle", "right_ankle"]
EDGES = [(5, 7), (7, 9), (6, 8), (8, 10), (5, 6), (5, 11), (6, 12),
         (11, 12), (11, 13), (13, 15), (12, 14), (14, 16)]
CONF_MIN = 0.3

# ── Phase 34 수술 ① — align_quality 임계 (quick-260808-r82) ──────────────────
# 렌더 스테이지의 tier 프록시 게이트(리포 7 doc 전부 trim_only → 렌더 부착 0,
# 프록시 가치 0)를 대체하는 **build_align 산출 자체**의 품질 판정 임계.
#
# 캘리브레이션 (승인 5편 align.json 실측, 2026-08-08 — elbow/kipup/pdshapefault/
# peterpan/powerspin GPU 산출 실물):
#   신뢰 커버리지(BODY12 × 프레임 중 conf>=CONF_MIN 비율):
#     user 최악 0.9468(elbow) / ref 최악 0.9441(pdshapefault)
#   곡선-자세거리 d_t = ||fu[t] − fr[round(curveRefSec[t]*fps)]||:
#     median 최악 3.125(elbow) / p85 최악 5.490(elbow)
#     (max 는 elbow 1129 등 일시 스파이크가 흔해 프로파일 통계로 부적합 — p85 채택)
# 마진 = 승인 최악값의 **2.0배** (구조적 마진 — 같은 결함 유형이 승인 최악의 두 배
# 까지 흔들려도 승인 문법으로 간주. 정렬이 실제로 깨지면(딴 동작 정렬·저신뢰 전멸)
# 자세거리·결측률은 한 자릿수 배로 벌어진다는 리그 decade-분리 구조 승계):
#   COVERAGE_MIN     = 1 − 2.0×(1−0.9441) = 0.888 → 0.88 (반올림 하향 = 완화 방향)
#   POSE_DIST_MED_MAX = 2.0×3.125 = 6.25 → 6.3 (반올림 상향 = 완화 방향)
#   POSE_DIST_P85_MAX = 2.0×5.490 = 10.98 → 11.0
# **일반화 한계 (박제):** 이 임계는 승인 5편 유도다 — belle-FAIL 측(doc 127a2a90)
# align 은 GPU 에서만 생산돼 로컬 캘리브레이션 불가(CPU align != GPU align, E 13% vs
# 28% 실측) → Pod 스윕 명시 이월 (.planning/quick/260808-r82-phase-34-3/POD-VERIFY.md).
COVERAGE_MIN = 0.88
POSE_DIST_MED_MAX = 6.3
POSE_DIST_P85_MAX = 11.0


def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def extract(video: Path, outdir: Path) -> list[Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    if not any(outdir.glob("*.jpg")):
        subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(video),
                        "-vf", f"fps={FPS}", "-q:v", "3", str(outdir / "%05d.jpg")], check=True)
    return sorted(outdir.glob("*.jpg"))


def build_model():
    """rtmlib Wholebody — **결정론 컨텍스트 안에서** 세션 생성 (Phase 34 실측 수리).

    이 경로에 결정론 주입이 빠져 있어 같은 영상의 재추출이 매번 다른 정렬을 만들었다
    (실측: 같은 Pod·같은 코드로 belle 반려본을 두 번 재분석 → align curveRefSec 불일치,
    렌더 저더 이벤트 1건 vs 9건으로 리그 판정이 갈림 = "통과가 운"). 채점 엔진
    (`rtmw_engine.RTMWPoseEngine`)은 이미 같은 컨텍스트를 쓰고 있었는데 렌더 정렬만
    누락된 상태였다 — 두 경로가 같은 규율을 공유해야 한다.

    env `RTMW_DETERMINISTIC` 미설정이면 컨텍스트는 아무것도 patch 하지 않는다
    (ort_determinism 계약 — 미설정 경로 byte-동일).
    """
    from rtmlib import Wholebody

    from .pose_engines.rtmw.ort_determinism import deterministic_inference_session

    det = os.environ.get("YOLOX_ONNX_PATH", "/workspace/yolox_weights/yolox_m.onnx")
    pose = os.environ.get("RTMW_ONNX_PATH", "/workspace/rtmw_weights/rtmw-x-384.onnx")
    device = os.environ.get("RTMW_DEVICE", "cuda")
    with deterministic_inference_session():
        return Wholebody(det=det, det_input_size=(640, 640), pose=pose,
                         to_openpose=False, backend="onnxruntime", device=device)


def infer_video(model, frames: list[Path]):
    import cv2
    kps, scs = [], []
    W = H = None
    for p in frames:
        img = cv2.imread(str(p))
        if W is None:
            H, W = img.shape[:2]
        out = model(img)
        k, s = out[0], out[1]
        if k is None or len(k) == 0:
            kps.append(np.full((17, 2), np.nan))
            scs.append(np.zeros(17))
            continue
        body_s = np.asarray(s)[:, :17]
        best = int(np.argmax(body_s.mean(axis=1)))
        kps.append(np.asarray(k)[best, :17, :2].astype(float))
        scs.append(body_s[best].astype(float))
    return np.stack(kps), np.stack(scs), W, H


def pose_feature(kp_norm: np.ndarray, sc: np.ndarray) -> np.ndarray:
    """(T,17,2) 정규화 좌표 → (T,24) 자세 특징: 힙중심·몸통스케일 정규화 12관절."""
    idx = [J17.index(j) for j in BODY12]
    hip = (kp_norm[:, J17.index("left_hip")] + kp_norm[:, J17.index("right_hip")]) / 2
    sho = (kp_norm[:, J17.index("left_shoulder")] + kp_norm[:, J17.index("right_shoulder")]) / 2
    torso = np.linalg.norm(sho - hip, axis=1)
    torso = np.where(torso > 1e-4, torso, np.nanmedian(torso[torso > 1e-4]) if (torso > 1e-4).any() else 1.0)
    feat = (kp_norm[:, idx] - hip[:, None, :]) / torso[:, None, None]
    conf = sc[:, idx]
    feat = np.where(conf[..., None] >= CONF_MIN, feat, 0.0)
    return np.nan_to_num(feat.reshape(len(kp_norm), -1), nan=0.0)


def dtw_path(D: np.ndarray) -> list[tuple[int, int]]:
    Tu, Tr = D.shape
    INF = np.inf
    cost = np.full((Tu + 1, Tr + 1), INF)
    cost[0, 0] = 0.0
    for i in range(1, Tu + 1):
        j0, j1 = 1, Tr + 1
        for j in range(j0, j1):
            c = D[i - 1, j - 1]
            cost[i, j] = c + min(cost[i - 1, j - 1], cost[i - 1, j], cost[i, j - 1])
    path = []
    i, j = Tu, Tr
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        moves = [(cost[i - 1, j - 1], i - 1, j - 1), (cost[i - 1, j], i - 1, j), (cost[i, j - 1], i, j - 1)]
        _, i, j = min(moves)
    return path[::-1]


def smooth_curve(path: list[tuple[int, int]], Tu: int) -> np.ndarray:
    """path → user 프레임별 ref 프레임 곡선 (단조 + 이동평균)."""
    from collections import defaultdict
    agg = defaultdict(list)
    for u, r in path:
        agg[u].append(r)
    xs = np.array(sorted(agg))
    ys = np.array([np.mean(agg[u]) for u in xs])
    full = np.interp(np.arange(Tu), xs, ys)
    k = 7
    pad = np.pad(full, (k // 2, k // 2), mode="edge")
    sm = np.convolve(pad, np.ones(k) / k, mode="valid")
    return np.maximum.accumulate(sm)  # 단조 보장


def select_pairs(records: list[dict], D: np.ndarray, curve: np.ndarray,
                 ukn: np.ndarray, usc: np.ndarray, rsc: np.ndarray,
                 moments: dict | None = None) -> dict:
    """감점 record → 정지 짝 재선정 (p35 프로토 process 블록의 순수 이동).

    atVideoSec 없는 record 는 moments 주입(rid 키) 시도 후에도 없으면 스킵
    (fail-closed — p35 현행). 짝 선정: 자세거리 최소 근방(<= min*1.15) 후보 중
    **해당 관절이 잘 보이는** ref 프레임 우선 (belle 엘보 ④ "정은지 팔이 좀 더
    잘 보이면"). 반환 = align.json `pairs` 스키마 그대로 (rid 키 dict).
    """
    inject = moments or {}
    fu_len, fr_len = D.shape
    pairs: dict = {}
    for rec in records:
        rid = rec["recordId"].split(":")[0]
        ut = rec.get("atVideoSec")
        if ut is None:
            ut = inject.get(rid, {}).get("atVideoSec")
        if ut is None:
            continue
        ui = int(np.clip(round(float(ut) * FPS), 0, fu_len - 1))
        center = int(round(curve[ui]))
        lo, hi = max(0, center - int(2 * FPS)), min(fr_len, center + int(2 * FPS) + 1)
        joint = rec["criterion"].split("__")[-1]
        window = D[ui, lo:hi]
        dmin = float(window.min())
        cand = np.where(window <= dmin * 1.15 + 1e-9)[0]
        if joint in J17 and len(cand) > 1:
            ji = J17.index(joint)
            ri = lo + int(cand[np.argmax(rsc[lo + cand, ji])])
        else:
            ri = lo + int(np.argmin(window))
        marker = None
        if joint in J17:
            ji = J17.index(joint)
            if usc[ui, ji] >= 0.5:
                marker = [float(ukn[ui, ji, 0]), float(ukn[ui, ji, 1])]
        pairs[rid] = {"atVideoSec": float(ut), "refVideoSec": ri / FPS,
                      "poseDist": float(D[ui, ri]), "joint": joint, "marker": marker,
                      "markerConf": float(usc[ui, J17.index(joint)]) if joint in J17 else None}
    return pairs


def draw_skeleton(img_path: Path, kp: np.ndarray, sc: np.ndarray, out: Path):
    import cv2
    img = cv2.imread(str(img_path))
    for a, b in EDGES:
        if sc[a] >= CONF_MIN and sc[b] >= CONF_MIN:
            cv2.line(img, tuple(kp[a].astype(int)), tuple(kp[b].astype(int)), (80, 220, 80), 3)
    for j in range(17):
        if sc[j] >= CONF_MIN:
            cv2.circle(img, tuple(kp[j].astype(int)), 6, (51, 75, 255), -1)
    cv2.imwrite(str(out), img)


def hstack_save(paths: list[Path], out: Path):
    import cv2
    imgs = [cv2.imread(str(p)) for p in paths]
    h = min(i.shape[0] for i in imgs)
    imgs = [cv2.resize(i, (int(i.shape[1] * h / i.shape[0]), h)) for i in imgs]
    cv2.imwrite(str(out), np.hstack(imgs))


def _write_verify_stills(verify: Path, pairs: dict, uframes: list[Path], rframes: list[Path],
                         ukp: np.ndarray, usc: np.ndarray,
                         rkp: np.ndarray, rsc: np.ndarray) -> None:
    """검증 스틸 — 짝 스틸(스켈레톤 포함) + 스켈레톤 6장 (p35 process 산출 동일).

    스테이지는 호출하지 않는다(verify_dir=None) — 스크립트 래퍼 전용 출력."""
    verify.mkdir(exist_ok=True)
    for rid, p in pairs.items():
        ui = int(np.clip(round(float(p["atVideoSec"]) * FPS), 0, len(uframes) - 1))
        ri = int(round(float(p["refVideoSec"]) * FPS))
        up, rp = verify / f"pair_{rid}_u.jpg", verify / f"pair_{rid}_r.jpg"
        draw_skeleton(uframes[ui], ukp[ui], usc[ui], up)
        draw_skeleton(rframes[ri], rkp[ri], rsc[ri], rp)
        hstack_save([up, rp], verify / f"pair_{rid}.jpg")
    # 스켈레톤 검증 6장 (균등 샘플)
    for i in np.linspace(0, len(uframes) - 1, 6).astype(int):
        draw_skeleton(uframes[i], ukp[i], usc[i], verify / f"skel_u{i:04d}.jpg")


def build_align(user_video: Path, ref_video: Path, records: list[dict], workdir: Path,
                *, model=None, infer_fn=None, moments: dict | None = None,
                verify_dir: Path | None = None) -> dict:
    """15fps 재추출 + 자세거리 DTW 정렬 + 짝 재선정 → align dict (align.json 스키마).

    Args:
      records: doc `result.deductionBreakdown.records` — atVideoSec 없는 record 는
        moments 주입 후에도 없으면 스킵 (fail-closed).
      model: rtmlib Wholebody (None 이면 build_model() — GPU 필요).
      infer_fn: (frames: list[Path]) -> (kp, sc, W, H) 주입 — 로컬/테스트에서 GPU
        없이 대체 (모델 경로 무접촉). None 이면 model 로 infer_video.
      moments: rid→{atVideoSec, ...} 주입 (프로토 전용 — 운영 스테이지 None).
      verify_dir: 지정 시 검증 스틸 출력 (스크립트 래퍼 전용 — 스테이지 None).

    Returns: {fps, userSize, refSize, userFrames, refFrames, curveRefSec, pairs,
      userKp, userScore, refKp, refScore, joints17} — 렌더러(compare_render)가
      읽는 align.json 스키마 그대로 (스크립트 래퍼가 "motion" 키만 앞에 붙인다).
    """
    workdir = Path(workdir)
    uframes = extract(Path(user_video), workdir / "uf15")
    rframes = extract(Path(ref_video), workdir / "rf15")

    if infer_fn is None:
        if model is None:
            model = build_model()
        _model = model

        def infer_fn(frames):
            return infer_video(_model, frames)

    ukp, usc, UW, UH = infer_fn(uframes)
    rkp, rsc, RW, RH = infer_fn(rframes)
    ukn = ukp / np.array([UW, UH])
    rkn = rkp / np.array([RW, RH])

    fu = pose_feature(ukn, usc)
    fr = pose_feature(rkn, rsc)
    D = np.linalg.norm(fu[:, None, :] - fr[None, :, :], axis=2)
    curve = smooth_curve(dtw_path(D), len(fu))  # user frame -> ref frame

    pairs = select_pairs(records, D, curve, ukn, usc, rsc, moments=moments)

    if verify_dir is not None:
        _write_verify_stills(Path(verify_dir), pairs, uframes, rframes, ukp, usc, rkp, rsc)

    return {
        "fps": FPS,
        "userSize": [UW, UH], "refSize": [RW, RH],
        "userFrames": len(fu), "refFrames": len(fr),
        "curveRefSec": [round(float(c) / FPS, 4) for c in curve],  # index = user frame @15fps
        "pairs": pairs,
        "userKp": np.round(ukn, 4).reshape(len(fu), -1).tolist(),
        "userScore": np.round(usc, 3).tolist(),
        "refKp": np.round(rkn, 4).reshape(len(fr), -1).tolist(),
        "refScore": np.round(rsc, 3).tolist(),
        "joints17": J17,
    }


def align_quality(align: dict) -> tuple[bool, list[str]]:
    """build_align 산출 dict 만 소비하는 순수 품질 판정 (Phase 34 수술 ①).

    tier 프록시(파이프라인 채점-측 정렬 신뢰)가 아니라 **렌더에 실제로 들어가는
    이 정렬 산출 자체**를 판정한다 — 리포 7 doc 전부 tier=trim_only(승인 픽스처
    포함) 실측 → 프록시 게이트는 렌더 부착 0 = 가치 0 이었다 (quick-260808-r82).

    판정 2축 (보드 명시, 임계 근거는 상단 캘리브레이션 주석):
      Q1/Q2 신뢰 커버리지 — userScore/refScore (T,17) → BODY12 열 → 전 (프레임×
             관절) 중 conf >= CONF_MIN 비율. user·ref 각각 COVERAGE_MIN 이상.
      Q3/Q4 자세거리 프로파일 — userKp/refKp reshape (T,17,2) → pose_feature
             (build_align 과 단일 출처) → 곡선 따라 d_t = ||fu[t] −
             fr[clip(round(curveRefSec[t]*fps))]|| → median <= POSE_DIST_MED_MAX
             ∧ p85 <= POSE_DIST_P85_MAX.

    반환: (전건 PASS 여부, 리그 verify 라인 형식 판정 목록 — "지표=값 임계=값").
    필수 필드 결측/형상 불량 = FAIL (fail-closed — 판정 불가 산출물은 내보내지
    않는다. 구버전 포맷(refKp 없음 벤치 슬롯)은 대상 외 — 운영 스테이지의
    build_align 은 항상 신포맷을 생산한다, data/README.md 실측).
    build_align/select_pairs/pose_feature 본체는 무접촉 — 소비만 한다.
    """
    try:
        fps = float(align["fps"])
        usc = np.asarray(align["userScore"], dtype=float)
        rsc = np.asarray(align["refScore"], dtype=float)
        ukn = np.asarray(align["userKp"], dtype=float).reshape(len(usc), 17, 2)
        rkn = np.asarray(align["refKp"], dtype=float).reshape(len(rsc), 17, 2)
        curve = np.asarray(align["curveRefSec"], dtype=float)
        if (
            usc.ndim != 2 or usc.shape[1] != 17 or rsc.ndim != 2
            or rsc.shape[1] != 17 or len(curve) != len(usc) or fps <= 0
            or len(usc) == 0 or len(rsc) == 0
        ):
            raise ValueError("align 필드 형상 불량")
    except (KeyError, TypeError, ValueError) as exc:
        return False, [
            f"  [FAIL] Q0 align 형상: 필수 필드 결측/불량 ({exc}) — 판정 불가 fail-closed"
        ]

    lines: list[str] = []
    idx = [J17.index(j) for j in BODY12]
    ucov = float((usc[:, idx] >= CONF_MIN).mean())
    rcov = float((rsc[:, idx] >= CONF_MIN).mean())
    for name, cov in (("user", ucov), ("ref", rcov)):
        ok = cov >= COVERAGE_MIN
        lines.append(
            f"  [{'PASS' if ok else 'FAIL'}] Q 신뢰 커버리지 {name}: "
            f"cov={cov:.3f} 임계>={COVERAGE_MIN}"
        )

    fu = pose_feature(ukn, usc)
    fr = pose_feature(rkn, rsc)
    ri = np.clip(np.round(curve * fps).astype(int), 0, len(fr) - 1)
    d = np.linalg.norm(fu - fr[ri], axis=1)
    d_med = float(np.median(d))
    d_p85 = float(np.percentile(d, 85))
    ok_med = d_med <= POSE_DIST_MED_MAX
    ok_p85 = d_p85 <= POSE_DIST_P85_MAX
    lines.append(
        f"  [{'PASS' if ok_med else 'FAIL'}] Q 자세거리 median: "
        f"d_med={d_med:.3f} 임계<={POSE_DIST_MED_MAX}"
    )
    lines.append(
        f"  [{'PASS' if ok_p85 else 'FAIL'}] Q 자세거리 p85: "
        f"d_p85={d_p85:.3f} 임계<={POSE_DIST_P85_MAX}"
    )
    return all("[PASS]" in ln for ln in lines), lines

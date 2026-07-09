"""합성 교란 순수 모듈 — 좌표 보정 학습 트랙의 자가 라벨 생성기 (22-01 Task 3, D-10a).

깨끗한 RTMW 시퀀스에 실측 분포 기반 교란을 주입하고, **정답 = 교란 전 원좌표**를
함께 반환한다 (자가 라벨, 교사 무관 — 사람 점수 라벨 아님). 모델은 이 페어로
"영상+튄 좌표 → 보정 좌표"를 학습한다.

교란 4종 구조 (NLM Q3 차용, 수치는 차용 금지):
  · 가려짐 Null run — 연속 프레임 좌표를 Null(NaN) + confidence 저값으로 덮어씀.
  · 가우시안 지터 — RTMW 프레임별 떨림 모방.
  · L/R 스왑 — 좌/우 관절 교환(생체역학 불가 상태).
  · 프레임 드롭 — 저fps 시뮬 (make_temporal_trap 의 셔플과 별개).

전 수치 파라미터(run 길이·지터 크기)는 rtmw_error_profile.json 히스토그램에서
rng 로 샘플 — NLM 임의 수치(3~5프레임 Null, 5% 지터)는 소스 근거 없음이 자인됨
(22-RESEARCH Pitfall 4, A3). 커리큘럼 stage 상수는 구조(관절 범주·연속성·복합
여부)만 정의한다.

[[scoring-redesign-must-generalize-no-overfit]]: 정답=원좌표라 교사·사람 라벨 무관,
curve-fit 불가. validation.py 규율 정합 — numpy 단독, boto3/네트워크 0, (T,J,C)
shape 계약 ValueError.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# 가려짐 confidence 저값 — Null 좌표에 동반되는 신뢰도 하한 (분포 아님, Null 표식).
OCCLUSION_CONFIDENCE = 0.1

# 핵심/비핵심 관절 범주 마커 (커리큘럼 구조 — 특정 동작 curve-fit 아님).
_CORE_MARKERS = ("hip", "knee", "ankle")
_NONCORE_MARKERS = ("shoulder", "elbow", "wrist", "hand", "arm")


@dataclass(frozen=True, eq=False)
class PerturbResult:
    """교란 결과 + 정답(원좌표). eq=False — ndarray 필드 요소비교 모호성 회피.

    perturbed         = 교란된 (T,J,C) 시퀀스.
    original          = 교란 전 원좌표 (정답 라벨, 자가 생성).
    perturbed_joints  = 교란된 관절 인덱스 tuple.
    perturbed_frames  = 교란된 프레임 인덱스 tuple.
    stage             = 커리큘럼 단계 (1/2/3).
    """

    perturbed: np.ndarray
    original: np.ndarray
    perturbed_joints: tuple
    perturbed_frames: tuple
    stage: int


def load_profile(path) -> dict:
    """rtmw_error_profile.json 로드 (교란 파라미터 분포). 순수 파일 I/O."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 분포 샘플러 — 히스토그램(bin_edges + counts)에서 값 1개 추출.
# ---------------------------------------------------------------------------
def _sample_histogram(hist: dict, rng: np.random.Generator) -> float:
    """히스토그램에서 값 샘플 — bin 을 counts 비례로 고르고 bin 내부 균등 추출."""
    edges = np.asarray(hist["bin_edges"], dtype=float)
    counts = np.asarray(hist["counts"], dtype=float)
    total = counts.sum()
    if edges.size < 2 or total <= 0:
        return float(edges[0]) if edges.size else 0.0
    probs = counts / total
    i = int(rng.choice(len(counts), p=probs))
    return float(rng.uniform(edges[i], edges[i + 1]))


def _aggregate_jump_hist(profile: dict) -> dict:
    """per_joint_jump_deg 관절별 히스토그램을 counts 합산(공유 bin_edges)해 집계."""
    per_joint = profile.get("per_joint_jump_deg") or {}
    edges = None
    total_counts = None
    for hist in per_joint.values():
        e = np.asarray(hist["bin_edges"], dtype=float)
        c = np.asarray(hist["counts"], dtype=float)
        if edges is None:
            edges = e
            total_counts = c.copy()
        elif e.shape == edges.shape:
            total_counts = total_counts + c
    if edges is None:
        raise KeyError("per_joint_jump_deg 히스토그램 부재 — profile 무효")
    return {"bin_edges": edges.tolist(), "counts": total_counts.tolist()}


def _sample_run_length(profile: dict, rng: np.random.Generator) -> int:
    """confidence_drop_run_length 분포에서 연속 Null run 길이 샘플 (>=1)."""
    hist = profile["confidence_drop_run_length"]
    return max(1, int(round(_sample_histogram(hist, rng))))


# ---------------------------------------------------------------------------
# 관절 범주 / L/R 스왑.
# ---------------------------------------------------------------------------
def _classify_joints(joint_keys) -> tuple[list[int], list[int]]:
    """joint_keys → (core 인덱스, noncore 인덱스). 마커 미매치는 어느 쪽도 아님."""
    core: list[int] = []
    noncore: list[int] = []
    for i, name in enumerate(joint_keys or ()):
        low = str(name).lower()
        if any(m in low for m in _CORE_MARKERS):
            core.append(i)
        elif any(m in low for m in _NONCORE_MARKERS):
            noncore.append(i)
    return core, noncore


def swap_lr_joints(coords: np.ndarray, joint_keys):
    """left_X ↔ right_X 관절 열을 교환 (생체역학 불가 상태 생성).

    반환 (swapped, pairs) — pairs 는 교환된 (left_name, right_name) tuple 리스트.
    순수 — 입력 미변형(복사본 반환)."""
    _check_shape(coords)
    swapped = coords.copy()
    index = {str(k): i for i, k in enumerate(joint_keys or ())}
    pairs: list[tuple] = []
    for name, li in index.items():
        if not name.startswith("left"):
            continue
        rname = "right" + name[len("left"):]
        ri = index.get(rname)
        if ri is None:
            continue
        swapped[:, li], swapped[:, ri] = coords[:, ri].copy(), coords[:, li].copy()
        pairs.append((name, rname))
    return swapped, pairs


# ---------------------------------------------------------------------------
# 시간 함정 — 역전/셔플 (언어-프라이어 shortcut 검출, Pitfall 6).
# ---------------------------------------------------------------------------
def make_temporal_trap(coords: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """프레임 순서 역전 또는 셔플한 함정 시퀀스 (행 순열, 값 보존).

    bake-off 에서 모델이 영상을 안 보고 시간 순서를 언어 프라이어로 추측하는
    shortcut 을 검출한다. 순수 — 복사본 반환."""
    _check_shape(coords)
    t = coords.shape[0]
    if rng.random() < 0.5:
        return coords[::-1].copy()  # 시간 역전.
    order = rng.permutation(t)  # 프레임 셔플.
    if t > 1 and np.array_equal(order, np.arange(t)):
        order = order[::-1]  # 항등 순열 회피 (변형 보장).
    return coords[order].copy()


# ---------------------------------------------------------------------------
# 커리큘럼 교란 주입 (stage 1/2/3).
# ---------------------------------------------------------------------------
def perturb_sequence(
    coords: np.ndarray,
    profile: dict,
    stage: int,
    rng: np.random.Generator,
    joint_keys=None,
) -> PerturbResult:
    """coords(T,J,C) 에 stage 커리큘럼 교란 주입, 정답=원좌표와 함께 반환 (D-10a).

    stage1 = 비핵심 관절 소수·단프레임 (지터 + 단발 가려짐).
    stage2 = 핵심 관절(무릎/엉덩이/발목) 연속 다프레임 Null (뼈길이 기하 추론).
    stage3 = L/R 스왑 + 복합 가려짐/지터 (CoT 오류 언어화 후 재수정).

    파라미터(run 길이·지터 크기)는 profile 히스토그램에서 샘플 — profile=None 이면
    TypeError(분포 출처 강제). 좌표 채널 x,y 는 [0,1] 정규화 가정(지터 std=샘플값/그리드).
    """
    if profile is None:
        raise TypeError("profile 필수 — 교란 파라미터는 rtmw_error_profile 분포에서 샘플 (A3)")
    _check_shape(coords)
    t, j, _c = coords.shape
    original = coords.copy()
    out = coords.copy()

    core, noncore = _classify_joints(joint_keys)
    # joint_keys 부재 시 인덱스 기반 폴백(앞절반 noncore, 뒤절반 core) — 구조만 유지.
    if not core and not noncore:
        half = max(1, j // 2)
        noncore = list(range(half))
        core = list(range(half, j))

    jump_hist = _aggregate_jump_hist(profile)
    perturbed_joints: set[int] = set()
    perturbed_frames: set[int] = set()

    if stage <= 1:
        targets = _pick(noncore or core, rng, k=min(2, len(noncore or core)))
        for ji in targets:
            f = int(rng.integers(0, t))
            _apply_jitter(out, ji, f, jump_hist, rng)
            perturbed_joints.add(ji)
            perturbed_frames.add(f)
        # 단발 가려짐 1건 (Null 바인딩 규격 확립).
        if targets:
            ji = int(_pick(targets, rng, k=1)[0])
            f = int(rng.integers(0, t))
            _apply_occlusion(out, ji, f, f + 1, t)
            perturbed_joints.add(ji)
            perturbed_frames.add(f)
    elif stage == 2:
        targets = _pick(core or noncore, rng, k=min(2, len(core or noncore)))
        for ji in targets:
            run = _sample_run_length(profile, rng)
            run = max(2, run)  # 연속 다프레임 보장 (stage2 구조).
            start = int(rng.integers(0, max(1, t - run)))
            end = min(t, start + run)
            _apply_occlusion(out, ji, start, end, t)
            perturbed_joints.add(ji)
            perturbed_frames.update(range(start, end))
    else:  # stage 3 — 복합.
        out, pairs = swap_lr_joints(out, joint_keys or [])
        if pairs:
            index = {str(k): i for i, k in enumerate(joint_keys or ())}
            for lname, rname in pairs:
                perturbed_joints.add(index[lname])
                perturbed_joints.add(index[rname])
            perturbed_frames.update(range(t))
        # 복합 가려짐 + 지터 (핵심 관절).
        for ji in _pick(core or noncore, rng, k=min(2, len(core or noncore))):
            run = max(2, _sample_run_length(profile, rng))
            start = int(rng.integers(0, max(1, t - run)))
            end = min(t, start + run)
            _apply_occlusion(out, ji, start, end, t)
            _apply_jitter(out, ji, int(rng.integers(0, t)), jump_hist, rng)
            perturbed_joints.add(ji)
            perturbed_frames.update(range(start, end))

    return PerturbResult(
        perturbed=out,
        original=original,
        perturbed_joints=tuple(sorted(perturbed_joints)),
        perturbed_frames=tuple(sorted(perturbed_frames)),
        stage=int(stage),
    )


# ---------------------------------------------------------------------------
# 교란 primitive.
# ---------------------------------------------------------------------------
def _apply_occlusion(out: np.ndarray, ji: int, start: int, end: int, t: int) -> None:
    """[start,end) 프레임의 관절 ji 좌표를 Null(NaN) + confidence 저값으로 덮어씀.

    키(관절 축) 삭제 금지 — 값만 Null 로 바인딩 (D-11 철칙 1)."""
    s = max(0, start)
    e = min(t, end)
    if e <= s:
        return
    c = out.shape[2]
    out[s:e, ji, 0] = np.nan
    if c >= 2:
        out[s:e, ji, 1] = np.nan
    if c >= 3:
        out[s:e, ji, 2] = OCCLUSION_CONFIDENCE  # confidence 저값 (Null 표식).


def _apply_jitter(
    out: np.ndarray, ji: int, f: int, jump_hist: dict, rng: np.random.Generator
) -> None:
    """관절 ji, 프레임 f 좌표에 분포-샘플 크기의 가우시안 지터 (도→그리드 환산).

    지터 std 는 per_joint_jump_deg 집계 히스토그램에서 샘플한 값(도)을 그리드
    스케일(/90)로 환산 — 실측 프레임간 튐 크기를 좌표 노이즈로 모방."""
    if f < 0 or f >= out.shape[0]:
        return
    std = _sample_histogram(jump_hist, rng) / 90.0  # 도 → 정규화 좌표 스케일.
    for ch in (0, 1):
        if ch < out.shape[2]:
            out[f, ji, ch] = out[f, ji, ch] + float(rng.normal(0.0, max(1e-6, std)))


def _pick(indices, rng: np.random.Generator, k: int) -> list[int]:
    """인덱스 목록에서 중복 없이 k 개 선택 (재현 가능)."""
    pool = list(indices)
    if not pool or k <= 0:
        return []
    k = min(k, len(pool))
    chosen = rng.choice(len(pool), size=k, replace=False)
    return [int(pool[i]) for i in chosen]


def _check_shape(coords) -> None:
    """(T,J,C) shape 계약 — 위반 시 ValueError (validation.py _as_tj 패턴)."""
    if not isinstance(coords, np.ndarray) or coords.ndim != 3:
        raise ValueError(
            f"coords 는 (T,J,C) ndarray 여야 함 — got "
            f"{getattr(coords, 'shape', type(coords).__name__)}"
        )
    if coords.shape[2] < 2:
        raise ValueError(f"C(좌표 채널) >= 2 필요 — got shape {coords.shape}")

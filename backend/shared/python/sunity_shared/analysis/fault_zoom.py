"""문제 부위 확대 비교 이미지 생성 (belle 2026-06-21).

깨진 3D 뷰어([[fault-zoom-compare-and-phase24-true3d]]) 대체. veto/결함이 잡힌
관절 부위만 worst-pose 시점 프레임에서 **crop + zoom** 해 학생 vs 기준(정은지/
이전 영상)을 나란히 보여주고, 부족한 각도를 숫자로 표기한다. 결함이 여러 개면
앱이 carousel 로 넘긴다.

설계:
  · 이미지에는 **숫자 각도 마커만** 그린다 (PIL 기본 폰트는 한글 글리프 부재 →
    한글 캡션/라벨은 앱이 담당, backend 는 시각 crop + 숫자만). 산출 출처 분리
    정합 — 좌표/각도는 backend, 표시는 app.
  · 프레임/좌표는 frame_extractor(9fps/640px) + keypointReport(정규화 0..1) 재사용.
  · 실패는 graceful — 본 기능은 부가물이라 분석 흐름을 막지 않는다 (호출측 try).

좌표계: keypointReport.data 는 flat (T*J*2), 값은 [0,1] 정규화 (frame 의 W/H 기준).
프레임은 frame_extractor 가 긴 변 640 으로 리사이즈한 (H,W,3) uint8.

Phase 31-03 (D-11/D-12) — 목표 각도 화살표 + correctedPose target:
  · **display 전용, 채점 무접촉** — 화살표/target 경로는 dimensions/kismam 을 import
    하지 않고 점수/veto/게이트에 어떤 값도 되돌리지 않는다.
  · 리뷰 B-02: 화살표 기하는 (proximal, vertex, distal) 3점 + DTW 대응 reference
    좌표로만 만든다. 감점 record 의 direction 어휘나 수치 필드로 화면 기하를 만들면
    "편차값을 절대 목표각으로" 오독하는 경로가 생긴다 (reference_relative record 의
    measuredValue 는 학생 절대 관절각이 아니라 정은지-대비 편차다).
  · 2차 리뷰 H2-03: 미러 반사 후보를 "현재 distal 에 더 가까운 쪽"으로 고르면 큰
    교정에서 오방향이 나온다 ("올바른 교정은 작은 이동"이라는 거짓 가정). 반사 여부는
    per-joint 거리가 아니라 full-body topology(어깨/힙 좌우 방향)로 프레임 단위 1회
    판정하고, 불명확하면 화살표를 생략한다.
  · 2차 리뷰 B2-01: 자동 교정의 joint/targetDeg/source frame 은 CorrectedPoseTarget
    단일 immutable 계약으로 묶는다 (따로 계산 금지). 감점 record 는 후보 우선순위에만
    쓰고, 목표각은 DTW matched reference 3점 내각에서만 계산한다.
"""

from __future__ import annotations

import io
import logging
import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw

log = logging.getLogger(__name__)

# crop 한 변 = 프레임 짧은 변의 비율 (관절 주변 zoom — 작을수록 더 확대).
_CROP_FRAC = 0.42
# 합성 시 각 crop 출력 한 변(px). 두 장 가로 합성 → (2*OUT, OUT).
_OUT = 360
# 마커 색 (브랜드 #FF4B33).
_BRAND = (255, 75, 51)

# 다리 사이각 선 최소 벡터 길이(px) — **display 전용, 채점 무접촉** (quick-260705-r6x).
# 골반 중점↔다리 끝 벡터가 이보다 짧으면(겹친 좌표) 선/호를 그려도 방향이 무의미해
# 오히려 오인 → 드로잉 생략하고 기존 렌더로 폴백. 채점/veto/게이트 경로에 진입하지
# 않는 표시 전용 상수이므로 calibration-source-hard-gate 대상 아님.
_MIN_LEG_VEC_PX = 8

# 사이각 선 keypoint 의 crop-포함 허용 마진(px) — **display 전용, 채점 무접촉**.
# 드로잉에 쓰는 hip 중점+다리 끝의 crop-내 raw 픽셀(clamp 전)이 crop 박스를
# 벗어나면 _to_crop_px clamp 가 좌표를 경계로 당겨 선이 몸과 무관하게 폭주한다
# (2026-07-05 belle pod PNG: 정은지 crop 이 정강이만 잘라 hip 이 crop 위로 벗어남 —
# conf 게이트는 통과했으나 자세가 스플릿이 아니고 crop 도 다리 하단만 포함).
# 경계 근처 rounding 은 허용하되 명백히 벗어난 점은 배제 = 그 측 사이각 생략.
_CROP_INCLUSION_MARGIN_PX = int(_OUT * 0.10)

# crop 앵커 keypoint 최소 confidence (quick-260702-sic). 프론트
# KeypointOverlay.KEYPOINT_LOW_CONFIDENCE_THRESHOLD = 0.5 선례 정합 — 저신뢰
# keypoint(RTMW 몸통 붕괴 등)를 crop 중심으로 쓰면 엉뚱한 부위(뒤통수)가 확대됨.
_KP_CONF_MIN = 0.5

# 결함단위(region) grouping — 같은 결함(스플릿 등)에서 온 좌+우 동일 부위 관절들을
# 카드 1장으로 묶는다 (quick-260702-sic). keypointReport 의 8-keypoint 이름공간
# (left/right_hand = COCO wrist 매핑) + 향후 확장 이름(ankle/elbow/wrist)을 함께 커버.
_REGION_JOINTS: dict[str, frozenset[str]] = {
    "legs": frozenset({
        "left_hip", "right_hip",
        "left_knee", "right_knee",
        "left_ankle", "right_ankle",
    }),
    "arms": frozenset({
        "left_shoulder", "right_shoulder",
        "left_elbow", "right_elbow",
        "left_wrist", "right_wrist",
        "left_hand", "right_hand",
    }),
}
# grouped bbox crop 마진 — 멤버 관절 전체 + 주변 컨텍스트.
_BBOX_MARGIN = 1.8

# 완화(relaxed) crop 확대 배율 — **display 전용, 채점 무접촉** (Phase 25-03).
# Phase 32 (D-20): 프레이밍에는 더 이상 적용하지 않는다 — relaxed 프레이밍이 valid
# 대비 2배 넓어 "정은지 crop 이 비교와 안 맞음"(belle 실기기)이라, _side_crop 의 relaxed
# 분기가 valid 와 동일하게 margin=1.0(양측 1.8배)으로 프레이밍을 통일했다
# (faultzoom-reference-crop-2x-wider-diagnosed 합의: 프레이밍은 좌표 오차에 둔감 →
# 통일, 마커는 민감 → relaxed anchor_px=None 생략 게이트만 유지). 상수는 삭제하지 않고
# 향후 마커 게이트/완화 crop 튜닝 참조용으로 보존한다(현재 프레이밍 미사용).
_RELAXED_MARGIN = 2.0


@dataclass(frozen=True)
class _CropUnit:
    """fan-out crop 단위 — 단일 관절(region=None) 또는 결함단위 좌+우 묶음."""

    joint: str  # 대표 keypoint (S3 key / TS 계약의 joint 필드)
    members: tuple[str, ...]  # crop bbox 에 담을 keypoint 전부 (단일이면 (joint,))
    region: str | None  # "legs" | "arms" | None


def _group_fault_joints(
    fault_joints: list[str], joint_kinds: dict[str, str] | None
) -> list[_CropUnit]:
    """fault_joints → crop unit 리스트 (순수, 순서 보존 + dedup).

    grouping 조건 (전부 만족 시 region 1 unit):
      · 같은 region(_REGION_JOINTS) 소속 fault joint 가 2개 이상
      · 좌(left_*)+우(right_*) 양측에 걸침
      · kind 가 전원 동일한 non-None 값 — mode3 improved/worsened 혼재 시 비활성.
        kind 전원 부재(None)는 grouping 하지 않음: production 은 항상 kind 를
        세팅(Mode1='deficit'/Mode3 방향)하므로 부재 = legacy 호출 — 기존 관절당
        1장 동작 보존 (기존 테스트 6개 무수정 PASS 하위호환 게이트).
    대표 joint = fault_joints 순서상 첫 멤버. 그 외는 관절당 1 unit (region=None).
    """
    kinds = joint_kinds or {}
    ordered: list[str] = []
    seen: set[str] = set()
    for j in fault_joints:
        if j not in seen:
            seen.add(j)
            ordered.append(j)

    grouped: dict[str, str] = {}  # member joint → region
    reps: dict[str, str] = {}  # region → 대표 joint
    for region, region_joints in _REGION_JOINTS.items():
        members = [j for j in ordered if j in region_joints]
        if len(members) < 2:
            continue
        has_left = any(m.startswith("left_") for m in members)
        has_right = any(m.startswith("right_") for m in members)
        if not (has_left and has_right):
            continue
        member_kinds = {kinds.get(m) for m in members}
        if len(member_kinds) != 1 or next(iter(member_kinds)) is None:
            continue
        for m in members:
            grouped[m] = region
        reps[region] = members[0]

    units: list[_CropUnit] = []
    for j in ordered:
        region = grouped.get(j)
        if region is None:
            units.append(_CropUnit(joint=j, members=(j,), region=None))
        elif reps.get(region) == j:
            members = tuple(m for m in ordered if grouped.get(m) == region)
            units.append(_CropUnit(joint=j, members=members, region=region))
        # grouped 비대표 멤버 → 개별 fan-out 에서 제거 (카드 1장).
    return units


def select_advisory_joints(
    kp_deltas: dict[str, float],
    confirmed: set[str],
    tol_deg: float,
    max_items: int = 2,
) -> list[str]:
    """측정 초과 관절 선별 — advisory("참고·확인 권장") 확대 카드 대상 (quick-260704-fz4).

    입력 kp_deltas 는 이미 **keypoint 이름공간**으로 매핑된 {keypoint: delta_deg(signed)}.
    kismam angle key → keypoint 매핑은 호출측 pipeline(_KISMAM_TO_KEYPOINT) 책임 —
    본 모듈은 이름공간 무지 유지. 반환 = |delta| > tol_deg AND confirmed(확정 결함)
    제외인 keypoint 를 |delta| 내림차순으로 최대 max_items 개 (캐러셀 과밀 방지).
    비유한(nan/inf)/변환 불가 delta 는 defensive skip.

    위양성 교훈 ([[window-median-silent-seed-fp-reverted]], quick-260702-o0c revert):
    window median 측정 초과를 감점 seed 로 쓰면 RTMW jitter/촬영거리 노이즈가 위양성
    감점으로 증폭된다. advisory 는 "측정 초과 = 참고"일 뿐 결함 확정이 아니다 —
    **표시 전용. 채점/veto/게이트 입력으로 절대 쓰지 말 것.**
    """
    scored: list[tuple[float, str]] = []
    for kp, delta in (kp_deltas or {}).items():
        if kp in confirmed:
            continue
        try:
            mag = abs(float(delta))
        except (TypeError, ValueError):
            continue
        if not np.isfinite(mag) or mag <= float(tol_deg):
            continue
        scored.append((mag, kp))
    scored.sort(key=lambda t: -t[0])
    return [kp for _mag, kp in scored[: max(0, int(max_items))]]


def _to_rep_idx(
    idx: int, frames_fps: float, rep_fps: float, rep_frames: int
) -> int:
    """9fps frames 인덱스 → keypointReport fps 인덱스 (B1 변환 공식 단일 출처).

    build_fault_zoom_comparisons 와 select_confident_frame 이 같은 공식을
    공유한다 — 중복 공식 금지 (quick-260705-ftn)."""
    return max(0, min(
        int(round(idx / max(1e-6, frames_fps) * rep_fps)),
        max(0, rep_frames - 1),
    ))


def select_confident_frame(
    report: dict,
    candidates: list,
    members: list[str] | tuple[str, ...],
    frames_fps: float = 9.0,
) -> int | None:
    """window candidates 중 멤버 관절 평균 confidence 최대 프레임 선택 (순수).

    window median 프레임이 keypoint 붕괴 구간이면 relaxed/full 강하로 카드가
    망가짐 (2026-07-05 pod 재현: ref-kip-up frame 37 전 keypoint <0.5, 동일
    영상 30/59/80 에선 legs 4점 valid) — 측정-표시 정합은 window 안에서
    유지하면서 신뢰 프레임을 고른다. 표시 전용, 채점/veto/게이트 무접촉.

    candidates = 9fps frames 인덱스 (sourceFrameIndices 의 user/reference 리스트).
    빈 리스트/전원 비정수 → None (호출측 폴백 = override 없음). 전 candidate
    전 멤버 conf None(legacy/confidence 부재 report) → sorted median 폴백
    (기존 pipeline 동작 보존 — 하위호환 diff 0). 동점은 sorted 오름차순 첫
    인덱스 (결정론 tie-break). 반환 = 9fps frames 인덱스.
    """
    rep = report or {}
    ints: list[int] = []
    for c in candidates or []:
        try:
            ints.append(int(c))
        except (TypeError, ValueError):
            continue
    if not ints:
        return None
    ordered = sorted(ints)
    rep_fps = float(rep.get("fps") or frames_fps)
    rep_frames = int(rep.get("frames") or 0)
    best_idx: int | None = None
    best_score = -1.0
    for idx in ordered:
        rep_idx = _to_rep_idx(idx, frames_fps, rep_fps, rep_frames)
        confs = [
            c for m in members
            if (c := _kp_conf(rep, rep_idx, m)) is not None
        ]
        if not confs:
            continue
        score = sum(confs) / len(confs)
        if score > best_score:
            best_score, best_idx = score, idx
    if best_idx is None:
        # legacy 폴백 — 기존 pipeline 의 sorted median 과 동일 산출.
        return ordered[len(ordered) // 2]
    return best_idx


def select_confident_index(
    report: dict,
    candidates: list,
    members: list[str] | tuple[str, ...],
    frames_fps: float = 9.0,
) -> int | None:
    """멤버 관절 confidence 최대 프레임의 **원본 candidates 내 위치** (순수).

    select_confident_frame 이 반환하는 '프레임 값'을 그 값의 candidates 내 index 로
    바꿔준다 — DTW 정렬용. user/ref window(sourceFrameIndices)는 **position 으로 DTW
    대응**(user_frame_candidates[i] ↔ ref_frame_candidates[i])하므로, 카드 안에서
    student↔reference 를 같은 순간으로 맞추려면 값이 아니라 **같은 index** 로 짝지어야
    한다 (faultzoom-same-frame-crops NEW 서브버그, belle 2026-07-25: sel_r 을 ref
    자기 confidence 로 독립 선택하면 index 가 어긋나 정은지 패널이 학생과 다른 순간을
    보여줌 — "정은지 쪽은 아예 다른 장면").

    선택 규칙은 select_confident_frame 과 동일(정렬 순회 + 최소 프레임값 tie-break,
    legacy conf 부재 → sorted median). 그 함수에 위임하므로 학생측 프레임 선택은
    byte-동일하게 보존된다. 빈/전원 비정수 → None. 선택 값의 원본 위치를 못 찾으면
    (이론상 불가) None → 호출측 batch 기본 프레임 폴백.
    """
    sel_value = select_confident_frame(report, candidates, members, frames_fps)
    if sel_value is None:
        return None
    for i, c in enumerate(candidates or []):
        try:
            if int(c) == int(sel_value):
                return i
        except (TypeError, ValueError):
            continue
    return None


# ── 같은-포즈 기준 프레임 매칭 (faultzoom-same-frame-crops, belle 육안 #2) ─────────
# belle 2026-07-25: "시작점·길이 다른 건 이해하나 **최대한 비슷한 포즈를 캡처해서
# 비교**해야지." DTW window position 정렬(ea55069)은 **타이밍 대응**이지 **시각 포즈
# 대응**이 아니다 — DTW 는 관절각(방향 불변) 시퀀스 위에서 계산되므로 학생이 등을
# 돌린 순간과 정은지가 정면을 보는 순간이 같은 position 에 놓일 수 있다.
#
# 2026-07-26 실측(ref-elbow-twist-sister, 9fps 그리드 육안): 학생 프레임 70 에 시각적으로
# 맞는 기준 프레임은 68 인데 DTW 짝은 73 이었다. 둘의 간격 5프레임(≈0.55s)은 종전 후보
# window(±2)를 완전히 벗어나므로, window 안에서 재선택하는 것만으로는 도달 자체가 불가.
# → 기준 후보를 DTW 짝 주변으로 **확대**하고 그 안에서 포즈 거리 최소를 고른다.
#
# 전부 **display 전용, 채점 무접촉** — fault_zoom 은 complete 이후 사후 렌더라
# deductionBreakdown/veto/게이트에 어떤 값도 되돌리지 않는다 (D-20).

# 기준 프레임 탐색 반경(초). DTW 짝을 중심으로 ±이 값 안에서만 고른다 — DTW 를
# 타이밍 backbone 으로 남기고 시각 대응만 국소 보정하는 취지(전 구간 탐색은 동작의
# 다른 국면에서 우연히 닮은 프레임을 집어올 위험). 실측 어긋남 0.55s 의 약 2배 마진.
# 초 단위로 두어 frames_fps 가 바뀌어도 의미가 보존된다.
_POSE_SEARCH_SECONDS = 1.2

# 포즈 거리 계산에 필요한 최소 공통 신뢰관절 수. 3점 이하면 이동/스케일 정규화 후
# 남는 자유도가 거의 없어 거리값이 의미를 잃는다(역립 구간 keypoint 붕괴 시 2~3개만
# 살아남는 경우가 흔함 — 그 노이즈로 프레임을 옮기면 오히려 악화).
# 2026-07-27 부터 **기저 크기 게이트**로도 재사용 — select_pose_matched_ref_frame 의
# 고정 기저(학생 신뢰관절)가 이 수 미만이면 탐색 자체를 안 한다(신규 튜닝상수 0).
_POSE_MIN_COMMON_JOINTS = 4

# 동률 판정 마진(상대). 최소 거리 대비 이 비율 안쪽은 "사실상 같은 정도로 닮음"으로
# 보고 그중 **DTW 짝에 가장 가까운** 프레임을 택한다 — 타이밍 대응을 근거 없이
# 버리지 않기 위한 tie-break (가중치 λ 튜닝 회피).
_POSE_TIE_MARGIN = 0.05


def _confident_pose(report: dict, kp_idx: int) -> dict[str, tuple[float, float]]:
    """(frame) 의 신뢰 keypoint 좌표 map — {joint: (x,y)}, 정규화 0..1 원본 그대로.

    게이트는 crop 앵커와 같은 _KP_CONF_MIN(0.5) 재사용 — 포즈 매칭 전용 신규 튜닝
    상수를 만들지 않는다. confidence 부재(legacy report)는 **불통과**: 신뢰를
    증명 못한 좌표로 기준 프레임을 옮기면 조용한 악화가 되므로, 그 경우 호출측이
    DTW 짝(종전 동작)으로 폴백하게 둔다.
    """
    out: dict[str, tuple[float, float]] = {}
    for joint in report.get("joints") or []:
        xy = _kp_xy(report, kp_idx, joint)
        if xy is None:
            continue
        c = _kp_conf(report, kp_idx, joint)
        if c is None or c < _KP_CONF_MIN:
            continue
        out[joint] = xy
    return out


def pose_distance(
    pose_a: dict[str, tuple[float, float]],
    pose_b: dict[str, tuple[float, float]],
    *,
    basis: Sequence[str] | None = None,
    weights: dict[str, float] | None = None,
) -> float | None:
    """두 포즈의 시각 거리 (순수). 낮을수록 같은 포즈. 계산 불가 → None.

    **공통 신뢰관절만** 써서 각자 centroid 이동 + RMS 반경 스케일 정규화 후
    관절당 L2 평균. 사람마다 체격/카메라 거리/화면 내 위치가 달라 원좌표 비교는
    무의미하므로 이동·스케일은 제거하고, **회전과 좌우 배치는 일부러 남긴다** —
    belle 이 지적한 "앞을 보는데 뒤돌아본 순간"(facing) 은 좌우 어깨/골반이 화면에서
    뒤집히는 것으로 나타나므로, 회전 정규화를 하면 바로 그 신호가 지워진다.

    토르소 4관절 고정 기준으로 정규화하지 않는 이유: 역립 구간에서 토르소 keypoint
    가 전부 살아있는 프레임이 20/70 뿐이라(2026-07-26 ref-elbow-twist-sister 실측)
    고정 기준을 쓰면 정작 필요한 구간에서 계산 자체가 안 선다.

    basis: 채점에 쓸 관절 집합을 **고정**한다. 양쪽 포즈가 이 관절을 전부 갖고 있을
      때만 값을 내고, 하나라도 없으면 None(= 그 후보는 채점 불가). None(default)이면
      두 포즈의 공통 관절을 자동 사용 — **단일 쌍 비교 전용**이다.

    weights: 관절별 기여 가중 (2026-07-27 게이트 재설계 — 학생 confidence). 주어지면
      centroid/스케일/평균이 전부 가중으로 바뀐다. **탐색 1회 안에서 반드시 동일한
      가중을 전 후보에 강제할 것** — 후보마다 가중이 다르면 basis 를 고정해도 값이
      서로 다른 공간에서 나와 비교불가 버그가 재발한다. 합 0/비유한 → None.
      None(default) = 비가중 (기존 산출 byte-보존 경로).

    ⚠ **여러 후보의 거리를 서로 비교(min 선택)할 때는 basis 를 반드시 고정할 것.**
    자동 공통관절 모드로 후보들을 줄세우면 후보마다 다른 관절 기저에서 나온 값을
    비교하게 되는데, 이동+스케일을 제거하고 남는 자유도가 관절 수에 비례하므로
    **관절이 적은 후보가 구조적으로 낮은 거리를 받아** 최소값 경쟁에서 부당하게
    이긴다(2026-07-27 실측: 랜덤 포즈 min 통계 k=4 → 0.185 vs k=8 → 0.486,
    ref-elbow-twist-sister 실 탐색에서 k=4 후보가 k=8 후보 전부를 이김). 극단적으로,
    후보가 학생의 부분집합 관절만 신뢰 가능하고 그게 닮음변환 사본이면 거리가
    ~0 이 되어 전신이 거의 일치하는 후보를 제친다.
    """
    if basis is None:
        common = sorted(set(pose_a) & set(pose_b))
    else:
        common = sorted(set(basis))
        if not set(common) <= (set(pose_a) & set(pose_b)):
            # 기저를 다 못 채우는 후보 = 비교 불가 → 탐색에서 제외(대체 관절로
            # 몰래 채점하면 바로 그 비교불가 버그가 된다).
            return None
    if len(common) < _POSE_MIN_COMMON_JOINTS:
        return None
    a = np.asarray([pose_a[j] for j in common], dtype=float)
    b = np.asarray([pose_b[j] for j in common], dtype=float)
    if not (np.isfinite(a).all() and np.isfinite(b).all()):
        return None
    if weights is not None:
        w = np.asarray([float(weights.get(j, 0.0)) for j in common], dtype=float)
        if not np.isfinite(w).all() or float(w.sum()) <= 1e-9 or (w < 0).any():
            return None
        wn = w / float(w.sum())
        a = a - (a * wn[:, None]).sum(axis=0)
        b = b - (b * wn[:, None]).sum(axis=0)
        sa = float(np.sqrt(float((wn * np.sum(a * a, axis=1)).sum())))
        sb = float(np.sqrt(float((wn * np.sum(b * b, axis=1)).sum())))
        if not (np.isfinite(sa) and np.isfinite(sb)) or sa <= 1e-9 or sb <= 1e-9:
            return None
        d = float((wn * np.linalg.norm(a / sa - b / sb, axis=1)).sum())
        return d if np.isfinite(d) else None
    a = a - a.mean(axis=0)
    b = b - b.mean(axis=0)
    sa = float(np.sqrt(np.mean(np.sum(a * a, axis=1))))
    sb = float(np.sqrt(np.mean(np.sum(b * b, axis=1))))
    if not (np.isfinite(sa) and np.isfinite(sb)) or sa <= 1e-9 or sb <= 1e-9:
        # 관절이 한 점에 뭉친 붕괴 프레임 — 정규화하면 0/0.
        return None
    d = float(np.mean(np.linalg.norm(a / sa - b / sb, axis=1)))
    return d if np.isfinite(d) else None


def select_pose_matched_ref_frame(
    user_report: dict,
    ref_report: dict,
    user_kp_idx: int,
    ref_anchor_idx: int,
    ref_n: int,
    *,
    frames_fps: float,
    ref_rep_fps: float,
    ref_rep_frames: int,
    search_seconds: float = _POSE_SEARCH_SECONDS,
) -> int | None:
    """학생 프레임과 **가장 닮은 포즈**의 기준 프레임 (9fps frames 인덱스) | None.

    ref_anchor_idx = DTW 짝 기준 프레임(9fps frames 공간). 그 주변 ±search_seconds
    안의 기준 프레임 전부에 대해 학생 포즈와의 pose_distance 를 재고 최소를 고른다.
    최소값 대비 _POSE_TIE_MARGIN 안쪽 후보가 여럿이면 **anchor 에 가장 가까운** 것
    (DTW 타이밍 존중). 판정 불가면 None → 호출측이 anchor(종전 동작) 유지.

    **매칭 신호 = finite 좌표 ∩ ref 이름공간, 가중 = 학생 confidence
    (2026-07-27 게이트 재설계)**. 종전 conf>=0.5 게이트는 실 fixture 에서 전 카드
    무발동이었다 — (a) 역립 구간 학생 신뢰관절 2~3개 < 4, (b) user report 12관절 vs
    ref report 8관절 이름공간 불일치로 기저(ankle/elbow 포함)를 ref 가 구조적으로
    못 덮음. 재설계: 기저 = 학생 프레임의 **finite 좌표** 관절 ∩ **ref report 가
    가진 관절 이름** ∩ conf>0, 가중치 = 학생 confidence 그대로(저신뢰 좌표도 신호로
    쓰되 기여를 신뢰도만큼 할인 — 신규 튜닝상수 0, conf 값 = 데이터). Pod A/B 실측
    (elbow-twist-sister 실 keypoint): 3카드 전부 발동, knee 승자가 육안 GT 국면
    (웅크린 역립+등돌림)과 일치, 오답 anchor 는 최하위권. 학생 report 에 confidence
    배열이 없으면(legacy) 가중을 세울 수 없어 종전대로 None → anchor 유지.

    **관절 기저·가중 고정 (비교불가 BLOCKER fix 유지)**: 탐색 1회 안의 모든 후보를
    동일 기저 + 동일 가중(학생측)으로 채점한다. 후보마다 자기 교집합/자기 가중으로
    채점하면 값이 서로 다른 공간에서 나와 관절 적은 후보가 최소값 경쟁에서 구조적으로
    이긴다(실측: pose_distance docstring). 기저를 못 덮는 후보는 채점 불가로 제외.
    기저 크기 게이트는 기존 _POSE_MIN_COMMON_JOINTS(4) 재사용. ref 측 confidence 는
    매칭에 쓰지 않는다 — 역립 구간 ref conf 붕괴(0~8 요동 실측)로 게이트하면 무발동
    재발하고, ref 좌표가 garbage 면 거리가 커져 스스로 탈락한다(자기배제).

    탐색 상한은 ref_n(비디오 배열)과 **rep 공간 길이** 중 작은 쪽 — ref 타임베이스
    불일치(rep 18.3s vs video 24.4s 실측) 시 rep 밖 인덱스는 _to_rep_idx clamp 로
    마지막 rep 프레임을 중복 채점하게 되므로 자른다.

    반환이 anchor 와 같을 수 있다(그게 실제 최적일 때). 표시 전용, 채점 무접촉.
    """
    if ref_n <= 0:
        return None
    ref_names = set(ref_report.get("joints") or [])
    user_pose: dict[str, tuple[float, float]] = {}
    weights: dict[str, float] = {}
    for joint in user_report.get("joints") or []:
        if joint not in ref_names:
            continue
        xy = _kp_xy(user_report, user_kp_idx, joint)
        if xy is None:
            continue
        c = _kp_conf(user_report, user_kp_idx, joint)
        if c is None or c <= 0.0:
            # conf 부재(legacy report) 포함 — 신뢰도 신호가 없는 좌표로는 기준
            # 프레임을 옮기지 않는다(조용한 악화 방지, 종전 보수성 유지).
            continue
        user_pose[joint] = xy
        weights[joint] = float(c)
    if len(user_pose) < _POSE_MIN_COMMON_JOINTS:
        return None
    # 기저 + 가중 = 학생 프레임에서 1회 고정 (탐색 내내 불변). 모든 후보가 동일
    # 관절·동일 가중으로 채점되어 "최소 거리 승자" 비교가 like-for-like 로 성립.
    basis = sorted(user_pose)
    rep9_n = int(round(
        int(ref_rep_frames) * float(frames_fps) / max(1e-6, float(ref_rep_fps))
    ))
    hi_bound = min(int(ref_n), rep9_n) if rep9_n > 0 else int(ref_n)
    span = int(round(max(0.0, float(search_seconds)) * max(1e-6, float(frames_fps))))
    lo = max(0, int(ref_anchor_idx) - span)
    hi = min(hi_bound - 1, int(ref_anchor_idx) + span)
    scored: list[tuple[float, int]] = []
    for r in range(lo, hi + 1):
        r_kp = _to_rep_idx(r, frames_fps, ref_rep_fps, ref_rep_frames)
        cand = {
            j: xy
            for j in basis
            if (xy := _kp_xy(ref_report, r_kp, j)) is not None
        }
        d = pose_distance(user_pose, cand, basis=basis, weights=weights)
        if d is not None:
            scored.append((d, r))
    if not scored:
        return None
    best = min(d for d, _r in scored)
    tie = best * (1.0 + _POSE_TIE_MARGIN)
    near = [r for d, r in scored if d <= tie]
    return min(near, key=lambda r: (abs(r - int(ref_anchor_idx)), r))


def ref_display_frame_index(
    r9_idx: int,
    ref_video_n: int,
    ref_rep_frames: int,
    ref_rep_fps: float,
    frames_fps: float = 9.0,
) -> int:
    """rep(각도/keypointReport) 9fps 인덱스 → ref **비디오 프레임 배열** 인덱스 (순수).

    **ref 타임베이스 불일치 fix (2026-07-27, faultzoom-same-frame-crops)**. 실측
    (ref-elbow-twist-sister): referenceKeypointReport = 329프레임@18fps(콘텐츠 18.3s,
    raw 매 2프레임 샘플)인데 렌더러의 frame_extractor 는 같은 영상에서 PTS 9fps 로
    220프레임(24.4s)을 뽑는다. 종전 렌더는 rep 공간 인덱스로 비디오 배열을 직접
    인덱싱해 **모든 ref 크롭이 자기 시점의 3/4 지점(결함 창 기준 ≈2.7s 이른 순간)**
    을 보여줬다 — belle "정은지 쪽은 아예 다른 장면"의 근본원인. Pod 에서 출하 RTMW
    를 비디오 프레임에 돌려 rep↔video 대응을 실측한 결과 t_vid = (4/3)·t_rep,
    오프셋 0 (양 끝점 정확) — 즉 두 시퀀스는 같은 콘텐츠를 다른 샘플링 밀도로 덮고
    있어 **길이 비례 선형 매핑**이 성립한다.

    매핑 = round(r9_idx × ref_video_n / rep9_n), rep9_n = rep_frames·frames_fps/rep_fps.
    rep 과 비디오가 정합(학생측 in-run report, mode3 지난영상, 올바른 재처리 ref)이면
    rep9_n == ref_video_n → 배율 1.0 → **identity(byte-동일)**. rep 메타 부재(legacy)
    → identity 폴백. 데이터에서 유도되는 자기보정 — 신규 튜닝상수 0. 표시 전용,
    채점 무접촉 (keypoint 좌표/refFrameIdx 는 rep 공간 그대로 — 뷰어 계약 불변).
    """
    if ref_video_n <= 0:
        return 0
    idx = max(0, min(int(r9_idx), ref_video_n - 1))
    if ref_rep_frames <= 0 or ref_rep_fps <= 0 or frames_fps <= 0:
        return idx
    rep9_n = int(ref_rep_frames) * float(frames_fps) / float(ref_rep_fps)
    if rep9_n <= 0:
        return idx
    scale = float(ref_video_n) / rep9_n
    return max(0, min(int(round(int(r9_idx) * scale)), ref_video_n - 1))


def _frame_index(seconds: float | None, fps: float, n_frames: int) -> int:
    """worst-pose 초 → 프레임 인덱스 (clamp). seconds None → 중앙 프레임."""
    if n_frames <= 0:
        return 0
    if seconds is None or fps <= 0:
        return n_frames // 2
    idx = int(round(seconds * fps))
    return max(0, min(idx, n_frames - 1))


def _matched_ref_frame(dtw_match, user_frame: int, ref_n: int) -> int | None:
    """B1 — DTW match 로 학생 프레임 ↔ 기준 프레임(같은 pose). None=불가.

    match.start = 사용자 구간 시작(angles 9fps), path = [(user_local, ref_idx)...].
    ref_idx = 기준 angles 인덱스 — **ref doc 의 keypointReport.fps 공간**(phase4_v1
    재처리 18fps, 28-01 실측). 반환도 이 angles(rep) 인덱스 공간이다. 호출측이
    clamp 상한(ref_n)과 9fps frames 배열로의 변환을 도메인에 맞게 책임진다
    (28-RESEARCH Pitfall 1, D2 fix — angles 인덱스를 9fps frames 에 그대로 넣으면
    시간 2배 오독). 학생 프레임을 구간-로컬로 변환 후 path 에서 같은 user_local 의
    ref_idx 들의 median 을 고른다(DTW 1:N 대응 안정화).

    **본체 수정 금지** — veto still 경로(app.py `_build_selected_frame_pair`)가 이
    함수를 공유하며 그쪽 입력이 바뀌면 점수가 움직인다 (28-RESEARCH Open Q2).
    """
    if dtw_match is None:
        return None
    try:
        start = int(getattr(dtw_match, "start", 0))
        path = getattr(dtw_match, "path", None) or []
    except Exception:  # noqa: BLE001 - match 형태 이상 시 graceful (proportional 폴백)
        return None
    local = user_frame - start
    js = sorted(j for (i, j) in path if i == local)
    if not js:
        return None
    return max(0, min(int(js[len(js) // 2]), ref_n - 1))


def _kp_xy(report: dict, frame_idx: int, joint: str) -> tuple[float, float] | None:
    """keypointReport(flat data) 의 frame_idx, joint 정규화 좌표 (x,y) | None.

    data layout = T * J * 2. joint 은 report['joints'] 의 이름.
    """
    joints = report.get("joints") or []
    if joint not in joints:
        return None
    j = joints.index(joint)
    nj = len(joints)
    data = report.get("data") or []
    frames = int(report.get("frames") or 0)
    if frames <= 0 or len(data) < frames * nj * 2:
        return None
    fi = max(0, min(frame_idx, frames - 1))
    base = (fi * nj + j) * 2
    x = float(data[base])
    y = float(data[base + 1])
    if not (np.isfinite(x) and np.isfinite(y)):
        return None
    return x, y


def _kp_conf(report: dict, frame_idx: int, joint: str) -> float | None:
    """keypointReport 의 (frame, joint) confidence. 부재/legacy → None (통과 취급).

    confidence 는 flat T*J (keypoint_frame.py KeypointReport). 길이가 frames*nj
    미만이면 부재 취급 (legacy/합성 report 하위호환).
    """
    joints = report.get("joints") or []
    if joint not in joints:
        return None
    j = joints.index(joint)
    nj = len(joints)
    conf = report.get("confidence") or []
    frames = int(report.get("frames") or 0)
    if frames <= 0 or len(conf) < frames * nj:
        return None
    fi = max(0, min(frame_idx, frames - 1))
    try:
        c = float(conf[fi * nj + j])
    except (TypeError, ValueError):
        return None
    return c if np.isfinite(c) else None


def _gated_kp(
    report: dict, frame_idx: int, joint: str
) -> tuple[float, float] | None:
    """좌표 finite AND 명시적 고신뢰(conf >= _KP_CONF_MIN)만 통과 (quick-260705-r6x).

    사이각 드로잉 전용 게이트 — crop 게이트(_member_pts, conf 부재=통과)보다
    엄격하다. confidence 부재(legacy report)도 불허: 2026-07-05 pod 실측(belle
    PNG 육안)에서 confidence 없는 reference report 가 통과해 몸과 무관한 방향으로
    선이 폭주했다 — 선/호는 확정적 시각 언어라 신뢰가 증명된 좌표에서만 그린다.
    저신뢰/미증명 → None (호출측 기존 렌더 폴백). 표시 전용, 채점 무접촉.
    """
    xy = _kp_xy(report, frame_idx, joint)
    if xy is None:
        return None
    c = _kp_conf(report, frame_idx, joint)
    if c is None or c < _KP_CONF_MIN:
        return None
    return xy


def _leg_line_pts(
    report: dict, frame_idx: int
) -> tuple[
    tuple[float, float], tuple[float, float], tuple[float, float]
] | None:
    """스플릿 사이각 드로잉용 3점(정규화): (골반 중점, 왼 다리 끝, 오른 다리 끝).

    belle 2026-07-05 실기기: "다리에 동그라미가 아니라 다리와 다리 사이각을 표시".
      · 골반 중점 = left_hip/right_hip 중점 — 양쪽 모두 게이트 통과 필수.
      · 다리 끝 = ankle 우선, 저신뢰/결측 시 knee 폴백 (측별 독립).
      · 셋 중 하나라도 해석 불가 → None (호출측 기존 렌더 폴백).
    fault_joints(결함 관절 목록)와 무관하게 report 에서 직접 조회한다 — 드로잉
    좌표는 결함 목록이 아니라 실제 관절 위치를 따른다 (fault_joints 에 knee 만
    있어도 hips 가 report 에 valid 하면 그린다).
    """
    lh = _gated_kp(report, frame_idx, "left_hip")
    rh = _gated_kp(report, frame_idx, "right_hip")
    if lh is None or rh is None:
        return None
    pelvis = ((lh[0] + rh[0]) / 2.0, (lh[1] + rh[1]) / 2.0)
    left_end = _gated_kp(report, frame_idx, "left_ankle") or _gated_kp(
        report, frame_idx, "left_knee"
    )
    right_end = _gated_kp(report, frame_idx, "right_ankle") or _gated_kp(
        report, frame_idx, "right_knee"
    )
    if left_end is None or right_end is None:
        return None
    return pelvis, left_end, right_end


def _crop_box(
    h: int, w: int, cx: float, cy: float, side: int | None = None
) -> tuple[int, int, int]:
    """정규화 중심 (cx,cy) 의 정사각 crop 박스 (left, top, side_px) — 순수 기하.

    side None 이면 min(H,W)*_CROP_FRAC (기존 단일 관절 zoom). 경계를 넘으면
    안쪽으로 shift (검은 패딩 회피) + 프레임 내 clamp (T-25-07 — NaN 은 상류
    finite 검사에서 이미 차단, 범위밖 좌표는 여기서 clamp).
    """
    if side is None:
        side = max(16, int(round(min(h, w) * _CROP_FRAC)))
    side = max(16, min(int(side), min(h, w)))
    px, py = cx * w, cy * h
    left = int(round(px - side / 2))
    top = int(round(py - side / 2))
    left = max(0, min(left, w - side)) if w >= side else 0
    top = max(0, min(top, h - side)) if h >= side else 0
    return left, top, side


def _render_crop(frame: np.ndarray, left: int, top: int, side: int) -> Image.Image:
    """crop 박스를 잘라 (_OUT,_OUT) 으로 리사이즈."""
    h, w = frame.shape[0], frame.shape[1]
    crop = frame[top:min(h, top + side), left:min(w, left + side)]
    return Image.fromarray(crop).convert("RGB").resize((_OUT, _OUT), Image.BILINEAR)


def _full_frame_fit(frame: np.ndarray) -> Image.Image:
    """full frame 을 비율 유지 contain-fit 으로 (_OUT,_OUT) 흰 캔버스에 배치.

    crop 앵커 keypoint 가 전부 결측/저신뢰인 측의 전신 폴백 — 엉뚱한 부위 확대보다
    전신이 낫다 (quick-260702-sic, belle 요구 3).
    """
    img = Image.fromarray(frame).convert("RGB")
    w, h = img.size
    scale = _OUT / max(1, max(w, h))
    nw = max(1, int(round(w * scale)))
    nh = max(1, int(round(h * scale)))
    resized = img.resize((nw, nh), Image.BILINEAR)
    canvas = Image.new("RGB", (_OUT, _OUT), (255, 255, 255))
    canvas.paste(resized, ((_OUT - nw) // 2, (_OUT - nh) // 2))
    return canvas


def _member_pts(
    report: dict, frame_idx: int, members: tuple[str, ...]
) -> tuple[
    list[tuple[str, tuple[float, float]]], list[tuple[float, float]]
]:
    """unit 멤버 keypoint 를 (valid, relaxed) 로 분류.

    valid = 좌표 finite AND (confidence 부재 → 통과 | confidence >= _KP_CONF_MIN)
    — (관절명, 좌표) 쌍 (앵커 대표 관절 선택에 관절명 필요, Phase 25-03 Task 2).
    저신뢰 keypoint 를 crop 앵커로 쓰면 엉뚱한 부위가 확대됨 (quick-260702-sic).
    relaxed = 좌표 finite 이지만 confidence < _KP_CONF_MIN — 완화 crop 후보.
    좌표 자체 결측(NaN/부재)은 어느 쪽에도 안 들어감 (전신 폴백 대상).
    """
    valid: list[tuple[str, tuple[float, float]]] = []
    relaxed: list[tuple[float, float]] = []
    for m in members:
        xy = _kp_xy(report, frame_idx, m)
        if xy is None:
            continue
        c = _kp_conf(report, frame_idx, m)
        if c is not None and c < _KP_CONF_MIN:
            relaxed.append(xy)
        else:
            valid.append((m, xy))
    return valid, relaxed


def _anchor_xy(
    valid: list[tuple[str, tuple[float, float]]],
    deltas: dict[str, float] | None,
) -> tuple[float, float]:
    """앵커(대표) 관절의 정규화 좌표 — deficit(|delta|) 최대 valid 멤버.

    delta 없는/비유한 멤버는 후보 제외, 전원 delta 부재면 첫 valid 멤버
    (fault_joints 순서 보존). grouped(2관절+) 카드의 circle 1개 대상 선정.
    """
    best_xy = valid[0][1]
    best_mag = -1.0
    for name, xy in valid:
        d = (deltas or {}).get(name)
        try:
            mag = abs(float(d))
        except (TypeError, ValueError):
            continue
        if np.isfinite(mag) and mag > best_mag:
            best_mag, best_xy = mag, xy
    return best_xy


def _to_crop_px(
    xy: tuple[float, float],
    left: int,
    top: int,
    side: int,
    w: int,
    h: int,
) -> tuple[int, int]:
    """정규화 좌표 → crop 박스(left,top,side) 내 출력 픽셀 변환 단일 출처 (quick-260705-r6x).

    _side_crop 의 anchor_px 산출과 _draw_leg_angle 의 선/호 좌표가 같은 공식을
    공유한다 (중복 금지). [0,_OUT-1] clamp — 캔버스 밖 좌표 방어.
    """
    s = max(1, int(side))
    ax = int(round((xy[0] * w - left) / s * _OUT))
    ay = int(round((xy[1] * h - top) / s * _OUT))
    return max(0, min(_OUT - 1, ax)), max(0, min(_OUT - 1, ay))


def _pt_in_crop(
    xy: tuple[float, float],
    left: int,
    top: int,
    side: int,
    w: int,
    h: int,
    margin: float = _CROP_INCLUSION_MARGIN_PX,
) -> bool:
    """xy(정규화)의 crop-내 raw 픽셀(clamp 전)이 [−margin, _OUT+margin] 안인가.

    _to_crop_px 는 [0,_OUT-1] 로 clamp 하므로 crop 밖 점도 경계로 접힌다 — 포함
    판정은 반드시 clamp 전 좌표로(quick-260705-r6x pod fix). 사이각 선 시작/끝점이
    crop 밖이면 선이 경계로 폭주하므로 그 측 드로잉을 생략하는 데 쓴다.
    """
    s = max(1, int(side))
    ax = (xy[0] * w - left) / s * _OUT
    ay = (xy[1] * h - top) / s * _OUT
    lo = -float(margin)
    hi = _OUT + float(margin)
    return lo <= ax <= hi and lo <= ay <= hi


def _side_crop(
    frame: np.ndarray,
    valid_pts: list[tuple[float, float]],
    relaxed_pts: list[tuple[float, float]],
    anchor: tuple[float, float] | None = None,
) -> tuple[
    Image.Image, str, tuple[int, int] | None, tuple[int, int, int] | None
]:
    """한 측(user/ref)의 unit crop 3단 강하 → (이미지, crop_kind, anchor_px, box).

    crop_kind ∈ {"valid", "relaxed", "full"} — _mark 가 앵커 표시 여부 결정.
    anchor_px = anchor(결함 관절 정규화 좌표)의 crop-내 출력 픽셀 좌표 — valid
    crop 에서만 산출 (circle 을 crop 중심이 아닌 관절 좌표에 고정, Task 2).
    relaxed/full 은 좌표 불확실이라 None (앵커 생략 = 오인 방지).
    box = 이 crop 이 쓴 프레임 좌표계 (left, top, side) — 사이각 선/호 좌표 변환용
    (quick-260705-r6x). full 폴백은 crop 박스가 없어 None. 기존 호출측은 [0]/[:2]/
    [2] 인덱싱이라 4번째 원소 추가는 하위호환.

    (1) valid(신뢰 좌표) 있음 → 기존 로직 그대로: 1개=단일 관절 zoom, 2개 이상
        (grouped)=멤버 bounding box crop (변 = max(bbox)*_BBOX_MARGIN,
        floor=_CROP_FRAC 줌 수준, 상한=프레임 내).
    (2) valid 0개, 저신뢰-유한 좌표 있음 → 완화(relaxed) crop: 그 좌표 중심,
        변 = max(floor, bbox*_BBOX_MARGIN*_RELAXED_MARGIN) — margin 은 bbox
        파생분에만, floor(기본 줌)는 그대로 (display 전용, 채점 무접촉).
        reference 저신뢰 전신 폴백이 카드마다 동일 전신 반복 → 부위-중심 완화
        crop 으로 카드별 차별화 (Phase 25 동반 스코프, belle 2026-07-04 실기기).
        오인 방지는 앵커 생략으로 유지 (260702-sic 요구 3).
    (3) 좌표 자체 결측 → 기존 _full_frame_fit 전신 폴백.

    촬영거리 불일치는 bbox 가 측별 person 스케일을 따라가며 자연 해소.
    """
    h, w = frame.shape[0], frame.shape[1]

    def _box_for(pts: list[tuple[float, float]], margin: float):
        xs = [p[0] * w for p in pts]
        ys = [p[1] * h for p in pts]
        cx = (min(xs) + max(xs)) / 2 / w
        cy = (min(ys) + max(ys)) / 2 / h
        # margin 은 bbox 파생분에만 곱한다 (quick-260705-ftn) — floor 에도 곱하면
        # 밀집/단일 relaxed 좌표의 side 가 프레임 전폭에 클램프돼 전신처럼 보임
        # (2026-07-05 pod 재현). valid 경로는 margin=1.0 이라 산출 무변경.
        floor_side = int(round(min(h, w) * _CROP_FRAC))
        side = floor_side
        if len(pts) > 1:
            bbox_side = max(max(xs) - min(xs), max(ys) - min(ys))
            side = max(floor_side, int(round(bbox_side * _BBOX_MARGIN * margin)))
        # 확대 후에도 _crop_box 가 프레임 경계로 clamp (T-25-07).
        return _crop_box(h, w, cx, cy, side)

    if valid_pts:
        left, top, s = _box_for(valid_pts, 1.0)
        anchor_px: tuple[int, int] | None = None
        if anchor is not None:
            anchor_px = _to_crop_px(anchor, left, top, s, w, h)
        return _render_crop(frame, left, top, s), "valid", anchor_px, (
            left, top, s,
        )
    if relaxed_pts:
        # D-20 (32-CONTEXT): 프레이밍은 valid 와 동일 배율(margin=1.0 → bbox*1.8)로 통일 —
        # relaxed 가 2배 넓어 정은지 crop 이 비교와 안 맞던 문제 해소. 마커는 민감하므로
        # crop_kind="relaxed" 유지 → anchor_px=None 생략 게이트는 현행대로(프레이밍/마커 분리).
        left, top, s = _box_for(relaxed_pts, 1.0)
        return _render_crop(frame, left, top, s), "relaxed", None, (
            left, top, s,
        )
    return _full_frame_fit(frame), "full", None, None


def _deficit_label(deficit_deg: float) -> str:
    """deficit 배지 라벨 포맷 (quick-260704-fz4 후속) — "40°" (숫자 + 도 기호).

    구 "40deg" 원어 표기 교체 (belle 실기기 피드백). U+00B0 도 기호는 PIL 기본
    폰트(Pillow 12 load_default) 글리프 보유 확인 완료 (getmask 4x8 + 렌더 픽셀
    검증) — "한글 글리프 부재" 제약(모듈 docstring)과 무관, latin-1 범위라 안전.
    """
    return f"{int(round(deficit_deg))}°"


def _mark(
    img: Image.Image,
    deficit_deg: float | None,
    circle: bool = True,
    anchor_px: tuple[int, int] | None = None,
) -> Image.Image:
    """브랜드 원 + (deficit 있으면) 숫자 배지. 한글 없음(폰트 회피).

    circle 중심 = anchor_px(결함 관절의 crop-내 좌표, Phase 25-03 Task 2 —
    grouped bbox crop 에서 관절이 중심을 벗어나도 원이 관절을 가리킴). anchor_px
    None 이면 기존 crop 중앙 (하위호환).
    circle=False = relaxed/전신 폴백 측 (좌표 불확실/중앙 비결함 — 원 생략,
    오인 방지). deficit 배지는 유지. 라벨 포맷 = _deficit_label ("40°") —
    confirmed/advisory 양 배치가 본 함수를 공유하므로 동일 적용.
    """
    draw = ImageDraw.Draw(img)
    if circle:
        cx, cy = anchor_px if anchor_px is not None else (_OUT // 2, _OUT // 2)
        r = int(_OUT * 0.16)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=_BRAND, width=4)
    if deficit_deg is not None and deficit_deg > 0:
        txt = _deficit_label(deficit_deg)
        # 배지 배경 (가독성) — 우상단. 폭 추정 = 글자당 8px 상한 유지
        # (° 글리프는 4px 로 더 좁음 — 여유폭, 잘림 없음).
        tw = 8 * len(txt) + 10
        draw.rectangle([_OUT - tw - 8, 8, _OUT - 8, 34], fill=_BRAND)
        draw.text((_OUT - tw - 2, 13), txt, fill=(255, 255, 255))
    return img


def _draw_leg_angle(
    img: Image.Image,
    pelvis_px: tuple[int, int],
    left_px: tuple[int, int],
    right_px: tuple[int, int],
    angle_deg: float | None,
) -> bool:
    """골반 중점→양 다리 선 2개 + 사이각 호(arc) + (있으면) 각도 수치 (in-place).

    belle 2026-07-05 실기기: 스플릿 결함의 본질 = 두 다리 벌림 각도. 앵커 동그라미
    대신 사이각을 직접 그려 호 크기 차이가 곧 결함으로 보이게 한다. 성공 여부를
    반환 — display 전용, 채점 무접촉. 한글 없음(선/호/숫자만, 모듈 docstring 정합).
    """
    px, py = pelvis_px
    lx, ly = left_px
    rx, ry = right_px
    # 겹친 좌표(벡터 길이 < _MIN_LEG_VEC_PX)는 그리면 오히려 오인 → 드로잉 생략.
    if (
        math.hypot(lx - px, ly - py) < _MIN_LEG_VEC_PX
        or math.hypot(rx - px, ry - py) < _MIN_LEG_VEC_PX
    ):
        return False
    draw = ImageDraw.Draw(img)
    draw.line([pelvis_px, left_px], fill=_BRAND, width=4)
    draw.line([pelvis_px, right_px], fill=_BRAND, width=4)
    r = int(_OUT * 0.14)
    # 이미지 좌표(y down)의 atan2 와 PIL arc(3시 기준 시계방향)가 정합.
    a_left = math.degrees(math.atan2(ly - py, lx - px))
    a_right = math.degrees(math.atan2(ry - py, rx - px))
    a1, a2 = a_left, a_right
    if (a2 - a1) % 360 > 180:  # 두 선 사이 minor arc 만 그린다.
        a1, a2 = a2, a1
    draw.arc(
        [px - r, py - r, px + r, py + r], start=a1, end=a2, fill=_BRAND, width=3
    )
    if angle_deg is not None and np.isfinite(angle_deg):
        txt = _deficit_label(float(angle_deg))
        # 호 이등분 방향 반지름 r+12 지점에 배지 (기존 _mark 배지 스타일 재사용,
        # 폭 추정 8px/글자 동일).
        mid = math.radians(a1 + ((a2 - a1) % 360) / 2.0)
        label_r = r + 12
        mx = px + label_r * math.cos(mid)
        my = py + label_r * math.sin(mid)
        tw = 8 * len(txt) + 10
        th = 22
        x0 = int(round(mx - tw / 2.0))
        y0 = int(round(my - th / 2.0))
        draw.rectangle([x0, y0, x0 + tw, y0 + th], fill=_BRAND)
        draw.text((x0 + 5, y0 + 5), txt, fill=(255, 255, 255))
    return True


def _draw_side_leg_angle(
    img: Image.Image,
    frame: np.ndarray,
    report: dict,
    kp_idx: int,
    box: tuple[int, int, int],
    angle_deg: float | None,
) -> bool:
    """한 측 crop 에 다리 사이각을 그린다 (quick-260705-r6x) — 성공 여부 반환.

    _leg_line_pts 3점(정규화) → _to_crop_px 로 crop-내 픽셀 → _draw_leg_angle.
    pts 해석 불가/degenerate → False (호출측 기존 렌더 폴백). box = _side_crop 이
    반환한 (left, top, side) — crop 이 쓴 그 프레임 좌표계.

    crop-포함 게이트(quick-260705-r6x pod fix): 3점 중 하나라도 crop 박스 밖이면
    (_to_crop_px clamp 로 선이 경계로 폭주 — 2026-07-05 정은지 ref 측 실측) 드로잉
    생략하고 기존 crop 폴백. conf 게이트(_gated_kp)와 AND — 신뢰 좌표라도 그 측
    crop 이 관절을 안 담으면 그리지 않는다.
    """
    pts = _leg_line_pts(report, kp_idx)
    if pts is None:
        return False
    h, w = frame.shape[0], frame.shape[1]
    left, top, side = box
    if not all(_pt_in_crop(p, left, top, side, w, h) for p in pts):
        return False
    pelvis_px = _to_crop_px(pts[0], left, top, side, w, h)
    left_px = _to_crop_px(pts[1], left, top, side, w, h)
    right_px = _to_crop_px(pts[2], left, top, side, w, h)
    return _draw_leg_angle(img, pelvis_px, left_px, right_px, angle_deg)


def split_angle_degs_from_records(
    records,
) -> tuple[float | None, float | None] | None:
    """deductionBreakdown.records 에서 스플릿 사이각 수치 추출 (순수, boto3 무관).

    수치 출처 = 점수가 쓴 그 record — 측정-표시 정합
    ([[scoring-must-be-transparent-deduction-tally]]). 단 벌림각(사이각) semantics
    를 가진 record 만 표기한다 (2026-07-05 belle pod PNG 검증 fix):

      · deviationSource=='ipsf_absolute' 만 수용 — measuredValue = 추정 학생
        벌림각(180 − deficit)이라 호 옆 각도로 정직. 기준 측은 baselineValue(180)
        가 IPSF 목표치이지 정은지 실측 벌림각이 아니므로 **항상 생략(None)** —
        미측정 수치를 정은지 몸 옆에 붙이면 오인.
      · deviationSource=='reference_relative'(현행 split_vs_reference 규칙,
        vision-주입 kip-up 경로 포함)는 measuredValue = 정은지-대비 편차(예: 50)
        라 벌림각이 아님 — 표기하면 "벌림각 50°"로 오독(실측 재현된 결함).
        전체 None (선+호만, 수치 생략).

    반환 = (학생 벌림각, None) 또는 None. float 변환 실패/비유한 → None.
    records None/비리스트 graceful.
    """
    if not isinstance(records, list):
        return None

    def _finite(v):
        try:
            x = float(v)
        except (TypeError, ValueError):
            return None
        return x if np.isfinite(x) else None

    for rec in records:
        if not isinstance(rec, dict):
            continue
        if rec.get("criterion") != "split_angle" or rec.get("unit") != "deg":
            continue
        if rec.get("deviationSource") != "ipsf_absolute":
            # reference_relative(편차 semantics)/미상 출처 — 벌림각 아님, 수치 생략.
            return None
        student = _finite(rec.get("measuredValue"))
        if student is None:
            return None
        return student, None
    return None


def has_split_angle_record(records) -> bool:
    """records 에 스플릿 사이각 criterion 이 하나라도 있는지 (순수, boto3 무관).

    수치 추출(split_angle_degs_from_records)과 존재 판정을 분리하는 이유 — kip-up
    경로의 reference_relative split record 는 measuredValue 가 정은지-대비 편차라
    벌림각 수치는 생략(None)하지만, "다리가 벌어졌다"는 사이각 자체는 의미가 있어
    선+호는 그려야 한다 (2026-07-05 belle pod 전동작 검증). 그래서 존재 판정(이
    함수)으로 legs 사이각 게이트를 열고, 수치는 별도로 붙인다:
      · reference_relative split record → True (선+호, 수치 None)
      · ipsf_absolute split record → True (선+호+수치)
      · line-only / split 없음 / unit!='deg' → False
      · None / 비리스트 / 빈 리스트 → False (graceful)
    """
    if not isinstance(records, list):
        return False
    for rec in records:
        if not isinstance(rec, dict):
            continue
        if rec.get("criterion") == "split_angle" and rec.get("unit") == "deg":
            return True
    return False


def _compose(user_crop: Image.Image, ref_crop: Image.Image) -> bytes:
    """[user | ref] 가로 합성 → PNG bytes. 가운데 흰 구분선."""
    gap = 6
    canvas = Image.new("RGB", (_OUT * 2 + gap, _OUT), (255, 255, 255))
    canvas.paste(user_crop, (0, 0))
    canvas.paste(ref_crop, (_OUT + gap, 0))
    buf = io.BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# ─────────── D-11 목표 각도 화살표 (Phase 31-03, 리뷰 B-02 / 2차 H2-03) ───────────
#
# 화살표가 답해야 하는 것은 "어디까지 올려야 하는가"이고, 그 답의 유일한 출처는
# **DTW 로 대응된 reference 프레임의 실제 관절 좌표**다. 감점 record 의 수치 필드로
# 화면 기하를 만들면 안 되는 이유 (리뷰 B-02):
#   · reference_relative record 의 measuredValue 는 학생의 절대 관절각이 아니라
#     정은지-대비 편차다 (split_angle_degs_from_records 의 동일 함정 참조).
#   · baselineValue 는 IPSF 목표치(180 등)이지 이 프레임의 목표 좌표가 아니다.
#   · direction 어휘('over_target')는 방향 부호일 뿐 화면 벡터가 아니다.
# 그래서 _build_arrow_spec 은 DeductionRecord 를 인자로 받지 않는다 (테스트가 시그니처
# 로 고정). record 는 CorrectedPoseTarget 의 후보 우선순위에만 쓴다.

# 화살표 최소 이동량(crop 출력 px) — **display 전용, 채점 무접촉**.
# 목표 endpoint 가 현재 distal 과 이만큼도 안 떨어지면 화살표가 점처럼 뭉쳐 방향을
# 못 읽는다 → 생략(negligible_delta). _MIN_LEG_VEC_PX 선례와 같은 성격의 표시 상수.
_MIN_ARROW_DELTA_PX = 12

# parity 판정용 좌우 최소 분리(정규화) — **display 전용, 채점 무접촉**.
# 어깨/힙의 수평 분리가 이보다 작으면 정면·측면 경계라 좌우 방향 부호가 노이즈다
# → 판정 불가('unknown') → 화살표 생략 (H2-03: 불확실하면 지시하지 않는다).
_MIN_PARITY_SEP = 0.02

# 세그먼트 degenerate 임계(frame px) — proximal↔vertex 가 겹치면 정합 변환이 정의되지
# 않는다 (0 으로 나눔). _MIN_LEG_VEC_PX 와 같은 취지의 드로잉 가드.
_MIN_SEG_PX = 1.0

# parity 판정에 쓰는 topology keypoint — 어깨/힙 4점 (full-body, per-joint 아님).
_PARITY_KEYS = ("left_shoulder", "right_shoulder", "left_hip", "right_hip")

# 화살표를 그릴 수 있는 관절의 **명시 선언 매핑**: joint_key → (proximal, vertex, distal).
# 선언되지 않은 관절은 화살표도 correctedPose target 도 만들지 않는다 (리뷰 B-02
# omission 규칙 — renderer 가 추론으로 관절을 만들어내지 않는다). skeleton.JOINT_ANGLES
# 와 동일 3점 구성이지만 여기 선언이 렌더 계약의 단일 출처다 (어깨는 vertex 기하가
# 몸통-팔 혼합이라 v1 화살표 대상에서 제외).
ARROW_JOINT_MAP: dict[str, tuple[str, str, str]] = {
    "left_knee": ("left_hip", "left_knee", "left_ankle"),
    "right_knee": ("right_hip", "right_knee", "right_ankle"),
    "left_elbow": ("left_shoulder", "left_elbow", "left_wrist"),
    "right_elbow": ("right_shoulder", "right_elbow", "right_wrist"),
    "left_hip": ("left_shoulder", "left_hip", "left_knee"),
    "right_hip": ("right_shoulder", "right_hip", "right_knee"),
}


def joint_inner_angle_deg(
    proximal_xy: tuple[float, float],
    vertex_xy: tuple[float, float],
    distal_xy: tuple[float, float],
) -> float:
    """vertex 내각(도) — **각도 산출의 단일 출처** (3차 리뷰: 계산 이원화 금지).

    TargetArrowSpec 과 CorrectedPoseTarget.target_deg, 그리고 31-06 pose gate 가
    전부 이 함수를 import 한다. 같은 3점에서 서로 다른 각도가 나오면 "생성 지시"와
    "검증 기준"이 갈라져 잘못된 목표에 정확히 맞춘 이미지가 gate 를 통과한다.

    입력은 **등방(isotropic) 좌표계** — frame px 를 넣는다. 정규화 [0,1] 좌표를 그대로
    넣으면 W/H 비율만큼 각도가 왜곡된다. 겹친 좌표(degenerate)는 nan.
    """
    ax = float(proximal_xy[0]) - float(vertex_xy[0])
    ay = float(proximal_xy[1]) - float(vertex_xy[1])
    bx = float(distal_xy[0]) - float(vertex_xy[0])
    by = float(distal_xy[1]) - float(vertex_xy[1])
    na = math.hypot(ax, ay)
    nb = math.hypot(bx, by)
    if na <= 0.0 or nb <= 0.0:
        return float("nan")
    cos = (ax * bx + ay * by) / (na * nb)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


@dataclass(frozen=True)
class TargetArrowSpec:
    """한 관절의 목표 각도 화살표 스펙 (display 전용, immutable).

    px 필드는 전부 **crop 출력 좌표**(_to_crop_px 경유, [0,_OUT-1]). omit_reason 이
    있으면 좌표는 None 이고 _draw_target_arrow 가 즉시 False (드로잉 0).
    mirror_parity 는 판정 결과 provenance — 'same' | 'mirrored' | 'unknown'.
    source_kind 는 v1 'reference_pose' 고정 ('ipsf_absolute' 는 필드만 예약).
    """

    vertex: str
    proximal: str | None
    distal: str | None
    user_vertex_px: tuple[int, int] | None
    user_proximal_px: tuple[int, int] | None
    user_distal_px: tuple[int, int] | None
    target_endpoint_px: tuple[int, int] | None
    source_kind: str
    mirror_parity: str
    confidence: float
    omit_reason: str | None


def _parity_pts(report: dict, frame_idx: int) -> dict[str, tuple[float, float] | None]:
    """parity 판정용 어깨/힙 4점(정규화) — 저신뢰/결측은 None (_gated_kp 계약)."""
    return {k: _gated_kp(report, frame_idx, k) for k in _PARITY_KEYS}


def _facing_sign(kps: dict[str, tuple[float, float] | None]) -> int | None:
    """한 프레임의 좌우 방향 부호 (+1 | -1) — 판정 불가면 None.

    어깨 벡터(left→right)와 힙 벡터(left→right)의 **수평 성분 부호**를 함께 본다.
    둘이 다르면(상체와 골반이 반대 방향을 가리킴) 몸통 topology 가 신뢰 불가 →
    None. 분리가 _MIN_PARITY_SEP 미만이면 정면/측면 경계라 부호가 노이즈 → None.
    """
    ls, rs = kps.get("left_shoulder"), kps.get("right_shoulder")
    lh, rh = kps.get("left_hip"), kps.get("right_hip")
    if ls is None or rs is None or lh is None or rh is None:
        return None
    s_dx = rs[0] - ls[0]
    h_dx = rh[0] - lh[0]
    if abs(s_dx) < _MIN_PARITY_SEP or abs(h_dx) < _MIN_PARITY_SEP:
        return None
    s_sign = 1 if s_dx > 0 else -1
    h_sign = 1 if h_dx > 0 else -1
    if s_sign != h_sign:
        return None
    return s_sign


def _frame_mirror_parity(
    user_kps: dict[str, tuple[float, float] | None],
    ref_kps: dict[str, tuple[float, float] | None],
) -> str:
    """사용자↔reference 프레임의 좌우 parity — 'same' | 'mirrored' | 'unknown'.

    **per-joint 거리 선택 금지** (2차 리뷰 H2-03). "반사한 후보가 현재 자세에 더
    가까우면 그쪽" 휴리스틱은 "올바른 교정은 작은 이동"이라는 거짓 가정이라, 축을
    가로지르는 큰 교정/잘못 접힌 무릎에서 정확히 반대 방향을 지시한다. 그래서 반사
    여부는 관절이 아니라 **프레임 단위 full-body topology 로 1회** 결정하고, 그
    결과를 provenance 에 남긴다. 불명확('unknown')이면 호출측이 화살표를 생략한다 —
    "가까운 쪽" 폴백을 사용자 지시에 쓰지 않는다.
    """
    u = _facing_sign(user_kps)
    r = _facing_sign(ref_kps)
    if u is None or r is None:
        return "unknown"
    return "same" if u == r else "mirrored"


def _omit_arrow(joint_key: str, reason: str, parity: str = "unknown") -> TargetArrowSpec:
    """omission 스펙 — 좌표 0개, 드로잉 0 (리뷰 B-02 omission 규칙)."""
    triple = ARROW_JOINT_MAP.get(joint_key)
    return TargetArrowSpec(
        vertex=joint_key,
        proximal=triple[0] if triple else None,
        distal=triple[2] if triple else None,
        user_vertex_px=None,
        user_proximal_px=None,
        user_distal_px=None,
        target_endpoint_px=None,
        source_kind="reference_pose",
        mirror_parity=parity,
        confidence=0.0,
        omit_reason=reason,
    )


def _build_arrow_spec(
    joint_key: str,
    user_report: dict,
    u_kp_idx: int,
    ref_report: dict,
    r_kp_idx: int,
    ref_match_failed: bool,
    crop_ctx: tuple[int, int, int, int, int],
) -> TargetArrowSpec:
    """목표 각도 화살표 스펙 산출 — reference 좌표 정합 기하만 사용 (리뷰 B-02).

    **감점 record 를 인자로 받지 않는다** — 화면 기하가 채점 수치에 오염될 경로 자체를
    시그니처에서 제거한다 (T-31-10). crop_ctx = (left, top, side, w, h): 사용자측 crop
    이 쓴 그 프레임 좌표계 (_side_crop 반환 box + 프레임 shape).

    정합 기하: reference 의 (proximal, vertex) 를 사용자의 (proximal, vertex) 에 겹치는
    2D similarity 변환(회전+등방 스케일+평행이동) T 를 구해 reference distal 에 적용한
    점이 목표 endpoint 다. 즉 "정은지의 그 순간 관절 형상을 내 몸 크기·방향에 맞춰
    올려놓으면 발끝이 어디로 가는가"를 그린다. 후보가 2개 나오는 선택 로직이 없다 —
    반사 여부는 parity 가 유일 결정자다 (H2-03).

    생략 규칙: ref 대응 실패 / 미선언 관절 / 6점 저신뢰 / parity 불명 / 미세 delta.
    """
    if ref_match_failed:
        return _omit_arrow(joint_key, "ref_match_failed")
    triple = ARROW_JOINT_MAP.get(joint_key)
    if triple is None:
        return _omit_arrow(joint_key, "unmapped_joint")
    p_key, v_key, d_key = triple

    u_pts = [_gated_kp(user_report, u_kp_idx, k) for k in (p_key, v_key, d_key)]
    r_pts = [_gated_kp(ref_report, r_kp_idx, k) for k in (p_key, v_key, d_key)]
    if any(p is None for p in u_pts) or any(p is None for p in r_pts):
        return _omit_arrow(joint_key, "low_confidence")
    confs = [
        _kp_conf(user_report, u_kp_idx, k) for k in (p_key, v_key, d_key)
    ] + [_kp_conf(ref_report, r_kp_idx, k) for k in (p_key, v_key, d_key)]
    confidence = min(float(c) for c in confs if c is not None)

    parity = _frame_mirror_parity(
        _parity_pts(user_report, u_kp_idx), _parity_pts(ref_report, r_kp_idx)
    )
    if parity == "unknown":
        return _omit_arrow(joint_key, "parity_unknown")

    left, top, side, w, h = crop_ctx
    # 각도/정합은 등방 좌표계(frame px)에서 — 정규화 좌표는 W/H 비율만큼 각을 왜곡.
    up, uv, ud = [(p[0] * w, p[1] * h) for p in u_pts]
    rp, rv, rd = [(p[0] * w, p[1] * h) for p in r_pts]
    if parity == "mirrored":
        # 좌우 반사(수직축). 축 위치는 similarity 의 평행이동이 흡수하므로 임의 —
        # reference vertex 를 축으로 잡는다. 후보 비교 없음: parity 가 이미 결정했다.
        axis = rv[0]
        rp = (2 * axis - rp[0], rp[1])
        rd = (2 * axis - rd[0], rd[1])
        rv = (axis, rv[1])

    vx, vy = rv[0] - rp[0], rv[1] - rp[1]
    Vx, Vy = uv[0] - up[0], uv[1] - up[1]
    den = vx * vx + vy * vy
    if den < _MIN_SEG_PX or (Vx * Vx + Vy * Vy) < _MIN_SEG_PX:
        # proximal↔vertex 가 겹침 = 정합 변환 미정의 (0 나눗셈). 그리면 방향이
        # 무의미하므로 생략 — _MIN_LEG_VEC_PX 드로잉 가드와 동일 취지.
        return _omit_arrow(joint_key, "degenerate_segment", parity)
    # z = V / v (복소수 나눗셈) = 회전 + 등방 스케일. T(p) = up + z * (p - rp).
    zr = (Vx * vx + Vy * vy) / den
    zi = (Vy * vx - Vx * vy) / den
    dx, dy = rd[0] - rp[0], rd[1] - rp[1]
    tx = up[0] + zr * dx - zi * dy
    ty = up[1] + zi * dx + zr * dy

    # crop-px 변환은 전부 _to_crop_px 경유 (좌표 변환 단일 출처).
    def to_px(xy: tuple[float, float]) -> tuple[int, int]:
        return _to_crop_px((xy[0] / w, xy[1] / h), left, top, side, w, h)

    u_prox_px = to_px(up)
    u_vert_px = to_px(uv)
    u_dist_px = to_px(ud)
    tgt_px = to_px((tx, ty))
    if math.hypot(
        tgt_px[0] - u_dist_px[0], tgt_px[1] - u_dist_px[1]
    ) < _MIN_ARROW_DELTA_PX:
        return _omit_arrow(joint_key, "negligible_delta", parity)

    return TargetArrowSpec(
        vertex=v_key,
        proximal=p_key,
        distal=d_key,
        user_vertex_px=u_vert_px,
        user_proximal_px=u_prox_px,
        user_distal_px=u_dist_px,
        target_endpoint_px=tgt_px,
        source_kind="reference_pose",
        mirror_parity=parity,
        confidence=confidence,
        omit_reason=None,
    )


def _draw_target_arrow(img: Image.Image, spec: TargetArrowSpec) -> bool:
    """현재 distal → 목표 endpoint 화살표 + 목표 마커 (in-place) — 성공 여부 반환.

    _draw_leg_angle 계약 준수: omit_reason 이 있으면 즉시 False(드로잉 0), degenerate
    는 생략, 라벨은 숫자/기호만(PIL 기본 폰트 한글 글리프 부재 — 한글은 앱 담당).
    display 전용, 채점 무접촉.
    """
    if spec.omit_reason is not None:
        return False
    if spec.user_distal_px is None or spec.target_endpoint_px is None:
        return False
    x0, y0 = spec.user_distal_px
    x1, y1 = spec.target_endpoint_px
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    if length < _MIN_ARROW_DELTA_PX:
        return False
    draw = ImageDraw.Draw(img)
    draw.line([(x0, y0), (x1, y1)], fill=_BRAND, width=4)
    # 삼각 화살촉 — 끝점에서 진행 반대 방향으로 head 만큼 물러난 밑변.
    ux, uy = dx / length, dy / length
    head = min(16.0, length * 0.45)
    half = head * 0.5
    bx, by = x1 - ux * head, y1 - uy * head
    nx, ny = -uy, ux
    draw.polygon(
        [
            (x1, y1),
            (int(round(bx + nx * half)), int(round(by + ny * half))),
            (int(round(bx - nx * half)), int(round(by - ny * half))),
        ],
        fill=_BRAND,
    )
    # 목표 endpoint 점선 마커 — 4 호 세그먼트(간격 40도)로 점선 원.
    r = max(6, int(_OUT * 0.05))
    for start in (0, 90, 180, 270):
        draw.arc(
            [x1 - r, y1 - r, x1 + r, y1 + r],
            start=start,
            end=start + 50,
            fill=_BRAND,
            width=3,
        )
    return True


# ─────────── CorrectedPoseTarget — 자동 교정 target 단일 계약 (2차 리뷰 B2-01) ───────────
#
# 리뷰 B2-01 원문 요구: "joint, targetDeg, src_png 를 따로 계산하지 않고 하나의
# immutable 계약으로 만든다." 따로 계산하면 top-1 감점과 top-1 fault zoom 이 서로 다른
# 기준을 골라 source frame / joint / target pose 가 각각 다른 순간을 가리킬 수 있고,
# 31-09 의 프롬프트와 pose gate 가 같은 오염 target 을 공유해 "잘못된 목표에 정확히
# 맞춘" 이미지가 gate 를 통과한다.
#
# 그래서 이 계약이 지키는 것 3가지:
#   (1) target_deg 는 **DTW matched reference 3점 내각**에서만 나온다. 감점 record 의
#       수치 필드는 어떤 산술에도 들어가지 않는다 — reference_relative record 의 측정
#       수치는 학생의 절대 관절각이 아니라 정은지-대비 편차라서, 그걸 목표각으로 쓰면
#       "편차값을 절대 목표각으로" 지시하게 된다 (리뷰 B-02 와 동일 함정).
#   (2) 후보 우선순위는 **abs(points) 내림차순 → 동률 시 criterion key 오름차순**.
#       DeductionRecord.points 는 signed-negative 라 max(points) 는 "가장 큰 감점"이
#       아니라 0 에 가장 가까운 **최소** 감점을 고른다 (deduction_engine.py:60 함정).
#       tie-break 를 criterion key 로 고정하는 이유(3차 M3-06): 같은 감점 record 의
#       순서가 입력/직렬화에 따라 바뀌면 target 도 바뀌어 결정론이 깨진다.
#   (3) criterion→joint 선언 매핑이 없으면 후보가 아니다. collective(line)·양측 묶음
#       (leg_extension/arm_extension/split_angle)·reach 는 어느 COCO 관절 하나로
#       환원할 수 없어 선언하지 않는다 = correctedPose 생략(legacy 숨김).

# 감점 criterion → ARROW_JOINT_MAP joint_key 의 **명시 선언 매핑**.
# ipsf_criteria.CRITERION_GROUPS 중 joint_keys 가 정확히 1개인 per-joint criterion만
# 이관한다. 다관절/collective criterion 을 임의로 한 관절에 배정하면 "잘못된 관절을
# 교정한 이미지"가 나온다 (B2-01). 어깨(angle_vs_reference__*_shoulder)는
# ARROW_JOINT_MAP 미선언이라 여기서도 제외 — 두 맵이 어긋나면 target 은 있는데 화살표는
# 없는 불일치가 생긴다.
CRITERION_JOINT_MAP: dict[str, str] = {
    f"angle_vs_reference__{jk}": jk for jk in ARROW_JOINT_MAP
}

# **삭제 전용 안정 레지스트리 — 절대 항목 제거 금지** (3차 리뷰 M3-05).
# append-only. 31-07 의 페어 삭제는 pairId(uid:analysisId:joint HMAC)를 재계산해야
# 하는데, ARROW_JOINT_MAP 에서 관절이 제거/rename 되면 과거에 적재된 페어의 joint
# 이름이 사라져 그 pairId 를 다시 만들 수 없다 = 삭제 불가능한 고아 페어. 그래서
# 렌더 계약(ARROW_JOINT_MAP)과 삭제 계약(이 레지스트리)을 분리하고, 여기서는 관절을
# 빼지 않는다. 새 관절 추가 시 양쪽에 함께 넣는다.
HISTORICAL_JOINT_REGISTRY: frozenset[str] = frozenset({
    "left_knee", "right_knee",
    "left_elbow", "right_elbow",
    "left_hip", "right_hip",
})

# 렌더 계약 ⊆ 삭제 계약 불변식 — 위반하면 삭제 불가 페어가 생긴다 (M3-05).
assert set(ARROW_JOINT_MAP) <= HISTORICAL_JOINT_REGISTRY
assert set(CRITERION_JOINT_MAP.values()) <= HISTORICAL_JOINT_REGISTRY

# provenance 버전 — 31-09 프롬프트/pose gate 와 31-10 payload 가 같은 계약을 읽는지
# 확인하는 스칼라. 계약 필드가 바뀌면 반드시 올린다.
CP_TARGET_PROVENANCE_VERSION = "cp-target-v1"


@dataclass(frozen=True)
class CorrectedPoseTarget:
    """자동 교정 생성의 joint/targetDeg/source frame 단일 immutable 계약 (B2-01).

    31-10 enqueue 는 to_payload() 의 스칼라만 job payload 에 기록하고, 31-09 의
    프롬프트와 pose gate 는 **같은 객체의 provenance** 를 소비한다 — 생성 지시와
    검증 기준이 갈라지지 않게.

    hash 필드명 단일 계약 (checker W1): payload key `sourceHash` = 원본 프레임 PNG 의
    sha256 **full hex** (pipeline 31-10 이 산출·병합, 여기 source_frame_hash 와 동일
    값). S3 srcKey 의 hash 세그먼트는 `sourceHash[:16]`.
    """

    joint_key: str
    proximal_key: str
    vertex_key: str
    distal_key: str
    user_frame_idx: int
    ref_frame_idx: int
    source_kind: str
    source_frame_hash: str | None
    target_deg: float
    confidence: float
    provenance_version: str = CP_TARGET_PROVENANCE_VERSION

    def to_payload(self) -> dict:
        """31-02 reserve_visual_job payload 의 flat scalar (Firestore-flat 정합).

        srcKey / sourceHash 는 프레임을 실제로 쓰는 pipeline(31-10)이 병합한다 —
        기하 계층은 프레임 바이트를 모른다.
        """
        return {
            "jointKey": self.joint_key,
            "targetDeg": self.target_deg,
            "userFrameIdx": self.user_frame_idx,
            "refFrameIdx": self.ref_frame_idx,
            "sourceKind": self.source_kind,
            "confidence": self.confidence,
            "provenanceVersion": self.provenance_version,
        }


def build_corrected_pose_target(
    records,
    user_report: dict,
    ref_report: dict,
    dtw_pairs: tuple[int, int] | None,
    ref_match_failed: bool,
    *,
    ref_frame_shape: tuple[int, int] | None = None,
) -> "CorrectedPoseTarget | None":
    """top-1 결함 관절의 교정 target — 불확실하면 None(생성 생략) (2차 리뷰 B2-01).

    records: deductionBreakdown.records (flat dict 리스트). **후보 우선순위에만** 쓴다 —
      criterion 과 points 외의 필드는 읽지 않는다 (수치 미유입, §8 gate 2).
    dtw_pairs: 줌 카드가 쓴 그 (u_kp_idx, r_kp_idx) — keypointReport 인덱스 공간.
      source frame 과 target 이 **같은 순간**을 가리키게 강제하는 계약 (B2-01).
    ref_frame_shape: reference 프레임 (H, W). keypointReport 좌표는 W/H 로 각각
      정규화돼 있어 정사각이 아니면 내각이 비율만큼 왜곡된다 — 모르면 목표각을
      신뢰할 수 없으므로 None 반환(생성 생략). joint_inner_angle_deg 와 동일한
      등방 좌표계 계약.

    None(생략) 조건: 후보 0 / ref 대응 실패 / DTW 쌍 부재 / 프레임 형상 미상 /
    reference 3점 저신뢰 / parity 불명. **잘못된 target 으로 생성하지 않는다.**
    """
    if ref_match_failed or dtw_pairs is None or ref_frame_shape is None:
        return None
    if not isinstance(records, list):
        return None

    # (a)(b) 후보 = 선언 매핑이 있는 criterion 만, abs(points) 내림차순 + key 오름차순.
    candidates: list[tuple[float, str, str]] = []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        crit = rec.get("criterion")
        joint_key = CRITERION_JOINT_MAP.get(crit)
        if joint_key is None:
            continue
        try:
            magnitude = abs(float(rec.get("points")))
        except (TypeError, ValueError):
            continue
        if not np.isfinite(magnitude):
            continue
        candidates.append((magnitude, str(crit), joint_key))
    if not candidates:
        return None
    candidates.sort(key=lambda t: (-t[0], t[1]))
    joint_key = candidates[0][2]

    triple = ARROW_JOINT_MAP.get(joint_key)
    if triple is None:
        return None
    p_key, v_key, d_key = triple

    u_kp_idx, r_kp_idx = int(dtw_pairs[0]), int(dtw_pairs[1])
    r_pts = [_gated_kp(ref_report, r_kp_idx, k) for k in (p_key, v_key, d_key)]
    if any(p is None for p in r_pts):
        return None
    parity = _frame_mirror_parity(
        _parity_pts(user_report, u_kp_idx), _parity_pts(ref_report, r_kp_idx)
    )
    if parity == "unknown":
        return None

    # (c) target_deg = DTW matched reference 3점 내각 (화살표와 동일 geometry helper).
    # 반사는 내각을 바꾸지 않으므로 parity 는 게이트로만 쓴다 (반사 적용 불필요).
    h, w = int(ref_frame_shape[0]), int(ref_frame_shape[1])
    rp, rv, rd = [(p[0] * w, p[1] * h) for p in r_pts]
    target_deg = joint_inner_angle_deg(rp, rv, rd)
    if not np.isfinite(target_deg):
        return None

    confs = [_kp_conf(ref_report, r_kp_idx, k) for k in (p_key, v_key, d_key)]
    confidence = min(float(c) for c in confs if c is not None)

    return CorrectedPoseTarget(
        joint_key=joint_key,
        proximal_key=p_key,
        vertex_key=v_key,
        distal_key=d_key,
        user_frame_idx=u_kp_idx,
        ref_frame_idx=r_kp_idx,
        source_kind="reference_pose",
        source_frame_hash=None,
        target_deg=float(target_deg),
        confidence=confidence,
    )


def build_fault_zoom_comparisons(
    user_frames: np.ndarray,
    ref_frames: np.ndarray,
    user_report: dict,
    ref_report: dict,
    worst_seconds: float | None,
    fault_joints: list[str],
    joint_deltas: dict[str, float] | None = None,
    frames_fps: float = 9.0,
    max_items: int = 4,
    joint_kinds: dict[str, str] | None = None,
    dtw_match=None,
    *,
    dtw_ref_fps: float | None = None,
    user_frame_idx: int | None = None,
    ref_frame_idx: int | None = None,
    user_frame_candidates: list[int] | tuple[int, ...] | None = None,
    ref_frame_candidates: list[int] | tuple[int, ...] | None = None,
    split_angle_degs: tuple[float | None, float | None] | None = None,
    split_angle_present: bool = False,
    draw_arrows: bool = False,
    analysis_id: str | None = None,
) -> list[dict]:
    """결함 unit 별 [학생|기준] 확대 비교 PNG 생성 → list[{joint, deficitDeg, png}].

    user_frames/ref_frames: frame_extractor.extract 결과 (T,H,W,3) uint8 @ frames_fps.
    worst_seconds: vision_veto.worst_pose_timestamp (None 이면 중앙 프레임).
    fault_joints: 강조할 keypoint 이름들 (visionVeto.faultJoints 또는 편차 top).
    joint_deltas: keypoint 이름 → deficit 각도(도). 없으면 마커만(숫자 X).
    user_frame_idx/ref_frame_idx: **명시 프레임 override (quick-260702-sic)** — 둘 다
      9fps frames 배열 인덱스 공간. 주어진 측은 worst_seconds/DTW 선택을 대체한다
      (vision veto 가 측정한 그 프레임 = 표시 프레임 정합). 둘 다 None(default) 이면
      기존 동작 100% 보존 (하위호환).
    user_frame_candidates/ref_frame_candidates (faultzoom-same-frame-crops fix): vision
      측정 worst-pose window(windowMedianAngleDeltas.sourceFrameIndices 의 user/reference
      리스트, ±window 연속 프레임)를 그대로 넘긴다. 주어지면 **crop unit(관절/region)
      마다** 그 unit 멤버 관절의 평균 confidence 최대 프레임을 window 안에서 독립 선택
      (select_confident_frame) → 카드마다 프레임이 달라진다. 회전 동작에서 관절 가시성
      peak 시점이 다르므로 "결함마다 자기 프레임"이 성립한다. 재발 버그(§6.6): 종전엔
      호출측이 window 를 select_confident_frame(전 fault_joints)로 **단일 프레임으로 뭉개**
      전달 → 모든 카드가 같은 프레임(userFrame=140). None(default)이면 단일
      user_frame_idx/worst_seconds/DTW 경로 100% 보존 (하위호환, mode3/legacy). 채점
      무접촉 — display 프레임 선택만 (deductionBreakdown 불변).
      기준(ref) 측 프레임은 이 window 의 DTW 짝을 **anchor** 로만 삼고, 최종 표시
      프레임은 select_pose_matched_ref_frame 이 anchor ±_POSE_SEARCH_SECONDS 안에서
      학생 포즈와 가장 닮은 것으로 고른다 (belle 육안 #2 — DTW 는 타이밍 대응일 뿐
      시각 국면을 보장하지 않음). 판정 불가 시 anchor 유지.
    split_angle_degs (quick-260705-r6x): region=='legs' 카드의 (학생 각도, 기준
      각도) 수치 — 호 옆 표기용. None(default) 이면 legs 카드도 선+호만(수치 생략).
      non-legs/legacy 경로는 무접촉. 채점 무접촉 — display 렌더 전용.
    dtw_ref_fps (CR-01): dtw_match.path 의 ref 인덱스가 사는 fps 공간. None(default)=
      r_rep_fps (mode1 = 정은지 reference doc, angles==keypointReport.fps 18fps —
      byte-identical 하위호환). mode3(지난 사용자 doc)는 prev angles 가 9fps 저장분
      인데 keypointReport 만 18fps upsample 이라 방출측이 9.0 을 명시해야 ref 프레임/
      좌표가 같은 시각을 가리킨다 (미지정 시 절반 시각 오독 = 파일럿 D2 재현).
    split_angle_present (quick-260705-wbs): 사이각 두 게이트.
      · 게이트 A — split_angle criterion 이 실제 records 에 있을 때만(True) legs
        카드에 사이각을 그린다. legs 카드는 스플릿뿐 아니라 무릎(leg_extension)/
        골반(hip) 결함으로도 뜨는데(2026-07-05 belle pod 전동작 검증), 사이각은
        "다리 벌림"의 시각 언어라 스플릿 아닌 결함에 그리면 오독을 낳는다 →
        False(default)면 스플릿 아닌 legs 카드는 r6x 이전 circle 렌더로 복귀.
      · 게이트 B — split 카드라도 학생(user) 측만 그린다. 정은지(ref) 측은 kip-up
        도립 pose 부정확으로 선이 폭주(pose 한계)해 선 없는 crop 을 유지한다.
    draw_arrows (Phase 31-03, D-11/D-12): 목표 각도 화살표를 학생측 crop 에 그린다.
      False(default) = 기존 호출 전부 **바이트 동일 무회귀**. True 여도 사이각을 그린
      legs 카드에는 그리지 않는다 — 호(벌림각)와 화살표(발끝 목표)가 같은 발목 주변에
      겹쳐 시각 언어가 충돌하므로 v1 은 한 카드에 하나만 (게이트 A/B 선례와 동일 취지,
      병행 렌더는 31-12 실 fixture 시각 게이트 후 재검토). reference 측은 무접촉.

    **인덱싱 주의**: 프레임배열은 frames_fps(9)로, keypointReport 는 report['fps']
    (reference 가변, phase4_v1=18fps 실측)로 **각자 시간 인덱싱** — upsample fps
    mismatch 회피. 기준 프레임은 DTW match 로 같은-pose 를 잡되, 반환 인덱스는 ref
    angles(rep) 공간이라 _to_rep_idx 역변환으로 9fps frames 로 내린다 (D2 fix).
    대응 실패 시 = ref 전신 폴백 + refMatch='failed' (D-04, 260702-sic confidence<0.5
    전신 폴백과 일관 — 시간비례 근사로 엉뚱한 pose 를 확대하는 오도를 제거, 정보 보존).

    결함단위 grouping (quick-260702-sic): 같은 결함에서 온 좌+우 동일 부위 관절
    (스플릿 → hips+knees)은 _group_fault_joints 로 카드 1장으로 묶이고, crop 은
    멤버 keypoint bounding box 기반. 방출 dict 에 scalar "region" 추가 (grouped 만).
    측별 crop 은 3단 강하 (Phase 25-03): 신뢰 좌표=기존 crop → 저신뢰-유한
    좌표=부위-중심 완화(relaxed) crop (카드별 차별화, 앵커 생략) → 좌표 결측=
    전신 폴백. 양측 다 신뢰 좌표 0 이면 기존처럼 skip.

    각 항목 png 는 호출측이 S3 업로드 후 presigned URL 로 doc 에 박는다.
    실패 항목은 조용히 skip (graceful).
    """
    out: list[dict] = []
    if user_frames is None or ref_frames is None:
        return out
    u_rep_fps = float(user_report.get("fps") or frames_fps)
    r_rep_fps = float(ref_report.get("fps") or frames_fps)
    u_n = int(user_frames.shape[0])
    r_n = int(ref_frames.shape[0])
    u_rep_frames = int(user_report.get("frames") or 0)
    r_rep_frames = int(ref_report.get("frames") or 0)

    # 프레임 배열 인덱스 (frames_fps 기준). override 는 worst_seconds/DTW 를 이긴다
    # — vision 측정 window 내 표시 프레임과 일치. 변환 공식은 모듈 레벨
    # _to_rep_idx (select_confident_frame 과 공유, quick-260705-ftn).
    if user_frame_idx is not None:
        u_idx = max(0, min(int(user_frame_idx), max(0, u_n - 1)))
        u_kp_idx = _to_rep_idx(u_idx, frames_fps, u_rep_fps, u_rep_frames)
    else:
        u_idx = _frame_index(worst_seconds, frames_fps, u_n)
        u_kp_idx = _frame_index(worst_seconds, u_rep_fps, u_rep_frames)
    # ref_match_failed = 기준 프레임 대응을 세울 수 없음 → ref 전신 폴백 + 앱 캡션
    # (refMatch='failed'). D-04: 어느 pose 인지 모르는 채 시간비례로 근사한 프레임을
    # 확대하면 "비교 부위 아닌 곳" 을 보여줘 오도한다 (파일럿 D2) — 260702-sic 의
    # confidence<0.5 전신 폴백과 일관된 정직 전략(오도 0, 정보 보존).
    ref_match_failed = False
    if ref_frame_idx is not None:
        # override 경로 = vision 측정 프레임 정합 (dtw 취급 — 프레임 대응 보장됨).
        r_idx = max(0, min(int(ref_frame_idx), max(0, r_n - 1)))
        r_kp_idx = _to_rep_idx(r_idx, frames_fps, r_rep_fps, r_rep_frames)
    else:
        # B1: DTW match 로 같은-pose 기준 프레임.
        # dtw_ref_fps = DTW path 의 ref 인덱스가 사는 fps 공간 (CR-01 fix). mode1
        # (정은지 reference doc)은 ref angles == keypointReport.fps(phase4_v1=18fps,
        # 28-01 실측)라 r_rep_fps 와 같지만, mode3(지난 사용자 doc)는 prev angles=
        # 9fps(파이프라인 저장분)인데 keypointReport 만 18fps 로 upsample 저장돼
        # r_rep_fps(18) != dtw 공간(9) 이다. None(default)=r_rep_fps 로 mode1
        # 하위호환(byte-identical) — 방출측이 mode3 에서만 9.0 을 명시한다.
        _dtw_ref_fps = (
            float(dtw_ref_fps)
            if dtw_ref_fps is not None and float(dtw_ref_fps) > 0
            else r_rep_fps
        )
        # clamp 도메인 = dtw fps 공간의 프레임 수 (r_rep_frames 를 fps 비율로 환산).
        # mode1: 18/18 → r_rep_frames. mode3: 18→9 → prev anglesFrames 수. angles
        # 인덱스를 잘못된 도메인으로 클램프하면 끝프레임 밀림(구 D2 오독).
        _dtw_ref_frames = max(
            1, int(round(r_rep_frames / max(1e-6, r_rep_fps) * _dtw_ref_fps))
        )
        if r_rep_frames <= 0:
            r_matched = None
        else:
            r_matched = _matched_ref_frame(dtw_match, u_idx, _dtw_ref_frames)
        if r_matched is not None:
            # dtw 공간 인덱스 → keypointReport(rep) / 9fps frames 각각 변환 (D2 fix).
            # 같은 _to_rep_idx 공식에 fps 인자만 다름(중복 공식 금지, quick-260705-ftn).
            # mode1(dtw_ref_fps=r_rep_fps): r_kp_idx=r_matched (identity), r_idx 는
            # 종전과 동일 — byte-identical. mode3(dtw_ref_fps=9): 9fps→18fps
            # keypointReport, 9fps→9fps frames 로 같은 시각 정합.
            r_kp_idx = _to_rep_idx(r_matched, _dtw_ref_fps, r_rep_fps, r_rep_frames)
            r_idx = _to_rep_idx(r_matched, _dtw_ref_fps, frames_fps, r_n)
        else:
            # 대응 실패 → ref 전신 폴백 (D-04, ratio 근사 제거). 프레임은 중앙
            # (전신이므로 어느 순간이든 오도 0), 좌표는 아래 루프에서 강제 skip.
            ref_match_failed = True
            r_idx = r_n // 2
            r_kp_idx = r_rep_frames // 2 if r_rep_frames > 0 else 0

    deltas = joint_deltas or {}
    for unit in _group_fault_joints(list(fault_joints), joint_kinds):
        if len(out) >= max_items:
            break
        # ── 관절별 프레임 선택 + DTW 정렬 (faultzoom-same-frame-crops fix) ────
        # candidates(worst-pose window) 주어지면 unit 멤버 관절 confidence 최대
        # 프레임의 **window position** 을 학생 가시성으로 1개 선택(크롭 앵커=학생
        # 결함) → 카드마다 프레임 상이. 기준 프레임은 **같은 position 의 ref 후보**
        # (DTW 짝)를 쓴다.
        #
        # NEW 서브버그 fix (belle 2026-07-25): 종전엔 sel_r 을 ref 자기 confidence 로
        # **독립 선택** → user/ref 가 서로 다른 window index 를 골라 카드 안에서
        # 정은지 패널이 학생과 다른 동작 순간을 보여줌("정은지 쪽은 아예 다른 장면").
        # user/ref window(sourceFrameIndices)는 position 으로 DTW 대응하므로 값이
        # 아니라 **같은 index** 로 짝지어 카드 내 student↔reference 를 같은 순간으로
        # 정렬한다. 선택 실패(window 부재/전원 저신뢰)면 batch 기본 프레임 폴백 =
        # 종전 동작. 채점 무접촉 — display 프레임 선택만.
        u_idx_unit, u_kp_idx_unit = u_idx, u_kp_idx
        r_idx_unit, r_kp_idx_unit = r_idx, r_kp_idx
        ref_match_failed_unit = ref_match_failed
        if user_frame_candidates:
            u_cands = list(user_frame_candidates)
            sel_pos = select_confident_index(
                user_report, u_cands, unit.members, frames_fps
            )
            if sel_pos is not None:
                u_idx_unit = max(0, min(int(u_cands[sel_pos]), max(0, u_n - 1)))
                u_kp_idx_unit = _to_rep_idx(
                    u_idx_unit, frames_fps, u_rep_fps, u_rep_frames
                )
                # 기준 프레임 = 같은 window position 의 DTW 짝 (독립 선택 제거).
                # window 는 DTW-matched worst-pose ±window 라 position 대응이
                # same-pose 를 유지 → override 경로와 동일 취급 (refMatch='dtw').
                if ref_frame_candidates is not None:
                    r_cands = list(ref_frame_candidates)
                    if sel_pos < len(r_cands):
                        try:
                            sel_r = int(r_cands[sel_pos])
                        except (TypeError, ValueError):
                            sel_r = None
                        if sel_r is not None:
                            r_idx_unit = max(0, min(sel_r, max(0, r_n - 1)))
                            r_kp_idx_unit = _to_rep_idx(
                                r_idx_unit, frames_fps, r_rep_fps, r_rep_frames
                            )
                            ref_match_failed_unit = False
                # ── 같은-포즈 매칭 (belle 육안 #2) ─────────────────────────
                # DTW 짝은 **타이밍** anchor 로만 쓰고, 실제 표시할 기준 프레임은
                # 그 주변에서 학생 포즈와 가장 닮은 것으로 고른다. DTW 가 관절각
                # (방향 불변) 위에서 계산되는 탓에 같은 window position 이어도
                # 앞/뒤가 뒤집힌 순간이 잡히던 문제(belle: "정은지는 앞을 보는데
                # 학생은 뒤돌아본 순간")를 여기서 교정한다. 신뢰 keypoint 부족 등으로
                # 판정 불가면 None → anchor(ea55069 동작) 그대로 = 조용한 악화 없음.
                if not ref_match_failed_unit:
                    posed = select_pose_matched_ref_frame(
                        user_report,
                        ref_report,
                        u_kp_idx_unit,
                        r_idx_unit,
                        r_n,
                        frames_fps=frames_fps,
                        ref_rep_fps=r_rep_fps,
                        ref_rep_frames=r_rep_frames,
                    )
                    log.info(
                        "fault_zoom_pose_match analysis_id=%s region=%s "
                        "user_kp=%s dtw_ref=%s posed_ref=%s",
                        analysis_id,
                        unit.region or unit.joint,
                        u_kp_idx_unit,
                        r_idx_unit,
                        posed if posed is not None else "none",
                    )
                    if posed is not None:
                        r_idx_unit = max(0, min(int(posed), max(0, r_n - 1)))
                        r_kp_idx_unit = _to_rep_idx(
                            r_idx_unit, frames_fps, r_rep_fps, r_rep_frames
                        )
        u_valid, u_relaxed = _member_pts(user_report, u_kp_idx_unit, unit.members)
        if ref_match_failed_unit:
            # 대응 실패 = ref 측 전신 폴백 강제 (D-04). 좌표 계산을 건너뛰고 빈
            # 리스트를 넘겨 _side_crop 3단 강하의 전신 폴백 단계로 직행 (새 렌더
            # 금지 — 기존 좌표-결측 전신 폴백 분기 재사용). 학생 카드는 유지.
            r_valid, r_relaxed = [], []
        else:
            r_valid, r_relaxed = _member_pts(ref_report, r_kp_idx_unit, unit.members)
        if not u_valid and not r_valid:
            # 양측 다 신뢰 좌표 0 — 최소 한 측 valid 일 때만 카드 (기존 skip
            # 규칙 보존). relaxed 는 반대측이 valid 인 카드에서 전신 폴백을
            # 대체하는 강하 단계이지, 단독으로 카드를 만들지 않는다 (양측
            # 불확실 crop = 오인 위험, 260702-sic 요구 3 정신).
            continue
        member_deltas = [
            float(deltas[m]) for m in unit.members if deltas.get(m) is not None
        ]
        deficit = max(member_deltas) if member_deltas else None
        try:
            u_frame = user_frames[u_idx_unit]
            # ref 표시 프레임 = 타임베이스 매핑 (rep 공간 → 비디오 배열,
            # ref_display_frame_index docstring 실측 근거). 정합 ref 는 배율 1.0
            # identity. 대응실패(전신 폴백)는 r_idx_unit 이 이미 비디오 중앙이라 제외.
            r_display_idx = (
                r_idx_unit
                if ref_match_failed_unit
                else ref_display_frame_index(
                    r_idx_unit, r_n, r_rep_frames, r_rep_fps, frames_fps
                )
            )
            r_frame = ref_frames[r_display_idx]
            u_img, u_kind, u_anchor, u_box = _side_crop(
                u_frame,
                [xy for _n, xy in u_valid],
                u_relaxed,
                anchor=_anchor_xy(u_valid, deltas) if u_valid else None,
            )
            # 게이트 B 로 ref 측 사이각 미드로잉 → kind/box 미사용(선 없는 crop).
            r_img, _r_kind, _r_anchor, _r_box = _side_crop(
                r_frame, [xy for _n, xy in r_valid], r_relaxed
            )
            # D-20 (32-CONTEXT): crop side px 구조 로그 (관측 전용, 채점/방출 무접촉).
            # 32-03 전수 스윕이 육안 비교에 더해 user/ref side 비(0.8~1.25)로 프레이밍
            # 수치 parity 를 판정하는 재료. box 는 (left, top, side) — full 폴백은 None
            # (crop 박스 없음). analysis_id 는 caller 가 넘긴 로그 상관 키(미지정=None).
            log.info(
                "fault_zoom_crop analysis_id=%s region=%s "
                "user_kind=%s user_side_px=%s ref_kind=%s ref_side_px=%s "
                "ref_rep_idx=%s ref_video_idx=%s",
                analysis_id,
                unit.region or unit.joint,
                u_kind,
                u_box[2] if u_box is not None else "full",
                _r_kind,
                _r_box[2] if _r_box is not None else "full",
                r_idx_unit,
                r_display_idx,
            )
            # legs(스플릿) 카드: 앵커 동그라미 대신 다리 사이각(선 2 + 호 + 수치).
            # 게이트 A(quick-260705-wbs) — split_angle criterion 이 실제 records 에
            # 있는 legs 카드(split_angle_present=True)만 진입. legs 카드는 스플릿뿐
            # 아니라 무릎(leg_extension)/골반(hip) 결함으로도 뜨는데 (2026-07-05
            # belle pod 전동작 검증: power-spin=leg_extension+hip, elbow-twist=
            # hip+knee), 사이각은 "다리 벌림"의 시각 언어라 스플릿 아닌 결함에
            # 그리면 오독을 낳는다 → 스플릿 아닌 legs 카드는 이 블록 미진입, 아래
            # 기존 circle 렌더로 복귀한다.
            # 게이트 B(quick-260705-wbs) — 학생(user) 측만 그린다. 정은지(ref) 측은
            # kip-up 도립 pose 부정확으로 선이 폭주(pose 한계)해 선 없는 crop 유지.
            # TODO(Phase 22): 자체학습 pose 개선 후 정은지(ref) 측 사이각 재활성.
            # split_angle_degs=(학생 수치, 기준 수치), None 이면 수치 생략(선+호만).
            u_deg = split_angle_degs[0] if split_angle_degs else None
            u_drew_legs = False
            if (
                unit.region == "legs"
                and split_angle_present
                and u_kind == "valid"
                and u_box is not None
            ):
                u_drew_legs = _draw_side_leg_angle(
                    u_img, u_frame, user_report, u_kp_idx_unit, u_box, u_deg
                )
            # user 측: 사이각을 그렸으면 원 생략(배지는 유지 — 배지=부족분/호=측정
            # 각도로 역할 분리), 아니면 기존 규칙 그대로.
            if u_drew_legs:
                u_crop = _mark(u_img, deficit, circle=False, anchor_px=None)
            else:
                u_crop = _mark(
                    u_img, deficit, circle=u_kind == "valid", anchor_px=u_anchor
                )
            # D-11 목표 각도 화살표 (Phase 31-03) — 학생측 crop 에만, ARROW_JOINT_MAP
            # 에 선언된 멤버 관절만. 사이각을 그린 카드는 건너뛴다(시각 언어 충돌).
            # 생략 규칙은 전부 _build_arrow_spec 안에 있고 _draw_target_arrow 가
            # omit_reason 을 보면 즉시 False 라 여기서 조건 중복 판정하지 않는다.
            if (
                draw_arrows
                and not u_drew_legs
                and u_kind == "valid"
                and u_box is not None
            ):
                u_h, u_w = u_frame.shape[0], u_frame.shape[1]
                for member in unit.members:
                    if member not in ARROW_JOINT_MAP:
                        continue
                    _draw_target_arrow(
                        u_crop,
                        _build_arrow_spec(
                            member,
                            user_report,
                            u_kp_idx_unit,
                            ref_report,
                            r_kp_idx_unit,
                            ref_match_failed_unit,
                            (u_box[0], u_box[1], u_box[2], u_w, u_h),
                        ),
                    )
            # ref 측은 _mark/사이각 모두 없음 — 선 없는 crop 그대로(게이트 B).
            png = _compose(u_crop, r_img)
        except Exception:  # noqa: BLE001 - 단일 항목 실패는 전체를 막지 않음
            continue
        item = {
            "joint": unit.joint,
            "deficitDeg": deficit,
            "png": png,
            # DTW 대응 프레임 쌍 (리뷰 B-01, Phase 31-03) — 2D 비교 뷰어(amended
            # D-10)의 프레임 정합 소스. draw_arrows 와 무관하게 **항상** 방출한다:
            # 뷰어는 화살표 유무와 별개로 "내 자세 어느 프레임 ↔ 목표 어느 프레임"을
            # 알아야 중첩할 수 있다. 둘 다 keypointReport 인덱스 공간(u_kp_idx/
            # r_kp_idx) — 프레임 배열(9fps) 인덱스가 아니다. refMatched=False 면
            # refFrameIdx 는 전신 폴백의 중앙 프레임이라 정합 근거가 아니다.
            "userFrameIdx": int(u_kp_idx_unit),
            "refFrameIdx": int(r_kp_idx_unit),
            "refMatched": not ref_match_failed_unit,
        }
        kind = (joint_kinds or {}).get(unit.joint)
        if kind:
            item["kind"] = kind
        if unit.region:
            item["region"] = unit.region
        # D-04 provenance scalar (region 선례 형식) — 기준 프레임 대응 성공='dtw',
        # 실패='failed'(전신 폴백). override(ref_frame_idx)는 vision 측정 프레임
        # 정합이 보장되므로 'dtw' 취급. scalar str 이라 _validate_dict_only_scalars
        # flat 제약 통과. app.py _render_fault_zoom mapper 가 최종 doc 까지 pass-through.
        item["refMatch"] = "failed" if ref_match_failed_unit else "dtw"
        out.append(item)
    return out

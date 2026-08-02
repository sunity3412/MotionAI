"""quick-260802-mrg — phrasebook (motion x exerciseId) 묶음의 해부학 정합 게이트.

왜 이 게이트가 생겼나: 앱이 이제 `DeductionRecord.exerciseId` 를 **표시 병합 키**로
쓴다. 같은 exerciseId 를 공유하는 부위 그룹은 화면에서 항목 1개(칩 1개·마커 1경계·
시트 1장)로 묶인다 (`app/src/lib/deductionSheet.ts buildCauseGroupKeys`). 그래서
phrasebook 을 나중에 고칠 때 exerciseId 배정이 어긋나면 **말이 안 되는 병합**
("어깨·다리" 같은 한 항목)이 조용히 화면에 생긴다 — 코드는 그대로인 채 데이터만으로.
이 파일은 그 경로를 데이터 쪽에서 막는다.

**채점 무접촉.** 여기서 검증하는 것은 문구 데이터의 부위 정합뿐이고, 점수 산출
(deduction_engine / dimensions / ipsf_criteria)과 phrasebook 문구 자체는 이 작업에서
한 글자도 바뀌지 않았다. exerciseId 는 종전부터 방출되던 필드다 (신규 계약 0).

부위 투영 표는 앱의 `BODY_PART_OF_KEYPOINT` + `CRITERION_REGION_KEYPOINTS` 의
**테스트 로컬 미러**다 (phase32 test_terminology_lockstep 선례 — 백엔드 산출 코드에
앱 표시 규칙을 심지 않기 위해 미러를 테스트가 소유한다). 앱 표를 고치면 여기도
같이 고쳐야 하고, 그 lockstep 자체는 아래 test_projection_mirror_covers_criteria 가
"phrasebook 에 실존하는 criterion 은 전부 투영 판정이 가능해야 한다"로 지킨다.

motion 키는 `entries` 에서 **파생**한다 — 동작명 리터럴 하드코딩 금지 (D-41).

순수 데이터 검증 — boto3/네트워크/GPU 무접촉.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_PHRASEBOOK_PATH = _BACKEND / "data" / "phrasebook.json"
_EXERCISES_PATH = _BACKEND / "data" / "corrective_exercises.json"

_COMMON_PREFIX = "__common__"
_ANGLE_PREFIX = "angle_vs_reference__"

# ── 앱 표시 규칙의 테스트 로컬 미러 ────────────────────────────────────────
# 출처: app/src/lib/deductionLabels.ts
#   KEYPOINT_FROM_ANGLE_KEY / BODY_PART_OF_KEYPOINT / REGION_MEMBER_KEYPOINTS /
#   CRITERION_REGION_KEYPOINTS
_BODY_PART_OF_KEYPOINT = {
    "left_shoulder": "shoulder",
    "right_shoulder": "shoulder",
    "left_elbow": "arm",
    "right_elbow": "arm",
    "left_hand": "arm",
    "right_hand": "arm",
    "left_hip": "leg",
    "right_hip": "leg",
    "left_knee": "leg",
    "right_knee": "leg",
    "left_ankle": "leg",
    "right_ankle": "leg",
}
_REGION_MEMBER_KEYPOINTS = {
    "legs": ("left_hip", "right_hip", "left_knee", "right_knee"),
    "arms": ("left_shoulder", "right_shoulder", "left_hand", "right_hand"),
}
_CRITERION_REGION_KEYPOINTS = {
    "leg_extension": _REGION_MEMBER_KEYPOINTS["legs"],
    "arm_extension": _REGION_MEMBER_KEYPOINTS["arms"],
    "split_angle": _REGION_MEMBER_KEYPOINTS["legs"],
}
# angle 키는 동명 관절로 직접 투영 (33-G S9 — elbow→hand 인접 매핑은 폐기됨).
_ANGLE_JOINTS = frozenset(
    (
        "left_elbow",
        "right_elbow",
        "left_shoulder",
        "right_shoulder",
        "left_hip",
        "right_hip",
        "left_knee",
        "right_knee",
    )
)
# 투영 공집합이 **정상**인 criterion — 그릴 부위가 없어 앱에서 `criterion:` 단독
# 그룹으로 떨어지고, 병합에 아예 참여하지 않는다 (buildCauseGroupKeys T6).
_NO_PROJECTION_CRITERIA = frozenset(("line", "body_relative_reach"))

_UPPER_TOKENS = frozenset(("shoulder", "arm"))
_LOWER_TOKENS = frozenset(("leg",))


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _project_tokens(criterion: str) -> frozenset[str]:
    """criterion → 부위 토큰 집합 (앱 projectDeductionRecordKeypoints 미러)."""
    keypoints: tuple[str, ...] = ()
    if criterion.startswith(_ANGLE_PREFIX):
        joint = criterion[len(_ANGLE_PREFIX) :]
        keypoints = (joint,) if joint in _ANGLE_JOINTS else ()
    else:
        keypoints = tuple(_CRITERION_REGION_KEYPOINTS.get(criterion, ()))
    return frozenset(
        token
        for token in (_BODY_PART_OF_KEYPOINT.get(kp) for kp in keypoints)
        if token
    )


def _bundles() -> dict[tuple[str, str], list[str]]:
    """(motion, exerciseId) → criterion 목록. motion 은 entries 에서 파생."""
    entries = _load(_PHRASEBOOK_PATH)["entries"]
    out: dict[tuple[str, str], list[str]] = defaultdict(list)
    for key, entry in entries.items():
        motion, _, criterion = key.partition(".")
        exercise_id = entry.get("exerciseId")
        if not isinstance(exercise_id, str) or not exercise_id:
            # fail-closed entry 는 exerciseId 를 갖지 않는다 — 병합 키가 없으므로
            # 앱에서도 간선을 만들지 않는다. 묶음 대상 밖.
            continue
        out[(motion, exercise_id)].append(criterion)
    return dict(out)


def test_no_bundle_spans_upper_and_lower_body() -> None:
    """상체(shoulder/arm)와 하체(leg)를 동시에 걸치는 (motion x exerciseId) 묶음 0.

    걸치는 묶음이 생기면 앱에서 "어깨·다리" 같은 한 항목이 만들어진다 — 사용자에게
    한 잘못으로 읽히지만 실제로는 서로 다른 두 결함이다. 억지 병합 금지의 데이터측
    수문.
    """
    violations = []
    for (motion, exercise_id), criteria in sorted(_bundles().items()):
        tokens: set[str] = set()
        for criterion in criteria:
            tokens |= _project_tokens(criterion)
        if tokens & _UPPER_TOKENS and tokens & _LOWER_TOKENS:
            violations.append(
                f"{motion}.{exercise_id}: {sorted(tokens)} <- {sorted(criteria)}"
            )
    assert not violations, "상하체를 걸치는 묶음 (무의미 병합): " + "; ".join(violations)


def test_bundle_exercise_ids_exist_in_corrective_exercises() -> None:
    """병합 키로 쓰이는 exerciseId 는 corrective_exercises.json defects 실존 키.

    유령 id 는 화면에서 조용히 "자기 자신하고만 묶이는" 그룹을 만든다 — 병합도
    안 되고 운동 연결도 끊긴 상태라 두 표면이 동시에 죽는다.
    """
    known = set(_load(_EXERCISES_PATH)["defects"].keys())
    used = {exercise_id for _motion, exercise_id in _bundles()}
    assert used, "exerciseId 를 가진 entry 가 0개 — phrasebook 데이터 미작성"
    assert used <= known, f"유령 exerciseId: {sorted(used - known)}"


def test_projection_mirror_covers_criteria() -> None:
    """phrasebook 실존 criterion 은 전부 투영 판정이 가능해야 한다 (미러 lockstep).

    앱 표에 없는 criterion 이 phrasebook 에 새로 생기면 앱은 그 record 를
    `criterion:` 단독 그룹으로 떨구고, 여기 미러도 조용히 빈 집합을 돌려준다 —
    그러면 위 상하체 게이트가 그 criterion 을 **검사하지 않은 채** 통과한다.
    투영 공집합이 정상인 criterion 은 명시 목록으로만 허용한다.
    """
    entries = _load(_PHRASEBOOK_PATH)["entries"]
    criteria = {key.partition(".")[2] for key in entries}
    unprojectable = sorted(
        c
        for c in criteria
        if not _project_tokens(c) and c not in _NO_PROJECTION_CRITERIA
    )
    assert not unprojectable, (
        "부위 투영 미러가 모르는 criterion: "
        f"{unprojectable} — app/src/lib/deductionLabels.ts 표와 함께 갱신할 것"
    )


def test_shoulder_arm_bundle_exists_and_is_the_merging_case() -> None:
    """belle 이 지목한 어깨↔팔꿈치 병합이 데이터로 실제 성립하는지 (측정 5 재현).

    이 케이스가 사라지면 병합 기능 자체가 죽은 코드가 된다. 동작명은 하드코딩하지
    않고 `entries` 에서 파생한 묶음에서 찾는다 — 어느 동작에서 성립하는지는 승인
    fixture 데이터가 정한다.
    """
    spanning = {
        (motion, exercise_id)
        for (motion, exercise_id), criteria in _bundles().items()
        if len({t for c in criteria for t in _project_tokens(c)} & _UPPER_TOKENS) == 2
    }
    assert spanning, (
        "shoulder 와 arm 을 함께 묶는 (motion x exerciseId) 가 0 — 병합 대상이 없다"
    )


def test_common_bundles_do_not_span_upper_body_incoherently() -> None:
    """`__common__` 묶음도 같은 규칙을 받는다 (동작 미해석 폴백 경로 보호).

    동작 인식에 실패한 doc 은 전 criterion 이 `__common__` 으로 떨어진다. 그 경로의
    exerciseId 배정이 어긋나면 인식 실패 시에만 나타나는 병합 결함이 되어 fixture
    에서 안 잡힌다.
    """
    common = {
        exercise_id: criteria
        for (motion, exercise_id), criteria in _bundles().items()
        if motion == _COMMON_PREFIX
    }
    assert common, "__common__ 묶음이 0개 — 폴백 문구 데이터 미작성"
    for exercise_id, criteria in sorted(common.items()):
        tokens: set[str] = set()
        for criterion in criteria:
            tokens |= _project_tokens(criterion)
        assert not (tokens & _UPPER_TOKENS and tokens & _LOWER_TOKENS), (
            f"__common__.{exercise_id} 가 상하체를 걸친다: {sorted(tokens)}"
        )

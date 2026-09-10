"""보완 운동 매핑 layer (Phase 13 Plan 13-A / PERS-03).

분석 결과의 실패 원인 후보(Phase 9 forcePatternInference.findings)와 자가입력
통증부위(BodyProfile.painAreas)를 입력으로 받아 결함/통증부위별 보완 운동을
backend/data/corrective_exercises.json fixture 에서 매핑한다.

순수성 (Layer 2 boto3 영구 차단 — force_pattern.py / classify_findings 패턴 정합):
  - numpy/AWS-free, network-free. 단위 test 로 전부 검증.
  - 입력은 plain dict / list[str] / str|None, 출력은 plain camelCase scalar dict
    (dataclass 아님 — Firestore recommendedExercises 가 그대로 저장됨).

3-way contract lockstep (Task 3 박제): TS `app/src/types/analysis.ts`
RecommendedExercise ↔ models.py recommendedExercises 계약 ↔ docs/contract.md §4.

D-05 하드월: painAreas 는 본 매핑 출력에만 흘러가고 어떤 점수/차원 채점 경로에도
닿지 않는다. 본 함수는 차원 채점 값을 인자로 받지 않으며 채점 경로 토큰을 참조하지
않는다 (test_exercise_map_no_scoring_leak.py grep 게이트).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from .. import models

# corrective_exercises.json — repo root 기준 (force_signals._CONTACT_POINTS_PATH
# 패턴 정합: analysis → sunity_shared → python → shared → backend / "data").
_CORRECTIVE_EXERCISES_PATH = (
    Path(__file__).parent.parent.parent.parent.parent
    / "data"
    / "corrective_exercises.json"
)
_CORRECTIVE_EXERCISES_CACHE: dict | None = None

# defect 키 검증용 frozenset (fixture defects 키와 lockstep).
# glute_hip_unstable = 13-A GAP 클로저 (pelvis_drop 커버리지 — 중둔근/고관절
# 외전근 STABILITY 결함, hip_hamstring_tight 의 flexibility 와 구분).
_DEFECT_KEYS: frozenset[str] = frozenset(
    {
        "grip_weak",
        "shoulder_unstable",
        "core_weak",
        "legs_not_extended",
        "hip_hamstring_tight",
        "glute_hip_unstable",
    }
)
# painArea 키 = models.PAIN_AREAS 재사용 (단일 진실원).
_PAIN_AREA_KEYS: frozenset[str] = frozenset(models.PAIN_AREAS)

# quick-260704-fwb — 부위(keypoint_set) → defect 키 매핑. 입력 출처는 둘이다 —
# vision veto 결함 부위(faultKey.keypoint_set)와 실제 감점 record 부위
# (quick-260910-pbs). 어휘가 같으므로 접는 규칙도 하나다(_rounds_by_part).
# 알 수 없는 keypoint_set 값은 조용히 skip (graceful — enum drift 시 크래시 0).
# vision_veto.FAULT_KEYPOINT_SETS 8값 전부 커버. vision_veto import 금지 (순수성
# 유지 — 문자열 리터럴 lockstep, 값 추가 시 여기도 갱신). 스플릿 각도 부족 =
# 고관절 유연성 → hip_hamstring_tight 를 leg 의 1순위로 (kip-up 케이스 정합).
_KEYPOINT_SET_TO_DEFECTS: dict[str, tuple[str, ...]] = {
    "leg": ("hip_hamstring_tight", "legs_not_extended"),
    "hip": ("glute_hip_unstable", "hip_hamstring_tight"),
    "shoulder": ("shoulder_unstable",),
    "arm": ("shoulder_unstable",),
    "head_neck": ("shoulder_unstable",),
    "grip": ("grip_weak",),
    "torso": ("core_weak",),
    "line": ("core_weak",),
}

# 보완 운동 출력 상한.
# belle 2026-09-10 (초): "동작별 최대 6개 정도로만" → quick-260910-pbs 가 5 를 6 으로
#   올렸다. 그 발언은 천장의 어림값("정도로만")이었지 6 을 요구한 것이 아니다.
# belle 2026-09-10 (후, 확정): "필요하다면 줄이는거지 억지로 맞추는건 맥시멈만
#   (현 5개 오케이)" → 5 로 충분하다. 올릴 이유가 없어 **5 로 복귀**(quick-260910-u67).
#   ★ 앞 발언만 보고 6 으로 되돌리지 말 것. 뒤 발언이 앞 발언을 확정·대체한 것이고,
#   6 으로 다시 올리려면 belle 의 새 발언이 필요하다.
# 이것은 **상한**이지 목표치가 아니다 — 하한은 없다. 필요한 결함이 1개면 1개만 나온다.
# belle 2026-09-10: "분석 나오는 거에 따라 다르겠지만" — 실제 개수는 분석이 정한다.
#   백필 폐지 후 실측(4개 doc)이 3·4·4·5 라 이 천장에는 닿지 않는다.
# 3곳 lockstep: 여기(생성) · models.MAX_RECOMMENDED_EXERCISES(저장 거부선) ·
# firestore_admin._validate_recommended_exercises(검증). 셋을 같이 바꿀 것.
_MAX_EXERCISES = 5

# 결함 하나당 대표 운동 개수 (quick-260910-pbs).
# belle 2026-09-10: "1개 필요하면 진짜 1개만, 3개 필요하면 3개" → 개수를 분석이
# 정하게 하려면 결함 수가 개수를 정해야 한다. 그래서 defect 당 **고정 1개**를 뽑고
# 남는 자리를 채우지 않는다(백필 폐지 — 그것이 개수를 항상 상한으로 붙여놓던 원인).
# belle 2026-09-03 은 "한 두개씩"이라 했으므로 1 이냐 2 냐는 화면을 보고 정할 여지가
# 있다. 그 조정은 **이 상수 한 줄**이다 (fault/findings 양쪽 경로가 이 값을 공유).
_EXERCISES_PER_DEFECT = 1


def _load_corrective_exercises() -> dict:
    """corrective_exercises.json lazy load + 모듈 캐시."""
    global _CORRECTIVE_EXERCISES_CACHE
    if _CORRECTIVE_EXERCISES_CACHE is None:
        _CORRECTIVE_EXERCISES_CACHE = json.loads(
            _CORRECTIVE_EXERCISES_PATH.read_text(encoding="utf-8")
        )
    return _CORRECTIVE_EXERCISES_CACHE


def _defect_keys_from_findings(findings: list) -> list[str]:
    """findings[] 의 sourceSignal + jointHint 를 defect 키로 join.

    fixture 의 defect.triggers.sourceSignals / jointHints 와 매칭. 우선순위는
    findings 순서 (Phase 9 가 이미 Top-3 ranking 적용) 를 보존한다.
    """
    library = _load_corrective_exercises()
    defects = library.get("defects", {})
    matched: list[str] = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        source_signal = finding.get("sourceSignal")
        joint_hint = finding.get("jointHint")
        for defect_key, defect in defects.items():
            if defect_key not in _DEFECT_KEYS or defect_key in matched:
                continue
            triggers = defect.get("triggers", {})
            signals = triggers.get("sourceSignals", [])
            hints = triggers.get("jointHints", [])
            signal_hit = source_signal is not None and source_signal in signals
            hint_hit = (
                joint_hint is not None
                and any(h in joint_hint or joint_hint in h for h in hints)
            )
            if signal_hit or hint_hit:
                matched.append(defect_key)
    return matched


# 준비운동 kind 값 (models.EXERCISE_KINDS lockstep). 목록 앞으로 보내는 규칙에만
# 쓴다 — 개수 배분에는 쓰지 않는다 (belle 이 강제 혼합을 기각).
_WARMUP_KIND = "warmup"


def _rounds_by_part(
    keypoint_sets: list[str] | None,
    exercises_of: Callable[[str], list],
    used_defects: set[str],
) -> list[list[dict]]:
    """부위(keypoint_set)마다 후보 운동을 한 줄씩 만든다 (quick-260910-vwh Task 3).

    줄의 순서 = 입력 순서 = **감점이 큰 부위부터**. 한 부위가 여러 defect 로
    펼쳐지면(`leg` → hip_hamstring_tight + legs_not_extended) 그 줄이 길어지고,
    이미 다른 부위가 가져간 defect 는 건너뛴다(`used_defects`).

    왜 부위 단위인가 — 종전엔 defect 단위로 앞에서부터 잘라, 부위 하나가 defect 2개로
    펼쳐지면 **다른 부위의 대표보다 먼저** 두 자리를 가져갔다. 결과 화면 카드는 3행만
    보여주므로(ResultExerciseTab MAX_ROWS) 감점이 작은 부위는 아예 화면 밖으로 밀렸다.
    """
    per_part: list[list[dict]] = []
    for kp_set in keypoint_sets or []:
        row: list[dict] = []
        for defect_key in _KEYPOINT_SET_TO_DEFECTS.get(kp_set, ()):
            if defect_key not in _DEFECT_KEYS or defect_key in used_defects:
                continue
            used_defects.add(defect_key)
            row.extend(exercises_of(defect_key)[:_EXERCISES_PER_DEFECT])
        if row:
            per_part.append(row)
    return per_part


def _interleave(per_part: list[list[dict]]) -> list[dict]:
    """부위마다 대표를 하나씩 먼저 채우고, 남으면 감점 큰 부위부터 두 번째를 준다.

    belle 2026-09-10: "분석 보고에 따라 조절 되어야 한다는 말이야." 어깨·팔꿈치·무릎이
    걸렸으면 세 부위가 다 나온다 — 한 부위가 목록을 독식하지 않는다.
    """
    out: list[dict] = []
    for round_index in range(max((len(row) for row in per_part), default=0)):
        for row in per_part:
            if round_index < len(row):
                out.append(row[round_index])
    return out


def _valid_pain_area_keys(pain_areas: list[str]) -> list[str]:
    """painAreas[] 를 painArea 키로 join — PAIN_AREAS 멤버만, 순서/중복 보존 제거."""
    result: list[str] = []
    for area in pain_areas or []:
        if area in _PAIN_AREA_KEYS and area not in result:
            result.append(area)
    return result


def map_exercises(
    force_pattern_inference: dict | None,
    pain_areas: list[str],
    motion_id: str | None,
    *,
    fault_keypoint_sets: list[str] | None = None,
    deduction_keypoint_sets: list[str] | None = None,
) -> list[dict]:
    """결함 + 통증부위 → 보완 운동 (개수는 결함 수가 정한다, 상한 _MAX_EXERCISES).

    Args:
        force_pattern_inference: Firestore result.forcePatternInference dict
            (findings[] camelCase) 또는 None (FallbackRecognizer / 미산출).
        pain_areas: bodyProfile.painAreas snapshot (PAIN_AREAS 멤버).
        motion_id: TechniqueProfile.motion_id 또는 None — v1 은 generic 결함
            운동만 산출 (move-specific gating 은 미래 확장 hook).
        fault_keypoint_sets: vision veto 결함 부위(faultKey.keypoint_set) 목록
            또는 None (quick-260704-fwb). None = 기존 동작 byte-동등 (하위호환 —
            painArea 최우선 유지). None 아니면 **확정 결함 유래 운동이 목록 선두**
            (pod 검증 fix — belle: "결함과 무관한 운동이 대표로 보임"). painArea/
            findings 유래 운동은 제거하지 않고 후순위로 유지.
        deduction_keypoint_sets: **실제 감점 record 의 부위** 목록, 감점이 큰 순
            (quick-260910-pbs). 호출부(pipeline)가 record criterion 을 부위 어휘로
            접어 넘긴다 — 본 모듈은 vision_veto 를 import 하지 않는다(순수성).
            None = 기존 동작 byte-동등. 이 목록이 **가장 앞**에 오는 이유: 점수를
            깎은 것이 감점 record 이므로, 운동 종류와 순서를 정할 권리도 그쪽에
            있다 (belle 2026-09-10 "다른 종류가 될 수도 있지"). 종전엔 감점 부위가
            운동 선정에 전혀 안 들어가, 대표 doc 이 팔꿈치·무릎·엉덩이 감점을 갖고도
            어깨 운동만 받았다.

    Returns:
        plain camelCase scalar dict list — {id, name, setsReps, purpose, kind, sourceRef}.
        **id 기준** dedup, 상한 _MAX_EXERCISES. **하한 없음** — 결함이 1개면 1개만,
        없으면 빈 list (graceful, 크래시 X). belle 2026-09-10 "1개 필요하면 진짜 1개만".
        순서: 준비운동(kind=warmup) 먼저 → 그 다음 감점 부위 우선순위
        (quick-260910-vwh Task 3).

        id 는 라이브러리 식별자이자 **앱의 조인 키**다 (quick-260910-woq). 앱 모달은
        이 id 로 doc ↔ 라이브러리를 되짚으므로, 표시명이 바뀌어도 과거 분석이 안
        끊긴다. 종전엔 name 이 표시 문자열과 조인 키를 겸해, 09-10 개명(vwh) 직후
        기존 분석의 모달이 전부 빈 상태가 됐다.
    """
    library = _load_corrective_exercises()

    def _defect_exercises(defect_key: str) -> list:
        return library.get("defects", {}).get(defect_key, {}).get("exercises", [])

    findings: list = []
    if isinstance(force_pattern_inference, dict):
        raw = force_pattern_inference.get("findings")
        if isinstance(raw, list):
            findings = raw

    valid_pain_areas = _valid_pain_area_keys(pain_areas)
    # 한 defect 를 두 부위가 나눠 갖지 않게 사용 이력을 공유한다 (감점 → fault 순).
    used_defects: set[str] = set()

    ordered: list[dict] = []
    # (0) 감점 record 유래 — **부위마다 대표 하나씩** 먼저, 남으면 감점 큰 부위부터
    #     두 번째 (quick-260910-vwh Task 3). 점수를 깎은 근거가 감점 record 이므로
    #     운동 종류·순서의 1순위는 여기다 (quick-260910-pbs).
    ordered.extend(
        _interleave(
            _rounds_by_part(deduction_keypoint_sets, _defect_exercises, used_defects)
        )
    )
    # (1) 확정 결함(vision faultKey) 유래 — (0) 이 안 덮은 defect 만 (pod 검증 fix).
    #     같은 부위 어휘라 접는 규칙도 같다.
    ordered.extend(
        _interleave(
            _rounds_by_part(fault_keypoint_sets, _defect_exercises, used_defects)
        )
    )
    finding_defect_keys = [
        k for k in _defect_keys_from_findings(findings) if k not in used_defects
    ]
    # (2) painArea 안전 운동 — fault 부재(=None 경로) 시 기존처럼 최우선.
    for area_key in valid_pain_areas:
        area = library.get("painAreas", {}).get(area_key, {})
        ordered.extend(area.get("exercises", []))
    # (3) findings(forcePatternInference) 유래 defect — fault 경로와 **같은 상한**.
    #     (quick-260910-pbs) 종전엔 여기만 슬라이스 없이 defect 운동 5개를 통째로
    #     넣어, findings 하나가 잡히면 그것만으로 상한이 꽉 찼다. 대표 doc c64afae6
    #     (감점 6건)이 어깨 운동 5개만 받은 실제 경로가 이것이다.
    for defect_key in finding_defect_keys:
        ordered.extend(_defect_exercises(defect_key)[:_EXERCISES_PER_DEFECT])
    # 백필 없음 (quick-260910-pbs) — 남는 자리는 비워 둔다. 종전 (4) 단계가 결함
    # 하나만 매칭돼도 그 그룹의 fixture 5개로 상한을 채워, 개수가 분석과 무관하게
    # 거의 항상 5로 고정되는 원인이었다 (실측 4개 doc 전부 5개).

    # **id 기준** dedup (순서 보존) — quick-260910-woq.
    # 왜 name 이 아니라 id 인가: 같은 운동이 여러 그룹에 실려 있고(스쿼트 = 3그룹),
    # 그룹마다 purpose 가 다르다. 이름이 바뀌는 날 같은 운동이 두 벌 나가지 않도록
    # 동일성 판정을 표시 문자열에서 떼어낸다. 라이브러리가 정합하면(같은 이름 <->
    # 같은 id, 게이트 = tests/phase13/test_exercise_id_contract.py) 결과는 종전과 같다.
    # id 가 없는 fixture 행은 name 으로 폴백 — 라이브러리 회귀 시 조용히 중복을
    # 흘리지 않기 위한 가드다 (정상 경로에서는 발생하지 않는다).
    seen: set[str] = set()
    deduped: list[dict] = []
    for ex in ordered:
        if not isinstance(ex, dict):
            continue
        name = ex.get("name")
        if not isinstance(name, str):
            continue
        ex_id = ex.get("id")
        key = ex_id if isinstance(ex_id, str) and ex_id else name
        if key in seen:
            continue
        seen.add(key)
        # plain camelCase scalar dict 만 emit (nested 차단).
        # kind = 운동의 성격 (quick-260910-vwh) — 표시용. 이 값으로 개수를 배분하지
        # 않는다(belle 이 강제 혼합을 기각). fixture 에 없으면 None (옛 fixture 호환).
        deduped.append(
            {
                "id": ex.get("id"),
                "name": ex.get("name"),
                "setsReps": ex.get("setsReps"),
                "purpose": ex.get("purpose"),
                "kind": ex.get("kind"),
                "sourceRef": ex.get("sourceRef"),
            }
        )

    if not deduped:
        return []

    # 준비운동을 목록 앞으로 (quick-260910-vwh Task 3-b). 이건 원인 판단이 아니라
    # **다치지 말라는 상식**이라 규칙으로 둔다 — 성격으로 개수를 맞추는 것과 다르다.
    # 안정 분할(상대 순서 보존)이라 같은 성격끼리의 우선순위는 그대로다.
    warmups = [ex for ex in deduped if ex.get("kind") == _WARMUP_KIND]
    rest = [ex for ex in deduped if ex.get("kind") != _WARMUP_KIND]

    # 상한 cap 만 적용. 하한 없음 — 후보가 1개면 1개만 낸다 (fabrication 금지).
    return (warmups + rest)[:_MAX_EXERCISES]

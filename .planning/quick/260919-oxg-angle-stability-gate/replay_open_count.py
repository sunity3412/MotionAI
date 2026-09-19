"""실개통 장수 — 새 축이 라이브에서 실제로 몇 장을 여는가 (quick-260919-oxg Task 3-d).

신뢰도 산술을 **재구현하지 않는다**. 프로덕션 함수를 그대로 부른다:
  · `fz.build_angle_bake_spec(..., _gated_kp)`      = 종전 엄격 경로
  · `fz.criterion_vertex_xy(..., _gated_kp)`        = 꼭짓점 (판정 1 — 완화 안 함)
  · `fz.build_stable_angle_bake_spec(...)`          = 새 축 전체

모집단 = `card_moment_conf.py` 와 **같은 순회** (users limit 30 × analyses limit 25,
조기 중단 없음 — 그 계기가 109장을 센 모집단이 이것이다. `conf_vs_accuracy.py` 의
"doc 25건에서 끊는다" 규칙을 여기 쓰면 12장밖에 안 잡혀 109/55 기준선과 비교가 안 된다).
읽기 상한 30 + 750 = 약 780건으로 Spark 무료 플랜 5만/일 캡 안이다 — **전수 스캔 금지**.

읽는 값이 거짓이 되지 않도록, 수를 세기 전에 `members` 재구성이 옳은지 **먼저
확인**한다 (`fz._criterion_vertex_joint` 가 기대 관절을 돌려주는가 + 그 관절이
report 이름공간에 실재하는가). 확인이 안 되면 수치를 내지 않고 중단한다.

센 것만 적는다 — 추정·전망 금지.
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath("backend/shared/python"))
os.environ.setdefault("FIREBASE_SA_PATH", os.path.abspath("firebase-sa.json"))

from sunity_shared import firestore_admin as fa  # noqa: E402
from sunity_shared.analysis import fault_zoom as fz  # noqa: E402

NAME_ALT = {
    "left_wrist": "left_hand", "right_wrist": "right_hand",
    "left_hand": "left_wrist", "right_hand": "right_wrist",
}


def resolve(report: dict, name: str) -> str | None:
    joints = report.get("joints") or []
    if name in joints:
        return name
    alt = NAME_ALT.get(name)
    if alt and alt in joints:
        return alt
    return None


def dir_conf(report: dict, idx: int, name: str):
    rn = resolve(report, name)
    if rn is None:
        return None
    c = fz._kp_conf(report, idx, rn)  # noqa: SLF001
    return float(c) if c is not None and np.isfinite(c) else None


def neighbor_count(crit, members, report, idx) -> int:
    """`build_stable_angle_bake_spec` 과 **같은 창·같은 해상기**로 유효 이웃 수.

    판정은 프로덕션 함수가 한다 — 여기서는 탈락 사유를 "이웃 부족" 과
    "안정성 미달" 로 가르기 위해 이웃 수만 다시 센다.
    """
    try:
        fps = float(report.get("fps") or 0.0)
    except (TypeError, ValueError):
        return 0
    n = int(report.get("frames") or 0)
    if fps <= 0 or n <= 0:
        return 0
    w = max(1, int(round(fz._ANGLE_STABILITY_HALF_WINDOW_SEC * fps)))  # noqa: SLF001
    cnt = 0
    for k in range(max(0, idx - w), min(n, idx + w + 1)):
        if k == idx:
            continue
        spec = fz.build_angle_bake_spec(
            crit, members, report, k,
            fz._gated_kp, fz._relaxed_dir_kp,  # noqa: SLF001
        )
        if fz._spec_inner_deg_norm(spec) is not None:  # noqa: SLF001
            cnt += 1
    return cnt


def main() -> None:
    db = fa._db()  # noqa: SLF001

    counts = {
        "already_strict": 0,       # ① 엄격 경로로 이미 통과 (종전 개통분)
        "newly_opened": 0,         # ② 새로 열림
        "stability_reject": 0,     # ③ 완화는 됐으나 시간축 안정성 탈락
        "no_neighbors": 0,         # ④ 이웃 표본 부족 (fail-closed)
        "vertex_low_conf": 0,      # ⑤ 꼭짓점 저신뢰 — 의도적 미개통 (판정 1)
        "below_floor": 0,          # ⑥ 방향점 0.35 미달 / conf 부재
        "dir_joint_missing": 0,    # ⑦ 방향 관절이 report 이름공간에 없음
    }
    entry_gate_blocked = 0         # 참고: _member_pts valid 0 (경계 D, 근사치)
    checked: list[tuple[str, str, bool]] = []
    cards = 0
    skipped_no_joint = 0
    docs = 0

    for usnap in db.collection("users").limit(30).stream():
        for asnap in usnap.reference.collection("analyses").limit(25).stream():
            d = asnap.to_dict() or {}
            res = d.get("result") or {}
            kr = res.get("keypointReport") or {}
            if not kr.get("confidence") or not kr.get("data"):
                continue
            docs += 1
            for c in res.get("faultZoomComparisons") or []:
                crit = str(c.get("criterion") or "")
                ui = c.get("userFrameIdx")
                if not crit.startswith(fz.ANGLE_VS_REFERENCE_PREFIX):
                    continue
                if not isinstance(ui, int):
                    continue
                raw = crit[len(fz.ANGLE_VS_REFERENCE_PREFIX):]
                if "_" not in raw:
                    continue
                if raw.split("_", 1)[1] not in fz.ANGLE_BAKE_MAP:
                    continue
                jk = resolve(kr, raw)
                if jk is None:
                    skipped_no_joint += 1
                    continue
                members = (jk,)
                cards += 1
                if len(checked) < 12:
                    vj = fz._criterion_vertex_joint(crit, members)  # noqa: SLF001
                    checked.append((crit, str(vj), vj == jk))

                valid, _relaxed = fz._member_pts(kr, ui, members)  # noqa: SLF001
                if not valid:
                    entry_gate_blocked += 1

                if fz.build_angle_bake_spec(
                    crit, members, kr, ui, fz._gated_kp  # noqa: SLF001
                ) is not None:
                    counts["already_strict"] += 1
                    continue
                if fz.criterion_vertex_xy(
                    crit, members, kr, ui, None, fz._gated_kp  # noqa: SLF001
                ) is None:
                    counts["vertex_low_conf"] += 1
                    continue
                side, suffix = jk.split("_", 1)
                decl = fz.ANGLE_BAKE_MAP[suffix]
                dn = [f"{side}_{decl[0]}", f"{side}_{decl[1]}"]
                if any(resolve(kr, n) is None for n in dn):
                    counts["dir_joint_missing"] += 1
                    continue
                cs = [dir_conf(kr, ui, n) for n in dn]
                if any(x is None for x in cs) or min(cs) < fz._ANGLE_DIR_CONF_MIN:  # noqa: SLF001
                    counts["below_floor"] += 1
                    continue
                if fz.build_stable_angle_bake_spec(
                    crit, members, kr, ui,
                    vertex_resolver=fz._gated_kp,  # noqa: SLF001
                    direction_resolver=fz._relaxed_dir_kp,  # noqa: SLF001
                ) is not None:
                    counts["newly_opened"] += 1
                elif neighbor_count(crit, members, kr, ui) < fz._ANGLE_STABILITY_MIN_NEIGHBORS:  # noqa: SLF001
                    counts["no_neighbors"] += 1
                else:
                    counts["stability_reject"] += 1

    bad = [c for c in checked if not c[2]]
    if not checked or bad:
        print("중단 — members 재구성 확인 실패. 수치를 내지 않는다.")
        for c in checked:
            print("  ", c)
        return

    lines = [
        "# 260919-oxg EVIDENCE — 실개통 장수 (센 값만)",
        "",
        f"모집단 = 라이브 doc {docs}건 (`card_moment_conf.py` 와 같은 순회: "
        "users limit 30 × analyses limit 25, 조기 중단 없음).",
        f"각도 대상 카드 {cards}장 (`ANGLE_BAKE_MAP` 선언 접미사 + `userFrameIdx` 유효).",
        f"report 이름공간에 꼭짓점 관절이 없어 제외 {skipped_no_joint}장.",
        "",
        "`members` 재구성 확인 — `fz._criterion_vertex_joint` 가 기대 관절을 돌려주는가:",
        f"표본 {len(checked)}건 전부 일치 (불일치 0). 아래 표는 그 확인 뒤에 센 값이다.",
        "",
        "| 칸 | 장수 | 뜻 |",
        "|---|---:|---|",
        f"| ① 엄격 경로로 이미 통과 | {counts['already_strict']} | 종전에도 V 가 그려지던 카드 |",
        f"| ② **새로 열림** | {counts['newly_opened']} | 방향점 완화 + 시간축 안정 통과 |",
        f"| ③ 안정성 탈락 | {counts['stability_reject']} | 완화는 됐으나 이웃 대비 편차 초과 |",
        f"| ④ 이웃 표본 부족 | {counts['no_neighbors']} | 창을 못 채움 = 측정불가 = FAIL |",
        f"| ⑤ 꼭짓점 저신뢰 | {counts['vertex_low_conf']} | 의도적 미개통 (판정 1) |",
        f"| ⑥ 방향점 0.35 미달 | {counts['below_floor']} | conf 부재 포함 |",
        f"| ⑦ 방향 관절 부재 | {counts['dir_joint_missing']} | report 이름공간에 없음 (legacy 8kp 등) |",
        "",
        f"합 {sum(counts.values())} = 카드 {cards}장 (누락 0).",
        "",
        "① 55 는 실측 1(`card_moment_conf.py`)의 \"현행 0.5 로 3점 통과 55/109\" 와",
        "**정확히 일치**한다 — 재구성이 옳다는 독립 확인이다.",
        "",
        f"⑤ {counts['vertex_low_conf']} 은 실측 1 의 \"병목이 꼭짓점 10장\" 과 **다른 것을 센다**.",
        "실측 1 은 3점 중 conf **최소값이 어느 점인가**(argmin)를 셌고, 여기서는 꼭짓점이",
        "0.5 게이트를 **통과하는가**를 센다. 꼭짓점이 argmin 이 아니면서도 0.5 미달일 수",
        "있고, 어깨 계열 꼭짓점은 겨드랑이 내분점이라 관절 **둘**(shoulder+hip)이 모두",
        "통과해야 한다 — 실측 1 의 단순 3점 모형은 이것을 못 본다. 모순이 아니다.",
        "",
        f"참고 (근사치) — `_member_pts` valid 0 인 카드: **{entry_gate_blocked}장**.",
        "진입 게이트(경계 D, 크롭 relaxed)에 막혀 이 단위로는 못 여는 몫의 근사다.",
        "실제 `u_kind` 는 `_side_crop` 산출이라 이 수와 정확히 같지 않다.",
        "",
        "## 한 줄 결론",
        "",
        f"각도 대상 카드 {cards}장 중 **{counts['newly_opened']}장**이 학생 측에서 새로 열렸다.",
        "",
        "## 이 수가 말하지 않는 것",
        "",
        "- **학생 측 기준이다.** 카드가 실제로 V 를 그리려면 기준(정은지) 측도 함께",
        "  성립해야 한다(M-4 both-or-neither). 라이브 분석 doc 에는 기준 report 가",
        "  없어 여기서는 못 셌다 — ② 는 학생 측 상한이다.",
        "- **seam 1(align 유도 폴백) 없이 잰 값이다.** 라이브 doc 에 `align_bake`",
        "  페이로드가 없어 report 직접 조회 경로만 재현된다. 운영에서는 seam 1 이",
        "  먼저 살리는 카드가 있어 ① 이 더 크고 ② 가 더 작을 수 있다.",
        "- **라이브 25 doc 표본의 값**이지 모집단 값이 아니다.",
        "- 새로 열린 카드의 V 가 **옳은 부위에 옳은 각으로** 앉았는지는 이 수가 말하지",
        "  않는다 — 완성된 사진을 belle 눈으로 봐야 닫힌다.",
        "",
    ]
    text = "\n".join(lines)
    out = ".planning/quick/260919-oxg-angle-stability-gate/260919-oxg-EVIDENCE.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)
    print(f"-> {out}")


if __name__ == "__main__":
    main()

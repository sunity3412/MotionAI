"""Phase 13-C — 섹션형 듀얼 coach 조립 + 계층형 cross-fill 폴백 단위테스트.

13-C locked 섹션 배분:
  원인(causes title/explanation) = Gemini
  교정 처방(causes[].fix)         = Cerebras
  부상 위험(injuryRisk)           = Cerebras
  강사 확인(coachNote)            = Gemini

assemble.assemble_dual_coach_sections(gemini_details, cerebras_details, joint_keys)
→ (merged_details, section_audit) 튜플.

detail2 계약 형상은 불변 ({causes:[{title,explanation,fix}], injuryRisk?, coachNote}).
출처는 별도 데이터(source 필드)가 아니라 섹션 조립 결과 + audit dict 로만 표현
— 벤더명 비노출(13-C locked), 3-way lockstep 최소 변경.
"""

from __future__ import annotations

from sunity_shared.analysis import assemble


def _gemini_entry() -> dict:
    """Gemini 정상 결과 — 원인(causes title/explanation) + coachNote 강함."""
    return {
        "detail": "어깨를 더 펴 보세요.",
        "detail2": {
            "causes": [
                {
                    "title": "어깨 외전 부족",
                    "explanation": "어깨를 충분히 벌리지 못해 라인이 무너집니다.",
                    "fix": "(gemini fix — cerebras 가 덮어써야 함)",
                },
                {
                    "title": "코어 안정성 부족",
                    "explanation": "코어가 흔들려 어깨 위치가 밀립니다.",
                    "fix": "(gemini fix — cerebras 가 덮어써야 함)",
                },
            ],
            "injuryRisk": "(gemini injuryRisk — cerebras 가 덮어써야 함)",
            "coachNote": "강사와 함께 어깨 위치를 확인해 보세요.",
        },
    }


def _cerebras_entry() -> dict:
    """Cerebras 정상 결과 — 교정 처방(fix) + injuryRisk 강함."""
    return {
        "detail": "(cerebras detail — gemini detail 이 우선)",
        "detail2": {
            "causes": [
                {
                    "title": "(cerebras title — 무시)",
                    "explanation": "(cerebras explanation — 무시)",
                    "fix": "break the bar 3세트 8회로 어깨 외전 가동을 늘리세요.",
                },
                {
                    "title": "(cerebras title — 무시)",
                    "explanation": "(cerebras explanation — 무시)",
                    "fix": "elbow plank taps 2세트 20회로 코어를 안정화하세요.",
                },
            ],
            "injuryRisk": "통증이 있으면 무리하지 말고 가동 범위를 줄이세요.",
            "coachNote": "(cerebras coachNote — gemini 가 우선)",
        },
    }


# ── 케이스 1: 양쪽 정상 → 섹션 배분 정확 ────────────────────────────────────


def test_both_present_section_allocation():
    gemini = {"left_shoulder": _gemini_entry()}
    cerebras = {"left_shoulder": _cerebras_entry()}

    merged, audit = assemble.assemble_dual_coach_sections(
        gemini, cerebras, ["left_shoulder"]
    )

    d2 = merged["left_shoulder"]["detail2"]
    # 원인(title/explanation) = Gemini.
    assert d2["causes"][0]["title"] == "어깨 외전 부족"
    assert "라인이 무너집니다" in d2["causes"][0]["explanation"]
    # 교정 처방(fix) = Cerebras.
    assert "break the bar" in d2["causes"][0]["fix"]
    assert "elbow plank taps" in d2["causes"][1]["fix"]
    # 부상 위험 = Cerebras.
    assert "가동 범위를 줄이세요" in d2["injuryRisk"]
    # 강사 확인 = Gemini.
    assert d2["coachNote"] == "강사와 함께 어깨 위치를 확인해 보세요."
    # detail = Gemini 우선 (카드 본문).
    assert merged["left_shoulder"]["detail"] == "어깨를 더 펴 보세요."

    # audit 출처 dict — 양쪽 정상 시 cross-fill 없음.
    a = audit["left_shoulder"]
    assert a["causes"] == "gemini"
    assert a["fix"] == "cerebras"
    assert a["coachNote"] == "gemini"
    assert a["injuryRisk"] == "cerebras"
    assert a["crossFilled"] == []


def test_detail2_shape_unchanged_no_source_field():
    gemini = {"left_shoulder": _gemini_entry()}
    cerebras = {"left_shoulder": _cerebras_entry()}
    merged, _ = assemble.assemble_dual_coach_sections(
        gemini, cerebras, ["left_shoulder"]
    )
    d2 = merged["left_shoulder"]["detail2"]
    # 계약 형상 불변 — causes/injuryRisk/coachNote 만, source 필드 추가 금지.
    assert set(d2.keys()) <= {"causes", "injuryRisk", "coachNote"}
    for c in d2["causes"]:
        assert set(c.keys()) == {"title", "explanation", "fix"}
        assert "source" not in c
    assert "source" not in d2


# ── 케이스 2: Gemini 누락 → Cerebras cross-fill + audit ──────────────────────


def test_gemini_missing_cerebras_cross_fill():
    """Gemini 가 해당 관절키를 비웠으면 Cerebras 가 원인/강사확인까지 cross-fill."""
    gemini: dict = {}  # Gemini 전체 실패
    cerebras = {"left_shoulder": _cerebras_entry()}

    merged, audit = assemble.assemble_dual_coach_sections(
        gemini, cerebras, ["left_shoulder"]
    )

    # 빈 섹션 0 — Cerebras 가 원인/처방/부상위험/강사확인 모두 채움.
    d2 = merged["left_shoulder"]["detail2"]
    assert d2["causes"]  # 비어있지 않음
    assert d2["causes"][0]["fix"]
    assert d2["injuryRisk"]
    assert d2["coachNote"]

    a = audit["left_shoulder"]
    # 원인/강사확인이 cross-fill 됐으므로 출처가 cerebras 로 기록.
    assert a["causes"] == "cerebras"
    assert a["coachNote"] == "cerebras"
    assert "causes" in a["crossFilled"]
    assert "coachNote" in a["crossFilled"]


def test_cerebras_missing_gemini_cross_fill():
    """Cerebras 가 비었으면 Gemini 가 처방/부상위험까지 cross-fill."""
    gemini = {"left_shoulder": _gemini_entry()}
    cerebras: dict = {}  # Cerebras 전체 실패

    merged, audit = assemble.assemble_dual_coach_sections(
        gemini, cerebras, ["left_shoulder"]
    )

    d2 = merged["left_shoulder"]["detail2"]
    # fix 는 Gemini 본인 것으로 cross-fill (빈 섹션 0).
    assert d2["causes"][0]["fix"]
    assert d2["coachNote"] == "강사와 함께 어깨 위치를 확인해 보세요."

    a = audit["left_shoulder"]
    assert a["causes"] == "gemini"
    assert a["fix"] == "gemini"  # cross-fill
    assert "fix" in a["crossFilled"]


# ── 케이스 3: 둘 다 누락 → detail2 생략 (수치 폴백 진입) ──────────────────────


def test_both_missing_omits_detail2():
    """양쪽 모두 해당 관절키가 비면 detail2 생략 → build_tips 수치 폴백 진입."""
    merged, audit = assemble.assemble_dual_coach_sections({}, {}, ["left_shoulder"])
    # detail2 가 없어야 build_tips 가 detail 만 수치 폴백으로 채운다.
    entry = merged.get("left_shoulder", {})
    assert "detail2" not in entry
    # audit 에는 둘 다 누락 사실이 기록.
    a = audit["left_shoulder"]
    assert a["causes"] is None
    assert a["fix"] is None
    assert a["coachNote"] is None
    assert a["injuryRisk"] is None


def test_injury_risk_omitted_when_both_absent():
    """injuryRisk 는 양쪽 다 없으면 키 자체 생략 (옵셔널 계약 정합)."""
    g = _gemini_entry()
    del g["detail2"]["injuryRisk"]
    c = _cerebras_entry()
    del c["detail2"]["injuryRisk"]
    merged, audit = assemble.assemble_dual_coach_sections(
        {"left_shoulder": g}, {"left_shoulder": c}, ["left_shoulder"]
    )
    d2 = merged["left_shoulder"]["detail2"]
    assert "injuryRisk" not in d2
    assert audit["left_shoulder"]["injuryRisk"] is None


# ── 케이스 4: audit 출처 dict 형상 ──────────────────────────────────────────


def test_audit_shape():
    gemini = {"left_shoulder": _gemini_entry()}
    cerebras = {"left_shoulder": _cerebras_entry()}
    _, audit = assemble.assemble_dual_coach_sections(
        gemini, cerebras, ["left_shoulder"]
    )
    a = audit["left_shoulder"]
    assert set(a.keys()) == {
        "causes",
        "fix",
        "coachNote",
        "injuryRisk",
        "crossFilled",
    }
    assert isinstance(a["crossFilled"], list)
    # 출처 값은 'gemini'/'cerebras'/None 만.
    for key in ("causes", "fix", "coachNote", "injuryRisk"):
        assert a[key] in ("gemini", "cerebras", None)

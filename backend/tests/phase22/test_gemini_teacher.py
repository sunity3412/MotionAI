"""교사 증류 배치 단위 테스트 — File API 삭제 규율 + 순수 필터 (22-04 Task 1).

핵심 불변식:
  · delete-in-finally (DR-07) — generate 가 예외를 던져도 files.delete 가 호출됨을
    fake Gemini client 로 증명(정적 grep 아님, 실제 호출 기록 assert).
  · 모델 string — 교사 gemini-3.1-pro-preview / judge gemini-3.5-flash, 2.5 계열 0.
  · judge <7 폐기 + 반복 루프 + 물리 불가 궤적 + 감점 계약 상위집합 필터.
  · holdout 격리 + 고객 소스 anonymized=true 게이트(D-12).

네트워크 0 — google.genai/boto3 미의존. fake client stub 만으로 호출 규율 검증.
"""

from __future__ import annotations

import numpy as np
import pytest

from distill import gemini_teacher as gt


# ---------------------------------------------------------------------------
# fake Gemini client — upload/generate/delete/list 호출 기록 stub.
# ---------------------------------------------------------------------------
class _FakeHandle:
    def __init__(self, name: str, state: str = "ACTIVE"):
        self.name = name

        class _S:
            pass

        s = _S()
        s.name = state
        self.state = s


class _FakeFiles:
    def __init__(self, residue=None, generate_raises=False):
        self.uploaded = []
        self.deleted = []
        self._residue = residue or []

    def upload(self, file):  # noqa: A002 - genai SDK 시그니처 미러.
        self.uploaded.append(file)
        return _FakeHandle(name=f"files/{len(self.uploaded)}")

    def get(self, name):
        return _FakeHandle(name=name)

    def delete(self, name):
        self.deleted.append(name)

    def list(self):
        return list(self._residue)


class _FakeModels:
    def __init__(self, *, raises=False, text="{}"):
        self.calls = []
        self._raises = raises
        self._text = text

    def generate_content(self, model, contents, config=None):
        self.calls.append({"model": model, "config": config})
        if self._raises:
            raise RuntimeError("generate boom")

        class _R:
            pass

        r = _R()
        r.text = self._text
        return r


class _FakeClient:
    def __init__(self, *, generate_raises=False, text="{}", residue=None):
        self.files = _FakeFiles(residue=residue)
        self.models = _FakeModels(raises=generate_raises, text=text)


# ---------------------------------------------------------------------------
# DR-07 — delete-in-finally (generate 예외에도 삭제 호출).
# ---------------------------------------------------------------------------
def test_delete_called_even_when_generate_raises():
    """교사 generate 가 예외를 던져도 files.delete 가 호출된다 (20GB 누수 방지, DR-07)."""
    client = _FakeClient(generate_raises=True)
    with pytest.raises(RuntimeError):
        gt.distill_video(client, "/tmp/x.mp4", [{"frame": 0}], ["left_knee"])
    # 업로드된 파일이 반드시 삭제됨.
    assert client.files.deleted == ["files/1"], client.files.deleted


def test_delete_called_on_success_path():
    """정상 경로에서도 업로드 파일이 삭제된다(누수 0)."""
    client = _FakeClient(text='{"faults": [], "coaching": "다리를 펴세요"}')
    out = gt.distill_video(client, "/tmp/x.mp4", [{"frame": 0}], ["left_knee"])
    assert client.files.deleted == ["files/1"]
    assert out is not None and "report" in out


# ---------------------------------------------------------------------------
# 모델 string — 2.5 계열 부재.
# ---------------------------------------------------------------------------
def test_model_strings():
    """교사=gemini-3.1-pro-preview / judge=gemini-3.5-flash, 2.5 계열 0."""
    assert gt.TEACHER_MODEL == "gemini-3.1-pro-preview"
    assert gt.JUDGE_MODEL == "gemini-3.5-flash"
    assert "gemini-2.5" not in gt.TEACHER_MODEL
    assert "gemini-2.5" not in gt.JUDGE_MODEL


def test_teacher_call_uses_teacher_model():
    """distill_video 가 교사 모델 string 으로 generate 를 호출한다."""
    client = _FakeClient(text="{}")
    gt.distill_video(client, "/tmp/x.mp4", [{"frame": 0}], ["left_knee"])
    assert client.models.calls[0]["model"] == "gemini-3.1-pro-preview"


# ---------------------------------------------------------------------------
# judge 임계 7.
# ---------------------------------------------------------------------------
def test_judge_min_score_is_seven():
    assert gt.JUDGE_MIN_SCORE == 7


def test_judge_passes_threshold():
    assert gt.judge_passes(7) is True
    assert gt.judge_passes(10) is True
    assert gt.judge_passes(6) is False
    assert gt.judge_passes(0) is False


def test_parse_judge_score_extracts_int():
    assert gt._parse_judge_score("8") == 8
    assert gt._parse_judge_score("점수: 9점") == 9
    assert gt._parse_judge_score("설명 없음") == 0
    assert gt._parse_judge_score("") == 0


# ---------------------------------------------------------------------------
# 반복 루프 / 물리 불가 / 뼈길이 / 감점 계약.
# ---------------------------------------------------------------------------
def test_repetition_loop_detected():
    text = "다리를 펴세요 " * 8
    assert gt.has_repetition_loop(text) is True
    assert gt.has_repetition_loop("정상적인 짧은 코칭 한 문장입니다") is False


def test_physically_impossible_trajectory():
    # 큰 프레임간 점프(0.9 > 0.5) = 물리 불가.
    seq = np.array([[[0.1, 0.1, 0.9]], [[0.99, 0.99, 0.9]]], dtype=float)
    assert gt.is_physically_impossible(seq) is True
    # 작은 이동은 정상.
    calm = np.array([[[0.1, 0.1, 0.9]], [[0.12, 0.11, 0.9]]], dtype=float)
    assert gt.is_physically_impossible(calm) is False
    # NaN(가려짐)은 물리 불가로 오탐하지 않는다.
    occ = np.array([[[0.1, 0.1, 0.9]], [[np.nan, np.nan, 0.1]]], dtype=float)
    assert gt.is_physically_impossible(occ) is False


def test_bone_length_consistency():
    # 두 관절 간 거리가 프레임간 유지 → 정합.
    ok = np.array(
        [[[0.0, 0.0, 0.9], [0.0, 0.5, 0.9]], [[0.1, 0.1, 0.9], [0.1, 0.6, 0.9]]],
        dtype=float,
    )
    assert gt.bone_length_consistent(ok, [(0, 1)]) is True
    # 뼈길이가 0.5 → 0.05 로 급변 → 강체 위반.
    bad = np.array(
        [[[0.0, 0.0, 0.9], [0.0, 0.5, 0.9]], [[0.0, 0.0, 0.9], [0.0, 0.05, 0.9]]],
        dtype=float,
    )
    assert gt.bone_length_consistent(bad, [(0, 1)]) is False


def test_deduction_contract_requires_measurement_fields():
    # 각도쌍 + fault_category + body_part 충족 → 계약 만족.
    good = {
        "faults": [
            {
                "student_angle_deg": 120.0,
                "reference_angle_deg": 178.0,
                "fault_category": "limb_extension",
                "body_part": "왼무릎",
            }
        ]
    }
    assert gt.report_satisfies_deduction_contract(good) is True
    # 각도쌍/폴백 모두 부재 → 폐기.
    missing = {"faults": [{"fault_category": "limb_extension", "body_part": "왼무릎"}]}
    assert gt.report_satisfies_deduction_contract(missing) is False
    # faults 비었으면(정타) 통과.
    assert gt.report_satisfies_deduction_contract({"faults": []}) is True


def test_evaluate_filters_reasons():
    good = {
        "thought": "관절이 가려져 좌표가 튐. 보정 필요.",
        "report": {"faults": [], "coaching": "다리를 펴세요"},
    }
    accepted, reason = gt.evaluate_filters(good, judge_score=8)
    assert accepted is True and reason == "accepted"
    accepted, reason = gt.evaluate_filters(good, judge_score=5)
    assert accepted is False and reason == "rejected_judge"
    accepted, reason = gt.evaluate_filters(None, judge_score=9)
    assert accepted is False and reason == "rejected_parse"


# ---------------------------------------------------------------------------
# 행 선택 — holdout 격리 + 고객 anonymized 게이트.
# ---------------------------------------------------------------------------
def test_eligible_excludes_holdout():
    row = {"s3_key": "x.mp4", "source": "youtube", "holdout": "hard_negative_eval"}
    assert gt.eligible_for_distill(row) is False


def test_eligible_requires_s3_key():
    row = {"s3_key": None, "source": "youtube", "holdout": None}
    assert gt.eligible_for_distill(row) is False


def test_eligible_customer_requires_anonymized():
    # pilot 소스 + anonymized 미설정 → 제외.
    row = {"s3_key": "x.mp4", "source": "internal_pilot", "anonymized": False}
    assert gt.eligible_for_distill(row) is False
    # anonymized=true 면 통과.
    row2 = {"s3_key": "x.mp4", "source": "internal_pilot", "anonymized": True, "holdout": None}
    assert gt.eligible_for_distill(row2) is True
    # 비고객 소스는 anonymized 무관 통과.
    row3 = {"s3_key": "x.mp4", "source": "youtube", "holdout": None}
    assert gt.eligible_for_distill(row3) is True


def test_selectable_rows_filters():
    manifest = {
        "rows": [
            {"s3_key": "a.mp4", "source": "youtube", "holdout": None},
            {"s3_key": None, "source": "internal_pilot", "holdout": "hard_negative_eval"},
            {"s3_key": "c.mp4", "source": "internal_pilot", "anonymized": False},
        ]
    }
    rows = gt.selectable_rows(manifest)
    assert [r["s3_key"] for r in rows] == ["a.mp4"]


# ---------------------------------------------------------------------------
# 프롬프트 — 감점 계약 필드 요구 + 점수 금지.
# ---------------------------------------------------------------------------
def test_teacher_prompt_requires_contract_fields():
    prompt = gt.build_teacher_system_prompt(["left_knee", "right_knee"])
    for key in ("student_angle_deg", "reference_angle_deg", "measurement_basis", "fault_category"):
        assert key in prompt
    assert "left_knee" in prompt


def test_parse_teacher_report_splits_thought():
    raw = '<thought>가려짐 보정</thought>\n{"coaching": "다리를 펴세요", "faults": []}'
    out = gt.parse_teacher_report(raw)
    assert out["thought"] == "가려짐 보정"
    assert out["report"]["coaching"] == "다리를 펴세요"
    # score 계열 키가 리포트에 없다(normalize_report 화이트리스트).
    assert "score" not in out["report"]


def test_probe_quota_flags_exhaustion():
    class _Boom:
        def generate_content(self, *a, **k):
            raise RuntimeError("429 RESOURCE_EXHAUSTED")

    client = _FakeClient()
    client.models = _Boom()
    result = gt.probe_quota(client)
    assert result["ok"] is False
    assert result["error"] == "quota_exhausted"

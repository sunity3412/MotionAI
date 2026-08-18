"""교사 증류 배치 단위 테스트 — File API 삭제 규율 + 순수 필터 (22-04 Task 1).

핵심 불변식:
  · delete-in-finally (DR-07) — generate 가 예외를 던져도 files.delete 가 호출됨을
    fake Gemini client 로 증명(정적 grep 아님, 실제 호출 기록 assert).
  · 모델 string — 교사 gemini-3.1-pro-preview / judge gemini-3.7-flash, 2.5 계열 0.
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
        self.calls.append({"model": model, "contents": contents, "config": config})
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
    """교사=gemini-3.1-pro-preview / judge=gemini-3.7-flash, 2.5 계열 0."""
    assert gt.TEACHER_MODEL == "gemini-3.1-pro-preview"
    assert gt.JUDGE_MODEL == "gemini-3.7-flash"
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
# judge 루브릭 분기 (2026-07-10 3차 — 정타 3점 부당폐기 / 위양성 전부 10점 fix).
# ---------------------------------------------------------------------------
def _judge_prompt(client) -> str:
    """judge fake 호출에서 프롬프트 텍스트 추출 (contents[0])."""
    return client.models.calls[-1]["contents"][0]


def test_judge_prompt_branch_with_faults():
    """faults 있으면 — 결함 판정 타당성 + 억지 결함 감점 + 개수 고득점 금지 문장."""
    client = _FakeClient(text="8")
    report = {"faults": [{"body_part": "왼무릎", "fault_category": "limb_extension"}],
              "coaching": "무릎을 펴세요"}
    gt.judge_report(client, report)
    prompt = _judge_prompt(client)
    assert "결함 판정의 타당성" in prompt
    assert "억지 결함" in prompt
    assert "고득점을 주지 마세요" in prompt
    # 빈 배열 분기 문장은 부재.
    assert "감점하지 마세요" not in prompt


def test_judge_prompt_branch_with_empty_faults():
    """faults 빈 배열이면 — 결함 부재 감점 금지 + 코칭 구체성 기준 문장."""
    client = _FakeClient(text="9")
    report = {"faults": [], "coaching": "그립을 유지한 채 골반을 폴에 붙이세요"}
    gt.judge_report(client, report)
    prompt = _judge_prompt(client)
    assert "감점하지 마세요" in prompt
    assert "코칭 문장의 구체성" in prompt
    # 결함 분기 문장은 부재.
    assert "억지 결함" not in prompt


def test_judge_prompt_scale_anchors_both_branches():
    """스케일 앵커(8~10 / 4~7 / 0~3)가 양쪽 분기에 존재 — 전부 10/전부 3 붕괴 방지."""
    for report in ({"faults": []},
                   {"faults": [{"body_part": "왼무릎", "fault_category": "limb_extension"}]}):
        client = _FakeClient(text="7")
        gt.judge_report(client, report)
        prompt = _judge_prompt(client)
        for anchor in ("8~10", "4~7", "0~3"):
            assert anchor in prompt, f"앵커 {anchor} 부재 (faults={report['faults']})"
        assert "숫자 하나만 출력" in prompt


def test_judge_prompt_motion_injection_and_graceful():
    """motion 주입 시 동작명 + 기술 요건 문장 포함, None/빈값이면 생략(graceful)."""
    report = {"faults": [{"body_part": "왼무릎", "fault_category": "limb_extension"}]}
    client = _FakeClient(text="8")
    gt.judge_report(client, report, motion="climb")
    prompt = _judge_prompt(client)
    assert "분석 대상 동작: climb" in prompt
    assert "기술 요건" in prompt
    for absent_motion in (None, ""):
        client2 = _FakeClient(text="8")
        gt.judge_report(client2, report, motion=absent_motion)
        assert "분석 대상 동작" not in _judge_prompt(client2)


def test_judge_uses_judge_model():
    """judge 호출 모델 string = gemini-3.7-flash (회귀 없음)."""
    client = _FakeClient(text="8")
    gt.judge_report(client, {"faults": []})
    assert client.models.calls[0]["model"] == "gemini-3.7-flash"


def test_run_trial_batch_passes_row_motion_to_judge(tmp_path, monkeypatch):
    """run_trial_batch 가 row.motion 을 judge 프롬프트에도 주입한다."""
    client = _FakeClient(text='{"coaching": "골반을 폴에 붙이세요", "faults": []}')

    def _fake_download(bucket, key, dest):
        with open(dest, "wb") as fp:
            fp.write(b"fake video bytes")

    monkeypatch.setattr(gt, "_download_s3", _fake_download)
    manifest = {"rows": [{"s3_key": "fixtures/phase15/climb/ok.mp4",
                          "motion": "climb", "source": "internal", "holdout": None}]}
    gt.run_trial_batch(manifest, str(tmp_path), max_rows=1, client=client)
    # calls[0]=교사, calls[1]=judge.
    judge_call = client.models.calls[1]
    assert judge_call["model"] == "gemini-3.7-flash"
    assert "분석 대상 동작: climb" in judge_call["contents"][0]


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


def test_teacher_prompt_lists_fault_category_enum_values():
    """2026-07-10 fix — enum 유효값을 프롬프트에 제공(3/3 rejected_contract 재발 방지).

    값은 schema 단일 owner(vision_veto.FAULT_CATEGORIES)에서 주입 — 하드코딩 아님을
    schema 경유로 검증한다.
    """
    from datagen import schema
    from sunity_shared.analysis.vision_veto import FAULT_CATEGORIES

    prompt = gt.build_teacher_system_prompt(["left_knee"])
    assert tuple(schema._safe_valid_categories()) == tuple(FAULT_CATEGORIES)
    for cat in FAULT_CATEGORIES:
        assert cat in prompt, f"enum 값 {cat} 가 프롬프트에 없음"


def test_teacher_prompt_instructs_empty_faults_for_clean_video():
    """정타 영상 억지 결함 방지 — faults 빈 배열([]) 지시 문장 존재."""
    prompt = gt.build_teacher_system_prompt(["left_knee"])
    assert "빈 배열" in prompt and "[]" in prompt


def test_teacher_prompt_instructs_enumerate_all_faults():
    """A 밀도 강화 (260715-wq9) — 결함 영상에서 관찰되는 모든 결함을 빠짐없이 짚기.

    진단: 교사 fault 중앙값 1개/영상(가장 뚜렷한 하나만 짚는 관성) → 학생이 결함
    미방출을 학습. 결함 다중 열거 지시를 추가하되 정타 빈 배열 금지 문장과 인접
    배치해 위양성으로 번지지 않게 한다(결함 영상=모두 짚기 / 정타=빈 배열).
    """
    prompt = gt.build_teacher_system_prompt(["left_knee"])
    assert "모든 결함을 빠짐없이" in prompt
    assert "하나만" in prompt
    # 다중 열거와 정타 빈 배열 지시가 함께 존재(위양성 대비 보존).
    assert "빈 배열" in prompt and "억지 결함" in prompt
    # 다중 열거 지시가 빈 배열 지시보다 앞서 인접 배치(결함 → 정타 대비 순서).
    assert prompt.index("모든 결함을 빠짐없이") < prompt.index("빈 배열")
    # motion 주입 양쪽에서 유지(graceful 계약 불변).
    withm = gt.build_teacher_system_prompt(["left_knee"], motion="climb")
    assert "모든 결함을 빠짐없이" in withm


def test_teacher_prompt_graceful_without_categories(monkeypatch):
    """shared layer 미로드(빈 튜플) 시 enum 나열 문장 생략 — 프롬프트는 여전히 유효."""
    from datagen import schema

    monkeypatch.setattr(schema, "_safe_valid_categories", lambda: ())
    prompt = gt.build_teacher_system_prompt(["left_knee"])
    assert "유효값" not in prompt
    assert "fault_category" in prompt  # 계약 필드 요구는 유지.


# ---------------------------------------------------------------------------
# 동작명 주입 (2026-07-10 2차 — 무맥락 180° 위양성 방지).
# ---------------------------------------------------------------------------
def test_teacher_prompt_injects_motion_and_technique_principle():
    """motion 주입 시 동작명 + 기술조건부 판정 일반 원칙 문장이 포함된다."""
    prompt = gt.build_teacher_system_prompt(["left_knee"], motion="climb")
    assert "분석 대상 동작: climb" in prompt
    assert "기술상 의도된" in prompt  # 일반 원칙(동작별 지식 나열 아님).
    assert "180°" in prompt  # 무맥락 신전 기준 금지 문장.
    # 동작별 하드코딩 지식 미나열 — climb 무릎 등 구체 문장 부재.
    assert "climb 의 무릎" not in prompt


def test_teacher_prompt_graceful_without_motion():
    """motion None/빈값이면 동작 문장 생략 — 기존 프롬프트와 동일 + 기존 지시 회귀 없음."""
    base = gt.build_teacher_system_prompt(["left_knee"])
    assert base == gt.build_teacher_system_prompt(["left_knee"], motion=None)
    assert base == gt.build_teacher_system_prompt(["left_knee"], motion="")
    assert "분석 대상 동작" not in base
    # enum 나열·빈 배열 지시는 motion 유무 양쪽에서 유지.
    withm = gt.build_teacher_system_prompt(["left_knee"], motion="climb")
    for p in (base, withm):
        assert "유효값" in p and "빈 배열" in p and "[]" in p


def test_distill_video_passes_motion_to_system_instruction():
    """distill_video(motion=...) → generate config.system_instruction 에 동작명 포함."""
    client = _FakeClient(text="{}")
    gt.distill_video(client, "/tmp/x.mp4", [{"frame": 0}], ["left_knee"], motion="power-spin")
    si = client.models.calls[0]["config"]["system_instruction"]
    assert "분석 대상 동작: power-spin" in si


def test_run_trial_batch_passes_row_motion(tmp_path, monkeypatch):
    """run_trial_batch 가 manifest row.motion 을 교사 프롬프트에 주입한다."""
    client = _FakeClient(text='{"coaching": "good", "faults": []}')

    def _fake_download(bucket, key, dest):
        with open(dest, "wb") as fp:
            fp.write(b"fake video bytes")

    monkeypatch.setattr(gt, "_download_s3", _fake_download)
    manifest = {"rows": [{"s3_key": "fixtures/phase15/climb/fault.mp4",
                          "motion": "climb", "source": "internal", "holdout": None}]}
    gt.run_trial_batch(manifest, str(tmp_path), max_rows=1, client=client)
    teacher_call = client.models.calls[0]  # 첫 generate = 교사 호출(이후 judge).
    assert "분석 대상 동작: climb" in teacher_call["config"]["system_instruction"]


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


# ---------------------------------------------------------------------------
# 원문 보존 — 폐기 행 진단 갭 fix (2026-07-10).
# ---------------------------------------------------------------------------
def test_distill_video_preserves_raw_text_on_success():
    raw = '<thought>t</thought>{"coaching": "다리를 펴세요", "faults": []}'
    client = _FakeClient(text=raw)
    out = gt.distill_video(client, "/tmp/x.mp4", [{"frame": 0}], ["left_knee"])
    assert out["raw_text"] == raw
    assert out["report"]["coaching"] == "다리를 펴세요"


def test_distill_video_preserves_raw_text_on_parse_failure():
    """파싱 불가 원문도 보존 — report=None 이지만 raw_text 로 진단 가능."""
    raw = "JSON 이 아닌 자유 서술 응답"
    client = _FakeClient(text=raw)
    out = gt.distill_video(client, "/tmp/x.mp4", [{"frame": 0}], ["left_knee"])
    assert out["report"] is None
    assert out["raw_text"] == raw
    # evaluate_filters 는 여전히 rejected_parse 로 폐기한다(필터 계약 무변경).
    accepted, reason = gt.evaluate_filters(out, judge_score=10)
    assert accepted is False and reason == "rejected_parse"


def test_run_trial_batch_saves_trial_reports(tmp_path, monkeypatch):
    """행별 (a) raw text (b) parsed (c) 사유가 scratch_dir/trial_reports/ 에 저장된다."""
    import json as _json

    raw = '<thought>진단</thought>{"coaching": "다리를 펴세요", "faults": []}'
    client = _FakeClient(text=raw)

    def _fake_download(bucket, key, dest):
        with open(dest, "wb") as fp:
            fp.write(b"fake video bytes")

    monkeypatch.setattr(gt, "_download_s3", _fake_download)
    manifest = {"rows": [{"s3_key": "fixtures/phase15/climb/fault.mp4",
                          "motion": "climb", "source": "internal", "holdout": None}]}
    result = gt.run_trial_batch(manifest, str(tmp_path), max_rows=1, client=client)

    reports_dir = result["trial_reports_dir"]
    assert reports_dir == str(tmp_path / "trial_reports")
    saved = _json.loads(
        (tmp_path / "trial_reports" / "fixtures__phase15__climb__fault.mp4.json")
        .read_text(encoding="utf-8")
    )
    assert saved["raw_text"] == raw
    assert saved["parsed"]["report"]["coaching"] == "다리를 펴세요"
    assert saved["result"] in {"accepted", "rejected_judge"}  # judge fake 는 임계 미충족 가능.
    assert saved["result"] == result["per_row"][0]["result"]


# ---------------------------------------------------------------------------
# 최상위 배열 파싱 fix (2026-07-10 — 시험 배치 정타 2/5 사망 케이스).
# ---------------------------------------------------------------------------
def test_parse_unwraps_single_dict_array():
    """최상위가 [단일 dict] 배열이면 unwrap 하여 정상 경로 (실증 케이스)."""
    raw = '<thought>t</thought>[{"coaching": "다리를 펴세요", "faults": []}]'
    out = gt.parse_teacher_report(raw)
    assert out is not None
    assert out["report"]["coaching"] == "다리를 펴세요"


def test_parse_rejects_multi_or_nondict_array():
    """다원소/비 dict 배열·스칼라 → None (rejected_parse graceful, 예외 0)."""
    assert gt.parse_teacher_report('[{"a": 1}, {"b": 2}]') is None
    assert gt.parse_teacher_report("[1, 2, 3]") is None
    assert gt.parse_teacher_report('"자유 문자열"') is None
    assert gt.parse_teacher_report("5") is None


def test_distill_video_no_raise_and_raw_preserved_on_list_output(monkeypatch):
    """교사가 배열 JSON 을 내도 distill_video 는 raise 하지 않고 raw 를 보존한다.

    기존 버그: normalize_report(list) AttributeError 가 밖으로 튀어 run_trial_batch
    except 에 잡히며 raw_text=null — 진단 불능. 이제 rejected_parse + raw 보존.
    """
    raw = '[{"a": 1}, {"b": 2}]'
    client = _FakeClient(text=raw)
    out = gt.distill_video(client, "/tmp/x.mp4", [{"frame": 0}], ["left_knee"])
    assert out["report"] is None
    assert out["raw_text"] == raw
    accepted, reason = gt.evaluate_filters(out, judge_score=10)
    assert accepted is False and reason == "rejected_parse"
    # 파싱 단계 임의 예외에도 raise 금지 + raw 보존 (방어 일반화).
    def _boom(_raw):
        raise AttributeError("'list' object has no attribute 'get'")

    monkeypatch.setattr(gt, "parse_teacher_report", _boom)
    out2 = gt.distill_video(client, "/tmp/x.mp4", [{"frame": 0}], ["left_knee"])
    assert out2["report"] is None and out2["raw_text"] == raw


def test_normalize_report_survives_list_input():
    """normalize_report 에 list/스칼라 입력 → 전 키 Null 리포트 (사망 금지)."""
    from datagen import schema

    for bad in ([{"coaching": "x"}], [1, 2], "str", 5):
        out = schema.normalize_report(bad)
        assert set(out) == set(schema.REPORT_KEYS)
        assert all(v is None for v in out.values())


def test_run_trial_batch_quota_abort_preserved(tmp_path, monkeypatch):
    """429 중단 경로 회귀 없음 — 생성 예외(quota)는 여전히 raise → abort."""
    class _QuotaModels:
        def generate_content(self, *a, **k):
            raise RuntimeError("429 RESOURCE_EXHAUSTED")

    client = _FakeClient()
    client.models = _QuotaModels()

    def _fake_download(bucket, key, dest):
        with open(dest, "wb") as fp:
            fp.write(b"fake video bytes")

    monkeypatch.setattr(gt, "_download_s3", _fake_download)
    manifest = {"rows": [
        {"s3_key": "a.mp4", "source": "internal", "holdout": None},
        {"s3_key": "b.mp4", "source": "internal", "holdout": None},
    ]}
    result = gt.run_trial_batch(manifest, str(tmp_path), max_rows=2, client=client)
    assert result["aborted"] is not None and "quota_exhausted" in result["aborted"]
    # 첫 행에서 즉시 중단 — 두 번째 행 미처리.
    assert result["per_row"][0]["result"] == "ABORT_429"
    assert len(result["per_row"]) == 1

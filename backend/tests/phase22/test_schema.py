"""D-11 JSON 규격 + D-01 통합 리포트 v1 스키마 단일 owner 검증 (22-01 Task 1).

핵심 불변식(하드 제약):
  · 모델은 점수를 절대 출력하지 않는다 — REPORT_KEYS·FAULT_ITEM_KEYS 에 score/
    severity/overall/points 계열 키 부재 (짚기·측정만; 감점은 Phase 24 엔진).
  · D-11 4철칙 — 결측=Null 고정(키 삭제 금지)·키 알파벳 정렬·관절 사전 필터·
    좌표 3자리 정수 이산화.
  · faults[] 는 deduction_engine 소비 계약(DEDUCTION_CONSUMED_KEYS)의 상위집합 —
    swap 후 감점 엔진이 결함을 무수정 채점 (lockstep, drift 시 FAIL).
"""

from datagen import schema


def test_report_keys_alphabetical_and_score_free():
    """Test 1 — REPORT_KEYS 정확 튜플, 알파벳 정렬, score/overall/points 부재."""
    assert schema.REPORT_KEYS == (
        "coaching",
        "corrected_coords",
        "faults",
        "segments",
        "svg_spec",
        "time_anchors",
    )
    # 알파벳 오름차순.
    assert list(schema.REPORT_KEYS) == sorted(schema.REPORT_KEYS)
    # 점수 계열 키 부재 (모델은 점수를 절대 내지 않는다).
    for banned in ("score", "overall", "points", "rating", "severity"):
        assert banned not in schema.REPORT_KEYS


def test_normalize_fills_missing_with_null_and_sorts_keys():
    """Test 2 — 결측 키 삭제 금지·Null 고정 + dict 키 알파벳 정렬 재방출 (철칙 1·2)."""
    raw = {"faults": [], "coaching": "다리를 더 펴세요"}
    out = schema.normalize_report(raw)
    # 결측 키(corrected_coords/segments/svg_spec/time_anchors)는 삭제되지 않고 None.
    for key in schema.REPORT_KEYS:
        assert key in out
    assert out["corrected_coords"] is None
    assert out["segments"] is None
    # 키가 알파벳 정렬로 재방출.
    assert list(out.keys()) == sorted(out.keys())
    # 화이트리스트 밖 키는 통과하지 않는다 (T-22-02).
    assert schema.normalize_report({"bogus": 1, **raw}).get("bogus") is None or (
        "bogus" not in schema.normalize_report({"bogus": 1})
    )


def test_discretize_roundtrip_within_one_grid_cell():
    """Test 3 — 000~999 3자리 정수 그리드, 왕복 오차 ≤ 그리드 1칸(1/1000)."""
    width, height = 640.0, 480.0
    for x, y in [(0.0, 0.0), (320.5, 240.25), (639.0, 479.0), (12.3, 456.7)]:
        dx, dy = schema.discretize((x, y), width, height)
        assert isinstance(dx, int) and isinstance(dy, int)
        assert 0 <= dx <= 999 and 0 <= dy <= 999
        rx, ry = schema.undiscretize((dx, dy), width, height)
        assert abs(rx - x) <= width / 1000.0 + 1e-9
        assert abs(ry - y) <= height / 1000.0 + 1e-9


def test_filter_joints_drops_face_and_finger():
    """Test 4 — 태스크 무관 관절(얼굴 이목구비·손가락)을 입력 전 삭제 (D-11 철칙)."""
    coords = {
        "left_shoulder": [1, 2],
        "right_knee": [3, 4],
        "face_12": [5, 6],
        "left_thumb1": [7, 8],
        "right_eye": [9, 10],
        "nose": [11, 12],
    }
    task_joints = ("left_shoulder", "right_knee")
    out = schema.filter_joints(coords, task_joints)
    assert "left_shoulder" in out and "right_knee" in out
    for irrelevant in ("face_12", "left_thumb1", "right_eye", "nose"):
        assert irrelevant not in out


def test_select_frame_indices_uniform_within_range():
    """Test 5 — stride=ceil(T/budget) 균등 서브샘플, 전 인덱스 [0,T) (Pattern 1)."""
    total = 270  # 30s * 9fps
    idx = schema.select_frame_indices(total, budget=64)
    assert len(idx) <= 64
    assert all(0 <= i < total for i in idx)
    # 균등 stride (인접 간격 동일).
    if len(idx) > 1:
        strides = {idx[i + 1] - idx[i] for i in range(len(idx) - 1)}
        assert len(strides) == 1
    # 예산 이하 프레임 수는 전부 반환.
    small = schema.select_frame_indices(40, budget=64)
    assert small == list(range(40))


def test_normalize_rejects_unknown_fault_category():
    """Test 6 — FAULT_CATEGORIES 밖 fault_category 는 normalize 에서 None 처리 (enum 단일 owner)."""
    raw = {
        "faults": [
            {"fault_category": "split_angle", "body_part": "왼다리"},
            {"fault_category": "made_up_category", "body_part": "오른팔"},
        ]
    }
    out = schema.normalize_report(raw)
    faults = out["faults"]
    assert faults[0]["fault_category"] == "split_angle"
    # enum 밖 값 → None (키 삭제 금지, Null 고정).
    assert faults[1]["fault_category"] is None


def test_faults_superset_of_deduction_consumed_keys_lockstep():
    """Test 7 — faults[] 항목이 감점 엔진 소비 계약의 상위집합 (lockstep, 점수/severity 부재)."""
    # 필수 측정 각도쌍 + 서술 필드 보유.
    for key in (
        "fault_category",
        "student_angle_deg",
        "reference_angle_deg",
        "measurement_basis",
        "root_cause_hypothesis",
        "source",
    ):
        assert key in schema.FAULT_ITEM_KEYS
    # DEDUCTION_CONSUMED_KEYS ⊆ FAULT_ITEM_KEYS (drift 시 FAIL).
    assert set(schema.DEDUCTION_CONSUMED_KEYS) <= set(schema.FAULT_ITEM_KEYS)
    # 점수/severity 필드 여전히 부재.
    for banned in ("score", "severity", "overall", "points"):
        assert banned not in schema.FAULT_ITEM_KEYS
        assert banned not in schema.DEDUCTION_CONSUMED_KEYS
    # gemini_vision_scorer SCHEMA v8.1 differences[] 계약과 lockstep — severity(비채점
    # 라벨) 제외한 모든 소비 키를 우리 스키마가 상위집합으로 커버한다.
    from sunity_shared.analysis import gemini_vision_scorer

    gemini_diff_keys = set(
        gemini_vision_scorer.build_schema()["properties"]["differences"]["items"][
            "properties"
        ].keys()
    )
    mirrored = gemini_diff_keys - {"severity"}
    assert mirrored <= set(schema.FAULT_ITEM_KEYS), (
        "gemini differences[] 소비 키가 FAULT_ITEM_KEYS 상위집합을 벗어남 (계약 drift)"
    )


def test_faults_item_keys_alphabetical():
    """FAULT_ITEM_KEYS 도 알파벳 정렬 (출력 구조 규칙성 — 파싱 오류 영점화)."""
    assert list(schema.FAULT_ITEM_KEYS) == sorted(schema.FAULT_ITEM_KEYS)


def test_normalize_report_fault_item_null_fixation():
    """faults[] 항목의 결측 필드도 Null 고정 (D-11 철칙 1)."""
    raw = {"faults": [{"fault_category": "grip"}]}
    out = schema.normalize_report(raw)
    item = out["faults"][0]
    for key in schema.FAULT_ITEM_KEYS:
        assert key in item
    assert item["student_angle_deg"] is None
    assert list(item.keys()) == sorted(item.keys())

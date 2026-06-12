"""Phase 17 Wave 0 — 4 영역 Gemini Vision Pydantic 응답 스키마.

박제 정신:
  · AI-SPEC §4b "Structured Outputs with Pydantic" 4 영역 schema 정의를 1:1 박제.
  · 후속 plan (02 reference / 03 coach / 04 finding / 05 keypoint) 이 schema 재정의 0 —
    본 모듈만 import 후 GeminiVisionCall(schema=...) 로 주입한다.
  · CheckpointJoint.joint_key Literal 8개 = sunity_shared.analysis.skeleton.JOINT_KEYS 와
    동일 (left/right Elbow/Shoulder/Hip/Knee). 변경 시 양쪽 동기화 필수 (skeleton 이 SOT).
  · 사람 점수/판단 어휘는 schema 차원에서 정의 X — guardrails 가 raw text 차원에서 차단.

후속 plan 정합:
  · 영역 A (reference 등록): ReferenceRegistration → Firestore reference 문서 박제.
  · 영역 B (coach): CoachPayload → coach_writer 가 detail2.causes 를 Coach v2 UI 로 박제.
  · 영역 C (finding): FindingFlags → 분석 결과 메타 — grip/backbend/occlusion 박제.
  · 영역 D (keypoint refinement): KeypointRefinement → RTMW 저신뢰 keypoint 박제 보강.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# CheckpointJoint.joint_key Literal — sunity_shared.analysis.skeleton.JOINT_KEYS 8개 박제.
# 변경 시 skeleton.JOINT_ANGLES (SOT) 와 동기화 필수.
JointKeyLiteral = Literal[
    "left_elbow",
    "right_elbow",
    "left_shoulder",
    "right_shoulder",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
]

# CheckpointJoint.expectation Literal — analysis.technique 의 JOINT_EXTEND/BENT_OK/CONTACT 박제.
ExpectationLiteral = Literal["EXTEND", "BENT_OK", "CONTACT"]


class CheckpointJoint(BaseModel):
    """영역 A reference 등록 시 1개 관절의 expectation 박제 (라인 채점 분기 키)."""

    model_config = ConfigDict(extra="forbid")

    joint_key: JointKeyLiteral = Field(description="채점 분기 관절 키 (8개 박제)")
    expectation: ExpectationLiteral = Field(
        description="동작 hold 시점에서 본 관절의 기대 상태 (EXTEND/BENT_OK/CONTACT)"
    )


class ReferenceRegistration(BaseModel):
    """영역 A — 정은지 선수 영상 → reference 문서 자동 등록 payload.

    Firestore `referenceMotions` 컬렉션 박제 source. 사람 점수 X — 동작 이름 + clip 구간 +
    관절 expectation 의 객관 메타만 박제.
    """

    model_config = ConfigDict(extra="forbid")

    motion_name_ipsf: str = Field(
        min_length=1, description="IPSF 공식 영문명 (예: 'Inverted Butterfly')"
    )
    motion_name_ko: str = Field(
        min_length=1, description="학원 통용 한국어명 (예: '인버티드 버터플라이')"
    )
    clip_start_seconds: float = Field(
        ge=0.0, description="기준 동작이 시작되는 timestamp (초, 0 이상)"
    )
    clip_end_seconds: float = Field(
        ge=0.0, description="기준 동작이 끝나는 timestamp (초, 0 이상)"
    )
    checkpoint_joints: list[CheckpointJoint] = Field(
        min_length=1,
        max_length=8,
        description="채점 분기 관절 리스트 (1~8개 박제)",
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Gemini 자체 분류 신뢰도 (0~1)"
    )


# ─────────────────── 영역 B (코칭 멘트) ───────────────────


class CoachCause(BaseModel):
    """Coach v2 detail2 1개 원인 — title / explanation / fix 3종 모두 박제 필수."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, description="원인 한 줄 헤드라인")
    explanation: str = Field(min_length=1, description="왜 그렇게 되는지 해설")
    fix: str = Field(min_length=1, description="구체적 교정 동작/큐")


class CoachDetail2(BaseModel):
    """Coach v2 detail2 — 1개 관절의 3~5개 원인 박제 (단순 수치 X, 원인 박제)."""

    model_config = ConfigDict(extra="forbid")

    causes: list[CoachCause] = Field(
        min_length=3,
        max_length=5,
        description="원인 3~5개 박제 (수치는 보조, 원인이 핵심)",
    )


class JointCoaching(BaseModel):
    """영역 B 1개 관절의 코칭 payload — detail (한 줄) + detail2 (원인 묶음)."""

    model_config = ConfigDict(extra="forbid")

    joint_key: JointKeyLiteral = Field(description="코칭 대상 관절 키")
    detail: str = Field(min_length=1, description="단일 핵심 코칭 멘트 (한 줄)")
    detail2: CoachDetail2 = Field(
        description="원인 묶음 (Coach v2 UI 박제 — 3~5개 cause)"
    )


class CoachPayload(BaseModel):
    """영역 B — Gemini 가 생성한 코칭 멘트 묶음 (관절별)."""

    model_config = ConfigDict(extra="forbid")

    joints: list[JointCoaching] = Field(
        min_length=1,
        max_length=8,
        description="코칭 대상 관절 리스트 (1~8개)",
    )


# ─────────────────── 영역 C (finding 인식) ───────────────────


class FindingFlags(BaseModel):
    """영역 C — 분석 결과 finding 메타 (객관 boolean + 200자 노트).

    notes_ko 는 한국어 코멘트지만 사람 판단 어휘는 raw text 가드에서 차단.
    """

    model_config = ConfigDict(extra="forbid")

    grip_visible: bool = Field(description="grip 위치가 영상에 보이는지")
    backbend_present: bool = Field(description="backbend (등 젖힘) 동작 존재 여부")
    occlusion_severe: bool = Field(description="occlusion (가림) 심각도")
    camera_angle_problematic: bool = Field(
        description="촬영 각도가 분석을 방해하는지"
    )
    notes_ko: str = Field(
        max_length=200, description="한국어 보조 노트 (최대 200자, 점수/판단 어휘 금지)"
    )


# ─────────────────── 영역 D (keypoint refinement) ───────────────────


class RefinedKeypoint(BaseModel):
    """영역 D — 1개 프레임의 1개 keypoint 보정값.

    좌표 (x/y) 는 영역 D 만 허용 — guardrails.allow_coords=True 박제 분기.
    """

    model_config = ConfigDict(extra="forbid")

    frame_index: int = Field(ge=0, description="대상 프레임 인덱스 (0 이상)")
    x_normalized: float = Field(
        ge=0.0, le=1.0, description="x 좌표 (영상 width 정규화, 0~1)"
    )
    y_normalized: float = Field(
        ge=0.0, le=1.0, description="y 좌표 (영상 height 정규화, 0~1)"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Gemini 자체 보정 신뢰도 (0~1)"
    )


class KeypointRefinement(BaseModel):
    """영역 D — Gemini 가 RTMW 저신뢰 keypoint 를 영상 직접 관찰로 보강한 payload."""

    model_config = ConfigDict(extra="forbid")

    refined: list[RefinedKeypoint] = Field(
        max_length=200,
        description="보정된 keypoint 리스트 (최대 200개 — Lambda payload 한계 박제)",
    )


__all__ = [
    "CheckpointJoint",
    "CoachCause",
    "CoachDetail2",
    "CoachPayload",
    "ExpectationLiteral",
    "FindingFlags",
    "JointCoaching",
    "JointKeyLiteral",
    "KeypointRefinement",
    "ReferenceRegistration",
    "RefinedKeypoint",
]

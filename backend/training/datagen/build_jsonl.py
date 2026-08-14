"""3트랙 학습 JSONL 조립기 — 교란/증류/shadow + T3/텍스트 혼합 (22-04 Task 2).

belle 노트 §8 원형(messages 3롤: system / user video+RTMW_Data / assistant thought+
통합리포트)으로 SFT 학습셋을 조립한다. 세 라벨 경로가 합류한다:
  · perturb — 22-01 perturb_sequence 좌표보정 자가 라벨(정답=원좌표, 교사 무관, D-10a).
  · distill — 22-04 Task 1 Gemini 교사 증류(짚기/측정/코칭, judge 통과분).
  · shadow  — 22-03 Firestore vlm_shadow 적재분(veto/coach). manifest video_hash join
              강제 — 미등록/미가명은 text-only 강등, media 참조 0 (DR-01).
추가로 T3 순수 텍스트 시간추론 + 순수 텍스트 instruction 을 혼합비(기본 0.15)만큼
섞어 시각 없는 시간축 각성 + 언어능력 감퇴 방지(D-11).

규율:
  · 프레임 재추출 0 — schema.select_frame_indices 인덱스 서브샘플만(Pattern 1, 영상
    디코더 의존 없음, 파이프라인 9fps 배열 인덱스만 사용).
  · assistant JSON 은 schema.normalize_report 통과 강제 — score 계열 키 0(D-01).
  · train/val split 소유자는 이 모듈 단독(video_hash 단위, leakage 0). 항상 _meta.
    validation_owner 방출(explicit_val_jsonl → val.jsonl 발행 / phase22_eval_gate → 미발행).
  · collection_complete fail-closed 진입(DR-06) — --partial 없이는 실패, --partial 은
    canonical prefix 업로드 금지.

Firestore/S3 는 주입 loader 로 분리 — 조립 로직은 네트워크 0 으로 테스트된다.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np

from datagen import perturb, schema

log = logging.getLogger("build_jsonl")
if not log.handlers:
    log.setLevel(logging.INFO)

# ── S3 canonical prefix (S3 ObjectCreated 미-notified — 학습 산출 전용) ──
CANONICAL_PREFIX = "training/phase22/jsonl/"
PARTIAL_PREFIX = "training/phase22/jsonl_partial/"
_VIDEO_BUCKET = "sunity-motion-pilot-videos"

# ── 텍스트 혼합비 config (기본 text 계열 합 0.15 — 수치는 ablation 축, Open Q4) ──
# 시각 없는 시간추론(t3_temporal)과 순수 언어 instruction 을 이 비율로 섞는다.
DEFAULT_MIX_RATIOS: dict[str, float] = {
    "t3_temporal": 0.075,
    "instruction": 0.075,
}

_VALID_VALIDATION_OWNERS = ("explicit_val_jsonl", "phase22_eval_gate")

# perturb 파라미터 분포 (22-01 산출) — 프레임 재추출 아님, 좌표 노이즈 주입만.
_PROFILE_PATH = Path(__file__).resolve().parent / "rtmw_error_profile.json"

# ── fault-free 캡 비율 (quick-260715-wq9 B 재균형) ──
# 진단: 학습셋 363행 중 fault 보유 80행(22%)뿐, faults=[] 다수가 결함 영상 학습을
# 익사시켜 학생이 "faults:[] 가 정상"을 학습(결함 미방출). fault-free 미디어를
# fault-bearing 의 이 비율 배 이하로 트림해 결함 신호를 살린다. 수치 자체가 아니라
# "정타 다수 익사 차단" 방향이 근거 — DEFAULT_MIX_RATIOS/_STAGE_CYCLE 과 동일한
# ablation 축. 트림은 fault-free 만(오버샘플/fault-bearing 부풀리기 금지 —
# curve-fit·overfit 방지 [[scoring-redesign-must-generalize-no-overfit]]).
FAULT_FREE_CAP_RATIO = 1.5

# perturb stage 배분 cycle (quick-260715-fjw D3). eligible perturb 행 순번 k 에
# stage = _STAGE_CYCLE[k % len(_STAGE_CYCLE)] 을 적용한다. 게이트 synthetic_holdout
# 은 가시 셀 변위 보정 L2 만 판정하고(가려짐 복원은 비게이트 관찰치
# grounding_occluded_restored), 변위-순수 stage1 이 그 신호를 가장 직접 만든다 —
# 그래서 stage1 을 2배 가중한다. (1,1,2,3) 은 ablation 축(수치 자체가 근거가 아니라
# 변위-우선이라는 방향이 근거).
_STAGE_CYCLE = (1, 1, 2, 3)


# ---------------------------------------------------------------------------
# 진입 게이트 — collection_complete fail-closed + upload prefix (DR-06).
# ---------------------------------------------------------------------------
def assert_collection_complete(manifest: dict, partial: bool) -> None:
    """manifest _meta.collection_complete is true 를 강제 — 아니면 실패(DR-06).

    --partial 이면 미완 수집으로도 진행하되(부분 실행), 호출자가 canonical prefix
    업로드를 금지해야 한다(resolve_upload_prefix).
    """
    if partial:
        return
    complete = bool((manifest or {}).get("_meta", {}).get("collection_complete"))
    if not complete:
        raise ValueError(
            "manifest _meta.collection_complete != true — 학습셋 조립 차단(DR-06). "
            "부분 실행은 명시적 --partial 필요(canonical prefix 업로드 금지)."
        )


def resolve_upload_prefix(partial: bool) -> str:
    """업로드 prefix — partial 은 canonical(training/phase22/jsonl/)을 절대 쓰지 않는다."""
    return PARTIAL_PREFIX if partial else CANONICAL_PREFIX


# ---------------------------------------------------------------------------
# 샘플 접근 헬퍼.
# ---------------------------------------------------------------------------
def sample_has_video(sample: dict) -> bool:
    """user content 에 type=video 항목이 있으면 True (media 참조 여부)."""
    try:
        user = sample["messages"][1]["content"]
    except (KeyError, IndexError, TypeError):
        return False
    if not isinstance(user, list):
        return False
    return any(isinstance(c, dict) and c.get("type") == "video" for c in user)


def assistant_report(sample: dict):
    """assistant content 문자열에서 JSON 리포트를 파싱 — 실패 시 None(text-only 라벨)."""
    try:
        content = sample["messages"][2]["content"]
    except (KeyError, IndexError, TypeError):
        return None
    if not isinstance(content, str):
        return None
    idx = content.find("</thought>")
    body = content[idx + len("</thought>"):] if idx != -1 else content
    body = body.strip()
    try:
        return json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 메시지 조립 primitive (belle 노트 §8 3롤 구조).
# ---------------------------------------------------------------------------
def _system_msg(joint_keys) -> dict:
    return {"role": "system", "content": schema.bind_key_prompt(joint_keys)}


def _s3_uri(s3_key: str) -> str:
    return f"s3://{_VIDEO_BUCKET}/{s3_key}"


def _rtmw_text(frames) -> str:
    """서브샘플 프레임 행 → RTMW_Data 텍스트 (원 영상 재추출 0, 인덱스만)."""
    return "RTMW_Data: " + json.dumps(frames or [], ensure_ascii=False, sort_keys=True)


# 태스크 지시문 (v4, 2026-07-14 자유생성 붕괴 fix): v3까지 user = video+좌표뿐이라
# 모델이 태스크를 좌표 통계로만 추정해야 했고, 자유생성이 베이스 프라이어로 이탈했다
# (swift infer val 4행 전부 스키마 밖 — 병합 무관, 어댑터도 동일). 고정 지시문으로
# 출력 계약을 입력에 명시한다. RTMW_Data 접두는 유지(테스트/파서 계약 불변).
_TASK_INSTRUCTION = (
    "\n\n위 영상과 RTMW 좌표를 분석해 다음 키를 갖는 JSON 리포트만 출력하라: "
    "coaching, corrected_coords, faults, segments, svg_spec, time_anchors. "
    "faults 항목은 body_part/fault_category 라우팅 키를 반드시 포함한다. "
    "결함이 없으면 faults 는 빈 배열이다."
)


def _user_media_msg(s3_key: str, frames) -> dict:
    return {
        "role": "user",
        "content": [
            {"type": "video", "video": _s3_uri(s3_key)},
            {"type": "text", "text": _rtmw_text(frames) + _TASK_INSTRUCTION},
        ],
    }


def _user_text_msg(text: str) -> dict:
    return {"role": "user", "content": [{"type": "text", "text": text}]}


# ── eye 트랙 (quick 260814-j24) — 기계 눈 관절 상태 관측 ─────────────────────
#
# 왜 faults[] 가 아니라 별도 6키 스키마인가: 눈 판정은 **결함이 아니라 관절 상태
# 관측**이다. 이를 faults 배열에 담으면 정상 관측(agrees=true)까지 결함으로 사칭돼
# 학습셋이 오염된다(감점 엔진이 소비하는 계약이라 실제로 감점으로 이어진다).
# v4 자유생성 붕괴 fix 의 교훈(_TASK_INSTRUCTION — 출력 계약을 입력에 명시)을 그대로
# 적용해 eye 태스크는 자체 지시문 + 자체 스키마를 갖는다. score/severity/overall/
# points 계열은 여기서도 구조적 부재다(D-01 불변식의 eye 판).
EYE_TASK_KEYS: tuple[str, ...] = (
    "joint",               # 마킹된 관절(입력에서 주어짐).
    "limb",                # 원 안의 관절이 팔의 것인지 다리의 것인지 — 마크-전위 축.
    "observed",            # 눈 관측: bent | extended | unclear | off_body.
    "reason",              # 그렇게 본 근거(자유텍스트).
    "side",                # user | ref.
    "track_claim",         # 트랙(파이프라인)이 주장한 상태 — 입력에서 주어진다.
    "track_claim_agrees",  # 2단 판정 결과. false = keypoint 환각/마크 전위.
)

_EYE_SYSTEM = (
    "당신은 폴스포츠 자세 분석의 검증자입니다. 주황색 원으로 표시된 관절 한 곳만 보고 "
    "그 관절이 접혔는지(bent) 펴졌는지(extended) 판정하고, 판정 불가면 unclear, 표시가 "
    "관절 위가 아니면 off_body 로 답합니다. 점수는 매기지 않습니다."
)

# track_claim_agrees 는 **2단 판정**이다 — card_gates._eye_verdict 단일 owner 의 규칙을
# 그대로 문장화한다: (1) 상태 일치 AND (2) 원 안의 사지 종류가 그 관절의 기대 사지와
# 일치. 무릎 마크가 굽은 팔에 얹혀 claim=bent 가 우연히 맞는 케이스(kneepath 실측)를
# false 로 잡는 것이 이 트랙의 존재 이유이므로, 1단만 가르치면 라벨과 지시문이 어긋나
# 학습이 잡음이 된다.
_EYE_TASK_INSTRUCTION = (
    "\n\n표시된 관절만 보고 다음 키를 갖는 JSON 만 출력하라: "
    "joint, limb, observed, reason, side, track_claim, track_claim_agrees. "
    "observed 는 bent | extended | unclear | off_body 중 하나이고, "
    "limb 은 원 안의 관절이 팔의 것이면 arm, 다리의 것이면 leg, 그 외/판정 불가면 "
    "other 또는 unclear 다. "
    "track_claim_agrees 는 (가) observed 가 track_claim 과 같은 상태이고 (나) limb 이 "
    "joint 가 속한 사지와 어긋나지 않을 때만 true 이며, 상태가 같아도 마크가 다른 사지에 "
    "얹혀 있으면 false 다. 점수·심각도는 출력하지 않는다."
)


def _eye_context_text(joint, side, claim) -> str:
    """Eye_Task 데이터 행 — _rtmw_text 관례(데이터 접두 + 공용 지시문)와 동형.

    track_claim 을 입력에 넣는 이유: 넣지 않으면 타겟의 track_claim /
    track_claim_agrees 가 원리적으로 학습 불가(모델이 추측해야 함)라 불일치 감독이
    잡음으로 변한다. 눈 태스크의 감독 신호는 "주어진 주장이 그림과 맞는가"다.
    """
    payload = {"claim": claim, "joint": joint, "side": side}
    return "Eye_Task: " + json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _user_image_msg(media_key: str, joint, side, claim) -> dict:
    return {
        "role": "user",
        "content": [
            {"type": "image", "image": _s3_uri(media_key)},
            {"type": "text", "text": _eye_context_text(joint, side, claim)
             + _EYE_TASK_INSTRUCTION},
        ],
    }


def normalize_eye_report(raw: dict) -> dict:
    """eye 리포트 정규화 — EYE_TASK_KEYS 화이트리스트 + 결측 None + 알파벳 정렬.

    schema.normalize_report 는 REPORT_KEYS 전용이라 재사용하지 않는다(다른 태스크).
    화이트리스트 밖 키(score/severity 등)는 통과하지 않는다 — 구조적 부재의 집행점.
    """
    raw = raw if isinstance(raw, dict) else {}
    return {k: raw.get(k) for k in sorted(EYE_TASK_KEYS)}


def _assistant_eye_msg(report: dict) -> dict:
    return {
        "role": "assistant",
        "content": json.dumps(normalize_eye_report(report), ensure_ascii=False, sort_keys=True),
    }


def _assistant_report_msg(thought, report: dict) -> dict:
    """thought + REPORT_KEYS 알파벳 정렬 JSON (normalize_report 통과 강제)."""
    normalized = schema.normalize_report(report)
    body = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
    thought_block = f"<thought>\n{thought}\n</thought>\n" if thought else ""
    return {"role": "assistant", "content": thought_block + body}


def _assistant_text_msg(text: str) -> dict:
    return {"role": "assistant", "content": text}


def _svg_spec(target_angle_deg=None, force_vector=None, ideal_trajectory=None) -> dict:
    """SVG_SPEC_KEYS 3키 고정(결측 Null) — target 은 결정적(자가 라벨), 나머지 교사분(F2)."""
    return {
        "force_vector": force_vector,
        "ideal_trajectory": ideal_trajectory,
        "target_angle_deg": target_angle_deg,
    }


# ---------------------------------------------------------------------------
# 좌표 → 서브샘플 프레임 행 (discretize, Null 바인딩).
# ---------------------------------------------------------------------------
def _coords_to_frames(
    coords, joint_keys, frame_indices, width, height, frame_labels=None
) -> list[dict]:
    """coords 를 프레임 행 리스트로 이산화한다.

    frame_indices 는 coords 배열의 행 인덱스(무엇을 읽을지), frame_labels 는 그 행에
    붙일 frame 라벨(원본 영상 프레임 번호)이다. subsample-first 교란(D4)에서 배열은
    (N,J,C) 서브샘플이라 인덱스가 0..N-1 로 재정렬되지만 라벨은 원본 idxs 를 유지해야
    user 행과 corrected_coords 행의 frame 라벨이 일치한다. frame_labels=None 이면
    인덱스가 곧 라벨(기존 동작)."""
    frames: list[dict] = []
    c = coords.shape[2]
    for pos, f in enumerate(frame_indices):
        label = int(frame_labels[pos]) if frame_labels is not None else int(f)
        row: dict = {"frame": label}
        for j, name in enumerate(joint_keys):
            x = coords[f, j, 0]
            y = coords[f, j, 1]
            conf = float(coords[f, j, 2]) if c > 2 else 1.0
            if not (np.isfinite(x) and np.isfinite(y)):
                row[name] = None  # 가려짐 = Null 바인딩(D-11 철칙 1, 키 삭제 금지).
            else:
                dx, dy = schema.discretize((x, y), width, height)
                row[name] = [dx, dy, round(conf, 2)]
        frames.append(row)
    return frames


# ---------------------------------------------------------------------------
# 행 선택 — holdout 격리 + 고객 anonymized 게이트 (gemini_teacher 계약 재사용).
# ---------------------------------------------------------------------------
def _is_customer_source(source) -> bool:
    s = str(source or "").lower()
    return any(m in s for m in ("customer", "pilot", "user"))


def _eligible_media_row(row: dict) -> bool:
    if row.get("holdout"):
        return False
    if not row.get("s3_key"):
        return False
    if _is_customer_source(row.get("source")) and row.get("anonymized") is not True:
        return False
    return True


def _faults_satisfy_contract(report: dict) -> bool:
    """faults[] 가 감점 엔진 소비 계약(각도쌍/폴백 + fault_category + body_part) 상위집합(F1)."""
    faults = (report or {}).get("faults")
    if not faults:
        return True
    for item in faults:
        if not isinstance(item, dict):
            return False
        has_pair = (
            item.get("student_angle_deg") is not None
            and item.get("reference_angle_deg") is not None
        )
        has_fallback = item.get("approx_angle_deviation_deg") is not None
        if not (has_pair or has_fallback):
            return False
        if not item.get("fault_category") or not item.get("body_part"):
            return False
    return True


# ---------------------------------------------------------------------------
# 트랙 조립.
# ---------------------------------------------------------------------------
def _load_profile():
    try:
        return perturb.load_profile(_PROFILE_PATH)
    except Exception:  # noqa: BLE001 - profile 부재 시 교란 없이 원좌표 passthrough.
        return None


def _build_perturb_samples(manifest, perturb_loader, reference_loader, rng) -> list[dict]:
    """정답=원좌표 좌표보정 트랙 (D-10a). 교란 서브샘플→user, 원좌표→corrected_coords.

    quick-260715-fjw 재설계: (D3) stage 배분을 _STAGE_CYCLE 로 변위-가중,
    (D4) subsample-first 교란, (D5) 1/3 좌표전용 샘플 혼합, (D6) corrected_coords
    전체 프레임 유지. 자세한 근거는 각 지점 주석.
    """
    if perturb_loader is None:
        return []
    profile = _load_profile()
    out: list[dict] = []
    # k = eligible+loaded 통과 순번(원본 row 인덱스 아님) — stage cycle/좌표전용 결정
    # 기준. 중간에 미가명 고객/holdout 행이 걸러져도 cycle 이 어긋나지 않게 한다.
    k = 0
    for row in manifest.get("rows", []):
        if not _eligible_media_row(row):
            continue
        loaded = perturb_loader(row)
        if not loaded:
            continue
        coords = np.asarray(loaded["coords"], dtype=float)
        joint_keys = loaded.get("joint_keys") or []
        width = float(loaded.get("width", 1.0))
        height = float(loaded.get("height", 1.0))
        idxs = schema.select_frame_indices(coords.shape[0])
        # D4 subsample-first: 표시 프레임으로 먼저 서브샘플한 뒤 교란한다. 과거엔
        # 전체 T 를 교란하고 ≤64 를 서브샘플해, 교란 프레임 대다수가 표시 밖으로
        # 빠져 user 는 무교란 좌표를 보는데 corrected=원좌표 = 순수 항등 echo 샘플이
        # 양산됐다(v2 "무보정 동률"의 기계적 원인). 서브샘플 먼저 → 모든 교란이
        # 표시 프레임에 반드시 반영된다.
        sub = coords[idxs]
        # D3 stage 배분 — 변위-우선 결정적 cycle (균등 (i%3)+1 교체).
        stage = _STAGE_CYCLE[k % len(_STAGE_CYCLE)]
        perturbed_sub = sub
        if profile is not None:
            try:
                perturbed_sub = perturb.perturb_sequence(
                    sub, profile, stage, rng, joint_keys
                ).perturbed
            except Exception:  # noqa: BLE001 - 교란 실패 시 원좌표(구조 유지).
                perturbed_sub = sub
        # 배열 인덱스(0..N-1)로 읽되 frame 라벨은 원본 영상 프레임 번호(idxs)로 기입.
        user_frames = _coords_to_frames(
            perturbed_sub, joint_keys, range(len(idxs)), width, height, frame_labels=idxs
        )
        # D6 corrected_coords = 표시 프레임 전체 행 echo (변경 프레임만 방출 채택 안 함).
        #   · 게이트 공정성: parse_corrected_coords 는 미방출 프레임=NaN 제외 — 부분
        #     방출을 학습시키면 모델이 쉬운(무교란) 프레임만 골라 방출해 상대 게이트
        #     (보정<무보정)를 뒷문으로 무력화(cherry-picking = 게이트 완화)할 수 있다.
        #     전체 방출은 계측 마스크 ≈ 무보정 기준선 마스크로 비교가 공정하다.
        #   · 무교란 셀의 "입력 그대로 출력"은 보정 함수의 올바른 항등 구간이지 v3
        #     distill 의 독(무의미 echo 가 의미 필드를 익사)과 다르다 — distill cc=None
        #     으로 익사 원인은 이미 제거됐고, perturb 내부 항등 비중은 D3/D4 + drift 의
        #     변위 밀도 확대로 실질 신호 비율을 올려 해소한다.
        orig_frames = _coords_to_frames(
            sub, joint_keys, range(len(idxs)), width, height, frame_labels=idxs
        )
        ref = reference_loader(row.get("motion")) if reference_loader else None
        target = (ref or {}).get("target_angle_deg")
        report = {
            "coaching": None,
            "corrected_coords": orig_frames,
            "faults": [],
            "segments": None,
            "svg_spec": _svg_spec(target_angle_deg=target),
            "time_anchors": None,
        }
        # D5 좌표전용 혼합 — eligible perturb 행의 1/3(k % 3 == 2)은 video 파트 없이
        # 좌표전용으로 방출한다. 게이트 synth=좌표전용 / 프로덕션 추론=video+coords —
        # 다수(2/3)는 video 유지로 시각 grounding 을 보존하고, 1/3 로 좌표전용 분포
        # (synthetic_holdout)를 커버해 "corrected_coords=[] 전량 방출" gap 을 해소한다.
        # user 텍스트는 _rtmw_text + _TASK_INSTRUCTION 모듈 상수 재사용 — 게이트
        # build_aligned_report_messages(rows, []) 좌표전용 경로와 문자 단위 동일(단일
        # 진실, 신규 지시문 작성 금지). 비율 1/3 은 ablation 축.
        coords_only = (k % 3 == 2)
        if coords_only:
            user_msg = _user_text_msg(_rtmw_text(user_frames) + _TASK_INSTRUCTION)
        else:
            user_msg = _user_media_msg(row["s3_key"], user_frames)
        out.append({
            "messages": [
                _system_msg(joint_keys),
                user_msg,
                _assistant_report_msg(
                    "교란된 좌표를 전후 프레임 궤적으로 보정합니다.", report
                ),
            ],
            "_track": "perturb",
            "_video_hash": row.get("video_hash"),
            "_motion": row.get("motion"),
            "_coords_only": coords_only,
            "_has_faults": False,  # perturb 리포트 faults=[] 고정(항상 fault-free).
        })
        k += 1
    return out


def _build_distill_samples(manifest, distill_loader, reference_loader) -> list[dict]:
    """Gemini 교사 증류 트랙 — video_hash 로 manifest join, 감점 계약 미충족 폐기(F1)."""
    if distill_loader is None:
        return []
    by_hash = {r.get("video_hash"): r for r in manifest.get("rows", []) if r.get("video_hash")}
    out: list[dict] = []
    for rec in distill_loader() or []:
        vh = rec.get("video_hash")
        row = by_hash.get(vh)
        if row is None or not _eligible_media_row(row):
            continue
        # 입구 정규화(2026-07-11 fix): 디스크 적재분(accepted/)은 구 normalize 산출일 수
        # 있어 중첩 타입(svg_spec str 등) 미강제 — schema 단일 지점에서 재정규화한다.
        # str svg 등 타입 불일치는 필드만 None 강등, 행은 유지(graceful).
        rec_report = schema.normalize_report(rec.get("report") or {})
        if not _faults_satisfy_contract(rec_report):
            continue  # 감점 계약 미충족 샘플 폐기(F1).
        ref = reference_loader(row.get("motion")) if reference_loader else None
        target = (ref or {}).get("target_angle_deg")
        src_svg = rec_report.get("svg_spec") or {}
        report = {
            "coaching": rec_report.get("coaching"),
            # v4 (2026-07-14): distill 행 corrected_coords 는 항상 None. 교사가 무교란
            # 실영상 좌표를 그대로 echo 한 값이라 (a) 타겟 토큰의 ~90%가 좌표 복사가 되어
            # 의미 필드(faults/coaching) 손실이 익사하고 (b) "corrected=입력 항등" 106행이
            # perturb 95행의 실보정 신호를 압도했다(v3 holdout 0.0444≈무보정 0.0417 = 항등
            # 학습 실증). 좌표 보정 감독은 perturb 트랙 단독 소유.
            "corrected_coords": None,
            "faults": rec_report.get("faults") or [],
            "segments": rec_report.get("segments"),
            "svg_spec": _svg_spec(
                target_angle_deg=target,
                force_vector=src_svg.get("force_vector"),
                ideal_trajectory=src_svg.get("ideal_trajectory"),
            ),
            "time_anchors": rec_report.get("time_anchors"),
        }
        joint_keys = rec.get("joint_keys") or []
        frames = rec.get("coords_by_frame") or []
        out.append({
            "messages": [
                _system_msg(joint_keys),
                _user_media_msg(row["s3_key"], frames),
                _assistant_report_msg(rec.get("thought"), report),
            ],
            "_track": "distill",
            "_video_hash": vh,
            "_motion": row.get("motion"),
            # B 재균형 태깅 — 결함 보유 여부(정타 리포트=False). 교사 증류만 True 가능.
            "_has_faults": bool(report["faults"]),
        })
    return out


def _build_shadow_samples(manifest, shadow_loader) -> tuple[list[dict], int, int]:
    """22-03 vlm_shadow 트랙 (DR-01) — 등록+가명만 media, 나머지 text-only 강등.

    반환 (samples, unregistered_dropped, text_only_count). 미등록/미가명은 media 참조
    0 으로 강등하고 드롭 카운터를 방출한다(드롭률 은폐 불가).
    """
    if shadow_loader is None:
        return [], 0, 0
    by_hash = {r.get("video_hash"): r for r in manifest.get("rows", []) if r.get("video_hash")}
    out: list[dict] = []
    unregistered_dropped = 0
    text_only_count = 0
    for rec in shadow_loader() or []:
        vh = rec.get("video_hash")
        roles = rec.get("roles") or {}
        coach = (roles.get("coach") or {}).get("text")
        verdict = (roles.get("veto") or {}).get("verdict")
        row = by_hash.get(vh)
        registered = row is not None and row.get("anonymized") is True and row.get("s3_key")
        if registered:
            report = {
                "coaching": coach,
                "corrected_coords": None,
                "faults": [],
                "segments": None,
                "svg_spec": None,
                "time_anchors": None,
            }
            out.append({
                "messages": [
                    _system_msg([]),
                    _user_media_msg(row["s3_key"], []),
                    _assistant_report_msg(None, report),
                ],
                "_track": "shadow",
                "_video_hash": vh,
                "_motion": (row or {}).get("motion"),
                "_has_faults": False,  # shadow 리포트 faults=[] 고정(fault-free).
            })
            continue
        # 미등록/미가명 → media 참조 0, text-only 강등(DR-01).
        unregistered_dropped += 1
        verdict_text = coach or (f"판정: {verdict}" if verdict else None)
        if not verdict_text:
            continue
        text_only_count += 1
        out.append({
            "messages": [
                _system_msg([]),
                _user_text_msg("이 동작에 대한 코칭/판정을 서술하세요."),
                _assistant_text_msg(verdict_text),
            ],
            "_track": "shadow",
            "_video_hash": vh,
            "_text_only": True,
        })
    return out, unregistered_dropped, text_only_count


def _build_eye_samples(eye_loader) -> tuple[list[dict], dict]:
    """기계 눈 원장(admit 행) → eye 트랙 샘플 + 관측 카운터 (quick 260814-j24).

    fail-closed 2겹: loader 층(full_batch.make_eye_loader)이 disposition=admit +
    motion 보유만 방출하고, 이 층이 다시 같은 조건과 media_key 존재를 확인한다.
    hold 행이 JSONL 에 유입되면 프라이버시 fence(P-1/P-3)가 무너지므로 이중 확인이다.
    """
    if eye_loader is None:
        return [], {"eye_admitted_count": 0}
    out: list[dict] = []
    for row in eye_loader() or []:
        if row.get("disposition") != "admit":
            continue  # hold 행 차단(프라이버시 fence).
        motion = row.get("motion")
        media_key = row.get("media_key")
        if not motion or not media_key:
            continue  # P-5 motion 미해결 / 미디어 미상 — dump-all 차단.
        agrees = row.get("track_claim_agrees")
        report = {
            "joint": row.get("joint"),
            "limb": row.get("limb"),
            "observed": row.get("observed"),
            "reason": row.get("reason"),
            "side": row.get("side"),
            "track_claim": row.get("claim"),
            "track_claim_agrees": agrees,
        }
        pending = not bool(row.get("uploaded"))
        out.append({
            "messages": [
                {"role": "system", "content": _EYE_SYSTEM},
                _user_image_msg(media_key, row.get("joint"), row.get("side"), row.get("claim")),
                _assistant_eye_msg(report),
            ],
            "_track": "eye",
            "_motion": motion,
            "_video_hash": None,   # 크롭은 영상 행이 아니다 — val split 대상 아님.
            "_has_faults": False,  # eye 는 관측 트랙(항상 fault-free).
            "_eye_agrees": agrees,
            "_eye_observed": row.get("observed"),
            "_media_pending_upload": pending,
        })
    return out, {"eye_admitted_count": len(out)}


def _eye_counters(eye_samples) -> dict:
    """최종(leakage 드롭 + 균등 트림 후) eye 관측치 — 은폐 불가하게 _meta 로 방출."""
    observed: dict = {}
    motions: dict = {}
    mismatch = pending = 0
    for s in eye_samples:
        obs = s.get("_eye_observed")
        observed[obs] = observed.get(obs, 0) + 1
        m = s.get("_motion")
        motions[m] = motions.get(m, 0) + 1
        if s.get("_eye_agrees") is False:
            mismatch += 1
        if s.get("_media_pending_upload"):
            pending += 1
    return {
        "eye_mismatch_count": mismatch,
        "eye_media_pending_upload": pending,
        "eye_observed_counts": observed,
        "eye_motion_counts": motions,
    }


def _build_text_samples(n_media: int, mix_ratios: dict) -> list[dict]:
    """T3 순수 텍스트 시간추론 + 순수 텍스트 instruction 혼합(D-11, 언어 감퇴 방지)."""
    out: list[dict] = []
    n_t3 = max(1, round(mix_ratios.get("t3_temporal", 0.0) * n_media))
    n_inst = max(1, round(mix_ratios.get("instruction", 0.0) * n_media))
    for k in range(n_t3):
        out.append({
            "messages": [
                {"role": "system", "content": "시각 정보 없이 프레임 순서/속도를 시간 추론으로 답하세요."},
                _user_text_msg(
                    f"프레임 {k}→{k+1}→{k+2} 순으로 무릎 각도가 커진다면 동작은 신전인가 굴곡인가?"
                ),
                _assistant_text_msg("각도가 커지므로 신전(펴짐)입니다."),
            ],
            "_track": "text",
            "_text_kind": "t3_temporal",
            "_text_only": True,
        })
    for k in range(n_inst):
        out.append({
            "messages": [
                {"role": "system", "content": "당신은 폴스포츠 코칭 어시스턴트입니다."},
                _user_text_msg("폴스포츠에서 '라인'이 무엇을 뜻하는지 한 문장으로 설명하세요."),
                _assistant_text_msg("라인은 몸 전체의 정렬·연장선이 만드는 심미적 곧은 선을 뜻합니다."),
            ],
            "_track": "text",
            "_text_kind": "instruction",
            "_text_only": True,
        })
    return out


# ---------------------------------------------------------------------------
# 균등 게이트 + video_hash split.
# ---------------------------------------------------------------------------
def _motion_counts(media_samples) -> dict:
    counts: dict = {}
    for s in media_samples:
        m = s.get("_motion")
        if m is None:
            continue
        counts[m] = counts.get(m, 0) + 1
    return counts


def _balance_media(media_samples) -> list[dict]:
    """동작별 media 샘플을 max <= 2*min 로 트림(결정적, 안정 순서). 균등 게이트."""
    counts = _motion_counts(media_samples)
    valid = [v for v in counts.values() if v > 0]
    if not valid:
        return media_samples
    cap = 2 * min(valid)
    kept: list[dict] = []
    per: dict = {}
    for s in media_samples:
        m = s.get("_motion")
        if m is None:
            kept.append(s)
            continue
        per[m] = per.get(m, 0) + 1
        if per[m] <= cap:
            kept.append(s)
    return kept


def _cap_fault_free(media, cap_ratio):
    """fault-free(faults=[]) 미디어를 fault-bearing(faults>0) 대비 캡 비율로 트림(B).

    반환 (trimmed_media, fault_bearing_count, fault_free_count) — 최종(트림 후) 관측치.
    결정적: 원 media 순서를 보존하며 fault-free 를 cap = int(cap_ratio*nb) 개까지만
    유지(안정 입력 순서, 랜덤/오버샘플 0). fault_bearing==0 이면 캡 skip(전량 트림
    방지 guard — 정타 신호 완전 소거는 역방향 위양성 실패, invariant
    [[analysis-objectivity-no-human-scores]]). fault-bearing 은 절대 트림하지 않는다."""
    nb = sum(1 for s in media if s.get("_has_faults"))
    nf = sum(1 for s in media if not s.get("_has_faults"))
    if nb == 0:
        return media, nb, nf  # guard: fault 신호 없으면 캡 미적용.
    cap = int(cap_ratio * nb)
    if nf <= cap:
        return media, nb, nf
    kept: list[dict] = []
    free_kept = 0
    for s in media:
        if s.get("_has_faults"):
            kept.append(s)
        elif free_kept < cap:
            kept.append(s)
            free_kept += 1
    return kept, nb, free_kept


def _split_val_hashes(hashes, validation_owner, val_frac):
    """video_hash 단위 val 집합 — explicit_val_jsonl 만 val 생성(leakage 0)."""
    if validation_owner != "explicit_val_jsonl":
        return set()
    ordered = sorted(h for h in hashes if h)
    n = len(ordered)
    if n < 2:
        return set()
    n_val = max(1, round(n * val_frac))
    return set(ordered[:n_val])


# ---------------------------------------------------------------------------
# 조립 진입점.
# ---------------------------------------------------------------------------
def build_dataset(
    *,
    manifest: dict,
    perturb_loader=None,
    distill_loader=None,
    shadow_loader=None,
    reference_loader=None,
    eye_loader=None,
    mix_ratios: dict | None = None,
    validation_owner: str = "explicit_val_jsonl",
    val_frac: float = 0.02,
    partial: bool = False,
    include_perturb: bool = False,
    seed: int = 0,
) -> dict:
    """3트랙 + 텍스트 혼합 학습셋 조립 → {"train", "val"|None, "_meta"}.

    validation_owner = explicit_val_jsonl(val.jsonl 발행, video_hash split) 또는
    phase22_eval_gate(val 미발행, held-out eval gate 가 소유). 값과 발행물이 정합한다(DR-04).

    include_perturb (belle C1 결정 2026-07-15, quick-260715-wq9): 기본 False —
    corrected_coords 전체 프레임 배열 방출 학습을 기본 학습셋에서 제외한다. 모델이
    5/5 빈배열로 거부 + perturb 95행(전부 faults=[])이 결함 신호를 익사시키는 최대
    주범이라 좌표보정 학습을 보류한다(삭제 아님 — 플래그 True 로 언제든 부활,
    D-10a 구현·NotebookLM 좌표 CoT 비전 보존, 가역 descope).
    """
    if validation_owner not in _VALID_VALIDATION_OWNERS:
        raise ValueError(
            f"validation_owner must be one of {_VALID_VALIDATION_OWNERS}: {validation_owner!r}"
        )
    assert_collection_complete(manifest, partial)
    mix_ratios = mix_ratios or DEFAULT_MIX_RATIOS
    rng = np.random.default_rng(seed)

    # C1 (belle 2026-07-15): perturb 트랙은 기본 off — include_perturb=True 로만 부활.
    perturb_samples = (
        _build_perturb_samples(manifest, perturb_loader, reference_loader, rng)
        if include_perturb
        else []
    )
    distill_samples = _build_distill_samples(manifest, distill_loader, reference_loader)
    shadow_samples, shadow_dropped, shadow_text_only = _build_shadow_samples(
        manifest, shadow_loader
    )

    # 균등 게이트는 **트랙별 독립** 적용 — 합산 적용 시 트랙 간 자리 경쟁이 생겨
    # 앞 트랙이 뒤 트랙을 잠식한다 (22-07A 실증: perturb 주입이 distill 85→38).
    # 각 트랙은 자체적으로 동작 균등(max<=2*min)을 만족하고, 트랙 혼합비는 별개 축.
    media_core = (
        _balance_media(perturb_samples)
        + _balance_media(distill_samples)
        + _balance_media([s for s in shadow_samples if sample_has_video(s)])
    )
    # B 재균형 — fault-free 미디어를 fault-bearing 대비 캡(결함 신호 익사 방지).
    # 트랙별 균등 게이트 이후, 트림된 media 기준으로 text 혼합이 자동 축소된다.
    # ★ eye 를 넣기 **전에** 적용한다: eye 는 전부 fault-free 라 캡을 잡아먹어 기존
    #   distill 행을 밀어낸다 — 이 순서를 어기면 무회귀 1급 게이트 위반이다.
    media_core, fault_bearing_count, fault_free_count = _cap_fault_free(
        media_core, FAULT_FREE_CAP_RATIO
    )
    shadow_text = [s for s in shadow_samples if not sample_has_video(s)]
    # 언어 감퇴 방지 혼합비의 분모는 media_core 로 고정한다 — eye 는 다른 태스크(관절
    # 상태 관측)라 "영상 태스크 대비 텍스트 비율" 의 분모가 아니다. 분모에 넣으면
    # eye 주입만으로 텍스트 행 수가 늘어 기존 3트랙 산출이 바뀐다(무회귀 위반).
    text_samples = _build_text_samples(len(media_core), mix_ratios)

    # video_hash 단위 split (leakage 0) — 소유자는 이 모듈 단독.
    media_hashes = {s.get("_video_hash") for s in media_core if s.get("_video_hash")}
    val_hashes = _split_val_hashes(media_hashes, validation_owner, val_frac)

    # eye 트랙 — val 에 속한 media 의 motion 과 겹치는 eye 샘플은 드롭(leakage 0).
    # eye 행은 video_hash 가 없어 hash split 으로는 격리되지 않으므로 motion 격리다.
    eye_samples, eye_counters = _build_eye_samples(eye_loader)
    val_motions = {
        s.get("_motion") for s in media_core
        if s.get("_video_hash") in val_hashes and s.get("_motion")
    }
    eye_kept = [s for s in eye_samples if s.get("_motion") not in val_motions]
    eye_leakage_dropped = len(eye_samples) - len(eye_kept)
    eye_balanced = _balance_media(eye_kept)  # 트랙 독립 균등(max <= 2*min).
    # 균등 트림 손실은 반드시 노출한다(드롭률 은폐 금지 — shadow_unregistered_dropped 관례).
    # eye 는 motion 별 표본이 아직 얇아 min 이 1 이면 cap 이 2 로 내려앉는다: 손실이
    # 크면 코드 문제가 아니라 motion 커버리지 문제다(수확 범위 확대가 처방).
    eye_balance_trimmed = len(eye_kept) - len(eye_balanced)

    media = media_core + eye_balanced
    all_samples = media + shadow_text + text_samples

    train: list[dict] = []
    val: list[dict] = []
    for s in all_samples:
        vh = s.get("_video_hash")
        if vh and vh in val_hashes:
            val.append(s)
        else:
            train.append(s)

    track_counts: dict = {"perturb": 0, "distill": 0, "shadow": 0, "text": 0, "eye": 0}
    for s in all_samples:
        t = s.get("_track")
        if t in track_counts:
            track_counts[t] += 1

    # 좌표전용 perturb 샘플 수(D5) — 균등 게이트 트림 후 최종 기준. 드롭률/혼합 실측 노출.
    perturb_coords_only_count = sum(
        1 for s in media if s.get("_track") == "perturb" and s.get("_coords_only")
    )

    # motion_counts 는 media_core 기준을 유지한다 — eye 를 섞으면 기존 _meta 값이
    # 바뀌어 additive 계약이 깨진다. eye 분포는 eye_motion_counts 로 따로 방출.
    meta = {
        "schema_version": schema.SCHEMA_VERSION,
        "prompt_version": schema.PROMPT_VERSION,
        "manifest_version": (manifest or {}).get("_meta", {}).get("schema_version"),
        "validation_owner": validation_owner,
        "track_counts": track_counts,
        "perturb_coords_only_count": perturb_coords_only_count,
        # B 재균형 관측치 — 드롭률/혼합 실측 노출(은폐 불가). 최종(트림 후) 카운트.
        "fault_bearing_count": fault_bearing_count,
        "fault_free_count": fault_free_count,
        "fault_free_cap_ratio": FAULT_FREE_CAP_RATIO,
        "motion_counts": _motion_counts(media_core),
        "shadow_unregistered_dropped": shadow_dropped,
        "shadow_text_only_count": shadow_text_only,
        "mix_ratios": dict(mix_ratios),
        "partial": bool(partial),
        "upload_prefix": resolve_upload_prefix(partial),
    }
    # eye 트랙 관측치 — 전부 additive 키(미주입 시 0/빈 dict).
    meta.update(eye_counters)
    meta.update(_eye_counters(eye_balanced))
    meta["eye_leakage_dropped"] = eye_leakage_dropped
    meta["eye_balance_trimmed"] = eye_balance_trimmed

    return {
        "train": train,
        "val": val if validation_owner == "explicit_val_jsonl" else None,
        "_meta": meta,
    }


# ---------------------------------------------------------------------------
# 로컬 기록 (S3 업로드는 Task 4 에서 uploader 주입 배선).
# ---------------------------------------------------------------------------
def write_jsonl(samples, path: Path) -> None:
    with Path(path).open("w", encoding="utf-8") as fp:
        for s in samples:
            fp.write(json.dumps(s, ensure_ascii=False) + "\n")


def write_dataset(data: dict, out_dir: Path) -> dict:
    """train.jsonl / (explicit 시) val.jsonl / _meta.json 로컬 기록. 경로 dict 반환."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {"train": out_dir / "train.jsonl", "meta": out_dir / "_meta.json"}
    write_jsonl(data["train"], paths["train"])
    if data.get("val") is not None:
        paths["val"] = out_dir / "val.jsonl"
        write_jsonl(data["val"], paths["val"])
    (out_dir / "_meta.json").write_text(
        json.dumps(data["_meta"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {k: str(v) for k, v in paths.items()}


if __name__ == "__main__":  # pragma: no cover - 실 배선(loader/업로드)은 Task 4.
    ap = argparse.ArgumentParser(description="Phase 22 학습 JSONL 조립기")
    ap.add_argument("--partial", action="store_true", help="collection_complete 미완 부분 실행(canonical 업로드 금지)")
    ap.add_argument("--validation-owner", default="explicit_val_jsonl", choices=_VALID_VALIDATION_OWNERS)
    ap.parse_args()
    raise SystemExit(
        "실 loader(Firestore vlm_shadow / S3 coords) + 업로드 배선은 22-04 Task 4"
        "(라이브 Pod + belle 승인)에서 실행한다."
    )

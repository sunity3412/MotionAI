"""Gemini motion_name 정규화 — production 모듈.

Plan 5-01 (2026-06-04, B2 fix revision). 박제 정신:
  · Gemini 응답이 한국어 / 영어 / IPSF code 중 어느 형태로 와도 5영상 scope 로 정규화.
  · spike (backend/research/spikes/spike_gemini_motion_classify.py) 가 본 모듈을 import
    (역방향 금지). Pod / Lambda runtime 에서 backend/research/spikes/ 경로 의존 0.
  · GeminiTechniqueRecognizer._classify_motion 가 본 모듈의 classify_motion_name 호출.
  · D-01 박제: v1 인식 스코프 = 5영상 (`ref-climb` / `ref-foxtop` / `ref-foxtop-split` /
    `ref-invert` / `ref-sideway-spin`). 그 외 = "unregistered" → Page 9 절대 트랙 단독 채점
    + TERM-DATA-01 분기 3 자동 수집 path (D-09 case 3).
  · P1 (2026-06-27, quick-260627-afq step 4): 10 motion scope — 기존 5 +
    `ref-kip-up` / `ref-power-spin` / `ref-peter-pan` / `ref-elbow-twist-sister` /
    `ref-pdshape` 객관 무릎신전(IPSF 180° 보편기준) 등록. sanctioned 근거 =
    15-IPSF-SOURCING-2026-06-27.md belle 결정 + 각 ref-{move}.yaml EXTEND 무릎 criteria.

박제 정신:
  · [[studio-term-3branch-system.md]] 분기 1 (학원 통용 한국어) → canonical 매핑.
  · [[analysis-objectivity-no-human-scores.md]] — 정규화 결과는 객관 enum, 사람 점수 X.
"""

from __future__ import annotations


# 박제 scope. REGISTERED_MOTIONS 변경은 Phase 5 scope 정의 변경과 동치 — P1
# (2026-06-27, quick-260627-afq) 가 5→10 확장의 sanctioned 근거(객관 무릎신전 등록).
REGISTERED_MOTIONS: frozenset[str] = frozenset(
    {
        # D-01 원 5영상 scope.
        "ref-climb",
        "ref-foxtop",
        "ref-foxtop-split",
        "ref-invert",
        "ref-sideway-spin",
        # P1 step 4 (2026-06-27): 객관 IPSF 무릎신전(180°) criteria yaml 보유 5동작.
        "ref-kip-up",
        "ref-power-spin",
        "ref-peter-pan",
        "ref-elbow-twist-sister",
        "ref-pdshape",
    }
)

# 한국어 / 영어 → canonical 매핑 (alias table).
# 모두 lowercase 박제. lookup 시 입력도 lowercase 정규화.
# 박제 정신: 학원 통용 한국어 (분기 1) + 영어 공식 명 (IPSF / 폴-arina) 모두 흡수.
# 부분 문자열 매치 (Step 3) 가 alias 우선순위 충돌을 흡수.
_ALIAS_TABLE: dict[str, str] = {
    # 한국어 (학원 통용, 분기 1) ----------------------------------------
    "인버트": "ref-invert",
    "인버티드": "ref-invert",
    "인버티드 버터플라이": "ref-invert",
    "인버티드버터플라이": "ref-invert",
    "기본 인버트": "ref-invert",
    "베이직 인버트": "ref-invert",
    "폭스탑": "ref-foxtop",
    "폭스 탑": "ref-foxtop",
    "여우탑": "ref-foxtop",
    "폭스탑 스플릿": "ref-foxtop-split",
    "폭스탑스플릿": "ref-foxtop-split",
    "폭스 탑 스플릿": "ref-foxtop-split",
    "폭스탑 다리벌리기": "ref-foxtop-split",
    "사이드웨이 스핀": "ref-sideway-spin",
    "사이드웨이스핀": "ref-sideway-spin",
    "사이드 스핀": "ref-sideway-spin",
    "사이드스핀": "ref-sideway-spin",
    "옆돌기": "ref-sideway-spin",
    "클라임": "ref-climb",
    "클라이밍": "ref-climb",
    "오르기": "ref-climb",
    "베이직 클라임": "ref-climb",
    # 영어 (공식/IPSF/폴-arina) ----------------------------------------
    "inverted butterfly": "ref-invert",
    "invert": "ref-invert",
    "basic invert": "ref-invert",
    "inverted": "ref-invert",
    "inverted split": "ref-foxtop-split",
    "fox top": "ref-foxtop",
    "foxtop": "ref-foxtop",
    "fox top split": "ref-foxtop-split",
    "foxtop split": "ref-foxtop-split",
    "sideway spin": "ref-sideway-spin",
    "sideways spin": "ref-sideway-spin",
    "side spin": "ref-sideway-spin",
    "climb": "ref-climb",
    "basic climb": "ref-climb",
    # ── P1 step 4 (2026-06-27) 객관 무릎신전 5동작 한/영 alias ──────────────
    # kip-up (학원 명칭 / 영어)
    "킵업": "ref-kip-up",
    "킵 업": "ref-kip-up",
    "kip-up": "ref-kip-up",
    "kip up": "ref-kip-up",
    "kipup": "ref-kip-up",
    # power-spin
    "파워스핀": "ref-power-spin",
    "파워 스핀": "ref-power-spin",
    "power spin": "ref-power-spin",
    "power-spin": "ref-power-spin",
    "powerspin": "ref-power-spin",
    # peter-pan
    "피터팬": "ref-peter-pan",
    "피터 팬": "ref-peter-pan",
    "peter pan": "ref-peter-pan",
    "peter-pan": "ref-peter-pan",
    "peterpan": "ref-peter-pan",
    # elbow-twist-sister (긴 alias 우선 — substring 매치가 "elbow twist" 를 흡수, 동일 canonical)
    "엘보 트위스트 시스터": "ref-elbow-twist-sister",
    "엘보트위스트": "ref-elbow-twist-sister",
    "엘보 트위스트": "ref-elbow-twist-sister",
    "elbow twist sister": "ref-elbow-twist-sister",
    "elbow twist": "ref-elbow-twist-sister",
    "elbow-twist": "ref-elbow-twist-sister",
    # pdshape
    "pdshape": "ref-pdshape",
    "pd shape": "ref-pdshape",
    "pd-shape": "ref-pdshape",
    "피디쉐입": "ref-pdshape",
    "피디 쉐입": "ref-pdshape",
}


def _normalize(raw: str) -> str:
    """lowercase + 양끝 공백 제거. 중간 공백은 substring 매치에서 의미.

    Gemini 응답이 IPSF code 형식 (예: "IPSF §4.2 Inverted Split (code XYZ)") 일 때
    괄호 부분은 substring 매치가 흡수.
    """
    return raw.strip().lower()


def classify_motion_name(raw_name: str) -> tuple[str, str]:
    """raw_name → (canonical_motion, scope_status).

    Args:
      raw_name: Gemini 응답의 motion 이름 (한국어 / 영어 / IPSF code 또는 그 mix).

    Returns:
      (canonical, scope_status):
        · canonical ∈ REGISTERED_MOTIONS 또는 raw_name (unregistered 시).
        · scope_status ∈ {"recognized", "unregistered"}.

      GeminiTechniqueRecognizer._classify_motion 가 `scope_status == "unregistered"`
      로 D-09 case 3 분기를 결정한다. 즉, 본 함수의 position 1 이 분기 키.

    매핑 단계:
      1. 정확 매치 — `_normalize(raw_name)` 가 REGISTERED_MOTIONS 에 있으면 통과.
         (Gemini 가 `ref-invert` 같이 정확한 ID 반환 케이스.)
      2. alias table — `_normalize` 결과 정확 매치.
      3. 부분 문자열 매치 — alias key 가 raw 안에 substring 으로 등장.
         예: "IPSF §4.2 Inverted Split (code XYZ)" → "inverted split" 매치 → ref-foxtop-split.
         가장 긴 매치를 우선 (그렇지 않으면 "invert" 가 "inverted split" 을 가로챔).
      4. 매치 실패 → (raw_name, "unregistered").

    박제 정신:
      · 사람 점수 X — 정규화 결과는 객관 enum.
      · REGISTERED_MOTIONS 변경 = Phase 5 scope 정의 변경 (별도 박제 작업).
    """
    if not isinstance(raw_name, str) or not raw_name.strip():
        return (raw_name or "", "unregistered")

    norm = _normalize(raw_name)

    # Step 1: 정확 매치 (canonical ID 직접 반환).
    if norm in REGISTERED_MOTIONS:
        return (norm, "recognized")

    # Step 2: alias table 정확 매치.
    if norm in _ALIAS_TABLE:
        return (_ALIAS_TABLE[norm], "recognized")

    # Step 3: 부분 문자열 매치 (긴 key 우선 — "inverted split" 이 "invert" 보다 우선).
    # canonical ID 자체도 substring 후보로 포함 (예: "Sequence: ref-invert performed").
    candidates: list[tuple[int, str]] = []
    for alias, canonical in _ALIAS_TABLE.items():
        if alias in norm:
            candidates.append((len(alias), canonical))
    for canonical_id in REGISTERED_MOTIONS:
        if canonical_id in norm:
            candidates.append((len(canonical_id), canonical_id))

    if candidates:
        # 가장 긴 매치 우선. 동률 시 alias_table 등재 순서 무관 — 결과 canonical 만 사용.
        candidates.sort(key=lambda x: x[0], reverse=True)
        return (candidates[0][1], "recognized")

    # Step 4: 매치 실패 → unregistered. raw_name 그대로 (alias / case 변환 X)
    # 보존 — Firestore 자동 수집 (TERM-DATA-01 분기 3) 가 학원 통용 용어를 그대로 저장.
    return (raw_name, "unregistered")

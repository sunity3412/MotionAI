"""분석 산출물의 출처(provenance) — 어느 코드·어느 기준으로 나온 결과인지 (quick-260919-tkv).

왜 만드는가 (belle 2026-09-19):
  "분석이 할 때마다 다르니까 문제 아냐. 언제는 3장이라 보고하고 6장이라 보고하고
   5장이라 보고하고 ... 몇 일은 이렇게 몇 일은 이렇게 해서 꼬이는 거 아냐."

라이브 이전 이력을 실측해 원인을 갈랐다 (같은 pdshape 영상, belle 계정 실 doc):

  | 언제            | 점수 | 감점 | 결과 지문 | 버전 기록 |
  |-----------------|------|------|-----------|-----------|
  | 3판 (9/02~9/03) | 60   | 5    | 389f9b31  | 없음      |
  | 3판 (9/09)      | 60   | 6    | 3ac37f2f  | 없음      |
  | 오늘            | 80   | 1    | c162916   | 없음      |

결론 두 개:
  (1) **비결정성이 아니다.** 같은 코드에서 3번 돌려 3번 다 지문이 같다(두 묶음 모두
      3/3). 주사위가 아니라 우리가 바꿀 때마다 움직이는 것이다.
  (2) **어느 판이 어느 코드/기준에서 나왔는지 기록이 doc 어디에도 없다.** 그래서
      답이 바뀌면 **분석이 바뀐 건지 우리가 바꾼 건지 구분할 수단이 없다.** 이것이
      belle 이 말한 "꼬임"의 기계적 원인이다.

이 모듈은 그 기록만 만든다 — **채점 무접촉.** 점수·감점·카드 수를 읽지도 쓰지도
않는다. 소급 채움도 없다(과거 doc 은 그대로 — 앞으로 나오는 분석부터 실린다).

노출값은 전부 **비밀이 아니다** — 커밋 SHA·릴리스 id·플래그 bool·엔진 클래스명은
릴리스 provenance 이지 시크릿이 아니다. 토큰·키·env **원문 값** 은 절대 싣지 않는다
(`runpod_inference/server.py` /health 의 T-04-W5-01 규율 승계).

Lambda·Pod 양쪽에서 돈다 — 무거운 의존(rtmlib/onnxruntime/torch) 을 import 하지
않는다. 그래서 아래 env 판정 규칙은 **소비처 코드를 그대로 복제** 하고, 복제가
어긋나지 않는 것은 `backend/tests/test_analysis_provenance.py` 의 parity 테스트가
지킨다 (contract.md §11.13 lockstep).
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Mapping
from pathlib import Path

log = logging.getLogger(__name__)

# 커밋 SHA 우선순위 1순위 — 배포 파이프라인이 주입하는 env (git 없는 Lambda 용).
COMMIT_SHA_ENV = "SUNITY_COMMIT_SHA"

# `git rev-parse HEAD` 를 돌릴 위치. Layer 로 배포되면 /opt/python/... 라 git 이
# 없고, 그때는 조용히 None 이 된다(추측 금지 — 키 생략).
#   provenance.py → sunity_shared → python → shared → backend
_BACKEND_DIR = Path(__file__).resolve().parents[3]

# ── env 플래그 판정 — 규칙이 플래그마다 다르다 (실측, 2026-09-19) ──────────────
#
# 이 셋은 "다 같은 bool" 이 아니다. 실제 동작을 켜는 소비처가 서로 다른 규칙을 쓴다:
#
#   ROT180_INVERSION_ENABLED  strip().lower() in ("1","true")
#     ← pose_engines/rtmw/rtmw_engine.py `_env_on` (_ROT180_INVERSION_ENV)
#   PR_INVERSION_ENABLED      strip().lower() in ("1","true")
#     ← 같은 `_env_on` (_PR_INVERSION_ENV)
#   RTMW_DETERMINISTIC        == "1"  (strip 없음, "true" 도 OFF)
#     ← pose_engines/rtmw/ort_determinism.py `deterministic_enabled`
#
# provenance 는 **실제로 켜졌던 것** 을 적어야 하므로 소비처 규칙을 그대로 따른다.
# (참고: runpod_inference/server.py `/health` 의 `_env_flag` 는 ("1","true","on",
#  "yes") 라 세 플래그 모두에 더 느슨하다 — 즉 `RTMW_DETERMINISTIC=true` 면
#  health 는 True 라 하고 엔진은 OFF 다. 그 불일치는 이 단위의 범위 밖이라
#  손대지 않았고 SUMMARY 에 기록했다. 이 모듈은 엔진 쪽을 따른다.)
_FLAG_TRUE_1_OR_TRUE = ("1", "true")


def _flag_1_or_true(name: str, env: Mapping[str, str] | None = None) -> bool:
    """rtmw_engine._env_on 복제 — strip+lower 후 "1"/"true" 만 True."""
    src: Mapping[str, str] = os.environ if env is None else env
    return src.get(name, "").strip().lower() in _FLAG_TRUE_1_OR_TRUE


def _flag_exact_1(name: str, env: Mapping[str, str] | None = None) -> bool:
    """ort_determinism.deterministic_enabled 복제 — 정확히 "1" 만 True."""
    src: Mapping[str, str] = os.environ if env is None else env
    return src.get(name, "") == "1"


# analysisVersion 의 플래그 3종: (doc 키, env 이름, 판정 함수).
# doc 키는 camelCase — contract 관례(app/src/types/analysis.ts 미러)이고,
# env 원문 이름을 doc 키로 쓰면 값이 아니라 **이름** 으로 env 를 흘리는 모양이 된다.
_FlagPredicate = Callable[[str, "Mapping[str, str] | None"], bool]

PROVENANCE_FLAGS: tuple[tuple[str, str, _FlagPredicate], ...] = (
    ("rot180InversionEnabled", "ROT180_INVERSION_ENABLED", _flag_1_or_true),
    ("prInversionEnabled", "PR_INVERSION_ENABLED", _flag_1_or_true),
    ("rtmwDeterministic", "RTMW_DETERMINISTIC", _flag_exact_1),
)

# analysisVersion 이 실을 수 있는 전체 키 (models.ANALYSIS_VERSION_KEYS lockstep).
ANALYSIS_VERSION_KEYS: tuple[str, ...] = (
    "commitSha",
    "referenceRelease",
    "poseEngine",
) + tuple(k for k, _e, _f in PROVENANCE_FLAGS)


_commit_sha_cache: str | None = None


def resolve_commit_sha() -> str | None:
    """이 프로세스가 로드한 코드의 커밋 SHA. 못 구하면 **None** (추측 금지).

    우선순위: `SUNITY_COMMIT_SHA` env → `git rev-parse HEAD` (backend/ 기준).
    프로세스 1회 캐시 — warm 재사용 중 작업트리가 바뀌어도 이 값은 **부팅 시점
    리비전** 을 가리킨다. 그게 핵심이다(프로세스가 실제로 로드한 코드).

    quick-260919-tkv 이전에는 이 함수가 runpod_inference/server.py 안에만 있어
    Pod 전용이었다(server 는 Lambda 에서 import 불가). 분석 doc 에 실으려면
    Lambda 경로에서도 돌아야 해서 여기로 옮겼고, server.py 가 이것을 호출한다 —
    구현은 한 벌뿐이다.
    """
    global _commit_sha_cache
    if _commit_sha_cache is not None:
        return _commit_sha_cache or None

    sha = os.environ.get(COMMIT_SHA_ENV, "").strip()
    if not sha:
        try:
            import subprocess

            out = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(_BACKEND_DIR),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if out.returncode == 0:
                sha = out.stdout.strip()
        except Exception:  # noqa: BLE001 - git 부재/타임아웃은 '모른다' 로 강등
            sha = ""

    # 빈 문자열을 캐시해 재시도(subprocess) 를 막되, 반환은 None 으로 통일.
    _commit_sha_cache = sha
    return sha or None


def build_analysis_version(
    *,
    reference_release: str | None = None,
    pose_engine: str | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, str | bool]:
    """`result.analysisVersion` flat dict 조립 (scalar only — Firestore nested 금지).

    값을 못 구한 항목은 **키를 생략** 한다 (fail-closed). 빈 문자열·'unknown'·
    추측값으로 채우지 않는다 — 모르는 것을 아는 척하면 기록이 거짓말이 된다.

    Args:
        reference_release: 이 분석이 실제로 overlay 한 기준 라이브러리 candidate
            version (예 'rot180_v1'). mode3 등 기준 없는 경로는 None → 키 생략.
        pose_engine: 포즈 엔진 클래스명 (예 'RTMWPoseEngine'). 어댑터 미로드 경로는
            None → 키 생략. 출처는 /health canary 와 같다(pipeline `_RTMW_ENGINE`).
        env: 테스트 주입용 env mapping (기본 os.environ).

    Returns:
        flat dict. 플래그 3종은 항상 bool 로 실린다(env 미설정 = False 가 곧 사실).
        따라서 반환 dict 는 절대 비지 않는다 — `analysisVersion` 의 **존재 자체** 가
        "quick-260919-tkv 이후 분석" 표식이고, 그 안의 키 부재가 "그 항목을 못 구했다"
        는 뜻이다.
    """
    out: dict[str, str | bool] = {}

    sha = resolve_commit_sha()
    if isinstance(sha, str) and sha:
        out["commitSha"] = sha

    if isinstance(reference_release, str) and reference_release:
        out["referenceRelease"] = reference_release

    if isinstance(pose_engine, str) and pose_engine:
        out["poseEngine"] = pose_engine

    for doc_key, env_name, predicate in PROVENANCE_FLAGS:
        out[doc_key] = bool(predicate(env_name, env))

    return out

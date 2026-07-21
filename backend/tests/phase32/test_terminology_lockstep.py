"""Plan 32-05 Task 2 — 용어 맵 단일 출처 ↔ 앱 미러 lockstep (D-12).

단일 출처 = backend/data/terminology_map.json. app/src/lib/terminologyMap.ts 는
그 미러다. 본 테스트는 **양방향** 텍스트 대조로 drift 를 차단한다 (주석 정합이
아니라 테스트 정합 — D-12):
  · forward  : JSON terms 의 전 키·값 문자열이 TS 파일 텍스트에 존재.
  · backward : TS TERMINOLOGY_MAP 의 전 항목(키·값)이 JSON terms 에 존재
               (TS 에만 있는 매핑도 실패).

계약 lockstep 텍스트 대조 선례(phase12 keypoint_report_lockstep) 복제.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from sunity_shared.analysis import phrasebook

_REPO_ROOT = Path(__file__).resolve().parents[3]
_TS_PATH = _REPO_ROOT / "app" / "src" / "lib" / "terminologyMap.ts"


def _json_terms() -> dict[str, str]:
    tmap = phrasebook.load_terminology_map()
    terms = tmap.get("terms", {})
    assert isinstance(terms, dict) and terms, "terminology_map.json terms 비었음"
    return terms


def _ts_text() -> str:
    return _TS_PATH.read_text(encoding="utf-8")


def _ts_map_entries(text: str) -> dict[str, str]:
    """TS TERMINOLOGY_MAP 객체 블록에서 `key: 'value'` 항목 추출 (헤더 주석 제외)."""
    block = re.search(
        r"TERMINOLOGY_MAP\s*=\s*\{(.*?)\}\s*as const", text, re.DOTALL
    )
    assert block, "terminologyMap.ts 에 `TERMINOLOGY_MAP = { ... } as const` 블록 없음"
    body = block.group(1)
    return {m.group(1): m.group(2) for m in re.finditer(r"(\w+):\s*'([^']*)'", body)}


def test_forward_json_terms_present_in_ts() -> None:
    text = _ts_text()
    for key, value in _json_terms().items():
        assert key in text, f"JSON term 키 {key!r} 가 terminologyMap.ts 에 없음"
        assert value in text, f"JSON term 값 {value!r} 가 terminologyMap.ts 에 없음"


def test_backward_ts_entries_present_in_json() -> None:
    terms = _json_terms()
    ts_entries = _ts_map_entries(_ts_text())
    assert ts_entries, "TS TERMINOLOGY_MAP 항목 파싱 0건"
    for key, value in ts_entries.items():
        assert key in terms, f"TS 에만 있는 매핑 키 {key!r} (JSON 단일 출처에 없음)"
        assert terms[key] == value, (
            f"값 drift key={key!r}: JSON={terms[key]!r} vs TS={value!r}"
        )


def test_bidirectional_key_set_identical() -> None:
    """키 집합이 정확히 동일 (개수·이름 drift 차단)."""
    terms = _json_terms()
    ts_entries = _ts_map_entries(_ts_text())
    assert set(terms) == set(ts_entries), (
        f"키 집합 불일치 JSON={sorted(terms)} TS={sorted(ts_entries)}"
    )

"""긴 영상에서 코칭이 통째로 수치 폴백으로 떨어지던 경로의 회귀 테스트.

증상(기록): 18초 영상 0건 실패 / 62초 포함 3/3 실패. 원인은 API 장애가 아니라
`max_completion_tokens=2500` 고정값 — 관절이 늘면 응답 JSON 이 중간에서 잘리고,
`json.loads` 가 던진 예외를 바깥 `except Exception` 이 삼켜 코칭 전체가 사라졌다.
로그도 "Cerebras 코칭 생성 실패"라 API 장애와 구분되지 않았다.

여기서 지키는 것 두 가지:
  1. 출력 상한이 관절 수를 따라간다 (짧은 영상은 기존 2500 그대로 — 바이트 불변).
  2. 그래도 잘리면 **완결된 관절만 건진다** — 3개 중 2개라도 살린다.
"""

from __future__ import annotations

import json

from sunity_shared.analysis.coach_writer import (
    _completion_budget,
    _salvage_partial_json,
)


class TestCompletionBudget:
    def test_어떤_경우에도_기존_상한보다_낮지_않다(self):
        # max_completion_tokens 는 **상한**이지 강제 길이가 아니다 — 올려도 모델이
        # 실제로 더 쓰지 않는 한 비용은 그대로다. 따라서 지켜야 할 불변식은
        # "기존 2500 아래로 내려가지 않는다" 이지 "2500 과 같다" 가 아니다.
        for n in range(0, 12):
            assert _completion_budget(n) >= 2500

    def test_관절이_늘면_상한도_는다(self):
        assert _completion_budget(6) > _completion_budget(1)
        assert _completion_budget(9) > _completion_budget(6)

    def test_상한에_뚜껑이_있다(self):
        # 무한정 키우지 않는다 — 비용과 지연이 따라 붙는다
        assert _completion_budget(100) == 8000


class TestSalvagePartialJson:
    def test_온전한_json_은_그대로(self):
        payload = {"shoulder": {"detail": "a"}, "hip": {"detail": "b"}}
        assert _salvage_partial_json(json.dumps(payload)) == payload

    def test_마지막_항목이_잘리면_앞의_완결분만_건진다(self):
        text = '{"shoulder": {"detail": "a"}, "hip": {"detail": "b"}, "knee": {"detail'
        got = _salvage_partial_json(text)
        assert got == {"shoulder": {"detail": "a"}, "hip": {"detail": "b"}}

    def test_첫_항목부터_잘리면_빈_dict(self):
        # 하나도 못 건지면 기존대로 수치 폴백 — 억지로 채우지 않는다
        assert _salvage_partial_json('{"shoulder": {"detail": "aaa') == {}

    def test_빈_문자열(self):
        assert _salvage_partial_json("") == {}

    def test_문자열_안의_중괄호에_속지_않는다(self):
        text = '{"shoulder": {"detail": "무릎을 {더} 펴세요"}, "hip": {"det'
        got = _salvage_partial_json(text)
        assert got == {"shoulder": {"detail": "무릎을 {더} 펴세요"}}

    def test_이스케이프된_따옴표에_속지_않는다(self):
        text = '{"shoulder": {"detail": "그는 \\"펴라\\" 했다"}, "hip": {"det'
        got = _salvage_partial_json(text)
        assert got == {"shoulder": {"detail": '그는 "펴라" 했다'}}

    def test_중첩이_깊어도_최상위_경계를_찾는다(self):
        text = (
            '{"shoulder": {"detail": "a", "detail2": {"causes": ["c1", "c2"]}}, '
            '"hip": {"detail": "b", "detail2": {"causes": ["x'
        )
        got = _salvage_partial_json(text)
        assert list(got.keys()) == ["shoulder"]
        assert got["shoulder"]["detail2"]["causes"] == ["c1", "c2"]

"""테스트 패키지 마커.

2026-08-28 추가 — 없으면 pytest 가 이 디렉터리의 conftest.py 를 **bare `conftest`**
로 등록한다. phase31/phase33 둘 다 conftest.py 를 가지고 있어서 이름이 충돌했고,
`from conftest import CommitLost` 가 옆 디렉터리(phase33)의 것을 잡아 ImportError 가
났다. 패키지로 만들면 `tests.phase31.conftest` 처럼 유일한 이름을 갖는다.
(다른 테스트 디렉터리는 이미 전부 __init__.py 를 갖고 있다 — 이 둘만 빠져 있었다)
"""

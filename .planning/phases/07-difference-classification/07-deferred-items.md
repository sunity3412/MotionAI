# Phase 7 deferred (out-of-scope) — Plan 02 박제

Plan 07-02 가 다음 pre-existing 환경 이슈를 발견했으나 scope 밖으로 deferred:

## tests/test_compare_engines_smoke.py — ModuleNotFoundError: 'backend'

- 위치: backend/tests/test_compare_engines_smoke.py:27
- 원인: `from backend.research.evaluations.compare_engines import ...` — 모듈 path 는
  repo root cwd 기반인데 pytest 는 backend cwd 에서 실행 → backend module 찾을 수 없음.
- Phase 7 무관 — Plan 11 sweep evaluation script. 별 plan 에서 fix 필요.
- 본 plan 의 게이트 = phase06 (136 PASS + 1 skipped) + phase07 (244 PASS, Plan 02 후) 만.

## SAM build cache

- backend/.aws-sam/cache/.../numpy/conftest.py 와 같은 cache 디렉토리도 pytest 가
  자동 수집 시 충돌 가능. 본 plan 에서는 영향 없음 — 명시적 path `tests/phase06/`
  + `tests/phase07/` 만 실행.

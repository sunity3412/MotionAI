# Phase 29 — Deferred / Out-of-Scope Discoveries

## 2026-07-16 (29-02 executor)

- **tests/pipeline end-to-end 스위트 로컬 실행 불가 (pre-existing, 환경)**: 로컬 python3(3.14 homebrew)에
  `imageio` 미설치 → `frame_extractor.py` import 실패로 `tests/pipeline` 15개 테스트가 base commit
  (935bef2)에서도 동일하게 FAIL (15 failed / 1 passed — 29-02 변경 전후 동일 세트, 신규 실패 0 확인).
  이 스위트는 heavy adapter deps(imageio/ffmpeg)가 있는 환경(Pod/CI)에서만 의미. 29-02 범위 밖 —
  수정하지 않음. 29-05 Pod sweep 게이트에서 실환경 검증됨.
- **backend/tests 로컬 pre-existing FAIL 44건 + collection error 12건 (환경)**: base commit
  935bef2 에서도 동일 세트로 FAIL (29-02 변경 전후 failure set diff = 0, 신규 실패 0 검증 완료).
  collection error 12건은 heavy deps(imageio/rtmlib/mediapipe/fixtures) 미설치 import 실패.
  44건은 로컬 자격/키 부재 등 환경 의존으로 추정 — 29-02 무관, 미수정.

"""R&D 비교군 평가 디렉터리.

Phase 1 Wave 2에서 compare_engines.py만 — NLF 격리 (Plan 04)는 Wave 3에서 진행.

Wave 순서 (H-1 박제, D-08/D-16 locked decision):
  Wave 1: MediaPipe 어댑터 (Plan 02) + PoleDetector/Aligner (Plan 03)
  Wave 2: compare_engines.py 회귀 검증 (본 Plan 06) — NLF 아직 옛 위치에 존재
  Wave 3: NLF R&D 격리 (Plan 04) + atomic swap (Plan 05) — belle 승인 후에만

패키지 구조:
  research/
    __init__.py
    evaluations/
      __init__.py
      compare_engines.py  — MediaPipe vs NLF 회귀 검증 스크립트
      reports/            — compare_engines.py 출력 디렉터리 (JSON + Markdown)
"""

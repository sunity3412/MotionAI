---
quick_id: 260923-swh
slug: clip-intake
date: 2026-09-23
mode: quick (inline — 260923-smt 와 같은 사유)
---

# Quick 260923-swh — 영상 받는 도구 + 짝 비교 (m49 인계서 §9 의 1·2)

belle 이 2026-09-24 경 영상을 준다. 그 전에 받을 준비.

## 무엇을 만드나 — 새 계산은 만들지 않는다

2026-09-23 kip-up 비교가 틀렸던 이유 두 가지를 구조로 막는다:
1. 어느 doc 을 썼는지 안 남았다 → **video_hash → 분석 doc 연결 원장**(`analysis_runs.jsonl`)
2. 운영과 다른 계산을 했다 → 짝 비교는 **기존 자(`measure_reference_axis.py`, 운영
   `_deviation_against` 호출)에 붙이고**, 점수·감점은 **저장된 값**을 읽는다

## Task 1 — `backend/scripts/intake_clips.py`

- `register --sheet` : 메모 시트(JSONL) → 검증 → 내용 해시 → S3 영구 사본(`fixtures/intake/`,
  `uploads/` 는 30일 수명) → `clips.jsonl` · `subjects.jsonl` · `pairs.jsonl`
- `analyze --pending|--hash` : Pod 떠 있을 때만(Lambda 주소가 자리표시자면 거절) · 직렬 ·
  S3 사본을 받아 해시 재확인 → `e2e_app_path.py` → `analysis_runs.jsonl`.
  시간 안에 안 끝나면 배치 중단(2026-09-22 동시 분석 사고)
- 사람 영상은 **manifest.json 에 넣지 않는다** — 플라이휠이 manifest 행을 증류 후보로
  자동 선택한다(`eligible_for_distill` 은 동의를 안 본다)

## Task 2 — `measure_reference_axis.py --pairs / --pair / --clips`

원장에서 doc 을 찾아 정타 vs 실수 관절별 편차(운영 점수 경로) + 정렬 창 + 저장된 점수·감점·억제.
기준 판 불일치 경고.

## Task 3 — 소급 + 검증

- phase15 fixture 12편 → `clips.jsonl`, 2026-09-22 분석 11건 → `analysis_runs.jsonl`
  (doc id = 지난 세션 대화 기록 복원, 영상 = S3 ETag 대조)
- 인수 기준: `--pair pr_kipup_je_001` 이 저장값(어깨 20.62도 · −0.7점 억제)을 재현
- 순수 함수 테스트, 드라이런, Pod 다운 거절 확인, S3 쓰기 권한 확인
- 37-DATA-SPEC §2-2 개정(clip 은 별 파일)

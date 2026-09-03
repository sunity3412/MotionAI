# 라이브 6동작 검증 — 감점 unit 수 == 확정 사진 수 (Pod sgl4muagt7xlb9 RTX 4090, 2026-09-03 밤)

1회차(7016e8c3): 클라임 1/1 · 엘보 트위스트 5/5(움직임 1장 사진 유지) · 파워스핀 2/2 · 킵업 1/1 · 피터팬 1/1 PASS,
**pdshape FAIL 4/5** — 게이트 verdict 는 5장 전부 생존인데 렌더 루프의 display_anchor 로그가 None 인덱싱(TypeError) → 부착 실패 → 1단계 4장 잔존.
수정 01ef4a9d(로그를 else 안으로) → 2회차 **pdshape PASS 5/5** (gated 5, unmarked 1 = 눈 실제 불일치 카드는 사진 유지·학생 표시 생략).
결과 원본: scratchpad verify_photo_per_pause_results.json (휘발) → 이 파일이 박제본. 서버 로그 `card_gates 대체 부착 완료 … expected_units=N emitted=N` 은 클라임·엘보에서 확인.

| 동작 | 감점 | expected | confirmed | gated | 비고 |
|---|---|---|---|---|---|
| pdshape (2회차) | 5 | 5 | 5 | 5 | unmarked 1 |
| 클라임 | 1 | 1 | 1 | 1 | |
| 파워스핀 | 2 | 2 | 2 | 0 | 비교 영상 정지 0 → 1단계 카드 |
| 엘보 트위스트 | 5 | 5 | 5 | 5 | moving 1 유지 |
| 킵업 | 1 | 1 | 1 | 0 | 정지 0 |
| 피터팬 | 1 | 1 | 1 | 1 | |

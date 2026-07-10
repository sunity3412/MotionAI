"""D-10b 교사 증류 트랙 (backend/training/distill).

좌표 보정 라벨은 합성 교란(22-01 perturb, 교사 무관)이 공급하고, 짚기·측정·코칭
라벨은 Gemini 교사 증류가 공급한다. 증류는 상한이 교사 품질(22-RESEARCH Pitfall 2)
이므로 judge(<7 폐기) + 물리 휴리스틱 + hard-negative eval 격리 + anonymized 고객
게이트(D-12)의 4중 방어와 함께 배치한다. File API 업로드는 즉시 삭제(finally)로
20GB 적체 누수(2026-06-22 이력)를 재발시키지 않는다.

network/boto3 는 lazy — 순수 필터 로직(judge 임계·반복 탐지·물리 궤적·행 선택)은
네트워크 0 으로 단위 테스트된다 (test_gemini_teacher.py).
"""

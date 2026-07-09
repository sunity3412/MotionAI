"""D-16 Wave 0 데이터 엔진 (backend/training/datagen).

이 패키지의 신규성은 학습 코드가 아니라 데이터 규격에 있다 (22-RESEARCH "Key
insight"). schema.py 가 학습 JSONL·bake-off·서빙 파서가 공유하는 유일한 규격
소스(D-11 4철칙 + D-01 통합 리포트 v1)이며, perturb.py 는 좌표 보정 학습 트랙의
자가 라벨(정답=원좌표) 생성기다. 두 모듈 모두 numpy 외 서드파티 의존 0,
boto3/네트워크 0 (analysis core 순수성 규율).
"""

"""RunPod GPU 분석 서버 (#7-follow 유닛 4).

backend/functions/pipeline/app.py 가 NLF 추출을 직접 시도하는 대신, 이 서버에
HTTP 위임하도록 설계. Pod 24/7 운영, NLF 모델 메모리 상주.
"""

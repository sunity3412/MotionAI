---
quick_id: 260923-weq
slug: s3-accelerate-download
date: 2026-09-23
mode: quick (inline — 실증을 막는 인프라 고장 예외)
---

# Quick 260923-weq — Pod 의 영상 다운로드가 멎는 문제를 S3 가속 엔드포인트로 우회

belle 충전 후 fixture 재분석을 돌리는데 첫 영상 다운로드(55MB)에 **30분**, 둘째 영상은 30분째 미완.
Pod 을 갈아치워도(4090 → L4) 같았다. 규칙(`[[pod-link-can-collapse-silently]]` "1MB/s 미만이면 교체")이
안 통하는 상황 — 호스트가 아니라 **경로**의 문제.

## Task 1 — 원인 가르기
- Pod 일반 egress(Cloudflare 30MB): 59MB/s → Pod 네트워크는 정상
- 서울 S3 직결 30MB: 4회 중 3회 5~7KB/s (멎음), 1회 4.4MB/s → **연결 단위로 멎는 EU-RO ↔ 서울 경로**
- S3 Transfer Acceleration 엔드포인트 30MB: 4/4 8.5~8.7MB/s

## Task 2 — 수리
- 버킷 가속 설정 ON (`put-bucket-accelerate-configuration`)
- `app.py`: 다운로드 전용 `_s3_dl`(`S3_USE_ACCELERATE=1`) + `_s3_download()` 7곳. 업로드·서명 URL 은
  종전 `_s3` — 앱이 받는 재생 URL 이 가속 호스트로 바뀌지 않게(가속 전송 GB 당 과금)
- `_s3` 는 호출 시점에 본다(테스트 49건이 가짜 `_s3` 를 끼운다 — 처음 판은 이걸 깨서 49 failed)
- `start_server.sh`: `S3_USE_ACCELERATE=1`

## Task 3 — 검증
- 테스트 3건 · 게이트 5010/0 · Pod 재기동 후 fixture 9편 배치의 s3_download 단계 시간

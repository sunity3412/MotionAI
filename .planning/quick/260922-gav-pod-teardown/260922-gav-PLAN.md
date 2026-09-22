---
quick_id: 260922-gav
slug: pod-teardown
date: 2026-09-22
status: in-progress
must_haves:
  truths:
    - "pod_teardown.py 가 RunPod GraphQL 을 403 없이 호출한다"
    - "인자 없는 실행이 Sunity-Motion 소유가 아닌 Pod 을 종료하지 않는다"
  artifacts:
    - backend/scripts/pod_teardown.py
  key_links:
    - backend/scripts/pod_teardown.py
---

# Quick 260922-gav — pod_teardown.py 안전 수리 2건

## 왜 지금

2026-09-22 세션에서 `pod_teardown.py` 를 실행하니 **HTTP 403** 으로 죽었다.
이 스크립트는 아침에 belle 에게 *"Pod 을 못 끄게 되면 이걸 누르세요"* 로 안내한
안전장치다. 즉 **안전장치가 작동하지 않는 상태로 안내돼 있었다.**

읽다가 두 번째 것을 발견했다 — 인자 없이 실행하면 `myself{pods}` **전체**를
종료한다. 오늘 계정에는 다른 프로젝트(Sunityfunding) 학습 Pod
`sunity-pipe-translator-q9b` 가 돌고 있었다. belle 이 안내대로 눌렀으면
**남의 학습이 죽었다.**

## 결함 ① — Cloudflare 1010 (실측)

```
urllib 기본 UA (Python-urllib/3.14)   → HTTP 403, body = "error code: 1010"
UA = curl/8.7.1                       → 200 OK
UA = sunity-motion-pod-teardown/1.0   → 200 OK
```

RunPod GraphQL 앞단 Cloudflare 가 `Python-urllib` UA 를 차단한다. curl 로 같은
쿼리가 통과하므로 키·권한 문제가 아니다. **아무 UA 라도 붙이면 통과한다.**

## 결함 ② — 무인자 실행이 계정 전체를 종료

`main()` 은 인자가 없으면 `targets = [모든 pod id]` 로 잡는다. 소유 판별이 없다.

## 하는 것

1. `_gql` 에 `User-Agent` 헤더 추가.
2. 무인자 실행 대상을 **이름이 `sunity-motion` 으로 시작하는 Pod** 으로 한정.
   그 외는 종료하지 않고 목록으로 출력해 사람이 명시적으로 지목하게 한다
   (fail-safe — 놓치는 쪽이 남의 것을 죽이는 쪽보다 낫다).
3. 실제 GraphQL 호출로 ① 검증, 무인자 필터를 드라이런으로 ② 검증.

## 안 하는 것

- 다른 프로젝트 Pod 을 종료하거나 건드리지 않는다.
- `--urls-only` 경로는 손대지 않는다(GraphQL 미사용).

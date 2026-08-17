---
phase: quick-260818-c0u
quick_id: 260818-c0u
slug: pod-podwatch
date: 2026-08-18
status: complete
---

# quick-260818-c0u 요약 — Pod 헬스 감시

## 한 일

`backend/infra/podwatch.yaml` + `backend/infra/README.md` 신설, **별도 CloudFormation 스택
`sunity-motion-podwatch` 로 실제 배포까지 완료.**

```
EventBridge rate(5 minutes) → Lambda sunity-motion-podwatch-probe
  → pipeline Lambda env RUNPOD_ANALYZE_URL 을 읽어 /health GET
  → CloudWatch Sunity/Motion {PodHealth, ConfigDrift}
  → 알람 sunity-motion-pod-down / sunity-motion-pod-url-drift → SNS sunity-motion-pod-alerts
```

## 실측 (배포 후 프로브 1회 강제 실행)

```
{"healthy": 1, "drift": 0,
 "env_url": "https://y1nw2dqpulh0op-8000.proxy.runpod.net/analyze",
 "ssm_url": "https://y1nw2dqpulh0op-8000.proxy.runpod.net/analyze",
 "detail": "{\"status\":\"ok\",...,\"pipeline_loaded\":true,...}"}
Duration 1473ms / Max Memory 101MB
```

## 설계 판단 3가지

1. **pilot 스택에 얹지 않았다.** `backend/template.yaml` 의 `RunpodAnalyzeUrl` 기본값이 빈
   문자열이고 `samconfig.toml` overrides 에 그 값이 없어서, 지금 `sam deploy` 를 하면 운영
   pipeline Lambda 의 `RUNPOD_ANALYZE_URL` 이 빈 문자열로 덮인다. 감시 붙이려다 운영을
   깨뜨리는 구조라 분리했다.
2. **감시 대상 URL 의 출처 = SSM 이 아니라 Lambda env.** 운영이 실제로 호출하는 값이 그것이다.
   SSM 은 대조용으로만 읽어 어긋나면 `ConfigDrift` 로 따로 운다 — Pod 교체 때 두 곳 중 한 곳만
   갱신하는 것이 반복 함정이었다.
3. **200 만으로 healthy 로 치지 않는다.** `status==ok` 그리고 `pipeline_loaded==true` 여야 1.
   모델이 안 올라온 채 프로세스만 살아 있는 상태를 "정상"으로 읽지 않기 위해서다.
   `TreatMissingData: breaching` 이라 프로브 자체가 죽어도 운다.

## ★남은 한 걸음 (belle 이 해야 함)

SNS 이메일 구독이 `PendingConfirmation` 이다. **belle6466@gmail.com 으로 온 AWS Notifications
메일의 `Confirm subscription` 을 눌러야** 알람이 실제로 메일로 나간다. 누르기 전까지는
알람은 울리지만 아무도 모른다 — 지금 상태와 같다.

배포 직후 `sunity-motion-pod-down` 은 ALARM 상태로 시작한다(데이터포인트 2개가 쌓이기
전이라 `breaching` 규칙이 적용됨). 정상이라면 약 10분 뒤 OK 로 내려간다.

## 범위 밖

- Pod 자동 재기동 (알림까지만)
- `_delegate_to_runpod` 폴백 부재 — 감시와 별개 문제로 남아 있다

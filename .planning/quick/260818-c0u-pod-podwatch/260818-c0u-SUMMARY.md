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

## 전 구간 실증 완료 (2026-08-18)

수신자는 `sunity3412@gmail.com`(RunPod/Firebase 운영 계정). 처음에 belle6466(git 이메일)로
잘못 넣었다가 belle 지적으로 교체 — **AWS 계정 이메일과 알림 수신 메일함은 다른 물건**이고,
확인해야 할 것은 "belle 이 실제로 읽는 메일함"이다.

```
구독 확인   belle 클릭 → SubscriptionArn 발급됨(PendingConfirmation 해소)
배선 시험   set-alarm-state ALARM → belle 수신 확인 ("메일 왔음")
```

★구독이 확인된 것만으로는 배선 증명이 아니다. **알람→SNS→받은편지함까지 실제로 울려서
belle 이 받은 것을 확인**했다. 시험 후 프로브 주기에 자동으로 OK 로 복귀(OK 알림도 켜져 있음).

배포 직후 `sunity-motion-pod-down` 이 ALARM 으로 시작하는 것은 정상이다 — 데이터포인트 2개가
쌓이기 전이라 `breaching` 규칙이 적용된다. 약 10분 뒤 OK 로 내려간다.

## 범위 밖

- Pod 자동 재기동 (알림까지만)
- `_delegate_to_runpod` 폴백 부재 — 감시와 별개 문제로 남아 있다

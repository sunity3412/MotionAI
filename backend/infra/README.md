# backend/infra — pilot 스택 **밖**의 인프라

여기 있는 템플릿은 SAM 스택 `sunity-motion-pilot` 과 **별개**로 배포된다.

## 왜 분리했나

`backend/template.yaml`(pilot) 은 파라미터 `RunpodAnalyzeUrl` 의 기본값이 빈 문자열이고,
`backend/samconfig.toml` 의 `parameter_overrides` 에 그 값이 없다. 즉 **지금 상태에서
`sam deploy` 를 하면 운영 pipeline Lambda 의 `RUNPOD_ANALYZE_URL` 이 빈 문자열로 덮인다**
— 앱 분석이 전량 실패한다(위임 실패 시 폴백 없음). 감시 하나 붙이자고 운영을 깨뜨릴
이유가 없어서 별도 스택으로 뺐다.

---

## podwatch.yaml — RunPod Pod 헬스 감시

스택 이름 `sunity-motion-podwatch` · 리전 `ap-northeast-2`.

```
EventBridge(5분) → Lambda 프로브 → CloudWatch 메트릭 → 알람 → SNS 이메일
```

프로브는 **pipeline Lambda 의 env `RUNPOD_ANALYZE_URL`** 을 읽어 그 URL 의 `/health` 를
친다. SSM 이 아니라 Lambda env 를 보는 이유는 그게 **운영이 실제로 호출하는 값**이기
때문이다. SSM 값은 대조용으로만 읽어서 어긋나면 `ConfigDrift` 알람이 따로 운다.

| 메트릭 | 1 = | 알람 |
|---|---|---|
| `Sunity/Motion PodHealth` | `/health` 가 200 이고 `status==ok` 이고 `pipeline_loaded==true` | `sunity-motion-pod-down` — 5분×2회 연속 실패 |
| `Sunity/Motion ConfigDrift` | SSM 값 ≠ Lambda env 값 | `sunity-motion-pod-url-drift` |

`PodHealth` 알람은 `TreatMissingData: breaching` 이다 — **프로브 자체가 죽어도 운다.**
복구되면 같은 SNS 로 OK 알림이 간다.

### 배포

```bash
aws cloudformation deploy \
  --stack-name sunity-motion-podwatch \
  --template-file backend/infra/podwatch.yaml \
  --parameter-overrides AlertEmail=belle6466@gmail.com \
  --capabilities CAPABILITY_IAM \
  --region ap-northeast-2 --profile sunity-motion
```

★첫 배포 후 **이메일 구독 확인이 필요하다.** AWS Notifications 가 보낸 메일의
`Confirm subscription` 을 누르기 전까지 알람은 울려도 메일이 안 간다. 확인 상태:

```bash
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:ap-northeast-2:<acct>:sunity-motion-pod-alerts \
  --region ap-northeast-2 --profile sunity-motion \
  --query 'Subscriptions[].[Endpoint,SubscriptionArn]' --output text
```
`PendingConfirmation` 이 아니라 arn 이 찍혀야 확인된 것이다.

### 지금 상태 즉시 보기

```bash
aws lambda invoke --function-name sunity-motion-podwatch-probe \
  --region ap-northeast-2 --profile sunity-motion /dev/stdout
```

### Pod 을 교체했을 때

프로브는 **Lambda env 를 따라가므로 감시 쪽은 따로 손댈 게 없다.** 기존 절차 그대로
SSM + Lambda env 두 곳만 갱신하면 되고, 한쪽을 빠뜨리면 `ConfigDrift` 알람이 잡아준다.

### 알람 배선 시험 (실제로 메일이 오는지)

```bash
aws cloudwatch set-alarm-state --alarm-name sunity-motion-pod-down \
  --state-value ALARM --state-reason "wiring test" \
  --region ap-northeast-2 --profile sunity-motion
```
다음 프로브 주기에 실제 상태로 되돌아온다.

# RunPod GPU 분석 서버

`#7-follow 유닛 4 (운영 GPU 인프라)`. Lambda 가 NLF GPU 추론을 직접 못 돌리는 문제(CPU NaN)를 풀기 위한 위임 서버. **Pod 24/7 운영**, NLF 모델 메모리 상주.

## 전체 흐름

```
앱(S3 PUT) → S3:ObjectCreated 이벤트 → SQS → Lambda(pipeline)
                                                       │
                                              (위임 분기 — 환경변수 RUNPOD_*)
                                                       │
                                                       ▼
                                  POST /analyze {bucket, key}  (X-RunPod-Token 헤더)
                                                       │
                                                  RunPod Pod
                                                       │
                                  ┌───────────────────────────────────┐
                                  │ S3 다운로드 → NLF 추출 → reference 비교 │
                                  │ → Firestore Admin: complete_analysis │
                                  └───────────────────────────────────┘
                                                       │
                                       앱이 onSnapshot 으로 결과 화면 자동 표시
```

## 한 번에 띄우기 (belle 절차)

```bash
# 1) RunPod Pod 시작 — PyTorch 베이스 이미지, RTX 3090/4090 24GB, SSH·HTTP 포트 노출
#    노출할 포트: 8000 (HTTP)
#    환경변수는 Pod 콘솔의 "Environment Variables" 에 박는 게 가장 안전 (자격증명).

# 2) Pod 안에서 (web terminal 또는 SSH):
cd /workspace
git clone https://github.com/sunity3412/MotionAI.git SunityMotion   # 최초 1회
cd SunityMotion && git pull
cd backend
bash runpod_inference/setup.sh        # 의존성 + NLF 모델 다운로드

# 3) Firebase 서비스 계정 JSON 을 Pod 에 올림 (둘 중 하나):
#    a) Pod 환경변수 FIREBASE_SA_JSON 에 JSON 원문 직접 박기 (가장 단순)
#    b) JSON 파일을 /workspace/firebase-sa.json 에 두고 FIREBASE_SA_PATH 로 지정

# 4) 환경변수 세팅 후 서버 기동:
export RUNPOD_AUTH_TOKEN="$(openssl rand -hex 32)"   # 한 번 생성 — Lambda 와 공유
export AWS_ACCESS_KEY_ID="..."                       # S3 read 권한 (sunity-api)
export AWS_SECRET_ACCESS_KEY="..."
export AWS_DEFAULT_REGION=ap-northeast-2
export FIREBASE_SA_PATH=/workspace/firebase-sa.json  # (또는 FIREBASE_SA_JSON)
export CUDA_VISIBLE_DEVICES=0                        # 어제 메모: 빈 문자열로 와서 덮어야

uvicorn runpod_inference.server:app --host 0.0.0.0 --port 8000 --workers 1

# 5) Pod 의 공개 URL 확인 (RunPod 콘솔 → Pod → "Connect" → "HTTP Service")
#    예: https://<pod-id>-8000.proxy.runpod.net
#    이 URL 을 Lambda 환경변수 RUNPOD_ANALYZE_URL 에 박기.
```

## 헬스체크 + 수동 테스트

```bash
# health: 인증 불필요
curl https://<pod-id>-8000.proxy.runpod.net/health
# {"status":"ok","auth_configured":true,"pipeline_loaded":true}

# analyze 수동 호출 (Lambda 없이 테스트):
curl -X POST https://<pod-id>-8000.proxy.runpod.net/analyze \
  -H "Content-Type: application/json" \
  -H "X-RunPod-Token: $RUNPOD_AUTH_TOKEN" \
  -d '{"bucket":"sunity-motion-pilot-videos","key":"uploads/<uid>/<analysisId>.mp4"}'
# 202 {"status":"accepted","uid":"<uid>","analysisId":"<analysisId>"}
# → Pod 로그를 살펴 진행. Firestore users/<uid>/analyses/<analysisId> 가 done 으로 갱신되면 성공.
```

## Lambda 측 변경 (belle 검토 후 다음 단계)

Lambda 가 NLF 를 직접 호출하는 대신 RunPod 에 위임하도록 변경. 환경변수가 있으면 위임, 없으면 기존 흐름 — **점진 전환 가능**(롤백 안전).

```python
# backend/functions/pipeline/app.py 의 _process 위에 추가:
import urllib.request, json

_RUNPOD_URL = os.environ.get("RUNPOD_ANALYZE_URL")
_RUNPOD_TOKEN = os.environ.get("RUNPOD_AUTH_TOKEN")

def _delegate_to_runpod(bucket: str, key: str) -> None:
    req = urllib.request.Request(
        _RUNPOD_URL,
        method="POST",
        data=json.dumps({"bucket": bucket, "key": key}).encode(),
        headers={
            "Content-Type": "application/json",
            "X-RunPod-Token": _RUNPOD_TOKEN,
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        if resp.status not in (200, 202):
            raise RuntimeError(f"runpod {resp.status} {resp.read()}")

# lambda_handler 안에서 _process 호출 전 분기:
#   if _RUNPOD_URL and _RUNPOD_TOKEN:
#       _delegate_to_runpod(bucket, key)
#       continue
#   _process(bucket, key, uid, analysis_id)  # 기존 흐름
```

SAM template 에 환경변수 슬롯 추가:
```yaml
PipelineFunction:
  Properties:
    Environment:
      Variables:
        RUNPOD_ANALYZE_URL: !Ref RunpodAnalyzeUrl    # Parameter
        RUNPOD_AUTH_TOKEN: !Ref RunpodAuthToken     # NoEcho
```

## 환경변수 레퍼런스

| 변수 | 필수 | 설명 |
|------|------|------|
| `RUNPOD_AUTH_TOKEN` | ✅ | Lambda 와 공유하는 shared secret. 미설정 시 모든 요청 503. |
| `AWS_ACCESS_KEY_ID` | ✅ | S3 read 권한 (sunity-api 사용자) |
| `AWS_SECRET_ACCESS_KEY` | ✅ | 위와 쌍 |
| `AWS_DEFAULT_REGION` | ✅ | `ap-northeast-2` |
| `FIREBASE_SA_JSON` | 둘 중 하나 | 서비스 계정 JSON 원문 |
| `FIREBASE_SA_PATH` | 둘 중 하나 | 파일 경로 (`/workspace/firebase-sa.json`) |
| `CUDA_VISIBLE_DEVICES` | ✅ | `0` 으로 덮음 (`runpod-gpu-env` 메모 참조) |
| `NLF_MODEL_PATH` | ⚪ | 기본 `backend/scripts/nlf_l_multi.torchscript` (setup.sh 가 받음) |

## 운영 메모

- **Pod stop 금지**: NLF 모델 디스크 + venv 가 사라짐. 비용 줄이려면 Pod terminate 후 재셋업하거나, persistent volume 사용 (runpod-gpu-env 메모).
- **모니터링**: `/health` 를 외부 모니터에 5분 간격 등록. Pod 가 죽으면 RunPod 알림.
- **로그**: stdout (uvicorn) → Pod 콘솔에서 확인. 영구 보존 필요하면 CloudWatch agent 등 별도 설정.
- **DLQ**: Lambda 가 RunPod 호출 실패 시 SQS DLQ 로 자동 이동(maxReceiveCount=3) → belle 가 수동 재시도 가능.

## 검증 시나리오

1. `/health` 200 + `auth_configured=true` + `pipeline_loaded=true`
2. 앱에서 영상 1개 업로드 → Pod 로그에 `/analyze accepted` → 1~2분 후 `분석 완료`
3. Firestore users/{uid}/analyses/{analysisId} 가 status=`done` + 정밀 점수/각도 채워짐
4. 앱 결과 화면이 자동 갱신 — 실측 (시뮬이 아닌)

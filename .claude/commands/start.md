---
name: start
description: 하루 시작 — 분석 Pod 기동 + belle 에게 앱 설치 안내. belle 2026-08-31 지시
allowed-tools:
  - Read
  - Bash
---

# 하루 시작 — Pod 켜고 앱 설치 안내

belle 2026-08-31 지시: **"내일 그냥 시작하면 포드 켜주고 APK 설치 방법 주는 쪽으로 하자."**

두 가지만 한다. 다른 작업은 belle 이 시킬 때. 착수점(`.planning/CONTINUE-*.md`)은
읽되, 여기서는 **읽고 요약만** 하고 그 안의 작업 목록에 손대지 않는다.

---

## 1. 분석 Pod 기동

절차 정본 = memory `demo-only-pod-bring-up-procedure`. 요지만 여기 둔다.
**Pod 이 없으면 앱 분석은 그냥 실패한다(폴백 없음).**

### 1-1. 이미 떠 있는지부터 본다 (중복 생성 = 돈)

```bash
KEY=$(aws ssm get-parameter --name /sunity/motion/runpod-api-key --with-decryption \
  --profile sunity-motion --region ap-northeast-2 --query Parameter.Value --output text)
curl -s -X POST https://api.runpod.io/graphql -H "Content-Type: application/json" \
  -H "Authorization: Bearer $KEY" \
  -d '{"query":"query { myself { pods { id name desiredStatus costPerHr } } }"}'
```

떠 있으면 1-2를 건너뛰고 1-4로 간다.

### 1-2. 생성 — **Ada 세대만** (L4 / 4090 / L40S)

서빙은 RTMW-x + YOLOX ONNX 뿐이라 **VRAM 1.3GB**면 충분하다(실측). 학습용 48GB+ 급을
잡지 말 것 — `/Users/Shared/sunity-podhunt/podhunt.sh` 는 **학습용**이라 그대로 쓰면 안 된다.

★Blackwell(RTX PRO 5000/6000, 5090) 금지 — onnxruntime-gpu 1.22 가 CUDA 12 빌드라
CUDA EP 가 안 뜬다. 판정은 "CUDA EP 뜨냐 / GPU 사용률"이지 카드 이름이 아니다
(memory `pod-env-in-bashrc-does-not-survive-new-container`).

```bash
for GPU in "NVIDIA L4" "NVIDIA GeForce RTX 4090" "NVIDIA L40S"; do
  R=$(curl -s -X POST https://api.runpod.io/graphql -H "Content-Type: application/json" \
    -H "Authorization: Bearer $KEY" \
    -d "{\"query\":\"mutation { podFindAndDeployOnDemand(input: { cloudType: SECURE, gpuCount: 1, gpuTypeId: \\\"$GPU\\\", name: \\\"sunity-motion-serve\\\", imageName: \\\"runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04\\\", networkVolumeId: \\\"a5z753defc\\\", volumeMountPath: \\\"/workspace\\\", containerDiskInGb: 50, ports: \\\"22/tcp,8000/http\\\", startSsh: true }) { id costPerHr } }\"}")
  echo "$R" | grep -q '"id"' && { echo "$GPU -> $R"; break; }
done
```

네트워크 볼륨 `a5z753defc` 필수 (모델 가중치가 거기 있다).

### 1-3. 부트스트랩 (새 컨테이너마다 매번)

**정본 = `backend/runpod_inference/bootstrap_full.sh`** (2026-08-31 실증).
★`.claude/scripts/setup_pod_full.sh` 도 있는데 그건 Phase 5 때의 **구본**이다 —
mmcv CUDA 빌드까지 하느라 15~45분 걸린다. 서빙은 ONNX 뿐이라 필요 없다. 헷갈리지 말 것.

★두 가지가 매번 사람을 물리는 지점이다:

- `pip uninstall -y onnxruntime` 후 `pip install onnxruntime-gpu==1.22`
  (rtmlib 이 CPU 판을 딸려 온다)
- **`source /workspace/aws_env.sh` 를 먼저** 하고 `bash /workspace/start_server.sh`.
  안 하면 SSM/Lambda 키 주입이 NoCredentialsError 로 **조용히** 실패하고
  `GEMINI_API_KEY len: 0` 이 된다.

미푸시 커밋이 있으면 bootstrap 의 `git pull` 로는 못 들어간다 — git bundle 로 반입:
`git bundle create delta.bundle origin/main..main` → scp → Pod 에서
`git fetch <bundle> main:local-main && git checkout local-main`.
Pod 리포가 dirty 면 **stash 먼저, 지우지 말 것.**

### 1-4. health 확인 — 이 4개가 다 나와야 기동 완료

```bash
curl -s https://{podId}-8000.proxy.runpod.net/health
```

`pipeline_loaded:true` · `poseEngine:RTMWPoseEngine` ·
`recognizer:GeminiTechniqueRecognizer` · CUDA EP.

### 1-5. Lambda + SSM 동기화 (★`sam deploy` 금지 — 라이브 스택이 낙후돼 있다)

```bash
aws lambda update-function-configuration \
  --function-name sunity-motion-pilot-pipeline \
  --profile sunity-motion --region ap-northeast-2 \
  --environment "Variables={...,RUNPOD_ANALYZE_URL=https://{podId}-8000.proxy.runpod.net/analyze}"
```
기존 변수를 먼저 읽어서 **통째로 다시 넣어야 한다**(이 API 는 병합이 아니라 치환).
그리고 SSM `/sunity/motion/runpod-analyze-url` 갱신 + `/sunity/motion/pod-expected=up`.

### 1-6. belle 에게 보고

판정 먼저: **"분석 준비됐습니다"** + Pod GPU·시간당 비용 한 줄.
수치는 쥐고만 있는다 (belle 보고 형식 — 판정 먼저, 수치는 물을 때).

★**쓰고 나면 반드시 terminate + `pod-expected=down`.** 켜둔 채 세션이 끝나면 돈이 샌다.

---

## 2. 앱 설치 안내

belle 은 iPhone·Android 둘 다 갖고 있다. **1.2.1 은 두 플랫폼 내용이 같다.**

착수점 `.planning/CONTINUE-*.md` 의 "상태" 블록에서 **그날의 최신 APK 링크와 빌드
번호를 확인해 쓸 것.** 아래 링크는 2026-08-31 자라 낡았을 수 있다.

### Android (APK 직접 설치)

1. 안드로이드 폰 브라우저로 링크 열기
   → https://expo.dev/artifacts/eas/AGeYizsfERcjZOTkdHtXTFyClaHYqKIv4OATbfbcGuI.apk
2. 다운로드된 파일 탭 → "출처를 알 수 없는 앱" 허용 요청이 뜨면 허용
3. 설치 → 실행

### iPhone (TestFlight)

1. App Store 에서 **TestFlight** 설치 (이미 있으면 생략)
2. TestFlight 열기 → `Sunity AI Coach` → **업데이트**
3. 버전이 **1.2.1** 인지 확인 (앱 안에서는 마이 탭 → 앱 버전)

### 같이 말해줄 것 (안 하면 belle 이 헛돈다)

- **튜토리얼은 첫 실행 1회만 뜬다** (`@sunity:tutorial_seen`). 이미 쓰던 기기에서는
  안 나온다. 보려면 앱이 처음인 기기로 볼 것 — 지우고 재설치하면 게스트 기록이 사라진다.
- **애플 로그인은 iPhone 전용.** 마이 탭 → 계정 카드 → 로그인.
- **로그인을 두 번 하면 두 번째는 화면이 안 넘어간다.** 이미 가입된 계정이라
  안내만 뜨고 멈추는데, 로그인 자체는 성공이라 뒤로가기를 누르면 반영돼 있다.
  (고장 아님 — 36-CONTEXT D-07 #6 승인 동작. belle 판정 대기 중)

---

## 하지 말 것

- 착수점의 다른 작업을 임의로 시작하지 말 것. 이 명령은 **Pod + 설치 안내 2건**이다.
- Pod 을 "미리" 켜두지 말 것 — belle 이 분석을 요청할 때만 (2026-08-28 결정).
- 안 물어본 수치·표를 들이밀지 말 것.

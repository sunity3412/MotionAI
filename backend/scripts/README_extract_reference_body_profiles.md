# extract_reference_body_profiles.py — Pod GPU 측정 (Plan 06-03 Task 2)

본 스크립트는 정은지 reference 5개 영상의 **두 필드**
(`bodyNormalizationProfile` + `bodyComparisonSourcePose`, R2 fix 2026-06-08
round-2) 를 측정한다. **Pod GPU 전용** (RTMW + measure_body_profile + 대표 hold
frame 추출). 산출 JSON 은 로컬에서 seed 스크립트로 Firestore atomic merge.

## 실행 단계

### 1) Pod SSH

```bash
ssh xbdkj1g2ylnfwi-64411701@ssh.runpod.io -i ~/.ssh/id_ed25519
```

### 2) git pull ([[gsd-pod-work-push-first]] 정합)

```bash
cd /workspace/SunityMotion
git pull origin main
```

### 3) 환경 변수

```bash
export AWS_DEFAULT_REGION=ap-northeast-2
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export RTMW_ONNX_PATH=/workspace/rtmw_weights/rtmw-x-384.onnx
export YOLOX_ONNX_PATH=/workspace/yolox_weights/yolox_m.onnx
export RTMW_DEVICE=cuda
export FIREBASE_SA_PATH=/workspace/firebase-sa.json
```

### 4) **(C5 권장)** dry-run 우선

```bash
python backend/scripts/extract_reference_body_profiles.py \
    --bucket sunity-motion-pilot-videos \
    --output /workspace/reference-body-data.json \
    --dry-run
```

**기대 출력 (dry-run)**: stdout JSON.

검증 항목:

- 5 motion ID 모두 측정됨
- 각 motion 의 `bodyNormalizationProfile.confidence >= 0.5`
- 각 motion 의 `bodyComparisonSourcePose` 존재 (null 아님)
- `bodyComparisonSourcePose.jointKeys` 길이 == 17 (COCO-17)
- `bodyComparisonSourcePose.values` 길이 == 68 (= 4 × 17)
- `bodyComparisonSourcePose.torsoPx > 0` + finite
- `bodyComparisonSourcePose.confidence >= 0.5`

파일 미생성 (`/workspace/reference-body-data.json` 부재).

### 5) real-run (dry-run 통과 후)

```bash
python backend/scripts/extract_reference_body_profiles.py \
    --bucket sunity-motion-pilot-videos \
    --output /workspace/reference-body-data.json
```

**기대**: `/workspace/reference-body-data.json` 생성. dry-run stdout 과 동일 내용.

### 6) 로컬 다운로드

```bash
scp xbdkj1g2ylnfwi-64411701@ssh.runpod.io:/workspace/reference-body-data.json .
```

### 7) seed 스크립트 진입

```bash
# 로컬에서
gcloud auth application-default login   # sunity3412@gmail.com (real-run 만 필요)
cd app
npm run seed:body-profile -- --profiles ../reference-body-data.json --dry-run
# (검증 후)
npm run seed:body-profile -- --profiles ../reference-body-data.json
```

## W3 박제 — `-m` 미사용

본 스크립트는 **직접 실행만** 지원. 모듈 invocation (`-m` 플래그 + dotted module
path) 형태는 **금지**. sys.path 주입은 in-script 에서 수행 (parents[1] / shared
/ python 삽입).

## 실패 처리

- 일부 motion 의 `bodyComparisonSourcePose` 가 null 로 산출되어도 (대표 frame
  확보 실패), 다른 motion 의 결과는 박제됨. seed 스크립트가 `null` 인 필드는
  Firestore 에 안 박제 (partial backfill — R2 fix graceful 정합).
- 모든 motion FAIL 시 stdout/stderr 에 traceback 표시. logs 확인 후 RTMW 가중치
  / Pod GPU 상태 점검.

## 관련 메모리

- [[runpod-gpu-env]] — Pod 환경 + 함정 박제
- [[gsd-pod-work-push-first]] — 로컬 commit → push → Pod pull 순서
- [[firestore-nested-array-flat]] — values 가 flat 인 이유

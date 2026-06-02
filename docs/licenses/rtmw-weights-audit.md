# RTMW 운영 가중치 라이선스 audit (D-25)

> **Audit 작성일:** 2026-06-02
> **Plan:** 01-20 (`.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-20-PLAN.md`)
> **목적:** belle 명시 (개발지시 §5) "rtmlib/RTMPose 코드는 Apache-2.0 이지만, 모델 가중치의 학습 데이터 상업 사용 가능 여부는 모델별로 반드시 확인". 본 문서는 plan 21 (RTMWPoseEngine 통합) 진입 전 가중치 라이선스 게이트.
> **결정 상태:** belle 검토 대기 (Plan 01-20 Task 2 checkpoint). 본 문서 §4 가 belle 응답 박제 자리.
> **출처 fetch 일자:** 2026-06-02 (rtmlib README, mmpose projects/rtmpose README, COCO Wholebody 공식)

---

## 1. Audit 범위

[D-17/D-18/D-25] 정의된 RTMW 운영 후보 가중치 4개를 audit 한다. plan 21 의 `RTMWPoseEngine` 가 실제로 로드할 수 있는 가중치만 본 문서에 등재한다.

| ID | 가중치명 | 입력 해상도 | 출력 | AP (Wholebody) | 비고 |
|---|---|---|---|---|---|
| (a) | RTMW-l 256x192 | 256x192 | 133 keypoints 2D | 66.0 | rtmlib `mode='lightweight'` 기본 매핑 |
| (b) | RTMW-l 384x288 | 384x288 | 133 keypoints 2D | 70.1 | rtmlib `mode='balanced'` 기본 매핑 |
| (c) | RTMW-x 384x288 | 384x288 | 133 keypoints 2D | 70.2 | rtmlib `mode='performance'` 기본 매핑 |
| (d) | RTMW3D-x 384x288 | 384x288 | 133 keypoints 3D | 68.0 (3D) | **plan 명시 RTMW3D-l 부재** (아래 §1-1 deviation) |

### 1-1. Plan 명시 RTMW3D-l vs 실 rtmlib 카탈로그 차이 (deviation 박제)

Plan 01-20 §1 은 "(d) RTMW3D-l 단일 카메라용" 으로 명시하나, rtmlib README (Wholebody 3D 섹션) 와 mmpose project zoo 에는 **RTMW3D-x (huggingface Soykaf 호스팅)** 만 등재되어 있다 (2026-06-02 fetch 기준). RTMW3D-l 버전은 공식 배포 채널에서 확인되지 않는다.

본 audit 은 사실 정합을 우선해 (d) 를 **RTMW3D-x 384x288** 로 박제한다. RTMW3D-l 가 향후 mmpose 또는 rtmlib release 에 추가되면 별도 manifest entry 추가 (별 Plan).

### 1-2. 공식 가중치 URL (rtmlib README + mmpose projects/rtmpose README 기준)

| ID | onnx (rtmlib 권장) | pth (mmpose checkpoint) |
|---|---|---|
| (a) | https://download.openmmlab.com/mmpose/v1/projects/rtmw/onnx_sdk/rtmw-dw-x-l_simcc-cocktail14_270e-256x192_20231122.zip | https://download.openmmlab.com/mmpose/v1/projects/rtmw/rtmw-dw-x-l_simcc-cocktail14_270e-256x192-20231122.pth |
| (b) | https://download.openmmlab.com/mmpose/v1/projects/rtmw/onnx_sdk/rtmw-dw-x-l_simcc-cocktail14_270e-384x288_20231122.zip | https://download.openmmlab.com/mmpose/v1/projects/rtmw/rtmw-dw-x-l_simcc-cocktail14_270e-384x288-20231122.pth |
| (c) | https://download.openmmlab.com/mmpose/v1/projects/rtmw/onnx_sdk/rtmw-x_simcc-cocktail13_pt-ucoco_270e-384x288-0949e3a9_20230925.zip | https://download.openmmlab.com/mmpose/v1/projects/rtmw/rtmw-x_simcc-cocktail14_pt-ucoco_270e-384x288-f840f204_20231122.pth |
| (d) | https://huggingface.co/Soykaf/RTMW3D-x/resolve/main/onnx/rtmw3d-x_8xb64_cocktail14-384x288-b0a0eab7_20240626.onnx | (mmpose 공식 pth 미공개, 2026-06-02 시점) |

호스팅: (a)(b)(c) = OpenMMLab 공식 CDN (`download.openmmlab.com`, Apache-2.0 프로젝트). (d) = Hugging Face 커뮤니티 미러 (Soykaf 계정). (d) 의 호스팅 신뢰성은 mmpose 공식 채널 아닌 점 박제 — belle 검토 시 OpenMMLab 공식 RTMW3D 배포 채널 추가 확인 필요.

(c) 의 onnx 파일명에 `cocktail13` 이 들어가지만 mmpose project README 표는 `cocktail14_pt-ucoco` (UBody+COCO pretrained 후 cocktail14 학습) 로 분류한다. 본 audit 은 mmpose README 의 분류 (cocktail14) 를 신뢰. rtmlib onnx 파일명의 `cocktail13` 은 초기 alpha 배포 (2023-09) 의 잔존 명명일 가능성 — belle 확인 필요시 §3 참조.

---

## 2. 후보별 학습 데이터셋

### 2-1. Cocktail14 구성 (mmpose RTMW 공식 정의)

mmpose `projects/rtmpose/README.md` (main branch, 2026-06-02 fetch) 의 "Cocktail14" 정의:

> `Cocktail14` denotes model trained on 14 public datasets:
> AI Challenger, CrowdPose, MPII, sub-JHMDB, Halpe, PoseTrack18, COCO-Wholebody, UBody, Human-Art, WFLW, 300W, COFW, LaPa, InterHand

### 2-2. Cocktail14 dataset 별 라이선스 + 상업 사용 여부

| # | 데이터셋 | 라이선스 / 사용 조건 | 상업 사용 | 출처 URL |
|---|---|---|---|---|
| 1 | **AI Challenger (AIC)** | "for research only" (대회 약관) — 상업 X 명시 | **no** | https://github.com/AIChallenger/AI_Challenger_2017 |
| 2 | **CrowdPose** | 데이터는 MS COCO 기반 (재사용). 코드 부분 라이선스만 명시 (Apache-2.0). 데이터셋 자체 commercial 명시 없음 | **unknown** | https://github.com/Jeff-sjtu/CrowdPose |
| 3 | **MPII Human Pose** | "the data can be used for non-commercial research purposes" (공식 약관) | **no** | http://human-pose.mpi-inf.mpg.de/ |
| 4 | **sub-JHMDB** | HMDB-51 derivative. HMDB-51 = CC BY 4.0 (Serre Lab) | **yes** (CC BY) | http://jhmdb.is.tue.mpg.de/ (HMDB: https://serre-lab.clps.brown.edu/resource/hmdb-a-large-human-motion-database/) |
| 5 | **Halpe Full-Body** | AlphaPose 프로젝트 산출 — AlphaPose LICENSE = Noncommercial Research Only | **no** | https://github.com/Fang-Haoshu/Halpe-FullBody |
| 6 | **PoseTrack18** | "Researchers may use the dataset for non-commercial purposes" | **no** | https://posetrack.net/ |
| 7 | **COCO-Wholebody** | COCO annotations = CC BY 4.0 (annotations); 이미지는 Flickr Terms — 데이터셋 사용 자체는 학술 무료, 그러나 commercial 시 Flickr 이미지 권리 별 확인. 어노테이션 자체는 commercial OK 가능 | **unknown (조건부 yes)** | https://github.com/jin-s13/COCO-WholeBody / https://cocodataset.org/#termsofuse |
| 8 | **UBody** | OSX project. 학술 비상업 명시 (IDEA-Research) | **no** | https://github.com/IDEA-Research/OSX |
| 9 | **Human-Art** | 학술 비상업 명시 (MMLab) | **no** | https://idea-research.github.io/HumanArt/ |
| 10 | **WFLW** | "academic research only" (TencentY Lab) | **no** | https://wywu.github.io/projects/LAB/WFLW.html |
| 11 | **300W** | "for research purposes only" (Imperial College) | **no** | https://ibug.doc.ic.ac.uk/resources/300-W/ |
| 12 | **COFW** | Caltech Vision — 라이선스 명시 없음 (default = research only 추정) | **unknown (no 추정)** | http://www.vision.caltech.edu/xpburgos/ICCV13/ |
| 13 | **LaPa** | JD AI Research, GitHub README "non-commercial research" 명시 | **no** | https://github.com/JDAI-CV/lapa-dataset |
| 14 | **InterHand2.6M** | "Researchers can use this dataset for academic, non-commercial use only" (FAIR / SNU) | **no** | https://mks0601.github.io/InterHand2.6M/ |

**합산 판정 (Cocktail14):** 14개 중 **최소 10개 가 비상업 명시**, 2개 unknown, 2개 commercial OK 후보 (sub-JHMDB / COCO-Wholebody annotations). 즉 cocktail14 가중치 자체는 **상업 사용 불가** 로 판단해야 함. 라이선스 "weakest link" 원칙 — 학습 데이터 중 1개라도 비상업이면 파생 가중치도 비상업.

### 2-3. 후보별 학습 데이터셋 매핑

| ID | 가중치 | 학습 데이터 | dataset license 판정 | 가중치 license_status |
|---|---|---|---|---|
| (a) | RTMW-l 256x192 (`rtmw-dw-x-l_simcc-cocktail14`) | Cocktail14 (14개 dataset) | weakest link = non-commercial (AIC/MPII/Halpe/UBody 등) | **restricted** |
| (b) | RTMW-l 384x288 (`rtmw-dw-x-l_simcc-cocktail14`) | Cocktail14 | 동일 | **restricted** |
| (c) | RTMW-x 384x288 (`rtmw-x_simcc-cocktail14_pt-ucoco`) | UBody+COCO pretrain → Cocktail14 fine-tune | 동일 (Cocktail14 포함) | **restricted** |
| (d) | RTMW3D-x 384x288 (`rtmw3d-x_8xb64_cocktail14`) | Cocktail14 + 3D component (UBody/InterHand2.6M 3D 어노테이션) | 동일 + 3D 데이터셋 (UBody/InterHand2.6M 모두 비상업) | **restricted** |

---

## 3. 의사결정 매트릭스

본 audit 은 **dataset license weakest-link 원칙**을 적용한다. 학습 데이터 중 1개라도 비상업 라이선스면 파생 가중치는 비상업으로 분류 — 데이터셋 라이선스 침해의 향후 소송 리스크는 belle 의 SaaS 파일럿을 차단할 수 있다.

### 3-1. 가중치별 판정

| ID | 가중치 | 코드 라이선스 (rtmlib/mmpose) | 학습 데이터 weakest license | `license_status` | `production_eligible` (초기값) | 근거 |
|---|---|---|---|---|---|---|
| (a) | RTMW-l 256x192 | Apache-2.0 | non-commercial (AIC 등) | **restricted** | false | Cocktail14 의 비상업 dataset 포함. 가중치 자체 사용 시 데이터셋 약관 위반 위험. |
| (b) | RTMW-l 384x288 | Apache-2.0 | non-commercial | **restricted** | false | (a) 동일 |
| (c) | RTMW-x 384x288 | Apache-2.0 | non-commercial | **restricted** | false | (a) 동일. UBody+COCO pretrained 단계도 UBody 비상업 영향 받음. |
| (d) | RTMW3D-x 384x288 | Apache-2.0 (rtmlib 코드) / hugging face 호스팅 (Soykaf 계정) | non-commercial | **restricted** | false | (a) 동일 + 호스팅 채널 비공식 (belle 확인 필요) |

### 3-2. belle action items (Task 2 checkpoint 에서 결정 필요)

1. **dataset 약관 위반 리스크 수용 여부**: 모델 가중치는 "학습 데이터의 derivative work" 인지 (실 판례 회색지대) 또는 "독립 파라미터" 인지. belle 가 법적 판단 또는 자문 후 결정.
   - 보수적 판단 (audit default) = restricted
   - belle 가 위험 수용 = `commercial_ok` 로 승급 (단 §4 박제 + 면책 근거 명시)
2. **상업 commercial_ok 가중치 후보 발굴**:
   - 옵션 1: COCO-Wholebody only 로 학습된 RTMW 변형 존재 시 commercial_ok 가능 (현재 rtmlib/mmpose 공식 zoo 에 없음)
   - 옵션 2: mmpose 공식 채널 (OpenMMLab Slack/Discord 또는 GitHub Issue) 에 commercial-friendly RTMW weight 문의
   - 옵션 3: 자체 fine-tune (COCO-Wholebody only 또는 CC-BY dataset 조합) — Phase 후속 plan
3. **(d) RTMW3D-x 호스팅 채널 추가 확인**: huggingface Soykaf 계정이 공식 mmpose 미러인지 검증. 아니라면 mmpose 공식 RTMW3D pth/onnx URL 확인 필요.
4. **Plan 21 진입 차단 여부**: 현 audit 기준 4개 모두 restricted → manifest 의 production_eligible 0 개. plan 21 의 `RTMWPoseEngine __init__` 가 manifest 기반 가드 적용 시 인스턴스화 실패. belle 결정 = (a) 위험 수용 후 1개 승급 / (b) 추가 후보 발굴 / (c) plan 21 보류.

### 3-3. 본 audit 의 자동 적용 가드

`weights_manifest.json` 의 모든 entry 초기 `production_eligible=false`. plan 21 의 RTMWPoseEngine 는 `production_eligible=true` 인 entry 만 로드. belle 승급 commit 없으면 plan 21 진입 시 가중치 0 개로 RTMWPoseEngine 인스턴스화 차단. **이 문서 §4 갱신 + manifest 동시 갱신이 belle 결정 박제 의무**.

---

## 4. belle 결정

_(belle 검토 대기 — Task 2 checkpoint 후 박제)_

이 섹션은 belle 응답 적재 시점에 다음 형식으로 갱신:

```
### 4-1. belle 응답 (YYYY-MM-DD)

- Production 가중치: <name> (sha256 검증 후 manifest production_eligible=true)
- Fallback 가중치: <name> 또는 "single backbone 충분"
- license_status 변경 근거: <belle 의 dataset 약관 위험 평가 / OpenMMLab 공식 답변 인용 / 자체 fine-tune 결정>
- 미해결 unknown 가중치 처리: <belle 추가 확인 진행 / 후보 제외>
```

belle 응답 옵션 (Plan 01-20 Task 2 §how-to-verify 5-6 항목):

- **approved**: `production=<name>, fallback=<name>` — manifest 갱신 + plan 21 진입
- **blocked**: `<reason>` — plan 21 진입 차단, 추가 audit/협의 plan 작성

---

## 5. 차단 목록 cross-reference

본 audit 은 [[license-blocklist-pose]] (memory 박제) 와 정합 검증한다:

| 차단 목록 모델 | 본 audit 후보 등장 여부 | 확인 결과 |
|---|---|---|
| AlphaPose | 후보 0건 | manifest weight name 에 `alphapose` 부분문자열 0개 (test_no_blocklisted_weights 자동 검증). **단 학습 데이터에는 등장 — Halpe dataset 이 AlphaPose 프로젝트 산출물** (이는 가중치 라이선스 게이트 별개 — §2-2 #5 참조) |
| NLF (Neural Localizer Fields) | 후보 0건 | manifest weight name 에 `nlf` 부분문자열 0개 |
| SMPL-X | 후보 0건 | manifest weight name 에 `smplx` 부분문자열 0개 |
| VideoPose3D | 후보 0건 | manifest weight name 에 `videopose3d` 부분문자열 0개 |

**차단 목록 위반 0건.** memory `license-blocklist-pose.md` 의 "RTMPose/HRNet OK" 화이트리스트 항목과 정합 — RTMW 는 RTMPose 의 wholebody 확장이라 코드 라이선스 (Apache-2.0) 차원 화이트리스트 충족. 학습 데이터 라이선스는 본 §2/§3 가 별도 게이트.

자동 검증: `backend/tests/test_rtmw_weights_manifest.py::test_no_blocklisted_weights`.

---

## 6. Plan 21 가중치 선택 게이트

### 6-1. manifest 만 입력

Plan 21 (RTMW 통합) 의 `RTMWPoseEngine.__init__` 는 `backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/weights_manifest.json` 의 `production_eligible=true` entry 만 로드한다. 다른 가중치 직접 지정 금지 (코드 path 자체에서 manifest lookup 강제).

이는 [D-25] 위반 차단의 hard gate — audit 통과 없는 가중치는 코드 path 에서 자동 거부.

### 6-2. 진입 조건 (Task 2 belle 응답 후)

1. belle 가 §4 에 production 가중치 1개 (+ optional fallback 1개) 박제
2. 해당 entry 의 `production_eligible=true` 로 manifest 갱신 (별도 commit, audit §4 갱신과 함께)
3. `test_production_eligible_implies_commercial_ok` 통과 — 즉 license_status='commercial_ok' 이어야 함. 'restricted' 또는 'unknown' entry 를 production 으로 승급할 수 없음 (테스트 자동 차단)
4. 가중치 다운로드 + sha256 박제 (plan 21 task)
5. plan 21 의 통합 작업 진입

### 6-3. 차단 시나리오

- 4개 모두 license_status='restricted' 유지: belle 가 추가 후보 발굴 또는 자체 fine-tune 결정 전 plan 21 진입 불가
- belle 가 license_status='unknown' entry 를 production 승급 시도: `test_production_eligible_implies_commercial_ok` 실패 → 먼저 라이선스 확인 후 commercial_ok 로 승급해야 통과
- mmpose 공식 채널 문의 결과 cocktail14 가중치도 상업 OK 회답 받으면: 그 회답 출처 (Github issue URL 등) 를 §4 에 박제 + license_status='commercial_ok' 갱신 가능

---

*본 audit 은 Plan 01-20 Task 1 산출. Plan 01-20 Task 2 belle checkpoint 통과까지 production_eligible 0 개 유지 — plan 21 진입 차단 상태.*

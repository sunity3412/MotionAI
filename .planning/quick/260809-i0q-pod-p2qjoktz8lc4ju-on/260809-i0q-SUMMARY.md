---
id: 260809-i0q
title: Pod p2qjoktz8lc4ju 기동 + 실업로드 경로 결정론 ON
date: 2026-08-09
status: complete
commits:
  - 30533327 chore(runpod): 기동 정본 start_server.sh 리포 버전화 + 결정론 env 박제
---

# 260809-i0q 요약

belle 이 Pod p2qjoktz8lc4ju (RTX 4090, 기존 Network Volume) 생성 → 08-08 마감의
운영 이전 잔여 1건(서버 경유 실업로드 경로 결정론 OFF)을 닫고 앱 업로드 대기 상태로 만듦.

## 착수 시 정정 — 메모리 노트가 함정 파일을 가리키고 있었다

08-08 노트: "`start_p15_server.sh` 에 `RTMW_DETERMINISTIC=1` 반영".
두 스크립트를 직접 열어 대조한 결과:

| 파일 | 크기/날짜 | PR_INVERSION_ENABLED | 코치·프리페치·모델 로테이션 |
|---|---|---|---|
| `start_server.sh` | 3118B / 07-22 | **1 (ON)** | 전부 있음 |
| `start_p15_server.sh` | 1033B / 06-21 | **없음(OFF)** | 없음 |

`current-pod-pqe6uaw7mf8bh9` 메모리가 이미 "정본 = start_server.sh, p15 판 = 인버전
OFF 함정 금지" 로 경고해둔 그 파일이었다. 노트대로 p15 에 결정론만 넣었으면
**결정론은 켜고 인버전은 끈 채** belle 이 업로드할 뻔했다.

→ 결정론 env 는 **정본 start_server.sh** 에 넣고, p15 는 정본 위임으로 무장해제.

## 한 일

1. **Pod 부트스트랩** — 새 컨테이너라 pip 패키지 없음(`bootstrap_full.sh`).
   weights 는 볼륨에 존속(rtmw-x-384 352M / yolox_m 97M). 리포 pull → `73042a27`(=main HEAD).
2. **결정론 env 박제** — `/workspace/start_server.sh` 14번 줄(인버전) 바로 아래에
   `export RTMW_DETERMINISTIC=1` + 근거 주석. 원본은 `.bak-20260809` 보존.
3. **p15 함정 무장해제** — `start_p15_server.sh` 내용을 지우고 `exec bash
   /workspace/start_server.sh` 로 위임 (어느 쪽을 실행해도 인버전·결정론 ON).
4. **서버 기동** — `source aws_env.sh && bash start_server.sh` (PID 4332).
   토큰은 Lambda env 에서 자동 동기(len 64), Gemini 키는 SSM 에서 주입(len 53).
5. **SSM/Lambda 동기화** — 둘 다 죽은 Pod(kgmldqyqjnyx5c)를 가리키고 있었음.
   SSM `/sunity/motion/runpod-analyze-url` v27→**v28**, Lambda
   `sunity-motion-pilot-pipeline` env `RUNPOD_ANALYZE_URL` 갱신(4키 보존 재조회 확인).
6. **리포 버전화** — `backend/runpod_inference/start_server.sh` (Pod 사본과 **md5 동일**
   `e7f224d648ef599270d14a6887bc7ae1`) + README 기동 절차에 정본 포인터·플래그 누락 경고.

## 기계 판정 (직접 호출·재조회로 확인)

`GET https://p2qjoktz8lc4ju-8000.proxy.runpod.net/health` →

```json
{"status":"ok","auth_configured":true,"pipeline_loaded":true,
 "commitSha":"73042a27b25e658de8b8621dca02da76c581e4b6",
 "envFlags":{"PR_INVERSION_ENABLED":true,"RTMW_DETERMINISTIC":true},
 "modelInitCanary":{"pipelineLoaded":true,"adaptersReady":true,
   "poseEngine":"RTMWPoseEngine","recognizer":"GeminiTechniqueRecognizer","modelLoaded":true}}
```

| 항목 | 기대 | 실측 |
|---|---|---|
| commitSha == main HEAD | 73042a27 | 73042a27 ✅ |
| RTMW_DETERMINISTIC | true | true ✅ |
| PR_INVERSION_ENABLED | true | true ✅ |
| modelLoaded / recognizer | true / Gemini | true / GeminiTechniqueRecognizer ✅ |
| `/analyze` 잘못된 토큰 | 401 | 401 ✅ |
| `/analyze` 무토큰 | 401 | 401 ✅ |
| Lambda RUNPOD_ANALYZE_URL | 새 proxy | `https://p2qjoktz8lc4ju-8000.proxy.runpod.net/analyze` ✅ |
| repo↔pod 스크립트 동일 | md5 일치 | e7f224d6… 일치 ✅ |

## 아직 검증 안 된 것 (박제)

> ⚠ 아래 2건은 이 문서 하단 "실경로 E2E 2회" 절에서 **해소됨** (2회 완주 실측).
> 세 번째(처리량)만 여전히 미측정. 잔여 비결정 ②(mp3 길이)는 **실측으로 확인됨**.

- ~~실업로드 E2E 미실행~~ → **2회 완주**(done + 렌더 부착 + S3 실물).
- ~~결정론 효과 재측정 안 함~~ → **채점 완전 재현 / 렌더 비재현**(정지 +0.03s, mp4 md5 상이).
- **belle 실기기 업로드는 여전히 미실행** — 이번 2회는 시뮬 uid 아래 S3 copy 트리거이고,
  앱→upload-url Lambda→presigned PUT 구간은 이번에 안 탔다(S3 이후 경로는 동일).
- **처리량 영향 미측정** — 결정론은 conv algo 벤치마크를 끄므로 세션 초기화는 빨라지고
  추론 처리량은 소폭 낮아질 수 있다(문서 명시). 분석 1건 282~340초 기준 체감 여부 미확인.

## LLM 학습 영향

없음. env 게이트·기동 스크립트·인프라 배선만 건드렸고 채점 산식·프롬프트·모델 선택은
무접촉. 다만 결정론 ON 은 앞으로 쌓일 판정 로그의 **재현성을 올려** 기계 단독 집계의
신뢰도를 높이는 방향(사람 검증 건수와는 무관).

---

## 실경로 E2E 2회 (belle 지시로 추가 — "제가 먼저 1건 돌린다" → 재현성 확인 위해 2회차)

시뮬 실업로드(sim uid 아래, S3 copy → ObjectCreated → SQS → Lambda → Pod). 원본 영상은
08-08 시뮬 업로드와 **동일 파일**(엘보, ref-elbow-twist-sister).

| | run1 `7915221e` | run2 `a65ce745` |
|---|---|---|
| 분석 | done 191s | done 180s |
| 점수 | **64** (angle 64 · stability 75) | **64** (angle 64 · stability 75) |
| 감점 합 | −35.9 | −35.9 |
| 감점 5건(편차) | 9.21 / 7.68 / 6.31 / 4.69 / 1.96 | **전건 동일** |
| 렌더 | done, 정지 5 | done, 정지 5 |
| 정지 위치 | 1.13 · 13.1 · **32.37** · **45.8** · **57.17** | 1.13 · 13.1 · **32.4** · **45.83** · **57.2** |
| mp4 | 12,541,407 B md5 `3304d0a4…` | 12,550,438 B md5 `f1c50204…` |

### 판정

- **채점 = 완전 재현** (소수점까지). 따라서 07-30·08-08 의 72 → 08-09 의 64 는
  비결정성이 아니라 **코드 변경(08-08 측정창 수술 ②)의 결과**임이 분리 확정.
- **렌더 = 재현 아님.** 3번째 정지부터 **+0.03s(30fps 1프레임)** 누적 이동, mp4 9,031 B 차이.
  원인은 이미 박제된 잔여 비결정 ②(freeze 길이 = 코칭 음성 mp3 길이 + tail, Polly 합성
  길이가 실행마다 변동) — 이번에 **운영 경로에서 실측**됨. ORT 결정론(①)은 렌더 정렬
  세션에 실제 적용됨을 Pod 로그로 확인(`RTMW deterministic mode ON — cudnn_conv_algo_search:
  DEFAULT … CUBLAS_WORKSPACE_CONFIG=:4096:8`).
- 산출물 눈검증: run1 mp4 다운로드 → 32.37s 정지 프레임 = 양패널 같은 역립 국면,
  오른팔꿈치 마커, 자막 "오른쪽 팔꿈치 각도가 엘보 트위스트 기준 자세와 차이가 있어요…".

### 점수 이력 (같은 영상, Firestore 실조회)

| 생성 | doc | 점수 | 감점 합 |
|---|---|---|---|
| 07-30 10:14 | elbowtwi | 72 | −27.7 |
| 08-08 15:47 | 2fe3ae94 | 72 | −27.9 |
| 08-09 13:12 | 7915221e | **64** | −35.9 |
| 08-09 13:32 | a65ce745 | **64** | −35.9 |

10일간 72 고정 → 측정창 수술로 1회 이동 → 이후 동일. **점수가 수시로 흔들린 것이 아니라
한 번 움직였고, 그 이동을 사전에 belle 께 예고하지 않은 것이 결함**(belle 08-09 지적).

### 드러난 게이트 구멍 (다음 라운드 후보)

08-08 게이트는 **산식 5파일 diff 0**(deduction_engine/dimensions/kismam/compare_render/
cue_text)을 봤는데, 측정창을 바꾼 `motiondtw` 는 그 목록에 없다 — **산식은 지켰지만 점수
결과는 아무도 안 지켰다.** 제안 = 고정 영상 N편의 점수 기준선을 박제하고, 변경이 그
숫자를 움직이면 배포 전 "이 변경은 엘보 72→64" 를 보고·승인받는 게이트. (belle 결정 대기)

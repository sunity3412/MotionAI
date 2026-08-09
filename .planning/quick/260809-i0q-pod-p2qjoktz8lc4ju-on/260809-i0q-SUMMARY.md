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

- **실업로드 E2E 미실행** — belle 이 앱에서 올려야 도는 경로. 이번 세션이 확인한 것은
  "도달 가능·env 켜짐"까지이지 "분석 1건 성공"이 아니다.
- **결정론의 효과(재현성) 이 Pod 에서 재측정 안 함** — env 는 켜졌으나, 같은 영상 2회
  렌더로 리그 판정이 재현되는지는 08-08 Pod(kgmldqyqjnyx5c) 실측이 마지막이다.
  ORT CUDA EP 는 완전 bitwise 결정론을 보장하지 않고(`ort_determinism` docstring),
  freeze 길이 = Polly mp3 길이 변동이라는 **잔여 비결정 2종은 그대로 남아 있다**.
- **처리량 영향 미측정** — 결정론은 conv algo 벤치마크를 끄므로 세션 초기화는 빨라지고
  추론 처리량은 소폭 낮아질 수 있다(문서 명시). 분석 1건 282~340초 기준 체감 여부 미확인.

## LLM 학습 영향

없음. env 게이트·기동 스크립트·인프라 배선만 건드렸고 채점 산식·프롬프트·모델 선택은
무접촉. 다만 결정론 ON 은 앞으로 쌓일 판정 로그의 **재현성을 올려** 기계 단독 집계의
신뢰도를 높이는 방향(사람 검증 건수와는 무관).

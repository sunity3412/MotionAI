# 32-03 Task 1 — Pod 배포 + fixture 6동작 전수 스윕 실측 (D-16/D-20/D-23)

**실행일:** 2026-07-21 (KST 16:20~18:30) · **실행:** phase25 harness (`backend/evals/phase25/run_sweep.py`, SERIAL in-process `_process`) · **Pod:** `6seluxc43awmqi` (RTX 4090 24GB, driver 570.172.08, EU — Network Volume `/workspace` 재사용)

## 1. Pod 재가동 + 재동기화 (구 Pod `xps7co0m2njzpi` 사망 → belle 신규 생성)

| 단계 | 결과 |
|---|---|
| SSH 직접 TCP (`root@213.173.98.93:14767`) | 접속 OK · GPU = **RTX 4090 24GB** (Blackwell 아님 — sm_120 JIT 함정 비해당) |
| Network Volume | `/workspace` 연결 확인 (SunityMotion repo·rtmw/yolox weights·firebase-sa.json·aws_env.sh·start_server.sh 전부 보존) |
| bootstrap | `bootstrap_wave5.sh` (~1분, git pull→`36fdde9`) + 서빙 패키지 수동 설치(fastapi/uvicorn/pydantic/**google-genai**/cerebras-cloud-sdk) |
| start_server.sh | VETO env 박제 확인 (`GEMINI_VISION_VETO_ENABLED=1`, `GEMINI_MAX_VETO_WALL_S=300`, phase27 env 4종, `LD_LIBRARY_PATH` cudnn 포함). 토큰 len 64 (Lambda fetch), Gemini key len 53 (SSM) |
| `/health` | **200** `{"status":"ok","auth_configured":true,"pipeline_loaded":true}` (배포 전·후 각 1회) |
| X-RunPod-Token 스모크 | 무인증 POST `/analyze` → **401** · 올바른 토큰 + key-only body → **422** (기대값 정확) |
| SSM `/sunity/motion/runpod-analyze-url` | `https://6seluxc43awmqi-8000.proxy.runpod.net/analyze` **v16** (boto3 literal put — CLI `--value https://` 405 함정 회피) |
| Lambda `RUNPOD_ANALYZE_URL` | 동일 URL로 in-process patch (get→patch→update, 4키 보존: FIREBASE_SA_PARAM/RUNPOD_AUTH_TOKEN/VIDEO_BUCKET 유지). `LastUpdateStatus=Successful` 확인. 구값 = `https://xps7co0m2njzpi-...` (사망 Pod) |
| wave-1 push→pull | 로컬 main 24커밋 push (`36fdde9..c45eb95`) → Pod `git pull --ff-only` → `c45eb95` → `__pycache__` 청소 + 서버 재기동 (PID 14740) → `/health` 200 재확인 |

## 2. 스윕 설계 (D-23 — 전수·순차·kip-up 편중 금지)

- **기준선 = 배포 전 스윕 1회** (Pod가 pre-wave-1 `36fdde9` 상태에서 cold run) — "가장 최근 스윕 기록"(phase25/29 baseline)은 phase 26~31 코드 변화가 섞여 wave-1 효과 격리 불가라 채택하지 않음.
- 6동작 페어(power-spin·peter-pan·elbow-twist-sister·pdshape·kip-up·climb) × {fault, correct} = 12멤버 + pdshape cold-rerun 1 = **13멤버 SERIAL** ([[pipeline-not-concurrency-safe-eval-serial]]).
- 기준선 run: runId `1784618645` (07:24~08:34 UTC) / 배포 후 run: runId `1784623086` (08:38~09:52 UTC). `RTMW_DETERMINISTIC=1`.
- **기질(substrate) 노트:** 두 스윕 모두 sweep 셸에 `LD_LIBRARY_PATH` 미설정으로 RTMW가 CPU EP로 실행됨(양쪽 동일 → A/B 유효). **프로덕션 서버 프로세스는 start_server.sh가 LD_LIBRARY_PATH를 주입해 GPU 정상** (PID 14740 environ 실측).

## 3. 점수·verdict diff — **전 멤버 0** (32-01 "채점 무접촉" 실측 증명)

| motion | fault (기준선→배포후) | correct (기준선→배포후) | errorCode | dimensionScores |
|---|---|---|---|---|
| power-spin | 55 → **55** | 100 → **100** | None→None | diff 0 |
| peter-pan | 79 → **79** | 100 → **100** | None→None | diff 0 |
| elbow-twist-sister | 66 → **66** | 100 → **100** | None→None | diff 0 |
| pdshape | 58 → **58** | 100 → **100** | None→None | diff 0 |
| kip-up | 80 → **80** | 100 → **100** | None→None | diff 0 |
| climb | gate → gate (`NotPoleMotionError: angle 10 < 25`, status=comparison) | gate → gate (동일) | 동일 | — |

- activatedCriteria 목록도 전 멤버 동일 (예: power-spin fault = `angle_vs_reference__left_shoulder`/`leg_extension`/`split_angle` 양쪽 일치).
- cold-rerun 결정론: pdshape correct 100/100, criteria identical (기준선·배포후 각각 selection_identical=true).
- 짚기-FP 관측: success 5멤버 pointed any 0 / upper 0 (양 run 동일).

## 4. motionAlignment 방출 — D-16 실측 (저신뢰 trim_only + anchors 보존)

**배포 후 변화는 정확히 이것뿐** — 저신뢰 8멤버가 `disabled` → `trim_only`(reason=`low_global_confidence`) 로 전환, anchors 전부 보존:

| member | tier 기준선→배포후 | reason(배포후) | anchorsLen (보존) |
|---|---|---|---|
| power-spin/fault | disabled → **trim_only** | low_global_confidence | 40 |
| power-spin/correct | disabled → **trim_only** | low_global_confidence | 50 |
| peter-pan/fault | disabled → **trim_only** | low_global_confidence | 30 |
| peter-pan/correct | trim_only → trim_only (불변) | rate_clamp_exceeded | 40 |
| elbow-twist-sister/fault | disabled → **trim_only** | low_global_confidence | 82 |
| elbow-twist-sister/correct | disabled → **trim_only** | low_global_confidence | 100 |
| pdshape/fault | disabled → **trim_only** | low_global_confidence | 84 |
| pdshape/correct | disabled → **trim_only** | low_global_confidence | 72 |
| kip-up/fault | disabled → **trim_only** | low_global_confidence | 32 |
| kip-up/correct | warped → warped (불변) | — | 38 |

- anchors head 실측 예: power-spin/fault `[0.0, 0.0, 0.444, 0.222]` — 유한·타임라인 내 (sanity 가드 통과).
- 비-저신뢰 tier(warped 1건, rate_clamp trim_only 1건)는 **불변** — 사다리 재배치가 저신뢰 분기에만 국소 적용됨을 증명.
- **acceptance "저신뢰 ≥ 1건 trim_only + anchors 보존" → 8건으로 충족.**

## 5. 확대비교 크롭 parity — D-20 실측 (로그 수치 + 육안)

**로그 수치 (wave-1 신규 `fault_zoom_crop` 구조 로그, 배포 후 run 18줄 전수):**

- user/ref side 비 = **18/18 전부 0.8~1.25 이내** (17줄 ratio 1.00, 1줄 1.07).
- **relaxed 재현 6줄** (ref_kind=relaxed): peter-pan fault right_hand · ETS fault legs · pdshape fault legs+right_knee · pdshape correct arms · pdshape cold-rerun arms — **전부 ratio 1.00** (relaxed 프레이밍이 valid와 동일 배율로 통일됨).
- analysis_id=None 은 32-01 known follow-up(파이프라인 배선 대기) — SERIAL 실행이라 타임스탬프로 멤버 귀속 (32-01-SUMMARY 명시 사항).

**육안 (기준선 vs 배포후 PNG, S3 결과물 직접 대조):**

| 케이스 | 기준선 | 배포후 | 판정 |
|---|---|---|---|
| ETS fault `zoom_left_knee.png` (ref=relaxed) | ref측 전신 광각(배경 다수, 인물 축소) — 212,797B | ref측 크롭 타이트닝, 좌(내 영상)와 배율 체감 일치 — 203,640B | **parity 달성 (교정 실측)** |
| power-spin fault `zoom_left_shoulder.png` (valid/valid) | 167,809B | **바이트 동일** 167,809B | valid 경로 무변경 증명 (결정론 부수 증거) |
| peter-pan fault `zoom_adv_right_hand.png` (ref=relaxed) | 138,454B | **바이트 동일** | 손 bbox 소형 → 최소변 floor가 구/신 크롭을 동일하게 지배 (양쪽 151px, parity 자체는 항상 성립) |

- PNG 원본 위치(S3, 인물 이미지라 repo 미커밋): `results/phase25eval/{analysisId}/zoom_*.png`, 기준선 analysisId 접미 `1784618645` / 배포후 `1784623086`.

## 6. 프로덕션 체인 E2E (재동기화 종단 검증)

`fixtures/phase15/power-spin/correct.mp4` → `uploads/pode2e32/powerspinE2e1784627613.mp4` COPY → S3 notification → SQS → Lambda(신 URL) → Pod `/analyze` → Firestore:

```json
{"status": "done", "overallScore": 100, "errorCode": null,
 "motionAlignmentTier": "trim_only", "motionAlignmentReason": "low_global_confidence",
 "faultZoomCount": 1}
```

- 스윕 동일 입력의 서버 경로(GPU) 점수도 100 — 채점 일관. wave-1 D-16 방출이 프로덕션 경로에서 라이브. uploads 오브젝트 정리 완료.

## 7. 산출물 위치

- Pod: `/workspace/eval32/{base,post}/phase25/phase25_sweep_report.json` + `base_sweep.log`/`post_sweep.log` + `{base,post}_docs.json` + `post_crop_lines.log`
- 로컬 사본: `/tmp/eval32/` (보고서·docs·crop 로그·PNG 4쌍) — 세션 임시, 영구 증거는 Pod 볼륨 + S3 PNG + 본 문서 수치.

**게이트 판정: D-23 웨이브 게이트 PASS** — 6동작 전수(순차) · 점수 diff 0 · trim_only 방출(8건, anchors 보존) · crop parity(로그 18/18 + 육안).

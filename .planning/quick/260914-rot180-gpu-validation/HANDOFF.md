---
title: 인수인계서 — 2026-09-14 세션
date: 2026-09-14
next_section: belle 판정 2건 (회전 운영 투입 · 감점 상한) + Gemini C 신호 살리기
status: rot180 GPU 실증 완료(플래그는 여전히 off) · 재학습 착수 금지 판정 · C2 전수 측정 완료
---

# 인수인계서 — 2026-09-14

09-13 인계서 §6 의 A·B·C 를 순서대로 처리했다. **관측과 진단을 구분해 적었다.**

---

## 0. 30초 요약

- **A(회전 GPU 실증) — 됐다.** 붕괴 6→**0**, 뼈위반 p90 −49%, 못 본 관절 1→**0**.
  로컬 CPU 예측치와 1.3% 이내 일치. **점수는 60→60 으로 안 움직였는데, 이유는
  회전이 무력해서가 아니라 감점 상한(40) 이 이미 포화**라서다(원감점 −40.3→−58.8).
- **B(재학습) — 착수 금지.** 데이터는 갖춰졌지만 **승격이 구조적으로 불가능**하다.
  게이트가 설계상 SKIPPED 때문에 항상 exit 3 이다. 데이터를 더 모아도 안 풀린다.
- **C2(Gemini 3필드) — belle 가설 확정.** 표본을 4→**1242**로 올려 쟀다.
  `camera_angle_problematic` / `occlusion_severe` 는 **4개월간 True 0건**.
- **C1(Omni) — 이미 답이 나와 있었다.** 09-13 인계서의 "미검증 추정"은 **09-05 에
  해소된 건**이다. 아래 §4.
- **플래그는 리포에서 여전히 `0`.** 오늘 앱 산출은 어제와 동일하다.

---

## 1. 지금 상태 (2026-09-14 실측)

```
브랜치   main   HEAD e3936dfb   (origin/main 보다 59 커밋 앞 — 미푸시)
게이트   pytest 4827 passed / 20 skipped / 0 failed   (backend/.venv 로 직접 실행)
플래그   ROT180_INVERSION_ENABLED=0   (start_server.sh:24, 리포 무변경)
Pod      0대 · SSM pod-expected=down · 잔액 $6.50 (오늘 $0.41 사용)
Lambda   무접촉 (RUNPOD_ANALYZE_URL 은 죽은 Pod 그대로 — 아래 §5 함정 2)
```

---

## 2. A — 회전 GPU 실증 (근거 전문 = `evidence/MEASUREMENTS.md`)

Pod `jhm4vvmv0z1yon` (RTX PRO 4500 Blackwell, EU-RO-1, 볼륨 `a5z753defc`),
커밋 `e3936dfb` 번들 반입, ORT-gpu 1.19.2 CUDA EP, `/health` 전 항목 통과.
같은 영상(belle pdshape, mode1/ref-pdshape, 182프레임)을 **3회** 돌렸다.

**잡음 바닥 = 0** — off 두 런의 `joints3d` 가 **byte 동일**(max abs diff 0.0),
점수·차원·unjudged 전부 동일. 그래서 런3 의 차이는 전부 플래그 탓이다.

| 지표 | off (=PR 워프, 현행 운영) | on (rot180) | 로컬 CPU 예측 |
|---|---|---|---|
| 붕괴 프레임 | 6 | **0** | 0 ✅ |
| 뼈위반 p90 평균 | 1.502 | **0.763** (−49%) | 0.753 ✅ |
| 못 본 관절 | 1 (`right_elbow`) | **0** | — |
| **overallScore** | **60** | **60** | — |
| angle / stability | 45 / 72 | 38 / 91 | — |
| 원감점 합 | −40.3 | **−58.8** | — |
| 상한 적용 후 | −40.0 | −40.0 | (`executionCap=40.0`) |

8개 뼈 **전부** 개선, 악화 0개. 계기도 재현 — 불일치 p50 0.109 / p90 1.608
(모듈 docstring 예측 0.110 / 1.618), **채택 182/182, fail-safe 기각 0건**.
`pr_warp_skipped=true` 로 우선순위 주장도 실경로 확인. 회전이 PR 워프보다
**더 싸다**(2패스 8.5s vs 10.9s).

### ★ 점수가 안 움직인 이유

`right_elbow` 가 회복되며 **최대 감점 −16.2** 로 처음 등장했고,
`left_shoulder` 는 "측정오차 내"로 억제됐다가 좌표가 좋아지자 **−12.0 으로 억제 해제**됐다.
그런데 off 가 이미 −40.3 으로 상한 40 을 막 넘긴 상태라 **상한이 전부 흡수**했다.

> **belle 09-13 기준과의 방향**: 회전은 "못 본 관절 감점을 지워 점수를 올리는" 설계의
> **반대**다. 관절을 보이게 만들어 감점을 **추가**한다. 방향은 belle 기준과 맞는다.
>
> **별개로 드러난 것**: 원감점 −40.3 짜리와 −58.8 짜리가 **둘 다 60점**이다.
> 상한 포화 구간에서 점수가 결함량을 구분하지 못한다. 회전과 무관한 사안이고
> **오늘 감점 코드는 한 줄도 안 건드렸다.**

## 3. B — 재학습: 착수 금지 (근거는 직접 확인)

데이터는 갖춰졌다(수집 manifest 427행, 분석원장 384행). **그런데 승격이 안 된다.**

```
assert_gates.py:474-478   --require-pass 는 SKIPPED 하나라도 남으면 return 3
run_sft_gates.sh:151-163  스크립트 종료코드 = require-pass 결과
promotion.py              exit 0 만 pass=True
```

SKIPPED 는 **설계상 반드시 남는다** — `pairs.yaml:99` kip-up `known_false_positive`,
`:115` climb `known_gate_blocked`, `assert_gates.py:293-297` 이 `expected != discriminate`
면 무조건 SKIPPED 방출. perturb 트랙도 0행이라 좌표보정 게이트도 SKIPPED.

**즉 4동작을 전부 맞혀도 exit 3.** Gemini 라벨링 + A100 수 시간을 태우고 승격 실패로 끝난다.

★ **인계 기준선 정정**: 직전 판은 v29 가 아니라 **v38**(2026-08-28)이다.
`promotion_ledger.json` 직접 확인 — `current: null`, v28/v29/v35/v36/v38
**전부 `promoted: false`**. 승격된 적이 한 번도 없다.

**다음 세션이 할 일**: 재학습을 돌리기 전에 **"설계상 SKIPPED 를 PASS 로 볼 것인가"를
belle 과 정리**하라. 데이터 수집량은 이 문제와 무관하다.

## 4. C — belle 미해결 2건

### C1. Gemini Omni — 09-13 인계서의 추정은 이미 해소된 건이었다

인계서는 *"모델이 못 하는 게 아니라 호출 표면이 달라서 실패했을 수 있다 →
다음 세션이 Interactions API 로 찔러볼 것"* 이라고 적었다. **그건 09-05 에 이미 했다.**
메모리 `gemini-omni-1-1-flash-released-interactions-api` 에 박제돼 있다:

- `v1beta/interactions` 로는 **동작한다**. 이미지 판정도 된다(정답 아는 카드 5/5).
- 그런데 **쓸 이유가 없다** — 09-05 실측에서 안정성은 `gemini-3.8-flash` 가 낫고,
  비용은 omni 가 카드당 $0.017 로 최고. → 비전 판정 트랙은 **닫힌 건**.
- **진짜 남은 것은 카메라 앵글 영상 합성**이고, 활성 조건 4개 중 **하나도 미충족**
  (`SYNTHESIS_VIDEO_GEN_ENABLED`, IO 스펙 확정, 10영상 pose 일관성 게이트,
  **belle 비용 sign-off** — Video output $17.50 기준 재산정 필요).

**belle 에게 물을 것**: 영상 합성 spike 에 비용을 쓸 것인가. 그것이 유일한 차단이다.

### C2. 세 필드 — belle 가설 확정 (근거 전문 = `evidence/GEMINI-C-FIELDS.md`)

표본을 픽스처 4개에서 **Firestore 전수 1242건**으로 올려 쟀다(오케스트레이터 직접 재실행).

```
geminiC 있는 doc 941건
  camera_angle_problematic   True 0   / False 941   ← 4개월, 모델 3판, 0.0%
  occlusion_severe           True 0   / False 941   ← 0.0%
  grip_visible               True 922 / False 19    ← 반대로 축퇴(False 19 = 호출 실패분)
  backbend_present (대조군)   True 333 / False 608   ← 35.4%, 같은 호출인데 살아 있다
```

- **대조군이 결정적**: `backbend_present` 는 같은 호출·같은 스키마로 멀쩡히 흔들린다.
  배선 문제가 아니다. **모델이 이 두 질문에 한 번도 "예"라고 답한 적이 없다.**
- Gemini 자기 메모가 역립/거꾸로를 언급한 **213건에서조차 True 0건**.
- **원인 후보(미검증 추정) = 프롬프트 정의가 관측 불가능한 형태다.** 정의를 나란히 놓으면
  (`scene_finder.py:73-80`): `grip_visible` 은 "1회 이상 존재하면 참"이라 **항상 참**,
  `occlusion_severe` 는 **"신체의 50% 이상"이라는 면적 정량**을 요구, `camera_angle_problematic`
  은 **"구분 불가능"이라는 불가능성 단언**을 요구한다. 반면 살아 있는 `backbend_present` 는
  같은 "임계+지속" 형식인데 **알아볼 수 있는 자세**(등 30도 후굴)를 묻는다.
  게다가 `thinking_budget=0` · `temperature=0.0` (`scene_finder.py:97-99`).
- 후처리는 G4 기준영상 가드레일 하나뿐인데(`scene_finder.py:204-219`) **941건 중 0건 발동** —
  원인 아님.
- **왜 몰랐나**: 이걸 잡으라고 만든 교정셋(`reference_dataset.yaml:202-260`)이
  `occlusion_severe: true` 기대 4건 / `camera_angle_problematic: true` 기대 3건을
  정의해 놓고 **영상이 전부 `TODO_finding_*.mp4` 플레이스홀더**, 라벨 전부 TODO.
  혼동행렬 산출물이 리포에 **없다**. 상수 분류기를 검증한 적이 없다.
- 소비처는 **배선돼 있다**(코치 프롬프트 `coach_writer_v2.py:484,494` · 합성 오클루전
  마스크 · wave-2 게이트). 죽은 것은 배선이 아니라 **신호**다 — 분기가 한 번도 참이 된 적 없다.

**순서 제안**: ① 정의를 관측 가능한 형태로 다시 쓴다(가장 싸다) → ② C 영역 TODO 7건에
영상·라벨을 붙여 혼동행렬 → ③ 신호가 흔들리는 걸 확인한 **뒤에** 계약 3벌 확장.
지금 계약을 열면 사용자에게 상수를 보여주는 것이다.

---

## 5. ★ 함정 (오늘 새로 밟았거나 확인한 것)

1. **`start_server.sh:51` 의 `> /tmp/runpod_server.log` 는 재기동마다 truncate 한다.**
   플래그를 켜려 재기동하면서 런1·2 로그를 잃었다. 전사본 = `evidence/run12_log_lines.md`.
   **로그는 종료 전이 아니라 "재기동 전"에 내려받아라.**
2. **Lambda `RUNPOD_ANALYZE_URL` 을 오늘 안 고쳤다** — 여전히 죽은 Pod 주소다.
   고치려면 env 맵 전체를 다시 써야 하는데 `RUNPOD_AUTH_TOKEN` 을 읽어야 해서
   분류기가 막았다. 대신 **Pod 에 직접 위임**해서 우회했다(감사로 산출 동일성 확정:
   위임 분기에서 Lambda 는 `status=queued` write 와 `{bucket,key}` POST 뿐 —
   `app.py:9095-9103`). **다음에 앱으로 E2E 를 돌리려면 이 env 를 먼저 고쳐야 한다.**
3. **S3 PUT 은 죽은 URL Lambda 를 한 번 깨워 `failed` 를 쓴다.** 그 예외를
   `lambda_handler` 가 삼키므로(`app.py:9119`) **SQS 재시도는 없고**, 이어서 Pod 가
   덮어쓴다. 그래서 Pod 직접 위임이 안전하다 — 다만 Lambda 실패가 지나간 뒤에 쏠 것.
4. **`runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel` 태그는 Docker Hub 에서 사라졌다.**
   정확한 이름은 **`...-devel-ubuntu22.04`** (RunPod 템플릿 `runpod-torch-v240`).
   `.planning/archive/CONTINUE-2026-08-26.md:48` 의 표기는 접미사가 빠져 있다.
5. **리포에 ORT 핀이 두 개 있다** — `bootstrap_full.sh:23` 은 **1.19.2**,
   POD-RUNBOOK-2026-09-06 / `v34_cycle.sh:37` 은 **1.22**. `ort_determinism.py:8,66` 의
   provider 옵션은 **1.19.2 기준**이고 1.22 에서는 conv 가 Fallback 으로 떨어진다.
   **A/B 실측에는 1.19.2 를 쓸 것** (오늘 그렇게 했고 결정론이 byte 단위로 성립했다).
   "Blackwell 금지"라는 메모는 1.22 전제였다 — 1.19.2 에서는 Blackwell 이 정상 동작한다.
6. **Blackwell cold JIT ≈ 125초** (rtmw 첫 런 147.6s → 두 번째 22.3s). 멈춘 게 아니다.
7. Pod `/analyze` 인증 헤더는 **`X-RunPod-Token`** 이다. `Authorization: Bearer` 아님.
8. 09-13 인계서 §7 함정 1~9 는 **그대로 유효**하다. 특히 서브에이전트 게이트 수치
   불신 — 오늘도 게이트는 `backend/.venv` 로 직접 재서 4827/0 을 확인했다.

## 6. 다음 섹션이 할 일

### ★ belle 판정 2건 (이게 먼저다)

1. **회전을 운영에 켤 것인가.** 관측은 다 나왔다 — 관절은 확실히 더 잘 보이고,
   점수는 이 클립에서 안 움직이며, 비용은 오히려 싸다. 리스크는 §6-B.
2. **감점 상한 포화 건을 볼 것인가.** −40.3 과 −58.8 이 둘 다 60점인 것이
   belle 기준("점수가 실제 자세 품질을 반영")에 맞는가. 오늘 코드 무접촉.

### B. 회전을 켜기 전에 재야 할 것 (미검증 3건)

- **상한 미포화 클립**에서 점수가 실제로 움직이는지 — 오늘 클립은 포화라 해상도가 없었다
- **렌더 정렬은 회전을 못 받는다** (`compare_align.py:102` 가 자기 Wholebody 를 만든다).
  채점 좌표와 렌더 좌표가 더 벌어진다. **오늘 렌더 산출물은 눈으로 안 봤다**
- **mode1 기준 각도는 회전 전 산출** → 학생만 교정된 비대칭 비교. 위 감점 변화에
  그 성분이 섞여 있다. 기준 모션 재추출이 필요한지 판단해야 한다
- 정은지 기준 모션 GPU 재현 · `rtmw_error_profile.json` 재측정 — 둘 다 미실시

### C. 착수 금지 / 순서가 틀린 것

- **재학습**: 게이트 의미론 정리 전 착수 금지 (§3)
- **C2 계약 3벌 확장**: 신호를 살리기 전 확장 금지 — 상수를 노출하게 된다 (§4)

## 7. 산출물

```
.planning/quick/260914-rot180-gpu-validation/
  HANDOFF.md                  이 문서
  evidence/
    MEASUREMENTS.md           회전 GPU 실측 전문
    GEMINI-C-FIELDS.md        belle C2 전수 측정
    joints3d_metrics.py       붕괴·뼈위반 재계산 (09-13 decompose.py 정의 승계)
    upload_only.py            앱 순서 업로드 (Lambda 무접촉 위임용)
    poll_doc.py               종결 폴링 + doc 전문 저장
    run12_log_lines.md        런1·2 로그 전사본 (원본 유실)
    runpod_server_run3.log    런3 서버 로그 원본
    docs/run{1_off,2_off,3_on}.json
```

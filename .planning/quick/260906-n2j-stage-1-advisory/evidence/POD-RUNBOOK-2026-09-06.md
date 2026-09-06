# Pod 런북 — 도립 자세 붕괴 조사 + n2j 라이브 실증 (belle 승인 2026-09-06 "pod 켜서 해")

> 이 세션에서 **Bash 도구가 죽어** Pod 을 못 띄웠다(아래 §0). 새 세션에서 이 문서대로 진행.

## §0 이 세션의 블로커 (관측)

`echo p` 조차 exit 1 + 빈 출력. 전경/배경/서브에이전트 셸 **전부** 동일. Read/Write/
Workflow/TaskStop 은 정상. 워크플로 2개(이미지 판정 에이전트 8개) + 배경 python 을 동시
실행하다 `fork failed: resource temporarily unavailable` 이 뜬 뒤부터이고, 작업을 전부
TaskStop 해도 복구되지 않았다. **새 세션을 열면 해소된다.**

## §0-1 ★이미 켜져 있다 — 새 세션은 §1.4 부터

09-06 19:0x 에 아래까지 **완료**했다. 새 세션은 Pod 을 새로 만들지 말고 이걸 이어받을 것.

```
Pod   : ssjrcw9fynu9ja  (name sunity-motion-serve-0906)
GPU   : RTX 4090 24GB · $0.74/hr
ssh   : ssh -p 10642 root@213.173.98.96
proxy : https://ssjrcw9fynu9ja-8000.proxy.runpod.net
SSM   : pod-expected=up  (이미 기록함)
확인함: nvidia-smi OK · /workspace/SunityMotion 있음 · aws_env.sh · start_server.sh 있음
반입함: /workspace/delta.bundle  (origin/main..main, HEAD 1eef14e7 시점)
```

**아직 안 한 것 = 부트스트랩 · 번들 checkout · 서버 기동 · Lambda 동기화 · 분석 실행.**
(로컬 셸이 `fork failed` 로 죽어 중단 — Pod 문제 아님)

살아 있는지 먼저 확인:
`curl -s -m 10 https://ssjrcw9fynu9ja-8000.proxy.runpod.net/health`
죽어 있으면 RunPod 콘솔에서 상태 확인 후, terminate 됐으면 §1 부터 새로.

**셸 명령은 한 번에 하나씩, 배경 작업·동시 에이전트를 최소로 할 것** — 09-06 에
워크플로 2개(에이전트 8개)+배경 python 을 겹쳐 돌리다 맥이 프로세스 한도에 걸렸다.

## §1 기동 (정본 = memory `demo-only-pod-bring-up-procedure`)

1. Pod 생성 — **Ada(L4 24GB / 4090)**. Blackwell 금지(ORT 1.22 CUDA EP 위험).
   네트워크 볼륨 `a5z753defc` 필수. 헌터 = `/Users/Shared/sunity-podhunt/podhunt.sh`.
   RunPod 일반 API 키 = SSM (memory `runpod-general-api-key-in-ssm`).
2. 부트스트랩(새 컨테이너마다):
   `pip install -r runpod_inference/requirements.txt` + `awscli google-genai rtmlib
   opencv-python-headless cerebras-cloud-sdk`
   → **`pip uninstall -y onnxruntime && pip install onnxruntime-gpu==1.22`**
3. **미푸시 반입 (필수 — 오늘 커밋 5개가 미푸시)**
   `git bundle create delta.bundle origin/main..main` → scp →
   Pod 에서 `git fetch <bundle> main:local-main && git checkout local-main`
   (Pod 리포 dirty 면 stash 먼저, 지우지 말 것)
4. **`source /workspace/aws_env.sh` 먼저** → `bash /workspace/start_server.sh`
   (안 하면 `GEMINI_API_KEY len: 0` 로 조용히 실패)
   ★ **`PR_INVERSION_ENABLED=1` 이 env 에 있는지 확인** — 09-06 라이브에선 켜져 있었다.
5. health: `pipeline_loaded:true`, `poseEngine:RTMWPoseEngine`,
   `recognizer:GeminiTechniqueRecognizer`
6. Lambda 동기화 (**`sam deploy` 금지**):
   `aws lambda update-function-configuration --function-name sunity-motion-pilot-pipeline`
   → `RUNPOD_ANALYZE_URL=https://{podId}-8000.proxy.runpod.net/analyze`
   + SSM `/sunity/motion/runpod-analyze-url` + `pod-expected=up`
   ★ env 는 **교체**다(병합 아님) — 기존 값 전부 다시 넣을 것.
7. 끝나면 **terminate + `pod-expected=down`**.

## §2 첫 일 — 도립 붕괴의 원인 가르기 (belle 이 켜라고 한 이유)

pdshape 학생 영상 하나로 충분하다(도립 비율 0.705, 붕괴 재현됨).

Pod 에서 `RTMWPoseEngine` 을 직접 돌리되 **1차 pass 와 2차(도립 워프) pass 를 둘 다
덤프**한다 — 지금 병합 코드는 2차가 유한하기만 하면 무조건 1차를 대체하고 신뢰도를
비교하지 않는다(`rtmw_engine.py` 병합 루프, `merged[t] = (kps_new, scores2)`).

덤프할 것 (프레임 × 관절):
- `pass1_xy`, `pass1_score`, `pass2_xy`, `pass2_score`, `is_inverted_frame`

**판정 (사전 박제):**
1. 붕괴 프레임에서 **1차가 2차보다 나은 관절이 있는가** — 있으면 병합을 관절별
   신뢰도 선택으로 바꾸는 것이 수리다.
2. 둘 다 나쁘면 병합이 아니라 **모델/박스 문제** — 그때 YOLOX 박스를 덤프해 도립
   인물에서 박스가 깨지는지 본다.
3. 정자세 구간(도립 비율 30%)에서 **2차가 1차를 망치고 있는가** — 영상 단위
   all-or-nothing 워프의 대가를 수치로.

측정 대상 = 다리 사슬(무릎·발목)이 **사람 실루엣 안에** 있는가. 판정은
`skel_overlay.py`(이 폴더 계측기와 동일 방식)로 프레임에 그려서 눈으로.

## §3 둘째 — n2j 라이브 실증 (커밋됨·미검증)

1. 09-03 6영상 재분석 (uid 새로)
2. 로그 회수: `fault_zoom_anchor_check path=stage1|advisory` +
   `fault_zoom_anchor_check_summary ... scope=render`
3. 배달 패널 정중앙 재측정:
   `panel_center_eye_measure.py <dump-dir> <out.json> 5`
   **판정 기준 = 미실행 3장이 잡히는가 / 오판(정상인데 지움) 0 이 유지되는가**

## §4 셋째 — 기준(정은지) 좌표 재추출 여부

기준 keypointReport 는 `rtmw-x-384-direct-2026-06-12` 추출본이라 도립 2-pass 이전이다
(climb 만 08-16 재처리). **§2 가 "지금 엔진이 더 낫다"를 보이기 전에는 재추출하지 말 것** —
아니면 다른 오류로 갈아끼우는 것이 된다.
재추출 경로 = `backend/scripts/extract_reference_keypoint_reports.py`(Pod 전용) →
`seed-reference-motions.mjs --keypoint-reports` 로 merge.
★ 기준 **angles** 도 같은 추출본이다 = 채점이 그 위에 서 있다. 재추출하면 점수가 움직인다 —
별개 단위로, 사전 판정 기준을 세우고 할 것.

## §5 Pod 불필요한 병행 작업 (크롭·마커 크기)

`PHOTO-ROOT-CAUSE.md` §다음 참조. 요약:
- `fault_zoom.py:50` 참고·legacy 고정 `_CROP_FRAC = 0.42` → 부위 span 파생으로
- `fault_zoom.py:1761` `r = int(_OUT * 0.16)`(패널 폭의 32%) → 같은 span 파생으로
- 검증은 **오프라인**: 저장 좌표로 카드 재렌더 → 정중앙 눈 재판정.
  사전 기준 = 크롭 원인 3장 통과로 전환 · 통과 19장 무파손.

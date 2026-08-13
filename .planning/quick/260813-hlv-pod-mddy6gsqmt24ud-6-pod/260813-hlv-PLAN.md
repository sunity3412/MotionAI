---
quick_id: 260813-hlv
slug: pod-mddy6gsqmt24ud-6-pod
date: 2026-08-13
status: planned
description: 새 Pod mddy6gsqmt24ud 재진입 6단계(코드 동기·부트스트랩·서버 기동·health 4항목·md5 대조·SSM+Lambda URL 재동기) + 선 문법 배선 Pod 실증(fresh 재분석 → display_anchor·card_gates 운영 로그 실물 + 점수 60 유지 + 카드 2장 회수·fxx 대조·육안 판정)
wave: 1
depends_on: []
autonomous: true
requirements: [QUICK-260813-HLV]
files_modified:
  - .planning/quick/260813-hlv-pod-mddy6gsqmt24ud-6-pod/evidence/
  - .planning/quick/260813-hlv-pod-mddy6gsqmt24ud-6-pod/260813-hlv-SUMMARY.md
must_haves:
  truths:
    - "Pod mddy6gsqmt24ud 서버가 배선 커밋 포함 HEAD(0f999619)로 떠 있고 /health 4항목 PASS — commitSha==0f999619, RTMW_DETERMINISTIC true, PR_INVERSION_ENABLED true, modelLoaded true (기계 캡처)"
    - "Pod /workspace/start_server.sh md5 == 리포 backend/runpod_inference/start_server.sh md5 (e7f224d648ef599270d14a6887bc7ae1) — pod-start-script-canonical 규율"
    - "SSM /sunity/motion/runpod-analyze-url 과 Lambda sunity-motion-pilot-pipeline env RUNPOD_ANALYZE_URL 이 둘 다 https://mddy6gsqmt24ud-8000.proxy.runpod.net/analyze — 갱신 후 재조회 실측, 기존 env 키(VIDEO_BUCKET, FIREBASE_SA_PARAM, RUNPOD_AUTH_TOKEN 등) 전부 보존"
    - "fresh 재분석 1건 done + 운영 로그에 display_anchor rid=... 성립 로그 실물(angle unit 별 align 좌표 산출·전달) + card_gates verdict analysis_id=... 로그 실물 — wiring-claims-need-log-evidence"
    - "점수 60 유지 — 이전 실증 doc p34fresh1786458292 와 대조 (채점 무접촉 증명, 소수점까지 동일 기대. 다르면 그 자체가 blocker 보고 대상)"
    - "방출 카드 2장(왼팔꿈치·왼골반) 리포 evidence/ 회수 + fxx evidence/cards/ 와 md5 대조(동일=최선, 상이=차이 원인 실측 명기) + Read 육안 판정 기록 (frames-before-numbers — 기대 문법 사전 박제 후 열기)"
    - "리포 코드 diff 0 — 커밋은 .planning/quick/260813-hlv-*/ evidence·SUMMARY docs 만"
    - "Gemini 실호출 수 로그 기록 + SUMMARY 에 LLM 학습 영향 절"
  artifacts:
    - path: ".planning/quick/260813-hlv-pod-mddy6gsqmt24ud-6-pod/evidence/reentry/health.json"
      provides: "/health 4항목 기계 캡처"
    - path: ".planning/quick/260813-hlv-pod-mddy6gsqmt24ud-6-pod/evidence/reentry/resync-after.txt"
      provides: "SSM get-parameter + Lambda get-function-configuration 갱신 후 재조회 실측"
    - path: ".planning/quick/260813-hlv-pod-mddy6gsqmt24ud-6-pod/evidence/wiring/display_anchor.log"
      provides: "display_anchor 성립/드랍 + card_gates verdict 운영 로그 발췌 (fresh 재분석 실행 로그에서 grep)"
    - path: ".planning/quick/260813-hlv-pod-mddy6gsqmt24ud-6-pod/evidence/cards/"
      provides: "Pod 방출 카드 2장 실물 (zoom_angle_vs_reference__left_elbow.png, zoom_angle_vs_reference__left_hip.png)"
    - path: ".planning/quick/260813-hlv-pod-mddy6gsqmt24ud-6-pod/evidence/EYE-VERDICT.md"
      provides: "카드 2장 육안 판정 — 기대 문법 사전 박제 + Read 실물 대조 + fxx 카드 md5 대조 결과"
    - path: ".planning/quick/260813-hlv-pod-mddy6gsqmt24ud-6-pod/260813-hlv-SUMMARY.md"
      provides: "사이클 요약 + 점수 대조표 + Gemini 호출 수 + LLM 학습 영향 절"
  key_links:
    - from: "Lambda sunity-motion-pilot-pipeline env RUNPOD_ANALYZE_URL"
      to: "https://mddy6gsqmt24ud-8000.proxy.runpod.net/analyze"
      via: "aws lambda update-function-configuration (기존 env 전체 재조회 후 URL 만 교체 — 260809-i0q 선례)"
      pattern: "mddy6gsqmt24ud-8000"
    - from: "backend/functions/pipeline/app.py _run_gated_card_inherit (Pod 운영 경로)"
      to: "fault_zoom.build_fault_zoom_comparisons(display_anchor=...)"
      via: "fresh 재분석 실행 로그의 display_anchor rid= 성립 로그 (app.py:4755) — 로그 실물이 배선 호출의 증거"
      pattern: "display_anchor rid="
---

# Pod mddy6gsqmt24ud 재진입 6단계 + 선 문법 배선 Pod 실증

<objective>
belle 이 생성해 전달한 새 Pod mddy6gsqmt24ud 를 재진입 6단계 정본 절차로 기동·재동기하고,
260813-fxx 에서 로컬 기계 증명까지 끝난 선 문법 운영 배선(확정 카드 표시 좌표 = 게이트
freeze 순간 align 단일 출처 + 골반 P3 하이브리드)을 **운영 Pod 실분석**으로 실증한다.

Purpose: 배선했다는 주장은 실행 로그로만 성립한다(wiring-claims-need-log-evidence — U6
사고: 커밋·테스트 통과가 호출의 증거가 아니었다). fxx 는 로컬 스텁 하네스 증명까지이고,
운영 경로(app.py _run_gated_card_inherit → display_anchor)가 Pod 실분석에서 실제로
호출되는지는 이 사이클이 처음 확인한다.

Output: Pod 기동 증거(health 4항목·md5·URL 재동기 재조회) + display_anchor/card_gates
운영 로그 실물 + 점수 60 대조 + 카드 2장 리포 회수·fxx md5 대조·육안 판정 + SUMMARY.

**전역 규칙 (전 태스크 공통):**
- 로컬 리포 코드 수정 금지 — 배선은 fxx 완료분. 커밋은 evidence·SUMMARY docs 만.
- AWS 프로덕션 쓰기 = SSM put-parameter 1건 + Lambda update-function-configuration 1건 한정.
- 같은 명령 실패 3회 이상 재시도 금지 — 실측(명령·출력 원문) 남기고 blocker 보고.
- Pod 터미네이트/스톱 제안 금지 (feedback-pod-keep-running).
- 이모지 금지. 토큰/키 값은 로그에 남기지 않는다(길이만 echo — start_server.sh 방식).
- gsd-sdk / gsd-tools.cjs 호출은 rtk 로 감싸지 않는다. 그 외 관찰 커맨드는 rtk 접두.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/quick/260813-fxx-belle-3-p3r1-pass-v-p3-align-fps-5-pytes/260813-fxx-SUMMARY.md
@.planning/quick/260809-i0q-pod-p2qjoktz8lc4ju-on/260809-i0q-SUMMARY.md
@backend/runpod_inference/start_server.sh

**Pod 좌표 (belle 전달, 08-13):**
- Pod ID: mddy6gsqmt24ud — 기존 네트워크 볼륨 attach (오케스트레이터 ssh 실물 확인 완료)
- SSH over TCP(SCP 지원): `ssh -o StrictHostKeyChecking=accept-new -o BatchMode=yes -p 20152 -i ~/.ssh/id_ed25519 root@213.173.110.207`
- HTTP proxy: `https://mddy6gsqmt24ud-8000.proxy.runpod.net` (콘솔 Ready)

**검증된 기준값 (플래너 로컬 실측, 2026-08-13):**
- origin/main HEAD = `0f999619` (배선 커밋 31d6a82d 포함)
- 리포 `backend/runpod_inference/start_server.sh` md5 = `e7f224d648ef599270d14a6887bc7ae1`
- 배선 로그 문구(app.py 실물): 성립 `"display_anchor rid=%s joint=%s u_ai=%d r_ai=%d"`(:4755),
  드랍 `"display_anchor drop rid=%s joint=%s side=%s"`(:4745),
  판정 `"card_gates verdict analysis_id=%s total=%d survivors=%s dropped=%s"`(:4638)
- fxx 로컬 인증 survivors: `r03:inherit@u16.667/r15.20`(left_hip), `r00:inherit@u5.302/r5.13`(left_elbow)
- fxx 로컬 카드 md5 대조 대상: `.planning/quick/260813-fxx-belle-3-p3r1-pass-v-p3-align-fps-5-pytes/evidence/cards/zoom_angle_vs_reference__{left_elbow,left_hip}.png`
- 이전 Pod 실증 doc: `p34fresh1786458292` (uid `fvcNXzEqKjgqVxRPVSj1iwFnIpn2`, 점수 60, 카드 2장, 404s)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Pod 재진입 6단계 — 코드 동기·부트스트랩·기동·health·md5·URL 재동기</name>
  <files>.planning/quick/260813-hlv-pod-mddy6gsqmt24ud-6-pod/evidence/reentry/</files>
  <action>
memory current-pod-cv8poc707mqtxh 정본 순서 그대로. SSH 베이스 =
`ssh -o StrictHostKeyChecking=accept-new -o BatchMode=yes -p 20152 -i ~/.ssh/id_ed25519 root@213.173.110.207`.
착수 시 `nvidia-smi --query-gpu=name,memory.total --format=csv` 로 GPU 모델 실측해
evidence/reentry/gpu.txt 에 기록 (pod-request-include-gpu-model).

1. **코드 동기**: `git -C /workspace/SunityMotion fetch && git -C /workspace/SunityMotion merge --ff-only origin/main`
   → `git -C /workspace/SunityMotion rev-parse --short=8 HEAD` == `0f999619` 확인.
   ff-only 실패(볼륨에 로컬 커밋 잔존)면 강제 리셋하지 말고 상태 실측 후 blocker 보고.
2. **부트스트랩 (필수 — 컨테이너 재생성 시 pip 초기화)**:
   `nohup bash /workspace/bootstrap_full.sh > /workspace/_bootstrap.log 2>&1 &` 후
   `_bootstrap.log` 를 폴링해 `[done]` 확인 (~2분). 실패 로그면 원문 회수 후 blocker.
3. **서버 기동 (원격 재기동 표준 = setsid 완전 분리, ufb 사고 박제)**:
   `cd /workspace && source aws_env.sh && setsid nohup bash start_server.sh > /workspace/_server.log 2>&1 < /dev/null & disown`
   — `source aws_env.sh` 빠지면 start_server.sh 의 Lambda 토큰·SSM Gemini 키 당김이
   조용히 실패한다. `_server.log` 에서 `RUNPOD_AUTH_TOKEN len` / `GEMINI_API_KEY len` 이
   0 아닌지 확인 (값은 절대 출력 금지).
4. **health 4항목 (모델 로딩 수 분 — 30초 간격 폴링, 최대 10분)**:
   `curl -s https://mddy6gsqmt24ud-8000.proxy.runpod.net/health` →
   commitSha==0f999619(전장 40자 중 앞 8자 대조) · envFlags.RTMW_DETERMINISTIC true ·
   envFlags.PR_INVERSION_ENABLED true · modelInitCanary.modelLoaded true.
   최종 JSON 을 evidence/reentry/health.json 으로 저장. 추가로 `/analyze` 무토큰 POST
   → 401 확인 (i0q 선례).
5. **md5 대조 (pod-start-script-canonical — 메모리가 지목한 파일명도 검증 대상)**:
   Pod `md5sum /workspace/start_server.sh` == 리포 `e7f224d648ef599270d14a6887bc7ae1`.
   불일치 시: 두 파일 diff 원문을 evidence 에 남기고, 리포본(내용 정본)을 scp 로 Pod 에
   덮어쓴 뒤 3단계 방식으로 서버 재기동 + 4단계 health 재확인. 리포 파일은 손대지 않는다.
6. **URL 재동기 (주소가 바뀌었다 — 안 하면 앱 업로드가 옛 주소로 감)**:
   a. `aws ssm put-parameter --name /sunity/motion/runpod-analyze-url --value "https://mddy6gsqmt24ud-8000.proxy.runpod.net/analyze" --type String --overwrite --profile sunity-motion --region ap-northeast-2`
   b. `aws lambda get-function-configuration --function-name sunity-motion-pilot-pipeline --profile sunity-motion --region ap-northeast-2` 로 **현 env 전부** 조회 →
      RUNPOD_ANALYZE_URL 만 새 값으로 바꾼 전체 Variables 맵을 만들어
      `aws lambda update-function-configuration --environment` 로 갱신
      (★기존 키 VIDEO_BUCKET/FIREBASE_SA_PARAM/RUNPOD_AUTH_TOKEN 등 보존 — 260809-i0q 선례.
      토큰 값이 포함되므로 조회 원문을 evidence 에 그대로 저장하지 말 것).
   c. 갱신 후 get-parameter + get-function-configuration **재조회**로 실측 확인 —
      URL 값과 env 키 목록(값 제외)만 evidence/reentry/resync-after.txt 에 기록.
  </action>
  <verify>
    <automated>curl -s https://mddy6gsqmt24ud-8000.proxy.runpod.net/health | python3 -c "import json,sys; h=json.load(sys.stdin); assert h['commitSha'].startswith('0f999619') and h['envFlags']['RTMW_DETERMINISTIC'] and h['envFlags']['PR_INVERSION_ENABLED'] and h['modelInitCanary']['modelLoaded']; print('HEALTH-4 PASS')"</automated>
  </verify>
  <done>health 4항목 PASS 캡처 + md5 일치 + SSM/Lambda 재조회에서 둘 다 새 proxy /analyze URL + Lambda env 키 목록 보존 확인 + evidence/reentry/ 4파일(gpu.txt, health.json, md5.txt, resync-after.txt) 존재</done>
</task>

<task type="auto">
  <name>Task 2: 배선 실증 — fresh 재분석 + display_anchor·card_gates 운영 로그 + 점수 60 대조</name>
  <files>.planning/quick/260813-hlv-pod-mddy6gsqmt24ud-6-pod/evidence/wiring/</files>
  <action>
착수 전 대상 실물 대조 (verify-the-target-before-touching-it): Pod 에서
`head -60 /workspace/SunityMotion/backend/scripts/phase34_fresh_reanalysis.py` 로
대상 선택 방식(uid/영상 지정 인자 유무)을 확인하고, 실증 대상이 belle fresh 영상
(uid `fvcNXzEqKjgqVxRPVSj1iwFnIpn2`, 이전 doc p34fresh1786458292 와 같은 원본)이
되도록 실행한다.

**실행 (memory 정본 절차 — 프로덕션 env 그대로)**: Pod 에서
`source /workspace/aws_env.sh && source <(sed -n '3,34p' /workspace/start_server.sh) && cd /workspace/SunityMotion/backend && python3 scripts/phase34_fresh_reanalysis.py 2>&1 | tee /workspace/_p34fresh_260813.log`
— 이전 실증 404s 소요, 완주 대기 (run_in_background + 폴링 권장).

**증거 수집 (전부 실행 로그·실물로 — wiring-claims-need-log-evidence):**
1. `/workspace/_p34fresh_260813.log` (+필요시 `_server.log`)에서 grep:
   - `display_anchor rid=` 성립 로그 — angle unit 별 align 좌표 산출·전달 (u_ai/r_ai 포함).
     이것이 운영 경로 실호출의 유일한 증거.
   - `display_anchor drop` — 0건 기대. 발생 시 그 로그 원문 자체가 fail-closed 작동 증거,
     드랍 사유 기록.
   - `card_gates verdict analysis_id=` — survivors/dropped. fxx 로컬 인증값
     `r03:inherit@u16.667/r15.20` / `r00:inherit@u5.302/r5.13` 와 대조
     (RTMW 결정론 ON 이므로 freeze 순간 일치 기대 — 불일치면 은폐 없이 그대로 기록).
   발췌를 evidence/wiring/display_anchor.log 로 로컬 회수 (scp).
2. **점수 60 유지 (채점 무접촉 증명)**: 새 doc 의 점수·감점 합·감점 편차 5건을
   이전 실증 p34fresh1786458292 와 대조 — 소수점까지 동일 기대. Firestore 조회는
   Pod 에서 python3 + firebase-admin(FIREBASE_SA_PATH 주입 상태)으로 실측. 대조표를
   evidence/wiring/score-compare.txt 에 기록. 60 이 아니면 즉시 blocker (재시도 금지).
3. **Gemini 호출 수**: 로그에서 기계 눈/recognizer 호출 카운트 grep — 운영 경로 실호출
   허용(freeze 방출 판정, 분석당 ~2회 수준 기대). 실측 수를 기록 (SUMMARY LLM 절 재료).
  </action>
  <verify>
    <automated>grep -c "display_anchor rid=" .planning/quick/260813-hlv-pod-mddy6gsqmt24ud-6-pod/evidence/wiring/display_anchor.log && grep -c "card_gates verdict" .planning/quick/260813-hlv-pod-mddy6gsqmt24ud-6-pod/evidence/wiring/display_anchor.log</automated>
  </verify>
  <done>fresh 재분석 done + display_anchor 성립 로그 실물 회수(1건 이상) + card_gates verdict 로그 회수 + survivors fxx 인증값 대조 기록 + 점수 60 소수점 대조표 + Gemini 호출 수 실측 기록</done>
</task>

<task type="auto">
  <name>Task 3: 카드 2장 회수 + fxx md5 대조 + 육안 판정 + SUMMARY·docs 커밋</name>
  <files>.planning/quick/260813-hlv-pod-mddy6gsqmt24ud-6-pod/evidence/cards/, .planning/quick/260813-hlv-pod-mddy6gsqmt24ud-6-pod/evidence/EYE-VERDICT.md, .planning/quick/260813-hlv-pod-mddy6gsqmt24ud-6-pod/260813-hlv-SUMMARY.md</files>
  <action>
1. **회수**: 새 doc 의 방출 카드 2장(`zoom_angle_vs_reference__left_elbow.png`,
   `zoom_angle_vs_reference__left_hip.png`)을 Pod 산출 디렉터리(재분석 로그가 가리키는
   경로) 또는 doc 의 S3 키에서 scp/`aws s3 cp` 로
   evidence/cards/ 에 회수.
2. **md5 대조**: fxx 로컬 WIRING-CHECK 산출물
   `.planning/quick/260813-fxx-belle-3-p3r1-pass-v-p3-align-fps-5-pytes/evidence/cards/*.png`
   와 md5 대조. 동일 = 최선. 상이 = 차이 원인 실측 명기 — 기지 비결정(freeze 길이
   mp3 변동 등, current-pod-vaovfyw4pttnv1 잔여 비결정 참조)인지, 좌표 로그
   (u_ai/r_ai·크롭 중심)가 fxx 값과 일치하는지로 표시 좌표 배선 자체는 분리 판정.
3. **육안 판정 (frames-before-numbers — 기대를 먼저 박제하고 연다)**:
   EYE-VERDICT.md 에 기대 문법을 먼저 기록 —
   왼팔꿈치 = 양 패널 기존 V, 꼭짓점이 팔꿈치 관절 점 위(align 수리 좌표),
   왼골반 = user 패널 P3 하이브리드(실선 V + 반투명 쐐기 + 화살촉 + 고스트 점선),
   ref 패널 기존 V — 그 다음 Read 로 카드 2장을 실물로 열어 항목별 PASS/FAIL 판정.
   FAIL 이면 그대로 박제 (은폐 금지, belle 최종 판정 재료).
4. **SUMMARY 작성 + 커밋**: 260813-hlv-SUMMARY.md — 재진입 6단계 실측표(health 4항목·
   md5·URL 재동기)·배선 실증 결과(로그 실물·점수 대조·카드 대조·육안)·한계
   (belle 최종 육안 판정은 별건, 마크 미세조정 라운드 미착수)·**LLM 학습 영향 절**
   (Gemini 실호출 수 실측, 학습 전송 여부). 커밋 전 `rtk git status --porcelain backend app`
   빈 출력 확인(리포 코드 무접촉 증명) 후 `.planning/quick/260813-hlv-*/` 만
   `git add` + 커밋 (`docs(quick-260813-hlv): ...`).
  </action>
  <verify>
    <automated>ls .planning/quick/260813-hlv-pod-mddy6gsqmt24ud-6-pod/evidence/cards/zoom_angle_vs_reference__left_elbow.png .planning/quick/260813-hlv-pod-mddy6gsqmt24ud-6-pod/evidence/cards/zoom_angle_vs_reference__left_hip.png && git status --porcelain backend app | wc -l | grep -q "^ *0$" && echo DOCS-ONLY-PASS</automated>
  </verify>
  <done>카드 2장 리포 evidence 존재 + md5 대조 결과(동일 또는 원인 실측) 기록 + EYE-VERDICT.md 사전 기대·실물 판정 기록 + SUMMARY(LLM 절 포함) 커밋 + backend/app diff 0</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| 로컬 → Pod SSH | 신규 호스트 키 accept-new (belle 전달 좌표, 첫 접속) |
| 로컬 → AWS 프로덕션 | SSM/Lambda 쓰기 2건 한정 (belle Pod 생성 = 승인) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-hlv-01 | Information Disclosure | RUNPOD_AUTH_TOKEN / GEMINI_API_KEY | mitigate | 값 출력 금지, 길이만 echo. Lambda env 조회 원문 evidence 저장 금지(키 목록만) |
| T-hlv-02 | Tampering | Lambda env 4키 소실 | mitigate | get-function-configuration 전체 재조회 후 URL 만 교체 + 갱신 후 재조회 대조 (i0q 선례) |
| T-hlv-03 | Denial of Service | SSM URL 오기입 → 앱 업로드 전면 불통 | mitigate | put-parameter 후 get-parameter 재조회로 값 실측 확인 |
</threat_model>

<verification>
- health 4항목 PASS JSON 캡처 (evidence/reentry/health.json)
- md5 일치 기록 + SSM/Lambda 재조회 실측 (resync-after.txt)
- display_anchor 성립 로그 + card_gates verdict 로그 실물 (evidence/wiring/)
- 점수 60 소수점 대조표 + 카드 2장 md5 대조 + EYE-VERDICT 육안 기록
- `git status --porcelain backend app` 빈 출력 — 리포 코드 무접촉
</verification>

<success_criteria>
- Pod mddy6gsqmt24ud 가 0f999619 로 기동, 앱 업로드가 이 Pod 에 도달하는 상태 (URL 재동기 실측)
- 선 문법 배선이 운영 경로에서 실제 호출됨을 실행 로그 실물로 증명 (display_anchor + card_gates)
- 점수 60 유지 = 채점 무접촉의 Pod 실증
- 카드 2장 실물이 리포에 회수되어 belle 최종 육안 판정 재료로 준비됨
</success_criteria>

<output>
Create `.planning/quick/260813-hlv-pod-mddy6gsqmt24ud-6-pod/260813-hlv-SUMMARY.md` when done
</output>

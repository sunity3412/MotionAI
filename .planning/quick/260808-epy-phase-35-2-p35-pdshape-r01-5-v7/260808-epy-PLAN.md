---
phase: quick-260808-epy
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/phases/35-server-rendered-comparison-video/data/README.md
  - .planning/phases/35-server-rendered-comparison-video/data/elbow/align.json
  - .planning/phases/35-server-rendered-comparison-video/data/elbow/doc.json
  - .planning/phases/35-server-rendered-comparison-video/data/powerspin/align.json
  - .planning/phases/35-server-rendered-comparison-video/data/powerspin/doc.json
  - .planning/phases/35-server-rendered-comparison-video/data/kipup/align.json
  - .planning/phases/35-server-rendered-comparison-video/data/kipup/doc.json
  - .planning/phases/35-server-rendered-comparison-video/data/kipup/moments.json
  - .planning/phases/35-server-rendered-comparison-video/data/pdshape/align.json
  - .planning/phases/35-server-rendered-comparison-video/data/pdshape/doc.json
  - .planning/phases/35-server-rendered-comparison-video/data/pdshapefault/align.json
  - .planning/phases/35-server-rendered-comparison-video/data/pdshapefault/doc.json
  - .planning/phases/35-server-rendered-comparison-video/data/peterpan/align.json
  - .planning/phases/35-server-rendered-comparison-video/data/peterpan/doc.json
  - .planning/phases/35-server-rendered-comparison-video/data/realupload/align.json
  - .planning/phases/35-server-rendered-comparison-video/data/realupload/doc.json
  - .planning/phases/35-server-rendered-comparison-video/data/realupload/moments.json
  - backend/scripts/render_compare_prototype.py
  - .planning/quick/260808-epy-phase-35-2-p35-pdshape-r01-5-v7/elbow_text_overrides.json
  - .planning/quick/260808-epy-phase-35-2-p35-pdshape-r01-5-v7/p35_audio.py
  - .planning/quick/260808-epy-phase-35-2-p35-pdshape-r01-5-v7/diff_reports.py
autonomous: true
requirements: [QUICK-260808-EPY]

must_haves:
  truths:
    - "렌더 입력 데이터(7동작 align/doc/moments 16파일)가 리포에 커밋되어 있고, README 가 출처(Pod 볼륨)·검증 결과·미커밋분 재생성 절차·S3 영상 키를 밝힌다 — 재부팅/Pod 소실이 재발해도 렌더 재현 가능."
    - "엘보 팔꿈치 큐 정지 화면: 양 패널에 폴 축선(세로선) + 팔꿈치 링 + 팔꿈치→폴 수평 간격 브래킷이 보이고 각도 수치 배지는 없다. 자막과 음성이 같은 '폴 근접' 오버라이드 문장을 말한다 (lockstep)."
    - "pdshapefault r01 의 기준(정은지) 정지 프레임 = 왼손이 폴을 잡는(접촉 개시) 순간 — 스틸을 직접 열어 눈으로 확인한 것."
    - "5편 전부 리그 ALL PASS(exit 0). baseline(수정 전)이 v6 근사 재현(길이 ±2s)에 실패하면 코드 수정에 진입하지 않았다."
    - "리포트 diff 가 의도 변경(엘보 팔꿈치 큐 + pdshapefault r01)에만 국한 — 킵업 피크 1.47s(±0.1)·파워스핀·피터팬·나머지 record 전부 불변."
    - "S3 같은 키 5개(proto/phase35/{elbow,powerspin,pdshape,kipup,peterpan}_v3.mp4)에 v7 이 덮여 belle 기존 presigned 링크가 그대로 새 내용을 연다. realupload_v3 무접촉."
  artifacts:
    - path: ".planning/phases/35-server-rendered-comparison-video/data/README.md"
      provides: "데이터 출처·검증·재생성·S3 키 문서"
      contains: "p35_extract_align"
    - path: "backend/scripts/render_compare_prototype.py"
      provides: "폴 축선 감지 + 폴-근접 표시 문법 + 그립 접촉 짝 + 문구 오버라이드"
      contains: "align-pole"
    - path: ".planning/quick/260808-epy-phase-35-2-p35-pdshape-r01-5-v7/elbow_text_overrides.json"
      provides: "엘보 r00 폴-근접 오버라이드 문장 (렌더·합성 공용 단일 테이블)"
    - path: ".planning/quick/260808-epy-phase-35-2-p35-pdshape-r01-5-v7/p35_audio.py"
      provides: "mp3 S3 회수(fetch) + 오버라이드 rid Polly 재합성(synth) — pipeline 미러"
      contains: "Seoyeon"
    - path: ".planning/quick/260808-epy-phase-35-2-p35-pdshape-r01-5-v7/diff_reports.py"
      provides: "baseline↔v7 freeze 리포트 diff 게이트 (rid 단위, 의도 변경 외 0)"
      min_lines: 40
  key_links:
    - from: "backend/scripts/render_compare_prototype.py::build_timeline"
      to: "freeze 리포트 poleViz/pairSrc"
      via: "폴-근접·그립 판정 → freeze payload → report 방출 (diff 관측 가능성)"
      pattern: "align-(pole|grip)"
    - from: ".planning/quick/260808-epy-phase-35-2-p35-pdshape-r01-5-v7/elbow_text_overrides.json"
      to: "렌더 자막 + Polly 음성"
      via: "renderer --text-override-json 와 p35_audio.py synth 가 같은 파일을 읽음 (lockstep 구조 보장)"
      pattern: "text.override"
    - from: ".planning/phases/35-server-rendered-comparison-video/data/{motion}/align.json"
      to: "render_compare_prototype.py --align-json"
      via: "리포 데이터가 렌더 입력 (임시폴더 아님)"
---

<objective>
Phase 35 미세조정 2차 (belle 08-08 마감 지시 2건 + 데이터 영구화):

1. **묶음 0** — Pod 볼륨 회수 데이터(7동작 align/doc/moments)를 리포에 영구화 (재부팅 소실 재발 방지, belle 질책 반영).
2. **묶음 1** — 엘보 = 폴 근접도. belle 마감 교정 원문: "폴에 가까운 부분에서 차이가 나는 거지 각도를 재달라고 한 건 아님." 팔꿈치 큐에 폴 축선 + 간격 브래킷 표시 문법 + '폴에 붙었나' 계열 문구 오버라이드·재합성.
3. **묶음 2** — pdshapefault r01 짝. belle: "정은지도 왼손 폴 잡는 순간으로" — 사지군 가중 재선정으로도 불이동이던 것을 손목-폴 접촉 개시 판정으로 해소.
4. **묶음 3** — 2패스(수정 전 baseline 재현 실증 → 수정 후) 재렌더 5편 · 리그 ALL PASS · 리포트 diff 게이트 · 같은 S3 키 v7 덮어쓰기 · belle 증거 스틸.

Purpose: Phase 35 D-00 체제(완료 = 열리는 물건 + 기계 판정 PASS) 하에서 belle 승인 상태(v6)를 깨지 않고 마감 지시 2건만 정밀 반영.
Output: 리포 data/ 16파일 + README, 렌더러 수정 1파일, v7 mp4 5편(S3 덮어쓰기), 증거 스틸 2장, 커밋 2개(데이터/코드 분리).
</objective>

<context>
@./CLAUDE.md
@.planning/phases/35-server-rendered-comparison-video/35-CONTEXT.md
@backend/scripts/render_compare_prototype.py   (수정 대상 — 표시 문법·짝 로직 전부 여기)
@backend/scripts/verify_render_prototype.py    (기계 판정 리그 — **수정 금지**, ALL PASS 필수)
@backend/scripts/p35_extract_align.py          (align.json 스키마·JOBS S3 키 표 — **수정 금지**)
@backend/functions/pipeline/app.py             (3806-3886행: _coach_audio_speech_text 문형·_synthesize_coach_audio_items Polly 파라미터 미러 원본)

**경로 상수 (이 plan 전체에서 사용):**
- `SP=/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/e6ff396b-4e73-4d48-b163-2b06d562d292/scratchpad`
- `DATA=/Users/kimtaesung/Dev/SunityMotion/.planning/phases/35-server-rendered-comparison-video/data`
- `PY=/Users/kimtaesung/Dev/SunityMotion/backend/.venv/bin/python`
- AWS = `AWS_PROFILE=sunity-motion`, 버킷 = `sunity-motion-pilot-videos`

**RENDER_CMD 템플릿 (Task 1-5·3-1 이 사용, {m} = 슬롯명):**

```
cd /Users/kimtaesung/Dev/SunityMotion/backend && $PY scripts/render_compare_prototype.py \
  --doc-json $DATA/{m}/doc.json --align-json $DATA/{m}/align.json \
  --user-video $SP/p35/{m}/user.mp4 --ref-video $SP/p35/{m}/ref.mp4 \
  --audio-dir $SP/p35/{m}/audio --workdir $SP/p35/{m}/render \
  --out $SP/p35/{m}/out_{tag}.mp4 > $SP/p35/{m}/report_{tag}.json
```

kipup 만 `--moments-json $DATA/kipup/moments.json` 추가. {tag} = baseline(Task 1) / v7(Task 3). v7 의 elbow 만 `--text-override-json .planning/quick/260808-epy-phase-35-2-p35-pdshape-r01-5-v7/elbow_text_overrides.json` 추가. 리포트가 stdout 이므로 리다이렉트 필수([warn] 오염 방지 = 1-4 의 mp3 전수 assert).

**RIG_CMD 템플릿:** `$PY scripts/verify_render_prototype.py --mp4 $SP/p35/{m}/out_{tag}.mp4 --report $SP/p35/{m}/report_{tag}.json --workdir $SP/rig/{m}` — exit 0 = ALL PASS.

**UPLOAD_CMD 템플릿 (Task 3-5):** `AWS_PROFILE=sunity-motion aws s3 cp $SP/p35/{m}/out_v7.mp4 s3://sunity-motion-pilot-videos/proto/phase35/{key}_v3.mp4 --content-type video/mp4`

**이 세션에서 이미 검증된 사실 (재검증 불요, 그대로 신뢰):**
- `$SP/p35_volume/{7동작}/` = Pod 회수 JSON 16파일 (elbow·powerspin·pdshape·pdshapefault·peterpan 각 2, kipup·realupload 각 3). 활성 5슬롯 검증 PASS. pdshape·realupload 는 구버전 포맷(refKp 없음 — 벤치 슬롯, 렌더러가 refKp 를 선택 필드로 다룸).
- `$SP/p35/{motion}/user.mp4·ref.mp4` = S3 재다운로드 완료. `$SP/p35/{motion}/render/u30_1080·r30_1080` = 30fps/1080h 프레임 사전 추출 완료 → 렌더러 `--workdir $SP/p35/{motion}/render` 로 주면 캐시 인식.
- 폴 감지 프로브 PASS 4/4 (`$SP/pole_probe_report.json` + `$SP/pole_probe.py`): elbow user x=0.4992/cov 0.385 · ref x=0.5003/cov 0.440, pdshapefault user x=0.4996/cov 0.335 · ref x=0.4993/cov 0.440. 알고리즘 = 그레이스케일 수평 그래디언트 상위 8% 에지 → 컬럼 커버리지 → 프레임 중앙값 → 클러스터. PIL+numpy 만 (cv2 는 로컬 venv 에 **없음** — import 금지).
- doc criterion 실측 (계획 시점 확인 완료): elbow = r00 `angle_vs_reference__right_elbow` / r01 right_shoulder / r02 left_hip / r03 right_knee. pdshapefault = r00 left_elbow / r01 **right_elbow(팔 큐 — 손목 큐 아님)** / r02 left_shoulder / r03 left_knee. → belle 지시 "왼손 잡는 순간"은 팔 큐 + user 손목 폴접촉 조건으로 발동 설계 (task_requirements 의 분기 지침 확정분).
- 발동 여유 실측: elbow r00 — ref 창 내 right_elbow 폴 간격/몸통 min ≈ 0.01~0.02 (붙음), user 창 내 max ≈ 0.46 (conf≥0.5) → 폴-근접 발동 여유 큼. pdshapefault r01 — user left_wrist @1.22s 간격/몸통 = 0.254 (conf 0.66), ref left_wrist 창 [0, 2.93]s 에서 이탈(0.6~0.8) 후 재접촉 개시 후보 ≈0.8s 또는 ≈1.6s(0.011) 존재.
- S3 현재 상태: `proto/phase35/` 에 elbow(12.2MB)·kipup(4.0MB)·pdshape(11.0MB)·peterpan(6.1MB)·powerspin(6.0MB)·realupload 6키 존재 (08-08 00:28 업로드분 = v6).
- coachAudio 키 형식: `results/{uid}/{analysisId}/coach_audio_{recordId}.mp3` (recordId = `r00:angle_vs_reference__...` 전체, 콜론 포함) — doc.json `result.coachAudio.items[].key` 에 그대로 있음.
</context>

<tasks>

<task type="auto">
  <name>Task 1: 데이터 리포 영구화 + baseline 재현 렌더 (코드 수정 전 — STOP 게이트)</name>
  <files>.planning/phases/35-server-rendered-comparison-video/data/** (16 JSON + README.md), .planning/quick/260808-epy-phase-35-2-p35-pdshape-r01-5-v7/p35_audio.py</files>
  <action>
**1-1. 데이터 복사 (묶음 0):** `$SP/p35_volume/{motion}/` 의 align.json·doc.json(+kipup·realupload 는 moments.json)을 `$DATA/{motion}/` 로 복사 — 7동작 16파일, 약 4MB. verify/ 스틸(62MB)은 복사하지 않는다.

**1-2. `$DATA/README.md` 작성** (내용 필수 항목):
- 출처: RunPod pqe6uaw7mf8bh9 볼륨 `/workspace/p35`, 회수일 2026-08-08 (`p35_volume.tgz`).
- 검증 결과: 활성 5슬롯(elbow·powerspin·kipup·pdshapefault·peterpan) 기계검증 PASS. pdshape(correct)·realupload 2건은 구버전 포맷(refKp 없음) — 벤치 슬롯이라 무해, 렌더러도 refKp 를 선택 필드로 다룸.
- verify 스틸 87장(62MB)은 미커밋 — 재생성 = Pod 에서 `p35_extract_align.py --workdir /workspace/p35` 재실행 (한 줄).
- 영상 원본 S3 키 표: `p35_extract_align.py` JOBS dict 를 그대로 옮김 (user/ref 키 7쌍) + 산출 mp4 키 `proto/phase35/{elbow,powerspin,pdshape,kipup,peterpan}_v3.mp4` (pdshapefault 렌더가 pdshape_v3 키로 감 — 현행 매핑).
- align.json 스키마 1줄 요약 + RENDER_CMD 템플릿 (context 의 것을 옮김).
- "이후 렌더는 이 디렉터리를 입력으로 사용 (임시폴더 아님)" 명시.

**1-3. 데이터 커밋 (코드 커밋과 분리):** 작업트리에 기존 dirty 파일 존재 — `git add` 는 `$DATA` 경로만 명시적으로. 커밋 메시지: `feat(35): p35 정렬 데이터 리포 영구화 — Pod 볼륨 회수 7동작 16파일 (재부팅 소실 재발 방지)`.

**1-4. mp3 회수:** `p35_audio.py` 작성 (quick dir), `fetch` 서브커맨드 — 렌더 5슬롯(elbow·powerspin·kipup·pdshapefault·peterpan) 각각 `$DATA/{m}/doc.json` 의 `result.coachAudio.items[].key` 를 boto3(Session profile_name="sunity-motion")로 GET → `$SP/p35/{m}/audio/{rid}.mp3` (rid = recordId.split(':')[0]). **assert: 다운로드 수 == 그 doc 에서 렌더될 record 수** (atVideoSec 보유 record — kipup 은 align pairs/moments 주입분 포함). mp3 누락 record 는 renderer 가 조용히 freeze 를 떨궈 A2 리그가 못 잡으므로 여기서 fail-fast.

**1-5. baseline 렌더 5슬롯 (코드 무수정 HEAD):** context 의 RENDER_CMD 템플릿, {tag}=baseline, 5슬롯 순차 실행. 벤치 2슬롯(pdshape correct·realupload)은 렌더하지 않는다.

**1-6. 리그 5회 + v6 근사 재현 확인:** context 의 RIG_CMD 로 5슬롯 전부 exit 0 (ALL PASS). report_baseline.json 의 outDurationS 가 v6 근사치인지: elbow 66s · powerspin 32s · pdshapefault 59s · kipup 16s · peterpan 18s, 각 ±2s. kipup freeze userSec = 1.47 (±0.1) 확인.

**STOP 게이트:** 리그 FAIL 이나 길이 이탈 1건이라도 있으면 **코드 수정(Task 2) 진입 금지** — 원인(어느 슬롯·어느 항목·실측값)을 보고하고 종료. 회수 데이터가 승인 상태를 재현함이 실증되어야만 진행.
  </action>
  <verify>
<automated>cd /Users/kimtaesung/Dev/SunityMotion && ls .planning/phases/35-server-rendered-comparison-video/data/*/ | grep -c json # == 16; git show --stat HEAD 가 data/ 파일만 포함; 리그 5회 exit 0; python 원라이너로 길이 assert (report_baseline.json outDurationS vs {elbow:66,powerspin:32,pdshapefault:59,kipup:16,peterpan:18} ±2, kipup freezes[0].userSec 1.47±0.1)</automated>
  </verify>
  <done>16파일+README 커밋 완료(데이터만). mp3 전수 회수 assert PASS. baseline 5편 리그 ALL PASS + 길이 v6 근사 재현 + kipup 1.47 확인 — 승인 상태 재현 실증. report_baseline.json 5개 보존.</done>
</task>

<task type="auto">
  <name>Task 2: 렌더러 수정 — 엘보 폴-근접 문법 + pdshapefault r01 그립 짝 + 문구 오버라이드·재합성</name>
  <files>backend/scripts/render_compare_prototype.py, .planning/quick/260808-epy-phase-35-2-p35-pdshape-r01-5-v7/elbow_text_overrides.json, .planning/quick/260808-epy-phase-35-2-p35-pdshape-r01-5-v7/p35_audio.py</files>
  <action>
모든 수정은 기존 코드 관례 승계: 한국어 why 주석 + belle 라운드 인용("belle 08-08 마감: 폴에 가까운 부분에서 차이가 나는 것 — 각도를 재달라는 게 아님" / "정은지도 왼손 폴 잡는 순간으로"), **criterion/데이터 판정만 — 동작명 분기 금지**, fail-closed. 리그(verify_render_prototype.py)는 무수정.

**2-1. 폴 축선 감지 이식:** `$SP/pole_probe.py` 의 column_coverage/detect 로직을 렌더러에 함수로 이식 (`_detect_pole(frame_dir, align, side) -> dict | None`). 입력 = 사전 추출된 30fps 프레임 디렉터리에서 균등 샘플 12~20장 (PIL+numpy, cv2 금지). 반환 = xNorm·halfWidthNorm·coverage.
- 그립 프라이어: align 의 양 손목(신뢰≥0.5 프레임) x 중앙값이 후보와 후보폭 3배 이내인 후보 우선, 없으면 최고 커버리지 후보.
- fail-closed: 최종 후보 커버리지 < 0.25 → None (폴 표시 생략 — 기존 링 마커 폴백). 감지 결과는 workdir 에 JSON 캐시 가능(재량).
- 구조 변경: render() 에서 extract_frames 호출을 build_timeline 앞으로 이동(캐시 멱등이라 안전)하고, user/ref 폴 감지 결과를 build_timeline 에 전달.

**2-2. 좌표→물리 스케일 헬퍼:** kp 정규화 좌표를 align userSize/refSize 로 픽셀 환산, torso_px = 어깨중점-힙중점 거리, gap_px = |joint_x − pole_x|×W. ratio = gap/torso. **임계는 전부 구조 유도(픽스처 curve-fit 금지):** τ_prox = pole_halfwidth_px/torso_px + 0.15 (팔꿈치는 뼈가 폴에 직접 닿음), τ_grip = pole_halfwidth_px/torso_px + 0.20 (손이 폴을 쥐면 손목점은 축에서 손폭만큼 벗어남 — 해부학 오프셋).

**2-3. 판정 우선순위 (angle_vs_reference 관절 큐, refKp 보유 align 한정):** ① 폴-근접(pole-prox) → ② 그립(grip) → ③ 기존 가중 짝(_weighted_repair_pair). 이 순서 근거를 주석으로: elbow r00 은 ref 팔꿈치가 폴에 붙어(0.01~0.02) 폴-근접이 선점, pdshapefault r01 은 ref 팔꿈치 비부착이라 ①불발 → ②발동 — 데이터가 가른다.

**① 폴-근접 (belle 마감 교정, 묶음 1):**
- 발동: criterion 이 `angle_vs_reference__{left,right}_elbow` AND 양 패널 폴 감지 성공 AND ref 창(정렬곡선 curve(atVideoSec)±2.5s, conf≥0.5 프레임) 내 팔꿈치 ratio min ≤ τ_prox AND user 창(atVideoSec±2.5s, conf≥0.5) 내 ratio max ≥ ref_min + 0.15 (유의미 마진, 몸통 단위).
- 표시 순간 (미세조정 1차 "양쪽 각자의 피크" 원칙 승계, 창 제한으로 엉뚱한 국면 방지): ut = user 창 내 간격 **최대** 프레임(자기 간격이 가장 잘 보이는 국면), rt = ref 창 내 간격 **최소** 프레임(폴에 붙은 대표 국면). pair_src = `"align-pole"`. 이 큐는 가중 짝 호출 생략(순간·짝 모두 폴 문법 소유). 0.15s 승인 짝 보호 규칙의 예외 — 예외는 **판정 조건 성립 한정**(record/동작 한정 아님), belle 명시 교정이 근거임을 주석으로.
- 그리기 (freeze payload `pole_viz`, 양 패널 대칭): 폴 축선 = 전체 높이 가는 세로선(BRAND 반투명, 예 alpha≈140·width≈3×S) + 팔꿈치 링(기존 신뢰 문법 승계: ≥0.5 solid / ≥0.35 est 점선 / 미만 링 생략) + 팔꿈치→폴 **수평 간격 브래킷**(팔꿈치 y 높이에서 팔꿈치 x↔폴 x 수평선 + 양끝 짧은 세로 틱). **수치 없음** — 수치 배지 철회 유지, 수치는 벌림각 전용(belle 4차 문법 불변). both-or-neither: 한쪽 패널이라도 폴/팔꿈치 신뢰 미달이면 pole_viz 전체 None → 기존 링 마커 폴백 (fault_zoom 계약 승계).
- report freeze 항목에 poleViz 요약(user/ref 성립 여부 + poleX) 방출 — diff 관측 가능성.

**② 그립 (belle "정은지도 왼손 잡는 순간으로", 묶음 2):**
- 발동 (전부 성립 시): 팔 큐(criterion 관절이 elbow/shoulder/wrist) AND 양 패널 폴 감지 성공 AND ①미발동 AND user 손목(좌/우 중 conf≥0.5) 중 cue 순간 ratio ≤ τ_grip 인 쪽 존재(둘 다면 ratio 작은 쪽) AND **user 그 손목의 접촉 개시가 |t−atVideoSec| ≤ 0.75s 안에 존재**("그 순간이 잡는 순간"임을 데이터로 — elbow 동작처럼 손이 처음부터 계속 잡고 있는 큐에 오발동해 승인 장면을 깨는 것을 구조적으로 차단) AND ref 같은 side 손목의 접촉 개시가 ref 창(curve(atVideoSec)±2.5s) 안에 존재.
- 접촉 개시 정의(user/ref 공통): ratio 시계열(conf≥0.5, 미달 프레임 NaN, 3프레임 중앙값 필터 — 15fps 지터 1프레임 스파이크 억제)에서 직전 ratio > 2×τ_grip(이탈 상태)이었다가 처음 ratio ≤ τ_grip 로 들어와 3프레임(0.2s) 이상 유지되는 프레임. 창 시작부터 이미 접촉인 구간은 개시 아님(이탈→재접촉 첫 순간). 실측 앵커: ref left_wrist 는 0.4~0.6s 이탈(0.6~0.8) 후 재접촉 — 개시 후보 ≈0.8s 또는 ≈1.6s, 중앙값 필터·유지 조건이 판별.
- 성공 → rt = ref 개시 프레임/afps, pair_src = `"align-grip"`, ut 는 atVideoSec 유지(user 장면은 belle 가 반려하지 않음). 표시는 기존 링 마커 문법 그대로(짝만 교정 — 묶음 2 범위).
- 실패(개시 못 찾음/신뢰 미달/user 개시 부재) → 기존 가중 짝 유지(fail-closed) + stderr 로그. **이 경우 SUMMARY 에 "belle 지시 미충족(사유)" 를 명기 — 조용한 생략 금지.**

**2-4. 발동 집합 프로브 (필수 선행 게이트, 렌더 전):** 5슬롯 × 전 record 에 대해 ①②③ 어느 경로가 잡히는지 표로 출력하는 dry-run(작은 스크립트나 renderer --probe 플래그, 재량). **기대 = 정확히 {elbow r00: align-pole, pdshapefault r01: align-grip}, 나머지 전부 기존 경로.** 초과 발동(예: pdshapefault r00 left_elbow 가 ①에 걸림) 시: 구조적 근거가 있는 조임(예: user-max 마진을 절대+상대 이중으로)만 허용 — 동작명 분기·픽스처 맞춤 금지. 조임으로 해소 불가면 STOP 하고 발동 표와 선택지를 보고 (승인 항목 보호가 최상위 — "변경은 엘보 팔꿈치 큐 표시와 pdshapefault r01 짝에 국한").

**2-5. 문구 오버라이드 (lockstep):**
- 렌더러에 `--text-override-json` 선택 인자 추가: rid→문장 dict. build_timeline 에서 text = overrides 에 rid 있으면 그 문장, 없으면 기존 speech_text(rec).
- `elbow_text_overrides.json` (quick dir): `r00` = "폴에 붙었나" 계열 한국어 문장. 문형 = pipeline `_coach_audio_speech_text` 규약 미러: **결함문 + 마침표 경계 + 행동문** (예시 구조: "팔꿈치가 폴에서 떨어져 있어요. 팔꿈치를 폴에 붙여 몸을 고정해 보세요." — 최종 문구 재량, 각도 언급 금지, 이모지 금지). 이 파일이 렌더 자막과 Polly 합성의 **공용 단일 테이블** — 자막=음성 lockstep 이 구조로 보장된다.
- `p35_audio.py synth` 서브커맨드: 같은 JSON 을 읽어 해당 rid 만 Polly 재합성 — pipeline `_synthesize_coach_audio_items` 미러: VoiceId Seoyeon, Engine neural, LanguageCode ko-KR, OutputFormat mp3, boto3 Session(profile_name="sunity-motion") → `$SP/p35/elbow/audio/r00.mp3` 덮어쓰기(다른 rid 무접촉).

**2-6. 절정 사이각 긴장 판단 기록:** 엘보 doc records 4건(r00 팔꿈치→폴-근접 이동 / r02 left_hip 가위스플릿 사이각 표시 유지 / r01 어깨 / r03 무릎)을 근거로, "사이각 수치(179 vs 173)가 '차이 있다' 문장과 어긋나던 긴장"이 팔꿈치 큐의 폴-근접 이동으로 해소되는 구조인지 판단해 SUMMARY 에 기록 (수치 표시는 r02 벌림 계열에만 남고, 팔꿈치 차이는 이제 각도가 아니라 간격 브래킷으로 말한다 — 가 기대 구조).

**2-7. 코드 커밋:** `git add` 는 렌더러 + quick dir 산출물만 명시적으로. 메시지: `feat(35): 미세조정 2차 — 엘보=폴 근접 문법(축선·간격 브래킷·문구 lockstep)·pdshape r01 왼손 그립 개시 짝 (belle 08-08 마감 교정)`.
  </action>
  <verify>
<automated>$PY -c "import ast;ast.parse(open('/Users/kimtaesung/Dev/SunityMotion/backend/scripts/render_compare_prototype.py').read())" && grep -c "align-pole\|align-grip" backend/scripts/render_compare_prototype.py # >= 2; grep -c "import cv2" backend/scripts/render_compare_prototype.py # == 0; 발동 프로브 출력 == 기대 집합 {elbow r00: pole, pdshapefault r01: grip}; p35_audio.py synth 후 elbow r00.mp3 mtime 갱신 + mp3 길이 출력(오버라이드 테이블 파일에서 합성됐음을 synth 로그로 확인)</automated>
  </verify>
  <done>렌더러가 폴 감지·폴-근접 표시·그립 짝·문구 오버라이드를 데이터 판정으로 수행(동작명 분기 0, cv2 0). 발동 프로브 = 정확히 기대 2건. elbow r00.mp3 재합성 완료(오버라이드 문장, Seoyeon/neural). 코드 커밋 완료. 사이각 긴장 판단 메모 확보.</done>
</task>

<task type="auto">
  <name>Task 3: v7 재렌더 · 리그 ALL PASS · diff 게이트 · S3 덮어쓰기 · 증거 스틸</name>
  <files>.planning/quick/260808-epy-phase-35-2-p35-pdshape-r01-5-v7/diff_reports.py (신규), $SP/p35/{m}/out_v7.mp4·report_v7.json, $SP/evidence/*.jpg (리포 밖)</files>
  <action>
**3-1. v7 렌더 5슬롯:** context 의 RENDER_CMD, {tag}=v7. elbow 만 `--text-override-json` 추가(context 템플릿 명기). 산출 mp4 는 리포 밖(scratchpad).

**3-2. 리그 5회:** context 의 RIG_CMD 로 5슬롯 전부 exit 0 (ALL PASS 아니면 업로드 금지 — D-00 "기계 판정 선행, belle 는 심사만").

**3-3. diff 게이트 (`diff_reports.py` 작성·실행):** report_baseline.json ↔ report_v7.json 을 rid 단위로 비교, 다음을 assert:
- powerspin·kipup·peterpan: 전 freeze 행(userSec·refSec·pairSrc·freezeS·text) 동일(수치 ±0.02) + outDurationS ±0.1. **kipup r00 userSec = 1.47 (±0.1) 명시 assert** (피크 퇴행 즉시 검출 — 미세조정 1차의 실측 철회 선례).
- pdshapefault: r01 만 refSec 변경 + pairSrc == "align-grip". r00·r02·r03 행 불변. outDurationS ±0.1 (rt 교체는 길이 무영향).
- elbow: r00 만 변경 — pairSrc == "align-pole", poleViz user/ref 모두 성립, text == 오버라이드 문장, freezeS 변경 = 새 mp3 길이 반영, ut/rt 는 각각 atVideoSec±2.5s / curve±2.5s 창 안. r01·r02·r03 행 불변. outDurationS 차이는 새 r00 mp3 길이차 + 0.3 이내.
- 위 외 diff 1건이라도 있으면 FAIL → 원인 수리 후 재렌더(수리 커밋 별도), 게이트 재통과까지 업로드 금지.

**3-4. 증거 스틸 (belle 보고용) + 눈확인:** ffmpeg 로 elbow v7 의 r00 freeze 중앙(voiceStartOutS+1.0s) 1프레임 → `$SP/evidence/elbow_r00_pole_freeze.jpg`, pdshapefault v7 의 r01 freeze 중앙 1프레임 → `$SP/evidence/pdshape_r01_grip_freeze.jpg`. **두 이미지를 Read 로 직접 열어** 확인: ① 엘보 — 양 패널 폴 축선+팔꿈치 링+간격 브래킷 보이고 수치 배지 없음, 기준 팔꿈치는 폴에 붙고 user 는 떨어져 "차이"가 한눈에 읽힘 ② pdshapefault — 기준 패널이 정은지 **왼손이 폴을 잡는 순간**으로 보임. 아니면 FAIL 취급(코드 통과 ≠ 확인 — 산출물 직접 열어보기 원칙). 그립 개시 후보(≈0.8s vs ≈1.6s) 중 어느 것이 선택됐고 눈으로 타당한지 SUMMARY 에 기록.

**3-5. S3 덮어쓰기 (같은 키 = belle 기존 presigned 링크·QuickTime 창 그대로 유효):** 3-2·3-3·3-4 전부 PASS 후에만, context 의 UPLOAD_CMD 로 5키. 매핑: elbow→elbow_v3 · powerspin→powerspin_v3 · **pdshapefault→pdshape_v3(현행 매핑 유지)** · kipup→kipup_v3 · peterpan→peterpan_v3. realupload_v3 는 무접촉. 업로드 후 `aws s3 ls` 로 5키 타임스탬프·크기 갱신 확인.

**3-6. 마무리:** diff_reports.py 를 quick dir 에 커밋(코드 커밋에 포함했거나 별도 소커밋 — 어느 쪽이든 데이터/코드 분리 원칙 유지). 상태 보드 아티팩트(정본, https://claude.ai/code/artifact/f8630d0f-c07f-4d82-943a-0fa272900b5f)를 v7 상태로 갱신 — 이 환경에서 갱신 불가하면 SUMMARY 에 "보드 갱신 필요" 를 명기(조용한 생략 금지). SUMMARY 에 임계값 실사용치(τ_prox/τ_grip/마진)·발동 표·긴장 판단(2-6)·그립 fail-closed 발생 여부·증거 스틸 경로·mp4 5키를 기록.
  </action>
  <verify>
<automated>RIG_CMD 5슬롯({tag}=v7) 전부 exit 0; $PY .planning/quick/260808-epy-phase-35-2-p35-pdshape-r01-5-v7/diff_reports.py exit 0 (kipup 1.47 assert 포함); AWS_PROFILE=sunity-motion aws s3 ls s3://sunity-motion-pilot-videos/proto/phase35/ 에서 5키 크기·시각 갱신 + realupload_v3 불변; ls $SP/evidence/*.jpg # == 2</automated>
  </verify>
  <done>v7 5편 리그 ALL PASS + diff 의도 변경 2건 국한 + kipup 1.47 불변. 증거 스틸 2장을 직접 열어 폴-근접 표시·왼손 그립 순간 눈확인. S3 5키 덮어쓰기 완료(realupload 무접촉). SUMMARY 판단 기록 완비.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| 로컬→S3 (sunity-motion profile) | mp3 GET·mp4 PUT — 기존 자격증명, 신규 시크릿 0 |
| 로컬→Polly | 합성 텍스트 1건 — 본문 외 데이터 미전송, 로그에 시크릿 미기록 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-35q-01 | Tampering | proto/phase35 키 덮어쓰기 | mitigate | 리그 ALL PASS + diff 게이트 통과 전 업로드 금지, realupload_v3 무접촉 assert |
| T-35q-02 | Info Disclosure | doc.json 커밋 (uid 포함) | accept | 기존 관례(quick dir 에 doc/스윕 산출물 다수 기커밋), 파일럿 내부 계정 |
| T-35q-SC | Tampering | 패키지 설치 | n/a | 신규 패키지 설치 0 (기존 venv 의 PIL/numpy/boto3 만 사용, cv2 금지) |
</threat_model>

<verification>
- 데이터: `$DATA` 16 JSON + README 커밋, git show 로 데이터 커밋에 코드 미포함 확인.
- baseline: 리그 5×PASS + 길이 v6 근사(±2s) — 실패 시 코드 미진입(STOP 준수 여부가 곧 검증).
- 코드: 판정용 동작명 리터럴 grep 0 (`grep -nE '"(elbow|kipup|powerspin|peterpan|pdshape)"' backend/scripts/render_compare_prototype.py` 빈 출력 — JOBS 류 데이터 표도 없어야 함), cv2 import 0, 리그 파일 무접촉 (`git diff HEAD -- backend/scripts/verify_render_prototype.py` 빈 출력).
- v7: 리그 5×PASS + diff_reports.py PASS + 증거 스틸 2장 눈확인 + S3 5키 갱신.
</verification>

<success_criteria>
- belle 가 기존 링크로 여는 5편이 v7: 엘보 팔꿈치 정지 = 폴 축선·간격 브래킷·"폴 근접" 문구(자막=음성), pdshape(fault) r01 기준 정지 = 정은지 왼손 폴 그립 순간. 나머지 승인 장면 전부 그대로.
- 렌더 입력 데이터가 리포에 있어 어떤 환경에서든 이 5편을 재현 가능.
- 기계 판정(리그+diff)이 belle 심사에 선행 — 전항목 PASS 아니면 전달 없음(D-00).
</success_criteria>

<output>
완료 시 `.planning/quick/260808-epy-phase-35-2-p35-pdshape-r01-5-v7/260808-epy-SUMMARY.md` 작성 — 임계값 실사용치, 발동 표, 그립 개시 선택 근거(0.8s vs 1.6s), 사이각 긴장 판단, fail-closed 발생 여부, 증거 스틸 경로, S3 키 5개, 커밋 해시(데이터/코드) 포함.
</output>

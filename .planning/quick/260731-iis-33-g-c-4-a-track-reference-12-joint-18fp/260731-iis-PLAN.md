---
phase: quick-260731-iis
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/scripts/reprocess_reference_motions_phase4.py
  - backend/tests/phase33/test_candidate_staging.py
  - .planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/measure_ref_state.py
  - .planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/write_ref_kp_report.py
  - .planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/reanalyze_render_docs.py
  - .planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/sweep_real_ref.py
  - .planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/260731-iis-SUMMARY.md
  - .planning/phases/33-result-trust-recovery/33-G-MOCKUP-DIFF.md
autonomous: true
requirements: [C4-1, C4-2, C4-5, S8, S10, S5, S22, F-3, S6, FLIP-DEF]

must_haves:
  truths:
    - "기준 11동작의 top-level referenceKeypointReport 가 18.0fps · 12관절 · frames == 그 doc 의 anglesFrames 로 교체된다 (11/11 all-or-nothing)"
    - "교체 전후로 채점 8필드(angles·anglesJointKeys·anglesFrames·joints3d·joints3dKeys·joints3dFrames·coordDim·space) 해시가 11/11 불변이다"
    - "activeVersion 11/11 불변 + reference/_release.activeCandidate 불변 — 릴리스 포인터 무접촉"
    - "쓰기 전 원본 백업이 존재하고 restore 왕복이 1건에서 실증된다 (되돌릴 수 있다)"
    - "flip 시 표시 보고서가 채점 타임베이스와 함께 넘어간다 — mirror 소스를 실측한 뒤 실제로 동작하는 형태로 넣는다"
    - "기준측 좌표가 실물일 때 무릎·팔꿈치 각도 베이크가 켜지는지를 등재 동작 전건에서 수치로 판정한다 (켜지든 안 켜지든 통과율로 설명)"
    - "이미 PASS 인 S8 어깨·힙 각도 베이크와 S9 정중앙 crop 과 S10 다리 사이각이 깨지지 않는다"
    - "S10 을 합성이 아닌 실 doc PNG 위에서 판정한다 — 선 2개 + 호 + 해부학적 정합"
    - "규칙이 데이터로만 키잉된다 — fault_zoom 동작명 분기 0 유지, 등재 동작 전건 확인"
    - "belle 에게 Pod 를 언제 꺼도 되는지 태스크 단위로 명시된다"
  artifacts:
    - path: ".planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/measure_ref_state.py"
      provides: "reference 11 doc 의 타임베이스·해시·릴리스 포인터 실측 (읽기 전용)"
    - path: ".planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/refkp_before.json"
      provides: "쓰기 전 BEFORE 실측 (anglesFrames / 두 보고서 fps·frames·joints / 해시 / activeVersion / _release / candidate)"
    - path: ".planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/reference-kp-18fps.json"
      provides: "Pod RTMW 18fps 12관절 추출 산출 11/11"
    - path: ".planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/write_ref_kp_report.py"
      provides: "top-level referenceKeypointReport 단일 필드 교체 + 백업/복구 + 게이트 + 사후 재조회"
    - path: ".planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/refkp_backup.json"
      provides: "교체 전 원본 11건 (복구 소스)"
    - path: ".planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/refkp_after.json"
      provides: "교체 후 재조회 실측 + 해시 대조 결과"
    - path: "backend/scripts/reprocess_reference_motions_phase4.py"
      provides: "_flip_active_pointer mirror 에 referenceKeypointReport 편입 (33-07 flip 잠복 버그 방어)"
      contains: "referenceKeypointReport"
    - path: ".planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/sweep_real_ref.py"
      provides: "등재 동작 전건 스위프 — 기준측만 실 12관절 보고서로 교체 (f5h 하네스 계보)"
    - path: ".planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/sweep_out/real-ref/summary.json"
      provides: "각도 베이크 drawn/omitted 사유별 집계 + 대칭 + 정중앙 배율 + 동작명 분기 0"
    - path: ".planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/zoom_after/"
      provides: "실 doc 재산출 faultZoom PNG (S10 해부학적 정합 판정 재료)"
  key_links:
    - from: "top-level reference/{id}.referenceKeypointReport"
      to: "pipeline app.py:5435 ref.get referenceKeypointReport"
      via: "_REFERENCE_CONSUMER_FIELDS 미포함 → candidate overlay 를 타지 않는 top-level 직독"
      pattern: "referenceKeypointReport"
    - from: "referenceKeypointReport.frames"
      to: "top-level anglesFrames"
      via: "mode1 DTW ref 인덱스 공간 = ref angles 공간 = rep 공간 (dtw_ref_fps 미전달 = None)"
      pattern: "anglesFrames"
    - from: "_flip_active_pointer mirror_fields"
      to: "referenceKeypointReport"
      via: "flip 시 표시 보고서를 채점 타임베이스와 동반 이동"
      pattern: "referenceKeypointReport"
---

<objective>
33-G §C-4 **A-트랙** — 기준 라이브러리의 **표시용** keypoint 보고서를 실 12관절로 갈아끼우고,
그 위에서 crop·각도 베이크를 전수 재생성한 뒤, S10 을 **실 doc** 에서 판정한다.

범위 = §C-4 5항목 중 **1 → 2 → 5** 뿐이다 (belle 승인).
- 3번(어깨·팔꿈치 일러스트 신규 생성) = **제외** — 별도 사이클.
- 4번(9모션 앵커 주석) = **조건부** — 1번이 들어오면 대부분 불필요. 2번 산출로 남은 필요분만
  판정하고 **값 채우기는 하지 않는다**.
- 일괄 OTA · belle 확인 ③ = 이 플랜 **밖**(D-45).

Purpose: 무릎·팔꿈치 각도 베이크가 원리적으로 못 켜지던 유일한 원인(기준 8관절)을 없애고,
S10 다리 사이각을 합성이 아닌 실 데이터 위에서 판정한다.
Output: Firestore top-level 표시 필드 교체 11/11 + flip 방어 + 전수 스위프 + 실 doc 재산출 PNG
+ 33-G 재채점 갱신 + SUMMARY(Pod 정지 시점 포함).
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/phases/33-result-trust-recovery/.continue-here.md
@.planning/phases/33-result-trust-recovery/33-G-MOCKUP-DIFF.md
@.planning/quick/260731-f5h-33-g-c-3-d-1-split-angle-leg-angle-omitt/260731-f5h-SUMMARY.md
@.planning/quick/260731-f5h-33-g-c-3-d-1-split-angle-leg-angle-omitt/sweep_leg_angle.py
@.planning/phases/33-result-trust-recovery/evidence-refkp/ref_ankle_elbow_conf.txt
@backend/scripts/extract_reference_keypoint_reports.py
@backend/scripts/reprocess_reference_motions_phase4.py
@backend/shared/python/sunity_shared/firestore_admin.py
@backend/shared/python/sunity_shared/analysis/fault_zoom.py
</context>

<verified_facts>
아래는 **오케스트레이터가 직접 코드를 열고 명령을 돌려 확인**한 것이다. 재조사 금지.

**Pod (셋업 완료, 살아 있음)**
- ID `gwa4jn3lq4tb21` · RTX 4090 24GB · EU-RO · Network Volume `/workspace` 계보 유지
- SSH(SCP 가능): `ssh -i ~/.ssh/id_ed25519 -p 17987 root@213.173.99.14`
- Proxy: `https://gwa4jn3lq4tb21-8000.proxy.runpod.net`
- Pod HEAD = `a6cb91c` = 로컬 HEAD. `/health` 가 `commitSha=a6cb91cd`, `pipeline_loaded:true`,
  poseEngine `RTMWPoseEngine`, recognizer `GeminiTechniqueRecognizer`
- SSM `/sunity/motion/runpod-analyze-url` **v23** + Lambda `sunity-motion-pilot-pipeline` env 동기화 완료
- 토큰 스모크 무토큰 401 / 유토큰 422 PASS
- **Pod→S3 서울 GET 회복** — `reference/ref-climb.mp4` 3MB 레인지 GET **1396 KB/s** 실측.
  `_s3stage` 우회와 로컬 프록시는 더 이상 필수가 아니다(`/workspace/_s3stage` 735M 는 남아 있음).
- 셋업 스크립트는 repo 가 아니라 볼륨 로컬: `/workspace/bootstrap_full.sh`,
  `/workspace/start_server.sh`, `/workspace/aws_env.sh`. **AWS CLI 는 Pod 에 없음 — boto3 사용.**

**필드 구조 (코드 직접 열람)**
- `firestore_admin._REFERENCE_CONSUMER_FIELDS`(2001행)에 **`referenceKeypointReport` 는 없다.**
  `get_reference_motion` 은 candidate 문서의 consumer 필드만 top-level base 위에 overlay 하므로
  `referenceKeypointReport` 는 **항상 top-level base 에서** 읽힌다.
- 백엔드 소비 지점 = `backend/functions/pipeline/app.py:5435` (mode1 fault_zoom 의 `ref_report`).
- **앱도 top-level 을 직독한다** — `app/src/lib/referenceMotions.ts:107` 이 `reference/{id}` 문서의
  `referenceKeypointReport` 를 읽고 `result.tsx:1556 / 2523 / 3234` 가 기준 오버레이에 쓴다
  (`docs/contract.md:1607` — analysis doc 에 mirror 안 함). **즉 이 교체는 OTA 없이도 앱 화면에
  즉시 반영된다.** T2 의 위험·롤백 절이 이것을 다룬다.
- `_flip_active_pointer.mirror_fields`(459~472행)에 `referenceKeypointReport` **누락** = 33-07 잠복 버그.
- `_release_doc_hash`(80행) = 채점 8필드 content hash. `_HASH_CONSUMER_FIELDS`(73행) 가 그 8필드.

**타임베이스 (이번 작업의 핵심 — 코드 직접 열람)**
- mode1 은 `_render_fault_zoom(...)` 을 **`dtw_ref_fps` 없이** 호출한다(app.py:3257) → `None` →
  fault_zoom 은 **DTW ref 인덱스가 `ref_report` 의 fps 공간에 산다고 가정**한다(app.py:2948).
- DTW ref 인덱스의 실제 출처는 `ref["angles"]` 공간이다(app.py:5376 `_deviation_against`).
- 따라서 **`referenceKeypointReport` 의 프레임 수는 그 doc 의 `anglesFrames` 와 같아야 한다.**
  이것이 fps 라벨보다 강한 불변식이다(같은 추출 fps 면 `anglesFrames == report.frames`).
- mode3 는 반대 이유로 `dtw_ref_fps=_pipeline_frame_fps()` 를 **명시**한다(app.py:3397) — prev 보고서가
  18fps 로 저장되는데 prev angles 는 9fps 라서. 이 주석이 "타임베이스 불일치 = D2 재현"의 근거다.
- `fault_zoom.ref_display_frame_index` docstring(806~840행) 실측 기록:
  현행 top-level `referenceKeypointReport`(ref-elbow-twist-sister) = **329프레임@18fps, "raw 매 2프레임
  샘플"** 이고 렌더러의 9fps 추출은 220프레임 → 배율 4/3 보정이 걸려 있다. 같은 docstring 이
  **"올바른 재처리 ref 면 rep9_n == ref_video_n → 배율 1.0 → identity"** 라고 적어 놓았다.
  프로덕션 추출기로 18fps 재추출하면 배율이 1.0 으로 정합될 **가능성**이 있다 — 단정 금지, 측정 대상.

**go/no-go = GO** (`evidence-refkp/ref_ankle_elbow_conf.txt`, candidate `phase33-cm3-run1`, 11/11 J=12).
게이트 통과율 최저 = `ref-elbow-twist-sister` L.ankle 0.364, `ref-pdshape` L.ankle 0.396,
최고 = `ref-sideway-spin` 0.965. **약하다고 동작을 빼지 말 것** — conf 게이트가 프레임 단위로 거른다.
다만 그 두 동작은 판정에서 별도 컬럼으로 볼 것.

**§C-3 D-1 (직전 완료, main `f05bc98d`)** — `_leg_line_pts(in_crop=)` 로 다리 끝을 ankle→knee 순회.
합성 스위프 0/10 → 10/10. **한계 = 기준 좌표가 합성** → 실 doc 판정이 이 플랜 몫(T5).

**로컬 환경 (직접 실행 확인)**
- 사용 가능: `PIL` · `numpy` · `firebase_admin` · `boto3` · `yaml` · `ffmpeg`(/opt/homebrew/bin)
- **없음: `imageio` / `imageio-ffmpeg`** → 로컬에서 `FfmpegFrameExtractor` 를 못 쓴다.
  T4 스위프는 f5h 하네스처럼 **정지 이미지 배경**을 쓰고 비디오 추출을 하지 않는다.
  **신규 패키지 설치 금지** (T-iis-SC).
- Firestore 로컬 접근 = 레포 루트 `firebase-sa.json`
  (선례 = `evidence-refkp/measure_ref_ankle_elbow_conf.py`).

**f5h 하네스 재사용 지점**
- `sweep_leg_angle.py` 의 `_USER_KP` 는 **12관절**(elbow·ankle 포함), `_REF_KP` 는 **8관절**(현행 기준 형상).
- 렌더 엔트리 = `fz.build_fault_zoom_comparisons(u_frames, r_frames, user_rep, ref_rep, ...)`.
- 보고서 좌표는 **정규화 [0,1]** 이라 배경 이미지와 무관하게 그릴 수 있다.
- 등재 동작 = `backend/judging_data/criteria/*.yaml` glob 파생(하드코딩 0, 현재 10).
  기준 라이브러리는 11 — `ref-combo` 는 criteria 미보유. **11 과 10 을 섞어 쓰지 말 것.**

**faultZoom PNG S3 키** = `results/{uid}/{analysis_id}/zoom_{criterion}.png`
(advisory = `zoom_adv_` 접두), 버킷 `sunity-motion-pilot-videos` (app.py:3066).
</verified_facts>

<locked_spec>
설계 재논의 금지(repair-cycle-no-rediscussion). 스펙 = 승인 목업 7R + `.continue-here.md` §C-4.
단 **데이터가 결정과 안 맞으면 그건 재논의가 아니라 보고**다 — 반드시 올린다
(evidence-outranks-prior-decisions).

**L-1. 점수 무접촉 경로 (확립됨 — 이 경로를 벗어나지 말 것)**
Firestore 쓰기 허용 범위는 정확히 두 가지다.
  (a) `reference/{id}` **top-level `referenceKeypointReport` 필드 하나** (`set(merge=True)`).
  (b) T3 재분석이 **파이프라인 정상 경로로** 쓰는 `users/{uid}/analyses/{id}` (백업 선행).
그 외 일체 금지. 특히 `angles` / `anglesJointKeys` / `anglesFrames` / `joints3d` 계열 / `coordDim` /
`space` / `activeVersion` / `reference/_release` / `versions/*` 에 **쓰면 즉시 실패**다.

**L-2. GATE-A (타임베이스 정합) — 쓰기 전 all-or-nothing**
11/11 전건이 아래를 동시에 만족할 때만 쓴다. 하나라도 어긋나면 **쓰기 0 + 보고**.
  - `report.fps == 18.0`
  - `len(report.joints) == 12`
  - `report.frames == 그 doc 의 top-level anglesFrames`  ← fps 라벨보다 강한 불변식
  - `len(report.data) == frames*joints*2` AND `len(report.confidence) == frames*joints`
  - NaN/inf 0
  - `firestore_admin._validate_keypoint_report` 통과

**L-3. GATE-B (점수 무접촉 증명) — 쓰기 후**
  - `_release_doc_hash`(reprocess 스크립트에서 **import**, 복제 금지)로 뜬 채점 8필드 해시가
    BEFORE == AFTER, **11/11**
  - `activeVersion` 11/11 BEFORE == AFTER
  - `reference/_release.activeCandidate` BEFORE == AFTER

**L-4. GATE-C (전제 붕괴 감지) — 쓰기 전**
`reference/_release.activeCandidate` 가 **세팅돼 있으면 쓰지 말고 중단·보고**한다.
그 경우 `get_reference_motion` 이 해석하는 `angles` 가 candidate 것이라 18fps 표시 보고서는
정합이 아니다(L-2 의 frames 대조가 자동으로 이것을 잡지만, 사유를 분명히 남길 것).

**L-5. flip 방어**
`_flip_active_pointer.mirror_fields` 에 `referenceKeypointReport` 를 편입한다.
**단 `payload.get(...)` 1줄이 실제로 값을 싣는지 먼저 측정**할 것 —
`_reprocess_one` 산출 payload 의 `REQUIRED_KEYS`(`_validate_payload_schema`)에는
`referenceKeypointReport` 가 **없고**, 그 필드는 `backfill_reference_downstream.py` 가 candidate
문서에 나중에 MERGE 한다. 측정 결과가:
  - payload 에 있다 → `payload.get("referenceKeypointReport")` 1줄로 끝.
  - payload 에 없다 → **1줄은 no-op** 이다. 그대로 두면 "방어했다"가 거짓이 된다.
    → candidate 버전 문서에서 읽어 폴백하는 형태(5줄 이내)로 **실제로 동작하게** 만들고,
      왜 1줄이 아니었는지 SUMMARY 에 측정치와 함께 적는다.
**flip 자체는 Phase 34 몫 — 이 플랜에서 flip 하지 말 것.**

**L-6. 항목 4 (9모션 앵커 주석) 처리**
값 채우기 금지. T4 스위프 산출로 "1번이 들어온 뒤에도 주석이 필요한 criterion 이 남는가"만
표로 판정하고, 남으면 목록만 §C-4 잔여로 넘긴다.

**L-7. 실패 시 태도**
게이트가 걸리면 임계를 조정하거나 baseline 을 재캡처하지 말 것(calibration-source-hard-gate).
정지하고 수치와 함께 보고한다.
</locked_spec>

<pod_lifecycle>
belle 지시: **"Pod 꺼도 되는 시점을 분명히 말해달라."**

| 태스크 | GPU/Pod | 이유 |
|---|---|---|
| T1 기준 18fps 12관절 추출 | **필요** | RTMW 추론(CUDA). 로컬은 imageio 조차 없음 |
| T2 flip 방어 + Firestore 교체 | 불필요 | 로컬 firebase_admin 읽기·쓰기만 |
| T3 실 doc 재산출 | **필요** | 파이프라인 전체(RTMW + Gemini)를 Pod 에서 실행 |
| T4 등재 동작 전수 스위프 | 불필요 | PIL/numpy 렌더. 배경은 정지 이미지, 비디오 추출 0 |
| T5 판정 + 회귀 + 문서 | 불필요 | 로컬 PNG 열람 · pytest · Firestore 읽기 |

**Pod 정지 가능 시점 = T3 의 done 체크리스트가 전부 충족된 직후.** 그 전에는 끄지 말 것.

**정지 전 체크리스트 (전부 확인하고 나서 belle 에게 알린다)**
1. `reference-kp-18fps.json` 이 **로컬** quick 디렉터리에 있고 11/11 · joints 12 · fps 18.0 (T1)
2. 추출 로그 `refkp_18fps.log` 로컬 회수 (증거 — Pod `/workspace` 에만 두지 말 것)
3. T3 재분석 4건이 Firestore `status == "done"` (Firestore·S3 는 Pod 와 무관하게 남는다)
4. `docs_after/*.json` 과 `zoom_after/*.png` 로컬 회수 완료
5. Pod `/workspace` 에만 있고 repo 에 없는 것 = `bootstrap_full.sh` · `start_server.sh` ·
   `aws_env.sh` — **Network Volume 이라 stop 으로는 사라지지 않는다.**
   belle 에게 **stop(정지)** 과 **terminate(삭제)** 를 구분해 안내할 것. terminate 하면 볼륨
   연결이 끊긴다.

**재기동 비용**
- stop → start: pod id·proxy URL 동일 → **SSM/Lambda 재동기화 불필요**. 서버 기동 ~5분
  (`/workspace/start_server.sh`, 가중치 로드 포함). GPU 재확보 실패 가능(EU-RO 4090 경합).
- **새 Pod 생성 시에는** proxy URL 이 바뀌므로 SSM `/sunity/motion/runpod-analyze-url` 갱신(v24)
  + Lambda `sunity-motion-pilot-pipeline` env 동기화 + 토큰 스모크가 다시 필요하다.

**나는 "지금 꺼도 됩니다"를 말할 뿐이다 — Pod 는 belle 가 콘솔에서 끈다.**
SUMMARY 최상단에 그 한 줄을 반드시 넣는다.

**무인 장시간 실행 전제확보** (feedback-secure-preconditions-before-promising-unattended-runs)
Pod 명령은 전부 `nohup ... > /workspace/<name>.log 2>&1 &` 로 띄우고,
`ssh ... "tail -n 5 /workspace/<name>.log"` 폴링으로 진행을 확인한다.
포그라운드 SSH 로 장시간 작업을 걸지 말 것(연결이 끊기면 작업이 죽는다).
</pod_lifecycle>

<tasks>

<task type="auto">
  <name>Task 1: Pod 18fps 12관절 추출 + 로컬 BEFORE 실측 (Pod 필요)</name>
  <files>
.planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/measure_ref_state.py,
.planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/refkp_before.json,
.planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/reference-kp-18fps.json,
.planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/refkp_18fps.log
  </files>
  <action>
(1-a) Pod 생존 확인. `curl -s https://gwa4jn3lq4tb21-8000.proxy.runpod.net/health` 로
`commitSha` 가 `a6cb91cd` 로 시작하고 `pipeline_loaded` 가 true 인지 확인한다. 다르면 중단·보고.

(1-b) 추출을 먼저 띄운다 (Pod 유휴 최소화).
기존 프로덕션 스크립트를 **코드 변경 없이** CLI 인자만 바꿔 쓴다:
`backend/scripts/extract_reference_keypoint_reports.py --target-fps 18.0`.
그 스크립트의 `MOTION_IDS` 기본값이 이미 11종이므로 동작 목록을 손으로 적지 말 것.
Pod 에서 `source /workspace/aws_env.sh` 와 `PYTHONPATH=$PWD:$PWD/shared/python` 를 걸고
`nohup ... --out /workspace/reference-kp-18fps.json > /workspace/refkp_18fps.log 2>&1 &` 로 띄운다.
RTMW 초기화 약 30초 + 11영상(최장 621프레임@9fps 이므로 18fps 는 약 2배)이라 수 분에서 십수 분을
예상하고 `tail -n 5` 폴링으로 본다. **한 동작이라도 FAIL 로 건너뛰면 그대로 진행하지 말고 보고**한다
(그 스크립트는 부분 실패를 허용하는 설계다 — 11/11 이 아니면 이 플랜은 진행 불가).

(1-c) 추출이 도는 동안 로컬 BEFORE 를 잰다 — GPU 무관, 병렬로 시간 절약.
신규 읽기 전용 스크립트 `measure_ref_state.py` 를 만든다(레포 루트에서 `firebase-sa.json` 로 init,
선례 = `evidence-refkp/measure_ref_ankle_elbow_conf.py`). **11 doc 전건**에 대해 다음을 기록한다:
  - top-level: `activeVersion`, `anglesFrames`, `len(anglesJointKeys)`,
    `keypointReport` 의 fps/frames/len(joints), `referenceKeypointReport` 의 fps/frames/len(joints)
    (부재면 null 로 명시 — 조용히 빠뜨리지 말 것)
  - `reference/_release` 문서 존재 여부와 `activeCandidate` 값 (**L-4 게이트 입력**)
  - candidate `phase33-cm3-run1`: `referenceKeypointReport` 의 fps/frames/len(joints) +
    `keypointReport` 의 fps/frames + `anglesFrames`.
    **이것이 오케스트레이터가 확인하지 않은 열린 질문이다. 가정하지 말고 읽어서 적을 것.**
  - 채점 8필드 해시 — `backend/scripts/reprocess_reference_motions_phase4.py` 의
    `_release_doc_hash` 를 **import 해서** 쓴다(해시 로직 복제 금지). top-level 스냅샷에 적용.
  - `firestore_admin.get_reference_motion(mid)` 를 호출해 **실제로 해석되는** 문서의
    `anglesFrames` 와 `keypointReport.fps` 를 같이 기록한다(shadow env 미설정 상태에서).
  - 파생 컬럼: `rep9_n = report.frames * 9.0 / report.fps` 와
    `anglesFrames * 9.0 / keypointReport.fps` 를 같이 적어, 현행 배율 왜곡
    (`ref_display_frame_index` 의 4/3 사례)이 동작별로 얼마인지 표로 남긴다.
산출 = `refkp_before.json` + stderr 표.

(1-d) 산출 회수. `scp` 로 `reference-kp-18fps.json` 과 `refkp_18fps.log` 를 quick 디렉터리로 내린다.
회수 후 **로컬 파일만으로** 11/11, `len(joints)==12`, `fps==18.0` 을 검증한다.

(1-e) GATE-A 예비 판정표. `reference-kp-18fps.json` 의 `frames` 와 `refkp_before.json` 의
`anglesFrames` 를 **동작별로 나란히** 출력한다. 전건 일치가 아니면 **쓰지 말고** 그 표를 근거로
보고한다. 차이가 1프레임이어도 봐주지 말 것 — 같은 추출기·같은 영상이면 결정적이어야 한다.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && python3 -c "
import json, pathlib
d = pathlib.Path('.planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp')
kp = json.loads((d/'reference-kp-18fps.json').read_text())['motions']
assert len(kp) == 11, f'추출 {len(kp)}/11'
bad = [m for m, r in kp.items() if float(r['fps']) != 18.0 or len(r['joints']) != 12]
assert not bad, f'fps/joints 위반: {bad}'
be = json.loads((d/'refkp_before.json').read_text())
rows = be if isinstance(be, list) else be.get('motions')
assert rows and len(rows) == 11, 'BEFORE 11행 아님'
print('추출 11/11 fps=18.0 joints=12 OK / BEFORE 11행 OK')
"</automated>
  </verify>
  <done>
`reference-kp-18fps.json` 11/11, joints 12, fps 18.0. `refkp_before.json` 에 11 doc 의
anglesFrames, 두 보고서 메타, 채점 8필드 해시, activeVersion, `_release.activeCandidate`,
candidate 실측이 전부 들어있다. GATE-A 예비 판정표(frames vs anglesFrames)가 출력됐고,
`_release.activeCandidate` 값이 명시적으로 기록됐다(부재면 "부재"라고 적는다).
  </done>
</task>

<task type="auto">
  <name>Task 2: flip 방어 + top-level 표시 보고서 교체 + 점수 무접촉 증명 (Pod 불필요)</name>
  <files>
backend/scripts/reprocess_reference_motions_phase4.py,
backend/tests/phase33/test_candidate_staging.py,
.planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/write_ref_kp_report.py,
.planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/refkp_backup.json,
.planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/refkp_after.json
  </files>
  <action>
(2-a) flip 방어 — 먼저 측정하고 나서 고친다 (L-5).
`_reprocess_one` 이 만드는 payload 에 `referenceKeypointReport` 가 실리는지, candidate 문서
(`reference/{id}/versions/phase33-cm3-run1`)에는 있는지를 **먼저 확인**한다(코드 읽기 + T1 실측).
결과에 따라:
  - payload 에 있다 → `mirror_fields` 에 `"referenceKeypointReport": payload.get(...)` 1줄.
  - payload 에 없다 → 1줄은 no-op 이므로 **candidate 버전 문서에서 읽어 폴백**하도록 만든다
    (`ref_doc.collection("versions").document(version).get()` 은 그 함수 근방의 기존 관용구다).
    5줄 이내로, 기존 None 제거 규칙(`{k: v for ... if v is not None}`) 앞에 놓아 그 규칙이
    그대로 적용되게 한다.
어느 쪽이든 한국어 주석에 "33-07 flip 잠복 버그 — 표시 보고서가 채점 타임베이스와 함께 이동해야 함"
근거를 적는다. **flip 을 실행하지는 않는다.**

테스트는 `backend/tests/phase33/test_candidate_staging.py` 에 추가한다(그 파일이 flip 계보를 이미
가지고 있다 — `test_flip_pre_phase4_immutable_and_idempotent` 등). **RED 를 먼저 확인**하고 구현한다:
  1. payload 에 `referenceKeypointReport` 가 있으면 top-level 로 미러된다
  2. payload 에 없고 candidate 문서에만 있으면(폴백을 만들었다면) 그래도 미러된다.
     폴백을 만들지 않기로 했다면 이 테스트 대신 **"1줄은 payload 에만 반응한다"를 명시적으로
     단언하는 테스트**를 쓰고 SUMMARY 에 한계로 적는다. 조용히 넘어가지 말 것.
  3. 기존 flip 테스트(post-write verify, pre_phase4 immutable, release pointer)가 무수정 통과

(2-b) writer 스크립트 `write_ref_kp_report.py` (quick 디렉터리, 프로덕션 아님). 모드 4개:
  - `--backup`: 11 doc 의 **현행 top-level `referenceKeypointReport` 원본 전체**를
    `refkp_backup.json` 에 저장(부재면 null 명시). **이것 없이는 `--write` 를 거부**한다.
  - `--dry-run`(기본): L-2 GATE-A 전건 + L-4 GATE-C 를 계산해 표로 출력. 검증은
    `firestore_admin._validate_keypoint_report` 를 **재사용**한다(새 validator 작성 금지).
    11/11 all-or-nothing — 하나라도 실패하면 write 0.
  - `--write`: `_doc(f"reference/{mid}").set({"referenceKeypointReport": rep}, merge=True)`.
    **이 dict 에 다른 키를 넣지 말 것.** 쓰기 직전에 `_release_doc_hash` 로 BEFORE 해시를 다시 떠
    T1 시점 이후 변화가 없음을 확인한다(변했으면 중단).
  - `--restore`: 백업 값을 그대로 되돌린다. 백업이 null 이던 doc 은 건너뛴다
    (Firestore 필드 삭제는 이 플랜 범위 밖).

(2-c) 실행 순서: `--backup` → `--dry-run`(게이트 표 확인) → `--write`.

(2-d) 사후 증명 (L-3). 11 doc 을 **재조회**해 `refkp_after.json` 에 기록하고 표를 출력한다:
  - `referenceKeypointReport` 의 fps/frames/len(joints) 가 11/11 = (18.0, anglesFrames, 12)
  - 채점 8필드 해시 BEFORE == AFTER **11/11**
  - `activeVersion` 11/11 불변, `reference/_release.activeCandidate` 불변
  - 파생: 새 `rep9_n` 이 `anglesFrames * 9 / keypointReport.fps` 와 맞아
    `ref_display_frame_index` 배율이 1.0(identity)으로 가는지 동작별로 적는다.
    안 맞으면 조정하지 말고 수치를 그대로 보고한다.

(2-e) 롤백 실증. 동작 **1건**만 골라 `--restore` → 재조회로 원본 복귀 확인 → 다시 `--write` →
재조회로 신규 값 복귀 확인 → 그 왕복 내내 채점 8필드 해시가 불변임을 확인한다.
"되돌릴 수 있다"를 문장이 아니라 **왕복 실측**으로 남긴다.

(2-f) 위험 고지. 이 쓰기는 **OTA 없이 앱에 즉시 반영**된다(verified_facts —
`referenceMotions.ts` 가 top-level 직독). 기준 오버레이 관절이 8에서 12로 늘어난다.
SUMMARY 에 (i) 즉시 반영된다는 사실, (ii) 되돌리는 명령 한 줄, (iii) 관측되는 변화를 적는다.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && PYTHONPATH=backend/tests python3 -m pytest backend/tests/phase33/test_candidate_staging.py -q 2>&1 | tail -5</automated>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && python3 -c "
import json, pathlib
d = pathlib.Path('.planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp')
def idx(x):
    rows = x if isinstance(x, list) else x['motions']
    return {r['motion']: r for r in rows}
B = idx(json.loads((d/'refkp_before.json').read_text()))
A = idx(json.loads((d/'refkp_after.json').read_text()))
assert len(A) == 11, len(A)
bad = [m for m, r in A.items() if r['refkpFps'] != 18.0 or r['refkpJoints'] != 12 or r['refkpFrames'] != r['anglesFrames']]
assert not bad, f'GATE-A 위반 {bad}'
h = [m for m in A if A[m]['scoringHash'] != B[m]['scoringHash']]
assert not h, f'채점 8필드 해시 변동 {h}'
v = [m for m in A if A[m]['activeVersion'] != B[m]['activeVersion']]
assert not v, f'activeVersion 변동 {v}'
print('GATE-A 11/11 · 채점 8필드 해시 불변 11/11 · activeVersion 불변 11/11 OK')
"</automated>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && test -z "$(git diff --name-only -- app/ backend/functions/ backend/shared/ docs/)" && echo '표시 전용 확인 — app/functions/shared/docs diff 0'</automated>
  </verify>
  <done>
top-level `referenceKeypointReport` 11/11 이 18.0fps, 12관절, frames == anglesFrames 로 교체됐고,
채점 8필드 해시와 activeVersion 과 `_release.activeCandidate` 전부 불변임이 재조회로 증명됐다.
`refkp_backup.json` 이 존재하고 1건 restore → write 왕복이 실증됐다.
flip 방어가 **실제로 값을 싣는 형태**로 들어갔거나(또는 no-op 임을 단언하는 테스트와 함께 한계가
기록됐고), `test_candidate_staging.py` 가 전건 통과한다.
프로덕션 수정 파일은 `reprocess_reference_motions_phase4.py` 하나뿐이다.
  </done>
</task>

<task type="auto">
  <name>Task 3: 실 doc 재산출 — 렌더 doc 4건 재분석 (Pod 필요 · 마지막 GPU 구간)</name>
  <files>
.planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/reanalyze_render_docs.py,
.planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/docs_before/,
.planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/docs_after/,
.planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/zoom_after/
  </files>
  <action>
목적 = §C-2 미검증 항목의 재료(재산출 doc)와 S10 실 doc 판정 재료(실 학생 x 실 기준 PNG)를
**한 번에** 만드는 것. 이 태스크가 끝나면 Pod 는 더 필요 없다.

(3-a) 대상 특정 + 백업. uid `fvcNXzEqKjgqVxRPVSj1iwFnIpn2` 의 렌더 doc 4건
(파워스핀 80 / 킵업 79 / pdshape 100 / 엘보 60 — `.continue-here.md` 기록)을 Firestore
**조회로 특정**한다(점수·mode·referenceMotionId 로 확인. 이름 추측 금지).
각 doc 전문을 `docs_before/{analysisId}.json` 으로 저장하고, 기존 `result.faultZoom` 의
joint/criterion/tier 목록과 `overallScore` 를 표로 남긴다.
기존 PNG 도 S3 에서 `zoom_before/` 로 받아 둔다(비교용, 커밋은 대표컷만).

(3-b) 직렬 재분석. 파이프라인은 **동시성 비안전**이다
(memory: pipeline-not-concurrency-safe-eval-serial) — 반드시 한 건씩, 완료 확인 후 다음.
토큰이 로그·셸 히스토리에 남지 않도록 **Pod 안에서 loopback 으로** 호출한다:
Pod 셸에서 `curl -s -X POST http://127.0.0.1:8000/analyze` 에
`X-RunPod-Token: $RUNPOD_AUTH_TOKEN` 헤더(Pod env 변수를 그 자리에서 참조)와
`{"bucket": "sunity-motion-pilot-videos", "key": "uploads/<uid>/<analysisId>.<ext>"}` 를 보낸다.
확장자는 `docs_before` 의 실제 업로드 키에서 읽는다(`.mov` 일 수 있다).
`/analyze` 는 백그라운드 처리이므로 Firestore `status` 와 `updatedAt` 을 폴링해 완료를 판정한다.
**doc 이 done 상태라 파이프라인이 거부하거나 `updatedAt` 이 움직이지 않으면, 상태를 강제로
되돌리지 말고 중단·보고**한다(fail-closed).

(3-c) 회수. 완료된 doc 전문을 `docs_after/{analysisId}.json` 으로, `result.faultZoom[].imageUrl`
에 대응하는 S3 객체(`results/{uid}/{analysisId}/zoom_*.png`, `zoom_adv_*.png`)를 `zoom_after/` 로
**전량** 내려받는다. presigned URL 만 저장하지 말 것(7일 만료 — memory: aws-keys-and-bucket).

(3-d) 대조표. doc 별로 다음을 적는다.
  - `overallScore` before → after. **움직였으면 그대로 보고**한다. 기준 표시 보고서는 채점
    무접촉이므로 이동분은 RTMW/Gemini 재실행 편차다 — 숨기지 말고 수치로 적는다.
  - faultZoom 카드 수와 criterion 목록 before → after
  - **`userVideoSec` / `refVideoSec` 방출 여부** (§C-1 F-3 산출이 이제 doc 에 실리는지 =
    S6 paircap 초 · F-3 참고코너 미검증 항목의 해소 조건)
  - 무릎·팔꿈치 계열 카드가 새로 생겼는지, 각도가 베이크됐는지

(3-e) Pod 정지 판정. `<pod_lifecycle>` 의 정지 전 체크리스트 5항목을 하나씩 확인하고, 전부
충족되면 SUMMARY 와 실행 로그에 **"Pod 정지 가능"** 을 명시한다. 하나라도 미충족이면 무엇이
남았는지 적는다. **Pod 를 직접 끄지 말 것 — belle 가 콘솔에서 끈다.**
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && python3 -c "
import json, pathlib
d = pathlib.Path('.planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp')
af = sorted((d/'docs_after').glob('*.json'))
assert len(af) == 4, f'재산출 {len(af)}/4'
for p in af:
    doc = json.loads(p.read_text())
    assert doc.get('status') == 'done', (p.name, doc.get('status'))
png = list((d/'zoom_after').glob('*.png'))
assert png, 'zoom PNG 0장'
print(f'재산출 4/4 done · PNG {len(png)}장 회수')
"</automated>
  </verify>
  <done>
4건 전부 `status == done` 으로 재산출됐고, doc 전문과 faultZoom PNG 전량이 로컬에 회수됐다.
before/after 대조표(점수, 카드 수, criterion, userVideoSec/refVideoSec)가 작성됐고 점수 이동이
있으면 수치와 함께 보고됐다. `docs_before/` 백업이 존재해 되돌릴 수 있다.
**정지 전 체크리스트 5항목 판정이 기록됐고, 충족 시 "Pod 정지 가능"이 명시됐다.**
  </done>
</task>

<task type="auto">
  <name>Task 4: 등재 동작 전수 스위프 — 기준측만 실 12관절 보고서로 교체 (Pod 불필요)</name>
  <files>
.planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/sweep_real_ref.py,
.planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/sweep_out/real-ref/
  </files>
  <action>
목적 = **기준측 좌표가 실물일 때 각도 베이크 게이트가 어떻게 갈리는지**를 등재 동작 전건에서 본다.
f5h 하네스를 복제해 **딱 한 변수만** 바꾸므로 f5h `after` 산출과 직접 비교된다.

(4-a) 하네스. `sweep_leg_angle.py` 를 이 디렉터리로 복제해 `sweep_real_ref.py` 로 만들고
**`_REF_KP` 합성 8관절 → T1 산출 실 보고서(18fps 12관절)** 만 교체한다.
  - 기준 보고서는 `reference-kp-18fps.json` 에서 동작 id 로 뽑아 그대로 넘긴다(재가공 금지).
  - 표시 프레임 인덱스는 프로덕션 함수를 쓴다 — `fz._to_rep_idx` 와 `fz.select_confident_frame` 을
    **직접 호출**해 고른다(변환식 복제 금지, f5h 규율 승계).
  - 배경 이미지, 학생 12관절, ankle 사다리, criteria glob 은 **f5h 그대로** 둔다(통제 변수).
    보고서 좌표가 정규화라 배경과 무관하게 그려진다.
  - **로컬에 imageio 가 없다** — 비디오 추출을 시도하지 말 것. 신규 패키지 설치 금지.
  - 등재 동작 = criteria glob(현재 10). 기준 보고서는 11 — `ref-combo` 는 criteria 미보유라
    스위프 대상이 아니다. 이 사실을 산출에 명시하고 "11" 과 "10" 을 섞어 쓰지 말 것.

(4-b) 측정 컬럼 (카드별).
  - `angle bake`: `drawn` / `omitted:<사유>`. 사유별 집계를 f5h·l7t 기록과 나란히 둔다
    (l7t 실측: drawn 21 / `omitted:ref_gate` 39 / `omitted:unmapped` 30).
  - **무릎·팔꿈치 계열 전환** — `angle_vs_reference__left_elbow` 계열과 `..._knee` 계열이
    `omitted` 에서 `drawn` 으로 갔는지. **안 갔으면 그 카드의 기준측 게이트 통과율을 찍어 왜인지
    설명**한다(evidence-refkp 표와 대조. `ref-elbow-twist-sister` 0.364, `ref-pdshape` 0.396 은
    별도 컬럼으로 볼 것). "약해서 뺐다" 는 금지. "몇 프레임 중 몇이 통과했고 그래서 fail-closed"
    로 적는다.
  - **회귀 방어(over-generalize-breaks-approved)**: 어깨·힙 계열 `drawn` 이 줄지 않았는가(S8),
    정중앙 crop 의 `user_side_px == ref_side_px` 전건 일치가 유지되는가(S9),
    `split_angle` 드로잉이 f5h 의 10/10 을 유지하는가(S10 합성분),
    각도 비대칭 카드 0(both-or-neither)인가.
  - **동작명 분기 0** — `fault_zoom.py` 주석 제외 grep 재확인.
  - f5h 의 A/B 픽셀 오라클과 결정성 확인(같은 카드 2회 렌더 byte 동일)을 그대로 승계한다.

(4-c) PNG 직접 열람 (code-only-verification 금지, D-40).
Read 도구로 **실제로 열어** 보고, 본 것과 못 본 것을 구분해 적는다. 최소 목록:
  1. 무릎 각도 카드 1장 (새로 켜졌다면 그 동작, 아니면 통과율이 가장 높은 동작)
  2. 팔꿈치 각도 카드 1장
  3. 어깨 각도 카드 1장 — S8 회귀 확인(승인 자산 `belle_shoulder_pair_dtwmatch_r7.png` 대조)
  4. `split_angle` 카드 1장 — S10 합성분 유지 확인
  5. 통과율 약한 2동작(`ref-elbow-twist-sister`, `ref-pdshape`) 각 1장
**컨텍스트 절약**: 열람은 6장 안팎으로 제한하고 나머지는 `summary.json` 수치로 판정한다.

(4-d) 항목 4 판정 (L-6). 기준이 12관절이 된 뒤에도 **앵커 주석이 여전히 필요한 criterion 이
남는지**를 표로 판정한다. 남으면 목록만 §C-4 잔여로 적는다. **주석 값을 채우지 말 것.**

(4-e) 대용량 산출. PNG 전량은 커밋하지 않는다 — `sweep_out/.gitignore` 로 제외하고
`summary.json` 과 대표컷만 커밋한다(f5h 선례).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && python3 .planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/sweep_real_ref.py --out real-ref --assert 2>&1 | tail -30</automated>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && grep -v '^[[:space:]]*#' backend/shared/python/sunity_shared/analysis/fault_zoom.py | grep -cE 'ref-(climb|combo|elbow-twist-sister|foxtop|invert|kip-up|pdshape|peter-pan|power-spin|sideway-spin)' | grep -qx 0 && echo '동작명 분기 0 확인'</automated>
  </verify>
  <done>
등재 동작 전건 스위프가 실 기준 보고서로 완료됐고 `summary.json` 에 카드별 drawn/omitted 사유
집계가 남았다. 무릎·팔꿈치 각도가 켜졌는지 여부가 **통과율 수치로 설명**됐다(안 켜졌으면 왜인지).
S8 어깨·힙 회귀 0, S9 정중앙 배율 전건 일치, S10 합성분 10/10 유지, 각도 비대칭 0,
동작명 분기 0 이 재확인됐다. PNG 6장 안팎을 직접 열어 본 것과 못 본 것이 구분돼 적혔다.
항목 4(앵커 주석 잔여) 판정표가 있다.
  </done>
</task>

<task type="auto">
  <name>Task 5: S10 실 doc 판정 + 보류 2건(S5·S22) + 회귀 + 33-G 재채점 (Pod 불필요)</name>
  <files>
.planning/phases/33-result-trust-recovery/33-G-MOCKUP-DIFF.md,
.planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/pytest_after.txt,
.planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/judgment_s10_s5_s22.md
  </files>
  <action>
(5-a) **S10 실 doc 판정** — T3 의 `zoom_after/` 에서 `zoom_split_angle.png` 계열을 Read 도구로
**직접 열어** 본다. f5h 가 합성 좌표라 못 봤던 것을 여기서 본다:
  (a) 골반에서 양다리로 뻗는 **선 2개 + 사이각 호**가 두 패널에 보이는가
  (b) **선이 실제 다리와 정렬되는가 — 해부학적 정합** (f5h 한계 항목. 이것이 이 태스크의 핵심)
  (c) 계약 4·5·6행(ankle·knee 둘 다 crop 밖 / 골반 crop 밖 / 좌우 비대칭)이 실 doc 에서
      발생하는가. 발생하면 그 카드의 거동이 f5h 단위 테스트가 규정한 것과 같은지 확인한다.
판정 재료로 `.planning/quick/260731-f5h-.../sweep_leg_angle.py` 의 crop 기하 스파이를 재사용해도
좋다. 4건 중 `split_angle` 카드가 없는 doc 이 있으면 **없다고 적는다**(있는 것처럼 쓰지 말 것).

(5-b) **S22 판정** (33-G 58행, 보류). "멈춤 컷 = 결함 텍스트 서술 순간(record 실측 창 안)".
재산출 doc 데이터로 계산한다: 각 음성 큐 tick 의 시각과 대응 record 의 실측 창
(`sourceFrameIndices` 또는 window 메타)을 초로 환산해 **tick 시각이 그 창 안에 드는지**를
doc 별·record 별 표로 낸다. 앱이 tick 시각에서 멈춘다는 것은 코드 경로로 확인한다
(`VideoCompare.tsx` 의 tick → pause 배선). 데이터로 못 가르는 부분이 있으면
**"왜 못 봤는지"를 적고 미판정으로 남긴다. 조용히 PASS 금지.**

(5-c) **S5 판정** (33-G 26행, 보류). "기본 화면 새 문장 0(D-05)".
재산출 doc 을 입력으로 기본 화면에 렌더되는 **문장 인벤토리**를 정적 열거해(앱 카피 소스 +
doc 필드) 승인 목업 `mockups/index.html` 의 기본 화면 문장 집합과 대조한다. 목업에 없는 문장이
나오면 그 문장과 출처 파일:줄을 적는다. **시뮬레이터가 있어야만 갈리는 부분은 실행자 도구로
불가**하므로, 그 경우 무엇을 어느 화면에서 봐야 하는지 절차를 적어 오케스트레이터에게 인계하고
미판정으로 남긴다.

(5-d) 회귀. `PYTHONPATH=backend/tests python3 -m pytest backend/tests -q` 를 돌려
FAILED/ERROR **node ID 집합**을 f5h baseline
(`.planning/quick/260731-f5h-.../pytest_baseline_before.txt`, 58건)과 `diff` 한다.
**숫자가 아니라 집합**을 본다. 신규 실패가 있으면 원인을 밝히고 보고한다.

(5-e) 33-G 재채점 갱신. `33-G-MOCKUP-DIFF.md` 의 해당 행을 이번 실측으로 갱신한다:
S8(무릎·팔꿈치 축), S10(실 doc), S5, S22, F-3(렌더), S6(paircap 초), 그리고 §C-1 잔여 이관표
①②③. **PASS 로 올릴 근거가 산출물에 없으면 올리지 말고 미검증 사유를 적는다.**
표 하단에 "C-4 A-트랙 기록" 절을 추가하고 수치를 넣는다(C-1/C-2 기록 절 형식 승계).

(5-f) 판정 요약을 `judgment_s10_s5_s22.md` 에 남긴다 — 항목별로 **본 것 / 못 본 것 / 그것을
성립시킨 행위**를 나눠 적는다(memory: state-evidence-act-or-mark-unverified).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && D=.planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp && PYTHONPATH=backend/tests python3 -m pytest backend/tests -q 2>&1 | tee "$D/pytest_after.txt" | tail -3 && grep -E '^(FAILED|ERROR)' "$D/pytest_after.txt" | sed 's/ - .*//' | sort -u > "$D/failed_ids_after.txt" && grep -E '^(FAILED|ERROR)' .planning/quick/260731-f5h-33-g-c-3-d-1-split-angle-leg-angle-omitt/pytest_baseline_before.txt | sed 's/ - .*//' | sort -u > "$D/failed_ids_baseline.txt" && diff "$D/failed_ids_baseline.txt" "$D/failed_ids_after.txt" && echo 'FAILED/ERROR node ID 집합 diff 0'</automated>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && test -s .planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/judgment_s10_s5_s22.md && grep -q 'C-4 A-트랙' .planning/phases/33-result-trust-recovery/33-G-MOCKUP-DIFF.md && echo '판정 문서 + 33-G 갱신 확인'</automated>
  </verify>
  <done>
S10 이 실 doc PNG 위에서 판정됐다 — 선 2개·호·**해부학적 정합**과 계약 4·5·6행 발생 여부가
본 것/못 본 것으로 구분돼 기록됐다. S5·S22 는 판정되었거나, 미판정이면 **왜 못 봤는지**와
어디서 볼 것인지가 적혔다. pytest FAILED/ERROR node ID 집합 diff 0. `33-G-MOCKUP-DIFF.md` 의
해당 행이 실측으로 갱신되고 "C-4 A-트랙 기록" 절이 추가됐다.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| 로컬 스크립트 → Firestore production `reference/*` | 프로덕션 기준 데이터에 쓴다. 채점 경로와 한 문서를 공유한다 |
| 로컬 스크립트 → Firestore production `users/{uid}/analyses/*` | belle 의 렌더 doc 을 재산출로 덮어쓴다 |
| 로컬 → Pod HTTP `/analyze` | 인증 토큰이 필요한 파이프라인 트리거 |
| Pod → S3 / Firestore | 쓰기 권한이 있는 자격증명이 Pod env 에 있다 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-iis-01 | Tampering | `write_ref_kp_report.py` → `reference/{id}` | mitigate | `set(merge=True)` 에 넘기는 dict 를 `{"referenceKeypointReport": rep}` 단일 키로 고정. 쓰기 후 `_release_doc_hash` 로 채점 8필드 BEFORE==AFTER 11/11 + `activeVersion` + `_release.activeCandidate` 불변 단언 (L-3) |
| T-iis-02 | Tampering | 표시 보고서 타임베이스 | mitigate | GATE-A: `frames == anglesFrames` AND `fps == 18.0` AND `joints == 12` 를 11/11 all-or-nothing 으로 검사, 하나라도 실패 시 쓰기 0 (L-2). fps 라벨만 믿지 않는다 |
| T-iis-03 | Denial of service | 되돌릴 수 없는 프로덕션 쓰기 | mitigate | `--backup` 선행 강제(백업 없으면 `--write` 거부) + 1건 restore→write 왕복 실증 (2-e) |
| T-iis-04 | Denial of service | 재분석이 belle 렌더 doc 파괴 | mitigate | `docs_before/*.json` 전문 백업 선행 + 직렬 실행 + `updatedAt` 폴링 + 거부 시 fail-closed 중단(상태 강제 변경 금지) |
| T-iis-05 | Information disclosure | Pod 토큰·AWS 키 노출 | mitigate | `/analyze` 호출을 Pod 내부 loopback 에서 env 변수 참조로 수행 — 토큰 값이 로컬 셸·로그·산출 JSON 에 남지 않는다. 실측 스크립트는 keys-not-values 출력 |
| T-iis-06 | Repudiation | flip 방어가 no-op 인데 방어했다고 기록 | mitigate | payload/candidate 양 소스를 먼저 측정하고, 실제로 값을 싣는 형태로 구현하거나 no-op 임을 단언하는 테스트 + SUMMARY 한계 기록 (L-5) |
| T-iis-07 | Tampering | 표시 교체가 OTA 없이 프로덕션 앱에 즉시 반영 | accept | `referenceMotions.ts` 가 top-level 직독이라 구조적으로 불가피. 변화는 기준 오버레이 관절 8→12(가산적)이고 점수·문구 무접촉. 롤백 명령 1줄을 SUMMARY 최상단에 박제 |
| T-iis-08 | Elevation of privilege | 스위프 하네스가 프로덕션 상수를 흔듦 | mitigate | 하네스는 quick 디렉터리 로컬, 심볼 교체는 컨텍스트 매니저로 원복(f5h `_NoLegAngle` 선례). `git diff` 로 프로덕션 diff 범위 확인 |
| T-iis-SC | Tampering | 패키지 설치 | mitigate | **신규 설치 0.** 로컬은 PIL/numpy/firebase_admin/boto3/yaml 기존 의존성만, Pod 은 기존 환경만 쓴다. imageio 가 없다고 설치하지 말고 하네스 설계를 바꾼다 |
</threat_model>

<anti_patterns>
| Anti-pattern | severity | 이 플랜에서의 의미 |
|---|---|---|
| single-motion-fixation | blocking | 규칙은 좌표·통과율로 키잉. 동작명 분기 0. 등재 동작 전건 + 기준 11/11 확인 |
| code-only-verification | blocking | 코드 통과 ≠ 완료. PNG 를 Read 로 열고 Firestore 값을 재조회해 찍는다 |
| over-generalize-breaks-approved | blocking | 이미 PASS 인 S8 어깨/힙 · S9 정중앙 crop · S10 다리를 깨지 말 것. 회귀 컬럼으로 매 실행 검사 |
| repair-rediscussion | blocking | 설계 재논의 금지. 단 데이터가 결정과 안 맞으면 **보고**(L-7) |
| 근거 없는 의심 | blocking | 반박할 측정치 없이 검증된 작업을 흔들지 말 것 |
| 점수 경로 오염 | blocking | 표시 필드만 건드린다. angles / activeVersion / 릴리스 포인터에 쓰면 즉시 실패 |
| 미검증을 PASS 로 | blocking | 못 본 것은 "왜 못 봤나 / 어디서 볼 것"과 함께 미검증으로 남긴다 |
</anti_patterns>

<verification>
플랜 전체 완료 판정 (전부 **산출물로** 증명한다):

1. **점수 무접촉** — 채점 8필드 해시 BEFORE==AFTER 11/11, `activeVersion` 11/11 불변,
   `reference/_release.activeCandidate` 불변. (T2 verify 자동화)
2. **18fps 12관절 실증** — Firestore **재조회**로 11/11 이 `fps==18.0` AND `len(joints)==12`
   AND `frames==anglesFrames`. 9fps 로 들어가면 실패. (T2 verify 자동화)
3. **crop 재생성 산출 직접 열람** — T4 스위프 PNG 6장 안팎 + T3 실 doc PNG 를 Read 로 열람.
   최소 = `split_angle`(S10) + 무릎·팔꿈치 각도 카드(항목 1의 목적) + 어깨 카드(S8 회귀).
   본 것과 못 본 것을 구분해 적는다.
4. **S10 실 doc 판정** — (a) 선 2개 + 호 (b) **해부학적 정합** (c) 계약 4·5·6행 발생 여부.
5. **무릎·팔꿈치 각도 베이크** — 켜졌으면 카드 PNG 로, 안 켜졌으면 기준측 게이트 통과율로 설명.
6. **회귀** — `PYTHONPATH=backend/tests python3 -m pytest backend/tests -q` 의 FAILED/ERROR
   **node ID 집합** 이 f5h baseline(58) 과 diff 0.
7. **S5·S22 판정** — 판정 불가면 "왜 못 봤는지"를 적고 미판정으로 남긴다. 조용히 PASS 금지.
8. **Pod 정지 시점** — T3 체크리스트 5항목 판정 + SUMMARY 최상단 한 줄.
</verification>

<success_criteria>
- Firestore top-level `referenceKeypointReport` 11/11 = 18.0fps · 12관절 · frames == anglesFrames
- 채점 8필드 해시 · activeVersion · `_release.activeCandidate` 11/11 불변 (재조회 증명)
- `refkp_backup.json` 존재 + 1건 restore→write 왕복 실증
- `_flip_active_pointer` 가 `referenceKeypointReport` 를 실제로 미러하거나, no-op 임을 단언하는
  테스트와 함께 한계가 기록됨. flip 실행 0
- 등재 동작 전건 스위프 완료 + 각도 베이크 사유별 집계 + S8/S9/S10 회귀 0 + 동작명 분기 0
- 렌더 doc 4건 재산출 완료(status done) + PNG 로컬 회수 + `userVideoSec`/`refVideoSec` 방출 확인
- S10 실 doc 판정 완료(해부학적 정합 포함), S5·S22 판정 또는 미판정 사유 기록
- pytest FAILED/ERROR node ID 집합 diff 0
- `33-G-MOCKUP-DIFF.md` 갱신 + "C-4 A-트랙 기록" 절 추가
- **SUMMARY 최상단에 "Pod 정지 가능/불가" 한 줄** + 정지 전 체크리스트 판정 + 재기동 비용
- 프로덕션 코드 변경 = `backend/scripts/reprocess_reference_motions_phase4.py` 하나
  (+ 테스트 `backend/tests/phase33/test_candidate_staging.py`). 그 외는 스크립트·하네스·산출물
- 신규 패키지 설치 0, 이모지 0, 주석·문서 한국어
</success_criteria>

<output>
`.planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/260731-iis-SUMMARY.md` 를 작성한다.

**SUMMARY 최상단 필수 3줄**
1. Pod 정지 가능 여부 한 줄 (belle 가 콘솔에서 끈다 — 나는 알릴 뿐)
2. 프로덕션 Firestore 를 되돌리는 명령 한 줄 (`write_ref_kp_report.py --restore`)
3. 이 교체가 OTA 없이 앱에 즉시 반영된다는 사실

**본문에 반드시 포함**
- BEFORE/AFTER 표 (fps · frames · joints · anglesFrames · 채점 해시 · activeVersion)
- 열린 질문 해소: candidate `phase33-cm3-run1` 의 `referenceKeypointReport` 실측값과, 그것이
  Phase 34 flip 판단에 무엇을 의미하는지 (이 플랜에서 candidate 를 고치지는 않는다)
- flip 방어의 실제 형태와 그것을 고른 측정 근거
- 각도 베이크 사유별 집계 before(l7t) → after(이번)
- 열람한 PNG 목록과 각각에서 본 것
- **미검증·미판정 목록** — 왜 못 봤는지 / 어디서 볼 것인지
- 데이터가 플랜과 안 맞은 것이 있으면 별도 절로 보고 (재논의 아님)
- 다음 단계: §C-4 3번(어깨·팔꿈치 일러스트) → 일괄 OTA → belle 확인 ③
</output>

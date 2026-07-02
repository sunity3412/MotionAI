---
phase: quick-260702-sic
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/shared/python/sunity_shared/analysis/fault_zoom.py
  - backend/functions/pipeline/app.py
  - backend/tests/test_fault_zoom.py
  - app/src/types/analysis.ts
  - app/src/lib/deductionLabels.ts
  - app/src/components/FaultZoomCompare.tsx
autonomous: true
requirements: [QT-260702-sic]
must_haves:
  truths:
    - "fault-zoom 좌/우 crop 은 각자 자기 영상의 keypoint 좌표 + 자기 프레임 인덱스를 쓰며, deficit 이 vision 측정(faultJointDeficits)에서 온 경우 crop 프레임 = visionVeto.windowMedianAngleDeltas.sourceFrameIndices 의 각-측 median 프레임(측정 프레임과 표시 프레임 일치)."
    - "같은 결함에서 온 좌+우 동일 부위 관절들(스플릿 → hips+knees 4관절)은 결함 단위 1장으로 묶이고, crop 은 멤버 keypoint 전체를 담는 bounding box 기반이며 캡션은 '양다리'."
    - "crop 앵커 keypoint 가 결측/저신뢰(confidence < 0.5)면 그 측은 엉뚱한 부위 확대 대신 전신(full-frame contain-fit) 표시."
    - "점수/분석 로직 무접촉 — fault_zoom/_attach_* 표시 경로만 변경. sourceFrameIndices 부재(legacy doc·mode3)면 기존 worst_seconds+DTW 경로 그대로(하위호환), mode3 fan-out 동작 보존."
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/fault_zoom.py"
      provides: "명시 프레임 인덱스 override + 결함단위(region) grouping + bbox/스케일 적응 crop + 저신뢰 전신 폴백"
      contains: "region"
    - path: "backend/functions/pipeline/app.py"
      provides: "_attach_fault_zoom_comparisons 가 vv.windowMedianAngleDeltas.sourceFrameIndices 를 crop 프레임으로 배선"
      contains: "sourceFrameIndices"
    - path: "backend/tests/test_fault_zoom.py"
      provides: "grouping / frame override / low-conf 폴백 / 하위호환 단위테스트"
    - path: "app/src/types/analysis.ts"
      provides: "FaultZoomComparison.region 옵션 scalar 필드 (lockstep)"
      contains: "region"
    - path: "app/src/components/FaultZoomCompare.tsx"
      provides: "region 카드 캡션 '양다리' 분기"
  key_links:
    - from: "backend/functions/pipeline/app.py::_attach_fault_zoom_comparisons"
      to: "result.visionVeto.windowMedianAngleDeltas.sourceFrameIndices"
      via: "user/reference 각-측 median → build_fault_zoom_comparisons 프레임 override"
      pattern: "sourceFrameIndices"
    - from: "app/src/components/FaultZoomCompare.tsx"
      to: "app/src/lib/deductionLabels.ts::REGION_LABEL_KO"
      via: "item.region 우선 캡션"
      pattern: "REGION_LABEL_KO"
---

<objective>
"문제 부위 확대 비교" carousel 의 reference-측 crop 이 결함 부위를 벗어나는 문제(C 작업) fix.
belle 실기기 증상(TestFlight #27, kip-up fault 88): 내 영상 crop 은 엉덩이 부근인데 정은지 crop 은
상체 뒤통수 — 좌우가 서로 다른 부위/모먼트. 스플릿(양다리) 결함인데 관절 단위 4장(dot 4개)으로
쪼개지고 캡션은 "오른쪽 엉덩이"로 오인 유발.

**조사 확정 결과 (코드로 검증 완료 — 재조사 금지):**

1. 합성 이미지는 backend 렌더 (`fault_zoom.build_fault_zoom_comparisons` → S3 PNG →
   `result.faultZoomComparisons[].imageUrl`). 프론트는 표시만 — crop 정합 fix 는 backend 필수.
2. reference crop 은 이미 reference 자체 keypoint 를 씀 (`_kp_xy(ref_report, r_kp_idx, joint)`)
   — "student 좌표 재사용" 가설은 FALSE. 실제 원인은 **타이밍+신뢰도+스케일** 3중:
   - **타이밍**: crop 은 `worst_pose_timestamp(profile)` (user) + 그 프레임의 DTW match (ref) 를
     쓰는데, 캡션의 30° deficit(`faultJointDeficits`)는 vision veto 가 **다른 프레임 쌍**에서 측정
     (kip-up 은 at_seconds=None candidate 스윕 — worst_pose 와 무관). 측정 프레임은 이미
     `visionVeto.windowMedianAngleDeltas.sourceFrameIndices = {user:[18..22], reference:[35..39]}`
     로 doc 에 저장돼 있고, **인덱스 공간 = 9fps frames 배열과 동일** (angles 행 = 9fps 추출
     프레임: `build_keypoint_report(pose_frames, fps=9.0)` 동일 소스, `_selected_frame_pair` 의
     u_idx/r_idx 가 frames 배열 인덱스로 window_median 에 그대로 전달됨 — vision_veto.py:486,
     pipeline/app.py:1716-1741).
   - **신뢰도**: kip-up 은 RTMW 가 다리 keypoint 를 못 잡고 몸통으로 붕괴
     ([[split-measurement-doesnt-discriminate-kipup]]) — 붕괴된 "right_hip" 좌표를 중심으로
     crop 하면 상체/뒤통수가 나옴. `_kp_xy` 에 confidence 게이트가 전혀 없음 (keypointReport 는
     flat `confidence` (T*J) 를 이미 보유 — keypoint_frame.py:94).
   - **스케일**: crop 변 = `min(H,W)*0.42` 고정 — 촬영거리 10x 불일치(torso_px ratio)면 좌우가
     완전히 다른 신체 범위를 보여줌.
   - **fan-out**: 스플릿 1결함 → faultJointDeficits 4관절 → 관절당 1장 = 4장.

Purpose: 확대비교가 "측정한 그 모먼트의 그 부위"를 좌우 동일하게 보여주게 — 분석 신뢰(핵심 가치) 직결.
Output: backend crop 정합 + 결함단위 grouping + 전신 폴백, 프론트 region 캡션. 점수 로직 무접촉.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@backend/shared/python/sunity_shared/analysis/fault_zoom.py
@backend/functions/pipeline/app.py  (lines ~2441-2617: _render_fault_zoom / _attach_fault_zoom_comparisons / _attach_mode3_fault_zoom)
@backend/tests/test_fault_zoom.py
@app/src/types/analysis.ts  (FaultZoomComparison ~line 430, VisionWindowMedianAngleDeltas ~line 380)
@app/src/components/FaultZoomCompare.tsx
@app/src/lib/deductionLabels.ts

주의: result.tsx / deductionLabels.ts 는 B 작업(c2b0911/1b7d1e4)이 방금 수정 — 반드시 최신 HEAD 에서 읽고 작업.
Firestore 제약: list[dict] 원소는 flat scalar 만 (`_validate_dict_only_scalars`) — faultZoomComparisons
항목에 list 필드(joints 배열 등) 추가 금지. 신규 필드는 scalar `region` 만.
</context>

<tasks>

<task type="auto">
  <name>Task 1: fault_zoom.py 코어 재작업 — 프레임 override + 결함단위 grouping + bbox crop + 저신뢰 전신 폴백 (+단위테스트)</name>
  <files>backend/shared/python/sunity_shared/analysis/fault_zoom.py, backend/tests/test_fault_zoom.py</files>
  <action>
`build_fault_zoom_comparisons` 를 다음 4가지로 확장한다 (순수 모듈 유지 — S3/네트워크/firestore import 금지, PIL/numpy 만):

**(1) 명시 프레임 인덱스 override.** 신규 keyword-only 파라미터
`user_frame_idx: int | None = None, ref_frame_idx: int | None = None` (둘 다 **9fps frames 배열
인덱스 공간**). 주어지면 worst_seconds/DTW 선택을 대체: `u_idx = clamp(user_frame_idx, 0, u_n-1)`,
`r_idx = clamp(ref_frame_idx, 0, r_n-1)`. report 인덱스 변환은 기존 공식 재사용:
`kp_idx = clamp(round(idx / frames_fps * rep_fps), 0, rep_frames-1)` — **user 측도 이 변환을 쓴다**
(기존 u_kp_idx 는 worst_seconds 기반이었음). 둘 중 하나만 주어지면 주어진 측만 override, 나머지는
기존 경로. 둘 다 None(default)이면 기존 동작 100% 보존 (기존 테스트 6개 무수정 PASS 가 하위호환 증거).

**(2) 결함단위 grouping.** 모듈 상수
`_REGION_JOINTS = {"legs": frozenset({left/right hip·knee·ankle 6개}), "arms": frozenset({left/right shoulder·elbow·wrist 6개})}`.
fan-out 전에 fault_joints 를 "crop unit" 으로 변환하는 순수 helper `_group_fault_joints(fault_joints, joint_kinds) -> list[unit]`
(unit = 대표 joint + 멤버 list + region | None):
- 같은 region 에 속하는 fault joint 가 **2개 이상이고 좌(left_*)+우(right_*) 양측에 걸치며 kind 가
  전원 동일**(또는 전원 kind 없음)하면 → 1개 grouped unit (region 세팅, 멤버 = 해당 region 의
  fault joints 전부, 대표 joint = fault_joints 순서상 첫 멤버). 멤버는 개별 fan-out 에서 제거.
- 그 외(단일 관절, 같은 측만, kind 혼재)는 기존처럼 관절당 1 unit (region=None).
- kip-up 케이스: {left_hip, right_hip, left_knee, right_knee} 전부 kind='deficit' → legs 1 unit.
grouped unit 의 deficitDeg = 멤버 deficit 의 max (스플릿은 4관절 전부 30 → 30). 방출 dict 에
`"region": unit.region` 을 **region 이 있을 때만** 추가 (scalar str — Firestore list[dict] flat 제약 준수).
`"joint"` 는 대표 keypoint 유지 (S3 key `zoom_{joint}.png` / TS KeypointName 계약 불변). max_items
카운트는 unit 단위.

**(3) confidence 게이트 + 좌표 수집.** `_kp_xy` 를 확장하거나 자매 helper `_kp_xy_conf(report, frame_idx, joint)`
신설: report 에 `confidence` flat 배열(T*J)이 있으면 해당 (frame, joint) confidence 를 함께 반환.
모듈 상수 `_KP_CONF_MIN = 0.5` (프론트 KEYPOINT_LOW_CONFIDENCE_THRESHOLD=0.5 선례 정합 — 주석으로
출처 인용). valid keypoint = 좌표 finite AND (confidence 부재 → 통과 | confidence >= 0.5).
confidence 배열 길이가 frames*nj 미만이면 부재 취급 (legacy/합성 report 하위호환).

**(4) unit 별 crop + 전신 폴백.** 각 unit, 각 측(user/ref 각자 자기 report + 자기 frame idx)에서:
- 멤버 keypoint 중 valid 만 수집. **valid 0개 → 그 측은 전신 폴백**: full frame 을 비율 유지
  contain-fit 으로 (_OUT,_OUT) 흰 배경 canvas 에 배치 (`_full_frame_fit(frame) -> Image` helper).
  전신 폴백 측에는 중앙 원 마커 그리지 않음 (중앙이 결함 부위가 아니므로 — 오인 방지). user 측
  deficit 숫자 배지는 유지.
- valid 1개 (단일 unit 일반 경로) → 기존 `_crop_zoom` (_CROP_FRAC) + `_mark` 유지.
- valid 2개 이상 (grouped unit) → bbox crop: 멤버 px 좌표 bounding box 의 중심을 crop 중심으로,
  정사각 한 변 = `clamp(round(max(bbox_w, bbox_h) * 1.8), round(min(H,W)*_CROP_FRAC), min(H,W))`
  (1.8 = 멤버 관절 전체 + 주변 컨텍스트 마진; min floor = 기존 줌 수준 유지; 상한 = 프레임 내).
  기존과 동일하게 경계 넘으면 안쪽 shift. 촬영거리 불일치는 bbox 가 측별 person 스케일을 따라가며
  자연 해소. user 측 마커: grouped crop 은 중앙 원 대신 원 생략 가능하나 단순화를 위해 **중앙 원
  유지 + 배지 유지** (라벨 가독성은 D 작업 스코프 밖 — 마커 형태 재설계 금지).
- 한 측이라도 crop/합성 실패 시 기존 try/except graceful skip 유지.

기존 좌표 부재 skip 동작 변경: 종전에는 `u_xy is None or r_xy is None → continue` (항목 자체 생략).
신규: **한 측만** 무효면 그 측 전신 폴백으로 항목을 살린다 (belle 요구 3 — 엉뚱한 확대보다 전신).
양측 다 무효면 전신 vs 전신도 정보가 없으므로 기존처럼 skip.

**테스트 (backend/tests/test_fault_zoom.py 확장 — 기존 6개 무수정 PASS 필수):**
- `_report` fixture 에 confidence 옵션 추가 (기본 부재 = legacy 하위호환 경로 검증 유지).
- grouping: 4 leg fault joints (kind 전원 'deficit') → comps 1개, `region == "legs"`,
  `deficitDeg == max`, PNG 시그니처 유효. 좌측만(left_hip+left_knee) → grouping 안 됨(2개 카드).
  kind 혼재(improved+worsened) → grouping 안 됨.
- frame override: 프레임마다 색이 다른 `_frames` 특성 이용 — `user_frame_idx=7` 전달 시 user crop
  픽셀색이 frame 7 색인지 assert (기존 test_build_uses_dtw_match_for_ref_frame 패턴 재사용).
  ref_frame_idx override 도 동일 검증. override 시 dtw_match 가 있어도 override 가 이긴다.
- low-conf 폴백: ref report 에 confidence=0.1 주입 → 항목이 skip 되지 않고 생성되며 PNG 유효
  (전신 폴백). 양측 다 무효 → skip.
- `_group_fault_joints` 순수 helper 직접 단위테스트 (대표 joint 안정성 = fault_joints 순서 첫 멤버).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && python -m pytest tests/test_fault_zoom.py -q</automated>
  </verify>
  <done>기존 6 테스트 무수정 PASS + 신규 grouping/override/폴백 테스트 PASS. fault_zoom.py 는 여전히 순수(PIL/numpy 만). 시그니처 default 가 기존 호출 100% 하위호환.</done>
</task>

<task type="auto">
  <name>Task 2: pipeline 배선 (sourceFrameIndices → crop 프레임) + TS 계약/캡션 (region '양다리')</name>
  <files>backend/functions/pipeline/app.py, app/src/types/analysis.ts, app/src/lib/deductionLabels.ts, app/src/components/FaultZoomCompare.tsx</files>
  <action>
**Backend 배선 (`_attach_fault_zoom_comparisons`, app.py ~2500):**
`vv.get("windowMedianAngleDeltas")` 에서 `sourceFrameIndices` 를 읽어 각-측 median 을 crop 프레임
override 로 전달한다:
- `sfi = (vv.get("windowMedianAngleDeltas") or {}).get("sourceFrameIndices") or {}`,
  `u_list = sfi.get("user") or []`, `r_list = sfi.get("reference") or []`.
- 둘 다 비어있지 않으면 `user_frame_idx = int(sorted(u_list)[len(u_list)//2])`,
  `ref_frame_idx = int(sorted(r_list)[len(r_list)//2])` (window 중심 = 측정 median 프레임, 9fps 공간 —
  Task 1 조사 확정 근거를 주석으로 박제: angles 행 = 9fps frames, vision_veto.py:486 정합).
- 이 override 는 `fault_joints` 가 **vv.faultJoints 에서 온 경우에만** 적용 (편차 top-2 폴백 경로는
  vision 측정 프레임과 무관하므로 기존 worst_seconds 경로 유지). 부재/legacy doc → None 전달 =
  기존 동작 (하위호환).
- `_render_fault_zoom` 시그니처에 `user_frame_idx=None, ref_frame_idx=None` passthrough 추가 →
  `build_fault_zoom_comparisons(..., user_frame_idx=..., ref_frame_idx=...)`.
- 방출 item 에 comp 의 `region` 이 있으면 `item["region"] = c["region"]` 추가 (scalar —
  `_validate_dict_only_scalars` flat 제약 통과).
- `_attach_mode3_fault_zoom` 은 **무변경** (override 인자 안 씀 — default None 으로 기존 경로;
  grouping 은 Task 1 의 kind-동일 조건에 의해 mode3 improved/worsened 혼재 시 자동 비활성).
- 점수/veto/deduction 로직 라인 무접촉 — `_attach_*`/`_render_fault_zoom` 내부만.

**TS 계약 (app/src/types/analysis.ts — FaultZoomComparison, ~line 430):**
`region?: 'legs' | 'arms' | null;` 옵션 필드 추가 + 주석: "같은 결함에서 온 좌+우 관절 묶음 카드
(스플릿=양다리). Python lockstep: fault_zoom.build_fault_zoom_comparisons + pipeline
_render_fault_zoom. list 필드 금지(Firestore flat 제약)라 scalar region 만." 옵션 필드라
normalize(userAnalyses.ts) 변경 불요 — result passthrough 그대로, legacy doc(region 부재) 호환.

**캡션 (app/src/lib/deductionLabels.ts + app/src/components/FaultZoomCompare.tsx):**
- deductionLabels.ts 에 `export const REGION_LABEL_KO: Record<string, string> = { legs: '양다리', arms: '양팔' };`
  추가 (JOINT_LABEL_KO 와 같은 단일 출처 파일 — B 작업이 방금 수정한 파일이므로 최신 HEAD 확인 후
  append. 기존 export 무수정).
- FaultZoomCompare.tsx `caption()`: `const label = (item.region && REGION_LABEL_KO[item.region]) || JOINT_LABEL_KO[item.joint] || '문제 부위';`
  — region 카드가 "양다리 · 기준보다 30° 부족해요" 로 나오게. carousel key(item.joint)는 grouped
  멤버가 개별 카드에서 제거되므로 충돌 없음 (Task 1 보장). 이모지 금지, theme 토큰 외 스타일 무변경.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && python -m pytest tests/test_fault_zoom.py -q && cd /Users/kimtaesung/Dev/SunityMotion/app && npm run typecheck</automated>
  </verify>
  <done>typecheck clean + fault_zoom 테스트 PASS. _attach_fault_zoom_comparisons 가 sourceFrameIndices median 을 override 로 전달하고 region 을 방출. mode3 경로/점수 로직 diff 0 라인. legacy doc(region·windowMedianAngleDeltas 부재)에서 기존 동작 보존.</done>
</task>

</tasks>

<verification>
- `cd backend && python -m pytest tests/test_fault_zoom.py -q` — 기존 6 + 신규 전부 PASS.
- `cd app && npm run typecheck` — clean.
- `git diff` 검사: deduction/veto/kismam/dimensions 등 채점 모듈 무접촉, fault_zoom.py + pipeline
  `_render_fault_zoom`/`_attach_fault_zoom_comparisons` + 프론트 3파일만.
- SUMMARY 에 belle 실기기 체크리스트 박제 (아래 success_criteria).
</verification>

<success_criteria>
- kip-up fault 재분석 시(belle pod 재실행 필요 — 저장된 PNG 는 재생성 안 됨) carousel 이:
  (a) 스플릿 결함 = "양다리" 카드 1장 (dot 4개 → 1~2개), (b) 좌/우 crop 이 같은 측정 모먼트
  (user 프레임 ~20 / ref 프레임 ~37, 9fps)의 다리 부위를 보여주거나, keypoint 저신뢰 측은 전신 표시,
  (c) 캡션 "양다리 · 기준보다 30° 부족해요".
- 기존 doc(재분석 전)은 기존 이미지/캡션 그대로 표시 (crash 0, region 부재 호환).
- mode3 비교(improved/worsened) 기존 동작 보존.
- belle 실기기 체크리스트 (SUMMARY 에 포함):
  1. kip-up fault 영상 Mode1 재분석 → 확대비교 카드 수/캡션/좌우 부위 일치 확인
  2. 정은지 success 영상 1개 재분석 → 확대비교 섹션 회귀 없음 (veto 미발동이면 편차 top-2 경로)
  3. 기존 분석(af8fb8c8...) 결과 화면 재진입 → crash 없음
</success_criteria>

<output>
Create `.planning/quick/260702-sic-crop-fix-reference-crop-crop/260702-sic-SUMMARY.md` when done.
</output>

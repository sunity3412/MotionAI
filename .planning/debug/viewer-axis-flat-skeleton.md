---
slug: viewer-axis-flat-skeleton
status: awaiting_human_verify
trigger: "Phase 31 실기기 버그(belle TestFlight) — 참고하세요 > 자세 비교 카드의 2D 스켈레톤이 사람 형태가 아니라 가로 일직선으로 뭉개져 그려짐. 31-DEBUG-HANDOFF.md §1 인계 (원인 실측 확정, 수정 미적용)."
created: 2026-07-20
updated: 2026-07-20
phase: 31-api-visual-correction
goal: find_and_fix
tdd_mode: false
---

# Debug: viewer-axis-flat-skeleton — 2D 비교 뷰어 가로 막대 뭉개짐

인계 원본: `.planning/phases/31-api-visual-correction/31-DEBUG-HANDOFF.md` §1 (2026-07-20 세션 종료 시점 작성)

## Symptoms

DATA_START

- **Expected**: 참고하세요 > 자세 비교 카드에서 사용자/기준(정은지) 양쪽 스켈레톤이 사람 형태로 그려져야 함.
- **Actual**: 카드는 뜨지만 스켈레톤이 **가로 일직선**으로 깔림 (belle 실기기 스크린샷 확인). 세로 좌표가 전 관절 상수라서 한 줄로 뭉개진 형상.
- **Error messages**: 없음 — 시각적 finding만. 단위 테스트 전부 통과, 12라운드 외부 리뷰도 통과한 코드.
- **Timeline**: Phase 31 결정론 산출물 OTA(`65a907a3` → 수정 1차 `c7acf831`) 배포 후 belle 실기기 확인에서 발견. 이 카드 자체가 phase 31 신규 기능이라 "이전엔 됐다"는 없음.
- **Reproduction**: belle 분석 `2f68dcb38c7c4479b64ec6a61690c64a` (frame 34) / 기준 `ref-power-spin` (frame 90) 실측으로 재현 데이터 확보 완료 (아래 표).

DATA_END

## Known Facts (인계 실측 — 재검증 불필요한 확정 사실)

**원인 확정 (실측):** `app/src/components/PoseCompareViewer.tsx:28-29`

```ts
const AXIS_H = 0;   // 화면 가로 = x
const AXIS_V = 2;   // 화면 세로 = z  ← 문제
```

주석 근거: "joints3d(pole_aligned)는 수직 분산이 Z축에 있다 (z spread ~235, x ~95, y≈0)" — 그런데 **실제 데이터는 정반대**:

| 축 | 사용자 spread (2f68dcb3… f34) | 기준 spread (ref-power-spin f90) |
|---|---|---|
| axis0 (x) | 66.03 | 99.13 |
| axis1 (y) | 79.01 | 175.85 |
| **axis2 (z)** | **0.00** | **0.00** |

z가 전 관절 0 → 세로 좌표 상수 → 한 줄. 주석이 경고한 바로 그 현상인데 축을 반대로 골랐다.

- 2026-07-20 현재 코드 확인: `AXIS_V = 2` 그대로 (미수정). 사용처는 `PoseCompareViewer.tsx:86-87` (`p[AXIS_H]`, `p[AXIS_V]`).
- **추정 수정: `AXIS_V = 1` (y).** RTMW가 2D 백본이라 joints3d가 `(x, y, 0)`으로 저장되는 것으로 보임.
- 주석의 "z spread ~235"는 **구 R3F 뷰어(NLF 3D 시절)** 근거일 가능성 — NLF→RTMW 전환으로 무효가 됐는데 주석만 남았을 수 있음.
- 세로 방향 부호: 31-08이 "어깨 중점이 고관절 중점보다 화면 위"로 런타임 결정하게 해뒀으므로 **축만 바꾸면 부호는 자동 처리**될 것.
- 같은 뷰어의 프레임 인덱스 버그(기준 인덱스를 사용자 프레임 수로 환산 → null → 뷰어 통째 숨김)는 `13685cc`에서 이미 수정·배포됨. 이번 건과 별개.

## Live 환경

- OTA 4회 발행: `65a907a3` → `c7acf831` (수정 1차) → `e5a4f177` (축 수정, `89402fc`) → `138ec235` (프레임 시점+로딩 100%, `b0f1d52`). Pod `xps7co0m2njzpi` (4090) 가동 중, `/health` 200, repo `4f13092`.
- 백엔드 회귀 baseline: 57 failed / 3366 passed / 수집오류 2 (`--continue-on-collection-errors` 필수). 이 baseline 악화 금지.

## Current Focus

hypothesis: "확정(코퍼스 실측으로 갱신) — 저장 joints3d의 축 의미는 문서별로 두 세대가 공존한다: y-era(z≡0, 세로=axis1 — 현 Pod, scipy 부재로 정렬 no-op)와 z-era(y≡0, 세로=axis2 — 정렬이 실행되던 환경 산출). reference 11건 = 6 y-era + 5 z-era. 상수 AXIS_V는 어느 값이든 한 세대를 평평하게 만든다. 올바른 수정 = 포즈별 런타임 세로축 선택(axis1 vs axis2 중 분산 있는 쪽 — 모든 실측 문서에서 정확히 한 쪽이 상수 0이라 무모호)."

test: "완료 — 하네스 v2 전부 PASS (y-era 1/1 · 혼합 1/2 · z-era 2/2 · 코퍼스 sweep 5,674프레임 무모호 · SVG 시각 확인 · typecheck clean)"

expecting: "달성 — 세 쌍 모두 yExtent>10, 17관절 유한, 어깨<고관절, 축 선택 기대값 일치."

next_action: "CHECKPOINT(human-verify) — belle 실기기 확인 대기 (OTA 138ec235, 재실행 2회). 확인 항목: ①기존 파워스핀 55점(mode1) 분석의 자세 비교 카드가 영상 속 시점과 일치하는 전신 자세인지 ②climb 또는 invert 기준 mode1 1건도 정상인지 ③다음 분석에서 로딩이 100% 표시 후 넘어가는지. 확인되면 /gsd-debug continue viewer-axis-flat-skeleton 으로 archive_session. 그다음 /gsd-code-review 31 (인계: force_signals tilt≡0 후보 + 축 의미 백엔드 고정 사안 + 뷰박스 클리핑)"

reasoning_checkpoint:
  hypothesis: "PoseCompareViewer AXIS_V=2가 실환경에서 상수 0인 z축을 화면 세로로 투영해 전 관절이 같은 세로 좌표를 얻는다 — 스켈레톤이 가로 일직선으로 붕괴한다. 실환경 세로 분산은 axis1(y, 이미지 세로)이다."
  confirming_evidence:
    - "실측(인계, 문서 2건 독립): 사용자 2f68dcb3 f34 spread x66.03/y79.01/z0.00, 기준 ref-power-spin f90 x99.13/y175.85/z0.00 — z 전 관절 정확히 0"
    - "구조적: rtmw_engine.py:231-233 'z 좌표 없으면 0 으로 패딩' kps_3d=np.zeros((133,3)) — rtmlib 2D 백본, z는 원천에서 0"
    - "구조적: 프로덕션 pole_axis = (0,1,0) vertical_fallback (pipeline/app.py:4024) + aligner TARGET_AXIS=[0,0,1] (aligner.py:26) — 정렬이 실행됐다면 y분산이 z로 회전해 z spread ≈175가 됐어야 함. 측정 z≡0 → 정렬 미실행"
    - "연역: adapter의 정렬 실패 경로는 except ImportError 하나뿐(rtmw_133_to_coco17.py:253). 다른 예외면 분석 자체가 크래시(완료된 분석과 모순), 정렬 성공이면 z에 분산(측정과 모순). 유일 생존 경로 = scipy 부재 ImportError 폴백 = 원시 (x,y,0) 복사. runpod_inference/requirements.txt에 scipy 없음"
    - "앱 경로 축 보존: reshapePose3dData→normalizeFrames는 평행이동+스케일만(축 교환/부호 반전 0), reference측 reshapeJoints3d는 원시 그대로 — 뷰어 입력까지 axis1=세로, axis2≡0 유지"
    - "주석 출처 확정: 'z spread ~235, y≈0'은 c49a075(2026-06-20, phase 20 구 R3F 뷰어 flat-line 수정)의 실측 — 정렬이 실제 수행되던 당시 환경의 축 의미. 현 프로덕션과 정반대"
  falsification_test: "실데이터 프레임에 AXIS_V=1 적용해도 세로 분산이 복원되지 않거나(y도 상수), 다른 분석 문서 표본에서 z spread가 0이 아닌 문서가 발견되면(현 Pod 산출인데도) 가설 기각 → [결과] 후자가 실제 발생: 코퍼스 스캔에서 z-era 문서 발견 — '상수 교정으로 충분' 부분이 기각되어 Eliminated에 기록, 수정을 런타임 축 선택으로 갱신. 갱신된 반증 조건: 포즈별 spread 비교로도 사람 형태가 안 나오는 실측 문서(양축 동시 0 또는 동시 분산인데 오판)가 나오면 기각"
  fix_rationale: "[코퍼스 실측으로 갱신] 축 의미가 문서 세대별로 다르다는 것이 측정 사실이므로, 컴파일타임 상수라는 가정 자체가 원인이다. 수정 = 포즈별 런타임 세로축 선택(axis1/axis2 중 분산 있는 쪽 — 실측 전 문서에서 나머지 한 축은 정확히 상수 0이라 무모호). 31-08 vSign(부호 런타임 결정)과 같은 설계 철학의 축 버전이고, phase 20 c49a075가 구 뷰어 같은 증상을 같은 방식으로 고친 선례. 혼합 세대 쌍(구 분석 × 현 참조)도 포즈별 선택이라 자동 처리"
  blind_spots: "①Pod에 scipy 부재를 SSH로 직접 확인하지 않음(연역+requirements로 확정) ②향후 진짜 3D(양축 동시 분산) 데이터가 오면 '더 큰 분산' 선택이 눕거나 깊이가 큰 특수 자세에서 오판할 수 있음 — 현 코퍼스 0건, 주석에 명시 ③z-era 5건의 세로 부호(z'=±y)가 문서별로 다를 수 있으나 vSign이 포즈별 런타임 결정이라 흡수됨 — 하네스 혼합 쌍 검증으로 확인 예정"
tdd_checkpoint: null

## Evidence

- timestamp: 2026-07-20 (인계) — belle 분석 `2f68dcb38c7c4479b64ec6a61690c64a` f34 / `ref-power-spin` f90 실측: axis0 spread 66.03/99.13, axis1 79.01/175.85, axis2 0.00/0.00. z 전 관절 0.
- timestamp: 2026-07-20 (세션 시작) — 현재 워킹트리 `PoseCompareViewer.tsx:29` `AXIS_V = 2` 미수정 상태 확인.
- timestamp: 2026-07-20 — checked: rtmw_engine.py:231-233. found: "z 좌표 없으면 0 으로 패딩" `kps_3d = np.zeros((133, 3))`. implication: rtmlib 2D 백본 → keypoints_3d의 z는 원천에서 항상 0 (구조적 확정, 표본 불필요 — 확인 1).
- timestamp: 2026-07-20 — checked: pole/aligner.py. found: `TARGET_AXIS = [0,0,1]` — 설계 의도는 "폴 축 → Z축" (z=세로). implication: 뷰어의 AXIS_V=2 선택은 설계 문서 기준으론 옳았음. 문제는 설계가 프로덕션에서 실현되지 않는 것 (확인 2).
- timestamp: 2026-07-20 — checked: pipeline/app.py:4024-4029 + rtmw_133_to_coco17.py:247-256. found: 프로덕션 pole_axis = (0,1,0) vertical_fallback. adapter는 `except ImportError`시 원시 xyz 복사 폴백. compute_alignment_matrix는 scipy lazy import. implication: 정렬 실행됐다면 y분산이 z로 회전(z spread ≈175 기대) — 측정 z≡0과 모순 → 정렬 미실행. 유일 경로 = scipy ImportError (다른 예외는 분석 크래시, 완료된 분석과 모순).
- timestamp: 2026-07-20 — checked: runpod_inference/requirements.txt + setup.sh. found: scipy 명시 없음 (ultralytics 전이 가능성은 있으나 측정이 부재를 입증). implication: 현 lean Pod에서 pole 정렬 no-op → 저장 joints3d = 원시 이미지 좌표 (x, y_세로아래, 0), 라벨만 "pole_aligned".
- timestamp: 2026-07-20 — checked: git log -S "z spread". found: `c49a075` fix(20) "3D viewer front-view axis remap for degenerate-depth poses" — analyzeAxisSpread+remapFrameForFrontView, 2026-06-20. implication: "z spread ~235, x ~95, y≈0" 주석은 phase 20 구 R3F 뷰어의 실측 — 당시 환경(정렬 실행됨)의 축 의미. NLF 유물이 아니라 **scipy 유무로 축 의미가 이미 한 번 뒤집힌 이력** (확인 3). 같은 flat-line 증상을 구 뷰어는 런타임 spread 재매핑으로 고쳤었음.
- timestamp: 2026-07-20 — checked: 앱 데이터 경로 전체 (result.tsx:860-930, joints.ts reshapePose3dData→normalizeFrames, referenceMotions.ts reshapeJoints3d). found: 사용자측 normalizeFrames는 평행이동+스케일만(축 교환/부호 0), 기준측은 원시+NaN 통일만. implication: 뷰어 입력까지 axis 의미 보존 — axis1=세로, axis2≡0. AXIS_V=1이 양측 모두 옳다.
- timestamp: 2026-07-20 — checked: normalizePose vSign (PoseCompareViewer.tsx:105). found: `shoulderMid.y >= hipMid.y ? -1 : 1` — 런타임 데이터 결정. implication: 축 교체 후에도 자동 적응. 이미지 y(아래 증가)에서 정립 자세 어깨 y < 고관절 y → vSign=1 → 화면 위 (확인 4).
- timestamp: 2026-07-20 — checked: PoseCompareViewer 소비처. found: ReferenceCornerSection.tsx:142 단일. PoseViewer3D는 라우팅 없는 smoke 화면 전용. implication: 수정 blast radius = 파일 1개 상수 1개 + 주석.
- timestamp: 2026-07-20 — checked: force_signals.py:924-959 (형제 후보, 수정 아님). found: `_shoulder_tilt_pole_aligned`/`_hip_tilt_pole_aligned` = arcsin(|dz|/norm), has_pole_aligned 게이트는 dict 존재만 확인(z=0이어도 truthy). implication: 프로덕션 z≡0이면 tilt 항상 0° — "코드의 데이터 가정 vs 실제 보유 불일치" 동일 계열 후보. **이 세션 스코프 밖** → /gsd-code-review 31 인계 대상.
- timestamp: 2026-07-20 — checked: 시뮬레이터 실기 검증(Expo Go 54, iPhone 16 Pro). belle 재현 문서(2f68dcb3)를 시뮬레이터 uid(OXBmHmjTazccoYQzEVQxC3mUnWT2)로 admin 복사 후 결과 화면 딥링크 진입. found: 앱 기동·결과 화면 전체 렌더 정상(55점 실측 일치), 자세 비교 카드에서 사용자(빨강)·기준(회색) 스켈레톤 모두 사람 형태 — 가로 막대 붕괴 재현 없음. 형상이 실측 spread와 정합(사용자 x66/y79≈정방형, 기준 x99/y176≈세로형). implication: 수정이 실데이터 앱 경로 전체(Firestore 구독→reshape→뷰어)에서 유효. 부수 관찰: 참고 지표 카드 텍스트 겹침은 Expo Go 폰트 폴백 아티팩트로 판단(TestFlight 빌드는 폰트 내장) — 이번 변경과 무관.
- timestamp: 2026-07-20 — 커밋 `89402fc` (PoseCompareViewer.tsx + 이 세션 파일) push 완료 → OTA 발행: branch production, update group `e5a4f177-0d2d-42e2-8846-70ec5d84a830`, runtime 1.0.0, iOS update `019f7fe0-0883-731c-a9e6-f3019f79197b`. 롤백 시: `npx eas update:republish --group <직전 정상 group>` (직전 = c7acf831 발행분, `npx eas update:list --branch production` 으로 확인).
- timestamp: 2026-07-20 (belle 실기기 138ec235 이전) — **형제 버그 #2 belle 실기기 발견**: 축 수정(e5a4f177) 적용 후에도 빨간 스켈레톤이 뭉개진 삼각형. 실측 원인: 사용자 문서는 keypointReport 18fps(frames=166) / joints3d·angles 9fps(83) **이중 공간**인데 result.tsx 가 faultZoom userFrameIdx(kr 공간)를 anglesFrames 로 환산(항등) → joints3d[34](2배 뒤 시점, spread 66×79 뭉개진 자세)를 그림. 올바른 환산 34×83/166=[17] 은 spread 140×174 전신 자세(ASCII 실측). reference 11건은 kr==joints3d==angles 단일 공간 전수 실측 — ref 항등 매핑 무결. ★내 시뮬레이터 검증 기준이 "한 줄 아님"에 그쳐 이걸 통과시켰음 — 검증도 §4 패턴(실데이터 의미 대조 누락)에 당함.
- timestamp: 2026-07-20 — fix #2 적용: result.tsx userSrcFrames = keypointReport.frames 우선(부재/0 → anglesFrames → 항등 폴백, 구 doc 불변). useMemo deps 에 keypointReport 추가. 시뮬레이터 재검증(강화 기준: 영상 시점 일치): 빨간 스켈레톤 전신 복원, ASCII[17] 형상과 일치. 커밋 `26fc9f9`.
- timestamp: 2026-07-20 — 동반 수정: 로딩 진행률 55% 점프(belle 동일 세션 보고). 원인: 진행률이 실측 229.6s 기준 시뮬레이션인데 파이프라인 고속화로 done 이 링 ~55% 시점 도착 → done 즉시 체크 화면 전환이라 100% 미표시. 분석 자체는 서버 완결 확인(c027e7bc done 55점 전 필드 정상 — 덜 끝난 것 아님). fix: done 후 700ms 링 100% 유지 → 체크 화면 → 전환(총 1.6s). 시뮬레이터 실캡처(100% 링 확인). 커밋 `b0f1d52`.
- timestamp: 2026-07-20 — OTA 재발행: update group `138ec235-814a-4c3d-a275-45bf877afcea` (커밋 b0f1d52). 직전 정상 group = e5a4f177 (축 수정만 포함).
- timestamp: 2026-07-20 — checked: 실데이터 하네스 1차 (verify-viewer-axis.mjs, 읽기 전용). found: ①인계 실측 정확 재현 (user f34 66.03/79.01/0.00, ref f90 99.13/175.85/0.00) ②프레임 선택 앱 동일 (userFrameIdx 34/refFrameIdx 90, 항등 매핑) ③AXIS_V=2 → 양측 yExtent 0.00 (버그 재현) ④AXIS_V=1 → user yExtent 35.14 / ref 112.01, 17관절 유한, 어깨(47.9)<고관절(50.0). implication: 실패 케이스에 한해 수정 유효 확인.
- timestamp: 2026-07-20 — checked: Firestore 코퍼스 z-스캔 + 축 의미 판별 (scan-axis-semantics.mjs). found: **reference 11건 = y-era 6건(z≡0: combo/elbow-twist-sister/kip-up/pdshape/peter-pan/power-spin) + z-era 5건(y≡0, z spread 149~198: climb/foxtop/foxtop-split/invert/sideway-spin)**. 분석 표본 14건 = y-era 11 + z-era 3 (pdshapeokr*, e2e 916203bb). true-3D(양축 동시 분산) 0건. implication: 저장 axis 의미가 처리 시점 환경(scipy 유무 = 정렬 실행 여부)에 따라 문서별로 다르다. 상수 축은 어느 값도 전 코퍼스에 옳을 수 없음 → **뷰어측 올바른 최소 수정 = 포즈별 런타임 세로축 선택** (두 후보 중 정확히 한 축이 상수 0이므로 판별 무모호). phase 20 `c49a075`가 같은 증상을 같은 방식(remapFrameForFrontView)으로 고친 선례.
- timestamp: 2026-07-20 — observed (스코프 밖 메모): AXIS_V=1 시 ref power-spin f90 yExtent=112 > VIEW 100 — 완전 신전 자세는 몸통 26유닛 기준 ~4.3배라 뷰박스를 살짝 넘어 상하단 클리핑 가능. 31-08 사이징 설계 파라미터(TORSO_UNITS) 사안이며 이번 버그와 별개 — 보고만.

## Eliminated

- hypothesis: "수정 = AXIS_V=1 상수 교정으로 충분 (인계 추정 — 모든 문서가 (x, y, 0))"
  evidence: "Firestore 전수/표본 스캔 실측 — reference 11건 중 5건(ref-climb/foxtop/foxtop-split/invert/sideway-spin)은 z-era (y≡0, z spread 149~198), 6건은 y-era (z≡0, y spread 128~252). 분석 문서에도 z-era 존재 (pdshapeokr*, e2e 916203bb). AXIS_V=1 상수는 belle 재현 케이스(power-spin)를 고치는 대신 z-era 5건을 평평하게 만든다 — 상수는 어느 값이든 라이브러리 절반을 깬다. true-3D 케이스는 0건 (모든 문서가 두 축 중 정확히 한 축이 상수 0)."
  timestamp: 2026-07-20

## Resolution

root_cause: "PoseCompareViewer가 세로축을 컴파일타임 상수(AXIS_V=2)로 고정했으나, 저장 joints3d의 축 의미는 문서별로 두 세대가 공존한다 — ①y-era(세로=axis1, z≡0): RTMW 2D 백본이 z를 0 패딩(rtmw_engine.py:233)하고 현 Pod에 scipy가 없어 폴 정렬(y→z 회전, aligner TARGET=[0,0,1], 프로덕션 pole_axis=(0,1,0) fallback)이 ImportError로 no-op(rtmw_133_to_coco17.py:253-256) ②z-era(세로=axis2, y≡0): 정렬이 실행되던 환경 산출(reference 5건 + 구 분석). belle 재현 케이스(power-spin=y-era)에서 상수 z축(≡0)을 세로로 투영 → 전 관절 같은 세로 좌표 → 가로 일직선. '한 축이 상수'라는 데이터 현실은 파일 자신의 주석이 경고했으나 그 주석의 실측치는 z-era 환경(c49a075, phase 20)의 것이라 축을 반대로 골랐다."

fix: "AXIS_V 상수 폐기 → 포즈별 런타임 세로축 선택 pickVerticalAxis(axis1/axis2 중 분산 큰 쪽 — 실측 전 코퍼스에서 나머지 한 축이 정확히 상수 0이라 무모호). 사용자/기준이 서로 다른 세대여도 각자 옳은 축을 고른다. 31-08 vSign(부호 런타임 결정) 보존 — 축 선택 후 자동 적응. 주석 2곳(헤더 + 투영축 블록)을 두-세대 실측 근거로 교체. phase 20 c49a075(remapFrameForFrontView)와 같은 해법 계열."

verification: "읽기 전용 Firestore 하네스 (scratchpad/verify-viewer-axis{,-v2}.mjs + scan-axis-semantics.mjs): ①인계 실측 정확 재현 ②구 코드로 버그 재현(yExtent 0.00) ③수정판: y-era 쌍(axisV 1/1)·혼합 쌍(1/2)·z-era 쌍(2/2) 전부 PASS — 17관절 유한, yExtent>10, 어깨<고관절 ④전 코퍼스 sweep 5,674프레임(reference 11건 전 프레임 + 분석 14건 표본): 양축동시분산 0, 양축동시0 0 — 선택 무모호 ⑤SVG 시각 산출물 2장: 관절 있는 사람 형태, 평평 소멸 ⑥tsc --noEmit clean. 시뮬레이터/OTA는 이 세션 스코프 밖 — OTA 전 시뮬레이터 기동은 다음 세션 몫([[verify-ui-on-simulator-before-ota]]), 최종 확정은 belle 실기기."

files_changed:
  - "app/src/components/PoseCompareViewer.tsx (단일 파일 — AXIS_V 상수 → pickVerticalAxis 런타임 선택 + 주석 2곳 실측 근거로 교체)"

## Constraints / Out of Scope

- **검증 수단**: 단위 테스트·12라운드 리뷰가 이 계열 3건을 모두 통과시켰다 — **실데이터 프레임 + 시뮬레이터 렌더 확인이 유효한 검증**. UI 변경은 시뮬레이터 확인 후에만 OTA (이 맥에 Xcode 26.6+시뮬레이터 있음, expo-updates는 재실행 2회째 적용). OTA 발행 자체는 이 세션 밖 — 수정+검증까지가 스코프.
- **형제 버그 수색은 이 세션 밖**: "코드의 데이터 가정 vs 실제 보유 불일치" 계열 수색은 후속 `/gsd-code-review 31` 담당 (인계 §4·§5).
- **목표 각도 화살표 버그는 32로 이월** (belle 결정, 인계 §3) — 건드리지 말 것.
- 수정은 최소 단위 — 축 상수 교정 + 필요 시 낡은 주석 교정. 31-08 부호 자동결정 로직 보존.

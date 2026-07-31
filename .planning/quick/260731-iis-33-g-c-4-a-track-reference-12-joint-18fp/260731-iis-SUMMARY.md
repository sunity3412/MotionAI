---
phase: quick-260731-iis
plan: 01
subsystem: reference-library / fault-zoom
tags: [33-G, C-4, reference-keypoint-report, angle-bake, fault-zoom, firestore]
requires: [quick-260731-f5h, quick-260730-l7t, phase33-cm3-run1]
provides: [기준 11동작 18fps 12관절 표시 보고서, flip 방어, 실 doc 재산출 4건]
affects: [app 기준 오버레이(OTA 없이 즉시), fault_zoom 각도 베이크, 33-G 재채점]
tech-stack:
  added: []
  patterns: [단일 필드 set(merge=True), all-or-nothing 게이트, 백업→dry-run→write→재조회]
key-files:
  created:
    - .planning/quick/260731-iis-.../measure_ref_state.py
    - .planning/quick/260731-iis-.../write_ref_kp_report.py
    - .planning/quick/260731-iis-.../reanalyze_render_docs.py
    - .planning/quick/260731-iis-.../sweep_real_ref.py
    - .planning/quick/260731-iis-.../pod_extract_wrapper.py
    - .planning/quick/260731-iis-.../judgment_s10_s5_s22.md
  modified:
    - backend/scripts/reprocess_reference_motions_phase4.py
    - backend/tests/phase33/test_candidate_staging.py
    - .planning/phases/33-result-trust-recovery/33-G-MOCKUP-DIFF.md
decisions: [flip 방어는 candidate 폴백까지 넣어야 실제 동작, 스위프 표시 프레임은 select_confident_frame 로 선택, 재산출은 sweep_phase15 direct-process 경로 재사용]
metrics:
  duration: 약 3시간
  completed: 2026-07-31
---

# quick-260731-iis: 33-G §C-4 A-트랙 (기준 12관절 18fps) Summary

기준 라이브러리의 **표시용** keypoint 보고서를 실 12관절 18fps 로 교체해 무릎·팔꿈치 각도
베이크를 원리적으로 막던 유일한 원인(기준 8관절)을 제거하고, S10 을 실 doc 에서 판정했다.

---

## 최상단 3줄 (belle 확인용)

1. **Pod 는 지금 꺼도 됩니다.** T3 까지 GPU 작업이 전부 끝났고 정지 전 체크리스트 5항목이 전부
   충족됐습니다(아래 표). **stop(정지)** 을 쓰세요 — `/workspace` 는 Network Volume 이라 남습니다.
   **terminate(삭제)** 하면 볼륨 연결이 끊기고 `bootstrap_full.sh`·`start_server.sh`·`aws_env.sh`·
   `_s3stage/`(735M) 가 사라집니다. Pod = `gwa4jn3lq4tb21`.
2. **되돌리는 명령 한 줄** (Pod 에서):
   `bash /workspace/rk.sh --restore --backup-file /workspace/refkp_backup.json`
   (백업 원본 11건 = `refkp_backup.json`, 로컬에도 1.98MB 사본 있음)
3. **이 교체는 OTA 없이 앱에 즉시 반영됩니다.** `app/src/lib/referenceMotions.ts:107` 이
   `reference/{id}` top-level 을 직독하기 때문입니다. 보이는 변화 = **기준 패널 오버레이 관절이
   8개에서 12개로 늘어남**(가산적). 점수·문구는 무접촉입니다.

---

## Pod 정지 전 체크리스트 (T3 종료 시점 판정)

| # | 항목 | 판정 | 어떻게 알았나 |
|---|---|---|---|
| 1 | `reference-kp-18fps.json` 로컬 · 11/11 · joints 12 · fps 18.0 | OK | 로컬 파일을 파싱해 값을 찍었다 |
| 2 | 추출 로그 `refkp_18fps.log` 로컬 회수 | OK (75줄) | 파일 크기·줄 수 확인 |
| 3 | 재산출 4건 Firestore `status == done` | OK | `docs_after/*.json` 4건 status 파싱 |
| 4 | `docs_after/` 4건 + `zoom_after/` 12장 로컬 회수 | OK | `ls` 로 개수 확인 |
| 5 | Pod 전용 파일 = 볼륨 잔존 (stop 안전) | OK | `/workspace` 목록 확인 |

---

## 게이트 결과

| 게이트 | 결과 | 성립시킨 행위 |
|---|---|---|
| **GATE-C** 릴리스 포인터 | **통과** — `reference/_release` 문서 **부재**(activeCandidate None) | Pod 에서 Firestore 직접 조회. **쓰기 직전에 한 번 더** 재확인 |
| **GATE-A** 타임베이스 | **11/11 통과** (all-or-nothing) | dry-run 표. fps 18.0 / 12관절 / `frames == anglesFrames` / `len(data)==f·j·2` / NaN 0 / `_validate_keypoint_report` 통과 |
| **GATE-B** 점수 무접촉 | **11/11 불변** | 쓰기 후 **재조회**. 채점 8필드 해시(`_release_doc_hash` **import**) BEFORE==AFTER, `activeVersion` 불변, `_release.activeCandidate` 불변 |

**롤백 왕복 실증 (ref-kip-up 1건)** — `--restore` → 재조회(18.0/118/**8**, 원본 형상 복귀 확인)
→ `--write` → 재조회(18.0/118/**12**). 세 상태 내내 채점 해시 `a352fb1e038570cf` **동일**.
문장이 아니라 값으로 남겼다.

---

## BEFORE → AFTER (11동작)

| motion | anglesFrames | BEFORE fps/frames/J | AFTER fps/frames/J | 채점해시 | activeVersion |
|---|---|---|---|---|---|
| ref-sideway-spin | 298 | 18.0/298/8 | 18.0/298/12 | 불변 | phase4_v1 불변 |
| ref-climb | 257 | 18.0/257/8 | 18.0/257/12 | 불변 | phase4_v1 불변 |
| ref-invert | 260 | 18.0/260/8 | 18.0/260/12 | 불변 | phase4_v1 불변 |
| ref-foxtop | 426 | 18.0/426/8 | 18.0/426/12 | 불변 | phase4_v1 불변 |
| ref-foxtop-split | 485 | 18.0/485/8 | 18.0/485/12 | 불변 | phase4_v1 불변 |
| **ref-combo** | 931 | **9.0/466/8** | 18.0/931/12 | 불변 | phase4_v1 불변 |
| ref-elbow-twist-sister | 329 | 18.0/329/8 | 18.0/329/12 | 불변 | phase4_v1 불변 |
| ref-kip-up | 118 | 18.0/118/8 | 18.0/118/12 | 불변 | phase4_v1 불변 |
| ref-pdshape | 237 | 18.0/237/8 | 18.0/237/12 | 불변 | phase4_v1 불변 |
| ref-peter-pan | 130 | 18.0/130/8 | 18.0/130/12 | 불변 | phase4_v1 불변 |
| ref-power-spin | 159 | 18.0/159/8 | 18.0/159/12 | 불변 | phase4_v1 불변 |

**`ref_display_frame_index` 배율 = 11/11 모두 1.0(identity)** 로 수렴했다.
docstring 이 "올바른 재처리 ref 면 rep9_n == ref_video_n → 배율 1.0" 이라 적어둔 조건이 실제로
성립했다(종전 4/3 왜곡 소멸). 조정한 게 아니라 재조회 값이 그렇게 나왔다.

---

## 데이터가 플랜과 안 맞은 것 (재논의 아님 — 보고)

### 1. `ref-combo` 는 교체 **전부터** 깨져 있었다
표시 보고서가 9.0fps/466프레임인데 `anglesFrames` 는 931. 그 동작만 표시 타임베이스가 채점의
**절반**이었다(28-RESEARCH D2 형상). 오케스트레이터 실측 2건(ref-climb·elbow-twist)에는 안
잡혔던 것이고, 이번 교체가 **부수적으로 고쳤다**. 나머지 10동작은 원래 정합이었다.

### 2. 렌더 doc 4건은 `/analyze` 로 재분석할 수 없었다
플랜은 `POST /analyze` 에 `uploads/{uid}/{analysisId}.{ext}` 키를 보내라고 했으나, 실측하니
그 doc 들의 키 필드는 `key` 가 아니라 **`videoKey`** 이고 값이
`fixtures/phase15/{motion}/{fault|correct}.mp4` 였다. `server.py:447` 이 `parse_upload_key` 로만
uid/analysisId 를 복원하므로 fixtures 키는 **라우팅 자체가 불가**하다.
→ 이 doc 들을 원래 만든 경로인 `backend/scripts/sweep_phase15.py --trigger direct-process`
(= `pipeline._process(bucket, sourceS3Key, uid, analysisId)` 직접 호출)를 **같은 관용구로 재사용**
했다. 신규 분석 path 0. `_load_pipeline` 도 그 스크립트와 동일하게 썼다.

### 3. faultZoom 필드 경로가 플랜 기술과 달랐다
`result.faultZoom` 이 아니라 **`result.faultZoomComparisons`** 이고,
`userVideoSec`/`refVideoSec` 는 `result` 최상위가 아니라 **카드 안**에 있다.
(처음 `result` 레벨로 읽어 "None" 을 보고 "미방출" 로 오판할 뻔했다 — 카드 키를 직접 찍어 정정.)

### 4. 재산출로 점수가 움직였다 (숨기지 않고 그대로)

| doc | 점수 | 카드 수 |
|---|---|---|
| powerspinFault | 80 → **60** | 5 → 4 |
| elbowtwistsisterFault | 60 → **63** | **0 → 5** |
| kipupFault | 79 → 79 | 3 → 2 |
| pdshapeCorrect | 100 → 100 | 2 → 1 |

기준 표시 보고서는 채점 무접촉(GATE-B 로 증명)이므로 이 이동분은 **RTMW/Gemini 재실행 편차**다.
특히 power-spin −20 은 작지 않다. 원인 분리는 이 플랜 범위 밖이며 **Phase 34(분석 일반화,
"같은 자세면 같은 점수")의 정확한 관측 대상**이다.
`elbowtwistsisterFault` 가 **0장 → 5장**이 된 것이 이번 트랙의 가장 큰 실 doc 효과다.

### 5. 스위프 하네스의 parity 게이트가 발화했다 (프로덕션 결함 아님으로 판단)
비-정중앙 카드 24건이 밴드(0.8~1.25)를 이탈(1.28~1.62). 임계를 **조정하지 않았다**.
원인을 수치로 특정: `user_side_px` 는 f5h 와 **완전 동일**(245/219 — 학생측 통제 변수 유지),
`ref_side_px` 만 230(합성 고정) → 151~253(실 해부)로 이동. 151 은
`floor_side = min(h,w) × _CROP_FRAC` **클램프**이며 14건이 여기 걸렸다.
즉 **합성 학생 × 실 기준** 이라는 프로덕션에 없는 조합의 산물이다.
다만 **실 doc 에서도 배율이 어긋나 보이는 카드를 1건 관찰**했다(elbow-twist 팔꿈치 — 기준
패널만 전신). → **실 doc parity 전수 확인을 §C-4 잔여로 올린다.** 안심으로 닫지 않았다.

---

## 각도 베이크 사유별 집계 (l7t/f5h → 이번)

| 사유 | f5h after | real-ref | 의미 |
|---|---|---|---|
| `drawn` | 21 | **79** | |
| `omitted:ref_gate` | 39 | **0** | **기준 8관절이 유일한 구조적 차단이었음이 증명됨** |
| `omitted:unmapped` | 30 | 30 | region criterion(arm/leg/split) — 각도 대상 아님, 불변 |
| `omitted:degenerate` | 0 | 1 | ref-invert 어깨, 세 점 겹침 |

계열별 `drawn`: 팔꿈치 **0→20** · 무릎 **0→20** · 어깨 **1→19** · 힙 20→20.

**원인 확정** — `ANGLE_BAKE_MAP` 은 `shoulder→(elbow,hip)`, `knee→(ankle,hip)`,
`elbow→(hand,shoulder)` 를 요구한다. 8관절 기준에는 **elbow·ankle 이 아예 없어서** 어깨·무릎·
팔꿈치가 전부 `ref_gate` 로 fail-closed 였고 힙만 살아 있었다(f5h 수치와 정확히 일치).
12관절이 되자 그 차단이 사라졌다. 추정이 아니라 맵과 관절 목록을 대조해 확인했다.

**회귀 0** — 정중앙 80장 `user_side_px==ref_side_px` 전건 일치(S9) · 각도 비대칭 0 ·
비결정 0 · `split_angle` 10/10 유지(S10) · INV-D1 위반 0 · 동작명 분기 0.

---

## 열람한 PNG 와 각각에서 본 것

**직접 Read 로 연 것 6장** (열지 않은 것은 아래에 명시):

| PNG | 본 것 |
|---|---|
| `zoom_after/kipupFault__zoom_split_angle.png` (실 doc) | **골반 꼭짓점 두 선 + 호, 두 패널 모두. 선이 실제 두 다리와 정합** — f5h 가 못 본 해부학적 정합이 실 doc 에서 성립 |
| `zoom_after/powerspinFault__zoom_split_angle.png` (실 doc) | 두 패널 모두 **원 마커 폴백**. crop 이 골반 주변으로 좁고 다리가 밖 |
| `zoom_after/powerspinFault__zoom_angle_vs_reference__left_shoulder.png` (실 doc) | **두 패널 모두 팔선+옆구리선+호**. 기준 패널에 각도가 그려진 것 자체가 8관절에선 불가능했던 산출 = S8 실 doc 실증 |
| `zoom_after/elbowtwistsisterFault__zoom_angle_vs_reference__left_elbow.png` (실 doc) | 학생 패널 원 마커, 기준 패널 전신·마커 없음. **각도 미베이크** + 두 패널 배율 상이 |
| `sweep_out/real-ref/ref-sideway-spin__angle_vs_reference__left_knee.png` | 무릎 각도 **선+호 그려짐**(두 패널) |
| `sweep_out/real-ref/ref-elbow-twist-sister__angle_vs_reference__left_elbow.png` | 통과율 약한 동작(L.elbow 0.529)에서도 팔꿈치 각도 **그려짐** — `select_confident_frame` 이 통과 프레임을 고르기 때문 |

⚠ **스위프 PNG 의 한계** — 배경이 목업 정지 이미지이고 좌표만 실 기준이라, 스위프 PNG 로는
**기하가 그려지는지**만 볼 수 있고 **해부학적 정합은 판정할 수 없다**(선이 배경 인물과 무관).
해부학적 정합은 실 doc PNG 에서만 판정했다.

**열지 않은 것** — 나머지 104장(스위프) + 6장(실 doc). 컨텍스트 절약을 위해 `summary.json`
수치로 판정했다. 통과율 약한 2동작 중 `ref-pdshape` 는 열지 않고 수치만 봤다.

---

## 기준측 게이트 통과율 (동작별, 전 프레임)

| motion | L.ankle | R.ankle | L.elbow | R.elbow | L.knee |
|---|---|---|---|---|---|
| ref-sideway-spin | 0.943 | 0.933 | 0.836 | 0.919 | 0.926 |
| ref-climb | 0.914 | 0.918 | 0.817 | 0.864 | 0.868 |
| ref-kip-up | 0.907 | 0.907 | 0.966 | 0.907 | 0.907 |
| ref-peter-pan | 0.800 | 0.746 | 0.669 | 0.723 | 0.785 |
| ref-foxtop-split | 0.629 | 0.602 | 0.687 | 0.656 | 0.629 |
| ref-invert | 0.596 | 0.638 | 0.661 | 0.681 | 0.642 |
| ref-power-spin | 0.547 | 0.579 | 0.616 | 0.786 | 0.535 |
| ref-foxtop | 0.514 | 0.538 | 0.645 | 0.603 | 0.498 |
| **ref-elbow-twist-sister** | **0.401** | 0.526 | 0.529 | 0.422 | 0.438 |
| **ref-pdshape** | **0.338** | 0.384 | 0.658 | 0.595 | 0.338 |

약한 2동작도 **동작을 빼지 않았다**. 통과율이 낮다 = 그릴 수 있는 프레임이 적다는 뜻이고,
`select_confident_frame` 이 통과 프레임을 고르므로 카드는 그려진다(위 PNG 로 확인).
프레임 단위 fail-closed 가 정상 동작한다.

---

## 열린 질문 해소: candidate `phase33-cm3-run1`

**실측값** — 11/11 에 `referenceKeypointReport` 존재, **9.0fps · 12관절**, 프레임 수는
top-level `anglesFrames` 의 **약 2/3** (ref-climb 172 vs 257, elbow-twist 220 vs 329,
combo 621 vs 931). candidate 자체의 `anglesFrames` 도 같은 9fps 공간이다.

**Phase 34 flip 판단에 주는 의미**: candidate 로 flip 하면 `angles` 가 9fps 공간으로 가고
candidate 의 표시 보고서도 9fps 라 **그 안에서는 정합**이다. 다만 지금 top-level 에 넣은
18fps 보고서를 그대로 두고 flip 하면 표시 18fps ↔ 채점 9fps 로 **어긋난다** — 이것이 33-07
잠복 버그의 실체이고, 이번에 넣은 flip 방어(candidate 폴백)가 flip 시 candidate 의 9fps
보고서를 top-level 로 동반 이동시켜 막는다. **candidate 는 이 플랜에서 고치지 않았다.**

---

## flip 방어의 실제 형태와 그것을 고른 측정 근거

**측정 먼저**: `_reprocess_one` 이 반환하는 payload 의 키를 코드에서 직접 확인했다 —
`_validate_payload_schema.REQUIRED_KEYS` 11개에 `referenceKeypointReport` 가 **없고**,
반환 dict 에도 없다(`backfill_reference_downstream.py` 가 candidate 문서에 나중에 MERGE 한다).
→ **`payload.get("referenceKeypointReport")` 1줄은 no-op** 이다. 그대로 뒀으면 "방어했다"가
거짓이 됐다.

**그래서 넣은 형태** (`backend/scripts/reprocess_reference_motions_phase4.py`):
payload 에 없으면 **candidate 버전 문서(`versions/{version}`)에서 읽어 폴백**하고, 양쪽 다
없으면 **값을 지어내지 않고 경고만** 남긴다(fail-closed). 기존 None 제거 규칙 앞에 놓아
그 규칙이 그대로 적용된다.

**테스트 3건** (`backend/tests/phase33/test_candidate_staging.py`) — payload 경로 / candidate
폴백 / 부재 시 보존+경고. **RED 를 먼저 확인**(2건 실패)한 뒤 구현했고 지금 15/15 통과.
**flip 은 실행하지 않았다** — Phase 34 몫.

---

## 미검증·미판정 (조용한 PASS 금지)

| 항목 | 판정 | 왜 못 봤나 | 어디서 볼 것 |
|---|---|---|---|
| S5 기본 화면 새 문장 | **미판정** | 문장 인벤토리는 실측했으나 어느 것이 **기본 화면**에 렌더되는지는 렌더 트리 + 목업 화면 대조 필요 | 시뮬, 점수 이동 doc 우선 |
| S22 멈춤 컷 | **부분 PASS** | 창 포함은 구조적으로 성립(수치+코드경로). 화면은 못 봄 — 멈춤 조건이 음성 발화 성공인데 F-6 무음 미해결 | belle 실기기 확인 ③ |
| S10 계약 4행 | **추정** | conf 원인은 제거했으나 crop box 가 doc 에 없어 crop 포함을 직접 못 쟀다 | crop box 방출 or 로그 재현 |
| S10 계약 5·6행 | **미관찰** | 표본 2건에 안 나타남. 없다고 단정하지 않음 | 더 많은 실 doc |
| S6 paircap · F-3 참고코너 | **초 방출 PASS / 화면 미확인** | 필드 방출은 실증. 화면 문자열·페어 일치는 렌더 필요 | 시뮬 |
| 실 doc parity | **미확인** | 하네스가 합성×실 조합이라 판정 불가. 실 doc 1건에서 배율 상이 관찰 | 실 doc 카드 전수 |
| 스위프 PNG 104장 | **미열람** | 컨텍스트 절약, 수치로 판정 | 필요 시 `sweep_out/real-ref/` |

---

## 회귀

- `pytest backend/tests` FAILED/ERROR **node ID 집합 diff 0** (f5h baseline 58건 == 이번 58건).
  숫자가 아니라 집합을 비교했다.
- `test_candidate_staging.py` **15/15** 통과 (기존 12 + 신규 3).
- `git diff -- app/ backend/functions/ backend/shared/ docs/` **0** — 표시 전용임을 확인.
- 동작명 분기 **0**. (플랜 verify 의 grep 은 4건을 잡지만 **전부 docstring 산문**이며 AST 로
  확인했다. 스위프의 엄격 게이트(`["']ref-`)는 0. `fault_zoom.py` 는 이번 사이클 diff 0.)

---

## 커밋

- `0485a2b` — `fix(quick-260731-iis): 33-07 flip 잠복 버그 방어 — 표시 보고서 동반 이동`
  (프로덕션 코드 변경은 이 1개 파일 + 테스트 1개가 전부)

`.planning/` 산출물(하네스·PNG·JSON·SUMMARY·33-G)은 실행자가 커밋하지 않았다.

---

## 자체 도출 결정

- **I-1** 스위프의 표시 프레임을 `select_confident_frame` + `_to_rep_idx` 로 고른다.
  f5h 의 `_identity(9)` 를 실 보고서(118~931프레임)에 그대로 쓰면 기준의 **앞 0.44초만** 보게
  되어 측정 대상이 아니게 된다. 변환식 복제 0.
- **I-2** Pod 의 boto3 `download_file`(멀티스레드)이 서울 GET 에서 행에 걸려 두 번 정지시켰다
  (임시파일 0바이트 4분+, GPU 0%). 단일 스레드 ranged GET 은 정상(566~1494 KB/s 실측).
  → 하네스 레벨 shim 으로 **S3 `ContentLength` 와 크기가 정확히 같을 때만** 로컬 스테이지를
  쓰고, 아니면 `use_threads=False` 로 받는다. 프로덕션 코드 변경 0.
- **I-3** 추출 실행에 `RTMW_ONNX_PATH`/`YOLOX_ONNX_PATH`/`LD_LIBRARY_PATH` 가 필요하다
  (`start_server.sh` 에만 있고 `aws_env.sh` 에는 없다). 재산출 러너도 `start_server.sh` 와
  **같은 env** 를 세팅했다 — env 가 다르면 재산출 조건이 원 doc 과 달라진다(통제 변수).

---

## 다음 단계

1. **§C-4 3번** — 어깨·팔꿈치 일러스트 신규 생성 (belle 07-31 지시, 별도 사이클).
   ⚠ 구도도 같이 — 현 에셋 82~89%가 빈 배경이라 belle #11 "빈 프레임"으로 읽힌다.
2. **§C-4 잔여(이번에 추가)** — 실 doc parity 전수 확인.
3. **일괄 OTA → belle 확인 ③** (D-45). 그전에 개별 배포 금지.
4. **Phase 34** — 재산출 점수 이동(power-spin −20)의 원인 분리. flip 판단도 여기.

---

## Self-Check: PASSED

산출물 22건(스크립트 5 · 문서 3 · JSON 6 · 로그 2 · 디렉터리 3 · 프로덕션 2 · 33-G 1) 전부
파일시스템에 존재 확인. 커밋 `0485a2b` git 이력에 존재 확인.

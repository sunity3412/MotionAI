---
quick_id: 260716-jg6
slug: phase22-v6-assemble-terra13-union-sft
title: phase22 v6 학습셋 assemble + terra13 union (SFT 입력 산출)
status: complete
date: 2026-07-16
commit: 40fe208
---

# Quick Task 260716-jg6 Summary

## 해소 (2026-07-16, belle 결정 후)

belle이 **(A) 7 recoveries 수용 → 업로드**를 승인. 게이트 2를 도메인상 올바른 불변식으로
교정(단순 완화 아님): `delta==0` 은 offered terra 가 전량 정당 드롭(dedup/계약위반)된
경우만 허용(조립 버그 무음 손실 차단) + `recoveries >= 7` 하한(수용 상태 고정). "8" 은
계약필터 미계산 추정치였음.

`assemble_v6.py --upload` 실행 → **S3 canonical 교체 완료(검증됨)**:
- 백업 `jsonl_v5_backup/` 생성(pre-v6 보존: perturb 169 / distill 152 / text 48).
- canonical `jsonl/` = v6: **perturb 0**(C1) / distill 149 / text 22 /
  **fault_bearing 88 · fault_free 61 · cap_ratio 1.5**(B) / validation_owner
  explicit_val_jsonl / partial False. train 13MB→4.2MB.
- 왕복 검증(_meta 재다운로드) 일치.

v6 = SFT canonical 입력. 다음 = belle Pod 기동 → SFT(런북 `260716-jg6-SFT-RUNBOOK.md`).

## 한 줄 요약

pre-v6 S3 학습셋의 distill 152행에서 소실된 accepted 라벨을 무손실 역복원 →
terra13 union(계약 안전장치 적용) → `full_batch.assemble_jsonl` 무변형 호출로 **로컬 v6
학습셋(train 168 / val 3 / _meta, distill 149 · perturb 0 · text 22, fault-bearing 88)을
산출**했다. 검증 8게이트 중 7개 PASS. **S3 업로드는 belle 결정 대기로 보류** — terra13
delta 게이트가 1영상(General-pole-movements)에서 계약 안전장치의 정당한 fault 드롭으로
"delta>0 each / 8 recoveries" 기대와 어긋난다(실측 7 recoveries, 12/13 delta>0).

## 무엇을 했나

- **복원**: 현재 S3 `training/phase22/jsonl/` 다운로드 → distill 152행(train 149 + val 3)
  에서 accepted 레코드(`video_hash`/`s3_key`/`motion`/`thought`/`report`/`joint_keys`/
  `coords_by_frame`) 역복원. assistant JSON 파싱 실패 0. RTMW_Data 는 `raw_decode` 로
  파싱(뒤 `_TASK_INSTRUCTION` 무시), s3_key 는 video URI prefix 제거, joint_keys 는 system
  대괄호 리스트 파싱. 152개 s3_key 전부 manifest join 성공(미매칭 0).
- **terra union**: terra_collect(149행)에서 `terra_fault_count > gemini_fault_count` 인
  13영상을 비교로 재도출(플랜 대조 목록과 정확히 일치). 각 video_hash 의 report.faults 에
  terra faults 를 append하되, **gemini faults 고정 + terra fault 개별 계약검증**
  (`schema.normalize_report` → `build_jsonl._faults_satisfy_contract`) 통과분만 채택.
  dedup: 동일 `(fault_category, body_part)` 는 gemini 우선.
- **assemble**: 복원 accepted → tmp `accepted/<slug>.json` → `full_batch.assemble_jsonl`
  (`manifest_with_hashes` + `build_dataset`, perturb_loader 미주입 → include_perturb=False
  C1, B cap·balance·video_hash split 전부 프로덕션 로직 무변형).
- **프로덕션 코드 0 수정** — `assemble_v6.py` 한 파일만 신규(전부 import 재사용).
  `git status` 상 backend/ 변경 0, pytest 273 passed 로 이중 확인.

## 검증 게이트 (belle certainty)

| # | 지표 | 기대 | 실측 | 판정 |
|---|---|---|---|---|
| 1 | fault_bearing / fault_free_count 방출 | _meta 방출, cap 1.5 | 88 / 61 (cap_ratio 1.5) | **PASS** |
| 1b | fault-free 드롭률 | — | **0%** (nf 61 ≤ cap 132 → 트림 불필요) | PASS (설명 하단) |
| 2 | terra13 delta>0 each + 8 recoveries | 13/13 delta>0, 8복구 | **12/13 delta>0, 7복구** | **DEVIATION** |
| 3 | track_counts.perturb == 0 (C1) | 0 | 0 | **PASS** |
| 4 | val∩train video_hash | ∅ | ∅ (교집합 0) | **PASS** |
| 5 | normalize round-trip 통과율 | 100% | 100% (파싱 실패 0/152) | **PASS** |
| 6 | pytest tests/phase22 | 273 passed | 273 passed, 1 skipped | **PASS** |
| 7 | 분포 sanity | distill≈149, fb~88, text 축소 | distill 149, fb 88, text 48→22 | **PASS** |
| 8 | jsonl_v5_backup 존재 + v6 왕복 | 백업 후 교체 | **미도달(업로드 보류)** | N/A |

### 게이트 1b — B 드롭률 0% 인 이유 (설명)

B(fault-free 캡)의 원래 처방 근거는 perturb 166행(전부 fault-free)이 결함 신호를
익사시키는 것이었다. **C1 이 perturb 트랙을 0으로 제거**하면서 fault-free 홍수가 이미
사라져, distill-only media 에서는 fault_free(61) ≤ cap(int(1.5×88)=132) 이라 트림이
발생하지 않는다. `fault_bearing_count`/`fault_free_count` 는 정상 방출되며, 드롭률 0%는
"C1 이 B 의 트림 필요성을 선제 해소했다"는 정당한 관측치다(수치 은폐 아님).

### 게이트 2 — terra13 실효표 (12/13 delta>0, 7 recoveries)

| video_hash | motion | before(g) | after | delta | recovered | terra_offered | dropped |
|---|---|---|---|---|---|---|---|
| 9a7d87a2cf47 | inside-leg-hang | 3 | 6 | 3 | no | 4 | 1 |
| 83623eee29e1 | Ayesha | 1 | 2 | 1 | no | 3 | 2 |
| d5aabb3d5d22 | FlyBy-Straddle-Cartwheel | 1 | 3 | 2 | no | 2 | 0 |
| 68cc0c09fe30 | Inverted-crucifix | 1 | 4 | 3 | no | 3 | 0 |
| 0b84677dd174 | vertical-split | 1 | 4 | 3 | no | 3 | 0 |
| dff1255baa90 | Ballerina | 0 | 1 | 1 | **yes** | 1 | 0 |
| a73ef703515c | Fireman-spin | 0 | 1 | 1 | **yes** | 1 | 0 |
| 1589e1c90f5c | **General-pole-movements** | 0 | 0 | **0** | **no** | 1 | **1** |
| 2f00de7f233c | Inverted-split | 0 | 2 | 2 | **yes** | 2 | 0 |
| 1f1f6ba788d6 | chopper | 0 | 1 | 1 | **yes** | 1 | 0 |
| 43f85e446ce4 | geumgangmakgi | 0 | 1 | 1 | **yes** | 1 | 0 |
| 95180a8429f0 | invert | 0 | 1 | 1 | **yes** | 1 | 0 |
| 8ef78c0ae977 | pole-split | 0 | 2 | 2 | **yes** | 3 | 1 |

- 순 추가 fault 21건. 12/13 영상 delta>0. **recoveries 7** (기대 8).
- **드롭 5건 전수 사유(은폐 없음)**:
  - 4건 = **dedup**(gemini fault 이미 존재, double-count 방지): inside-leg-hang
    `limb_extension/left_knee-right_knee` ×1, Ayesha `pole_gap/pelvis` ×2,
    pole-split `split_angle/양측 고관절 분할선` ×1. → 해당 영상은 여전히 net delta>0.
  - 1건 = **계약위반**(정당 드롭): General-pole-movements 의 **유일한** terra fault =
    `fault_category='other', body_part='head/eyes', student/reference_angle_deg=None,
    approx_angle_deviation_deg=None`. 각도쌍도 폴백편차도 없어 감점 엔진이 소비 불가
    (`_faults_satisfy_contract` False). 플랜이 명령한 안전장치가 정확히 작동한 것.

## 블로커 — belle 결정 필요 (업로드 보류 사유)

**게이트 2가 belle 명시 certainty 게이트("delta>0 each / 8 recoveries")와 어긋난다.**
원인은 데이터 손상이나 조립 버그가 아니라 **플랜이 강제한 계약 안전장치의 정당한 작동**이다:

- General-pole-movements 의 유일한 terra fault 는 각도·편차가 전무한 서술형(head/eyes
  시선) 결함이라 IPSF 감점 계약(각도쌍 OR approx 편차)에 근본적으로 부적합하다.
- 이 fault 를 **억지로 넣으면** `_build_distill_samples` 의 F1 필터가 **행 전체를 폐기**
  → General-pole-movements 가 distill 셋에서 완전히 사라진다(fault-free 로 남기는 것보다
  strictly 나쁨). 즉 8 recoveries 는 이 데이터로는 도달 불가능한 상한이다.
- 플랜 제약이 명시한 STOP 조건("terra faults break contract irrecoverably → STOP and
  surface rather than forcing a bad upload")에 정확히 해당 → **S3 canonical 교체를
  자동 실행하지 않았다**. 현재 S3 `jsonl/` = pre-v6 원본 그대로 보존(교체 0, 백업 0).

**belle 선택지:**
- **(A) 7 recoveries 수용 → 업로드 진행** (권장): 로컬 v6 는 정확·완전하다. General-pole-
  movements 는 정량 가능한 terra 결함이 없어 fault-free 로 남을 뿐, 나머지 12영상 union +
  전 게이트(perturb 0 / leakage 0 / normalize 100% / fb 88)는 건강하다. 승인 시 아래
  한 줄로 백업→교체→왕복검증이 원자적으로 실행된다:
  `AWS_PROFILE=sunity-motion python3 .planning/quick/260716-jg6-.../assemble_v6.py --upload`
  (스크립트가 전 게이트 재검 후 통과분만 업로드 — 단, 현재 게이트 2 하드체크로 `--upload`
  는 SystemExit 차단됨. belle 승인 시 게이트 2를 "≥7 recoveries + 12/13 delta>0"로 완화
  하거나 belle 가 직접 백업+업로드 지시).
- **(B) 재라벨**: belle 가 General-pole-movements 의 head/eyes 결함에 정량 각도(또는 approx
  편차)를 부여해 terra_collect 갱신 후 재실행 → 8 recoveries 달성.

## 산출물

- `.planning/quick/260716-jg6-.../assemble_v6.py` (커밋 40fe208) — 복원+union+assemble 스크립트.
- 로컬 v6 (tmp work_dir, 미영속): train.jsonl 168행 / val.jsonl 3행 / _meta.json.
- S3 `training/phase22/jsonl/` = **pre-v6 원본 보존**(교체 0). `jsonl_v5_backup/` 미생성.

## 무변형 재사용 확인

- `full_batch.assemble_jsonl` / `manifest_with_hashes` / `save_accepted` — 무변형 호출.
- `build_jsonl.build_dataset` / `_cap_fault_free` / `assistant_report` /
  `_faults_satisfy_contract` — import 재사용.
- `schema.normalize_report` — import 재사용.
- backend/ 파일 변경 0 (`git status` 확인 + pytest 273 passed).

## Self-Check: PASSED

- 스크립트 존재: `.planning/quick/260716-jg6-.../assemble_v6.py` FOUND.
- 커밋 존재: `40fe208` FOUND (git log).
- pytest tests/phase22: 273 passed, 1 skipped.
- 프로덕션 무접촉: git status 상 backend/ 변경 0건.

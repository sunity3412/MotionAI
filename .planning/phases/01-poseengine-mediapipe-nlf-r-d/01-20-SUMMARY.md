---
phase: 01-poseengine-mediapipe-nlf-r-d
plan: "20"
subsystem: ml-pose-engine
status: awaiting_belle_checkpoint
tags:
  - rtmw
  - license-audit
  - weights-manifest
  - cocktail14
  - apache-2.0-code
  - dataset-restricted
  - awaiting-belle
  - gap_closure
  - blocking-human

dependency_graph:
  requires: []
  provides:
    - "docs/licenses/rtmw-weights-audit.md — RTMW 4 후보 가중치 라이선스 audit (D-25)"
    - "weights_manifest.json — plan 21 의 가중치 선택 hard gate (production_eligible 0 초기)"
    - "test_rtmw_weights_manifest.py — schema + license gate 자동 강제 (7 tests)"
  affects:
    - 01-21  # RTMW 통합 — Task 2 belle 승급 commit 필요. 현 상태 진입 차단.

tech_stack:
  added: []  # plan 20 은 라이선스 박제만, 코드 의존성 0
  patterns:
    - "manifest gate — production_eligible=true 인 entry 만 RTMWPoseEngine 로드 가능"
    - "weakest-link license — 학습 데이터 14개 중 1개라도 비상업이면 가중치 = restricted"
    - "audit doc §4 + manifest entry production_eligible 동시 갱신 강제 (T-20-02 mitigation)"

key_files:
  created:
    - docs/licenses/rtmw-weights-audit.md
    - backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/__init__.py
    - backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/weights_manifest.json
    - backend/tests/test_rtmw_weights_manifest.py
    - .planning/phases/01-poseengine-mediapipe-nlf-r-d/01-20-SUMMARY.md
  modified: []

decisions:
  - "RTMW3D-l 부재 → RTMW3D-x 384x288 로 (d) 박제 (deviation, §1-1). rtmlib README + mmpose project zoo 2026-06-02 fetch 기준 RTMW3D-l 공식 배포 채널 없음. RTMW3D-x 만 huggingface Soykaf 호스팅으로 등재."
  - "Cocktail14 = 14 dataset (AIC/CrowdPose/MPII/sub-JHMDB/Halpe/PoseTrack18/COCO-Wholebody/UBody/Human-Art/WFLW/300W/COFW/LaPa/InterHand). weakest-link 분석 — 10+ dataset 명시적 non-commercial, 2 unknown, 2 commercial OK 후보. 가중치 license_status=restricted 보수 판정."
  - "4 후보 모두 production_eligible=false 초기값. belle 검토 (Task 2) 통과 전까지 plan 21 진입 차단."
  - "RTMW 코드 라이선스 (rtmlib/mmpose 본체) = Apache-2.0 — 차단 목록 (AlphaPose/NLF/SMPL-X/VideoPose3D) cross-reference 위반 0건. memory license-blocklist-pose 화이트리스트 정합."
  - "Plan 01-20 Task 2 (belle license checkpoint) 는 blocking-human 게이트 — auto-mode 자동 승인 불가. orchestrator 가 belle 에게 직접 surface."

requirements_completed: []  # POSE-01 부분 — audit 박제만. license_status='commercial_ok' 가중치 0건이므로 manifest 가 plan 21 게이트로 기능. 완전 충족은 belle 승급 후.

metrics:
  duration: "~50 min (rtmlib README + mmpose project README + COCO Wholebody 약관 fetch + audit 작성 + manifest + tests)"
  completed_date: null  # belle Task 2 응답 후 갱신
  tasks_completed: 1  # Task 1 완료. Task 2 belle 대기.
  tasks_total: 2
  files_created: 4
  files_modified: 0
---

# Phase 01 Plan 20: RTMW weights license audit — awaiting belle checkpoint

**One-liner:** Task 1 audit + manifest + tests 박제 완료. Cocktail14 dataset weakest-link 분석 결과 RTMW 후보 4개 모두 `license_status=restricted` → `production_eligible=0` → plan 21 진입 차단. Task 2 belle 라이선스 검토 대기 (blocking-human, license business decision — auto-approve 불가).

---

## TL;DR

| 항목 | 내용 |
|---|---|
| **Verdict** | **`awaiting_belle_license_review`** |
| **Task 1** | 완료 — audit doc + manifest + 7 tests PASS + placeholder `__init__.py` 박제 |
| **Task 2** | **belle 대기** — blocking-human (license 결정은 비즈니스 판단, 자동화 불가) |
| **Plan 21 진입** | **차단** — production_eligible=true 인 entry 0건 |
| **만든 커밋** | 1 (Task 1 atomic) + 본 SUMMARY commit |
| **단위 테스트** | 7 PASS (`backend/tests/test_rtmw_weights_manifest.py`) |
| **운영 코드 수정** | 0 (라이선스 박제 plan, 코드 통합은 plan 21) |
| **차단 목록 위반** | 0 건 (AlphaPose/NLF/SMPL-X/VideoPose3D 부분문자열 0) |

---

## Task 1 Deliverables

| 산출 | 경로 | 역할 |
|---|---|---|
| Audit 문서 | `docs/licenses/rtmw-weights-audit.md` | 6 섹션, 4 후보 + Cocktail14 14 dataset weakest-link 분석 + 의사결정 매트릭스 + §4 belle 박제 자리 |
| Manifest | `backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/weights_manifest.json` | 4 entries, production_eligible=false 초기, sha256=null |
| Placeholder | `backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/__init__.py` | docstring only (plan 21 에서 RTMWPoseEngine 추가) |
| 스키마 테스트 | `backend/tests/test_rtmw_weights_manifest.py` | 7 tests (schema + license enum + production gate + blocklist) |

### 후보 가중치 (manifest entries)

| ID | name | input_size | AP | training | license_status | production_eligible |
|---|---|---|---|---|---|---|
| (a) | rtmw-l-256x192 | 256x192 | 66.0 | Cocktail14 | restricted | **false** |
| (b) | rtmw-l-384x288 | 384x288 | 70.1 | Cocktail14 | restricted | **false** |
| (c) | rtmw-x-384x288 | 384x288 | 70.2 | Cocktail14 (UBody+COCO pretrain) | restricted | **false** |
| (d) | rtmw3d-x-384x288 | 384x288 | 68.0 (3D) | Cocktail14 + 3D | restricted | **false** |

**Deviation §1-1**: Plan 01-20 §1 의 "(d) RTMW3D-l" 은 rtmlib + mmpose 공식 zoo 부재 — RTMW3D-x (huggingface Soykaf 호스팅) 로 박제. audit §1-1 에 정직 기록.

### Test 결과

```
$ cd backend && python -m pytest tests/test_rtmw_weights_manifest.py -x -q
.......                                                                  [100%]
7 passed in 0.01s
```

| Test | 역할 |
|---|---|
| test_manifest_loads_as_valid_json | json.load 성공 |
| test_manifest_required_keys | 최상위 schema (manifest_version, audit_date, weights) |
| test_each_weight_required_keys | 각 entry 7 필수 키 |
| test_license_status_enum | license_status ∈ {commercial_ok, restricted, unknown} |
| test_production_eligible_implies_commercial_ok | **hard gate**: production_eligible=true 인 entry 는 license_status='commercial_ok' 필수 |
| test_at_least_one_candidate_weight | weights ≥ 1 |
| test_no_blocklisted_weights | alphapose/nlf/smplx/videopose3d 부분문자열 0 |

### Acceptance criteria 검증

- [x] 7개 테스트 모두 PASS
- [x] `grep -c "^## " docs/licenses/rtmw-weights-audit.md` = **6** (≥6)
- [x] manifest weights 개수 = **4** (≥4)
- [x] audit 문서에 "Apache-2.0" (8건), "COCO-Wholebody" (5건), "license-blocklist-pose" (2건) 모두 등장
- [x] blocklist 부분문자열 manifest 등장 0건

---

## belle 에게 묻는 질문 (Task 2 §how-to-verify)

Task 2 는 `checkpoint:human-verify gate="blocking-human"` — auto-mode 도 자동 승인 금지. belle 가 audit 문서를 직접 검토 후 다음 결정을 박제해야 함.

### Q1. §2 표의 4개 후보 가중치 학습 데이터셋 검토

→ `docs/licenses/rtmw-weights-audit.md` §2-2 (Cocktail14 14 dataset 라이선스 표) 직접 확인. weakest-link 판정에 동의하는지, 또는 specific dataset 의 약관을 다르게 해석하는지.

### Q2. Production 가중치 1개 선택

조건: `license_status='commercial_ok'` 인 entry 중 1개 (현재 0개). belle 선택지:

- **옵션 A**: Cocktail14 dataset 약관 위반 위험을 수용하고 (a)~(d) 중 1개를 commercial_ok 로 승급. 면책 근거를 §4 박제 + manifest license_status 동시 갱신.
- **옵션 B**: 추가 후보 발굴 (COCO-Wholebody only 또는 CC-BY dataset 조합 학습 RTMW 변형). mmpose 공식 채널 (GitHub Issue 또는 Slack/Discord) 문의 → 회답 적재 후 manifest 추가 entry + commercial_ok 승급.
- **옵션 C**: 자체 fine-tune (Phase 후속 plan 으로 deferred — Phase 1 진입 차단).

### Q3. 폴백 가중치 1개 선택

또는 "single backbone 충분 — 폴백 불필요" 결정. RTMW 단일 백본 운영 시 plan 21 의 RTMWPoseEngine 가 단일 가중치 로드. 폴백이 필요한 경우는 production 가중치 다운로드 실패 / 추론 실패 시 fallback path 사용.

### Q4. license_status=unknown 추가 확인 여부

현 audit 은 unknown 0건 — 모두 weakest-link 로 restricted. 다만 (d) RTMW3D-x 의 hugging face Soykaf 호스팅이 mmpose 공식 미러인지 belle 가 추가 확인할 의사 (옵션):

- mmpose GitHub Issue 검색 (Soykaf 계정 reference 또는 공식 RTMW3D pth/onnx URL)
- OpenMMLab Discord/Slack 문의

선택적 — RTMW3D 가 v1 우선순위 아니면 (a)~(c) 만 결정해도 무방.

---

## Plan 21 진입 게이트

Plan 21 진입은 belle 의 다음 형식 응답 후:

```
approved: production=<name>, fallback=<name>
```

또는 single backbone:

```
approved: production=<name>, fallback=none
```

또는 차단:

```
blocked: <reason>
```

### approved 시 후속 작업 (별 commit, plan 21 진입 전)

1. `docs/licenses/rtmw-weights-audit.md` §4 갱신 — belle 결정 + 일자 + 면책 근거 박제
2. `weights_manifest.json` 의 선택된 entry `license_status='commercial_ok'` + `production_eligible=true` 갱신
3. `test_production_eligible_implies_commercial_ok` 통과 확인
4. commit: `docs(01-20): belle license approved — production=<name>, fallback=<name>`
5. `/gsd:execute-phase 1 --plan 21` 진입

### blocked 시

- Plan 21 진입 보류
- belle 가 옵션 B (mmpose 공식 채널 문의) 또는 옵션 C (자체 fine-tune) 결정 → 별 plan 작성
- Phase 1 의 RTMW 운영 백본 도입은 belle 결정 적재 후 재진입

---

## Deviations from Plan

### [Rule 1 - Sourcing] RTMW3D-l → RTMW3D-x 로 (d) 박제

- **Found during**: Task 1 §1 가중치 URL 박제 시 rtmlib README + mmpose project zoo 2026-06-02 fetch
- **Issue**: Plan 01-20 §1 의 "(d) RTMW3D-l 단일 카메라용" 명시는 공식 배포 채널 부재
- **Fix**: 사실 정합 우선 — (d) 를 RTMW3D-x 384x288 (huggingface Soykaf 호스팅) 로 박제. audit §1-1 에 deviation 명시 + RTMW3D-l 가 향후 release 되면 별 entry 추가
- **Files modified**: `docs/licenses/rtmw-weights-audit.md` §1-1, `weights_manifest.json` (d) entry name
- **Commit**: `226259b feat(01-20): RTMW weights audit + manifest + schema tests (D-25, awaiting belle)`

### 자동 결정 (사실 박제): Cocktail14 의 weakest-link license 판정

- audit doc §3-1 의 license_status=restricted 4건은 dataset 약관 검토 결과의 자동 판정 — belle 가 §3-2 action items 에서 위험 수용 여부 결정. weakest-link 원칙은 보수적 default 로 채택.

**Total deviations:** 1 (Rule 1 - Sourcing). Plan 21 진입 게이트 자체는 변경 없음.

---

## Known Stubs

없음. manifest + audit 는 belle 검토 자료로 완전. sha256 = null 은 의도 (plan 21 가중치 다운로드 시 박제 예정).

---

## Threat Flags

없음 — 신규 네트워크 엔드포인트 / auth path / Firestore 스키마 변경 없음. license audit + 메타데이터 박제만.

본 plan 의 threat model (Plan 01-20 `<threat_model>`):
- **T-20-01** (audit 우회 tampering) → `test_production_eligible_implies_commercial_ok` 가 license_status 동시 확인 강제 (PASS 확인)
- **T-20-02** (belle 결정 박제 누락) → Task 2 checkpoint 가 audit §4 갱신 + commit 강제 (Task 2 단계)
- **T-20-SC** (rtmlib 가중치 무결성) → manifest sha256 필드 — plan 21 가 다운로드 시 검증 (plan 21 task)

---

## Self-Check: PASSED

**파일 존재 확인:**

```bash
[ -f docs/licenses/rtmw-weights-audit.md ] && echo "FOUND" || echo "MISSING"
[ -f backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/__init__.py ] && echo "FOUND" || echo "MISSING"
[ -f backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/weights_manifest.json ] && echo "FOUND" || echo "MISSING"
[ -f backend/tests/test_rtmw_weights_manifest.py ] && echo "FOUND" || echo "MISSING"
```

모두 FOUND.

**커밋 존재 확인:**

- `226259b` feat(01-20): RTMW weights audit + manifest + schema tests (D-25, awaiting belle) — FOUND

**Acceptance criteria 확인:**

- 7/7 pytest tests PASS
- audit doc 6 sections (§1~§6)
- manifest 4 entries
- 키워드 모두 등장 (Apache-2.0 / COCO-Wholebody / license-blocklist-pose)
- blocklist 부분문자열 0건

**운영 코드 무수정 확인:**

- `backend/functions/` UNCHANGED
- `backend/runpod_inference/` UNCHANGED
- `backend/shared/python/sunity_shared/analysis/` 기존 모듈 UNCHANGED (pose_engines/rtmw/ 신규 디렉터리만 추가)
- 기존 Plan 01-19 산출물 UNCHANGED
- STATE.md / ROADMAP.md UNCHANGED (belle Task 2 응답 후 갱신 예정)

---

## Verdict 요약 — orchestrator 에게

- **verdict**: `awaiting_belle_license_review`
- **status**: Task 1 완료, Task 2 (blocking-human) 대기. plan 21 진입 차단.
- **one-liner**: RTMW 4 후보 가중치 audit 박제 — Cocktail14 dataset weakest-link 분석 결과 모두 `restricted`. belle 가 (a)~(d) 중 1개를 commercial_ok 로 승급 (위험 수용 + 면책 근거) 또는 추가 후보 발굴 (mmpose 공식 채널 문의) 또는 자체 fine-tune (별 plan) 결정 필요.
- **commits**: 1 (`226259b` Task 1) + 본 SUMMARY commit.
- **next action**: orchestrator → belle 에게 audit doc §2-2 (Cocktail14 14 dataset 라이선스 표) + §3-2 (action items) surface. belle 응답 형식 = "approved: production=<name>, fallback=<name>" 또는 "blocked: <reason>". 응답 후 audit §4 + manifest production_eligible=true + STATE/ROADMAP 갱신 → `/gsd:execute-phase 1 --plan 21` 진입.

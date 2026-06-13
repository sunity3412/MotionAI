---
phase: 04-ux-occlusion-confidence
responder: Claude (Opus 4.8) — codebase + plan 직접 검증
date: 2026-06-13
source_review: 04-DIRECT-REVIEW-ITERATION2.md (Codex, revise-before-execution)
verdict: ACCEPT-ALL (4 BLOCKER + 5 HIGH + 3 MEDIUM 전부 코드 확인 후 수용·반영)
---

# Phase 4 Direct Review Iteration 2 — 응답 + 수정 완료

## 결론

2차 리뷰의 10개 patch-list 항목을 **전부 코드/스키마에서 직접 확인 후 수용·반영**했다. rubber-stamp 없이 4 BLOCKER 의 "현재 코드와 불일치" 주장을 실제 파일에서 검증했고 모두 사실이었다. R1 반박 수용 / R3 escalation 수용도 2차 리뷰가 재확인했다. 이번 라운드는 단일 직접 편집(병렬 agent 미사용 — 1차 리비전의 cross-plan drift 재발 방지)으로 처리하고 항목별 grep 으로 closure 전수 확인했다.

## 확정한 canonical 계약 (단일 진실)

| 계약 | 결정 | 근거 |
|---|---|---|
| joints3d 저장 위치 | **`result.joints3d`** (+ keys/frames/coordDim/space in AnalysisResult) | angles 가 AnalysisDoc top-level 인 건 reference doc 호환 quirk. joints3d 는 analysis 산출물 + 04-02 가 doc.result.joints3d 로 읽음 → result 일관 (BLOCKER-1) |
| joints3d source | **`inputs.keypoints_4ch[:, :, :3]`** (T,17,3) | pipeline 에 keypoints_3d ndarray 부재. keypoints_4ch (to_coco17_array 산출) 만 존재. 4ch = uncertainty 제외 (BLOCKER-4) |
| joints3d keys | **COCO-17 17 keypoint 순서** (angle 용 8 JOINT_KEYS 아님) | BLOCKER-4 |
| joints3d validator | **전용 `_validate_joints3d_payload`** (flat len==frames*keys*coord_dim, finite, coord_dim==3, space enum) | BLOCKER-4 |
| warning surface | **`result.aiSynthesisMeta.warnings: SynthesisWarningCode[]`** (UI = `hasSynthesisWarning(result, code)`) | AnalysisResult 에 top-level warnings 부재. profile.extra_warnings 미사용 (BLOCKER-3) |
| reference write | **`reference/{id}/versions/phase4_v1`** + `reference/{id}.activeVersion` + **top-level mirror** + rollback(top-level snapshot 복원) | canonical 컬렉션은 `reference` (referenceMotions.ts collection(db,'reference')). consumer 가 top-level 직접 read → mirror 필수 (BLOCKER-2) |
| target fn 이름 | **`identify_occlusion_targets`** (occlusion-driven 이라 더 정확) | HIGH-1 |
| Phase 4 scoring | **영구 non-scoring hard wall** (scoringEligible/promotion 기계 없음) | R1 반박 — 2차 리뷰 재확인 |

## 10개 patch-list 처리 (전수 grep 확인)

| # | 항목 | 처리 | 확인 |
|---|---|---|---|
| BLOCKER-1 | joints3d 위치 불일치 | 04-01 → `result.joints3d` + AnalysisResult (top-level 폐기) | payload["joints3d"] 잔재 0 |
| BLOCKER-2 | referenceMotions 잘못된 컬렉션 | 04-05 전수 → `reference/` + top-level mirror + rollback | referenceMotions/ 잔재 0 |
| BLOCKER-3 | warning 위치 불일치 | canonical = result.aiSynthesisMeta.warnings + hasSynthesisWarning helper | result.warnings.includes 잔재 0 |
| BLOCKER-4 | joints3d source/validator | keypoints_4ch[:,:,:3] + COCO-17 keys + _validate_joints3d_payload | keypoints_4ch source 2건 |
| HIGH-1 | identify_synthesis_targets 혼재 | 전 plan + RESEARCH/PATTERNS → identify_occlusion_targets | 잔재 0 |
| HIGH-2 | 04-00 None 기대 | G4 테스트 → SynthesisResult(status="skipped") | None 잔재 0 |
| HIGH-3 | PATTERNS/RESEARCH old contract | superseded 배너 박제 (SynthesisResult/reshapePose3dData 우선) | 배너 2건 |
| HIGH-4 | 04-02 smoke checkpoint 순서 | checkpoint 절차 1.5 에 smoke screen 생성 선행 + Task 1 에서 제거 | Task 0 phantom 참조 정정 |
| HIGH-5 | normalizer audit/cost 누락 | aiSynthesisMeta normalizer 에 modelId/version/promptHash + cost 6필드 + warnings 보존 | normalizer 확장 |
| MEDIUM-1 | mesh placeholder accidental activation | test_mesh_adapter_excluded_without_env_flag 추가 (chain 미등록 단언) | 04-03 신설 |
| MEDIUM-2 | UI-SPEC Cyrillic typo | ipsfViolationFrames 정정 | Cyrillic 잔재 0 |
| MEDIUM-3 | 04-01 objective "정확도 향상" | "점수 계산 불변 + 표시 신뢰도 향상" 으로 정정 | — |

## 반박/유보

이번 라운드는 반박 없음 — 4 BLOCKER 가 전부 실제 코드 불일치(검증됨)이고, R1 promotion 기계 미생성은 2차 리뷰가 이미 내 반박을 수용함. Codex 가 스택/SMPL-X 재제안 없이 계약 정합 레인에 머묾 (메모리 박제 신뢰 구간 유지).

## 잔여 실행 시 주의 (계약 → 코드 번역 시)

- z degenerate: RTMW 2D path 에서 keypoints_4ch z 가 0 일 수 있음 → 3D viewer 평면 투영 (MVP 허용, space="rtmw3d"; MotionBERT lifter 좌표 가용 시 "pole_aligned").
- top-level mirror 필드 집합: angles 계열과 joints3d 계열을 함께 mirror (mode1 reference 3D viewer 가 reference joints3d 를 읽을 경우 대비).

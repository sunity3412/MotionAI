---
phase: quick-260713-jxr
plan: 01
status: complete
completed: 2026-07-13
---

# 처방 B 배선 — 내부 fault 트랙 enumerate + anonymize + manifest 등재 (SUMMARY)

## 결과

22-07 게이트 FAIL 근본원인 1번(fault 트랙 0행 — 결함 짚기 감독 신호 부재)의 데이터 처방을 위한 로컬 코드·문서 조각을 완성했다. Pod 실행(anonymize 배치, 교사 라벨링)은 PLAN.md `<runbook>` 섹션의 명령 시퀀스로 문서화만 했고, 실제 실행은 오케스트레이터가 SSH로 수행한다.

belle 결정(2026-07-13): 파일럿 이전 내부 데이터 학습사용 일괄 승인 + 명시 거부(learningOptIn=false) 1건 무조건 제외 + anonymize 강제 + 이후 신규는 optIn=true 엄격.

## 태스크별 산출 (커밋)

| Task | 산출 | 커밋 |
|------|------|------|
| 1 | `enumerate_internal.py`(349행) — Firestore 열거 + consent 게이트 3분기 + ETag pre-dedup + 스케일 가드 + 후보 JSON 방출 / 테스트 22건 | fd328d1(RED) + 894f680(GREEN) |
| 2 | `anonymize_batch.py` — 재개 가능 배치(터미널/bucket None/hash 중복 skip) + manifest 행 생성/병합 / 테스트 20건 | ec189e1 |
| 3 | LICENSE-AUDIT §7-1 일괄승인 + §8 이력 2행 + R4 갱신 / manifest _meta.customer_track 승인 박제(rows 131 불변) / models.py 주석 갱신 | 386398e |

## 검증

- `pytest tests/phase22/` = **222 passed, 1 skipped** (기존 스위트 무회귀 + 신규 2파일 42건).
- 신규 manifest 행이 `gemini_teacher.eligible_for_distill`(source에 'user'+anonymized=true+s3_key) 및 `test_provenance` fence(REQUIRED_PROVENANCE_FIELDS truthy + label_bucket enum + 금지 식별자 부재)를 **무수정 통과** — 후속 라벨링에 코드 변경 0.
- manifest rows 131 불변, `_meta.customer_track` approved_at=2026-07-13/approved_by=belle 박제.
- provenance fence 상수는 `test_provenance`에서 import(단일 owner — 하드코딩 복제 금지).

## belle 결정 박제 4곳 정합

1. 코드 — `enumerate_internal.consent_allows` 기본 strict(부재=제외) + `--bulk-approval` + 컷오프(2026-07-13) 이중 방어. false는 플래그 무관 무조건 제외.
2. manifest — `_meta.customer_track.approval_scope`.
3. LICENSE-AUDIT — §7-1(결정/제외/anonymize/신규필터/서면화권장/행규약) + §8 이력 행.
4. models.py — learningOptIn 계약 주석 "미집행"→"consent_allows 집행 시작"(계약 자체 불변, 3-way lockstep 유지).

## STRIDE 완화 (threat_model 5건)

- T-Q13-01 uid 유출 → build_manifest_row + assert_no_identifier_keys 이중 fence, source_url은 video_hash 기반 sentinel(uid 비파생), 후보 JSON은 리포 밖 강제.
- T-Q13-02 동의 우회 → consent_allows 3분기 단위 테스트.
- T-Q13-03 SQS 오발화 → internal_upload_key가 fixtures/phase22/internal/ 하드소유, uploads/ 생성 경로 구조적 부재.
- T-Q13-04 과금 폭주 → 스케일 가드 100~500(≈371 스케일) 밖이면 계수만 출력 후 정지, --force로만 우회.
- T-Q13-05 승인 부인 → LICENSE-AUDIT + manifest _meta + 행별 consent_evidence 3중 박제.

## 다음 (Pod 실행 — 오케스트레이터)

PLAN.md `<runbook>` 순서: (0) 코드 pull → (1) enumerate --dry-run 계수 확인 → (2) enumerate 본실행(후보 JSON, 리포 밖) → (3) anonymize_batch --max-rows 5 눈검증 → (4) 본배치(재개 가능) → (5) manifest 커밋+push → (6) belle greenlight 후 full_batch 교사 라벨링(Gemini 과금 ≈2.9x). 신규 internal_pilot_user 행은 anonymized=true라 selectable_rows에 자동 포함, 기존 129행은 터미널 결과로 skip(재과금 0).

## 참고

- 실행 중 fable executor가 크레딧 소진으로 Task 1 구현 중 중단 → Opus 4.8로 이어받아 완주(Task 1 GREEN 커밋 + Task 2·3 신규). enumerate_internal.py 본체는 fable 작성분(테스트 GREEN 확인 후 커밋), anonymize_batch/문서는 Opus 작성.

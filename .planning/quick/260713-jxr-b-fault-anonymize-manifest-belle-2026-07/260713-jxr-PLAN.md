---
phase: quick-260713-jxr
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/training/datagen/enumerate_internal.py
  - backend/training/datagen/anonymize_batch.py
  - backend/tests/phase22/test_enumerate_internal.py
  - backend/tests/phase22/test_anonymize_batch.py
  - backend/training/data/manifest.json
  - backend/training/LICENSE-AUDIT.md
  - backend/shared/python/sunity_shared/models.py
autonomous: true
requirements: [22-07-처방B]
must_haves:
  truths:
    - "learningOptIn=false 문서는 어떤 플래그 조합에서도 학습 후보에서 제외된다 (belle 결정: 명시 거부 1건 무조건 제외)"
    - "learningOptIn 부재 문서는 belle 일괄승인 플래그를 명시로 켤 때만 통과한다 — 기본값은 strict 제외 (models.py 254-269 fail-safe 계약 보존)"
    - "dedup 후 후보 계수가 100~500 밖이면 러너가 계수만 출력하고 멈춘다 (--force 없이는 진행 불가)"
    - "anonymize 산출물 업로드 키는 fixtures/phase22/internal/{video_hash}.mp4 뿐이다 — uploads/ prefix 기록 경로 없음 (SQS 발화 차단)"
    - "신규 manifest 행은 uid 미포함 + anonymized=true + source='internal_pilot_user' 로 gemini_teacher.eligible_for_distill 을 통과한다"
    - "신규 manifest 행은 test_provenance 의 REQUIRED_PROVENANCE_FIELDS(truthy source_url 포함)와 label_bucket enum(정타|fault) fence 를 통과한다 — bucket 미상 후보는 병합 전 skip"
    - "배치 러너는 재개 가능 — 행별 결과 파일이 있으면 재실행 시 skip (anonymize/업로드 재수행 0)"
  artifacts:
    - path: "backend/training/datagen/enumerate_internal.py"
      provides: "Firestore 열거 + optIn 게이트 + ETag pre-dedup + 스케일 가드 + 후보 JSON 방출"
      min_lines: 120
    - path: "backend/training/datagen/anonymize_batch.py"
      provides: "후보 소비 → anonymize_video → S3 업로드 → manifest 행 생성/병합 (재개 가능)"
      min_lines: 120
    - path: "backend/tests/phase22/test_enumerate_internal.py"
      provides: "optIn 게이트 3분기 / dedup / 스케일 가드 / uid 미유출 테스트"
    - path: "backend/tests/phase22/test_anonymize_batch.py"
      provides: "manifest 행 스키마(provenance fence 포함) / eligible_for_distill 통과 / 재개 skip / 업로드 prefix 테스트"
    - path: "backend/training/LICENSE-AUDIT.md"
      provides: "belle 2026-07-13 일괄승인 섹션 + 결정 이력 행 + 명시 거부 1건 제외 기록"
  key_links:
    - from: "backend/training/datagen/anonymize_batch.py"
      to: "backend/training/datagen/anonymize.py"
      via: "anonymize_video(in_path, out_path) 호출 (lazy import)"
      pattern: "anonymize_video"
    - from: "backend/training/datagen/enumerate_internal.py"
      to: "Firestore users/{uid}/analyses"
      via: "collection_group('analyses') 스트림 (measure_error_profile 패턴)"
      pattern: "collection_group"
    - from: "backend/training/datagen/anonymize_batch.py 생성 행"
      to: "backend/training/distill/gemini_teacher.py"
      via: "eligible_for_distill (source에 'user' 포함 + anonymized=true)"
      pattern: "internal_pilot_user"
    - from: "backend/training/datagen/anonymize_batch.py 생성 행"
      to: "backend/tests/phase22/test_provenance.py"
      via: "REQUIRED_PROVENANCE_FIELDS / VALID_BUCKETS 상수 import 검증"
      pattern: "REQUIRED_PROVENANCE_FIELDS"
---

<objective>
처방 B 배선 — 내부 fault 트랙(구 "내부 371", Firestore 실측 done 707 / video 662) 열거 + anonymize + manifest 등재를 위한 로컬 코드·문서 작업.

Purpose: 22-07 게이트 FAIL 근본원인 1번(fault 트랙 0행 — 결함 짚기 감독 신호 부재)의 유일한 데이터 처방. belle 결정(2026-07-13, 구두 승인): 파일럿 이전 내부 데이터 학습사용 일괄 승인 + 명시 거부(learningOptIn=false) 1건 무조건 제외 + anonymize(얼굴 블러) 강제 유지 + 이후 신규 데이터는 optIn=true 엄격 필터.

Output: enumerate/anonymize-batch 모듈 2개 + 테스트 2개 + manifest _meta 갱신 + LICENSE-AUDIT 승인 박제. 실제 Pod 실행(anonymize 배치, 교사 라벨링)은 이 plan 범위 밖 — 하단 runbook 섹션에 명령 시퀀스만 문서화(오케스트레이터가 SSH 수행).

분업 경계 (executor 준수): 이 plan 의 executor 는 로컬 코드+문서만 작성·커밋한다. Pod SSH / Firestore 실 스트림 / S3 실 업로드 / Gemini 호출은 절대 수행하지 않는다.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@backend/training/distill/gemini_teacher.py          # eligible_for_distill(_is_customer_source), _download_s3, slug 규칙
@backend/training/distill/full_batch.py              # 재개 가능 러너 패턴(행별 결과 파일 + TERMINAL skip)
@backend/training/datagen/anonymize.py               # anonymize_video / blur_bbox_regions (재사용, 수정 금지)
@backend/training/datagen/measure_error_profile.py   # collection_group 스트림 + T-22-01 식별자 미유출 패턴
@backend/training/data/manifest.json                 # 행 스키마 + _meta.customer_track
@backend/training/LICENSE-AUDIT.md                   # §7 D-12 / §8 결정 이력
@backend/tests/phase22/test_provenance.py            # REQUIRED_PROVENANCE_FIELDS / VALID_BUCKETS / FORBIDDEN_IDENTITY_FIELDS fence
@backend/shared/python/sunity_shared/s3keys.py       # uploads/{uid}/{analysisId}.{ext}
@backend/shared/python/sunity_shared/models.py       # 254-269행 learningOptIn 계약 주석
@backend/tests/phase22/test_full_batch.py            # import/sys.path 컨벤션 참조
@.planning/phases/22-custom-vlm-finetune/22-07-SUMMARY.md  # 처방 B 정의 76-93행
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: enumerate_internal.py — Firestore 열거 + 동의 게이트 + dedup + 스케일 가드</name>
  <files>backend/training/datagen/enumerate_internal.py, backend/tests/phase22/test_enumerate_internal.py</files>
  <behavior>
    - consent 게이트 3분기: learningOptIn is False → 제외(플래그 무관, belle 명시 거부 1건). True → 통과. 필드 부재 → bulk_approval=False(기본)면 제외, bulk_approval=True 면 createdAt < 승인 컷오프(2026-07-13 epoch ms 상수)일 때만 통과(방어적 — phase 26 이후 문서는 필드를 항상 기록하므로 부재=파일럿 이전이지만 이중 방어).
    - 후보 자격: status=="done" 그리고 video 재구성 가능(문서 경로에서 uid/analysisId + videoFormat/fileName 확장자로 uploads/{uid}/{analysisId}.{ext} 도출).
    - dedup: (a) 후보 간 ETag 중복 → 첫 행만 유지 (b) 기존 manifest 행(collected=true, s3_key 보유)의 S3 ETag 집합과 일치 → 제외(시드/reference/수집분 재업로드 차단). ETag에 '-'(멀티파트)가 있으면 pre-dedup 은 통과시키고 후속 content-hash dedup(Task 2)에 위임한다는 주석 명시.
    - 스케일 가드: dedup 후 계수가 min(100)~max(500) 밖이면 계수 요약만 stdout 출력 + exit 1 (--force 로만 우회). belle 승인 예산 = 129행 배치의 ~2.9배(≈371행 스케일) 근거 주석.
    - uid 취급: 후보 JSON(중간산출물)에는 s3_key(uid 포함)가 실리지만, 산출 파일 기본 경로는 리포 밖(/workspace 또는 --out 필수 인자)이고 리포 내 기록 금지 — 최종 manifest 에는 uid 파생 필드가 절대 들어가지 않음을 테스트로 고정.
  </behavior>
  <action>
    backend/training/datagen/enumerate_internal.py 신규 작성. 구조는 measure_error_profile.py 를 원형으로: 모듈 docstring(한국어, 처방 B + belle 2026-07-13 결정 + models.py learningOptIn 계약 인용), sys.path 에 shared 삽입, firestore_admin._db() 재사용, collection_group("analyses") 읽기 전용 스트림.

    순수 함수(네트워크 0, 최상단 배치 — google/boto3 는 lazy import):
    - consent_allows(doc: dict, *, bulk_approval: bool, cutoff_ms: int = BELLE_BULK_APPROVAL_CUTOFF_MS) -> bool — 위 behavior 3분기. 기본 strict(부재=제외)로 models.py fail-safe 계약을 보존하고, belle 일괄승인은 호출자가 플래그로 명시할 때만 발동.
    - derive_upload_key(uid: str, analysis_id: str, doc: dict) -> str | None — videoFormat 우선, 없으면 fileName 확장자(mp4/mov만), 그 외 None. s3keys.build_upload_key 재사용.
    - dedup_candidates(candidates: list[dict], known_etags: set[str]) -> list[dict] — 후보 간 + 기존 manifest ETag 대비 dedup. 후보 dict 는 {s3_key, etag, created_at_ms, motion, provisional_bucket, opt_in} 형태.
    - scale_guard(n: int, *, lo: int = 100, hi: int = 500) -> bool — 범위 내 True.
    - provisional_label_bucket(doc: dict) -> str | None — result.overall(정수) 존재 시 >= 80 → "정타", 미만 → "fault", 부재 → None. docstring 에 "잠정 버킷 — 교사 라벨이 최종, ground truth 아님([[analysis-objectivity-no-human-scores]] 저촉 없음: 파이프라인 산출 임계 라벨)" 명시.

    I/O 껍데기:
    - iter_candidate_docs(db, *, limit) — collection_group 스트림. snap.reference.path 에서 uid/analysisId 파싱(users/{uid}/analyses/{id}). measure_error_profile._iter_analyses 와 달리 uid 가 필요하므로 (uid, analysis_id, doc) 튜플 yield — docstring 에 "uid 는 s3 키 도출용 중간값, 최종 manifest 미기록(T-22-01 정신)" 명시.
    - fetch_etag(s3, bucket, key) -> str | None — head_object, 404 는 None(존재 확인 겸용). 따옴표 strip.
    - known_manifest_etags(manifest, s3, bucket) -> set — collected=true + s3_key 보유 행의 ETag 수집(head 실패 graceful skip).
    - main/CLI: --out(필수), --bulk-approval(store_true), --limit, --force, --bucket 기본 sunity-motion-pilot-videos, --dry-run(계수 요약만, 파일 미기록). 산출 JSON = {"_meta": {generated_at, bulk_approval, counts: {scanned, done, opted_out, no_video, s3_missing, deduped, final}}, "candidates": [...]}. 스케일 가드 위반 시 counts 만 출력하고 exit 1.

    테스트(backend/tests/phase22/test_enumerate_internal.py, fake dict/fake s3 — 네트워크 0, test_full_batch.py 의 import 컨벤션 재사용): consent 3분기(false 는 bulk_approval=True 에서도 제외 / 부재+strict 제외 / 부재+bulk+컷오프이전 통과 / 부재+bulk+컷오프이후 제외 / true 통과), derive_upload_key(videoFormat/fileName/미상 None), dedup(후보 간 중복 + known_etags 제외 + 멀티파트 ETag 통과), scale_guard 경계값, provisional_label_bucket 3분기, 후보 dict 에 uid 키 부재 확인(s3_key 안의 uid 는 허용 — 최종 manifest 행 fence 는 Task 2).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && python3 -m pytest tests/phase22/test_enumerate_internal.py -x -q</automated>
  </verify>
  <done>consent 게이트 3분기·dedup·스케일 가드·잠정 버킷이 순수 함수로 분리되어 테스트 GREEN. CLI 는 --out 필수 + 기본 strict + --bulk-approval 명시 시에만 부재 문서 통과. 스케일 가드 위반 시 계수만 출력 후 exit 1.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: anonymize_batch.py — 재개 가능 배치 러너 + manifest 행 생성/병합</name>
  <files>backend/training/datagen/anonymize_batch.py, backend/tests/phase22/test_anonymize_batch.py</files>
  <behavior>
    - manifest 행 스키마: 기존 131행과 동일 키 + consent_evidence 추가. source="internal_pilot_user"(gemini_teacher._is_customer_source 발화), anonymized=true, s3_key=f"fixtures/phase22/internal/{video_hash}.mp4", source_url=f"internal://firestore-analyses/{video_hash}"(truthy 내부 sentinel — test_provenance REQUIRED_PROVENANCE_FIELDS 충족. uid/analysisId 파생값 절대 금지, video_hash 기반만 — T-Q13-01 fence 유지), channel="internal", motion=후보값(None 허용), label_bucket=잠정값("정타"|"fault" enum 강제), tier="customer", license_evidence="파일럿 참가 동의서(D-12 1겹)", consent_evidence="belle 일괄승인 2026-07-13 — 파일럿 이전 내부 데이터 학습사용(구두), 명시 거부 1건 제외", usage="training-only-no-redistribution", holdout=null, collected=true. uid/analysisId/이메일 계열 키는 어떤 행에도 금지(테스트 fence).
    - provisional_bucket 이 None(result.overall 부재)인 후보는 manifest 병합 전 skip — 행 결과 파일에 result="skipped_no_bucket" 사유 카운트 기록(test_provenance VALID_BUCKETS enum 위반 원천 차단). build_manifest_row 는 bucket 이 "정타"/"fault" 밖(None 포함)이면 ValueError(방어 assert).
    - 생성 행은 gemini_teacher.eligible_for_distill 를 실제로 통과한다 (직접 호출 테스트).
    - 생성 행은 test_provenance fence 를 실제로 통과한다 — REQUIRED_PROVENANCE_FIELDS 전부 truthy + label_bucket in VALID_BUCKETS + FORBIDDEN_IDENTITY_FIELDS 부재 (상수를 import 해 검증, 단일 owner 유지).
    - 재개: 행별 결과 파일(out_dir/rows/{video_hash 또는 s3 slug}.json)이 터미널(result in {"uploaded","skipped_no_bucket"})이면 skip(full_batch TERMINAL 패턴). content-hash 중복(이미 처리한 hash 재등장)도 skip.
    - 업로드 키는 fixtures/phase22/internal/ 로 시작 — uploads/ 로 시작하는 키를 만들면 ValueError (SQS 발화 차단을 코드로 강제).
    - merge_manifest_rows(manifest, new_rows) 는 순수(사본 반환) + 멱등(s3_key 기준 중복 병합 0) + _meta.customer_track 갱신.
  </behavior>
  <action>
    backend/training/datagen/anonymize_batch.py 신규 작성. full_batch.py 의 재개 규율을 원형으로(행별 결과 파일 = 진실, 메모리 반환 의존 금지).

    순수 함수:
    - internal_upload_key(video_hash: str) -> str — f"fixtures/phase22/internal/{video_hash}.mp4". 인자 검증(빈 값 ValueError). uploads/ prefix 생성 경로가 구조적으로 없음을 docstring 에 명시(S3 ObjectCreated→SQS 함정).
    - internal_source_url(video_hash: str) -> str — f"internal://firestore-analyses/{video_hash}". provenance fence(test_provenance REQUIRED_PROVENANCE_FIELDS 의 truthy source_url) 충족용 내부 sentinel — docstring 에 "uid/analysisId 파생 금지, hash 기반만(T-Q13-01)" 명시.
    - build_manifest_row(candidate: dict, video_hash: str) -> dict — behavior 의 스키마. 방어 assert 2종: (a) 금지 키(uid/analysisId/email 계열) 부재 (b) label_bucket 이 "정타"/"fault" 밖(None 포함)이면 ValueError — 호출 전 skip 이 정상 경로지만 이중 방어.
    - merge_manifest_rows(manifest: dict, new_rows: list[dict]) -> dict — deepcopy 사본에 s3_key 기준 upsert(기존 131행 불변), _meta.customer_track 을 {count 갱신, anonymized: "in_progress", approved: "belle 2026-07-13 일괄승인(파일럿 이전), 이후 신규는 learningOptIn=true 엄격"} 형태로 갱신. full_batch.manifest_with_hashes 의 사본 규율 재사용.
    - is_row_done(payload) -> bool — result in {"uploaded", "skipped_no_bucket"} 터미널 판정.
    - assert_no_identifier_keys(rows) — 행 키 화이트리스트 검증(measure_error_profile._assert_no_identifiers 정신). uid 포함 s3_key 값(uploads/... 원본 키)이 행에 남으면 실패.
    I/O 껍데기(boto3/anonymize/imageio 전부 lazy import):
    - run_anonymize_batch(candidates_path, out_dir, scratch_dir, *, bucket, manifest_path, dry_run) — 후보 순회: (행 결과 터미널 → skip) → (provisional_bucket 이 None → 행 결과 "skipped_no_bucket" 기록 후 다음 행, 다운로드/anonymize 미수행) → gemini_teacher._download_s3 로 uploads 원본 다운로드 → sunity_shared.analysis.technique_cache.compute_video_hash → (이미 처리된 hash → skip 기록) → anonymize.anonymize_video(원본, scratch 블러본) → s3.upload_file(블러본, internal_upload_key(hash), ExtraArgs ContentType video/mp4) → 행 결과 파일 {result:"uploaded", video_hash, s3_key, row} 기록 → 로컬 파일 삭제(finally). 전체 종료 시 rows/ 의 uploaded 행을 모아 merge_manifest_rows → manifest_path 에 기록(indent 2, ensure_ascii=False — 기존 파일 포맷과 diff 최소화 확인) + 요약 stdout(uploaded/skipped_no_bucket/hash 중복 카운트 포함). dry_run 은 다운로드/업로드 없이 계획 계수만.
    - CLI: --candidates(필수), --out-dir, --scratch-dir, --bucket, --manifest 기본 backend/training/data/manifest.json, --dry-run, --max-rows(시험 배치용).

    테스트(backend/tests/phase22/test_anonymize_batch.py, fake s3/fake anonymize 주입 또는 monkeypatch — GPU/네트워크 0): internal_upload_key prefix 검증(uploads 불가 구조 + 빈 hash ValueError), build_manifest_row 스키마(필수 키 존재 + 금지 키 부재 + source 에 user 포함 + bucket enum 밖/None ValueError), 생성 행이 gemini_teacher.eligible_for_distill 통과(직접 import 호출 — holdout/anonymized/s3_key 3게이트), 생성 행이 provenance fence 통과 — tests.phase22.test_provenance 의 REQUIRED_PROVENANCE_FIELDS/VALID_BUCKETS/FORBIDDEN_IDENTITY_FIELDS 상수를 import 해 all(row.get(f)) + label_bucket in enum + 금지 키 부재 검증(상수 단일 owner — 하드코딩 복제 금지), merge_manifest_rows 멱등(2회 병합 = 1회) + 기존 행 불변 + _meta.customer_track 갱신, 재개 skip(터미널 결과 파일 존재 시 anonymize 호출 0회 — 호출 카운터 fake), bucket None 후보 skip(다운로드/anonymize 호출 0회 + skipped_no_bucket 기록 + manifest 병합분 미포함), hash 중복 skip. anonymize_video 자체는 재테스트하지 않는다(기존 소유 테스트 존재 — 수치 채우기 금지).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && python3 -m pytest tests/phase22/test_anonymize_batch.py tests/phase22/test_manifest_consistency.py tests/phase22/test_provenance.py -x -q</automated>
  </verify>
  <done>배치 러너가 재개 가능(터미널 skip + hash 중복 skip + bucket None skip)하고, 생성 행이 eligible_for_distill 과 test_provenance fence(truthy source_url sentinel + bucket enum)를 실제 통과하며, 업로드 키가 fixtures/phase22/internal/ 로 강제된다. merge 는 멱등·사본·기존 행 불변. 기존 manifest 정합 테스트 무회귀.</done>
</task>

<task type="auto">
  <name>Task 3: LICENSE-AUDIT 승인 박제 + manifest _meta·models.py 주석 갱신 + 커밋</name>
  <files>backend/training/LICENSE-AUDIT.md, backend/training/data/manifest.json, backend/shared/python/sunity_shared/models.py</files>
  <action>
    LICENSE-AUDIT.md 갱신 (기존 확정 문구 재조사 금지 — 추가만):
    - §7(고객 데이터 동의 3겹) 뒤에 "§7-1. 내부 fault 트랙 일괄승인 (belle 2026-07-13)" 섹션 신설: (a) 결정 내용 — 파일럿 이전 내부 데이터(직원 실증·내부 테스트, Firestore 실측 done 707/video 662, learningOptIn 부재 871건 = 전부 phase 26 동의 UI 도입 이전) 학습사용 일괄 승인(구두). (b) 명시 거부 learningOptIn=false 1건 무조건 제외(코드 fence: enumerate_internal.consent_allows). (c) anonymize(얼굴 블러) 적재 전 강제 불변(D-12 소급 불가). (d) 이후 신규 데이터는 learningOptIn=true 엄격 필터(부재=미동의 fail-safe 복원). (e) 권장 후속 — 직원 구두동의의 서면화(파일럿 참가 동의서 부속 또는 간단 확인서), A9-7 실사 항목과 연결. (f) 등재 행의 consent_evidence 필드 규약 + source_url sentinel 규약(internal://firestore-analyses/{video_hash} — uid 비파생) 명시.
    - §8 결정 이력 표에 행 추가: 2026-07-13 / 내부 fault 트랙 일괄승인 / 위 요지.
    - §6 리스크 표(R4 행)의 고객 트랙 서술에 "2026-07-13 일괄승인으로 등재 착수(anonymize 강제 경로: enumerate_internal → anonymize_batch)" 한 줄 반영.

    manifest.json _meta 만 갱신(rows 무변경 — 행 추가는 Pod 실행 후 anonymize_batch 가 수행):
    - _meta.customer_track 에 approved_at: "2026-07-13", approved_by: "belle", approval_scope: "파일럿 이전 내부 데이터 학습사용 일괄 승인(구두) — learningOptIn=false 1건 제외, anonymize 강제, 이후 신규는 optIn=true 엄격", pending 문구를 "enumerate_internal → anonymize_batch 경로로 등재 진행 중(행 추가는 Pod 배치 후)" 로 교체. count 371 은 "구 추정치 — 실측 후보 수는 enumerate 산출로 대체" 주석 성격으로 description 에 반영.
    - _meta 갱신 후 기존 manifest 정합 테스트 무회귀 확인.

    models.py 254-269행 learningOptIn 계약 주석 갱신(주석만 — 코드 무접촉): "현 22-04 게이트는 ... 미집행 상태" 문단을 "집행 시작(2026-07-13): enumerate_internal.consent_allows 가 학습 후보 진입점에서 이 계약을 집행한다 — false 무조건 제외 / 부재 fail-safe 제외, 단 belle 2026-07-13 일괄승인 플래그(--bulk-approval + 컷오프)로 파일럿 이전 문서만 예외 통과" 로 갱신. 3-way lockstep 문구는 불변(계약 자체 변경 아님).

    커밋: 이 plan 의 산출 전부(신규 모듈 2 + 테스트 2 + 문서 2 + models.py 주석)를 conventional commit 으로. 메시지 예: "feat(quick-260713): 처방 B 배선 — 내부 fault 트랙 enumerate+anonymize 배치 + belle 일괄승인 박제".
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && python3 -m pytest tests/phase22/ -q && python3 -c "import json; m=json.load(open('training/data/manifest.json')); ct=m['_meta']['customer_track']; assert ct.get('approved_at')=='2026-07-13' and ct.get('approved_by')=='belle', ct; assert len(m['rows'])==131, len(m['rows']); print('meta ok, rows unchanged')" && grep -c "2026-07-13" training/LICENSE-AUDIT.md && grep -c "consent_allows" shared/python/sunity_shared/models.py</automated>
  </verify>
  <done>LICENSE-AUDIT 에 §7-1 일괄승인 섹션(§source_url sentinel 규약 포함) + §8 이력 행 + R4 갱신. manifest _meta.customer_track 에 승인 박제(rows 131 불변). models.py learningOptIn 주석이 consent_allows 집행 시작을 반영. phase22 전체 스위트 GREEN. 전 산출물 커밋 완료.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Firestore analyses → 학습 코퍼스 | 사용자 개인 영상/식별자가 학습 원장으로 건너는 경계 (D-12) |
| uploads/ S3 → fixtures/phase22/internal/ | 분석 파이프라인 발화 prefix 에서 학습 전용 비-notified prefix 로의 이동 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-Q13-01 | Information Disclosure | manifest 행 / 후보 JSON | mitigate | 최종 manifest 에 uid·analysisId·이메일 키 금지 — build_manifest_row assert + assert_no_identifier_keys + 테스트 fence. source_url sentinel 은 video_hash 기반만(uid 비파생). 후보 JSON(uid 포함 s3_key)은 리포 밖 경로 강제(--out 필수, 기본 /workspace) |
| T-Q13-02 | Elevation (동의 우회) | consent_allows | mitigate | 기본 strict(부재=제외), --bulk-approval 명시 + 컷오프 이전 문서만 통과, false 는 무조건 제외 — 3분기 전부 단위 테스트 |
| T-Q13-03 | Denial of Service (파이프라인 오발화) | S3 업로드 키 | mitigate | internal_upload_key 가 fixtures/phase22/internal/ 를 하드 소유, uploads/ 생성 경로 구조적 부재 + prefix 테스트 |
| T-Q13-04 | Tampering (과금 폭주) | anonymize/라벨링 배치 규모 | mitigate | 스케일 가드 100~500(≈371 스케일, belle 승인 예산 ~2.9x) 밖이면 계수만 출력 후 정지, --force 로만 우회 |
| T-Q13-05 | Repudiation | 승인 근거 | mitigate | LICENSE-AUDIT §7-1/§8 + manifest _meta + 행별 consent_evidence 3중 박제, 서면화 후속 권장 명기 |
</threat_model>

<runbook>
## Pod 실행 runbook (문서화만 — executor 실행 금지, 오케스트레이터가 SSH 수행)

전제: A100 pod(현행 ns8smhcydnduq9 계열), 코드 push 후 pod 에서 pull. env: AWS 자격(sunity-motion), FIREBASE_SA_PATH 또는 FIREBASE_SA_PARAM, FACE_WEIGHTS_PATH(선택). 파이프라인 동시성 비안전 — 전 단계 순차([[pipeline-not-concurrency-safe-eval-serial]]).

```bash
# 0) 코드 동기화
cd /workspace/SunityMotion && git pull

# 1) 열거 (dry-run 으로 계수 먼저 — 스케일 가드 확인)
cd backend/training
FIREBASE_SA_PATH=/workspace/firebase-sa.json python3 datagen/enumerate_internal.py \
  --bulk-approval --dry-run
# counts 확인 (final 이 100~500 인지). belle 예산 ≈371행 스케일.

# 2) 열거 본실행 → 후보 JSON (리포 밖 경로 — uid 포함 중간산출물, 커밋 금지)
FIREBASE_SA_PATH=/workspace/firebase-sa.json python3 datagen/enumerate_internal.py \
  --bulk-approval --out /workspace/internal_candidates.json

# 3) anonymize 배치 시험 (--max-rows 5 로 산출물 눈검증: 얼굴 블러 + fixtures/phase22/internal/ 키)
python3 datagen/anonymize_batch.py --candidates /workspace/internal_candidates.json \
  --out-dir /workspace/internal_anon_out --scratch-dir /workspace/internal_anon_scratch \
  --max-rows 5
aws s3 ls s3://sunity-motion-pilot-videos/fixtures/phase22/internal/ | head

# 4) 본배치 (재개 가능 — 중단 시 같은 명령 재실행)
python3 datagen/anonymize_batch.py --candidates /workspace/internal_candidates.json \
  --out-dir /workspace/internal_anon_out --scratch-dir /workspace/internal_anon_scratch

# 5) manifest 갱신본 로컬 반영 + 커밋 (pod 에서 커밋 후 push — [[gsd-pod-work-push-first]])
git add training/data/manifest.json && git commit && git push

# 6) 교사 라벨링 (별도 belle greenlight — Gemini 과금 ≈2.9x, DR-05)
#    RTMW 좌표 캐시가 신규 행에 없으므로 pod_coords 가 추출·캐시(기존 22-04 경로).
PHASE22_BELLE_GREENLIGHT=1 python3 -m distill.full_batch \
  --out-dir /workspace/phase22_distill_out --scratch-dir /workspace/phase22_distill_scratch \
  --cache-dir /workspace/phase22_coords_cache
# 신규 internal_pilot_user 행은 anonymized=true 라 selectable_rows 에 자동 포함,
# 기존 129행은 터미널 결과 파일로 skip(재과금 0).
```
</runbook>

<verification>
- `cd backend && python3 -m pytest tests/phase22/ -q` 전체 GREEN (기존 스위트 무회귀 + 신규 2파일).
- manifest.json rows 131 불변, _meta.customer_track 에 belle 2026-07-13 승인 박제.
- `grep -n "internal_pilot_user" backend/training/datagen/anonymize_batch.py` — customer 게이트 발화 source 존재.
- `grep -n "internal://firestore-analyses" backend/training/datagen/anonymize_batch.py` — provenance sentinel source_url 존재.
- `grep -rn "uploads/" backend/training/datagen/anonymize_batch.py` — 업로드 대상 키 생성에 uploads/ 부재(다운로드 원본 키 참조만 허용).
- git status clean (전 산출물 커밋).
</verification>

<success_criteria>
- 처방 B 의 로컬 조각 완성: 열거(동의 게이트+dedup+스케일 가드) → anonymize 배치(재개 가능+prefix 강제+provenance fence 충족 행 생성) → manifest 병합(멱등+uid 금지) 이 코드+테스트로 존재하고, Pod 실행은 runbook 만 따라가면 되는 상태.
- belle 2026-07-13 결정이 코드(consent_allows 기본 strict + 명시 플래그)·manifest(_meta)·LICENSE-AUDIT(§7-1/§8)·models.py 주석 4곳에 정합되게 박제.
- 신규 행이 기존 gemini_teacher/full_batch 를 무수정으로 통과(selectable)하고 test_provenance/test_manifest_consistency 를 무수정으로 통과 — 후속 라벨링에 코드 변경 0.
</success_criteria>

<output>
Create `.planning/quick/260713-jxr-b-fault-anonymize-manifest-belle-2026-07/260713-jxr-SUMMARY.md` when done.
</output>

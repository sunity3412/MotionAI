# Phase 22 학습셋·모델 라이선스 감사 (LICENSE-AUDIT)

> FT-06 산출물. Due Diligence(투자 실사)·상업 출시 게이트(A9) 대비 감사 원장.
> 근거: 22-CONTEXT D-04(belle 2026-07-06 확정) + NLM "LLM, Finetuning Guide"(belle 노트) + 22-NLM-EXTRACT §5·§11·§12 + `backend/training/data/manifest.json`(수집 마감본).
> **초판 2026-07-09(정책) → 개정 2026-07-10(수집 마감 실측 원장 반영).** 확정 라이선스 문구는 재조사 금지 — belle 확정본 그대로.
> **본 문서는 사실 정리(소스·라이선스 상태·리스크 플래그)이며 법률 자문이 아니다.** 법적 판단이 필요한 항목은 전부 §9 A9 체크리스트로 플래그.

---

## 1. 목적·범위 (수집 마감 스코프)

- **usage = training-only-no-redistribution**: 수집 영상은 **학습 전용**. **재배포 없음, 앱 미노출.** 앱 Mode1 reference 라이브러리(정은지 등록 11개)와 **완전 분리** — 수집물은 S3 `fixtures/phase22/` 비-notified prefix에만 존재하며 분석 파이프라인·앱 어디에도 서빙되지 않는다.
- **감사 대상 = manifest 131행 확정본.** `_meta.collection_complete=true`, `_meta.collection_closed` 인용:
  > closed_at: 2026-07-10 / approved_by: belle / scope: "131행(시드19 + YouTube 68 + IG 44) 기준 마감 — selectable 129행이 22-04 full batch 대상" / deferred: "내부 371 fault track(customer_track)은 anonymize.py 가명처리 후 다음 라운드 등재(이월)"
- 시드 19 = seed 17행(정은지 reference 11 정타 + 일부러-실수 6 fault) + hard_negative 2행(eval 전용, 학습 제외). selectable 129 = 131 − hard_negative 2.
- 이 문서의 수치는 전부 manifest 실측 집계(2026-07-10 마감본 파싱)이며 추정치가 아니다.

## 2. 모델 라이선스 확정표 (belle 2026-07-06 확정 + 2026-07-10 Cosmos 추가, 재조사 금지)

| 컴포넌트 | 역할 | 라이선스 | 상업 이용 |
|----------|------|----------|-----------|
| **MMPose RTMW / RTMW3D** | 포즈 추정(관절 좌표) | **Apache 2.0** | 무제한 |
| **Qwen 3.6-VL** (<35B) | 분석/추론 엔진 후보 | **Apache 2.0** | 무제한 |
| **InternVL 3.5** (1B~38B) | 분석/추론 엔진 후보 | 코드 **MIT** + LLM/Vision 백본 **Apache 2.0** | 무제한 (MAU·로열티 없음) |
| InternVL 3.5 241B-A28B (MoE) | (대형, 미사용) | Qwen License | 100M MAU 한도 조건 |
| **Cosmos-Reason2-8B** (HF `nvidia/Cosmos-Reason2-8B`, Qwen3-VL-8B 계열 post-train) | 분석/추론 엔진 후보 (bake-off 3번째, belle 2026-07-10 추가) | **NVIDIA Open Model License** (+Apache-2.0 병기) — 상업 사용·파생모델·출력물 소유 전부 명시 허용 | 무제한 |

- 분석 엔진 bake-off: 2026-07-06 원안 = **Qwen 3.6 ↔ InternVL 3.5 중 하나 선택**(D-04) → **belle 2026-07-10 확대 = Qwen 3.6 ↔ InternVL 3.5 ↔ Cosmos-Reason2 3파전**. 셋 다 라이선스 클린이므로 **성능만으로 선정** 원칙 불변.
- 참고(NLM): InternVL 3.5는 내부 LLM 백본으로 Qwen3를 채택, Cosmos-Reason2 도 Qwen3-VL 계열 post-train — 세 후보 모두 Qwen 계열 언어지능.
- **Cosmos 경로 주의**: build.nvidia.com **호스팅 API 는 Trial ToS 상 생성물의 프로덕션 사용 금지** → 우리는 **HF 가중치 셀프호스트 경로만 사용**(교사 라벨 생성에 호스팅 API 사용 금지).

### 2-1. v2 후보 (미사용, 등재만 — belle 2026-07-10, 22-CONTEXT addendum)

| 컴포넌트 | 역할 | 라이선스 | 비고 |
|----------|------|----------|------|
| Cosmos3-Nano (HF `nvidia/Cosmos3-Nano`, cosmos3_omni) | v2 생성 엔진 후보 (InternVL-U 와 병렬) | NVIDIA Open Model License 계열 추정 — **v2 착수 시 재확인 필요** | safetensors 34.9GB, gated 아님, A100 80GB 단일 탑재 가능 → 실전 배포형 후보 |
| Cosmos3-Super (HF `nvidia/Cosmos3-Super`, cosmos3_omni) | v2 품질 상한 참조 / 양자화·프리미엄 배치 생성 검토 | 상동 — **v2 착수 시 재확인 필요** | safetensors 132.6GB → A100 80GB 단일 로드 불가(멀티 GPU 필수) |

- **v1 분석엔진 bake-off 부적합**(cosmos3_omni 신규 아키텍처 = ms-swift 미지원, 디퓨전 타워 동반)이라 §2 본표(v1)와 분리 등재. 현재 미사용이므로 확정 라이선스 조사는 수행하지 않음 — v2 설계 시점에 InternVL-U vs Cosmos3-Nano(+Super 참조) 장당 생성 원가·지연 실측 비교와 함께 라이선스 확정.

## 3. 금지 목록 (상업 출시 fence)

- **LLaVA 계열** — 상업 이용 불가. 사용 금지.
- **InternVL-U**(시각 생성/편집 통합 파생모델) — 가중치·코드는 MIT지만, 정렬 학습 코퍼스 **ScaleEdit-12M**이 **CC BY-NC-SA 4.0(비상업)**. 비상업 데이터로 학습된 모델은 파생물로 해석되어 비상업 제약이 전염될 법적 취약성.
  - **결론**: InternVL-U를 그대로 상업 서빙 금지. **아키텍처만 차용**(MMDiT 생성 헤드 구조) + **시각 생성 헤드를 자사 스포츠 데이터로 완전 재학습**해 법적 제약 우회 — v2 트랙(D-03). v1은 InternVL-U 미사용(픽셀 생성 없음, SVG 기하 스펙까지만).

## 4. 데이터 수집 정책 (Phase 22 학습 코퍼스)

- **provenance 원장**: `backend/training/data/manifest.json`(행별 source_url·channel·tier·license_evidence·vision_verdict·usage) + 유튜브 `info.json` 사이드카(S3 `fixtures/phase22/`, yt-dlp 2026.07.04). 저작권 분쟁 시 출처 입증 근거(T-22-05 Repudiation 완화).
- **사람 숫자 점수 라벨 영구 금지** — 버킷(정타/fault)만. Vision 선별 verdict 도 score/severity 필드 부재 불변식(테스트 fence). 채점은 Phase 24 감점 엔진(불변).
- 출처 티어: 1순위 공식 대회 채널(정타), 2순위 강사/스튜디오(YouTube·Instagram), 개인 브로거·TV예능 제외. 채널 아닌 시리즈/영상 단위 판단(BerryTV 예능 제외·"폴인폴" 시리즈 채택).
- 전 수집 미디어(YT 68 + IG 44 = 112행)는 다운로드 전 Gemini Vision 선별 게이트 통과분만 적재 — manifest 실측: vision_verdict 보유 112/112.

## 5. 소스별 원장 (manifest 131행 실측 집계, 2026-07-10 마감본)

### 5-1. 소스·티어 총괄

| 소스 | 행 수 | 티어 | 라이선스 상태 | 리스크 |
|------|------:|------|----------------|--------|
| internal (시드) | 17 | seed | 자사 촬영 + 파일럿 참가 동의서(D-12 1겹) | 낮음 |
| internal_pilot (hard-negative) | 2 | hard_negative | 파일럿 참가 동의서(D-12 1겹), usage=eval-only-no-redistribution | 낮음 |
| YouTube | 68 | 1_official 58 + 2_studio 10 | YouTube 표준 라이선스 하 시청용 공개 — **학습 이용은 fair-use 회색** | 중 — A9 |
| Instagram | 44 | 2_studio | 공개 릴스, gallery-dl 수집 — **IG ToS 회색** | 중상 — A9 |
| **합계** | **131** | | 버킷: 정타 122 / fault 9 | |

### 5-2. 채널/계정별 상세

| 채널/계정 | 소스 | 티어 | 행 | 정타/fault | 콘텐츠 성격 | 라이선스 상태·비고 |
|-----------|------|------|---:|-----------|-------------|---------------------|
| internal (정은지) | internal | seed | 17 | 11/6 | reference 정타 11 + 일부러-실수 fault 6 | 자사 촬영·파트너 동의. 클린 |
| internal_pilot | internal | hard_negative | 2 | 0/2 | 실증 A2 피터팬·A3 power-spin 위양성 | 동의서 확보. s3_key=null(미디어 relocate 이월), 학습 제외(holdout=hard_negative_eval) |
| @uspolesportsfederation4210 (USPSF) | YouTube | 1_official | 15 | 15/0 | 미국 대회 단일 루틴 | YouTube 표준 라이선스. info.json 보관 |
| @KoreaPole (KPSA) | YouTube | 1_official | 14 | 14/0 | 한국선수권 단일 선수 루틴 | 상동 |
| @CzechPoleDance | YouTube | 1_official | 12 | 12/0 | 체코 선수권 | 상동 |
| @kpsf_official (KPSF) | YouTube | 1_official | 8 | 8/0 | POLE ART/SPORTS 등급 스펙트럼 | 상동 |
| @PoleSportOrg (PSO) | YouTube | 1_official | 7 | 7/0 | 미국, 체형·연령 다양성 | 상동 |
| @InternationalPoleSportsFed (IPSF) | YouTube | 1_official | 2 | 2/0 | WPAC 세계대회 | 상동 |
| @PoleDanceLessonsPoleDream | YouTube | 2_studio | 6 | 6/0 | 콤보 강의 | 상동 |
| @PoleFreaks | YouTube | 2_studio | 3 | 3/0 | 교육형 | 상동 |
| BerryTV "폴인폴" 시리즈 | YouTube | 2_studio | 1 | 1/0 | 동작명 라벨 강의(예능 클립 제외) | 상동 |
| eunji.poledancer (정은지 본인) | Instagram | 2_studio | 9 | 9/0 | 선수 본인 릴스 | **파트너 동의 깨끗, gold reference** — IG 중 최저 리스크 |
| polerspoledance | Instagram | 2_studio | 9 | 9/0 | 스튜디오 릴스 | gallery-dl metadata. IG ToS 회색 |
| yurim_pole | Instagram | 2_studio | 9 | 8/1 | 선수/스튜디오 (fault 1: flag 오류동작) | 상동. belle 추가 2026-07-09 |
| albertamores_polesport | Instagram | 2_studio | 8 | 8/0 | 선수 릴스 | 상동. belle 추가 2026-07-09 |
| turniroh.pole | Instagram | 2_studio | 6 | 6/0 | 스튜디오/선수 | 상동 |
| hoseoart_polesports | Instagram | 2_studio | 3 | 3/0 | 호서예전 폴스포츠학과(기관) | 상동 |

- 수집 실행 시각(실측): 2026-07-09 08:36~12:22 UTC. yt-dlp 2026.07.04.
- **customer_track(내부 371, fault 금광)**: 개별 행 미등재 — `_meta.customer_track` 구조 참조만(count 371, uid 미기재, anonymized=false). anonymize.py 가명처리 후 다음 라운드 등재(마감 시 이월 명시).

## 6. 리스크 플래그 테이블

| # | 플래그 | 대상 | 사실 관계 (실측) | 등급 | 처리 |
|---|--------|------|-------------------|------|------|
| R1 | YouTube 표준 라이선스 하 학습 이용 | YT 68행 | 시청용 공개 영상의 ML 학습 이용 = fair-use/TDM 회색지대. 완화: 학습전용·비재배포·앱 미노출, info.json provenance 보관 | 중 | **법률검토 필요(A9-1)** |
| R2 | Instagram ToS | IG 44행 | 공개 릴스 gallery-dl 수집 — IG ToS는 자동화 수집 제약(로그인월·rate-limit 회색). 유튜브보다 법적 노출 큼. 완화: 공식기관·스튜디오·선수 본인 계정 위주, 개인 추정 계정 보류, 정은지 9행은 파트너 동의 | 중상 | **법률검토 필요(A9-2)** |
| R3 | 미성년 | **실수집분 0행** | @polesportkids 는 레지스트리 enabled=false 격리 — manifest 131행 전수 확인 결과 **미성년 전용 채널 행 없음**. 잔여 리스크: 일반 대회 채널에 주니어 부문 혼입 가능성(Vision 선별 게이트는 연령 판정을 하지 않음) | 낮음(현재) | A9-3에 취급 정책 상정 유지, counsel 확인 전 미성년 전용 소스 harvest 금지 |
| R4 | 초상권·가명처리 | 공개 수집 112행 | 전 행 anonymized=false — **공개 영상 트랙은 D-12 가명처리 범위 밖(provenance만)**이며 얼굴 블러 미적용 상태로 학습 입력됨(VLM은 픽셀 입력). anonymize.py(얼굴 검출+blur, 상단 1/3 폴백)는 **고객 트랙 전용, 적재 전 강제·소급 불가**. 2026-07-13 belle 일괄승인으로 고객 트랙 등재 착수 — anonymize 강제 경로(enumerate_internal → anonymize_batch)로만 진입, 우회 불가 | 중 | 공개영상 초상권은 **법률검토 필요(A9-4)**. 고객 트랙은 가명처리 전 등재 금지(툴 인포스먼트) |
| R5 | balance_waiver | selectable 129행 | 수집분 정타 편중(fault 7/129) — 균등 게이트 3항목(per_motion_jeongta_min1·per_motion_fault_min1·max_le_2min) 미충족을 belle 승인 waiver(2026-07-10)로 문서화. fault 표본은 내부 371 fault track 이월로 충당, JSONL 단계 균등은 build_jsonl._balance_media 소유 | 낮음(법적 아님·품질) | 다음 라운드 371 등재 시 해소 |
| R6 | hard-negative 미디어 미이관 | 2행 | A2·A3 실증 영상 s3_key=null·collected=false(정직 등재). eval-only, 학습 카운트 제외 | 낮음 | fixtures/phase22/hard_negative/ relocate 이월 |
| R7 | Vision 선별 시 제3자 콘텐츠 외부 전송 | IG 44행 | 선별 게이트가 IG 후보 영상을 Gemini File API에 업로드(YT는 URL 네이티브 판정) — 제3자 콘텐츠의 Google 처리 경유 사실 기록 | 낮음 | 사실 기록(A9 부속 참고) |

## 7. 고객 데이터 동의 3겹 (D-12)

1. **파일럿**: 학원 참가 동의서 1장에 학습 활용 포함(오프라인 포괄) — hard_negative 2행·customer_track 371 의 근거.
2. **정식**: 처리방침 고지 + **가명처리(얼굴 블러 + 식별자 제거) 후 학습 활용** — 가명정보의 과학적 연구 목적 활용 구조. 모델은 포즈/모션만 학습, 얼굴 픽셀 불필요(anonymize.py가 적재 전 강제, 소급 불가).
3. **출시 전 법률 검토 1회 문서화** (DD 대비). 고지 문구 구현 = 온보딩 phase(SCENARIO 0.5).
- 매니페스트에 uid·사용자 식별자 필드 금지(테스트 fence로 강제, 실측 uid 필드 0).

## 7-1. 내부 fault 트랙 일괄승인 (belle 2026-07-13)

처방 B(22-07 게이트 FAIL 근본원인 1번 = fault 트랙 0행)의 데이터 처방으로, 내부 실사용 분석 영상을 학습 코퍼스에 등재하기 위한 belle 결정.

- **(a) 결정 내용** — 파일럿 이전 내부 데이터(직원 실증·내부 테스트 영상)의 학습사용을 일괄 승인(구두). Firestore 실측(2026-07-13 read-only 전수): `users/{uid}/analyses` 872 docs, status=done 707, video 보유 662. `learningOptIn` 필드 부재 871건 = 전부 Phase 26 동의 UI 도입 이전 업로드(파일럿 이전 내부 데이터).
- **(b) 명시 거부 제외** — `learningOptIn=false` 1건은 어떤 플래그 조합에서도 무조건 제외. 코드 fence: `enumerate_internal.consent_allows`(false 무조건 False 반환, 단위 테스트 고정).
- **(c) anonymize 강제 불변** — 얼굴 블러(anonymize.py)는 적재 전 강제, 소급 불가(D-12). 등재는 `enumerate_internal → anonymize_batch` 경로로만 진입하며, 업로드 키는 `fixtures/phase22/internal/{video_hash}.mp4` 로 하드 고정(uploads/ 생성 경로 부재 → S3 ObjectCreated→SQS 발화 차단).
- **(d) 이후 신규 데이터** — 파일럿 이후(승인 컷오프 2026-07-13 이후) 문서는 `learningOptIn=true` 엄격 필터. 부재=미동의 fail-safe 복원(`consent_allows` 기본 strict + 컷오프 이중 방어).
- **(e) 권장 후속(서면화)** — 직원 구두동의의 서면화(파일럿 참가 동의서 부속 또는 간단 확인서) 권장. A9-7(파일럿 참가 동의서 원본 보관) 실사 항목과 연결.
- **(f) 등재 행 규약** — 신규 행은 `source="internal_pilot_user"`(customer 게이트 발화)·`anonymized=true`·`consent_evidence`(본 일괄승인 근거)·`source_url="internal://firestore-analyses/{video_hash}"`(provenance sentinel — uid/analysisId 비파생, video_hash 기반만) 필드를 갖는다. uid/식별자 필드는 어떤 행에도 금지(build_manifest_row + assert_no_identifier_keys 이중 fence).

## 7-2. fault 타겟 재수집 라운드 (belle 승인 2026-07-14)

v4 aligned 게이트에서 eval18 fault 짚기 실패의 근본원인 = fault 학습신호 부족(실결함 라벨 10개)에 대한 데이터 처방. 22-02 수집에서 YT/IG fault=0 이었던 이유는 큐레이션 게이트(default 프로필)가 편집/자막/오버레이 영상을 자동 reject 해 튜토리얼(편집·자막이 표준 형식)이 통째로 걸러졌기 때문.

- **(a) 결정 내용** — 다음 2트랙 재수집을 승인(belle, 2026-07-14).
  1. **튜토리얼 타겟 외부 재수집** — fault_demo 큐레이션 프로필 신설(편집/자막 수용, "잘못된 예시" 시연 여부 짚기). 대상 = 기존 Tier-2 fault 채널 5개 재큐레이션 + fault 표적 검색쿼리 5개(`phase22_sources.yaml` 등재, 실체 검증 = 실행 단계 dry 열거→제목 스팟체크→belle 확인 후 --curate).
  2. **정은지 IG cap 상향** — eunji.poledancer `cap_per_account` 20→60. **본인 동의 확보(belle, 2026-07-14).**
- **(b) 라이선스 등급** —
  - 튜토리얼 YT 수집분 = **fair-use 회색** (기존 R1/A9-1 등급과 동일 취급). 완화 요건 동일 적용: 학습전용·비재배포·앱 미노출·info.json provenance 보관.
  - 정은지 IG 추가분 = **본인 동의로 IG 중 최저 리스크** (기존 §5-2 eunji 행 등급 승계).
- **(c) 게이트 유지** — 미성년 제외(연령 스크리닝 절차 A9-3, @polesportkids enabled=false 불변)·후프/에어리얼/실크/폴 없는 스트렝스/비폴 reject·점수 라벨 영구 금지(verdict score/severity 부재 불변식)·uploads/ prefix 금지(HIGH 1) 전부 현행 유지. **fault_demo 프로필은 편집/자막 reject 만 완화한다.** verdict 캐시는 프로필 스코프 키(`{video_id}::fault_demo`)로 분리 — 22-02 default reject 박제와 충돌 없음.
- **(d) train-on-test fence** — 정은지 성공/실패 페어 6쌍(eval18 시험지와 동일 자산)은 **학습 투입 영구 금지**. 이번 라운드 수집분(외부 튜토리얼 + eunji IG 릴스)과 무관하다 — 페어 6쌍은 이번 라운드의 수집 대상·경로에 포함되지 않는다.
- **(e) 수집 실측 수치** — **라운드 개시 시점 — 행 수 미정.** 실행(오케스트레이터, RUN-SHEET 경유) 후 keep/reject 집계·manifest 행 수를 본 절과 §5 원장에 실측 기입하고 `_meta.recollection_rounds[].status` 를 갱신한다.

## 8. belle 결정 이력 (일자순)

| 일자 | 결정 | 내용 |
|------|------|------|
| 2026-07-06 | D-04 모델 라이선스 확정 | §2 확정표 — 재조사 금지 |
| 2026-07-09 | 소싱 정책·티어 확정 | 22-DATA-SOURCES.md — 정타=공식대회 / fault=강사·스튜디오(A안) / 시리즈 단위 판단 / @polesportkids·개인 추정 IG 격리 |
| 2026-07-09 | 수집 greenlight | PHASE22_BELLE_GREENLIGHT=1 로 `--curate`(Vision 선별)→`--collect`(다운로드·S3 적재) 실행 승인. IG 계정 yurim_pole·albertamores_polesport 추가 승인 |
| 2026-07-10 | 수집 마감 | `_meta.collection_complete=true`, 131행 확정. balance_waiver 승인(fault 7/129, 내부 371 이월) |
| 2026-07-10 | bake-off 3파전 확대 | 분석 엔진 후보에 **Cosmos-Reason2-8B** 추가(§2 표 갱신). HF 셀프호스트 경로만 — 호스팅 API(Trial ToS) 사용 금지 |
| 2026-07-13 | 백본 확정 | bake-off PROVISIONAL 우승 **Qwen3-VL-8B** 공식 확정(CONFIRMED). 22-BAKEOFF-RESULT.md 판정 갱신 |
| 2026-07-13 | 내부 fault 트랙 일괄승인 | §7-1 — 파일럿 이전 내부 데이터(직원 실증·내부 테스트) 학습사용 일괄 승인(구두). learningOptIn=false 1건 제외, anonymize 강제, 이후 신규는 optIn=true 엄격. 처방 B 착수 근거 |
| 2026-07-14 | fault 타겟 재수집 라운드 승인 | §7-2 — 튜토리얼 타겟 외부 재수집(fault_demo 큐레이션 프로필, 편집/자막 reject 만 완화) + 정은지 IG cap 상향 20→60(본인 동의 확보). 점수 금지·미성년 제외·uploads/ 금지 게이트 불변 |

## 9. A9 게이트 체크리스트 (출시 전 법률검토 1회 — counsel 확인 항목)

- **본 감사 문서는 counsel 서명 전까지 `release-clean`을 함의하지 않는다.** 유튜브/인스타 등 공개 영상의 학습 이용 법적 지위는 파일럿 리서치 용도로 유예 상태. 상업 출시 게이트는 별도.

1. **공개영상 학습 이용 최종 법적 판단** — YouTube 68행(표준 라이선스, fair-use/TDM 회색). 완화 요건(학습전용·비재배포·앱 미노출·provenance 원장) 충분성 확인.
2. **IG ToS 준수 방식 확정** — IG 44행. 자동화 수집 적법성, 계정별 사후 동의 취득 필요 여부(정은지 9행 제외 35행), 로그인월·rate-limit 우회 이슈.
3. **미성년 데이터 취급 정책** — 현 수집분 0행(실측) 확인. 향후 라운드의 주니어 부문 혼입 방지 절차(연령 스크리닝) 수립.
4. **초상권·가명처리 실사** — 공개 수집 112행 얼굴 블러 미적용 상태의 학습 이용 적법성 + 고객 371 가명처리(anonymize.py) 구조·소급 불가 인포스먼트 실사.
5. **InternVL-U 생성 헤드 자체 재학습 완료 확인** — ScaleEdit-12M(CC BY-NC-SA) 전염 차단, v2 트랙 시점.
6. **정은지 파트너 동의 문서화** — reference 11 + 일부러-실수 6 + IG 9행. 구두/포괄 동의의 서면화 여부.
7. **파일럿 참가 동의서 원본 보관 확인** — hard_negative 2행 + customer_track 371 의 D-12 1겹 근거 실물.
8. **usage 준수 실사** — training-only-no-redistribution: 수집물 재배포 0·앱 노출 0·Mode1 reference 분리 유지 확인. LLaVA/InternVL-U 금지 fence(테스트) 유지 확인.
9. **Cosmos-Reason2 경로 준수 확인** — bake-off·교사 라벨·서빙 전 구간에서 HF `nvidia/Cosmos-Reason2-8B` 셀프호스트 가중치만 사용했는지 실사. build.nvidia.com 호스팅 API(Trial ToS, 생성물 프로덕션 사용 금지) 경유 산출물 0 확인. NVIDIA Open Model License 조건(상업·파생·출력물 소유 허용) 최종 검토.

---

*Phase: 22-custom-vlm-finetune · FT-06 · 초판 2026-07-09 · 개정 2026-07-10 (수집 마감 실측 반영)*

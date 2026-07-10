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

## 2. 모델 라이선스 확정표 (belle 2026-07-06, 재조사 금지)

| 컴포넌트 | 역할 | 라이선스 | 상업 이용 |
|----------|------|----------|-----------|
| **MMPose RTMW / RTMW3D** | 포즈 추정(관절 좌표) | **Apache 2.0** | 무제한 |
| **Qwen 3.6-VL** (<35B) | 분석/추론 엔진 후보 | **Apache 2.0** | 무제한 |
| **InternVL 3.5** (1B~38B) | 분석/추론 엔진 후보 | 코드 **MIT** + LLM/Vision 백본 **Apache 2.0** | 무제한 (MAU·로열티 없음) |
| InternVL 3.5 241B-A28B (MoE) | (대형, 미사용) | Qwen License | 100M MAU 한도 조건 |

- 분석 엔진은 **Qwen 3.6 ↔ InternVL 3.5 중 bake-off로 하나 선택**(D-04). 둘 다 라이선스 클린이므로 **성능만으로 선정**.
- 참고(NLM): InternVL 3.5는 내부 LLM 백본으로 Qwen3를 채택 — 두 후보 모두 Qwen 계열 언어지능.

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
| R4 | 초상권·가명처리 | 공개 수집 112행 | 전 행 anonymized=false — **공개 영상 트랙은 D-12 가명처리 범위 밖(provenance만)**이며 얼굴 블러 미적용 상태로 학습 입력됨(VLM은 픽셀 입력). anonymize.py(얼굴 검출+blur, 상단 1/3 폴백)는 **고객 트랙 전용, 적재 전 강제·소급 불가** | 중 | 공개영상 초상권은 **법률검토 필요(A9-4)**. 고객 371은 가명처리 전 등재 금지(툴 인포스먼트) |
| R5 | balance_waiver | selectable 129행 | 수집분 정타 편중(fault 7/129) — 균등 게이트 3항목(per_motion_jeongta_min1·per_motion_fault_min1·max_le_2min) 미충족을 belle 승인 waiver(2026-07-10)로 문서화. fault 표본은 내부 371 fault track 이월로 충당, JSONL 단계 균등은 build_jsonl._balance_media 소유 | 낮음(법적 아님·품질) | 다음 라운드 371 등재 시 해소 |
| R6 | hard-negative 미디어 미이관 | 2행 | A2·A3 실증 영상 s3_key=null·collected=false(정직 등재). eval-only, 학습 카운트 제외 | 낮음 | fixtures/phase22/hard_negative/ relocate 이월 |
| R7 | Vision 선별 시 제3자 콘텐츠 외부 전송 | IG 44행 | 선별 게이트가 IG 후보 영상을 Gemini File API에 업로드(YT는 URL 네이티브 판정) — 제3자 콘텐츠의 Google 처리 경유 사실 기록 | 낮음 | 사실 기록(A9 부속 참고) |

## 7. 고객 데이터 동의 3겹 (D-12)

1. **파일럿**: 학원 참가 동의서 1장에 학습 활용 포함(오프라인 포괄) — hard_negative 2행·customer_track 371 의 근거.
2. **정식**: 처리방침 고지 + **가명처리(얼굴 블러 + 식별자 제거) 후 학습 활용** — 가명정보의 과학적 연구 목적 활용 구조. 모델은 포즈/모션만 학습, 얼굴 픽셀 불필요(anonymize.py가 적재 전 강제, 소급 불가).
3. **출시 전 법률 검토 1회 문서화** (DD 대비). 고지 문구 구현 = 온보딩 phase(SCENARIO 0.5).
- 매니페스트에 uid·사용자 식별자 필드 금지(테스트 fence로 강제, 실측 uid 필드 0).

## 8. belle 결정 이력 (일자순)

| 일자 | 결정 | 내용 |
|------|------|------|
| 2026-07-06 | D-04 모델 라이선스 확정 | §2 확정표 — 재조사 금지 |
| 2026-07-09 | 소싱 정책·티어 확정 | 22-DATA-SOURCES.md — 정타=공식대회 / fault=강사·스튜디오(A안) / 시리즈 단위 판단 / @polesportkids·개인 추정 IG 격리 |
| 2026-07-09 | 수집 greenlight | PHASE22_BELLE_GREENLIGHT=1 로 `--curate`(Vision 선별)→`--collect`(다운로드·S3 적재) 실행 승인. IG 계정 yurim_pole·albertamores_polesport 추가 승인 |
| 2026-07-10 | 수집 마감 | `_meta.collection_complete=true`, 131행 확정. balance_waiver 승인(fault 7/129, 내부 371 이월) |

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

---

*Phase: 22-custom-vlm-finetune · FT-06 · 초판 2026-07-09 · 개정 2026-07-10 (수집 마감 실측 반영)*

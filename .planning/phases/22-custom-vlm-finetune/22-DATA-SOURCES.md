# Phase 22 — 학습셋 소스 레지스트리 (belle 큐레이션, 2026-07-09)

> 22-02 `phase22_sources.yaml` 큐레이션의 근거. **수집=학습 전용**(S3 `fixtures/phase22/`, `usage=training-only-no-redistribution`, 앱 미노출·재배포 없음). 앱 Mode1 reference(정은지 11 등록분)와 완전 별개.
> 정책 상세 = 메모리 `phase22-data-sourcing-policy-2026-07-09.md`. 메타데이터는 yt-dlp `--flat-playlist` 열람만 수행(다운로드 0). **실제 다운로드→S3는 belle greenlight 필요.**

## 데이터 정책 (belle 확정)
- **정타 버킷** = 공식 대회 채널(선수는 정타). 후프/에어리얼후프 종목 제외(폴 아님).
- **fault/기술 버킷** = 단일강사/스튜디오 튜토리얼(A안: 랜덤 브로거·TV예능·9살신동 제외, 강사 정면·전신·고정캠 허용) + 내부 실사용 371 + 정은지 일부러-실수.
- **채널이 아니라 시리즈/영상 단위로 판단** (예: BerryTV 예능 제외, "폴인폴" 시리즈 채택).
- **수집 = 균등 샘플**(dump-all 아님; 동작별 max ≤ 2×min, 미보유 동작 ≥2종).

## Tier-1 정타 — 공식 대회 채널 (YouTube)

| 채널 | 전체 | 폴 계열 | 비고 |
|------|-----:|-----:|------|
| `@KoreaPole` (KPSA 한국협회) | 282 | 166 | 2020~25 한국선수권, "[연도 한국폴스포츠선수권] 종목 등급/부문 선수명", 단일선수 4~5분 |
| `@kpsf_official` (KPSF 한국연맹) | 276 | 204 | POLE ART/POLE SPORTS/LOW FLOW, AMATEUR~PRO 등급 스펙트럼 |
| `@InternationalPoleSportsFed` (IPSF 국제) | 2398 | 수백+ | WPAC 세계대회, 국제 다양성, POLE 필터 필요(후프 다수) |
| `@PoleSportOrg` (PSO 미국) | 1030 | 547 | 체형·연령·스타일 다양성 최고. **길이 필터 필수**(120~400s=단일루틴, 1000s+=다인블록 제외, 6/16s=타이틀카드 제외) → 유효 ~300-400 |
| `@CzechPoleDance` (체코) | 866 | 다수 | Mistrovství ČR, 선수명 구조화 |
| `@PoleSportContest` (유럽) | 371 | 다수 | 선수명+부문, ~185s 단일루틴 |
| `@uspolesportsfederation4210` (USPSF 미국) | 282 | 다수 | USPSF 대회/세미파이널 |
| `@polesportkids` | 126 | 다수 | 키즈 대회. ⚠️ **미성년 — A9 법률검토 별도 플래그**(프라이버시·동의 민감) |

정타 유효 폴 루틴 합계 ≈ **2000+**. 관건은 찾기 아닌 **균등 샘플링**.

## Tier-2 fault/기술 — 강사·스튜디오

**YouTube (강의/튜토리얼):**
| 채널/시리즈 | 규모 | 비고 |
|------|-----:|------|
| BerryTV **"폴인폴"(Fall In Pole)** 시리즈 | ~100-150 유니크 | "EP X-Y 오늘의 동작 #N [동작명]" 동작명 라벨 내장; 윈드밀·펜슬·엘보우스탠드·스콜피온 등 어휘 확장(D-15 미보유동작); 한/영 중복 dedup 필요. **BerryTV 예능클립(비키니폴·치어리더·뷰티폴)은 제외** |
| `@PoleDanceLessonsPoleDream` | 326 | 콤보 강의(짧음 ~36s) |
| `@PoleFreaks` | 175 | 교육/다큐형(길이 김) |
| `@becciedunnfitness` | 55 | 초급 스핀폴 레슨(fault 풍부) |
| `@poleplace` | 40 | 초급 스트렝스/강의 |
| `@jessicamarshpole` | 28 | 선수 공연 |
| ClickUp 리스트 단일강사 튜토리얼 | ~15 | Joyful TV(백인벌트·우나스핀·발레리나·아프로디테)·조수정(클라임)·mongsil(슈퍼맨·angel fold)·폴댄서토리(이글·헤라)·승연쌤(에어인버트)·너피·벨라리나·리하벨 등 |

**YouTube Shorts (필터 필요 — 오버레이·빠른컷·세로 전신잘림):**
`@sarahpolerbeara`(559) · `@spinwithsophia`(409) · `@CatwomanPoleAcademy`(304) · `@ValentinaGOLOVACHSHENKO`(123, 날짜만 제목) · `@Spincess24`(23, 굿즈 위주 가치낮음)

**Instagram (Tier-2, 수집 까다로움 — 로그인월·rate-limit·ToS 회색, 쿠키 인증 필요):**
- 스튜디오/기관: `hoseoart_polesports`(호서예전 폴스포츠학과) · `polerspoledance` · `turniroh.pole`
- 선수 본인: `eunji.poledancer`(**정은지, gold reference, 동의 깨끗, 고가치**) · `yurim_pole` · `albertamores_polesport`
- 보류(개인 추정): `chaei_dam_jin` · `h________.jin`

## 내부 데이터 (fault 금광, 동의·provenance 깨끗)
- 실사용 371건(수강생 실제 실수) — anonymized 후 학습 소비(22-04 build_jsonl은 anonymized/internal만)
- 정은지 일부러-실수 페어, 실증 A2 피터팬 위양성 · A3 power-spin (→ hard_negative_eval 격리, 학습 오염 금지)

## 제외
TV/예능/방송(나혼자산다·마리텔·TV조선·세상에이런일이 등), 브이로그/졸업공연, 후프 종목, Shorts 저품질(굿즈·날짜제목).

## 다음 단계
1. (문서) 본 레지스트리 belle 확인.
2. (코드) 22-02 revise — 원안(손 URL목록 `--no-playlist`) → **티어별 채널 harvest(`--yes-playlist`)+길이/종목 필터+IG 트랙**. deviation 문서화.
3. (belle greenlight) 균등 quota 샘플로 실제 다운로드→S3 `fixtures/phase22/` + provenance 매니페스트. **카피라이트 영상 prod S3 적재 = belle 승인 필요.**
4. 이후 RTMW 처리·Gemini 교사 라벨(22-04)은 Pod 필요.

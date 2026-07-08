# Sunity AI Coach

## What This Is

폴스포츠 수강생이 연습 영상을 올리면 AI가 프로 선수(정은지) 모션과 비교해 자세 교정 피드백을 주는 모바일 앱. 수강생은 학원에서 혼자 앱을 켜고 본인 영상을 올려 분석 결과와 점수를 확인한다. 현재 파일럿 MVP 단계로, 정은지 선수 시연 → 폴스포츠 학원 실증을 목표로 한다.

## Core Value

**분석 정확도.** 점수가 믿을 만하고, 첫 분석이 "전문가 수준으로 구체적"이어야 한다. 고수가 낮게 나오는 위양성(정은지 영상 41점 같은) 없이 점수가 실제 자세 품질을 반영하고, 출력은 단순 수치가 아니라 "왜 안 되는지 + 무엇이 필요한지"를 제시해야 한다 (수치는 보조, 원인이 핵심). 현장 리서치 결론: AI가 일반적 답변만 하면 수강생은 이탈하고, 각도 수치만 보여주면 강사 철학과 충돌한다 — 분석 정확도가 곧 신뢰이고, 신뢰가 곧 도입이다. 트레이드오프가 생기면 분석 정확도를 우선한다 (비용 하한은 구독료 수준).

## Requirements

### Validated

<!-- 기존 코드에서 추론 — 이미 build되어 동작하는 능력 (.planning/codebase/ 맵 + plan.md 완료 목록 기준) -->

- ✓ Expo 앱 셸 + 화면 (인트로, 바텀탭 4개, analysis flow: reference/samples/loading/result) — existing
- ✓ Firebase 익명 인증 + Firestore (회원가입 없이 게스트 진입) — existing
- ✓ S3 presigned 업로드 (앱 → S3 직접 PUT) — existing
- ✓ Lambda 비동기 분석 파이프라인 (SQS 트리거, 결과 Firestore 기록) — existing
- ✓ RunPod NLF 3D 실분석 end-to-end (YOLO11n → NLF 3D → band-constrained DTW) — existing (2026-05-29 최초 통과)
- ✓ IPSF 기반 채점 엔진 (각도/라인/안정성 차원, 균형·대칭 제거) — existing
- ✓ Cerebras LLM 한국어 코칭 문장 생성 (키 없으면 graceful no-op) — existing
- ✓ TestFlight 빌드/제출 파이프라인 (EAS Build + ASC API Key 무인 submit) — existing
- ✓ 자가입력 BodyProfile (키·몸무게·경력·통증부위·우세손) — 마이페이지 상시 편집 + 첫분석 1회 권유, BodyProfile 3-way 계약(TS↔Python↔contract.md) + 분석 doc snapshot → coach context 전달 (BODY-02). Validated in Phase 3: bodyprofileinput (2개 실기기 UAT 항목 잔여)
- ✓ CoachCommentHook 데이터 구조 + text-only Gemini 자연어 번역 (number-free, 객관) — 두 리포트(ForcePatternInference/BodyComparisonReport)에 hook 부착, 결과 화면 "강사에게 확인할 점" 병합 노출 + "강사 보조 도구" 포지셔닝. Validated in Phase 11: coachcommenthook-gemini (COACH-01, FEED-03; hook은 best-effort — 분석 절대 실패 안 함 D-08). 실 LLM E2E는 Phase 15 실증
- ✓ 분석 이전 여정(시나리오 0/0.5/1/1.5) 온보딩·업로드 가이드 — 첫 실행 튜토리얼(스와이프 3슬라이드+이미지) + 이용방법/FAQ(/help, 샘플 미리보기 대체) + 프라이버시 1줄·학습활용 opt-out(`learningOptIn` 계약 3-way, 기본 동의·해제 가능 — belle 결정 2026-07-08) + 카톡 압축본 `_talkv_` 감지 경고·앨범 재선택 + not_pole 구도/거리 안내 + F3 통증 기타 자유입력·F4 배너 정리. Validated in Phase 26: onboarding-upload-guide (ONBD-01~04; 실기기 6항목은 26-HUMAN-UAT 배치 이월, 22-04 manifest gate의 learningOptIn 필터는 Phase 22 반영 예정)

### Active

<!-- 파일럿 MVP done 기준 — 아래 세 묶음 모두 충족해야 완성 -->

**점수 신뢰도 (분석이 믿을 만해야 함):**
- [ ] Gemini 기술 인식기 어댑터 — 영상 → 기술 인식 → 관절별 EXTEND/BENT 판정 → line 차원이 의미있게 작동
- [ ] "각도 정확도 100" 아티팩트 수정 — 같은/유사 영상 비교 케이스 처리, 라벨·로직 정정
- [x] overall 점수 구성 취약성 수정 — 차원 한 개(예: 안정성)에 휘둘리지 않는 합성 (Phase 19 — IPSF 감점식 집계로 단일 major fault 지배 + stability 종합 분리 + micro-bent 0점, SCORE-06/07·TRUST-02. 실영상 end-to-end 검증은 Phase 15)
- [ ] 신뢰도 게이트 — 정은지(고수) 위양성 없음 + 스피닝 폴 포함 다양한 영상에서 인체 추적·분석 정확 (강사/운영자 신뢰의 핵심)
- [ ] **IPSF 5트랙 채점 시스템 v1 박제** — (a) Compulsory Criteria + (c) Technical Deduction + Page 9 "all components" 절대 공통 트랙. 동작 인식 실패/비등재/자유 루틴 모든 케이스에서 Page 9 절대 트랙 단독으로도 자세 품질 채점 가능 (mode3 reference 없는 채점의 IPSF 공식 근거). (b) Tech Bonus 연계 + (d) Artistic 정성 = v2 (Phase 16 → v2)

**피드백 품질 (전문가 수준 구체성 — 현장 리서치 P0):**
- [ ] 관절 각도 수치 표시 — 결과 화면에 "현재 87° → 기준 110°" 형태로
- [ ] 키포인트·중심축 오버레이 — 영상 위에 어깨/골반/무릎/손/중심축 표시 (발끝은 v2)
- [ ] 원인 → 해결 순서 피드백 — "실패 원인 → 내 몸 기준 힘 방향·중심축 → 필요한 유연성/근력 → 보조 동작", 부위별 언어(고관절/후굴/코어/내전근 등) (Cerebras 프롬프트)
- [x] "강사 보조 도구" 포지셔닝 — 결과 카피에서 AI가 강사를 대체한다는 인상 제거 (Phase 11 — "강사에게 확인할 점" 섹션 + 상단 1줄 + Mode 1 "하나의 참고일 뿐")

**두 모드 실영상 동작:**
- [ ] Mode 1 — 정은지 기준 모션 불러와 비교, 전문가 기준 점수 실영상 end-to-end
- [ ] Mode 3 — 본인 영상 2개 비교, 발전(progress) 확인 실영상 end-to-end

**기준 모션 + 진입:**
- [ ] 정은지 기준 모션 등록 — 비교 분석이 가장 정확해지는 방식(촬영 조건/앵글 통제 포함)으로 설계
- [ ] TestFlight 게스트 모드로 수강생이 혼자 Mode 1 + Mode 3 완주 가능 (실기기 검증)
- [ ] **학원 용어 3분기 시스템 박제 (Phase 16)** — 분기 1 AKA 매핑 13개 (IPSF 등재 ↔ 한국 학원 통용) + 분기 2 정은지 reference (폭스탑 등 비등재 한국 통용 동작) + 분기 3 자동 수집 + UX 카피 노출. 학원 사용자 1차 진입 시 학원 용어 그대로 입력 가능. 현장 니즈 충족: 강사 5-1 "기본기 표준화" + 운영자 5-2 "기술 데이터 표준화" + "폭스탑 3회 분석" 예시

### Out of Scope

<!-- 파일럿 MVP에서 명시적으로 제외 — 이유 포함 -->

- 결제/구독 (RevenueCat) — 파일럿은 과금 없음
- 회원가입 강제 — 게스트 모드로 충분 (북극성 = 혼자 켜고 확인)
- 결제/구독 (RevenueCat) — 파일럿은 과금 없음
- 회원가입 강제 — 게스트 모드로 충분
- 회전 360° / 모멘텀 / 예술성 차원 — 현 파이프라인 범위 밖
- 다크 모드 — 라이트 전용 (design.md)

**안티패턴 (현장 최종 전달 — 하지 말 것):** 영상 공개 커뮤니티 랭킹(개인정보 노출), 월 구독형 B2C 단독 출시(B2B 학원 우선), 프로 자세 단순 유사도 비교(기술/원인 기반이어야), 모든 동작 범용 모델, AI가 점수만 매김, "AI가 선생님 대체" 메시지. → 이대로 가면 정확도 논란·전문가 반발·개인정보 우려가 동시에 터짐.

**v2로 연기 (현장 리서치 P1/P2 — 파일럿 후):** 체형 입력+맞춤 피드백, 부상 위험 경고, 회차별 성장 그래프, 영상 인앱 다운로드(CloudFront 서명 URL), 학원 운영자 대시보드, 분석 자료 공유 제한, 프라이버시 설명 화면, 카메라 앵글 합성, 측정 차원 확장(정렬/자세), **IPSF (b) Technical Bonus 연계 가산 자동 인식** (Dynamic Combinations / Combining Spins), **IPSF (d) Artistic Flow 측정 + Stage Usage** (정성 영역 일부, 나머지는 코치 영역 영구 분리), **다국 alias 풀 구현** (`aliases.ipsf_code` / `aliases.kpsa_name` / `aliases.coach_variants`), **자동 수집 → 표준화 승격 알고리즘**. 상세는 REQUIREMENTS.md v2.

## Context

- **Brownfield, 3-component monorepo**: `/app` (RN+Expo, TS), `/backend` (Lambda Python + SAM + RunPod FastAPI GPU 서버), `/ml` (문서만 — 실 ML 코드는 `backend/shared/python/sunity_shared/analysis/`).
- **인프라 분리**: 서니티에는 이미 sunity.ai 운영 플랫폼(EC2)이 있음. Motion AI는 별도 Lambda+S3 인프라로 분리 운영. 기존 EC2에 얹지 않음.
- **분석 측정 한계 (정직)**: 현 포즈 = NLF 3D, COCO-17 8관절각 기반 → 라인/유지/각도만 측정 가능. 정렬·자세는 keypoint 부족으로 측정 불가 (Phase 3 업그레이드 대상).
- **현 핵심 블로커**: 실분석은 2026-05-29 최초 통과했으나 점수 신뢰도가 미해결 — fallback 인식기가 굽은 그립 자세에서 EXTEND 관절을 못 찾아 line이 None으로 빠지고, overall이 사실상 한 차원으로 결정됨. Gemini 인식기가 핵심 레버.
- **팀**: belle = 창업자/비개발자. 콘솔·멀티스텝 작업은 직접 넘기지 않고 Claude가 CLI/도구로 수행. 분석 도메인 정확도가 의사결정의 최우선 기준.
- **이해관계자 역학 (현장 리서치)**: 수강생(직접 사용자)은 "AI가 일반 답변만 하면" 이탈한다. 강사/선수·학원 운영자는 **도입 결정권자이자 동시에 가장 큰 저항 세력** — 설득 못 하면 학원 파일럿이 막힌다. 핵심 우려: ① AI가 강사를 대체할까 (도입 거부 원인) ② 스피닝 폴에서 분석이 정확한가 (신뢰) ③ 부상 유발 ④ 분석 자료 무분별 배포. 강사 철학: "각도가 중요한 게 아니라 힘·유연성 한계 인식이 핵심."
- **상세 컨텍스트**: 코드베이스 맵은 `.planning/codebase/`, 도메인 지식은 `docs/research/폴스포츠-지식.md`, 현장 니즈 설문은 `docs/research/폴스포츠 수강생의 설문조사.md`(=강사 설문조사, 동일), 현재 작업 큐는 `plan.md`.

## Constraints

- **Tech stack**: 결정 완료, 변경 금지 — Expo+RN(TS) / Lambda(Python)+SAM / Firestore / S3 / YOLO11→NLF 3D→MotionDTW / Cerebras LLM / EAS Build. (CLAUDE.md §3)
- **인프라**: Motion AI는 반드시 별도 Lambda+S3. 기존 sunity.ai EC2에 얹지 말 것.
- **시크릿**: AWS Parameter Store 사용. `.env` 하드코딩 금지.
- **디자인**: 브랜드 컬러 #FF4B33 (변경 금지), Pretendard, 라이트 전용. UI는 Figma 우선(fileKey jrdI7kp245HkPfLB0nclsz), design.md는 보조.
- **GPU 의존**: NLF 3D는 CUDA 필수 (CPU에서 NaN). 실분석은 RunPod Pod에 위임. Pod 생명주기 수동 — 재생성 시 proxy URL 변경 → Lambda env 동기화 필요.
- **외부 의존**: Gemini 기술 인식기는 belle의 Gemini API 키(Google AI Studio) 필요 → Parameter Store/Pod env 주입.
- **분석 동작 범위**: 초기 분석은 3~5개 동작군(후굴 계열·인버트 계열·특정 기본 포징)으로 한정. 모든 동작 범용 모델 금지 — 처음부터 전 동작 커버는 실패 가능성 큼.
- **품질 원칙**: 작은 단위 작업, 의미있는 테스트만, 이모지·슬롭 코드 금지. (CLAUDE.md §7)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 채점 차원 = IPSF 심사기준 기반 (각도/라인/안정성), 신체부위 아님 | 폴스포츠 전문 기준에 근거한 점수 | ✓ Good |
| 균형(좌우대칭) 차원 제거 | 폴 동작은 의도적 비대칭 정상 → 대칭 감점은 위양성(41점 주범) | ✓ Good |
| Mode 3 = 발전(progress) 표시, %일치 헤드라인 금지 | 절대지표 세션 간 델타로 성장 측정 | ✓ Good |
| 기술 인식층 = Gemini 어댑터로 시작(턴키) → Pole-arina식 분류기(나중) | 도메인 분류기 완성 전 빠른 레버 확보 | — Pending |
| 기준 모션 등록 = 분석 정확도 최대화 방식으로 설계 | 비교의 기준이므로 정확도가 곧 Mode 1 신뢰도 | — Pending |
| 피드백 = 수치는 보조, 원인이 핵심 (원인 → 해결 순서) | 강사 철학("각도보다 힘·유연성 한계")과 수강생 니즈("왜 안 되는지") 양쪽 충족 | — Pending |
| AI = "강사 보조 도구"로 포지셔닝 (대체 아님) | 강사/운영자의 도입 거부 1순위 우려 해소 — 학원 파일럿 성사 조건 | — Pending |
| 스피닝 폴 추적 정확도 = 신뢰 게이트에 포함 | 운영자가 명시한 신뢰 조건 ("돌아가는 폴에서 인물 정확 추적") | — Pending |
| 초기 분석 = 3~5개 동작군으로 한정 (범용 모델 금지) | 처음부터 전 동작 커버는 실패 가능성 큼 (현장 최종 전달) | — Pending |
| Mode 1 = 단순 유사도 아님, 기술/원인 기반 | "프로 자세 단순 유사도 비교"는 강사 철학과 충돌 (안티패턴) | — Pending |
| 커뮤니티 랭킹·B2C 구독 단독 출시 안 함 | 개인정보·신체 노출 우려 + B2B 학원 우선 (안티패턴) | — Pending |
| IPSF 5트랙 채점 v1 scope = (a) Compulsory Criteria + (c) Technical Deduction + Page 9 절대 공통 트랙 | NotebookLM IPSF CoP 2024-2025 lookup (2026-06-02) — Page 9 "all components" 명시로 동작 인식 실패/비등재 케이스에도 합법 채점. mode3 reference 없는 채점의 IPSF 공식 근거. (b) Tech Bonus / (d) Artistic = v2 | — Pending (Phase 16) |
| 학원 용어 처리 = 3분기 (AKA 매핑 / 정은지 reference / 자동 수집) | 학원 사용자 1차 진입 시 한국 학원 통용 용어 (폭스탑 등) 그대로 입력 가능해야 함. 13개 AKA 매핑 NotebookLM 확보. 자동 수집 = 한국 최초 학원 용어 표준화 데이터 (KPSA 미작성 영역) | — Pending (Phase 16) |
| UX 카피 박제 (분기 3 미등재 안내) | belle 직접 작성 카피 — "공식 등재되어 있지 않은 기술명입니다. 서니티는 국제 대회 기준 명칭을 기준으로 평가하며 추가로 학원에서 등록된 명칭을 사용합니다..." 변경/요약/재가공 금지 | — Pending (Phase 16) |
| (2026-06-08) 분석 정확도 핵심 차원 v1 진행 — 체형 정규화 + 힘 패턴 + 오버레이 (이전 보류 결정 무효) | belle 박제 — "분석이 제대로 되는 게 목표. 오버레이, 체형 정규화, 힘 패턴은 필수적. 어떻게든 기필코 개발하려고 하는 게 지금." 메모리 [[feedback-analysis-first]] (분석이 망하면 다 망함, 도메인 제대로 우선) 정합. 2026-06-07 "Phase 2~11 보류" 박제는 본 결정으로 무효 | — 진입 (Phase 6 CONTEXT 박제, plan-phase 2026-06-09 진입) |
| (2026-06-08) Phase 6 좌표 변환 방향 = B (프로 → 수강생 체형) | belle intent — "사용자 목적은 자신의 동작에서 수정". Phase 12 오버레이 = 사용자 영상 위에 "내 키로 환산된 정은지 자세" 표시 직관. 점수 산출은 방향 A/B 동치, 시각화만 다름 | — Pending (Phase 6 plan) |
| (2026-06-08) Phase 6 universal — confidence-tiered hybrid | confidence 낮음 = 안전 fallback (raw 비교 / Page 9 단독 / 정규화 OFF), confidence 높음 = 분석 가능한 모든 path 활성화 (5 필드 정규화 + 매칭 reference fallback + 모든 차원). 메모리 [[feedback-analysis-first]] + [[mvp-simple-pilot-quality]] 동시 정합 | — Pending (Phase 6 plan) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-07-08 — Phase 28 (dtw-motion-based-alignment: motionAlignment 계약+방출/tier 사다리/fault_zoom fps 정합+refMatch/VideoCompare 워핑/legacy 배너/채점 무접촉 게이트, ALGN-01~06) 완료 반영. D2 크롭·power-spin 싱크 한 뿌리 해소, production OTA 349aceb 라이브. 코드 리뷰 Critical 2+Warning 4 fix 반영(WR-04는 채점 무접촉으로 deferred). 실기기 6항목은 28-HUMAN-UAT 배치 이월(phase 31 후 합동). 직전: Phase 27 (분석 속도 229.6s→124.7s −46%) 완료.*
*Updated 2026-06-02: Phase 16 신설 — 학원 용어 3분기 + 5트랙 채점 v1 scope. NotebookLM IPSF CoP 2024-2025 lookup 박제. v1 신설 SCORE-05/TERM-01/TERM-DATA-01/TERM-COPY-01. v2 신설 SCORE-V2-02/03 + TERM-V2-01/02. memory studio-term-3branch-system + ipsf-5-track-scoring 박제. Active 그룹 (점수 신뢰도 / 기준 모션) 항목 추가, Out of Scope v2 보강, Key Decisions 3건 추가.*
*Updated 2026-06-08: 분석 정확도 핵심 차원 v1 진행 결정 (이전 2026-06-07 "Phase 2~11 보류" 박제 무효). v1 시퀀스 = Phase 6 → 7 → 8 → 9 → 12 → 13. belle 박제 — "오버레이, 체형 정규화, 힘 패턴은 필수적. 어떻게든 기필코 개발하려고 하는 게 지금." Phase 6 CONTEXT.md 박제 (좌표 변환 방향 B + confidence-tiered hybrid + 3 케이스 통합 schema). Key Decisions 3건 추가.*

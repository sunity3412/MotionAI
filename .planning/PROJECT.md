# Sunity AI Coach

## What This Is

폴스포츠 수강생이 연습 영상을 올리면 AI가 프로 선수(정은지) 모션과 비교해 자세 교정 피드백을 주는 모바일 앱. 수강생은 학원에서 혼자 앱을 켜고 본인 영상을 올려 분석 결과와 점수를 확인한다. 현재 파일럿 MVP 단계로, 정은지 선수 시연 → 폴스포츠 학원 실증을 목표로 한다.

## Core Value

**분석 정확도.** 점수가 믿을 만하지 않으면 나머지는 모두 무의미하다. 고수가 낮게 나오는 위양성(정은지 영상 41점 같은) 없이, 점수가 실제 자세 품질을 반영해야 한다. 트레이드오프가 생기면 분석 정확도를 우선한다 (비용 하한은 구독료 수준).

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

### Active

<!-- 파일럿 MVP done 기준 — 아래 세 묶음 모두 충족해야 완성 -->

**점수 신뢰도 (분석이 믿을 만해야 함):**
- [ ] Gemini 기술 인식기 어댑터 — 영상 → 기술 인식 → 관절별 EXTEND/BENT 판정 → line 차원이 의미있게 작동
- [ ] "각도 정확도 100" 아티팩트 수정 — 같은/유사 영상 비교 케이스 처리, 라벨·로직 정정
- [ ] overall 점수 구성 취약성 수정 — 차원 한 개(예: 안정성)에 휘둘리지 않는 합성
- [ ] 신뢰도 게이트 — 정은지(고수) 영상이 위양성 없이 신뢰할 만한 점수로 산출

**두 모드 실영상 동작:**
- [ ] Mode 1 — 정은지 기준 모션 불러와 비교, 전문가 기준 점수 실영상 end-to-end
- [ ] Mode 3 — 본인 영상 2개 비교, 발전(progress) 확인 실영상 end-to-end

**기준 모션 + 진입:**
- [ ] 정은지 기준 모션 등록 — 비교 분석이 가장 정확해지는 방식(촬영 조건/앵글 통제 포함)으로 설계
- [ ] TestFlight 게스트 모드로 수강생이 혼자 Mode 1 + Mode 3 완주 가능 (실기기 검증)

### Out of Scope

<!-- 파일럿 MVP에서 명시적으로 제외 — 이유 포함 -->

- 결제/구독 (RevenueCat) — 파일럿은 과금 없음
- 회원가입 강제 — 게스트 모드로 충분 (북극성 = 혼자 켜고 확인)
- 카메라 앵글 합성 (CameraCtrl II / UCPE) — 데이터 증강·시점보정·코치뷰. Phase 2로 분리, MVP 범위 밖
- 측정 차원 확장 (정렬: 무릎-발끝, 자세: 머리) — toe/head keypoint 필요. 포즈 데이터 업그레이드(Phase 3) 의존
- 회전 360° / 모멘텀 / 예술성 차원 — 현 파이프라인 범위 밖
- CloudFront — 영상 전송은 S3 presigned 직접 사용으로 충분
- 다크 모드 — 라이트 전용 (design.md)

## Context

- **Brownfield, 3-component monorepo**: `/app` (RN+Expo, TS), `/backend` (Lambda Python + SAM + RunPod FastAPI GPU 서버), `/ml` (문서만 — 실 ML 코드는 `backend/shared/python/sunity_shared/analysis/`).
- **인프라 분리**: 서니티에는 이미 sunity.ai 운영 플랫폼(EC2)이 있음. Motion AI는 별도 Lambda+S3 인프라로 분리 운영. 기존 EC2에 얹지 않음.
- **분석 측정 한계 (정직)**: 현 포즈 = NLF 3D, COCO-17 8관절각 기반 → 라인/유지/각도만 측정 가능. 정렬·자세는 keypoint 부족으로 측정 불가 (Phase 3 업그레이드 대상).
- **현 핵심 블로커**: 실분석은 2026-05-29 최초 통과했으나 점수 신뢰도가 미해결 — fallback 인식기가 굽은 그립 자세에서 EXTEND 관절을 못 찾아 line이 None으로 빠지고, overall이 사실상 한 차원으로 결정됨. Gemini 인식기가 핵심 레버.
- **팀**: belle = 창업자/비개발자. 콘솔·멀티스텝 작업은 직접 넘기지 않고 Claude가 CLI/도구로 수행. 분석 도메인 정확도가 의사결정의 최우선 기준.
- **상세 컨텍스트**: 코드베이스 맵은 `.planning/codebase/`, 도메인 지식은 `docs/research/폴스포츠-지식.md`, 현재 작업 큐는 `plan.md`.

## Constraints

- **Tech stack**: 결정 완료, 변경 금지 — Expo+RN(TS) / Lambda(Python)+SAM / Firestore / S3 / YOLO11→NLF 3D→MotionDTW / Cerebras LLM / EAS Build. (CLAUDE.md §3)
- **인프라**: Motion AI는 반드시 별도 Lambda+S3. 기존 sunity.ai EC2에 얹지 말 것.
- **시크릿**: AWS Parameter Store 사용. `.env` 하드코딩 금지.
- **디자인**: 브랜드 컬러 #FF4B33 (변경 금지), Pretendard, 라이트 전용. UI는 Figma 우선(fileKey jrdI7kp245HkPfLB0nclsz), design.md는 보조.
- **GPU 의존**: NLF 3D는 CUDA 필수 (CPU에서 NaN). 실분석은 RunPod Pod에 위임. Pod 생명주기 수동 — 재생성 시 proxy URL 변경 → Lambda env 동기화 필요.
- **외부 의존**: Gemini 기술 인식기는 belle의 Gemini API 키(Google AI Studio) 필요 → Parameter Store/Pod env 주입.
- **품질 원칙**: 작은 단위 작업, 의미있는 테스트만, 이모지·슬롭 코드 금지. (CLAUDE.md §7)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 채점 차원 = IPSF 심사기준 기반 (각도/라인/안정성), 신체부위 아님 | 폴스포츠 전문 기준에 근거한 점수 | ✓ Good |
| 균형(좌우대칭) 차원 제거 | 폴 동작은 의도적 비대칭 정상 → 대칭 감점은 위양성(41점 주범) | ✓ Good |
| Mode 3 = 발전(progress) 표시, %일치 헤드라인 금지 | 절대지표 세션 간 델타로 성장 측정 | ✓ Good |
| 기술 인식층 = Gemini 어댑터로 시작(턴키) → Pole-arina식 분류기(나중) | 도메인 분류기 완성 전 빠른 레버 확보 | — Pending |
| 기준 모션 등록 = 분석 정확도 최대화 방식으로 설계 | 비교의 기준이므로 정확도가 곧 Mode 1 신뢰도 | — Pending |

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
*Last updated: 2026-05-29 after initialization*

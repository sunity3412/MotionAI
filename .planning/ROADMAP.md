# Roadmap: Sunity AI Coach

## Overview

이 로드맵은 그린필드가 아니다. 앱은 2026-05-29에 이미 end-to-end로 동작한다 (RN 앱 → S3 presigned 업로드 → Lambda/SQS 파이프라인 → RunPod NLF 3D 분석 → IPSF 채점 → Firestore → 결과 화면). 인프라 골격(walking skeleton)은 완성되어 있다. 남은 일은 **이 파이프라인을 신뢰할 수 있게 만들고 파일럿 MVP를 완성하는 것**이다.

핵심 가치는 분석 정확도다. 점수가 믿을 만하고 첫 분석이 "전문가 수준으로 구체적"이어야 한다. 따라서 여정은 **점수 신뢰도 먼저 → 그 위에 피드백 품질 → 두 모드 실영상 동작 → 신뢰 게이트 검증 → 실기기 전달** 순으로 흐른다. 현 블로커는 `FallbackRecognizer`가 굽은 그립 자세에서 EXTEND 관절을 못 찾아 `line` 차원이 None으로 빠지고 overall이 사실상 한 차원으로 결정되는 것이다. Gemini 기술 인식기가 이 모든 것을 푸는 핵심 레버이므로 가장 먼저 온다. 두 모드와 피드백 품질이 모두 신뢰할 만한 점수에 의존하기 때문이다.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Gemini 기술 인식기** - 영상→기술 인식→관절별 EXTEND/BENT 판정으로 line 차원을 의미있게 살린다 (핵심 레버)
- [ ] **Phase 2: Overall 점수 합성 견고화** - 단일 차원에 휘둘리지 않는 안정적 overall 합성
- [ ] **Phase 3: 각도 정확도 100 아티팩트 수정** - 같은/유사 영상 비교 시 잘못된 라벨·점수 정정
- [ ] **Phase 4: 실측 관절 각도 표시 + 키포인트 오버레이** - "현재 87° → 기준 110°" 실데이터 + 어깨/골반/무릎/손/중심축 오버레이
- [ ] **Phase 5: 원인→해결 피드백** - "실패 원인 → 필요한 힘/유연성 → 보조 동작" 순서 코칭 (Cerebras 프롬프트)
- [ ] **Phase 6: 강사 보조 도구 포지셔닝** - 결과 카피에서 AI가 강사를 대체한다는 인상 제거
- [ ] **Phase 7: 정은지 기준 모션 등록** - 비교 정확도를 최대화하는 방식으로 기준 모션 등록
- [ ] **Phase 8: Mode 1 실영상 동작** - 정은지 기준 비교 + 전문가 점수 end-to-end
- [ ] **Phase 9: Mode 3 발전 추적 동작** - 본인 영상 2개 비교로 progress 확인 end-to-end
- [ ] **Phase 10: 신뢰도 게이트 검증** - 고수 위양성 없음 + 스피닝 폴 추적 정확도 (강사/운영자 신뢰)
- [ ] **Phase 11: TestFlight 게스트 완주** - 실기기에서 수강생 혼자 Mode 1 + Mode 3 완주

## Phase Details

### Phase 1: Gemini 기술 인식기
**Goal**: 영상에서 기술을 인식하고 관절별 EXTEND/BENT를 판정해 line 차원이 None으로 빠지지 않고 의미있게 산출된다 — 점수 신뢰도 전체를 푸는 핵심 레버
**Mode:** mvp
**Depends on**: Nothing (first phase — 기존 `TechniqueRecognizer` Protocol 위에 어댑터 교체)
**Requirements**: SCORE-01
**Scope 제약**: 초기 인식 대상은 3~5개 동작군(후굴 계열·인버트 계열·특정 기본 포징)으로 한정. 모든 동작 범용 모델 금지.
**Success Criteria** (what must be TRUE):
  1. 굽은 그립을 포함한 폴 동작 영상에서 line 차원이 None이 아닌 실제 점수로 산출된다
  2. 인식기가 동작 이름과 관절별 EXTEND/BENT 기대치를 반환하고, `dimensions.py`의 line 채점이 그 프로파일을 사용한다
  3. Gemini 인식기 호출 실패 시 `FallbackRecognizer`로 graceful degrade하고 분석이 크래시하지 않는다
  4. 인식 범위가 3~5개 동작군으로 한정되고, 범위 밖 동작은 명시적으로 "미지원"으로 처리된다
**Plans**: TBD
**External dependency**: belle의 Gemini API 키(Google AI Studio) 필요 → AWS Parameter Store / RunPod Pod env 주입. 키 미확보 시 Phase 1 블로킹 — belle에게 키 발급 요청 우선.

### Phase 2: Overall 점수 합성 견고화
**Goal**: overall 점수가 단일 차원(예: 안정성)에 휘둘리지 않고 안정적으로 합성된다
**Mode:** mvp
**Depends on**: Phase 1 (line 차원이 살아나야 합성이 의미를 가짐)
**Requirements**: SCORE-03
**Success Criteria** (what must be TRUE):
  1. 한 차원(안정성)만 높고 나머지가 낮은 영상에서 overall이 비현실적으로 높게 나오지 않는다
  2. 각도/라인/안정성 세 차원이 모두 overall에 의미있게 기여하고, 한 차원 결손 시 합성 규칙이 명시적으로 처리된다
  3. 동일 영상 재분석 시 overall 점수가 안정적으로 재현된다
**Plans**: TBD

### Phase 3: 각도 정확도 100 아티팩트 수정
**Goal**: 같은/유사 영상 비교 시 "각도 정확도 100" 아티팩트 없이 정확한 라벨과 점수가 표시된다
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: SCORE-02
**Success Criteria** (what must be TRUE):
  1. 같은 영상 2개를 비교해도 "각도 정확도 100"이 자동으로 찍히지 않고 실제 정렬 결과를 반영한다
  2. 각도 차원 라벨·로직이 정정되어 결과 화면에 표시되는 수치가 실제 측정값과 일치한다
  3. 유사하지만 동일하지 않은 영상에서 100이 아닌 차등 점수가 나온다
**Plans**: TBD

### Phase 4: 실측 관절 각도 표시 + 키포인트 오버레이
**Goal**: 결과 화면에 관절 각도 수치가 "현재 87° → 기준 110°" 형태로 표시되고(실데이터), 영상 위에 어깨·골반·무릎·손 키포인트와 중심축이 오버레이로 그려진다
**Mode:** mvp
**Depends on**: Phase 3 (정확한 각도 채점 위에 표시)
**Requirements**: FEED-01, VIS-01
**Success Criteria** (what must be TRUE):
  1. 결과 화면 angleGuide가 백엔드가 산출한 실제 user current 각도를 표시한다 (fixture 아님)
  2. 각 관절이 "현재 N° → 기준 M°" 형태로 현재값과 기준값을 나란히 보여준다
  3. 데이터 계약(`analysis.ts` ↔ `models.py` ↔ `assemble.py`)이 lockstep으로 갱신되어 currentAngle 키가 양쪽에 존재한다
  4. 영상 프레임 위에 어깨·골반·무릎·손 키포인트와 중심축이 오버레이로 표시된다 (발끝은 toe keypoint 미지원 — v2)
**Plans**: TBD
**UI hint**: yes

### Phase 5: 원인→해결 피드백
**Goal**: 피드백이 "실패 원인 → 내 몸 기준 힘 쓰는 방향·중심축 → 필요한 유연성/근력 → 보조 동작" 순서로 구성되고, 부위별 언어로 표현된다 (수치는 보조, "왜 안 되는지 + 무엇이 부족한지"가 한 세트)
**Mode:** mvp
**Depends on**: Phase 4 (실측 각도 위에 원인 코칭)
**Requirements**: FEED-02
**Success Criteria** (what must be TRUE):
  1. KISMAM Top-3가 "무릎 신전 부족" 수준이 아니라 "왜 이 동작이 안 되는지 + 어디에 힘을 줘야 하는지" 언어로 번역된다
  2. 각 피드백 항목이 원인 → 힘 쓰는 방향·중심축 → 필요한 유연성/근력 → 보조 동작 순서로 제시된다
  3. 코칭이 부위별 언어(고관절·후굴·코어·내전근·전완근·광배 등)와 힘의 방향성을 사용한다
  4. Cerebras 키 미설정 시에도 graceful no-op로 분석이 완료되고 fallback 카피가 표시된다
**Plans**: TBD
**UI hint**: yes

### Phase 6: 강사 보조 도구 포지셔닝
**Goal**: 결과 화면 카피가 AI를 "강사 보조 도구"로 포지셔닝한다 (AI가 강사를 대체한다는 인상 제거)
**Mode:** mvp
**Depends on**: Phase 5 (피드백 카피가 확정된 위에 포지셔닝 톤 적용)
**Requirements**: FEED-03
**Success Criteria** (what must be TRUE):
  1. 결과 화면 어디에도 AI가 강사를 대체한다는 표현이 없다
  2. 기준 모션이 "하나의 참고일 뿐, 개인 신체 조건에 따라 다를 수 있음"으로 명시된다
  3. 카피가 "분석은 강사 피드백을 뒷받침하는 도구"라는 톤을 일관되게 유지한다
**Plans**: TBD
**UI hint**: yes

### Phase 7: 정은지 기준 모션 등록
**Goal**: 정은지 기준 모션을 등록할 수 있고, 등록 경로는 비교 분석 정확도가 최대화되는 방식(촬영 조건/앵글 통제 포함)으로 설계된다
**Mode:** mvp
**Depends on**: Phase 1 (인식기가 기준 모션의 EXTEND 프로파일을 정확히 산출해야 비교 신뢰도 확보)
**Requirements**: REF-01
**Scope 제약**: 기준 모션도 초기 3~5개 동작군(후굴/인버트/기본 포징) 범위에서 등록.
**Success Criteria** (what must be TRUE):
  1. 정은지 영상을 업로드하면 기준 모션으로 등록되어 `reference/{motionId}`에 저장되고 앱 Mode 1 선택 목록에 나타난다
  2. 등록된 기준 모션이 실제 meanAngles와 EXTEND 프로파일을 포함해 Mode 1 비교에 바로 쓰인다
  3. 촬영 조건/앵글 통제 가이드가 문서화되어 등록 정확도가 재현 가능하다
**Plans**: TBD

### Phase 8: Mode 1 실영상 동작
**Goal**: 사용자가 정은지 기준 모션을 불러와 본인 영상과 비교하고 전문가 기준 점수를 실영상으로 end-to-end 확인할 수 있다
**Mode:** mvp
**Depends on**: Phase 7 (등록된 기준 모션), Phase 2/3/4/5/6 (신뢰할 만한 점수 + 피드백)
**Requirements**: MODE-01
**Success Criteria** (what must be TRUE):
  1. 사용자가 앱에서 정은지 기준 모션을 선택해 본인 영상을 올리면 실분석 결과와 전문가 기준 점수가 표시된다
  2. `referenceMotionId`가 앱 setDoc 페이로드와 백엔드 meta 읽기에서 lockstep으로 전달되어 "기준 모션 없음" 오류가 없다
  3. 결과 화면이 KISMAM 편차, 각도 비교, 원인→해결 피드백을 fixture 없이 실데이터로 보여준다
**Plans**: TBD
**UI hint**: yes

### Phase 9: Mode 3 발전 추적 동작
**Goal**: 사용자가 본인 영상 2개를 비교해 발전(progress)을 실영상으로 end-to-end 확인할 수 있다
**Mode:** mvp
**Depends on**: Phase 8 (Mode 1 실영상 검증으로 채점/표시 경로 안정화)
**Requirements**: MODE-02
**Success Criteria** (what must be TRUE):
  1. 사용자가 본인 영상 2개를 올리면 절대 지표의 세션 간 델타가 발전으로 표시된다
  2. 헤드라인이 "%일치"가 아닌 "지난 분석보다 무릎 신전 8° 개선" 형태의 발전 메시지다
  3. 이전 분석이 없는 첫 영상에서도 graceful하게 베이스라인으로 처리되고 크래시하지 않는다
**Plans**: TBD
**UI hint**: yes

### Phase 10: 신뢰도 게이트 검증
**Goal**: 고수(정은지) 영상이 위양성 감점 없이 신뢰할 만한 점수로 산출되고, 스피닝 폴 포함 다양한 영상에서 인체 추적·분석이 정확하다 — 강사/운영자 신뢰의 핵심 게이트
**Mode:** mvp
**Depends on**: Phase 8, Phase 9 (두 모드가 실영상으로 동작한 위에 신뢰도 검증)
**Requirements**: SCORE-04
**Scope 제약**: 검증 대상은 초기 3~5개 동작군. 범위 밖 동작 false-reject는 허용(미지원 처리).
**Success Criteria** (what must be TRUE):
  1. 정은지(고수) 영상이 41점 같은 위양성 없이 자세 품질을 반영하는 높은 점수로 산출된다
  2. 스피닝 폴 영상에서 폴 회전·배경 움직임과 인체 움직임이 분리되어 인체 추적이 안정적이다
  3. `not_pole_motion` 게이트와 채점 tolerance가 정상적인 폴 영상을 false-reject하지 않도록 실footage로 튜닝된다
  4. 다양한 동작/앵글 영상 세트에서 분석이 크래시 없이 일관된 점수를 낸다
**Plans**: TBD

### Phase 11: TestFlight 게스트 완주
**Goal**: 수강생이 TestFlight 게스트 모드에서 회원가입 없이 Mode 1 + Mode 3를 혼자 실기기로 완주할 수 있다
**Mode:** mvp
**Depends on**: Phase 10 (신뢰할 만한 분석이 실기기에서 동작 확인되어야 전달 의미)
**Requirements**: DELIV-01
**Success Criteria** (what must be TRUE):
  1. 수강생이 TestFlight 빌드를 열어 익명 게스트로 진입하고 회원가입 없이 분석을 시작할 수 있다
  2. 실기기(iOS 26+ 포함)에서 Mode 1 영상 비교를 크래시 없이 완주하고 결과를 본다 (letterSpacing SIGABRT 회귀 없음)
  3. 실기기에서 Mode 3 발전 비교를 완주하고 발전 메시지를 본다
  4. 업로드된 영상이 결과 화면에서 재생되고 presigned URL 만료/Content-Type 이슈가 없다
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Gemini 기술 인식기 | 0/TBD | Not started | - |
| 2. Overall 점수 합성 견고화 | 0/TBD | Not started | - |
| 3. 각도 정확도 100 아티팩트 수정 | 0/TBD | Not started | - |
| 4. 실측 관절 각도 표시 | 0/TBD | Not started | - |
| 5. 원인→해결 피드백 | 0/TBD | Not started | - |
| 6. 강사 보조 도구 포지셔닝 | 0/TBD | Not started | - |
| 7. 정은지 기준 모션 등록 | 0/TBD | Not started | - |
| 8. Mode 1 실영상 동작 | 0/TBD | Not started | - |
| 9. Mode 3 발전 추적 동작 | 0/TBD | Not started | - |
| 10. 신뢰도 게이트 검증 | 0/TBD | Not started | - |
| 11. TestFlight 게스트 완주 | 0/TBD | Not started | - |

---
*Roadmap created: 2026-05-29 (brownfield MVP — vertical slices over existing pipeline)*

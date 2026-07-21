# Phase 32: 분석 결과를 읽히게 만들기 — 해석·방법·코치 - Research

**Researched:** 2026-07-21
**Domain:** 결과 화면 재설계(RN/Expo) + 코칭 피드백 근거(모터 러닝/HCI) + 분석 엔진 레버(omni 검수·RTMW 측정층·PR 보정)
**Confidence:** HIGH (코드 경로 전수 실파일 확인) / MEDIUM (모터 러닝 문헌 — 재현 논쟁 존재, 아래 D-02 섹션에 정직 표기)

<user_constraints>
## User Constraints (from 32-CONTEXT.md)

### Locked Decisions (D-01~D-30 — verbatim)

#### A. 화면 골격
- **D-01 골격:** 요약 카드 1장(잘한 점 1 + 오늘 고칠 것 1 + 다음 행동 1 + 점수 소형 보조) + 펼침 상세. **펼침 상세도 현행 유지가 아니라 재배치·UI 점검 대상.**
- **D-02 상세 섹션 순서:** 감으로 정하지 않는다 — **사용자 심리·접근성 근거를 가진 객관적 리서치**로 순서안 도출 + 근거 제시 + belle 확인 게이트. Wulf external-focus 재검증(SEED §7 Q5, 반나절)을 이 리서치에 **한 묶음으로 포함** [belle 확정].
- **D-03 참고 지표 카드 (result.tsx:2139 구 '세부 점수'):** 존폐가 아니라 **표현 방식 문제**로 재정의. '안정성' 같은 추상 용어 대신 **"실제 심사는 이렇게 파악한다" 심사 정보 코너** 방향 후보. 흡수 여부는 목업 비교 후 결정. 어느 쪽이든 표현 전면 수정 확정 (겹침 버그는 존폐 결정에 따라 수리 또는 제거로 해소 — wave-1).
- **D-04 강사용 뷰:** 파일럿은 통합(강사가 수강생 화면을 함께 봄). 강사용은 장기 필요 — 공유형 vs 회원별 대시보드는 현장 검증 후, belle 희망은 후자 (deferred).
- **D-05 타이포:** **현행 폰트 전반이 너무 작음 → 기본 크기 상향 확정.** 강조(볼드·크기·색) 체계는 표현(B) 확정 후 목업 게이트에서.
- **D-06 잘한 점 근거:** 사실은 **측정 근거에서만**(감점 0 차원·기준 충족·mode3 개선). 문장은 친절·응원 톤 + 방법 곁들임(마이페이지 글 스타일 설정과 정합). **근거 없는 칭찬 금지** — 빈약 케이스는 응원 톤 정직 고지 후 바로 '오늘 고칠 것'으로.
- **D-07 첫 진입:** 첫 1회 코치마크 2개("오늘 고칠 건 하나만" / "자세히는 펼쳐요"), 재노출 없음.

#### B. 번역·문장 (숫자→사람 말)
- **D-08 감점 카드 문장 3단:** 상태(몸 말, 관절명 허용 — 이해용) → 왜(감점·위험 이유 1줄) → 행동(외부 큐 — 수행용). 예: "무릎이 기준보다 덜 접혔어요 → 다리 라인이 흐트러져 심사에서 감점되는 부분 → [무릎으로 가슴을 끌어안듯]".
- **D-09 수치 노출 invariant (★belle 지적으로 확립):** **헤드라인·강조에 수치 등장 금지.** 수치는 카드당 한 곳, 소형 보조로만("실제 수치로 검증했다" 신뢰 배지 — belle 원문 "신뢰를 위해 작게나마 표기"). 상세 수치·편차·규칙은 펼침. **% 환산 금지**(감점 규칙과 다른 자의적 숫자 생성 방지). 전 화면 공통 적용.
- **D-10 게임 프레임:** 감점 카드에 **목표 게이지 바**(실측 단위 그대로, 현재→목표 거리감) + **오늘의 미션**(행동 큐 결합) + **mode3 기록 갱신 배지** 확정. **적용 범위(전면 확장 여부)는 미결** — sketch에서 강도별 목업 2~3안 + 추가 아이디어 제안 후 belle 결정. 톤 잣대는 D-12와 동일.
- **D-11 문구 제작:** 동작×결함별 **고정 문구집**(Claude가 IPSF·폴스포츠 지식 문서·NotebookLM 기반 초안) + LLM은 가변부만(상황 수치·조사 연결·응원 톤). **belle 승인 선출시** → 파일럿 현장(강사·수강생) 반응으로 개정. LLM이 "무릎을 더 펴세요" 수준의 일반론을 생성하는 경로 금지.
- **D-12 용어 맵:** '안정성'·'동작 흐름'·'각도 정확도' 등 차원·지표 용어를 심사 언어 기반 사람 말로 통일하는 용어 맵 신설. **톤 기준 = 친숙하되 장난스럽지 않게** [belle 원문]. Claude 초안 → belle 승인 → 전 화면 일괄.
- **D-13 보완 운동:** 전면엔 top-1 결함 연결 운동 **1개**(왜 이 운동인지 결함→운동 연결 이유 1줄 **필수**). '다른 운동 보기' 탭 시 **가로로 펼쳐짐, 최대 3개.** 5개 세로 나열 폐지.
- **D-14 위험 결함(safetyFlags):** **게임 프레임 제외.** 차분한 안전 톤 + 왜 위험한지 + "혼자 고치지 말고 강사와 이 화면을 함께 보세요" 코치 유도. 요약 카드 바로 아래 승격(트리아지). 미션화 금지.
- **D-15 드릴다운 시트(원인·처방):** 같은 3단+문구집 원칙 적용 (별도 설계 없음).

#### C. 비교·재생 + 수리 3건
- **D-16 동작 비교 초 맞춤 (belle 최우선 수리):** DTW 신뢰 낮아도 **끄지 않는다** — 구간 시작 오프셋 자동 적용("대략 맞춤" 정직 라벨) + 사용자 ±초 **수동 미세조정 슬라이더**. "자동 정렬 꺼짐" 배지 폐지. 프레임별 완전 워핑은 고신뢰에서만(현행 유지).
- **D-17 실물 게이트 (★판단 원칙):** 동작 비교 형태(방향 제안 = 기본 양옆 동시 + 탭하면 한쪽 확대 + 가로 유지), 자세 비교 카드 존폐(+ 관절 좌표 **방향 매칭** 프로토: 몸 방향 비슷한 정은지 프레임 짝짓기, 실패 시 카드 숨김), 재생 중 큐 밀도 — 셋 다 **"고장난 현행 위에서 판단 불가"(belle)** 이므로 wave-1 수리 후 **수리된 실물을 belle과 실기기로 보고 그 자리에서 확정.**
- **D-18 재생 중 큐:** **자막+오디오 동시 출시**(오디오는 설정 on/off). 목소리 방식(기기 TTS vs 클라우드 TTS)은 같은 코칭 문장 음성 샘플 2종 belle 청취 후 확정. **Expo 오디오 모듈 1개 추가 = 신규 의존성 금지 원칙의 예외 승인 항목**(공식 소형 모듈임을 명시하고 belle 승인 받고 진행).
- **D-19 미션 선정 규칙 (★게이미피케이션 아님 — 측정 기반):** ① 위험 결함(안전 안내 우선, 게임 제외) > ② 반복 미개선 결함(mode3 이력 — belle "지속적으로 안 고쳐지는 부분") > ③ 감점 최대 결함.
- **D-20 확대비교:** 줌 쌍(내 줌 vs 정은지 줌)을 **감점 카드 안으로 인라인** — 상태(말)+증거(줌)+게이지+미션이 카드 하나에 완결. **크롭 배율 통일은 결정 불요 백엔드 수리로 wave-1**(새 분석부터, 기존 진단 = 기준 crop만 2배 넓음·재처리 불필요).
- **D-21 시각 일러스트:** 캐릭터 X, 졸라맨(단순 선) X — **"형태감 있는 고품질 인체 일러스트"가 기준선** [belle]. 샘플 제작 → belle 품질 게이트 통과 시만 도입, **미달이면 시각 표현 없이 실프레임+텍스트로 정직 폴백.**

#### D. 분석 엔진 (omni 한정 금지 — 검증된 모델 풀 재활용 [belle 지시])
- **D-22 레버 3종 전부 채택** (belle: "더 정확하고 분석에 뛰어난 건 셋 다" — 핵심 가치 '분석 정확도 우선' 정합). 단 **UI 본체(수리 3건+요약 카드+번역)가 크리티컬 패스** — 엔진 레버는 뒤 웨이브:
  - **omni 짚기·검수 보강:** 결함 짚기 정밀화 + 문구집 조립 검수 + 잘한 점 교차검증. 분석 속도 예산 내 지점 선별(phase 27의 1분대 달성 회귀 금지).
  - **RTMW 측정층 확장 (2단):** 백본이 이미 검출하는 발목·팔꿈치·손목을 측정·표시로 먼저 승격 → **감점 반영은 관절별 신뢰도 실측 게이트 통과 후만**(가림 많은 폴 동작에서 위양성 감점 유입 금지 — 신뢰 미달 관절은 감점 제외 fail-safe).
  - **PR 인버전 보정:** 거꾸로 동작 한정 좌표 품질 보정(spike 실측 오차 −58% 근거).
- **D-23 검증 루프 ("중간중간 끊임없이 판단"의 실체):** 개발 = 웨이브마다 보유 fixture 6동작 전수 스윕 게이트(kip-up 편중 금지 원칙 유지). 운영 = 분석별 자가검증 — omni가 "감점 카드 문장↔영상 일치" 스팟체크, 불일치 시 **해당 카드 숨김 + 로그 적재**(틀린 말을 내보내느니 안 보여줌).
- **D-24 SMPL:** **MVP 불요로 확정.** 근거: 최근 막힘의 주범은 포즈 모델이 아니었고(생성 AI 품질/측정층 갭/UI 버그/검증 누락), SMPL 계열은 NLF를 빼려는 바로 그 연구용 라이선스 문제를 되들임. 3D 필요가 실측으로 입증되면 유료 상용 라이선스(Meshcapade 등) 포함 재검토 — 길은 열어둠.
- **D-25 22 플라이휠 트랙(Qwen3-VL):** 32 범위 밖 유지 — belle 도메인 결정 대기 중인 독립 트랙.

#### E~H. 루프·출구·실패·진입
- **D-26 지난 미션 피드백:** mode3 요약 카드 **잘한 점 자리의 1순위 소스** = 지난 미션 개선. 헤드라인은 사람 말("무릎이 지난번보다 훨씬 더 접혔어요 — 목표에 절반 넘게 접근"), 수치는 구석 소형(D-09). 개선 없으면 다른 측정 장점 폴백. 미션→연습→확인 루프가 첫 화면에서 닫힘.
- **D-27 미션 에스컬레이션:** 2회차 미개선 = 같은 미션 + 보완 운동 우회 제안("이 운동부터 해보면 쉬워져요"). **3회차 = 코치 카드 전면 승격**("혼자 안 되는 건 자세가 아니라 방법 문제일 수 있어요 — 강사님과 이 화면을 보세요") + 물어볼 질문 자동 정리. 제품 정의 ③의 자동 발동 지점.
- **D-28 코치 질문 목록:** 자동 수집(위험 결함 항상 + 3회 미개선 미션 + 이번에 못 잰 것) + 사용자 담기(각 감점 카드 '강사님께 물어보기' 버튼). 질문은 문구집 스타일 완성문. 탭하면 해당 카드로 점프.
- **D-29 부분 실패 UX:** 측정 커버리지 정직 고지("이번엔 하반신만 확실히 잴 수 있었어요") + 잰 범위 내 미션 구성 + 못 잰 것 코치 질문 자동 등재 + 재촬영 팁 1줄(온보딩 가이드 연결).
- **D-30 전체 실패 화면(not_pole·no_human 등):** 카피·톤만 새 언어로 정비(친숙·응원·다음 행동 1개) + 재업로드 동선 점검. 구조 재설계는 안 함.

### 4대 미결 게이트 (남은 결정은 이 방식으로만 닫는다)
1. **리서치 게이트:** 상세 섹션 순서 + Wulf 재검증 → 근거 제시 + belle 확인 (D-02) — **본 문서 §"D-02 리서치 게이트 산출물"이 그 제출물**
2. **목업 게이트 (sketch):** 게임 프레임 적용 범위·강조 체계·참고 지표 형태(심사 코너 vs 흡수) → 목업 비교 + belle 결정 (D-03/D-05/D-10)
3. **실물 게이트:** 동작 비교 형태·자세 카드 존폐·큐 밀도 → wave-1 수리 후 belle 실기기 리뷰 (D-17)
4. **샘플 게이트:** TTS 목소리 방식·일러스트 품질 → belle 청취/검수 (D-18/D-21)

### Claude's Discretion
- 게이지·배지 시각 스타일(테마 토큰·design.md 준수), 코치마크 카피, 요약 카드→해당 큐 점프 동선, "함께 보기" 동선(질문 목록=진입점, 상세=펼침으로 충분), 성장 탭의 미션 추적 표기 세부, mode3/mode1 요약 카드 차별화 세부(불변식: mode3 헤드라인=발전 델타), 문구집 초안 작성(감수는 D-11 경로), 운영 자가검증 스팟체크 프롬프트 설계.
- UI 작업 전 최악 데이터 케이스 목업 선제시 원칙 유지.

### Deferred Ideas (OUT OF SCOPE)
- **강사 관리 회원별 대시보드** — belle 희망 형태. 파일럿 현장 검증(공유로 충분한가) 후 별도 phase
- **보완 운동으로 극복한 선수/사례 콘텐츠** — 콘텐츠 제작 트랙이라 별도 후보 (SEED §10)
- **수치 항상 펼침 사용자 설정(Q3-C)** — 파일럿엔 과함, 현장 요구 시 재고
- **분석 완료 푸시 알림** — 31 D-06 [AMENDED]에서 독립 기능으로 분리된 상태 유지
- **GEN3C 재평가** — depth 소스 개선 시 (31 deferred 승계)
- **22 플라이휠(Qwen3-VL) 재개** — belle 도메인 결정 대기 (D-25)
</user_constraints>

<phase_requirements>
## Phase Requirements

공식 REQ ID 매핑 없음 — **32-CONTEXT.md의 D-01~D-30이 요구사항 원본**이다. 아래는 D-결정 → 리서치 근거 매핑.

| 결정 | 리서치 지원 (본 문서 섹션) |
|------|---------------------------|
| D-01/D-02 골격·순서 | §D-02 리서치 게이트 산출물 (Shneiderman overview-first + OPTIMAL + 재검증 결과) |
| D-03 참고 지표 겹침·재정의 | §수리 3건 진단 #2 (lineHeight 근본원인) + §도메인 소스 (심사 정보 코너 재료) |
| D-05 타이포 | §타이포그래피 현황 (토큰 스케일·Pretendard 미로드) |
| D-08~D-12 번역·문구집 | §문구집 아키텍처 (fixture 패턴·grep 게이트·Cerebras 가변부) |
| D-13/D-14 운동·안전 | §기존 재료 (exercise_map·safetyFlags·InjuryRiskSection) |
| D-16 초 맞춤 | §수리 3건 진단 #1 (tier 사다리·trim_only 재활용·legacy 폴백·수동 슬라이더) |
| D-18 재생 중 큐 | §TTS 비교 (expo-speech vs Polly+expo-audio, 샘플 게이트 제작법) |
| D-19/D-26/D-27/D-28 미션 루프 | §미션 이력 스키마 (prev chain·flat 저장·계약 3면) |
| D-20 확대비교 크롭 | §수리 3건 진단 #3 (_RELAXED_MARGIN 분리 수정) |
| D-22/D-23 엔진 레버 | §엔진 레버 3종 (omni 사후 스팟체크·RTMW 확장·PR 조건부) |
| D-29/D-30 실패 UX | §기존 재료 (커버리지 신호·실패 카피 위치) |

**REQUIREMENTS.md와의 긴장 1건 (planner 주의):** FEED-01("현재 87° → 기준 110° 형태로 명확히 표시", Phase 12 Pending)의 원문 취지는 D-09(수치 헤드라인 금지, 소형 배지+펼침)와 충돌한다. **D-09(2026-07-21 belle 확립)가 우선** — FEED-01의 "수치 표시" 요구는 펼침 상세+소형 배지로 충족되는 것으로 해석한다. FEED-02(부위별 언어)·FEED-03(강사 보조 톤)은 D-08/D-12와 정합.
</phase_requirements>

## Summary

Phase 32는 "측정은 됐는데 읽히지 않는" 결과 화면을 belle 제품 정의 ①해석 ②방법 ③코치로 재구성하는 phase다. 조사 결과 **신규 개발 대상은 거의 없고, 기존 자산 21종 컴포넌트 + 저장 데이터 전부를 재배치·번역하는 작업**임이 코드 수준에서 확인됐다. 수리 3건은 전부 근본 원인이 특정됐다: (1) 참고 지표 겹침 = `result.tsx` `diagSentence` 스타일이 `typography.body`(fontSize 25)를 상속하면서 `lineHeight: 21`을 명시 — fontSize보다 작은 lineHeight가 다중 행에서 줄겹침을 만든다. (2) 동작 비교 초 맞춤 = 백엔드 `motion_alignment.py` 사다리가 저신뢰(distance>T2)에서 anchors를 **빈 배열로 버리고** disabled를 방출하는 구조가 원인 — 이미 존재하는 `trim_only` tier(warp(t)=t−u0+r0 = 정확히 "구간 시작 오프셋")로 저신뢰를 수용하면 **계약 변경 0**으로 해결된다. (3) 확대비교 크롭 = `fault_zoom._side_crop` relaxed 경로의 `_BBOX_MARGIN(1.8)×_RELAXED_MARGIN(2.0)=3.6배` — 프레이밍/마커 분리 수정 방향이 이미 합의·문서화돼 있다.

D-02 리서치 게이트(외부 근거)는 재검증을 완료했다. 접근 실패로 기각됐던 Wulf 계열 3건은 전부 실존·확인됐다(골프 X-factor 운동학 변화, good-trial 피드백, 관대한 성공 기준). 단 2024-25년 메타분석 지형이 중요하다: **외부 초점(external focus)의 원문헌 효과는 출판 편향 보정 후 크게 축소**(McKay 재분석)되고, OPTIMAL의 동기 기둥(기대감·자율성)은 근거가 약하다. 따라서 32의 번역 레이어 정당화는 "학습 효과가 증명됐다"가 아니라 **"이해 가능성"(191°를 읽지 못하는 사용자)과 안전 트리아지**에 둬야 하며, 섹션 순서안은 HCI의 overview-first(Shneiderman 1996)와 위험 우선(Kaia 선례)을 1차 근거로 제시한다 — 이 정직한 프레임 그대로 belle 게이트에 제출한다.

엔진 레버 3종의 통합 지점도 확정됐다: omni 스팟체크는 `fault_zoom` 사후 분리 패턴(status=done 이후 부분 업데이트)을 재사용해 크리티컬 패스 밖에서 돌리고, RTMW 측정층 확장은 `keypoint_frame._KEYPOINT_NAMES` 8개(어깨·엉덩이·무릎·손)를 발목·팔꿈치로 넓히는 것이 출발점이며(★각도층 `JOINT_ANGLES` 8개와 이름공간이 다름 — SEED §6-5 함정의 실체), PR 인버전 보정은 spike 006 실측(−58%/전면 적용 시 power-spin 파괴)에 따라 인버전 검출 시 조건부로만 Pod 전처리에 넣는다.

**Primary recommendation:** wave-1은 확정 진단 3건을 그대로 수리(계약 변경 0 경로 우선)하고, UI 본체는 기존 컴포넌트 재배치 + 문구집 fixture(exercise_map 선례) + D-09 grep 게이트로 구성하라. 신규 의존성은 오디오 모듈 1개(expo-speech ~14.0.8 또는 expo-audio ~1.1.1, 샘플 게이트 후 택1)만 허용된다.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 요약 카드·섹션 재배치·코치마크 | 앱 (result.tsx + 신규 컴포넌트) | — | 데이터는 전부 기존 doc 필드, 표시만 재구성 |
| 감점 카드 3단 문장 (문구집) | 백엔드 (fixture data + assemble 조립) | 앱 (렌더), Cerebras (가변부만) | 품질 통제 = 데이터로. LLM 일반론 경로 차단 (D-11) |
| 용어 맵 (D-12) | 앱+백엔드 공용 상수 | — | 라벨 단일 출처 — 앱 `deductionLabels.ts`/백엔드 라벨 상수 정합 필요 |
| 동작 비교 초 맞춤 (D-16) | 백엔드 (`motion_alignment.py` 사다리) | 앱 (`alignmentWarp.ts`/`VideoCompare` 수동 슬라이더 + legacy 폴백) | 새 분석 = 백엔드 방출 변경, 기존 doc = 앱 폴백 |
| 참고 지표 겹침 (D-03) | 앱 (result.tsx styles) | — | 스타일 버그. 존폐는 목업 게이트 |
| 확대비교 크롭 (D-20) | 백엔드 Pod (`fault_zoom.py`) | — | PNG는 분석 시 생성·저장 — 새 분석부터 적용 |
| 재생 중 큐 — 자막 | 앱 (VideoCompare + 큐 트랙) | 백엔드 (결함 프레임 인덱스 — 기존 데이터) | anglesFrames·faultZoom sourceFrameIndices·motionAlignment 이미 보유 |
| 재생 중 큐 — 오디오 (D-18) | 앱 (expo-speech 또는 expo-audio) | 클라우드 TTS 선택 시 백엔드 (Polly→S3→playback-url asset) | 샘플 게이트 후 택1 |
| 미션 선정·이력·에스컬레이션 (D-19/26/27) | 백엔드 (선정 규칙 순수 함수 + prev chain) | Firestore (flat 필드) + 앱 (표시) | mode3 `get_previous_analysis` 경로 재사용 |
| 코치 질문 목록 (D-28) | 앱 (수집 UI+점프) | 백엔드 (자동 등재 항목 방출) | 기존 "강사에게 확인할 점" 섹션 강화 |
| omni 스팟체크 (D-23) | 백엔드 (pipeline 사후 스테이지) | Firestore (검증 플래그) → 앱 (카드 숨김) | fault_zoom 사후 분리 패턴 재사용 — 속도 예산 보호 |
| RTMW 측정층 확장 (D-22) | 백엔드 (`keypoint_frame`/`assemble`/`skeleton`) + Pod | 앱 (KeypointOverlay 소비) + 계약 3면 | 표시 승격 먼저, 감점은 신뢰도 게이트 후 |
| PR 인버전 보정 (D-22) | 백엔드 Pod (pose 추론 전처리, 조건부) | — | spike 006 산출물 재사용, fixture 스윕 게이트 |
| 일러스트 (D-21) | 정적 에셋 (빌드타임 번들) | — | 런타임 생성 AI 0 invariant — 제작만 오프라인 |

## Standard Stack

### Core (전부 기존 — 신규 설치 없음)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| expo / react-native | ~54.0.33 / 0.81.5 | 앱 본체 | 스택 고정 (CLAUDE.md §3) [VERIFIED: app/package.json] |
| expo-video | ~3.0.16 | 동작 비교 재생 (VideoCompare) | 기존 사용 [VERIFIED: app/package.json] |
| react-native-svg | 15.12.1 | 게이지 바(D-10)·차트 | OctagonScore/GrowthChart 선례 — 신규 차트 lib 금지 [VERIFIED] |
| expo-screen-orientation | ~9.0.9 | 가로 확대 뷰어 유지 | 260702-t0v 선례 [VERIFIED] |
| firebase (JS) | ^12.13.0 | onSnapshot 실시간 구독 | 신규 필드도 같은 구독 경로 [VERIFIED] |
| google.genai (Python) | 기존 | omni/Gemini 스팟체크 클라이언트 | `gemini_vision_scorer._ensure_client()` lazy 패턴 [VERIFIED: 코드] |
| cerebras.cloud.sdk | 기존 | 문구집 가변부 LLM | `coach_writer.py` graceful no-op 패턴 [VERIFIED: 코드] |
| boto3 (Lambda 제공) | 기존 | Polly 호출(클라우드 TTS 선택 시) | 신규 pip 의존성 0 — Polly는 boto3 client("polly") [VERIFIED: Polly ko-KR 음성 실계정 조회] |

### 신규 후보 (샘플 게이트 후 정확히 1개만 — D-18 예외 승인 항목)
| Library | Version (SDK 54) | Purpose | When to Use |
|---------|------------------|---------|-------------|
| expo-speech | **~14.0.8** | 기기 TTS (iOS AVSpeechSynthesizer) — 서버·계약·비용 0 | 기기 목소리 샘플이 belle 청취 통과 시 |
| expo-audio | **~1.1.1** | 클라우드 TTS mp3 재생 (expo-av 후속 공식 모듈) | Polly 목소리 채택 시 (mp3 재생 필요) |

버전 출처: 로컬 `app/node_modules/expo/bundledNativeModules.json` (SDK 54의 자체 매니페스트 — 공식·권위 소스) + npm 레지스트리 교차 확인. 설치는 반드시 `npx expo install <pkg>` (SDK 호환 버전 자동 선택). ⚠ npm dist-tag `latest`는 57.x(SDK 55+ 라인)이므로 **`npm install expo-speech` 직접 실행 금지.**

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| expo-speech (기기) | Polly+expo-audio (클라우드) | 기기: 비용 0·오프라인·구현 최소·음질 기기 의존 / 클라우드: 음질 통제·백엔드 TTS 단계+S3+계약+재서명 필요·생성 지연 |
| expo-audio | expo-av ~16.0.8 | expo-av는 deprecated (SDK 54에서 expo-audio/expo-video로 대체) — 신규 채택 금지 |
| AWS Polly | Google Cloud TTS / OpenAI TTS | Polly = 기존 AWS 인프라(IAM role 권한 1줄) + ap-northeast-2 지원 + ko-KR 음성 2종(Seoyeon: standard/neural/generative, Jihye: neural) 실계정 확인. 타사는 신규 키·계정 표면 추가 |

**Installation (택1 확정 후):**
```bash
cd app && npx expo install expo-speech   # 또는: npx expo install expo-audio
```

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| expo-speech | npm | 2019-02~ (7년+) | expo 공식 배포 | github.com/expo/expo | [OK] (npm) | Approved — SDK 54 번들 매니페스트 등재 |
| expo-audio | npm | expo 공식 (SDK 51~) | expo 공식 배포 | github.com/expo/expo | [OK] (npm) | Approved — SDK 54 번들 매니페스트 등재 |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

감사 노트 (투명성): slopcheck 기본 실행이 PyPI를 조회해 두 패키지를 [SLOP]로 오판 — `--ecosystem npm` 재실행으로 [OK] 확정 (프로토콜이 경고하는 cross-ecosystem 혼동의 실사례). 또한 `slopcheck install`이 검사 후 실제 `npm install`을 수행해 홈 디렉터리(`~/package.json` — git 저장소)에 두 패키지가 설치되는 부작용 발생 → **`npm uninstall`로 즉시 원복 완료, 잔존 0건 확인.** planner는 설치 태스크에서 `slopcheck install` 대신 검증만 하거나 `npx expo install`을 직접 쓸 것. maintainer(expo org)·repo(expo/expo)·created(2019) 은 npm 메타데이터로 확인.

## D-02 리서치 게이트 산출물 — 섹션 순서 + Wulf 재검증 (belle 확인용)

### 1. Wulf external-focus 재검증 결과 (SEED §2-7의 0-3 기각 3건 — 전부 실존 확인)

| 실험 | 실체 | 재검증 결과 | 신뢰 |
|------|------|------------|------|
| 골프 어깨-골반 각 | An, Wulf & Kim (2013), *J. Motor Learning & Development* 1(1) "Increased Carry Distance and X-Factor Stretch in Golf Through an External Focus" | **확인** — 외부 큐("지면 왼쪽을 밀어내듯") 그룹이 내부 큐("체중을 왼발로")·통제 그룹 대비 X-factor stretch(어깨-골반 회전)·골반/어깨/손목 최대 각속도·비거리 모두 우수. **단일 외부 큐가 전신 협응 패턴을 실제로 바꿈** — 32 번역 레이어(D-08 3단의 '행동'단)의 핵심 가정 지지 | HIGH (원문 PDF 공개, 운동학 계측) |
| best-trials 피드백 | Chiviacowsky & Wulf (2007), *RQES* 78(2) "Feedback After Good Trials Enhances Learning" | **확인** — 좋은 시도에만 피드백 받은 그룹이 나쁜 시도에 피드백 받은 그룹보다 파지(retention) 우수. D-06(잘한 점은 측정 근거에서) 방향 지지 | HIGH (원문 확인) — 단 동기 기둥 전반의 메타 비판은 아래 참조 |
| 관대한 성공 기준 | Palmer, Chiviacowsky & Wulf (2016), *Psych. Sport & Exercise* "Enhanced expectancies facilitate golf putting" (큰 원 14cm vs 작은 원 7cm) | **확인 + 유보** — 원 연구는 큰 원(쉬운 성공 기준) 그룹의 학습 우위. **그러나 2021년 후속(*PSE*, "Different task success criteria affect expectancies... but do not improve performance")은 기대감만 바뀌고 수행 개선은 재현 실패** | MEDIUM (원문 확인·재현 혼재) |

### 2. 2024-26 메타분석 지형 (정직 표기 — 이 등급을 지우지 말 것)

| 근거 | 내용 | 32에 대한 함의 |
|------|------|---------------|
| Chua, Jimenez-Diaz, Lewthwaite, Kim & Wulf (2021), *Psychological Bulletin* 147 — 143연구 메타 | 외부 초점 우위: 수행 g=0.26, 학습(파지) g=0.58 | 원문헌 기준 외부 큐는 방향성 있게 유리 |
| **McKay 외 (2025), "Reporting bias, not external focus" — 로버스트 베이지안 재분석** (PubMed 39480294) | 출판 편향 보정 후 평균 효과 **소멸 수준**: 수행 g=0.01, 파지 g=0.15, 전이 g=0.09. "외부 초점이 항상 우월"이라는 합의에 반박 | 외부 큐를 "학습 효과 증명됨"으로 팔지 말 것. **해롭다는 증거도 없음** — 평균 효과 축소이지 역효과 아님 |
| McKay 외 (2023) + *PSE* (2024) "OPTIMAL theory's claims about motivation lack evidence" | 기대감 증진 = 약한 근거, 자율성 지원 = 이득 반대 방향의 중간 근거 (48+47 연구) | 잘한 점 먼저·관대한 톤은 **학습 개입이 아니라 UX·이탈 방지 선택**으로 정당화 (현장 리서치: 일반론 답변 → 수강생 이탈) |

**종합 판정 (belle 게이트 제출 프레임):** 32 번역 레이어의 1차 정당화는 모터 러닝 효과가 아니라 **이해 가능성**이다 — "각도 191도"는 번역 없이는 구조적으로 이해 불가(SEED §1, belle 원문)하고, 외부 큐 문장("발끝으로 천장을 밀어내듯")은 최소한 **이해·실행 가능하며 해롭지 않고, 원문헌 기준으로는 유리**하다. "우리 출력 형식(수치·교정 지시·관절명)이 OPTIMAL이 명명한 악순환 패턴"이라는 SEED §2-1 판정(high/3-0)은 유지하되, 처방의 확신 수준은 한 단계 낮춰 서술한다. **수치 삭제 금지(계층화만)** 결정(SEED §2-3)은 이 지형에서도 그대로 유효 — 피드백 축소를 지지하는 근거는 여전히 없다.

### 3. 섹션 순서안 (근거 부착 — belle 확인 게이트 제출안)

**정보 위계 1차 근거 = Shneiderman (1996) "The Eyes Have It" (IEEE VL):** "Overview first, zoom and filter, then details-on-demand" — 요약 1장 + 펼침 상세(D-01)와 정확히 동형인 30년 검증 HCI 원칙. 2차 근거 = 위험 우선 트리아지(Kaia Motion Coach, JMIR PMC8317029 — 기존 deep-research high/3-0) + OPTIMAL pull(요청 시 상세)/one-thing.

| 순서 | 섹션 | 근거 | 현행 위치와의 차이 |
|------|------|------|-------------------|
| 1 | **요약 카드 1장** (잘한 점 1·오늘 고칠 것 1·다음 행동 1·점수 소형 배지) | Shneiderman overview-first / D-01 고정 | 신설 (현행은 점수 게이지가 첫 화면) |
| 2 | **위험 결함** (있을 때만) | 트리아지 — 안전은 스크롤 이탈 전에 봐야 함. Kaia 선례 + D-14 고정 | 현행 2위 유지·승격 형태만 변경 |
| 3 | **오늘 고칠 것 상세 카드** = top-1 감점 카드 (3단 문장 + 인라인 줌 쌍 + 게이지 + 미션) | one-thing(OPTIMAL ①③ — 재현 유보 포함 방향 지지) + D-20 인라인 완결 | 신설 형태 (현행 '점수 계산 내역' 승격분 재구성) |
| 4 | **동작 비교** (초 맞춤 + 재생 중 큐) | 주장→증거 순서: 카드가 말한 것을 영상으로 확인하는 흐름. 큐가 붙으면 비교가 "코칭받는 재생"이 됨 (SEED §4-④) | 현행 6위 → 상향 |
| 5 | **나머지 감점 카드** (기본 접힘 — 탭하여 펼침) | pull 방식(OPTIMAL ①) + 수치 삭제 아닌 계층화(SEED §2-3) | 현행 '점수 계산 내역' 잔여분 |
| 6 | **성장·지난 미션 확인** (mode3) | 미션→연습→확인 루프 폐쇄(D-26). 잘한 점 헤드라인은 이미 1번 카드에 있으므로 여기는 상세 | 현행 구간별 점수 자리 통합 |
| 7 | **보완 운동** (top-1 연결 1개 + 이유 1줄, 가로 펼침 최대 3) | 행동 처방은 문제 이해 후에 와야 맥락이 생김 (D-13) | 현행 9위 → 형태 전환 |
| 8 | **강사님과 확인할 것** (코치 질문 목록 — D-28) | 화면의 끝 = 다음 행동으로 나가는 출구. 마지막 인상이 "코치를 찾아라"(제품 정의 ③) — peak-end 프레임 [ASSUMED] | 현행 8위 유지·강화 |
| 9 | **심사 정보 코너** (구 참고 지표 — 형태는 목업 게이트) | 교육 콘텐츠는 판정 뒤. '실제 심사는 이렇게 파악한다' 재료는 폴스포츠-지식.md §감점 분류에 실존 (회당 −0.2/−0.5, 20° 허용 오차, 추락 −3.0) | 현행 11위(맨 아래) 유지 또는 3번 카드로 흡수 |
| 10 | **참고하세요** (31 참고코너) | **31 D-09 invariant — 채점 표면 전부 뒤에 배치(비채점이 레이아웃으로 드러나야 함).** 이 순서를 위로 올리면 31 결정 위반 | 현행 10위 유지 (invariant) |

**순서안이 열어두는 것 (게이트별):** 세로 스크롤 vs 카드 가로 넘김(belle 끄적임 §10)은 목업 게이트에서 비교. 동작 비교 형태·자세 비교 카드 존폐·큐 밀도는 실물 게이트(D-17). 게임 프레임 강도는 목업 게이트(D-10).

**현행 순서 (참고 — result.tsx 실측):** 점수 게이지 → 부상 위험 → 성공 축하(감점 0) → 점수 계산 내역 → 구간별 점수 → 동작 비교 → 코칭 팁 → 강사에게 확인할 점 → 보완 운동 → 참고코너(31) → 참고 지표.

## 수리 3건 진단 (wave-1 — 전부 근본 원인 특정 완료)

### #1 D-16 동작 비교 초 맞춤 — 원인: disabled tier가 anchors를 버림

**현행 구조 [VERIFIED: 코드]:**
- 백엔드 `backend/shared/python/sunity_shared/analysis/motion_alignment.py` — DTW `MotionMatch` → tier 사다리: `distance ≤ T1 ∧ slopes_ok` → `warped`(프레임별 워핑) / `distance ≤ T2` → `trim_only`(첫 앵커 기준 평행이동) / 그 외 → `_disabled(distance, "low_global_confidence")` — **anchors를 빈 배열로 방출**(과약속 차단 의도, 28-02 W3).
- 앱 `app/src/lib/alignmentWarp.ts` — `warpTime()`: `trim_only`는 `warp(t) = t − u0 + r0` = **정확히 "구간 시작 오프셋"**. `VideoCompare.tsx:925~` — tier='disabled'면 "자동 정렬 꺼짐" 배지.
- `firestore_admin._validate_motion_alignment` — 역불변식: 빈 anchors는 disabled만 허용, warped/trim_only는 anchors ≥ 4 float 강제.

**권장 수리 경로 (계약 변경 0):**
1. **새 분석:** 사다리 else 분기(`low_global_confidence`)를 `disabled` 대신 **`trim_only` + reason='low_global_confidence'** 로 방출 (anchors 보존 — 첫 앵커만 있어도 오프셋 성립). `disabled`는 진짜 degenerate(empty_path/invalid_fps/insufficient_anchors)에만 남는다. tier enum·계약·validator·앱 normalize 전부 무변경. 앱은 `tier='trim_only' ∧ reason='low_global_confidence'` 를 "대략 맞춤" 정직 라벨로 렌더.
2. **기존 doc(legacy — disabled + 빈 anchors, 복구 불가):** 앱 폴백 — `result.faultZoomComparisons`의 `userFrameIdx`/`refFrameIdx`(refMatch='dtw', 31-08부터 방출)로 대략 오프셋 산출: `offset ≈ refFrameIdx/ref_fps − userFrameIdx/user_fps`. `pickCompareFrames()` (result.tsx:855) 가 이미 이 필드를 소비 중.
3. **수동 ±초 슬라이더 (전 tier 공통):** 워핑 목표시각의 **단일 경유 지점**이 이미 존재 — `VideoCompare` 의 클램프된 warp 타깃 계산(WR-01 경로, "right 쓰기의 유일한 warp 경유 지점" 주석 명시). 여기에 `manualOffsetSec` 상태를 더해 `clamp(warp(cL) + manualOffset, 0, dR)` 로 확장하면 drift 보정 tick·togglePlay·seek 전부 자동 반영된다. 세션 상태로 시작(영속화는 실물 게이트 후 판단).

**fps 함정 (phase 31 실증 — 반드시 준수):** reference doc의 keypointReport는 18fps upsample(phase4_v1), 사용자·prev는 9fps. 프레임→초 환산은 반드시 각자의 `keypointReport.fps` 로 나눈다 — result.tsx:2105~2135의 `compareFrames.userIdx / (result.keypointReport?.fps || 9)` / `refIdx / (referenceKeypointReport?.fps || 18)` 패턴이 정본. joints3d(9fps) 공간과 kr 공간을 절대 섞지 말 것.

### #2 D-03 참고 지표 겹침 — 원인: lineHeight < fontSize

**[VERIFIED: 코드]** `result.tsx` 스타일:
```ts
// result.tsx (styles) — 겹침 버그 근본 원인
diagSentence: {
  ...typography.body,   // fontSize: 25 (theme/typography.ts)
  color: colors.textPrimary,
  lineHeight: 21,       // ← fontSize(25) > lineHeight(21) = 다중 행 줄겹침
  marginTop: 6,
},
```
`DimensionDiagnosisRow`(result.tsx:508)가 mode1+breakdown 보유 시 '동작 흐름'/'안정성' 진단 **장문 문장**을 이 스타일로 렌더 — belle 실기기 스크린샷의 "동작 흐름·안정성 장문 줄겹침"과 정확히 일치. RN에서 lineHeight가 fontSize보다 작으면 행이 겹친다(iOS 실기기에서 폰트 메트릭에 따라 증폭 — Expo Go 폰트 폴백으로 세션 중 오판했던 이력이 SEED §10에 기록됨). 수리 = lineHeight ≥ fontSize×1.4(≈35) 또는 더 작은 토큰으로 교체. **단 D-03 결정에 따라 이 섹션 자체가 '심사 정보 코너'로 전환/흡수될 수 있으므로, wave-1에서는 최소 수리(겹침 해소)만 하고 표현 전면 수정은 목업 게이트 이후.**

### #3 D-20 확대비교 크롭 — 원인: relaxed 경로만 3.6배

**[VERIFIED: 코드 + 메모리 faultzoom-reference-crop-2x-wider-diagnosed]** `fault_zoom.py::_side_crop`:
- valid(신뢰 좌표) 경로: bbox × `_BBOX_MARGIN`(1.8) × margin **1.0**
- relaxed(저신뢰 좌표 — 정은지 쪽이 도립·가림으로 conf<0.5 36~46%) 경로: bbox × 1.8 × `_RELAXED_MARGIN`(**2.0**) = **3.6배** → 프레임 경계 클램프 → 전신처럼 보임 + 마커 미표시.

**합의된 수정 방향 (메모리 박제, 미실행):** 하나의 신뢰도 게이트가 프레이밍(좌표 오차 둔감)과 마커(민감)를 동시에 결정하는 구조를 **분리** — 프레이밍은 양측 동일 배율(1.8, relaxed도 margin=1.0), 마커는 현행 신뢰도 게이트 유지(relaxed는 앵커 원 생략 유지). display 전용 — 채점·veto 무접촉(점수 불변). **새 분석부터 적용**(PNG는 분석 시 생성·S3 저장, 재처리 불필요 — 재처리 금지 근거는 메모리에 반증 3건과 함께 박제: 같은 RTMW 엔진이라 재처리해도 신뢰도 동일). 검증 = Pod에서 저장된 분석 데이터로 수정 전/후 crop PNG 육안 비교(앱·시뮬레이터 불필요, 재현 입력 `csKWYvI3…/f54cf3e080d74c` 파워스핀).

## 엔진 레버 3종 — 통합 지점 (뒤 웨이브)

### omni 짚기·검수 (D-22/D-23)

- **통합 패턴 = 사후 분리 (크리티컬 패스 밖).** pipeline `_process` 는 `firestore_complete` 스테이지(app.py:5236)에서 status='done' 확정 후 `fault_zoom` 스테이지(app.py:5290)를 사후 부분 업데이트로 돌린다 — omni 스팟체크는 이 자리(fault_zoom 후행 또는 병행)에 새 사후 스테이지로 넣고, 결과는 `update_analysis_*` 계열 부분 업데이트로 doc에 검증 플래그를 쓴다. 이러면 "분석 속도 회귀 금지" 예산을 구조적으로 지킨다(사용자 체감 시간 = status done까지).
- **클라이언트 = 기존 `google.genai` lazy 패턴** (`gemini_vision_scorer._ensure_client()` — top-level import 금지, graceful 실패). 모델 ID는 env 주입(`GEMINI_MODEL` 선례) — 현행 분석 기본값 `gemini-3.1-pro-preview` [VERIFIED: 코드].
- **⚠ "omni" 모델 실체 [ASSUMED — 착수 전 확인 필수]:** spike 004에서 검증된 것은 `gemini-omni-flash-preview`의 **영상 출력**(Interactions API, 편집)뿐이다. D-23 스팟체크는 **텍스트 출력 판정**(영상+감점 카드 문장 입력 → 일치/불일치) — omni가 any-to-any로 텍스트 판정을 지원하는지, 비용이 얼마인지는 미검증. 폴백 = 현행 `gemini-3.1-pro-preview`(같은 어댑터·검증된 경로). planner는 "스팟체크 모델 선정" 태스크에 소액 스모크(1콜)를 넣을 것.
- **결정론 invariant:** temp 0 + 캐시(TechniqueCache/PROMPT_VERSION bump 선례 — [[TRUST-06]]). 스팟체크 프롬프트 버전이 바뀌면 캐시 키 bump(260705-fmg 선례).
- **불일치 처리 (D-23 고정):** 해당 감점 카드 숨김 + 로그 적재. 계약: 카드별 검증 플래그(예: `deductionBreakdown.records[i]` 대응 flat 필드 또는 별도 `spotCheck` 결과 오브젝트) — 계약 3면 + scoped validator (safetyFlags/motionAlignment "result 안으로 흐른다, 신규 kwarg 없음" 선례).
- **속도 참고 실측:** phase 27 종료 실측 229.6s→124.7s (메모리). CONTEXT의 "1분대" 표기와 편차 있음 — 예산 수치는 planner가 timingsMs 실측으로 재확인하되, 원칙은 "동기 경로에 신규 외부 호출 추가 금지".

### RTMW 측정층 확장 (D-22 — 2단)

**★ 이름공간이 두 개다 (SEED §6-5 함정의 실체) [VERIFIED: 코드]:**

| 층 | 정의 위치 | 구성 8개 | 용도 |
|----|----------|---------|------|
| **좌표 표시층** `keypointReport.joints` | `keypoint_frame._KEYPOINT_NAMES` | 어깨2·엉덩이2·무릎2·**손2**(left_hand→left_wrist 매핑) | 오버레이·crop·화살표·2D 뷰어의 좌표 소스 |
| **각도 측정층** `JOINT_ANGLES` | `skeleton.py` | **팔꿈치2**·어깨2·엉덩이2·무릎2 (각도 계산에 wrist/ankle 키포인트 내부 사용) | (T,J) 각도 행렬·감점·DTW |

31 화살표가 안 뜬 원인 = ARROW_JOINT_MAP(fault_zoom.py:828)이 요구하는 발목/팔꿈치/손목 **좌표**가 표시층에 없음(엉덩이만 3점 충족). RTMW 백본은 COCO-17 전체를 검출하므로(무릎 각도가 발목 키포인트로 이미 계산되고 있는 것이 증거) **데이터는 있는데 영속만 안 되는 상태**다.

확장 절차 (표시 승격 = 1단):
1. `_KEYPOINT_NAMES` 8 → 12 (+left/right_ankle, +left/right_elbow — wrist는 hand로 이미 존재) + `JOINT_KEY_TO_ANGLE_KEY` 매핑 + `NUM_KEYPOINTS_PHASE12` 파생.
2. KeypointReport validator(len==8 강제 부분)·firestore_admin scoped validator·계약 3면(`contract.md` + `analysis.ts` + `models.py`) lockstep. **하위호환:** 기존 doc(joints 8)과 신규 doc(joints 12)을 앱이 `joints` 배열 길이로 판별 — 앱 소비처(KeypointOverlay/PoseCompare/fault_zoom 인덱싱)는 이미 `joints` 리스트 기반이라 하드코딩 8 검사만 제거하면 됨 (실제 하드코딩 지점 전수 grep 필요).
3. **Firestore 용량·인덱스:** data 길이 T×J×2 — J 8→12는 1.5배. reference 문서는 이미 인덱스 면제([[firestore-index-entry-limit]] — keypointReport 등 6필드), analyses 쪽 면제도 기존 fix([[analyses-index-exemption-fix]]) 확인 후 신규 필드 면제 필요 여부 점검. 1MB 문서 한도는 30초 영상(9fps=270프레임) 기준 여유 있으나 18fps reference(≈540프레임×12×2)는 계산 확인.
4. **감점 반영(2단)은 별도 게이트 뒤:** 관절별 신뢰도 실측(fixture 6동작 스윕에서 발목/팔꿈치 conf 분포 측정) → 게이트 통과 관절만 감점 편입, 미달은 "표시만·감점 제외" fail-safe. `keypointReport.confidence`(T×J flat)가 관절별 신뢰도 데이터 그 자체다.
5. **화살표(ARROW_JOINT_MAP)는 수리 대상이 아니라 대체 대상** (SEED §0-A ⑪ belle 결정) — 측정층 확장으로 화살표가 "다시 뜨게" 만드는 방향으로 계획하지 말 것. 외부 큐 문장이 그 자리를 대체한다.

### PR 인버전 보정 (D-22)

- **근거 실측 (spike 006, [VERIFIED: spike 004 README]):** PersPose 위상회전(Rodrigues 회전 → H=K·R·K⁻¹ 호모그래피 워프) — invert(역수직) boneCV 1.16→0.489(**−58%**). **전면 적용은 부적격**: power-spin 1.03→**7.0**(고속 스핀에서 프레임별 워프 요동 → 추적 파괴), sideway-spin/peter-pan 동반 악화.
- **채택 형태 = 인버전 조건부:** 인버전 검출 시에만 적용. 검출 신호 후보: (a) keypoint 기하 휴리스틱(엉덩이 y < 어깨 y 지속 구간), (b) 기존 recognizer/technique profile의 동작 분류. 통합 지점 = Pod 추론 경로(`pose_estimator.py` 전처리 또는 PersPose 원안대로 모델 입력 crop 단계) — 스파이크 산출물 `pr_warp_pod.py`(spike 004 디렉터리·볼륨) 재사용.
- **게이트 (D-23):** fixture 6동작 전수 스윕(순차 — [[pipeline-not-concurrency-safe-eval-serial]]) — invert 개선 확인 + **비-인버전 5동작 무회귀**(특히 power-spin) 양방 검증. kip-up 편중 금지.

## 문구집·용어 맵 아키텍처 (D-11/D-12)

**선례 3종이 이미 코드에 있다 [VERIFIED]:**

| 선례 | 위치 | 재사용 포인트 |
|------|------|--------------|
| fixture 데이터 매핑 | `exercise_map.py` + `backend/data/corrective_exercises.json` | 문구집 = `backend/data/` JSON fixture + 순수 조립 함수(boto3/네트워크 0 — 단위테스트 가능) |
| canned 문구 + 금지어 grep 게이트 | `copy_templates.py` (33 카피 + FORBIDDEN_PHRASES + 테스트 grep 게이트) | D-09 위반("%일치"·수치 헤드라인)·"박제" 등 금지어를 같은 방식의 grep 게이트로 강제 |
| LLM 가변부 graceful | `coach_writer.py` (Cerebras, 키 미설정/실패 시 {} → 수치 폴백, "주입된 실측 데이터만, 임의 수치 생성 금지" 시스템 프롬프트 기존) | 가변부(상황 수치·조사 연결·응원 톤)만 LLM — 고정 골격은 fixture에서. LLM 전체 실패 시에도 문구집 골격만으로 출력 성립해야 함 |

**구성 제안:** 동작(6+미등재 폴백) × 결함 criterion(deductionBreakdown.records의 `criterion`/`ruleId`가 키 후보) → {상태문(몸 말), 이유문(감점·위험 1줄), 행동문(외부 큐), 코치 질문 완성문(D-28), 운동 연결 이유(D-13)}. **키 설계 주의:** 문구집 키는 반드시 실존 방출값(criterion/ruleId/keypointSet enum)과 대조해 작성 — 31 화살표의 "코드가 요구하는 데이터를 파이프라인이 안 만드는" 함정 재발 방지(§6-5). 도메인 소스 = `docs/research/폴스포츠-지식.md`(IPSF 감점 분류 실존: 회당 −0.2 정렬/라인/신장, −0.5 나쁜 각도/트랜지션, 20° 허용 오차, Flow/Shades 개념 — D-12 용어 맵의 심사 언어 원천) + NotebookLM 폴스포츠 노트북([[notebook-lm-pole-sports]]).

**용어 맵 (D-12):** 현행 라벨 단일 출처 = 앱 `DIMENSION_LABEL_KO`/`deductionLabels.ts`·백엔드 `JOINT_LABEL_KO`(skeleton.py). 용어 맵은 이들의 **교체가 아니라 상위 매핑**(측정 용어 → 심사 언어)으로 신설하고 전 화면 일괄 적용 — belle 승인 후.

## 미션 이력 스키마 (D-19/D-26/D-27)

- **읽기 경로 재사용:** `firestore_admin.get_previous_analysis(uid, ...)` — status='done' + createdAt desc 단건 조회가 이미 mode3 채점·fault_zoom에서 사용 중 [VERIFIED: 코드].
- **권장 구조 = 문서 내 체인 (별도 컬렉션 신설 없음):** 각 분석 doc의 result에 flat 미션 오브젝트를 방출 — 예: `mission: {faultKey, criterion, ruleId, cueText, selectedBy('safety'|'repeat'|'max_deduction'), streak(정수 — 직전 doc의 mission과 동일 결함이며 미개선이면 prev.streak+1, 아니면 1)}` + 다음 분석에서 `missionOutcome: {improved: bool, deltaSummary}` 산출. streak 카운터가 doc 체인을 따라 전파되므로 **N개 문서 쿼리 없이** 직전 1건 조회만으로 D-27 에스컬레이션(2회차/3회차) 판정 가능.
- **제약:** nested-array 금지 → 전부 flat scalar dict. 저장은 "result 안으로 흐른다 + scoped validator" 선례(safetyFlags/motionAlignment — complete_analysis 신규 kwarg 금지). 계약 3면 동시 수정. 미션 선정 규칙(D-19 우선순위 ①②③)은 **순수 함수**로 작성해 단위테스트(백엔드 pytest).
- **D-26 잘한 점 소스:** mode3에서 prev.mission 대비 개선 실측 → 요약 카드 헤드라인(사람 말) + 소형 수치 배지(D-09). 개선 없으면 감점 0 차원/기준 충족 폴백(D-06) — 폴백 소스도 전부 기존 측정 필드(dimensionScores·deductionBreakdown)에 있음.

## 재생 중 큐 + TTS (D-18)

**큐 타이밍 데이터는 전부 기존 [VERIFIED]:** `deductionBreakdown` 결함 + `faultZoomComparisons[].userFrameIdx`(kr 공간) + `motionAlignment`(양 영상 대응) + `anglesFrames`. 자막 큐 = VideoCompare의 tick(100ms) 루프에서 currentTime이 결함 구간에 들어오면 오버레이 표시 — 신규 의존성 0.

**TTS 두 방식 비교 (샘플 게이트 제출용):**

| 축 | A. 기기 TTS (expo-speech ~14.0.8) | B. 클라우드 TTS (Polly + expo-audio ~1.1.1) |
|----|-----------------------------------|---------------------------------------------|
| 음질 | iOS 한국어 시스템 음성(유나 계열) — 기기·OS 의존 [ASSUMED: 청감은 샘플 게이트가 판정] | Seoyeon(standard/neural/generative)·Jihye(neural) — 통제 가능 [VERIFIED: ap-northeast-2 실계정 조회] |
| 비용 | 0 | Polly neural ~$16/1M자 수준 — 파일럿 규모 무시 가능 [ASSUMED: 요금표 미재확인] |
| 지연 | 즉시 (재생 중 실시간 발화) | 분석 시 사전 생성 → 재생은 즉시. 생성 단계가 파이프라인에 추가 |
| 구현 | 앱만: `Speech.speak(text, {language:'ko-KR'})` 를 큐 타이밍에 호출 + 이전 발화 stop 처리 | 백엔드: 사후 스테이지에서 Polly synthesize → S3 `results/{uid}/{analysisId}/` mp3 + doc에 key/status → **playback-url asset 확장 패턴**(31 correctedPose/rotation 선례 — 서버가 key 구성, URL 비저장, H-02) → 앱 expo-audio 재생 |
| 계약 | 변경 0 | 3면 + asset enum + 상태 필드 (visual 필드 선례 그대로) |
| 오프라인/학원 소음 | 이어폰 전제 동일. on/off 설정(D-18 고정) | 동일 |

**샘플 게이트 제작법 (belle 청취 2종 — 저비용):** A = 시뮬레이터/실기기에서 expo-speech 1화면 스파이크(또는 근사치로 macOS `say -v Yuna` 녹음). B = `aws polly synthesize-speech --engine neural --voice-id Seoyeon --output-format mp3 --text "<같은 코칭 문장>" --profile sunity-motion out.mp3` — CLI 1커맨드, 비용 수원 미만.

## 타이포그래피 현황 (D-05)

[VERIFIED: `app/src/theme/typography.ts`]
- 현행 스케일: caption 12 / boxLabel 15 / buttonSecondary 17 / listTitle 18 / sectionTitle·button 20 / body·bodyBold 25 / heading 30 / score 50. **12~20 구간에 본문용 중간 단계가 없어** 화면 대부분이 caption(12)·boxLabel(15)로 조판됨 — belle "전반이 너무 작음"의 구조 원인.
- **Pretendard는 아직 로드되지 않았다** — fontFamily 미지정 → 시스템 폰트 폴백 (typography.ts 주석 명시). D-05 상향 작업 시 Pretendard 로드(expo-font) 동반 여부를 목업 게이트에서 함께 결정할 사안.
- **letterSpacing 음수 금지 박제:** iOS 26+ SIGABRT(빌드 9 근본 원인) — 신규 토큰도 `track()=0` 유지.
- 상향 전략 옵션: (a) 전역 토큰 값 상향 — 전 화면 파급(리스크: 다른 화면 레이아웃 붕괴, 시뮬레이터 전수 확인 필요), (b) 결과 화면용 신규 토큰 단계 추가(예: bodySm 17/bodyMd 19) 후 결과 화면부터 적용, 이후 전 화면 확산. **(b) 권장** — 파급 통제 + 목업 게이트와 정합. 하드코딩 금지 원칙은 동일(신규 값도 토큰으로만).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 오디오 재생/TTS | 커스텀 네이티브 모듈·expo-av 신규 채택 | expo-speech 또는 expo-audio (공식, SDK 54 번들 매니페스트 등재) | expo-av deprecated, 커스텀 네이티브는 EAS 빌드 리스크 |
| 클라우드 음성 합성 | 자체 TTS 서버 | AWS Polly (boto3 기존) | IAM 권한 1줄, ko-KR 음성 검증 완료 |
| 게이지/배지 렌더 | 신규 차트 라이브러리 (victory 등) | react-native-svg 직접 (OctagonScore/GrowthChart 선례) | 신규 npm 의존성 금지 (SEED §5) |
| 시간 정렬 | 새 정렬 알고리즘 | `alignmentWarp.ts` warpTime/trim_only + motionAlignment 기존 DTW | 28에서 검증·클램프·드리프트 보정까지 완비 |
| 코칭 문장 생성 | LLM 전면 생성 | 고정 문구집 fixture + Cerebras 가변부 (coach_writer graceful 패턴) | D-11 고정 — LLM 일반론 = 현장 이탈 실증 |
| 이전 분석 조회 | 신규 쿼리/컬렉션 | `get_previous_analysis` + 문서 내 체인(streak) | 인덱스 신설 불필요, 단건 조회로 에스컬레이션 판정 |
| 앱 로직 테스트 | Jest/Vitest 도입 | `node --test` + node:assert (Node 24 type stripping — pickerFailure.test.ts 선례) | belle가 의존성 1,120개 이유로 테스트 러너 반려 (SEED §5) |
| 검증 플래그 저장 | 신규 kwarg/컬렉션 | "result 안으로 흐른다" + scoped validator (safetyFlags/motionAlignment 선례) | validator 본체 무변경 원칙 유지 |

## Common Pitfalls

### Pitfall 1: 코드가 쓰는 데이터를 파이프라인이 안 만든다 (§6-5 — 31 화살표 재발 방지)
**What goes wrong:** 단위테스트 111개 통과 + 실환경 0 렌더 (ARROW_JOINT_MAP 발목/팔꿈치 좌표 부재).
**How to avoid:** 번역 레이어·문구집 키·재생 중 큐가 소비하는 필드는 **좌표 표시층 8개**(어깨2·엉덩이2·무릎2·손2)와 **각도층 8개**(팔꿈치2·어깨2·엉덩이2·무릎2)를 구분해 대조. 발목·팔꿈치·손목 **좌표** 기반 표현은 측정층 확장(뒤 웨이브) 전에는 만들 수 없다.
**Warning signs:** 문구집/큐 키에 ankle·elbow·wrist 좌표 참조가 확장 전 등장.

### Pitfall 2: 18fps kr ↔ 9fps joints3d 환산 (phase 31 실증)
reference keypointReport=18fps upsample, 사용자·프레임배열=9fps. 프레임↔초 환산은 각자의 `report.fps`로만. 하드코딩 9/18 금지 — result.tsx:2105 패턴이 정본.

### Pitfall 3: lineHeight < fontSize (D-03 겹침의 일반형)
`...typography.body`(25) 상속 후 명시 lineHeight를 더 작게 두면 겹침. 신규 스타일 작성 시 lineHeight ≥ fontSize×1.3 규칙 + **시뮬레이터가 아닌 실기기 확인**(Expo Go 폰트 폴백이 이 계열을 가림 — SEED §10 오판 이력).

### Pitfall 4: 시뮬레이터 한계 + OTA 절차
typecheck·유닛테스트는 렌더 크래시를 못 잡고, 시뮬레이터도 프로덕션 번들 고유 문제(앨범 알림창 크래시)는 못 잡는다. 대응 = 시뮬레이터 확인([[verify-ui-on-simulator-before-ota]]) + **빌드 경로 청결**(임시 worktree·node_modules 심볼릭 링크 금지) + 롤백 준비(`npx eas update:republish --group <직전 정상 group>`, 1분, 실증 완료) + expo-updates는 **완전 종료 2회째** 적용.

### Pitfall 5: 계약 3면 단면 수정
신규 필드(미션·오디오 key·검증 플래그·keypointReport 확장) 방출 시 `docs/contract.md` + `app/src/types/analysis.ts` + `models.py` 동시 수정 + firestore_admin scoped validator + 앱 normalize 대칭. 부재=legacy 하위호환(`tier?` 서술 모범).

### Pitfall 6: Firestore 제약
nested-array 금지(flat + reshape 메타), motionAlignment anchors 512 float 상한, 대형 배열 인덱스 면제(owner 계정 gcloud), 문서 1MB 한도(keypointReport J 확장 시 계산 확인).

### Pitfall 7: LLM 일반론 유입 (D-11 금지 경로)
Cerebras가 "무릎을 더 펴세요" 수준을 뱉으면 현장 이탈 실증 그대로. 방어 = 고정 문구집이 골격 소유 + LLM은 슬롯만 + copy_templates 식 금지어 grep 게이트에 D-09 위반 패턴(수치 헤드라인·% 환산) 추가.

### Pitfall 8: Gemini 캐시 스테일
스팟체크/짚기 프롬프트 변경 시 PROMPT_VERSION bump로 캐시 무효화(260705-fmg 선례). temp 0 단독은 결정론 보장 아님 — 캐시가 실 보장(TRUST-06).

### Pitfall 9: 파이프라인 동시성
스윕·eval·재분석은 순차만([[pipeline-not-concurrency-safe-eval-serial]]). fixture 6동작 게이트도 직렬.

### Pitfall 10: Pod 운영
`/health` 200 확인 전 다음 단계 진행 금지(31 사고). `start_server.sh`의 pkill 패턴이 SSH 원격 명령 문자열까지 죽이는 함정. Pod 재생성 시 proxy URL 변경 → SSM+Lambda 재동기화.

### Pitfall 11: Figma 이름 검색 무효
프레임명이 자동생성(`Group 53`) — 텍스트 내용으로 훑고, 못 찾으면 페이지 스크린샷 육안 확인(2026-07-20 belle 반박 이력). 목업 게이트 전 결과 화면 관련 Figma 프레임 존재 여부를 이 방식으로 확인.

### Pitfall 12: 31 결정과의 충돌
참고코너는 채점 표면 뒤 배치 invariant(31 D-09), "3D/회전" 문구 금지(31 D-10), 생성 AI OFF 유지(31-CLOSEOUT), 푸시 알림 범위 밖(31 D-06 AMENDED). 섹션 재배치 시 참고코너를 위로 올리지 말 것.

## Code Examples (핵심 경로 발췌 — 전부 실파일 확인)

### trim_only = 구간 시작 오프셋 (D-16 재활용 대상)
```ts
// app/src/lib/alignmentWarp.ts — warpTime()
// trim_only — 트림+오프셋만 (D-02 tier 2, 가변속도 끔): warp(t) = t - u0 + r0.
if (a.tier === 'trim_only') return tStudent - us[0] + rs[0];
```

### disabled 방출이 anchors를 버리는 지점 (백엔드 수리 대상)
```python
# backend/shared/python/sunity_shared/analysis/motion_alignment.py — tier 사다리
if distance <= DISTANCE_T1 and slopes_ok:
    tier = "warped"
elif distance <= DISTANCE_T2:
    tier = "trim_only"
else:
    tier = "disabled"          # ← 여기서 anchors가 빈 배열로 방출됨
    reason = "low_global_confidence"
```

### 크롭 배율 분기 (D-20 수리 대상)
```python
# fault_zoom.py::_side_crop — relaxed 경로만 margin 2.0 (1.8×2.0=3.6배)
if valid_pts:
    left, top, s = _box_for(valid_pts, 1.0)      # 내 자세: 1.8배
    ...
if relaxed_pts:
    left, top, s = _box_for(relaxed_pts, _RELAXED_MARGIN)  # 정은지: 3.6배 ← 분리 수정
```

### 사후 분리 패턴 (omni 스팟체크가 재사용할 자리)
```python
# backend/functions/pipeline/app.py — status=done 확정 후 사후 스테이지
with _stage(timings_ms, analysis_id, "firestore_complete"):  # :5236 — 여기서 done
    ...
with _stage(timings_ms, analysis_id, "fault_zoom"):          # :5290 — 사후 부분 업데이트
    ...  # omni 스팟체크 = 이 패턴의 신규 사후 스테이지
```

### 좌표 표시층 확장 지점 (D-22 1단)
```python
# keypoint_frame.py — 8 → 12 확장의 단일 출처
_KEYPOINT_NAMES = ("left_shoulder","right_shoulder","left_hip","right_hip",
                   "left_knee","right_knee","left_hand","right_hand")
JOINT_KEY_TO_ANGLE_KEY = {..., "left_hand": "left_wrist", ...}  # COCO-17 키로 매핑
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| expo-av 오디오 | expo-audio (SDK 52+ 공식 후속) | SDK 52~54 | 신규 채택은 expo-audio만 |
| "외부 초점 항상 우월" 합의 | 출판 편향 보정 후 평균 효과 축소 (McKay 재분석) | 2024-25 | 외부 큐는 이해 가능성으로 정당화, 학습 효과 과장 금지 |
| 교정 이미지/회전 영상 생성 | 생성 AI 전부 OFF — 결정론 산출물만 | 31-CLOSEOUT (2026-07-20) | 32는 생성 없이 ①②③ 달성 |
| severity→cap 밴드 채점 | 투명 감점 tally (deductionBreakdown) | Phase 24 | 문구집 키는 criterion/ruleId 기반으로 설계 |
| 화살표(관절 지목+수치) | 외부 큐 문장으로 대체 | 32 (SEED ⑪) | ARROW_JOINT_MAP 수리 금지 — 대체 |

**Deprecated/outdated:** expo-av(신규 채택 금지) · ViTPose-S(구 문서 잔재 — 실제는 RTMW) · "자동 정렬 꺼짐" 배지(D-16으로 폐지 예정).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | gemini-omni-flash-preview가 텍스트 출력 판정(스팟체크)에 사용 가능하며 비용이 합리적 | 엔진 레버 omni | 낮음 — 폴백 `gemini-3.1-pro-preview`가 검증된 동일 어댑터 경로. 스모크 1콜로 확정 |
| A2 | 기기 TTS(expo-speech) 한국어 음질이 코칭 용도로 수용 가능 | TTS 비교 | 없음 — 샘플 게이트가 판정하도록 설계됨 (D-18) |
| A3 | Polly neural 요금 수준(~$16/1M자) | TTS 비교 | 낮음 — 파일럿 볼륨에서 자릿수 틀려도 무시 가능. 채택 시 요금표 확인 |
| A4 | "코치 출구를 마지막에" 배치의 peak-end 프레임 | 섹션 순서안 #8 | 낮음 — 제품 정의 ③ 자체가 1차 근거. peak-end는 보조 서사 |
| A5 | "1분대" 속도 예산 표기 (메모리 실측 124.7s와 상이) | 엔진 레버 omni | 낮음 — 원칙(동기 경로 신규 호출 금지)은 수치와 무관. planner가 timingsMs로 재확인 |
| A6 | legacy doc 대략 오프셋 소스로 faultZoomComparisons 프레임 인덱스 사용 가능(refMatch='dtw'인 카드 존재 전제) | 수리 #1 | 중간 — refMatched=false/카드 0장 doc은 폴백 불가 → 수동 슬라이더만 제공(그래도 D-16 충족) |
| A7 | keypointReport J 확장 후에도 reference doc(18fps)이 1MB 한도 내 | RTMW 확장 | 중간 — 초과 시 fps 다운샘플 또는 확장 관절 분리 저장 필요. 확장 태스크에 계산 검증 포함할 것 |

## Open Questions (ROUTED — 게이트/태스크로 해소: 1→32-13 T1 스모크, 2→32-08 T3 샘플 게이트+32-12, 3·4→32-04 목업 게이트, 5→32-03 실물 게이트, 6→32-03/32-13~15 Pod 절차)

1. **omni 스팟체크 모델 ID** — gemini-omni-flash-preview(텍스트 판정 미검증) vs gemini-3.1-pro-preview(검증). 권장: 스모크 1콜 태스크로 확정, 실패 시 3.1-pro. (A1)
2. **오디오 방식** — 샘플 게이트(D-18)가 닫음. 리서치는 양 경로 구현 코스트를 위 표로 제공 완료.
3. **참고 지표 존폐/형태** — 목업 게이트(D-03). wave-1은 겹침 최소 수리만.
4. **게임 프레임 적용 범위·타이포 강조 체계** — 목업 게이트(D-05/D-10).
5. **동작 비교 형태·자세 카드 존폐·큐 밀도** — 실물 게이트(D-17, wave-1 수리 후 실기기).
6. **Pod 재생성 시점** — 엔진 레버 웨이브(D-20 검증 PNG·RTMW 확장 스윕·PR)에 필요. 현재 가동 여부 미확인(수동 생명주기) — 해당 웨이브 진입 시 `/health` 확인부터.

## Environment Availability

| Dependency | Required By | Available | Version/근거 | Fallback |
|------------|------------|-----------|--------------|----------|
| AWS CLI + sunity-motion 프로필 | Polly 샘플·SSM | ✓ | 본 세션 Polly describe-voices 성공 | — |
| AWS Polly ko-KR | 클라우드 TTS | ✓ | Seoyeon/Jihye 실계정 조회 | 기기 TTS |
| Node 24 (node --test) | 앱 순수 로직 테스트 | ✓ | pickerFailure.test.ts 실행 실적 | — |
| Xcode 26.6 + iOS 시뮬레이터 | UI 확인 게이트 | ✓ | 메모리 박제 (이 맥에 설치) | — |
| ios-simulator·firebase MCP | 시뮬레이터/Firestore 조작 | ✓(메모리) | 2026-07-21 연결 기록 | CLI 대체 |
| Figma MCP + fileKey jrdI7kp245HkPfLB0nclsz | 목업 게이트·§6-1 | ✓ | 환경에 Figma MCP 등재 | 스크린샷 육안 |
| RunPod Pod (GPU) | 엔진 레버 스윕·crop PNG 검증 | **? 미확인** | 수동 생명주기 — 직전 31에서 xps7co0m2njzpi 사용 | 재생성 절차 = 메모리 [[current-pod-hbpvhedq2bu01i]] + Network Storage |
| Gemini API 키 (belle) | omni/스팟체크 | ✓ | SSM 주입 경로 기존 | 크레딧 확인([[gemini-credits-depleted]]) |
| Cerebras 키 | 문구집 가변부 | ✓ | CEREBRAS_KEY_PARAM 기존 | graceful no-op (문구집 골격만) |

**Missing dependencies with no fallback:** 없음 (Pod는 뒤 웨이브 진입 시 재생성으로 해소).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Backend | pytest >=8,<9 (`backend/requirements-dev.txt`), 테스트 루트 `backend/tests/` (phase별 디렉터리 관례) |
| App (정적) | `npm run typecheck` (tsc --noEmit, strict) — 유일한 앱 정적 게이트 |
| App (로직) | `node --test app/src/lib/*.test.ts` (Node 24 type stripping, node:test/node:assert — 신규 러너 금지) |
| Quick run | `cd backend && python -m pytest tests/phase32 -x -q` (신설 예정) |
| Full suite | 백엔드 전체 baseline 대비 diff (기존 관례: FAILED/ERROR node-ID baseline 비교 — 57 failed/3366 passed baseline 초과 금지, 31-CLOSEOUT 기록) |

### Phase Requirements → Test Map
| 결정 | Behavior | Test Type | Automated Command | File Exists? |
|------|----------|-----------|-------------------|-------------|
| D-16 | 사다리 재배치: low_global_confidence → trim_only + anchors 보존, degenerate만 disabled | unit | `pytest backend/tests/phase32/test_motion_alignment_ladder.py -x` | ❌ Wave 0 |
| D-16 | 수동 오프셋 클램프·warp 합성 순수 계산 | unit (app) | `node --test app/src/lib/__tests__/manualOffset.test.ts` | ❌ Wave 0 |
| D-20 | relaxed 프레이밍 margin=1.0·마커 게이트 유지 | unit | `pytest backend/tests/phase32/test_fault_zoom_crop_parity.py -x` | ❌ Wave 0 |
| D-03 | 겹침 수리 — lineHeight ≥ fontSize 정적 검사 | grep/unit | 스타일 grep 게이트 또는 typecheck + 시뮬레이터/실기기 확인 | ❌ Wave 0 (manual-only 부분: 실기기 — Expo Go가 못 잡는 계열 실증) |
| D-11/D-09 | 문구집 금지어(수치 헤드라인·% 환산·일반론 패턴) grep 게이트 | unit | `pytest backend/tests/phase32/test_phrasebook_forbidden.py -x` (copy_templates 선례) | ❌ Wave 0 |
| D-19/D-27 | 미션 선정 우선순위·streak 체인 순수 함수 | unit | `pytest backend/tests/phase32/test_mission_rules.py -x` | ❌ Wave 0 |
| D-22 RTMW | keypointReport 12관절 방출·validator·하위호환(8관절 doc) | unit | `pytest backend/tests/phase32/test_keypoint_report_expansion.py -x` | ❌ Wave 0 |
| D-23 | 스팟체크 불일치 → 카드 숨김 플래그·로그 (graceful 실패 = no-op) | unit + Pod | 로컬 unit + Pod fixture 6동작 순차 스윕 | ❌ Wave 0 / Pod manual |
| D-22 PR | 인버전 조건부 적용·비인버전 무회귀 | Pod sweep | fixture 6동작 순차 (kip-up 편중 금지) | Pod manual-only (GPU 필수) |
| 계약 3면 | 신규 필드 lockstep | unit | 기존 lockstep 테스트 패턴 확장 | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** 영향 phase 디렉터리 pytest + `npm run typecheck` (+해당 시 node --test)
- **Per wave merge:** 백엔드 전체 baseline diff + typecheck + 시뮬레이터 화면 진입 확인 (UI wave)
- **Phase gate:** fixture 6동작 전수 스윕(엔진 웨이브, Pod 순차) + 시뮬레이터 → belle 실기기(실물 게이트) → OTA(완전 종료 2회) → HUMAN-UAT 적립([[batch-uat-after-phase-31]])

### Wave 0 Gaps
- [ ] `backend/tests/phase32/` 디렉터리 + 위 표 unit 테스트 파일 일체
- [ ] 앱 순수 로직 테스트 파일 (`node --test` 규약 — .ts 확장자 import 명시)
- [ ] 문구집 fixture 스키마 + 금지어 목록 (copy_templates FORBIDDEN_PHRASES 확장)
- 프레임워크 설치: 불필요 (pytest·tsc·node --test 전부 기존)

## Security Domain

### Applicable ASVS Categories (L1)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (변경 없음) | 기존 Firebase ID 토큰 검증 유지 |
| V3 Session | no | 기존 익명 auth 유지 |
| V4 Access Control | **yes** | 오디오 asset 확장 시 playback-url H-02 패턴 필수 — 클라이언트는 asset 종류만 보내고 **key는 서버가 구성 + 저장 key exact 비교** (31 correctedPose/rotation 선례 그대로) |
| V5 Input Validation | **yes** | 신규 Firestore 필드 전부 scoped validator (flat scalar 강제·enum 화이트리스트·finite 검사 — motionAlignment validator 선례). 앱 측 normalize 대칭(null 폴백, 크래시 0) |
| V6 Cryptography | no (신규 없음) | 시크릿은 SSM Parameter Store만 (.env 하드코딩 금지). Polly는 신규 시크릿 0 — Lambda IAM role에 `polly:SynthesizeSpeech` 권한만 SAM 템플릿 추가 |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| presigned URL 임의 key 서명 유도 | Elevation | 서버 key 구성 + exact 비교 (H-02/H-05 — 이미 구현된 패턴 재사용) |
| LLM 프롬프트를 통한 비측정 주장 생성 | Tampering(신뢰) | 문구집 골격 고정 + "주입 실측만" 시스템 프롬프트(기존) + 금지어 grep 게이트 + omni 스팟체크(불일치 카드 숨김) |
| PII — 음성 파일 | Info Disclosure | 코칭 문장에 개인 식별 정보 없음(측정 수치·동작명만). 파일은 `results/{uid}/` uid-scoped + presigned TTL. 홈 디렉터리 임시보관 금지([[home-dir-is-git-repo-pii-hazard]]) |
| Firestore 클라이언트 직접 쓰기 | Tampering | 신규 컬렉션 없음(문서 내 체인) — firestore.rules catch-all default-deny 유지, 미션/플래그는 백엔드 Admin만 기록 |

## Project Constraints (from CLAUDE.md)

- 기술 스택 변경 금지 (§3) — 본 리서치의 신규 후보는 Expo 공식 모듈 1개(D-18 예외 승인 항목)뿐
- Motion AI = 별도 Lambda+S3 (기존 EC2에 얹지 말 것) — 오디오/스팟체크도 기존 sunity-motion 스택 내
- 시크릿 = AWS Parameter Store, .env 하드코딩 금지
- 브랜드 #FF4B33 변경 금지 · Pretendard · 라이트 전용 · 다크 배경 금지 — UI는 Figma 우선(fileKey jrdI7kp245HkPfLB0nclsz), design.md 보조
- 테마 토큰 강제 (색·간격 하드코딩 금지) + 접근성 props 관례
- 작은 단위 작업 · 의미있는 테스트만 · 이모지 금지 · 작업 완료 시 plan.md 업데이트
- 한국어 사용자 카피 + 스펙 인용 주석 관례 (`design.md §5-4`, `contract.md §2` 식)
- GSD 워크플로 준수 · rtk 접두 (단 gsd-sdk/gsd-tools는 rtk 금지)

## Sources

### Primary (HIGH confidence — 실파일/실계정/공식)
- 코드 전수 확인: `result.tsx`(2745줄 — 섹션 순서·diagSentence·compareFrames), `alignmentWarp.ts`, `VideoCompare.tsx`, `motion_alignment.py`, `fault_zoom.py`(_side_crop/ARROW_JOINT_MAP), `skeleton.py`, `keypoint_frame.py`, `assemble.py`(build_keypoint_report), `coach_writer.py`, `copy_templates.py`, `exercise_map.py`, `firestore_admin.py`(validator/get_previous_analysis), `pipeline/app.py`(_stage/사후 분리), `playback-url/app.py`(asset 패턴), `typography.ts`, `analysis.ts`
- `app/node_modules/expo/bundledNativeModules.json` — SDK 54 공식 버전 매니페스트 (expo-speech ~14.0.8 / expo-audio ~1.1.1)
- AWS Polly `describe-voices` 실계정 호출 (ap-northeast-2, ko-KR: Seoyeon/Jihye)
- `.planning/spikes/004-gemini-omni-view-editing/README.md` — omni/PR/Wan2.7/GEN3C 실측 전체
- 31-CONTEXT/31-CLOSEOUT/32-SEED/32-CONTEXT — 결정·invariant 원문

### Secondary (MEDIUM-HIGH — 학술 원문 확인)
- [An, Wulf & Kim 2013 — X-Factor 골프 (JMLD)](https://journals.humankinetics.com/view/journals/jmld/1/1/article-p2.xml) · [원문 PDF](https://gwulf.faculty.unlv.edu/wp-content/uploads/2014/05/An-Wulf-Kim-2013.pdf)
- [Chiviacowsky & Wulf 2007 — Feedback After Good Trials (PubMed)](https://pubmed.ncbi.nlm.nih.gov/17479573/) · [원문 PDF](https://gwulf.faculty.unlv.edu/wp-content/uploads/2014/05/Chiviacowsky_Wulf_good_FB_2007.pdf)
- [Palmer, Chiviacowsky & Wulf 2016 — Enhanced expectancies golf putting](https://www.sciencedirect.com/science/article/abs/pii/S1469029215300066) · [2021 재현 실패](https://www.sciencedirect.com/science/article/abs/pii/S1469029221000054)
- [Chua et al. 2021 — 외부 초점 메타분석 (PubMed)](https://pubmed.ncbi.nlm.nih.gov/34843301/) · [McKay 재분석 — Reporting bias, not external focus (PubMed)](https://pubmed.ncbi.nlm.nih.gov/39480294/)
- [OPTIMAL 동기 기둥 근거 부족 (PSE 2024)](https://www.sciencedirect.com/science/article/pii/S1469029224001018) · [Wulf & Lewthwaite 2016 OPTIMAL 원문](https://link.springer.com/article/10.3758/s13423-015-0999-9)
- [Shneiderman 1996 — The Eyes Have It (원문 PDF)](https://www.mat.ucsb.edu/~g.legrady/academic/courses/11w259/schneiderman.pdf)

### Tertiary (LOW — 검증 대기/보조)
- Polly neural 요금 수준 (A3 — 채택 시 요금표 확인)
- expo-speech iOS 한국어 음질 체감 (A2 — 샘플 게이트가 판정)

## Metadata

**Confidence breakdown:**
- 수리 3건 진단: HIGH — 세 건 모두 코드 라인 단위 원인 특정 (겹침=스타일 실측, 초맞춤=사다리 방출 실측, 크롭=합의 문서+코드 정합)
- 엔진 레버 통합 지점: HIGH(코드) / MEDIUM(omni 모델 실체 — A1)
- D-02 문헌: HIGH(개별 연구 실존·내용 확인) / MEDIUM(효과 크기 — 재현 논쟁을 등급 그대로 노출)
- 스택·버전: HIGH — 로컬 공식 매니페스트 + npm + 실계정 교차

**Research date:** 2026-07-21
**Valid until:** 2026-08-20 (안정 영역) / omni 모델·Gemini API 표면은 7일 단위 재확인 권장 (belle: "한 달이면 AI가 크게 변한다")

# IPSF 객관 기하 요건 소싱 (P1 step 3) — 2026-06-27

소스: NotebookLM "IPSF Rules and Advanced Strength Pole Moves Guide" (id 96b061e8-bb7c-41c5-8606-8ceef2ce1aa3, 70 sources incl. 공식 IPSF Pole Sports Code of Points 2025-2027 + appendices).

## 결정적 발견 (P1 경로를 바꿈)

### A. IPSF의 사지 신전(extension) 채점 = 범주형(categorical), per-degree 임계 없음
- IPSF는 사지 신전을 3-범주로만 판정: **"Fully extended" / "Micro bent (Extended)" / "Bent"**.
  (출처: IPSF Pole Sports Code of Points Glossary, Page 130-131)
- 어떤 element가 "Fully Extended"를 요구하는데 micro-bend라도 있으면 → **그 element 0점(award 안 함)**. 비례 감점 아님.
- **사지 신전에는 numeric degree tolerance가 없음** — split만 명시적 **20° tolerance**를 가짐(출처: split angle 정의, "legs must be in a straight line where 180 is required", IPSF Aerial Pole CoP 2024-2025 Page 18; 20° tolerance 정의).
- 발끝(pointed feet)/자세 = **-0.2 flat singular deduction** per occurrence.
- 어느 라인이 곧아야 하는지는 **element별 "Criteria" 칼럼에 하드코딩**됨(예: F31 Front Split "both legs fully extended"; F33 "inside arm fully extended"). 보편 원칙이 아니라 element별 정의.

### B. 6개 동작은 IPSF Code of Points element가 아님 (전부 학원/커뮤니티 명칭)
NotebookLM 명시적 답변 — 다음 전부 **"NOT a recognized IPSF Code of Points element"**:
- power-spin — 학원 명칭. IPSF 미등재. "Transitions & Climbs"로만 평가.
- pd-shape / pd-split — 커뮤니티 용어/해시태그. IPSF 미등재.
- kip-up — 학원 명칭(마운팅 transition). IPSF 미등재. per-move geometry 미지정.
- elbow-twist (sister) — 학원 명칭. IPSF 미등재. (유사 IPSF element는 Elbow Spin SP16/SP60, Elbow Grip Split Spin SP58 — 그러나 "Elbow Twist" 매핑 없음)
- peter-pan — 학원 명칭(side-plank hook 변형). IPSF 미등재.
- (climb은 "Transitions & Climbs" 카테고리 — angle criterion 없음, 기존 ref-climb.yaml과 정합)

→ **IPSF Code of Points에서 "이 동작의 이 관절이 곧아야 한다"는 per-move element 요건을 소싱하는 것은 불가능.** 이 동작들이 IPSF element가 아니기 때문. per-move 요건을 IPSF에서 날조하면 그게 곧 curve-fit/임의정의(금지).

## 함의: 객관 채점은 여전히 가능 (단 경로가 다름)

IPSF가 주는 **객관·보편 기준은 실재**한다:
- "곧게 제시된(presented-straight) 사지는 완전 신전(180°)이어야 한다" = IPSF Glossary 보편 기준.
- split 180°, 20° tolerance.
- 발끝/자세 -0.2.

빠진 것은 IPSF element 정의가 아니라 **"이 동작에서 어느 관절을 곧게 펴려고 의도하는가"** (= 동작의 의도된 형태). 이건:
- IPSF element lookup으로는 안 나옴(미등재).
- **belle 도메인 지식**(각 동작의 의도된 폼) 또는 **Gemini 비전(영상별 판정)**으로만 정의 가능.
- 정은지 측정값 흉내가 아니고(180° 객관 기준 사용), 13영상에 맞춘 임계 튜닝도 아님(curve-fit 아님).

즉 채점 공식: **선택된 관절을 180° IPSF 보편 기준 + 표준 20° tolerance로 deduction** (정은지-따라하기 reference-relative 제거). "선택된 관절"만 belle/비전이 지정.

## belle 확인 필요 (step 4 진입 전 게이트 — curve-fit 방지)

제안 per-move EXTEND 매핑 (각 동작의 의도된 곧은-라인 = 180° 객관 채점 대상). belle가 확인/수정:

| 동작 | 제안 EXTEND 관절(곧아야 함, 180°) | 근거(동작의 의도된 폼) |
|---|---|---|
| kip-up | left_knee, right_knee | 공중 양 다리 신전 (belle pair: 굽은 무릎 = fault) |
| power-spin | left_knee, right_knee | 다리 신전 + split (belle pair: 무릎 굽음 = fault) |
| pd-shape | 자유 다리 무릎(예: left_knee 또는 right_knee) | belle pair: 자유 다리 무릎 굽음 = fault |
| elbow-twist-sister | left_knee, right_knee (+ split 라인) | belle pair: 스플릿 부족/라인 붕괴 = fault |
| peter-pan | (미정 — side hold, 어느 다리/팔이 곧아야?) | belle 도메인 필요 |
| climb | 없음(angle criterion 없음) | IPSF "Transitions & Climbs", 기존 ref-climb.yaml 정합 |

주: source_ref는 "IPSF Pole Sports CoP Glossary 'Fully extended leg' 범주형 신전 기준 (Page 130-131) + 동작 의도된 폼(belle 도메인, IPSF element 미등재)"로 정직하게 인용 — 존재하지 않는 element code를 날조하지 않음.

## belle 결정 (2026-06-27)
1. **채점 "왜"가 약해지면 안 됨 → 범주형(micro-bend=0점) 제외.** 비례/하이브리드만(현 deduction_engine 비례형 유지).
2. 기준은 **UI/보고서에 사용자에게 노출**(설득 텍스트 필수).
3. IPSF 없는 곳: 잡을 수 있으면 심사 기준 잡고, **Mode 1 = 프로(정은지) 모션 기준.**
4. 아이디어(후속 feature, P1 아님): **대회 실측 기준 vs 프로 모션 기준 사용자 선택권.**

## P1 통합 해법 (step 4 방향)
오염의 진짜 문제 = "정은지 사용"이 아니라 "왜가 약함"(체형차 오판 + kip-up 누락). belle의 "왜 강해야"가 곧 해법:
- **곧아야 할 관절(주로 무릎)을 객관 180°(ipsf_absolute deviationSource)로 채점** → "왜" 강함(다리 X° 굽음) + 정타 오염 제거(둘 다 곧으면 둘 다 통과, 정은지와 14~18° 차이 무관) + kip-up 검출(18° 굽음→감점).
- 그 관절에서 reference_relative(정은지 흉내) 감점은 빠짐(24-07 cross-exclusion 활용 — double-count 금지).
- source_ref = "IPSF CoP Glossary 'Fully extended leg' 범주형 신전 기준 + 동작 의도된 폼(belle 도메인)" — 존재 안 하는 element code 날조 금지.

## per-move EXTEND 매핑 (fault 데이터 = 의도된 곧은-라인)
| 동작(motion_id) | EXTEND 관절 | 비고 |
|---|---|---|
| ref-kip-up | left_knee, right_knee | 대칭(양 다리 공중 신전). 최고가치(현 100/100 위양성) |
| ref-power-spin | left_knee, right_knee | 대칭 |
| ref-peter-pan | left_knee, right_knee | fault=무릎 굽음(신전 부족) |
| ref-elbow-twist-sister | left_knee, right_knee | fault=스플릿 부족/라인 붕괴(양 다리 split) |
| ref-pdshape | 자유 다리 무릎 | **비대칭** — 한 다리만 곧음. 양 무릎 EXTEND 시 anchor 다리 위양성 위험 → step5 pod sweep + clean-residual 게이트가 검증(정타에 잔차 뜨면 재조정) |
| ref-climb | 없음 | spine/back = 8 JOINT_KEYS 밖, IPSF Transitions(angle criterion 無). 기존 ref-climb.yaml 정합 |

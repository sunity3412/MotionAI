# `judging_data/` — IPSF GeometricCriterion 데이터 (JUDGE-DATA-01)

Plan 박제: `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-15-PLAN.md`
요구사항 인용: `REQUIREMENTS.md` JUDGE-DATA-01 (line 74).
모듈: `backend/shared/python/sunity_shared/judging/` (스키마 + 로더).

---

## 1. 단일 기준 = IPSF Code of Points

- 본 디렉터리의 모든 임계값은 **IPSF Code of Points (국제폴스포츠연맹)** 한 가지에서만 가져옵니다.
- 한국폴스포츠협회(KPSA) 도 IPSF 규정을 따르므로 별도 기준이 아닙니다 (`docs/research/폴스포츠-지식.md:26` 참조).
- POSA / 미국연맹 / 학원 자체 기준 등 **다른 채점 기준 도입 금지**.
  - memory 박제: `judging-baseline-ipsf-code-of-points`.

## 2. 사람 점수 라벨링 영구 금지

- belle / 강사 / 심사자 누구도 "이 영상 몇 점" 형태의 ground truth 를 작성하지 않습니다.
  - 형식 불문 (순위 / 3단계 / 100점 / 4단계 등 전부 금지).
- belle 가 본 디렉터리에서 채우는 값은 **객관 임계값 수치** 입니다:
  - `angle_target` — IPSF 규정에 명시된 phase별 target angle (degree).
  - `tolerance_full` — IPSF Full Mark tolerance (degree, ±). 기본 20° (아래 참조).
  - `deduction_per_step` — tolerance 초과 1° 당 감점값. IPSF 기본 0.2점.
  - `minimum_requirement` — IPSF minimum 충족 각도. 이 값 미만이면 동작 실패.
  - `source_ref` — IPSF Code of Points 정확한 섹션 인용 (예: `"IPSF Code of Points 2024 §4.2.1"`).
- memory 박제: `analysis-objectivity-no-human-scores`.

## 3. IPSF 기본 객관 수치 (이미 박제됨)

| 항목 | IPSF 수치 | 출처 |
| --- | --- | --- |
| 각도 tolerance (Full Mark) | ±20° (규정 각도 기준) | `docs/research/폴스포츠-지식.md:311` |
| tolerance 초과 1° 당 감점 | -0.2점 | `docs/research/폴스포츠-지식.md:311` |
| 4대 심사 섹션 | 기술 보너스 / 기술 감점 / 예술 및 안무 / 필수 요소 | `docs/research/폴스포츠-지식.md:70` |
| 발 형태 | Pointed feet (Flexed 금물) | `docs/research/폴스포츠-지식.md:533` |

본 디렉터리는 IPSF 4대 섹션 중 **기술 점검 (knee/elbow angle 등 기하)** 만 다룹니다.
"예술 및 안무 / 필수 요소" 평가는 영구 제외 (REQUIREMENTS JUDGE-01 — "예술 점수 제외, 기술 점검").

## 4. YAML 스키마

```yaml
motion: ref-invert
source: "IPSF Code of Points 2024 — invert family"
criteria:
  setup_moment: []           # phase 없으면 빈 list
  hold_moment:               # IPSF target / tolerance / deduction / minimum
    - joint: left_knee
      angle_target: 180.0    # 완전 펴짐 (invert hold)
      tolerance_full: 20.0   # IPSF 표준 ±20° (-0.2점 감점)
      deduction_per_step: 0.2
      minimum_requirement: 130.0
      source_ref: "IPSF Code of Points 2024 §4.2.1 invert family knee extension"
    - joint: right_knee
      angle_target: 180.0
      tolerance_full: 20.0
      deduction_per_step: 0.2
      minimum_requirement: 130.0
      source_ref: "IPSF Code of Points 2024 §4.2.1 invert family knee extension"
  peak_moment: []
  release_moment: []
```

규칙:
- 4 phase 키 = `setup_moment` / `hold_moment` / `peak_moment` / `release_moment`. 빈 list 허용.
- `joint` 는 `backend/shared/python/sunity_shared/analysis/skeleton.py` 의 `JOINT_KEYS` 와
  일치해야 합니다 (예: `left_knee`, `right_elbow`).
- 모든 entry 의 `source_ref` 는 IPSF 섹션을 인용해야 하며, 빈 문자열이면
  로더 `validate()` 가 "객관 인용 의무화" ValueError 로 차단합니다.
- 변환은 모두 float (각도/감점). 단위 = degree, 감점 = 점수.

## 5. belle 라벨링 절차

1. 본 README + `docs/research/폴스포츠-지식.md` IPSF 4대 섹션 + tolerance 20° 단락 숙독.
2. 5개 YAML 파일 (`criteria/ref-climb.yaml`, `ref-foxtop-split.yaml`, `ref-foxtop.yaml`,
   `ref-invert.yaml`, `ref-sideway-spin.yaml`) 각각에 대해 IPSF 규정 lookup.
3. 핵심은 `hold_moment` 입니다 (Plan 01-13/14 게이트가 가장 먼저 사용). 다른 phase 는
   필요시 채워주세요.
4. 각 entry 의 `source_ref` 에 IPSF Code of Points 정확한 섹션을 인용하세요.
   인용 형식 예: `"IPSF Code of Points 2024 §4.2.1 invert family knee extension"`.
5. tolerance 가 IPSF 규정에서 동작군별로 다르게 명시되어 있으면 그 값을 따르세요.
   별도 명시가 없으면 기본 20°.
6. **점수를 매기지 마세요.** 점수는 측정 각도 ↔ `angle_target` 갭으로 자동 계산됩니다 (Plan 01-13).

## 6. 강사 협업 (선택)

- belle 가 IPSF 규정 lookup 에 자신 없는 entry 만 강사 검토 의뢰 가능 (belle 단독 OK).
- 강사도 점수 라벨링 X — IPSF 규정 인용만.

## 7. 검증

belle 라벨링 완료 후:

```bash
python3 -m pytest backend/tests/test_geometric_criterion_loader.py -v
```

5영상 다 `validate()` PASS = 데이터 정합. 실패 시 메시지에 어느 motion / moment / joint
가 문제인지 명시됩니다.

스키마 자체 가드 (사람 점수 우회 방지) 는 별도:

```bash
python3 -m pytest backend/tests/test_geometric_criterion_schema.py -v
```

## 8. 다른 동작 추가

- 본 디렉터리는 sweep 5영상 (`ref-climb / ref-foxtop-split / ref-foxtop / ref-invert /
  ref-sideway-spin`) 만 포함합니다 (Plan 08/10/11 일관성 유지).
- 다른 동작 임계값 추가는 별 plan 으로 진행. 본 5영상 외 파일을 임의로 추가하지 마세요.

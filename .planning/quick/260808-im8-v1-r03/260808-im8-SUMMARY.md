---
task: 260808-im8
type: execute
date: 2026-08-08
commits:
  - 2e8ab938 (feat: p35_observe_screen.py — 자율 스크린 v1, v0 회귀 게이트 내장)
  - 2f077393 (docs: RESULT.md + report.json — r03 verdict FAIL 정직 박제)
key-files:
  created:
    - backend/scripts/p35_observe_screen.py (740줄 — 전구간+홀드 스크린, POLE_X_CACHE, --regress-v0, --verdict-r03)
    - .planning/quick/260808-im8-v1-r03/260808-im8-RESULT.md (9절 — 표 5동작 + verdict + 회귀 대조 + LLM 학습 기여)
    - .planning/quick/260808-im8-v1-r03/260808-im8-report.json (기계 산출 원본 — regress_v0 + verdict 블록 포함)
  modified: []
---

# 260808-im8: 자율 스크린 v1 — v0 리포 영구화 + 홀드 구간 인식 + r03 블라인드 재발견 verdict

## 한 줄

v0 자율 스크린(08-08 세션 인라인)을 리포 스크립트로 영구화하고 v0 실측 6게이트 회귀 PASS
로 박제했다. v1 신규 홀드 스크린의 r03 블라인드 재발견 verdict 는 **FAIL** — 기본 파라미터
에서 user·ref 동시 홀드 짝이 5동작 전부 0 이라 판정 자체가 서지 못했다 (실패 그대로 기록,
튜닝 0). 단 전구간 스크린에는 r03 방향 신호(elbow gap_hip_mid 2위·bodyline 3위, user>ref)
가 존재 — 실패는 신호 부재가 아니라 홀드 격리 메커니즘.

## 게이트별 실측 수치

| 게이트 | 판정 | 실측 |
|--------|------|------|
| Task 1 STOP (`--regress-v0`) | **PASS (exit 0)** | powerspin left_ankle **+0.5555** [0.51,0.61] / 벌림각 **−24.55°** [−27.5,−21.5] / u_med **27.74°** (27.7±3) / r_med **98.05°** (98.1±3) / elbow 전 피처 최대 scaled **0.393** (<=0.5) / 미러 **5/5 동측** |
| v0 정성 참고 (hard gate 없음) | 방향 일치 | kipup 음수 diff 12/14, peterpan 10/14 ("진폭 부족" 방향) |
| r03 verdict G1 (재발견) | **FAIL** | elbow 홀드 판정 불가 — 동시 홀드 짝 0 < HOLD_PAIR_MIN 10 (user 홀드 run 최장 12프레임 < 15) |
| r03 verdict G2 (과검출 없음) | **FAIL** | pdshapefault 홀드 판정 불가 — 측정 불가 = FAIL (fail-closed). 참고: 전구간 bodyline scaled 0.153 / gap_hip_mid 0.083 은 침묵 방향(<1.0) |
| r03 verdict G3 (유지) | **PASS** | powerspin 전구간 top3 에 gap_left_ankle 1위(+0.5555, scaled 3.703) + gap_right_ankle 2위(+0.2928) |
| r03 verdict overall | **FAIL** | G1∧G2∧G3 불성립 — 기본 파라미터 1회 판정, 재실행·파라미터 변경 0 |
| Task 2 검증 (JSON 키·9절 grep·무접촉) | ALL-CHECKS-PASS | verdict 4키 존재, RESULT 9절 전건, `git diff HEAD -- backend/shared render_compare_prototype.py` 빈 출력(staged 포함), 이모지 0 |
| 렌더러 lazy import 게이트 | PASS | cv2 0건, PIL·render_compare_prototype top-level import 0건 (폴 재계산 함수 내부 lazy 만) |

## 계획 대비 편차

1. **[plan 명문 교차 1회] 좌표 관례 px → 정규화 공간 채택** — px 관례로 v0 실측 4건 전부
   재현 실패(벌림각 −30.50/u 46.37/r 84.94, ankle +0.341) → plan 이 허용한 정규화 관례
   교차에서 4건 전부 재현(−24.55/27.74/98.05/+0.5555) → 채택 + 스크립트 ANGLE_SPACE 주석에
   근거 박제. 부수 확정 2건: 간격 분모 torso 도 정규화 공간 길이(plan 의 px 공식 서술은
   planner 재구성 — v0 실측이 정본), 패널 중앙값 = 각 시계열 독립 nanmedian(r_med 98.05
   재현의 필요조건). 실측 대조는 스크립트 주석 + RESULT §6 에 병기.
2. **[fail-closed 해석] G2 측정 불가 = FAIL** — plan 은 홀드 스크린 불가 시 G2 처분을
   명시하지 않음. 프로젝트 fail-closed 원칙대로 "측정 불가 = FAIL" 로 구현(스크립트 주석
   명문). 완화 해석(무검출=무과검출 PASS)을 취해도 G1 FAIL 이라 overall 은 동일.
3. **[박제 강화] report JSON 에 regress_v0 블록 포함** — plan 의 --json-out 명세(전구간+
   홀드+미러+verdict)에 더해 회귀 체크 8행도 같은 파일에 박제(RESULT §6 인용 출처 단일화).
   verdict 는 동일 기본 파라미터 결정론 산출이라 재실행에 해당 없음(수치 전건 동일 확인).

## 미검증 항목

| 항목 | 사유 |
|------|------|
| 폴 재계산 폴백 경로(--pole-frames-dir → _detect_pole lazy import) 실발동 | 기본 경로가 POLE_X_CACHE 라 이번 실행에서 미발동 — 코드 경로만 존재(스틸 프레임 디렉터리가 scratchpad 세션 의존) |
| POLE_X_CACHE 미등재 동작의 fail-closed(폴 피처 제외) 실발동 | 기본 5동작 전부 캐시 등재 — 사유 로그 경로 미발동 |
| 홀드 스크린의 정상 집계 경로 (available=true) | 기본 p40 에서 5동작 전부 짝 0 — 집계 코드는 p50 관찰 실행(pdshapefault 짝 17, RESULT §9)으로만 통과 확인 |
| 타 촬영 환경(이동 카메라·비수직 폴) 일반화 | 파일럿 고정 카메라 가정 — 데이터 없음 |
| v0 좌표 관례 판별의 타 동작 교차 검증 | v0 수치가 powerspin 에만 남아 있어 1동작 실측 기반 (elbow "전 피처 약함"·미러 5/5 는 정합) |

## LLM 학습 기여

- **(a) 사람검증 완료**: elbow 몸-폴(belle 승인 r03) — 재발견 FAIL 이라 "자율 스크린이
  사람 라벨을 재현" 근거는 이번 판정으로 **성립하지 않음**. 라벨로 쓸 수 있는 것은 여전히
  belle 승인본뿐. 전구간 방향 신호(+0.0546/+0.0472)는 약신호 참고.
- **(b) 기계단독(미검증, belle 검증 선행 필요)**: powerspin left/right_ankle 폴간격
  (+0.5555/+0.2928 — 결함 부위 라벨), powerspin 벌림각 −24.55°(u 27.7 vs r 98.0 — 각도
  회귀 타깃), kipup·peterpan 진폭 부족(12/14·10/14 음수 — 클립 레벨 라벨), peterpan
  knee_angle_right +10.52°(무릎 편차 — 단 정규화 공간이라 해부학 각도 비호환), 미러 5/5
  동측(플립 augmentation 게이트). 홀드 구간 경계는 짝 0 이라 **라벨 후보 부적격**.
- 상세 표 = RESULT §8.

## v1 한계 + 다음 가설

**v1 한계**: 홀드 인식이 상대 임계(p40)의 run 조각내기(elbow user 최장 12프레임 < 15) +
DTW 짝-홀드 경계 불일치(pdshapefault 는 양 패널 홀드 성립에도 교집합 0)의 이중 원인으로
동시 홀드 짝을 만들지 못함 — **다음 가설(구현 아님, 결정 대기)**: 히스테리시스 이중
임계(진입/이탈 분리)로 조각내기 완화 + "양쪽 모두 홀드" 를 "한쪽 홀드 + 상대 저에너지"
완화짝으로 교체(p50 관찰에서 pdshapefault 짝 17 성립이 방향 방증).

## Self-Check: PASSED

- 커밋 존재 2/2: 2e8ab938(스크립트 1파일 740줄, 삭제 0) / 2f077393(RESULT+report 2파일, 삭제 0)
- 산출 파일 존재 3/3: p35_observe_screen.py / 260808-im8-RESULT.md / 260808-im8-report.json
- 산출물 직접 열어 확인: report JSON verdict {G1 F/G2 F/G3 T/overall F} + regress pass=true 값 확인, RESULT 표 수치 = 캐논 실행 stdout 전사 대조
- 채점·렌더러 무접촉: `git diff HEAD -- backend/shared backend/scripts/render_compare_prototype.py` 빈 출력 (staged 포함)
- `--regress-v0` exit 0 재확인, 이모지 0, cv2/top-level heavy import 0

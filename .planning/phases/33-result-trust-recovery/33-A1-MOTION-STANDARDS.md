---
phase: 33-result-trust-recovery
plan: 08
title: A-1 동작별 기준 자세 조사 표 (동작 x 4질의)
status: task1-fixtures
authored: 2026-07-28
requirements: [D-09, D-18, D-19, D-23, D-28]
consumers: [33-09 (A-2 코칭 문구), 33-10 (A-3 크롭 설계), 33-14 (A-7 일러스트)]
canonical_coverage: ".planning/phases/33-result-trust-recovery/33-COVERAGE-MATRIX.md (단일 canonical — 본 문서는 그 소비자)"
substrate: "candidate phase33-cm3-run1 (33-17 shadow resolver 경로, reference/{id}/versions/phase33-cm3-run1) — flip(33-07)은 belle 결정(2026-07-28)으로 A-트랙 뒤 이연"
sources:
  - "reference/{id}/versions/phase33-cm3-run1 (Firestore, reprocessedAt 2026-07-23) — joints3d/(x,y,0), angles, meanAngles, techniqueProfile 직접 열람"
  - "backend/evals/phase25/baseline/phase25_sweep_report.json — 동작별 activatedCriteria (fault 멤버)"
  - "backend/judging_data/criteria/ref-*.yaml — IPSF/정은지 측정 박제 (P1 2026-06-27 / Plan 5-00)"
  - "docs/reference-motions.md §5 (정은지 선수 v6 확정) + app/scripts/seed-reference-motions.mjs MOTIONS (신규 6동작 CROSS-CHECK)"
  - "NotebookLM 폴스포츠 노트북 96b061e8 query 2건 (2026-07-28): 스트래들/수직 스플릿 계열 + 인버트/레그행/엘보그립/스핀/클라임 계열 — IPSF CoP 인용 포함"
  - "docs/research/폴스포츠-지식.md 보고서 4-6 (IPSF 실행 감점 5요소, 자세/그립 용어, 모멘텀 정의)"
  - "docs/research/폴스포츠 수강생의 설문조사.md (강사 철학: 각도 수치는 보조, 원인-해결이 핵심)"
---

# 33-A1-MOTION-STANDARDS — 동작 x 4질의 공통 재료 표

> **좌표 읽기 규약:** 아래 "실측"은 candidate 문서의 joints3d `(x, y, 0)` (픽셀계, y 아래+)
> 기준이다. 다리 방향각 = hip→ankle 벡터가 아래(+y)에서 벗어난 각: 0°=아래, 90°=옆(수평),
> 180°=위. 프레임 번호 f = 9fps 기준 (t = f/9 초).
>
> **어휘 규약 (D-09):** 새 표기법 발명 0. ③열 어휘는 기존 프로젝트 문서가 이미 쓰는 말
> (reference-motions.md 체크포인트 노트 — 정은지 v6 확정, seed 스크립트 노트, IPSF 한국어
> 보고서의 감점 언어: 신전/포인/라인/견갑/훅/스트래들/아치)만 재사용한다. 특정 동작에 대한
> 강사 인터뷰 원문은 미보유 — ③열은 위 문서 어휘의 재조합이며 그 한계를 여기 명시한다 (D-18).

## 4질의 정의 (33-PLANNING-APPROACH §1)

| 질의 | 어디에 쓰이나 |
|---|---|
| ① 완성 기준 — 무엇이 되면 잘한 것인가 | 코칭 문구 · 크롭 대상 선정 (A-2/A-3) |
| ② 흔한 실패 | 코칭 문구 · 일러스트 소재 (A-2/A-7) |
| ③ 강사가 교정할 때 쓰는 말 | 코칭 문구 어휘 (A-2) |
| ④ 강사가 어디를(부위) 어느 순간에 보라 하는가 | 확대비교 크롭이 잘라야 할 것 (A-3) |

## 표 1 — fixture 보유 6동작 (phase25 success+fault 쌍 보유)

| 동작 | ① 완성 기준 | ② 흔한 실패 | ③ 강사 교정 어휘 | ④ 어디를 · 어느 순간 | criteria scope (sweep fault 실측) | ref frame 검증 |
|---|---|---|---|---|---|---|
| **ref-power-spin** (파워스핀) | 스플릿 그립 공중 매달림 → 후반 hold(약 7.1~10.2s)에서 **다리를 폴 축을 따라 위·아래 일자 스플릿(수직 스플릿)**, 양 무릎 완전 신전(실측 165~176°), 발끝 포인, 강한 원심력을 버티는 양 견갑 안정. **방향 정정(belle "천장" 모순의 사실층 해결): "천장으로 뻗으세요" 단일 큐는 오답 — 위로 가는 다리는 하나뿐이고 반대 다리는 아래로 뻗어야 일자 라인이 완성된다. "옆으로(스트래들) 벌림"도 실측과 모순 — 옆이 아니라 폴 축 상하 스플릿이다.** 좌우 라벨은 UNVERIFIED(아래 검증 노트) | 다리 미신전(무릎 굽음 — fault fixture 가 leg_extension −20 으로 실포착), 스플릿 라인 짧아짐, 아래 그립 견갑 무너져 라인 기울어짐, 발끝 포인 부족(IPSF −0.1 누적), 회전 모멘텀 부족으로 몸이 폴에 붙음(IPSF −2.0) | "무릎 펴", "발끝 포인", "위 다리는 폴 따라 수직으로", "아래 다리 길게 눌러", "어깨 으쓱하지 마(견갑 안정)", "라인 길게" | hold 구간(7.1~10.2s, f71~f92)의 **양 무릎 + 위·아래 다리 라인 + 양 견갑**. 진입 펌핑 구간(0.5~6.6s)은 크롭 대상 아님 | `angle_vs_reference__{left_hip, left_shoulder, right_hip}` + `leg_extension` (fault 57점) | **ref frame confirms** — candidate f71~f92 수치 + 원본 영상 8s/9s 프레임 육안 |
| **ref-peter-pan** (피터팬) | 상하 스플릿 그립 매달림 + **hook 무릎(실측: 오른무릎 40~107° 굽힘)이 폴을 감고, 반대(왼)다리는 무릎 완전 신전(176~178°)으로 길게 뻗는 스태그 셰이프**, 약 4회전 hold-in-rotation. 인버전 없음(실측 inv 3%). techniqueProfile(left_knee=extend, left_elbow=extend)이 실측과 일치 | 자유(신전) 다리 무릎 굽음(라인 짧아짐), hook 무릎이 너무 펴져 hook 풀림, 두 손 그립 간격 무너짐(셰이프 불안정), 위 그립 어깨 떨어져 셰이프 라인 무너짐 | "무릎 걸어(훅)", "뒷다리 길게 펴", "발끝 포인", "그립 간격 유지해", "어깨 눌러" | hold 회전 중(peak 4s 전후, f18~f54): **신전 다리 무릎 + hook 무릎 굽힘각 + 위 그립 어깨** | `angle_vs_reference__{left_shoulder, right_elbow, right_knee}` (fault 83점) | **ref frame confirms** — candidate f18~f54 (36프레임 일관). **좌우 정정:** seed 문서는 왼쪽=hook 으로 기재했으나 candidate 실측·techniqueProfile 모두 오른무릎=hook / 왼다리=신전 |
| **ref-elbow-twist-sister** (엘보 트위스트 시스터) | **도립**(메인 hold 9.5~17.5s, 실측 window inv 86%) + 엘보 백 그립 + 무릎 hook + **윗다리 폴 축 수직 익스텐션** — 실측 f117(13s): 오른다리 위(165.6°)·왼다리 아래(12.5°), 가위각 178°. 백벤드 + 트위스트 유지 약 8초 hold | 윗다리 무릎 굽음(수직 라인 손상 — 채점 핵심), hook 풀림(도립 무너짐), 엘보 그립 고쳐잡기(IPSF re-grip −0.5), 흉추 안 열려 트위스트 얕아짐, hold 지속 실패 | "팔꿈치로 감아(엘보 그립)", "윗다리 수직으로 뽑아", "무릎 걸어", "가슴 열어(흉추까지)", "버텨" | 메인 hold(9.5~17.5s, peak 13s, f99~f117): **윗다리 무릎·수직 라인 + 엘보 그립 팔 + hook 무릎** | `angle_vs_reference__` 7관절 (left/right elbow·knee·shoulder + left_hip — 전신 붕괴형, fault 61점) | **ref frame confirms** — candidate f99~f117 (도립 + 상하 가위 스플릿 실측) |
| **ref-pdshape** (pdshape) | **비대칭 인버티드 클로즈드 셰이프**(실측 inv 74%): 한 다리 hip-knee hook + 반대 다리 folded(접음), 양손 폴, 메인 hold 3.5~11.5s 약 8초, 12회전+ 등속. 실측 f54(6s): 도립 + 양 무릎 굽힘(141.6°/101.8°) + 다리 위쪽. **무릎 신전은 이 동작의 결함 축이 아님** — 정타가 무릎을 깊게 굽힘(yaml step5 pod 실측, EXTEND 제거 이력) | hook 깊이 풀림(hold 무너짐), folded 다리 각 흐트러짐(너무 펴거나 너무 굽음 — 셰이프 손상), 비대칭 균형 상실(한쪽으로 기움), 어깨 부하 쏠림 | "다리 깊게 걸어", "접은 다리 모양 그대로", "골반 잠가", "어깨로 버텨" | 메인 hold(3.5~11.5s, peak 8s, f54 부근): **hook 측 무릎·고관절 + folded 다리 무릎 각 + 척추 비대칭 정렬** | `angle_vs_reference__` 8관절 전부 (fault 54점) | **ref frame confirms** — candidate f54±(8s 부근 일부 결측 프레임은 제외하고 판독) |
| **ref-kip-up** (킵업) | **인버전 없이**(실측 inv 3%) 머리 위·발 아래 유지, 다리 반동(사이드 스윕)으로 약 3~3.5회전. 스윙~후방 통과에서 **양 무릎 신전(실측 168~176°) + 와이드 스트래들(실측 벌림각 최대 ~70°)**, 위 그립 팔 신전(실측 오른 팔꿈치 171.7°/오른 어깨 152.1°) | 어깨 처짐·으쓱(스윙 추진력 손실 — fault 가 left/right_shoulder 로 실포착), 스트래들 폭 부족·좌우 비대칭(split_angle 실포착), 무릎 굽음(추진 모멘트 손실). **주의: 무릎각은 fault 변별 신호가 아님이 실증됨**(정타가 fault 보다 더 굽는 신호 inversion — yaml 이력) → 코칭 우선순위는 어깨·스트래들 | "어깨 눌러(으쓱 금지)", "다리 크게 벌려(스트래들)", "무릎 펴고 발끝 포인", "반동은 다리로 만들어" | 스윙~후방 통과(3~5.5s, peak 4s, f27~f50): **양 어깨 + 스트래들 폭(양 고관절)**, 무릎은 보조 | `angle_vs_reference__{left_shoulder, right_shoulder}` + `split_angle` (fault 47점) | **ref frame confirms** — candidate f27~f50 (24프레임 일관) |
| **ref-climb** (클라임) | 오른손 상단 그립 + **양 무릎 X자**(왼 무릎 폴 앞·오른 무릎 폴 뒤)로 폴 잠금, 직립(실측 inv 4%), 연속 회전. peak(5s, f45) 실측: **양 무릎 대칭 굽힘 109.9°/109.6°(X자 hook)** + 그립 팔 신전(팔꿈치 176.8°/173.3°). 두 무릎의 접촉 안정성이 체공·회전 매끄러움 결정. IPSF Climbs 카테고리 = 각도 임계 없음(의도된 미박제) | 앞 무릎이 폴에 깊게 안 닿음(X자 잠금 약화 → 미끄러짐), 뒤 무릎 풀림(회전 감속 → 낙하), 어깨 으쓱(회전축 흔들림), 눈에 띄는 고쳐잡기·덜컹임(IPSF visible adjustments −0.5/건) | "무릎으로 잠가(X자)", "앞 무릎 깊게 대", "어깨 내려", "부드럽게 이어서" | hook 잠금 순간(peak 5s, f45 부근): **양 무릎 X자 접촉부 + 주 그립 어깨** | 없음 — **mode1 비교 게이트 전용(점수 없음)**, sweep status=comparison, activatedCriteria=None (COVERAGE-MATRIX (a) 항) | **ref frame confirms** — candidate f45± (X자 굽힘·직립·그립 신전 실측) |

## 검증 노트 — 무엇을 열어서 무엇을 확인했나 (D-19)

전 동작 공통: Firestore `reference/{motionId}/versions/phase33-cm3-run1` (reprocessedAt
2026-07-23, pipelineVersion phase33-cm3-run1) 을 읽기 전용으로 열어 joints3d `(x,y,0)` 를
(F,17,2) 로 재구성, peak window 프레임별 다리 방향각·인버전 비율·관절각을 산출했다
(스크립트는 세션 scratchpad, 관찰 전용·write 0). 골격 전체가 한 점으로 붕괴한 결측
프레임(span<30px)은 판독에서 제외했다.

| 동작 | 열어본 것 | 확인 결과 |
|---|---|---|
| power-spin | candidate f55~f92 전 프레임 수치 + **원본 영상(S3 ref-power-spin.mp4) 8s/9s 프레임 2장 육안** | hold 구간(f71~f92)에서 한 다리 위(155~180°)·한 다리 아래(0~33°), 무릎 165~176° 신전 — **폴 축 상하 수직 스플릿**. 영상 프레임 육안도 동일(다리 두 개가 폴을 따라 위·아래 일자) |
| peter-pan | candidate f18~f54 (36프레임) | 왼 무릎 176~178° 신전 고정 + 오른 무릎 40~107° 굽힘(hook) 고정 — 스태그 좌우가 seed 문서와 반대임을 확인, techniqueProfile 과는 일치 |
| elbow-twist-sister | candidate f99~f135 | window inv 86%(도립), f117 오른다리 위 165.6°·왼다리 아래 12.5°·가위각 178.1° |
| pdshape | candidate f54~f90 | inv 74%(도립), f54 양 무릎 141.6°/101.8° 굽힘 + 다리 위쪽(178°/148°) — 클로즈드 접힘 셰이프 |
| kip-up | candidate f27~f50 (24프레임) | inv 3%(인버전 없음), 무릎 168~176° 신전 유지, 다리 벌림각 최대 ~70°(스트래들 사이클), 오른팔 신전(팔꿈치 171~175°)·왼팔 굽힘 |
| climb | candidate f27~f63 | inv 4%(직립), peak f45 양 무릎 109.9°/109.6° 대칭 굽힘(X자 hook), 팔꿈치 176.8°/173.3° 신전 |

### UNVERIFIED 항목 (D-18 — 전수 불가분 명시)

- **power-spin 위 다리의 좌우 라벨:** candidate 데이터 = 왼다리 위 / seed 문서 = 오른다리 위
  — 상호 모순. 회전 중 키포인트 좌우 혼동은 이 파이프라인의 알려진 한계(faultzoom debug,
  facing 정량 프로브 FAIL)이므로 **좌우 라벨은 UNVERIFIED 로 박제**한다. 상하 방향(한 다리
  위·한 다리 아래 수직 스플릿) 자체는 수치+영상 육안 이중 확인으로 확정.
- **③열(강사 교정 어휘) 전체:** 특정 동작에 대한 강사 인터뷰 원문 미보유. 기존 문서
  (reference-motions.md 체크포인트 노트 정은지 v6 확정 + seed 노트 + IPSF 한국어 보고서)의
  어휘 재조합이다. 파일럿에서 강사 실사용 어휘가 수집되면 이 열을 갱신한다.

## 이 산출물이 틀렸다면 어떻게 알았을까 (D-18)

- 방향 claim 이 틀렸다면 → 표의 모든 방향 claim 은 열어본 candidate 프레임 번호를 달고
  있어 같은 프레임을 다시 열면 즉시 반증된다 (power-spin 은 영상 프레임 2장 이중 확인).
- 문서 간 모순(seed vs candidate)은 숨기지 않고 "정정" 으로 표에 노출했다 — peter-pan
  스태그 좌우, power-spin 위 다리 좌우, power-spin "천장/옆" 방향.
- criteria scope 가 틀렸다면 → sweep report 의 activatedCriteria 원문 대조로 반증 가능
  (fault 점수까지 병기).
- 확인 못 한 것(UNVERIFIED)은 비워두지 않고 무엇을 왜 못 봤는지 위 절에 명시했다.

# 축 반전 눈-우선 검증 — 발굴/침묵 시트 (quick-260816-p1x)

**이 페이지는 판정 재료다 — 판정은 belle 몫이다.** belle 승인일: 2026-08-16.

belle 가 같은 날 원안(폴거리를 "트랙이 먼저 주장하고 눈이 확인하는" 축으로
추가)을 뒤집었다. 구조:

```
구(폐기): 수치가 주장한다 → 눈이 검증한다   (축이 좁고, 좌표가 깨지면 무력)
신(채택): 눈이 후보를 낸다 → 수치가 검증한다  (축 제약 없음, 지어낸 것은 수치로 걸림)
```

폴거리는 "주장하는 축"에서 "검증기"로 자리를 옮겼다. 관절각도·사지기울기도
같은 검증기 목록에 함께 있다 — 눈이 좌표·마크 없이 학생/기준 전신 짝 스틸만
보고 형태 차이를 최대 3개 제안하면, 그 제안을 잴 수 있는 수치(폴거리/관절각/
다리기울기)로 검증해 promoted(일치)/rejected(불일치)/unmeasurable(수치화
불가 또는 tie-band) 3버킷으로 분류한다.

이 사이클은 **belle 판정 재료 생산까지다.** 운영 코드·채점·S3 업로드·
Firestore 쓰기 전부 무접촉 — card_gates/fault_zoom/skeleton/discover_sweep 은
전부 임포트 재사용(수정 0). backend/ diff = 0.

---

## 1. 기계 증명 요지

- **좌표 품질 게이트 (5동작, align.json 만 — 영상/Gemini 불요)**

  | 동작 | 해부학 모순(학생/기준) | 저신뢰 conf&lt;0.5(학생/기준) | 라벨 |
  |---|---|---|---|
  | elbow | 12.69% / 23.48% | 22.42% / 22.00% | **low** |
  | kipup | 0.00% / 0.00% | 2.08% / 0.28% | high |
  | pdshapefault | 5.51% / 12.66% | 14.52% / 21.62% | low |
  | peterpan | 0.00% / 0.00% | 0.92% / 2.97% | **high** |
  | powerspin | 32.52% / 32.91% | 10.84% / 9.70% | low |

  전 계산은 `evidence/quality_gate.json` — 콘솔 표와 동일.

  **정의 차이 정직 기재**: belle 가 2026-08-16 직접 실측해 준 참고값은
  elbow 모순 3.7%/7.8%·저신뢰 20.1%/22.3%, peterpan 모순 0%/0%·저신뢰
  0%/2.7% 였다(§verification_notes). 저신뢰율은 거의 일치(elbow 22.4%/22.0%
  vs 참고 20.1%/22.3%, peterpan 0.9%/3.0% vs 참고 0%/2.7%)하지만, **모순율은
  elbow 에서 3~4배 크게 나온다**(12.7%/23.5% vs 3.7%/7.8%). 원인은 셈 정의
  차이 — belle 의 계산은 좌우 다리를 각각 세어 분모가 "프레임×다리"였고, 이
  하네스는 plan 지정대로 "한쪽이라도 모순이면 그 프레임을 카운트"(분모=
  프레임)한다. 절대값은 다르지만 **elbow 가 peterpan/kipup 보다 확연히
  나쁘다는 순서는 그대로 유지**된다(모순 12.7~32.9%대인 elbow/pdshapefault/
  powerspin vs 0%대인 kipup/peterpan) — plan 이 사전 승인한 조건("순서만
  유지되면 진행")을 충족해 그대로 진행했다. pdshapefault/powerspin 은 이번에
  처음 산출(계획대로) — powerspin 은 모순율이 elbow 보다도 높게(32.5%/32.9%)
  나와 눈에 띈다(원인 미조사, 다음 사이클 참고 재료).

- **후보 소스**: `.planning/quick/260814-ehz-5/evidence/{elbow,peterpan}/
  candidates.json` 의 `poseMin`(claim 무관 최근접 짝, 재스캔 0) 을
  `row.pair.poseDist` 오름차순 top-4/record 로 압축. elbow 4 record
  (r00 right_elbow / r01 right_shoulder / r02 left_hip / r03 right_knee)
  x4 = 16, peterpan 1 record(r00 left_shoulder) x4 = 4. **합계 20건.**

- **눈 호출**: `eye_propose`(gemini-3.5-flash, temp 0, JSON schema 강제) —
  스모크 2 + 전량 20 = **총 22회**. 원본 프레임(무마크·무크롭) 전송, 추론
  호출만.

- **수치 검증**: 폴거리(`card_gates.body_pole_dist`, 힙중점-폴, tie
  0.15몸통) · 관절각(`card_gates.joint_angle`, tie 10도) · 다리기울기
  (`limb_tilt_deg` 신규, hip→ankle atan2, tie 8도). 55개 difference 전건
  분류: **promoted 8 · rejected 8 · unmeasurable 39.**

- **frames-before-numbers**: 짝 스틸 20건 전건 실행자 Read 육안 확인 —
  [evidence/VISUAL-REVIEW.md](evidence/VISUAL-REVIEW.md). 국면 불일치·붕괴·
  오크롭 0건.

- **제약**: backend/ diff 0, S3 업로드 0, Firestore 쓰기 0(refmotion 읽기만),
  Pod 무접촉, 채점 무접촉, pytest 기준선(4371 passed/59 failed/26 skipped)
  유지 — Task 3 §5 재확인.

---

## 2. elbow — 후보 20건 중 16건 (4 record x 4)

품질 라벨 = **low**(모순/저신뢰 둘 다 컷오프 초과) — "좌표가 깨진 동작에서도
구조가 무력해지지 않는가"의 실증 대상.

### r00 right_elbow

| cid | u/r(s) | poseDist | axis | 눈 moreSide | 수치(학생/기준) | numericMore | 버킷 |
|---|---|---|---|---|---|---|---|
| cand01 | 6.0/7.4 | 0.088 | joint_angle(left_knee) | reference | 35.5/41.5도 | similar | unmeasurable(tie) |
| cand01 | 6.0/7.4 | 0.088 | joint_angle(left_hip) | reference | 74.0/93.4도 | student | **rejected** |
| cand01 | 6.0/7.4 | 0.088 | limb_tilt(right) | student | 8.7/7.0도 | similar | unmeasurable(tie) |
| cand02 | 1.7333/1.6667 | 0.124 | joint_angle(right_elbow) | student | 98.2/96.4도 | similar | unmeasurable(tie) |
| cand02 | 1.7333/1.6667 | 0.124 | joint_angle(right_hip) | student | 71.1/82.3도 | student | **promoted** |
| cand02 | 1.7333/1.6667 | 0.124 | limb_tilt(left) | reference | -/74.7도 | None | unmeasurable(좌표부재) |
| cand03 | 7.4/9.1333 | 0.186 | limb_tilt(left) | reference | 36.3/44.3도 | similar | unmeasurable(tie) |
| cand03 | 7.4/9.1333 | 0.186 | pole_distance | reference | 0.264/0.345 | similar | unmeasurable(tie) |
| cand04 | 8.3333/10.7333 | 0.264 | joint_angle(left_knee) | reference | 176.1/160.7도 | reference | **promoted** |
| cand04 | 8.3333/10.7333 | 0.264 | joint_angle(left_elbow) | reference | 142.7/104.6도 | reference | **promoted** |
| cand04 | 8.3333/10.7333 | 0.264 | pole_distance(left_hip) | reference | 0.027/0.181 | reference | **promoted** |

**cand04(u8.33s/r10.73s) — 3개 항목 전부 promoted, 이 사이클 단일 최강
후보.** 눈이 낸 서술 3개(왼무릎 더 굽음/왼팔꿈치 더 굽음/골반이 폴에서 더
멀다, 전부 "기준이 더" 방향) 전부 수치와 방향 일치. pole_distance 항목은
`belleDirectionMatch=True` — belle 가 08-16 원 관찰("잘된 영상은 두 다리가
폴에서 띄어져")과도 같은 방향이다. 스틸: [stills/r00_cand04_PAIR_
u8.3333s_r10.7333s.jpg](evidence/elbow/stills/r00_cand04_PAIR_u8.3333s_r10.7333s.jpg).

### r01 right_shoulder

| cid | u/r(s) | poseDist | axis | 눈 moreSide | 수치(학생/기준) | numericMore | 버킷 |
|---|---|---|---|---|---|---|---|
| cand01 | 0.4667/0.5333 | 0.066 | joint_angle(right_elbow) | student | 93.6/91.4도 | similar | unmeasurable(tie) |
| cand01 | 0.4667/0.5333 | 0.066 | limb_tilt(right) | reference | 74.8/76.5도 | similar | unmeasurable(tie) |
| cand01 | 0.4667/0.5333 | 0.066 | joint_angle(left_knee) | student | 85.0/82.5도 | similar | unmeasurable(tie) |
| cand02 | 5.9333/7.3333 | 0.091 | joint_angle(left_elbow) | student | 94.5/92.6도 | similar | unmeasurable(tie) |
| cand02 | 5.9333/7.3333 | 0.091 | joint_angle(right_knee) | student | 173.3/174.7도 | similar | unmeasurable(tie) |
| cand02 | 5.9333/7.3333 | 0.091 | joint_angle(left_knee) | reference | 63.6/63.3도 | similar | unmeasurable(tie) |
| cand03 | 1.4/1.2667 | 0.107 | joint_angle(right_elbow) | student | 135.3/138.9도 | similar | unmeasurable(tie) |
| cand03 | 1.4/1.2667 | 0.107 | joint_angle(left_knee) | reference | 98.4/117.7도 | student | **rejected** |
| cand03 | 1.4/1.2667 | 0.107 | limb_tilt(left) | student | 67.8/73.0도 | similar | unmeasurable(tie) |
| cand04 | 15.5333/18.9333 | 0.296 | joint_angle(right_knee) | reference | 136.9/172.7도 | student | **rejected** |
| cand04 | 15.5333/18.9333 | 0.296 | pole_distance(left) | student | 0.308/0.125 | student | **promoted** |

cand04 의 promoted pole_distance 는 `belleDirectionMatch=False`(학생 쪽
다리가 더 멀다 — belle 일반 관찰과 반대 방향). 눈과 수치는 서로 일치하니
promoted 가 맞지만, 이 순간(클립 끝자락, u15.53/r18.93)에서는 **로컬 진실이
전체 서사와 반대**일 수 있다는 뜻 — 아래 §5 한계에 재론.

### r02 left_hip

| cid | u/r(s) | poseDist | axis | 눈 moreSide | 수치(학생/기준) | numericMore | 버킷 |
|---|---|---|---|---|---|---|---|
| cand01 | 0.9333/0.8667 | 0.064 | limb_tilt(left) | reference | 24.3/18.4도 | similar | unmeasurable(tie) |
| cand01 | 0.9333/0.8667 | 0.064 | joint_angle(right_knee) | reference | 176.0/177.4도 | similar | unmeasurable(tie) |
| cand01 | 0.9333/0.8667 | 0.064 | joint_angle(left_elbow) | student | 163.2/163.4도 | similar | unmeasurable(tie) |
| cand02 | 1.0/0.9333 | 0.106 | limb_tilt(right) | reference | 22.1/33.4도 | reference | **promoted** |
| cand02 | 1.0/0.9333 | 0.106 | joint_angle(left_hip) | student | 17.9/14.4도 | similar | unmeasurable(tie) |
| cand02 | 1.0/0.9333 | 0.106 | joint_angle(right_elbow) | student | 97.1/83.8도 | reference | **rejected** |
| cand03 | 15.7333/19.0 | 0.110 | joint_angle(right_knee) | reference | 178.5/176.9도 | similar | unmeasurable(tie) |
| cand03 | 15.7333/19.0 | 0.110 | limb_tilt(left) | reference | 39.4/64.1도 | reference | **promoted** |
| cand03 | 15.7333/19.0 | 0.110 | pole_distance(left) | student | 0.359/0.293 | similar | unmeasurable(tie) |
| cand04 | 11.1333/12.0667 | 0.148 | limb_tilt(left) | student | 9.7/7.0도 | similar | unmeasurable(tie) |
| cand04 | 11.1333/12.0667 | 0.148 | joint_angle(right_elbow) | reference | 71.4/103.3도 | student | **rejected** |

### r03 right_knee

| cid | u/r(s) | poseDist | axis | 눈 moreSide | 수치(학생/기준) | numericMore | 버킷 |
|---|---|---|---|---|---|---|---|
| cand01 | 0.6667/0.7333 | 0.052 | joint_angle(right_elbow) | student | 120.6/106.3도 | reference | **rejected** |
| cand01 | 0.6667/0.7333 | 0.052 | limb_tilt(left) | student | 40.0/33.5도 | similar | unmeasurable(tie) |
| cand02 | 1.7333/1.6667 | 0.124 | pole_distance | reference | 0.427/0.406 | similar | unmeasurable(tie) |
| cand02 | 1.7333/1.6667 | 0.124 | joint_angle(left_hip) | student | 13.3/7.4도 | similar | unmeasurable(tie) |
| cand02 | 1.7333/1.6667 | 0.124 | joint_angle(right_elbow) | student | 98.2/96.4도 | similar | unmeasurable(tie) |
| cand03 | 6.6667/6.7333 | 0.152 | joint_angle(right_knee) | reference | 179.8/173.0도 | similar | unmeasurable(tie) |
| cand03 | 6.6667/6.7333 | 0.152 | limb_tilt(right) | student | 5.9/2.3도 | similar | unmeasurable(tie) |
| cand04 | 3.4/5.6667 | 0.165 | limb_tilt(left) | student | 79.4/70.6도 | student | **promoted** |
| cand04 | 3.4/5.6667 | 0.165 | joint_angle(left_knee) | student | 14.8/19.0도 | similar | unmeasurable(tie) |
| cand04 | 3.4/5.6667 | 0.165 | pole_distance | student | 0.334/0.354 | similar | unmeasurable(tie) |

**elbow 소계 — 43 difference: promoted 8 · rejected 6 · unmeasurable 29.**

---

## 3. peterpan — 후보 4건 (1 record x 4)

품질 라벨 = **high**(모순 0%, 저신뢰 1~3%). "깨끗한 좌표에서도 눈이 틀릴 수
있고, 그 오답을 수치가 잡는가"의 실증 대상.

### r00 left_shoulder

| cid | u/r(s) | poseDist | axis | 눈 moreSide | 수치(학생/기준) | numericMore | 버킷 |
|---|---|---|---|---|---|---|---|
| cand01 | 5.2/6.8667 | 0.139 | joint_angle(left_elbow) | student | 170.0/174.4도 | similar | unmeasurable(tie) |
| cand01 | 5.2/6.8667 | 0.139 | joint_angle(right_knee) | reference | 55.5/104.4도 | student | **rejected** |
| cand01 | 5.2/6.8667 | 0.139 | pole_distance(left) | reference | 0.592/0.479 | similar | unmeasurable(tie) |
| cand02 | 1.4667/0.9333 | 0.145 | joint_angle(right_elbow) | student | 177.6/178.1도 | similar | unmeasurable(tie) |
| cand02 | 1.4667/0.9333 | 0.145 | pole_distance(left_hip) | student | 0.106/0.044 | similar | unmeasurable(tie) |
| cand02 | 1.4667/0.9333 | 0.145 | limb_tilt(left) | student | 11.0/9.8도 | similar | unmeasurable(tie) |
| cand03 | 6.0/7.6 | 0.163 | joint_angle(left_knee) | reference | 175.7/174.4도 | similar | unmeasurable(tie) |
| cand03 | 6.0/7.6 | 0.163 | joint_angle(right_hip) | reference | 90.4/132.1도 | student | **rejected** |
| cand03 | 6.0/7.6 | 0.163 | pole_distance | reference | 0.704/0.737 | similar | unmeasurable(tie) |
| cand04 | 3.3333/5.2667 | 0.167 | joint_angle(left_knee) | reference | 176.6/176.5도 | similar | unmeasurable(tie) |
| cand04 | 3.3333/5.2667 | 0.167 | pole_distance | reference | 0.782/0.824 | similar | unmeasurable(tie) |
| cand04 | 3.3333/5.2667 | 0.167 | joint_angle(right_knee) | student | 54.4/46.0도 | similar | unmeasurable(tie) |

**peterpan 소계 — 12 difference: promoted 0 · rejected 2 · unmeasurable
10.** 발굴(promoted) 0건 — **정직 기재, 억지 성립 0.**

---

## 4. peterpan 폴거리 대조 — belle 실측 방향과의 일치 여부

이번 top-4 poseMin 후보(§3)의 pole_distance 항목 4건은 **전부 unmeasurable
(tie-band)** 이다 — du-dr 차이가 POLE_TIE_TORSO(0.15몸통) 안쪽이라 방향을
확정하지 못한다. 그중 3건(cand01/cand03/cand04)은 moreSide=reference(belle
방향과 같은 쪽), 1건(cand02)은 moreSide=student(§Context 의 알려진 오답과
같은 방향)였지만, 넷 다 수치 차이가 작아 promoted/rejected 로 갈리지
못했다. **"이번 후보군에 belle 의 알려진 오답이 명확히 재현되지 않았다"가
정직한 결론이다** — 억지로 rejected 로 만들지 않았다.

belle 가 실측한 정확한 프레임(align 2.27초, u2.2667s/r2.2667s)은 poseDist
순위 5위(0.1954)로 top-4 컷 밖이라 정식 후보에 없다. §verification_notes
요청에 따라 **별건 프로브**로 그 프레임을 직접 검증기에 통과시켰다
([evidence/peterpan/belle_direction_probe.json](evidence/peterpan/belle_direction_probe.json)):

| 지표 | 학생 | 기준 | 방향 | belle 방향과 일치? |
|---|---|---|---|---|
| 힙중심 폴거리 (`card_gates.body_pole_dist`, 이 사이클 검증기) | 0.7621 | 0.4967 | student 더 멀다 | **불일치** — 눈의 오답(moreSide=student)과 방향이 같아 **promoted 로 확인돼버림** |
| 발목 폴거리 (참고 계산, 좌우 평균) | ~0.756 | ~0.871 | reference 더 멀다 | **일치** — belle "학생이 폴에 더 가깝다"와 같은 방향 |

같은 순간, **힙 지표와 발목 지표가 반대 방향을 가리킨다.** plan 이 재사용을
지정한 폴거리 검증기(`card_gates.body_pole_dist`, 힙중점 기준)는 이 특정
사례에서 눈의 오답을 걸러내지 못했다 — 오히려 확인해버렸다. belle 의 원
관찰("두 다리가 폴에서 띄어져")은 **다리(발목)** 에 대한 것이었는데, 이
사이클이 재사용한 지표는 **몸통 전체(골반)** 를 잰다 — 관찰 대상과 검증
지표의 신체 기준점이 어긋나는 경우가 있다는 뜻이다. §5 한계에 재론.

---

## 5. 한계·미결 (정직 박제)

1. **이 사이클은 판정 재료 생산만이다.** 운영 방출 아님 — 반영은 belle 판정
   후 별건 사이클. S3 업로드 0 / Firestore 쓰기 0(읽기만) / Pod 무접촉.
2. **좌표 품질표 절대값은 belle 사전 실측과 다르다**(모순율 elbow 12.7%/
   23.5% vs 참고 3.7%/7.8%) — 원인은 셈 정의(프레임 단위 vs 다리별 단위)
   차이, §1 에 명기. 순서(elbow≫peterpan/kipup)는 재현됐다.
3. **힙중심 폴거리 지표의 신체 기준점 한계**(§4) — belle 의 육안 관찰이
   다리/발목에 대한 것일 때, 힙중점 지표는 반대 방향을 낼 수 있다. 이번
   정식 후보(top-4)에서는 이 불일치가 tie-band 뒤에 가려 promoted/rejected
   어느 쪽으로도 드러나지 않았지만, 별건 프로브(§4)에서는 명백히 드러났다.
   **다음 의제 후보**: 발목 기준 폴거리 축을 추가하거나, "다리" 관련 눈
   서술에는 발목 지표를, "몸통/골반" 서술에는 힙 지표를 매칭하는 分岐(눈이
   이미 side/joint 로 신체 부위를 밝히므로 라우팅 가능) — 이 사이클에서
   구현하지 않았다(범위 밖, belle 판정 후 결정).
4. **tie-band(POLE_TIE_TORSO=0.15/ANGLE_TIE_DEG=10/TILT_TIE_DEG=8)는 이
   하네스의 신규 상수** — 기존 card_gates 게이트 임계(HOLD_MAX_DPS 등)와
   달리 **재튜닝 금지 대상이 아니다.** 55건 중 39건(71%)이 tie-band 로
   unmeasurable 인데, 이 비율이 임계가 너무 넓어서인지(진짜 차이도 가린다)
   너무 좁아야 하는지(우연 일치도 promoted 로 새는지) 판단할 fixture 가
   더 필요하다 — belle 판정 후 근거와 함께 조정 가능.
5. **peterpan 발굴 0건**은 순간 선택 방식(poseMin, claim 무관 최근접)의
   결과다 — 눈에게 물은 후보 4개가 전부 학생/기준 자세가 이미 상당히
   비슷한(포즈거리 0.14~0.17) 순간들이었다. claimContrast 처럼 의도적으로
   반대 자세를 찾는 방식이면 다른 결과가 나올 수 있으나, 이 사이클은 계획
   지정대로 poseMin 만 썼다.
6. **elbow 는 좌표가 깨졌는데도(모순 12.7%/23.5%) promoted 8건이 나왔다** —
   §Context 가 우려한 "좌표가 깨지면 트랙-주장 구조가 무력해진다" 문제를
   눈-우선 구조가 회피했다는 증거다(트랙 각도를 먼저 주장시키지 않고, 눈이
   본 것만 관절각/폴거리로 검증하므로 트랙 환각이 애초에 입력되지 않는다).
   다만 rejected 6건도 같은 동작에서 나왔으므로 "눈이 항상 옳다"는 뜻은
   아니다 — 검증기가 양방향으로 작동한다는 증거로 읽어야 한다.
7. **moreSide 텍스트 분류는 모델 판단에 의존**한다 — Gemini 가 "student"/
   "reference" 를 잘못 답할 가능성은 검증기가 잡지만, "axis"/"joint"/"side"
   분류 자체가 틀리면(예: 관절 이름을 잘못 짚음) 검증기가 엉뚱한 것을 잰다.
   이번 20건에서 스키마 위반·enum 이탈은 0건이었다(전건 유효 JSON).

---

## 6. belle 판정 요청 항목

| # | 항목 | 재료 |
|---|---|---|
| 1 | **elbow ★1순위 추천 — r00/cand04(u8.33s/r10.73s), 3축 전부 promoted** 채택/반려 | §2 표 + [스틸](evidence/elbow/stills/r00_cand04_PAIR_u8.3333s_r10.7333s.jpg) |
| 2 | 동반 promoted 5건(r00/cand02, r01/cand04, r02/cand02, r02/cand03, r03/cand04) 처분 | §2 표 |
| 3 | peterpan 발굴 0건을 **옳은 침묵**으로 볼 것인가 | §3 |
| 4 | **힙 vs 발목 폴거리 지표 불일치**(§4) — 다음 사이클에서 발목 지표를 추가할 가치가 있는가 | §4, belle_direction_probe.json |
| 5 | tie-band 값(§5-4)이 적절한가 — 조정 필요 여부 | §5 |
| 6 | 축 반전 구조(눈이 후보→수치가 검증) 자체를 이 방향으로 계속할 것인가 | 전체 |

사전 박제(추천과 근거)는 belle 판정 **전에** 커밋된다 —
[wif DISCOVERY-LEDGER.md](../260813-wif-knee-discovery/DISCOVERY-LEDGER.md)
승격 실적 장부에 이 사이클 절로 append 했다.

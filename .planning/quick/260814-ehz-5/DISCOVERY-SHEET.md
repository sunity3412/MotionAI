# 발굴 일반화 스윕 — 발굴/침묵 시트 (quick-260814-ehz)

**이 페이지는 판정 재료다 — 판정은 belle 몫이다.** belle 질문 "pdshape 에서만
한겨?" 의 답이자 지시 "다른 영상들도 이런식으로 아주 잘 부탁해" 의 이행이다.
wif 사이클이 왼무릎 단일 record 에서 성립시킨 발굴(좌표 무입력 스캔 → 게이트
3종 → 기계 눈 → 카드)을 **승인 5동작 13 record 전수**로 돌린 결과를 그대로
적는다. **발굴이 0건인 동작은 실행 수치와 탈락 사유로 침묵을 증명한다** —
후보를 억지로 성립시키지 않았다.

---

## 1. 기계 증명 요지

- **데이터 좌표 (5동작 전건 로컬 replay)** — doc/판정 트랙 = `.planning/phases/
  35-server-rendered-comparison-video/data/{motion}/{doc,align}.json`, 폴 =
  `.planning/quick/260811-ii0-card-gates-5/sweep_out/poles.json`, 승인 freeze =
  같은 디렉터리 `probes.log`, 영상 = S3 **read-only** (ufb `SWEEP_JOBS` 원문 키),
  기준 리포트 = Firestore **읽기만**.
- **소스 게이트 5/5 PASS** (record 스캔 **전**에 판정) — P35 doc/align 실물 +
  align 스키마(userKp/refKp/userScore/refScore/curveRefSec/fps/…) + 영상 다운로드
  + fps 교차검증. **"로컬 불가 — Pod 필요" 로 떨어진 동작 0건.**

  | 동작 | align fps 라벨 | 프레임수/길이 (학생/기준) | 실효 fps (학생/기준) | 판정 |
  |---|---|---|---|---|
  | elbow | 15.0 | 14.972 / 14.998 | 9.983 / 9.970 | PASS |
  | kipup | 15.0 | 14.970 / 15.000 | 9.973 / 10.000 | PASS |
  | pdshapefault | 15.0 | 15.019 / 15.029 | 9.997 / 9.957 | PASS |
  | peterpan | 15.0 | 14.943 / 15.000 | 9.963 / 9.923 | PASS |
  | powerspin | 15.0 | 14.982 / 15.005 | 9.983 / 10.000 | PASS |

- **게이트 임계 = `card_gates` 모듈 상수 그대로** (260811-ii0 SWEEP-REPORT §2
  확정값: hold <60도/초 3창 Theil-Sen · pose <0.85 · poleDiff <0.375 몸통 ·
  conf >=0.35 · 눈 claim 이분 <=100 / >=150도). **이 사이클 임계 재튜닝 0,
  하네스 내 신규 임계 0.**
- **초 환산 = align 15fps 타임베이스 단일.** 하네스 안에 9.0/18.0 라벨 분모
  사용 0 (카드 라벨만 운영 `label_fps` 실효 fps가 소유 — u8i 규율).
- **기계 눈 = `card_gates.machine_eye` 실호출 58회** (gemini-3.5-flash, temp 0).
  상한 = **record 당 16회**, `(motion, rid)` 키 계수기로 코드 강제 — 실측 최대
  9회(pdshapefault r00). 로그 = `evidence/{motion}/eye_calls.log`, 원장(마킹
  크롭 PNG + 판정 JSON) = `evidence/{motion}/eye_ledger/`.
- **렌더 = 운영 헬퍼 `app._run_gated_card_inherit` 그대로** (display_anchor
  단일 출처 + align_bake + label_fps). 새 문법 발명 0, 스타일 파라미터 신설 0.
  같은 입력 2회 재렌더 md5 **5/5 동일**.
- **frames-before-numbers** — 압축 후보 37건 전건의 (학생|기준) 무축소 짝 스틸
  + 산출 카드 5장을 실행자가 Read 로 직접 열어 확인한 뒤에만 이 표에 올렸다.
  기록 = [evidence/VISUAL-REVIEW.md](evidence/VISUAL-REVIEW.md).
- **제약** — backend/ diff 0, S3 업로드 0, Firestore 쓰기 0, Pod 무접촉, 채점
  무접촉(records 는 읽기만).

---

## 2. 동작별 1행 요약

| 동작 | record | 홀드 통과(프레임) | 버킷 | claim 유도 성립 | 압축 | 육안 | 눈 PASS | 재발견/신규 | 추천 | 침묵 사유 분포 |
|---|---|---|---|---|---|---|---|---|---|---|
| elbow | r00 right_elbow | 111/268 | 17 | 9 | 4 | 3 | **0** | — | 없음 | 눈 기각 3 (limb 상충 2 · 상태 반대 1) · 짝 불성립 8 · 육안 탈락 1 |
| elbow | r01 right_shoulder | 119/268 | 18 | 6 | 4 | 3 | **0** | — | 없음 | 눈 기각 3 (상태 반대 3, 어깨 가림) · 짝 불성립 11 · 중간각 1 · 육안 탈락 1 |
| elbow | r02 left_hip | 141/268 | 18 | 9 | 4 | 3 | **0** | — | 없음 | 눈 기각 3 (학생 굽힘 주장을 눈이 폄으로 2 · unclear 1) · 짝 불성립 8 · 중간각 1 · 육안 탈락 1 |
| elbow | r03 right_knee | 218/268 | 18 | 10 | 4 | 3 | **0** | — | 없음 | 눈 기각 3 (기준 굽힘 주장을 눈이 폄으로 2 · 학생 굽힘 기각 1) · 짝 불성립 8 · 육안 탈락 1 |
| kipup | r00 split_angle | 40/100 | 7 | — | 0 | — | **0** | — | 없음 | **split 단일 마크 좌표 부재 — 눈 유도 불가 7버킷 전건** |
| pdshapefault | r00 left_elbow | 158/272 | 19 | 15 | 4 | 4 | **1** | 신규 | **★ cand17B** | 눈 기각 3 (unclear 1 · off_body 1 · 상태 반대 1) · 짝 불성립 4 |
| pdshapefault | r01 right_elbow | 197/272 | 19 | 14 | 4 | 4 | **0** | — | 없음 | 눈 기각 4 (기준 4건 전부 굽힘으로 관측 = extended 주장 불성립) · 짝 불성립 4 · 중간각 1 |
| pdshapefault | r02 left_shoulder | 214/272 | 18 | 6 | 4 | 3 | **1** | 신규 | (동반) | 눈 기각 2 (상태 반대 2) · 짝 불성립 11 · 중간각 1 · 육안 탈락 1 |
| pdshapefault | r03 left_knee | 124/272 | 18 | 12 | 4 | 3 | **2** | **재현 1** + 신규 1 | (검증 행) | 눈 기각 1 (기준 마크가 팔) · 짝 불성립 5 · 중간각 1 · 육안 탈락 1 |
| peterpan | r00 left_shoulder | 90/91 | 7 | 1 | 1 | 1 | **0** | — | 없음 | 눈 기각 1 (기준 굽힘 주장을 눈이 폄으로) · 짝 불성립 6 |
| powerspin | r00 leg_extension | 86/123 | 8 | — | 0 | — | **0** | — | 없음 | **split 단일 마크 좌표 부재 — 눈 유도 불가 8버킷 전건** |
| powerspin | r01 split_angle | 86/123 | 8 | — | 0 | — | **0** | — | 없음 | **split 단일 마크 좌표 부재 — 눈 유도 불가 8버킷 전건** |
| powerspin | r02 left_shoulder | 75/123 | 8 | 6 | 4 | 2 | **1** | 신규 | **★ cand01E** | 눈 기각 1 (기준 unclear) · 짝 불성립 2 · 육안 탈락 2 |

합계 — **13/13 record 스캔 실행** · claim 유도 성립 88버킷 · 압축 37 · 육안 통과
29(탈락 8) · 기계 눈 실호출 58 · **눈 PASS 5 / 기각 24** · 카드 5장.

동작별 발굴 결과: **elbow 0 · kipup 0 · pdshapefault 4 · peterpan 0 · powerspin 1.**

---

## 3. 발굴 성립 — pdshapefault (4건)

### 3-1. ★ 추천: r00 / cand17B — 왼팔꿈치 (학생 16.47s / 기준 15.13s)

카드: [evidence/pdshapefault/cards/r00_cand17B_u16.4667s_r15.1333s_zoom_angle_vs_reference__left_elbow.png](evidence/pdshapefault/cards/r00_cand17B_u16.4667s_r15.1333s_zoom_angle_vs_reference__left_elbow.png)
전신 짝: [스틸 시트](evidence/pdshapefault/stills/r00_cand17B_PAIR_u16.4667s_r15.1333s.jpg)

- 게이트: 학생 hold 17.06도/초 PASS · 기준측 hold PASS · pose 0.3035 · poleDiff
  0.0251 · conf 양측 성립.
- 유도된 claim: 학생 트랙 94.1도 → `bent` / 기준 트랙 162.5도 → `extended`
  (서로 반대 = 대조 성립). 관절별 하드코딩 아님.
- 기계 눈: user bent→**bent/arm** + ref extended→**extended/arm** — 양측 확정 PASS.
- 육안: 두 패널 모두 폴을 등지고 잡은 같은 국면. 학생은 팔꿈치에서 꺾인 예각 V,
  기준은 팔을 따라 곧게 뻗은 선. **이번 산출 5장 중 대조가 가장 잘 읽힌다.**
- 승인 freeze 대조: 이 record 의 승인 정지는 u8.556/r9.40 → **신규 순간**
  (dU 7.91s). 참고로 스캔의 홀드 버킷은 승인 순간(8.556s)도 dU 0.044 로 덮는다
  — 발굴이 승인 장면을 못 찾아서 다른 데를 고른 것이 아니라, **그 자리에서
  claim 대조가 성립한 순간**을 고른 것이다.
- record 맥락: pdshapefault 최대 감점 record (편차 12.72, -15.3점).

### 3-2. 검증 행: r03 / cand13B — 왼무릎 (학생 12.87s / 기준 12.40s)

카드: [evidence/pdshapefault/cards/r03_cand13B_u12.8667s_r12.4s_zoom_angle_vs_reference__left_knee.png](evidence/pdshapefault/cards/r03_cand13B_u12.8667s_r12.4s_zoom_angle_vs_reference__left_knee.png)

- ★ **belle 이 wif 에서 채택한 바로 그 순간·그 카드를 일반 스윕이 재생산했다.**
  카드 md5 = `e891e7ae1fd13b0be1a7ec0470095edb` — wif 채택 카드와 **byte-동일**
  (0p2 재렌더 상속본과도 동일 = 세 경로 일치).
- 게이트 수치도 wif 와 동일: hold 21.743344080220453도/초 · pose
  0.4174272521676217 · 각도 0.3 / 155.2. (poleDiff 만 0.23511 → 0.23735 —
  wif 는 `compare_render._detect_pole` 자체 검출, 이번은 ii0 poles.json 정본을
  썼기 때문. 판정 불변.)
- 다만 **경로가 다르다**: wif 는 fresh doc `p34fresh1786628533` + `build_align`
  replay, 이번은 P35 `pdshapefault` doc + `align.json` 직접 로드 + 일반화된
  양방향 claim 유도. **좌표 무입력·다른 마운트·다른 유도 규칙에서 같은 결론.**
- **신규 추천으로 올리지 않는다** (중복 발명 금지 — 이미 belle 채택·반영 완료).
  이 행의 값은 "일반화가 채택 실적을 깨뜨리지 않았다"는 기계 증명이다.

### 3-3. 동반 재료: r03 / cand14B — 왼무릎 (학생 13.60s / 기준 12.93s)

카드: [evidence/pdshapefault/cards/r03_cand14B_u13.6s_r12.9333s_zoom_angle_vs_reference__left_knee.png](evidence/pdshapefault/cards/r03_cand14B_u13.6s_r12.9333s_zoom_angle_vs_reference__left_knee.png)

- 게이트: hold 4.38도/초 · pose 0.3734 · poleDiff 0.0436. 눈 양측 leg 확정 PASS.
- 같은 결함(다리 안 폄)의 **다른 순간**. 카드에 V 가 양측 구워졌다(학생 예각
  99도 vs 기준 일자 176도).
- **미결 명기**: "예각 V vs 일자 V" 는 belle 이 wif cand02b 에서 "사진상 알아볼
  수가 없음"으로 반려한 바로 그 문법이다. 가독성은 같은 의제 아래 있다.
- 같은 record 에 이미 채택 카드가 있으므로 추천 1안에서 제외.

### 3-4. 동반 재료: r02 / cand02B — 왼어깨 (학생 1.07s / 기준 2.20s)

카드: [evidence/pdshapefault/cards/r02_cand02B_u1.0667s_r2.2s_zoom_angle_vs_reference__left_shoulder.png](evidence/pdshapefault/cards/r02_cand02B_u1.0667s_r2.2s_zoom_angle_vs_reference__left_shoulder.png)

- 게이트: hold 22.60도/초 · pose 0.2021 · poleDiff 0.0708. 눈 양측 arm 확정 PASS.
- 승인 freeze(u3.222/r2.00) 대비 **신규 순간**.
- 육안: 어깨 V 는 "무엇이 사지인지"가 팔꿈치·무릎보다 덜 직관적이라 가독 중간.

---

## 4. 발굴 성립 — powerspin (1건)

### 4-1. ★ 추천: r02 / cand01E — 왼어깨 (학생 0.47s / 기준 0.73s)

카드: [evidence/powerspin/cards/r02_cand01E_u0.4667s_r0.7333s_zoom_angle_vs_reference__left_shoulder.png](evidence/powerspin/cards/r02_cand01E_u0.4667s_r0.7333s_zoom_angle_vs_reference__left_shoulder.png)
전신 짝: [스틸 시트](evidence/powerspin/stills/r02_cand01E_PAIR_u0.4667s_r0.7333s.jpg)

- 게이트: 학생 hold 6.13도/초 PASS · 기준측 hold PASS · pose 0.2859 · poleDiff
  0.1444.
- 유도된 claim: 학생 179.0도 → `extended` / 기준 30.2도 → `bent` — **방향이
  반대다**(학생이 뻗고 기준이 접음). 기계 눈 양측 arm 확정 PASS.
- 육안: 두 패널 다 폴을 잡고 몸을 수평으로 띄운 같은 국면. 학생은 곧은 선,
  기준은 접힌 V.
- 승인 freeze(u3.222/r5.733) 대비 **신규 순간**.
- **정직 명기**: 이 방향("챔피언은 접어 당기는데 학생은 뻗었다")이 코칭상
  결함 서사로 옳은지는 내가 단정하지 않는다 — belle 판정 재료로만 올린다.

---

## 5. 침묵 증명 — elbow (발굴 0)

**스캔은 전부 실행됐다.** 4 record 전건에서 홀드가 대량 통과했고(111~218 /
268프레임), claim 대조도 34버킷에서 성립했으며, 압축 16후보 중 12건이 육안을
통과해 기계 눈까지 갔다. **눈이 12건을 전부 기각했다.**

| record | 후보 | 학생 주장→관측 | 기준 주장→관측 | 기각 유형 |
|---|---|---|---|---|
| r00 right_elbow | cand02B (1.73/1.40) | bent→bent/arm ✓ | extended→extended/**leg** | limb 상충 (팔 마크가 다리에) |
| r00 right_elbow | cand07E (6.13/7.40) | extended→**bent**/arm | bent→**extended**/leg | 상태 반대 + limb 상충 |
| r00 right_elbow | cand10B (9.27/12.67) | bent→bent/arm ✓ | extended→**off_body** | 마크가 신체 밖 |
| r01 right_shoulder | cand16B (15.53/15.53) | bent→bent/arm ✓ | extended→**bent**/arm | 상태 반대 |
| r01 right_shoulder | cand12B (11.27/15.53) | bent→**extended** | extended→**bent** | 양측 상태 반대 |
| r01 right_shoulder | cand14B (13.40/15.53) | bent→bent/arm ✓ | extended→**bent**/arm | 상태 반대 |
| r02 left_hip | cand07B (6.80/6.73) | bent→**unclear** | extended→**unclear** | 양측 판독 불가 |
| r02 left_hip | cand10B (9.07/12.87) | bent→**extended**/leg | extended→extended/leg ✓ | 학생 굽힘 주장 불성립 |
| r02 left_hip | cand13B (12.60/12.87) | bent→**extended**/leg | extended→extended/leg ✓ | 학생 굽힘 주장 불성립 |
| r03 right_knee | cand05E (4.93/8.67) | extended→extended/leg ✓ | bent→**extended**/leg | 기준 굽힘 주장 불성립 |
| r03 right_knee | cand07E (6.67/8.67) | extended→extended/leg ✓ | bent→**extended**/leg | 기준 굽힘 주장 불성립 |
| r03 right_knee | cand11B (10.73/13.73) | bent→**extended**/leg | extended→extended/leg ✓ | 학생 굽힘 주장 불성립 |

★ **이 침묵에서 읽히는 것** — r02/r03 기각 5건은 트랙이 **5.0 / 6.0 / 6.8도**
같은 극단 굽힘을 주장한 순간인데 기계 눈이 전부 "펴져 있다"고 봤다. 관절 트랙
환각을 눈이 잡아낸 실물이다 (frames-before-numbers 게이트가 겨냥한 바로 그
현상). 임계를 만져 통과시키지 않았다.

육안 탈락 4건(cand06E · cand04B · cand14B · cand12E)의 사유는
[VISUAL-REVIEW.md](evidence/VISUAL-REVIEW.md) 에 건별로 적혀 있다.

## 6. 침묵 증명 — peterpan (발굴 0)

- 홀드는 **90/91프레임**이 통과했다(클립 대부분이 정지 판정). 그런데 claim 대조
  짝은 7버킷 중 **1건만** 성립했다 — 나머지 6버킷은 창 ±2s 안에 (양측 홀드 ∧
  반대 claim ∧ 짝 정합)을 동시에 만족하는 기준 프레임이 없었다.
- 유일 후보 cand03E(u2.267/r2.267, pose 0.804 = 임계 0.85 턱밑)는 육안 통과 후
  **기계 눈이 기준 측을 기각**했다: 기준 트랙은 17.0도(`bent`)라 했는데 눈은
  `extended/arm` 으로 봤다.
- **부록 실측(별건 의제 재확인)**: 이 record 의 승인 freeze 는 u6.444s 인데
  align 학생 클립은 91프레임/15fps = **6.067s** 다 — 승인 정지가 판정 트랙
  **클립 밖**이라 대조 행은 클램프된 6.0s 로 계산됐다. u8i 가 한계로 박제한
  "peterpan freeze 초가 클립 끝 밖" 이 이 스윕에서 재확인됐다 (freeze 타임베이스
  상류 의제, 이 사이클 범위 밖).

## 7. 침묵 증명 — split 3 record (kipup r00 · powerspin r00/r01)

- 세 record 는 `card_gates.crit_joint()` 가 **`split`**(벌림각)으로 판별하는
  축이다. 벌림각은 발목-힙중점-발목의 4점 각도라 **표시할 단일 관절 좌표가
  없다**(`cg.kp(rep, idx, "split")` = None). 기계 눈은 "주황 원이 표시한 관절"을
  묻는 판정이므로 **원리적으로 유도가 불가**하다.
- 그래서 이 세 record 는 claim 대조를 시도조차 하지 않고 **정직 탈락**시켰다
  (kipup 7버킷 / powerspin 8버킷 × 2 = 전건 사유 박제). 스캔·홀드 수치는 표에
  그대로 남아 있다 (kipup 40/100프레임, powerspin 86/123프레임).
- **운영 helper 와의 대조**: 운영 경로(`app._run_gated_card_inherit`)는 같은
  split 계열을 `pairSrc='align-peak'` + 비-각도주장 criterion 조건에서
  **게이트 비구속 pass-through** 로 통과시킨다(ii0 발견 1 — 절정은 원리적으로
  홀드가 아니다). 즉 **운영은 "게이트를 면제"하고, 발굴은 "유도가 불가하므로
  침묵"** 한다. 둘은 모순이 아니라 서로 다른 층의 결정이며, split 축을 발굴로
  회복하려면 **눈에게 물을 새 질문 형식**(벌림 정도)이 먼저 필요하다 — 이번
  사이클에서 발명하지 않았다.

---

## 8. 한계·미결 (정직 박제)

1. **이 사이클은 판정 재료 생산만이다.** 운영 방출 아님 — 반영은 belle 판정 후
   di7 일반 경로로 별건이다. S3 업로드 0 / Firestore 쓰기 0 / Pod 무접촉.
2. **pdshapefault 는 wif 와 같은 원본 영상이다.** wif 의 fresh doc
   (`p34fresh1786628533`)이 replay 로 쓴 트랙이 바로 P35 `pdshapefault`
   align(272/237프레임)이다. 그래서 3-2 는 "독립 표본에서의 재발견"이 아니라
   **같은 영상·다른 경로에서의 재생산**이다 — 과장하지 않는다.
3. **눈 기각 24건은 되돌리지 않았다.** 재시도·크롭 재조정·임계 완화 0 (1후보
   1판정). 기각이 옳았는지의 최종 판단은 belle 몫이며, 크롭 원장이 전건 있다.
4. **압축은 record 당 4건 상한**(포즈거리 오름차순)이다. 성립한 claim 대조
   버킷 88건 중 37건만 눈까지 갔다 — 상한 밖 후보 중에 더 나은 것이 있을
   가능성을 배제하지 못한다.
5. **split 축 발굴은 미해결** (§7). 새 눈 질문 형식이 필요하다.
6. **peterpan freeze 타임베이스** 클립 밖 문제 재확인 (§6) — 상류 의제.
7. **하네스 부작용 1건**: 렌더 중 `card_gates eye ledger 적재 실패 (비차단)`
   경고가 카드마다 1회 뜬다. 드라이버가 눈 판정을 메모 재사용하면서 크롭
   이미지를 함께 넘기지 않기 때문이며 **운영 코드 결함이 아니다**(운영은
   `_eye_cache` 가 튜플이라 이 경로가 없다). 크롭 원장은 `eye_ledger/` 에 이미
   전건 보존돼 있다.

## 9. belle 판정 요청 항목

| # | 항목 | 재료 |
|---|---|---|
| 1 | **pdshapefault 추천 cand17B(왼팔꿈치 16.5s) 채택/반려** | §3-1 카드 + 전신 짝 |
| 2 | **powerspin 추천 cand01E(왼어깨 0.5s) 채택/반려** — 방향 반대 서사가 유효한가 | §4-1 카드 + 전신 짝 |
| 3 | 동반 재료 2건(cand14B 왼무릎 13.6s · cand02B 왼어깨 1.1s) 처분 | §3-3, §3-4 |
| 4 | elbow·peterpan 침묵을 **옳은 침묵**으로 볼 것인가, 아니면 이 동작들에 발굴이 나와야 하는가 | §5, §6 |
| 5 | split 축(kipup·powerspin 2건) 발굴을 다음 사이클 의제로 세울 것인가 | §7 |

사전 박제(추천과 근거)는 belle 판정 **전에** 커밋된다 —
[wif DISCOVERY-LEDGER.md](../260813-wif-knee-discovery/DISCOVERY-LEDGER.md)
승격 실적 장부에 동작별 행으로 append 했다.

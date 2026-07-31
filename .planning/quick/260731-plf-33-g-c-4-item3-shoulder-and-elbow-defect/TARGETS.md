# 생성 대상표 — 어깨·팔 결함 일러스트 (quick-260731-plf Task 2)

정본 데이터 = `emit_census.json`(실 doc 방출 집계, 앱 함수 직접 호출) + `33-A1-MOTION-STANDARDS.md`
(국면·가이드 키잉). 기계 판독본 = `targets.json`.

## 1. 방출 집계 재산출 — 무엇을 해서 알았나

`emit_census.ts` 를 새로 만들어 **앱의 실제 함수를 import** 해서 돌렸다
(`deductionSheet.regionPartKeyForRecord` ← `deductionLabels.projectDeductionRecordKeypoints`).
규칙 사본 0 — `result.tsx:1852` 가 화면에서 하는 호출과 문자 그대로 같고, `faultJoints` 인자도
`result.tsx:1017` 과 같은 조건(`visionVeto.status === 'applied'` 일 때만 전달)으로 넘겼다.
입력 = §C-4 A-트랙 재산출 doc 4건 (`260731-iis-.../docs_after/*.json`).

| doc | referenceMotionId | 점수 | 카드 | 부위 키 → record |
|---|---|---|---|---|
| elbowtwistsisterFault | ref-elbow-twist-sister | 63 | 5 | **arm** ← left_elbow −3.8 · right_elbow −12.4 / **shoulder** ← left_shoulder −0.5 · right_shoulder −11.1 / leg ← left_hip −2.2 · right_hip −2.1 · left_knee −2.2 · right_knee −2.6 |
| kipupFault | ref-kip-up | 79 | 2 | leg ← split_angle −20.0 [vision] / **shoulder** ← left_shoulder −0.8 |
| pdshapeCorrect | ref-pdshape | 100 | 1 | leg ← right_knee −0.2 |
| powerspinFault | ref-power-spin | 60 | 4 | leg ← leg_extension −20.0 · split_angle −12.0 [vision] / **shoulder** ← left_shoulder −12.8 |

**PLAN verified_facts (A) 표와 차이 0.** 관절·부호·수치가 전부 일치했다 — 조용히 따른 것이 아니라
직접 재계산해서 같은 값이 나온 것이다. 차이가 났다면 이 절에 적었을 것이다.

**화면이 실제로 여는데 그림이 없는 조합 = 4건** (= Tier 1):
`ref-power-spin×shoulder` · `ref-kip-up×shoulder` · `ref-elbow-twist-sister×arm` ·
`ref-elbow-twist-sister×shoulder`.

`shoulder+arm` 복합 키는 4건 doc 어디에도 방출되지 않았다 (`arm_extension` 미발화). 구조적으로는
실재하는 키(`CRITERION_REGION_KEYPOINTS.arm_extension` = `REGION_MEMBER_KEYPOINTS.arms`)이므로
스위프 프로브 축에는 남아 있고, 부착은 fail-closed 로 0 이다.

## 2. Tier 1 — 생성 대상 4건

| # | 동작 | 부위 | t | 국면 창 (A-1) | 가이드 | 얹는 곳 | 방위 | 스타일 앵커 | cite 등급 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ref-power-spin | shoulder | **8.75s** | 7.1~10.2s hold | 원 | 양 견갑 | 도립 | ref-power-spin.jpg (동일 동작) | A |
| 2 | ref-kip-up | shoulder | 3.75s | 3~5.5s 스윙~후방 | 원 | 양 어깨 | 직립 | ref-kip-up.jpg (동일 동작) | A |
| 3 | ref-elbow-twist-sister | arm | 13.00s | 9.5~17.5s hold | 원 | 엘보 그립 팔꿈치 | 도립 | ref-invert.jpg (동일 방위) | A |
| 4 | ref-elbow-twist-sister | shoulder | 13.00s | 9.5~17.5s hold | 원 | 그립 측 어깨 | 도립 | ref-invert.jpg (동일 방위) | **B** |

### 가이드 종류가 4건 모두 `circle` 인 이유 (동작명 분기 아님)

L-4 키잉 규칙을 그대로 적용한 결과다. 어깨·팔꿈치의 A-1 코칭 어휘가 전부 **잠금·고정 계열**
(`으쓱하지 마(견갑 안정)` / `어깨 눌러(으쓱 금지)` / `팔꿈치로 감아` / `버텨`)이고 신전·라인 계열이
하나도 없다. 특히 엘보 그립은 **굽힘이 정답**이라 직선 금지 조항(L-4)에 정면으로 걸린다.
`line` 이 나올 수 있는 어깨·팔 갈래는 `arm_extension`(어깨→손 한 줄) 계열인데 그것은 4건 doc 에
방출되지 않았다 — 즉 규칙이 상수가 된 게 아니라 **입력이 한쪽으로 몰린 것**이다.
각 행의 `guideRuleMatch` 에 어느 문구가 규칙을 발화시켰는지 박제했다.

### t 교체 1건 (33-14 climb 선례)

`ref-power-spin` 은 33-14 선정 프레임 **8.50s** 에서 **양 견갑이 흰 상의와 머리카락에 가려**
크롭을 열어봐도 확인이 안 됐다. A-1 창(7.1~10.2s) 안에서 ±0.25s 로 7컷 콘택트 스트립
(`crop/ps_contact_strip.jpg`, 7.75/8.00/8.25/8.50/8.75/9.00/9.25)을 만들어 열람했고,
**8.75s** 가 등면 + 검정 브라 스트랩 아래 양 견갑 노출 + 위 다리 수직 스플릿 유지로 유일하게
두 조건을 동시에 만족했다. 9.00s 는 견갑은 더 잘 보이나 위 다리 무릎이 굽어 국면 완성이 흐려진다.

## 3. cite 등급 B 1건 — 보고 (재논의 아님)

`ref-elbow-twist-sister × shoulder` 는 A-1 표1 그 행의 **①②③④ 산문 어느 칸도 '어깨'·'견갑'
단어를 직접 쓰지 않는다.** 확인한 것: ① "도립 + 엘보 백 그립 + 무릎 hook + 윗다리 수직 익스텐션 +
백벤드/트위스트 8초 hold" · ② "윗다리 무릎 굽음 / hook 풀림 / 엘보 그립 고쳐잡기 / 흉추 안 열려 /
hold 지속 실패" · ③ "팔꿈치로 감아 / 윗다리 수직으로 뽑아 / 무릎 걸어 / 가슴 열어(흉추까지) / 버텨" ·
④ "윗다리 무릎·수직 라인 + 엘보 그립 팔 + hook 무릎".

그럼에도 Tier 1 에 넣은 근거는 둘이다.
1. 같은 행의 **criteria scope 열(sweep fault 실측)** 이 `left/right_shoulder` 를 채점 관절로
   명시한다 — 산문이 아니라 측정치다. 그리고 실제로 doc 이 `right_shoulder −11.1` 을 방출해
   **어깨 시트가 화면에서 열린다**.
2. ④의 "엘보 그립 **팔**"이 앱 부위 모델에서 어깨를 포함한다 —
   `REGION_MEMBER_KEYPOINTS.arms = [left_shoulder, right_shoulder, left_hand, right_hand]`.
   즉 ④의 '그립 팔'은 앱 기준으로 어깨 keypoint 를 덮는다.

**한계 명시:** 이 조합만 코칭 문구 근거가 간접이다. 그래서 그림 주제를 "어깨를 이렇게 만들어라"가
아니라 **"엘보 그립을 버티는 어깨를 고정한다"** 로 좁혔고, 그래도 게이트를 못 넘으면 배선하지
않는다(L-7). 이 사실을 SUMMARY 에도 올린다.

## 4. Tier 2 (예산 남을 때만 — §budget)

| 동작 | 부위 | a1_cite 요지 | 앵커 |
|---|---|---|---|
| ref-foxtop | shoulder | ④ "주 그립 견갑" · ③ "견갑 고정" | ref-foxtop.jpg |
| ref-climb | shoulder | ④ "주 그립 어깨" · ③ "어깨 내려" | ref-climb.jpg |

## 5. 제외 조합 — 이름과 사유 (조용한 누락 금지)

| 조합 | 제외 사유 |
|---|---|
| ref-pdshape × shoulder | ④에 어깨 없음. ②③에만 "어깨 부하 쏠림"/"어깨로 버텨" — 플랜이 지목한 경계선. 게다가 pdshape doc 은 leg 1건만 방출해 어깨 시트가 열리지도 않는다 |
| ref-foxtop-split × shoulder / arm | ④ = "양 다리 벌림각 + 신전측 무릎 + hook 무릎 / 보조: 슬로우 로테이션 척추 정렬" — 상체 부위 없음 |
| ref-invert × shoulder | ④ 본문은 다리, 어깨는 "보조: 리프트 구간(1~3s) 주 지지 견갑"뿐. 채점 국면(6~10s hold)과 다른 구간이라 국면 완성 프레임을 고를 수 없다 |
| ref-sideway-spin × shoulder | ④ "주 그립 어깨" 있음. 그러나 33-14 에서 3회 상한 소진한 미완 동작이고 다리 통과본도 없어 같은 방위(직립) 앵커만으로 자세 복제 위험이 가장 큼 — 예산 순위 밖 |
| ref-peter-pan × shoulder | ④ "위 그립 어깨" 있음. sideway-spin 과 같은 이유(33-14 미완, 앵커 없음) — 예산 순위 밖 |
| ref-climb × arm · ref-sideway-spin × arm · ref-kip-up × arm | ① 에 팔 신전 실측은 있으나 ④ 가 팔을 짚지 않는다. ④(강사가 어디를 보라 하는가)가 크롭·일러스트의 지정 열이므로 제외 |
| 전 동작 × shoulder+arm | 4건 doc 미방출 + 두 부위를 함께 짚는 가이드를 세울 A-1 근거가 지금 없다 (L-3 다토큰 편법 금지) |

## 6. 입력 프레임 — 무엇을 열어봤나 (PII: 리포 밖)

원본 mp4 3개를 S3 에서 **스크래치패드**로 받아 ffmpeg 로 단일 프레임 추출 후 PIL 로
대상 부위 중심 상반신 3:4 크롭을 만들었다. **리포에 영상·실사 0** (검증 게이트로 확인).

| 대상 | 크롭 박스(1080x1920 원본) | 크롭 비배경 | 열어보고 확인한 것 |
|---|---|---|---|
| power-spin × shoulder | (300,380,825,1080) 525x700 | 88.2% | 등면, 검정 브라 스트랩 아래 좌·우 견갑 노출. 위 다리가 폴을 따라 수직, 그립 팔 위로 |
| kip-up × shoulder | (270,600,690,1160) 420x560 | 82.5% | 등면, 한 팔 위 그립 + 양 어깨/승모근 선명. 스트래들 다리는 프레임 밖(어깨 주제로 좁힘) |
| elbow-twist × arm | (335,640,725,1160) 390x520 | 70.9% | 도립, 팔꿈치가 폴을 감은 잠금부가 화면 중앙 |
| elbow-twist × shoulder | (300,680,720,1240) 420x560 | 66.9% | 도립, 그립 측 어깨~겨드랑이 접합부 + 머리 아래 |

4장 전부 Read 로 직접 열어 대상 부위가 실제로 보이는지 확인한 뒤 진행했다.

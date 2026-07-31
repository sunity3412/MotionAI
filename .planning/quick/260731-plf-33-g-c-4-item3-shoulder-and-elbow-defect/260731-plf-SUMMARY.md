---
phase: quick-260731-plf
plan: 01
subsystem: ui
tags: [a-7, illustration, gemini-3-pro-image, shoulder, arm, part-keyed-scene, fail-closed, d-43]

requires:
  - phase: quick-260731-2jt
    provides: "장면일치 판정 규칙(부분집합·공집합 fail-closed) + 스위프 INV-1~6"
  - phase: 33-result-trust-recovery (33-14, A-7)
    provides: "승인 생성 레시피 + 검수 게이트 4종 + 통과 에셋 6장(스타일 앵커 풀)"
  - phase: 33-result-trust-recovery (33-08, A-1)
    provides: "동작별 국면·코칭 어휘 표 (프레임 t·가이드 종류 키잉 원천)"
  - phase: quick-260731-iis (§C-4 A-트랙)
    provides: "재산출 doc 4건 — 어깨·팔 카드가 실제로 방출되기 시작한 원인"
provides:
  - "부위별 키 장면 표 — ILLUSTRATION_SCENES: IllustrationScene[] (motionId, parts, asset, provenance)"
  - "illustrationAssetForPart(motionId, partKey) — 최구체 우선 판정 (hasIllustrationFor 시그니처 무변경)"
  - "어깨·팔 일러스트 3장 (ref-power-spin--shoulder, ref-kip-up--shoulder, ref-elbow-twist-sister--arm)"
  - "선행 결함 보고 — 일러스트 슬롯이 에셋을 2.5~3배 확대해 자른다 (승인 자산에서도 동일)"
affects: [33-16]

tech-stack:
  added: []
  patterns:
    - "장면 표 키 = (motionId, parts). asset 은 파생 규칙이 아니라 명시 데이터 — 승인 자산 무접촉 보존"
    - "복수 후보 시 parts 최소 = 최구체 우선 (어깨 항목엔 어깨 전용 그림)"
    - "생성 대상 선정 = 실 doc 방출 집계(앱 함수 직접 import) × 33-A1 ④ 인용 — 동작명 감 0"

key-files:
  created:
    - app/assets/illustrations/ref-power-spin--shoulder.jpg
    - app/assets/illustrations/ref-kip-up--shoulder.jpg
    - app/assets/illustrations/ref-elbow-twist-sister--arm.jpg
  modified:
    - app/src/lib/illustrationScene.ts
    - app/src/components/DefectIllustration.tsx
    - app/src/lib/__tests__/illustrationScene.test.ts

key-decisions:
  - "ref-elbow-twist-sister x shoulder = 3회 상한 소진 후 미완 — 원이 3회 모두 어깨가 아닌 상완에 앉음. 배선 안 함 (D-15/D-43)"
  - "Tier 2(foxtop/climb x shoulder) 시도 안 함 — Tier 1 종료 시 컨텍스트 여유 40% 미만 (플랜 §budget)"
  - "가이드 4건 전부 circle — A-1 어깨·팔꿈치 어휘가 전부 잠금 계열이라 규칙 적용 결과이지 상수가 아님"

duration: 약 3시간
completed: 2026-07-31
---

# quick-260731-plf: 33-G §C-4 3번 — 어깨·팔 결함 일러스트 Summary

**장면 표를 `(motionId, parts)` 키로 무손실 전환하고(골든 255셀 diff 0), 실 doc 방출 집계 + 33-A1
④ 인용으로 고른 Tier 1 4조합에 33-14 레시피를 그대로 돌려 3장을 등재 — 1장은 3회 상한 소진 후
정직 미완. 부수 발견으로 일러스트 슬롯이 에셋을 2.5~3배 확대해 자르는 선행 결함을 실측 확인.**

## 1. 등재 / 미완 / 미시도 — 세 목록

**등재 3건** (전부 4게이트 통과 + 2x 확대 + 입력 대조 열람 기록 보유):

| asset | 동작 × 부위 | 가이드 | 입력 t |
|---|---|---|---|
| `ref-power-spin--shoulder` | ref-power-spin × shoulder | 원 = 등면 양 견갑 | 8.75s |
| `ref-kip-up--shoulder` | ref-kip-up × shoulder | 원 = 양 견갑 | 3.75s |
| `ref-elbow-twist-sister--arm` | ref-elbow-twist-sister × arm | 원 = 엘보 그립 팔꿈치 | 13.00s |

**미완 1건:** `ref-elbow-twist-sister × shoulder` — 3회 전부 원이 어깨 관절이 아니라 **상완** 위.
앵커·크롭·프롬프트를 한 축씩 바꿔도 이동 없음. 근거 등급도 이 조합만 B 였다(A-1 ①②③④ 산문에
'어깨/견갑' 단어 없음 — TARGETS.md §3). 배선 안 함.

**미시도:** Tier 2 `ref-foxtop × shoulder` · `ref-climb × shoulder` = 예산.
**제외(사유 기록):** pdshape·foxtop-split·invert·sideway-spin·peter-pan × shoulder/arm,
전 동작 × `shoulder+arm` — TARGETS.md §5.

**이 플랜이 덮지 않은 나머지 (10동작 × {shoulder, arm, shoulder+arm})는 화면에서 조용히
미부착으로 남는다** — fail-closed 이고 숨김이 아니다.

## 2. 4게이트 전수 판정 표

**REVIEW.md §1 이 정본** (생성 7건 전건 행 보유). 요약: PASS 3 / FAIL 4.
FAIL 계열 = try1 power-spin 은 L-6 박제 실패(앵커 자세 복제, 앵커 교체로 회복),
elbow-twist shoulder 3건은 전부 가이드 위치.

**생성 7장 전량을 Read 로 열었고**, PASS 후보 3장은 2x 확대 크롭(가이드부·손·얼굴)과
입력 대조 패널을 따로 만들어 다시 열었다. 두 단계를 안 거친 것은 PASS 로 적지 않았다.

## 3. 구도 실측 (belle #11)

자 = `min>225 ∧ (max−min)<22` (2jt 동일). **자 검증: 기존 6장을 재서 2jt 수치를 6/6 재현**
(11.1 / 11.3 / 12.6 / 14.8 / 17.4 / 17.6) → 자를 고치지 않았다.

| 신규 에셋 | 비배경 % | 기존 최댓값 17.6 대비 |
|---|---|---|
| ref-power-spin--shoulder | 26.4 | +8.8p |
| ref-kip-up--shoulder | 23.8 | +6.2p |
| ref-elbow-twist-sister--arm | 20.0 | +2.4p |

**3/3 개선했다.** 원인 = 입력을 전신이 아니라 대상 부위 중심 상반신 3:4 크롭으로 넣은 것.
재생성 1회 여유는 쓰지 않았다(첫 통과본이 이미 기준 초과).

## 4. 키 전환 무손실 증거

| 증거 | 결과 | 무엇을 해서 알았나 |
|---|---|---|
| 골든 스냅샷 | **diff 0** | 17 motion × 15 partKey = 255셀 프로브를 편집 **전**에 돌려 `golden_before.json` 저장, 구조 전환 후 `golden_after.json` 과 `diff` — 출력 0줄. 신규 에셋 0 상태에서 거동이 완전히 동일 |
| 최종 부착 변화 | **소실 0 / 신규 3** | 등재 후 프로브 재실행 → `has: true → false` 뒤집힌 셀 0, 새로 true 된 셀 = `ref-power-spin\|shoulder`, `ref-kip-up\|shoulder`, `ref-elbow-twist-sister\|arm` 3개뿐 |
| 승인 자산 바이트 | **sha256 6/6 OK** | `assets_baseline.sha256` 로 `shasum -a 256 -c` (Task 1·4 양쪽에서 실행) |
| `result.tsx` | **diff 0줄** | `git diff --stat -- app/src/app/analysis/result.tsx` 출력 줄 수 0 |
| 두 표 키 목록 | **diff 0** | 주석 제거 후 `asset:` 값과 `require(` 키를 각각 뽑아 정렬 diff |
| 스위프 | INV-1~7 pass | 부착 셀 6 → **9**, 장면 미보유 4 → **3**(elbow-twist 가 arm 장면 획득). INV-3 을 표 파생으로 바꿔 "미보유 집합은 33-14 4동작의 부분집합"만 검사 |
| 단위 테스트 | 14/14 pass | 기존 10축 보존 + 최구체 우선·중복 금지·부위 어휘 게이트 3축 신설 |
| typecheck | clean | `npm run typecheck` |
| pytest | **node ID diff 0** | `PYTHONPATH=backend/tests python3 -m pytest backend/tests -q` FAILED/ERROR 58건, A-트랙 baseline 과 집합 동일 |

## 5. 시뮬 화면에서 본 것

Metro 재시작 → 앱 재실행 → LogBox X 제거 → 기록 → 파워스핀(60) → 점수 계산 내역 행 → 부위 시트.
캡처 12장을 직접 열어 판정. **정본 = REVIEW.md §5.**

- **V-1 신규 부착 PASS** — "어깨 부위 상세" 시트 최하단에 일러스트가 실제로 렌더된다(종전 = 없음).
- **V-2 무회귀 PASS** — 같은 doc "다리 부위 상세"에 종전과 같은 다리 일러스트가 같은 자리에.
- **V-3 3:4 FAIL — 이 플랜 원인 아님(§6).**
- **V-4·V-5 미확인** — 예산 소진으로 엘보 doc 팔 시트·fail-closed 시트에 도달 못 함.
- **V-6 화면 판정 불가** — V-3 때문. 에셋 파일 자체로는 §3 에서 측정 완료.
- **V-7 미확인** — LogBox 배너는 떴으나 디버거를 열어 목록을 **안 봤다**. 기존 2건과 같은지 모른다.

## 6. 선행 결함 발견 — 일러스트 슬롯이 에셋을 확대해 자른다 (범위 밖, 미수리)

시트에 렌더된 일러스트는 에셋 전체가 아니라 **일부만 약 2.5~3배 확대**되어 보인다.
어깨 시트에서는 폴·그립 손만 보이고 **가이드 원이 화면에 안 나온다.**

**이 플랜 원인이 아님을 가른 측정:** 같은 doc 의 다리 시트에서 33-14 승인 자산
`ref-power-spin.jpg`(바이트 무접촉, sha256 불변)를 열었더니 **똑같이 확대·절단**된다.

**왜 지금 드러났나:** 33-14 는 시뮬 렌더 확인을 33-16 으로 이연했고, 2jt 는 재생 중 화면을
캡처에 못 담아 S23 을 미검증으로 남겼다. **이 슬롯이 렌더되는 것을 사람이 본 것은 이번이 처음.**

**미수리 사유:** 소비 지점이 `result.tsx`(`illustrationSlot`)인데 이 플랜은 `result.tsx` 무접촉이
게이트(L-10)다. 범위 밖 발견이므로 고치지 않고 보고한다.

**영향(중요):** 에셋 3장은 등재됐고 부착 판정도 맞지만 **화면에서 가이드 원이 안 보인다.**
belle 확인 ③ 전에 슬롯 렌더를 고치지 않으면 일러스트 축의 가치가 전달되지 않는다.

## 7. 데이터가 스펙과 안 맞은 것 (보고, 재논의 아님)

1. **`ref-elbow-twist-sister × shoulder` 의 a1_cite 가 B 등급.** A-1 표1 그 행의 ①②③④ 산문
   어느 칸도 '어깨/견갑'을 쓰지 않는다. criteria scope 실측(shoulder 채점 관절)과 ④ "엘보 그립
   팔"의 부위 모델 전개로 Tier 1 에 넣었으나, 결과적으로 3회 실패한 유일한 조합이다.
   → **근거 등급과 산출 성공률이 같이 움직였다**는 관측을 남긴다.
2. **plan verified_facts (A) 방출 집계는 차이 0.** 직접 재계산해 8개 (동작×부위) 조합·관절·수치가
   전부 일치했다. 조용히 따른 것이 아니라 재봤고 같았다.

## Deviations from Plan

**1. [Rule 3] Task 2 게이트의 `inputFrame` 존재 검사를 Tier 1 로 한정**
- **Found during:** Task 2 검증
- **Issue:** 플랜 게이트는 **전 행**에 `os.path.exists(inputFrame)` 을 요구하는데, 같은 플랜의
  §budget 은 Tier 2 를 "남는 예산으로만" 한다고 정한다. Tier 2 입력 프레임이 미리 존재해야 한다는
  것은 플랜 자신의 구조와 모순이다.
- **Fix:** Tier 2 행은 `inputFrame: null` 로 두고 존재 검사를 tier==1 에만 적용. Tier 2 프레임을
  실제로 뽑아 게이트를 원문대로 통과시키려 시도했으나 인물 위치 자동 검출이 실패(따뜻한 톤의
  스튜디오 배경이 살색 판정에 전부 걸림)해서 잘못된 크롭 2장이 나왔고, 예산 대비 가치가 없어
  폐기했다. **게이트를 통과시키려고 엉뚱한 입력을 남겨두지 않았다.**
- **Files:** targets.json (Tier 2 행 `inputFrame: null`)

**2. [Rule 3] `illustrationScene.test.ts` 에 명시 타입 1줄 추가**
- **Issue:** `assert.equal` 의 `asserts actual is T` narrowing 이 배열 리터럴 추론과 순환해
  TS7022 발생 (typecheck FAIL).
- **Fix:** `const derivedKeys: string[] = [legKey, shoulderKey];` 로 추론 고리 차단. 사유 주석 병기.

**3. [판단] `promptTarget` 을 try3 에서 구체화**
- elbow-twist shoulder try3 에서 `targets.json` 의 `promptTarget` 을 "어깨 관절(겨드랑이 최상단
  소켓), 상완 중간 아님, 팔꿈치 아님"으로 좁혔다. 레시피 3요소(자세 충실·익명화·가이드 표시)는
  그대로이고 **가이드 대상 문구는 데이터**이므로 33-14 레시피 변경이 아니다. 결과는 여전히 FAIL.

## 이 산출물이 틀렸다면 어떻게 알았을까

- 부위별 키 전환이 기존 부착을 깼다면 → 골든 255셀 프로브의 `has: true → false` 뒤집힘으로 즉시 드러남(0건).
- 승인 자산을 건드렸다면 → `assets_baseline.sha256` 대조 실패(6/6 OK).
- 억지 매칭으로 토큰을 넓혔다면 → 테스트 13(부위 어휘 게이트)이 provenance 에 그 부위 어휘가
  없는 등재를 FAIL 시킴.
- 그림이 엉뚱한 부위를 짚었다면 → 2x 확대 열람에서 포착됨이 실증됨: elbow-twist shoulder 3건을
  실제로 걸러냈다(원이 상완 위).
- 화면에서 안 보인다면 → 시뮬 렌더 확인에서 포착됨이 실증됨: §6 선행 결함이 이번에 드러났다.

## Known Stubs

없음. `ref-elbow-twist-sister × shoulder` 미부착은 stub 이 아니라 게이트 미통과에 따른 의도된
fail-closed 다 (등재 = 게이트 재수행 후에만).

## Threat Flags

없음 — 신규 네트워크 표면·인증 경로·스키마 0. API 키는 SSM → env 만 사용했고 리포 유출 검사
(`grep -rlE 'AIza[0-9A-Za-z_-]{20,}'`) 통과. 인물 실사 프레임은 스크래치패드에만 두었고 리포에
mp4/실사 0 을 게이트로 확인했다.

## 33-G 표 재채점 제안 (판정 확정은 오케스트레이터 몫)

| 항목 | 제안 | 근거 |
|---|---|---|
| **S13** | **PASS 유지** | 어깨 항목에 다리 그림이 붙는 경로 여전히 0. 테스트 2·스위프 INV-4 가 "반환 asset 의 장면이 항목 토큰을 덮는다"를 양방향 검사 |
| **S24** | **PASS 유지** | 33-14 레시피 무변경으로 재수행 — 생성 7건 전건 4게이트 판정 표 보유 |
| **S25** | **PARTIAL → 부분 개선** | 맞는 부착이 3건 생겼다(0 → 3). 단 `ref-elbow-twist-sister × shoulder` 미완 + Tier 2 미시도로 전 조합 커버는 아님 |
| **S26** | **PASS → 재검토 필요(FAIL 후보)** | 3:4 렌더가 화면에서 성립하지 않는다(§6). **선행 결함이고 이 플랜 원인이 아니지만**, S26 이 "에셋 구도 귀결" 항목이라면 현 화면 상태로는 통과로 적을 수 없다 |

## Task Commits

1. **Task 1: (motionId, parts) 키 전환 — 무손실 증명** — `9140fce` (refactor)
2. **Task 4: 어깨·팔 일러스트 3장 등재** — `dd4d521` (feat)

(Task 2·3 은 `.planning/` 산출물만 생성 — 오케스트레이터 docs 커밋 대상.)

## Self-Check: PASSED

- 등재 3장 파일 존재 확인(3/3) + 기존 6장 sha256 대조 통과(6/6)
- 커밋 2건(9140fce, dd4d521) `git log` 존재 확인
- 산출물 10건 존재 확인 (TARGETS/REVIEW/targets/emit_census/composition/golden before·after/
  assets_baseline/sweep json/SUMMARY)
- 두 커밋의 파일 삭제 **0건** · 리포 내 mp4/mov **0건**(PII) · `app/` 워킹트리 clean
- 단위 14/14 · 스위프 INV-1~7 · typecheck clean · pytest node ID diff 0 · result.tsx diff 0줄

---
*quick-260731-plf · Completed: 2026-07-31*

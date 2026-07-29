---
phase: 33-result-trust-recovery
plan: 14
subsystem: ui
tags: [a-track, a-7, illustration, gemini-3-pro-image, anatomy-review, silent-hidden, d-15]

# Dependency graph
requires:
  - phase: 33-result-trust-recovery (33-11, A-4)
    provides: "A-7 생성 규칙 개정 확정 + 승인 불변식 ②(장면-일러스트 일치) + 스타일 앵커 = 7R 후보 1 경로 + 검수 게이트 4종"
  - phase: 33-result-trust-recovery (33-08, A-1)
    provides: "동작별 국면 정의 표 (프레임 선정 데이터 키잉 원천 — ④ 어디를·어느 순간)"
  - phase: 33-result-trust-recovery (33-09, A-2)
    provides: "교정 방향 확정 phrasebook (그림 = 옳은 교정 대조 원천)"
  - phase: 33-result-trust-recovery (33-13, A-6)
    provides: "result.tsx 배선 질서 (드릴다운 시트 = 결함별 상세 소비 위치)"
provides:
  - "검수 통과 일러스트 6동작 번들 (app/assets/illustrations/{motionId}.jpg — power-spin, kip-up, climb, invert, foxtop, foxtop-split)"
  - "DefectIllustration 컴포넌트 — motionId 키 정적 require 맵 + silent 'hidden' 폴백 (미검증/mode3 = 렌더 0)"
  - "DeductionDetailSheet.illustrationSlot — 승인 목업 ② 일러스트 슬롯 위치, 매핑은 result.tsx 소유"
  - "미완 4동작 정직 기록 (peter-pan, elbow-twist-sister, pdshape, sideway-spin — fail-closed hidden)"
affects: [33-15, 33-16]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "일러스트 생성 파이프라인 = 데이터 테이블(33-A1 국면 키잉) 소비 — 동작명 코드 분기 0"
    - "검수 게이트 4종(익명·자세 충실·가이드 선·해부학) 육안 전수 + 실패 = fail-closed 미배선"
    - "6R 표준 선 교정 폴백 (코럴 검출 -> 중앙값 인페인트 -> 직선 재작도) 재사용"

key-files:
  created:
    - app/assets/illustrations/ref-power-spin.jpg
    - app/assets/illustrations/ref-kip-up.jpg
    - app/assets/illustrations/ref-climb.jpg
    - app/assets/illustrations/ref-invert.jpg
    - app/assets/illustrations/ref-foxtop.jpg
    - app/assets/illustrations/ref-foxtop-split.jpg
    - app/src/components/DefectIllustration.tsx
  modified:
    - app/src/components/DeductionDetailSheet.tsx
    - app/src/app/analysis/result.tsx

key-decisions:
  - "power-spin 에셋 = 7R 승인 통과본 cand1 채택 (동일 8.5s 입력 프레임·동일 경로 산출물, belle 열람 검수 통과 — 재생성 불필요)"
  - "자세 후퇴(앵커 자세 복제) 대응: try3 = 입력 인물 크롭 확대 + 같은 방위 통과본을 스타일 앵커로 교체 (2안 계열 스타일 유지)"
  - "미완 4동작 = 재생성 상한 3회 소진 후 fail-closed hidden — 틀린 그림은 배선하지 않는다 (D-15/D-18)"
  - "일러스트 슬롯 = DeductionDetailSheet 옵셔널 prop, 매핑은 result.tsx 소유 (승인 목업 ② 위치)"

# Metrics
duration: 약 50분 (2026-07-29 03:10~04:00 UTC)
completed: 2026-07-29
---

# Phase 33 Plan 14: A-7 결함 일러스트 세트 Summary

**승인 레시피(기준 영상 국면 완성 프레임 → gemini-3-pro-image 이미지 투 이미지 → 4종 게이트 육안 전수 검수)로 등재 10동작 전부에 일러스트 생성을 수행 — 6동작 PASS 번들 + silent-hidden 배선, 4동작은 상한 3회 소진 후 정직 미완 (틀린 그림은 배선하지 않음)**

## 생성 파이프라인 (10동작 전수 성립 — blocking anti-pattern 대조)

동작명 하드코딩 코드 분기 **0**. 파이프라인 전 단계가 데이터 테이블(`motions.json`, 세션 산출)을 소비하고, 테이블의 전 항목은 33-A1 표에서 키잉:

1. **프레임 선정** — S3 원본(`reference/{motionId}.mp4`, 7R 목업과 동일 경로) 로컬 다운로드 → 33-A1 ④ 국면 창·peak 키잉으로 후보 5컷 추출(창 내 클램프) → 콘택트시트 육안 전수 열람 후 국면 완성 프레임 선정(승인 불변식 ②). Pod 무접촉 (분석 호출 0).
2. **생성** — gemini-3-pro-image v1beta generateContent, responseModalities [TEXT,IMAGE], aspect 3:4, SSM 키(profile sunity-motion). 입력 1 = 국면 완성 프레임, 입력 2 = 2안 스타일 앵커(illust_variant2_pro.jpg). 프롬프트 = 자세 충실 + 익명화 + 가이드 표시(highlight 데이터 키잉: 신전/라인 계열 = 곧은 선, hook/잠금 계열 = 부위 원 — 굽힘이 정답인 부위에 직선 금지).
3. **검수** — 게이트 4종(① 익명 ② 자세 충실 ③ 가이드 선 ④ 해부학) 생성 전량 Read 육안 + PASS 후보는 2x 확대 크롭(선·손발·얼굴) 추가 열람 + 입력 프레임 원본 대조.

**등재 10동작 전수에 동일 파이프라인 실행** (표 아래). 산출 성립은 6/10 — 미완 4동작은 아래 정직 기록.

## 입력 프레임 선정 기록 (전수 육안)

| 동작 | 선정 t | 근거 (33-A1 창 내) |
|---|---|---|
| ref-power-spin | 8.50s | 7R 검증 재확인 — 두 다리 폴 축 한 줄 최곧음, hold 7.1~10.2s |
| ref-peter-pan | 3.00s | 측면 — 신전 다리 곧음 + hook 무릎 동시 가시 (창 2~6s, 추가 4컷 재추출 후 선정) |
| ref-elbow-twist-sister | 13.00s | A-1 peak f117 일치 — 윗다리 수직 익스텐션 최대 |
| ref-pdshape | 8.25s | 폴 가림 없는 측면 클로즈드 셰이프 (창 3.5~11.5s) |
| ref-kip-up | 3.75s | 등면 와이드 스트래들 최대 + 양 무릎 신전 (창 3~5.5s) |
| ref-climb | 5.25s | X자 잠금 + 그립 팔 동시 가시 (5.00s 등면은 머리카락 가림) |
| ref-invert | 7.25s | 대칭 와이드 스플릿 최대 개방 (창 6~10s) |
| ref-foxtop | 18.25s | A-1 f164~f183 창 내 — 위 다리 수직 + 아래 다리 신전 |
| ref-foxtop-split | 12.25s | 신전측 다리 곧음 + 벌림 개방 (창 11~13s) |
| ref-sideway-spin | 9.00s | A-1 peak f81 일치 — 발레 라인 + 그립 팔 신전 |

## 검수 게이트 4종 전수 판정 표 (생성 21회 + 채택 1건 — 전량 Read 열람)

게이트: ① 익명(이목구비 제거) ② 자세 충실(입력 프레임 동일 자세) ③ 가이드 선(곧은 획·부위 관통) ④ 해부학(사지 수·관절)

| 동작 | 시도 | 판정 | 세부 |
|---|---|---|---|
| power-spin | try1 | FAIL ② | 스타일 앵커의 앉은 자세 복제 (7R 박제 실패 계열) |
| power-spin | **채택 = 7R cand1** | **PASS** | 동일 8.5s 입력·동일 경로의 belle 열람 통과본 (⑤ provenance: 팔 2·다리 2·무이목구비·수직 스플릿·선 한 줄) — 본 세션 재열람 확인 |
| peter-pan | try1·try2 | FAIL ② | 앵커 앉은 자세 복제 x2 |
| peter-pan | try3 | FAIL ②③ | 스태그는 성립했으나 자유 다리 무릎 가시적 굽음(핵심 코칭 "뒷다리 길게 펴"와 모순 = 틀린 교정 그림) + 선이 발끝 밖 초과·엉뚱한 시작점 — 확대 재판정으로 확정 |
| elbow-twist-sister | try1 | FAIL ③② | 선이 몸통 관통 곡선 + 손이 골반 위(엘보 그립 불충실) |
| elbow-twist-sister | try2 | FAIL ② | 앵커 앉은 자세 복제 |
| elbow-twist-sister | try3 | FAIL ② | 도립은 성립, 신전 다리가 수평 — A-1 실측(위 165.6° 수직 익스텐션)과 국면 기하 불일치 |
| pdshape | try1·try2 | FAIL ② | 앵커 앉은 자세 복제 x2 (클로즈드 셰이프 아님) |
| pdshape | try3 | FAIL ④② | **발 3개(다리 3개) — 1안 기각과 동일 해부학 오류** + 접힘 대신 스플릿 |
| kip-up | try1 | **PASS** | 등면 스트래들·양 무릎 신전·선 2줄 곧음·손가락 자연·무이목구비. 정직 노트: 입력에서 가림된 왼팔을 들어올린 팔로 재구성 + 그립 팔 좌우 반전(회전 좌우 라벨 UNVERIFIED 축 — 코칭 주제인 스트래들 폭·무릎·어깨는 충실) |
| climb | try1 | **PASS** | X자 잠금·직립·부위 원·발가락 자연·무이목구비. 정직 노트: 아래 그립 팔이 실측 신전 대신 굽은 스태거 그립, 원이 앞무릎 중심(뒷무릎 일부 포함). climb = 비교 전용(점수 없음 — record 발생 없어 표시 빈도 낮음) |
| invert | try1 | FAIL ② | 직립 V-sit — 도립 아님 |
| invert | try2 | **PASS** | 도립 + 대칭 스플릿 + 선 2줄 곧음·발가락 자연·얼굴 완전 가림(확대 확인). 정직 노트: 벌림각이 실측 152°보다 좁게(~120°) 그려짐 — 목표 방향 동일, 과소 표현 |
| foxtop | try1 | FAIL ③ | 선 2줄이 몸 밖 초과 + 얼굴 관통, 스타일 이탈(순수 연필화) |
| foxtop | try2 | FAIL ② | 앵커 앉은 자세 복제 |
| foxtop | try3 | **PASS** | 도립 + 위 다리 수직 신전 + 선이 골반→발끝 곧게 몸 위만(확대 확인) + 무이목구비·그립 손 자연 |
| foxtop-split | try1 | PASS 조건부 → **PASS (선 교정)** | 자세·해부학·익명 통과, 선이 전장 완만한 휨(윤곽 추종) → **6R 표준 폴백 적용**(코럴 6,235px 검출 → 중앙값 인페인트 → 기존 양 끝점 잇는 직선 재작도, 코어 9px #FF4B33 + halo) → 교정 후 확대 재열람: 직선이 다리 위에만, 잔재 0. 정직 노트: 신전측 다리가 입력(12.25s 사선)보다 수평 — A-1 peak f108 실측(수평 100.9°)과는 일치 |
| sideway-spin | try1·try2 | FAIL ② | 앵커 앉은 자세 복제 x2 |
| sideway-spin | try3 | FAIL ② | climb 앵커의 무릎 굽힘 잠금 자세 복제 — 발레 라인 아님 |

**최종: PASS 6동작 (power-spin, kip-up, climb, invert, foxtop, foxtop-split) / 미완 4동작 (peter-pan, elbow-twist-sister, pdshape, sideway-spin — 각 3회 상한 소진).** FAIL 산출물은 전부 번들 밖(스크래치 보관), 배선 0.

## 미완 4동작 정직 보고

- 공통 실패 계열 = **스타일 앵커 자세 복제(자세 후퇴)** — 7R에서 4/6 기각으로 박제된 것과 동일. 입력 크롭 + 같은 방위 앵커 교체(try3 전략)로 invert·foxtop 은 회복됐으나 4동작은 회복 실패.
- 이 4동작의 결함 상세 시트는 **일러스트 없이 기존 그대로** 렌더 (DefectIllustration 이 null — 에러 표면 0).
- 재시도 경로(차기 플랜 재량): 앵커 풀이 커진 상태(이번 PASS 6장)에서 방위 일치 앵커 재선택 + 상한 리셋.

## Task 2 — 배선 (silent-hidden)

- `DefectIllustration.tsx`: named export + inline prop + 헤더 결정 주석 + StyleSheet 하단 + 토큰만(radius.card — 하드코딩 색/간격 0). `VERIFIED_ILLUSTRATIONS` 정적 require 맵(motionId 키), 미등록 = `return null` ('hidden'). RN 기본 `Image` — 신규 라이브러리 0.
- `DeductionDetailSheet`: `illustrationSlot?: React.ReactNode` — 행동 큐 아래 = 승인 목업 ② "확대 크롭 + 감점근거 글 + 일러스트 슬롯" 순서. D-05: 캡션/라벨 텍스트 0 (그림이 말을 대체).
- `result.tsx`: `motionId = mode1 ? cmp.referenceMotionId : null` — mode3·미등재는 자동 hidden (fail-closed). 드릴다운 시트는 topFix·접힘 카드·범례·틱 4개 진입점 전부의 상세 소비처라 "결함별 매핑" 단일 지점으로 성립.

## 검증 결과

- `npm run typecheck` (tsc --noEmit) clean.
- 신규 패키지 0 (package.json 무변경).
- git diff = app/assets/illustrations(6) + DefectIllustration.tsx + result.tsx + DeductionDetailSheet.tsx (Deviation 1) + SUMMARY/STATE/ROADMAP. 채점·백엔드·Pod 무접촉.
- 에셋 6장 = 720x964 (3:4), 개당 48~61KB, 총 ~340KB (번들 부담 최소화 리사이즈).

## Deviations from Plan

**1. [Rule 2 - 승인 계약] DeductionDetailSheet.tsx 수정 (plan files_modified 밖)**
- **Found during:** Task 2 배선 지점 결정
- **Issue:** 승인 목업 ②가 일러스트 슬롯 위치를 "부위 탭 → 상세"로 지정 — 앱에서 그 표면은 DeductionDetailSheet. result.tsx 인라인 배선만으로는 승인 설계 위치와 불일치
- **Fix:** 시트에 옵셔널 `illustrationSlot` prop 만 추가(기본 undefined = 타 소비처 diff 0), 매핑 로직은 계획대로 result.tsx 소유. 33-13 의 "승인 설계 = 상위 계약" 해석 선례
- **Commit:** 4a6921e

**2. [Rule 3 - 생성 실패 대응] try3 전략 변경 (입력 크롭 + 방위 일치 앵커)**
- **Issue:** 2안 스타일 앵커(앉은 자세)가 자세를 오염 — 10회 중 8회 앵커 자세 복제
- **Fix:** 입력 인물 크롭 확대 + 같은 방위의 이번 세션 통과본을 스타일 앵커로 교체(2안 계열 스타일 유지 — 레시피 취지 보존). invert(try2 힌트만으로)·foxtop(try3) 회복
- **잔여 영향:** 미완 4동작 (위 정직 보고)

**3. [판단] power-spin = 7R cand1 채택 (신규 생성 대체)**
- 승인 규칙의 스타일 앵커 자체가 "후보 1 경로"이고 cand1 은 동일 입력 프레임(8.5s)·동일 경로의 검수 전 항목 통과본 + belle 열람본 — 재생성은 검수 통과본을 버리고 복권을 다시 긁는 행위라 채택이 규칙에 더 충실
**4. [데이터 수정] foxtop highlight = "양다리 관통 한 줄" → "위 다리 한 줄"**
- 근거: A-1 ④ "위(왼)다리 라인 + 양 무릎" — 위 다리 라인이 주 대상. 입력 프레임에서 두 다리가 동일선상이 아니라 한 줄 관통이 기하적으로 불성립 (try1 선 실패의 원인)

## 무엇을 열어서 확인했는가 (D-19)

- 콘택트시트 11장(50+4컷) + 선정 프레임 원본 5장 재열람 (프레임 선정).
- 생성 산출물 21장 전량 Read 열람 + PASS 후보 확대 크롭 10장(선·손발·얼굴·잠금부) + 선 교정본·교정부 확대.
- 번들 저장본 스팟 체크 (ref-power-spin.jpg 리사이즈 후 재열람).
- **시뮬레이터 렌더 확인은 33-16 예약** (D-21, 플랜 명시 이연) — "typecheck passed"가 렌더 확인을 대체하지 않음: 시트 열림 시 일러스트 슬롯 표시 + mode3/미완 동작에서 아무것도 안 보임을 33-16 에서 육안 확인할 것.

## 이 산출물이 틀렸다면 어떻게 알았을까 (D-18)

- 3-다리/역관절 그림 → 전수 육안 열람에서 포착됨이 실증됨: pdshape try3 의 발 3개를 실제로 걸러냄 (1안 기각과 동일 유형).
- 앵커 자세 복제 → 입력 프레임과 나란히 대조로 포착 (10회 걸러냄).
- 틀린 그림 유입 → VERIFIED_ILLUSTRATIONS 맵에 없는 키는 렌더 경로 자체가 없음.

## Known Stubs

없음 — 미완 4동작의 일러스트 부재는 stub 이 아니라 의도된 fail-closed hidden (등록 = 게이트 재수행 후에만).

## Threat Flags

없음 — 신규 네트워크 표면·인증 경로·스키마 변경 0. T-33-49(틀린 그림) = 게이트+미배선으로 완화, T-33-50(렌더 크래시) = 정적 require + null 폴백 + tsc.

## Task Commits

1. **Task 1: 일러스트 6동작 에셋 생성 + 검수** — `6b5546a` (feat)
2. **Task 2: DefectIllustration + 시트 슬롯 배선** — `4a6921e` (feat)

## Next Phase Readiness

- **33-15 (Wave B):** DeductionDetailSheet 추가 표면 작업 시 illustrationSlot 위치(행동 큐 아래) 유지.
- **33-16 (페이즈 게이트):** 시뮬 렌더 확인(위 D-19 예약) + belle 실물 재확인 + OTA 일괄. ④-b 음성 시점 일러스트 동반(VideoCompare voiceCueRecordId 결합)은 이 플랜 밖 — 33-16 재량 입력.
- 미완 4동작 재시도 = 방위 일치 앵커 풀(이번 6장)로 별도 플랜/quick 재량.

## Self-Check: PASSED

- 에셋 6장 + DefectIllustration.tsx 존재 확인, 커밋 2건(6b5546a, 4a6921e) 존재 확인
- typecheck clean, VERIFIED_ILLUSTRATIONS/illustrationSlot/hidden 앵커 grep 확인

---
*Phase: 33-result-trust-recovery*
*Completed: 2026-07-29*

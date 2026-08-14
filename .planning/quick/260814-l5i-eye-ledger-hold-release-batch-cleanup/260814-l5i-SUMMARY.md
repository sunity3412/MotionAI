---
phase: quick-260814-l5i
plan: 01
subsystem: training-data
tags: [flywheel, eye-track, consent-fence, balance-axis, instagram-collection]

requires:
  - phase: quick-260814-j24
    provides: eye 트랙 + 수확기 + 프라이버시 fence (P-1~P-5) + 규모 실측
provides:
  - 미오픈 내부 계정 근거 (sha16 화이트리스트 + 만료 조건 + 명단 밖 보호 회귀 테스트)
  - harvest_eye --readjudicate (판정 필드만 갱신, 관측치·출처 보존)
  - data/eye_maps/ 4파일 (j24 유실분 복원 — 재현 가능성 회복)
  - eye 균등 축 = (관절 x 관측) — 동작 축이 판정 신호를 지우던 것 수리
  - 정은지 IG 신규 4편 (watch 러너 최초 실행)
affects: [Phase 22 학습 코퍼스, 수집 플라이휠, 프라이버시 게이트]

key-decisions:
  - "게이트 제거가 아니라 화이트리스트 — 명단 밖은 기존 게이트 유지가 1급(앱 오픈 후 자동 보호)"
  - "uid 원문을 코드에 두지 않음 (sha256 앞 16자 대조) — P-4 규율 준수"
  - "learningOptIn=false 명시 거부는 자사 계정이라도 불가역 (7-1(b) 최우선 유지)"
  - "눈 샘플 균등 축은 동작이 아니라 (관절 x 관측) — 배우는 대상이 관절 상태이므로"

requirements-completed: [QUICK-260814-L5I]
completed: 2026-08-14
---

# Quick 260814-l5i: 플라이휠 첫 가동 Summary

**기계 판정 한 줄**: belle 판정 2건("정은지 계정만 먼저" / "앱 계정은 그냥 우리거야
아직 앱이 오픈되지도 않음")을 반영해 **수집 러너를 최초 실행**(정은지 IG 신규 4편)
하고 **동의 축 hold 를 해제**(원장 admit 41→100, 불일치 admit 28→95)했으며,
**균등 축 오적용을 수리**(방출 7→35행, 불일치 6→23행)했다.

## 1. 수집 재개 — watch 러너 최초 실행

- 2026-07-14 이후 첫 수집. `collection_batches` 가 빈 배열이었다 = 22-11 이 만든
  러너가 **한 번도 실행된 적 없었음**(오케스트레이터 실측).
- `--only eunji` 로 범위 한정(belle "정은지 계정만 먼저"). 결과 = **신규 4편**
  (정타 4 / reject 28 / skip 기존 28), manifest rows 239 → 243.
- **헛돈 2회 정직 박제**: (1) gallery-dl 미설치 → 크래시, 배치 `watch-260814` 가
  `status:"open"` 으로 잔존. (2) `GEMINI_API_KEY` 를 넘겼으나 코드가 기대하는 이름은
  `GEMINI_KEY_PARAM`(SSM 파라미터명) → 선별기 미초기화로 0건 수집.
  둘 다 고친 3회차가 실제 수집. **잔여 = 빈 배치 2건**(`watch-260814` open /
  `watch-260814-2` collected 0) — 원장이 append-only 라 삭제 대신 이력으로 남김.
- Gemini 선별 중 일부 응답이 JSON 파싱 실패(레닌트 파서도 실패) — 그 건들은
  reject 로 흘렀다. **품질 reject 와 파싱 실패 reject 가 구분되지 않는다**(한계).

## 2. 동의 축 hold 해제 — 게이트는 살렸다

belle 판정으로 P-1/P-3 의 전제(보호할 제3자)가 사라졌다. 그러나 **fence 를 끄지
않았다** — 앱 오픈 후 실제 수강생 업로드가 생기면 게이트가 반드시 살아 있어야 한다.

- `PRELAUNCH_INTERNAL_UID_SHA16` = 오늘 존재가 확인된 자사 계정 **3개만**
  (재분석 러너 / 픽스처 영상 소유 / belle 등록). **uid 원문은 코드에 없다** —
  sha256 앞 16자로만 대조(P-4 규율).
- 명단 밖(`owner=unverified`)은 기존 P-1/P-3 가 그대로 걸린다 → **앱 오픈 후 신규
  계정 자동 보호**. 이 보호가 새지 않는지 회귀 테스트로 못박음
  (`test_unlisted_account_still_held`).
- `learningOptIn=false` 명시 거부는 자사 계정이라도 뒤집지 않는다(7-1(b) 최우선).
- **만료 조건** 코드 주석 박제: 앱이 외부 공개되는 순간 이 근거는 소멸하며 상수를
  비우고 learningOptIn 실측만 남겨야 한다.
- `--readjudicate` 신설: 정책 근거가 바뀌었을 때 원장을 지우지 않고 **판정 필드만**
  (`disposition` / `disposition_reason` / `consent_flag`) 갱신. 관측치·이미지 해시·
  출처는 불변 — append-only 취지(이력 유실 금지)는 지켜진다.

## 3. 부수 발견 2건 (둘 다 수리)

1. **j24 motion 매핑 유실** — 재현 명령이 참조하는 4개 맵 파일이 저장돼 있지
   않아(scratchpad 휘발) 재실행 시 152행이 `motion_unknown` 으로 떨어졌다.
   리포트 부록 A 의 원문을 `backend/training/data/eye_maps/` 4파일로 복원.
   **근거 문자열 포함**(resolve_motion 이 evidence 없는 주입을 거부하므로).
2. **오진단** — 내부 계정 행이 motion 미해결일 때 `side=="user"` 분기에 먼저 걸려
   `customer_anonymize_required`(동의 축)로 보고됐다. 실제 막는 축은 motion 인데
   동의 문제로 읽혔다 → 내부 계정은 motion 축만 남으므로 즉시 `motion_unknown`
   반환하도록 교정. 교정 후 사유 분포가 `motion_unknown` 단일로 정리됨.

## 4. 균등 축 수리 — 이번 사이클 최대 효과

- 증상: 적재 99행인데 방출 13행, **86행이 균등 트림에 소실**.
- 원인 실측: `_balance_media` 는 **동작 축** `max <= 2*min` 인데 eye admit 의 동작별
  최소가 `ref-peter-pan` **2행** → 상한이 4로 고정 → 전 동작이 4행으로 깎임.
- 판단: 눈 샘플이 가르치는 것은 "표시된 관절이 접혔나 폈나"이지 그 장면이 어떤
  동작인지가 아니다. **동작 편중이 아니라 관절·관측 편중이 문제인 트랙**이다.
- 수리: `_balance_eye` 신설 — 축 = `(관절, 관측)`. 균등 규율(max<=2*min · 결정적 ·
  안정 순서 · 오버샘플 0 · dump-all 금지)은 그대로. `_balance_media` 의
  `motion is None` 무조건 통과(균등 우회, j24 P-5 실측)는 **답습하지 않음** —
  축 값 부재도 하나의 버킷으로 함께 센다.
- 효과: **방출 13→35행 / 불일치 9→23행** (사이클 시작 시점 7행·6불일치 대비 5배).
  잔여 트림 64행은 희소 (관절 x 관측) 조합이 상한을 눌러서다 — 코드 문제가 아니라
  커버리지 문제이고, 처방은 수확 범위 확대다.

## 5. 게이트

- pytest **59 failed 기준선 동일 / 4298 passed**(신규 9 포함) · phase22 **389 passed**
- 신규 테스트 9: 내부 계정 admit · 명시 거부 불가역 · motion 미해결 유지 ·
  **명단 밖 hold 유지(회귀 방지선)** · owner_scope fail-closed · 화이트리스트 크기
  고정 · 재판정 필드 한정 · 재판정 기본 off
- S3 쓰기 = 수집분만(승인 범위) · Firestore 쓰기 0 · 산식·채점 무접촉

## 6. 한계 박제

- **잔여 hold 41행** = motion 미해결(P-5). 동의 축이 아니라 커버리지 축이다.
- **균등 트림 64행** 잔존 — 희소 조합이 상한을 누른다.
- **크롭 PNG S3 미업로드** — `--upload --with-eye` 는 여전히 fail-closed 차단.
  학습 실행 전에 크롭 업로드 사이클이 필요하다.
- **빈 배치 2건** 원장 잔존(append-only 라 삭제 불가, 이력으로 남김).
- **Gemini 파싱 실패가 품질 reject 와 구분되지 않음** — 좋은 영상이 파서 버그로
  버려졌을 수 있다(수치 미분리).
- **얼굴 블러 미적용** — belle 판정으로 동의 축은 풀렸으나 가명처리 자체를 한 것은
  아니다. 필요하면 별건으로 요청 가능(행은 재판정으로 되돌릴 수 있음).

## 7. LLM 학습 영향 (필수)

- **Gemini 실호출**: 수집 큐레이션 — 정은지 IG 릴스 후보 60건 판정(File API 업로드
  + verdict). 추론만, 학습 전송 0. verdict 는 `vision_verdicts.json` 캐시에 적재돼
  재호출을 막는다. 이 사이클의 코드 작업 자체는 호출 0.
- **누적 원장**: 눈 원장 141행 중 **100행이 학습 적재 대상**이 됐고 그중 35행이
  실제 JSONL 에 들어갔다. 모델이 배우는 것은 "파이프라인 트랙의 오답을 짚는 능력"
  이며, 위험은 **눈 자체의 오답이 섞이는 것**이다(행 단위 인증은 여전히 없음).

## 다음

1. 크롭 PNG S3 업로드 사이클 (학습 실행의 선행 조건)
2. 실제 SFT 1바퀴 (Qwen3-VL-8B QLoRA — 받은 4090 사양 적합)
3. Pod 실증 (ghs 재렌더 수리의 GPU 확인 — 미착수)
4. ehz 스윕 추천 2건 belle 판정 대기

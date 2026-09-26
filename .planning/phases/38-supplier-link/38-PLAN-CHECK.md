---
phase: 38
checked_at: 2026-09-26
checker: gsd-plan-checker (리뷰 R1-R15 반영본 대상)
status: open
blockers: 3
warnings: 2
---

# Phase 38 — 리뷰 반영 뒤 plan-checker 결과 (미반영)

> 리뷰(`38-REVIEWS.md`, Codex R1-R15)는 전부 플랜에 들어갔다. 38-01 끝 `## Review Response` 표가 기록이고, 검사기가 R 항목 15개를 플랜 본문과 대조해 PASS 했다.
> 그 반영 과정에서 플랜 사이 계약 불일치 3건이 새로 생겼다. 수정 에이전트가 Fable 크레딧 소진(HTTP 429)으로 중단돼 **아직 안 고쳤다** [확인: `13함수` 1건 · `--offline` 0건 · `_dataclass_to_camel_case_dict` 0건].
> **이 3건을 고치기 전에는 `/gsd-execute-phase 38` 금지.** 차단 1 은 정상 등록을 전부 실패시킨다.

## 차단 3

1. **38-07 T2 step 8 · 38-05 T1** — `check_registration` 에 `build_keypoint_report()` 의 `KeypointReport` frozen dataclass(`keypoint_frame.py:113-114`)가 그대로 들어간다. 38-05 의 판정 함수는 전부 `hold_height._arrays` 를 타는데, 이 함수는 Mapping 이 아니면 None 을 낸다(`hold_height.py:63-66`). 결과: 정상 영상도 `no_standing_start`(fail-closed) 또는 TypeError, Success ① 도달 불가.
   - 수정: `report_obj = build_keypoint_report(...)`; None 이면 `_fail_registration(server_error)`; `report = _dataclass_to_camel_case_dict(report_obj)`(`pipeline/app.py:1966`, 기존 11개 `referenceKeypointReport` 와 같은 camelCase 형상 = D-05, 앱은 `kr.axisData` 를 읽는다 `referenceMotions.ts:122`). 같은 dict 를 `check_registration` 과 `set_reference_angles(keypoint_report=report)` 둘 다에 넘기고 step 10 의 asdict 우회는 지운다.
   - 38-05 T1: `check_registration`·`low_confidence_joints`·`standing_start_*` 입력 = keypointReport **dict**(joints/frames/data/confidence, `test_hold_height._report` 형상), Mapping 아니면 TypeError(fail-loud).
   - 38-07 T2 acceptance 추가: happy path 테스트가 `check_registration` 이 dict(joints 12개)로 호출됐음을 단언.
2. **38-06 T1 ↔ 38-09 T1 · 38-14 T2/T4** — `ref-` legacy 가드가 "13함수"로 읽기 함수(`get_reference_registration`·`get_reference_registration_private`)까지 막는다. R10 기준선은 legacy 11개를 그 읽기 함수로 읽으므로 첫 id 에서 ValueError, Success ④ 증거를 못 만든다.
   - 수정: `_require_registration_ref_id` 는 쓰는 함수 9개만 — `create_reference_registration`, `claim_registration`, `set_registration_queued`, `set_registration_expired`, `set_registration_active`, `set_registration_failed`, `set_reference_angles`, `begin_self_check`, `set_reference_self_check`. 읽기 2개와 `list_reference_registrations_by_status` 는 아무 id 허용(38-09/38-14 의 raw legacy 읽기). "13함수" → "9함수". 테스트 추가: `get_reference_registration("ref-kip-up")` 가 raise 하지 않는다.
3. **38-09 T1 ↔ 38-14 T2** — 38-14 T2 게이트가 `snapshot_reference_baseline.py --offline <after.json>` 을 부르는데, 스크립트 주인인 38-09 T1 스펙엔 `--out` 과 `--diff <before> --out <after>` 뿐이다. 38-14 는 그 스크립트를 고칠 권한이 없다.
   - 수정: 38-09 T1 스펙과 `test_snapshot_reference_baseline.py` 에 `--offline <after.json>`(두 파일 비교, Firestore 읽기 0, exit 0/1) 추가. 38-14 는 그대로.

## 경고 2 (오케스트레이터 결정 포함)

1. **과적 task** — 38-04 T1(파일 16개: 설치 · export 최대 2회 · 웹 로그인 분기 · 프로브 3파일 · 이중 서빙 · 스크린샷 · 측정 기록)과 38-09 T1(기준선 보존 + 스냅샷 스크립트/테스트 + 5함수 보존 + 규칙 캡처 + template + SSM + `sam build` + changeset, 12파일). R10 "쓰기 전 기준선" 순서가 커밋 순서로만 지켜진다.
   - 결정: 38-04 T1 → T1a(설치·export·웹 로그인) / T1b(프로브·서빙·측정). 38-09 step 0 → 플랜 첫 번째 읽기 전용 task 로 분리(순서를 task 경계로). task 40 → 42, VALIDATION 행 갱신, wave·의존 변경 없음.
2. **38-12 T1** — `rules.js` 에 `supplierRules.ts` + `supplierForm.ts` 를 이어 붙이면 `./supplierRules` → `./rules.js` 치환 때문에 번들이 자기 자신을 import 하고, "표 밖이면 빌드 실패" 가드는 못 잡는다.
   - 결정: `rules.js` 와 `form.js` 를 따로 내보낸다(`form.js` 가 `./rules.js` 를 import). 남은 specifier 가 번들 자신을 가리키면 빌드 실패.

## 정보 (반영 결정)

- 38-09 T1: legacy id 출처 = `app/src/constants/motionThumbs.ts`(11개). `docs/reference-motions.md` 에만 있는 12번째 `ref-gemini-to-ayesha-combo` 도 Firestore 에 있으면 기준선에 포함, 없으면 absent 로 기록.
- 38-04 T3 · VALIDATION 범례의 `⏭` → ASCII `[skipped-by-decision]`(CLAUDE.md §7 이모지 금지). `★` 는 그대로.
- 그 밖(rtk 접두 없음 · PATTERNS 행 누락 · low_confidence 가 multiple_people 보다 먼저) 변경 없음.

## 다음 세션

`/gsd-plan-phase 38 --reviews` 로 들어가되 **재계획하지 않는다.** 오케스트레이터가 이 파일을 checker_issues 로 넣어 플래너 수정 1회(plan-phase 12단계) → 검사기 1회 → 통과하면 이 파일 `status: resolved` + 커밋·push → `/gsd-execute-phase 38`.
주의: `.planning/config.json` 의 `model_overrides` 가 GSD 에이전트 전부 `fable` 이다. 바꾸지 않으면 에이전트가 Fable 크레딧을 쓴다(belle 결정 대기, 2026-09-26).

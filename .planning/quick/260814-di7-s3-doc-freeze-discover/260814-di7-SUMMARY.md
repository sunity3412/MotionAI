---
phase: quick-260814-di7
plan: 01
subsystem: compare-render / compare-verify / firestore-contract / production-ops
tags: [discovery-freeze, doc-persistence, wiring, production-apply, phase35]
requires: [quick-260814-chd (승인본 재렌더 + 주입 스펙 실증), quick-260814-0p2 (SUPPORT-SURFACE §5)]
provides:
  - result.discovery doc 영속화 규약 (models DISCOVERY_* + _validate_discovery + update_analysis_discovery)
  - compare_render.build_timeline discovery 주입 레이어 (운영 정식 경로)
  - compare_verify H1~H4 discover 정식 지원 (fail-closed)
  - s3keys.build_discover_audio_key canonical 단일 출처
  - 프로덕션 반영 완료 (S3 mp4/mp3 + doc discovery/renderedCompare)
affects: [후속 Pod 실증 사이클, 발굴 일반화 스윕]
key-files:
  created:
    - backend/tests/phase35/test_discovery_freeze.py
    - .planning/quick/260814-di7-s3-doc-freeze-discover/wire_discover.py
    - .planning/quick/260814-di7-s3-doc-freeze-discover/evidence/{wire_verdict,production_log,live_verdict}.json
  modified:
    - backend/shared/python/sunity_shared/{models,s3keys,firestore_admin}.py
    - backend/shared/python/sunity_shared/analysis/{compare_render,compare_verify}.py
    - docs/contract.md (§12.10 신설 + §12.9 :discover 틱 규칙)
decisions:
  - "D-di7-04 이행: _H2_UT_DISPLACING_SRC 튜플 불변 — discover 는 H2 자체 분기 fail-closed (SUPPORT-SURFACE §5-2 튜플안 대체, 유닛으로 핀)"
  - "D-di7-05 이행: doc renderedCompare.freezes discover 항목 rid = 'r04:discover' (앱 무접촉)"
metrics:
  duration: 20분
  completed: 2026-08-14T01:21Z
  commits: 4 (59c1fa6a test / 3a268d45 feat / 4150e07a wire / 6a70af60 apply)
---

# quick-260814-di7: 발굴 채택 반영 사이클 — doc 영속화 + 정식 경로 승격 + 프로덕션 반영 Summary

**기계 판정 한 줄**: 무수정 compare_verify ALL PASS (면제 monkeypatch 0) + 배선/live 재렌더 compose 사슬 == chd 승인본 (baseline 2126 / injected 2461 프레임 전건) + 프로덕션 반영 4건 실행 로그 박제 (mp4 md5 77cdcd43 왕복 재확인) — check-wire / check-apply 둘 다 exit 0.

## 성립한 것

1. **doc 영속화 규약** (`result.discovery`): models `DISCOVERY_KEYS/ITEM_KEYS/PAIR_SRC` + `_validate_discovery`(키 화이트리스트·enum·prefix/suffix·mp3Key 중복 거부·중첩 배열 거부) + `update_analysis_discovery`(단일 field-path 통째 교체) + `build_discover_audio_key` canonical 단일 출처 + contract.md §12.10 (서버 전용/앱 미독 — TS 무변경).
2. **주입 레이어 승격**: `build_timeline` record 루프 뒤 discovery items 순회 — basename(mp3Key) 조인, 부재 = `discover_no_mp3` 회계 (fail-closed 예외 0), rt 경계 = record 경로와 같은 `REF_BOUNDARY_PIN_S`, knee 관절만 몸-폴 라인 시도(성립 시 markers 소유권 이양), `[discover]` 실행 로그. chd `_install_injection` 사본 delta 가 더 이상 불필요.
3. **verify discover 정식 지원**: `_discovery_item_for` 단일 매칭 헬퍼(rid + |Δut| 최소 & <=0.2s)를 H2/H3/H4 가 공유. H2 는 rec-부재 guard 앞 자체 분기 — doc discovery 에 없는 순간 = FAIL (blanket 면제 없음, `_H2_UT_DISPLACING_SRC` 튜플 불변 유닛 핀). H3 expected = doc 영속화 원문, H4 = mp3Key results/ 조인, H1 eligible 에 discovery rid 합류(신규 rid 발굴 미래 케이스 게이트).
4. **배선 재현 게이트** (wire_verdict.json): 베이스라인 사슬 == chd `frames_md5_baseline` (discovery 부재 무회귀의 실렌더 증명) / 주입 사슬 == chd `frames_md5_injected` / report freeze 6건 값 == chd 정본 (voiceStartOutS 5.33/15.67/29.93/**42.07**/54.17/69.0) / 무수정 verify ALL PASS / 음성 게이트 = discovery userSec +0.5s 비틀기 → `H2 순간 r04[discover]` FAIL 정확 1건 (H3/H4 discover 도 같이 FAIL — 공유 매칭 헬퍼의 fail-closed 정상 동작, verdict 에 전문 박제).
5. **프로덕션 반영** (production_log.json, 쓰기 4건 전 로그): ① 승인본 mp4(`/Users/Shared/…/재렌더영상_신규정지포함.mp4`, md5 사전 assert) → `results/{uid}/{aid}/compare_v1.mp4` (doc 현행 key == canonical exact assert 후 같은 키 덮어쓰기) + S3 GET md5 재확인 ② discover mp3 → `discover_audio_r04_left_knee.mp3` canonical 키 + 재확인 ③ `update_analysis_discovery` (Task 2 와 단일 소스 payload) ④ `update_analysis_rendered_compare` freezes 6건 (discover rid `r04:discover`).
6. **live 검증** (live_verdict.json): Firestore 재fetch doc == 반영 payload → 그 live doc + **S3 방금 쓴 키에서 GET 한 mp3** 로 재렌더 — 사슬 == chd injected + 무수정 verify ALL PASS + `[discover]` 로그. 영속화 필드 → 렌더 구동의 왕복 증명 완결.
7. **push 완료**: origin/main..HEAD 0 (후속 Pod 실증 전제 충족).

## 제약 준수

- **채점 무접촉**: 산식 5파일(deduction_engine/dimensions/kismam/motiondtw/assemble) 커밋 범위 diff 빈 출력 (GATES-OK).
- **pytest 기준선 무회귀**: 59 failed IDENTICAL / 4205 passed (신규 38 전부 PASS).
- **일반 경로**: backend diff 에 pdshape/p34fresh/12.8667/uid 리터럴 0 (grep 게이트 GATES-OK) — belle "다른 영상들도 이런식으로" 재사용 가능.
- **이모지 0 · heredoc 0** (파일 생성 = Write 도구만) · 렌더 결정론 규율 = chd `_render_once` 형식 미러 (render 캐시 포함 wif_fresh 통째 복사로 chd 렌더 조건 재현).
- **app.py / app/ 무접촉** (D-di7-03 — coachAudio 도 무접촉).

## LLM 학습 영향

이 사이클 LLM 추론 호출 **0** (Gemini 0 / Polly 0 — 렌더·업로드·doc 쓰기만). 학습 전송 0. mp3 는 chd repo 고정본 재사용 (재합성 없음).

## Deviations from Plan

None — plan 대로 실행. 참고 기록 1건: 음성 게이트(+0.5s 비틀기)에서 H2 외에 H3/H4 discover 도 함께 FAIL (단일 매칭 헬퍼 공유 설계의 귀결 — plan 의 "H2 FAIL 정확 발생" 게이트는 H2 FAIL 정확 1건으로 판정, 전체 FAIL 라인은 wire_verdict `perturbFailLines` 에 정직 박제).

## Self-Check: PASSED

- 4 커밋 존재 (59c1fa6a / 3a268d45 / 4150e07a / 6a70af60), push 완료 (origin delta 0)
- evidence 3종 (wire_verdict / production_log / live_verdict) 존재 + check-wire/check-apply exit 0
- 신규 테스트 파일 존재, backend/ working tree clean

## 다음 1단계

**Pod 실증 사이클**: 새 Pod 재진입(current-pod 메모리 6단계 — SSM/Lambda URL 재동기) + 운영 경로(`_run_deferred_compare_render`)에서 discovery 재현 + **discovery mp3 회수 배선** (Pod 렌더 스테이지가 S3 discover mp3 를 audio_dir 로 내려받는 경로 — 이번 사이클 의제 밖, D-di7-03 명기대로 그때 재검). 이후 **발굴 일반화 스윕** (승인 5동작 — belle "pdshape 만?" 답) 대기.

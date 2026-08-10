---
id: 260810-e4v
title: fps 실효 rate 단일 출처 교정 — U1·U2·U3 코드 완료, 백필·U4 대기
date: 2026-08-10
status: 코드 3단위 완료 · 백필(점수 이동 스위치) belle 확인 대기
commits:
  - b0dbe3c5 U1 실효 rate 산출·기록 (산출 배열 무접촉)
  - cfb3a447 U2 표시 앵커 초를 실효 rate 로 (점수 무접촉)
  - c0b7488b U3 기준 실측 rate 읽기 경로 + 백필 스크립트(미실행)
---

# 260810-e4v 요약

근거 = quick 260810-cbt 실측 · belle 08-10 결정("전역 + 점수표 게이트, 점수 변동은
정당하면 괜찮다").

## 무엇이 들어갔나

| 단위 | 무엇 | 점수 | 게이트 |
|---|---|---|---|
| **U1** | `effective_fps(src_fps,target)` + `extract()` 가 **경로별** 실효 rate 기록 | 무접촉 | 신규 13 pass · 산출 배열 불변 assert |
| **U2** | `_pipeline_frame_fps(video_path)` · `_moment_video_sec()` → `atVideoSec` 가 실효 rate 로 | **불변**(tally 종료 후 각인) | 신규 7 pass · 산식 5파일 diff 0 |
| **U3** | `_reference_angles_fps(ref)` — `anglesRealFps` 우선, 없으면 라벨 fail-open | 백필 전까지 **byte-동일** | 신규 11 pass |

전 구간 pytest **59 failed IDENTICAL(기준선) / 4096 passed**. 채점 산식 5파일
(`deduction_engine`·`dimensions`·`kismam`·**`motiondtw`**·`assemble`) diff 0 —
08-08 게이트가 목록에서 빠뜨렸던 `motiondtw` 를 명시 포함해 확인했다.

## 새로 알게 된 것

- **기준 11건 전수** 실제 rate = 14.88~15.00fps, 저장 라벨은 전부 18.0
  (아침 260810-cbt 는 5건 표본이었다). 마진 `ceil(0.5s×fps)` 가 전 동작에서 9 → 8.
- **경로별 기록이 필요한 이유**가 실측으로 확인됨: 한 분석에서 사용자·기준·이전 영상을
  같은 싱글턴으로 추출하고, 사용자는 target 9(→step 3), 기준 트랙은 target 18(→step 2)
  이라 rate 가 다르다. 단일 속성이면 나중 추출이 앞 기록을 덮는다.
- ★**fail-closed 게이트가 내 유도식을 잡았다** — 백필 교차검증을 `anglesFrames/길이` 로
  했더니 **강제 마지막 프레임 1장**(12-deferred §12-B) 때문에 전 건이 조금 크고, 짧은
  클립(peter-pan 8.6s)에서 1.56% 로 불일치 판정됐다. `(n−1)/길이` 로 교정하고 기록값은
  원리 정본(`src_fps/step`)으로 → 11/11 통과. 게이트가 없었으면 편향된 값을 심었다.

## 미완 (박제)

- **백필 미실행** — `--dry-run` 만 돌렸다(Firestore 쓰기 0). 이 실행이 **점수가 움직이는
  스위치**다. 로컬 근사 점수표(260810-cbt: 편차 이동 최대 0.150/0.571/0.597/0.290/0.294도)
  는 있고, **허용오차 20도 경계에 걸린 record 의 감점 유무 뒤집힘은 아직 안 쟀다.**
- **U4 미착수** — `fault_zoom:852` 4/3 보정 제거 + 승인본 카드 대조(belle 승인분),
  교정으로 표시 미성립이 되는 카드를 링·맥락으로 남기기(belle 승인분).
- **실 파이프라인 미검증** — U2 의 앵커 이동, U3 의 점수 이동 모두 Pod 재분석이 확정
  수단이다. 지금 것은 단위 테스트 + 로컬 근사다.
- U2 의 `pose_fps` 는 mode1/mode3 공용 call site 1곳에만 배선했다. `dtw_ref_fps`
  (mode3 fault_zoom)·Gemini 프롬프트 초 라벨은 여전히 `target_fps` 를 쓴다 — 각각
  표시·프롬프트 문자열이라 점수 무영향이지만 남은 자리로 기록한다.

## LLM 학습 영향

코드 자체는 없음(채점 신호 무접촉). 단 백필 후에는 **표시 순간과 기준 경계 마진이 바뀌므로**
Phase 22 교사 라벨이 프레임·초를 인용하는 경우 재라벨 대상이 된다 — 인용 여부 미확인(별건).

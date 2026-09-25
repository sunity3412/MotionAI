---
quick_id: 260925-mvh
slug: sealed-test-power-spin-climb
date: 2026-09-25
status: complete
code_changes: 0
---

# 봉인 시험지 1회 — power-spin·climb 실수 — 결과 0/2

> 순서: belle 정답 봉인 커밋(08fa54c0, 16:28) → 그 뒤 09-24 Pod 카드(Firestore, 6d70f4b1) 와 대조.
> 이 두 편으로 이 세션에 코드 변경 0 (약속대로). 대상 doc 은 SEALED.md 에.

## 채점표

| 동작 | belle 정답 (봉인) | 09-24 카드가 말한 것 | 판정 |
|---|---|---|---|
| climb 실수 | 왼팔이 접힌 채로 돈다 | 오른고관절 −20 · 왼무릎 −20 · 오른무릎 −20 · 오른팔꿈치 −2.8. **왼팔 기록 0** | × |
| power-spin 실수 | 도는 위치의 높이가 다르다 · 다리 벌림이 다르다 | 무릎 덜 펴짐(leg_extension −20) · 왼어깨 −7.7 · 오른어깨 −4.7. **높이 0 · 벌림 0** | × (무릎은 인접, 같은 말 아님) |

**2편 중 0편 맞게 말함.** kip-up(09-24 ○)까지 합치면 실수 3편 중 1편 — 그 1편은 belle 판독으로 고친 뒤의 것.

## 관측 — 카드 뒤에 무엇이 있었나 (`[확인]` = 09-24 doc·로그·코드 실측)

- `[확인: doc visionVeto]` **climb: Gemini 는 belle 과 같은 것을 봤다.** primaryFault =
  *"왼팔의 자세와 그립 방식이 기준과 완전히 다름 (기준은 아래로 뻗어 잡으나, 학생은 굽혀서 안고 있음)"*,
  faultJoints=[left_hand, left_shoulder, right_shoulder]. 그런데 collectionStatus=`no_fault` · severity=`none` ·
  fallback=`gemini_silent` → 감점·카드 0. **보고 말 안 했다.**
- `[확인: 로그 09-24 14:43]` climb 높이 축: hip −0.203 · grip +0.312 · hipBelowHand −0.501 (정타 ≈0). 방향은 "팔이 접혀 몸이 손 아래로 처짐"과 맞을 수 있다 — `[해석 미정]`.
- `[확인: 로그 09-24 14:39]` **power-spin 높이는 잰 값이 있다** — grip −0.646 · hip −0.184 · hipBelowHand +0.393 (정타 grip −0.075). "도는 위치가 낮다"와 방향 일치 `[belle 미확인]`. 카드 배선(`measuredVariants`)은 kip-up × 왼어깨 한 칸뿐이라 화면 0.
- `[확인: 코드]` **power-spin 다리 벌림 축은 09-05 와 같다.** `required_split_deg=None` 4곳(gemini_technique_recognizer.py 318·347·460·527), 기하 게이트 사문(app.py 2935·3114·8839). Gemini visionVeto primaryFault='없음'. → 벌림은 **잴 수 없는 상태 그대로.**
- `[확인: 메모리]` belle 은 09-05 에 이미 *"양 다리 벌림이 가장 문제인데 그거는 안잡고 어깨를 잡아 놨네"* 라고 했다. 오늘 *"이걸 몇번째 말하는거여"* = 20일간 카드가 안 바뀌었다는 관측. 맞다.
- `[확인]` 카드는 세 편 전부 "각도가 기준 자세와 차이가 있어요" 문형(climb 4/4, power-spin 2/3). belle 이 보는 원인 문장은 kip-up 한 칸에만 있다.

## 진단 후보 (재검증 대상, 승계 금지)
- Gemini 가 결함을 문장으로 적고도 severity=none 으로 닫는 경로 — 어디서 none 이 되는지 미추적.
- 높이 카드 배선을 kip-up 전용에서 동작 일반으로 — 잰 값은 5동작 중 3동작에 있다(i38).
- 벌림 게이트 — 09-05 수리 방향 그대로 미착수.

## 이 두 편의 신분
연습 문제로 옮김(정답 공개됨). 다음 봉인 시험지 = 정은지 추가 영상.

---
status: complete
quick_id: 260720-hn8
date: 2026-07-20
---

# 260720-hn8: 영상 선택 실패 알림창 전환 + iCloud 폴백

> 재구성 노트: executor 가 worktree 에 쓴 SUMMARY.md 가 커밋 전에 worktree 강제 삭제로 유실되어(오케스트레이터 절차 오류 — quick 워크플로우의 "docs 는 커밋하지 말 것" 지시와 worktree force-remove 가 충돌), executor 최종 보고를 근거로 오케스트레이터가 재작성함. 커밋 해시·검증 수치는 실측 확인함.

## 배경

belle 실기기(TestFlight)에서 **앨범은 열리는데 영상을 고르는 순간** "앨범을 여는 중 문제가 발생했어요" 가 고정 표시되고 진행 불가. 사진 권한은 "모든 사진 허용" 정상. 같은 영상이 이전엔 동작했고 `analyze.tsx` 는 phase 26 이후 변경 0 → 앱 코드 회귀가 아니라 기기/영상 상태 변화로 판단.

belle 요구: **"분석조차 안 되면 안 되니까 해결방안을 알려줘야지 고객들에게."** 목적은 에러 표시가 아니라 사용자가 다음에 뭘 하면 되는지 아는 것.

## 커밋

| 커밋 | 내용 |
| --- | --- |
| `1025f79` | (선행 핫픽스) `Current` 실패 시 `Automatic` 재시도 + `errText()` + try 범위 분리 |
| `53849a8` | `pickerFailure.ts` — 실패 원인 → 해결안내 순수 매핑 모듈 |
| `57de295` | `PickErrorSheet` 바텀시트 (→ `f329e99` 에서 교체) |
| `3aa84ac` | `analyze.tsx` 배선 — 인라인 `setError`/`permissionBlocked` 제거 |
| `f329e99` | **바텀시트 → Figma 카드형 정정** |

## 산출물

- `app/src/lib/pickerFailure.ts` — `describePickFailure(kind, detail?)` → `{title, lines, primaryLabel, primaryAction}`. 의존성 0 순수 함수. `never` exhaustiveness 가드로 kind 추가 시 typecheck 실패.
- `app/src/lib/pickerFailure.test.ts` — `node --test` 7 케이스. Figma 확정 문구를 문자열 동일성으로 고정.
- `app/src/components/PickErrorDialog.tsx` — 중앙 카드형 알림창 (Figma node 1:499 `Group 53`).
- `app/src/app/(tabs)/analyze.tsx` — 알림창 배선.
- `app/src/theme/` — 신규 토큰 `colors.dialogBg`/`dialogMutedText`, `radius.dialog`/`dialogButton`, `layout.dialog*`, `typography.dialog*`.

## Figma 확정 문구 (원문 그대로, 창작 0)

| 실패 | 제목 | 본문 |
| --- | --- | --- |
| 용량 초과 | 용량이 너무 커요 | 100MB 이하 영상만 업로드 할 수 있어요. / 영상을 잘라서 다시 시도해주세요. |
| 형식 미지원 | 지원할 수 없는 파일이에요 | mp4, mov형식의 영상만 / 업로드 가능해요. |

`mp4, mov형식의` 붙임(공백 없음)도 원문 유지. Figma 에 없는 실패(picker 실패·권한 거부·처리 실패)는 같은 양식으로 확장.

## 검증 (오케스트레이터 실측)

- `npm run typecheck` — 무오류
- `node --test src/lib/pickerFailure.test.ts` — **7/7 pass**
- `package.json`/`package-lock.json` diff — **0** (신규 의존성 0)
- `PickErrorSheet` 잔존 참조 — 0
- 컴포넌트 하드코딩 hex — 0
- 음수 letterSpacing 유입 — 0

## 편차

1. **★ Figma 음수 letterSpacing(−0.72/−0.52/−0.6) 미적용 — 오케스트레이터 지시를 의도적으로 거부.** `typography.ts` 1~6행 박제: *"letterSpacing = 박제 (2026-06-06 belle): iOS 26+ 의 native style 회귀로 음수 letterSpacing 이 SIGABRT (TestFlight 빌드 9 분석하기 버튼 튕김 root cause)."* 지시대로 넣었다면 이미 규명·차단된 크래시를 되살리는 것. `track()` 경유로 0 유지, fontSize·lineHeight 만 실측 반영. **시각차가 문제되면 `Platform.Version` 분기 재검토 — belle 판단 필요.**
2. 버튼 inset 흰색 그림자(`inset 0 0 5.276px rgba(255,255,255,0.25)`) 생략 — RN 미지원.
3. 버튼 폭 98.6/153.7 고정값 대신 비율(flex 1:1.56) — 소형 기기 오버플로 방지.
4. 초기 지침이 bottom-sheet 였으나 belle 가 Figma 실물(node 1:499)을 지목해 카드형으로 정정.

## 원인 분석 — 왜 "Figma 에 디자인 없음" 이라고 잘못 결론냈나

최초 검색이 **노드 이름 기반**이었고, 해당 프레임이 `Group 53`/`Rectangle 271` 같은 자동 생성명이라 의미가 텍스트 노드에만 존재해 걸리지 않았다. 파일에 없었던 게 아니라 검색 방법이 이 파일에 맞지 않았다. 교훈은 [[figma-search-by-text-not-node-name]] 로 메모리 적립.

## 미해결

**근본 원인(픽 실패 자체)은 미해결.** iCloud 오프로드는 정황 증거(에어드랍 로컬 파일 성공 / 앨범 원본 실패)뿐인 **가설**이다. 그래서 알림창이 실제 picker 오류 문자열을 회색 영역에 선택 가능하게 표시한다 — belle 가 그 문자열을 읽어주는 것이 가설을 확정하거나 폐기하는 유일한 증거다.

## HUMAN-UAT (배치 검토 대상)

1. 앨범에서 iCloud 오프로드된 영상 선택 → 알림창이 뜨고 해결 안내가 읽히는가
2. **★ 알림창 하단 회색 오류 문자열 캡처** — iCloud 가설 확정/폐기의 증거
3. 100MB 초과 / mp4·mov 외 형식 → Figma 문구대로 표시되는가
4. 권한 거부 → [설정 열기] 버튼이 실제로 설정 앱을 여는가
5. 카톡 압축 경고·저화질 경고 모달과 새 알림창이 동시에 뜨지 않는가
6. iOS 26+ 기기에서 알림창 표시 시 크래시 없는가 (letterSpacing 회귀 확인)

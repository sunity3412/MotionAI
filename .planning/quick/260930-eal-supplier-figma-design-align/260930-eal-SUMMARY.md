---
phase: quick-260930-eal
plan: 01
status: complete
subsystem: app/supplier (Phase 38 공급자 페이지 웹 라우트)
tags: [supplier, figma-282-506, 38-DESIGN, ui]
requires: [38-10, 38-11]
provides: [공급자 3 라우트 + 공용 프리미티브가 38-DESIGN.md 시안 값으로]
affects: [38-13 실기기 검증 — 이제 시안 기준 화면을 본다]
tech-stack:
  added: []
  patterns: [selfCheckView score/body 분리, absolute BottomBar + onHeight 여백]
key-files:
  created: []
  modified:
    - app/src/theme/colors.ts
    - app/src/constants/supplierCopy.ts
    - app/src/constants/supplierCopy.test.ts
    - app/src/lib/supplierRules.ts
    - app/src/lib/supplierRules.test.ts
    - app/src/components/SupplierUi.tsx
    - app/src/app/supplier/index.tsx
    - app/src/app/supplier/upload.tsx
    - app/src/app/supplier/guide.tsx
decisions:
  - "A-3c 재현성 카드: 점수는 오른쪽 `{score}점` 한 자리에만, 낮음 본문 = row.self.lowBody '낮아요. 다시 찍어 주세요.' (row.self.low 는 소비처 0 이 되어 삭제)"
  - "신규 색 토큰 4개 + 그라디언트 1개(supplierPinkBg · dividerSoft · barGlass · barSolid · supplierPhotoShade) — 화면 색 리터럴 0 을 지키려고"
  - "30pt 제목 −2% 자간은 웹에서만(iOS 26+ 음수 자간 SIGABRT)"
metrics:
  duration: "약 45분"
  completed: 2026-09-30
  tasks: 3
  files: 9
---

# Quick 260930-eal: 공급자 페이지를 Figma 282:506 시안(38-DESIGN.md)에 맞춤 Summary

`/supplier` 세 화면과 공용 부품을 38-DESIGN.md 값으로 바꿨다. 로그인 칩·Google 54 버튼·헤더 복귀·진행 점·코드 준비 중 카드·2칸 진행 막대·번호 체크 카드·유리 하단 바·A-5 요약 카드·A-3c 재현성 카드·가이드 번호 카드와 연분홍 상자가 들어갔다.

## 커밋

| Task | 내용 | 커밋 |
|---|---|---|
| 1 | 문구 키 · 규칙 함수 · 색 토큰 (테스트 먼저) | `25a8edfc` |
| 2 | 공용 부품(공통·홈·상세) + index.tsx A-1/A-2/A-3/A-3b/A-3c | `8e9ad01f` |
| 3 | 폼 부품 + upload.tsx STEP 01/02 · A-5 + guide.tsx A-6 | `d1651a76` |

## 관측 (잰 값·명령 출력 — 승계해도 되는 것)

- [확인] RED: 테스트를 먼저 고친 뒤 실행 → `SyntaxError: The requested module './supplierRules.ts' does not provide an export named 'selfCheckView'`, supplierCopy.test 는 `✖ 38-DESIGN.md 새/바뀐 문구 키` 외 2건 실패.
- [확인] `npm run typecheck` exit 0 (HEAD `d1651a76`).
- [확인] node 테스트 6파일 → tests 66 · pass 66 · fail 0. 전에는 65. 새 테스트 1건('38-DESIGN.md 새/바뀐 문구 키')이 더해졌다.
- [확인] `git diff --stat HEAD~3 HEAD` = 계획한 9파일뿐이다. docs/supplier-guide.md · analysis.ts · backend 변경 0. 삭제된 파일 0.
- [확인] `CI=1 npx expo export --platform web` exit 0. 번들 `entry-768b3ad….js` 에서 `backdropFilter` 2회 검출. `backdrop-filter` 는 번들에 없다. react-native-web 이 `modules/prefixStyles/static.js` 에서 이 속성을 처리한다. 실제 DOM 에 blur 가 붙는지는 [미확인]이다. STEP 화면은 로그인 뒤에만 열린다.
- [확인] 색 리터럴(주석 밖 `#xxxxxx`·`rgba(`)은 supplier 3파일 + SupplierUi.tsx 에서 0건이다.
- [확인] 한국어 리터럴(주석 밖 한글)은 supplier 3파일 + SupplierUi.tsx 에서 0건이다. node 스크립트 `scratchpad/ko-check.mjs` 로 확인했다.
- [확인] 이모지는 supplier 화면·SupplierUi·supplierCopy 에서 0건이다.
- [확인] `row.self.low` · `row.self.ok` · `home.codePending` · `form.uploading.progress` · `selfCheckLine` · `showWordmark` · `moreLabel` · `showChevron` 이 app/src 와 docs 에서 0건이다(grep). 테스트는 옛 키가 없는지도 잠근다.

### 스크린샷 (휘발 scratchpad: `/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/ef3648dc-db87-4310-a2aa-b555fa84c027/scratchpad/`)

- `eal-a1.png` (390x844, `/supplier`) [확인 눈]: 순서는 워드마크(브랜드) → 칩 `강사·선수 전용` → 제목 → 본문 → Google 버튼 → 흐린 힌트 → 아래 `빌드 dev` 이다. Google 버튼은 G 아이콘과 라벨이 가운데에 묶여 있고, 높이는 눈대중 ≈54 다. 화면 글자도 CDP 로 뽑아 같은 문구임을 확인했다.
  - [불일치·근사] 워드마크는 y≈40 에 있다. 웹에는 safe-area 가 없어서 시안 y≈97(= 59 + 38)보다 위다.
  - [불일치 가능] 메인 세션의 시안 렌더(`section.png`·`a1.png`)에서는 워드마크 → 칩 간격이 48 보다 좁아 보인다. 해상도가 낮아 값은 [미확인]이다. 아래 '재량값' 참조.
- `eal-a6.png` (390x3400, `/supplier/guide`) [확인 눈]: `01`~`07` 브랜드색 번호 → 제목 → 회색 점 항목, 카드 간격이 좁아졌다(16). ① 끝에 정사각 사진 2장과 캡션이 있다. ④ 끝에 연분홍 상자(알림 아이콘 + `등록이 안 되는 4가지` + `· ` 줄 4개)가 있다.
- `eal-a6-s5.png` (390x844, `?section=s5`) [확인 눈]: `05 권리와 동의` 카드가 화면 맨 위에 온다. 38-11 때는 화면 중간이었다.
- 서버 방식 편차: `npx expo serve` 는 `/supplier` 에 404 를 돌려줬다(SPA export, 폴백 없음, 스크린샷에 `Not Found`). 그래서 38-11 처럼 파이썬 SPA 서버로 :8082 를 띄웠다. Chrome `--screenshot` + `--virtual-time-budget` 로 찍으면 A-1 이 흰 화면이었다(boot 단계에서 멈춤). 그래서 Chrome `--remote-debugging-port` + Node 내장 WebSocket(CDP)으로 8초를 실제로 기다린 뒤 찍었다. 패키지 설치 0.
- [확인] 끝난 뒤 `lsof -i :8082` 와 `lsof -i :9333` 둘 다 빈 결과다.

### 그리지 못한 화면

- [미확인 — 38-13 실기기에서 belle 확인] A-2 권한 없음 · A-3 홈(동작 있음/빈 상태/Pod 꺼짐 알약/전체보기) · 내 코드 카드(사진 음영 · 코드 준비 중) · A-3b 실패 · 만료 · A-3c 등록 완료 · STEP 01 · STEP 02 · 유리 하단 바 · A-5 올리는 중 · 다이얼로그. 모두 로그인과 화이트리스트가 필요하다. 이 실행에서는 한 번도 그려 보지 않았다. 타입검사와 grep 게이트만 통과했다. "시각 검증 완료" 가 아니다.

## 38-DESIGN.md 절별 반영

| 절 | 반영 파일 | 표기 |
|---|---|---|
| §0 토큰(보조 15·흐린 보조·캡션 13·STEP 15·번호 13·칩·구분선 #EDEDED·연분홍·자간·하단 바 재질) | SupplierUi.tsx `text`/`s`/`f`, colors.ts | [확인 코드] · 가이드 번호·연분홍·보조 15 [확인 눈] |
| A-1 로그인 전 | index.tsx, SupplierUi(BrandMark·Chip·GoogleButton) | [확인 눈] |
| A-2 권한 없음 | index.tsx | [미확인] |
| A-3 헤더·시트·내 동작 카드·행 | index.tsx, SupplierUi(GradientHeader·SectionHeader·PillCta·ListRow) | [미확인] |
| A-3 빈 상태 | index.tsx(StepCard 단독), SupplierUi | [미확인] |
| A-3 내 코드 | SupplierUi(CodeCard), index.tsx | [미확인] |
| A-4 STEP 01 | upload.tsx, SupplierUi(StepHeader·CheckCard·TextInput54·SelectField·CheckboxRow·VideoPreview·BottomBar) | [미확인] |
| A-4 STEP 02 | upload.tsx, SupplierUi(AllAgreeBox·CheckboxRow inset·WithdrawNote) | [미확인] |
| 검증 다이얼로그 | 변경 없음(PickErrorDialog 그대로) | [확인 코드] |
| A-5 올리는 중 | upload.tsx, SupplierUi(UploadSummary·VideoThumb·ProgressBar) | [미확인] |
| A-3b 실패 상세 | SupplierUi(FailurePanel·TipCard) | [미확인] |
| A-3c 등록 완료 | SupplierUi(DonePanel), index.tsx, supplierRules.selfCheckView | [확인 코드 — 테스트] · 화면 [미확인] |
| A-6 가이드 | guide.tsx | [확인 눈] |
| 새/바뀐 문구 키 요약 | supplierCopy.ts | [확인 — 테스트 잠금] |

## 재량값·근사값 (belle 확인 대상)

- A-1 워드마크 → 칩 48: 시안에 y 값이 없어 플랜 값을 따랐다. 시안 렌더에서는 더 좁아 보인다[미확인]. checking·A-2 의 워드마크 위 여백 40 은 A-1 과 맞춘 재량값이다.
- A-3 `전체보기`: 헤더 오른쪽 자리를 `{n}개` 가 가져가서 목록 아래 가운데 링크로 옮겼다.
- `{n}개` 는 목록을 불러오는 중이거나 오류일 때 숨긴다.
- 헤더 SHEET_OVERLAP 84(시안 헤더 ≈300, 시트 216 에서 역산). 헤더 위 여백은 insets.top + 16 이다.
- A-5 위 여백 60 = 48 + 12. 시안 y≈120 = 59 + 60 근사다.
- StepCard 점선: RN `borderStyle: 'dashed'` 는 dash 6/4 길이를 제어하지 못한다 [근사].
- 콤보 체크 행: 시안은 체크박스 → 8 → `[선택]` → 8 → 라벨이다. 코드는 동의 행과 같은 부품(체크박스 → 10 → 한 문단)을 쓴다. 차이는 2 [근사].
- 문구 키 4개를 추가했다(`form.uploading.summaryTitle/summaryMeta/pct`, `row.self.scoreText`). 38-DESIGN 키 요약에는 없다. 화면 파일에 ` · `·`점`·`%` 리터럴을 두지 않으려는 것이다. `form.sec1.guideLink` 는 A-4 본문의 '자세한 가이드' 를 따랐다.
- 색 토큰은 38-DESIGN 이 #FFF4F2 하나만 적었지만 #EDEDED · 흰 86/96% · 사진 음영 0.55 도 넣었다(리터럴 금지).
- A-2 `등록 확인하기` 라벨은 확인 중에도 같다. 확인 중·여전히 없음 문구는 아래 힌트 자리에 뜬다(38-DESIGN A-2). 38-10 에서는 버튼 라벨이 바뀌었다.
- A-2 `stillNo` 는 38-10 의 틸 색 대신 흐린 보조 색으로 바뀌었다(힌트 자리).

## Deviations from Plan

### Auto-fixed Issues

**1. [오케스트레이터 결정 6] A-3c 낮음 분기에서 점수가 두 번 보이던 것**
- 플랜 behavior 의 low body 는 '본인 재현성 61점 · 낮아요. 다시 찍어 주세요' 였다. 이대로면 카드 오른쪽 `61점` 과 본문 `61점` 이 겹친다.
- 수정: `row.self.lowBody = '낮아요. 다시 찍어 주세요.'` 를 추가하고 selfCheckView 의 low body 로 썼다. `row.self.low` 는 소비처가 selfCheckLine(삭제) 하나뿐이었다[grep]. 그래서 키를 지우고 테스트 단언을 lowBody 로 바꿨다. 새 테스트는 다섯 분기 모두 본문에 `\d+점` 이 없음을 잠근다. 홈 행 부제 `row.status.selfLow` 는 그대로다.
- 커밋: `25a8edfc`, `8e9ad01f`

**2. [Rule 3 - Blocking] 스크린샷 서버·캡처 방식**
- `npx expo serve` 가 SPA 딥 링크에 404 를 냈다. headless `--screenshot` 은 A-1 을 흰 화면으로 찍었다.
- 파이썬 SPA 서버와 CDP 캡처로 바꿨다(scratchpad 스크립트 `spa.py`·`cdp-shot.mjs`, 설치 0). 코드 변경은 없다.

**3. [계획 세부] BottomBar 웹 흐림은 `backdropFilter` 만 붙였다**
- `WebkitBackdropFilter` 는 따로 넣지 않았다. react-native-web 의 prefixStyles 가 `backdropFilter` 를 알고 접두어를 붙인다[확인: node_modules 소스 grep]. 실제 DOM 적용은 [미확인].

## 진단 (재검증 대상 — 승계 전에 확인할 것)

- A-1 흰 화면(virtual-time 캡처)의 원인은 Firebase 인증 복원이 가상 시간 안에 끝나지 않아 `boot` 에 머문 것으로 추정한다[미확인]. 실제 시간 8초 대기로는 A-1 이 떴다.
- 네이티브에서 `barSolid`(흰 96%) 바가 마지막 입력 칸을 가리지 않는지는 onHeight 여백 계산에 달려 있다. 웹·앱 모두 [미확인].

## Known Stubs

없음. 새로 생긴 빈 값·자리표시 문구는 없다. ListRow 썸네일 자리(images-outline 아이콘)는 38-10 부터 있던 그대로다.

## Threat Flags

없음. 새 네트워크·인증·저장 경로가 없다. 치환은 전부 String.replace + `<Text>` 다(T-eal-01).

## Self-Check: PASSED

- 수정 9파일 존재 [확인 `git diff --stat`].
- 커밋 `25a8edfc` · `8e9ad01f` · `d1651a76` 존재 [확인 `git log --oneline -4`].
- 스크린샷 3장 `eal-a1.png` · `eal-a6.png` · `eal-a6-s5.png` 을 Read 로 직접 열어 봤다.

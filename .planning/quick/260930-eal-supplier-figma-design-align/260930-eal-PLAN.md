---
phase: quick-260930-eal
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/src/theme/colors.ts
  - app/src/constants/supplierCopy.ts
  - app/src/constants/supplierCopy.test.ts
  - app/src/lib/supplierRules.ts
  - app/src/lib/supplierRules.test.ts
  - app/src/components/SupplierUi.tsx
  - app/src/app/supplier/index.tsx
  - app/src/app/supplier/upload.tsx
  - app/src/app/supplier/guide.tsx
autonomous: true
requirements: [REQ-38-3, REQ-38-4, REQ-38-5, REQ-38-6, REQ-38-8]

must_haves:
  truths:
    - "/supplier 로그인 전 화면(A-1)에 브랜드 워드마크 110x37, '강사·선수 전용' 칩, 30pt 제목, 높이 54 Google 버튼(아이콘+라벨이 가운데 묶음), 흐린 15pt 힌트가 38-DESIGN.md A-1 순서대로 보인다"
    - "/supplier/guide(A-6)의 7개 섹션 카드는 01~07 번호(13/700 브랜드) + 18/700 제목 + 회색 점 항목 15pt 로 그려지고, ④ 카드 끝에 연분홍(#FFF4F2) '등록이 안 되는 4가지' 상자가 있다"
    - "홈(A-3) 헤더에는 흰 워드마크·촬영 가이드 링크·제목·identity 가 있고, 내 동작 카드 머리 오른쪽에 '{n}개', 진행 중 행은 쉐브론 대신 8px 점, 행 부제는 '{레벨} · {상태어}' 다"
    - "내 코드 카드는 코드 준비 중일 때 '코드 준비 중'(20/700 회색) + 비활성 '코드 복사'(opacity 0.4) + '운영팀이 코드를 넣으면 여기에 보여요.' 를 보여 준다"
    - "STEP 01/02 머리에 2칸 진행 막대가 있고(01=1칸 브랜드, 02=2칸 모두 브랜드), 촬영 전 체크는 번호 1~5 카드 안에 확인 체크 행과 '자세한 가이드' 링크를 품는다"
    - "A-5 올리는 중 화면은 파일 요약 카드 + '올리는 중' / '{pct}%' 두 조각 + 8px 진행 트랙 + 바뀐 keepOpen 문구 + 가운데 '올리기 취소' 로 그려진다"
    - "A-3c 등록 완료는 '{name} · {athlete} 선수' 부제, 회색 재현성 카드(제목 + {score}점 + 본문 + 고지), 7행 정보 표 카드로 그려진다"
    - "guide.* 와 docs/supplier-guide.md 글자 동일성, row.fail.* 계약 문구 잠금 테스트가 계속 통과한다"
  artifacts:
    - path: "app/src/theme/colors.ts"
      provides: "공급자 시안 신규 색 토큰(#FFF4F2 + 리터럴 금지를 지키기 위한 최소 토큰) + 사진 음영 그라디언트"
      contains: "#FFF4F2"
    - path: "app/src/constants/supplierCopy.ts"
      provides: "38-DESIGN.md '새/바뀐 문구 키 요약' 반영"
      contains: "codePendingTitle"
    - path: "app/src/lib/supplierRules.ts"
      provides: "rowSubtitle '{레벨} · {상태어}' + selfCheckView(score/body 분리)"
      exports: ["rowSubtitle", "selfCheckView", "selfCheckNote"]
    - path: "app/src/components/SupplierUi.tsx"
      provides: "시안 값으로 바뀐 공용 프리미티브(Chip, BrandMark, StepHeader 진행 막대, CheckCard, 유리 BottomBar, UploadSummary 등)"
    - path: "app/src/app/supplier/index.tsx"
      provides: "A-1 / A-2 / A-3 / A-3b / A-3c 시안 배치"
    - path: "app/src/app/supplier/upload.tsx"
      provides: "STEP 01 / STEP 02 / A-5 시안 배치"
    - path: "app/src/app/supplier/guide.tsx"
      provides: "A-6 번호 카드 + 연분홍 상자"
  key_links:
    - from: "app/src/app/supplier/index.tsx"
      to: "supplierRules.selfCheckView"
      via: "DonePanel 재현성 카드 score/body"
      pattern: "selfCheckView\\("
    - from: "app/src/app/supplier/guide.tsx"
      to: "colors.supplierPinkBg"
      via: "④ 등록이 안 되는 4가지 상자 배경"
      pattern: "supplierPinkBg"
    - from: "app/src/components/SupplierUi.tsx"
      to: "gradients.supplierPhotoShade"
      via: "CodeCard 사진 음영 LinearGradient"
      pattern: "supplierPhotoShade"
---

<objective>
38 공급자 페이지(`/supplier` Expo Router 라우트 3개 + 공용 프리미티브)를 Figma 시안(섹션 282:506)에 맞춘다.
명세 정본은 `.planning/phases/38-supplier-link/38-DESIGN.md` 하나다. 실행기는 Figma MCP 를 열지 않는다(열 수 없다) — 값은 전부 그 파일에서 읽는다.

Purpose: belle 2026-09-30 결정 "먼저 시안에 맞추기" — 38-13(HTTPS 배포 + 실기기 검증) 전에 끝내야 38-13 실기기 확인이 시안 기준 화면을 본다.
Output: 9개 파일 수정, node 테스트 6파일 통과, 웹 export 성공, 로그인 없이 닿는 화면(A-1, A-6) 스크린샷.

우선순위 규칙:
- 38-DESIGN.md 와 38-UI-SPEC.md 가 시각 값에서 부딪히면 38-DESIGN.md 가 이긴다(38-DESIGN.md 9행).
- 문구 규율은 그대로다: 화면 파일 한국어 리터럴 0(supplierCopy 단일 출처), `guide.*` 는 docs/supplier-guide.md 와 글자 동일(바꾸지 않는다), `row.fail.*` 는 계약 문구 잠금(바꾸지 않는다).
- 색·간격은 theme 토큰 또는 SupplierUi.tsx 안의 선언값(`space`/`H`/`R`/`F`)만. 화면 파일 색 리터럴 0. 이모지 0.
- 음수 letterSpacing 은 iOS 26+ SIGABRT(typography.ts 2~6행) — 38-DESIGN §0 의 30pt −2% 는 웹에서만 적용한다(이 라우트는 38-04 option-1 로 웹이 주 무대). 코드 +4% 는 양수라 모든 플랫폼 적용.
- 새 애니메이션 추가 0(apple-design: 눌림 피드백은 press-down = Pressable `pressed` 스타일. reduced motion 을 고려할 움직임을 새로 만들지 않는다).
- backend · infra · Firestore 규칙 · 다른 앱 화면은 건드리지 않는다.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@app/CLAUDE.md
@.planning/phases/38-supplier-link/38-DESIGN.md
@app/src/components/SupplierUi.tsx
@app/src/constants/supplierCopy.ts

필요할 때만(부분 읽기):
- app/src/app/supplier/index.tsx 325~669행(렌더부) · upload.tsx 400~701행(렌더부) · guide.tsx 전체(152행)
- app/src/lib/supplierRules.ts 150~220행(doneScore · rowStatusWord · rowSubtitle · selfCheckLine)
- app/src/lib/supplierRules.test.ts 86~130행 · app/src/constants/supplierCopy.test.ts 176~240행
- app/src/theme/colors.ts(토큰 이름) · app/src/theme/typography.ts 1~35행(track()=0 규칙)
- app/src/components/PickErrorDialog.tsx 30행 `AlertIcon({size})` — 38-DESIGN 의 "알림 원형 !" 아이콘은 이것을 쓴다(18/24/44)
- app/src/app/auth/login.tsx 119행 — 로그인 워드마크 크기 110x37

현재 코드 사실(플래너가 읽고 확인한 것):
- 이미 있는 토큰: #D9D9D9=colors.divider, #B1B6BE=colors.inputBorder, #767676=colors.resultTextSub, #5A5A5A=colors.textMid, #F5F5F5=colors.softBg, #EBEBEB=colors.trackBg, #22B47A=colors.progressGreen, #2C7C8C=colors.infoTeal, #FFB7AD=colors.brandButtonDisabled, #0C0C0C=colors.textPrimary, 시트 흰→#FFF0EE=gradients.homeCard, 알약=gradients.brandButton, 헤더=gradients.homeTop.
- 없는 값: #FFF4F2, #EDEDED, 흰 86%/96%, 사진 음영 rgba(0,0,0,0.55).
- `row.self.ok` 소비처 = supplierRules.selfCheckLine 하나(→ index.tsx DonePanel). `home.codePending` 소비처 = index.tsx 618행 하나. `form.uploading.progress` 소비처 = upload.tsx 439행 하나. 38-12 단일 HTML 은 skip 이라 다른 소비처 없음.
- rowSubtitle 는 지금 `${레벨} ${상태어}`(공백) — 시안은 ` · `.
- supplierForm.ts 의 trimmedName 은 export 되지 않는다. nameChoice 는 dict/new 둘 다 `name` 필드를 가진다.
- dist/ 는 app/.gitignore 에 있다. 38-10 은 `npx expo serve` 로 :8082 에 띄워 스크린샷을 찍었다.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 문구 키 · 규칙 함수 · 색 토큰 (테스트 먼저)</name>
  <files>app/src/constants/supplierCopy.ts, app/src/constants/supplierCopy.test.ts, app/src/lib/supplierRules.ts, app/src/lib/supplierRules.test.ts, app/src/theme/colors.ts</files>
  <behavior>
    - supplierCopy.login.chip === '강사·선수 전용'
    - supplierCopy.noAccess.refreshHint === '등록이 끝나면 눌러서 바로 확인할 수 있어요.'
    - supplierCopy.home.count === '{n}개'; home.upload === '동작 올리기' 이고 '>' 를 포함하지 않는다
    - home.codePending 키가 없다; home.codePendingTitle === '코드 준비 중'; home.codePendingBody === '운영팀이 코드를 넣으면 여기에 보여요.'
    - form.sec5.allHint === '필수 3개'; row.done.sub === '{name} · {athlete} 선수'
    - row.self.ok 키가 없다; row.self.title === '자기 영상 재분석'; row.self.okBody === '추출·저장이 일관돼요.'; row.self.scoreText === '{score}점'
    - form.uploading.progress 키가 없다; form.uploading.progressLabel === '올리는 중'; form.uploading.pct === '{pct}%'; form.uploading.keepOpen === '화면을 닫지 마세요. 다 올라가면 목록으로 돌아가요.'
    - form.uploading.summaryTitle === '{name} · {level}'; form.uploading.summaryMeta === '{file} · {meta}'
    - form.sec1.guideLink === '자세한 가이드'
    - guide.* 와 row.fail.* 는 한 글자도 바뀌지 않는다(기존 md 동일성·계약 3원 일치 테스트 그대로 통과)
    - rowSubtitle(registering 기본기) === '기본기 · 올린 영상 확인 중'; activeOk === '기본기 · 재현성 97점'; activeLow === '고급 · 재현성 61점 · 다시 찍어 주세요'
    - selfCheckView(activeOk) → { score: 97, body: row.self.okBody }; activeLow → { score: 61, body: '본인 재현성 61점 · 낮아요. 다시 찍어 주세요' }; activePending → { score: null, body: row.self.pending }; activeSelfQueued → { score: null, body: row.self.queued }; activeSelfFailed → { score: null, body: row.self.failed }
    - selfScoreBoundary 픽스처: view.score === Math.round(selfScore), ok 쪽 body === okBody, low 쪽 body 가 '다시 찍어 주세요' 와 `${rounded}점` 을 포함
  </behavior>
  <action>
RED 먼저: supplierCopy.test.ts 와 supplierRules.test.ts 를 behavior 대로 고친 뒤 node --test 로 실패를 확인하고, 그다음 구현한다.

supplierCopy.test.ts: 176~183행 ui-checker flags 테스트에서 `home.codePending.includes('운영팀')` 을 `home.codePendingBody.includes('운영팀')` 으로, `home.upload === '동작 올리기 >'` 를 `'동작 올리기'` + `!includes('>')` 로 바꾼다(주석 "flag #4 유지" → "38-DESIGN A-3: '>' 대신 쉐브론 아이콘"). 231~233행 R11 테스트의 row.self.ok 단언 두 개를 `row.self.okBody.includes('추출·저장이 일관돼요')` + `row.self.title === '자기 영상 재분석'` 으로 바꾼다('기준으로 쓸 수 있어요' 금지 루프 · note · low 단언은 그대로). 새 test 하나를 "38-DESIGN.md 새/바뀐 문구 키" 라는 이름으로 추가해 behavior 의 키 값들을 assert.equal 로 잠그고, `'progress' in supplierCopy.form.uploading`, `'codePending' in supplierCopy.home`, `'ok' in supplierCopy.row.self` 가 모두 false 인지도 확인한다. 파일 머리 "검증 축" 주석에 11) 한 줄 추가.

supplierRules.test.ts: 88~100행 rowSubtitle 테스트의 기대값 전부를 `${레벨} · ${상태어}` 형식으로 바꾸고 테스트 이름도 `{레벨} · {상태어}` 로. 102~112행 selfCheckLine 테스트를 selfCheckView 5분기 테스트로 교체(behavior 값. selfCheckNote() === note 단언과 body 에 '{score}' 가 남지 않는다는 단언 유지). 114~130행 경계 테스트는 selfCheckLine 대신 selfCheckView 를 쓰도록 바꾸고 rowSubtitle endsWith 단언은 그대로 둔다(형식이 ` · ` 로 바뀌어도 끝부분은 같다). import 목록에서 selfCheckLine 을 selfCheckView 로.

supplierCopy.ts (38-DESIGN '새/바뀐 문구 키 요약' + A-4/A-5/A-3c 본문): login.chip, noAccess.refreshHint, home.count, home.codePendingTitle/codePendingBody(codePending 삭제, ui-checker flag #3 주석은 "38-DESIGN A-3 에서 둘로 나눔"으로 교체), home.upload '동작 올리기'(flag #4 주석 교체), row.done.sub, row.self.title/okBody/scoreText(ok 삭제 — R11 취지 '일관성 진단'은 okBody 가 잇는다는 주석), form.sec5.allHint, form.uploading 을 { title, progressLabel, pct, keepOpen(새 문구), summaryTitle, summaryMeta } 로(progress 삭제), form.sec1.guideLink '자세한 가이드'. 재량 판단 2건을 주석으로 남긴다: (a) summaryTitle/summaryMeta/pct/scoreText 는 38-DESIGN 키 요약에 없지만 A-5·A-3c 화면 파일에 ` · `·'점'·'%' 리터럴을 두지 않으려고 추가, (b) sec1.guideLink 는 키 요약에서 빠졌으나 A-4 본문이 '자세한 가이드' 를 명시해 따름. 파일 머리 주석에 "2026-09-30 38-DESIGN.md 가 표시 문구 일부를 바꿨다 — 이 파일이 여전히 단일 출처" 한 줄. guide.* 와 row.fail.* 는 건드리지 않는다.

supplierRules.ts: rowSubtitle 을 `${LEVEL_LABEL_KO[m.level]} · ${rowStatusWord(m)}` 로(주석 "Figma 1:717 어법" → "38-DESIGN A-3 행 부제"). selfCheckLine 을 지우고 selfCheckView(m): { score: number | null; body: string } 를 export — doneScore 로 score 를 구하고, score 가 있으면 SELF_SCORE_OK_MIN 이상일 때 body = row.self.okBody, 미만일 때 withScore(row.self.low, score). score 가 없으면 기존 분기(queued / failed·done / pending) 그대로 body 만 돌려준다. "표시와 분기가 같은 반올림 숫자" 불변식 주석 유지. selfCheckNote 는 그대로.

colors.ts: colors 객체 끝에 "Phase 38 공급자 시안(Figma 282:506, 38-DESIGN §0)" 블록 — supplierPinkBg '#FFF4F2'(A-6 상자, 38-DESIGN 이 지정한 신규 토큰), dividerSoft '#EDEDED'(카드 안 구분선), barGlass 'rgba(255,255,255,0.86)'(웹 하단 바), barSolid 'rgba(255,255,255,0.96)'(네이티브 하단 바). gradients 에 supplierPhotoShade { colors: ['rgba(0,0,0,0)', 'rgba(0,0,0,0.55)'] as const, locations: [0.35, 1] as const } 추가. 주석: "38-DESIGN §0 은 신규 색을 #FFF4F2 하나로 적었지만 #EDEDED · 흰 86/96% · 음영 0.55 도 기존 토큰이 없어, 화면 색 리터럴 금지(app/CLAUDE.md)를 지키려고 같이 추가". 기존 값 변경 0.

이 태스크 뒤 index.tsx·upload.tsx 는 지운 키 때문에 타입 오류가 난다 — Task 2·3 이 고친다. 이 태스크의 게이트는 node 테스트다.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/app && node --test src/constants/supplierCopy.test.ts src/lib/pickerFailure.test.ts src/lib/supplierForm.test.ts src/lib/supplierRules.test.ts src/lib/videoDuration.test.ts src/lib/videoMeta.test.ts 2>&1 | tail -8</automated>
  </verify>
  <done>6파일 node 테스트 fail 0(pass 수는 기존 65 에서 바뀐 값을 SUMMARY 에 적는다). RED 실패 출력 한 줄을 SUMMARY 에 인용. `git diff --stat` 에 docs/supplier-guide.md 변경 0. 커밋 `feat(quick-260930-eal): supplier copy keys + rules + color tokens per 38-DESIGN` — 이 태스크 5파일만 명시 스테이징.</done>
</task>

<task type="auto">
  <name>Task 2: 공용 프리미티브(공통·홈·상세) + index.tsx A-1 / A-2 / A-3 / A-3b / A-3c</name>
  <files>app/src/components/SupplierUi.tsx, app/src/app/supplier/index.tsx</files>
  <action>
SupplierUi.tsx 머리 주석에 "2026-09-30 38-DESIGN.md(Figma 282:506) 값으로 갱신 — UI-SPEC 과 부딪히는 시각 값은 DESIGN 우선" 한 줄. 38-10 의 `≈` 값 중 Google 48 은 54 로 확정(38-DESIGN A-1).

선언값: `space` 에 xxs 2, s6 6, s10 10, s13 13, s14 14, s40 40 추가(기존 키 유지). `H.google` 54. `text` 에 추가 — aux(regular 15, lineHeight 20, textMid: 38-DESIGN §0 보조 문구), auxFaint(같은 크기, resultTextSub: 흐린 보조), body15(regular 15/20 textPrimary), body15Bold(bold 15/20 textPrimary), caption13(regular 13, lineHeight 18, textMid), num13(bold 13/18 brand: 가이드 01~07), chipText(bold 13/18 textMid), code(bold 30, lineHeight 39, brand, letterSpacing +1.2 = 30x4%). `text.step` 을 bold 15/20 brand 로(13.8 폐기, 38-DESIGN §0). `text.display` 에 letterSpacing = Platform.OS === 'web' ? −0.6 : 0 (typography.ts 음수 자간 SIGABRT 규칙 인용 주석). 굵기는 반드시 fontFamily.bold/regular 로 지정(fontWeight 만으로는 iOS 가 무시).

프리미티브(각각 38-DESIGN 절 인용 주석):
- 새 `BrandMark({ variant })`: brand = SunityWordmark 110x37(login.tsx 와 같은 로고), white = 83x28(0.75배). A-1·A-2·checking 화면이 TopBar showWordmark 대신 쓴다. showWordmark 소비처가 사라지면 그 prop 을 지운다.
- 새 `Chip({ label })`: softBg, 반경 8, 패딩 4/10, chipText.
- `GoogleButton`: 높이 54, 반경 13, 흰 바탕, 1px inputBorder, G 아이콘 20 + 간격 10 + 18/700 라벨을 가로 묶음으로 가운데 정렬(아이콘 absolute 배치 폐기).
- `TextLink`: tone 'signOut' 에 밑줄 추가(38-DESIGN A-3 "틸 링크 17 밑줄"), 새 tone 'onHeader'(흰 17/700 밑줄 — 헤더 촬영 가이드). 'cancel'·'go' 그대로. 새 prop center?: boolean → alignSelf center.
- `OutlineButton`: 비활성 opacity 0.4(s.cardPressed), 눌림은 0.7 유지(press-down 피드백).
- `GradientHeader({ title, identity, guideLabel, onGuide })` 재작성: paddingTop = insets.top + 16 → 높이 44 첫 줄(BrandMark white 왼쪽 + TextLink onHeader 오른쪽) → 8 → 제목 display 흰색 → 4 → identity 17/700 흰색(numberOfLines 1) → paddingBottom = SHEET_OVERLAP + 24. 새 상수 SHEET_OVERLAP = 84(시안 헤더 ≈300, 시트 216 에서 겹침). `Sheet` marginTop = −SHEET_OVERLAP.
- `SectionHeader({ title, count? })`: 제목 20/700 왼쪽 + 오른쪽 count 17 textMid. moreLabel/onMore 제거.
- `PillCta`: 라벨 17/700 흰 + 흰 chevron-forward 20 아이콘 가로 묶음(간격 4). 글자 `>` 흉내 금지.
- `ListRow`: showChevron 을 `trailing: 'chevron' | 'progress' | null` 로 — chevron = Ionicons chevron-forward 20 inputBorder, progress = 8x8 원(반경 4) brandButtonDisabled. 이름 18/700 → 2 → 부제 aux. 행 구분선 1px dividerSoft. 썸네일 48 반경 8 · highlighted 테두리 유지.
- `StepCard`: 1px dashed brand, 반경 15, 패딩 20/16, 가운데 정렬 — STEP(text.step) → 4 → 18/700 제목 → 8 → aux 본문 → 16 → cta(alignSelf stretch). dash 6/4 는 RN 이 길이를 제어 못 한다 — borderStyle dashed 로 두고 SUMMARY 에 [근사] 로 적는다.
- `IdBox`: 패딩 12/16, 17/700, 줄바꿈 허용.
- `CodeCard` 재구성(38-DESIGN A-3 내 코드): props { photoUrl, sportLabel, athleteLine, codeTitle, code, pendingTitle, pendingBody, copyLabel, onCopy, howText }. 카드 = 1px divider, 반경 15, overflow hidden, 패딩 0. 사진이 있으면 높이 180 cover + absoluteFill LinearGradient(gradients.supplierPhotoShade, start {x:0,y:0} end {x:0,y:1}) + 왼쪽·아래 16 에 `폴스포츠` body15Bold 흰(아래 2px brand 밑줄, alignSelf flex-start) → `{name} 선수` 18/700 흰. 사진이 없으면 기존 이름 블록 유지. 본문 패딩 16 가운데 정렬: codeTitle(body15Bold textMid) → 4 → 코드 text.code(selectable), 준비 중이면 pendingTitle(bold 20/28 resultTextSub) → 12 → OutlineButton copyLabel 전폭(준비 중이면 disabled) → 12 → aux 가운데(howText, 준비 중이면 pendingBody). 기존 photoShade 반투명 View 폐기.
- `FailurePanel`: 패널 paddingTop 24(내용 y≈128). 링 72 → 24 → 제목 18/700 → 8 → 본문 17 textMid → 8 → 코드 칩(softBg 반경 8, 패딩 2/8, caption 12 resultTextSub) → 24 → TipCard → 24 → PrimaryCta 54 → 16 → TextLink cancel center.
- `TipCard`: 머리 AlertIcon 18 + 6 + 17/700 → 8 → 줄 body15, 간격 4.
- `DonePanel` 재구성(38-DESIGN A-3c): props { title, sub, selfTitle, scoreText: string | null, selfBody, note, info, low, tip, reuploadLabel, onReupload, backLabel, onBack }. 패널 paddingTop 8(내용 y≈112), 가운데 정렬: 체크 링 progressGreen → 20 → 제목 18/700 → 4 → sub 17 textMid → 24 → 재현성 카드(softBg, 반경 15, 패딩 16, alignSelf stretch): 가로 줄 selfTitle 17/700 왼쪽 + scoreText(있을 때만) bold 20 brand 오른쪽 → 4 → selfBody aux → 8 → note auxFaint → 16 → 정보 표 카드(1px divider, 반경 15, 패딩 4/16): 행 세로 패딩 10, 행 사이 1px dividerSoft, 키 aux · 값 body15Bold 오른쪽 정렬 → low 면 24 → TipCard → 24 → PrimaryCta → 24 → TextLink cancel center. 기존 selfLine 숫자 쪼개기 로직 폐기.
- `NoticePill`: 반경 15, 1px divider, 패딩 12/16, AlertIcon 24 + 12 + 줄 aux 두 줄(홈 podDown 과 폼 ④ 가 같이 쓴다).
- `GrayCard`·`Toast`·`PageFrame`·`Card`·`RingIcon` 은 그대로.

index.tsx:
- A-1(phase login): BrandMark brand(safe-area 위 40, 시안 y≈97) → 48 → Chip(login.chip) → 12 → 제목 display → 8 → 본문 17 textMid → 48 → GoogleButton → 12 → login.sameAccountHint auxFaint 가운데 → loginNotice(teal, 기존 그대로) → flex 채움 → 빌드 caption(12 resultTextSub) 가운데, 하단 여백 layout.safeAreaBottom(34). 워드마크→칩 48 은 시안에 y 가 없어 재량값 — SUMMARY 에 적는다.
- checking/error: BrandMark brand → 32 → 제목 → 4 → identity → 이하 기존 흐름·문구 그대로.
- A-2(noAccess): BrandMark → 32 → 제목 display(home.title) → 4 → identity 17 textMid → 32 → Card(패딩 16) 하나: AlertIcon 44 → 16 → noAccess.title 18/700 → 8 → body 17 textMid → 16 → idLabel body15Bold textMid → 6 → IdBox → 8 → OutlineButton copyId 전폭 → copyFallback 이면 8 → aux. 카드 밖: 16 → OutlineButton refresh(라벨은 항상 noAccess.refresh, recheckBusy 동안 disabled) → 8 → 힌트 auxFaint 가운데 accessibilityLiveRegion polite = recheckBusy ? noAccess.checking : stillNo ? noAccess.stillNo : noAccess.refreshHint → 24 → TextLink signOut. 카드 안은 왼쪽 정렬(38-DESIGN 이 A-2 에 가운데 정렬을 적지 않았다). 기존 AlertCircle(Ionicons) 함수 삭제.
- A-3 홈: GradientHeader 에 identity 와 촬영 가이드 링크(common.guideLink → /supplier/guide)를 넘기고, 시트 맨 위 identityRow 삭제(ui-checker flag 7행 주석을 "38-DESIGN A-3 로 헤더 복귀" 로 교체). 목록이 비었고 로딩·오류가 아니면 내 동작 Card 대신 StepCard 하나(cta = PillCta). 그 밖엔 Card(패딩 16/16/8): SectionHeader(title, count = home.count 의 {n} ← sorted.length) → 4 → motionsSub aux → 16 → (anyQueued 면 NoticePill → 12) → PillCta → 8 → 행 목록(ListRow trailing: registering/processing/queued = 'progress', hasDetail = 'chevron', 나머지 null) → 숨긴 행이 있으면(!showAll && sorted.length > ROWS_BEFORE_SEE_ALL) 목록 아래 TextLink go center common.seeAll(재량: 헤더 오른쪽 자리를 count 가 가져가 옮김 — SUMMARY 에 적는다). 오류·로딩 분기는 카드 안 기존 자리.
- 내 코드: 카드 밖 heading 삭제, CodeCard 에 codeTitle = home.codeTitle, pendingTitle/pendingBody = home.codePendingTitle/codePendingBody. 앞 간격 16.
- 하단: 24 → TextLink signOut → 8 → 빌드 caption.
- 상세(A-3c): view = selfCheckView(m); DonePanel 에 sub = row.done.sub 치환({name}=m.name, {athlete}=m.athleteName), selfTitle = row.self.title, scoreText = view.score != null ? row.self.scoreText 치환 : null, selfBody = view.body, note = selfCheckNote(), low = view.score != null && view.score < SELF_SCORE_OK_MIN. shownSelfScore 가 view.score 와 같은 값을 내면 shownSelfScore 를 지우고 view 를 쓴다(표시와 분기가 같은 숫자). selfCheckLine import 삭제. A-3b·만료는 FailurePanel 호출 그대로.
- 치환은 전부 String.replace(T-38-03-2). 화면 한국어 리터럴 0, 색 리터럴 0.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/app && (npx tsc --noEmit 2>&1 | grep -cE "supplier/index\.tsx|SupplierUi\.tsx" || true) && (grep -nE "#[0-9A-Fa-f]{6}|rgba\(" src/app/supplier/index.tsx src/components/SupplierUi.tsx | grep -vE ":[0-9]+:\s*(//|\*|\{/\*)" | wc -l)</automated>
  </verify>
  <done>첫 숫자(index.tsx·SupplierUi.tsx 타입 오류 수) 0, 둘째 숫자(주석 밖 색 리터럴) 0. upload.tsx 의 남은 오류(uploading.progress 등)는 Task 3 몫이라 여기서 허용. 커밋 `feat(quick-260930-eal): supplier home/login/detail match Figma 282:506` — 2파일만 명시 스테이징.</done>
</task>

<task type="auto">
  <name>Task 3: 폼 프리미티브 + upload.tsx STEP 01/02 · A-5 + guide.tsx A-6 + 전체 게이트 · 스크린샷</name>
  <files>app/src/components/SupplierUi.tsx, app/src/app/supplier/upload.tsx, app/src/app/supplier/guide.tsx</files>
  <action>
SupplierUi.tsx 폼 프리미티브(38-DESIGN A-4 / A-5):
- `StepHeader({ step, title, current: 1 | 2 })`: text.step → 8 → 진행 막대 2칸(가로, 간격 6, 각 flex 1, 높이 4, 반경 2; 칸 번호 ≤ current 면 brand, 아니면 trackBg; accessibilityRole progressbar, accessibilityValue {min 1, max 2, now current}) → 16 → display 제목(header). 새 상수 F.stepBar 4.
- 새 `CheckCard({ title, items, confirmLabel, checked, onToggle, linkLabel, onLink })`: Card(패딩 16/16/8) — 머리 AlertIcon 18 + 6 + title 18/700 → 12 → 항목(간격 8): 번호 `${i+1}` 15/700 brand + 10 + body15(flex 1). 문구 앞 `· ` 는 화면에서만 떼어 보여 준다(원문 supplierCopy 는 그대로 — 38-DESIGN A-4 ①) → 12 → 1px dividerSoft → 체크 행(세로 패딩 13): 왼쪽 Pressable(CheckBox 22 + 10 + confirmLabel 17/700 flex 1, role checkbox) + 오른쪽 Pressable 링크(linkLabel 15 brand + chevron-forward 14 brand, role link, hitSlop 8).
- `Helper`: aux 로(17→15), 위 8.
- `TextInput54`: 라벨이 있으면 17/700(text.labelBold), 포커스 테두리 1.5px brand(비포커스 1px).
- `SelectField`: 라벨 17/700. 컨트롤 값은 그대로(54/13/1px inputBorder/값 17/chevron-down 20 textMid).
- `CheckBox`·`CheckboxRow`: 행 = 체크박스 22 + 10 + 한 문단 17(태그 `[필수]` 700 brand / `[선택]` 700 resultTextSub 가 같은 문단 안), 세로 패딩 12. 새 prop inset?: boolean → 가로 패딩 16(STEP 02 동의 행). note 는 아래 4 에 caption13 + resultTextSub. chevron 20 inputBorder 유지. 콤보 행은 같은 컴포넌트(시안의 8 간격과 2 차이는 [근사] 로 SUMMARY).
- `AllAgreeBox({ label, hint, checked, onToggle })`: 54 / 반경 13 / 1px divider / 패딩 0 16: 체크박스 + 12 + label 17/700(flex 1) + 오른쪽 hint auxFaint.
- 새 `WithdrawNote({ text })`: softBg, 반경 15, 패딩 16, aux.
- `VideoPreview`: 바깥 상자 전폭 x 360, 반경 15, 배경 textPrimary, overflow hidden, 가운데 정렬 — 그 안에 9:16 VideoView(높이 360, contentFit contain).
- 새 `VideoThumb({ uri })`: 40x64, 반경 8, 배경 trackBg, overflow hidden, VideoView(nativeControls false, contentFit cover, muted player, 재생 안 함). uri 없으면 trackBg 상자만.
- 새 `UploadSummary({ uri, title, meta })`: softBg, 반경 15, 패딩 12, 가로 — VideoThumb → 12 → title 18/700 / 2 / meta aux.
- `ProgressBar({ pct, label, valueText })`: 가로 줄(label 17 왼쪽 + valueText 17/700 brand 오른쪽, aria-live polite) → 8 → 트랙 8/반경 4 trackBg + 채움 brand(role progressbar).
- `BottomBar({ hint, children, onHeight? })`: position absolute left/right/bottom 0, 위 테두리 없음, 패딩 16/20 + insets.bottom. 배경: 웹 = colors.barGlass + backdropFilter/WebkitBackdropFilter 'blur(20px)'(RN ViewStyle 타입 밖이라 Platform.OS === 'web' 에서만 좁은 캐스트로 붙이고 주석), 네이티브 = colors.barSolid. hint 가 있으면 CTA 위에 aux 가운데(aria-live), 아래 8. onLayout 높이를 onHeight 로 알려 준다 — 화면이 ScrollView contentContainer paddingBottom 에 그 값을 더해 마지막 내용이 바 뒤에 숨지 않게 한다.

upload.tsx:
- STEP 01: TopBar(뒤로) 바로 아래 StepHeader(step1.label, step1.title, current 1) → 32 → CheckCard(sec1.title, sec1.items, sec1.confirm, checkConfirmed, 토글, sec1.guideLink → /supplier/guide) → FieldError(sec1.error) → 40 → ② 필드(외곽 Card 와 `동작 정보` 섹션 제목 삭제 — 38-DESIGN A-4 ②): SelectField(동작 이름) → (new 면 8 → TextInput54) → 8 → Helper(name.helper) → 4 → 콤보 CheckboxRow → 16 → TextInput54(선수 이름) + Helper → 24 → 레벨 라벨 17/700 → 8 → Segment → FieldError → Helper. → 40 → heading `이 동작에 대해` 20/700 → 16 → 질문 3개 각각 Card(패딩 16, 카드 간격 12): 질문 17/700 → 12 → Segment 네/아니오 → FieldError → 8 → Helper → stand=no 면 그 아래 FieldError(stand.blocked, infoTeal). 외곽 Card 삭제. → 40 → heading `영상 파일` 20/700 → 16 → NoticePill(sec4.pill) → 12 → 파일 전: FileCard + FieldError(required) / 파일 후: VideoPreview → 12 → 메타 줄(가로 wrap: 파일 이름 17/700 → 8 → meta 17 textMid, meta 가 null 이면 이름만) → 4 → previewHint aux → 12 → OutlineButton repick. 외곽 Card 삭제. BottomBar(hint = 기존 bottomHint: 비활성일 때만 보이는 remaining/blocked) + PrimaryCta next.
- STEP 02: StepHeader(step2, current 2) → 32 → AllAgreeBox(sec5.all, hint = sec5.allHint) → 8 → CheckboxRow inset 4개(기존 props 그대로) → FieldError → 16 → WithdrawNote(sec5.withdraw) → inlineError 블록 기존대로 → BottomBar submit.
- A-5 uploading: TopBar 없이 PageFrame 패딩 위 60(시안 y≈120 = 59 + 60 근사) → display 제목(uploading.title) → 24 → UploadSummary(uri = step1.file?.uri, title = uploading.summaryTitle 치환 {name} = step1.nameChoice?.name.trim() ?? '' · {level} = step1.level 이 있으면 LEVEL_LABEL_KO(supplierRules) 없으면 빈 문자열, meta = meta 문자열이 있으면 uploading.summaryMeta 치환 {file}=파일 이름 {meta}=meta, 없으면 파일 이름) → 32 → ProgressBar(label = uploading.progressLabel, valueText = uploading.pct 치환) → 12 → keepOpen aux → 32 → TextLink cancel center(common.cancel).
- 업로드 실패 FailurePanel·PickErrorDialog 호출은 그대로(38-DESIGN "검증 다이얼로그 바꿀 것 없음").
- ScrollView contentContainer paddingBottom 에 BottomBar 높이(state) 를 더한다(STEP 01·02 둘 다).

guide.tsx(38-DESIGN A-6):
- TopBar → 8 → 제목 display → 8 → 부제 17 textMid → 32 → 섹션 카드 7개 간격 16(기존 24 → space.md).
- 카드 안: 번호 String(i+1).padStart(2, '0') num13 → 2 → 제목 18/700(header) → 12 → 항목(간격 8): 가로 줄 `·` 15/700 inputBorder + 8 + body15(flex 1). 점은 화면이 붙이는 기호라 supplierCopy 밖이어도 된다 — 지금도 `· ${line}` 으로 붙이고 있다(한국어 아님).
- ① 끝: 16 → 예시 사진 2장(정사각, 간격 12, 반경 15 — 38-11 그대로) → 8 → caption13(textMid).
- ④ 끝: TipCard 대신 16 → 상자(colors.supplierPinkBg, 반경 13, 패딩 14): AlertIcon 18 + 6 + guide.s4.tipHead 17/700 → 8 → guide.s4.tip 줄 body15, 간격 6(원문 `· ` 포함 그대로 렌더).
- nativeID 's5' 앵커와 section 스크롤 로직은 그대로.

전체 게이트(이 태스크 끝에서 전부 실행하고 원문 수치를 SUMMARY 에):
1) `cd app && npm run typecheck` exit 0.
2) node 테스트 6파일 fail 0.
3) `cd app && CI=1 npx expo export --platform web` exit 0(출력 app/dist 는 gitignore). 번들에서 `backdropFilter` 또는 `backdrop-filter` 가 1회 이상 grep 되는지 기록.
4) 색 리터럴 0: supplier 3파일 + SupplierUi.tsx 에서 주석 줄 밖 `#xxxxxx`·`rgba(` 0.
5) 한국어 리터럴 0: supplier 3파일에서 주석이 아닌 줄의 한글 0 — node 한 줄로 확인(각 줄에서 `//` 뒤를 자르고 `/*…*/`·`{/*…*/}` 줄은 건너뛴 뒤 /[가-힣]/ 검사).
6) 스크린샷: app 에서 `npx expo serve --port 8082` 를 백그라운드로 띄우고, `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --hide-scrollbars --window-size=390,844 --virtual-time-budget=10000 --screenshot=<scratchpad>/eal-a1.png http://localhost:8082/supplier`, 같은 방식으로 `eal-a6.png`(창 390x3400, /supplier/guide), `eal-a6-s5.png`(390x844, /supplier/guide?section=s5). scratchpad = /private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/ef3648dc-db87-4310-a2aa-b555fa84c027/scratchpad. 찍은 PNG 를 Read 로 직접 열어 38-DESIGN A-1·A-6 와 대조(칩·워드마크·Google 버튼 54·번호 01~07·연분홍 상자)하고 보이는 차이를 SUMMARY 에 [확인 눈]/[불일치] 로 적는다. 끝나면 서버를 끄고 `lsof -i :8082` 가 비었는지 기록. A-1 대신 오류 화면이 뜨면 그대로 적는다(Firebase env 가 export 에 안 들어간 경우 등) — 고치려고 env 를 만지지 않는다.
7) 로그인·화이트리스트 뒤 화면(A-2, A-3, A-3b, A-3c, STEP 01/02, A-5)은 이 실행에서 그릴 수 없다 — SUMMARY 에 [미확인 — 38-13 실기기에서 belle 확인] 으로 적고 "시각 검증 완료"라고 쓰지 않는다.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/app && npm run typecheck && node --test src/constants/supplierCopy.test.ts src/lib/pickerFailure.test.ts src/lib/supplierForm.test.ts src/lib/supplierRules.test.ts src/lib/videoDuration.test.ts src/lib/videoMeta.test.ts 2>&1 | tail -6 && CI=1 npx expo export --platform web >/dev/null 2>&1 && echo EXPORT_OK && grep -nE "#[0-9A-Fa-f]{6}|rgba\(" src/app/supplier/index.tsx src/app/supplier/upload.tsx src/app/supplier/guide.tsx src/components/SupplierUi.tsx | grep -vE ":[0-9]+:\s*(//|\*|\{/\*)" | wc -l</automated>
  </verify>
  <done>typecheck exit 0 · node 테스트 fail 0 · EXPORT_OK 출력 · 색 리터럴 수 0 · 한국어 리터럴 0 · 스크린샷 3장 경로가 SUMMARY 에 있고 각 장을 열어 본 관찰이 [확인 눈]/[불일치] 로 적혀 있음 · 로그인 뒤 화면은 [미확인] 명시 · 서버 종료 확인. 커밋 `feat(quick-260930-eal): supplier form/upload/guide match Figma 282:506` — 3파일만 명시 스테이징. `.planning/TRAINING-DUE.md` 스테이징 금지 · push 금지 · PLAN/SUMMARY/STATE 는 커밋하지 않는다(오케스트레이터 몫).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| 사용자 입력 → 화면 텍스트 | 동작 이름·선수 이름·파일 이름(선택한 파일)·Google displayName 이 문구 템플릿에 치환돼 화면에 나온다 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-eal-01 | Tampering | supplierCopy 템플릿 치환(row.done.sub · uploading.summaryTitle/summaryMeta · home.count) | mitigate | String.replace 만 쓰고 RN `<Text>` 로 렌더(HTML/JSX 해석 없음) — T-38-03-2 규칙 그대로 |
| T-eal-02 | Information Disclosure | A-5 파일 요약의 파일 이름 · A-2 ID | accept | 본인 기기·본인 계정 화면에만 보이는 값, 새로 서버로 보내는 데이터 없음 |
| T-eal-03 | Spoofing | 웹 backdropFilter 캐스트 | accept | 스타일 값만, 입력 경로 없음 |

패키지 설치 없음(T-SC 해당 없음). 백엔드·규칙·인프라 변경 없음.
</threat_model>

<verification>
- Task 3 전체 게이트 1)~7)이 이 플랜의 최종 검증이다.
- `git diff --stat` 이 files_modified 9파일 밖을 건드리지 않았는지 확인(docs/supplier-guide.md · analysis.ts · backend 변경 0).
- 38-DESIGN.md 절별 체크(§0 · A-1 · A-2 · A-3 · 빈 상태 · 내 코드 · A-4 STEP 01 · STEP 02 · 다이얼로그 무변경 · A-5 · A-3b · A-3c · A-6 · 문구 키 요약)를 SUMMARY 에 표로 — 각 행에 반영 파일과 [확인 눈]/[확인 코드]/[미확인] 표기.
</verification>

<success_criteria>
- 38-DESIGN.md 의 모든 절이 코드에 반영됐다(재량값·근사값은 SUMMARY 에 목록).
- supplierCopy 단일 출처, guide.* md 동일성, row.fail.* 계약 잠금 테스트가 통과한다.
- typecheck · node 6파일 · 웹 export 모두 통과.
- 화면 파일 색 리터럴 0 · 한국어 리터럴 0 · 이모지 0.
- 로그인 없이 닿는 A-1 · A-6 스크린샷이 있고, 닿지 않는 화면은 [미확인] 으로 남았다.
</success_criteria>

<output>
Create `.planning/quick/260930-eal-supplier-figma-design-align/260930-eal-SUMMARY.md` when done (커밋하지 않는다 — 오케스트레이터가 docs 커밋).
관측(잰 값·명령 출력)과 진단(왜)을 다른 절에 적는다(CLAUDE.md §7 보고 규칙).
</output>

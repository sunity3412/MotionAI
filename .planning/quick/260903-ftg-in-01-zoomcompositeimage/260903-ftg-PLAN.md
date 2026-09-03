---
phase: quick-260903-ftg
plan: 01
type: execute
wave: 1
depends_on: [quick-260903-f2w]
files_modified:
  - app/src/components/ZoomCompositeImage.tsx
  - app/src/components/DeductionCard.tsx
  - app/src/lib/resultSections.ts
  - app/src/lib/__tests__/resultSections.test.ts
  - app/src/app/analysis/result.tsx
autonomous: true
requirements: [quick-260903-ftg]
must_haves:
  truths:
    - "역립 저신뢰(attributionReliability.unreliable=true) 문서에서 확정 확대비교 사진이 '예상 부위 (참고)' 카드로 **전부** 인라인으로 보인다 — belle pdshape 60점(813abf24)이면 왼팔꿈치·왼엉덩이 2장"
    - "카드에 관절명·statusLine·감점 수치는 없다 (07-24 IN-01 확정 설계 — per-joint 단정 강등 — 유지). 카드 탭 = 종전과 같은 시트(estimatedArea hedge)"
    - "faultZoomStatus='pending' 이고 아직 카드가 0장이면 placeholder 카드 1개, done 도착 시 onSnapshot 으로 사진 카드로 교체"
    - "저신뢰가 아닌 문서(unreliable=false/부재)는 렌더 diff 0 — topFix 카드 인라인(260903-f2w)이 그대로"
    - "합성 PNG 렌더(프레임·태그·로딩·실패·재발급)는 ZoomCompositeImage 한 컴포넌트 — DeductionCard 와 IN-01 카드가 같은 것을 소비 (사본 0)"
    - "typecheck 0 오류, node --test 기준선 215 → 신규 테스트 포함 전부 pass"
  artifacts:
    - path: "app/src/components/ZoomCompositeImage.tsx"
      provides: "합성 PNG 1장 프레임(정확 종횡비)+좌/우 태그+로딩 skeleton+실패 캡션+onError 재발급+pending placeholder"
      contains: "export function ZoomCompositeImage"
    - path: "app/src/lib/resultSections.ts"
      provides: "selectEstimatedZoomEntries — 저신뢰 경로 사진 카드 목록 선택(순수 함수)"
      contains: "export function selectEstimatedZoomEntries"
    - path: "app/src/app/analysis/result.tsx"
      provides: "IN-01 진입 링크 → 예상 부위 사진 카드 목록"
      contains: "selectEstimatedZoomEntries"
  key_links:
    - from: "app/src/app/analysis/result.tsx (IN-01 블록, 3060 부근)"
      to: "result.faultZoomComparisons"
      via: "selectEstimatedZoomEntries(records, matchZoomForRecord, isRecordHidden, estimatedAreaRecordIndex) → ZoomCompositeImage(resolveZoomImageUrl)"
      pattern: "ZoomCompositeImage"
---

<objective>
역립 저신뢰(IN-01) 경로에도 확정 확대비교 사진을 인라인으로 — 예상 부위 카드 목록(확정 카드 전부).

**실측(09-03, 시뮬 iPhone 16 Pro, belle pdshape 60점 doc 복사본):** 260903-f2w 로 topFix 카드에 사진을 배선했지만
belle 문서는 `attributionReliability.unreliable=true` 라 07-24 IN-01 확정 설계(quick-260724-q6b)대로 topFix 카드·
'다른 감점 항목' 목록이 **억제**된다. 그 경로의 확대비교 진입점은 "예상 부위 확대 비교 보기 ›" 주황 링크 1개뿐이고
(`screens/00-before-in01-entry-link-only.png`), 링크는 |points| 최대 record 1건의 시트만 연다. 확정 카드가 2장
(왼팔꿈치·왼엉덩이)이어도 두 번째는 이 경로에서 **도달 불가**. belle 09-02 "왜 확대비교 사진이 하나밖에 없어"의
실체가 이것이다.

belle 후속 결정(07-24, 260724-q6b SUMMARY "후속"): "예상 부위라도 보여줘야" → 링크+시트(크롭 유지, 관절 단정 없음).
이 작업은 그 결정의 연장: 같은 hedge 라벨("예상 부위 (참고)")로 **사진을 링크 뒤가 아니라 인라인에**, 그리고 **확정
카드 전부**. 관절명·statusLine·수치는 계속 내지 않는다(IN-01 락 유지).

**손대지 않는 것:** advisory 카드(belle 판정 대기), 매칭 규칙, 계약, 백엔드, 저신뢰 아닌 경로의 렌더, 문구 재배치(표 1·2).
</objective>

<context>
읽을 것:
- `.planning/quick/260903-f2w-topfix-png/260903-f2w-SUMMARY.md` (직전 작업 — DeductionCard zoom 모델·resolveZoomImageUrl)
- `app/src/components/DeductionCard.tsx` 전체 — 합성 PNG 렌더부(zoomFrame/zoomTag/skeleton/fallback/pending, ZOOM_COMPOSITE_ASPECT, useEffect 리셋)를 컴포넌트로 뽑는다
- `app/src/app/analysis/result.tsx` 160-182 (IN-01 상수), 1195-1256 (attributionUnreliable / estimatedAreaRecordIndex),
  2009-2013 (topFixZoom), 3040-3078 (IN-01 안내줄 + 진입 링크 블록), 3787-3806 (estimatedZoomEntry 스타일),
  `isRecordHidden` 정의(grep), 1067-1076 (freshZoomUrls/onZoomImageError)
- `app/src/lib/resultSections.ts` (순수 함수 관례 — buildRecordMaps 등) + `__tests__/resultSections.test.ts` (node:test 관례)
- `app/src/components/DeductionDetailSheet.tsx` 120-140 (ESTIMATED_AREA_TITLE = '예상 부위 (참고)' — 카드 제목과 문자 동일하게)
- `.planning/quick/260724-q6b-in-01-attributionreliability-ai/*SUMMARY.md` (IN-01 락 8면 — 무엇을 내면 안 되는지)

규율: 토큰만, 이모지 0, 라이트 전용, 한국어 주석에 출처(`quick-260903-ftg`, `IN-01`, `260724-q6b`). 계약 무접촉. 버전 범프 금지.
</context>

<tasks>

<task id="1" name="ZoomCompositeImage 컴포넌트 추출 + DeductionCard 소비">
files: app/src/components/ZoomCompositeImage.tsx, app/src/components/DeductionCard.tsx
action:
- 신규 `app/src/components/ZoomCompositeImage.tsx`:
  `export const ZOOM_COMPOSITE_ASPECT = (360 * 2 + 6) / 360;` (DeductionCard 에서 이동, lockstep 주석 유지)
  `export function ZoomCompositeImage({ imageUrl, pending = false, leftLabel = '내 영상', rightLabel, onError, accessibilityLabel }: { imageUrl?: string; pending?: boolean; leftLabel?: string; rightLabel: string; onError?: () => void; accessibilityLabel?: string })`
  · `imageUrl` 있으면: 프레임(width 100%, aspectRatio, radius.listItem, overflow hidden, softBg) + Image contain + 로딩 skeleton + 실패 캡션(태그 숨김 — f2w 실행자 판단 승계) + 좌/우 태그 + `useEffect([imageUrl])` 리셋 + onError → 실패 상태 + `onError?.()`.
  · 없고 `pending` 이면: 같은 프레임에 ActivityIndicator + '확대 비교 이미지를 준비하고 있어요' (accessibilityRole progressbar).
  · 둘 다 아니면 null. 훅은 조기 반환 전에 호출(Rules of Hooks).
  · 상수(IMG_FAILED_CAPTION / ZOOM_PENDING_CAPTION)와 스타일(zoomFrame/zoomImage/zoomSkeleton/zoomFallback*/zoomPending*/zoomTag*)을 DeductionCard 에서 **이동**(복제 아님).
- `DeductionCard.tsx`: 3) 블록을 `zoom ? <ZoomCompositeImage imageUrl={zoom.imageUrl} rightLabel={rightLabel} onError={onZoomImageError} accessibilityLabel={`내 영상과 ${rightLabel} 확대 비교 이미지`} /> : zoomPending ? <ZoomCompositeImage pending rightLabel={rightLabel} /> : null` 로 교체. 이동한 상태 훅·상수·스타일 제거(죽은 코드 0). `zoomPill` 접힘 표시는 그대로. 헤더 주석에 한 줄(quick-260903-ftg — 합성 PNG 렌더는 ZoomCompositeImage 로 이동, IN-01 카드와 공유).
verify: `cd app && npx tsc --noEmit` 0 오류; `grep -n "ZOOM_COMPOSITE_ASPECT\|zoomSkeleton\|zoomFallback" app/src/components/DeductionCard.tsx` 0건
done: DeductionCard 렌더 결과 동일(사진/placeholder/접힘 pill), 합성 PNG 렌더가 한 컴포넌트에만 존재
</task>

<task id="2" name="selectEstimatedZoomEntries 순수 함수 + 테스트">
files: app/src/lib/resultSections.ts, app/src/lib/__tests__/resultSections.test.ts
action:
- `resultSections.ts` 에 추가:
  ```ts
  export interface EstimatedZoomEntry<Z> { recordIndex: number; zoom: Z }
  export function selectEstimatedZoomEntries<R, Z>(
    records: readonly R[] | null | undefined,
    matchZoom: (record: R, index: number) => Z | null,
    zoomKey: (zoom: Z) => string,
    isHidden: (record: R) => boolean,
    primaryIndex: number | null,
  ): EstimatedZoomEntry<Z>[]
  ```
  규칙: records 순서로 훑되 `primaryIndex`(estimatedAreaRecordIndex — |points| 최대) 가 있으면 **맨 앞**; 숨김 record(스팟체크) 제외; 매칭 없음 제외; 같은 카드(`zoomKey` 동일 — 좌+우 region 묶음 카드가 두 record 에 매칭되는 경우)는 첫 등장만. 순수 함수(RN/doc 타입 의존 0 — 제네릭). 주석: quick-260903-ftg, IN-01 경로에서 확정 카드 **전부**를 카드로 내는 선택 규칙의 단일 지점.
- 테스트 4건(node:test, 기존 파일에 추가): primary 가 맨 앞 / 숨김 제외 / 같은 키 dedupe(첫 등장 유지) / 매칭 0 = 빈 배열·records null = 빈 배열.
verify: `cd app && node --test "src/lib/__tests__/*.test.*"` 219 pass 이상 fail 0
done: 함수 export + 테스트 green
</task>

<task id="3" name="result.tsx IN-01 진입 링크 → 예상 부위 사진 카드 목록">
files: app/src/app/analysis/result.tsx
action:
- import: `ZoomCompositeImage` (components), `selectEstimatedZoomEntries` (lib/resultSections — 기존 import 줄에 합침), `zoomCardKey` (lib/faultZoomUrls — 기존 import 줄에 합침; dedupe 키).
- 상수(160-182 부근): `const ATTR_ZOOM_ESTIMATED_CARD_TITLE = '예상 부위 (참고)';` — 주석: 시트 제목(DeductionDetailSheet ESTIMATED_AREA_TITLE)과 문자 동일, 관절명 없음(IN-01 락). 종전 `ATTR_ZOOM_ESTIMATED_ENTRY_LABEL` 은 accessibilityLabel 로 계속 사용.
- `estimatedAreaRecordIndex` 아래(또는 matchZoomForRecord 정의 뒤 2013 부근)에:
  `const estimatedZoomEntries = useMemo(() => attributionUnreliable ? selectEstimatedZoomEntries(records, (r) => matchZoomForRecord(r), zoomCardKey, isRecordHidden, estimatedAreaRecordIndex) : [], [attributionUnreliable, records, result.faultZoomComparisons, vetoFaultJoints, hiddenRecordIds, estimatedAreaRecordIndex])` — deps 는 recordMaps useMemo(2099 부근)와 같은 관례(eslint-disable 주석 포함). `isRecordHidden` 정의 위치를 grep 해 그 뒤에 둔다.
- IN-01 블록(3060-3078) 교체:
  · `attributionUnreliable && estimatedZoomEntries.length > 0` → entries.map: Pressable 카드(`styles.estimatedZoomCard` — advisoryOrangeBg 배경, radius.card, padding spacing.cardPadding, gap 10) 안에 제목 행(`ATTR_ZOOM_ESTIMATED_CARD_TITLE` advisoryOrange bodyMdBold + chevron ›) + `<ZoomCompositeImage imageUrl={resolveZoomImageUrl(entry.zoom, freshZoomUrls)} rightLabel={cmp.mode === 'mode1' ? `${cmp.athleteName} 선수` : '지난 영상'} onError={onZoomImageError} accessibilityLabel={`${ATTR_ZOOM_ESTIMATED_CARD_TITLE} 확대 비교 이미지`} />`. onPress → `setDetailRecordIndex(entry.recordIndex)`. key = `zoomCardKey(entry.zoom)`. accessibilityLabel = ATTR_ZOOM_ESTIMATED_ENTRY_LABEL. **관절명·statusLine·수치 렌더 금지.**
  · else `attributionUnreliable && zoomPending && estimatedAreaRecordIndex != null` → 같은 카드 1개에 `<ZoomCompositeImage pending rightLabel=... />` (탭 → 시트, 종전 pending 동작 유지).
  · 그 외 미렌더(종전과 동일 — 빈 시트 열지 않음).
- 주석: IN-01 락(260724-q6b) 유지 선언 + 09-03 실측(사진 2장인데 1장만 도달) 인용. 종전 링크 전용 스타일(estimatedZoomEntry/Pressed/Text/Chevron) 중 카드 제목 행에 재사용되는 것은 유지, 안 쓰이면 제거.
- 저신뢰 아닌 경로 무접촉 (topFix 블록·다른 감점 항목 블록 diff 0).
verify: `cd app && npx tsc --noEmit` 0; `node --test "src/lib/__tests__/*.test.*"` fail 0; `git diff --stat` 이 이 태스크에서 result.tsx 만
done: 저신뢰 문서에서 확정 카드 수만큼 사진 카드가 인라인 렌더, 탭 시 각자의 시트
</task>

</tasks>

<verification>
- tsc 0 · node --test ≥219 pass / 0 fail
- `grep -rn "ZOOM_COMPOSITE_ASPECT" app/src` → ZoomCompositeImage.tsx 정의 1곳(+ 소비처 import 만)
- 시뮬 실물(오케스트레이터 후속, Metro Fast Refresh): belle pdshape 복사본에서 "예상 부위 (참고)" 카드 2장(왼팔꿈치·왼엉덩이 합성 PNG), 탭 → 시트. 스크린샷 `screens/`.
</verification>

<success_criteria>
- IN-01 경로 확정 사진 전부 인라인, per-joint 단정 0, 비저신뢰 경로 diff 0, 렌더 컴포넌트 단일화.
- 커밋 3개(태스크당 1개, 코드만). docs 커밋은 오케스트레이터.
</success_criteria>

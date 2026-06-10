# Phase 12: 실측 각도 + 키포인트 오버레이 + UIUX 한번에 — UI Design Contract

**Generated:** 2026-06-10
**Status:** Locked
**Mode:** mvp
**Source:** 12-CONTEXT.md (D-12-A1..U6) + Figma spike (4-frame section, Claude 박제 2026-06-10) + design.md + Phase 12.5 패턴 1:1 mirror

---

## 0. Visual Reference

**Figma fileKey:** `jrdI7kp245HkPfLB0nclsz`
**Section node:** `94:506` — "Phase 12 - 실측 각도 + 키포인트 오버레이 (Claude 박제, 2026-06-10)"
**Frames (4)**:
- `94:508` (frame01) — mode1 결과 화면 (정은지 비교)
- `106:506` (frame02) — mode3 first 결과 화면 (첫 분석)
- `(03 frame)` (frame03) — mode3 progress 결과 화면 (발전 비교)
- `105:506` (frame04) — ForcePatternCard 자세히 모달

**Phase 12.5 reference section:** `73:506` (frame patterns mirror — 차원 카드 / 모달 / disclaimer / gauge 패턴 source)

**Design.md fallback:** Figma 없는 영역은 design.md + Phase 12.5 코드 (`app/src/components/`) 자체 판단.

---

## 1. Brand Tokens (변경 금지)

| Token | Value | 출처 |
|---|---|---|
| `colors.brand` | `#FF4B33` | CLAUDE.md §4 (변경 금지) |
| `colors.brandSoft` | `#FFD9D2` | Phase 9 카드 작은 chip 배경 |
| `colors.brandBg` | `#FFE5E0` | 옥타곤 outer ring 톤 |
| `font` | Pretendard | CLAUDE.md §4 |
| theme | light only | CLAUDE.md §4 / design.md §10 |
| `colors.textHi` | `#1A1A1A` | 본문 |
| `colors.textMid` | `#5A5A5A` | sub 본문 |
| `colors.textLo` | `#888888` | hint / footer |
| `colors.border` | `#E0E0E0` | 카드 테두리 |
| `colors.softBg` | `#F5F5F5` | jointHint chip / unknown chip 배경 |
| `colors.trackBg` | `#EBEBEB` | 점수 트랙 배경 |
| `colors.estimateGray` | `#B0B0B0` | 저신뢰 "추정 N°" 컬러 |
| `colors.progressGreen` | `#22B47A` | mode3_progress +N점 발전 |
| `colors.progressRed` | `#E64545` | mode3_progress -N점 후퇴 |
| `colors.warnAmber` | `#E6A300` | ⚠ occlusion badge |
| `colors.videoBg` | `#2A2A2A` | 영상 카드 배경 (다크 예외 — design.md §5-1) |

**모든 색은 `src/theme/colors.ts` 토큰화 — 하드코딩 금지 (CLAUDE.md §4 + `[[ui-figma-first]]` 정합).**

---

## 2. Spacing / Layout Tokens

| Token | Value | 적용 |
|---|---|---|
| screen padding | 16pt | iPhone safe area 좌우 |
| content width | 358pt | 390 - 16*2 (frame 너비 - padding) |
| card padding | 16-20pt | 카드 내부 padding |
| card inner width | 326pt | content - 16*2 (카드 안 inner) |
| card radius | 15pt | 큰 카드 (design.md §5-4) |
| small card radius | 12pt | 작은 카드 (Phase 9 finding[1..2]) |
| chip radius | 9-11pt | pattern / joint chip |
| section gap | 28pt | 영역 간 (예: 영상 → 원인 카드) |
| inner gap | 12-16pt | 카드 내부 row gap |
| stroke weight | 1pt | 카드 테두리 |

**Typography (Pretendard)**:
| 용도 | Size | Weight |
|---|---|---|
| 점수 (옥타곤 가운데) | 56pt | Bold |
| section label | 16pt | Semi Bold |
| section sub | 11pt | Regular |
| card 본문 (finding[0]) | 14-16pt | Semi Bold |
| card 본문 (finding[1..2]) | 11pt | Regular |
| 각도 수치 | 13-14pt | Semi Bold |
| chip text | 9-11pt | Medium / Semi Bold |
| disclaimer / footer | 11pt | Regular |
| confidence label | 10-12pt | Medium |

---

## 3. Screen Layout — 6 영역 + footer (D-12-A1 정합)

### 위에서 아래 순서 (모든 mode 공통):

```
┌──────────────────────────────────────────────┐
│ 0. Disclaimer (상단 footer 카피)              │
│    "이 분석은 강사 수업을 대체하지 않아요"     │
├──────────────────────────────────────────────┤
│ 1. 점수 게이지 (옥타곤)                       │
│    Phase 12.5 vector clone (74:507) 그대로    │
├──────────────────────────────────────────────┤
│ 2. (mode3_first/progress only) 인사이트 카드  │
│    - mode3_first: "첫 분석이에요" + 안내      │
│    - mode3_progress: "+N점 발전" + 요약        │
├──────────────────────────────────────────────┤
│ 3. 영상 + 키포인트 오버레이 (Phase 12 신규)    │
│    - mode1: 정은지+사용자 split (2-up)        │
│    - mode3: 사용자만 single                   │
│    - 토글 (디폴트 ON), 키포인트 + bone +      │
│      delta 강조 + floating angle label        │
├──────────────────────────────────────────────┤
│ 4. Phase 9 원인 카드 Top-3 (신규)             │
│    - finding[0] = 큰 카드 (358×168)           │
│    - finding[1..2] = 작은 카드 가로 (174×110) │
│    - tap → 자세히 모달                        │
├──────────────────────────────────────────────┤
│ 5. 세부 점수 (12.5 mirror + ⚠ + 가림 카피)   │
│    - mode1: 차원 3개 (각도 정확도 / 팔다리 /  │
│      안정성)                                  │
│    - mode3_first: 차원 2개 (베이스라인 없음)  │
│    - mode3_progress: 차원 3개 + delta 표기    │
│      (지난 분석 대비 +N / -N)                  │
├──────────────────────────────────────────────┤
│ 6. 각도 가이드 (Phase 12 신규, 5 joint 그룹*)  │
│    - 어깨 / 골반 / 무릎 / 손 + 중심축          │
│    - "현재 N° → 기준 M°" 형식                 │
│    - 저신뢰 frame "추정 N°" + ⓘ              │
│    - mode 분기 기준:                          │
│      · mode1 = 정은지 measured                │
│      · mode3_first = IPSF baseline            │
│      · mode3_progress = 이전 영상 measured +  │
│        delta (+N° / -N°)                      │
├──────────────────────────────────────────────┤
│ 7. Footer                                     │
│    "분석 결과는 강사와 함께 확인해 보세요."   │
└──────────────────────────────────────────────┘
```

### 영역별 세부 spec

**1. 점수 게이지 (gauge-wrap, 358×210)**:
- 80×210 위치에 옥타곤 polygon 4개 (Phase 12.5 vector clone)
- 가운데 점수 56pt Bold brand 컬러
- 아래 "내 점수" 13pt Medium textLo
- 옥타곤 fill = 점수 % 비례 (예: 81 = 81% brand, 19% track)

**2. 영상 + 오버레이 (video-compare-with-overlay)**:
- 358×220 카드, 배경 `colors.videoBg`, radius 15pt
- 상단 라벨 (11pt Medium WHITE 0.7) — mode1: "정은지 선수 vs 내 자세 (키포인트 오버레이)" / mode3: "내 영상 (키포인트 오버레이)"
- 우상단 토글 (46×22, brand bg ON / soft bg OFF)
- 영상 영역:
  - mode1: split 2 video (158×158 each, gap 8pt) — 좌 정은지, 우 사용자
  - mode3: single full-width video (326×158)
- 키포인트 (KeypointOverlay component — §5 참조)

**3. 인사이트 카드 (mode3_first/progress only, 358×112)**:
- mode3_first: 좌측 ! badge (24×24 brand ellipse + 흰 글자) + 제목 14pt Semi Bold "첫 분석이에요" + 본문 12pt Regular "다음 영상부터 발전을 비교해 드려요..."
- mode3_progress: 좌측 ↑ badge (24×24 PROGRESS_GREEN ellipse + 흰 글자) + 제목 14pt "지난 분석보다 +N점 발전했어요" + 본문 12pt "특히 X 에서 큰 성장이 보여요..."

**4. Phase 9 원인 카드 (§4 ForcePatternCard 참조)**

**5. 세부 점수 (detail-scores, 358×320 mode1/progress / 220 first)**:
- Phase 12.5 frame 의 `detail-scores` 패턴 1:1 mirror
- 각 차원 row: 이름 14pt Medium + 점수 20pt Semi Bold + track bar (8pt height, brand fill % 비례) + sub + "자세히 ›" + deficit 본문
- ⚠ occlusion badge: 차원 이름 우측 inline (12pt amber, 발현 조건 = 해당 차원 frame 중 occlusion 추정 ≥ 20%)
- mode3_progress delta: 점수 아래 11pt Semi Bold "지난 분석 대비 +N점" (초록) / "-N점" (빨강)

**6. 각도 가이드 (angle-guide-card, 358×184-226 가변)**:
- 5 joint **그룹** × row (어깨/골반/무릎/손 좌우 평균 + 중심축 — UI 표시상 5 그룹, R11 정합. KeypointReport 의 8 keypoint + axisData 로부터 산출). 16pt y간격, divider 1px BORDER
- row 구성: 이름 13pt Medium + 현재 14pt Semi Bold + → + 기준 13pt Medium
- 저신뢰: 현재 "추정 N°" estimateGray + ⓘ 14×14 회색 ellipse (tap → tooltip)
- mode 분기:
  - mode1: "기준 110°" (정은지 측정값)
  - mode3_first: "IPSF ≥ 175°" (IPSF baseline)
  - mode3_progress: "지난 N°" + 우측 delta (+/- 초록/빨강 12pt Semi Bold)

---

## 4. Component Spec — `ForcePatternCard` (신규)

**Location:** `app/src/components/ForcePatternCard.tsx`

### Props

```typescript
type ForcePatternCardProps = {
  finding: ForcePatternFinding;  // Phase 9 산출
  rank: 0 | 1 | 2;                 // 카드 순위
  variant: 'big' | 'small';        // big = finding[0], small = finding[1..2]
  onTap: () => void;               // tap → 자세히 모달
};
```

### Variants

#### `variant='big'` (finding[0]) — 358×168
```
┌────────────────────────────────────────────┐
│ #1  [RELEASE]  [몸 중심]      신뢰도 높음  │  (20pt padding)
│                                            │
│ 정은지 선수 기준 패턴과 비교했을 때, 몸    │
│ 중심이 옆으로 기울며 중심 잡는 힘이 약해   │
│ 지는 모습이 보여요.                        │  (14pt Semi Bold, lineHeight 22)
│                                            │
│                          탭하여 자세히 보기 →│
└────────────────────────────────────────────┘
```

- 카드: WHITE bg, BORDER stroke 1pt, radius 15pt
- `#N` 11pt Semi Bold textLo
- pattern chip (62×22): brand bg, "RELEASE" 9pt Semi Bold WHITE, radius 11pt — pattern 별 색 매핑 §6
- jointHint chip (78×22): softBg + 11pt Medium textHi (jointHint 일반어 — 몸 중심/엉덩이 관절/허벅지 안쪽/등 근육)
- confidence label (우측): "신뢰도 높음/보통/낮음" 10pt Medium, brand (높음) / textMid (보통) / textLo (낮음) — confidence: ≥0.7 높음 / 0.4~0.7 보통 / <0.4 낮음
- 본문: `finding.interpretation` 14pt Semi Bold textHi, lineHeight 22
- 하단 hint: 11pt Regular textLo "탭하여 자세히 보기 →" 우측 정렬

#### `variant='small'` (finding[1..2]) — 174×110
```
┌──────────────────────────┐
│ #2  [BRACE]              │
│ 허벅지 안쪽              │  (12pt jointHint sub-label)
│                          │
│ 다리가 봉에 닿는 타이밍이│  (11pt Regular, 2-line clamp)
│ 늦어지는 모습            │
└──────────────────────────┘
```

- 카드: WHITE bg, BORDER stroke 1pt, radius 12pt
- pattern chip 색 = brand 가 아닌 pattern → `brandSoft` bg + brand text (시각 hierarchy — finding[0] 보다 약함)
- jointHint = 본문 위 sub-label (10pt Medium textMid)
- 본문: `finding.interpretation` 11pt Regular textHi, lineHeight 17, 2-line clamp

#### Edge cases (findings.length)

- `0` finding: `variant='big'` 카드 1개만 표시, body = `_FALLBACK_BODY` ("이 영상에서는 분명한 힘 흐름 이슈 신호가 보이지 않습니다. 강사와 함께 확인하는 것을 권장해요."), confidence label = "신뢰도 낮음" textLo, chip 영역 = 단일 "정보" textMid chip
- `1` finding: `variant='big'` 1개만, 작은 카드 slot 비움
- `2` finding: `variant='big'` 1개 + `variant='small'` 1개 (왼쪽), 오른쪽 slot 비움
- `3` finding: 모두 표시 (현재 spec)

### A11y

- `accessibilityRole='button'`
- `accessibilityLabel='실패 원인 #{rank+1}, {pattern}, {jointHint}, 자세히 보려면 탭'`
- `hitSlop={8}`

---

## 5. Component Spec — `KeypointOverlay` (신규)

**Location:** `app/src/components/KeypointOverlay.tsx`

### Props

```typescript
type KeypointOverlayProps = {
  videoSize: { width: number; height: number };  // 비디오 native size
  videoCurrentTime: number;                       // expo-video currentTime hook
  keypoints: KeypointFrame[];                     // frame-by-frame (x, y, confidence) 데이터
  referenceKeypoints?: KeypointFrame[];           // mode1 only — 정은지 데이터 비교
  mode: 'mode1' | 'mode3';
  deltaThresholdDeg?: number;                     // default 10
};
```

### Rendering

- `react-native-svg` `<Svg>` element, absolute positioning over `<expo-video>`
- viewBox = `videoSize` (e.g. "0 0 720 1280")
- **8 body keypoints** (R11 정합): `shoulder_left/right`, `hip_left/right`, `knee_left/right`, `hand_left/right` — Phase 12 KEYPOINT_NAMES Literal 8 (axis 는 별도 contract).
- **axis polyline** (R2 정합 — 별도 `axisData`): `shoulder_mid ↔ hip_mid ↔ knee_mid?` (3-point polyline). 12-00 `compute_axis_frames()` 산출, KeypointReport.axisData flat array (T × 3 × 2). knee_mid 가 None 인 frame 은 2-point 만 렌더.
- 각 joint = `<Circle>` 10pt radius (디자인 mockup 기준 — viewBox 좌표로 변환)
- 각 bone = `<Line>` 1.8pt stroke (강조 시 3pt)
- 컬러: 기본 WHITE stroke `#000` 0.6 / 강조 brand `#FF4B33`

### delta 강조 룰 (D-12-C3)

```typescript
// Per-joint delta 계산
const delta = Math.abs(currentJointAngle - referenceJointAngle);
const highlighted = delta >= deltaThresholdDeg;  // default 10°
```

- mode1: `referenceJointAngle` = 정은지 keypoint angle
- mode3_first: `referenceJointAngle` = IPSF baseline (joint 별 fixed)
- mode3_progress: `referenceJointAngle` = 이전 영상 keypoint angle

강조된 joint 의 keypoint + 연결 bone = brand 컬러, stroke weight 3pt.

### Floating angle label (강조된 joint 옆)

- 강조된 joint 1개당 floating label (`<G>` + `<Rect>` + `<Text>`):
  - 위치: keypoint 우측 +12pt
  - 크기: 48×18, brand bg, radius 9
  - 텍스트: "88°" 10pt Semi Bold WHITE (현재 각도)
  - mode1 reference 측에는 동일 위치에 다른 컬러 ("110°" textHi on WHITE 0.85)

### Frame 동기화

- `videoCurrentTime` (초) → `Math.floor(currentTime * frameRate)` index 로 `keypoints[index]` lookup
- 비디오 native fps vs JS fps mismatch 시 latest available frame 사용 (researcher 가 best practice 확인)

### Fallback

- `keypoints` 없거나 빈 배열 → `<View>` placeholder (검은 배경 + "키포인트 데이터 미가용" 흰 글자 12pt) — D-12-U6 정합

### A11y

- `accessibilityElementsHidden={!visible}` (토글 OFF 시)
- 별도 a11y label 없음 (시각 보조 layer)

---

## 6. Pattern Chip Color Map (Phase 9 6 pattern)

| pattern | finding[0] 큰 카드 | finding[1..2] 작은 카드 |
|---|---|---|
| `release` | brand bg + WHITE text | brandSoft bg + brand text |
| `pull` | brand bg + WHITE text | brandSoft bg + brand text |
| `push` | brand bg + WHITE text | brandSoft bg + brand text |
| `brace` | brand bg + WHITE text | brandSoft bg + brand text |
| `rotate` | brand bg + WHITE text (v2 enum 박제만, 발현 0) | brandSoft bg + brand text |
| `unknown` | softBg + textMid text | softBg + textMid text |

**Why `unknown` 차별**: high_jerk / high_jitter signal 은 부위 불명확 — UX 시각적 차별로 "신뢰 비교적 낮음" 의도 전달.

---

## 7. 모달 Spec — ForcePatternCard 자세히 (frame04 reference, 358×620)

**Location:** `app/src/components/ForcePatternDetailModal.tsx` (또는 기존 `DimensionDetailModal.tsx` 패턴 mirror 신설)

### Layout

```
┌──────────────────────────────────────────────┐
│ — (40×4 handle, BORDER, radius 2)           │
│                                              │
│ 실패 원인 #1                          ✕     │  (18pt Semi Bold + 닫기)
│                                              │
│ [RELEASE]  [몸 중심]            신뢰도 높음  │  (chips + confidence)
│                                              │
│ 정은지 선수 기준 패턴과 비교했을 때, 몸     │
│ 중심이 옆으로 기울며 중심 잡는 힘이 약해   │  (16pt Semi Bold lineHeight 26)
│ 지는 모습이 보여요.                          │
│                                              │
│ 💬 강사가 함께 보면 더 구체적 피드백을      │  (12pt Regular textLo)
│ 받을 수 있어요                              │
│                                              │
│ ┌──────────────────────────────────────────┐│
│ │ 이 원인은 어떻게 측정됐나                ││  (softBg card, 13pt + 12pt)
│ │ lock 단계에서 어깨 기울기가 25° 측정됐어요.││
│ │ IPSF 폴스포츠 기준 = 20° 이내.             ││
│ └──────────────────────────────────────────┘│
│                                              │
│ • 관련 부위 — 몸 중심 (코어 안정)            │  (13pt Medium)
│ • 확인하기 — 거울 보며 동작 직접 재현       │
│                                              │
│ ┌──────────────────────────────────────────┐│
│ │ AI 가 추정한 가능성이에요. 강사 수업과    ││  (brandSoft 0.5 bg, 11pt Regular)
│ │ 함께 확인하면 가장 정확한 피드백을 받을   ││
│ │ 수 있어요.                                 ││
│ └──────────────────────────────────────────┘│
│                                              │
│ ┌──────────────────────────────────────────┐│
│ │              닫기                          ││  (brand bg, 16pt Semi Bold WHITE)
│ └──────────────────────────────────────────┘│
└──────────────────────────────────────────────┘
```

### Behavior

- Bottom sheet — `react-native` `Modal` + `transparent={true}` + 반투명 검정 backdrop
- Backdrop tap → 닫기
- 핸들 swipe down → 닫기 (Phase 12.5 일관)
- "어떻게 측정됐나" 본문 = `finding.reason` (EN — Phase 11 통합 시 KO 자연어 풍부화)

### Phase 11 통합 자리

- `finding.interpretation` = canned KO (현재) → LLM 풍부화 산출 (Phase 11 통합 시 자동 교체)
- `finding.reason` = EN debug (현재 모달 안 KO 한 줄 정도 노출) → LLM 풍부화 시 더 자세한 KO 본문

---

## 8. State & Interaction

### Toggle (overlay ON/OFF)

- 영상 카드 우상단, 46×22 toggle
- AsyncStorage key `@sunity:keypoint_overlay_enabled` (R8 정합 — keypoint overlay 토글로 scope narrow), default `true`
- OFF 시: KeypointOverlay `visible={false}` → SVG 렌더 0 (성능 절약)
- ON 시: KeypointOverlay 렌더 + 영상 frame 동기화

### 스크롤 동작

- 결과 화면 = single `ScrollView`
- 점수 게이지 = 상단 고정 X (스크롤됨 — 일반 흐름)
- 영역 간 gap = 28pt
- 최하단 footer 후 16pt safe area bottom

### Tap → 모달

- ForcePatternCard tap → `ForcePatternDetailModal` open
- 차원 카드 "자세히 ›" tap → `DimensionDetailModal` open (기존 Phase 12.5)
- 각도 가이드 row tap → 별도 액션 없음 (단순 display)
- ⓘ 저신뢰 아이콘 tap → tooltip ("이 구간은 가림 또는 측정 불확실로 추정값입니다.")

### Loading state

- 분석 진행 중 = `analysis/loading.tsx` 다른 화면 (Phase 12 영역 X)
- 결과 화면 진입 시 `analysisDoc.status === 'done'` 확인 후 렌더 (기존 패턴)

### Error state

- `analysisDoc.error` 있을 시 = 결과 화면 진입 X (loading 화면이 에러 → re-analyze 분기)
- `forceSignalsReport === undefined` (예: 백엔드 미완 영상) → 영상+오버레이 영역 placeholder + Phase 9 카드 영역 fallback ("분석이 부분적으로 완료됐어요")

---

## 9. Mode 분기 룰 (D-12-D6 정합)

### mode1 (정은지 비교)

- 영상: split (좌 정은지 / 우 사용자)
- 인사이트 카드: 없음
- 원인 카드: `modeContext='mode1'`, interpretation prefix "정은지 선수 기준 패턴과 비교했을 때, ..."
- 세부 점수: 차원 3개, baseline = 정은지
- 각도 가이드: "현재 N° → 기준 M°" (정은지 measured)

### mode3_first (첫 분석)

- 영상: single (사용자만)
- 인사이트 카드: "첫 분석이에요" + IPSF baseline 비교 안내
- 원인 카드: `modeContext='mode3_first'`, interpretation prefix "이번 첫 분석에서, ..."
- 세부 점수: 차원 2개 (각도 일관성 차원 없음 — 비교 baseline 부재)
- 각도 가이드: "현재 N° → IPSF ≥ M°" (IPSF baseline)

### mode3_progress (발전 비교)

- 영상: single (사용자만)
- 인사이트 카드: "지난 분석보다 +N점 발전했어요" + 요약
- 원인 카드: `modeContext='mode3_progress'`, interpretation prefix "지난 영상 대비, ..."
- 세부 점수: 차원 3개 (각도 일관성 차원 포함), delta 표기 "지난 분석 대비 +N점" / "-N점" (초록/빨강)
- 각도 가이드: "현재 N° → 지난 M°" + delta (+/-N°)

### 백엔드 자동 분기 (UI 분기 코드 최소화 — D-12-U3)

- `analysisDoc.mode` + `_select_mode_context` helper (pipeline 안 inline 박제, RESEARCH Pitfall 3) → `forcePatternInference.modeContext` 박제
- UI 는 `modeContext` 읽고 interpretation 그대로 렌더 (분기 코드 0)
- 세부 점수 / 각도 가이드 baseline 도 동일 — backend `assemble.py` 가 mode 별 dimensionExplanation 출력

---

## 10. Edge Cases

### 영상 데이터 가용성

- `analysisDoc.angles` (flat) + 신설 `analysisDoc.keypoints` (flat) 둘 다 필요
- `keypoints` 없으면 → 영상 영역 placeholder ("키포인트 데이터 미가용 — 영상만 표시") + 오버레이 layer 렌더 X
- `referenceKeypoints` 없으면 (mode1 시) → split 영상 유지하되 정은지 측 오버레이만 X (사용자 측은 그대로)

### Firestore nested-array

- `keypoints` 저장 = flat (`{joints: [...], frames: N, data: [x0,y0,x1,y1,...]}`) per [[firestore-nested-array-flat]]
- 읽기 = `userAnalyses.ts::normalize` 가 reshape (R11 정합 — 8 body keypoint × N frame × 2 axis + 별도 axisData T × 3-point × 2)
- `referenceKeypoints` 도 동일 패턴 (mode1 시 reference doc 의 동일 schema)

### 점수 게이지 mode3 차이

- mode3 도 옥타곤 게이지 동일 — Phase 12.5 의 mode3_first/progress frame 도 동일 게이지 사용 (gauge clone)
- 단 mode3_progress 는 옥타곤 fill % 가 현재 점수 (이전 영상 점수 비교는 인사이트 카드만)

### Confidence 분류 (Phase 9 finding)

- finding 본문 confidence 분류 = §4 ForcePatternCard 의 confidence label
- 동일 분류를 영상 위 floating angle label 색에도 적용? **NO** — floating label 은 delta 크기 강조용 (≥ 10° = brand, < 10° = WHITE), confidence 와 무관

### 0 finding edge case

- Phase 9 `findings.length === 0` 시 단일 큰 카드 ("이 영상에서는 분명한 힘 흐름 이슈 신호가 보이지 않습니다...") 표시
- 작은 카드 slot 비움 (렌더 X — UI 가 자동 분기)
- 점수 게이지 / 세부 점수 / 각도 가이드 는 정상 표시

### 영상 길이 짧음

- 영상 < 3초 (분석 최소 길이 미달) → 결과 화면 진입 X, 에러 분기 (기존)

---

## 11. Accessibility

| 영역 | a11y label |
|---|---|
| 점수 게이지 | "내 점수 81점" + `accessibilityRole='text'` |
| 영상 카드 | "분석 영상. 키포인트 오버레이 토글." |
| 토글 | "키포인트 오버레이. 현재 켜짐. 끄려면 두 번 탭." (`accessibilityRole='switch'`) |
| 원인 카드 | "실패 원인 #1. RELEASE. 몸 중심. 신뢰도 높음. 자세히 보려면 탭." (`accessibilityRole='button'`) |
| 차원 카드 | "각도 정확도 80점. 자세히 보려면 탭." |
| 각도 가이드 row | "오른쪽 어깨. 현재 88도. 기준 110도." (text only) |
| ⓘ 저신뢰 | "추정값. 정확도 낮음. 설명 보려면 탭." (`accessibilityRole='button'`) |
| ⚠ occlusion | "가림 추정 경고. 설명 보려면 탭." (`accessibilityRole='button'`) |

---

## 12. 안티 패턴 (절대 금지)

- ❌ 다크 테마 (CLAUDE.md §4 / design.md §10) — 영상 카드 배경만 예외
- ❌ #FF4B33 외 다른 brand color (변경 금지)
- ❌ Pretendard 외 폰트 사용
- ❌ 하드코딩된 색/spacing/radius (모두 토큰)
- ❌ 박제 단어 카피 안 들어감 ([[no-baekje-filler]])
- ❌ "%일치" / "유사도" 표현 ([[mode3-progress-not-similarity]])
- ❌ Phase 9 finding 카피 직접 수정 (canned KO 출처 = `force_pattern_copy.py`)
- ❌ UI 단 mode 분기 코드 (backend modeContext 자동 분기 — D-12-U3)
- ❌ 영상 위 각도 라벨 = 직접 측정값 (백엔드 산출만 사용 — 자체 계산 X)
- ❌ 키포인트 좌표 (x, y) 직접 계산 (백엔드 산출만 read)
- ❌ 이모지 (CLAUDE.md §7) — 단 footer 의 💬 같은 안내 이모지는 design.md §10 의 한정 예외 (검수 후 결정)

---

## 13. Pre-existing component reuse

| 영역 | 기존 component (재사용) |
|---|---|
| 점수 게이지 | `OctagonScore.tsx` (Phase 12.5) — 그대로 |
| 차원 카드 | `result.tsx` 안 detail-scores 영역 (Phase 12.5) — 그대로 + ⚠ badge 추가 |
| 차원 모달 | `DimensionDetailModal.tsx` (Phase 12.5) — 그대로 |
| 영상 카드 | `VideoCompare.tsx` (확장 — KeypointOverlay slot 추가) |
| 코칭팁 모달 | `CoachingTipDetailModal.tsx` (Phase 12.5) — 별도 (Phase 9 모달과 분리) |
| 성장 차트 | `GrowthChart.tsx` (Phase 12.5) — 그대로 (mode3 progress 의 영역 6 후) |
| 결과 화면 본체 | `result.tsx` — 6 영역 layout 재정비 (component 분리 + 끼워넣기) |

---

## 14. 신설 파일

| Path | Role |
|---|---|
| `app/src/components/KeypointOverlay.tsx` | 신규 component — §5 |
| `app/src/components/ForcePatternCard.tsx` | 신규 component — §4 |
| `app/src/components/ForcePatternDetailModal.tsx` | 신규 component — §7 |
| `app/src/lib/keypointSync.ts` (옵션) | helper — expo-video currentTime → keypoint frame index |

---

## 15. Backend 의존 (Wave 0 작업)

- `assemble.py::build_result` — 모든 joint currentAngle/targetAngle 채움 (현재 부분 wired)
- 신설 `keypoints` 필드 (flat) — Firestore 저장 + `userAnalyses.ts::normalize` reshape
- `forcePatternInference.modeContext` — pipeline `_process` 가 mode 별 자동 박제 (Phase 9 완료)
- `forcePatternInference.findings[].confidence` — 0/1 range, UI 가 그대로 신뢰도 분류

---

## 16. Validation

UI 단위 test (Wave 1 책임 — planner 가 구체화):

- `KeypointOverlay` snapshot 회피 (시각 회귀로 자주 깨짐) — 대신 props → 렌더 element 카운트 + 강조 joint id assertion
- `ForcePatternCard` variant `big`/`small` 분기 + chip color 패턴별 assertion + 0/1/2/3 finding edge case
- `ForcePatternDetailModal` open/close + finding props 표시 assertion
- `result.tsx` 영역 순서 (1-7) snapshot — 영역 순서 회귀 차단

타입 검증:
- `cd app && npm run typecheck` → 0 error (TS strict mode)
- 3-way contract lockstep — `analysis.ts` ↔ `models.py` ↔ `docs/contract.md` neuron 정합 (Wave 0 책임)

---

## 17. Open Questions (planner 영역)

- expo-video Expo SDK 54 의 currentTime hook API 정확한 형식 (`useVideoPlayer` vs deprecated API)
- react-native-svg overlay 위 비디오 frame 동기화 fps drift 처리 best practice
- KEYPOINT_DELTA_HIGHLIGHT_DEG = 10.0 임계값 sensitive 검증 (실증 테스트 시점 belle 검수 — `12-deferred-items.md` 박제)
- `keypoints` Firestore vs Storage 저장 위치 (60s × 30fps × 9 keypoint × 2 axis = 32400 number — Firestore 1MB 검토)
- 성장 차트 (영역 7) 위치 미세 조정 (차원 카드 ↔ 각도 상세 사이로 이동 가능성)
- 한국어 stick figure mockup 의 폴 (수직 막대) 표시 여부 — Figma frame 에는 없으나 실제 폴댄스 영상 위 = 폴 keypoint 추가 가능 (v2 deferred 가능)

---

*Locked: 2026-06-10 (Claude 박제, Figma 4-frame 시각 reference + 12-CONTEXT.md D-12-* 결정 + design.md + Phase 12.5 코드 패턴 1:1 mirror)*

# Phase 26: 온보딩·기대설정 + 원본 업로드 가이드 - Pattern Map

**Mapped:** 2026-07-07
**Files analyzed:** 12 (신규 4 / 수정 8)
**Analogs found:** 10 / 12 (스와이프 튜토리얼 페이저·체크박스 행은 코드베이스에 무존재 — 부분 아날로그 명시)

> 전제: 이 phase는 **앱만** 건드린다 (D-01, 백엔드/채점 무접촉). opt-in 동의값(D-08/D-09)은
> 앱이 직접 쓰는 Firestore 필드로 해결 가능 — 문서 생성은 앱 몫(`loading.tsx` `setDoc`)이므로
> Lambda 코드 변경 불필요. 단 `AnalysisDoc` 계약 필드를 추가하면 3-way lockstep
> (`app/src/types/analysis.ts` + `backend/shared/python/sunity_shared/models.py` + `docs/contract.md`) 준수.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/src/app/tutorial.tsx` (신규, S1) | route/screen | UI flow (swipe pager) | `app/src/app/index.tsx` (풀스크린 CTA 골격) + Figma 프레임 | partial — 페이저 무아날로그 |
| `app/src/lib/onboarding.ts` (신규, S1 첫실행 플래그) | utility (local storage) | key-value read/write | `result.tsx:972-990` AsyncStorage 사용례 | exact |
| `app/src/app/analysis/samples.tsx` (교체, S2 이용방법/FAQ) | route/screen | static content list | `samples.tsx` 자체 골격 (in-place) | exact |
| `app/src/components/WarningDialog.tsx` 또는 analyze.tsx 인라인 (신규, S4 카톡 경고) | component (modal) | request-response (confirm/cancel) | `analyze.tsx:386-422` lqCard 모달 + `BodyProfilePromptModal.tsx` | exact (로직) / Figma (비주얼) |
| `app/src/components/OptInCheckRow.tsx` 또는 analyze.tsx 인라인 (신규, S3) | component (controlled input) | controlled state | `KeypointOverlayToggle.tsx` (controlled + a11y) | role-match — checkbox 무아날로그 |
| `app/src/app/(tabs)/analyze.tsx` (수정, S3/S4/S5) | route/screen | pick→validate→route | 자체 (in-place) — `_talkv_` 감지·프라이버시 1줄·거리 안내 삽입 | exact |
| `app/src/app/analysis/loading.tsx` (수정, S6 + opt-in 저장) | route/screen | upload orchestration + Firestore subscribe | 자체 (in-place) — 에러 계층·lowQuality 분기·setDoc | exact |
| `app/src/app/index.tsx` (수정, 첫실행→튜토리얼 라우팅) | route/entry | auth bootstrap → route | 자체 (in-place) | exact |
| `app/src/types/analysis.ts` (수정, 동의 필드) | contract types | — | `AnalysisDoc.bodyProfile` 필드 추가 선례 (589-610행) | exact |
| `app/src/app/(tabs)/index.tsx` (수정, F4 공지 간격/카피) | route/screen | Firestore subscribe → render | 자체 (in-place) newsBanner 337-356행 | exact |
| `app/src/theme/colors.ts` (수정 가능, Figma 다이얼로그 토큰 신설) | config (tokens) | — | 자체 — Phase 12/10 토큰 신설 주석 패턴 (37-83행) | exact |
| F3 기타+자유입력 대상 지점 (플래너 재량) | route/screen (form) | controlled form | `inquiry.tsx` chip 단일선택 + TextInput | exact |

라우팅 등록: expo-router 파일 기반 — `app/src/app/` 에 파일을 만들면 라우트 자동 생성.
루트 `_layout.tsx` 는 `<Stack screenOptions={{ headerShown: false }} />` 단일 선언이라 **수정 불필요**.

---

## Pattern Assignments

### `app/src/app/tutorial.tsx` (screen, 스와이프 튜토리얼 — S1)

**Analog:** 비주얼 = Figma 프레임(계약, fileKey `jrdI7kp245HkPfLB0nclsz`). 코드 골격 = `app/src/app/index.tsx` + `analyze.tsx`.
코드베이스에 `pagingEnabled` ScrollView/FlatList 페이저가 **0건** — 페이저 자체는 신규 작성 (RN 코어 `ScrollView horizontal pagingEnabled`, 신규 라이브러리 도입 금지 — UI-SPEC Registry Safety).

**파일 헤더 주석 + import 패턴** (`index.tsx:1-11`) — 모든 화면이 이 형식:
```typescript
import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, gradients, layout, radius, spacing, typography } from '../theme';

// 인트로 — 파일럿 최소 게스트 진입 (plan.md #3, design.md §1·§5-1·§6·§10).
// (한국어 블록 주석으로 why + 스펙 인용 — design.md §N / D-NN 형식으로 인용할 것)
```

**CTA 버튼 패턴** (`index.tsx:98-106` — "시작하기" CTA에 그대로 적용):
```typescript
cta: {
  height: layout.ctaHeight,          // 54
  borderRadius: radius.button,       // 13
  backgroundColor: colors.brand,     // 흰 배경 위 = brand filled (그라디언트 위면 흰 버튼)
  alignItems: 'center',
  justifyContent: 'center',
},
ctaDimmed: { opacity: 0.4 },        // design.md §9 비활성/피드백
ctaText: { ...typography.button, color: colors.textWhite },
```

**건너뛰기/Pressable a11y 패턴** (`analyze.tsx:338-346` backBtn — 우상단 건너뛰기에 동일 적용):
```typescript
<Pressable
  onPress={skip}
  accessibilityRole="button"
  accessibilityLabel="튜토리얼 건너뛰기"
  hitSlop={10}
  style={({ pressed }) => [styles.skipBtn, pressed && styles.backBtnPressed]}
>
```
- dot 인디케이터 활성 dot = `colors.brand` (UI-SPEC §Color reserved). 크기/간격은 Figma 추출값.
- 화면 배경 = `colors.bg` (라이트 전용). 다크 배경 금지.

---

### `app/src/lib/onboarding.ts` (utility, 첫 실행 1회 플래그 — S1/D-03)

**Analog:** `app/src/app/analysis/result.tsx:966-990` — 프로젝트 유일의 AsyncStorage read/write 사용례. 그대로 복사.

**AsyncStorage graceful 패턴** (result.tsx:972-990):
```typescript
import AsyncStorage from '@react-native-async-storage/async-storage';

// AsyncStorage key '@sunity:keypoint_overlay_enabled' — Firebase Auth backing
// store 와 namespace 충돌 0 (T-12-03-T4).
const [overlayVisible, setOverlayVisible] = useState<boolean>(true);
useEffect(() => {
  AsyncStorage.getItem('@sunity:keypoint_overlay_enabled')
    .then((v) => {
      if (v === 'false') setOverlayVisible(false);
    })
    .catch(() => {
      /* graceful — 시각 토글 default 보존 */
    });
}, []);
const handleToggleOverlay = (next: boolean) => {
  setOverlayVisible(next);
  AsyncStorage.setItem('@sunity:keypoint_overlay_enabled', next ? 'true' : 'false')
    .catch(() => { /* graceful — UI 는 이미 반영 */ });
};
```
**적용 규칙:**
- 키 네임스페이스 = `@sunity:` prefix 필수 (예: `@sunity:tutorial_seen`). Firebase Auth backing store 충돌 회피 선례.
- read/write 모두 `.catch(() => {})` graceful — 실패해도 흐름 차단 금지.
- 데이터소스 격리 원칙(`bodyProfile.ts:1-11` 헤더): 화면은 AsyncStorage 직접 접근보다 `src/lib/` helper 경유가 기존 컨벤션 (result.tsx 는 인라인이지만, 신규 파일은 lib 모듈로 빼는 쪽이 `useXxx()` 패턴과 정합).

**첫 실행 감지 라우팅 삽입점** — `app/src/app/index.tsx:18-28` (인증 복원 후 라우팅 단일 수렴점):
```typescript
useEffect(() => {
  // 인증 상태가 생기면(신규 게스트 로그인 or 복원) 홈으로. 내비게이션을 한 곳에 집중.
  const unsubscribe = onAuthStateChanged(auth, (user) => {
    if (user) {
      router.replace('/(tabs)');   // ← 여기서 튜토리얼 미노출이면 '/tutorial' 로 분기
    } else {
      setBootstrapping(false);
    }
  });
  return unsubscribe;
}, [router]);
```
분기 전 AsyncStorage 읽기가 비동기이므로 `bootstrapping` state 패턴(깜빡임 방지, index.tsx:15)을 재사용해 플래그 로드까지 CTA/라우팅을 보류.

---

### `app/src/app/analysis/samples.tsx` (교체 — S2 이용방법/FAQ)

**Analog:** 자기 자신 — 골격(backBtn + heading + sub + ScrollView 카드 리스트)을 유지하고 내용만 교체. UI-SPEC S2가 이 골격을 명시적으로 계약.

**화면 골격** (samples.tsx:50-82):
```typescript
return (
  <View style={styles.container}>
    <Pressable
      onPress={() => router.back()}
      accessibilityRole="button"
      accessibilityLabel="뒤로 가기"
      hitSlop={10}
      style={({ pressed }) => [styles.backBtn, pressed && styles.backBtnPressed]}
    >
      <Ionicons name="chevron-back" size={26} color={colors.textPrimary} />
    </Pressable>
    <Text style={styles.heading}>이용 방법</Text>
    <Text style={styles.sub}>Sunity AI 코치를 잘 쓰는 방법을 모아뒀어요.</Text>
    <ScrollView
      style={styles.list}
      contentContainerStyle={styles.listContent}
      showsVerticalScrollIndicator={false}
    >
      {/* FAQ 카드 map */}
    </ScrollView>
  </View>
);
```

**카드 + 배지 스타일** (samples.tsx:154-190 — FAQ pill 배지는 이 badge 패턴 그대로, UI-SPEC §Color):
```typescript
card: {
  flexDirection: 'row',
  alignItems: 'center',
  gap: 12,
  backgroundColor: colors.cardBg,
  borderWidth: layout.cardBorderWidth,   // 0.858
  borderColor: colors.divider,
  borderRadius: radius.card,             // 15
  padding: spacing.cardPadding,          // 16
},
badge: {
  paddingHorizontal: 8,
  paddingVertical: 3,
  borderRadius: 999,
  backgroundColor: colors.brandTint,
},
badgeText: { ...typography.caption, color: colors.brand, fontWeight: '600' },  // 기존 600 재사용 1곳 허용
```

**진입 링크 교체 지점** — `analyze.tsx:482-489` (기존 "샘플 결과 미리보기" 링크를 이 화면으로 연결 교체):
```typescript
<Pressable
  onPress={() => router.push('/analysis/samples')}
  accessibilityRole="button"
  hitSlop={6}
>
  <Text style={styles.sampleLink}>샘플 결과 미리보기</Text>
</Pressable>
```
- `튜토리얼 다시 보기` 진입점 = 텍스트 링크 패턴 (`analyze.tsx:618-623` link 스타일: `colors.brand` + underline) 또는 리스트 항목.
- 기존 `saveSampleAnalysis`/`SAMPLE_SCENARIOS` import 는 교체 시 제거 대상 (simulationWriter 의존 소멸 — 단 다른 진입점 잔존 여부 확인).

---

### 카톡 압축본 경고 다이얼로그 (S4, D-06/D-07)

**Analog (로직):** `analyze.tsx` lqCard 모달 + 보류-picked 상태머신. **Analog (비주얼):** Figma 실물 다이얼로그 프레임("용량이 너무 커요" 류) — Figma 추출이 계약, lqCard 스타일과 다르면 Figma 승 (UI-SPEC §Figma Dialog Pattern. 이 기회에 lqCard 도 Figma 패턴 정렬 검토 — 단 D-07 로직 불변).

**감지 삽입점** — `analyze.tsx:235-259` `handleResult` (저화질 감지와 동일 위치, 파일명 기반):
```typescript
const handleResult = (result: ImagePicker.ImagePickerResult) => {
  if (result.canceled || !result.assets?.[0]) return;
  const asset = result.assets[0];
  const problem = validate(asset);
  if (problem) { setError(problem); return; }
  setError(null);
  const source = asset.fileName ?? asset.uri;   // ← _talkv_ 검사는 이 source 문자열
  ...
  // [#20 입력 화질] 저화질이면 조용히 진행하지 않고 비차단 경고를 띄운다.
  const quality = checkLowQuality(asset);
  if (quality.low) {
    setLowQualityPicked(picked);   // ← _talkv_ 감지도 동일하게 picked 보류 + 모달 state
    return;
  }
  maybePromptBeforeRoute(picked);
};
```

**보류-picked → 승인 플래그 패턴** (analyze.tsx:261-273 — D-07 연동의 핵심. `_talkv_` 승인도 **동일한 `lowQuality: true` 플래그**를 심으면 not_pole 화질 우선 분기가 공짜로 연동됨):
```typescript
// quick-260704-fwb — "경고를 보고 진행한" 업로드만 lowQuality 플래그를 심는다
// (경고 없이 통과한 영상은 플래그 X). not_pole 실패 시 화질 우선 안내 분기용.
const continueLowQuality = () => {
  const p = lowQualityPicked;
  setLowQualityPicked(null);
  if (p) maybePromptBeforeRoute({ ...p, lowQuality: true });
};
// [다른 영상 선택] — 보류한 영상을 버린다.
const cancelLowQuality = () => { setLowQualityPicked(null); };
```

**모달 구조 패턴** (analyze.tsx:386-422 — native back/백드롭 = 영상 버림 안전 동작 유지):
```typescript
<Modal
  visible={lowQualityPicked != null}
  transparent
  animationType="fade"
  onRequestClose={cancelLowQuality}   // native back = 취소와 동일 (영상 버림)
>
  <View style={styles.lqBackdrop}>
    <View style={styles.lqCard}>
      <Text style={styles.lqTitle}>화질이 낮아요</Text>
      <Text style={styles.lqBody}>...</Text>
      <Pressable onPress={continueLowQuality} accessibilityRole="button"
        accessibilityLabel="이대로 계속 분석하기"
        style={({ pressed }) => [styles.lqPrimaryBtn, pressed && styles.cardDimmed]}>
        <Text style={styles.lqPrimaryLabel}>이대로 계속</Text>
      </Pressable>
      ...
    </View>
  </View>
</Modal>
```
```typescript
lqBackdrop: {
  flex: 1,
  backgroundColor: colors.brandOverlay,
  alignItems: 'center',
  justifyContent: 'center',
  paddingHorizontal: spacing.screenX,
},
lqCard: {
  width: '100%',
  backgroundColor: colors.cardBg,   // ← Figma 패턴이면 brandTint 계열 틴트 카드로 교체 검토
  borderRadius: radius.modal,        // 20 — Figma 추출값이 더 크면 토큰 신설
  padding: 24,
  gap: 14,
},
```
**Figma 2버튼 가로 배치** (UI-SPEC 계약: 좌 보조 `이대로 계속` 흰+보더 / 우 주액션 `다른 영상 선택` brand filled — lqCard 의 세로 배치와 다름, Figma 승). 보조 버튼 스타일 선례 = `BodyProfilePromptModal.tsx:107-116`:
```typescript
secondary: {
  height: layout.ctaHeight,
  borderRadius: radius.button,
  borderWidth: 1,
  borderColor: colors.inputBorder,
  backgroundColor: colors.bg,
  alignItems: 'center',
  justifyContent: 'center',
},
secondaryText: { ...typography.buttonSecondary, color: colors.textPrimary },
```
재사용 컴포넌트로 뺄 경우 props 계약 선례 = `BodyProfilePromptModal.tsx:17-23` (`{ visible, onInput, onSkip }` — 3-way dismiss 수렴 주석 포함).

---

### `app/src/app/(tabs)/analyze.tsx` 수정 (S3 프라이버시 1줄 + opt-in / S5 거리 안내)

**Analog:** 자체 guidance 캡션 블록 (in-place 확장).

**guidance 캡션 삽입점 + 스타일** (analyze.tsx:367-372, 575-581 — 프라이버시 1줄·거리 안내 모두 이 스타일):
```typescript
{/* [#20 입력 화질] 가장 정확한 분석을 위한 안내 — ... */}
<Text style={styles.guidance}>
  가장 정확한 분석을 위해 앱에서 직접 촬영하거나 원본 화질 영상을 올려주세요.
  카톡 등으로 받은 영상은 압축돼 정확도가 낮을 수 있어요 (카톡은 '원본'으로 전송).
</Text>
```
```typescript
guidance: {
  ...typography.caption,
  color: colors.textMid,
  marginTop: 16,
  lineHeight: 18,   // caption 다줄 본문은 반드시 lineHeight 명시 (UI-SPEC Typography)
},
```
- S5 촬영 거리 안내는 이 기존 guidance 문단에 이어 붙이거나 두 번째 guidance 로 추가 (카피 = UI-SPEC §Copywriting).
- S3 프라이버시 1줄도 동일 스타일 — pick 직전 노출 보장 (소스 선택 단계 = `if (mode)` 블록 안, cards 아래).

**opt-in 체크 행 (S3):** 코드베이스에 checkbox 없음 — `KeypointOverlayToggle.tsx:34-46` 의 controlled + a11y 골격을 checkbox 로 변환:
```typescript
<Pressable
  onPress={() => onValueChange(!value)}
  accessibilityRole="switch"                    // ← "checkbox" 로 교체
  accessibilityState={{ checked: value }}
  accessibilityLabel={a11yLabel}
  hitSlop={8}
  style={...}
>
```
- 행 전체 Pressable + 라벨 포함 터치 44pt 이상 (UI-SPEC S3). unchecked 테두리 `colors.inputBorder` / checked `colors.brand` + 흰 체크(`Ionicons name="checkmark"`).
- controlled 분리 원칙 (KeypointOverlayToggle.tsx:9-10 주석): "caller 가 useState + 영속 read/write 담당. 본 component 는 단순 controlled (value + onValueChange)".
- opt-in state 는 `analyze.tsx` 가 들고 → 라우터 param 으로 loading 에 전달 (아래 lowQuality param 선례) → loading 의 `setDoc` 에서 Firestore 기록.

**라우터 param 전달 선례** (analyze.tsx:136-181 `routeAfterPick` — lowQuality 를 그대로 복제해 opt-in 추가):
```typescript
// quick-260704-fwb — 저화질 승인 플래그를 라우터 param 으로 로컬 전달.
// undefined 면 param 자체 미포함 (기존 흐름 불변).
const lowQuality = picked.lowQuality ? '1' : undefined;
router.push({
  pathname: '/analysis/loading',
  params: { mode: 'mode3', name: picked.name, uri: picked.uri,
            size: String(picked.size), format: picked.format, lowQuality },
});
```
주의: mode1 미선택 경로는 `/analysis/reference` 를 경유하므로 (analyze.tsx:157-166), 신규 param 은 **reference.tsx 의 param pass-through 에도 추가**해야 유실이 없다 (lowQuality 가 이미 이 경로를 지나감 — `grep lowQuality app/src/app/analysis/reference.tsx` 로 pass-through 위치 확인).

---

### `app/src/app/analysis/loading.tsx` 수정 (S6 not_pole 구도 안내 + opt-in Firestore 기록)

**Analog:** 자체 — 에러 계층·lowQuality 분기·setDoc 모두 이 파일 안 (in-place).

**에러 표시 계층 (불변 계약)** (loading.tsx:332-338 — 로컬 > Firestore > 기본):
```typescript
// 표시할 상태: localError > Firestore doc > 업로드 전 기본.
const status: AnalysisStatus = localError ? 'failed' : (storedDoc?.status ?? 'uploading');
const errorCode: AnalysisErrorCode | null = localError ?? storedDoc?.error?.code ?? null;
```

**D-07 화질 우선 분기 (불변) + S6 구도 안내 삽입점** (loading.tsx:390-407):
```typescript
const code: AnalysisErrorCode = errorCode ?? 'server_error';
const isNotPole = code === 'not_pole_motion';
// quick-260704-fwb — 저화질 경고를 승인하고 진행한 업로드가 not_pole 로 실패하면
// "기준 동작과 너무 달라요" 대신 화질 우선 안내. 플래그 없는 not_pole 은 기존 카피 그대로.
const isLowQualityNotPole = isNotPole && lowQuality === '1';
const errorTitle = isNoHuman ? '사람을 찾지 못했어요'
  : isLowQualityNotPole ? '화질이 낮아 분석하지 못했을 수 있어요'
  : isNotPole ? '기준 동작과 너무 달라요'        // ← S6: 타이틀 유지, 본문에 구도 원인+행동 추가
  : '분석 중 문제가 발생했어요';
```
S6 구도 안내는 **플래그 없는 not_pole 분기**(`isNotPole && !isLowQualityNotPole`)의 body/tipCard 에만 추가. tipCard 항목 패턴 (loading.tsx:440-464):
```typescript
{isNotPole && (
  <View style={styles.tipCard}>
    <View style={styles.tipHeadRow}>
      <Ionicons name="alert-circle" size={16} color={ERROR_RED} />
      <Text style={styles.tipHead}>확인해보세요</Text>
    </View>
    <Text style={styles.tipItem}>· 폴스포츠 연습 영상이 맞는지</Text>
    ...
  </View>
)}
```
- 이 화면은 기존 네이비 예외 화면 — 신규 색 도입 금지, 기존 스타일 토큰(`tipCard`/`tipItem`/`ERROR_RED`) 그대로 (UI-SPEC S6).
- Figma 에 대응 오류 프레임이 있으면 그 구조·카피 우선 (실행자 선탐색).

**opt-in 동의값 Firestore 기록점** (loading.tsx:124-137 `startAnalysisUpload` — bodyProfile snapshot 과 동일한 조건부 spread):
```typescript
const bodyProfile = await getBodyProfileOnce();
const now = Date.now();
await setDoc(doc(db, 'users', uid, 'analyses', analysisId), {
  analysisId,
  mode: input.mode,
  status: 'uploading',
  fileName: input.fileName,
  createdAt: now,
  updatedAt: now,
  ...(input.referenceMotionId ? { referenceMotionId: input.referenceMotionId } : {}),
  ...(bodyProfile ? { bodyProfile } : {}),
  // ← 여기에 학습활용 동의 필드 추가 (예: learningOptIn: true — 동의 시에만 spread
  //    또는 항상 boolean 기록. Phase 22 manifest 게이트가 분석 문서에서 읽는 형태 —
  //    22-04-PLAN.md 의 anonymized/registration 게이트 소비 가능해야 함, D-09)
});
```
param 수신은 loading.tsx:270-294 `useLocalSearchParams` 의 `lowQuality?: string` 선례 그대로 (`'1'` 문자열 규약).

---

### `app/src/types/analysis.ts` 수정 (동의 필드 — 3-way lockstep)

**Analog:** `AnalysisDoc.bodyProfile` 필드 추가 선례 (analysis.ts:589-610) — 옵셔널 필드 + why 주석 + 출처 인용:
```typescript
export interface AnalysisDoc {
  analysisId: string;
  mode: AnalysisMode;
  status: AnalysisStatus;
  ...
  // 분석-당시 자가입력 SNAPSHOT (live users/{uid}.bodyProfile 아님 — 결과 화면
  // 재현성, R1). 03-03 result.tsx 가 이 snapshot 을 우선 표시. loading.tsx 가
  // getBodyProfileOnce() (client normalize) 로 기록.
  bodyProfile?: BodyProfile | null;
  // ← 동일 형식으로 학습활용 opt-in 필드 추가 (D-08/D-09, Phase 22 D-12 소비 인용)
}
```
**Lockstep:** 계약 필드 추가 시 `backend/shared/python/sunity_shared/models.py` 와 `docs/contract.md` 동시 편집 (프로젝트 invariant). 백엔드 로직 무접촉이어도 계약 문서 미러는 유지 — models.py 에 필드 주석 추가는 "채점 로직" 이 아니므로 스코프 위반 아님. 플래너가 앱-로컬(계약 외) 저장을 택하면 lockstep 불필요 — 단 Phase 22 게이트 소비 가능성이 우선 기준.

정규화 방어 선례 (Firestore raw 를 신뢰하지 않음) = `bodyProfile.ts:66-100` `normalizeBodyProfile` — 잘못된 타입 → null, 절대 throw 안 함.

---

### F3 기타 자유입력 (S7)

**Analog:** `app/src/app/inquiry.tsx` — 문의 유형은 이미 `기타`(etc) 보유 + 자유입력 TextInput 완비. 나머지 설문/입력 지점 특정은 플래너 재량.

**chip 단일선택 패턴** (inquiry.tsx:185-207):
```typescript
{CATEGORY_OPTIONS.map((opt) => {
  const selected = category === opt.value;
  return (
    <Pressable
      key={opt.value}
      onPress={() => { setCategory(opt.value); if (error) setError(null); }}
      accessibilityRole="button"
      accessibilityState={{ selected }}
      accessibilityLabel={`문의 유형 ${opt.label}${selected ? ', 선택됨' : ''}`}
      hitSlop={6}
      style={[styles.chip, selected && styles.chipSelected]}
    >
      <Text style={[styles.chipText, selected && styles.chipTextSelected]}>{opt.label}</Text>
    </Pressable>
  );
})}
```

**자유입력 필드 패턴** (inquiry.tsx:311-326 — design.md §5-3-1 입력 계약 그대로):
```typescript
textAreaBox: {
  minHeight: 140,
  borderWidth: 1,
  borderColor: colors.inputBorder,
  borderRadius: radius.button,
  backgroundColor: colors.bg,
  paddingHorizontal: spacing.cardPadding,
  paddingVertical: 12,
},
textArea: { flex: 1, minHeight: 116, ...typography.buttonSecondary, color: colors.textPrimary },
```
인라인 오류 = `error: { ...typography.caption, color: colors.inputError }` (틸 — 인라인 폼 스코프, inquiry.tsx:326).
placeholder 색: inquiry 는 `colors.textSecondary` 를 쓰지만 UI-SPEC S7 은 `colors.textDisabled` 계약 — 신규 코드는 UI-SPEC 준수.

---

### `app/src/app/(tabs)/index.tsx` 수정 (F4 공지 간격/카피)

**Analog:** 자체 newsBanner (in-place 최소 수정 — 배너 비주얼 brand pill 불변).

**배너 렌더** (index.tsx:83-119):
```typescript
// NEW 공지 배너: 가장 최근 updatedAt 모션. 모션이 없으면 배너 숨김.
{newest && (
  <View style={styles.newsBanner}>
    <View style={styles.newsBadge}>
      <Text style={styles.newsBadgeText}>NEW</Text>
    </View>
    <Text style={styles.newsText} numberOfLines={1}>
      {newest.name} 기준모션이 추가되었어요.     {/* ← F4: 불필요 문장 제거 대상 카피 */}
    </Text>
  </View>
)}
```
**간격 수정점** (index.tsx:337-347 — 인접 요소 간격 최소 12 확보, UI-SPEC Spacing):
```typescript
newsBanner: {
  flexDirection: 'row',
  alignItems: 'center',
  alignSelf: 'stretch',
  backgroundColor: 'rgba(255,255,255,0.16)',
  borderRadius: 999,
  paddingVertical: 6,
  paddingLeft: 6,
  paddingRight: 14,
  marginTop: 16,        // ← 간격 조정은 여기 + TOP_AREA_HEIGHT(315행, 240) 연동 확인
},
```

---

### `app/src/theme/colors.ts` 수정 가능 (Figma 다이얼로그 토큰 신설)

**Analog:** 자체 — 토큰 신설 시 phase 표기 + 근거 주석 패턴 (colors.ts:37-48, 65-68):
```typescript
// ── Phase 12 신설 토큰 (UI-SPEC §1) ──────────────────────────────────
// 기존 brand #FF4B33 는 변경 0 (CLAUDE.md §4 / D-12-U5). 신규 키만 추가.
brandSoft: '#FFD9D2', // Phase 9 작은 카드 chip 배경
...
// ── Phase 10 신설 토큰 (10-UI-SPEC §Color, 2026-06-30) ────────────────
warnAmberBg: '#FFF6E5', // 부상 위험 경고 배너 배경 (D-08)
```
매핑 후보 (Figma 추출 hex → 우선 매핑): 틴트 카드 배경 → `brandTint`(rgba 0.15) / `brandSoft`(#FFD9D2) / `brandBg`(#FFE5E0). 빨간 느낌표 아이콘 → `colors.brand` 계열 우선, 상이하면 신설. `radius.modal`(20) 초과 radius 필요 시 `radius` 토큰 신설 (`app/src/theme/index.ts`).

---

## Shared Patterns

### 화면 파일 공통 골격
**Source:** `analyze.tsx` / `samples.tsx` / `inquiry.tsx` 전부 동일
**Apply to:** tutorial.tsx, samples.tsx 교체본
- 한국어 헤더 블록 주석(why + 스펙 인용 `design.md §N` / `D-NN` / `belle P1 #n`) → import (type-only 는 `import type`) → 상수 SCREAMING_SNAKE → default export 화면 함수 → 로컬 헬퍼 named function (inline prop type) → `StyleSheet.create` 파일 하단.
- 컨테이너: `{ flex: 1, backgroundColor: colors.bg, paddingTop: layout.safeAreaTop, paddingHorizontal: spacing.screenX, paddingBottom: layout.safeAreaBottom + 24 }` (analyze.tsx:529-535).
- 하드코딩 색/spacing 금지 — 토큰만. 이모지 금지.

### 접근성 (전 Pressable)
**Source:** `analyze.tsx:338-346, 508-516`
**Apply to:** 모든 신규 Pressable
```typescript
accessibilityRole="button"          // switch/checkbox 는 role 교체
accessibilityLabel="..."            // 한국어
accessibilityState={{ disabled }}   // 상태 있으면 명시
hitSlop={6~10}
style={({ pressed }) => [styles.x, pressed && styles.cardDimmed]}  // opacity 0.4 dimmed
```

### 에러/안내 문구
**Source:** `analyze.tsx:106-108, 570-574`
**Apply to:** 전 화면
- 사용자 대면 = 한국어 "~해요" 체 인라인 문자열, state 에 저장 후 렌더. `console.log` 금지 (`__DEV__` guard `console.warn` 만 허용 — samples.tsx:45).
- 인라인 폼 오류색 = `colors.inputError` (틸). 다이얼로그 오류 시각 언어는 Figma 패턴 (이원 계약 — UI-SPEC §Color).

### 비차단 경고 + 보류-picked 상태머신
**Source:** `analyze.tsx:70-72, 235-273` (lowQualityPicked) + `:79-86, 192-233` (pendingPicked/BodyProfilePrompt)
**Apply to:** S4 카톡 경고, 향후 모든 pick-시점 게이트
- 게이트마다 picked 를 state 에 보류 → 모달 → 모든 dismiss 경로(버튼/백드롭/native back)가 단일 수렴 함수로 → 승인 시 플래그 심고 `maybePromptBeforeRoute(picked)` 재개.
- 게이트 체인 주의: `_talkv_` 감지는 기존 lowQuality 게이트·BodyProfile 권유 게이트와 **직렬로** 연결돼야 함 (handleResult → talkv → lowQuality → bodyProfile prompt → route). 두 경고가 동시에 뜨지 않게 순서 설계는 플래너 몫.

### AsyncStorage 로컬 플래그
**Source:** `result.tsx:966-990`
**Apply to:** 튜토리얼 first-run 플래그, 기타 로컬 1회성 플래그
- `@sunity:` 키 prefix, 문자열 값(`'true'`/`'false'`), 양방향 `.catch(() => {})` graceful.

### Firestore 필드 기록 (사용자/분석 문서)
**Source:** `bodyProfile.ts:189-210` (users/{uid} merge-write) + `loading.tsx:124-137` (analyses/{id} 생성 시 조건부 spread)
**Apply to:** opt-in 동의값 저장 (D-09)
- 사용자 레벨이면 `setDoc(doc(db, 'users', uid), { ... }, { merge: true })` — merge 는 nested map deep merge (WR-01 주석의 deleteField 함정 인지).
- 분석 문서 레벨이면 생성 setDoc 의 `...(cond ? { field } : {})` 스타일.
- 데이터소스 격리: 화면이 Firestore 직접 접근 금지 — `src/lib/` helper 경유 (bodyProfile.ts:1-11 헤더 원칙). 예외: loading.tsx 의 분석 문서 생성은 기존 인라인 선례.

---

## No Analog Found

| File/요소 | Role | Data Flow | Reason / 대체 소스 |
|------|------|-----------|--------|
| 튜토리얼 스와이프 페이저 (S1) | component | horizontal paging | 코드베이스에 `pagingEnabled`/horizontal FlatList 0건. Figma 프레임이 비주얼 계약. RN 코어 `ScrollView horizontal pagingEnabled` + `onMomentumScrollEnd` 로 dot index 산출 — 신규 라이브러리 금지 (UI-SPEC Registry Safety) |
| 체크박스 컴포넌트 (S3 opt-in) | component | controlled boolean | `accessibilityRole="checkbox"` 사용례 0건. 가장 가까운 구조 = `KeypointOverlayToggle.tsx` (controlled switch + a11y) — role/비주얼만 checkbox 로 변환 |

## Metadata

**Analog search scope:** `app/src/app/`, `app/src/components/`, `app/src/lib/`, `app/src/types/`, `app/src/theme/`
**Files scanned:** 44 (전수 목록) / 정밀 추출 13
**Pattern extraction date:** 2026-07-07

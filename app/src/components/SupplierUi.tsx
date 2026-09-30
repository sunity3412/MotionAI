// 공급자 페이지 공용 프리미티브 (Phase 38-10 · UI-SPEC §Component Inventory).
//
// 원형 = Figma jrdI7kp245HkPfLB0nclsz 노드(1:960 가입 · 1:977 Google · 1:419~424 권한 ·
// 1:717 메인 · 1:743 섹션 · 1:646/663/713/709 선수 카드 · 1:399 알약 · 1:482/483 TIP).
// 2026-09-30 38-DESIGN.md(Figma 282:506) 값으로 갱신 — UI-SPEC 과 부딪히는 시각 값은 DESIGN 우선.
// 38-10 이 `≈` 로 남긴 값 중 Google 48 은 54 로 확정(38-DESIGN A-1), STEP 라벨 13.8 은 15/700
// 으로(38-DESIGN §0). 테두리 버튼 48 은 38-DESIGN 이 높이를 적지 않아 그대로 둔다.
//
// 규칙: 색은 전부 theme 토큰(리터럴 색 0) · 문구는 호출부가 supplierCopy 에서 넘긴다(여기 한국어
// 리터럴 0) · 라이트 전용 · 이모지 0. 간격은 이 파일의 선언값만(`space`).
// 눌림 피드백 = Pressable `pressed` 스타일(apple-design press-down). 움직임은 크게 보기 모달 fade
// 하나(투명도만) — 미끄러짐·확대가 없어 reduced-motion 과 같은 모습이다(38-DESIGN-v2).
// 2026-09-30 38-DESIGN-v2(quick-260930-lfw): IdBox·CodeCard 삭제 → AccountBox · ContactRow ·
// CodeRow · BigCodeModal.

import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useVideoPlayer, VideoView } from 'expo-video';
import { useState, type ReactNode } from 'react';
import {
  Modal,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  useWindowDimensions,
  View,
  type StyleProp,
  type ViewStyle,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { bigCodeFontSize } from '../lib/supplierRules';
import { colors, fontFamily, gradients, layout, radius, sns, spacing, typography } from '../theme';
import { AlertIcon } from './PickErrorDialog';
import SocialIcon from './SocialIcon';
import SunityWordmark from './SunityWordmark';

// 간격 선언값. 새 theme 토큰을 만들지 않고 이 화면군 안에서만 쓴다.
// xxs~s40 은 38-DESIGN.md 가 적은 간격(2 · 6 · 10 · 13 · 14 · 40)이라 4 의 배수 밖이다.
export const space = {
  xxs: 2,
  xs: 4,
  s6: 6,
  sm: 8,
  s10: 10,
  row: 12,
  s13: 13,
  s14: 14,
  md: 16,
  screen: spacing.screenX, // 20
  lg: 24,
  xl: 32,
  s40: 40,
  xxl: 48,
} as const;

// UI-SPEC §Spacing Exceptions — 높이 규격.
const H = {
  cta: layout.ctaHeight, // 54
  outline: 48, // 1:423 / 1:424 (38-DESIGN 이 높이를 적지 않음)
  google: 54, // 38-DESIGN A-1
  pill: 44, // 1:717 알약
  touch: 44,
  thumb: 48, // 1:717 썸네일
  rowMin: 72,
  ring: 72, // 38-DESIGN X 링 · 체크 링
  chipBtn: 36, // 38-DESIGN-v2 강사 코드 줄 알약 버튼
  contactIcon: 32, // 38-DESIGN-v2 A-2 문의 행 아이콘 사각
} as const;

// 반경 — theme 토큰 + 박제값(시트 17 · 알약 22 · 칩 8 · 토스트 12).
const R = {
  button: radius.button, // 13
  card: radius.card, // 15
  thumb: 8, // radius.listItem 8.58 → 웹 8 (UI-SPEC)
  sheet: 17, // 1:717 17.16 → 17
  pill: 22,
  chip: 8,
  toast: 12,
  noticePill: 15, // 38-DESIGN A-4 ④ 안내 알약 15
} as const;

// 페이지 최대 폭(UI-SPEC Page frame). 크게 보기 코드 크기도 이 폭 기준.
const FRAME_MAX_W = 430;

// 시트가 헤더 위로 겹치는 높이 — 시안 헤더 ≈300, 시트가 216 에서 시작(38-DESIGN A-3).
const SHEET_OVERLAP = 84;

// 웹은 1px(서브픽셀 불안정, UI-SPEC Decisions 20), 앱은 박제값 0.858.
const BORDER = Platform.OS === 'web' ? 1 : layout.cardBorderWidth;

// 굵기는 fontFamily 로 정한다 — fontWeight 만으로는 iOS 가 Pretendard 굵기를 무시한다.
const REGULAR = { fontFamily: fontFamily.regular, fontWeight: '400', letterSpacing: 0 } as const;
const BOLD = { fontFamily: fontFamily.bold, fontWeight: '700', letterSpacing: 0 } as const;

// 30pt 제목 자간 −2%(38-DESIGN §0). 음수 letterSpacing 은 iOS 26+ SIGABRT(typography.ts 2~6행)라
// 웹에서만 준다 — 이 라우트는 38-04 option-1 로 웹이 주 무대.
const DISPLAY_TRACK = Platform.OS === 'web' ? -0.6 : 0;

// UI-SPEC §Typography 4단(17 / 18 / 20 / 30) + 38-DESIGN §0 보조 15 · 캡션 13.
export const text = StyleSheet.create({
  label: { ...typography.buttonSecondary, lineHeight: 24, color: colors.textPrimary },
  labelBold: { ...typography.metricNumber, lineHeight: 24, color: colors.textPrimary },
  title: { ...typography.listTitle, lineHeight: 25, color: colors.textPrimary },
  heading: { ...typography.sectionTitle, lineHeight: 28, color: colors.textPrimary },
  display: { ...typography.headline, letterSpacing: DISPLAY_TRACK, color: colors.textPrimary },
  caption: { ...typography.caption, color: colors.resultTextSub },
  mid: { color: colors.textMid },
  sub: { color: colors.resultTextSub },
  center: { textAlign: 'center' },
  // 38-DESIGN §0 보조 문구 15/400/20 textMid — 도움말·카드 부제·행 부제·알약 본문·코드 안내.
  aux: { ...REGULAR, fontSize: 15, lineHeight: 20, color: colors.textMid },
  // 38-DESIGN §0 흐린 보조 — 로그인 힌트·등록 확인 힌트·재현성 고지·"필수 3개".
  auxFaint: { ...REGULAR, fontSize: 15, lineHeight: 20, color: colors.resultTextSub },
  body15: { ...REGULAR, fontSize: 15, lineHeight: 20, color: colors.textPrimary },
  body15Bold: { ...BOLD, fontSize: 15, lineHeight: 20, color: colors.textPrimary },
  caption13: { ...REGULAR, fontSize: 13, lineHeight: 18, color: colors.textMid },
  // 38-DESIGN A-6 가이드 섹션 번호 01~07.
  num13: { ...BOLD, fontSize: 13, lineHeight: 18, color: colors.brand },
  // 38-DESIGN §0 칩 글자.
  chipText: { ...BOLD, fontSize: 13, lineHeight: 18, color: colors.textMid },
  // 38-DESIGN-v2 A-3 강사 코드 줄 코드 20/700 brand, 자간 +6%(양수라 모든 플랫폼).
  code: { ...BOLD, fontSize: 20, lineHeight: 26, letterSpacing: 1.2, color: colors.brand },
  // 38-DESIGN §0 STEP 라벨 15/700 brand(38-10 의 13.8 폐기).
  step: { ...BOLD, fontSize: 15, lineHeight: 20, color: colors.brand },
});

// ── 골격 ─────────────────────────────────────────────────────────────────

// 페이지 프레임 — 최대 폭 430 중앙(UI-SPEC Page frame). 폰 브라우저에서는 전폭.
export function PageFrame({ children }: { children: ReactNode }) {
  return <View style={s.frame}>{children}</View>;
}

// 높이 44. 뒤로 chevron 44×44(광학 −8) · 오른쪽 링크(선택). help.tsx 선례.
export function TopBar({
  onBack,
  backLabel,
  right,
}: {
  onBack?: () => void;
  backLabel?: string;
  right?: ReactNode;
}) {
  return (
    <View style={s.topBar}>
      {onBack ? (
        <Pressable
          onPress={onBack}
          style={({ pressed }) => [s.backBtn, pressed && s.pressed]}
          accessibilityRole="button"
          accessibilityLabel={backLabel}
          hitSlop={8}
        >
          <Ionicons name="chevron-back" size={24} color={colors.textPrimary} />
        </Pressable>
      ) : null}
      <View style={s.flex} />
      {right}
    </View>
  );
}

// 워드마크 — brand = 로그인 화면(login.tsx 1:573)과 같은 110×37, white = 0.75배 83×28(A-3 헤더).
export function BrandMark({ variant }: { variant: 'brand' | 'white' }) {
  return variant === 'brand' ? (
    <SunityWordmark variant="brand" width={110} height={37} />
  ) : (
    <SunityWordmark variant="white" width={83} height={28} />
  );
}

// 38-DESIGN §0 칩 — softBg · 반경 8 · 패딩 4 10 · 13/700 textMid.
export function Chip({ label }: { label: string }) {
  return (
    <View style={s.chipLogin}>
      <Text style={text.chipText}>{label}</Text>
    </View>
  );
}

// 38-DESIGN A-3 헤더 — 첫 줄(높이 44) 흰 워드마크 + 오른쪽 `촬영 가이드` 흰 밑줄 → 8 → 제목
// 30/700 흰 → 4 → identity 17/700 흰. 아래로 시트가 SHEET_OVERLAP 만큼 겹친다.
export function GradientHeader({
  title,
  identity,
  guideLabel,
  onGuide,
}: {
  title: string;
  identity: string;
  guideLabel: string;
  onGuide: () => void;
}) {
  const insets = useSafeAreaInsets();
  return (
    <LinearGradient
      colors={gradients.homeTop.colors}
      locations={gradients.homeTop.locations}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 0.08 }}
      style={[s.header, { paddingTop: insets.top + space.md }]}
    >
      <View style={s.headerTop}>
        <BrandMark variant="white" />
        <TextLink label={guideLabel} onPress={onGuide} tone="onHeader" />
      </View>
      <Text style={[text.display, s.onBrand, s.mt8]} accessibilityRole="header">
        {title}
      </Text>
      <Text style={[text.labelBold, s.onBrand, s.mt4]} numberOfLines={1}>
        {identity}
      </Text>
    </LinearGradient>
  );
}

// 헤더 위로 SHEET_OVERLAP 겹치는 흰 시트(상단 반경 17, gradients.homeCard, 패딩 20 20 24).
export function Sheet({ children }: { children: ReactNode }) {
  return (
    <LinearGradient colors={gradients.homeCard.colors} style={s.sheet}>
      {children}
    </LinearGradient>
  );
}

export function Card({
  children,
  style,
}: {
  children: ReactNode;
  style?: StyleProp<ViewStyle>;
}) {
  return <View style={[s.card, style]}>{children}</View>;
}

export function GrayCard({ message }: { message: string }) {
  return (
    <View style={s.grayCard}>
      <Text style={[text.label, text.mid]}>{message}</Text>
    </View>
  );
}

// 38-DESIGN A-3 — 제목 20/700 왼쪽 · 오른쪽 `{n}개` 17 textMid.
export function SectionHeader({ title, count }: { title: string; count?: string | null }) {
  return (
    <View style={s.sectionHead}>
      <Text style={text.heading} accessibilityRole="header">
        {title}
      </Text>
      {count ? <Text style={[text.label, text.mid]}>{count}</Text> : null}
    </View>
  );
}

export type RowTrailing = 'chevron' | 'progress' | null;

// 38-DESIGN A-3 행 — 세로 12 · 썸네일 48 반경 8 → 12 → 이름 18/700 / 2 / 부제 15 textMid.
// 오른쪽: 상세 있음 = 쉐브론 20 inputBorder, 진행 중 = 8px 점 brandButtonDisabled. 행 사이 dividerSoft.
export function ListRow({
  title,
  subtitle,
  trailing,
  onPress,
  highlighted,
  isLast,
  onLayout,
}: {
  title: string;
  subtitle: string;
  trailing: RowTrailing;
  onPress?: () => void;
  highlighted?: boolean;
  isLast?: boolean;
  onLayout?: (y: number) => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={!onPress}
      onLayout={onLayout ? (e) => onLayout(e.nativeEvent.layout.y) : undefined}
      style={({ pressed }) => [
        s.row,
        !isLast && s.rowDivider,
        highlighted && s.rowHighlighted,
        pressed && s.cardPressed,
      ]}
      accessibilityRole={onPress ? 'button' : 'text'}
      accessibilityLabel={`${title}, ${subtitle}`}
    >
      <View style={s.thumb}>
        <Ionicons name="images-outline" size={20} color={colors.inputBorder} />
      </View>
      <View style={s.rowText}>
        <Text style={text.title} numberOfLines={1}>
          {title}
        </Text>
        <Text style={text.aux}>{subtitle}</Text>
      </View>
      {trailing === 'chevron' ? (
        <Ionicons name="chevron-forward" size={20} color={colors.inputBorder} />
      ) : trailing === 'progress' ? (
        <View style={s.progressDot} />
      ) : null}
    </Pressable>
  );
}

// ── 버튼 ─────────────────────────────────────────────────────────────────

// 38-DESIGN A-3 알약 CTA — 전폭 · 44 · 반경 22 · gradients.brandButton · 흰 17/700 + 흰 쉐브론 20.
// 글자 `>` 로 쉐브론을 흉내 내지 않는다(38-DESIGN §0 아이콘).
export function PillCta({ label, onPress }: { label: string; onPress: () => void }) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [s.pillWrap, pressed && s.pressed]}
      accessibilityRole="button"
      accessibilityLabel={label}
    >
      <LinearGradient
        colors={gradients.brandButton.colors}
        locations={gradients.brandButton.locations}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 0 }}
        style={s.pill}
      >
        <Text style={[text.labelBold, s.onBrand]}>{label}</Text>
        <Ionicons name="chevron-forward" size={20} color={colors.textWhite} />
      </LinearGradient>
    </Pressable>
  );
}

// 1:960 CTA — 54 / 반경 13 / 채움 brand · 비활성 brandButtonDisabled(글자 흰색 유지).
// onDisabledPress(38-11): 비활성인데 눌렀을 때 — 폼이 빈 칸의 인라인 오류를 드러낸다(UI-SPEC A-4
// "표시마다 답"). 주면 Pressable 을 막지 않고 aria-disabled 만 둔다. 안 주면 38-10 동작 그대로.
export function PrimaryCta({
  label,
  onPress,
  disabled,
  onDisabledPress,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  onDisabledPress?: () => void;
}) {
  return (
    <Pressable
      onPress={disabled ? onDisabledPress : onPress}
      disabled={disabled && !onDisabledPress}
      style={({ pressed }) => [
        s.primary,
        disabled && s.primaryDisabled,
        pressed && !disabled && s.pressed,
      ]}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: !!disabled }}
    >
      <Text style={[typography.button, s.onBrand]}>{label}</Text>
    </Pressable>
  );
}

// 1:423 / 1:424 테두리 버튼 — 48 / 반경 13 / 테두리 inputBorder / 글자 textPrimary 700.
// 비활성 = opacity 0.4, 누를 수 없음(38-DESIGN A-3 코드 준비 중). 눌림 = 0.7(press-down).
export function OutlineButton({
  label,
  onPress,
  disabled,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [s.outline, pressed && !disabled && s.pressed, disabled && s.cardPressed]}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: !!disabled }}
      accessibilityLiveRegion="polite"
    >
      <Text style={text.labelBold}>{label}</Text>
    </Pressable>
  );
}

// 38-DESIGN A-1 — 54 · 반경 13 · 흰 · 1px inputBorder · G 20 + 10 + 18/700 라벨을 가로로 묶어
// 가운데 정렬. 진행 중 opacity 0.6.
export function GoogleButton({
  label,
  onPress,
  busy,
}: {
  label: string;
  onPress: () => void;
  busy?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={busy}
      style={({ pressed }) => [s.google, (pressed || busy) && s.busy]}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: !!busy, busy: !!busy }}
    >
      <SocialIcon id="google" width={20} height={20} />
      <Text style={text.title}>{label}</Text>
    </Pressable>
  );
}

// design.md §0 — 이동 = brand 밑줄 · 로그아웃 = infoTeal 밑줄(38-DESIGN A-3 "틸 링크 17 밑줄") ·
// 취소 = textMid 밑줄 · onHeader = 흰 17/700 밑줄(A-3 헤더 촬영 가이드).
export function TextLink({
  label,
  onPress,
  tone,
  center,
}: {
  label: string;
  onPress: () => void;
  tone: 'go' | 'signOut' | 'cancel' | 'onHeader';
  center?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [s.link, center && s.linkCenter, pressed && s.pressed]}
      accessibilityRole="link"
      hitSlop={8}
    >
      <Text
        style={[
          tone === 'onHeader' ? text.labelBold : text.label,
          tone === 'go' && s.linkGo,
          tone === 'signOut' && s.linkSignOut,
          tone === 'cancel' && s.linkCancel,
          tone === 'onHeader' && s.linkOnHeader,
        ]}
      >
        {label}
      </Text>
    </Pressable>
  );
}

// ── 안내 · 카드 ───────────────────────────────────────────────────────────

// 38-DESIGN A-4 ④ 안내 알약 — 반경 15 · 1px divider · 패딩 12 16 · AlertIcon 24 + 12 + 두 줄 15.
// 홈 podDown 과 폼 ④ 가 같이 쓴다.
export function NoticePill({ lines }: { lines: readonly string[] }) {
  return (
    <View style={s.notice} accessibilityRole="alert">
      <AlertIcon size={24} />
      <View style={s.flex}>
        {lines.map((line) => (
          <Text key={line} style={text.aux}>
            {line}
          </Text>
        ))}
      </View>
    </View>
  );
}

// 38-DESIGN A-3b TIP 카드 — 머리 AlertIcon 18 + 6 + 17/700 → 8 → 줄 15(간 4).
export function TipCard({ head, lines }: { head: string; lines: readonly string[] }) {
  return (
    <View style={[s.card, s.tipCard]}>
      <View style={s.tipHead}>
        <AlertIcon size={18} />
        <Text style={text.labelBold}>{head}</Text>
      </View>
      <View style={s.tipLines}>
        {lines.map((line) => (
          <Text key={line} style={text.body15}>
            {line}
          </Text>
        ))}
      </View>
    </View>
  );
}

// 38-DESIGN A-3 빈 상태 점선 STEP 카드 — 1px dashed brand · 반경 15 · 패딩 20 16 · 가운데 정렬:
// STEP 15/700 → 4 → 18/700 제목 → 8 → 보조 문구 → 16 → 알약(전폭).
// 시안의 dash 6/4 는 RN borderStyle 이 길이를 제어하지 못해 dashed 기본 모양으로 둔다(근사).
export function StepCard({
  step,
  title,
  body,
  cta,
}: {
  step: string;
  title: string;
  body: string;
  cta: ReactNode;
}) {
  return (
    <View style={s.stepCard}>
      <Text style={text.step}>{step}</Text>
      <Text style={[text.title, text.center, s.mt4]}>{title}</Text>
      <Text style={[text.aux, text.center, s.mt8]}>{body}</Text>
      <View style={[s.mt16, s.stretch]}>{cta}</View>
    </View>
  );
}

// 38-DESIGN-v2 A-2 지금 로그인한 계정 — softBg · 반경 13 · 패딩 14 16 · 라벨 15 textMid / 메일 17/700.
export function AccountBox({ label, email }: { label: string; email: string }) {
  return (
    <View style={s.accountBox}>
      <Text style={text.aux}>{label}</Text>
      <Text style={[text.labelBold, s.mt2]} selectable>
        {email}
      </Text>
    </View>
  );
}

// 38-DESIGN-v2 A-2 문의 행 — 1px divider · 반경 13 · 패딩 12 16. 아이콘 32(반경 8) + 제목 17/700 /
// 부제 15 textMid(선택 — 카카오 줄은 부제 없음, belle 09-30 폰 확인) + 쉐브론 20 inputBorder. 카카오 노랑은 외부 서비스 식별 예외(기존 토큰 sns.kakao).
export function ContactRow({
  kind,
  title,
  sub,
  onPress,
}: {
  kind: 'kakao' | 'mail';
  title: string;
  sub?: string;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [s.contactRow, pressed && s.pressed]}
      accessibilityRole="link"
      accessibilityLabel={title}
    >
      <View style={[s.contactIcon, kind === 'kakao' ? s.contactIconKakao : s.contactIconMail]}>
        {kind === 'kakao' ? (
          <SocialIcon id="kakao" width={18} height={16} />
        ) : (
          <Ionicons name="mail-outline" size={18} color={colors.textMid} />
        )}
      </View>
      <View style={s.contactText}>
        <Text style={text.labelBold}>{title}</Text>
        {sub ? <Text style={text.aux}>{sub}</Text> : null}
      </View>
      <Ionicons name="chevron-forward" size={20} color={colors.inputBorder} />
    </Pressable>
  );
}

// 상단 토스트 — safe-top + 16 · 배경 textPrimary(design.md §0 다크 배경 금지의 명시 예외) · 3초는 호출부.
export function Toast({ message }: { message: string | null }) {
  const insets = useSafeAreaInsets();
  if (!message) return null;
  return (
    <View
      pointerEvents="none"
      style={[s.toast, { top: insets.top + space.md }]}
      accessibilityLiveRegion="polite"
      accessibilityRole="alert"
    >
      <Text style={[text.label, s.onBrand]}>{message}</Text>
    </View>
  );
}

// 38-DESIGN-v2 A-3 강사 코드 줄 — 흰 면 · 1px divider · 반경 15 · 패딩 12 12 12 16 · 가로.
// 왼쪽 `내 강사 코드` 13 textMid / 코드 20/700 brand(+6%). 오른쪽 알약 2개(36 · 반경 18 · 1px
// inputBorder · 15/700 · 좌우 14 · 간격 8). 알약은 36 이라 hitSlop 4 로 터치 44 를 채운다.
export function CodeRow({
  label,
  code,
  copyLabel,
  onCopy,
  bigLabel,
  onBig,
}: {
  label: string;
  code: string;
  copyLabel: string;
  onCopy: () => void;
  bigLabel: string;
  onBig: () => void;
}) {
  return (
    <View style={s.codeRow}>
      <View style={s.codeRowText}>
        <Text style={text.caption13}>{label}</Text>
        <Text style={text.code} selectable>
          {code}
        </Text>
      </View>
      <View style={s.codeRowBtns}>
        <ChipButton label={copyLabel} onPress={onCopy} />
        <ChipButton label={bigLabel} onPress={onBig} />
      </View>
    </View>
  );
}

function ChipButton({ label, onPress }: { label: string; onPress: () => void }) {
  const slop = (H.touch - H.chipBtn) / 2;
  return (
    <Pressable
      onPress={onPress}
      hitSlop={{ top: slop, bottom: slop, left: space.xs, right: space.xs }}
      style={({ pressed }) => [s.chipBtn, pressed && s.pressed]}
      accessibilityRole="button"
      accessibilityLabel={label}
    >
      <Text style={text.body15Bold}>{label}</Text>
    </Pressable>
  );
}

// 38-DESIGN-v2 크게 보기(299:666) — 흰 전체 화면 모달. 오른쪽 위 X 28(터치 44). 세로 가운데:
// 제목 20/700 textMid → 16 → 코드 700 brand(자간 +8%, 크기 = bigCodeFontSize — 72 기본, 긴 코드는
// 폭에 맞춰 줄인다) → 24 → 안내 17 textMid 가운데. 열고 닫기는 fade(투명도만). 웹 ESC 는
// react-native-web ModalContent 가 onRequestClose 를 부른다.
export function BigCodeModal({
  visible,
  title,
  code,
  how,
  closeLabel,
  onClose,
}: {
  visible: boolean;
  title: string;
  code: string;
  how: string;
  closeLabel: string;
  onClose: () => void;
}) {
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const size = bigCodeFontSize(code.length, Math.min(width, FRAME_MAX_W) - space.screen * 2);
  return (
    <Modal visible={visible} animationType="fade" transparent={false} onRequestClose={onClose}>
      <View style={[s.bigPage, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
        <View style={s.bigTop}>
          <Pressable
            onPress={onClose}
            style={({ pressed }) => [s.bigClose, pressed && s.pressed]}
            accessibilityRole="button"
            accessibilityLabel={closeLabel}
          >
            <Ionicons name="close" size={28} color={colors.textPrimary} />
          </Pressable>
        </View>
        <View style={s.bigBody}>
          <Text style={[text.heading, text.mid, text.center]}>{title}</Text>
          <Text
            style={[
              s.bigCode,
              { fontSize: size, lineHeight: Math.round(size * 1.2), letterSpacing: size * 0.08 },
            ]}
            numberOfLines={1}
            selectable
          >
            {code}
          </Text>
          <Text style={[text.label, text.mid, text.center, s.mt24]}>{how}</Text>
        </View>
      </View>
    </Modal>
  );
}

// ── 상세 패널 (A-3b · 만료 · A-3c) ─────────────────────────────────────────
//
// 1:428 / 1:479 / 1:482 / 1:483 / 1:486 / 1:458 (실패) · 1:498 (완료) 의 **구조**만 가져온다 —
// 원형은 AI분석 계열 다크 화면이라 색은 라이트 토큰으로 옮긴다(UI-SPEC Figma 참조 표 서두).
// 원형 X = 링 brand · 원형 체크 = 링 progressGreen. 문구는 전부 호출부가 supplierCopy/supplierRules 로.

function RingIcon({ name, color }: { name: 'close' | 'checkmark'; color: string }) {
  return (
    <View style={[s.ring, { borderColor: color }]}>
      <Ionicons name={name} size={36} color={color} />
    </View>
  );
}

// 38-DESIGN A-3b 실패 패널 + 만료 패널(리뷰 R4: code·tip 없이). 내용 y≈128(TopBar 아래 24).
// X 링 72 → 24 → 제목 18/700 → 8 → 본문 17 textMid → 8 → 코드 칩(패딩 2 8, 12 resultTextSub) →
// 24 → TIP → 24 → CTA 54 → 16 → `목록으로` 가운데.
export function FailurePanel({
  title,
  body,
  code,
  tip,
  reuploadLabel,
  onReupload,
  backLabel,
  onBack,
}: {
  title: string;
  body: string;
  code?: string | null;
  tip?: { head: string; lines: readonly string[] } | null;
  reuploadLabel: string;
  onReupload: () => void;
  backLabel: string;
  onBack: () => void;
}) {
  return (
    <View style={[s.panel, s.panelFail]}>
      <RingIcon name="close" color={colors.brand} />
      <Text style={[text.title, text.center, s.mt24]} accessibilityRole="header">
        {title}
      </Text>
      <Text style={[text.label, text.mid, text.center, s.mt8]}>{body}</Text>
      {code ? (
        <View style={[s.chip, s.mt8]}>
          <Text style={text.caption}>{code}</Text>
        </View>
      ) : null}
      {tip ? (
        <View style={[s.stretch, s.mt24]}>
          <TipCard head={tip.head} lines={tip.lines} />
        </View>
      ) : null}
      <View style={[s.stretch, s.mt24]}>
        <PrimaryCta label={reuploadLabel} onPress={onReupload} />
      </View>
      <View style={s.mt16}>
        <TextLink label={backLabel} onPress={onBack} tone="cancel" center />
      </View>
    </View>
  );
}

export type InfoRow = { label: string; value: string };

// 38-DESIGN A-3c 완료 패널 — 내용 y≈112(TopBar 아래 8). 체크 링 → 20 → `등록됐어요` 18/700 → 4 →
// `{name} · {athlete} 선수` 17 textMid → 24 → 재현성 카드(softBg · 반경 15 · 패딩 16):
// 제목 17/700 왼쪽 + `{score}점` 20/700 brand 오른쪽(점수가 있을 때만) → 4 → 본문 보조 → 8 → 고지
// 흐린 보조(리뷰 R11 · D-11 — 항상) → 16 → 정보 표 카드(행 7, 세로 10, 사이 dividerSoft) →
// 낮음이면 24 → TIP → 24 → 다시 올리기 → 24 → `목록으로`.
// 점수·본문·낮음 분기는 호출부가 supplierRules.selfCheckView 한 값으로 정한다(표시 = 분기).
export function DonePanel({
  title,
  sub,
  selfTitle,
  scoreText,
  selfBody,
  note,
  info,
  low,
  tip,
  reuploadLabel,
  onReupload,
  backLabel,
  onBack,
}: {
  title: string;
  sub: string;
  selfTitle: string;
  scoreText: string | null;
  selfBody: string;
  note: string;
  info: readonly InfoRow[];
  low: boolean;
  tip: { head: string; lines: readonly string[] };
  reuploadLabel: string;
  onReupload: () => void;
  backLabel: string;
  onBack: () => void;
}) {
  return (
    <View style={[s.panel, s.panelDone]}>
      <RingIcon name="checkmark" color={colors.progressGreen} />
      <Text style={[text.title, text.center, s.mt20]} accessibilityRole="header">
        {title}
      </Text>
      <Text style={[text.label, text.mid, text.center, s.mt4]}>{sub}</Text>
      <View style={[s.selfCard, s.stretch, s.mt24]}>
        <View style={s.selfHead}>
          <Text style={[text.labelBold, s.flex]}>{selfTitle}</Text>
          {scoreText ? <Text style={[text.heading, s.scoreNum]}>{scoreText}</Text> : null}
        </View>
        <Text style={[text.aux, s.mt4]}>{selfBody}</Text>
        <Text style={[text.auxFaint, s.mt8]}>{note}</Text>
      </View>
      <View style={[s.card, s.infoCard, s.stretch, s.mt16]}>
        {info.map((r, i) => (
          <View key={r.label} style={[s.infoRow, i < info.length - 1 && s.rowDivider]}>
            <Text style={text.aux}>{r.label}</Text>
            <Text style={[text.body15Bold, s.infoValue]}>{r.value}</Text>
          </View>
        ))}
      </View>
      {low ? (
        <>
          <View style={[s.stretch, s.mt24]}>
            <TipCard head={tip.head} lines={tip.lines} />
          </View>
          <View style={[s.stretch, s.mt24]}>
            <PrimaryCta label={reuploadLabel} onPress={onReupload} />
          </View>
        </>
      ) : null}
      <View style={s.mt24}>
        <TextLink label={backLabel} onPress={onBack} tone="cancel" center />
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  flex: { flex: 1 },
  stretch: { alignSelf: 'stretch' },
  frame: { flex: 1, width: '100%', maxWidth: FRAME_MAX_W, alignSelf: 'center', backgroundColor: colors.bg },
  pressed: { opacity: 0.7 },
  busy: { opacity: 0.6 },
  cardPressed: { opacity: 0.4 },
  mt2: { marginTop: space.xxs },
  mt4: { marginTop: space.xs },
  mt8: { marginTop: space.sm },
  mt12: { marginTop: space.row },
  mt16: { marginTop: space.md },
  mt20: { marginTop: space.screen },
  mt24: { marginTop: space.lg },
  onBrand: { color: colors.textWhite },

  topBar: {
    height: H.touch,
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.xs,
  },
  backBtn: {
    width: H.touch,
    height: H.touch,
    marginLeft: -space.sm,
    alignItems: 'center',
    justifyContent: 'center',
  },

  chipLogin: {
    alignSelf: 'flex-start',
    backgroundColor: colors.softBg,
    borderRadius: R.chip,
    paddingVertical: space.xs,
    paddingHorizontal: space.s10,
  },

  header: {
    paddingHorizontal: space.screen,
    paddingBottom: SHEET_OVERLAP + space.lg,
  },
  headerTop: {
    height: H.touch,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  sheet: {
    marginTop: -SHEET_OVERLAP,
    borderTopLeftRadius: R.sheet,
    borderTopRightRadius: R.sheet,
    paddingTop: space.screen,
    paddingHorizontal: space.screen,
    paddingBottom: space.lg,
  },

  card: {
    backgroundColor: colors.cardBg,
    borderWidth: BORDER,
    borderColor: colors.divider,
    borderRadius: R.card,
    padding: spacing.cardPadding,
  },
  grayCard: {
    backgroundColor: colors.softBg,
    borderRadius: R.card,
    padding: spacing.cardPadding,
  },

  sectionHead: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: space.sm,
  },

  row: {
    minHeight: H.rowMin,
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.row,
    paddingVertical: space.row,
    borderRadius: R.thumb,
  },
  rowDivider: { borderBottomWidth: BORDER, borderBottomColor: colors.dividerSoft },
  rowHighlighted: { borderWidth: 1, borderColor: colors.brand, paddingHorizontal: space.sm },
  thumb: {
    width: H.thumb,
    height: H.thumb,
    borderRadius: R.thumb,
    backgroundColor: colors.softBg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  rowText: { flex: 1, gap: space.xxs },
  progressDot: {
    width: space.sm,
    height: space.sm,
    borderRadius: space.xs,
    backgroundColor: colors.brandButtonDisabled,
  },

  pillWrap: { alignSelf: 'stretch' },
  pill: {
    height: H.pill,
    borderRadius: R.pill,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: space.xs,
    paddingHorizontal: space.md,
  },
  primary: {
    height: H.cta,
    borderRadius: R.button,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'stretch',
  },
  primaryDisabled: { backgroundColor: colors.brandButtonDisabled },
  outline: {
    minHeight: H.outline,
    borderRadius: R.button,
    borderWidth: 1,
    borderColor: colors.inputBorder,
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'stretch',
    paddingHorizontal: space.md,
  },
  google: {
    height: H.google,
    borderRadius: R.button,
    borderWidth: 1,
    borderColor: colors.inputBorder,
    backgroundColor: colors.bg,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: space.s10,
    alignSelf: 'stretch',
    paddingHorizontal: space.md,
  },
  link: { minHeight: H.touch, justifyContent: 'center', alignSelf: 'flex-start' },
  linkCenter: { alignSelf: 'center' },
  linkGo: { color: colors.brand, textDecorationLine: 'underline' },
  linkSignOut: { color: colors.infoTeal, textDecorationLine: 'underline' },
  linkCancel: { color: colors.textMid, textDecorationLine: 'underline' },
  linkOnHeader: { color: colors.textWhite, textDecorationLine: 'underline' },

  notice: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.row,
    borderRadius: R.noticePill,
    borderWidth: 1,
    borderColor: colors.divider,
    backgroundColor: colors.bg,
    paddingVertical: space.row,
    paddingHorizontal: space.md,
  },
  tipCard: { alignSelf: 'stretch' },
  tipHead: { flexDirection: 'row', alignItems: 'center', gap: space.s6 },
  tipLines: { marginTop: space.sm, gap: space.xs },
  stepCard: {
    backgroundColor: colors.cardBg,
    borderWidth: 1,
    borderStyle: 'dashed',
    borderColor: colors.brand,
    borderRadius: R.card,
    paddingVertical: space.screen,
    paddingHorizontal: space.md,
    alignItems: 'center',
  },
  accountBox: {
    alignSelf: 'stretch',
    backgroundColor: colors.softBg,
    borderRadius: R.button,
    paddingVertical: space.s14,
    paddingHorizontal: space.md,
  },
  contactRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.row,
    borderWidth: BORDER,
    borderColor: colors.divider,
    borderRadius: R.button,
    paddingVertical: space.row,
    paddingHorizontal: space.md,
  },
  contactIcon: {
    width: H.contactIcon,
    height: H.contactIcon,
    borderRadius: R.chip,
    alignItems: 'center',
    justifyContent: 'center',
  },
  contactIconKakao: { backgroundColor: sns.kakao.bg },
  contactIconMail: { backgroundColor: colors.softBg },
  contactText: { flex: 1, gap: space.xxs },
  toast: {
    position: 'absolute',
    left: space.screen,
    right: space.screen,
    backgroundColor: colors.textPrimary,
    borderRadius: R.toast,
    paddingVertical: space.row,
    paddingHorizontal: space.md,
    zIndex: 10,
  },

  codeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.bg,
    borderWidth: BORDER,
    borderColor: colors.divider,
    borderRadius: R.card,
    paddingTop: space.row,
    paddingBottom: space.row,
    paddingRight: space.row,
    paddingLeft: space.md,
  },
  codeRowText: { flex: 1, gap: space.xxs },
  codeRowBtns: { flexDirection: 'row', gap: space.sm },
  chipBtn: {
    height: H.chipBtn,
    borderRadius: H.chipBtn / 2,
    borderWidth: BORDER,
    borderColor: colors.inputBorder,
    paddingHorizontal: space.s14,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.bg,
  },
  bigPage: { flex: 1, backgroundColor: colors.bg },
  bigTop: { flexDirection: 'row', justifyContent: 'flex-end', paddingHorizontal: space.sm },
  bigClose: { width: H.touch, height: H.touch, alignItems: 'center', justifyContent: 'center' },
  bigBody: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: space.screen,
  },
  bigCode: { ...BOLD, color: colors.brand, textAlign: 'center', marginTop: space.md },

  panel: { alignItems: 'center' },
  panelFail: { paddingTop: space.lg },
  panelDone: { paddingTop: space.sm },
  ring: {
    width: H.ring,
    height: H.ring,
    borderRadius: H.ring / 2,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  chip: {
    backgroundColor: colors.softBg,
    borderRadius: R.chip,
    paddingVertical: space.xxs,
    paddingHorizontal: space.sm,
  },
  selfCard: {
    backgroundColor: colors.softBg,
    borderRadius: R.card,
    padding: spacing.cardPadding,
  },
  selfHead: { flexDirection: 'row', alignItems: 'center', gap: space.sm },
  scoreNum: { color: colors.brand },
  infoCard: { paddingVertical: space.xs, paddingHorizontal: spacing.cardPadding },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: space.row,
    paddingVertical: space.s10,
  },
  infoValue: { flexShrink: 1, textAlign: 'right' },
});

// ── 올리기 폼 프리미티브 (Phase 38-11 · UI-SPEC A-4 · A-5 · Component Inventory) ──────────
//
// 2026-09-30 38-DESIGN.md A-4 STEP 01 / STEP 02 · A-5 값으로 갱신. 검증 다이얼로그(PickErrorDialog)는
// 38-DESIGN "바꿀 것 없음" 이라 그대로다. 파일 카드 아이콘-텍스트 간격은 ui-checker flag 11행 16.

const F = {
  input: layout.inputHeight, // 54 (design.md §5-3-1)
  segment: 44, // 38-DESIGN A-4 세그먼트 44
  box: 22, // 체크박스 22
  boxRadius: 8, // radius.listItem 8.58 → 웹 8
  check: 14, // 흰 체크 14
  fileIcon: 32, // 1:407 images-outline 32
  chevron: 20,
  linkChevron: 14, // 38-DESIGN A-4 ① 체크 행 링크의 작은 쉐브론
  track: 8, // A-5 진행 트랙 높이 8 / 반경 4
  stepBar: 4, // 38-DESIGN A-4 진행 막대 높이 4 / 반경 2
  preview: 360, // 38-DESIGN A-4 ④ 미리보기 상자 높이
  thumbW: 40, // 38-DESIGN A-5 썸네일 40×64
  thumbH: 64,
  focusBorder: 1.5, // 38-DESIGN A-4 입력 포커스 테두리
} as const;

// 38-DESIGN A-4 머리 — `STEP 01 / 02` 15/700 brand → 8 → 진행 막대 2칸(높이 4 · 반경 2 · 간격 6 ·
// 균등, 칸 번호 ≤ current = brand, 아니면 trackBg) → 16 → 30 제목.
export function StepHeader({
  step,
  title,
  current,
}: {
  step: string;
  title: string;
  current: 1 | 2;
}) {
  return (
    <View>
      <Text style={text.step}>{step}</Text>
      <View
        style={f.stepBars}
        accessibilityRole="progressbar"
        accessibilityValue={{ min: 1, max: 2, now: current }}
      >
        {[1, 2].map((n) => (
          <View key={n} style={[f.stepBar, n <= current && f.stepBarOn]} />
        ))}
      </View>
      <Text style={[text.display, s.mt16]} accessibilityRole="header">
        {title}
      </Text>
    </View>
  );
}

// 인라인 오류 — Label 17 infoTeal, 위 8, aria-live polite(UI-SPEC Input 규격).
export function FieldError({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <Text style={[text.label, f.error]} accessibilityLiveRegion="polite">
      {message}
    </Text>
  );
}

// 도움말 — 38-DESIGN §0 보조 문구 15 textMid, 위 8.
export function Helper({ children }: { children: string }) {
  return <Text style={[text.aux, f.helper]}>{children}</Text>;
}

// 입력 54 / 반경 13 · 테두리 1px inputBorder → 포커스 1.5px brand(38-DESIGN A-4) → 오류 inputError ·
// 라벨 17/700 위 8 · 오류 아래 8.
export function TextInput54({
  label,
  value,
  onChangeText,
  placeholder,
  maxLength,
  error,
}: {
  label?: string;
  value: string;
  onChangeText: (v: string) => void;
  placeholder?: string;
  maxLength?: number;
  error?: string | null;
}) {
  const [focused, setFocused] = useState(false);
  return (
    <View>
      {label ? <Text style={[text.labelBold, f.fieldLabel]}>{label}</Text> : null}
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={colors.resultTextSub}
        maxLength={maxLength}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        accessibilityLabel={label ?? placeholder}
        style={[
          text.label,
          f.input,
          focused && f.inputFocus,
          !!error && !focused && f.inputError,
        ]}
      />
      <FieldError message={error ?? null} />
    </View>
  );
}

export type SelectOption = { value: string; label: string };

// Select — 웹은 네이티브 `<select>` 를 Input 규격으로(54 · 13 · 1px inputBorder · 값 17 · 오른쪽
// chevron-down 20 textMid). 라벨 17/700(38-DESIGN A-4 ②). 이 라우트는 웹 전용(38-04 option-1)이라
// 네이티브는 옵션 목록 버튼으로만 둔다(Picker 패키지 설치 0).
export function SelectField({
  label,
  placeholder,
  options,
  value,
  onChange,
  error,
}: {
  label: string;
  placeholder: string;
  options: readonly SelectOption[];
  value: string | null;
  onChange: (value: string) => void;
  error?: string | null;
}) {
  if (Platform.OS === 'web') {
    const border = error ? colors.inputError : colors.inputBorder;
    return (
      <View>
        <Text style={[text.labelBold, f.fieldLabel]}>{label}</Text>
        <View style={f.selectWrap}>
          <select
            aria-label={label}
            value={value ?? ''}
            onChange={(e) => onChange(e.target.value)}
            style={{
              width: '100%',
              height: F.input,
              borderRadius: radius.button,
              border: `1px solid ${border}`,
              backgroundColor: colors.bg,
              color: value ? colors.textPrimary : colors.resultTextSub,
              fontFamily: fontFamily.regular,
              fontSize: typography.buttonSecondary.fontSize,
              paddingLeft: space.md,
              paddingRight: space.md + F.chevron + space.sm,
              appearance: 'none',
              WebkitAppearance: 'none',
            }}
          >
            <option value="" disabled>
              {placeholder}
            </option>
            {options.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <View style={f.selectChevron} pointerEvents="none">
            <Ionicons name="chevron-down" size={F.chevron} color={colors.textMid} />
          </View>
        </View>
        <FieldError message={error ?? null} />
      </View>
    );
  }
  return (
    <View>
      <Text style={[text.labelBold, f.fieldLabel]}>{label}</Text>
      <View style={f.optionList} accessibilityRole="radiogroup">
        {options.map((o) => {
          const on = o.value === value;
          return (
            <Pressable
              key={o.value}
              onPress={() => onChange(o.value)}
              style={({ pressed }) => [f.option, on && f.optionOn, pressed && s.pressed]}
              accessibilityRole="radio"
              accessibilityState={{ checked: on }}
            >
              <Text style={[text.label, on && s.onBrand]}>{o.label}</Text>
            </Pressable>
          );
        })}
      </View>
      <FieldError message={error ?? null} />
    </View>
  );
}

// 탭/세그먼트 — 균등 가로, 간격 8, 44 / 13, 미선택 흰 + 테두리 divider + 700 textMid,
// 선택 = brand 채움 + 흰 글자(38-DESIGN A-4 ② 레벨 · ③ 네/아니오). role radiogroup / radio.
export function Segment<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: readonly { value: T; label: string }[];
  value: T | null;
  onChange: (value: T) => void;
}) {
  return (
    <View style={f.segment} accessibilityRole="radiogroup" accessibilityLabel={label}>
      {options.map((o) => {
        const on = o.value === value;
        return (
          <Pressable
            key={o.value}
            onPress={() => onChange(o.value)}
            style={({ pressed }) => [f.segItem, on && f.segItemOn, pressed && s.pressed]}
            accessibilityRole="radio"
            accessibilityLabel={o.label}
            accessibilityState={{ checked: on }}
          >
            <Text style={[text.labelBold, on ? s.onBrand : text.mid]}>{o.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

function CheckBox({ checked }: { checked: boolean }) {
  return (
    <View style={[f.box, checked && f.boxOn]}>
      {checked ? <Ionicons name="checkmark" size={F.check} color={colors.textWhite} /> : null}
    </View>
  );
}

// 38-DESIGN A-4 ① 촬영 전 체크 카드 — Card(패딩 16 16 8): 머리 AlertIcon 18 + 6 + 18/700 → 12 →
// 항목(간격 8) 번호 1~5 15/700 brand + 10 + 본문 15 → 12 → 구분선 → 체크 행(세로 13): 체크박스 22
// + 10 + 확인 문구 17/700 · 오른쪽 링크 15 brand + 작은 쉐브론(가이드로).
// 문구 원문(supplierCopy.form.sec1.items)은 `· ` 로 시작한다 — 번호가 그 자리를 대신해 화면에서만
// 떼어 보여 준다(원문은 그대로, 38-DESIGN A-4 ①).
export function CheckCard({
  title,
  items,
  confirmLabel,
  checked,
  onToggle,
  linkLabel,
  onLink,
}: {
  title: string;
  items: readonly string[];
  confirmLabel: string;
  checked: boolean;
  onToggle: () => void;
  linkLabel: string;
  onLink: () => void;
}) {
  return (
    <View style={[s.card, f.checkCard]}>
      <View style={f.checkCardHead}>
        <AlertIcon size={18} />
        <Text style={[text.title, s.flex]} accessibilityRole="header">
          {title}
        </Text>
      </View>
      <View style={f.checkItems}>
        {items.map((item, i) => (
          <View key={item} style={f.checkItem}>
            <Text style={text.step}>{String(i + 1)}</Text>
            <Text style={[text.body15, s.flex]}>{item.replace(/^·\s*/, '')}</Text>
          </View>
        ))}
      </View>
      <View style={f.checkConfirmRow}>
        <Pressable
          onPress={onToggle}
          style={({ pressed }) => [f.checkConfirm, pressed && s.pressed]}
          accessibilityRole="checkbox"
          accessibilityState={{ checked }}
          accessibilityLabel={confirmLabel}
        >
          <CheckBox checked={checked} />
          <Text style={[text.labelBold, s.flex]}>{confirmLabel}</Text>
        </Pressable>
        <Pressable
          onPress={onLink}
          style={({ pressed }) => [f.checkLink, pressed && s.pressed]}
          accessibilityRole="link"
          accessibilityLabel={linkLabel}
          hitSlop={8}
        >
          <Text style={[text.body15, f.brandText]}>{linkLabel}</Text>
          <Ionicons name="chevron-forward" size={F.linkChevron} color={colors.brand} />
        </Pressable>
      </View>
    </View>
  );
}

// 38-DESIGN A-4 체크 행 — 체크박스 22 + 10 + 한 문단 17(태그 `[필수]` 700 brand / `[선택]` 700
// resultTextSub 가 같은 문단 안), 세로 12. inset = 가로 16(STEP 02 동의 행). 부연 = 아래 4 에
// 13 resultTextSub. chevron(상세가 있을 때, 따로 누른다) 20 inputBorder.
export function CheckboxRow({
  label,
  checked,
  onToggle,
  tag,
  note,
  onChevron,
  chevronLabel,
  inset,
}: {
  label: string;
  checked: boolean;
  onToggle: () => void;
  tag?: { text: string; required: boolean };
  note?: string;
  onChevron?: () => void;
  chevronLabel?: string;
  inset?: boolean;
}) {
  return (
    <View style={[f.checkRow, inset && f.checkRowInset]}>
      <Pressable
        onPress={onToggle}
        style={({ pressed }) => [f.checkMain, pressed && s.pressed]}
        accessibilityRole="checkbox"
        accessibilityState={{ checked }}
        accessibilityLabel={tag ? `${tag.text} ${label}` : label}
      >
        <CheckBox checked={checked} />
        <View style={s.flex}>
          <Text style={text.label}>
            {tag ? (
              <Text style={[text.labelBold, tag.required ? f.brandText : text.sub]}>
                {tag.text}{' '}
              </Text>
            ) : null}
            {label}
          </Text>
          {note ? <Text style={[text.caption13, text.sub, s.mt4]}>{note}</Text> : null}
        </View>
      </Pressable>
      {onChevron ? (
        <Pressable
          onPress={onChevron}
          style={({ pressed }) => [f.chevronBtn, pressed && s.pressed]}
          accessibilityRole="link"
          accessibilityLabel={chevronLabel}
          hitSlop={8}
        >
          <Ionicons name="chevron-forward" size={F.chevron} color={colors.inputBorder} />
        </Pressable>
      ) : null}
    </View>
  );
}

// 38-DESIGN A-4 STEP 02 전체 동의 상자 — 54 / 13 / 1px divider / 패딩 0 16: 체크박스 + 12 +
// 17/700(늘어남) + 오른쪽 `필수 3개` 흐린 보조.
export function AllAgreeBox({
  label,
  hint,
  checked,
  onToggle,
}: {
  label: string;
  hint: string;
  checked: boolean;
  onToggle: () => void;
}) {
  return (
    <Pressable
      onPress={onToggle}
      style={({ pressed }) => [f.allAgree, pressed && s.pressed]}
      accessibilityRole="checkbox"
      accessibilityState={{ checked }}
      accessibilityLabel={label}
    >
      <CheckBox checked={checked} />
      <Text style={[text.labelBold, s.flex]}>{label}</Text>
      <Text style={text.auxFaint}>{hint}</Text>
    </Pressable>
  );
}

// 38-DESIGN A-4 STEP 02 철회 고지 — softBg · 반경 15 · 패딩 16 · 보조 문구.
export function WithdrawNote({ text: body }: { text: string }) {
  return (
    <View style={f.withdraw}>
      <Text style={text.aux}>{body}</Text>
    </View>
  );
}

// 1:407 선택 카드(파일) — Card 규격 + images-outline 32 brand → 16(ui-checker flag 11행) →
// Title + 보조 부제(4 아래) → chevron 20. 눌림 opacity 0.4(cardDimmed 선례).
export function FileCard({
  title,
  sub,
  onPress,
  disabled,
}: {
  title: string;
  sub: string;
  onPress: () => void;
  disabled?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [s.card, f.fileCard, (pressed || disabled) && s.cardPressed]}
      accessibilityRole="button"
      accessibilityLabel={title}
      accessibilityState={{ disabled: !!disabled, busy: !!disabled }}
    >
      <Ionicons name="images-outline" size={F.fileIcon} color={colors.brand} />
      <View style={s.flex}>
        <Text style={text.title}>{title}</Text>
        <Text style={[text.aux, s.mt4]}>{sub}</Text>
      </View>
      <Ionicons name="chevron-forward" size={F.chevron} color={colors.inputBorder} />
    </Pressable>
  );
}

// 38-DESIGN A-4 ④ 미리보기 — 전폭 × 360 · 반경 15 · 배경 textPrimary 상자 가운데에 9:16 영상.
// 무음 · 컨트롤 · 자동 재생 없음(프레임 자가 확인용). 어두운 면은 영상 뒤판(videoBg 선례와 같은 예외).
export function VideoPreview({ uri }: { uri: string }) {
  const player = useVideoPlayer(uri, (p) => {
    p.muted = true;
  });
  return (
    <View style={f.previewBox}>
      <VideoView player={player} style={f.preview} nativeControls contentFit="contain" />
    </View>
  );
}

// 38-DESIGN A-5 썸네일 40×64 · 반경 8 — 영상 첫 프레임(재생 안 함, 컨트롤 없음, 무음).
// uri 가 없으면 trackBg 상자만.
export function VideoThumb({ uri }: { uri: string | null }) {
  const player = useVideoPlayer(uri, (p) => {
    p.muted = true;
  });
  return (
    <View style={f.thumb}>
      {uri ? (
        <VideoView player={player} style={f.thumbVideo} nativeControls={false} contentFit="cover" />
      ) : null}
    </View>
  );
}

// 38-DESIGN A-5 파일 요약 카드 — softBg · 반경 15 · 패딩 12 · 가로: 썸네일 → 12 →
// `{name} · {레벨}` 18/700 / 2 / `{파일 이름} · {길이} · {용량}` 보조.
export function UploadSummary({
  uri,
  title,
  meta,
}: {
  uri: string | null;
  title: string;
  meta: string;
}) {
  return (
    <View style={f.summary}>
      <VideoThumb uri={uri} />
      <View style={f.summaryText}>
        <Text style={text.title} numberOfLines={2}>
          {title}
        </Text>
        <Text style={text.aux} numberOfLines={2}>
          {meta}
        </Text>
      </View>
    </View>
  );
}

// 38-DESIGN A-5 진행 — 줄(`올리는 중` 17 왼쪽 + `{pct}%` 17/700 brand 오른쪽, aria-live) → 8 →
// 트랙 8/4 trackBg + 채움 brand · role progressbar(스피너 금지, design.md §0).
export function ProgressBar({
  pct,
  label,
  valueText,
}: {
  pct: number;
  label: string;
  valueText: string;
}) {
  const clamped = Math.max(0, Math.min(100, pct));
  return (
    <View>
      <View style={f.progressHead} accessibilityLiveRegion="polite">
        <Text style={text.label}>{label}</Text>
        <Text style={[text.labelBold, f.brandText]}>{valueText}</Text>
      </View>
      <View
        style={[f.track, s.mt8]}
        accessibilityRole="progressbar"
        accessibilityValue={{ min: 0, max: 100, now: clamped }}
      >
        <View style={[f.fill, { width: `${clamped}%` }]} />
      </View>
    </View>
  );
}

// 38-DESIGN §0 하단 바 재질 — 흰 86% + 뒤 흐림 20(웹 backdrop-filter), 위 테두리 없음. 네이티브는
// 흐림이 없어 흰 96%. 화면 아래에 떠 있으므로(absolute) onHeight 로 높이를 알려 주고, 화면이
// ScrollView contentContainer paddingBottom 에 더해 마지막 내용이 바 뒤에 숨지 않게 한다.
// hint(남은 필수 등)는 CTA 위 보조 문구 가운데(aria-live).
export function BottomBar({
  hint,
  children,
  onHeight,
}: {
  hint: string | null;
  children: ReactNode;
  onHeight?: (height: number) => void;
}) {
  const insets = useSafeAreaInsets();
  return (
    <View
      style={[f.bottomBar, BAR_MATERIAL, { paddingBottom: space.md + insets.bottom }]}
      onLayout={onHeight ? (e) => onHeight(e.nativeEvent.layout.height) : undefined}
    >
      {hint ? (
        <Text style={[text.aux, f.bottomHint]} accessibilityLiveRegion="polite">
          {hint}
        </Text>
      ) : null}
      {children}
    </View>
  );
}

// backdropFilter 는 RN ViewStyle 타입 밖이라 웹에서만 좁은 캐스트로 붙인다. react-native-web 이
// 이 속성을 알고(prefixStyles) -webkit- 접두도 붙인다.
const BAR_MATERIAL: ViewStyle =
  Platform.OS === 'web'
    ? ({ backgroundColor: colors.barGlass, backdropFilter: 'blur(20px)' } as ViewStyle)
    : { backgroundColor: colors.barSolid };

const f = StyleSheet.create({
  fieldLabel: { marginBottom: space.sm },
  error: { color: colors.infoTeal, marginTop: space.sm },
  helper: { marginTop: space.sm },
  brandText: { color: colors.brand },
  stepBars: { flexDirection: 'row', gap: space.s6, marginTop: space.sm },
  stepBar: {
    flex: 1,
    height: F.stepBar,
    borderRadius: F.stepBar / 2,
    backgroundColor: colors.trackBg,
  },
  stepBarOn: { backgroundColor: colors.brand },
  input: {
    height: F.input,
    borderRadius: R.button,
    borderWidth: 1,
    borderColor: colors.inputBorder,
    backgroundColor: colors.bg,
    paddingHorizontal: space.md,
  },
  inputFocus: { borderColor: colors.brand, borderWidth: F.focusBorder },
  inputError: { borderColor: colors.inputError },
  selectWrap: { justifyContent: 'center' },
  selectChevron: { position: 'absolute', right: space.md },
  optionList: { gap: space.sm },
  option: {
    minHeight: F.segment,
    borderRadius: R.button,
    borderWidth: 1,
    borderColor: colors.divider,
    justifyContent: 'center',
    paddingHorizontal: space.md,
  },
  optionOn: { backgroundColor: colors.brand, borderColor: colors.brand },
  segment: { flexDirection: 'row', gap: space.sm },
  segItem: {
    flex: 1,
    height: F.segment,
    borderRadius: R.button,
    borderWidth: 1,
    borderColor: colors.divider,
    backgroundColor: colors.bg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  segItemOn: { backgroundColor: colors.brand, borderColor: colors.brand },

  checkCard: { paddingBottom: space.sm },
  checkCardHead: { flexDirection: 'row', alignItems: 'center', gap: space.s6 },
  checkItems: { marginTop: space.row, gap: space.sm },
  checkItem: { flexDirection: 'row', alignItems: 'flex-start', gap: space.s10 },
  checkConfirmRow: {
    marginTop: space.row,
    borderTopWidth: BORDER,
    borderTopColor: colors.dividerSoft,
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.sm,
  },
  checkConfirm: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.s10,
    paddingVertical: space.s13,
  },
  checkLink: { flexDirection: 'row', alignItems: 'center', gap: space.xxs, minHeight: H.touch },

  checkRow: { flexDirection: 'row', alignItems: 'center' },
  checkRowInset: { paddingHorizontal: space.md },
  checkMain: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: space.s10,
    paddingVertical: space.row,
  },
  chevronBtn: {
    width: H.touch,
    height: H.touch,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: -space.sm,
  },
  box: {
    width: F.box,
    height: F.box,
    borderRadius: F.boxRadius,
    borderWidth: 1,
    borderColor: colors.inputBorder,
    backgroundColor: colors.bg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  boxOn: { backgroundColor: colors.brand, borderColor: colors.brand },
  allAgree: {
    height: F.input,
    borderRadius: R.button,
    borderWidth: 1,
    borderColor: colors.divider,
    paddingHorizontal: space.md,
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.row,
  },
  withdraw: {
    backgroundColor: colors.softBg,
    borderRadius: R.card,
    padding: spacing.cardPadding,
  },
  fileCard: { flexDirection: 'row', alignItems: 'center', gap: space.md },
  previewBox: {
    alignSelf: 'stretch',
    height: F.preview,
    borderRadius: R.card,
    backgroundColor: colors.textPrimary,
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
  },
  preview: { height: F.preview, aspectRatio: 9 / 16 },
  thumb: {
    width: F.thumbW,
    height: F.thumbH,
    borderRadius: R.thumb,
    backgroundColor: colors.trackBg,
    overflow: 'hidden',
  },
  thumbVideo: { width: F.thumbW, height: F.thumbH },
  summary: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.row,
    backgroundColor: colors.softBg,
    borderRadius: R.card,
    padding: space.row,
  },
  summaryText: { flex: 1, gap: space.xxs },
  progressHead: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: space.sm,
  },
  track: {
    height: F.track,
    borderRadius: F.track / 2,
    backgroundColor: colors.trackBg,
    overflow: 'hidden',
  },
  fill: { height: F.track, backgroundColor: colors.brand },
  bottomBar: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    paddingTop: space.md,
    paddingHorizontal: space.screen,
  },
  bottomHint: { marginBottom: space.sm, textAlign: 'center' },
});

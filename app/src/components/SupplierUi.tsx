// 공급자 페이지 공용 프리미티브 (Phase 38-10 · UI-SPEC §Component Inventory).
//
// 원형 = Figma jrdI7kp245HkPfLB0nclsz 노드(1:960 가입 · 1:977 Google · 1:419~424 권한 ·
// 1:717 메인 · 1:743 섹션 · 1:646/663/713/709 선수 카드 · 1:399 알약 · 1:482/483 TIP).
// 값은 UI-SPEC 표의 값(= design.md·theme 에 박제된 같은 Figma 추출값)이다. UI-SPEC 이 `≈` 로
// 남긴 4개(Google 버튼 48 · STEP 라벨 13.8 · 테두리 버튼 48 · 안내 알약 반경 15)는 이 실행에서
// Figma MCP 를 열 수 없어 UI-SPEC 값 그대로 두었다 — 38-10 SUMMARY "Figma 실측" 절 [미확인].
//
// 규칙: 색은 전부 theme 토큰(리터럴 색 0) · 문구는 호출부가 supplierCopy 에서 넘긴다(여기 한국어
// 리터럴 0) · 라이트 전용 · 이모지 0. 간격은 UI-SPEC §Spacing Scale 의 선언값만(`space`).
// ui-checker flags(UI-SPEC §Decisions) 적용: 7행 헤더 = 워드마크 + 제목만 · 8행 TIP 헤더-줄 8 /
// 줄 간 4 · 9행 코드 문자 = textPrimary · 10행 칩 패딩 4 8.

import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useVideoPlayer, VideoView } from 'expo-video';
import { useState, type ReactNode } from 'react';
import {
  Image,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
  type StyleProp,
  type ViewStyle,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { colors, fontFamily, gradients, layout, radius, spacing, typography } from '../theme';
import { AlertIcon } from './PickErrorDialog';
import SocialIcon from './SocialIcon';
import SunityWordmark from './SunityWordmark';

// UI-SPEC §Spacing Scale (4 의 배수 선언값). 새 theme 토큰을 만들지 않고 이 화면군 안에서만 쓴다.
export const space = {
  xs: 4,
  sm: 8,
  row: 12,
  md: 16,
  screen: spacing.screenX, // 20
  lg: 24,
  xl: 32,
  xxl: 48,
} as const;

// UI-SPEC §Spacing Exceptions — 높이 규격.
const H = {
  cta: layout.ctaHeight, // 54
  outline: 48, // 1:423 / 1:424 (≈, 실측 대기)
  google: 48, // 1:977 (≈, 실측 대기)
  pill: 44, // 1:717 알약
  touch: 44,
  thumb: 48, // 1:717 썸네일
  rowMin: 72,
  photo: 180, // 1:646 선수 카드 사진 영역
} as const;

// 반경 — theme 토큰 + UI-SPEC 박제값(시트 17 · 알약 22 · 칩 8 · 토스트 12).
const R = {
  button: radius.button, // 13
  card: radius.card, // 15
  thumb: 8, // radius.listItem 8.58 → 웹 8 (UI-SPEC)
  sheet: 17, // 1:717 17.16 → 17
  pill: 22,
  chip: 8,
  toast: 12,
  noticePill: 15, // 1:399 (≈, 실측 대기)
} as const;

// 웹은 1px(서브픽셀 불안정, UI-SPEC Decisions 20), 앱은 박제값 0.858.
const BORDER = Platform.OS === 'web' ? 1 : layout.cardBorderWidth;

// UI-SPEC §Typography 4단(17 / 18 / 20 / 30) — 기존 토큰 + lineHeight.
export const text = StyleSheet.create({
  label: { ...typography.buttonSecondary, lineHeight: 24, color: colors.textPrimary },
  labelBold: { ...typography.metricNumber, lineHeight: 24, color: colors.textPrimary },
  title: { ...typography.listTitle, lineHeight: 25, color: colors.textPrimary },
  heading: { ...typography.sectionTitle, lineHeight: 28, color: colors.textPrimary },
  display: { ...typography.headline, color: colors.textPrimary },
  caption: { ...typography.caption, color: colors.resultTextSub },
  mid: { color: colors.textMid },
  sub: { color: colors.resultTextSub },
  center: { textAlign: 'center' },
  // 1:960 STEP 라벨 ≈13.8/700 브랜드 — Figma 가 정한 소형이라 17 하한 밖(UI-SPEC Typography 표).
  step: {
    fontSize: 13.8,
    fontWeight: '700',
    fontFamily: fontFamily.bold,
    letterSpacing: 0,
    color: colors.brand,
  },
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
  showWordmark,
  right,
}: {
  onBack?: () => void;
  backLabel?: string;
  showWordmark?: boolean;
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
      {showWordmark ? <SunityWordmark variant="brand" width={59} height={20} /> : null}
      <View style={s.flex} />
      {right}
    </View>
  );
}

// A-3 그라디언트 헤더 — 워드마크(흰) + Display 제목만(ui-checker flag 7행).
export function GradientHeader({ title }: { title: string }) {
  const insets = useSafeAreaInsets();
  return (
    <LinearGradient
      colors={gradients.homeTop.colors}
      locations={gradients.homeTop.locations}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 0.08 }}
      style={[s.header, { paddingTop: insets.top + space.md }]}
    >
      <SunityWordmark variant="white" width={59} height={20} />
      <Text style={[text.display, s.headerTitle]} accessibilityRole="header">
        {title}
      </Text>
    </LinearGradient>
  );
}

// 헤더 위로 −24 겹치는 흰 시트(상단 반경 17, gradients.homeCard).
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

// 1:743 — Heading 20/700 왼쪽 · 오른쪽 `전체보기` + chevron(행 6개 초과일 때만).
export function SectionHeader({
  title,
  moreLabel,
  onMore,
}: {
  title: string;
  moreLabel?: string;
  onMore?: () => void;
}) {
  return (
    <View style={s.sectionHead}>
      <Text style={text.heading} accessibilityRole="header">
        {title}
      </Text>
      {onMore && moreLabel ? (
        <Pressable
          onPress={onMore}
          style={({ pressed }) => [s.moreBtn, pressed && s.pressed]}
          accessibilityRole="link"
          hitSlop={8}
        >
          <Text style={[text.label, text.mid]}>{moreLabel}</Text>
          <Ionicons name="chevron-forward" size={16} color={colors.textMid} />
        </Pressable>
      ) : null}
    </View>
  );
}

// 1:717 행 — 썸네일 48 자리 + Title 18/700 + 부제 17 textMid + chevron(상세가 있는 행만).
export function ListRow({
  title,
  subtitle,
  showChevron,
  onPress,
  highlighted,
  isLast,
  onLayout,
}: {
  title: string;
  subtitle: string;
  showChevron: boolean;
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
        <Text style={[text.label, text.mid]}>{subtitle}</Text>
      </View>
      {showChevron ? (
        <Ionicons name="chevron-forward" size={20} color={colors.inputBorder} />
      ) : null}
    </Pressable>
  );
}

// ── 버튼 ─────────────────────────────────────────────────────────────────

// 1:717 알약 CTA — 높이 44 · 반경 22 · gradients.brandButton · 흰 Label 17/700.
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
      style={({ pressed }) => [s.outline, (pressed || disabled) && s.pressed]}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: !!disabled }}
      accessibilityLiveRegion="polite"
    >
      <Text style={text.labelBold}>{label}</Text>
    </Pressable>
  );
}

// 1:977 — 흰 배경 + 1px inputBorder + 왼쪽 16 에 G 20 + Title 18/700 중앙. 진행 중 opacity 0.6.
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
      <View style={s.googleIcon}>
        <SocialIcon id="google" width={20} height={20} />
      </View>
      <Text style={[text.title, s.googleLabel]}>{label}</Text>
    </Pressable>
  );
}

// design.md §0 — 이동 = brand 밑줄 · 로그아웃 = infoTeal · 취소 = textMid 밑줄.
export function TextLink({
  label,
  onPress,
  tone,
}: {
  label: string;
  onPress: () => void;
  tone: 'go' | 'signOut' | 'cancel';
}) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [s.link, pressed && s.pressed]}
      accessibilityRole="link"
      hitSlop={8}
    >
      <Text
        style={[
          text.label,
          tone === 'go' && s.linkGo,
          tone === 'signOut' && s.linkSignOut,
          tone === 'cancel' && s.linkCancel,
        ]}
      >
        {label}
      </Text>
    </Pressable>
  );
}

// ── 안내 · 카드 ───────────────────────────────────────────────────────────

// 1:399 안내 알약 — AlertIcon 24 + Label 17 2줄(podDown 재사용, UI-SPEC Decisions 21).
export function NoticePill({ lines }: { lines: readonly string[] }) {
  return (
    <View style={s.notice} accessibilityRole="alert">
      <AlertIcon size={24} />
      <View style={s.flex}>
        {lines.map((line) => (
          <Text key={line} style={text.label}>
            {line}
          </Text>
        ))}
      </View>
    </View>
  );
}

// 1:482 / 1:483 TIP 카드 — 헤더 alert-circle 16 brand + Label 700 → 8 → 줄(간 4).
export function TipCard({ head, lines }: { head: string; lines: readonly string[] }) {
  return (
    <View style={[s.card, s.tipCard]}>
      <View style={s.tipHead}>
        <Ionicons name="alert-circle" size={16} color={colors.brand} />
        <Text style={text.labelBold}>{head}</Text>
      </View>
      <View style={s.tipLines}>
        {lines.map((line) => (
          <Text key={line} style={text.label}>
            {line}
          </Text>
        ))}
      </View>
    </View>
  );
}

// 1:717 점선 STEP 카드(빈 상태) — STEP 라벨 → 4 → Title → 8 → Label → 16 → 알약.
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
      <Text style={[text.title, s.mt4]}>{title}</Text>
      <Text style={[text.label, text.mid, s.mt8]}>{body}</Text>
      <View style={s.mt16}>{cta}</View>
    </View>
  );
}

// ID box — softBg · 반경 13 · Label 17/700 · 선택 가능(웹 user-select).
export function IdBox({ value }: { value: string }) {
  return (
    <View style={s.idBox}>
      <Text style={text.labelBold} selectable>
        {value}
      </Text>
    </View>
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

// 1:646 / 1:663 / 1:713 선수 카드 — photoURL 있으면 사진 180 + 하단 어둡게 + `폴스포츠`(밑줄 brand)
// + `{name} 선수`; 없으면 흰 카드(1:709). 코드 Display 30/700 = textPrimary(ui-checker flag 9행).
export function CodeCard({
  photoUrl,
  sportLabel,
  athleteLine,
  code,
  pendingLabel,
  copyLabel,
  onCopy,
  howText,
}: {
  photoUrl: string | null;
  sportLabel: string;
  athleteLine: string;
  code: string | null;
  pendingLabel: string;
  copyLabel: string;
  onCopy: () => void;
  howText: string;
}) {
  return (
    <View style={[s.card, s.codeCard]}>
      {photoUrl ? (
        <View style={s.photo}>
          <Image source={{ uri: photoUrl }} style={StyleSheet.absoluteFill} resizeMode="cover" />
          {/* 하단 어둡게 — 색 리터럴 없이 textPrimary + opacity (UI-SPEC 오버레이 0→0.5 근사) */}
          <View style={s.photoShade} />
          <View style={s.photoText}>
            <Text style={[text.labelBold, s.onBrand, s.sportUnderline]}>{sportLabel}</Text>
            <Text style={[text.title, s.onBrand]}>{athleteLine}</Text>
          </View>
        </View>
      ) : (
        <View style={s.codeNameOnly}>
          <Text style={[text.labelBold, s.sportUnderline]}>{sportLabel}</Text>
          <Text style={text.title}>{athleteLine}</Text>
        </View>
      )}
      <View style={s.codeBody}>
        {code ? (
          <>
            <Text style={[text.display, text.center]} selectable>
              {code}
            </Text>
            <View style={s.mt8}>
              <OutlineButton label={copyLabel} onPress={onCopy} />
            </View>
          </>
        ) : (
          <Text style={[text.label, text.mid, text.center]}>{pendingLabel}</Text>
        )}
        <Text style={[text.label, text.mid, s.mt12]}>{howText}</Text>
      </View>
    </View>
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

// A-3b 실패 패널 + 만료 패널(리뷰 R4: code·tip 없이). 코드 칩 패딩 4 8(ui-checker flag 10행).
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
    <View style={s.panel}>
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
        <View style={[s.panelBlock, s.mt24]}>
          <TipCard head={tip.head} lines={tip.lines} />
        </View>
      ) : null}
      <View style={[s.panelBlock, s.mt24]}>
        <PrimaryCta label={reuploadLabel} onPress={onReupload} />
      </View>
      <View style={s.mt8}>
        <TextLink label={backLabel} onPress={onBack} tone="cancel" />
      </View>
    </View>
  );
}

export type InfoRow = { label: string; value: string };

// A-3c 완료 패널 — 재현성 줄(점수 숫자만 Heading 20/700 brand, UI-SPEC Color accent 5) + 바로 아래
// 고지(row.self.note, 리뷰 R11 · D-11 — 항상) + 정보 표 + 낮으면 TIP·다시 올리기.
export function DonePanel({
  title,
  selfLine,
  score,
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
  selfLine: string;
  score: number | null;
  note: string;
  info: readonly InfoRow[];
  low: boolean;
  tip: { head: string; lines: readonly string[] };
  reuploadLabel: string;
  onReupload: () => void;
  backLabel: string;
  onBack: () => void;
}) {
  // 숫자 강조는 표시만 — 문구·분기는 supplierRules.selfCheckLine 이 이미 정했다.
  const scoreText = score != null ? String(score) : null;
  const at = scoreText ? selfLine.indexOf(scoreText) : -1;
  return (
    <View style={s.panel}>
      <RingIcon name="checkmark" color={colors.progressGreen} />
      <Text style={[text.title, text.center, s.mt24]} accessibilityRole="header">
        {title}
      </Text>
      <Text style={[text.label, text.mid, text.center, s.mt8]}>
        {at >= 0 && scoreText ? (
          <>
            {selfLine.slice(0, at)}
            <Text style={[text.heading, s.scoreNum]}>{scoreText}</Text>
            {selfLine.slice(at + scoreText.length)}
          </>
        ) : (
          selfLine
        )}
      </Text>
      <Text style={[text.label, text.mid, text.center, s.mt4]}>{note}</Text>
      <View style={[s.card, s.panelBlock, s.mt24]}>
        {info.map((r, i) => (
          <View key={r.label} style={[s.infoRow, i < info.length - 1 && s.rowDivider]}>
            <Text style={[text.label, text.mid]}>{r.label}</Text>
            <Text style={[text.labelBold, s.infoValue]}>{r.value}</Text>
          </View>
        ))}
      </View>
      {low ? (
        <>
          <View style={[s.panelBlock, s.mt24]}>
            <TipCard head={tip.head} lines={tip.lines} />
          </View>
          <View style={[s.panelBlock, s.mt24]}>
            <PrimaryCta label={reuploadLabel} onPress={onReupload} />
          </View>
        </>
      ) : null}
      <View style={s.mt8}>
        <TextLink label={backLabel} onPress={onBack} tone="cancel" />
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  flex: { flex: 1 },
  frame: { flex: 1, width: '100%', maxWidth: 430, alignSelf: 'center', backgroundColor: colors.bg },
  pressed: { opacity: 0.7 },
  busy: { opacity: 0.6 },
  cardPressed: { opacity: 0.4 },
  mt4: { marginTop: space.xs },
  mt8: { marginTop: space.sm },
  mt12: { marginTop: space.row },
  mt16: { marginTop: space.md },
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

  header: {
    paddingHorizontal: space.screen,
    paddingBottom: space.md + space.lg, // 시트 겹침 24 포함
  },
  headerTitle: { color: colors.textWhite, marginTop: space.md },
  sheet: {
    marginTop: -space.lg,
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
  },
  moreBtn: { flexDirection: 'row', alignItems: 'center', minHeight: H.touch },

  row: {
    minHeight: H.rowMin,
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.row,
    paddingVertical: space.row,
    borderRadius: R.thumb,
  },
  rowDivider: { borderBottomWidth: BORDER, borderBottomColor: colors.divider },
  rowHighlighted: { borderWidth: 1, borderColor: colors.brand, paddingHorizontal: space.sm },
  thumb: {
    width: H.thumb,
    height: H.thumb,
    borderRadius: R.thumb,
    backgroundColor: colors.softBg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  rowText: { flex: 1, gap: space.xs },

  pillWrap: { alignSelf: 'stretch' },
  pill: {
    height: H.pill,
    borderRadius: R.pill,
    alignItems: 'center',
    justifyContent: 'center',
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
    minHeight: H.google,
    borderRadius: R.button,
    borderWidth: 1,
    borderColor: colors.inputBorder,
    backgroundColor: colors.bg,
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'stretch',
    paddingHorizontal: space.xxl,
  },
  googleIcon: { position: 'absolute', left: space.md },
  googleLabel: { textAlign: 'center' },
  link: { minHeight: H.touch, justifyContent: 'center', alignSelf: 'flex-start' },
  linkGo: { color: colors.brand, textDecorationLine: 'underline' },
  linkSignOut: { color: colors.infoTeal },
  linkCancel: { color: colors.textMid, textDecorationLine: 'underline' },

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
  tipHead: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  tipLines: { marginTop: space.sm, gap: space.xs },
  stepCard: {
    backgroundColor: colors.cardBg,
    borderWidth: 1,
    borderStyle: 'dashed',
    borderColor: colors.brand,
    borderRadius: R.card,
    padding: spacing.cardPadding,
  },
  idBox: {
    backgroundColor: colors.softBg,
    borderRadius: R.button,
    paddingVertical: space.row,
    paddingHorizontal: space.md,
  },
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

  codeCard: { padding: 0, overflow: 'hidden' },
  photo: { height: H.photo, justifyContent: 'flex-end' },
  photoShade: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    height: H.photo / 2,
    backgroundColor: colors.textPrimary,
    opacity: 0.5,
  },
  photoText: { padding: spacing.cardPadding, gap: space.xs },
  sportUnderline: {
    alignSelf: 'flex-start',
    borderBottomWidth: 2,
    borderBottomColor: colors.brand,
  },
  codeNameOnly: {
    paddingTop: spacing.cardPadding,
    paddingHorizontal: spacing.cardPadding,
    gap: space.xs,
  },
  codeBody: { padding: spacing.cardPadding },

  mt24: { marginTop: space.lg },
  panel: { alignItems: 'center', paddingTop: space.xl },
  panelBlock: { alignSelf: 'stretch' },
  ring: {
    width: 72,
    height: 72,
    borderRadius: 36,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  chip: {
    backgroundColor: colors.softBg,
    borderRadius: R.chip,
    paddingVertical: space.xs,
    paddingHorizontal: space.sm,
  },
  scoreNum: { color: colors.brand },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: space.row,
    paddingVertical: space.row,
  },
  infoValue: { flexShrink: 1, textAlign: 'right' },
});

// ── 올리기 폼 프리미티브 (Phase 38-11 · UI-SPEC A-4 · A-5 · Component Inventory) ──────────
//
// Figma D-22 실측(`1:960` 입력/STEP/CTA · `1:1064` 동의 행 · `1:407` 파일 카드 · `1:499`
// 다이얼로그)은 이 실행에서도 Figma MCP 가 열리지 않아 못 했다 — 값은 UI-SPEC Component
// Inventory 그대로이고 38-11 SUMMARY "Figma 실측" 표에 [미확인] 으로 남겨 38-13 Task 3 로 넘긴다.
// 파일 카드 아이콘-텍스트 간격만 ui-checker flag 11행 적용값 16.

const F = {
  input: layout.inputHeight, // 54 (design.md §5-3-1)
  segment: 44, // 탭 44 (UI-SPEC 탭/세그먼트)
  checkRow: 48, // 체크 행 최소 48
  box: 22, // 체크박스 22
  boxRadius: 8, // radius.listItem 8.58 → 웹 8
  check: 14, // 흰 체크 14
  fileIcon: 32, // 1:407 images-outline 32
  chevron: 20,
  track: 8, // 진행 막대 높이 8 / 반경 4
  previewMaxH: 360, // Video preview 최대 높이
} as const;

// `STEP 01 / 02` — brand 소문 라벨(1:960) → 4 → Display 제목.
export function StepHeader({ step, title }: { step: string; title: string }) {
  return (
    <View>
      <Text style={text.step}>{step}</Text>
      <Text style={[text.display, s.mt4]} accessibilityRole="header">
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

// 도움말 — Label 17 textMid, 위 8.
export function Helper({ children }: { children: string }) {
  return <Text style={[text.label, text.mid, f.helper]}>{children}</Text>;
}

// 입력 54 / 반경 13 · 테두리 inputBorder → 포커스 brand → 오류 inputError · 라벨 위 8 · 오류 아래 8.
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
      {label ? <Text style={[text.label, f.fieldLabel]}>{label}</Text> : null}
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

// Select — 웹은 네이티브 `<select>` 를 Input 규격으로(오른쪽 chevron 20 textMid). 이 라우트는
// 웹 전용(38-04 option-1)이라 네이티브는 옵션 목록 버튼으로만 둔다(Picker 패키지 설치 0).
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
        <Text style={[text.label, f.fieldLabel]}>{label}</Text>
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
      <Text style={[text.label, f.fieldLabel]}>{label}</Text>
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

// 탭/세그먼트 — 균등 가로, 44 / 13, 미선택 흰 + 테두리 divider + Label 700 textMid,
// 선택 = brand 채움 + 흰 글자(reference.tsx 탭 문법). role radiogroup / radio.
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

// 1:1064 체크 행 — 행 전체 탭, 최소 48, 박스 22/8, 태그 `[필수]` brand 700 / `[선택]`
// resultTextSub 700 → 4 → 라벨 → chevron(상세가 있을 때, 따로 누른다) · 부연 12 caption 아래 4.
export function CheckboxRow({
  label,
  checked,
  onToggle,
  tag,
  note,
  onChevron,
  chevronLabel,
}: {
  label: string;
  checked: boolean;
  onToggle: () => void;
  tag?: { text: string; required: boolean };
  note?: string;
  onChevron?: () => void;
  chevronLabel?: string;
}) {
  return (
    <View style={f.checkRow}>
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
              <Text style={[text.labelBold, tag.required ? f.tagRequired : text.sub]}>
                {tag.text}{' '}
              </Text>
            ) : null}
            {label}
          </Text>
          {note ? <Text style={[text.caption, s.mt4]}>{note}</Text> : null}
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

// 1:1064 전체 동의 박스 — 54 / 13, 테두리 divider, 패딩 0 16: 체크박스 22 + 12 + Label 700.
export function AllAgreeBox({
  label,
  checked,
  onToggle,
}: {
  label: string;
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
      <Text style={text.labelBold}>{label}</Text>
    </Pressable>
  );
}

// 1:407 선택 카드(파일) — Card 규격 + images-outline 32 brand → 16(ui-checker flag 11행) →
// Title + Label 부제(4 아래) → chevron 20. 눌림 opacity 0.4(cardDimmed 선례).
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
        <Text style={[text.label, text.mid, s.mt4]}>{sub}</Text>
      </View>
      <Ionicons name="chevron-forward" size={F.chevron} color={colors.inputBorder} />
    </Pressable>
  );
}

// Video preview — 9:16, 최대 높이 360, 반경 15, 무음 · 컨트롤 · 자동 재생 없음(프레임 자가 확인용).
export function VideoPreview({ uri }: { uri: string }) {
  const player = useVideoPlayer(uri, (p) => {
    p.muted = true;
  });
  return (
    <View style={f.previewWrap}>
      <VideoView player={player} style={f.preview} nativeControls contentFit="contain" />
    </View>
  );
}

// 진행 막대 — 트랙 8/4 trackBg · 채움 brand · role progressbar(스피너 금지, design.md §0).
export function ProgressBar({ pct, label }: { pct: number; label: string }) {
  const clamped = Math.max(0, Math.min(100, pct));
  return (
    <View>
      <Text style={text.label} accessibilityLiveRegion="polite">
        {label}
      </Text>
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

// 하단 고정 바 — 흰 배경 · 위 1px divider · 패딩 16 20 · 위 Label(남은 필수 개수 등, aria-live).
export function BottomBar({ hint, children }: { hint: string | null; children: ReactNode }) {
  const insets = useSafeAreaInsets();
  return (
    <View style={[f.bottomBar, { paddingBottom: space.md + insets.bottom }]}>
      {hint ? (
        <Text style={[text.label, text.mid, f.bottomHint]} accessibilityLiveRegion="polite">
          {hint}
        </Text>
      ) : null}
      {children}
    </View>
  );
}

const f = StyleSheet.create({
  fieldLabel: { marginBottom: space.sm },
  error: { color: colors.infoTeal, marginTop: space.sm },
  helper: { marginTop: space.sm },
  input: {
    height: F.input,
    borderRadius: R.button,
    borderWidth: 1,
    borderColor: colors.inputBorder,
    backgroundColor: colors.bg,
    paddingHorizontal: space.md,
  },
  inputFocus: { borderColor: colors.brand },
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
  checkRow: { minHeight: F.checkRow, flexDirection: 'row', alignItems: 'center' },
  checkMain: {
    flex: 1,
    minHeight: F.checkRow,
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.row,
    paddingVertical: space.sm,
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
  tagRequired: { color: colors.brand },
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
  fileCard: { flexDirection: 'row', alignItems: 'center', gap: space.md },
  previewWrap: { alignItems: 'center' },
  preview: {
    height: F.previewMaxH,
    aspectRatio: 9 / 16,
    borderRadius: R.card,
    overflow: 'hidden',
    backgroundColor: colors.softBg,
  },
  track: {
    height: F.track,
    borderRadius: F.track / 2,
    backgroundColor: colors.trackBg,
    overflow: 'hidden',
  },
  fill: { height: F.track, backgroundColor: colors.brand },
  bottomBar: {
    backgroundColor: colors.bg,
    borderTopWidth: 1,
    borderTopColor: colors.divider,
    paddingTop: space.md,
    paddingHorizontal: space.screen,
  },
  bottomHint: { marginBottom: space.sm, textAlign: 'center' },
});

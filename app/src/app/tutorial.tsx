import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import {
  type NativeScrollEvent,
  type NativeSyntheticEvent,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';
import { markTutorialSeen } from '../lib/onboarding';
import { colors, layout, radius, spacing, typography } from '../theme';

// 첫 실행 튜토리얼 — 기대설정 온보딩 (D-03/D-04, 26-UI-SPEC S1, 시나리오 0단계).
// why: 수강생이 학원에서 혼자 앱을 켰을 때 "무엇을 측정하고 무엇은 못 하는지"를
// 첫 화면에서 캘리브레이션 — 사전 불신("AI는 일반 답변만") 해소가 목적.
// 비주얼 = Figma(fileKey jrdI7kp245HkPfLB0nclsz) 승인 디자인이 최종 계약이며,
// belle 육안 확인은 26-06 checkpoint 에서 수행한다. 아래 카피/구조는 26-UI-SPEC S1
// 구조 계약을 따르는 기대설정 중심 초안 — Figma 확정 카피가 있으면 그것이 우선.
// 페이저: RN 코어 ScrollView horizontal pagingEnabled (신규 라이브러리 도입 금지 —
// 26-UI-SPEC Registry Safety). 배경 = colors.bg 라이트 전용 (다크 배경 금지).

type Slide = {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  body: string;
};

// 기대설정 중심 3슬라이드 (26-UI-SPEC §Copywriting, "~해요" 체, 이모지 금지).
// (1) 무엇을 측정하는지 (2) 무엇은 못 하는지 (3) 정확한 분석을 위한 촬영 안내.
const SLIDES: readonly Slide[] = [
  {
    icon: 'body-outline',
    title: '자세를 숫자로 정확히 봐드려요',
    body: '관절 각도를 재고 기준 모션과 비교해서, 어디가 얼마나 다른지 투명한 감점 내역으로 보여드려요. 막연한 칭찬이 아니라 근거가 있는 분석이에요.',
  },
  {
    icon: 'school-outline',
    title: '강사님을 대신하진 않아요',
    body: 'AI는 자세를 객관적으로 재주는 보조 도구예요. 측정 밖의 표현이나 흐름 같은 부분은 강사님과 함께 확인하면 더 좋아요.',
  },
  {
    icon: 'videocam-outline',
    title: '정확한 분석엔 원본 영상이 필요해요',
    body: '몸 전체가 화면에 잘 들어오는 거리에서 앱으로 직접 촬영하거나 원본 화질 영상을 올려주세요. 카톡으로 받은 영상은 압축돼 분석에 실패할 수 있어요.',
  },
] as const;

export default function Tutorial() {
  const router = useRouter();
  const { width } = useWindowDimensions();
  const [page, setPage] = useState(0);

  const onMomentumScrollEnd = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    // 활성 페이지 = 스크롤 오프셋 / 화면 너비 (반올림). dot 인디케이터·CTA 노출용.
    setPage(Math.round(e.nativeEvent.contentOffset.x / width));
  };

  // 종료 단일 수렴점 — 건너뛰기/시작하기 모두 이 경로. markTutorialSeen() 으로
  // 재노출을 막고, 첫 실행(replace 진입)은 홈으로, FAQ 재진입(push)은 뒤로 복귀.
  const finish = () => {
    markTutorialSeen();
    if (router.canGoBack()) {
      router.back();
    } else {
      router.replace('/(tabs)');
    }
  };

  const isLast = page === SLIDES.length - 1;

  return (
    <View style={styles.container}>
      <View style={styles.topBar}>
        <Pressable
          onPress={finish}
          accessibilityRole="button"
          accessibilityLabel="튜토리얼 건너뛰기"
          hitSlop={10}
          style={({ pressed }) => [styles.skipBtn, pressed && styles.pressed]}
        >
          <Text style={styles.skipText}>건너뛰기</Text>
        </Pressable>
      </View>

      <ScrollView
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onMomentumScrollEnd={onMomentumScrollEnd}
        style={styles.pager}
      >
        {SLIDES.map((slide) => (
          <View key={slide.title} style={[styles.slide, { width }]}>
            <View style={styles.visual}>
              <Ionicons name={slide.icon} size={72} color={colors.brand} />
            </View>
            <Text style={styles.title}>{slide.title}</Text>
            <Text style={styles.body}>{slide.body}</Text>
          </View>
        ))}
      </ScrollView>

      <View style={styles.dots}>
        {SLIDES.map((slide, i) => (
          <View
            key={slide.title}
            style={[styles.dot, i === page ? styles.dotActive : styles.dotInactive]}
          />
        ))}
      </View>

      <View style={styles.bottom}>
        {isLast ? (
          <Pressable
            onPress={finish}
            accessibilityRole="button"
            accessibilityLabel="시작하기"
            style={({ pressed }) => [styles.cta, pressed && styles.ctaDimmed]}
          >
            <Text style={styles.ctaText}>시작하기</Text>
          </Pressable>
        ) : (
          // CTA 자리 예약 — 마지막 슬라이드 전환 시 레이아웃 점프 방지.
          <View style={styles.ctaPlaceholder} />
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg, // 서브 화면 = 흰 배경 (design.md §5-1, 다크 배경 금지)
    paddingTop: layout.safeAreaTop,
    paddingBottom: layout.safeAreaBottom + 24,
  },
  topBar: {
    alignItems: 'flex-end',
    paddingHorizontal: spacing.screenX,
  },
  skipBtn: {
    minWidth: 40,
    height: 40,
    alignItems: 'flex-end',
    justifyContent: 'center',
  },
  skipText: { ...typography.buttonSecondary, color: colors.textSecondary },
  pager: { flex: 1 },
  slide: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.screenX,
  },
  visual: {
    width: 140,
    height: 140,
    borderRadius: 999,
    backgroundColor: colors.brandTint,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 28,
  },
  title: {
    ...typography.sectionTitle,
    color: colors.textPrimary,
    textAlign: 'center',
  },
  body: {
    ...typography.caption,
    color: colors.textMid,
    textAlign: 'center',
    lineHeight: 19, // caption 다줄 본문은 lineHeight 명시 (26-UI-SPEC Typography)
    marginTop: 12,
  },
  dots: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 8,
    marginTop: 24,
  },
  dot: { width: 8, height: 8, borderRadius: 999 },
  dotActive: { backgroundColor: colors.brand }, // 활성 dot = brand (26-UI-SPEC §Color)
  dotInactive: { backgroundColor: colors.divider },
  bottom: {
    paddingHorizontal: spacing.screenX,
    marginTop: 24,
  },
  cta: {
    height: layout.ctaHeight, // 54
    borderRadius: radius.button, // 13
    backgroundColor: colors.brand, // 흰 배경 위 = brand filled (index.tsx cta 선례)
    alignItems: 'center',
    justifyContent: 'center',
  },
  ctaDimmed: { opacity: 0.4 }, // design.md §9 버튼 피드백
  ctaText: { ...typography.button, color: colors.textWhite },
  ctaPlaceholder: { height: layout.ctaHeight },
  pressed: { opacity: 0.5 },
});

import { useRouter } from 'expo-router';
import { useState } from 'react';
import {
  Image,
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
import { saveBodyProfile } from '../lib/bodyProfile';
import { EXPERIENCE_LABEL_KO, type ExperienceLevel } from '../types/analysis';
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
  // 정적 asset require() — expo-updates OTA 는 require 된 asset 을 번들과 함께
  // 배포하므로 OTA 호환 (26-06, belle 승인 생성 이미지).
  image?: number;
  imageAlt?: string;
  /** true = 그림 대신 경력 선택 버튼을 렌더한다(3장). */
  question?: boolean;
  title: string;
  body: string;
};

// 기대설정 중심 3슬라이드 (26-UI-SPEC §Copywriting, "~해요" 체, 이모지 금지).
// 3장 구성 (belle 2026-08-31 승인, NotebookLM 심층 리서치 근거):
//   (1) 가치  (2) 체형 조정  (3) 경력 질문
//
// 근거 — 리서치(Material Design / NN/g / Google PAIR·Microsoft HAX / Kaia·18Birdies):
//   · 캐러셀은 **최대 3장**, 제목 5~7단어·본문 12단어 미만. 첫 실행 마케팅 카피는
//     대부분 읽히지 않으므로 제목만 읽어도 뜻이 통해야 한다.
//   · 각 장은 "설명"이 아니라 **개인화하거나 기능을 열어야** 한다 → 3장을 경력 질문으로.
//   · 촬영 안내는 온보딩이 아니라 **촬영 시점**에 둔다(NN/g: 시작 시 안내는 건너뛰고
//     정작 그 단계에서 기억나지 않는다). 우리 앱은 이미 analyze 에서 압축본을 잡는다.
//   · 2장(체형)은 belle 현장 근거 — 수강생이 실제로 품는 의심이 "나는 저 선수랑 몸이
//     다른데 비교가 되나"였다. 앱은 이미 영상에서 몸통 대비 팔·다리 비율을 재서
//     맞추고 있는데(body_normalizer) 아무도 모른다 → 말해준다.
//
// "강사님을 대신하진 않아요"는 3장 제한 안에서 체형·경력에 자리를 내줬다 —
// 같은 취지 문구가 결과 화면에 이미 있다(중복 제거).
const SLIDES: readonly Slide[] = [
  {
    image: require('../../assets/tutorial/slide-1.jpg'),
    imageAlt: '폴 위에서 우아하게 확장한 폴스포츠 포즈',
    title: '프로와도, 지난 나와도 비교해요',
    body: '관절 각도로 어디가 얼마나 다른지 보여드려요.',
  },
  {
    image: require('../../assets/tutorial/slide-3.jpg'),
    imageAlt: '폴 상단에서 당당하게 취한 성취의 포즈',
    title: '몸이 달라도 괜찮아요',
    body: '체형 차이를 맞춰서 비교해드려요.',
  },
  {
    // 3장 = 질문. 그림 자리를 선택 버튼이 대신한다(Figma 이미지 카드 리듬 유지).
    question: true,
    title: '폴을 얼마나 하셨어요?',
    body: '경력에 맞춰 무리한 동작을 미리 알려드려요.',
  },
] as const;

// 선택 버튼 순서 + 문답체 카피. 값 자체는 ExperienceLevel(단일 출처), 화면 문구만
// 온보딩 말투로 바꾼다 — 마이 탭 폼은 EXPERIENCE_LABEL_KO(초급/중급/고급)를 그대로 쓴다.
const EXPERIENCE_ORDER: readonly ExperienceLevel[] = [
  'beginner',
  'intermediate',
  'advanced',
];
const EXPERIENCE_COPY: Record<ExperienceLevel, string> = {
  beginner: '이제 시작했어요',
  intermediate: '조금 해봤어요',
  advanced: '자신 있어요',
};

export default function Tutorial() {
  const router = useRouter();
  const { width } = useWindowDimensions();
  const [page, setPage] = useState(0);
  // 3장 경력 선택 — 고른 값은 즉시 저장한다(별도 확인 버튼 없음). 저장 실패는
  // 온보딩을 막지 않는다: 경력은 안전 경고를 켜는 값이지 진입 조건이 아니다.
  const [experience, setExperience] = useState<ExperienceLevel | null>(null);

  const chooseExperience = (value: ExperienceLevel) => {
    setExperience(value);
    void saveBodyProfile({ experience: value }).catch(() => {
      // 게스트 uid 미생성 등으로 실패해도 화면은 그대로 진행 (마이 탭에서 재입력 가능).
    });
  };

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
            {/* 질문 장은 제목이 선택지보다 **위**에 온다 — 묻고 나서 고르는 순서.
                이미지 장은 Figma 리듬대로 그림이 위(그림은 읽는 대상이 아니다). */}
            {slide.question ? <Text style={styles.title}>{slide.title}</Text> : null}
            {slide.question ? (
              // 그림 자리에 선택 버튼 3개 (Figma 이미지 카드와 같은 높이 리듬).
              <View style={[styles.visual, styles.choiceBox]}>
                {EXPERIENCE_ORDER.map((value) => {
                  const selected = experience === value;
                  return (
                    <Pressable
                      key={value}
                      onPress={() => chooseExperience(value)}
                      accessibilityRole="button"
                      accessibilityState={{ selected }}
                      accessibilityLabel={`경력 ${EXPERIENCE_LABEL_KO[value]}`}
                      style={({ pressed }) => [
                        styles.choice,
                        selected && styles.choiceSelected,
                        pressed && styles.pressed,
                      ]}
                    >
                      <Text
                        style={[
                          styles.choiceText,
                          selected && styles.choiceTextSelected,
                        ]}
                      >
                        {EXPERIENCE_COPY[value]}
                      </Text>
                    </Pressable>
                  );
                })}
              </View>
            ) : (
              <View style={styles.visual}>
                <Image
                  source={slide.image}
                  resizeMode="cover"
                  accessible
                  accessibilityLabel={slide.imageAlt}
                  style={styles.visualImage}
                />
              </View>
            )}
            {slide.question ? null : (
              <Text style={styles.title}>{slide.title}</Text>
            )}
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
  // 이미지 카드 (26-06) — 생성 이미지(808x1080, 3:4 세로)를 라운드 카드에 cover 로
  // 채움. radius.card 토큰 유지, 로딩 전 자리색 = brandTint (기존 플레이스홀더 톤).
  // maxWidth 로 소형 기기에서 title/body/CTA 가 밀리지 않게 상한.
  visual: {
    width: '72%',
    maxWidth: 280,
    aspectRatio: 3 / 4,
    borderRadius: radius.card,
    backgroundColor: colors.brandTint,
    overflow: 'hidden',
    marginBottom: 24,
  },
  visualImage: { width: '100%', height: '100%' },
  // 3장 질문 — 그림 카드와 같은 크기 안에 선택 버튼 3개를 균등 배치해 페이지 간
  // 레이아웃 점프를 막는다(1·2장 이미지 카드와 동일 박스).
  choiceBox: {
    backgroundColor: 'transparent',
    marginTop: 12,
    justifyContent: 'center',
    gap: 10, // 카드 내부 간격 — 토큰에 sm 단위가 없어 카드 규격(16)의 절반대
  },
  choice: {
    borderWidth: 1,
    borderColor: colors.divider,
    borderRadius: radius.card,
    backgroundColor: colors.cardBg,
    paddingVertical: spacing.cardPadding,
    alignItems: 'center',
  },
  choiceSelected: {
    borderColor: colors.brand,
    backgroundColor: colors.brandTint,
  },
  choiceText: { ...typography.body, color: colors.textPrimary },
  choiceTextSelected: { color: colors.brand, fontWeight: '700' },
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

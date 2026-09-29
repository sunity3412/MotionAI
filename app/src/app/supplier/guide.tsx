// 공급자 촬영·등록 상세 가이드 — `/supplier/guide` (Phase 38 A-6, D-18, REQ-38-8).
//
// 문구 = supplierCopy.guide 만(화면 리터럴 0). 그 객체는 docs/supplier-guide.md 와 글자 단위로
// 같고 supplierCopy.test.ts 가 md 를 읽어 대조한다 — 여기서 문장을 만들거나 고치지 않는다.
// 로그인 불요(링크 공유 가능 — 가이드는 공개 정보). Firestore · API 호출 0.
//
// 구조 = UI-SPEC A-6: Top bar 뒤로 → Display 제목 → Label 부제 → 32 → 섹션 7 흰 카드(사이 24,
// 제목 Title 18/700 + 줄 Label 17 각 `· `) · ① 끝 예시 사진 2장(정은지 기준 프레임만, 나쁜 예
// 사진 없음 — Decisions 19) + 캡션 · ④ 안 실패 4형 = TIP 카드(1:482/483 문법).
// `?section=s5`(또는 웹 `#s5`)로 들어오면 그 섹션으로 스크롤한다(동의 화면 학습 사용 chevron).

import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { Image, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Card, PageFrame, space, text, TipCard, TopBar } from '../../components/SupplierUi';
import { supplierCopy } from '../../constants/supplierCopy';
import { colors, radius } from '../../theme';

const SECTIONS = [
  { id: 's1', copy: supplierCopy.guide.s1 },
  { id: 's2', copy: supplierCopy.guide.s2 },
  { id: 's3', copy: supplierCopy.guide.s3 },
  { id: 's4', copy: supplierCopy.guide.s4 },
  { id: 's5', copy: supplierCopy.guide.s5 },
  { id: 's6', copy: supplierCopy.guide.s6 },
  { id: 's7', copy: supplierCopy.guide.s7 },
] as const;

type SectionId = (typeof SECTIONS)[number]['id'];

// 예시 = 정은지 기준 프레임 2장(D-18 ①). 자산이 512×512 정사각이라 9:16 로 자르면 발끝이
// 잘린다 — 거리 예시가 목적이라 원본 비율(1:1) 그대로 둔다(38-11 SUMMARY 편차).
const EXAMPLES = [
  require('../../../assets/motion-thumbs/ref-kip-up.jpg'),
  require('../../../assets/motion-thumbs/ref-power-spin.jpg'),
];

function isSectionId(v: string): v is SectionId {
  return SECTIONS.some((s) => s.id === v);
}

function paramOf(v: unknown): string {
  if (typeof v === 'string') return v;
  if (Array.isArray(v) && typeof v[0] === 'string') return v[0];
  return '';
}

// 스크롤 대상 — `section` param 우선, 없으면 웹 location.hash(`#s5`).
function targetSection(params: Record<string, unknown>): SectionId | null {
  const fromParam = paramOf(params.section);
  if (isSectionId(fromParam)) return fromParam;
  if (Platform.OS === 'web' && typeof window !== 'undefined') {
    const hash = window.location.hash.replace('#', '');
    if (isSectionId(hash)) return hash;
  }
  return null;
}

export default function SupplierGuide() {
  const router = useRouter();
  const params = useLocalSearchParams();
  const target = targetSection(params);
  const scrollRef = useRef<ScrollView>(null);
  // 섹션 y 는 섹션 목록 View 기준이라 목록의 y 를 더해야 스크롤 좌표가 된다.
  const [listY, setListY] = useState<number | null>(null);
  const [targetY, setTargetY] = useState<number | null>(null);

  useEffect(() => {
    if (listY == null || targetY == null) return;
    scrollRef.current?.scrollTo({ y: Math.max(0, listY + targetY - space.md), animated: false });
  }, [listY, targetY]);

  const goBack = () => {
    if (router.canGoBack()) router.back();
    else router.replace('/supplier');
  };

  return (
    <SafeAreaView style={styles.page} edges={['top', 'bottom']}>
      <PageFrame>
        <ScrollView ref={scrollRef} contentContainerStyle={styles.pad}>
          <TopBar onBack={goBack} backLabel={supplierCopy.common.back} />
          <Text style={[text.display, styles.mt8]} accessibilityRole="header">
            {supplierCopy.guide.title}
          </Text>
          <Text style={[text.label, text.mid, styles.mt8]}>{supplierCopy.guide.sub}</Text>

          <View style={styles.sections} onLayout={(e) => setListY(e.nativeEvent.layout.y)}>
            {SECTIONS.map(({ id, copy }) => (
              <View
                key={id}
                nativeID={id}
                onLayout={id === target ? (e) => setTargetY(e.nativeEvent.layout.y) : undefined}
              >
                <Card>
                  <Text style={text.title} accessibilityRole="header">
                    {copy.h}
                  </Text>
                  <View style={styles.lines}>
                    {copy.items.map((line) => (
                      <Text key={line} style={text.label}>
                        {`· ${line}`}
                      </Text>
                    ))}
                  </View>
                  {id === 's1' ? (
                    <View style={styles.mt16}>
                      <View style={styles.examples}>
                        {EXAMPLES.map((src, i) => (
                          <Image
                            key={i}
                            source={src}
                            style={styles.example}
                            resizeMode="cover"
                            accessibilityIgnoresInvertColors
                          />
                        ))}
                      </View>
                      <Text style={[text.label, text.mid, styles.mt8]}>{supplierCopy.guide.s1.caption}</Text>
                    </View>
                  ) : null}
                  {id === 's4' ? (
                    <View style={styles.mt16}>
                      <TipCard head={supplierCopy.guide.s4.tipHead} lines={supplierCopy.guide.s4.tip} />
                    </View>
                  ) : null}
                </Card>
              </View>
            ))}
          </View>
        </ScrollView>
      </PageFrame>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  pad: { flexGrow: 1, paddingHorizontal: space.screen, paddingBottom: space.lg },
  mt8: { marginTop: space.sm },
  mt16: { marginTop: space.md },
  sections: { marginTop: space.xl, gap: space.lg },
  lines: { marginTop: space.sm, gap: space.xs },
  examples: { flexDirection: 'row', gap: space.row },
  example: {
    flex: 1,
    aspectRatio: 1,
    borderRadius: radius.card,
    backgroundColor: colors.softBg,
  },
});

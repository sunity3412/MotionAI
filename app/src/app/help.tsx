import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { colors, layout, radius, spacing, typography } from '../theme';

// 이용 방법 / FAQ 화면 (F2/D-05, 26-UI-SPEC §S2).
// 파일럿 피드백 F2 — 기존 샘플 결과 미리보기 화면을 상시 기대설정
// 레이어로 교체한다. 온보딩(튜토리얼) 1회 노출 이후의 재접근 지점이자, D-03 의
// 튜토리얼 재진입점을 겸한다. Figma 에 이용방법/FAQ 프레임이 없어(Figma Contract =
// 튜토리얼 + 다이얼로그만 확정) samples 골격을 재사용한다 (UI-SPEC S2).
// 카피 톤 = "~해요" 체, 강사 보조 도구 포지셔닝 상시 (FEED-03 / SCENARIO 불변 원칙).

type FaqItem = {
  id: string;
  title: string;
  body: string;
};

// 기대설정 최소 6항목 (UI-SPEC §Copywriting S2). 수치는 보조, 원인·행동이 핵심.
const FAQ_ITEMS: readonly FaqItem[] = [
  {
    id: 'what-measured',
    title: '무엇을 측정하나요?',
    body: '관절 각도와 기준 모션을 비교해 자세를 분석해요. 점수는 투명한 감점 내역으로 보여드리고, 수치보다 "왜 그런지"와 "무엇을 바꾸면 되는지"를 함께 알려드려요.',
  },
  {
    id: 'coach-replace',
    title: 'AI 점수가 강사님 평가를 대체하나요?',
    body: '아니요. 이 분석은 강사 지도를 돕는 참고 도구예요. 측정으로 드러나지 않는 부분은 강사님과 함께 확인해 주세요.',
  },
  {
    id: 'why-original',
    title: '왜 원본 영상을 올려야 하나요?',
    body: '카톡 등으로 전달받은 영상은 압축돼 화질이 낮아져 분석에 실패할 확률이 높아요. 원본 영상을 올리거나 앱에서 직접 촬영하면 더 정확하게 분석할 수 있어요.',
  },
  {
    id: 'how-to-film',
    title: '어떻게 촬영하면 좋나요?',
    body: '몸 전체가 화면에 잘 들어오는 거리(약 2~3m)에서 정면을 기준으로 촬영해 주세요. 너무 가깝거나 멀면 분석에 실패할 수 있어요.',
  },
  {
    id: 'on-failure',
    title: '분석이 실패하면 어떻게 하나요?',
    body: '촬영 구도와 거리, 화질을 확인한 뒤 다시 촬영해 주세요. 계속 문제가 생기면 문의하기로 알려주시면 도와드릴게요.',
  },
  {
    id: 'video-storage',
    title: '영상은 어떻게 보관되나요?',
    body: '올려주신 영상은 분석에만 사용하고 안전하게 보관해요. 언제든 삭제를 요청하실 수 있어요.',
  },
];

export default function Help() {
  const router = useRouter();
  // 한 번에 하나만 펼침 — 목록 스캔이 쉽도록. null = 전부 접힘.
  const [expandedId, setExpandedId] = useState<string | null>(null);

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
        {FAQ_ITEMS.map((item) => (
          <FaqCard
            key={item.id}
            item={item}
            expanded={expandedId === item.id}
            onToggle={() =>
              setExpandedId((cur) => (cur === item.id ? null : item.id))
            }
          />
        ))}

        <Pressable
          onPress={() => router.push('/tutorial')}
          accessibilityRole="button"
          accessibilityLabel="튜토리얼 다시 보기"
          hitSlop={6}
          style={styles.tutorialLinkRow}
        >
          <Text style={styles.tutorialLink}>튜토리얼 다시 보기</Text>
        </Pressable>
      </ScrollView>
    </View>
  );
}

function FaqCard({
  item,
  expanded,
  onToggle,
}: {
  item: FaqItem;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <View style={styles.card}>
      <Pressable
        onPress={onToggle}
        accessibilityRole="button"
        accessibilityLabel={item.title}
        accessibilityState={{ expanded }}
        hitSlop={6}
        style={styles.cardHeader}
      >
        <Text style={styles.cardTitle}>{item.title}</Text>
        <Ionicons
          name={expanded ? 'chevron-up' : 'chevron-down'}
          size={20}
          color={colors.textSecondary}
        />
      </Pressable>
      {expanded && <Text style={styles.cardBody}>{item.body}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
    paddingTop: layout.safeAreaTop,
    paddingHorizontal: spacing.screenX,
    paddingBottom: layout.safeAreaBottom + 24,
  },
  backBtn: {
    width: 40,
    height: 40,
    marginLeft: -8,
    marginTop: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  backBtnPressed: { opacity: 0.5 },
  heading: { ...typography.heading, color: colors.textPrimary, marginTop: 4 },
  sub: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 8,
    lineHeight: 18,
  },
  list: { flex: 1, marginTop: 20 },
  listContent: { gap: 10, paddingBottom: 24 },
  card: {
    backgroundColor: colors.cardBg,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    borderRadius: radius.card,
    padding: spacing.cardPadding,
    gap: 8,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  cardTitle: { ...typography.listTitle, color: colors.textPrimary, flexShrink: 1 },
  cardBody: {
    ...typography.caption,
    color: colors.textMid,
    lineHeight: 18,
  },
  tutorialLinkRow: {
    alignSelf: 'flex-start',
    marginTop: 12,
    paddingVertical: 4,
  },
  tutorialLink: {
    ...typography.caption,
    color: colors.brand,
    textDecorationLine: 'underline',
  },
});

// 영상 선택 실패 알림창 (quick-260720-hn8).
//
// belle 실기기: 앨범에서 영상을 고르는 순간 실패했는데, 화면에 뜬 인라인 회색 캡션은
// 사실상 보이지 않았고 원인도 해결책도 알려주지 못했다. 이 시트의 목적은 "에러를
// 예쁘게 보여주기"가 아니라 **사용자가 다음에 뭘 하면 되는지 알게 하는 것**이다.
//
// Figma: 에러 전용 알림창 디자인은 없어 `modal-sheet`(node 87:506) 패턴을 따른다 —
// grab handle + 둥근 바텀시트 / 큰 볼드 제목 + 우측 X / 회색 설명문 / 브랜드색 점
// 불릿 목록 / 회색 정보카드 / 하단 풀폭 브랜드 버튼.
//
// 골격(Modal + 백드롭 Pressable + sheet)은 BodyProfilePromptModal 을 그대로 재사용한다
// — 검증된 바텀시트 패턴이라 새 시각 언어를 발명하지 않는다.
// 토큰만 사용 (하드코딩 색/spacing/fontSize 금지 — app/CLAUDE.md / design.md §5-3).

import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, layout, radius, spacing, typography } from '../theme';
import type { PickFailure, PickFailureAction } from '../lib/pickerFailure';

interface Props {
  failure: PickFailure | null; // null = 미표시
  onClose: () => void; // X / 백드롭 / native back 3-way 수렴
  onAction: (action: PickFailureAction) => void;
}

// 긴 해결단계 + 오류 원문이 겹치면 소형 기기에서 시트가 화면을 넘긴다. 본문만
// 스크롤시키고 하단 액션 버튼은 스크롤 밖에 고정해 항상 닿게 한다.
const BODY_MAX_HEIGHT_RATIO = 0.46;

export function PickErrorSheet({ failure, onClose, onAction }: Props) {
  const { height } = useWindowDimensions();
  return (
    <Modal
      visible={failure != null}
      transparent
      animationType="slide"
      // native back = dismiss 3-way 중 하나 → onClose 로 수렴.
      onRequestClose={onClose}
    >
      <View style={styles.backdrop}>
        <Pressable
          style={styles.backdropTop}
          onPress={onClose}
          accessibilityRole="button"
          accessibilityLabel="닫기"
        />
        {failure != null && (
          <View style={styles.sheet} accessibilityViewIsModal>
            <View style={styles.handle} />

            <View style={styles.titleRow}>
              <Text style={styles.title}>{failure.title}</Text>
              <Pressable
                onPress={onClose}
                accessibilityRole="button"
                accessibilityLabel="닫기"
                hitSlop={10}
                style={({ pressed }) => pressed && styles.pressed}
              >
                <Ionicons
                  name="close"
                  size={24}
                  color={colors.textSecondary}
                />
              </Pressable>
            </View>

            <ScrollView
              style={[styles.body, { maxHeight: height * BODY_MAX_HEIGHT_RATIO }]}
              contentContainerStyle={styles.bodyContent}
              showsVerticalScrollIndicator={false}
            >
              <Text style={styles.cause}>{failure.cause}</Text>

              <Text style={styles.stepsHeading}>이렇게 해보세요</Text>
              <View style={styles.steps}>
                {failure.steps.map((step) => (
                  <View key={step} style={styles.stepRow}>
                    <View style={styles.bullet} />
                    <Text style={styles.stepText}>{step}</Text>
                  </View>
                ))}
              </View>

              {/* iCloud 오프로드는 아직 가설이라(정황 증거뿐) 실패가 재현될 때 원인을
                  확정·기각할 증거가 화면에 남아야 한다. 사용자에게는 눈에 띄지 않는
                  회색 정보 영역이지만, selectable 로 길게 눌러 복사·캡처할 수 있다. */}
              {failure.detail != null && (
                <View style={styles.detailCard}>
                  <Text style={styles.detailHeading}>오류 정보</Text>
                  <Text style={styles.detailText} selectable>
                    {failure.detail}
                  </Text>
                </View>
              )}
            </ScrollView>

            <Pressable
              onPress={() => onAction(failure.action)}
              accessibilityRole="button"
              accessibilityLabel={failure.action.label}
              hitSlop={6}
              style={({ pressed }) => [styles.primary, pressed && styles.pressed]}
            >
              <Text style={styles.primaryText}>{failure.action.label}</Text>
            </Pressable>
          </View>
        )}
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: colors.brandOverlay,
    justifyContent: 'flex-end',
  },
  backdropTop: { flex: 1 },
  sheet: {
    backgroundColor: colors.cardBg,
    borderTopLeftRadius: radius.modal,
    borderTopRightRadius: radius.modal,
    paddingTop: spacing.cardPadding,
    paddingBottom: spacing.cardPadding * 2,
    paddingHorizontal: spacing.screenX,
    gap: 12,
  },
  handle: {
    width: 40,
    height: 4,
    backgroundColor: colors.divider,
    borderRadius: radius.button,
    alignSelf: 'center',
    marginBottom: 6,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  title: { ...typography.heading, color: colors.textPrimary, flex: 1 },
  body: { alignSelf: 'stretch' },
  bodyContent: { gap: 14, paddingBottom: 4 },
  cause: {
    ...typography.caption,
    color: colors.textMid,
    lineHeight: 19,
  },
  stepsHeading: { ...typography.listTitle, color: colors.textPrimary },
  steps: { gap: 10 },
  stepRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
  },
  // 브랜드색 점 불릿 (Figma modal-sheet). 번호 매기지 않는다.
  bullet: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.brand,
    marginTop: 6,
  },
  stepText: {
    ...typography.caption,
    color: colors.textHi,
    lineHeight: 19,
    flex: 1,
  },
  // 회색 정보카드 — picker 원본 오류 문자열 보관용 (진단 증거).
  detailCard: {
    backgroundColor: colors.softBg,
    borderRadius: radius.listItem,
    padding: spacing.cardPadding,
    gap: 6,
  },
  detailHeading: { ...typography.caption, color: colors.textLo },
  detailText: {
    ...typography.caption,
    color: colors.textMid,
    lineHeight: 18,
  },
  primary: {
    height: layout.ctaHeight,
    borderRadius: radius.button,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 4,
  },
  primaryText: { ...typography.button, color: colors.textWhite },
  pressed: { opacity: 0.85 },
});

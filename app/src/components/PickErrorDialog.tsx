// 영상 선택 실패 알림창 (quick-260720-hn8).
//
// belle 실기기: 앨범에서 영상을 고르는 순간 실패했는데, 화면에 뜬 인라인 회색 캡션은
// 사실상 보이지 않았고 원인도 해결책도 알려주지 못했다. 이 알림창의 목적은 "에러를
// 예쁘게 보여주기"가 아니라 **사용자가 다음에 뭘 하면 되는지 알게 하는 것**이다.
//
// 디자인 — Figma node 1:499 `Group 53` 실측 (belle 지목). 중앙 정렬 **카드형**이며
// 바텀시트가 아니다: 연핑크 카드(반경 30) + 상단 중앙 원형 느낌표 + 제목 + 2줄 본문 +
// 가로 2버튼([닫기] 좁게 / 주액션 넓게).
//
// 아이콘은 Figma 이미지 애셋이지만 원격 URL 은 7일 만료라 앱에 넣을 수 없어
// react-native-svg(이미 설치됨)로 직접 그린다 — 신규 의존성 0.
//
// 토큰만 사용 (하드코딩 색/spacing/fontSize 금지 — app/CLAUDE.md / design.md §5-3).

import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';
import { colors, layout, radius, spacing, typography } from '../theme';
import type { PickFailure, PickFailureAction } from '../lib/pickerFailure';

interface Props {
  failure: PickFailure | null; // null = 미표시
  onClose: () => void; // [닫기] / 백드롭 / native back 3-way 수렴
  onAction: (action: PickFailureAction) => void;
}

// 빨간 원 + 흰 느낌표 (Figma 30.33 × 30.33). viewBox 24 기준으로 그리고 크기는
// 토큰(layout.dialogIconSize)이 정한다.
function AlertIcon() {
  const size = layout.dialogIconSize;
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Circle cx={12} cy={12} r={12} fill={colors.brand} />
      {/* 느낌표 막대 + 점 — 흰색 */}
      <Path
        d="M12 5.5c.72 0 1.28.62 1.21 1.34l-.5 5.2a.72.72 0 0 1-1.42 0l-.5-5.2A1.21 1.21 0 0 1 12 5.5z"
        fill={colors.textWhite}
      />
      <Circle cx={12} cy={16.6} r={1.35} fill={colors.textWhite} />
    </Svg>
  );
}

export function PickErrorDialog({ failure, onClose, onAction }: Props) {
  return (
    <Modal
      visible={failure != null}
      transparent
      animationType="fade"
      // native back = dismiss 3-way 중 하나 → onClose 로 수렴.
      onRequestClose={onClose}
    >
      {/* 백드롭 탭 = dismiss. 카드 자체는 순수 View 라 탭이 통과하지 않는다. */}
      <View style={styles.backdrop}>
        <Pressable
          style={styles.backdropFill}
          onPress={onClose}
          accessibilityRole="button"
          accessibilityLabel="닫기"
        />
        {failure != null && (
          <View style={styles.card} accessibilityViewIsModal>
            <View style={styles.icon}>
              <AlertIcon />
            </View>

            <Text style={styles.title}>{failure.title}</Text>

            <View style={styles.lines}>
              {failure.lines.map((line) => (
                <Text key={line} style={styles.body}>
                  {line}
                </Text>
              ))}
            </View>

            {/* [진단 목적] picker 원본 오류 문자열. iCloud 오프로드는 아직 가설이고
                (정황 증거뿐) 이 텍스트가 없으면 다음 실패 때도 원인을 알 수 없다.
                Figma 양식에는 없는 요소라 사용자 눈에 띄지 않게 최소 크기·회색으로
                두되, selectable 로 길게 눌러 복사·캡처할 수 있게 한다. */}
            {failure.detail != null && (
              <Text style={styles.detail} selectable>
                {failure.detail}
              </Text>
            )}

            <View style={styles.buttons}>
              <Pressable
                onPress={onClose}
                accessibilityRole="button"
                accessibilityLabel="닫기"
                hitSlop={6}
                style={({ pressed }) => [
                  styles.closeBtn,
                  pressed && styles.pressed,
                ]}
              >
                <Text style={styles.closeLabel}>닫기</Text>
              </Pressable>
              <Pressable
                onPress={() => onAction(failure.primaryAction)}
                accessibilityRole="button"
                accessibilityLabel={failure.primaryLabel}
                hitSlop={6}
                style={({ pressed }) => [
                  styles.primaryBtn,
                  pressed && styles.pressed,
                ]}
              >
                <Text style={styles.primaryLabel}>{failure.primaryLabel}</Text>
              </Pressable>
            </View>
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
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.screenX,
  },
  // 카드 뒤 전면을 덮는 dismiss 영역 (카드는 그 위에 절대배치가 아니라 형제로 렌더).
  backdropFill: { ...StyleSheet.absoluteFillObject },
  card: {
    width: '100%',
    maxWidth: layout.dialogMaxWidth, // Figma 308.8 → 반응형 최대 320
    backgroundColor: colors.dialogBg, // Figma 연핑크 카드 배경
    borderRadius: radius.dialog, // 30.33 → 30
    paddingHorizontal: spacing.cardPadding,
    paddingTop: spacing.cardPadding + 8,
    paddingBottom: spacing.cardPadding,
    alignItems: 'center',
  },
  icon: { marginBottom: 12 },
  title: {
    ...typography.dialogTitle,
    color: colors.textPrimary,
    textAlign: 'center',
  },
  lines: { marginTop: 6, alignSelf: 'stretch' },
  body: {
    ...typography.dialogBody,
    color: colors.textPrimary,
    textAlign: 'center',
  },
  detail: {
    ...typography.dialogDetail,
    color: colors.textLo,
    textAlign: 'center',
    marginTop: 10,
    alignSelf: 'stretch',
  },
  buttons: {
    flexDirection: 'row',
    gap: 8,
    alignSelf: 'stretch',
    marginTop: 18,
  },
  // Figma 폭 98.6 : 153.7 = 1 : 1.56 → flex 비율로 재현(소형 기기 대응).
  closeBtn: {
    flex: layout.dialogCloseFlex,
    height: layout.dialogButtonHeight,
    borderRadius: radius.dialogButton,
    backgroundColor: colors.cardBg,
    borderWidth: StyleSheet.hairlineWidth, // Figma 0.688px
    borderColor: colors.divider, // Figma 회색 테두리
    alignItems: 'center',
    justifyContent: 'center',
  },
  closeLabel: { ...typography.dialogButton, color: colors.dialogMutedText },
  primaryBtn: {
    flex: layout.dialogPrimaryFlex,
    height: layout.dialogButtonHeight,
    borderRadius: radius.dialogButton,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
  },
  primaryLabel: { ...typography.dialogButton, color: colors.textWhite },
  pressed: { opacity: 0.85 },
});

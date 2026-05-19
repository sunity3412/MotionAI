import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Linking, Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, layout, radius, spacing, typography } from '../../theme';

// 영상 소스 선택 (plan.md #4, design.md §6·§5-1·§5-4·§9).
// 분석 탭 진입 = 이 화면. 즉석 촬영 / 앨범에서 선택 → 검증 → (#5 AI 분석 로딩으로 연결 예정).
// 실제 S3 업로드는 백엔드(#6~7)에서 연결. 여기서는 영상 확보 + 형식/용량 검증까지.

const MAX_BYTES = 100 * 1024 * 1024; // design.md: 100MB 초과 불가
const ALLOWED = ['mp4', 'mov']; // design.md: mp4, mov만 지원

type Picked = { name: string };

export default function Analyze() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [permissionBlocked, setPermissionBlocked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [picked, setPicked] = useState<Picked | null>(null);

  const reset = () => {
    setError(null);
    setPermissionBlocked(false);
    setPicked(null);
  };

  const validate = (asset: ImagePicker.ImagePickerAsset): string | null => {
    const source = asset.fileName ?? asset.uri;
    const ext = source.split('.').pop()?.toLowerCase() ?? '';
    if (!ALLOWED.includes(ext)) return 'mp4, mov 형식의 영상만 분석할 수 있어요.';
    if (asset.fileSize != null && asset.fileSize > MAX_BYTES)
      return '100MB 이하 영상만 분석할 수 있어요.';
    return null;
  };

  const handleResult = (result: ImagePicker.ImagePickerResult) => {
    if (result.canceled || !result.assets?.[0]) return;
    const asset = result.assets[0];
    const problem = validate(asset);
    if (problem) {
      setError(problem);
      return;
    }
    setError(null);
    setPicked({ name: asset.fileName ?? '선택한 영상' });
  };

  const pickFromCamera = async () => {
    setBusy(true);
    try {
      const perm = await ImagePicker.requestCameraPermissionsAsync();
      if (!perm.granted) {
        setPermissionBlocked(true);
        setError('촬영하려면 카메라 권한이 필요해요.');
        return;
      }
      handleResult(
        await ImagePicker.launchCameraAsync({ mediaTypes: ['videos'] }),
      );
    } catch {
      setError('카메라를 여는 중 문제가 발생했어요. 다시 시도해주세요.');
    } finally {
      setBusy(false);
    }
  };

  const pickFromLibrary = async () => {
    setBusy(true);
    try {
      const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!perm.granted) {
        setPermissionBlocked(true);
        setError('앨범에서 가져오려면 사진 접근 권한이 필요해요.');
        return;
      }
      handleResult(
        await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['videos'] }),
      );
    } catch {
      setError('앨범을 여는 중 문제가 발생했어요. 다시 시도해주세요.');
    } finally {
      setBusy(false);
    }
  };

  if (picked) {
    return (
      <View style={styles.container}>
        <Text style={styles.heading}>영상을 가져왔어요</Text>
        <View style={styles.confirmCard}>
          <Ionicons name="checkmark-circle" size={28} color={colors.brand} />
          <Text style={styles.confirmName} numberOfLines={1}>
            {picked.name}
          </Text>
        </View>
        <View style={styles.spacer} />
        <Pressable
          style={({ pressed }) => [styles.cta, pressed && styles.ctaDimmed]}
          onPress={() =>
            router.push({
              pathname: '/analysis/loading',
              // mode3 = 자기 성장(기준 불필요). 모드/기준 선택은 #9에서.
              params: { mode: 'mode3', name: picked.name },
            })
          }
          accessibilityRole="button"
        >
          <Text style={styles.ctaText}>분석 시작하기</Text>
        </Pressable>
        <Pressable onPress={reset} accessibilityRole="button">
          <Text style={styles.link}>다른 영상 다시 선택</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.heading}>어떻게 영상을{'\n'}가져올까요?</Text>
      <Text style={styles.sub}>분석할 폴스포츠 연습 영상을 골라주세요.</Text>

      <View style={styles.cards}>
        <SourceCard
          icon="videocam-outline"
          title="즉석 촬영"
          subtitle="지금 바로 카메라로 촬영"
          onPress={pickFromCamera}
          disabled={busy}
        />
        <SourceCard
          icon="images-outline"
          title="앨범에서 선택"
          subtitle="저장된 영상에서 불러오기"
          onPress={pickFromLibrary}
          disabled={busy}
        />
      </View>

      {error && <Text style={styles.error}>{error}</Text>}
      {permissionBlocked && (
        <Pressable
          onPress={() => Linking.openSettings()}
          accessibilityRole="button"
        >
          <Text style={styles.link}>설정에서 권한 허용하기</Text>
        </Pressable>
      )}
    </View>
  );
}

function SourceCard({
  icon,
  title,
  subtitle,
  onPress,
  disabled,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  subtitle: string;
  onPress: () => void;
  disabled: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityState={{ disabled }}
      style={({ pressed }) => [
        styles.card,
        (pressed || disabled) && styles.cardDimmed,
      ]}
    >
      <Ionicons name={icon} size={32} color={colors.brand} />
      <View style={styles.cardText}>
        <Text style={styles.cardTitle}>{title}</Text>
        <Text style={styles.cardSub}>{subtitle}</Text>
      </View>
      <Ionicons name="chevron-forward" size={20} color={colors.textDisabled} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg, // 서브 화면 = 흰 배경 (§5-1)
    paddingTop: layout.safeAreaTop,
    paddingHorizontal: spacing.screenX,
    paddingBottom: layout.safeAreaBottom + 24,
  },
  heading: { ...typography.heading, color: colors.textPrimary, marginTop: 12 },
  sub: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 8,
  },
  cards: { marginTop: 28, gap: 12 },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    backgroundColor: colors.cardBg,
    borderWidth: layout.cardBorderWidth, // 0.858 (§5-4)
    borderColor: colors.divider,
    borderRadius: radius.card, // 15 (§5-4)
    padding: spacing.cardPadding,
  },
  cardDimmed: { opacity: 0.4 }, // §9 비활성/피드백
  cardText: { flex: 1 },
  cardTitle: { ...typography.listTitle, color: colors.textPrimary },
  cardSub: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 4,
  },
  error: {
    ...typography.caption,
    color: colors.inputError, // 오류 = 틸 (§4)
    marginTop: 20,
  },
  link: {
    ...typography.caption,
    color: colors.brand,
    textDecorationLine: 'underline',
    marginTop: 12,
  },
  confirmCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: colors.cardBg,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    borderRadius: radius.card,
    padding: spacing.cardPadding,
    marginTop: 24,
  },
  confirmName: { ...typography.boxLabel, color: colors.textPrimary, flex: 1 },
  spacer: { flex: 1 },
  cta: {
    height: layout.ctaHeight,
    borderRadius: radius.button,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ctaDimmed: { opacity: 0.4 }, // §9 누름 피드백
  ctaText: { ...typography.button, color: colors.textWhite },
});

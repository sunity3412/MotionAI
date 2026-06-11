import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { Linking, Pressable, StyleSheet, Text, View } from 'react-native';
import { useReferenceMotion } from '../../lib/referenceMotions';
import { useMyAnalyses } from '../../lib/userAnalyses';
import type { AnalysisMode } from '../../types/analysis';
import { colors, layout, radius, spacing, typography } from '../../theme';

// 분석 탭 진입점 — 비교 모드 먼저, 그 다음 영상 선택 (belle P1 #2).
//
// 단계:
//   1) 모드 선택 — "전문가와 비교"(mode1) / "내 자세 분석"(mode3).
//      mode3 부텍스트는 이전 분석 갯수로 분기:
//        · 0건: "첫 자세 점수를 받아보세요" (절대 평가 + 좌우 대칭 코칭)
//        · 1건+: "지난 분석과 얼마나 늘었는지도 확인"
//   2) 영상 선택 — 즉석 촬영 / 앨범. 모드별로 상단 안내 분기.
//   3) 영상 선택 후 자동 라우팅:
//        · mode1 + referenceMotionId(홈 챌린지 우회) → /analysis/loading
//        · mode1 + 미선택 → /analysis/reference (motion 선택 단계로)
//        · mode3                                    → /analysis/loading
//
// mode3 두 영상 동시 비교는 의도적으로 안 함 — 첫 분석은 절대 평가, 이후는
// 자동으로 가장 최근 mode3 와 delta 비교(백엔드 get_previous_analysis).

const MAX_BYTES = 100 * 1024 * 1024; // design.md: 100MB 초과 불가
const ALLOWED = ['mp4', 'mov']; // design.md: mp4, mov만 지원

type VideoFormat = 'mp4' | 'mov';
type Picked = {
  name: string;
  uri: string;
  size: number;
  format: VideoFormat;
};

export default function Analyze() {
  const router = useRouter();
  // 홈 챌린지 카드 우회 진입 — referenceMotionId 가 있으면 모드 선택 단계를
  // 건너뛰고 mode1 + 영상 선택 단계로 시작 (belle P1 #7).
  const { referenceMotionId } = useLocalSearchParams<{
    referenceMotionId?: string;
  }>();
  const { motion: preselectedMotion } = useReferenceMotion(referenceMotionId);
  // mode3 부텍스트 분기용 — 이전 분석 갯수만 필요.
  const { analyses } = useMyAnalyses({ doneOnly: true });
  const hasPreviousMode3 = analyses.some((a) => a.mode === 'mode3');

  const [mode, setMode] = useState<AnalysisMode | null>(
    referenceMotionId ? 'mode1' : null,
  );
  const [error, setError] = useState<string | null>(null);
  const [permissionBlocked, setPermissionBlocked] = useState(false);
  const [busy, setBusy] = useState(false);

  // belle UAT 2026-06-12 F1 — 홈 챌린지 카드에서 진입 시 모드 선택 화면이 떴음.
  // useState initial 만으로는 mount 후 referenceMotionId 가 늦게 들어오거나
  // 탭 재진입 시 못 잡음. param 변경 시 자동으로 mode1 설정.
  useEffect(() => {
    if (referenceMotionId && mode === null) {
      setMode('mode1');
    }
  }, [referenceMotionId, mode]);

  const backToModeSelect = () => {
    setMode(null);
    setError(null);
    setPermissionBlocked(false);
  };

  const validate = (asset: ImagePicker.ImagePickerAsset): string | null => {
    const source = asset.fileName ?? asset.uri;
    const ext = source.split('.').pop()?.toLowerCase() ?? '';
    if (!ALLOWED.includes(ext)) return 'mp4, mov 형식의 영상만 분석할 수 있어요.';
    if (asset.fileSize != null && asset.fileSize > MAX_BYTES)
      return '100MB 이하 영상만 분석할 수 있어요.';
    return null;
  };

  // 영상 확보 직후 다음 단계로 라우팅. 머무를 화면 없음(라우팅 끝나면 뒤로
  // 돌아왔을 때 모드 선택 단계가 자연스럽게 보임).
  const routeAfterPick = (picked: Picked) => {
    if (!mode) return; // 방어 — 이론상 도달 불가
    if (mode === 'mode1') {
      if (referenceMotionId) {
        router.push({
          pathname: '/analysis/loading',
          params: {
            mode: 'mode1',
            name: picked.name,
            uri: picked.uri,
            size: String(picked.size),
            format: picked.format,
            referenceMotionId,
            referenceMotionName: preselectedMotion?.name ?? '',
          },
        });
      } else {
        router.push({
          pathname: '/analysis/reference',
          params: {
            name: picked.name,
            uri: picked.uri,
            size: String(picked.size),
            format: picked.format,
          },
        });
      }
    } else {
      router.push({
        pathname: '/analysis/loading',
        params: {
          mode: 'mode3',
          name: picked.name,
          uri: picked.uri,
          size: String(picked.size),
          format: picked.format,
        },
      });
    }
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
    const source = asset.fileName ?? asset.uri;
    const ext = (source.split('.').pop()?.toLowerCase() ?? 'mp4') as VideoFormat;
    routeAfterPick({
      name: asset.fileName ?? '선택한 영상',
      uri: asset.uri,
      size: asset.fileSize ?? 0,
      format: ext,
    });
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

  // 단계 2: 영상 소스 선택
  if (mode) {
    const modeContext =
      mode === 'mode1'
        ? preselectedMotion
          ? `${preselectedMotion.name} · ${preselectedMotion.athleteName} 선수와 비교`
          : '정은지 선수 동작과 비교'
        : hasPreviousMode3
          ? '지난 분석과 비교해서 성장도 확인할게요'
          : '첫 분석이라 절대 평가로 자세를 봐드릴게요';
    return (
      <View style={styles.container}>
        <Pressable
          onPress={backToModeSelect}
          accessibilityRole="button"
          accessibilityLabel="비교 모드 다시 고르기"
          hitSlop={10}
          style={({ pressed }) => [styles.backBtn, pressed && styles.backBtnPressed]}
        >
          <Ionicons name="chevron-back" size={26} color={colors.textPrimary} />
        </Pressable>
        <Text style={styles.heading}>어떻게 영상을{'\n'}가져올까요?</Text>
        <Text style={styles.sub}>{modeContext}</Text>

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

  // 단계 1: 비교 모드 선택
  const mode3Subtitle = hasPreviousMode3
    ? '지난 분석과 얼마나 늘었는지도 확인'
    : '첫 자세 점수와 코칭을 받아보세요';
  return (
    <View style={styles.container}>
      <Text style={styles.heading}>{'어떻게\n분석할까요?'}</Text>
      <Text style={styles.sub}>비교 기준을 먼저 골라주세요.</Text>

      <View style={styles.cards}>
        <SourceCard
          icon="trophy-outline"
          title="전문가와 비교"
          subtitle="정은지 선수 동작과 얼마나 가까운지 점수로 확인"
          onPress={() => setMode('mode1')}
          disabled={false}
        />
        <SourceCard
          icon="trending-up-outline"
          title="내 자세 분석"
          subtitle={mode3Subtitle}
          onPress={() => setMode('mode3')}
          disabled={false}
        />
      </View>

      <View style={styles.spacer} />
      {/* 시연·검토용 진입점 — 실 분석 파이프라인(#7-follow) 켜지면 같이 제거. */}
      <Pressable
        onPress={() => router.push('/analysis/samples')}
        accessibilityRole="button"
        hitSlop={6}
      >
        <Text style={styles.sampleLink}>샘플 결과 미리보기</Text>
      </Pressable>
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
  backBtn: {
    width: 40,
    height: 40,
    marginLeft: -8,
    marginTop: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  backBtnPressed: { opacity: 0.5 },
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
  sampleLink: {
    ...typography.caption,
    color: colors.textSecondary,
    textAlign: 'center',
    textDecorationLine: 'underline',
  },
  spacer: { flex: 1 },
});

import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { Linking, Modal, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useReferenceMotion } from '../../lib/referenceMotions';
import { useMyAnalyses } from '../../lib/userAnalyses';
import { dismissBodyProfilePrompt, useBodyProfile } from '../../lib/bodyProfile';
import { BodyProfilePromptModal } from '../../components/BodyProfilePromptModal';
import BodyProfileForm from '../../components/BodyProfileForm';
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

// [#20 입력 화질] 저화질 입력은 미세 자세 차이를 못 잡아 점수가 조용히 틀어진다
// (belle: 카톡 전송 34MB→1.6MB 압축 → 분석 실패). 하드 블록은 하지 않되(더 나은
// 영상이 없을 수 있음), 픽 시점에 휴리스틱으로 감지해 사용자에게 솔직히 경고한다.
const MIN_QUALITY_SHORT_SIDE = 720; // 720p 미만(짧은 변 기준) = 저화질 신호
const MIN_QUALITY_BITRATE_BPS = 6 * 1000 * 1000; // ~6 Mbps 미만 = 과압축 신호

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
  // [#20 입력 화질] 저화질 감지 시 비차단 경고 — 계속/취소. picked 를 보류했다가
  // [계속]이면 정상 라우팅(maybePromptBeforeRoute), [취소]면 영상을 버린다.
  const [lowQualityPicked, setLowQualityPicked] = useState<Picked | null>(null);

  // [R2] 첫 분석 권유 게이트 상태머신. profile/promptDismissedAt 구독으로 게이트
  // 조건(미입력 AND 미dismiss)을 판별. pendingPicked 로 라우팅을 보류했다가
  // 모달 결과(입력완료/건너뛰기/백드롭/native back) 4-경로 모두 continuePendingRoute
  // 로 수렴해 동일 picked 영상으로 분석을 재개 (stale closure/영상 유실 방지).
  const { profile, promptDismissedAt, loading: profileLoading } = useBodyProfile();
  const [pendingPicked, setPendingPicked] = useState<Picked | null>(null);
  const [promptVisible, setPromptVisible] = useState(false);
  const [formVisible, setFormVisible] = useState(false); // [입력하기] → 폼 진입
  // [WR-04] 세션-로컬 재권유 차단. dismissBodyProfilePrompt 의 영속 write 가
  // 실패해도(오프라인 게스트·rules transient) promptDismissedAt 가 안 남아 매
  // 첫-pick 마다 모달이 다시 뜨는 것을 방지 — 한 번 권유를 처리한 세션 안에서는
  // 영속 결과와 무관하게 모달을 다시 띄우지 않는다 (재권유 0, D-06 graceful).
  const promptedThisSession = useRef(false);

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

  // [#20 입력 화질] 저화질 휴리스틱 — 짧은 변이 720p 미만이거나(해상도 부족),
  // 추정 비트레이트가 ~6Mbps 미만(과압축)이면 저화질로 본다. width/height/fileSize/
  // duration 은 시스템이 0/누락으로 줄 수 있으므로 값이 유효할 때만 판정한다(거짓 경고
  // 방지). 막지 않고 경고만 — boolean + 짧은 사유 반환.
  const checkLowQuality = (
    asset: ImagePicker.ImagePickerAsset,
  ): { low: boolean; reason: string } => {
    const shortSide = Math.min(asset.width || 0, asset.height || 0);
    if (shortSide > 0 && shortSide < MIN_QUALITY_SHORT_SIDE) {
      return { low: true, reason: `해상도 ${shortSide}p` };
    }
    const durationSec =
      asset.duration != null && asset.duration > 0 ? asset.duration / 1000 : 0;
    if (asset.fileSize != null && asset.fileSize > 0 && durationSec > 0) {
      const bitrate = (asset.fileSize * 8) / durationSec;
      if (bitrate < MIN_QUALITY_BITRATE_BPS) {
        return { low: true, reason: `비트레이트 약 ${Math.round(bitrate / 1e6 * 10) / 10}Mbps` };
      }
    }
    return { low: false, reason: '' };
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

  // [R2] 게이트: 프로필 미입력 AND 권유 미dismiss 이면 picked 를 보류하고 권유
  // 모달을 띄운다. 프로필이 이미 있거나(profile != null) 이미 dismiss 했으면
  // (promptDismissedAt != null) 즉시 routeAfterPick — 분석을 막지 않음 (게스트
  // 우선, SC#4 미입력 graceful). profile 은 normalizer 가 all-empty → null 로
  // 접으므로 null = 미입력 판정에 그대로 사용.
  // [CR-01] 구독이 아직 로딩 중이면 profile/promptDismissedAt 가 일시적으로 null
  // 이라 기존 프로필·이미 dismiss 한 사용자에게도 권유가 잘못 뜰 수 있다(콜드스타트/
  // 느린 네트워크 레이스). loading 중에는 권유를 보류하고 즉시 라우팅 — 게스트 우선
  // 원칙상 모달 미출현이 오출현보다 안전.
  const maybePromptBeforeRoute = (picked: Picked) => {
    if (profileLoading) {
      routeAfterPick(picked);
      return;
    }
    // [WR-04] 이 세션에서 이미 권유를 처리했으면(영속 dismiss 실패 포함) 재출현 X.
    if (promptedThisSession.current) {
      routeAfterPick(picked);
      return;
    }
    const notEntered = profile === null;
    const notDismissed = promptDismissedAt == null;
    if (notEntered && notDismissed) {
      setPendingPicked(picked);
      setPromptVisible(true);
      return;
    }
    routeAfterPick(picked);
  };

  // [R2] 단일 수렴점 — 4-경로(입력완료/건너뛰기/백드롭/native back) 모두 여기로.
  // 보류된 picked 를 캡처 후 state 초기화하고 동일 영상으로 라우팅 재개.
  const continuePendingRoute = () => {
    const p = pendingPicked;
    setPendingPicked(null);
    setPromptVisible(false);
    setFormVisible(false);
    if (p) routeAfterPick(p);
  };

  // [건너뛰기 / 백드롭 / native back] → once-flag 세팅 후 분석 계속 (재권유 0, D-06).
  const skipPrompt = async () => {
    // [WR-04] 영속 write 보다 먼저 세션 flag 를 세워 둔다 — dismiss 가 실패해도
    // 이 세션 안에서는 모달이 다시 뜨지 않도록 (재권유 0 보장의 in-memory 폴백).
    promptedThisSession.current = true;
    try {
      await dismissBodyProfilePrompt();
    } catch {
      // graceful — once-flag 저장 실패해도 분석은 막지 않음 (게스트 우선).
    }
    continuePendingRoute();
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
    const picked: Picked = {
      name: asset.fileName ?? '선택한 영상',
      uri: asset.uri,
      size: asset.fileSize ?? 0,
      format: ext,
    };
    // [#20 입력 화질] 저화질이면 조용히 진행하지 않고 비차단 경고를 띄운다.
    const quality = checkLowQuality(asset);
    if (quality.low) {
      setLowQualityPicked(picked);
      return;
    }
    maybePromptBeforeRoute(picked);
  };

  // [#20 입력 화질] 저화질 경고에서 [이대로 계속] — 보류한 picked 로 정상 라우팅.
  const continueLowQuality = () => {
    const p = lowQualityPicked;
    setLowQualityPicked(null);
    if (p) maybePromptBeforeRoute(p);
  };

  // [#20 입력 화질] 저화질 경고에서 [다른 영상 선택] — 보류한 영상을 버린다.
  const cancelLowQuality = () => {
    setLowQualityPicked(null);
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
      // [#20 입력 화질] 즉석 촬영은 최고 화질로 캡처 — 카톡 압축본을 받기 전에
      // 원본 디테일을 확보해야 미세 자세 차이를 분석할 수 있음 (iOS 전용 필드,
      // Android 에선 무시됨).
      handleResult(
        await ImagePicker.launchCameraAsync({
          mediaTypes: ['videos'],
          videoQuality: ImagePicker.UIImagePickerControllerQualityType.High,
        }),
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
      // [#20 입력 화질] 앨범에서 가져올 때 transcoding 으로 인한 추가 화질 손실을
      // 막음 — Current 는 가능하면 원본 표현을 그대로 사용해 재인코딩을 피한다
      // (기본 Automatic 은 호환 코덱으로 재변환할 수 있음, iOS 전용).
      handleResult(
        await ImagePicker.launchImageLibraryAsync({
          mediaTypes: ['videos'],
          preferredAssetRepresentationMode:
            ImagePicker.UIImagePickerPreferredAssetRepresentationMode.Current,
        }),
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

        {/* [#20 입력 화질] 가장 정확한 분석을 위한 안내 — 카톡 압축본은 정확도가
            낮아질 수 있음을 미리 고지. */}
        <Text style={styles.guidance}>
          가장 정확한 분석을 위해 앱에서 직접 촬영하거나 원본 화질 영상을 올려주세요.
          카톡 등으로 받은 영상은 압축돼 정확도가 낮을 수 있어요 (카톡은 '원본'으로 전송).
        </Text>

        {error && <Text style={styles.error}>{error}</Text>}
        {permissionBlocked && (
          <Pressable
            onPress={() => Linking.openSettings()}
            accessibilityRole="button"
          >
            <Text style={styles.link}>설정에서 권한 허용하기</Text>
          </Pressable>
        )}

        {/* [#20 입력 화질] 저화질 비차단 경고 — 계속/취소. native back(백드롭)은
            취소와 동일하게 영상 버림. */}
        <Modal
          visible={lowQualityPicked != null}
          transparent
          animationType="fade"
          onRequestClose={cancelLowQuality}
        >
          <View style={styles.lqBackdrop}>
            <View style={styles.lqCard}>
              <Text style={styles.lqTitle}>화질이 낮아요</Text>
              <Text style={styles.lqBody}>
                이 영상은 화질이 낮아 미세한 자세 차이 분석이 제한될 수 있어요. 더
                정확하려면 원본 화질 영상을 올리거나 앱에서 직접 촬영하세요. 이대로
                계속할까요?
              </Text>
              <Pressable
                onPress={continueLowQuality}
                accessibilityRole="button"
                accessibilityLabel="이대로 계속 분석하기"
                style={({ pressed }) => [
                  styles.lqPrimaryBtn,
                  pressed && styles.cardDimmed,
                ]}
              >
                <Text style={styles.lqPrimaryLabel}>이대로 계속</Text>
              </Pressable>
              <Pressable
                onPress={cancelLowQuality}
                accessibilityRole="button"
                accessibilityLabel="다른 영상 선택하기"
                hitSlop={6}
                style={({ pressed }) => pressed && styles.cardDimmed}
              >
                <Text style={styles.lqSecondaryLabel}>다른 영상 선택</Text>
              </Pressable>
            </View>
          </View>
        </Modal>

        {/* [R2] 첫 분석 권유 게이트. 건너뛰기/백드롭/native back → skipPrompt
            (once-flag + 분석 계속). 입력하기 → 폼 진입. */}
        <BodyProfilePromptModal
          visible={promptVisible}
          onInput={() => {
            setPromptVisible(false);
            setFormVisible(true);
          }}
          onSkip={skipPrompt}
        />

        {/* [입력하기] 진입 폼 — 저장 완료(onSaved) 또는 닫기(onClose) 모두 보류된
            picked 로 분석 재개 (continuePendingRoute 단일 수렴). */}
        <Modal
          visible={formVisible}
          animationType="slide"
          presentationStyle="pageSheet"
          onRequestClose={continuePendingRoute}
        >
          <SafeAreaView style={styles.formSafe} edges={['top']}>
            <BodyProfileForm
              initial={profile}
              onSaved={continuePendingRoute}
              onClose={continuePendingRoute}
            />
          </SafeAreaView>
        </Modal>
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
  // [#20 입력 화질] 소스 선택 안내 — 보조 캡션 톤, 비강압적.
  guidance: {
    ...typography.caption,
    color: colors.textMid,
    marginTop: 16,
    lineHeight: 18,
  },
  // [#20 입력 화질] 저화질 경고 모달.
  lqBackdrop: {
    flex: 1,
    backgroundColor: colors.brandOverlay,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.screenX,
  },
  lqCard: {
    width: '100%',
    backgroundColor: colors.cardBg,
    borderRadius: radius.modal,
    padding: 24,
    gap: 14,
  },
  lqTitle: { ...typography.sectionTitle, color: colors.textPrimary },
  lqBody: {
    ...typography.caption,
    color: colors.textMid,
    lineHeight: 19,
  },
  lqPrimaryBtn: {
    height: layout.ctaHeight,
    borderRadius: radius.button,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 4,
  },
  lqPrimaryLabel: { ...typography.button, color: colors.textWhite },
  lqSecondaryLabel: {
    ...typography.buttonSecondary,
    color: colors.textSecondary,
    textAlign: 'center',
    paddingVertical: 8,
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
  formSafe: { flex: 1, backgroundColor: colors.bg },
});

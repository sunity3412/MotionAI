// 참고코너 "참고하세요" 섹션 (Phase 31, 31-08).
//
// 근거:
//  · D-09 — 배치는 결과 화면 점수 내역 아래의 별도 "참고하세요" 섹션. 채점과
//    시각적으로 분리한다 (점수 비반영 원칙이 레이아웃으로 드러나야 함).
//    31-08 Task 1 belle 승인 = option-a: 교정 자세 카드도 이 섹션 소속
//    (결함 줌은 독립 캐러셀이 아니라 result.tsx 드릴다운 시트 안에서 소비되므로,
//     "캐러셀 옆" 배치는 성립하지 않고 채점 영역에 비채점 생성물을 섞게 된다).
//  · amended D-10 — 비교 뷰어는 카메라 평면 고정 2D 중첩 (PoseCompareViewer).
//  · amended D-04 — 시점을 바꿔 보려는 니즈는 Wan2.7 합성 회전 영상이 전담한다.
//    이 카드/버튼에서만 "회전" 표현을 쓴다 (산출물이 실제로 회전 영상이므로 정직).
//    PoseCompareViewer 쪽은 그 문구를 쓰지 않는다 — 거기선 하지 않는 일이라서.
//  · D-08 — 실패는 사용자에게 에러로 노출하지 않는다. 'hidden' = 카드 미렌더.
//    Alert/Toast/에러 배너 0 (조용한 폴백).
//  · 단일 카메라 invariant ([[single-camera-first-multi-view-last]]) — 다각도
//    촬영을 유도하는 문구를 쓰지 않는다.
//  · 점수 비반영 invariant ([[camera-angle-scoring-stretch-reference-corner]]) —
//    이 섹션은 점수 수치를 일절 표시하지 않는다.
//
// 상태 구동 컴포넌트. 재서명/네트워크는 caller(31-11) 소유 — 이 컴포넌트는
// onCorrectedPoseImageError 콜백만 노출하고 POST /playback-url 을 직접 부르지
// 않는다 (리뷰 H-02 앱 측 계약).
//
// ScoreBreakdownSection 표준형: named export + inline prop 타입 + 헤더 주석 +
// StyleSheet 하단 + theme 토큰만. 하드코딩 색상/간격/반경 0. 이모지 0. 라이트 전용.

import { useVideoPlayer, VideoView } from 'expo-video';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';

import { PoseCompareFrames, type PoseFrameSlot } from './PoseCompareFrames';
import { PoseCompareViewer } from './PoseCompareViewer';
import { colors, layout, radius, spacing, typography } from '../theme';

/** 교정 자세 이미지 / 회전 영상 카드의 표시 상태. 'hidden' = 렌더 생략. */
export type ReferenceCardState = 'hidden' | 'pending' | 'loading' | 'ready';
/** 회전 영상은 온디맨드라 '아직 요청 전(requestable)' 상태가 하나 더 있다. */
export type RotationCardState = 'hidden' | 'pending' | 'ready' | 'requestable';

export function ReferenceCornerSection({
  correctedPoseState,
  correctedPoseImageUrl,
  correctedPoseJointLabel,
  onCorrectedPoseImageError,
  rotationState,
  rotationVideoUrl,
  onRequestRotation,
  rotationRequestBusy,
  limitNotice,
  userPose,
  refPose,
  jointKeys,
  poseFrames,
}: {
  correctedPoseState: ReferenceCardState;
  /** 재서명된 fresh URL (caller 가 playback-url asset 으로 발급). */
  correctedPoseImageUrl?: string;
  /** 교정 대상 관절 한글 라벨 (예: '왼쪽 무릎'). 없으면 캡션 생략. */
  correctedPoseJointLabel?: string;
  /** 만료/403 등 로드 실패 → caller 가 재서명 후 새 URL 을 내려준다. */
  onCorrectedPoseImageError?: () => void;
  rotationState: RotationCardState;
  rotationVideoUrl?: string;
  onRequestRotation?: () => void;
  rotationRequestBusy?: boolean;
  /** 생성 한도 등 인라인 고지 1줄. 배너/토스트 아님. */
  limitNotice?: string;
  /** DTW 대응 결함 프레임의 단일 프레임 (17,3). 없으면 뷰어 숨김. */
  userPose: number[][] | null;
  refPose: number[][] | null;
  jointKeys: string[];
  /**
   * 2026-07-21 belle 결정 ("사람이 나와야지") — 비교 순간의 실제 영상 프레임 쌍.
   * 양쪽 url 이 있으면 스켈레톤 대신 실프레임(PoseCompareFrames)을 그린다.
   * 없거나 한쪽 url 이 비면 기존 스켈레톤 뷰어 폴백 (조용한 폴백, D-08).
   */
  poseFrames?: {
    user: PoseFrameSlot;
    reference: PoseFrameSlot;
    videoSize: { width: number; height: number };
  } | null;
}) {
  // expo-video: source 가 null 이면 자원만 잡고 재생 가능 상태가 아니다.
  // 훅은 조건부 호출이 불가하므로 항상 호출하고 URL 유무로 제어한다
  // (VideoCompare 선례).
  const rotationPlayer = useVideoPlayer(
    rotationState === 'ready' && rotationVideoUrl ? rotationVideoUrl : null,
    (p) => {
      p.loop = true;
    },
  );

  const showCorrected = correctedPoseState !== 'hidden';
  // 뷰어는 양쪽 자세가 다 있을 때만. mode3(대응 기준 없음) / refMatched=false
  // 는 caller 가 refPose=null 로 내려 여기서 자연히 숨겨진다 — 학생 단독
  // 스켈레톤을 "비교"라고 부르며 보여주는 것보다 숨기는 편이 정직하다.
  const showViewer =
    userPose != null && refPose != null && jointKeys.length > 0;
  // 실프레임은 양쪽 영상 URL 이 있을 때만 — 한쪽만 사람이 나오는 "비교"는 성립하지
  // 않으므로(정직한 강등) 그 경우 스켈레톤 뷰어로 폴백한다.
  const framesReady =
    poseFrames != null && !!poseFrames.user.url && !!poseFrames.reference.url;
  const showRotation = rotationState !== 'hidden';

  // 셋 다 숨김이면 섹션 헤더만 남아 빈 껍데기가 된다 → 섹션 자체를 렌더하지 않음.
  if (!showCorrected && !showViewer && !showRotation) return null;

  return (
    <View style={styles.wrapper}>
      <Text style={styles.sectionTitle}>참고하세요</Text>
      {/* quick-260809-jnb — belle 08-09 "지금은 뭘 말하는지 모르겠음".
          원인 = 위 '동작 비교'가 이미 멈추고 자막으로 설명하는데, 여기서 또
          "어디가 다른지 견줘보는 용도"라고 하니 같은 말을 두 번 하는 셈이었다.
          → 이 섹션만 줄 수 있는 것(멈춰 있는 그림·고친 모습)을 앞세운다.
          "점수 무관"(D-09)은 유지하되 부정문으로 문을 열지 않도록 아래로. */}
      <Text style={styles.sectionSub}>영상은 지나가지만, 여기 그림은 멈춰 있어요</Text>
      <Text style={styles.sectionGuide}>점수에는 들어가지 않아요</Text>

      {showCorrected && (
        <View style={styles.card}>
          {/* quick-260809-jnb — "교정된 자세"는 결과 서술이라 무엇을 하라는지가
              없다. belle 08-09 요구 = "아 이걸 고치면 되겠군" 이 오는 글. */}
          <Text style={styles.cardTitle}>이렇게 바꾸면 돼요</Text>
          {correctedPoseState === 'ready' && correctedPoseImageUrl ? (
            <>
              <Image
                source={{ uri: correctedPoseImageUrl }}
                style={styles.correctedImage}
                resizeMode="contain"
                // 만료 URL 복구 경로 (리뷰 H-02). 사용자에겐 에러 문구를 띄우지
                // 않고 caller 가 조용히 재서명한다.
                onError={onCorrectedPoseImageError}
                accessibilityRole="image"
                // 조사(을/를)는 받침 유무로 갈려 관절 이름마다 달라진다.
                // 라벨 목록이 늘어날 때마다 틀린 조사가 새는 것보다, 조사가
                // 없는 형태로 두는 편이 안전하다.
                accessibilityLabel={
                  correctedPoseJointLabel
                    ? `${correctedPoseJointLabel} 교정된 자세 이미지`
                    : '교정된 자세 이미지'
                }
              />
              {correctedPoseJointLabel != null && (
                <Text style={styles.caption}>
                  {`고친 곳 · ${correctedPoseJointLabel}`}
                </Text>
              )}
            </>
          ) : (
            <View style={styles.placeholder}>
              <Text style={styles.placeholderText}>
                {correctedPoseState === 'pending'
                  ? '만들고 있어요. 잠시만 기다려주세요'
                  : '불러오고 있어요'}
              </Text>
            </View>
          )}
        </View>
      )}

      {showViewer && (
        <View style={styles.card}>
          {/* quick-260809-jnb — "자세 비교"는 위 '동작 비교' 섹션과 이름이 겹쳐
              무엇이 다른지 안 보였다. 이 카드의 정체 = 영상이 멈췄던 그 순간. */}
          <Text style={styles.cardTitle}>같은 순간, 나란히</Text>
          {framesReady && poseFrames ? (
            <>
              {/* 33-15 (D-16) — 이 카드 문구에 "점수" 표현 금지. 섹션이
                  "점수에는 들어가지 않아요"라고 해놓고 카드가 "점수에 반영된
                  비교 순간"이라 부르던 모순을 없앤 규칙 (지금도 유효).
                  사실 자체는 유지 = 분석이 비교한 그 순간의 실프레임. */}
              <Text style={styles.caption}>
                위 영상이 멈춘 그 순간이에요
              </Text>
              <PoseCompareFrames
                user={poseFrames.user}
                reference={poseFrames.reference}
                videoSize={poseFrames.videoSize}
              />
            </>
          ) : (
            <>
              <Text style={styles.caption}>
                내 자세 위에 목표 자세를 겹쳐놨어요
              </Text>
              <PoseCompareViewer
                userPose={userPose}
                refPose={refPose}
                jointKeys={jointKeys}
              />
              <View style={styles.legendRow}>
                <View style={styles.legendItem}>
                  <View
                    style={[styles.legendSwatch, styles.legendSwatchUser]}
                  />
                  <Text style={styles.legendText}>내 자세</Text>
                </View>
                <View style={styles.legendItem}>
                  <View
                    style={[styles.legendSwatch, styles.legendSwatchTarget]}
                  />
                  <Text style={styles.legendText}>목표 자세</Text>
                </View>
              </View>
            </>
          )}
        </View>
      )}

      {showRotation && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>회전 참고 영상</Text>
          {rotationState === 'ready' && rotationVideoUrl ? (
            <VideoView
              player={rotationPlayer}
              style={styles.rotationVideo}
              nativeControls
              contentFit="contain"
              accessibilityLabel="회전 참고 영상"
            />
          ) : rotationState === 'pending' ? (
            <View style={styles.placeholder}>
              {/* 진행률/남은시간 수치를 쓰지 않는다 — 파일럿에서 85% 진행률
                  표시가 사용자 오인을 만든 이력([[pilot-feedback-2026-07-06]]).
                  거짓 정밀도 없이 대략의 기대만 전한다. */}
              <Text style={styles.placeholderText}>
                만들고 있어요. 몇 분 걸려요
              </Text>
            </View>
          ) : (
            <>
              <Text style={styles.caption}>
                내 동작을 여러 방향에서 본 참고 영상을 만들어 드려요
              </Text>
              <Pressable
                onPress={onRequestRotation}
                disabled={rotationRequestBusy === true}
                accessibilityRole="button"
                accessibilityLabel="회전 영상 만들기"
                accessibilityState={{ disabled: rotationRequestBusy === true }}
                hitSlop={8}
                style={[
                  styles.requestButton,
                  rotationRequestBusy === true && styles.requestButtonDisabled,
                ]}
              >
                <Text style={styles.requestButtonText}>회전 영상 만들기</Text>
              </Pressable>
            </>
          )}
          {limitNotice != null && limitNotice !== '' && (
            <Text style={styles.limitNotice}>{limitNotice}</Text>
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: { gap: 12 },
  sectionTitle: { ...typography.sectionTitle, color: colors.textPrimary },
  // 점수 비반영 고지 — 섹션 최상단 서브카피 (D-09).
  sectionSub: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
    marginTop: -8,
  },
  // 33-15 (D-16) — 무엇을 왜 보는지 안내 1줄. 서브카피와 한 묶음 (동일 톤).
  sectionGuide: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
    marginTop: -8,
  },
  // 기존 result 카드 패턴 mirror (ScoreBreakdownSection.card 상당) — 토큰만.
  card: {
    backgroundColor: colors.cardBg,
    borderRadius: radius.card,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    padding: spacing.cardPadding,
    gap: 12,
  },
  cardTitle: { ...typography.boxLabel, color: colors.textPrimary },
  caption: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  correctedImage: {
    width: '100%',
    aspectRatio: 1,
    borderRadius: radius.listItem,
    backgroundColor: colors.softBg,
  },
  rotationVideo: {
    width: '100%',
    aspectRatio: 1,
    borderRadius: radius.listItem,
    backgroundColor: colors.softBg,
  },
  placeholder: {
    width: '100%',
    aspectRatio: 1,
    borderRadius: radius.listItem,
    backgroundColor: colors.softBg,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.cardPadding,
  },
  placeholderText: {
    ...typography.caption,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 18,
  },
  legendRow: { flexDirection: 'row', gap: 16 },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  legendSwatch: { width: 14, height: 3, borderRadius: 2 },
  legendSwatchUser: { backgroundColor: colors.brand },
  legendSwatchTarget: { backgroundColor: colors.neutralDark, opacity: 0.4 },
  legendText: { ...typography.caption, color: colors.textSecondary },
  requestButton: {
    height: layout.inputHeight,
    borderRadius: radius.button,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
  },
  requestButtonDisabled: { backgroundColor: colors.brandButtonDisabled },
  requestButtonText: {
    ...typography.buttonSecondary,
    fontWeight: '700',
    color: colors.textWhite,
  },
  // 한도 고지는 배너/토스트가 아니라 버튼 인근 인라인 1줄 (D-08 정합).
  limitNotice: {
    ...typography.captionSmall,
    color: colors.textSecondary,
    lineHeight: 16,
  },
});

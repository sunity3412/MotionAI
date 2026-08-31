import Constants from 'expo-constants';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { signInAnonymously, signOut } from 'firebase/auth';
import { useMemo, useState } from 'react';
import {
  Alert,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { authCopy } from '../../constants/authCopy';
import { auth } from '../../lib/firebase';
import { displayNameOf, useAuthUser } from '../../lib/authUser';
import { useMyAnalyses } from '../../lib/userAnalyses';
import { useBodyProfile } from '../../lib/bodyProfile';
import BodyProfileForm from '../../components/BodyProfileForm';
import type { AnalysisDoc, BodyProfile } from '../../types/analysis';
import {
  DOMINANT_HAND_LABEL_KO,
  EXPERIENCE_LABEL_KO,
  PAIN_AREA_LABEL_KO,
} from '../../types/analysis';
import { colors, layout, radius, spacing, typography } from '../../theme';

// 마이 탭 — 파일럿 단순 정보. (IA AC-MY-* 의 프로필 편집·구독·알림 등은 MVP 밖.)
// 게스트 모드(익명 인증) 상태와 분석 통계, 폴스포츠 고정 표시.
//
// ★계정 영역 (36-06, belle 2026-08-31 지시): 로그인 입구가 **인트로에만** 있었는데
// 게스트 세션은 영속이라 한 번 들어오면 인트로를 다시 볼 일이 없다 — 앱 안에서
// 로그인 화면에 갈 길이 아예 없었다(애플·구글 로그인을 눌러볼 수조차 없었다).
// 그래서 계정 카드가 게스트일 때 로그인 입구가 된다.
//
// 게스트 진입 자체는 **무접촉**이다 (belle 08-31 "실증할 땐 게스트로 들어갈 테니").
// 인트로 "시작하기" = 익명 인증 그대로. 이 화면은 로그인을 권할 뿐 강요하지 않는다
// (CLAUDE.md §2 파일럿 요건 = 회원가입 강제 없음).

function averageScore(analyses: AnalysisDoc[]): number | null {
  const scores = analyses
    .map((a) => a.result?.overallScore)
    .filter((s): s is number => typeof s === 'number');
  if (scores.length === 0) return null;
  return Math.round(scores.reduce((sum, s) => sum + s, 0) / scores.length);
}

function shortenUid(uid: string): string {
  return uid.length <= 8 ? uid : `${uid.slice(0, 4)}…${uid.slice(-4)}`;
}

// 채워진 필드만 "·" 로 묶어 요약 (부분 입력 graceful, D-06). 전부 비면 null.
// 라벨은 analysis.ts 단일 출처(WR-03) — *_LABEL_KO 사용.
// painAreaNote(F3): 앱-로컬 '기타' 자유입력 — 계약 필드가 전부 비어도(profile=null)
// 메모만 있으면 요약에 노출. 통증부위 라벨 뒤에 "기타: <메모>" 로 붙인다.
function summarizeBodyProfile(
  profile: BodyProfile | null,
  painAreaNote?: string | null,
): string | null {
  const parts: string[] = [];
  if (profile) {
    if (profile.heightCm != null) parts.push(`${profile.heightCm}cm`);
    if (profile.experience) parts.push(EXPERIENCE_LABEL_KO[profile.experience]);
    if (profile.dominantHand) parts.push(DOMINANT_HAND_LABEL_KO[profile.dominantHand]);
    if (profile.painAreas.length > 0) {
      parts.push(profile.painAreas.map((a) => PAIN_AREA_LABEL_KO[a]).join('·'));
    }
  }
  if (painAreaNote) parts.push(`기타: ${painAreaNote}`);
  return parts.length > 0 ? parts.join(' · ') : null;
}

export default function Profile() {
  const router = useRouter();
  const { analyses } = useMyAnalyses({ doneOnly: true });
  const { profile, painAreaNote } = useBodyProfile();
  const { user, isGuest, ready } = useAuthUser();
  const uid = user?.uid ?? null;
  const avg = useMemo(() => averageScore(analyses), [analyses]);
  const appVersion = Constants.expoConfig?.version ?? '1.0.0';

  const [editing, setEditing] = useState(false);
  const [signOutError, setSignOutError] = useState<string | null>(null);
  const summary = useMemo(
    () => summarizeBodyProfile(profile, painAreaNote),
    [profile, painAreaNote],
  );

  // 로그아웃 = **게스트로 되돌리기**. signOut 만 하면 인증이 아예 없는 상태로 남는데,
  // 이 앱의 모든 탭은 uid 를 전제하므로 그 상태는 아무것도 못 하는 막다른 길이다.
  //
  // ★처음엔 signOut 후 인트로(`/`)로 보내 "시작하기"를 다시 누르게 하려 했는데,
  //   시뮬레이터에서 **홈 탭으로 떨어졌다**. 라우트 그룹은 경로에 세그먼트를 더하지
  //   않아 `src/app/index.tsx`(인트로)와 `src/app/(tabs)/index.tsx`(홈)가 **둘 다 `/`**
  //   라서 그렇다 — 인트로를 경로로 지목할 방법이 없다. 그래서 화면을 옮기는 대신
  //   여기서 새 익명 세션을 만든다. 사용자는 제자리에서 게스트로 돌아온다.
  //
  // 확인 한 번을 두는 이유: 되돌리기 어려워서가 아니라(기록은 계정에 남는다), 탭
  // 화면의 한 번 누름으로 세션이 바뀌면 실수로 눌렀을 때 알아채기 어려워서다.
  const confirmSignOut = () => {
    setSignOutError(null);
    Alert.alert(authCopy.account.signOutTitle, authCopy.account.signOutBody, [
      { text: authCopy.account.signOutCancel, style: 'cancel' },
      {
        text: authCopy.account.signOut,
        style: 'destructive',
        onPress: () => {
          signOut(auth)
            .then(() => signInAnonymously(auth))
            .catch(() => setSignOutError(authCopy.account.signOutFailed));
        },
      },
    ]);
  };

  const memberName = displayNameOf(user) ?? authCopy.account.memberFallbackName;

  return (
    <View style={styles.container}>
      <Text style={styles.headerTitle}>마이</Text>
      {/* 로그인하면 더 이상 게스트가 아니다 — 헤더가 계속 "게스트 모드"라고 하면
          로그인이 안 된 것처럼 읽힌다(로그인 성공을 확인할 수 있는 유일한 표시). */}
      <Text style={styles.headerSub}>
        {isGuest ? '파일럿 게스트 모드' : '파일럿'}
      </Text>

      <ScrollView
        contentContainerStyle={styles.body}
        showsVerticalScrollIndicator={false}
      >
        {/* 계정 카드 — 게스트면 로그인 입구, 로그인 상태면 계정 표시.
            ready 전에는 그리지 않는다: 세션 복원 중 잠깐 currentUser 가 null 이라
            게스트에게 "로그인" 이 한 번 깜빡인다 (authUser.ts ready 주석). */}
        {!ready ? null : isGuest ? (
          <>
            <Pressable
              onPress={() => router.push('/auth/login')}
              accessibilityRole="button"
              accessibilityLabel={`${authCopy.account.loginAction} — ${authCopy.account.guestHint}`}
              style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
            >
              <View style={styles.avatar}>
                <Ionicons name="person-outline" size={26} color={colors.brand} />
              </View>
              <View style={styles.profileText}>
                <Text style={styles.profileName}>{authCopy.account.guestName}</Text>
                <Text style={styles.profileMeta}>
                  {uid ? `ID ${shortenUid(uid)}` : '익명 세션 준비 중'}
                </Text>
              </View>
              <Text style={styles.cardAction}>{authCopy.account.loginAction}</Text>
              <Ionicons name="chevron-forward" size={20} color={colors.brand} />
            </Pressable>
            <Text style={styles.guestHint}>{authCopy.account.guestHint}</Text>
          </>
        ) : (
          <View style={styles.card}>
            <View style={styles.avatar}>
              <Ionicons name="person-outline" size={26} color={colors.brand} />
            </View>
            <View style={styles.profileText}>
              <Text style={styles.profileName}>{memberName}</Text>
              <Text style={styles.profileMeta}>
                {user?.email ?? (uid ? `ID ${shortenUid(uid)}` : '')}
              </Text>
            </View>
          </View>
        )}

        {/* 내 몸 정보 — 미입력=권유 / 입력됨=요약+수정 (D-01/D-02/D-06) */}
        <Pressable
          onPress={() => setEditing(true)}
          accessibilityRole="button"
          accessibilityLabel={
            summary ? `내 몸 정보 수정, 현재 ${summary}` : '내 몸 정보 입력하기'
          }
          style={({ pressed }) => [
            summary ? styles.bodyCard : styles.bodyPrompt,
            pressed && styles.bodyCardPressed,
          ]}
        >
          <View style={styles.bodyCardText}>
            <Text style={styles.bodyCardTitle}>내 몸 정보</Text>
            <Text
              style={summary ? styles.bodyCardSummary : styles.bodyPromptText}
              numberOfLines={1}
            >
              {summary ?? '키·경력·통증부위를 입력하면 코칭이 더 정확해져요'}
            </Text>
          </View>
          <Ionicons name="chevron-forward" size={20} color={colors.brand} />
        </Pressable>

        {/* 통계 */}
        <View style={styles.stats}>
          <StatBox label="분석 횟수" value={`${analyses.length}`} suffix="회" />
          <StatBox
            label="평균 점수"
            value={avg != null ? `${avg}` : '–'}
            suffix={avg != null ? '점' : ''}
          />
        </View>

        {/* 정보 리스트 */}
        <View style={styles.infoList}>
          {[
            { label: '주 종목', value: '폴스포츠' },
            { label: '레벨', value: '입문 (기본값)' },
            { label: '앱 버전', value: appVersion },
          ].map((row, i, arr) => (
            <InfoRow
              key={row.label}
              label={row.label}
              value={row.value}
              isLast={i === arr.length - 1}
            />
          ))}
        </View>

        {/* MVP 범위 안내 */}
        <View style={styles.notice}>
          <Ionicons name="information-circle-outline" size={18} color={colors.textSecondary} />
          {/* quick-260831-lcc — 스테일 카피 수리: 로그인은 Phase 36 에서 구현
              완료라 "정식 출시 단계" 안내와 모순. 결제·알림만 남긴다. */}
          <Text style={styles.noticeText}>
            결제·알림 설정은 정식 출시 단계에서 열려요.
          </Text>
        </View>

        {/* 로그아웃 — 로그인 상태에서만. 게스트에게는 내놓지 않는다: 익명 계정은
            자격증명이 없어 한 번 나가면 그 uid 로 **다시 들어올 방법이 없고**,
            기록에 닿을 길이 사라진다. 게스트에게 필요한 건 나가기가 아니라 로그인이다. */}
        {ready && !isGuest ? (
          <Pressable
            onPress={confirmSignOut}
            accessibilityRole="button"
            accessibilityLabel={authCopy.account.signOut}
            hitSlop={8}
            style={({ pressed }) => [styles.signOut, pressed && styles.cardPressed]}
          >
            <Text style={styles.signOutText}>{authCopy.account.signOut}</Text>
          </Pressable>
        ) : null}
        {signOutError ? (
          <Text style={styles.signOutError}>{signOutError}</Text>
        ) : null}
      </ScrollView>

      {/* 내 몸 정보 편집 — 전체화면 폼 (기존값 prefill, 저장 후 onSnapshot 자동 갱신) */}
      <Modal
        visible={editing}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setEditing(false)}
      >
        <SafeAreaView style={styles.modalSafe} edges={['top']}>
          <BodyProfileForm
            initial={profile}
            initialPainAreaNote={painAreaNote}
            onClose={() => setEditing(false)}
            onSaved={() => setEditing(false)}
          />
        </SafeAreaView>
      </Modal>
    </View>
  );
}

function StatBox({
  label,
  value,
  suffix,
}: {
  label: string;
  value: string;
  suffix: string;
}) {
  return (
    <View style={styles.statBox}>
      <Text style={styles.statLabel}>{label}</Text>
      <View style={styles.statValueRow}>
        <Text style={styles.statValue}>{value}</Text>
        {suffix ? <Text style={styles.statSuffix}>{suffix}</Text> : null}
      </View>
    </View>
  );
}

function InfoRow({
  label,
  value,
  isLast,
}: {
  label: string;
  value: string;
  isLast?: boolean;
}) {
  return (
    <View style={[styles.infoRow, isLast && styles.infoRowLast]}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
    paddingTop: layout.safeAreaTop,
    paddingHorizontal: spacing.screenX,
    paddingBottom: layout.safeAreaBottom,
  },
  headerTitle: { ...typography.heading, color: colors.textPrimary, marginTop: 8 },
  headerSub: { ...typography.caption, color: colors.textSecondary, marginTop: 6 },
  body: { paddingVertical: 18, paddingBottom: 24, gap: 14 },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    backgroundColor: colors.cardBg,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    borderRadius: radius.card,
    padding: spacing.cardPadding,
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: colors.brandTint,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cardPressed: { opacity: 0.7 },
  profileText: { flex: 1, gap: 4 },
  profileName: { ...typography.listTitle, color: colors.textPrimary },
  profileMeta: { ...typography.caption, color: colors.textSecondary },
  // 카드 오른쪽 "로그인" — 브랜드색 + chevron 으로 "여기 눌러 가는 곳"임을 알린다
  // (내 몸 정보 카드의 chevron 과 같은 어법).
  cardAction: { ...typography.boxLabel, color: colors.brand },
  guestHint: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: -6, // 카드에 붙은 설명 — body gap(14)을 절반으로 당긴다
    paddingHorizontal: 4,
  },
  signOut: { alignSelf: 'center', paddingVertical: 12, paddingHorizontal: 20 },
  signOutText: { ...typography.caption, color: colors.textSecondary },
  signOutError: {
    ...typography.caption,
    color: colors.brand,
    textAlign: 'center',
  },
  bodyCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: colors.cardBg,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    borderRadius: radius.card,
    padding: spacing.cardPadding,
  },
  bodyPrompt: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: colors.brandTint,
    borderRadius: radius.card,
    padding: spacing.cardPadding,
  },
  bodyCardPressed: { opacity: 0.7 },
  bodyCardText: { flex: 1, gap: 4 },
  bodyCardTitle: { ...typography.listTitle, color: colors.textPrimary },
  bodyCardSummary: { ...typography.caption, color: colors.textSecondary },
  bodyPromptText: { ...typography.caption, color: colors.textPrimary },
  modalSafe: { flex: 1, backgroundColor: colors.bg },
  stats: { flexDirection: 'row', gap: 10 },
  statBox: {
    flex: 1,
    backgroundColor: colors.cardBg,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    borderRadius: radius.card,
    padding: spacing.cardPadding,
    gap: 8,
  },
  statLabel: { ...typography.caption, color: colors.textSecondary },
  statValueRow: { flexDirection: 'row', alignItems: 'baseline', gap: 4 },
  statValue: { ...typography.score, fontSize: 28, color: colors.brand },
  statSuffix: { ...typography.caption, color: colors.textSecondary },
  infoList: {
    backgroundColor: colors.cardBg,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    borderRadius: radius.card,
    paddingHorizontal: spacing.cardPadding,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: colors.divider,
  },
  infoRowLast: { borderBottomWidth: 0 },
  infoLabel: { ...typography.caption, color: colors.textSecondary },
  infoValue: { ...typography.boxLabel, color: colors.textPrimary },
  notice: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    padding: spacing.cardPadding,
    backgroundColor: colors.brandTint,
    borderRadius: radius.card,
  },
  noticeText: { ...typography.caption, color: colors.textPrimary, flex: 1 },
});

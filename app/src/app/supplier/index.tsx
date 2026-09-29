// 공급자 페이지 첫 화면 — `/supplier` (Phase 38 D-01·D-02·D-03·D-09·D-10·D-12·D-20·D-22).
//
// 링크 = 같은 앱의 공급자 모드 첫 화면(belle Q1 ○, 38-04 결정 option-1 = Expo Router web export).
// 폰 브라우저에서 열린다. 상태기계:
//   boot     — Firebase 가 세션을 복원하는 중(깜빡임 방지, authUser.ts ready)
//   login    — A-1: 로그인 전 또는 익명(게스트) 세션. Google 팝업 1개(socialAuth.web.ts)
//   checking — 로그인 직후 화이트리스트 확인(`POST /reference/upload-url {probe:true}`)
//   noAccess — A-2: 403 forbidden. 내 ID(uid)를 보여주고 복사·재확인(닭-달걀 절차, D-03)
//   home     — A-3: 내 동작(where supplierUid 단일 구독) + 내 코드(표시·복사만, D-12/D-13)
//
// 문구는 전부 supplierCopy(화면 리터럴 0), 규칙은 전부 supplierRules import(리뷰 R14),
// 색·반경은 theme 토큰 → SupplierUi 프리미티브. 브라우저는 Firestore 를 쓰지 않는다(T-38-10-4).

import { Ionicons } from '@expo/vector-icons';
import Constants from 'expo-constants';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { signOut } from 'firebase/auth';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import {
  Card,
  CodeCard,
  GoogleButton,
  GradientHeader,
  GrayCard,
  IdBox,
  ListRow,
  NoticePill,
  OutlineButton,
  PageFrame,
  PillCta,
  SectionHeader,
  Sheet,
  space,
  StepCard,
  text,
  TextLink,
  Toast,
  TopBar,
} from '../../components/SupplierUi';
import { supplierCopy } from '../../constants/supplierCopy';
import { ApiError, probeSupplier } from '../../lib/api';
import { displayNameOf, useAuthUser } from '../../lib/authUser';
import { auth } from '../../lib/firebase';
import { signInWithGoogle } from '../../lib/socialAuth';
import { useSupplierMotions } from '../../lib/supplierMotions';
import {
  hasDetail,
  mapPresignFailure,
  presignFailureMessage,
  rowSubtitle,
  sortNewestFirst,
} from '../../lib/supplierRules';
import { colors } from '../../theme';

// 목록 카드에 한 번에 보이는 행 수 — 넘으면 `전체보기`(UI-SPEC A-3 "행 6개 초과").
const ROWS_BEFORE_SEE_ALL = 6;
const TOAST_MS = 3000;
const COPIED_LABEL_MS = 2000;
const HIGHLIGHT_MS = 3000;

type Probe =
  | { kind: 'idle' }
  | { kind: 'checking' }
  | { kind: 'ok'; code: string | null }
  | { kind: 'forbidden' }
  | { kind: 'error'; message: string };

type Phase = 'boot' | 'login' | 'checking' | 'noAccess' | 'home' | 'error';

const BUILD_SHA: string =
  (Constants.expoConfig?.extra as { commitSha?: string } | undefined)?.commitSha ?? 'dev';

function buildLabel(): string {
  return supplierCopy.common.build.replace('{sha}', BUILD_SHA);
}

// 웹 클립보드. 네이티브·권한 거부·비보안 컨텍스트면 false → 호출부가 copyFallback 문구.
async function copyText(value: string): Promise<boolean> {
  const clip = (globalThis as { navigator?: { clipboard?: { writeText?: (t: string) => Promise<void> } } })
    .navigator?.clipboard;
  if (!clip?.writeText) return false;
  try {
    await clip.writeText(value);
    return true;
  } catch {
    return false;
  }
}

function errorStatus(e: unknown): { status: number; code: string | null } {
  if (e instanceof ApiError) return { status: e.status, code: e.code };
  // fetch 자체 실패(TypeError: Failed to fetch 등) = 네트워크.
  return { status: 0, code: null };
}

export default function SupplierHome() {
  const router = useRouter();
  const params = useLocalSearchParams<{ detail?: string; justUploaded?: string }>();
  const { user, isGuest, ready } = useAuthUser();
  const signedIn = !!user && !isGuest;
  const uid = signedIn ? user.uid : null;

  // ── A-1 로그인 ──
  const [loginBusy, setLoginBusy] = useState(false);
  const [loginNotice, setLoginNotice] = useState<string | null>(null);

  // 팝업은 클릭 직후 동기적으로 열려야 차단되지 않는다 — signInWithGoogle 앞에 await 없음.
  const onGoogle = () => {
    setLoginNotice(null);
    setLoginBusy(true);
    signInWithGoogle()
      .then(({ outcome }) => {
        if (outcome === 'cancelled') return;
        // 성공은 onAuthStateChanged → useAuthUser 가 화면을 넘긴다.
      })
      .catch((e: unknown) => {
        const code = (e as { code?: unknown })?.code;
        setLoginNotice(
          code === 'auth/popup-blocked' ? supplierCopy.login.popupBlocked : supplierCopy.login.failed,
        );
      })
      .finally(() => setLoginBusy(false));
  };

  const onSignOut = () => {
    void signOut(auth);
  };

  // ── 화이트리스트 확인(probe) ──
  const [probe, setProbe] = useState<Probe>({ kind: 'idle' });
  const [recheckBusy, setRecheckBusy] = useState(false);
  const [stillNo, setStillNo] = useState(false);

  const runProbe = useCallback(async (): Promise<Probe> => {
    try {
      const res = await probeSupplier();
      return { kind: 'ok', code: res.supplierCode };
    } catch (e) {
      const kind = mapPresignFailure(errorStatus(e));
      if (kind === 'forbidden') return { kind: 'forbidden' };
      if (kind === 'sessionExpired') {
        // 401 → A-1 + 세션 만료 문구(UI-SPEC A-7).
        setLoginNotice(supplierCopy.form.sessionExpired);
        void signOut(auth);
        return { kind: 'idle' };
      }
      return { kind: 'error', message: presignFailureMessage(kind) ?? supplierCopy.common.offline };
    }
  }, []);

  useEffect(() => {
    if (!uid) {
      setProbe({ kind: 'idle' });
      setStillNo(false);
      return;
    }
    let cancelled = false;
    setProbe({ kind: 'checking' });
    void runProbe().then((p) => {
      if (!cancelled) setProbe(p);
    });
    return () => {
      cancelled = true;
    };
  }, [uid, runProbe]);

  const onRecheck = async () => {
    setRecheckBusy(true);
    setStillNo(false);
    const p = await runProbe();
    setRecheckBusy(false);
    if (p.kind === 'forbidden') setStillNo(true);
    setProbe(p);
  };

  const onRetryProbe = async () => {
    setProbe({ kind: 'checking' });
    setProbe(await runProbe());
  };

  // ── 토스트 · 복사 ──
  const [toast, setToast] = useState<string | null>(null);
  const [codeCopied, setCodeCopied] = useState(false);
  const [copyFallback, setCopyFallback] = useState(false);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), TOAST_MS);
    return () => clearTimeout(t);
  }, [toast]);
  useEffect(() => {
    if (!codeCopied) return;
    const t = setTimeout(() => setCodeCopied(false), COPIED_LABEL_MS);
    return () => clearTimeout(t);
  }, [codeCopied]);

  const onCopy = async (value: string, isCode: boolean) => {
    const ok = await copyText(value);
    if (ok) {
      setCopyFallback(false);
      setToast(supplierCopy.common.copied);
      if (isCode) setCodeCopied(true);
    } else {
      setCopyFallback(true);
    }
  };

  // ── 내 동작(A-3 카드 1) ──
  const { motions, loading: listLoading, error: listError, retry } = useSupplierMotions(
    probe.kind === 'ok' ? uid : null,
  );
  const sorted = useMemo(() => sortNewestFirst(motions), [motions]);
  const [showAll, setShowAll] = useState(false);
  const visible = showAll ? sorted : sorted.slice(0, ROWS_BEFORE_SEE_ALL);
  const anyQueued = sorted.some((m) => m.registrationStatus === 'queued');

  // 방금 올린 행(?justUploaded=refId) — 테두리 brand 3초 + 스크롤(UI-SPEC A-3).
  const justUploaded = typeof params.justUploaded === 'string' ? params.justUploaded : null;
  const [highlightId, setHighlightId] = useState<string | null>(null);
  const scrollRef = useRef<ScrollView>(null);
  const offsets = useRef({ sheet: 0, card: 0, list: 0 });
  useEffect(() => {
    if (!justUploaded) return;
    setHighlightId(justUploaded);
    const t = setTimeout(() => setHighlightId(null), HIGHLIGHT_MS);
    return () => clearTimeout(t);
  }, [justUploaded]);
  const onRowLayout = (motionId: string, y: number) => {
    if (motionId !== highlightId) return;
    const o = offsets.current;
    scrollRef.current?.scrollTo({ y: Math.max(0, o.sheet + o.card + o.list + y - space.md), animated: true });
  };

  const openDetail = (motionId: string) => {
    router.push({ pathname: '/supplier', params: { detail: motionId } });
  };

  // ── 화면 결정 ──
  let phase: Phase;
  if (!ready) phase = 'boot';
  else if (!signedIn) phase = 'login';
  else if (probe.kind === 'forbidden') phase = 'noAccess';
  else if (probe.kind === 'ok') phase = 'home';
  else if (probe.kind === 'error') phase = 'error';
  else phase = 'checking';

  if (phase === 'boot') {
    return <SafeAreaView style={styles.page} />;
  }

  if (phase === 'login') {
    return (
      <SafeAreaView style={styles.page} edges={['top', 'bottom']}>
        <PageFrame>
          <View style={styles.pad}>
            <TopBar showWordmark />
            <Text style={[text.display, styles.mt32]} accessibilityRole="header">
              {supplierCopy.login.title}
            </Text>
            <Text style={[text.label, text.mid, styles.mt8]}>{supplierCopy.login.body}</Text>
            <View style={styles.mt48}>
              <GoogleButton
                label={loginBusy ? supplierCopy.login.busy : supplierCopy.login.google}
                onPress={onGoogle}
                busy={loginBusy}
              />
            </View>
            <Text style={[text.label, text.mid, text.center, styles.mt12]}>
              {supplierCopy.login.sameAccountHint}
            </Text>
            {loginNotice ? (
              <Text style={[text.label, styles.teal, styles.mt12]} accessibilityLiveRegion="polite">
                {loginNotice}
              </Text>
            ) : null}
            <View style={styles.flex} />
            <Text style={[text.label, text.sub, text.center, styles.mt24]}>{buildLabel()}</Text>
          </View>
        </PageFrame>
      </SafeAreaView>
    );
  }

  const identity = supplierCopy.home.identity
    .replace('{name}', displayNameOf(user) ?? '')
    .replace('{email}', user?.email ?? '');

  if (phase === 'checking' || phase === 'error') {
    return (
      <SafeAreaView style={styles.page} edges={['top', 'bottom']}>
        <PageFrame>
          <View style={styles.pad}>
            <TopBar showWordmark />
            <Text style={[text.display, styles.mt32]} accessibilityRole="header">
              {supplierCopy.home.title}
            </Text>
            <Text style={[text.label, text.mid, styles.mt4]}>{identity}</Text>
            {probe.kind === 'error' ? (
              <View style={styles.mt32}>
                <Text style={[text.label, styles.teal]} accessibilityLiveRegion="polite">
                  {probe.message}
                </Text>
                <View style={styles.mt16}>
                  <OutlineButton label={supplierCopy.common.retry} onPress={onRetryProbe} />
                </View>
              </View>
            ) : (
              <Text style={[text.label, text.mid, styles.mt32]} accessibilityLiveRegion="polite">
                {supplierCopy.noAccess.checking}
              </Text>
            )}
            <View style={styles.mt24}>
              <TextLink label={supplierCopy.common.signOut} onPress={onSignOut} tone="signOut" />
            </View>
          </View>
        </PageFrame>
      </SafeAreaView>
    );
  }

  if (phase === 'noAccess') {
    return (
      <SafeAreaView style={styles.page} edges={['top', 'bottom']}>
        <Toast message={toast} />
        <PageFrame>
          <ScrollView contentContainerStyle={styles.pad}>
            <TopBar showWordmark />
            <Text style={[text.display, styles.mt32]} accessibilityRole="header">
              {supplierCopy.home.title}
            </Text>
            <Text style={[text.label, text.mid, styles.mt4]}>{identity}</Text>
            <View style={[styles.mt32, styles.iconCenter]}>
              <AlertCircle />
            </View>
            <Text style={[text.title, text.center, styles.mt16]}>{supplierCopy.noAccess.title}</Text>
            <Text style={[text.label, text.mid, text.center, styles.mt8]}>
              {supplierCopy.noAccess.body}
            </Text>
            <Text style={[text.label, styles.mt16]}>{supplierCopy.noAccess.idLabel}</Text>
            <View style={styles.mt4}>
              <IdBox value={user?.uid ?? ''} />
            </View>
            {copyFallback ? (
              <Text style={[text.label, text.mid, styles.mt8]}>{supplierCopy.common.copyFallback}</Text>
            ) : null}
            <View style={[styles.mt16, styles.gap8]}>
              <OutlineButton
                label={supplierCopy.noAccess.copyId}
                onPress={() => onCopy(user?.uid ?? '', false)}
              />
              <OutlineButton
                label={recheckBusy ? supplierCopy.noAccess.checking : supplierCopy.noAccess.refresh}
                onPress={onRecheck}
                disabled={recheckBusy}
              />
            </View>
            {stillNo ? (
              <Text style={[text.label, styles.teal, styles.mt8]} accessibilityLiveRegion="polite">
                {supplierCopy.noAccess.stillNo}
              </Text>
            ) : null}
            <View style={styles.mt24}>
              <TextLink label={supplierCopy.common.signOut} onPress={onSignOut} tone="signOut" />
            </View>
          </ScrollView>
        </PageFrame>
      </SafeAreaView>
    );
  }

  // ── A-3 홈 ──
  const supplierCode = probe.kind === 'ok' ? probe.code : null;
  const athleteName = displayNameOf(user) ?? '';
  const uploadCta = (
    <PillCta label={supplierCopy.home.upload} onPress={() => router.push('/supplier/upload')} />
  );

  return (
    <View style={styles.page}>
      <Toast message={toast} />
      <PageFrame>
        <ScrollView ref={scrollRef} contentContainerStyle={styles.homeScroll}>
          <GradientHeader title={supplierCopy.home.title} />
          <View onLayout={(e) => (offsets.current.sheet = e.nativeEvent.layout.y)}>
            <Sheet>
              {/* ui-checker flag 7행 — identity · 가이드 링크는 헤더가 아니라 시트 맨 위 한 줄 */}
              <View style={styles.identityRow}>
                <Text style={[text.label, text.mid, styles.flex]} numberOfLines={1}>
                  {identity}
                </Text>
                <TextLink
                  label={supplierCopy.common.guideLink}
                  onPress={() => router.push('/supplier/guide')}
                  tone="go"
                />
              </View>

              {/* 카드 1 — 내 동작 */}
              <View onLayout={(e) => (offsets.current.card = e.nativeEvent.layout.y)}>
                <Card style={styles.mt16}>
                  <SectionHeader
                    title={supplierCopy.home.motionsTitle}
                    moreLabel={supplierCopy.common.seeAll}
                    onMore={
                      !showAll && sorted.length > ROWS_BEFORE_SEE_ALL ? () => setShowAll(true) : undefined
                    }
                  />
                  <Text style={[text.label, text.mid, styles.mt8]}>{supplierCopy.home.motionsSub}</Text>
                  {anyQueued ? (
                    <View style={styles.mt16}>
                      <NoticePill lines={supplierCopy.home.podDown} />
                    </View>
                  ) : null}
                  {listError ? (
                    <View style={[styles.mt16, styles.gap8]}>
                      <GrayCard message={listError} />
                      <OutlineButton label={supplierCopy.common.retry} onPress={retry} />
                    </View>
                  ) : listLoading ? null : sorted.length === 0 ? (
                    <View style={styles.mt16}>
                      <StepCard
                        step={supplierCopy.home.emptyStep}
                        title={supplierCopy.home.emptyTitle}
                        body={supplierCopy.home.emptyBody}
                        cta={uploadCta}
                      />
                    </View>
                  ) : (
                    <>
                      <View style={styles.mt12}>{uploadCta}</View>
                      <View
                        style={styles.mt12}
                        onLayout={(e) => (offsets.current.list = e.nativeEvent.layout.y)}
                      >
                        {visible.map((m, i) => (
                          <ListRow
                            key={m.motionId}
                            title={m.name}
                            subtitle={rowSubtitle(m)}
                            showChevron={hasDetail(m)}
                            onPress={hasDetail(m) ? () => openDetail(m.motionId) : undefined}
                            highlighted={m.motionId === highlightId}
                            isLast={i === visible.length - 1}
                            onLayout={(y) => onRowLayout(m.motionId, y)}
                          />
                        ))}
                      </View>
                    </>
                  )}
                </Card>
              </View>

              {/* 카드 2 — 내 코드 (표시·복사만, D-12/D-13) */}
              <View style={styles.mt16}>
                <Text style={[text.heading, styles.mb8]} accessibilityRole="header">
                  {supplierCopy.home.codeTitle}
                </Text>
                <CodeCard
                  photoUrl={user?.photoURL ?? null}
                  sportLabel={supplierCopy.home.sport}
                  athleteLine={supplierCopy.home.athlete.replace('{name}', athleteName)}
                  code={supplierCode}
                  pendingLabel={supplierCopy.home.codePending}
                  copyLabel={codeCopied ? supplierCopy.common.copiedShort : supplierCopy.common.copy}
                  onCopy={() => supplierCode && onCopy(supplierCode, true)}
                  howText={supplierCopy.home.codeHow}
                />
                {copyFallback ? (
                  <Text style={[text.label, text.mid, styles.mt8]}>{supplierCopy.common.copyFallback}</Text>
                ) : null}
              </View>

              <View style={styles.mt24}>
                <TextLink label={supplierCopy.common.signOut} onPress={onSignOut} tone="signOut" />
              </View>
              <Text style={[text.label, text.sub, styles.mt8]}>{buildLabel()}</Text>
            </Sheet>
          </View>
        </ScrollView>
      </PageFrame>
    </View>
  );
}

// A-2 아이콘 — alert-circle 44 brand (UI-SPEC A-2).
function AlertCircle() {
  return <Ionicons name="alert-circle" size={44} color={colors.brand} />;
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  flex: { flex: 1 },
  pad: { flexGrow: 1, paddingHorizontal: space.screen, paddingBottom: space.lg },
  homeScroll: { flexGrow: 1 },
  mt4: { marginTop: space.xs },
  mt8: { marginTop: space.sm },
  mt12: { marginTop: space.row },
  mt16: { marginTop: space.md },
  mt24: { marginTop: space.lg },
  mt32: { marginTop: space.xl },
  mt48: { marginTop: space.xxl },
  mb8: { marginBottom: space.sm },
  gap8: { gap: space.sm },
  teal: { color: colors.infoTeal },
  iconCenter: { alignItems: 'center' },
  identityRow: { flexDirection: 'row', alignItems: 'center', gap: space.sm },
});

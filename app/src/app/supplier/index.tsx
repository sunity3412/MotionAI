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
// 2026-09-30 배치 = 38-DESIGN.md(Figma 282:506) A-1 · A-2 · A-3 · A-3b · A-3c.

import Constants from 'expo-constants';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { signOut } from 'firebase/auth';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { AlertIcon } from '../../components/PickErrorDialog';
import {
  BrandMark,
  Card,
  Chip,
  CodeCard,
  DonePanel,
  FailurePanel,
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
  type RowTrailing,
} from '../../components/SupplierUi';
import { supplierCopy } from '../../constants/supplierCopy';
import { ApiError, probeSupplier } from '../../lib/api';
import { displayNameOf, useAuthUser } from '../../lib/authUser';
import { auth } from '../../lib/firebase';
import { signInWithGoogle } from '../../lib/socialAuth';
import { useSupplierMotions, useSupplierRegistrationPrivate } from '../../lib/supplierMotions';
import {
  expiredCopy,
  failCopy,
  hasDetail,
  LEVEL_LABEL_KO,
  mapPresignFailure,
  presignFailureMessage,
  rowSubtitle,
  SELF_SCORE_OK_MIN,
  selfCheckNote,
  selfCheckView,
  sortNewestFirst,
  type SupplierMotion,
  type SupplierMotionPrivate,
} from '../../lib/supplierRules';
import { colors, layout } from '../../theme';

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

// 등록일 `YYYY.MM.DD`(UI-SPEC A-3c). createdAt 0 = 모름 → 대시.
function formatDate(epochMs: number): string {
  if (!(epochMs > 0)) return EMPTY_VALUE;
  const d = new Date(epochMs);
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}.${mm}.${dd}`;
}

// 비공개 doc 로딩 중·값 없음 표시.
const EMPTY_VALUE = '–';

// 38-DESIGN A-3 행 오른쪽 — 진행 중(registering/processing/queued)은 8px 점, 상세가 있으면 쉐브론.
function rowTrailing(m: SupplierMotion): RowTrailing {
  const st = m.registrationStatus;
  if (st === 'registering' || st === 'processing' || st === 'queued') return 'progress';
  return hasDetail(m) ? 'chevron' : null;
}

// 38-11 올리기 폼이 읽는 프리필 파라미터 계약 — 이름 그대로(name · athleteName · level ·
// isSplit · hasHold · standingStart). 선언 3 은 비공개 doc 에서(R13) — 아직 못 읽었으면 뺀다.
function yesNoParam(v: boolean | undefined): '1' | '0' | undefined {
  return v == null ? undefined : v ? '1' : '0';
}

function errorStatus(e: unknown): { status: number; code: string | null } {
  if (e instanceof ApiError) return { status: e.status, code: e.code };
  // fetch 자체 실패(TypeError: Failed to fetch 등) = 네트워크.
  return { status: 0, code: null };
}

export default function SupplierHome() {
  const router = useRouter();
  const params = useLocalSearchParams<{ detail?: string; justUploaded?: string; expired?: string }>();
  const { user, isGuest, ready } = useAuthUser();
  const insets = useSafeAreaInsets();
  const signedIn = !!user && !isGuest;
  const uid = signedIn ? user.uid : null;

  // ── A-1 로그인 ──
  const [loginBusy, setLoginBusy] = useState(false);
  // 38-11: 올리기 폼 제출이 401 이면 폼이 `?expired=1` 로 여기 보낸다 → A-1 에 세션 만료 문구(UI-SPEC A-7).
  const [loginNotice, setLoginNotice] = useState<string | null>(() =>
    params.expired === '1' ? supplierCopy.form.sessionExpired : null,
  );

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

  // ── 상세(A-3b · 만료 · A-3c) — URL param `?detail=refId` 로 표현(브라우저 뒤로 = 목록) ──
  const detailId = typeof params.detail === 'string' && params.detail ? params.detail : null;
  const detailMotion =
    probe.kind === 'ok' && detailId ? sorted.find((m) => m.motionId === detailId) ?? null : null;
  const detailOpen = detailMotion != null && hasDetail(detailMotion);
  // 비공개 doc 은 상세가 열렸을 때만 1건 구독(R13) — 목록에서는 읽지 않는다.
  const { priv, loading: privLoading, error: privError } = useSupplierRegistrationPrivate(
    detailOpen ? detailMotion.motionId : null,
  );
  // 남의 doc(permission-denied)이면 목록으로 — 실패 문구로 강등하지 않는다.
  useEffect(() => {
    if (privError === 'permission-denied') router.replace('/supplier');
  }, [privError, router]);

  // 방금 올린 행(?justUploaded=refId) — 토스트 form.uploaded.toast + 테두리 brand 3초 + 스크롤
  // (UI-SPEC A-3 · A-5). 38-11: 홈이 보인 뒤(probe ok)에 띄운다 — 확인 중 화면에는 Toast 가 없어
  // 3초 타이머가 먼저 끝나면 아무것도 안 보였다.
  const justUploaded = typeof params.justUploaded === 'string' ? params.justUploaded : null;
  const homeReady = probe.kind === 'ok';
  const [highlightId, setHighlightId] = useState<string | null>(null);
  const scrollRef = useRef<ScrollView>(null);
  const offsets = useRef({ sheet: 0, card: 0, list: 0 });
  useEffect(() => {
    if (!justUploaded || !homeReady) return;
    setToast(supplierCopy.form.uploaded.toast);
    setHighlightId(justUploaded);
    const t = setTimeout(() => setHighlightId(null), HIGHLIGHT_MS);
    return () => clearTimeout(t);
  }, [justUploaded, homeReady]);
  const onRowLayout = (motionId: string, y: number) => {
    if (motionId !== highlightId) return;
    const o = offsets.current;
    scrollRef.current?.scrollTo({ y: Math.max(0, o.sheet + o.card + o.list + y - space.md), animated: true });
  };

  const openDetail = (motionId: string) => {
    router.push({ pathname: '/supplier', params: { detail: motionId } });
  };

  const closeDetail = () => {
    if (router.canGoBack()) router.back();
    else router.replace('/supplier');
  };

  const reupload = (m: SupplierMotion, p: SupplierMotionPrivate | null) => {
    router.push({
      pathname: '/supplier/upload',
      params: {
        name: m.name,
        athleteName: m.athleteName,
        level: m.level,
        isSplit: yesNoParam(p?.isSplit),
        hasHold: yesNoParam(p?.hasHold),
        standingStart: yesNoParam(p?.standingStart),
      },
    });
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
    // 38-DESIGN A-1 — 워드마크(safe-area 위 40) → 48 → 칩 → 12 → 제목 → 8 → 본문 → 48 → Google 54 →
    // 12 → 힌트 → (알림) → 아래 빌드, 하단 여백 34.
    return (
      <SafeAreaView style={styles.page} edges={['top']}>
        <PageFrame>
          <View
            style={[
              styles.pad,
              { paddingBottom: Math.max(insets.bottom, layout.safeAreaBottom) },
            ]}
          >
            <View style={styles.mt40}>
              <BrandMark variant="brand" />
            </View>
            <View style={styles.mt48}>
              <Chip label={supplierCopy.login.chip} />
            </View>
            <Text style={[text.display, styles.mt12]} accessibilityRole="header">
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
            <Text style={[text.auxFaint, text.center, styles.mt12]}>
              {supplierCopy.login.sameAccountHint}
            </Text>
            {loginNotice ? (
              <Text style={[text.label, styles.teal, styles.mt12]} accessibilityLiveRegion="polite">
                {loginNotice}
              </Text>
            ) : null}
            <View style={styles.flex} />
            <Text style={[text.caption, text.center, styles.mt24]}>{buildLabel()}</Text>
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
            <View style={styles.mt40}>
              <BrandMark variant="brand" />
            </View>
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
    // 38-DESIGN A-2 — 카드 하나(아이콘 · 제목 · 본문 · 내 ID · ID 복사) + 카드 밖 `등록 확인하기` ·
    // 힌트(확인 중 · 여전히 없음 문구도 이 자리) · 다른 계정 링크. 카드 안은 왼쪽 정렬.
    const recheckHint = recheckBusy
      ? supplierCopy.noAccess.checking
      : stillNo
        ? supplierCopy.noAccess.stillNo
        : supplierCopy.noAccess.refreshHint;
    return (
      <SafeAreaView style={styles.page} edges={['top', 'bottom']}>
        <Toast message={toast} />
        <PageFrame>
          <ScrollView contentContainerStyle={styles.pad}>
            <View style={styles.mt40}>
              <BrandMark variant="brand" />
            </View>
            <Text style={[text.display, styles.mt32]} accessibilityRole="header">
              {supplierCopy.home.title}
            </Text>
            <Text style={[text.label, text.mid, styles.mt4]}>{identity}</Text>
            <Card style={styles.mt32}>
              <AlertIcon size={44} />
              <Text style={[text.title, styles.mt16]}>{supplierCopy.noAccess.title}</Text>
              <Text style={[text.label, text.mid, styles.mt8]}>{supplierCopy.noAccess.body}</Text>
              <Text style={[text.body15Bold, text.mid, styles.mt16]}>
                {supplierCopy.noAccess.idLabel}
              </Text>
              <View style={styles.mt6}>
                <IdBox value={user?.uid ?? ''} />
              </View>
              <View style={styles.mt8}>
                <OutlineButton
                  label={supplierCopy.noAccess.copyId}
                  onPress={() => onCopy(user?.uid ?? '', false)}
                />
              </View>
              {copyFallback ? (
                <Text style={[text.aux, styles.mt8]}>{supplierCopy.common.copyFallback}</Text>
              ) : null}
            </Card>
            <View style={styles.mt16}>
              <OutlineButton
                label={supplierCopy.noAccess.refresh}
                onPress={onRecheck}
                disabled={recheckBusy}
              />
            </View>
            <Text
              style={[text.auxFaint, text.center, styles.mt8]}
              accessibilityLiveRegion="polite"
            >
              {recheckHint}
            </Text>
            <View style={styles.mt24}>
              <TextLink label={supplierCopy.common.signOut} onPress={onSignOut} tone="signOut" />
            </View>
          </ScrollView>
        </PageFrame>
      </SafeAreaView>
    );
  }

  // ── A-3b · 만료 · A-3c 상세 ──
  if (detailOpen) {
    const m = detailMotion;
    const tip = { head: supplierCopy.row.tipHead, lines: supplierCopy.row.tip };
    let panel: React.ReactNode;
    if (m.registrationStatus === 'failed') {
      if (privLoading) {
        panel = <View style={styles.skeleton} accessibilityLabel={supplierCopy.noAccess.checking} />;
      } else {
        const err = priv?.registrationError;
        const copy = failCopy(err?.code ?? 'server_error', err?.joints);
        panel = (
          <FailurePanel
            title={copy.title}
            body={copy.body}
            code={err?.code ?? 'server_error'}
            tip={tip}
            reuploadLabel={supplierCopy.row.reupload}
            onReupload={() => reupload(m, priv)}
            backLabel={supplierCopy.common.toList}
            onBack={closeDetail}
          />
        );
      }
    } else if (m.registrationStatus === 'expired') {
      // 리뷰 R4 — 코드 칩·TIP 없이 제목·본문 + 다시 올리기(같은 프리필).
      const copy = expiredCopy();
      panel = (
        <FailurePanel
          title={copy.title}
          body={copy.body}
          reuploadLabel={supplierCopy.row.reupload}
          onReupload={() => reupload(m, priv)}
          backLabel={supplierCopy.common.toList}
          onBack={closeDetail}
        />
      );
    } else {
      // 표시와 분기가 같은 숫자 — 카드의 `{score}점` 과 낮음 분기(TIP + 다시 올리기) 모두 view.score.
      const view = selfCheckView(m);
      const info = supplierCopy.row.done.info;
      const yn = (v: boolean | undefined) =>
        privLoading || v == null ? EMPTY_VALUE : v ? supplierCopy.form.sec3.yes : supplierCopy.form.sec3.no;
      panel = (
        <DonePanel
          title={supplierCopy.row.done.title}
          sub={supplierCopy.row.done.sub
            .replace('{name}', m.name)
            .replace('{athlete}', m.athleteName)}
          selfTitle={supplierCopy.row.self.title}
          scoreText={
            view.score != null
              ? supplierCopy.row.self.scoreText.replace('{score}', String(view.score))
              : null
          }
          selfBody={view.body}
          note={selfCheckNote()}
          info={[
            { label: info.name, value: m.name },
            { label: info.athlete, value: m.athleteName },
            { label: info.level, value: LEVEL_LABEL_KO[m.level] },
            { label: info.registeredAt, value: formatDate(m.createdAt) },
            { label: info.split, value: yn(priv?.isSplit) },
            { label: info.hold, value: yn(priv?.hasHold) },
            { label: info.stand, value: yn(priv?.standingStart) },
          ]}
          low={view.score != null && view.score < SELF_SCORE_OK_MIN}
          tip={tip}
          reuploadLabel={supplierCopy.row.reupload}
          onReupload={() => reupload(m, priv)}
          backLabel={supplierCopy.common.toList}
          onBack={closeDetail}
        />
      );
    }
    return (
      <SafeAreaView style={styles.page} edges={['top', 'bottom']}>
        <PageFrame>
          <ScrollView contentContainerStyle={styles.pad}>
            <TopBar onBack={closeDetail} backLabel={supplierCopy.common.back} />
            {panel}
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

  const showEmpty = !listError && !listLoading && sorted.length === 0;
  const hiddenRows = !showAll && sorted.length > ROWS_BEFORE_SEE_ALL;
  const countText =
    listError || listLoading ? null : supplierCopy.home.count.replace('{n}', String(sorted.length));

  return (
    <View style={styles.page}>
      <Toast message={toast} />
      <PageFrame>
        <ScrollView ref={scrollRef} contentContainerStyle={styles.homeScroll}>
          {/* 38-DESIGN A-3 로 identity · 촬영 가이드 링크가 헤더에 복귀(ui-checker flag 7행 대체) */}
          <GradientHeader
            title={supplierCopy.home.title}
            identity={identity}
            guideLabel={supplierCopy.common.guideLink}
            onGuide={() => router.push('/supplier/guide')}
          />
          <View onLayout={(e) => (offsets.current.sheet = e.nativeEvent.layout.y)}>
            <Sheet>
              {/* 카드 1 — 내 동작. 비었으면 점선 STEP 카드 하나가 그 자리(38-DESIGN 빈 상태) */}
              {showEmpty ? (
                <StepCard
                  step={supplierCopy.home.emptyStep}
                  title={supplierCopy.home.emptyTitle}
                  body={supplierCopy.home.emptyBody}
                  cta={uploadCta}
                />
              ) : (
                <View onLayout={(e) => (offsets.current.card = e.nativeEvent.layout.y)}>
                  <Card style={styles.motionsCard}>
                    <SectionHeader title={supplierCopy.home.motionsTitle} count={countText} />
                    <Text style={[text.aux, styles.mt4]}>{supplierCopy.home.motionsSub}</Text>
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
                    ) : listLoading ? null : (
                      <>
                        <View style={anyQueued ? styles.mt12 : styles.mt16}>{uploadCta}</View>
                        <View
                          style={styles.mt8}
                          onLayout={(e) => (offsets.current.list = e.nativeEvent.layout.y)}
                        >
                          {visible.map((m, i) => (
                            <ListRow
                              key={m.motionId}
                              title={m.name}
                              subtitle={rowSubtitle(m)}
                              trailing={rowTrailing(m)}
                              onPress={hasDetail(m) ? () => openDetail(m.motionId) : undefined}
                              highlighted={m.motionId === highlightId}
                              isLast={i === visible.length - 1}
                              onLayout={(y) => onRowLayout(m.motionId, y)}
                            />
                          ))}
                        </View>
                        {/* 재량: 헤더 오른쪽 자리를 `{n}개` 가 가져가 `전체보기` 는 목록 아래 가운데로 */}
                        {hiddenRows ? (
                          <TextLink
                            label={supplierCopy.common.seeAll}
                            onPress={() => setShowAll(true)}
                            tone="go"
                            center
                          />
                        ) : null}
                      </>
                    )}
                  </Card>
                </View>
              )}

              {/* 카드 2 — 내 코드 (표시·복사만, D-12/D-13) */}
              <View style={styles.mt16}>
                <CodeCard
                  photoUrl={user?.photoURL ?? null}
                  sportLabel={supplierCopy.home.sport}
                  athleteLine={supplierCopy.home.athlete.replace('{name}', athleteName)}
                  codeTitle={supplierCopy.home.codeTitle}
                  code={supplierCode}
                  pendingTitle={supplierCopy.home.codePendingTitle}
                  pendingBody={supplierCopy.home.codePendingBody}
                  copyLabel={codeCopied ? supplierCopy.common.copiedShort : supplierCopy.common.copy}
                  onCopy={() => supplierCode && onCopy(supplierCode, true)}
                  howText={supplierCopy.home.codeHow}
                />
                {copyFallback ? (
                  <Text style={[text.aux, styles.mt8]}>{supplierCopy.common.copyFallback}</Text>
                ) : null}
              </View>

              <View style={styles.mt24}>
                <TextLink label={supplierCopy.common.signOut} onPress={onSignOut} tone="signOut" />
              </View>
              <Text style={[text.caption, styles.mt8]}>{buildLabel()}</Text>
            </Sheet>
          </View>
        </ScrollView>
      </PageFrame>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  flex: { flex: 1 },
  pad: { flexGrow: 1, paddingHorizontal: space.screen, paddingBottom: space.lg },
  homeScroll: { flexGrow: 1 },
  mt4: { marginTop: space.xs },
  mt6: { marginTop: space.s6 },
  mt8: { marginTop: space.sm },
  mt12: { marginTop: space.row },
  mt16: { marginTop: space.md },
  mt24: { marginTop: space.lg },
  mt32: { marginTop: space.xl },
  mt40: { marginTop: space.s40 },
  mt48: { marginTop: space.xxl },
  gap8: { gap: space.sm },
  teal: { color: colors.infoTeal },
  // 38-DESIGN A-3 내 동작 카드 패딩 16 16 8.
  motionsCard: { paddingBottom: space.sm },
  skeleton: {
    alignSelf: 'stretch',
    height: space.lg,
    borderRadius: space.sm,
    backgroundColor: colors.softBg,
    marginTop: space.xl,
  },
});

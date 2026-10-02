// 공급자 페이지 첫 화면 — `/supplier` (Phase 38 D-01·D-02·D-03·D-09·D-10·D-12·D-20·D-22).
//
// 링크 = 같은 앱의 공급자 모드 첫 화면(belle Q1 ○, 38-04 결정 option-1 = Expo Router web export).
// 폰 브라우저에서 열린다. 상태기계:
//   boot     — Firebase 가 세션을 복원하는 중(깜빡임 방지, authUser.ts ready)
//   login    — A-1: 로그인 전 또는 익명(게스트) 세션. Google 팝업 1개(socialAuth.web.ts)
//   checking — 로그인 직후 명단 확인 + 메일 초대 수락(`POST /reference/upload-url {probe:true}`)
//   noAccess — A-2 v2: 403 not_invited — 로그인 메일 + 다른 계정 + 문의 2(38-DESIGN-v2)
//   home     — A-3: 내 동작(where supplierUid 단일 구독) + 강사 코드 줄 + 크게 보기(38-DESIGN-v2)
//
// 문구는 전부 supplierCopy(화면 리터럴 0), 규칙은 전부 supplierRules import(리뷰 R14),
// 색·반경은 theme 토큰 → SupplierUi 프리미티브. 브라우저는 Firestore 를 쓰지 않는다(T-38-10-4).
// 2026-09-30 배치 = 38-DESIGN.md(Figma 282:506) A-1 · A-3b · A-3c + 38-DESIGN-v2 A-2 · A-3 · 크게 보기
// (quick-260930-lfw — 코드 카드·빌드 라벨 삭제).
// 2026-09-30 quick-260930-w9l — 다시 올리기 프리필 = name · level · techniqueRefId, A-3c 정보 표의
// 스플릿·유지·서 있는 시작 행 삭제, 목록 행 썸네일(thumbnailS3Key → referenceThumbs.ts).
// 2026-10-02 quick-261002-pa2(belle 결정 3·4) — 승인 전 행도 눌러서 검토 중 패널(하루 안 안내), queued ·
// review 만 '검토 요청 취소' → 화면 안 확인창(ConfirmDialog) → POST {cancel, refId}, cancelled 행 = 취소됨 패널.

import { useLocalSearchParams, useRouter } from 'expo-router';
import { signOut } from 'firebase/auth';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Linking, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { AlertIcon } from '../../components/PickErrorDialog';
import {
  AccountBox,
  BigCodeModal,
  BrandMark,
  Card,
  Chip,
  CodeRow,
  ConfirmDialog,
  ContactRow,
  DonePanel,
  FailurePanel,
  GoogleButton,
  GradientHeader,
  GrayCard,
  ListRow,
  NoticePill,
  OutlineButton,
  PageFrame,
  PendingPanel,
  PillCta,
  PrimaryCta,
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
import { ApiError, cancelReferenceRegistration, probeSupplier } from '../../lib/api';
import { displayNameOf, useAuthUser } from '../../lib/authUser';
import { auth } from '../../lib/firebase';
import { useReferenceThumbUri } from '../../lib/referenceThumbs';
import { toPrefillParams } from '../../lib/supplierForm';
import { signInWithGoogle } from '../../lib/socialAuth';
import { useSupplierMotions, useSupplierRegistrationPrivate } from '../../lib/supplierMotions';
import {
  canCancel,
  cancelFailureMessage,
  cancelledCopy,
  detailKind,
  expiredCopy,
  failCopy,
  hasDetail,
  isInProgress,
  LEVEL_LABEL_KO,
  mapPresignFailure,
  pendingCopy,
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
const HIGHLIGHT_MS = 3000;

// notInvited.email = 403 not_invited 의 error.email(로그인 메일). 옛 서버 응답엔 없어 null 일 수 있다.
type Probe =
  | { kind: 'idle' }
  | { kind: 'checking' }
  | { kind: 'ok'; code: string | null; displayName: string | null }
  | { kind: 'notInvited'; email: string | null }
  | { kind: 'error'; message: string };

type Phase = 'boot' | 'login' | 'checking' | 'noAccess' | 'home' | 'error';

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

// 38-DESIGN A-3 행 오른쪽 — 진행 중(registering/processing/queued/review)은 8px 점, 상세가 있으면 쉐브론.
// 진행 판정은 supplierRules.isInProgress 한 곳(quick-261001-thx 가 review 를 더했다). pa2 뒤 진행 중 행도
// 눌린다(검토 중 패널) — 점은 그대로 두고, cancelled 는 끝난 상태라 쉐브론.
function rowTrailing(m: SupplierMotion): RowTrailing {
  if (isInProgress(m)) return 'progress';
  return hasDetail(m) ? 'chevron' : null;
}

// 목록 행 — 썸네일 훅을 행마다 부르려고 작은 컴포넌트로 뗐다(w9l 항목 3). 키가 없거나
// 요청이 실패하면 thumbUri null = 종전 아이콘.
function SupplierListRow({
  motion,
  isLast,
  highlighted,
  onPress,
  onLayout,
}: {
  motion: SupplierMotion;
  isLast: boolean;
  highlighted: boolean;
  onPress?: () => void;
  onLayout: (y: number) => void;
}) {
  const thumbUri = useReferenceThumbUri(motion.motionId, motion.thumbnailS3Key);
  return (
    <ListRow
      title={motion.name}
      subtitle={rowSubtitle(motion)}
      trailing={rowTrailing(motion)}
      onPress={onPress}
      highlighted={highlighted}
      isLast={isLast}
      onLayout={onLayout}
      thumbUri={thumbUri}
    />
  );
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

  // ── 명단 확인(probe) — 서버가 같은 호출에서 메일 초대를 수락한다(38-DESIGN-v2) ──
  const [probe, setProbe] = useState<Probe>({ kind: 'idle' });

  const runProbe = useCallback(async (): Promise<Probe> => {
    try {
      const res = await probeSupplier();
      return { kind: 'ok', code: res.supplierCode, displayName: res.displayName ?? null };
    } catch (e) {
      const kind = mapPresignFailure(errorStatus(e));
      if (kind === 'notInvited') {
        return { kind: 'notInvited', email: e instanceof ApiError ? e.email : null };
      }
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

  const onRetryProbe = async () => {
    setProbe({ kind: 'checking' });
    setProbe(await runProbe());
  };

  // ── 토스트 · 복사 · 크게 보기 ──
  const [toast, setToast] = useState<string | null>(null);
  const [copyFallback, setCopyFallback] = useState(false);
  const [bigOpen, setBigOpen] = useState(false);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), TOAST_MS);
    return () => clearTimeout(t);
  }, [toast]);

  const onCopy = async (value: string) => {
    const ok = await copyText(value);
    if (ok) {
      setCopyFallback(false);
      setToast(supplierCopy.common.copied);
    } else {
      setCopyFallback(true);
    }
  };

  // 문의 행 — react-native-web 은 새 창(카카오 채널) · 메일 앱(mailto)으로 연다.
  const openLink = (url: string) => {
    void Linking.openURL(url).catch(() => undefined);
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
  // 비공개 doc 은 상세가 열렸을 때만 1건 구독(R13) — 목록에서는 읽지 않는다. 검토 중 패널(pa2)은 비공개
  // doc 을 쓰지 않으므로 구독하지 않는다(읽기 1건 절약). 취소되면 detailKind 가 cancelled 로 바뀌어 그때
  // 구독이 시작된다(다시 올리기 프리필의 techniqueRefId).
  const { priv, loading: privLoading, error: privError } = useSupplierRegistrationPrivate(
    detailOpen && detailKind(detailMotion) !== 'pending' ? detailMotion.motionId : null,
  );
  // 남의 doc(permission-denied)이면 목록으로 — 실패 문구로 강등하지 않는다.
  useEffect(() => {
    if (privError === 'permission-denied') router.replace('/supplier');
  }, [privError, router]);

  // ── 검토 요청 취소(quick-261002-pa2, 결정 4) — 확인창 → 서버 → 행·패널은 onSnapshot 이 바꾼다 ──
  const [cancelAsk, setCancelAsk] = useState(false);
  const [cancelBusy, setCancelBusy] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);
  // 다른 행의 상세로 넘어가면 앞 행의 확인창 · 실패 문구를 남기지 않는다.
  useEffect(() => {
    setCancelAsk(false);
    setCancelError(null);
  }, [detailId]);

  // 성공이면 창만 닫는다 — cancelled 로의 전환은 Firestore 구독이 그린다(낙관적 상태 쓰기 없음).
  // 실패면 창을 닫고 검토 중 패널에 한국어 문구(409 not_cancellable · 404 · 세션 · 오프라인).
  const confirmCancel = async (motionId: string) => {
    setCancelBusy(true);
    setCancelError(null);
    try {
      await cancelReferenceRegistration(motionId);
    } catch (e) {
      setCancelError(cancelFailureMessage(errorStatus(e)));
    } finally {
      setCancelBusy(false);
      setCancelAsk(false);
    }
  };

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

  // 다시 올리기 프리필 = name · level · techniqueRefId(supplierForm.toPrefillParams — 폼이 같은 규칙으로
  // 읽는다). 선수 이름은 폼이 probe displayName 으로 보여 주고, 선언은 w9l 에서 지웠다.
  const reupload = (m: SupplierMotion, p: SupplierMotionPrivate | null) => {
    router.push({
      pathname: '/supplier/upload',
      params: toPrefillParams({ name: m.name, level: m.level, techniqueRefId: p?.techniqueRefId ?? null }),
    });
  };

  // ── 화면 결정 ──
  let phase: Phase;
  if (!ready) phase = 'boot';
  else if (!signedIn) phase = 'login';
  else if (probe.kind === 'notInvited') phase = 'noAccess';
  else if (probe.kind === 'ok') phase = 'home';
  else if (probe.kind === 'error') phase = 'error';
  else phase = 'checking';

  if (phase === 'boot') {
    return <SafeAreaView style={styles.page} />;
  }

  if (phase === 'login') {
    // 38-DESIGN A-1 — 워드마크(safe-area 위 40) → 48 → 칩 → 12 → 제목 → 8 → 본문 → 48 → Google 54 →
    // 12 → 힌트 → (알림), 하단 여백 34. 빌드 라벨은 38-DESIGN-v2 가 지웠다(38-SCENARIOS §4).
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
    // 38-DESIGN-v2 A-2 — 워드마크(40) → 32 → 알림 44 → 16 → 제목 → 8 → 본문 → 24 → 지금 로그인한 계정 →
    // 12 → 다른 계정으로 로그인(CTA 54) → 40 → 도움 제목 → 4 → 도움 본문 → 12 → 카카오 · 8 · 메일.
    const na = supplierCopy.noAccess;
    const email = (probe.kind === 'notInvited' ? probe.email : null) ?? user?.email ?? EMPTY_VALUE;
    return (
      <SafeAreaView style={styles.page} edges={['top', 'bottom']}>
        <PageFrame>
          <ScrollView contentContainerStyle={styles.pad}>
            <View style={styles.mt40}>
              <BrandMark variant="brand" />
            </View>
            <View style={styles.mt32}>
              <AlertIcon size={44} />
            </View>
            <Text style={[text.display, styles.mt16]} accessibilityRole="header">
              {na.title}
            </Text>
            <Text style={[text.label, text.mid, styles.mt8]}>{na.body}</Text>
            <View style={styles.mt24}>
              <AccountBox label={na.accountLabel} email={email} />
            </View>
            <View style={styles.mt12}>
              <PrimaryCta label={supplierCopy.common.signOut} onPress={onSignOut} />
            </View>
            <Text style={[text.labelBold, styles.mt40]}>{na.helpTitle}</Text>
            <Text style={[text.aux, styles.mt4]}>{na.helpBody}</Text>
            <View style={[styles.mt12, styles.gap8]}>
              <ContactRow
                kind="kakao"
                title={na.kakaoTitle}
                onPress={() => openLink(na.kakaoUrl)}
              />
              <ContactRow
                kind="mail"
                title={na.mailTitle}
                sub={na.mailSub}
                onPress={() => openLink(na.mailUrl)}
              />
            </View>
          </ScrollView>
        </PageFrame>
      </SafeAreaView>
    );
  }

  // ── A-3b · 만료 · A-3c · 검토 중 · 취소됨 상세 (종류 = supplierRules.detailKind 한 곳) ──
  if (detailOpen) {
    const m = detailMotion;
    const tip = { head: supplierCopy.row.tipHead, lines: supplierCopy.row.tip };
    const kind = detailKind(m);
    let panel: React.ReactNode;
    let dialog: React.ReactNode = null;
    if (kind === 'pending') {
      // pa2 결정 3·4 — 하루 안 안내 + (queued · review 일 때만) 검토 요청 취소 링크 → 화면 안 확인창.
      const copy = pendingCopy();
      const cancellable = canCancel(m);
      panel = (
        <PendingPanel
          title={copy.title}
          body={copy.body}
          cancelLabel={cancellable ? supplierCopy.row.pending.cancel : undefined}
          onCancel={cancellable ? () => setCancelAsk(true) : undefined}
          error={cancelError}
          backLabel={supplierCopy.common.toList}
          onBack={closeDetail}
        />
      );
      const ask = supplierCopy.row.cancelConfirm;
      dialog = (
        <ConfirmDialog
          visible={cancelAsk}
          title={ask.title}
          lines={ask.lines}
          closeLabel={supplierCopy.common.close}
          confirmLabel={ask.confirm}
          busyLabel={ask.busy}
          busy={cancelBusy}
          onClose={() => setCancelAsk(false)}
          onConfirm={() => void confirmCancel(m.motionId)}
        />
      );
    } else if (kind === 'cancelled') {
      // pa2 결정 4 — 만료 패널 문법(코드 칩·TIP 없이) + 다시 올리기(같은 프리필).
      const copy = cancelledCopy();
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
    } else if (kind === 'failed') {
      if (privLoading) {
        panel = <View style={styles.skeleton} accessibilityLabel={supplierCopy.noAccess.checking} />;
      } else {
        const err = priv?.registrationError;
        const copy = failCopy(err?.code ?? 'server_error', err?.joints, err?.reason);
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
    } else if (kind === 'expired') {
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
      // kind === 'done'.
      // 표시와 분기가 같은 숫자 — 카드의 `{score}점` 과 낮음 분기(TIP + 다시 올리기) 모두 view.score.
      const view = selfCheckView(m);
      const info = supplierCopy.row.done.info;
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
        {dialog}
      </SafeAreaView>
    );
  }

  // ── A-3 홈 ──
  const supplierCode = probe.kind === 'ok' ? probe.code : null;
  const supplierName = probe.kind === 'ok' ? probe.displayName : null;
  const bigTitle = supplierName
    ? supplierCopy.bigCode.title.replace('{name}', supplierName)
    : supplierCopy.bigCode.titleNoName;
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
              {/* 38-DESIGN-v2 A-3 강사 코드 줄 — 코드가 있을 때만, 내 동작 카드 위 12. */}
              {/* 카드 y 는 시트 안 상대값이라 이 줄이 생겨도 방금 올린 행 스크롤 계산이 그대로 맞다. */}
              {supplierCode ? (
                <View style={styles.mb12}>
                  <CodeRow
                    label={supplierCopy.home.codeRow.label}
                    code={supplierCode}
                    copyLabel={supplierCopy.home.codeRow.copy}
                    onCopy={() => onCopy(supplierCode)}
                    bigLabel={supplierCopy.home.codeRow.big}
                    onBig={() => setBigOpen(true)}
                  />
                  {copyFallback ? (
                    <Text style={[text.aux, styles.mt8]}>{supplierCopy.common.copyFallback}</Text>
                  ) : null}
                </View>
              ) : null}
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
                            <SupplierListRow
                              key={m.motionId}
                              motion={m}
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

              <View style={styles.mt24}>
                <TextLink label={supplierCopy.common.signOut} onPress={onSignOut} tone="signOut" />
              </View>
            </Sheet>
          </View>
        </ScrollView>
      </PageFrame>
      {supplierCode ? (
        <BigCodeModal
          visible={bigOpen}
          title={bigTitle}
          code={supplierCode}
          how={supplierCopy.bigCode.how}
          closeLabel={supplierCopy.common.close}
          onClose={() => setBigOpen(false)}
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  pad: { flexGrow: 1, paddingHorizontal: space.screen, paddingBottom: space.lg },
  homeScroll: { flexGrow: 1 },
  mt4: { marginTop: space.xs },
  mt8: { marginTop: space.sm },
  mt12: { marginTop: space.row },
  mt16: { marginTop: space.md },
  mt24: { marginTop: space.lg },
  mt32: { marginTop: space.xl },
  mt40: { marginTop: space.s40 },
  mt48: { marginTop: space.xxl },
  mb12: { marginBottom: space.row },
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

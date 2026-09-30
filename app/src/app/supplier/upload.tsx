// 공급자 올리기 폼 — `/supplier/upload` (Phase 38 A-4 STEP 01 / 02 · A-5, D-04·D-07·D-08·D-09·D-14).
//
// 규칙은 전부 38-03 순수 함수 import(리뷰 R14) — 남은 필수 개수·서 있는 시작 차단·파일 검증·
// 요청 조립·프리필은 supplierForm, presign 오류 분기·업로드 결과 전이는 supplierRules.
// 이 파일에는 규칙을 다시 쓰지 않는다. 문구는 전부 supplierCopy(화면 리터럴 0), 색·간격은
// SupplierUi 프리미티브 → theme 토큰. 페이지는 Firestore 에 쓰지 않는다(선작성은 Lambda).
//
// 단계 = 라우트 param `step`(없음 = STEP 01, '2' = STEP 02). 브라우저 뒤로가기 = STEP 01.
// 두 단계가 다른 화면 인스턴스라 입력은 모듈 범위 세션 초안(sessionDraft)에 같이 적는다 —
// 뒤로 가도, 가이드를 보고 와도, 새로고침 전까지(세션 안) 입력이 남는다(UI-SPEC Decisions 11).
// 2026-09-30 배치 = 38-DESIGN.md(Figma 282:506) A-4 STEP 01 · STEP 02 · A-5.
// 2026-09-30 quick-260930-w9l(belle 폰 확인) — 콤보 체크·'이 동작에 대해' 3문항·학습 체크박스·
// 철회 문단 삭제, 필수 4 곳에 '필수' 표시, 선수 이름 = probe displayName(읽기 전용, 없으면 '다음'
// 차단), STEP 02 = '[필수] ○○ 동의 · 보기 >' 두 줄 + 필수 안내 + 학습 계약 안내, 5초~2분 · 1GB.

import * as ImagePicker from 'expo-image-picker';
import { useFocusEffect, useLocalSearchParams, useNavigation, useRouter } from 'expo-router';
import { signOut } from 'firebase/auth';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { PickErrorDialog } from '../../components/PickErrorDialog';
import {
  AllAgreeBox,
  BottomBar,
  CheckCard,
  CheckboxRow,
  FailurePanel,
  FieldLabel,
  FileCard,
  FieldError,
  Helper,
  NoticePill,
  OutlineButton,
  PageFrame,
  PrimaryCta,
  ProgressBar,
  ReadOnlyField,
  RequiredMark,
  Segment,
  SelectField,
  space,
  StepHeader,
  text,
  TextInput54,
  TextLink,
  TopBar,
  UploadSummary,
  VideoPreview,
  type SelectOption,
} from '../../components/SupplierUi';
import { supplierCopy } from '../../constants/supplierCopy';
import { ApiError, probeSupplier, requestReferenceUploadUrl, uploadToS3WithProgress } from '../../lib/api';
import { useAuthUser } from '../../lib/authUser';
import { auth } from '../../lib/firebase';
import type { PickFailure, PickFailureKind } from '../../lib/pickerFailure';
import { useReferenceMotions } from '../../lib/referenceMotions';
import { buildRequest, consentAllRequired, emptyConsent, emptyStep1, formatOf, parsePrefill, REFERENCE_NAME_MAX_LEN, remainingRequired, supplierNameMissing, validateFile, type ConsentState, type FileFailureKind, type Step1State } from '../../lib/supplierForm';
import { LEVEL_LABEL_KO, mapPresignFailure, uploadOutcomeNext, type UploadOutcome } from '../../lib/supplierRules';
import { readVideoDurationSec } from '../../lib/videoMeta';
import { colors } from '../../theme';
import type { ReferenceUploadUrlResponse, SkillLevel } from '../../types/analysis';

// 사전 선택의 마지막 옵션 = 새 이름 직접 입력(motionId 와 겹치지 않는 값).
const NEW_NAME_VALUE = '__new__';
const MB = 1024 * 1024;

type Draft = { step1: Step1State; consent: ConsentState };

// 선수 이름 = probe displayName(초대 때 이름, w9l 항목 10). loading = 아직 모름(막지 않는다),
// ok = 서버 답(name null = 이름 없는 공급자 → '다음' 차단), unknown = 네트워크 실패(막지 않는다 —
// 서버가 409 로 다시 막는다).
type SupplierNameState =
  | { kind: 'loading' }
  | { kind: 'ok'; name: string | null }
  | { kind: 'unknown' };

// 세션 초안 — 화면 인스턴스(STEP 01 / 02)가 공유한다. 새로고침하면 사라진다(의도).
let sessionDraft: Draft | null = null;

function paramOf(v: unknown): string {
  if (typeof v === 'string') return v;
  if (Array.isArray(v) && typeof v[0] === 'string') return v[0];
  return '';
}

function errorStatus(e: unknown): { status: number; code: string | null } {
  if (e instanceof ApiError) return { status: e.status, code: e.code };
  return { status: 0, code: null };
}

// 파일명이 없을 때(드묾) MIME 으로 확장자를 붙인다 — 형식 판정은 supplierForm.formatOf 가 한다.
function fileNameOf(asset: ImagePicker.ImagePickerAsset): string {
  if (asset.fileName) return asset.fileName;
  if (asset.mimeType === 'video/mp4') return 'video.mp4';
  if (asset.mimeType === 'video/quicktime') return 'video.mov';
  return asset.file?.name ?? '';
}

// 검증 다이얼로그(1:499) — supplierCopy.dialog 문구를 PickErrorDialog 형상으로. unreadable 은
// PickErrorDialog 의 processFailed 자리(같은 '읽는 중 문제' 의미).
type DialogKind = FileFailureKind | 'unreadable';
const DIALOG_KIND: Record<DialogKind, PickFailureKind> = {
  format: 'format',
  tooLarge: 'tooLarge',
  tooShort: 'tooShort',
  tooLong: 'tooLong',
  unreadable: 'processFailed',
};

function dialogFailure(kind: DialogKind): PickFailure {
  const c = supplierCopy.dialog[kind];
  return {
    kind: DIALOG_KIND[kind],
    title: c.title,
    lines: [...c.lines],
    primaryLabel: supplierCopy.form.sec4.repick,
    primaryAction: 'repick',
  };
}

// STEP 02 제출 뒤 화면. form = 동의 화면 그대로(presigning 은 CTA 만 막는다),
// uploading = A-5 진행 패널, failed = 실패 패널(presign 5xx 또는 PUT 실패 — 본문만 다르다).
type SubmitPhase =
  | { kind: 'form' }
  | { kind: 'presigning' }
  | { kind: 'uploading'; pct: number }
  | { kind: 'failed'; body: string };

export default function SupplierUpload() {
  const router = useRouter();
  const params = useLocalSearchParams();
  const { user, isGuest, ready } = useAuthUser();
  const signedIn = !!user && !isGuest;
  const uid = signedIn ? user.uid : null;

  // ── 초기 상태: 다시 올리기 프리필(name 이 있음)이면 프리필로 새 초안, 아니면 세션 초안 ──
  const [step1, setStep1] = useState<Step1State>(() => {
    if (paramOf(params.name)) {
      sessionDraft = { step1: parsePrefill(params), consent: emptyConsent() };
    }
    return sessionDraft?.step1 ?? emptyStep1();
  });

  const update = (patch: Partial<Step1State>) => {
    setStep1((prev) => {
      const next = { ...prev, ...patch };
      sessionDraft = { step1: next, consent: sessionDraft?.consent ?? emptyConsent() };
      return next;
    });
  };

  const [consent, setConsent] = useState<ConsentState>(() => sessionDraft?.consent ?? emptyConsent());
  const updateConsent = (patch: Partial<ConsentState>) => {
    setConsent((prev) => {
      const next = { ...prev, ...patch };
      sessionDraft = { step1: sessionDraft?.step1 ?? step1, consent: next };
      return next;
    });
  };

  // 다른 인스턴스(STEP 02 · 가이드 다녀옴 · 올리기 성공 뒤 초기화)가 바꾼 초안을 포커스 때 다시 읽는다.
  useFocusEffect(
    useCallback(() => {
      if (!sessionDraft) return;
      setStep1(sessionDraft.step1);
      setConsent(sessionDraft.consent);
    }, []),
  );

  // ── 인증 가드: 로그인 전 · 게스트면 /supplier(A-1). 화이트리스트 밖(403) · 세션 만료(401)도
  //    /supplier 가 A-2 / A-1 을 보여준다. 네트워크 실패는 폼을 막지 않는다 — 제출 때 서버가
  //    같은 화이트리스트를 다시 본다(T-38-11-1).
  useEffect(() => {
    if (ready && !signedIn) router.replace('/supplier');
  }, [ready, signedIn, router]);
  const [supplierName, setSupplierName] = useState<SupplierNameState>({ kind: 'loading' });
  useEffect(() => {
    if (!uid) return;
    let cancelled = false;
    probeSupplier()
      .then((res) => {
        if (cancelled) return;
        // 옛 서버 응답엔 displayName 이 없을 수 있다 — `?? null`(contract.md §2).
        const name = typeof res.displayName === 'string' ? res.displayName.trim() : '';
        setSupplierName({ kind: 'ok', name: name || null });
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        const kind = mapPresignFailure(errorStatus(e));
        if (kind === 'notInvited' || kind === 'sessionExpired') router.replace('/supplier');
        else setSupplierName({ kind: 'unknown' });
      });
    return () => {
      cancelled = true;
    };
  }, [uid, router]);
  // 이름 없는 공급자 = 서버 답을 받았는데 비었을 때만(모르는 동안은 막지 않는다).
  const nameBlocked = supplierName.kind === 'ok' && supplierNameMissing(supplierName.name);

  // ── 동작 이름 사전 = 활성 기준 동작 이름 중복 제거(값 = motionId) + 새 이름 ──
  const { motions } = useReferenceMotions();
  const nameOptions = useMemo<SelectOption[]>(() => {
    const seen = new Set<string>();
    const list: SelectOption[] = [];
    for (const m of motions) {
      if (seen.has(m.name)) continue;
      seen.add(m.name);
      list.push({ value: m.motionId, label: m.name });
    }
    const choice = step1.nameChoice;
    if (choice?.kind === 'dict' && !list.some((o) => o.value === choice.motionId)) {
      list.unshift({ value: choice.motionId, label: choice.name });
    }
    list.push({ value: NEW_NAME_VALUE, label: supplierCopy.form.sec2.name.newOption });
    return list;
  }, [motions, step1.nameChoice]);

  const selectValue =
    step1.nameChoice == null ? null : step1.nameChoice.kind === 'dict' ? step1.nameChoice.motionId : NEW_NAME_VALUE;

  const onSelectName = (value: string) => {
    if (value === NEW_NAME_VALUE) {
      update({ nameChoice: { kind: 'new', name: step1.nameChoice?.kind === 'new' ? step1.nameChoice.name : '' } });
      return;
    }
    const opt = nameOptions.find((o) => o.value === value);
    if (opt) update({ nameChoice: { kind: 'dict', motionId: opt.value, name: opt.label } });
  };

  // ── 파일 선택 → 길이 읽기 → validateFile(38-03) → 다이얼로그 또는 미리보기 ──
  const [picking, setPicking] = useState(false);
  const [dialog, setDialog] = useState<PickFailure | null>(null);

  const pickFile = async () => {
    if (picking) return;
    setPicking(true);
    try {
      let result: ImagePicker.ImagePickerResult;
      try {
        result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['videos'] });
      } catch {
        setDialog(dialogFailure('unreadable'));
        return;
      }
      const asset = result.canceled ? null : result.assets?.[0];
      if (!asset) return;
      const name = fileNameOf(asset);
      const webFile = asset.file ?? null;
      const sizeBytes = asset.fileSize ?? webFile?.size ?? 0;
      // metadata 를 못 읽으면 null = 통과(fail-open) — 서버가 길이를 2차로 본다(D-14).
      const durationSec = await readVideoDurationSec(webFile ?? asset.uri);
      const kind = validateFile({ name, sizeBytes, durationSec });
      const format = formatOf(name);
      if (kind || !format) {
        setDialog(dialogFailure(kind ?? 'format'));
        return;
      }
      update({
        file: { name, sizeBytes, durationSec, format, uri: asset.uri, blob: webFile ?? undefined },
      });
    } catch {
      setDialog(dialogFailure('unreadable'));
    } finally {
      setPicking(false);
    }
  };

  // ── 남은 필수 · 이름 차단 · 인라인 오류 ──
  const count = remainingRequired(step1);
  const requiredMark = supplierCopy.form.requiredTag;
  const [showErrors, setShowErrors] = useState(false);
  const err = (missing: boolean, message: string) => (showErrors && missing ? message : null);
  const nameMissing = !step1.nameChoice || step1.nameChoice.name.trim().length === 0;

  // 뒤로 = STEP 02 → STEP 01(입력 유지), STEP 01 → 홈. 기록이 없으면(직접 URL) 같은 곳으로 replace.
  const goBack = () => {
    if (router.canGoBack()) router.back();
    else router.replace(paramOf(params.step) === '2' ? '/supplier/upload' : '/supplier');
  };

  const onNext = () => {
    router.push({ pathname: '/supplier/upload', params: { step: '2' } });
  };

  // ── STEP 02 · 제출 · 업로드 (A-4 STEP 02 · A-5 · A-7) ──
  const wantsStep2 = paramOf(params.step) === '2';
  // 직접 URL 로 step=2 에 왔는데 STEP 01 이 비었으면 STEP 01 을 보여준다(buildRequest 가 null 인 상태).
  const step = wantsStep2 && count === 0 && !nameBlocked ? 2 : 1;
  const [submitPhase, setSubmitPhase] = useState<SubmitPhase>({ kind: 'form' });
  const [inlineError, setInlineError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const uploadingRef = useRef(false);
  const uploading = submitPhase.kind === 'uploading';

  // 업로드 중 화면 전환 차단 — 앱 안 뒤로(beforeRemove) + 웹 탭 닫기·새로고침(beforeunload).
  const navigation = useNavigation();
  useEffect(
    () =>
      navigation.addListener('beforeRemove', (e) => {
        if (uploadingRef.current) e.preventDefault();
      }),
    [navigation],
  );
  useEffect(() => {
    if (!uploading || Platform.OS !== 'web' || typeof window === 'undefined') return;
    const warn = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [uploading]);

  // 이 페이지는 Firestore 에 쓰지 않는다 — 앱 분석 경로(loading.tsx)는 presign 뒤 앱이
  // users/{uid}/analyses doc 을 만들지만, 공급자 경로는 upload-url Lambda 가 reference/{refId}
  // 를 registering 으로 선작성한다(규칙 write false, T-38-11-5).
  const submit = async () => {
    const f = step1.file;
    if (!f) return;
    const req = buildRequest(step1, consent, f);
    if (!req) return;
    setInlineError(null);
    setSubmitPhase({ kind: 'presigning' });

    let res: ReferenceUploadUrlResponse;
    try {
      res = await requestReferenceUploadUrl(req);
    } catch (e) {
      const kind = mapPresignFailure(errorStatus(e));
      if (kind === 'sessionExpired') {
        // 401 → A-1 + form.sessionExpired 문구(홈이 expired param 으로 띄운다). replace 먼저 —
        // signOut 이 먼저면 인증 가드가 param 없이 /supplier 로 보낸다.
        router.replace({ pathname: '/supplier', params: { expired: '1' } });
        void signOut(auth);
        return;
      }
      if (kind === 'notInvited') {
        router.replace('/supplier'); // 403 → A-2 는 홈의 probe 가 보여준다.
        return;
      }
      if (kind === 'offline') {
        setSubmitPhase({ kind: 'form' });
        setInlineError(supplierCopy.common.offline);
        return;
      }
      setSubmitPhase({ kind: 'failed', body: supplierCopy.form.presignFail });
      return;
    }

    const controller = new AbortController();
    abortRef.current = controller;
    uploadingRef.current = true;
    setSubmitPhase({ kind: 'uploading', pct: 0 });
    let outcome: UploadOutcome;
    try {
      const body = f.blob instanceof Blob ? f.blob : await (await fetch(f.uri ?? '')).blob();
      await uploadToS3WithProgress(res.uploadUrl, body, f.format, {
        onProgress: (pct) => setSubmitPhase({ kind: 'uploading', pct }),
        signal: controller.signal,
      });
      outcome = 'ok';
    } catch {
      outcome = controller.signal.aborted ? 'aborted' : 'failed';
    } finally {
      uploadingRef.current = false;
      abortRef.current = null;
    }

    switch (uploadOutcomeNext(outcome)) {
      case 'home':
        // 다음 동작을 바로 올릴 수 있게 초안은 비우되 촬영 전 체크 확인은 세션 안에서 유지(Decisions 11).
        sessionDraft = {
          step1: { ...emptyStep1(), checkConfirmed: step1.checkConfirmed },
          consent: emptyConsent(),
        };
        // 토스트 form.uploaded.toast 와 새 행 강조는 홈이 justUploaded 로 띄운다.
        router.replace({ pathname: '/supplier', params: { justUploaded: res.refId } });
        return;
      case 'step2':
        // 올리기 취소 → 동의 화면 그대로(입력 유지). 선작성된 registering doc 은
        // uploadExpiresAt 뒤 requeue --sweep-expired 가 expired 로 닫고 홈이 만료 행으로 보여 준다(R4).
        setSubmitPhase({ kind: 'form' });
        return;
      case 'failPanel':
        setSubmitPhase({ kind: 'failed', body: supplierCopy.form.uploadFail.body });
        return;
    }
  };

  // 다시 올리기 = 새 presign 부터(= 새 refId). 옛 registering doc 은 900초 뒤 requeue 스윕이
  // expired 로 닫는다 — 같은 refId 로 다시 PUT 하지 않는다(리뷰 R4, T-38-11-6).
  const retrySubmit = () => {
    setSubmitPhase({ kind: 'form' });
    void submit();
  };

  const cancelUpload = () => {
    abortRef.current?.abort();
  };

  const toggleAllRequired = () => {
    // 전체 동의 = 필수 2(초상·성명 / 영상 이용). 학습은 체크박스가 아니다(공급자 계약, w9l 항목 5·11).
    const on = !consentAllRequired(consent);
    updateConsent({ portrait: on, usage: on });
  };
  const openConsentGuide = () => router.push({ pathname: '/supplier/guide', params: { section: 's5' } });
  const levelOptions = (Object.keys(supplierCopy.form.sec2.level.options) as SkillLevel[]).map((k) => ({
    value: k,
    label: supplierCopy.form.sec2.level.options[k],
  }));
  // 하단 바가 화면 아래에 떠 있어(absolute) 그 높이만큼 스크롤 끝에 여백을 더한다.
  const [barHeight, setBarHeight] = useState(0);
  const scrollPad = [styles.pad, { paddingBottom: space.lg + barHeight }];

  const file = step1.file;
  const meta =
    file && file.durationSec != null
      ? supplierCopy.form.sec4.meta
          .replace('{durationSec}', file.durationSec.toFixed(1))
          .replace('{sizeMB}', (file.sizeBytes / MB).toFixed(1))
      : null;

  if (!ready || !signedIn) {
    return <SafeAreaView style={styles.page} />;
  }

  if (step === 2 && submitPhase.kind === 'uploading') {
    // 38-DESIGN A-5 — 뒤로 없음. 제목 → 24 → 파일 요약 → 32 → `올리는 중` / `{pct}%` → 트랙 → 12 →
    // keepOpen → 32 → 가운데 `올리기 취소`.
    const u = supplierCopy.form.uploading;
    const summaryTitle = u.summaryTitle
      .replace('{name}', step1.nameChoice?.name.trim() ?? '')
      .replace('{level}', step1.level ? LEVEL_LABEL_KO[step1.level] : '');
    const fileName = file?.name ?? '';
    const summaryMeta = meta ? u.summaryMeta.replace('{file}', fileName).replace('{meta}', meta) : fileName;
    return (
      <SafeAreaView style={styles.page} edges={['top', 'bottom']}>
        <PageFrame>
          <View style={[styles.pad, styles.uploadingTop]}>
            <Text style={text.display} accessibilityRole="header">
              {u.title}
            </Text>
            <View style={styles.mt24}>
              <UploadSummary uri={file?.uri ?? null} title={summaryTitle} meta={summaryMeta} />
            </View>
            <View style={styles.mt32}>
              <ProgressBar
                pct={submitPhase.pct}
                label={u.progressLabel}
                valueText={u.pct.replace('{pct}', String(submitPhase.pct))}
              />
            </View>
            <Text style={[text.aux, styles.mt12]}>{u.keepOpen}</Text>
            <View style={styles.mt32}>
              <TextLink label={supplierCopy.common.cancel} onPress={cancelUpload} tone="cancel" center />
            </View>
          </View>
        </PageFrame>
      </SafeAreaView>
    );
  }

  if (step === 2 && submitPhase.kind === 'failed') {
    return (
      <SafeAreaView style={styles.page} edges={['top', 'bottom']}>
        <PageFrame>
          <ScrollView contentContainerStyle={styles.pad}>
            <TopBar onBack={() => setSubmitPhase({ kind: 'form' })} backLabel={supplierCopy.common.back} />
            {/* 1:428 구조, TIP 카드 없음(UI-SPEC A-5). presign 5xx 는 form.presignFail 본문. */}
            <FailurePanel
              title={supplierCopy.form.uploadFail.title}
              body={submitPhase.body}
              reuploadLabel={supplierCopy.form.uploadFail.retry}
              onReupload={retrySubmit}
              backLabel={supplierCopy.form.uploadFail.home}
              onBack={() => router.replace('/supplier')}
            />
          </ScrollView>
        </PageFrame>
      </SafeAreaView>
    );
  }

  if (step === 2) {
    const missingConsents = [consent.portrait, consent.usage].filter((v) => !v).length;
    const allRequired = consentAllRequired(consent);
    const presigning = submitPhase.kind === 'presigning';
    const required = { text: supplierCopy.form.sec5.tagRequired, required: true };
    return (
      <SafeAreaView style={styles.page} edges={['top']}>
        <PageFrame>
          <ScrollView contentContainerStyle={scrollPad}>
            <TopBar onBack={goBack} backLabel={supplierCopy.common.back} />
            <StepHeader
              step={supplierCopy.form.step2.label}
              title={supplierCopy.form.step2.title}
              current={2}
            />
            <View style={styles.mt32}>
              <AllAgreeBox
                label={supplierCopy.form.sec5.all}
                hint={supplierCopy.form.sec5.allHint}
                checked={allRequired}
                onToggle={toggleAllRequired}
              />
              {/* w9l 항목 4 — '[필수] ○○ 동의 · 보기 >'. 보기 = 가이드 s5(권리와 동의). */}
              <View style={styles.mt8}>
                <CheckboxRow inset label={supplierCopy.form.sec5.portrait} tag={required} checked={consent.portrait} onToggle={() => updateConsent({ portrait: !consent.portrait })} onChevron={openConsentGuide} linkText={supplierCopy.form.sec5.view} />
                <CheckboxRow inset label={supplierCopy.form.sec5.usage} tag={required} checked={consent.usage} onToggle={() => updateConsent({ usage: !consent.usage })} onChevron={openConsentGuide} linkText={supplierCopy.form.sec5.view} />
              </View>
              <FieldError message={showErrors && !allRequired ? supplierCopy.form.sec5.error : null} />
              <Text style={[text.aux, styles.mt16]}>{supplierCopy.form.sec5.requiredNote}</Text>
              {/* w9l 항목 5+11 — 학습은 체크박스가 아니라 공급자 계약 근거. 안내 한 줄(보조 글자). */}
              <Text style={[text.caption13, styles.mt8]}>{supplierCopy.form.sec5.trainingNotice}</Text>
            </View>
            {inlineError ? (
              <View style={styles.mt24}>
                <FieldError message={inlineError} />
                <View style={styles.mt8}>
                  <OutlineButton label={supplierCopy.common.retry} onPress={() => void submit()} />
                </View>
              </View>
            ) : null}
          </ScrollView>
          <BottomBar
            hint={missingConsents > 0 ? supplierCopy.form.remaining.replace('{n}', String(missingConsents)) : null}
            onHeight={setBarHeight}
          >
            <PrimaryCta
              label={supplierCopy.form.submit}
              onPress={() => void submit()}
              disabled={!allRequired || presigning}
              onDisabledPress={presigning ? undefined : () => setShowErrors(true)}
            />
          </BottomBar>
        </PageFrame>
      </SafeAreaView>
    );
  }

  const bottomHint =
    count > 0
      ? supplierCopy.form.remaining.replace('{n}', String(count))
      : nameBlocked
        ? supplierCopy.form.sec2.athlete.missing
        : null;

  return (
    <SafeAreaView style={styles.page} edges={['top']}>
      <PageFrame>
        <ScrollView contentContainerStyle={scrollPad} keyboardShouldPersistTaps="handled">
          <TopBar onBack={goBack} backLabel={supplierCopy.common.back} />
          <StepHeader
            step={supplierCopy.form.step1.label}
            title={supplierCopy.form.step1.title}
            current={1}
          />

          {/* ① 촬영 전 체크 4 + 확인 1 — 가이드 링크는 체크 행 안(38-DESIGN A-4 ①, Decisions 11 세션 유지) */}
          <View style={styles.mt32}>
            <CheckCard
              title={supplierCopy.form.sec1.title}
              requiredMark={requiredMark}
              items={supplierCopy.form.sec1.items}
              confirmLabel={supplierCopy.form.sec1.confirm}
              checked={step1.checkConfirmed}
              onToggle={() => update({ checkConfirmed: !step1.checkConfirmed })}
              linkLabel={supplierCopy.form.sec1.guideLink}
              onLink={() => router.push('/supplier/guide')}
            />
            <FieldError message={err(!step1.checkConfirmed, supplierCopy.form.sec1.error)} />
          </View>

          {/* ② 동작 정보 — 섹션 제목·외곽 카드 없음(페이지 제목과 겹쳐서 뺐다, 38-DESIGN A-4 ②) */}
          <View style={styles.mt40}>
            <SelectField
              label={supplierCopy.form.sec2.name.label}
              requiredMark={requiredMark}
              placeholder={supplierCopy.form.sec2.name.placeholder}
              options={nameOptions}
              value={selectValue}
              onChange={onSelectName}
              error={step1.nameChoice?.kind === 'new' ? null : err(nameMissing, supplierCopy.form.sec2.name.error)}
            />
            {step1.nameChoice?.kind === 'new' ? (
              <View style={styles.mt8}>
                <TextInput54
                  value={step1.nameChoice.name}
                  onChangeText={(v) => update({ nameChoice: { kind: 'new', name: v } })}
                  placeholder={supplierCopy.form.sec2.name.newPlaceholder}
                  maxLength={REFERENCE_NAME_MAX_LEN}
                  error={err(nameMissing, supplierCopy.form.sec2.name.error)}
                />
              </View>
            ) : null}
            {/* 리뷰 R7 — 이름은 등록 정보로 보관, 채점은 지금 기본 비교 방식(techniqueRefId 소비 배선 없음) */}
            <Helper>{supplierCopy.form.sec2.name.helper}</Helper>
            {/* w9l 항목 10 — 선수 이름은 초대 때 이름(읽기 전용). 없으면 안내 + '다음' 차단. */}
            <View style={styles.mt24}>
              <ReadOnlyField
                label={supplierCopy.form.sec2.athlete.label}
                value={supplierName.kind === 'ok' ? supplierName.name : null}
                pending={supplierName.kind !== 'ok'}
                missingMessage={supplierCopy.form.sec2.athlete.missing}
              />
              {nameBlocked ? null : <Helper>{supplierCopy.form.sec2.athlete.helper}</Helper>}
            </View>
            <View style={styles.mt24}>
              <FieldLabel label={supplierCopy.form.sec2.level.label} requiredMark={requiredMark} />
              <Segment
                label={supplierCopy.form.sec2.level.label}
                options={levelOptions}
                value={step1.level}
                onChange={(level) => update({ level })}
              />
              <FieldError message={err(step1.level == null, supplierCopy.form.sec2.level.error)} />
              <Helper>{supplierCopy.form.sec2.level.helper}</Helper>
            </View>
          </View>

          {/* ④ 영상 파일 — 안내 알약이 파일 카드 위(38-DESIGN A-4 ④) */}
          <View style={styles.mt40}>
            <View style={styles.titleRow}>
              <Text style={text.heading} accessibilityRole="header">
                {supplierCopy.form.sec4.title}
              </Text>
              <RequiredMark label={requiredMark} />
            </View>
            <View style={styles.mt16}>
              <NoticePill lines={supplierCopy.form.sec4.pill} />
            </View>
            {file ? (
              <View style={styles.mt12}>
                {file.uri ? <VideoPreview uri={file.uri} /> : null}
                <View style={[styles.metaRow, styles.mt12]}>
                  <Text style={text.labelBold}>{file.name}</Text>
                  {meta ? <Text style={[text.label, text.mid]}>{meta}</Text> : null}
                </View>
                <Text style={[text.aux, styles.mt4]}>{supplierCopy.form.sec4.previewHint}</Text>
                <View style={styles.mt12}>
                  <OutlineButton label={supplierCopy.form.sec4.repick} onPress={pickFile} disabled={picking} />
                </View>
              </View>
            ) : (
              <View style={styles.mt12}>
                <FileCard
                  title={supplierCopy.form.sec4.card.title}
                  sub={supplierCopy.form.sec4.card.sub}
                  onPress={pickFile}
                  disabled={picking}
                />
                <FieldError message={err(true, supplierCopy.form.sec4.err.required)} />
              </View>
            )}
          </View>
        </ScrollView>
        <BottomBar hint={bottomHint} onHeight={setBarHeight}>
          <PrimaryCta
            label={supplierCopy.form.next}
            onPress={onNext}
            disabled={count > 0 || nameBlocked}
            onDisabledPress={() => setShowErrors(true)}
          />
        </BottomBar>
      </PageFrame>
      <PickErrorDialog
        failure={dialog}
        onClose={() => setDialog(null)}
        onAction={() => {
          setDialog(null);
          void pickFile();
        }}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  pad: { flexGrow: 1, paddingHorizontal: space.screen, paddingBottom: space.lg },
  // A-5 내용 y≈120 = safe-area 59 + 60(근사).
  uploadingTop: { paddingTop: space.xxl + space.row },
  mt4: { marginTop: space.xs },
  mt8: { marginTop: space.sm },
  mt12: { marginTop: space.row },
  mt16: { marginTop: space.md },
  mt24: { marginTop: space.lg },
  mt32: { marginTop: space.xl },
  mt40: { marginTop: space.s40 },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: space.s6 },
  metaRow: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'baseline', columnGap: space.sm },
});

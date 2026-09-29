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

import * as ImagePicker from 'expo-image-picker';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { PickErrorDialog } from '../../components/PickErrorDialog';
import {
  BottomBar,
  Card,
  CheckboxRow,
  FileCard,
  FieldError,
  Helper,
  NoticePill,
  OutlineButton,
  PageFrame,
  PrimaryCta,
  Segment,
  SelectField,
  space,
  StepHeader,
  text,
  TextInput54,
  TextLink,
  TipCard,
  TopBar,
  VideoPreview,
  type SelectOption,
} from '../../components/SupplierUi';
import { supplierCopy } from '../../constants/supplierCopy';
import { ApiError, probeSupplier } from '../../lib/api';
import { displayNameOf, useAuthUser } from '../../lib/authUser';
import type { PickFailure, PickFailureKind } from '../../lib/pickerFailure';
import { useReferenceMotions } from '../../lib/referenceMotions';
import { emptyStep1, formatOf, parsePrefill, REFERENCE_NAME_MAX_LEN, remainingRequired, validateFile, type ConsentState, type FileFailureKind, type Step1State, type YesNo } from '../../lib/supplierForm';
import { mapPresignFailure } from '../../lib/supplierRules';
import { readVideoDurationSec } from '../../lib/videoMeta';
import { colors } from '../../theme';
import type { SkillLevel } from '../../types/analysis';

// 사전 선택의 마지막 옵션 = 새 이름 직접 입력(motionId 와 겹치지 않는 값).
const NEW_NAME_VALUE = '__new__';
const MB = 1024 * 1024;

type Draft = { step1: Step1State; consent: ConsentState };

function emptyConsent(): ConsentState {
  return { portrait: false, usage: false, silent: false, training: false };
}

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
  const athleteTouched = useRef(step1.athleteName.length > 0);

  const update = (patch: Partial<Step1State>) => {
    setStep1((prev) => {
      const next = { ...prev, ...patch };
      sessionDraft = { step1: next, consent: sessionDraft?.consent ?? emptyConsent() };
      return next;
    });
  };

  // ── 인증 가드: 로그인 전 · 게스트면 /supplier(A-1). 화이트리스트 밖(403) · 세션 만료(401)도
  //    /supplier 가 A-2 / A-1 을 보여준다. 네트워크 실패는 폼을 막지 않는다 — 제출 때 서버가
  //    같은 화이트리스트를 다시 본다(T-38-11-1).
  useEffect(() => {
    if (ready && !signedIn) router.replace('/supplier');
  }, [ready, signedIn, router]);
  useEffect(() => {
    if (!uid) return;
    let cancelled = false;
    probeSupplier().catch((e: unknown) => {
      if (cancelled) return;
      const kind = mapPresignFailure(errorStatus(e));
      if (kind === 'forbidden' || kind === 'sessionExpired') router.replace('/supplier');
    });
    return () => {
      cancelled = true;
    };
  }, [uid, router]);

  // 선수 이름 프리필 = Google 표시 이름(사람이 고치기 전까지만).
  useEffect(() => {
    if (athleteTouched.current || !user) return;
    const name = displayNameOf(user);
    if (name) update({ athleteName: name });
    // update 는 매 렌더 새 함수라 deps 에서 뺀다 — user 가 바뀔 때만 채운다.
  }, [user]);

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
      const kind = validateFile({ name, sizeBytes, durationSec, isCombo: step1.isCombo });
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

  // 콤보를 바꾸면 길이 상한(30 ↔ 60)이 바뀐다 — 이미 고른 파일을 새 상한으로 다시 본다.
  const onToggleCombo = () => {
    const isCombo = !step1.isCombo;
    const f = step1.file;
    if (f) {
      const kind = validateFile({ name: f.name, sizeBytes: f.sizeBytes, durationSec: f.durationSec, isCombo });
      if (kind) {
        update({ isCombo, file: null });
        setDialog(dialogFailure(kind));
        return;
      }
    }
    update({ isCombo });
  };

  // ── 남은 필수 · 차단 · 인라인 오류 ──
  const { count, blocked } = remainingRequired(step1);
  const [showErrors, setShowErrors] = useState(false);
  const err = (missing: boolean, message: string) => (showErrors && missing ? message : null);
  const nameMissing = !step1.nameChoice || step1.nameChoice.name.trim().length === 0;

  const goBack = () => {
    if (router.canGoBack()) router.back();
    else router.replace('/supplier');
  };

  const onNext = () => {
    router.push({ pathname: '/supplier/upload', params: { step: '2' } });
  };

  const yesNo: { value: YesNo; label: string }[] = [
    { value: 'yes', label: supplierCopy.form.sec3.yes },
    { value: 'no', label: supplierCopy.form.sec3.no },
  ];
  const levelOptions = (Object.keys(supplierCopy.form.sec2.level.options) as SkillLevel[]).map((k) => ({
    value: k,
    label: supplierCopy.form.sec2.level.options[k],
  }));
  const declarations = [
    { key: 'isSplit', copy: supplierCopy.form.sec3.split },
    { key: 'hasHold', copy: supplierCopy.form.sec3.hold },
    { key: 'standingStart', copy: supplierCopy.form.sec3.stand },
  ] as const;

  if (!ready || !signedIn) {
    return <SafeAreaView style={styles.page} />;
  }

  const file = step1.file;
  const meta =
    file && file.durationSec != null
      ? supplierCopy.form.sec4.meta
          .replace('{durationSec}', file.durationSec.toFixed(1))
          .replace('{sizeMB}', (file.sizeBytes / MB).toFixed(1))
      : null;
  const bottomHint =
    count > 0
      ? supplierCopy.form.remaining.replace('{n}', String(count))
      : blocked
        ? supplierCopy.form.sec3.stand.blocked
        : null;

  return (
    <SafeAreaView style={styles.page} edges={['top']}>
      <PageFrame>
        <ScrollView contentContainerStyle={styles.pad} keyboardShouldPersistTaps="handled">
          <TopBar onBack={goBack} backLabel={supplierCopy.common.back} />
          <View style={styles.mt8}>
            <StepHeader step={supplierCopy.form.step1.label} title={supplierCopy.form.step1.title} />
          </View>

          {/* ① 촬영 전 체크 5 + 확인 1 (UI-SPEC Decisions 11 — 세션 안에서 유지) */}
          <View style={styles.section}>
            <TipCard head={supplierCopy.form.sec1.title} lines={supplierCopy.form.sec1.items} />
            <View style={styles.mt12}>
              <CheckboxRow
                label={supplierCopy.form.sec1.confirm}
                checked={step1.checkConfirmed}
                onToggle={() => update({ checkConfirmed: !step1.checkConfirmed })}
              />
            </View>
            <FieldError message={err(!step1.checkConfirmed, supplierCopy.form.sec1.error)} />
            <TextLink
              label={supplierCopy.form.sec1.guideLink}
              onPress={() => router.push('/supplier/guide')}
              tone="go"
            />
          </View>

          {/* ② 동작 정보 */}
          <Card style={styles.section}>
            <Text style={text.heading} accessibilityRole="header">
              {supplierCopy.form.sec2.title}
            </Text>
            <View style={styles.mt16}>
              <SelectField
                label={supplierCopy.form.sec2.name.label}
                placeholder={supplierCopy.form.sec2.name.placeholder}
                options={nameOptions}
                value={selectValue}
                onChange={onSelectName}
                error={step1.nameChoice?.kind === 'new' ? null : err(nameMissing, supplierCopy.form.sec2.name.error)}
              />
            </View>
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
            {/* 리뷰 R7 — 이름·선언은 등록 정보로 보관, 채점은 지금 기본 비교 방식(techniqueRefId 소비 배선 없음) */}
            <Helper>{supplierCopy.form.sec2.name.helper}</Helper>
            <View style={styles.mt12}>
              <CheckboxRow
                label={supplierCopy.form.sec2.combo.label}
                tag={{ text: supplierCopy.form.sec5.tagOptional, required: false }}
                checked={step1.isCombo}
                onToggle={onToggleCombo}
              />
            </View>
            <View style={styles.mt16}>
              <TextInput54
                label={supplierCopy.form.sec2.athlete.label}
                value={step1.athleteName}
                onChangeText={(v) => {
                  athleteTouched.current = true;
                  update({ athleteName: v });
                }}
                error={err(step1.athleteName.trim().length === 0, supplierCopy.form.sec2.athlete.error)}
              />
              <Helper>{supplierCopy.form.sec2.athlete.helper}</Helper>
            </View>
            <View style={styles.mt16}>
              <Text style={[text.label, styles.mb8]}>{supplierCopy.form.sec2.level.label}</Text>
              <Segment
                label={supplierCopy.form.sec2.level.label}
                options={levelOptions}
                value={step1.level}
                onChange={(level) => update({ level })}
              />
              <FieldError message={err(step1.level == null, supplierCopy.form.sec2.level.error)} />
              <Helper>{supplierCopy.form.sec2.level.helper}</Helper>
            </View>
          </Card>

          {/* ③ 선언 3 (D-07 · D-09 서 있는 시작 아니오 = 제출 차단) */}
          <Card style={styles.section}>
            <Text style={text.heading} accessibilityRole="header">
              {supplierCopy.form.sec3.title}
            </Text>
            {declarations.map(({ key, copy }) => (
              <View key={key} style={styles.mt16}>
                <Text style={[text.label, styles.mb8]}>{copy.q}</Text>
                <Segment label={copy.q} options={yesNo} value={step1[key]} onChange={(v) => update({ [key]: v } as Partial<Step1State>)} />
                <FieldError message={err(step1[key] == null, supplierCopy.form.sec3.error)} />
                {key === 'standingStart' && step1.standingStart === 'no' ? (
                  <FieldError message={supplierCopy.form.sec3.stand.blocked} />
                ) : null}
                <Helper>{copy.helper}</Helper>
              </View>
            ))}
          </Card>

          {/* ④ 영상 파일 (1:407 카드 · 1:399 알약 — 알약 문구는 정정본 form.sec4.pill) */}
          <Card style={styles.section}>
            <Text style={text.heading} accessibilityRole="header">
              {supplierCopy.form.sec4.title}
            </Text>
            {file ? (
              <View style={[styles.mt16, styles.gap8]}>
                {file.uri ? <VideoPreview uri={file.uri} /> : null}
                {meta ? <Text style={text.label}>{meta}</Text> : null}
                <Text style={[text.label, text.mid]}>{supplierCopy.form.sec4.previewHint}</Text>
                <OutlineButton label={supplierCopy.form.sec4.repick} onPress={pickFile} disabled={picking} />
              </View>
            ) : (
              <View style={styles.mt16}>
                <FileCard
                  title={supplierCopy.form.sec4.card.title}
                  sub={supplierCopy.form.sec4.card.sub}
                  onPress={pickFile}
                  disabled={picking}
                />
                <FieldError message={err(true, supplierCopy.form.sec4.err.required)} />
              </View>
            )}
            <View style={styles.mt12}>
              <NoticePill lines={supplierCopy.form.sec4.pill} />
            </View>
          </Card>
        </ScrollView>
        <BottomBar hint={bottomHint}>
          <PrimaryCta
            label={supplierCopy.form.next}
            onPress={onNext}
            disabled={count > 0 || blocked}
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
  section: { marginTop: space.lg },
  mt8: { marginTop: space.sm },
  mt12: { marginTop: space.row },
  mt16: { marginTop: space.md },
  mb8: { marginBottom: space.sm },
  gap8: { gap: space.sm },
});

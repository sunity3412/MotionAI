// 자가입력 신체 프로필 공유 폼 (Phase 3, Plan 03-02).
//
// 5필드: 키(cm) · 몸무게(kg) · 경력 · 통증부위(다중) · 우세손.
// RN core primitive(TextInput/Pressable)만 사용 — 신규 npm 패키지 0 (EAS Build 리스크 0).
// 03-01 의 saveBodyProfile 로 부분/전체 merge-write (빈 필드는 null/[] 로 graceful, D-06).
//
// [R6 keyboard-safe] 앱의 첫 실제 TextInput 화면이라 KeyboardAvoidingView + ScrollView
// 로 감싼다. 작은 화면(iPhone SE급)에서 키보드가 떠도 저장 CTA 가 가려지지 않고
// 스크롤로 도달·탭 가능해야 한다. iOS number-pad 는 done 키가 없으므로 폼 전체를
// Pressable(Keyboard.dismiss) 로 감싸 빈 영역 탭으로 키보드를 닫는다.
//
// 토큰만 사용 (하드코딩 색/spacing/fontSize 금지 — app/CLAUDE.md / design.md §5-3·§5-3-1).

import { useState } from 'react';
import {
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { saveBodyProfile, savePainAreaNote } from '../lib/bodyProfile';
import type {
  BodyProfile,
  DominantHand,
  ExperienceLevel,
  PainArea,
} from '../types/analysis';
import {
  DOMINANT_HAND_LABEL_KO,
  EXPERIENCE_LABEL_KO,
  PAIN_AREA_LABEL_KO,
} from '../types/analysis';
import { colors, layout, radius, spacing, typography } from '../theme';

// height/weight 합리적 범위 (bodyProfile.ts / models.normalize_body_profile 와 동일 — 이중 검증).
const HEIGHT_CM_MIN = 90;
const HEIGHT_CM_MAX = 250;
const WEIGHT_KG_MIN = 25;
const WEIGHT_KG_MAX = 200;

// [WR-03] 표시 순서만 여기서 정하고 라벨은 analysis.ts 단일 출처(*_LABEL_KO)에서
// 끌어 쓴다 — union 멤버 추가 시 라벨 누락이 빌드에서 막힌다. value 배열은
// 화면 노출 순서 정의용 (닫힌 union, 자유텍스트 불가, D-03).
const EXPERIENCE_OPTIONS: ReadonlyArray<{ value: ExperienceLevel; label: string }> = (
  ['beginner', 'intermediate', 'advanced'] as const
).map((value) => ({ value, label: EXPERIENCE_LABEL_KO[value] }));

const HAND_OPTIONS: ReadonlyArray<{ value: DominantHand; label: string }> = (
  ['left', 'right', 'both'] as const
).map((value) => ({ value, label: DOMINANT_HAND_LABEL_KO[value] }));

// 통증부위 — 폴스포츠 고하중 관절 (docs/research/폴스포츠-지식.md 정합).
const PAIN_AREA_OPTIONS: ReadonlyArray<{ value: PainArea; label: string }> = (
  ['shoulder', 'wrist', 'lower_back', 'knee', 'ankle', 'neck', 'hip', 'elbow'] as const
).map((value) => ({ value, label: PAIN_AREA_LABEL_KO[value] }));

type Props = {
  initial?: BodyProfile | null;
  // 통증부위 '기타' 자유입력 prefill (F3). 앱-로컬 painAreaNote — 옵셔널이라
  // analyze 등 prefill 없는 첫-입력 호출부는 무변경 (계약/호출부 무접촉).
  initialPainAreaNote?: string | null;
  onSaved?: () => void;
  onClose?: () => void;
};

// 숫자 입력 검증 — 빈값은 허용(null), 범위 밖이면 한국어 에러 메시지 반환.
function validateNumber(
  raw: string,
  lo: number,
  hi: number,
  unit: string,
): { value: number | null; error: string | null } {
  const trimmed = raw.trim();
  if (trimmed === '') return { value: null, error: null }; // 부분 입력 허용 (D-06)
  const n = Number(trimmed);
  if (!Number.isFinite(n)) return { value: null, error: '숫자만 입력해주세요.' };
  if (n < lo || n > hi) {
    // [IN-02] 범위는 물결로 묶고 단위는 끝에 1회만 (90~250cm). 공백 물결 / 단위 중복 제거.
    return { value: null, error: `${lo}~${hi}${unit} 사이로 입력해주세요.` };
  }
  return { value: n, error: null };
}

export default function BodyProfileForm({
  initial,
  initialPainAreaNote,
  onSaved,
  onClose,
}: Props) {
  const insets = useSafeAreaInsets();

  // 숫자는 string state 로 보관 (빈 문자열 = 미입력). prefill = 기존값(수정 진입).
  const [heightStr, setHeightStr] = useState<string>(
    initial?.heightCm != null ? String(initial.heightCm) : '',
  );
  // weightKg 는 보조 ONLY (D-05) — 분석 단정·점수 가중 금지. 저장만 하고 scoring 미전달.
  const [weightStr, setWeightStr] = useState<string>(
    initial?.weightKg != null ? String(initial.weightKg) : '',
  );
  const [experience, setExperience] = useState<ExperienceLevel | null>(
    initial?.experience ?? null,
  );
  const [dominantHand, setDominantHand] = useState<DominantHand | null>(
    initial?.dominantHand ?? null,
  );
  const [painAreas, setPainAreas] = useState<PainArea[]>(initial?.painAreas ?? []);

  // 통증부위 '기타' + 자유입력 (F3). etcSelected 초기값 = prefill 메모 존재 여부.
  // noteStr = 자유입력 텍스트. noteFocused = 포커스 시 브랜드 보더 (UI-SPEC S7).
  const [etcSelected, setEtcSelected] = useState<boolean>(
    !!(initialPainAreaNote && initialPainAreaNote.trim() !== ''),
  );
  const [noteStr, setNoteStr] = useState<string>(initialPainAreaNote ?? '');
  const [noteFocused, setNoteFocused] = useState<boolean>(false);

  const [heightError, setHeightError] = useState<string | null>(null);
  const [weightError, setWeightError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState<boolean>(false);

  const onChangeHeight = (text: string) => {
    const digits = text.replace(/[^0-9]/g, '');
    setHeightStr(digits);
    if (heightError) setHeightError(null);
  };

  const onChangeWeight = (text: string) => {
    const digits = text.replace(/[^0-9]/g, '');
    setWeightStr(digits);
    if (weightError) setWeightError(null);
  };

  const togglePainArea = (area: PainArea) => {
    setPainAreas((prev) =>
      prev.includes(area) ? prev.filter((a) => a !== area) : [...prev, area],
    );
  };

  const onSave = async () => {
    Keyboard.dismiss();
    const h = validateNumber(heightStr, HEIGHT_CM_MIN, HEIGHT_CM_MAX, 'cm');
    const w = validateNumber(weightStr, WEIGHT_KG_MIN, WEIGHT_KG_MAX, 'kg');
    setHeightError(h.error);
    setWeightError(w.error);
    if (h.error || w.error) return;

    setSaving(true);
    setSaveError(null);
    try {
      // 빈 필드는 null/[] 로 merge — 부분 입력 OK (D-06).
      await saveBodyProfile({
        heightCm: h.value,
        weightKg: w.value, // 보조 ONLY (D-05)
        experience,
        painAreas,
        dominantHand,
      });

      // F3 dirty-guard: prefill 없는 호출부(analyze 등)에서 기존 메모를 빈 값으로
      // 덮어쓰지 않도록 initialPainAreaNote 와 다를 때만 기록. 기타 해제 시 '' 취급
      // (해제 = 메모 삭제 의도 → null 명시 기록, WR-01).
      const trimmedNote = etcSelected ? noteStr.trim() : '';
      const baseNote = (initialPainAreaNote ?? '').trim();
      if (trimmedNote !== baseNote) {
        await savePainAreaNote(trimmedNote === '' ? null : trimmedNote);
      }

      onSaved?.();
    } catch {
      setSaveError('저장 중 문제가 발생했어요. 다시 시도해주세요.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      {/* iOS number-pad 는 done 키가 없음 → 빈 영역 탭으로 키보드 닫기 (R6). */}
      <Pressable style={styles.flex} onPress={Keyboard.dismiss} accessible={false}>
        <View style={styles.headerRow}>
          <Text style={styles.title}>내 몸 정보</Text>
          {onClose ? (
            <Pressable
              onPress={onClose}
              accessibilityRole="button"
              accessibilityLabel="닫기"
              hitSlop={10}
            >
              <Ionicons name="close" size={26} color={colors.textPrimary} />
            </Pressable>
          ) : null}
        </View>
        <Text style={styles.subtitle}>
          입력한 정보는 분석 코칭을 더 정확하게 맞추는 데 쓰여요. 일부만 채워도 괜찮아요.
        </Text>

        <ScrollView
          style={styles.flex}
          contentContainerStyle={[
            styles.scrollBody,
            { paddingBottom: insets.bottom + spacing.cardPadding * 2 },
          ]}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          {/* 키 (cm) */}
          <NumberField
            label="키"
            unit="cm"
            value={heightStr}
            placeholder="예: 165"
            error={heightError}
            onChangeText={onChangeHeight}
            accessibilityLabel="키, 센티미터"
            // [IN-03] 입력 자릿수 상한을 범위 상수에서 파생 — 매직넘버 제거, 범위 변경 시 자동 추종.
            maxLength={String(HEIGHT_CM_MAX).length}
          />

          {/* 몸무게 (kg) — 보조 ONLY (D-05): 분석 점수에 절대 반영되지 않음 */}
          <NumberField
            label="몸무게"
            unit="kg"
            value={weightStr}
            placeholder="예: 55"
            error={weightError}
            onChangeText={onChangeWeight}
            accessibilityLabel="몸무게, 킬로그램"
            maxLength={String(WEIGHT_KG_MAX).length}
          />

          {/* 경력 */}
          <Segmented<ExperienceLevel>
            label="경력"
            options={EXPERIENCE_OPTIONS}
            selected={experience}
            groupLabel="경력"
            onSelect={(v) => setExperience((prev) => (prev === v ? null : v))}
          />

          {/* 우세손 */}
          <Segmented<DominantHand>
            label="우세손"
            options={HAND_OPTIONS}
            selected={dominantHand}
            groupLabel="우세손"
            onSelect={(v) => setDominantHand((prev) => (prev === v ? null : v))}
          />

          {/* 통증부위 (다중선택) */}
          <View style={styles.field}>
            <Text style={styles.label}>통증부위</Text>
            <Text style={styles.hint}>불편한 곳이 있으면 모두 골라주세요. 없으면 비워두세요.</Text>
            <View style={styles.chipWrap}>
              {PAIN_AREA_OPTIONS.map((opt) => {
                const selected = painAreas.includes(opt.value);
                return (
                  <Pressable
                    key={opt.value}
                    onPress={() => togglePainArea(opt.value)}
                    accessibilityRole="button"
                    accessibilityState={{ selected }}
                    accessibilityLabel={`통증부위 ${opt.label}${selected ? ', 선택됨' : ''}`}
                    hitSlop={6}
                    style={[styles.chip, selected && styles.chipSelected]}
                  >
                    <Text style={[styles.chipText, selected && styles.chipTextSelected]}>
                      {opt.label}
                    </Text>
                  </Pressable>
                );
              })}
              {/* '기타' chip — 닫힌 8개 enum 밖의 자유입력 진입점 (F3). 선택 상태는
                  로컬 boolean(etcSelected), enum 배열(painAreas)엔 넣지 않는다. */}
              <Pressable
                key="etc"
                onPress={() => setEtcSelected((v) => !v)}
                accessibilityRole="button"
                accessibilityState={{ selected: etcSelected }}
                accessibilityLabel={`통증부위 기타${etcSelected ? ', 선택됨' : ''}`}
                hitSlop={6}
                style={[styles.chip, etcSelected && styles.chipSelected]}
              >
                <Text style={[styles.chipText, etcSelected && styles.chipTextSelected]}>
                  기타
                </Text>
              </Pressable>
            </View>
            {/* 기타 자유입력 — placeholder textDisabled, 포커스 시 brand 보더 (UI-SPEC S7). */}
            {etcSelected ? (
              <TextInput
                value={noteStr}
                onChangeText={setNoteStr}
                onFocus={() => setNoteFocused(true)}
                onBlur={() => setNoteFocused(false)}
                placeholder="직접 입력해 주세요"
                placeholderTextColor={colors.textDisabled}
                accessibilityLabel="기타 통증부위 직접 입력"
                style={[styles.noteInput, noteFocused && styles.noteInputFocused]}
              />
            ) : null}
          </View>

          {saveError ? <Text style={styles.error}>{saveError}</Text> : null}

          {/* 저장 CTA — full-width, height 54, radius.button (design.md §5-3) */}
          <Pressable
            onPress={onSave}
            disabled={saving}
            accessibilityRole="button"
            accessibilityState={{ disabled: saving }}
            accessibilityLabel="내 몸 정보 저장"
            style={[styles.cta, saving && styles.ctaDisabled]}
          >
            <Text style={styles.ctaText}>{saving ? '저장 중…' : '저장하기'}</Text>
          </Pressable>
        </ScrollView>
      </Pressable>
    </KeyboardAvoidingView>
  );
}

// 숫자 입력 + 우측 단위 suffix + 한국어 inline error (design.md §5-3-1).
function NumberField({
  label,
  unit,
  value,
  placeholder,
  error,
  onChangeText,
  accessibilityLabel,
  maxLength,
}: {
  label: string;
  unit: string;
  value: string;
  placeholder: string;
  error: string | null;
  onChangeText: (t: string) => void;
  accessibilityLabel: string;
  maxLength: number;
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <View style={[styles.inputBox, error ? styles.inputBoxError : null]}>
        <TextInput
          value={value}
          onChangeText={onChangeText}
          placeholder={placeholder}
          placeholderTextColor={colors.textSecondary}
          keyboardType="number-pad"
          maxLength={maxLength}
          accessibilityLabel={accessibilityLabel}
          style={styles.input}
        />
        <Text style={styles.unit}>{unit}</Text>
      </View>
      {error ? <Text style={styles.errorInline}>{error}</Text> : null}
    </View>
  );
}

// 제네릭 단일선택 세그먼트 (경력/우세손). 토글로 선택 해제 가능 (부분 입력, D-06).
function Segmented<T extends string>({
  label,
  options,
  selected,
  groupLabel,
  onSelect,
}: {
  label: string;
  options: ReadonlyArray<{ value: T; label: string }>;
  selected: T | null;
  groupLabel: string;
  onSelect: (v: T) => void;
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.segmentRow}>
        {options.map((opt) => {
          const isSel = selected === opt.value;
          return (
            <Pressable
              key={opt.value}
              onPress={() => onSelect(opt.value)}
              accessibilityRole="button"
              accessibilityState={{ selected: isSel }}
              accessibilityLabel={`${groupLabel} ${opt.label}${isSel ? ', 선택됨' : ''}`}
              hitSlop={6}
              style={[styles.segment, isSel && styles.segmentSelected]}
            >
              <Text style={[styles.segmentText, isSel && styles.segmentTextSelected]}>
                {opt.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.screenX,
    paddingTop: spacing.cardPadding,
  },
  title: { ...typography.heading, color: colors.textPrimary },
  subtitle: {
    ...typography.caption,
    color: colors.textSecondary,
    paddingHorizontal: spacing.screenX,
    marginTop: 8,
  },
  scrollBody: {
    paddingHorizontal: spacing.screenX,
    paddingTop: 18,
    gap: 18,
  },
  field: { gap: 8 },
  label: { ...typography.boxLabel, color: colors.textPrimary },
  hint: { ...typography.caption, color: colors.textSecondary },
  inputBox: {
    flexDirection: 'row',
    alignItems: 'center',
    height: layout.inputHeight,
    borderWidth: 1,
    borderColor: colors.inputBorder,
    borderRadius: radius.button,
    backgroundColor: colors.bg,
    paddingHorizontal: spacing.cardPadding,
  },
  inputBoxError: { borderColor: colors.inputError },
  input: { flex: 1, ...typography.buttonSecondary, color: colors.textPrimary },
  unit: { ...typography.caption, color: colors.textSecondary, marginLeft: 8 },
  errorInline: { ...typography.caption, color: colors.inputError },
  segmentRow: { flexDirection: 'row', gap: 10 },
  segment: {
    flex: 1,
    height: layout.inputHeight,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: colors.inputBorder,
    borderRadius: radius.button,
    backgroundColor: colors.bg,
  },
  segmentSelected: { backgroundColor: colors.brand, borderColor: colors.brand },
  segmentText: { ...typography.buttonSecondary, color: colors.textPrimary },
  segmentTextSelected: { color: colors.textWhite },
  chipWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  chip: {
    paddingHorizontal: spacing.cardPadding,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: colors.inputBorder,
    borderRadius: radius.button,
    backgroundColor: colors.bg,
  },
  chipSelected: { backgroundColor: colors.brandTint, borderColor: colors.brand },
  chipText: { ...typography.buttonSecondary, color: colors.textPrimary },
  chipTextSelected: { color: colors.brand },
  // 기타 자유입력 (F3 / UI-SPEC S7) — inputHeight 단일행, 포커스 시 brand 보더.
  noteInput: {
    height: layout.inputHeight,
    borderWidth: 1,
    borderColor: colors.inputBorder,
    borderRadius: radius.button,
    backgroundColor: colors.bg,
    paddingHorizontal: spacing.cardPadding,
    ...typography.buttonSecondary,
    color: colors.textPrimary,
  },
  noteInputFocused: { borderColor: colors.brand },
  error: { ...typography.caption, color: colors.inputError },
  cta: {
    height: layout.ctaHeight,
    borderRadius: radius.button,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 6,
  },
  ctaDisabled: { backgroundColor: colors.brandButtonDisabled },
  ctaText: { ...typography.button, color: colors.textWhite },
});

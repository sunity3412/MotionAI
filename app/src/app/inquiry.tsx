// 문의하기 폼 (quick-260706-sis, F1).
//
// belle 요구(2026-07-06): 문의 유형을 드롭다운으로 고르고 내용을 적어 cs@sunity.ai
// 로 보내는 양식. 전달 방식 = 메일 작성기(belle 선택) — expo-mail-composer 로 기기
// 메일 앱에 수신자·제목·본문을 채워 띄우고, 사용자가 전송 버튼만 누른다. 백엔드 0.
//   · 메일 앱 미설정 기기는 mailto(Linking) 폴백, 그것도 안 되면 주소 안내.
//   · 폼 스타일/토큰은 BodyProfileForm 컨벤션과 동일(하드코딩 색/spacing/fontSize 금지).
//
// 라우트 = /inquiry (expo-router 파일 기반). 로딩 오류 화면의 '문의하기' 가 이 화면을
// 열며, 분석 실패 맥락에선 category=error 로 진입해 '오류 신고' 를 미리 선택한다.

import { Ionicons } from '@expo/vector-icons';
import Constants from 'expo-constants';
import * as MailComposer from 'expo-mail-composer';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useState } from 'react';
import {
  Keyboard,
  KeyboardAvoidingView,
  Linking,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { colors, layout, radius, spacing, typography } from '../theme';

const SUPPORT_EMAIL = 'cs@sunity.ai';

// 문의 유형 — 닫힌 union. value 는 라우트 param/식별용, label 은 화면·메일 제목용.
type InquiryCategory = 'error' | 'feature' | 'partnership' | 'howto' | 'etc';
const CATEGORY_OPTIONS: ReadonlyArray<{ value: InquiryCategory; label: string }> = [
  { value: 'error', label: '오류 신고' },
  { value: 'feature', label: '기능 제안' },
  { value: 'partnership', label: '제휴 문의' },
  { value: 'howto', label: '사용 방법' },
  { value: 'etc', label: '기타' },
];
const CATEGORY_LABEL: Record<InquiryCategory, string> = CATEGORY_OPTIONS.reduce(
  (acc, o) => ({ ...acc, [o.value]: o.label }),
  {} as Record<InquiryCategory, string>,
);

function isCategory(v: unknown): v is InquiryCategory {
  return CATEGORY_OPTIONS.some((o) => o.value === v);
}

export default function Inquiry() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { category: presetCategory } = useLocalSearchParams<{ category?: string }>();

  const [category, setCategory] = useState<InquiryCategory | null>(
    isCategory(presetCategory) ? presetCategory : null,
  );
  const [message, setMessage] = useState('');
  const [contact, setContact] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  const onSend = async () => {
    Keyboard.dismiss();
    if (!category) {
      setError('문의 유형을 선택해주세요.');
      return;
    }
    if (!message.trim()) {
      setError('문의 내용을 입력해주세요.');
      return;
    }
    setSending(true);
    setError(null);

    const label = CATEGORY_LABEL[category];
    const subject = `[${label}] Sunity AI Coach 문의`;
    const appVer = Constants.expoConfig?.version ?? '';
    const meta = `\n\n───\n앱: Sunity AI Coach ${appVer} (${Platform.OS})`;
    const contactLine = contact.trim() ? `\n회신 연락처: ${contact.trim()}` : '';
    const body = `${message.trim()}${contactLine}${meta}`;

    try {
      const available = await MailComposer.isAvailableAsync();
      if (available) {
        const res = await MailComposer.composeAsync({
          recipients: [SUPPORT_EMAIL],
          subject,
          body,
        });
        // sent/saved = 사용자가 보냄/임시저장 → 완료 처리. cancelled = 화면 유지(재시도 가능).
        if (res.status === 'sent' || res.status === 'saved') setSent(true);
      } else {
        // 메일 앱 미설정 — mailto 폴백. 그것도 불가하면 주소 안내.
        const url = `mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent(
          subject,
        )}&body=${encodeURIComponent(body)}`;
        if (await Linking.canOpenURL(url)) {
          await Linking.openURL(url);
        } else {
          setError(`메일 앱을 열 수 없어요. ${SUPPORT_EMAIL} 로 보내주세요.`);
        }
      }
    } catch {
      setError('문의를 보내지 못했어요. 잠시 후 다시 시도해주세요.');
    } finally {
      setSending(false);
    }
  };

  if (sent) {
    return (
      <View style={[styles.container, { paddingTop: insets.top + spacing.cardPadding }]}>
        <StatusBar style="dark" />
        <View style={styles.doneCenter}>
          <View style={styles.doneRing}>
            <Ionicons name="checkmark" size={34} color={colors.brand} />
          </View>
          <Text style={styles.doneTitle}>문의를 접수했어요</Text>
          <Text style={styles.doneSub}>
            보내주신 내용을 확인한 뒤 {SUPPORT_EMAIL} 로 답변드릴게요.
          </Text>
          <Pressable
            onPress={() => router.back()}
            accessibilityRole="button"
            style={styles.cta}
          >
            <Text style={styles.ctaText}>닫기</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={[styles.container, { paddingTop: insets.top }]}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <StatusBar style="dark" />
      <View style={styles.headerRow}>
        <Pressable
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel="닫기"
          hitSlop={10}
        >
          <Ionicons name="chevron-back" size={26} color={colors.textPrimary} />
        </Pressable>
        <Text style={styles.title}>문의하기</Text>
        <View style={styles.headerSpacer} />
      </View>

      <Pressable style={styles.flex} onPress={Keyboard.dismiss} accessible={false}>
        <ScrollView
          style={styles.flex}
          contentContainerStyle={[
            styles.scrollBody,
            { paddingBottom: insets.bottom + spacing.cardPadding * 2 },
          ]}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <Text style={styles.subtitle}>
            문의 유형을 고르고 내용을 남겨주세요. 확인 후 이메일로 답변드릴게요.
          </Text>

          {/* 문의 유형 (단일선택) */}
          <View style={styles.field}>
            <Text style={styles.label}>문의 유형</Text>
            <View style={styles.chipWrap}>
              {CATEGORY_OPTIONS.map((opt) => {
                const selected = category === opt.value;
                return (
                  <Pressable
                    key={opt.value}
                    onPress={() => {
                      setCategory(opt.value);
                      if (error) setError(null);
                    }}
                    accessibilityRole="button"
                    accessibilityState={{ selected }}
                    accessibilityLabel={`문의 유형 ${opt.label}${selected ? ', 선택됨' : ''}`}
                    hitSlop={6}
                    style={[styles.chip, selected && styles.chipSelected]}
                  >
                    <Text style={[styles.chipText, selected && styles.chipTextSelected]}>
                      {opt.label}
                    </Text>
                  </Pressable>
                );
              })}
            </View>
          </View>

          {/* 문의 내용 */}
          <View style={styles.field}>
            <Text style={styles.label}>문의 내용</Text>
            <View style={styles.textAreaBox}>
              <TextInput
                value={message}
                onChangeText={(t) => {
                  setMessage(t);
                  if (error) setError(null);
                }}
                placeholder="어떤 점이 궁금하거나 불편하셨나요?"
                placeholderTextColor={colors.textSecondary}
                multiline
                textAlignVertical="top"
                accessibilityLabel="문의 내용"
                style={styles.textArea}
              />
            </View>
          </View>

          {/* 회신 연락처 (선택) */}
          <View style={styles.field}>
            <Text style={styles.label}>회신 연락처 (선택)</Text>
            <Text style={styles.hint}>답변받을 이메일이나 연락처를 남겨주세요.</Text>
            <View style={styles.inputBox}>
              <TextInput
                value={contact}
                onChangeText={setContact}
                placeholder="예: name@email.com"
                placeholderTextColor={colors.textSecondary}
                keyboardType="email-address"
                autoCapitalize="none"
                autoCorrect={false}
                accessibilityLabel="회신 연락처"
                style={styles.input}
              />
            </View>
          </View>

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <Pressable
            onPress={onSend}
            disabled={sending}
            accessibilityRole="button"
            accessibilityState={{ disabled: sending }}
            accessibilityLabel="문의 보내기"
            style={[styles.cta, sending && styles.ctaDisabled]}
          >
            <Text style={styles.ctaText}>{sending ? '보내는 중…' : '문의 보내기'}</Text>
          </Pressable>
        </ScrollView>
      </Pressable>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  flex: { flex: 1 },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.screenX,
    paddingVertical: spacing.cardPadding,
  },
  title: { ...typography.heading, color: colors.textPrimary },
  headerSpacer: { width: 26 },
  subtitle: { ...typography.caption, color: colors.textSecondary },
  scrollBody: {
    paddingHorizontal: spacing.screenX,
    paddingTop: 4,
    gap: 18,
  },
  field: { gap: 8 },
  label: { ...typography.boxLabel, color: colors.textPrimary },
  hint: { ...typography.caption, color: colors.textSecondary },
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
  input: { flex: 1, ...typography.buttonSecondary, color: colors.textPrimary },
  textAreaBox: {
    minHeight: 140,
    borderWidth: 1,
    borderColor: colors.inputBorder,
    borderRadius: radius.button,
    backgroundColor: colors.bg,
    paddingHorizontal: spacing.cardPadding,
    paddingVertical: 12,
  },
  textArea: {
    flex: 1,
    minHeight: 116,
    ...typography.buttonSecondary,
    color: colors.textPrimary,
  },
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
  // 전송 완료 상태
  doneCenter: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.screenX,
    gap: 14,
  },
  doneRing: {
    width: 84,
    height: 84,
    borderRadius: 42,
    borderWidth: 2,
    borderColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
  },
  doneTitle: { ...typography.heading, color: colors.textPrimary, textAlign: 'center' },
  doneSub: {
    ...typography.caption,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 19,
  },
});

// 강사 교정 입력 모달 (quick-260918-0q8, belle 2026-09-17 승인).
//
// 보완운동 탭 '강사에게 확인할 점' 카드의 메모 행이 연다. 학원에서 **강사가 학생
// 폰에 직접 입력**하는 자리다 — 그래서 로그인/역할 전환이 없고, 이름은 신원 증명이
// 아니라 출처 표기(자유 입력)다.
//
// 저장은 부모가 한다(lib/coachReview.saveCoachReview). 이 컴포넌트는 입력만 받고
// onSave 를 부른다 — 화면이 Firestore 에 직접 닿지 않는 규율 유지.

import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { colors, layout, radius, spacing, typography } from '../../theme';
import {
  COACH_COMMENT_MAX,
  COACH_NAME_MAX,
  isSavableCoachReview,
} from '../../lib/coachReview';
import type { CoachReview } from '../../types/analysis';

export interface CoachReviewModalProps {
  visible: boolean;
  /** 기존 저장값 — 열 때 입력칸 초기값으로 쓴다. */
  current?: CoachReview | null;
  /** 저장. 실패하면 throw — 이 컴포넌트가 문구로 보여준다. */
  onSave: (comment: string, reviewedBy: string) => Promise<void>;
  /** 저장된 메모 삭제. 저장값이 없으면 버튼 자체를 안 그린다. */
  onDelete?: () => Promise<void>;
  onClose: () => void;
}

export function CoachReviewModal({
  visible,
  current,
  onSave,
  onDelete,
  onClose,
}: CoachReviewModalProps) {
  const [comment, setComment] = useState('');
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 열릴 때마다 저장값으로 초기화 — 닫았다 다시 열면 직전 입력이 남지 않는다.
  useEffect(() => {
    if (!visible) return;
    setComment(current?.comment ?? '');
    setName(current?.reviewedBy ?? '');
    setError(null);
    setBusy(false);
  }, [visible, current]);

  const canSave = isSavableCoachReview(comment) && !busy;

  async function run(fn: () => Promise<void>, failMsg: string) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      onClose();
    } catch {
      setError(failMsg);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <Pressable style={styles.backdrop} onPress={busy ? undefined : onClose}>
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          style={styles.center}
        >
          {/* 카드 자체 탭은 닫힘으로 전파되지 않게 흡수 */}
          <Pressable style={styles.card} onPress={() => {}}>
            <Text style={styles.title}>강사 메모</Text>
            <Text style={styles.sub}>
              이 분석에서 강사님이 본 것을 남겨 주세요. 수강생 화면에 그대로 보여요.
            </Text>

            <ScrollView
              style={styles.scroll}
              keyboardShouldPersistTaps="handled"
              showsVerticalScrollIndicator={false}
            >
              <Text style={styles.label}>교정 내용</Text>
              <TextInput
                value={comment}
                onChangeText={setComment}
                editable={!busy}
                multiline
                maxLength={COACH_COMMENT_MAX}
                placeholder="예) 팔꿈치를 펴는 것보다 어깨를 먼저 내려야 이 셰이프가 잡혀요."
                placeholderTextColor={colors.textSecondary}
                style={[styles.input, styles.inputMultiline]}
                accessibilityLabel="교정 내용 입력"
              />
              <Text style={styles.counter}>
                {`${comment.length} / ${COACH_COMMENT_MAX}`}
              </Text>

              <Text style={[styles.label, styles.labelGap]}>강사 이름</Text>
              <TextInput
                value={name}
                onChangeText={setName}
                editable={!busy}
                maxLength={COACH_NAME_MAX}
                placeholder="선택 — 비워도 저장돼요"
                placeholderTextColor={colors.textSecondary}
                style={styles.input}
                accessibilityLabel="강사 이름 입력"
              />
            </ScrollView>

            {error ? <Text style={styles.error}>{error}</Text> : null}

            <View style={styles.btnRow}>
              {current && onDelete ? (
                <Pressable
                  onPress={() => void run(onDelete, '삭제하지 못했어요. 다시 시도해 주세요.')}
                  disabled={busy}
                  accessibilityRole="button"
                  accessibilityLabel="강사 메모 삭제"
                  style={({ pressed }) => [styles.btnGhost, pressed && styles.pressed]}
                >
                  <Text style={styles.btnGhostText}>삭제</Text>
                </Pressable>
              ) : (
                <Pressable
                  onPress={onClose}
                  disabled={busy}
                  accessibilityRole="button"
                  accessibilityLabel="닫기"
                  style={({ pressed }) => [styles.btnGhost, pressed && styles.pressed]}
                >
                  <Text style={styles.btnGhostText}>취소</Text>
                </Pressable>
              )}
              <Pressable
                onPress={() =>
                  void run(
                    () => onSave(comment, name),
                    '저장하지 못했어요. 연결을 확인하고 다시 시도해 주세요.',
                  )
                }
                disabled={!canSave}
                accessibilityRole="button"
                accessibilityLabel="강사 메모 저장"
                accessibilityState={{ disabled: !canSave }}
                style={({ pressed }) => [
                  styles.btnBrand,
                  !canSave && styles.btnDisabled,
                  pressed && canSave && styles.pressed,
                ]}
              >
                {busy ? (
                  <ActivityIndicator color={colors.textWhite} />
                ) : (
                  <Text style={styles.btnBrandText}>저장</Text>
                )}
              </Pressable>
            </View>
          </Pressable>
        </KeyboardAvoidingView>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  // 같은 화면 ResultPointModal.scrim 과 동일 (그 파일이 관례의 정본).
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)' },
  center: { flex: 1, justifyContent: 'center', paddingHorizontal: spacing.screenX },
  card: {
    backgroundColor: colors.cardBg,
    borderRadius: radius.resultCard,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.resultCardBorder,
    padding: 20,
    gap: 6,
    maxHeight: '80%',
  },
  title: { ...typography.listTitle, color: colors.textPrimary },
  sub: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
    marginBottom: 6,
  },
  scroll: { flexGrow: 0 },
  label: { ...typography.boxLabel, color: colors.textPrimary },
  labelGap: { marginTop: 14 },
  input: {
    ...typography.caption,
    color: colors.textPrimary,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.resultCardBorder,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginTop: 6,
  },
  inputMultiline: { minHeight: 96, textAlignVertical: 'top' },
  counter: {
    ...typography.captionSmall,
    color: colors.textSecondary,
    alignSelf: 'flex-end',
    marginTop: 4,
  },
  error: {
    ...typography.caption,
    color: colors.brand,
    marginTop: 8,
  },
  btnRow: { flexDirection: 'row', gap: 10, marginTop: 16 },
  btnGhost: {
    flex: 1,
    height: 48,
    borderRadius: 12,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.resultCardBorder,
    alignItems: 'center',
    justifyContent: 'center',
  },
  btnGhostText: { ...typography.boxLabel, color: colors.textPrimary },
  btnBrand: {
    flex: 1,
    height: 48,
    borderRadius: 12,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
  },
  btnBrandText: { ...typography.boxLabel, color: colors.textWhite },
  btnDisabled: { opacity: 0.4 },
  pressed: { opacity: 0.85 },
});

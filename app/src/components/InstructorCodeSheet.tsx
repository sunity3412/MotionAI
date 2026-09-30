// 마이 탭 강사 코드 — 행 · 입력 시트 · 강사 확인 · 토스트 (quick-260930-o0u, 38-DESIGN-v2 §W2 화면 1~5).
//
// 시각 값은 38-DESIGN-v2 §W2(Figma v2 옮김) 그대로. 색은 theme 토큰, 간격은 SupplierUi `space` ·
// theme spacing/layout, 문구는 전부 profileCopy.instructorCode(이 파일에 한국어 문자열 0).
// SupplierUi.tsx 는 고치지 않고 export 만 쓴다(고치면 공급자 웹 export 게이트가 붙는다).
//
// apple-design: 눌림은 누르는 순간 opacity 0.7(Pressable pressed). 연결은 되돌릴 수 없어서(한 번뿐)
// 강사 확인 단계를 둔다. 저모션 설정이면 시트는 fade, 토스트는 즉시.
//
// 상태 전이는 lib/instructorCode.sheetReducer(순수, node --test 로 잠금), Firestore 는
// lib/instructorLink(get 1회 · runTransaction create-once). 최종 판정은 firestore.rules.

import { Ionicons } from '@expo/vector-icons';
import { useEffect, useReducer, useRef, useState } from 'react';
import {
  AccessibilityInfo,
  Animated,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { profileCopy } from '../constants/profileCopy';
import {
  canSubmit,
  INITIAL_SHEET_STATE,
  instructorName,
  sheetReducer,
  type InstructorLink,
  type InputError,
} from '../lib/instructorCode';
import {
  linkInstructor,
  lookupInstructorCode,
  type InstructorLinkStatus,
} from '../lib/instructorLink';
import { colors, layout, radius, spacing, typography } from '../theme';
import { PrimaryCta, space, text } from './SupplierUi';

const copy = profileCopy.instructorCode;

// 38-DESIGN-v2 §W2 크기 — 그랩바 36×5 · 강사 확인 원형 64 · 입력값 20 자간 +6%(1.2) ·
// 토스트 반경 12(SupplierUi Toast 와 같은 값). SupplierUi `H` 선례처럼 한곳에 둔다.
const SIZE = {
  grabW: 36,
  grabH: 5,
  avatar: 64,
  avatarIcon: 28,
  chevron: 20,
  inputFont: 20,
  inputTrack: 1.2,
  inputBorder: 1,
  inputBorderFocus: 1.5,
  inputMaxLength: 16,
  toastRadius: 12,
  toastFadeMs: 150,
  rowPadV: 14,
  hintInset: 4,
  cancelHitSlop: 12,
} as const;

const PRESSED_OPACITY = 0.7;

function useReduceMotion(): boolean {
  const [on, setOn] = useState(false);
  useEffect(() => {
    let alive = true;
    AccessibilityInfo.isReduceMotionEnabled()
      .then((v) => {
        if (alive) setOn(v);
      })
      .catch(() => {
        // 조회 실패 = 끔(기본 애니메이션).
      });
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setOn);
    return () => {
      alive = false;
      sub.remove();
    };
  }, []);
  return on;
}

// ── 행 ────────────────────────────────────────────────────────────────────
// loading: 라벨만(연결된 사람에게 입력하기가 깜빡이지 않게), 누를 수 없음, 힌트 없음.
// 미연결(ready/error + link 없음): 행 전체 버튼 · 오른쪽 입력하기 + 쉐브론 · 아래 힌트.
// 연결됨: 누를 수 없음 · 오른쪽 두 줄(이름 강사님 / 코드) · 쉐브론 없음 · 아래 바꾸기 힌트.
// error 는 미연결로 그린다 — 이미 연결된 사람이 다시 눌러도 트랜잭션이 already 를 돌려준다.
export function InstructorCodeRow({
  status,
  link,
  onPress,
}: {
  status: InstructorLinkStatus;
  link: InstructorLink | null;
  onPress: () => void;
}) {
  if (link) {
    const name = instructorName(link.displayName, link.code);
    return (
      <View>
        <View
          style={s.card}
          accessible
          accessibilityLabel={copy.a11yLinked(name, link.code)}
        >
          <View style={s.row}>
            <Text style={s.label}>{copy.label}</Text>
            <View style={s.linkedRight}>
              <Text style={s.linkedName}>{copy.instructorTitle(name)}</Text>
              <Text style={s.linkedCode}>{link.code}</Text>
            </View>
          </View>
        </View>
        <Text style={s.hint}>{copy.linkedHint}</Text>
      </View>
    );
  }

  if (status === 'loading') {
    return (
      <View style={s.card} accessible accessibilityLabel={copy.label}>
        <View style={s.row}>
          <Text style={s.label}>{copy.label}</Text>
        </View>
      </View>
    );
  }

  return (
    <View>
      <Pressable
        onPress={onPress}
        accessibilityRole="button"
        accessibilityLabel={copy.a11yEmpty}
        hitSlop={4}
        style={({ pressed }) => [s.card, pressed && s.pressed]}
      >
        <View style={s.row}>
          <Text style={s.label}>{copy.label}</Text>
          <View style={s.actionRight}>
            <Text style={s.action}>{copy.action}</Text>
            <Ionicons name="chevron-forward" size={SIZE.chevron} color={colors.brand} />
          </View>
        </View>
      </Pressable>
      <Text style={s.hint}>{copy.hint}</Text>
    </View>
  );
}

// ── 입력 시트 ──────────────────────────────────────────────────────────────

function errorText(error: InputError | null): string | null {
  return error === null ? null : copy.errors[error];
}

export function InstructorCodeSheet({
  visible,
  uid,
  onClose,
  onLinked,
}: {
  visible: boolean;
  uid: string;
  onClose: () => void;
  onLinked: (link: InstructorLink, kind: 'linked' | 'already') => void;
}) {
  const [state, dispatch] = useReducer(sheetReducer, INITIAL_SHEET_STATE);
  const [focused, setFocused] = useState(false);
  const reduceMotion = useReduceMotion();
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  // 열릴 때마다 처음부터(값·오류·단계 초기화).
  useEffect(() => {
    if (visible) dispatch({ type: 'reset' });
  }, [visible]);

  const message = errorText(state.error);
  // 오류가 바뀌면 VoiceOver 에 읽어 준다(accessibilityLiveRegion 은 Android 전용).
  useEffect(() => {
    if (message) AccessibilityInfo.announceForAccessibility(message);
  }, [message]);

  const close = () => {
    if (!state.busy) onClose();
  };

  const submitLookup = async () => {
    if (!canSubmit(state)) return;
    dispatch({ type: 'lookupStart' });
    const result = await lookupInstructorCode(state.value, uid);
    if (alive.current) dispatch({ type: 'lookupDone', result });
  };

  const submitLink = async () => {
    if (state.step !== 'confirm' || state.busy) return;
    dispatch({ type: 'linkStart' });
    const out = await linkInstructor(uid, state.found);
    if (!alive.current) return;
    if (out.kind === 'linked') {
      onLinked(out.link, 'linked');
      onClose();
      return;
    }
    if (out.kind === 'already') {
      // 읽기가 모양을 못 맞추면(null) 방금 확인한 코드로 보여 준다 — 연결돼 있다는 사실은 같다.
      onLinked(out.link ?? { ...state.found, linkedAtMs: null }, 'already');
      onClose();
      return;
    }
    if (out.kind === 'denied') {
      dispatch({ type: 'linkDenied' });
      return;
    }
    dispatch({ type: 'linkFailed', reason: out.kind });
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType={reduceMotion ? 'fade' : 'slide'}
      onRequestClose={close}
    >
      <KeyboardAvoidingView
        style={s.backdrop}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <Pressable
          style={s.backdropTop}
          onPress={close}
          accessibilityRole="button"
          accessibilityLabel={copy.sheet.close}
        />
        <View style={s.sheet} accessibilityViewIsModal>
          <View style={s.grab} />
          {state.step === 'input' ? (
            <View>
              <Text style={text.heading}>{copy.sheet.title}</Text>
              <Text style={[text.aux, s.mt4]}>{copy.sheet.body}</Text>
              <TextInput
                value={state.value}
                onChangeText={(v) => dispatch({ type: 'edit', value: v })}
                onFocus={() => setFocused(true)}
                onBlur={() => setFocused(false)}
                editable={!state.busy}
                autoCapitalize="characters"
                autoCorrect={false}
                autoComplete="off"
                spellCheck={false}
                keyboardType="ascii-capable"
                maxLength={SIZE.inputMaxLength}
                autoFocus
                returnKeyType="done"
                onSubmitEditing={() => {
                  if (canSubmit(state)) void submitLookup();
                }}
                accessibilityLabel={copy.sheet.inputA11y}
                style={[
                  s.input,
                  focused && s.inputFocus,
                  state.error !== null && s.inputError,
                ]}
              />
              {message ? (
                <Text style={[text.aux, s.errorText, s.mt8]} accessibilityLiveRegion="polite">
                  {message}
                </Text>
              ) : null}
              <View style={s.mt20}>
                <PrimaryCta
                  label={copy.sheet.submit}
                  onPress={() => void submitLookup()}
                  disabled={!canSubmit(state)}
                />
              </View>
            </View>
          ) : (
            <View>
              <View style={s.center}>
                <View style={s.avatar}>
                  <Ionicons name="person-outline" size={SIZE.avatarIcon} color={colors.brand} />
                </View>
                <Text style={[text.heading, s.mt12, s.textCenter]}>
                  {copy.instructorTitle(
                    instructorName(state.found.displayName, state.found.code),
                  )}
                </Text>
                <Text style={[text.auxFaint, s.mt4, s.textCenter]}>
                  {copy.codeLine(state.found.code)}
                </Text>
              </View>
              <View style={[s.notice, s.mt16]}>
                <Text style={text.aux}>{copy.confirm.notice}</Text>
              </View>
              <View style={s.mt20}>
                <PrimaryCta
                  label={copy.confirm.submit}
                  onPress={() => void submitLink()}
                  disabled={state.busy}
                />
              </View>
              {message ? (
                <Text style={[text.aux, s.errorText, s.mt8]} accessibilityLiveRegion="polite">
                  {message}
                </Text>
              ) : null}
              <Pressable
                onPress={() => dispatch({ type: 'cancel' })}
                disabled={state.busy}
                hitSlop={SIZE.cancelHitSlop}
                accessibilityRole="button"
                accessibilityLabel={copy.confirm.cancel}
                accessibilityState={{ disabled: state.busy }}
                style={({ pressed }) => [s.cancel, pressed && s.pressed]}
              >
                <Text style={s.cancelText}>{copy.confirm.cancel}</Text>
              </Pressable>
            </View>
          )}
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

// ── 토스트 ────────────────────────────────────────────────────────────────
// 탭 화면 컨테이너 안에 절대 위치 — 컨테이너 바닥이 탭바 위라 탭바 바로 위에 뜬다.
// 배경 textPrimary 는 SupplierUi Toast 와 같은 예외(design.md §0 — 짧게 뜨는 알림).
export function BottomToast({ message }: { message: string | null }) {
  const reduceMotion = useReduceMotion();
  const opacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!message) {
      opacity.setValue(0);
      return;
    }
    AccessibilityInfo.announceForAccessibility(message);
    if (reduceMotion) {
      opacity.setValue(1);
      return;
    }
    opacity.setValue(0);
    const anim = Animated.timing(opacity, {
      toValue: 1,
      duration: SIZE.toastFadeMs,
      useNativeDriver: true,
    });
    anim.start();
    return () => anim.stop();
  }, [message, reduceMotion, opacity]);

  if (!message) return null;
  return (
    <Animated.View
      pointerEvents="none"
      style={[s.toast, { opacity }]}
      accessibilityLiveRegion="polite"
    >
      <Text style={[text.label, s.onDark]}>{message}</Text>
    </Animated.View>
  );
}

const s = StyleSheet.create({
  // profile infoList/infoRow 모양 복제 — 흰 면 · 0.858 divider · 반경 15 · 좌우 16 · 행 세로 14.
  card: {
    backgroundColor: colors.cardBg,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    borderRadius: radius.card,
    paddingHorizontal: spacing.cardPadding,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: SIZE.rowPadV,
    gap: space.row,
  },
  pressed: { opacity: PRESSED_OPACITY },
  label: { ...typography.caption, color: colors.resultTextSub },
  actionRight: { flexDirection: 'row', alignItems: 'center', gap: space.xxs },
  action: { ...text.labelBold, color: colors.brand },
  linkedRight: { alignItems: 'flex-end', flexShrink: 1 },
  linkedName: { ...text.labelBold, color: colors.textPrimary, textAlign: 'right' },
  linkedCode: { ...text.caption13, color: colors.resultTextSub, textAlign: 'right' },
  // profile guestHint 처럼 카드에 붙인다 — 그쪽은 body gap 14 를 -6 으로 당겨 실제 8. 이 힌트는
  // 카드와 같은 View 안이라 gap 이 없으므로 8 을 직접 준다. 좌우 4.
  // 글자는 바로 위 로그인 힌트(profile.tsx guestHint = typography.caption + textSecondary)와
  // 같은 크기·색 (belle 09-30 "안내 글자만 맞추고" — 명세 15 는 로그인 힌트보다 커 보였다).
  hint: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: space.sm,
    paddingHorizontal: SIZE.hintInset,
  },

  backdrop: {
    flex: 1,
    backgroundColor: colors.brandOverlay,
    justifyContent: 'flex-end',
  },
  backdropTop: { flex: 1 },
  sheet: {
    backgroundColor: colors.bg,
    borderTopLeftRadius: radius.modal,
    borderTopRightRadius: radius.modal,
    paddingHorizontal: spacing.screenX,
    paddingTop: space.sm,
    paddingBottom: layout.safeAreaBottom,
  },
  grab: {
    alignSelf: 'center',
    width: SIZE.grabW,
    height: SIZE.grabH,
    borderRadius: SIZE.grabH / 2,
    backgroundColor: colors.divider,
    marginBottom: spacing.screenX - space.sm,
  },
  input: {
    marginTop: space.screen,
    height: layout.inputHeight,
    borderRadius: radius.button,
    borderWidth: SIZE.inputBorder,
    borderColor: colors.inputBorder,
    paddingHorizontal: space.md,
    fontFamily: typography.buttonSecondary.fontFamily,
    fontSize: SIZE.inputFont,
    letterSpacing: SIZE.inputTrack,
    color: colors.textPrimary,
  },
  inputFocus: { borderWidth: SIZE.inputBorderFocus, borderColor: colors.brand },
  inputError: { borderWidth: SIZE.inputBorderFocus, borderColor: colors.inputError },
  errorText: { color: colors.infoTeal },
  center: { alignItems: 'center' },
  textCenter: { textAlign: 'center' },
  avatar: {
    width: SIZE.avatar,
    height: SIZE.avatar,
    borderRadius: SIZE.avatar / 2,
    backgroundColor: colors.brandAvatarBg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  notice: {
    backgroundColor: colors.softBg,
    borderRadius: radius.button,
    paddingVertical: space.s14,
    paddingHorizontal: space.md,
  },
  cancel: { alignSelf: 'center', marginTop: space.row },
  cancelText: { ...text.label, color: colors.textMid, textDecorationLine: 'underline' },
  mt4: { marginTop: space.xs },
  mt8: { marginTop: space.sm },
  mt12: { marginTop: space.row },
  mt16: { marginTop: space.md },
  mt20: { marginTop: space.screen },

  toast: {
    position: 'absolute',
    left: spacing.screenX,
    right: spacing.screenX,
    bottom: layout.safeAreaBottom + space.row,
    backgroundColor: colors.textPrimary,
    borderRadius: SIZE.toastRadius,
    paddingVertical: space.row,
    paddingHorizontal: space.md,
    alignItems: 'center',
  },
  onDark: { color: colors.textWhite },
});

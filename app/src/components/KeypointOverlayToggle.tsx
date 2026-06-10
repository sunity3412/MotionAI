// Phase 12 Wave 2 (Plan 12-03 T2) — KeypointOverlay 토글 (controlled switch).
//
// 책임:
//   - 46 × 22 pill 형 switch. ON = brand bg / OFF = softBg.
//   - 안 18 × 18 WHITE 동그라미 thumb. translateX 4 (off) ↔ 24 (on).
//   - radius 11 (pill).
//   - a11y switch role + accessibilityState.checked + label (UI-SPEC §11).
//
// 책임 분리: caller (result.tsx) 가 useState + AsyncStorage 의 read/write 담당.
// 본 component 는 단순 controlled (value + onValueChange) — AsyncStorage 의존 0.
//
// AsyncStorage key 는 caller 가 '@sunity:keypoint_overlay_enabled' 박제 (T-12-03-T4
// namespace 우회 — Firebase Auth backing store 와 충돌 0).
//
// 토큰만 사용 (CLAUDE.md §4 / D-12-U5). brand #FF4B33 변경 0.

import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { colors } from '../theme';

export type KeypointOverlayToggleProps = {
  value: boolean;
  onValueChange: (next: boolean) => void;
};

export function KeypointOverlayToggle({
  value,
  onValueChange,
}: KeypointOverlayToggleProps) {
  const a11yLabel = `키포인트 오버레이. 현재 ${value ? '켜짐' : '꺼짐'}. ${
    value ? '끄려면' : '켜려면'
  } 두 번 탭.`;

  return (
    <Pressable
      onPress={() => onValueChange(!value)}
      accessibilityRole="switch"
      accessibilityState={{ checked: value }}
      accessibilityLabel={a11yLabel}
      hitSlop={8}
      style={({ pressed }) => [
        styles.track,
        value ? styles.trackOn : styles.trackOff,
        pressed && styles.pressed,
      ]}
    >
      <View
        style={[
          styles.thumb,
          { transform: [{ translateX: value ? 24 : 4 }] },
        ]}
      />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  track: {
    width: 46,
    height: 22,
    borderRadius: 11,
    justifyContent: 'center',
  },
  trackOn: { backgroundColor: colors.brand },
  trackOff: { backgroundColor: colors.softBg },
  thumb: {
    width: 18,
    height: 18,
    borderRadius: 9,
    backgroundColor: colors.textWhite,
  },
  pressed: { opacity: 0.85 },
});

// 수요자 영상 길이 검사 — 순수 분기 (Phase 38 D-14, REQ-38-6).
//
// 3초 미만은 동작 전체가 안 담긴다(IA 3-3 AC-VID-003-1L — 문구는 pickerFailure.ts 가
// 소유). 90초 초과는 수요자 상한 밖이다(Phase 38 D-14). 상한·하한 상수는 이 파일에만
// 두고 analyze.tsx 는 이름만 쓴다 — 값이 두 곳에 갈리지 않게.
//
// ★보장 범위 = 클라이언트 검사뿐 (리뷰 R15c, 2026-09-26).
// duration 을 안 주는 픽(웹·일부 갤러리, RESEARCH Pitfall 5)은 통과(fail-open)하고,
// 수요자 `uploads/` 경로에는 서버 측 길이 상한이 없다(Phase 38 범위 밖 — 공급자 경로만
// 서버 2차 방어). 이 fail-open 은 의도된 수용이다 — 값 없음/0 은 "짧다"가 아니라
// "판정 불가"이고, 그것을 실패로 돌리면 메타를 안 주는 갤러리 픽이 통째로 막힌다
// (analyze.tsx checkLowQuality 의 `duration != null && duration > 0` 가드와 같은 규율).
//
// react / react-native / expo import 0 — pickerFailure.ts 와 같은 이유로 `node --test`
// 가 트랜스파일 없이 바로 검증한다 (신규 npm 의존성 0).

export const MIN_DURATION_MS = 3 * 1000; // IA 3-3 AC-VID-003-1L — 3초 미만 실패 (Phase 38 D-14)
export const MAX_DURATION_MS = 90 * 1000; // Phase 38 D-14 — 수요자 상한 90초

export type DurationFailure = 'tooShort' | 'tooLong';

// durationMs = expo-image-picker ImagePickerAsset.duration (밀리초 · 영상이 아니면 null).
export function classifyDurationMs(
  durationMs: number | null | undefined,
): DurationFailure | null {
  // 값 없음 / 0 / NaN / 음수 = 판정 불가 → 통과 (fail-open, 헤더 참조).
  if (durationMs == null || !(durationMs > 0)) return null;
  if (durationMs < MIN_DURATION_MS) return 'tooShort';
  if (durationMs > MAX_DURATION_MS) return 'tooLong';
  return null;
}

// picker duration → ms 단일 변환점 (38-04 실측 이월 · 진단 D-1, 38-10 Task 0).
//
// expo-image-picker 의 ImagePickerAsset.duration 단위가 플랫폼마다 다르다:
//   - iOS/Android: 밀리초.
//   - 웹: 초 — node_modules/expo-image-picker/build/ExponentImagePicker.web.js
//     getVideoMetadata() 가 HTMLVideoElement.duration(초)을 그대로 준다(:137).
// 앱은 ms 로 읽으므로(classifyDurationMs · analyze.tsx 비트레이트) 웹에서는 8초 클립이
// 8ms 로 읽혀 tooShort 가 됐다(38-04 belle 항목 3 "영상이 너무 짧아요").
// Platform 은 import 하지 않고 os 를 인자로 받는다 — 이 파일의 node --test 성질 유지.
// 값 없음/0/NaN/음수는 그대로 흘려 classifyDurationMs 의 fail-open 에 맡긴다.
export function pickerDurationMs(
  duration: number | null | undefined,
  os: string,
): number | null | undefined {
  if (duration == null || !(duration > 0)) return duration;
  return os === 'web' ? duration * 1000 : duration;
}

// 결과 화면 첫 진입 코치마크 1회 플래그 helper (32-07 D-07, 시나리오 결과 단계).
// why: 결과 화면에 처음 들어온 사용자에게 "오늘 고칠 건 하나만"/"자세히는 펼쳐요"
// 코치마크를 1회만 노출하고, 이후에는 재노출하지 않기 위한 로컬 플래그.
// 서버 무접촉 — 기기 로컬 저장만 (신뢰 경계 내부, T-32-16 accept).
//
// 데이터소스 격리 원칙(onboarding.ts 정본): 화면은 AsyncStorage 직접 접근 대신 이
// lib helper 를 경유한다. '@sunity:' prefix 필수 — Firebase Auth backing store 와
// namespace 충돌 회피 (result.tsx '@sunity:keypoint_overlay_enabled' 선례와 정합).

import AsyncStorage from '@react-native-async-storage/async-storage';

const RESULT_COACHMARK_SEEN_KEY = '@sunity:result_coachmark_seen';

// 결과 코치마크를 이미 봤는지 조회. 값이 정확히 'true' 일 때만 "봤음".
// graceful: 읽기 실패(catch) 시 true 반환 — 읽기 오류가 코치마크 재노출 루프를
// 만들면 안 되므로 "본 것으로 간주"하는 방향으로 실패한다 (onboarding.ts T-26-02 정합).
export async function hasSeenResultCoachmark(): Promise<boolean> {
  try {
    const v = await AsyncStorage.getItem(RESULT_COACHMARK_SEEN_KEY);
    return v === 'true';
  } catch {
    return true;
  }
}

// 코치마크 노출(또는 닫기) 완료를 기록. fire-and-forget — UI 는 이미 코치마크를
// 닫았으므로 쓰기 결과를 기다리지 않는다. 실패해도 흐름 차단 금지 (graceful) —
// 다음 실행에 재노출될 뿐.
export function markResultCoachmarkSeen(): void {
  AsyncStorage.setItem(RESULT_COACHMARK_SEEN_KEY, 'true').catch(() => {
    /* graceful — 쓰기 실패해도 현재 세션은 이미 진행 */
  });
}

// ── belle 09-07 — 가로 전체화면 손가락 확대 안내 1회 플래그 ──────────────────
// why: 확대 카드가 엉뚱한 부위를 가리키는 문제를 "카드를 더 똑똑하게" 로 풀지 않고,
// 코칭이 결함을 짚는 순간 사용자가 직접 멈추고 손가락으로 확대해 보게 했다
// (belle 원문 "손가락으로 영상을 멈추고 확대할 수 있게"). 핀치 줌은 화면에 단서가
// 남지 않는 제스처라 처음 한 번은 말해 줘야 하고, 그 뒤에는 말하지 않아야 한다
// (영상 위 상시 문구 금지 — quick-260705-r6v).
// 위 RESULT_COACHMARK_SEEN_KEY 와 같은 계약: '@sunity:' prefix, 읽기 실패 = true
// (재노출 루프 금지), 쓰기 = fire-and-forget.
const FULLSCREEN_PINCH_HINT_SEEN_KEY = '@sunity:fullscreen_pinch_hint_seen';

export async function hasSeenFullscreenPinchHint(): Promise<boolean> {
  try {
    const v = await AsyncStorage.getItem(FULLSCREEN_PINCH_HINT_SEEN_KEY);
    return v === 'true';
  } catch {
    return true;
  }
}

export function markFullscreenPinchHintSeen(): void {
  AsyncStorage.setItem(FULLSCREEN_PINCH_HINT_SEEN_KEY, 'true').catch(() => {
    /* graceful — 쓰기 실패해도 현재 세션은 이미 안내를 닫았다 */
  });
}

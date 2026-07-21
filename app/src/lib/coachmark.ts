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

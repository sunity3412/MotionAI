// 온보딩 첫 실행 1회 플래그 helper (D-03, 26-UI-SPEC S1, 시나리오 0단계).
// why: 첫 실행 게스트에게 기대설정 튜토리얼을 1회만 노출하고, 스킵/완료 후에는
// 재노출하지 않기 위한 로컬 플래그. 서버 무접촉 — 기기 로컬 저장만 (신뢰 경계 내부).
//
// 데이터소스 격리 원칙(bodyProfile.ts:1-11): 화면은 AsyncStorage 직접 접근 대신
// 이 lib helper 를 경유한다. AsyncStorage read/write 선례 = result.tsx T-12-03-T4
// (@sunity: prefix — Firebase Auth backing store namespace 충돌 회피).

import AsyncStorage from '@react-native-async-storage/async-storage';

// '@sunity:' prefix 필수 — Firebase Auth backing store 와 namespace 충돌 0
// (result.tsx '@sunity:keypoint_overlay_enabled' 선례와 정합).
const TUTORIAL_SEEN_KEY = '@sunity:tutorial_seen';

// 첫 실행 튜토리얼을 이미 봤는지 조회. 값이 정확히 'true' 일 때만 "봤음".
// graceful: 읽기 실패(catch) 시 true 반환 — 읽기 오류가 홈 진입을 막거나 튜토리얼
// 재노출 루프를 만들면 안 되므로 "본 것으로 간주"하는 방향으로 실패한다 (T-26-02).
export async function hasSeenTutorial(): Promise<boolean> {
  try {
    const v = await AsyncStorage.getItem(TUTORIAL_SEEN_KEY);
    return v === 'true';
  } catch {
    return true;
  }
}

// 튜토리얼 시청(또는 스킵) 완료를 기록. fire-and-forget — UI 는 이미 다음 화면으로
// 진행하므로 쓰기 결과를 기다리지 않는다. 실패해도 흐름 차단 금지 (graceful).
export function markTutorialSeen(): void {
  AsyncStorage.setItem(TUTORIAL_SEEN_KEY, 'true').catch(() => {
    /* graceful — 쓰기 실패해도 현재 세션은 이미 진행. 다음 실행에 재노출될 뿐 */
  });
}

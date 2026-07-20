/**
 * Jest 설정 — 31-11 Task 1 (리뷰 M-03: typecheck 만으로는 상태 분기 검증 불충분).
 *
 * preset 'jest-expo' 는 Expo SDK 54 런타임(RN 0.81 / React 19.1)에 맞춘 transform 과
 * transformIgnorePatterns 를 제공한다. 이 preset 없이 순수 jest 로 RN 소스를 돌리면
 * node_modules 안의 ESM(RN/Expo 패키지)이 transform 되지 않아 즉시 깨진다.
 *
 * 버전 고정 근거 (belle 승인 핀 세트, 플랜 원문의 무핀 명령 아님):
 *   jest-expo@~54.0.17  — SDK 54 라인. latest(57.x)는 SDK 57 용이라 불일치.
 *   jest@~29.7.0        — jest-expo@54 가 jest 29 생태계(babel-jest/@jest/globals
 *                         /jest-environment-jsdom ^29)에 묶여 있다. jest 30 은 불일치.
 *   @testing-library/react-native@~13.3.3 — 14.x 는 peer 로 test-renderer@^1 이라는
 *                         네 번째 신규 패키지를 요구한다. 13.3.3 은 jest-expo@54 가
 *                         이미 벤더링한 react-test-renderer@19.1.0 을 그대로 쓴다.
 */
module.exports = {
  preset: 'jest-expo',
  testMatch: ['**/__tests__/**/*.test.{ts,tsx}'],
  // 테스트 파일 자체는 수집 대상에서 제외 (테스트가 테스트를 커버하는 착시 방지)
  collectCoverageFrom: ['src/**/*.{ts,tsx}', '!src/**/__tests__/**'],
};

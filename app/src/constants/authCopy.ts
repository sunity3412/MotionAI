// 계정 시스템 문구 단일 출처 (Phase 36).
//
// belle 2026-08-28: "디자인은 피그마를 따라줘" — 단, **카피는 논의 후 확정**.
// 그래서 지금 값은 전부 Figma 원문 그대로이고, 확정되면 **이 파일만** 고치면 된다.
// 화면 파일(index.tsx / auth/login.tsx / auth/signup.tsx)에는 한국어 리터럴을 두지 말 것.
//
// 출처 노드 (fileKey jrdI7kp245HkPfLB0nclsz):
//   인트로 1:142 · 로그인 1:550 · 가입 1:961
//
// ★belle 논의 대기 (36-CONTEXT D-07):
//   1. login.greetingWithName — Figma 는 "희연님, 오늘도 한 발 더!" 로 이름을 쓴다.
//      그런데 **최초 로그인 전에는 이름이 없다**(게스트는 displayName 없음). 그래서
//      지금은 greetingNoName 을 쓴다. 이름을 언제부터 알 수 있는지는 36-02 이후.
//   2. signup.subtitle "3초만에 가입하고..." 는 마케팅 톤이라, 현재 앱의 기대설정 톤
//      ("강사님을 대신하진 않아요" — 현장 리서치 반영)과 계열이 다르다. 튜토리얼 카피
//      충돌과 같은 건.

export const authCopy = {
  intro: {
    taglineTop: '프로의 동작과 비교하는',
    taglineBottom: '나만의 AI 운동 코치',
    cta: '시작하기',
    ctaLoading: '시작하는 중...',
    error: '연결에 실패했어요. 잠시 후 다시 시도해주세요.',
    haveAccount: '이미 계정이 있으신가요? ',
    loginLink: '로그인하기',
  },

  login: {
    // {name} 자리에 표시 이름을 넣는다. 이름을 모르면 greetingNoName.
    greetingWithName: '{name}님,\n오늘도 한 발 더!',
    greetingNoName: '오늘도\n한 발 더!',
    welcomeBack: 'WELCOME BACK',
    newHere: '처음 오셨나요? ',
    signupLink: '회원가입',
    back: '뒤로',
  },

  signup: {
    title: '시작해 볼까요?',
    subtitle: '3초만에 가입하고\n나만의 AI 코치를 만나보세요.',
    // 하단 약관 안내 — 링크 목적지는 belle 확인 대기 (36-CONTEXT D-07 #4).
    termsPrefix: '가입 시 서비스 ',
    termsOfService: '이용약관',
    termsMiddle: '과 ',
    privacyPolicy: '개인정보 처리방침',
    termsSuffix: '에 동의하게 됩니다.',
    back: '뒤로',
  },

  // 소셜 버튼 라벨. 가입 화면은 "{provider}로 시작하기" 전폭 버튼,
  // 로그인 화면은 아이콘만 (라벨은 접근성 label 로만 쓴다).
  providers: {
    kakao: { start: '카카오로 시작하기', login: '카카오로 로그인' },
    naver: { start: '네이버로 시작하기', login: '네이버로 로그인' },
    google: { start: 'Google로 시작하기', login: 'Google로 로그인' },
    apple: { start: 'Apple로 시작하기', login: 'Apple로 로그인' },
  },

  // 36-01 은 화면만 세우는 단계라 provider 가 아직 아무 데도 안 붙어 있다.
  // 눌렀을 때 조용히 아무 일도 안 나는 것이 가장 나쁘므로(Phase 33 "표시마다 답")
  // 준비 중이라고 말한다. 36-02~05 에서 이 분기는 사라진다.
  notWiredYet: '아직 연결 중이에요. 지금은 게스트로 시작할 수 있어요.',
} as const;

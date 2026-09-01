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
    // belle 2026-09-01: "시작하기" = 로그인 게이트로 이동 (08-30 "시작하기=게스트
    // 진입" 결정을 대체). CTA 가 비동기 작업을 잃어 ctaLoading/error 는 삭제 —
    // 문구는 login.guestCtaLoading/guestError 로 승계됐다.
    taglineTop: '프로의 동작과 비교하는',
    taglineBottom: '나만의 AI 운동 코치',
    cta: '시작하기',
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
    // belle 2026-09-01: 로그인 화면 = 앱의 첫 관문(로그인·회원가입·게스트 3구성) —
    // 08-30 "시작하기=게스트 진입" 결정을 대체한다. 게스트 로그인 행위가 인트로에서
    // 이 화면으로 옮겨오면서 로딩/오류 문구도 intro.ctaLoading/error 에서 그대로 승계.
    guestCta: '게스트로 시작하기',
    guestCtaLoading: '시작하는 중...',
    guestError: '연결에 실패했어요. 잠시 후 다시 시도해주세요.',
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

  legal: {
    back: '뒤로',
    // 법무 검토 전이라는 사실을 이용자에게도 숨기지 않는다. 검토가 끝나면
    // 문서 파일의 status 를 'reviewed' 로 바꾸면 이 배너가 사라진다.
    draftNotice:
      '파일럿 단계의 초안입니다. 법무 검토를 거쳐 확정되며, 변경 시 앱 공지로 알려드려요.',
  },

  // 마이 탭 계정 영역 (36-06).
  //
  // 이 화면이 필요한 이유: 로그인 입구가 인트로에만 있었는데, 게스트 세션은 영속이라
  // **한 번 들어오면 인트로를 다시 볼 일이 없다** — 즉 앱 안에서 로그인에 갈 길이
  // 아예 없었다. belle 2026-08-31 지시로 마이 탭에 입구를 낸다.
  //
  // 게스트 기록의 사실관계(문구가 이 사실을 넘지 않도록):
  //   · 게스트 = 익명 인증. 세션은 **그 기기에만** 저장된다 → 앱 삭제·기기 변경이면
  //     그 uid 로 다시 못 들어간다(기록에 닿을 길이 없다).
  //   · 로그인 = 그 익명 계정에 자격증명을 link → **uid 불변**이라 기록이 그대로 남고,
  //     다른 기기에서 같은 계정으로 들어오면 같은 uid 라 기록이 이어진다.
  account: {
    guestName: '게스트',
    loginAction: '로그인',
    // 카드 밑 한 줄. "지금 잃는다"가 아니라 "로그인하면 이어진다"로 쓴다.
    guestHint: '로그인하면 기기를 바꿔도 기록이 이어져요.',
    memberFallbackName: '회원',
    signOut: '로그아웃',
    signOutTitle: '로그아웃할까요?',
    // belle 2026-08-31: "다시 로그인 하면 당연히 보여야 하지 않을까...? 당연한건
    // 텍스트로 안 남겨도 될 것 같은데" — "기록은 계정에 남아 있어요 / 다시 로그인하면
    // 그대로 보여요"를 뺐다. 남긴 한 줄은 자명하지 않은 것: 로그인 화면으로 튕기는 게
    // 아니라 **게스트로 돌아온다**(이 앱만의 동작).
    signOutBody: '게스트로 돌아갑니다.',
    signOutCancel: '취소',
    signOutFailed: '로그아웃에 실패했어요. 잠시 후 다시 시도해주세요.',
  },

  // 아직 배선 안 된 provider (카카오·네이버). Apple 은 36-03 에서 배선 완료.
  // 눌렀을 때 조용히 아무 일도 안 나는 것이 가장 나쁘므로(Phase 33 "표시마다 답")
  // 준비 중이라고 말한다.
  notWiredYet: '아직 연결 중이에요. 지금은 게스트로 시작할 수 있어요.',

  // 로그인 결과 안내.
  // ★switched 는 조용히 넘어가면 안 된다 — 사용자 입장에서 기록이 사라진 것처럼 보인다.
  result: {
    linked: '로그인했어요. 그동안의 기록은 그대로예요.',
    signedIn: '로그인했어요.',
    switched:
      '이미 가입된 계정이에요. 그 계정으로 들어갑니다. 게스트로 보던 기록은 이 기기에서 더 이상 보이지 않아요.',
    failed: '로그인에 실패했어요. 잠시 후 다시 시도해주세요.',
  },
} as const;

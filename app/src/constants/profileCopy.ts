// 마이 탭 문구 단일 출처 (Phase 38 D-12) — authCopy.ts 규율 미러.
//
// 화면 파일((tabs)/profile.tsx · components/InstructorCodeSheet.tsx)에는 한국어 리터럴을 두지
// 않는다. 문구가 바뀌면 이 파일만.
//
// instructorCode — 수강생 강사 코드 입력(quick-260930-o0u, 38-DESIGN-v2 §W2 = Figma v2 옮김).
//   행 3상태(로딩 · 미연결 · 연결됨) · 입력 시트 · 강사 확인 · 토스트. 연결은 한 번뿐이고
//   바꾸려면 cs@sunity.ai(운영 해제 — backend/scripts/instructor_link.py). 크레딧 문구 없음
//   (D-13 — 실증은 돈을 받지 않는다). 이모지 없음.
//   명세 밖으로 더한 키 두 개:
//     · errors.failed — 알 수 없는 오류에 offline 문구를 쓰면 "인터넷을 확인" 이 거짓이 된다.
//     · alreadyLinked — 이미 연결된 사람이 다시 넣었을 때(SCENARIOS R4 "변경 막음").
//   `{name}` `{code}` 는 함수 인자 — 소비처가 JSX 로 해석하지 않는다.

import { supplierCopy } from './supplierCopy.ts';

export const profileCopy = {
  instructorCode: {
    label: '강사 코드',
    action: '입력하기',
    hint: '수업에서 받은 코드를 넣으면 강사님과 연결돼요.',
    linkedHint: '바꾸려면 cs@sunity.ai 로 알려 주세요.',
    a11yEmpty: '강사 코드 입력하기. 수업에서 받은 코드를 넣으면 강사님과 연결돼요.',
    a11yLinked: (name: string, code: string) => `강사 코드 ${code}, ${name} 강사님과 연결됨`,
    instructorTitle: (name: string) => `${name} 강사님`,
    codeLine: (code: string) => `코드 ${code}`,
    toastLinked: (name: string) => `${name} 강사님과 연결됐어요`,
    alreadyLinked: (name: string) => `이미 ${name} 강사님과 연결돼 있어요`,
    sheet: {
      title: '강사 코드 입력',
      body: '수업에서 받은 코드를 넣어 주세요. 대소문자는 상관없어요.',
      inputA11y: '강사 코드',
      submit: '확인',
      close: '닫기',
    },
    confirm: {
      notice: '연결은 한 번만 할 수 있어요. 나중에 바꾸려면 cs@sunity.ai 로 알려 주세요.',
      submit: '연결하기',
      cancel: '취소',
    },
    errors: {
      notFound: '없는 코드예요. 강사님께 받은 코드를 다시 확인해 주세요.',
      selfCode: '본인 코드는 넣을 수 없어요.',
      offline: supplierCopy.common.offline,
      failed: '연결하지 못했어요. 잠시 뒤 다시 시도해 주세요.',
    },
  },
} as const;

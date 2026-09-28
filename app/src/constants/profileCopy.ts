// 마이 탭 문구 단일 출처 (Phase 38 D-12) — authCopy.ts 규율 미러.
//
// 화면 파일((tabs)/profile.tsx)에는 한국어 리터럴을 두지 않는다. 문구가 바뀌면 이 파일만.
//
// instructorCode — 공급자 링크 페이지 "내 코드" 카드의 수요자 쪽 자리(D-12).
//   이 phase 는 **표시만**이다: 입력·귀속(수강생 ↔ 강사 연결)·크레딧 지급은 다음
//   (기획안 §C-2 (a), §10 단계 2 이후 belle 승인). 결제 SDK 없음(D-13 — 실증은 돈을
//   받지 않는다). 그래서 값은 항상 `미입력`이고 탭 동작이 없다. 빈 행에 "다음 행동"을
//   붙여 죽은 행으로 읽히지 않게 한다(UI-SPEC §Decisions 17 · Open for belle 4).
//
// 마이 화면 본체는 Figma(jrdI7kp245HkPfLB0nclsz)에 없고 탭(1:754)만 있다 — 문자열은
// 38-UI-SPEC §B 표(신규)가 정본이며 기존 InfoRow 양식(라벨 회색 · 값 굵게)을 재사용한다.

export const profileCopy = {
  instructorCode: {
    label: '강사 코드',
    value: '미입력',
    hint: '수업에서 받은 코드를 넣는 자리예요. 입력은 다음 업데이트에서 열려요.',
    a11y: '강사 코드 미입력. 입력은 다음 업데이트에서 열려요',
  },
} as const;

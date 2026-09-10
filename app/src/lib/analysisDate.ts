// 분석 시각 한 줄 표기 (quick-260910-hsk — belle 2026-09-10 승인).
//
// 순수 함수만 (react/react-native/expo 의존 0 — `tsc --noEmit` + `node --test` 로 검증).
// replaySettle.ts / playbackInvariant.ts 관례와 동일: 판정을 순수 모듈이 소유하고
// 화면(result.tsx)은 import 해 호출만 한다.
//
// 실행: node --test app/src/lib/__tests__/analysisDate.test.ts
//
// **왜 이 파일이 있는가**
// result.tsx 는 점수 원 아래 라벨을 `const DIAL_LABEL = 'Today'` 로 박아 뒀다.
// 날짜를 계산하지 않으므로 기록 탭에서 3일 전 분석을 열어도 "Today" 가 뜬다 —
// 표기 취향 문제가 아니라 거짓 정보를 보여주는 결함이다.
//
// **표기 규칙 (belle 2026-09-10 승인. belle 이 먼저 제안하고 내 추천안을 받았다)**
//   오늘     → `오늘 10:24`  하루에 여러 번 찍는다. 시각이 구분자다
//                            (기록 탭이 같은 이유로 시:분을 넣었다 — belle 08-31,
//                             quick-260831-lcc / history.tsx:20)
//   어제     → `어제 10:24`  같은 날 여러 건 문제는 어제에도 동일
//   2~6일 전 → `3일 전`      연습 앱에서 의미 있는 것은 "며칠 만이냐"다
//   7일 이상 → `9월 3일`     날짜로
//
// 경계를 3일이 아니라 7일에 둔 이유: 애플이 사진·메시지에서 "이번 주 안"까지
// 상대 표기를 쓴다. 3일에서 끊으면 "4일 전"이 갑자기 날짜가 돼 뚝 끊긴다.
//
// **경계 정의 (호출자가 임의로 바꾸지 말 것)**
// - "오늘/어제"는 경과 시간이 아니라 **달력 날짜** 기준이다. 로컬 타임존 자정으로
//   가른다 — 23:50 에 찍고 00:10 에 열면 20분 차이지만 날짜가 바뀌었으므로 "어제".
// - 일수 = floor((오늘 자정 − 그날 자정) / 86400000).
//   ※ DST 가 있는 타임존에서는 23/25시간 짜리 날이 생겨 floor 가 하루를 삼킬 수
//     있다. 파일럿 대상(KST)은 DST 가 없어 실제 피해가 없고, 규칙을 명시로 못박는 쪽을
//     택했다. DST 지역을 지원하게 되면 여기부터 고칠 것.
// - 미래 시각(기기 시계 오차로 createdAt 이 now 보다 뒤)은 "오늘"로 접는다.
//   "-1일 전" 같은 표기는 만들지 않는다.
// - createdAt 이 없거나(0/undefined) 유한수가 아니면 '' 를 돌려준다 —
//   화면은 그 줄을 그리지 않는다(빈 문자열 라벨).
//
// ★ 범위 밖: `(tabs)/index.tsx` 의 formatRelative 와 `(tabs)/history.tsx` 의
//   formatDate 는 이 모듈을 쓰지 않는다. 둘 다 근거가 주석에 박혀 있고
//   (Figma 1:719 "마지막 접속일 | 2일 전" / belle 08-31 시:분 지시), belle 이 그
//   두 화면의 표기 변경을 요청한 적이 없다. 승인된 출력을 과잉 일반화로 깨지 말 것.

const DAY_MS = 24 * 60 * 60 * 1000;

/** 상대 표기를 유지하는 상한 (이 값 이상이면 날짜로 적는다). */
export const ABSOLUTE_DATE_FROM_DAYS = 7;

/** 로컬 타임존 자정의 epoch ms. 달력 날짜 비교의 기준점. */
function startOfLocalDay(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}

function two(n: number): string {
  return String(n).padStart(2, '0');
}

/** 24시간제 `HH:MM` 2자리 고정 (history.tsx:20 과 같은 형식). */
function hhmm(d: Date): string {
  return `${two(d.getHours())}:${two(d.getMinutes())}`;
}

/**
 * 분석 시각 한 줄 표기.
 *
 * `nowMs` 를 인자로 받는다 — Date.now() 를 내부에서 부르면 테스트가 시계에
 * 의존하게 된다(검증축 2·4·7 은 특정 날짜 조합이 있어야 성립한다).
 *
 * 반환 예: `'오늘 10:24'` · `'어제 23:50'` · `'3일 전'` · `'9월 3일'` · `''`.
 */
export function formatAnalysisMoment(createdAtMs: number, nowMs: number): string {
  // 0 은 "없음"의 관용 표기다 — 호출부가 `createdAt ?? 0` 으로 넘긴다.
  if (!Number.isFinite(createdAtMs) || createdAtMs <= 0) return '';
  if (!Number.isFinite(nowMs)) return '';

  const created = new Date(createdAtMs);
  const now = new Date(nowMs);
  const diffDays = Math.floor(
    (startOfLocalDay(now) - startOfLocalDay(created)) / DAY_MS,
  );

  // diffDays < 0 = 미래 시각 → 오늘로 접는다.
  if (diffDays <= 0) return `오늘 ${hhmm(created)}`;
  if (diffDays === 1) return `어제 ${hhmm(created)}`;
  if (diffDays < ABSOLUTE_DATE_FROM_DAYS) return `${diffDays}일 전`;
  return `${created.getMonth() + 1}월 ${created.getDate()}일`;
}

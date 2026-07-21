// 재생 중 큐(D-18 자막) — 결함 구간 → 큐 윈도우 산출 순수 함수 (32-08).
//
// 순수 함수만 (react/expo-video/player 의존 0 — `tsc --noEmit` + `node --test` 검증).
// manualOffset.ts / alignmentWarp.ts 헤더 관례와 동일: 큐 타이밍(프레임→초 환산 +
// 윈도우 판정)을 순수 함수로 격리해 VideoCompare 의 재생 제어(seek/tick) 부작용과
// 분리한다.
//
// 데이터 원천 (32-RESEARCH §재생 중 큐 — 신규 타이머 0):
//   - 큐 타이밍은 기존 데이터로만: faultZoomComparisons[].userFrameIdx(학생 9fps
//     angles 도메인 프레임 인덱스) + 각자의 keypointReport.fps. 신규 측정·타이머 0 —
//     VideoCompare 의 기존 tick(100ms)이 activeCue 로 현재 구간을 판정한다.
//   - fps 는 호출부가 인자로 넘긴다 (9/18 하드코딩 금지, SP-6 — user 9fps / ref 18fps
//     공간 혼합 방지). 학생 프레임 인덱스는 학생 fps 로만 환산한다.
//
// 배선 계획 (32-11 — 이 파일은 순수 함수 + 계약만 제공, 배선/주입은 result.tsx):
//   - text 슬롯 ← records 의 cueLine(문구집 행동문, D-09 수치 0). cueLine 부재
//     legacy doc 은 기존 buildDeductionMarkers 행동구로 폴백(32-11 배선 책임).
//   - recordId 슬롯 ← records 의 recordId. fault zoom 카드 점프 · 오디오 mp3 조인
//     (32-12 B안 — cueId=recordId)의 안정 키 (리뷰 반영 — 정렬·필터·숨김 무관 조인).
//   - windowSec/maxCues ← D-17 확정 밀도(결함 구간당 1개)에서 파생한 상수.

/**
 * 큐 입력 (구조적 타입 — 32-09 방출 전이므로 최소 형상만 요구).
 * - userFrameIdx: 학생(user) 9fps angles 도메인 정수 프레임 인덱스.
 * - text: 오버레이 자막 (문구집 cueLine — 수치 0, D-09). 빈 문자열은 무시.
 * - points: SIGNED NEGATIVE 감점 (밀도 초과 시 |points| 큰 순 우선용). 부재=0 취급.
 * - recordId: 안정 조인 키 (있으면 그대로 승계).
 */
export type CueInput = {
  userFrameIdx: number;
  text: string;
  points?: number;
  recordId?: string;
};

/** 큐 윈도우 — 재생 시각 [startSec, endSec) 구간에서 text 를 오버레이. */
export type CueWindow = {
  startSec: number;
  endSec: number;
  text: string;
  recordId?: string;
};

/**
 * 결함 프레임 인덱스 쌍들 → 큐 윈도우 배열.
 *
 * startSec = userFrameIdx/userFps − windowSec/2 (0 클램프),
 * endSec = userFrameIdx/userFps + windowSec/2 (하한 클램프 시에도 종료는 고정 —
 * 결함 순간 이후 windowSec/2 까지 자막 유지). recordId 는 입력에서 그대로 승계.
 *
 * 무효 입력 방어 (크래시 0):
 *   - comparisons 부재/빈 배열 → []
 *   - userFps·windowSec 가 비유한/≤0 → [] (프레임↔초 환산 불가)
 *   - userFrameIdx 비정수/음수, text 빈 문자열 인 쌍은 개별 스킵
 *
 * 밀도 제한 (D-17): maxCues 가 유효(유한·≥0)하고 유효 쌍 수가 이를 초과하면
 * |points| 큰 순(감점 큰 순) 상위 maxCues 개만 남긴다. 반환은 재생 스캔 결정성을
 * 위해 startSec 오름차순.
 */
export function buildCueWindows(
  comparisons: readonly CueInput[] | null | undefined,
  userFps: number,
  windowSec: number,
  maxCues?: number,
): CueWindow[] {
  if (!Array.isArray(comparisons) || comparisons.length === 0) return [];
  if (!Number.isFinite(userFps) || userFps <= 0) return [];
  if (!Number.isFinite(windowSec) || windowSec <= 0) return [];
  const half = windowSec / 2;

  const scored: { win: CueWindow; score: number }[] = [];
  for (const c of comparisons) {
    if (!c) continue;
    const u = c.userFrameIdx;
    if (typeof u !== 'number' || !Number.isInteger(u) || u < 0) continue;
    if (typeof c.text !== 'string' || c.text.length === 0) continue;
    const center = u / userFps;
    const win: CueWindow = {
      startSec: Math.max(0, center - half),
      endSec: center + half,
      text: c.text,
    };
    if (c.recordId != null) win.recordId = c.recordId;
    // 감점 크기 = |points| (부재/비유한 = 0 → 밀도 초과 시 최저 우선순위).
    const score =
      typeof c.points === 'number' && Number.isFinite(c.points)
        ? Math.abs(c.points)
        : 0;
    scored.push({ win, score });
  }
  if (scored.length === 0) return [];

  let selected = scored;
  if (
    typeof maxCues === 'number' &&
    Number.isFinite(maxCues) &&
    maxCues >= 0 &&
    scored.length > maxCues
  ) {
    // 감점 큰 순(내림차순) 상위 N개. V8 stable sort — 동점은 입력 순 보존.
    selected = [...scored].sort((a, b) => b.score - a.score).slice(0, maxCues);
  }
  return selected.map((s) => s.win).sort((a, b) => a.startSec - b.startSec);
}

/**
 * 현재 재생 시각에 해당하는 큐 1개 또는 null.
 * 구간은 반개구간 [startSec, endSec). 겹치는 큐가 여럿이면 **시작이 늦은(더 정확한)**
 * 큐를 우선한다 (뒤에 진입한 결함이 현재 순간에 더 근접). 비유한 시각/빈 배열 → null.
 */
export function activeCue(
  windows: readonly CueWindow[] | null | undefined,
  currentSec: number,
): CueWindow | null {
  if (!Array.isArray(windows) || windows.length === 0) return null;
  if (!Number.isFinite(currentSec)) return null;
  let best: CueWindow | null = null;
  for (const w of windows) {
    if (!w) continue;
    if (currentSec >= w.startSec && currentSec < w.endSec) {
      if (best === null || w.startSec > best.startSec) best = w;
    }
  }
  return best;
}

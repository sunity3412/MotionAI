// 재생 중 큐(D-18 자막) — 결함 구간 → 큐 윈도우 산출 순수 함수 (32-08).
//
// 순수 함수만 (react/expo-video/player 의존 0 — `tsc --noEmit` + `node --test` 검증).
// manualOffset.ts / alignmentWarp.ts 헤더 관례와 동일: 큐 타이밍(프레임→초 환산 +
// 윈도우 판정)을 순수 함수로 격리해 VideoCompare 의 재생 제어(seek/tick) 부작용과
// 분리한다.
//
// 데이터 원천 (32-RESEARCH §재생 중 큐 — 신규 타이머 0):
//   - 큐 타이밍은 기존 데이터로만: record.atVideoSec(인증된 측정 순간, 초 —
//     centerSec 입력, belle 08-07 이후 기본) 또는 legacy 프레임 인덱스+fps.
//     신규 측정·타이머 0 — VideoCompare 의 기존 tick(100ms)이 activeCue 로
//     현재 구간을 판정한다.
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
 * - centerSec: **인증된 측정 순간**(record.atVideoSec, 학생 영상 도메인 초 —
 *   gbk 백엔드 산출). 있으면 우선 — fps 환산 없이 그대로 중심이 된다
 *   (belle 08-07: 큐는 감점의 제 순간에만 발화).
 * - userFrameIdx: 학생(user) 프레임 인덱스 (centerSec 부재 시의 legacy 앵커 —
 *   호출부가 넘긴 fps 로 초 환산).
 * - text: 오버레이 자막 (문구집 cueLine — 수치 0, D-09). 빈 문자열은 무시.
 * - points: SIGNED NEGATIVE 감점 (밀도 초과 시 |points| 큰 순 우선용). 부재=0 취급.
 * - recordId: 안정 조인 키 (있으면 그대로 승계).
 */
export type CueInput = {
  centerSec?: number;
  userFrameIdx?: number;
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
 * center = centerSec(인증 순간, 초 — 우선) 또는 userFrameIdx/userFps(legacy).
 * startSec = center − windowSec/2 (0 클램프),
 * endSec = center + windowSec/2 (하한 클램프 시에도 종료는 고정 —
 * 결함 순간 이후 windowSec/2 까지 자막 유지). recordId 는 입력에서 그대로 승계.
 *
 * 무효 입력 방어 (크래시 0):
 *   - comparisons 부재/빈 배열 → []
 *   - userFps·windowSec 가 비유한/≤0 → [] (프레임↔초 환산 불가)
 *   - centerSec 비유한/음수이고 userFrameIdx 도 비정수/음수, 또는 text 빈 문자열
 *     인 쌍은 개별 스킵
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
    if (typeof c.text !== 'string' || c.text.length === 0) continue;
    let center: number;
    if (
      typeof c.centerSec === 'number' &&
      Number.isFinite(c.centerSec) &&
      c.centerSec >= 0
    ) {
      center = c.centerSec;
    } else {
      const u = c.userFrameIdx;
      if (typeof u !== 'number' || !Number.isInteger(u) || u < 0) continue;
      center = u / userFps;
    }
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

// belle 08-07 #3 (quick-260807-fpw) — 인접 큐 체이닝 지평선(초). 음성 자연 종료
// 시점에 현재 재생시각 +이 값 이내에 시작하는 미발화 큐가 있으면 재개 없이 같은
// 멈춤에서 이어 발화한다 — 파워스핀 큐 2개 0.11초 간격의 "음성1 종료 → 0.1초 재생
// → 음성2 정지" 끊김 해소.
export const CUE_CHAIN_HORIZON_SEC = 1.0;

/**
 * 음성 자연 종료 시점의 체이닝 후보 큐 1개 또는 null (belle 08-07 #3).
 *
 * 후보 조건 (전부 만족):
 *   - recordId 보유 (발화 이력·mp3 조인의 안정 키 — 없는 윈도우는 체인 불가)
 *   - spokenRecordIds 에 없음 (이미 말한 큐 재발화 금지)
 *   - endSec > currentSec (이미 지나간 윈도우 제외)
 *   - startSec <= currentSec + horizonSec (이미 열려 있는 미발화 윈도우 포함 —
 *     파워스핀 겹침 윈도우가 정확히 이 모양)
 * 선택: startSec 최소(가장 이른 것), 동률은 입력 순 (first-wins).
 * 무효 입력 방어: currentSec/horizonSec 비유한·windows 부재 → null (크래시 0).
 */
export function nextChainedCue(
  windows: readonly CueWindow[] | null | undefined,
  currentSec: number,
  spokenRecordIds: ReadonlySet<string>,
  horizonSec: number,
): CueWindow | null {
  if (!Array.isArray(windows) || windows.length === 0) return null;
  if (!Number.isFinite(currentSec)) return null;
  if (!Number.isFinite(horizonSec) || horizonSec < 0) return null;
  let best: CueWindow | null = null;
  for (const w of windows) {
    if (!w) continue;
    if (w.recordId == null || spokenRecordIds.has(w.recordId)) continue;
    if (w.endSec <= currentSec) continue;
    if (w.startSec > currentSec + horizonSec) continue;
    if (best === null || w.startSec < best.startSec) best = w;
  }
  return best;
}

/**
 * belle 08-07 밤 ① (quick-260807-m63) — 스크럽 릴리스 지점에 **이미 열려 있는**
 * 윈도우의 recordId 집합. 릴리스 핸들러가 이 결과로 발화 이력(chainSpokenRef)을
 * 교체해, 열린 윈도우 = "통과한 것" 취급(즉시 발화 0 — 이력은 speak 만 차단하고
 * 자막 갱신은 유지하는 기존 관례) + 그 외 이력 전부 소거(스크럽으로 되감았으면
 * 릴리스 지점 이전 큐들은 재생 재통과 시 정상 발화 — replay 의미 보존).
 *
 * activeCue(겹침 시 승자 1개)와 달리 currentSec 을 포함하는 **모든** 윈도우를
 * 수집한다 — 겹침 구간(파워스핀 형상)에 릴리스했을 때 승자 하나만 마킹하면
 * 나머지 겹침 윈도우가 진행 중 전환·체인에서 발화한다. 릴리스 이후 "새로 진입"
 * 한 윈도우만 발화한다는 원칙.
 *
 * 구간은 반개구간 [startSec, endSec). recordId 없는 윈도우(고아 큐)는 스킵.
 * 무효 입력 방어: 비유한 currentSec·windows 부재/빈 배열 → [] (크래시 0,
 * activeCue 방어 관례). 반환 순서는 입력 순 (Set 시드 용도 — 결정성 유지).
 */
export function openCueRecordIds(
  windows: readonly CueWindow[] | null | undefined,
  currentSec: number,
): string[] {
  if (!Array.isArray(windows) || windows.length === 0) return [];
  if (!Number.isFinite(currentSec)) return [];
  const ids: string[] = [];
  for (const w of windows) {
    if (!w) continue;
    if (w.recordId == null) continue;
    if (currentSec >= w.startSec && currentSec < w.endSec) ids.push(w.recordId);
  }
  return ids;
}

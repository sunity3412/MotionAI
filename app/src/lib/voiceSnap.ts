// 음성 멈춤 동안 기준(우) 패널 짝 프레임 스냅 맵 — 순수 빌더 (quick-260807-iwp).
//
// 순수 함수만 (react/expo-video/player 의존 0 — `tsc --noEmit` + `node --test` 검증).
// cueTrack.ts 헤더 관례와 동일: recordId→기준 도메인 초 조인을 순수 함수로 격리해
// VideoCompare 의 재생 제어(seek/tick) 부작용과 분리한다.
//
// belle 08-07 실기기: "정은지 선수 영상이 음성이랑 안 맞는다. 학생 영상은 맞는데" —
// 학생 패널은 잰 순간(record.atVideoSec)에 정지해 맞는 게 보장되지만, 기준 패널은
// 시작점 오프셋만 맞춘 시간 동기 위치라 자세 짝이 아니다. 발화 멈춤 동안 우측을
// record 의 짝 시각으로 seek 하기 위한 recordId→초 맵을 여기서 만든다.
//
// 스냅 시각의 유일한 정당 소스 = FaultZoomComparison.refVideoSec (33-G F-3 백엔드
// 방출 — 기준 영상 도메인 초, types/analysis.ts 계약). ⚠ refFrameIdx /
// keypointReport.fps 로 초를 **재계산하지 말 것** — rep 프레임 공간(18fps)과 영상
// 초 공간(9fps)의 불일치가 F-3("참고하세요 페어가 다른 순간")의 실 원인이었다.
// refVideoSec 부재 = refMatched=false(기준 대응 실패) 또는 legacy doc → 스냅 생략
// (순간 날조 0 — 없는 짝을 지어내지 않는다).
//
// 배선 (VideoCompare cueRefSnapSecs prop):
//   - result.tsx 가 records + matchZoomForRecord(recordId 원자 조인 단일 출처)로
//     entries 를 만들어 이 빌더를 호출한다 — 신규 조인 규칙 0.
//   - 값 소비는 VideoCompare 의 음성 멈춤 스냅/복원 헬퍼 (발화 pause 중에만 seek).

/**
 * recordId → refVideoSec(기준 영상 도메인 초) 스냅 맵.
 *
 * 등재 조건 (전부 만족):
 *   - recordId 가 비어있지 않은 문자열 (조인 키 없는 스냅 금지 — DeductionRecord
 *     .recordId 는 `string | null | undefined` 계약이라 null 도 방어)
 *   - refVideoSec 이 유한 수이고 >= 0 (NaN/Infinity/음수 = 무효 — fabricate 0)
 * 중복 recordId 는 first-wins (결정성). 입력 null/undefined/빈 배열/null 원소는
 * 빈 맵/스킵 (크래시 0 — cueTrack buildCueWindows 방어 관례).
 */
export function buildRefSnapSecs(
  entries:
    | readonly { recordId?: string | null; refVideoSec?: number }[]
    | null
    | undefined,
): Record<string, number> {
  const out: Record<string, number> = {};
  if (!Array.isArray(entries)) return out;
  for (const e of entries) {
    if (!e) continue;
    const id = e.recordId;
    if (typeof id !== 'string' || id.length === 0) continue;
    const sec = e.refVideoSec;
    if (typeof sec !== 'number' || !Number.isFinite(sec) || sec < 0) continue;
    if (Object.prototype.hasOwnProperty.call(out, id)) continue; // first-wins
    out[id] = sec;
  }
  return out;
}

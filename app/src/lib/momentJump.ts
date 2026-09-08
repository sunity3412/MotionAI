// 손가락 확대 뷰어가 뛰어갈 "순간" 목록 — 순수 빌더 (belle 09-07).
//
// belle 09-07 승인 방향: 확대 카드가 맞는 부위를 가리키게 만드는 대신, 코칭이 결함을
// 짚는 그 순간에 사용자가 **손가락으로 영상을 멈추고 확대해** 직접 본다. 이 모듈은
// 그 화면이 필요로 하는 유일한 데이터 — "어느 초로 뛰어갈 수 있는가" — 를 만든다.
// 화면/제스처/렌더 의존 0 (react·react-native·expo import 금지 — `tsc --noEmit` +
// `node --test` 로만 검증되는 순수 계층, voiceSnap.ts / cueTrack.ts 관례).
//
// 순간의 정당 소스는 **저장값 2개뿐**이다. 앱은 초를 한 번도 계산하지 않는다:
//   - 학생 측 초 = DeductionRecord.atVideoSec (types/analysis.ts:833 — 백엔드가
//     파이프라인 fps 로 나눠 준 초). 부재 = 순간을 신뢰 있게 정할 수 없는 criterion
//     (reach·whole-score fallback·vision 주입 split) 또는 legacy doc → 그 record 는
//     목록에서 **통째로 빠진다**. 없는 순간을 지어내 보내면 사용자가 엉뚱한 곳을
//     확대하고 "확대해 봤는데 아무것도 없다"가 된다 (fabricate 0).
//   - 오른쪽 패널 초 = FaultZoomComparison.refVideoSec 을 voiceSnap.buildRefSnapSecs 가
//     검증해 낸 값. ⚠ `refFrameIdx / keypointReport.fps` 로 초를 **재계산하지 말 것** —
//     rep 프레임 공간과 영상 초 공간이 다르다 (docs/contract.md:1961-1962,
//     types/analysis.ts:518-529). 엘보 fixture 가 그 오차의 크기를 보여준다:
//     userVideoSec 11.111 ↔ refVideoSec 14.889 = 3.78초 차이.
//
// 조인 규칙 신설 0 — record→카드는 deductionLabels.matchZoomForDeductionRecord,
// 카드→기준초는 voiceSnap.buildRefSnapSecs, 번호는 deductionLabels
// .buildDeductionMarkers 를 그대로 소비한다 (규칙 사본 금지, 33-12 A-5 seam #1).

import type {
  DeductionRecord,
  FaultZoomComparison,
  KeypointName,
} from '../types/analysis';
import {
  buildDeductionMarkers,
  matchZoomForDeductionRecord,
} from './deductionLabels.ts';
import { buildRefSnapSecs } from './voiceSnap.ts';

/**
 * 사용자가 멈추고 확대해 볼 수 있는 한 순간.
 *
 * - `recordId` — 감점 record 의 안정 조인 키 (contract.md §12.3 각인). 화면이
 *   시트 행·마커와 같은 항목을 가리키는 데 쓴다.
 * - `number` — 감점 표시 번호. 재생바 틱(buildDeductionTicks)·내역 행 원문자와
 *   **같은 축**이다 (아래 buildMomentTargets 주석의 입력 순서 규약 참조).
 * - `userSec` — 학생 영상에서 뛰어갈 초 (저장된 atVideoSec 그대로).
 * - `refSec` — 오른쪽 패널 영상에서 뛰어갈 초. null = 그 카드가 짝을 못 찾았다.
 * - `certified` — refSec 이 실제 매칭된 짝인가. false 면 화면은 기준 패널을 짝인
 *   척 세우지 말고 정직 문구를 대신 보여준다 (belle 규칙: 양쪽이 같은 순간이어야).
 */
export type MomentTarget = {
  recordId: string;
  number: number;
  userSec: number;
  refSec: number | null;
  certified: boolean;
};

/**
 * 감점 record 목록 → 확대 뷰어가 뛰어갈 순간 목록.
 *
 * **입력 순서 규약** — `records` 는 화면이 번호를 매길 때 쓴 **그 배열**이어야 한다
 * (result.tsx 는 sortDeductionRecordsByMoment 로 시간순 정렬한 배열을
 * buildDeductionMarkers 에 넘긴다). 여기서 다시 정렬하면 번호 축이 화면과 갈라진다
 * — 정렬은 표시 계층 소관이고 이 함수는 순서를 보존만 한다 (belle 08-07 #1).
 *
 * 등재 조건 (전부 만족해야 목록에 오른다):
 *   1) buildDeductionMarkers 가 번호를 준 record — 번호 null(투영 실패·전부 선점)
 *      은 재생바 틱에도 안 실리므로(buildDeductionTicks 동일 규칙) 여기서도 뺀다.
 *   2) `recordId` 가 비어있지 않은 문자열 — 조인 키 없는 순간 금지
 *      (buildRefSnapSecs 와 동일 방어, DeductionRecord.recordId 는 optional 계약).
 *   3) `atVideoSec` 이 유한 수이고 >= 0 — 비유한/부재는 순간 미확정이라 제외하고,
 *      음수는 재생 위치가 될 수 없다 (buildRefSnapSecs 의 sec>=0 선례).
 * 중복 recordId 는 first-wins (결정성 — buildRefSnapSecs 와 같은 규칙).
 *
 * **mode 분기 없음** (belle 09-07 감사 수리). 종전에는 mode3 에서 refSnapSecs 를
 * 통째로 버렸고, 근거로 "mode3 는 기준 영상 자체가 없다"고 적었다. 그 전제가 코드와
 * 어긋난다 — mode3 의 오른쪽 패널은 지난 분석 영상이고(result.tsx rightUrl =
 * prev myVideoUrl, 라벨 '지난 영상'), 백엔드도 mode3 카드를 mode1 과 **같은 코어**로
 * 만들어 refVideoSec 을 싣는다(pipeline `_build_mode3_fault_zoom_comparisons` →
 * `_render_fault_zoom`). 무엇보다 같은 화면의 음성 큐 경로(result.tsx cueRefSnapSecs
 * → VideoCompare snapRightToCuePair)에는 mode 게이트가 **한 줄도 없어** 이미 mode3
 * 에서 오른쪽을 짝 프레임에 세우고 있었다. 여기만 버리면 같은 감점을 시트로 여느냐
 * 음성 pill 로 여느냐에 따라 오른쪽 프레임이 달라진다 — 한 항목에 두 개의 답.
 * 그래서 게이트를 걷어내고 **두 진입점을 같은 규칙으로** 맞춘다.
 *
 * @param faultJoints - visionVeto.faultJoints. source='vision' record 의 카드 조인에
 *   쓰인다 (matchZoomForDeductionRecord 계약). 부재면 vision record 는 criterion 키
 *   일치로만 카드를 얻는다 — 화면은 result.tsx 의 vetoFaultJoints 를 그대로 넘긴다.
 */
export function buildMomentTargets(
  records: readonly DeductionRecord[] | null | undefined,
  zooms: readonly FaultZoomComparison[] | null | undefined,
  faultJoints?: readonly KeypointName[],
): MomentTarget[] {
  if (!Array.isArray(records) || records.length === 0) return [];

  // null/undefined 원소는 번호 부여 전에 걷어낸다 — 뒤 단계(투영·조인)가 전부
  // record 필드를 직접 읽는다. 걷어낸 배열 하나로 번호·조인·산출을 모두 돌려야
  // index 정합이 유지된다 (buildCueWindows 방어 관례, 크래시 0).
  const list = records.filter((r): r is DeductionRecord => r != null);
  if (list.length === 0) return [];

  // 번호 단일 출처 — 사본 금지. buildDeductionMarkers 는 배열을 변형하지 않지만
  // readonly 계약을 유지하려고 복제본을 넘긴다.
  const { recordNumbers } = buildDeductionMarkers([...list], faultJoints);

  // 기준 초 맵: recordId → refVideoSec.
  // entries 조립은 result.tsx cueRefSnapSecs 와 **동형**이다 (조인 규칙 신설 0).
  // 두 진입점이 같은 맵을 만들어야 같은 감점에서 같은 오른쪽 프레임이 나온다.
  const refSnapSecs = buildRefSnapSecs(
    list.map((rec) => ({
      recordId: rec.recordId,
      refVideoSec: matchZoomForDeductionRecord(rec, faultJoints, zooms)
        ?.refVideoSec,
    })),
  );

  const out: MomentTarget[] = [];
  const seen = new Set<string>();
  list.forEach((rec, i) => {
    const number = recordNumbers[i];
    if (number == null) return;
    const recordId = rec.recordId;
    if (typeof recordId !== 'string' || recordId.length === 0) return;
    if (seen.has(recordId)) return; // first-wins
    const userSec = rec.atVideoSec;
    if (typeof userSec !== 'number' || !Number.isFinite(userSec) || userSec < 0) {
      return; // 순간 미확정 record — 초를 지어내지 않는다
    }
    seen.add(recordId);
    const snapped = Object.prototype.hasOwnProperty.call(refSnapSecs, recordId)
      ? refSnapSecs[recordId]
      : null;
    out.push({
      recordId,
      number,
      userSec,
      refSec: snapped,
      certified: snapped != null,
    });
  });
  return out;
}

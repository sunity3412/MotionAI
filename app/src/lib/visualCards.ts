/**
 * Phase 31 — 참고코너 카드 상태 파생 순수 로직.
 *
 * 이 모듈은 **순수 함수만** 둔다 (React/React Native import 0). 이유는 리뷰 M-03 —
 * 상태 분기(legacy 부재/failed/pending 신선/pending 만료/done)는 typecheck 로 검증되지
 * 않고, 화면에 붙은 채로는 렌더 환경 없이 테스트할 수 없다. 여기로 떼어내면 jest 로
 * 전이표를 통째로 고정할 수 있다.
 *
 * 계약: docs/contract.md §2 "visual 교정 시각물 필드" / §4.
 *
 * **import 0 (의존성 없음)** — 이건 스타일 취향이 아니라 검증 가능성 요건이다.
 * jest 도입이 철회되면서(devDependency 1,120개) 이 모듈의 검증 수단은 plain-node
 * (`node --test`, Node 24 네이티브 타입 스트리핑)뿐이다. 여기서 `./api` 를 import 하면
 * firebase 런타임이 딸려 들어와 plain-node 로는 로드 자체가 불가능해진다.
 * 따라서 오류 판별은 아래 apiErrorCode 처럼 **구조적(structural)** 으로 한다.
 */

/** 카드 표시 상태. 'hidden' = 카드 자체를 렌더하지 않음 (D-08 조용한 폴백). */
export type VisualCardState = 'hidden' | 'pending' | 'done';

/**
 * pending 타임아웃 — 표시 폴백 상한.
 *
 * **주의: 이 타임아웃은 서버 잡을 취소하지 않는다** (리뷰 L-04). 순수하게 "언제까지
 * 로딩 자리표시를 보여줄 것인가"만 정한다. 무한 pending 고아 문서를 사용자에게
 * 영원히 로딩으로 보여주지 않으려는 표시 계층 방어일 뿐, 백엔드 잡은 계속 살아 있다.
 * 실제 고아 잡의 운영 가시성은 backend/scripts/list_stuck_visual_jobs.py 담당.
 */
export const CORRECTED_POSE_PENDING_TIMEOUT_MS = 180_000; // 3분 — 이미지 생성 수초~수십초
export const ROTATION_PENDING_TIMEOUT_MS = 1_500_000; // 25분 — worker 폴링 상한 20분(31-09 MAX_POLLS) + 여유

/**
 * 카드 상태 파생.
 *
 * - status 부재(legacy doc) / 'failed' → 'hidden'. 계약상 둘은 동일 처리다 —
 *   모더레이션 차단(실측 ~10%)을 에러로 노출하지 않는 조용한 폴백(D-08).
 * - 'pending' + 전용 timestamp 기준 경과 > timeout → 'hidden' (고아 방어).
 * - updatedAtMs 가 없거나 비정상이면 타임아웃 판정을 포기하고 'pending' 유지 —
 *   시계 정보가 없다는 이유로 살아 있는 잡의 자리표시를 지우지 않는다.
 *
 * updatedAtMs 는 **각 필드 전용**(correctedPoseUpdatedAtMs / rotationUpdatedAtMs)이어야
 * 한다 (리뷰 H-06). 공용 updatedAt 은 무관한 write 로도 갱신돼 pending 수명을
 * 잘못 늘린다.
 */
export function visualCardState(
  status: 'pending' | 'done' | 'failed' | undefined,
  updatedAtMs: number | undefined,
  nowMs: number,
  timeoutMs: number,
): VisualCardState {
  if (status === 'done') return 'done';
  if (status !== 'pending') return 'hidden'; // 부재 + 'failed'
  if (typeof updatedAtMs !== 'number' || !Number.isFinite(updatedAtMs)) {
    return 'pending';
  }
  return nowMs - updatedAtMs > timeoutMs ? 'hidden' : 'pending';
}

/**
 * 프레임 공간 매핑 — keypointReport(9fps angles 도메인) 인덱스를 joints3d 프레임
 * 공간으로 옮긴다. 두 배열의 프레임 수가 다를 수 있어 비율로 환산 후 clamp 한다.
 *
 * 비정상 입력(음수/비정수/빈 공간)은 null — 0 으로 폴백하지 않는다. 0 폴백은
 * "첫 프레임"이라는 그럴듯한 자세를 그려내서, 잘못된 순간을 사용자가 자기 결함으로
 * 오인하게 만든다. 못 고르면 안 그리는 편이 정직하다.
 */
export function mapFrameIdx(
  idx: number,
  fromFrames: number,
  toFrames: number,
): number | null {
  if (!Number.isInteger(idx) || idx < 0) return null;
  if (!Number.isInteger(fromFrames) || fromFrames <= 0) return null;
  if (!Number.isInteger(toFrames) || toFrames <= 0) return null;
  if (idx >= fromFrames) return null;
  if (fromFrames === toFrames) return idx;
  const scaled = Math.round((idx / fromFrames) * toFrames);
  return Math.min(Math.max(scaled, 0), toFrames - 1);
}

/** 뷰어가 그릴 좌/우 프레임 쌍. */
export interface CompareFrames {
  userIdx: number;
  refIdx: number;
}

/**
 * 비교 뷰어 프레임 선택 — top-1 comparison 기준.
 *
 * `refMatched !== true` 면 null 을 반환해 **뷰어를 숨긴다**. DTW 대응은 mode1
 * reference 에만 성립하며(Pitfall 6), 대응이 없는데 학생 자세만 그려놓고 "비교"라
 * 부르는 것은 거짓이다. 31-08 이 같은 근거로 refPose=null → 숨김을 택했다.
 *
 * 주: app/src/types/analysis.ts 의 userFrameIdx 주석(31-04 작성)은 refMatched=false
 * 를 "학생 단독 렌더"로 서술하지만, 이후 31-08/31-11 에서 숨김으로 확정됐다.
 * 구현 정본은 여기이며 해당 주석은 후속 정정 대상 (31-11 SUMMARY 기록).
 */
export function pickCompareFrames(
  comparisons:
    | { userFrameIdx?: number; refFrameIdx?: number; refMatched?: boolean }[]
    | undefined,
): CompareFrames | null {
  const top = comparisons?.[0];
  if (!top) return null;
  if (top.refMatched !== true) return null;
  const { userFrameIdx, refFrameIdx } = top;
  if (!Number.isInteger(userFrameIdx) || !Number.isInteger(refFrameIdx)) {
    return null;
  }
  if ((userFrameIdx as number) < 0 || (refFrameIdx as number) < 0) return null;
  return { userIdx: userFrameIdx as number, refIdx: refFrameIdx as number };
}

/**
 * 오류에서 계약상 `code` 를 구조적으로 읽는다.
 *
 * 원안은 `e instanceof ApiError` 였다. 구조적 검사로 바꾼 이유는 위 모듈 주석대로
 * import 0 을 지켜야 plain-node 검증이 가능하기 때문이다. 트레이드오프를 명시하면:
 * `{code:'daily_limit'}` 형태의 아무 객체나 통과할 수 있다. 실제로 이 값들은 전부
 * api.ts 의 ApiError 에서만 오므로 파일럿 범위에서 위험은 낮지만, instanceof 대비
 * 약한 보장인 것은 사실이다. 테스트 러너가 복원되면 instanceof 로 되돌릴 것.
 */
function apiErrorCode(e: unknown): string | null {
  if (typeof e !== 'object' || e === null) return null;
  const code = (e as { code?: unknown }).code;
  return typeof code === 'string' ? code : null;
}

/**
 * 일일 생성 한도 초과 (429 daily_limit). 사용자 3건/일 + 전역 30건/일, KST 자정
 * 리셋 (contract.md §2). 이 경우만 사용자에게 인라인으로 알린다 — 남은 오류는
 * 조용히 처리(D-08).
 */
export function isDailyLimit(e: unknown): boolean {
  return apiErrorCode(e) === 'daily_limit';
}

/** 기능 플래그 OFF (503 feature_disabled) — 조용히 버튼만 원복. */
export function isFeatureDisabled(e: unknown): boolean {
  return apiErrorCode(e) === 'feature_disabled';
}

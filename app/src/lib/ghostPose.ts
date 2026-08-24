// 잔상 = 학생 실측 자세 데이터 렌더 (quick-260824-jw4, belle 08-24 승인).
//
// 배경 (원장 = .planning/quick/260824-gt1-ghost-noarrow-gemini-belle/PREDICTION.md):
// 잔상을 생성 모델로 그리는 시도 8라운드 전건 기각 — 모델은 "얼마나"(각도·크기)를
// 프롬프트로 지키지 못한다는 실측. belle: "뭐가 됐든 일러스트 기능이 완료되면 돼,
// 우리가 파워스핀만 하는 것도 아니고" → 잔상의 정보 원천을 그림이 아니라 **데이터**
// 로 전환한다: 감점 record 의 측정 순간(atVideoSec)에 학생 keypointReport 를 잘라
// 스켈레톤 잔상으로 그린다. 각도가 좌표라 어긋날 수 없고, 학생마다 자기 잔상이며
// ("내가 캡처한 거 그대로"의 일반화), keypointReport·atVideoSec 은 기존 doc 에 이미
// 있어 **소급 적용**된다. 신규 백엔드·계약 변경 0.
//
// 좌표 계약:
//   - keypointReport.data = flat T×J×2 (px, 화면 y-down) / confidence = flat T×J.
//   - 정규화 = 골반(양 힙 중점) 원점, 몸통 길이(골반→어깨 중점) = 1.
//   - 그림 정렬 = GHOST_ALIGN 메타(에셋별): 그림 속 골반 위치·몸통 길이·몸통 방향.
//     몸통 방향을 맞춰 회전시키므로 도립 그림(파워스핀)에도 다리가 몸통 기준
//     올바른 곳에 앉는다.
//
// fail-closed 전 축 (잔상 없음 = 그림만, 기존 겉모습 회귀 0):
//   메타 없는 에셋 / report 부재·형상 불일치 / 측정 순간 없는 record 뿐(split_angle
//   등 vision 주입) / 힙·어깨 신뢰도 미달 / 몸통 길이 0 / 통과 관절 < MIN_POINTS.
//
// RN import 0 — node --test 실행 가능 (progressCaption 선례).

/** 관절 신뢰도 게이트 — 각도 미표시 게이트와 같은 선(conf<0.5 게이트 선례). */
export const GHOST_CONF_MIN = 0.5;

/** 골반·어깨 4점 외에 최소 이만큼은 있어야 잔상이 자세로 읽힌다. */
export const GHOST_MIN_POINTS = 6;

/** 스켈레톤 변 — 양 끝 관절이 다 통과했을 때만 그린다. */
export const GHOST_EDGES: ReadonlyArray<readonly [string, string]> = [
  ['left_shoulder', 'right_shoulder'],
  ['left_hip', 'right_hip'],
  ['left_shoulder', 'left_hip'],
  ['right_shoulder', 'right_hip'],
  ['left_hip', 'left_knee'],
  ['left_knee', 'left_ankle'],
  ['right_hip', 'right_knee'],
  ['right_knee', 'right_ankle'],
  ['left_shoulder', 'left_elbow'],
  ['left_elbow', 'left_hand'],
  ['right_shoulder', 'right_elbow'],
  ['right_elbow', 'right_hand'],
];

export interface GhostAlignMeta {
  /** 그림 속 골반(양 힙 중점) 위치 — 폭·높이 비율. */
  pelvisFx: number;
  pelvisFy: number;
  /** 그림 속 몸통 길이(골반→어깨 중점) — 높이 비율. */
  torsoF: number;
  /** 그림 속 몸통 방향(골반→어깨 중점, 화면 좌표 atan2 도) — 잔상 회전 정렬 기준. */
  torsoAngleDeg: number;
  /** 그림과 학생 영상의 좌우가 뒤집혀 보이면 true (시뮬 실측으로 정한다). */
  flipX?: boolean;
}

/**
 * 에셋별 정렬 메타 — 값은 에셋 이미지 실측 (좌표는 격자 오버레이 측정).
 * 등재 = 시뮬 실물 확인 후에만 (grammar-approval-is-not-asset-approval).
 * 미등재 에셋 = 잔상 없음 (fail-closed).
 */
export const GHOST_ALIGN: Readonly<Record<string, GhostAlignMeta>> = {
  // 등재 0 (2026-08-24 belle 기각) — 파워스핀 실렌더에서 원시 스켈레톤 잔상이
  // "실존하지 않는 자세"로 읽혔다: 몸통 정렬 회전이 세계 방향을 바꾸고, 신뢰도
  // 게이트로 사지가 빠져 몸이 깨져 보인다. 잔상은 illustrationHow 의 rotate
  // 앵커(그림 자신의 사지를 실측 각도만큼 회전)로 그린다. 이 lib 는 순간 선택
  // (pickGhostMomentSec)과 추출 기하가 검증돼 있어 보존 — 재등재는 belle 실물
  // 승인 후에만.
};

export interface GhostPoint {
  key: string;
  x: number;
  y: number;
}

export interface GhostPose {
  /** 몸통 정렬까지 끝난 정규화 좌표 — 골반 원점, 몸통 길이 1, 화면 y-down. */
  points: ReadonlyArray<GhostPoint>;
}

/**
 * KeypointReport 의 소비 필드만 — joints 는 넓은 string 으로 받는다 (계약 타입
 * KeypointName[] 이 그대로 대입 가능, 테스트 합성 report 도 수용).
 */
export interface KeypointReportLike {
  fps: number;
  frames: number;
  joints: readonly string[];
  data: readonly number[];
  confidence: readonly number[];
}

/** record 에서 잔상 순간을 고른다 — 순간이 있는(프레임 측정) 첫 record. */
export function pickGhostMomentSec(
  records: ReadonlyArray<{ atVideoSec?: number | null } | null | undefined>,
): number | null {
  for (const rec of records) {
    const sec = rec?.atVideoSec;
    if (typeof sec === 'number' && Number.isFinite(sec) && sec >= 0) return sec;
  }
  return null;
}

/**
 * 측정 순간의 학생 자세를 정규화 좌표로 추출. 실패 축은 전부 null (fail-closed).
 * 반환 좌표는 아직 그림에 정렬되지 않은 원시 정규화 (torsoAngleDeg 포함).
 */
export function extractGhostPose(
  report: KeypointReportLike | null | undefined,
  atVideoSec: number,
): { points: GhostPoint[]; torsoAngleDeg: number } | null {
  if (report == null) return null;
  const { fps, frames, joints, data, confidence } = report;
  if (
    typeof fps !== 'number' ||
    !Number.isFinite(fps) ||
    fps <= 0 ||
    typeof frames !== 'number' ||
    !Number.isInteger(frames) ||
    frames <= 0 ||
    !Array.isArray(joints) ||
    joints.length === 0 ||
    !Array.isArray(data) ||
    data.length !== frames * joints.length * 2 ||
    !Array.isArray(confidence) ||
    confidence.length !== frames * joints.length
  )
    return null;
  if (!Number.isFinite(atVideoSec) || atVideoSec < 0) return null;

  const J = joints.length;
  const idx = Math.min(frames - 1, Math.max(0, Math.round(atVideoSec * fps)));

  const raw = new Map<string, { x: number; y: number }>();
  for (let j = 0; j < J; j += 1) {
    const conf = confidence[idx * J + j];
    if (typeof conf !== 'number' || !(conf >= GHOST_CONF_MIN)) continue;
    const x = data[(idx * J + j) * 2];
    const y = data[(idx * J + j) * 2 + 1];
    if (
      typeof x !== 'number' ||
      typeof y !== 'number' ||
      !Number.isFinite(x) ||
      !Number.isFinite(y)
    )
      continue;
    raw.set(joints[j], { x, y });
  }

  const lh = raw.get('left_hip');
  const rh = raw.get('right_hip');
  const ls = raw.get('left_shoulder');
  const rs = raw.get('right_shoulder');
  if (!lh || !rh || !ls || !rs) return null;

  const pelvis = { x: (lh.x + rh.x) / 2, y: (lh.y + rh.y) / 2 };
  const shoulderMid = { x: (ls.x + rs.x) / 2, y: (ls.y + rs.y) / 2 };
  const torso = Math.hypot(shoulderMid.x - pelvis.x, shoulderMid.y - pelvis.y);
  if (!(torso > 1e-6)) return null;

  const points: GhostPoint[] = [];
  for (const [key, p] of raw) {
    points.push({
      key,
      x: (p.x - pelvis.x) / torso,
      y: (p.y - pelvis.y) / torso,
    });
  }
  if (points.length < GHOST_MIN_POINTS) return null;

  const torsoAngleDeg =
    (Math.atan2(shoulderMid.y - pelvis.y, shoulderMid.x - pelvis.x) * 180) /
    Math.PI;
  return { points, torsoAngleDeg };
}

/** 몸통 방향을 그림의 몸통 방향으로 회전 정렬 (+옵션 좌우 반전). 순수 함수. */
export function alignGhostToTorso(
  pose: { points: GhostPoint[]; torsoAngleDeg: number },
  targetTorsoAngleDeg: number,
  flipX = false,
): GhostPose {
  const src = flipX
    ? pose.points.map((p) => ({ ...p, x: -p.x }))
    : pose.points;
  const srcAngle = flipX ? 180 - pose.torsoAngleDeg : pose.torsoAngleDeg;
  const delta = ((targetTorsoAngleDeg - srcAngle) * Math.PI) / 180;
  const cos = Math.cos(delta);
  const sin = Math.sin(delta);
  return {
    points: src.map((p) => ({
      key: p.key,
      x: p.x * cos - p.y * sin,
      y: p.x * sin + p.y * cos,
    })),
  };
}

/**
 * 에셋 + doc 재료 → 그림에 정렬된 잔상. 어느 축이든 실패 = null (그림만 표시).
 * thresholds 류와 같은 규율: 메타·게이트는 데이터, 판정은 순수 함수.
 */
export function buildGhostPoseForAsset(
  asset: string | null | undefined,
  report: KeypointReportLike | null | undefined,
  records: ReadonlyArray<{ atVideoSec?: number | null } | null | undefined>,
  align: Readonly<Record<string, GhostAlignMeta>> = GHOST_ALIGN,
): GhostPose | null {
  if (!asset) return null;
  const meta = align[asset];
  if (meta == null) return null;
  const sec = pickGhostMomentSec(records);
  if (sec == null) return null;
  const rawPose = extractGhostPose(report, sec);
  if (rawPose == null) return null;
  return alignGhostToTorso(rawPose, meta.torsoAngleDeg, meta.flipX === true);
}

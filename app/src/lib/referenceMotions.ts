// 기준 모션(정은지) 데이터 소스 레이어 (plan.md #9).
//
// 화면 코드는 데이터 소스에 무지하도록 격리한다. 지금은 Firestore 직접 구독,
// 나중에 백엔드 Lambda(GET /reference) 가 켜지면 이 파일 내부만 교체하면 됨
// (훅 시그니처 고정). docs/contract.md §3 / firestore.rules: reference/** 인증 read.
//
// 데이터 스키마: reference/{motionId} 단일 컬렉션. 단일 진실 = docs/reference-motions.md §3.
//   필수: name, athleteName, level('basic'|'intermediate'|'advanced')
//   옵셔널: entryType/entryDescription/description/videoUrl/thumbnailUrl/clipRange/
//           checkpoints/sharedBaseMotionId/baseUntilS, isActive(false 면 앱 미노출)

import {
  collection,
  doc,
  onSnapshot,
  query,
  type FirestoreError,
} from 'firebase/firestore';
import { useEffect, useState } from 'react';
import { db } from './firebase';
import type {
  KeypointReport,
  ReferenceMotion,
  SkillLevel,
} from '../types/analysis';

const LEVEL_ORDER: Record<SkillLevel, number> = {
  basic: 0,
  intermediate: 1,
  advanced: 2,
};

export interface ReferenceMotionsState {
  motions: ReferenceMotion[];
  loading: boolean;
  error: string | null;
}

// Firestore 의 flat 저장 angles(T*J) + anglesJointKeys → 관절 평균 각도(deg) 계산.
// nested-array 금지(2026-05-23 시드 메모) 우회로 flat 으로 들어옴. 길이가 J 의
// 배수가 아니거나 키 누락이면 undefined — 결과 화면이 자동으로 시뮬 폴백.
// NaN/inf 가 평균에 섞이면 nanmean (값이 하나라도 finite 이면 그것만 평균).
function deriveMeanAngles(
  anglesFlat: unknown,
  jointKeys: unknown,
): Record<string, number> | undefined {
  if (!Array.isArray(anglesFlat) || !Array.isArray(jointKeys)) return undefined;
  const keys = jointKeys.filter((k): k is string => typeof k === 'string');
  const J = keys.length;
  if (J === 0) return undefined;
  if (anglesFlat.length === 0 || anglesFlat.length % J !== 0) return undefined;
  const T = anglesFlat.length / J;
  const sums = new Array<number>(J).fill(0);
  const counts = new Array<number>(J).fill(0);
  for (let t = 0; t < T; t += 1) {
    for (let j = 0; j < J; j += 1) {
      const v = anglesFlat[t * J + j];
      if (typeof v === 'number' && Number.isFinite(v)) {
        sums[j] += v;
        counts[j] += 1;
      }
    }
  }
  const out: Record<string, number> = {};
  for (let j = 0; j < J; j += 1) {
    if (counts[j] > 0) out[keys[j]] = sums[j] / counts[j];
  }
  return Object.keys(out).length ? out : undefined;
}

// Firestore 문서를 앱 타입으로 정규화. 필수 필드 누락 시 null → 화면에서 무시.
function normalize(id: string, raw: Record<string, unknown>): ReferenceMotion | null {
  const name = typeof raw.name === 'string' ? raw.name : null;
  const athleteName =
    typeof raw.athleteName === 'string' ? raw.athleteName : null;
  const level = raw.level as SkillLevel | undefined;
  if (!name || !athleteName || !level || !(level in LEVEL_ORDER)) return null;
  if (raw.isActive === false) return null;
  const str = (v: unknown): string | undefined =>
    typeof v === 'string' ? v : undefined;

  // meanAngles: 시드가 미리 저장했으면 그걸 우선, 없으면 angles flat 에서 derive.
  // 둘 다 없으면 undefined → 결과 화면은 시뮬 픽스처 targetAngle 폴백.
  const seededMean =
    raw.meanAngles && typeof raw.meanAngles === 'object'
      ? Object.fromEntries(
          Object.entries(raw.meanAngles as Record<string, unknown>).filter(
            (entry): entry is [string, number] =>
              typeof entry[1] === 'number' && Number.isFinite(entry[1]),
          ),
        )
      : undefined;
  const meanAngles =
    seededMean && Object.keys(seededMean).length
      ? seededMean
      : deriveMeanAngles(raw.angles, raw.anglesJointKeys);

  const anglesJointKeys = Array.isArray(raw.anglesJointKeys)
    ? (raw.anglesJointKeys as unknown[]).filter(
        (k): k is string => typeof k === 'string',
      )
    : undefined;

  // Phase 12 Wave 0B (Plan 12-01, R3 iter-2) — referenceKeypointReport null-guard.
  // seed script 가 정은지 영상 분석 결과로 박제. 누락 시 undefined 유지 (구 doc 호환).
  // mode1 split overlay 의 정은지 측 데이터 source — `useReferenceMotion` 직접 read.
  const refKpRaw = raw.referenceKeypointReport;
  let referenceKeypointReport: KeypointReport | null | undefined;
  if (refKpRaw && typeof refKpRaw === 'object') {
    const kr = refKpRaw as Record<string, unknown>;
    referenceKeypointReport = {
      version: typeof kr.version === 'string' ? kr.version : '1.0',
      joints: Array.isArray(kr.joints)
        ? (kr.joints as KeypointReport['joints'])
        : [],
      frames: typeof kr.frames === 'number' ? kr.frames : 0,
      fps: typeof kr.fps === 'number' ? kr.fps : 9.0,
      data: Array.isArray(kr.data) ? (kr.data as number[]) : [],
      confidence: Array.isArray(kr.confidence)
        ? (kr.confidence as number[])
        : [],
      reliability: Array.isArray(kr.reliability)
        ? (kr.reliability as KeypointReport['reliability'])
        : [],
      axisData: Array.isArray(kr.axisData) ? (kr.axisData as number[]) : [],
      axisMask: Array.isArray(kr.axisMask) ? (kr.axisMask as boolean[]) : [],
      warnings: Array.isArray(kr.warnings) ? (kr.warnings as string[]) : [],
    };
  } else if (refKpRaw === null) {
    referenceKeypointReport = null;
  }

  // Phase 14 (Plan 14-01, R2-4) — 백필 다운스트림 필드 surfacing.
  // 기존 normalize() 는 고정 subset 만 반환해 bodyNormalizationProfile 등 type 이
  // 선언한 필드를 silently strip 했다. type/contract/normalize 3-way lockstep
  // (CLAUDE.md Cross-cutting) 정합을 위해 null-safe 로 추출·반환한다. 백필 미완
  // reference 는 undefined 유지 (defensive — referenceKeypointReport guard idiom
  // 정합). Pitfall 5 — T-scaled per-frame array 는 추가하지 않는다 (40k index).
  const obj = (v: unknown): Record<string, unknown> | undefined =>
    v && typeof v === 'object' && !Array.isArray(v)
      ? (v as Record<string, unknown>)
      : undefined;

  const bodyNormalizationProfile =
    raw.bodyNormalizationProfile === null
      ? null
      : (obj(raw.bodyNormalizationProfile) as
          | ReferenceMotion['bodyNormalizationProfile']
          | undefined);

  const techniqueProfile =
    raw.techniqueProfile === null
      ? null
      : (obj(raw.techniqueProfile) as ReferenceMotion['techniqueProfile'] | undefined);

  const forceDirectionPattern =
    raw.forceDirectionPattern === null
      ? null
      : (obj(raw.forceDirectionPattern) as
          | ReferenceMotion['forceDirectionPattern']
          | undefined);

  const captureViews =
    typeof raw.captureViews === 'number' && Number.isFinite(raw.captureViews)
      ? raw.captureViews
      : undefined;

  return {
    motionId: id,
    name,
    athleteName,
    level,
    entryType: raw.entryType as ReferenceMotion['entryType'],
    entryDescription: str(raw.entryDescription),
    description: str(raw.description),
    videoUrl: str(raw.videoUrl),
    thumbnailUrl: str(raw.thumbnailUrl),
    clipRange: raw.clipRange as ReferenceMotion['clipRange'],
    checkpoints: Array.isArray(raw.checkpoints)
      ? (raw.checkpoints as ReferenceMotion['checkpoints'])
      : undefined,
    sharedBaseMotionId: str(raw.sharedBaseMotionId),
    baseUntilS: typeof raw.baseUntilS === 'number' ? raw.baseUntilS : undefined,
    updatedAt: typeof raw.updatedAt === 'number' ? raw.updatedAt : undefined,
    anglesJointKeys,
    anglesFrames:
      typeof raw.anglesFrames === 'number' ? raw.anglesFrames : undefined,
    meanAngles,
    referenceKeypointReport,
    bodyNormalizationProfile,
    techniqueProfile,
    forceDirectionPattern,
    captureViews,
  };
}

// 단일 모션 조회 (결과 화면 mode1 메타 카드 등). 컬렉션 구독을 재사용 —
// 별도 doc 구독을 만들면 캐시 분기·인증 처리 중복. 컬렉션이 작아(파일럿 수십개)
// 비용 무시 가능. 시드 전엔 null 반환 → 화면은 params 폴백 사용.
export function useReferenceMotion(
  motionId: string | undefined,
): { motion: ReferenceMotion | null; loading: boolean } {
  const { motions, loading } = useReferenceMotions();
  const motion = motionId ? motions.find((m) => m.motionId === motionId) ?? null : null;
  return { motion, loading };
}

export function useReferenceMotions(): ReferenceMotionsState {
  const [motions, setMotions] = useState<ReferenceMotion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const q = query(collection(db, 'reference'));
    const unsub = onSnapshot(
      q,
      (snap) => {
        const list: ReferenceMotion[] = [];
        snap.forEach((d) => {
          const m = normalize(d.id, d.data() as Record<string, unknown>);
          if (m) list.push(m);
        });
        // 레벨 오름차순 → 이름 가나다순. 화면에서 탭 필터링 시 안정적인 순서.
        list.sort((a, b) => {
          const lv = LEVEL_ORDER[a.level] - LEVEL_ORDER[b.level];
          return lv !== 0 ? lv : a.name.localeCompare(b.name, 'ko');
        });
        setMotions(list);
        setLoading(false);
        setError(null);
      },
      (err: FirestoreError) => {
        if (__DEV__) console.warn('[referenceMotions] onSnapshot error', err);
        setLoading(false);
        setError('기준 동작을 불러오지 못했어요. 잠시 후 다시 시도해주세요.');
      },
    );
    return unsub;
  }, []);

  return { motions, loading, error };
}

// ── Phase 31 (31-08, amended D-10) — 자세 비교 뷰어용 단일 문서 구독 ────────
//
// 리뷰 M-02: 위 `useReferenceMotions` 컬렉션 구독에 joints3d 를 얹지 않는다.
// joints3d 는 T*17*3 flat 배열(수천~수만 원소)이라 컬렉션 구독에 실으면 reference
// 문서 전 건의 대형 배열을 매 구독마다 내려받게 된다 (읽기 비용 + 메모리). 비교
// 뷰어는 "지금 보고 있는 mode1 기준 동작 1건" 만 필요하므로 doc() 단일 문서를
// 따로 구독한다. `normalize()` 가 joints3d 를 의도적으로 strip 하는 것과 정합 —
// 컬렉션 경로는 계속 메타데이터 전용으로 남는다.
//
// 읽기 전용. 이 훅은 reference 문서에 절대 write 하지 않는다 (40k index-entry
// 한도 — [[analyses-index-exemption-fix]] 선례).
export interface ReferencePose3dState {
  /** (T, 17, 3) reshape 결과. 검증 실패 시 null (조용한 강등). */
  joints3d: number[][][] | null;
  /** joints3d 의 keypoint 이름 (length 17). null 이면 undefined. */
  jointKeys: string[] | null;
  frames: number;
  loading: boolean;
}

const POSE3D_JOINT_COUNT = 17; // COCO-17
const POSE3D_COORD_DIM = 3; // xyz

// flat joints3d → (T, 17, 3). 길이/키 개수/좌표 차원이 서로 어긋나면 null.
// 부분 복구를 시도하지 않는다 — 어긋난 배열을 잘라 쓰면 엉뚱한 관절이 연결된
// 스켈레톤이 그려져 "틀린 그림을 자신있게 보여주는" 최악의 실패가 된다.
function reshapeJoints3d(
  flat: unknown,
  keys: unknown,
  frames: unknown,
  coordDim: unknown,
): { joints3d: number[][][]; jointKeys: string[]; frames: number } | null {
  if (!Array.isArray(flat) || !Array.isArray(keys)) return null;
  const jointKeys = keys.filter((k): k is string => typeof k === 'string');
  if (jointKeys.length !== POSE3D_JOINT_COUNT) return null;
  // coordDim 은 부재 가능(구 doc) — 존재하면 3 이어야 한다.
  if (coordDim !== undefined && coordDim !== POSE3D_COORD_DIM) return null;
  const stride = POSE3D_JOINT_COUNT * POSE3D_COORD_DIM;
  if (flat.length === 0 || flat.length % stride !== 0) return null;
  const T = flat.length / stride;
  // joints3dFrames 는 reshape 메타 — 존재하면 실제 길이와 일치해야 한다.
  if (typeof frames === 'number' && frames !== T) return null;

  const out: number[][][] = new Array(T);
  for (let t = 0; t < T; t += 1) {
    const frame: number[][] = new Array(POSE3D_JOINT_COUNT);
    for (let j = 0; j < POSE3D_JOINT_COUNT; j += 1) {
      const base = t * stride + j * POSE3D_COORD_DIM;
      const p: number[] = new Array(POSE3D_COORD_DIM);
      for (let c = 0; c < POSE3D_COORD_DIM; c += 1) {
        const v = flat[base + c];
        // NaN/inf/비수치는 그대로 통과시키지 않고 NaN 으로 통일 — 뷰어가
        // 유한값 검사 한 번으로 해당 관절을 건너뛴다.
        p[c] = typeof v === 'number' && Number.isFinite(v) ? v : NaN;
      }
      frame[j] = p;
    }
    out[t] = frame;
  }
  return { joints3d: out, jointKeys, frames: T };
}

/**
 * reference/{motionId} 단일 문서의 joints3d 를 구독한다 (컬렉션 구독 아님).
 *
 * motionId 가 null/undefined 면 구독을 만들지 않고 즉시 빈 상태를 반환한다 —
 * 훅은 조건부 호출 없이 항상 호출할 수 있어야 하므로(리뷰 M-04) 가드는 훅
 * 바깥이 아니라 내부 effect 에 둔다.
 */
export function useReferenceMotionDoc(
  motionId: string | null | undefined,
): ReferencePose3dState {
  const [state, setState] = useState<ReferencePose3dState>({
    joints3d: null,
    jointKeys: null,
    frames: 0,
    loading: Boolean(motionId),
  });

  useEffect(() => {
    if (!motionId) {
      setState({ joints3d: null, jointKeys: null, frames: 0, loading: false });
      return;
    }
    setState((prev) => ({ ...prev, loading: true }));
    const unsub = onSnapshot(
      doc(db, 'reference', motionId),
      (snap) => {
        const raw = snap.data() as Record<string, unknown> | undefined;
        const parsed = raw
          ? reshapeJoints3d(
              raw.joints3d,
              raw.joints3dKeys,
              raw.joints3dFrames,
              raw.coordDim,
            )
          : null;
        setState({
          joints3d: parsed?.joints3d ?? null,
          jointKeys: parsed?.jointKeys ?? null,
          frames: parsed?.frames ?? 0,
          loading: false,
        });
      },
      (err: FirestoreError) => {
        if (__DEV__) console.warn('[referenceMotions] doc onSnapshot error', err);
        // 조용한 강등 (D-08) — 에러 문자열을 노출하지 않는다. 뷰어를 숨기는 건
        // 호출부(참고코너)의 렌더 가드 몫.
        setState({ joints3d: null, jointKeys: null, frames: 0, loading: false });
      },
    );
    return unsub;
  }, [motionId]);

  return state;
}

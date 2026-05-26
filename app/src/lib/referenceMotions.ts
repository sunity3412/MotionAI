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
  onSnapshot,
  query,
  type FirestoreError,
} from 'firebase/firestore';
import { useEffect, useState } from 'react';
import { db } from './firebase';
import type { ReferenceMotion, SkillLevel } from '../types/analysis';

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

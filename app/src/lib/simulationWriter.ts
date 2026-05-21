// 시뮬 분석 종료 시 Firestore done 문서 쓰기 — 실 백엔드 연결 전 임시 스캐폴드.
// 백엔드(#7-follow)에서 S3 트리거 파이프라인이 Admin SDK 로 문서를 직접 갱신하기
// 시작하면 이 모듈은 폐기 대상.
//
// 현재 흐름:
//   analyze → loading(시뮬 status 진행) → done 도달 시 saveSimulatedAnalysis()
//   → users/{uid}/analyses 에 status='done' 문서 1건 (호출자가 1회만 호출 책임).
//
// 정합성: contract.md §3 의 AnalysisDoc 모양. 보안 규칙은 users/{uid}/{**} 본인만
// 쓰기 허용이므로 익명 게스트도 정상 동작. 실 파이프라인은 본인 외 Admin SDK 만.

import {
  collection,
  doc,
  getDoc,
  getDocs,
  query,
  setDoc,
  where,
} from 'firebase/firestore';
import { auth, db } from './firebase';
import { getSimulatedResult, simulatedSegmentScores } from './simulatedResult';
import type {
  AnalysisDoc,
  AnalysisMode,
  AnalysisResult,
  BodyPart,
  ReferenceMotion,
  SegmentScores,
} from '../types/analysis';

// reference/{motionId} 1건 — 콤보 여부(sharedBaseMotionId) 판단용.
async function loadReferenceMotion(
  motionId: string,
): Promise<ReferenceMotion | null> {
  const snap = await getDoc(doc(db, 'reference', motionId));
  if (!snap.exists()) return null;
  return { motionId, ...snap.data() } as ReferenceMotion;
}

export interface SaveSimulatedInput {
  mode: AnalysisMode;
  fileName: string;
  // mode1 진입 시 사용자가 #9 에서 고른 기준 모션. 결과 픽스처에 덮어쓰기.
  referenceMotionId?: string;
  referenceMotionName?: string;
}

// 가장 최근 mode3 done 분석 (delta 비교 대상). 없으면 null.
// 컴포짓 인덱스 불필요하도록 where(mode) 만 쓰고 status/정렬은 클라이언트에서.
async function findPreviousMode3(uid: string): Promise<AnalysisDoc | null> {
  const snap = await getDocs(
    query(
      collection(db, 'users', uid, 'analyses'),
      where('mode', '==', 'mode3'),
    ),
  );
  const docs = snap.docs
    .map((d) => d.data() as AnalysisDoc)
    .filter((d) => d.status === 'done' && !!d.result)
    .sort((a, b) => (b.createdAt ?? 0) - (a.createdAt ?? 0));
  return docs[0] ?? null;
}

/**
 * Firestore 에 시뮬 분석 결과 문서를 저장하고 그 analysisId 를 반환.
 * 인증된 사용자가 없으면 null 반환(쓰기 안 함). 호출자는 idempotency 보장(savedRef 등).
 *
 * mode3 는 이전 done 문서를 찾아 isFirst / previousAnalysisId / deltaFromPrevious
 * 를 실측치로 채움 (시뮬이라도 자기-비교의 의미가 정확해짐).
 */
export async function saveSimulatedAnalysis(
  input: SaveSimulatedInput,
): Promise<string | null> {
  const uid = auth.currentUser?.uid;
  if (!uid) return null;

  // 새 analysisId — Firestore 자동 ID(서버 기반 단조 정렬에 유리).
  const docRef = doc(collection(db, 'users', uid, 'analyses'));
  const analysisId = docRef.id;

  const result: AnalysisResult = getSimulatedResult(input.mode, analysisId);

  if (result.comparison.mode === 'mode1' && input.referenceMotionId) {
    // mode1: 사용자가 고른 기준 모션 정보로 픽스처를 덮어씀(result.tsx 분기와 동일).
    // 콤보 모션이면 베이스/확장 구간 부분 점수도 채움(백엔드 pipeline 과 동일 판단).
    const refMotion = await loadReferenceMotion(input.referenceMotionId);
    let segmentScores: SegmentScores | undefined;
    if (refMotion?.sharedBaseMotionId) {
      const baseMotion = await loadReferenceMotion(refMotion.sharedBaseMotionId);
      segmentScores = simulatedSegmentScores(
        result.overallScore,
        refMotion.sharedBaseMotionId,
        baseMotion?.name ?? '',
      );
    }
    result.comparison = {
      ...result.comparison,
      referenceMotionId: input.referenceMotionId,
      referenceMotionName:
        input.referenceMotionName || result.comparison.referenceMotionName,
      ...(segmentScores ? { segmentScores } : {}),
    };
  } else if (result.comparison.mode === 'mode3') {
    // mode3: 이전 분석 있나 확인. 없으면 isFirst, 있으면 실 delta 계산.
    const prev = await findPreviousMode3(uid);
    if (!prev) {
      result.comparison = { mode: 'mode3', isFirst: true };
    } else {
      const prevParts = prev.result?.partScores;
      if (prevParts) {
        const delta: Record<BodyPart, number> = {
          상체: result.partScores['상체'] - prevParts['상체'],
          코어: result.partScores['코어'] - prevParts['코어'],
          하체: result.partScores['하체'] - prevParts['하체'],
        };
        result.comparison = {
          mode: 'mode3',
          isFirst: false,
          previousAnalysisId: prev.analysisId,
          deltaFromPrevious: delta,
        };
      } else {
        // prev 는 있는데 result 가 없는 비정상 케이스 — isFirst 처럼 안전 동작
        result.comparison = { mode: 'mode3', isFirst: true };
      }
    }
  }

  const now = Date.now();
  await setDoc(docRef, {
    analysisId,
    mode: input.mode,
    status: 'done',
    fileName: input.fileName,
    createdAt: now,
    updatedAt: now,
    result,
  });
  return analysisId;
}


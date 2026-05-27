// 샘플 시나리오 진입(영상 없는 시연용) 전용 Firestore 쓰기.
// 실 분석 흐름은 loading.tsx 가 직접 /upload-url → S3 PUT → 백엔드 갱신을 트리거.

import { collection, doc, getDoc, setDoc } from 'firebase/firestore';
import { auth, db } from './firebase';
import {
  getSimulatedResultFromScenario,
  simulatedSegmentScores,
  type SampleScenario,
} from './simulatedResult';
import type {
  AnalysisResult,
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

/**
 * 샘플 시나리오 1건을 Firestore done 문서로 저장. 영상 없는 시연/검토용.
 * Mode1: reference doc 의 sharedBaseMotionId 가 있으면 segmentScores 자동 채움.
 * Mode3: scenario.isFirst/deltaFromPrevious 를 그대로 사용 (실 prev 조회 안 함).
 */
export async function saveSampleAnalysis(
  scenario: SampleScenario,
): Promise<string | null> {
  const uid = auth.currentUser?.uid;
  if (!uid) return null;

  const docRef = doc(collection(db, 'users', uid, 'analyses'));
  const analysisId = docRef.id;
  const result: AnalysisResult = getSimulatedResultFromScenario(
    scenario,
    analysisId,
  );

  if (
    result.comparison.mode === 'mode1' &&
    result.comparison.referenceMotionId
  ) {
    const refMotion = await loadReferenceMotion(
      result.comparison.referenceMotionId,
    );
    if (refMotion?.sharedBaseMotionId) {
      const baseMotion = await loadReferenceMotion(refMotion.sharedBaseMotionId);
      const segmentScores: SegmentScores = simulatedSegmentScores(
        result.overallScore,
        refMotion.sharedBaseMotionId,
        baseMotion?.name ?? '',
      );
      result.comparison = { ...result.comparison, segmentScores };
    }
  }

  const now = Date.now();
  await setDoc(docRef, {
    analysisId,
    mode: scenario.mode,
    status: 'done',
    fileName: `샘플 · ${scenario.label}`,
    createdAt: now,
    updatedAt: now,
    result,
  });
  return analysisId;
}


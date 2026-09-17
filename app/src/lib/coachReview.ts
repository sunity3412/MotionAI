// 강사 교정 데이터 소스 레이어 (quick-260918-0q8, belle 2026-09-17 승인).
//
// users/{uid}/analyses/{analysisId} 의 coachReview 필드를 쓴다. 화면은 Firestore 에
// 직접 닿지 않는다 — bodyProfile.ts / userAnalyses.ts 와 같은 격리 패턴이다.
//
// **읽기 hook 이 없는 이유**: 결과 화면은 이미 useAnalysisDoc 으로 문서 전체를
// onSnapshot 구독한다. coachReview 는 그 문서의 필드라 저장하면 같은 구독이
// 자동으로 rerender 한다 — 별도 구독/폴링을 만들면 안티패턴이다.
//
// **누가 쓰는가**: 학생 세션이다. 학원에서 강사가 학생 폰에 직접 입력한다.
// 그래서 새 인증도, 새 백엔드 엔드포인트도, Firestore 규칙 변경도 없다
// (규칙: users/{uid}/** 본인만 read/write — 익명 게스트 포함).
// reviewedBy 는 신원 증명이 아니라 출처 표기(자유 입력)다.

import { doc, setDoc } from 'firebase/firestore';
import { auth, db } from './firebase';
import type { CoachReview } from '../types/analysis';

/** 입력 상한 — 저장 전 잘라낸다(Firestore 문서 비대 방지, 표시 레이아웃 보호). */
export const COACH_COMMENT_MAX = 500;
export const COACH_NAME_MAX = 30;

/** 저장 가능한 입력인가 — 공백만인 코멘트는 저장하지 않는다. */
export function isSavableCoachReview(comment: string): boolean {
  return comment.trim().length > 0;
}

/**
 * 강사 교정 저장. comment 가 공백만이면 저장하지 않고 false 를 돌려준다.
 *
 * merge:true 로 coachReview 맵만 갱신한다 — 같은 문서의 result/angles 등 다른
 * 필드는 건드리지 않는다.
 */
export async function saveCoachReview(
  analysisId: string,
  comment: string,
  reviewedBy: string,
): Promise<boolean> {
  const uid = auth.currentUser?.uid;
  if (!uid) throw new Error('로그인이 필요합니다.');
  if (!isSavableCoachReview(comment)) return false;
  const payload: CoachReview = {
    comment: comment.trim().slice(0, COACH_COMMENT_MAX),
    reviewedBy: reviewedBy.trim().slice(0, COACH_NAME_MAX),
    updatedAt: Date.now(),
  };
  await setDoc(
    doc(db, 'users', uid, 'analyses', analysisId),
    { coachReview: payload },
    { merge: true },
  );
  return true;
}

/**
 * 강사 교정 삭제. Firestore merge:true 는 키 생략을 "건드리지 않음"으로 읽으므로
 * 비울 때는 null 을 **명시 기록**해야 한다 (bodyProfile.savePainAreaNote 와 같은 선례).
 */
export async function clearCoachReview(analysisId: string): Promise<void> {
  const uid = auth.currentUser?.uid;
  if (!uid) throw new Error('로그인이 필요합니다.');
  await setDoc(
    doc(db, 'users', uid, 'analyses', analysisId),
    { coachReview: null },
    { merge: true },
  );
}

/** 저장값 정규화 — 형식이 깨진 doc 은 null (userAnalyses.normalize 와 같은 방어). */
export function normalizeCoachReview(raw: unknown): CoachReview | null {
  if (!raw || typeof raw !== 'object') return null;
  const r = raw as Record<string, unknown>;
  const comment = typeof r.comment === 'string' ? r.comment : '';
  if (!comment.trim()) return null;
  return {
    comment,
    reviewedBy: typeof r.reviewedBy === 'string' ? r.reviewedBy : '',
    updatedAt: typeof r.updatedAt === 'number' && Number.isFinite(r.updatedAt)
      ? r.updatedAt
      : 0,
  };
}

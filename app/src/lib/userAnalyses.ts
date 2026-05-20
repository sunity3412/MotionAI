// 분석 기록 데이터 소스 레이어 (홈 탭 최근 분석 + 기록 탭 리스트).
//
// users/{uid}/analyses 컬렉션 onSnapshot 구독. 화면은 데이터 소스에 무지하도록 격리 —
// 나중에 GraphQL/REST 로 바꿔도 이 파일만 교체(referenceMotions.ts 와 동일 패턴).
//
// 익명 인증(게스트)도 정상 — 보안 규칙: users/{uid}/{**} 본인만 read/write.

import {
  collection,
  doc,
  onSnapshot,
  query,
  orderBy,
  type FirestoreError,
} from 'firebase/firestore';
import { onAuthStateChanged } from 'firebase/auth';
import { useEffect, useState } from 'react';
import { auth, db } from './firebase';
import type { AnalysisDoc, AnalysisStatus } from '../types/analysis';

export interface UserAnalysesState {
  analyses: AnalysisDoc[]; // createdAt 내림차순
  loading: boolean;
  error: string | null;
}

function normalize(id: string, raw: Record<string, unknown>): AnalysisDoc | null {
  const mode = raw.mode === 'mode1' || raw.mode === 'mode3' ? raw.mode : null;
  const status = raw.status as AnalysisStatus | undefined;
  const fileName = typeof raw.fileName === 'string' ? raw.fileName : null;
  const createdAt = typeof raw.createdAt === 'number' ? raw.createdAt : null;
  const updatedAt = typeof raw.updatedAt === 'number' ? raw.updatedAt : createdAt;
  if (!mode || !status || !fileName || createdAt == null || updatedAt == null) return null;
  return {
    analysisId: id,
    mode,
    status,
    fileName,
    createdAt,
    updatedAt,
    error: raw.error as AnalysisDoc['error'],
    result: raw.result as AnalysisDoc['result'],
  };
}

// 단일 분석 문서 구독 (결과 화면 등). analysisId 없으면 doc=null·loading=false.
export function useAnalysisDoc(analysisId: string | undefined): {
  doc: AnalysisDoc | null;
  loading: boolean;
} {
  const [docState, setDocState] = useState<AnalysisDoc | null>(null);
  const [loading, setLoading] = useState<boolean>(!!analysisId);
  const [uid, setUid] = useState<string | null>(auth.currentUser?.uid ?? null);

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, (u) => setUid(u?.uid ?? null));
    return unsub;
  }, []);

  useEffect(() => {
    if (!uid || !analysisId) {
      setDocState(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    const ref = doc(db, 'users', uid, 'analyses', analysisId);
    const unsub = onSnapshot(
      ref,
      (snap) => {
        if (!snap.exists()) {
          setDocState(null);
        } else {
          const a = normalize(snap.id, snap.data() as Record<string, unknown>);
          setDocState(a);
        }
        setLoading(false);
      },
      (err: FirestoreError) => {
        if (__DEV__) console.warn('[useAnalysisDoc] error', err);
        setDocState(null);
        setLoading(false);
      },
    );
    return unsub;
  }, [uid, analysisId]);

  return { doc: docState, loading };
}

export function useMyAnalyses(opts?: { doneOnly?: boolean }): UserAnalysesState {
  const doneOnly = opts?.doneOnly ?? false;
  const [analyses, setAnalyses] = useState<AnalysisDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uid, setUid] = useState<string | null>(auth.currentUser?.uid ?? null);

  // 인트로에서 (tabs)로 진입 후엔 currentUser 보장되지만, 콜드스타트 race 대비.
  useEffect(() => {
    const unsub = onAuthStateChanged(auth, (u) => setUid(u?.uid ?? null));
    return unsub;
  }, []);

  useEffect(() => {
    if (!uid) {
      setAnalyses([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    const q = query(
      collection(db, 'users', uid, 'analyses'),
      orderBy('createdAt', 'desc'),
    );
    const unsub = onSnapshot(
      q,
      (snap) => {
        const list: AnalysisDoc[] = [];
        snap.forEach((d) => {
          const a = normalize(d.id, d.data() as Record<string, unknown>);
          if (a && (!doneOnly || a.status === 'done')) list.push(a);
        });
        setAnalyses(list);
        setLoading(false);
        setError(null);
      },
      (err: FirestoreError) => {
        if (__DEV__) console.warn('[userAnalyses] onSnapshot error', err);
        setLoading(false);
        setError('분석 기록을 불러오지 못했어요.');
      },
    );
    return unsub;
  }, [uid, doneOnly]);

  return { analyses, loading, error };
}

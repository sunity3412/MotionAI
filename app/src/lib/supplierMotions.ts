// 공급자 페이지 데이터 소스 — 내 기준 동작 목록 + 상세용 비공개 doc (Phase 38 D-09 · D-10, 리뷰 R13).
//
// 화면(`app/supplier/index.tsx`)은 Firestore 를 모른다 — referenceMotions.ts 와 같은 격리.
// 규칙(정규화 · 상태어 · 문턱)은 38-03 `supplierRules` 에 있고 여기서는 import 만 한다(리뷰 R14).
//
// ★Spark 5만 읽기/일 캡(메모리 firestore-spark-50k-read-cap) — 목록 구독은
// `where('supplierUid','==',uid)` 하나뿐이다. 전수 스캔 금지. `useReferenceMotions()` 를
// 재사용하지 않는 이유: 그 normalize 가 등록 필드(registrationStatus·selfScore 등)를 strip 하고
// 컬렉션 전체를 읽는다(38-PATTERNS 관측 7).

import {
  collection,
  doc,
  onSnapshot,
  query,
  where,
  type FirestoreError,
} from 'firebase/firestore';
import { useCallback, useEffect, useState } from 'react';
import { supplierCopy } from '../constants/supplierCopy';
import { db } from './firebase';
import {
  normalizePrivate,
  normalizeRegistration,
  type SupplierMotion,
  type SupplierMotionPrivate,
} from './supplierRules';

export interface SupplierMotionsState {
  motions: SupplierMotion[];
  loading: boolean;
  error: string | null;
  retry: () => void;
}

export function useSupplierMotions(uid: string | null): SupplierMotionsState {
  const [motions, setMotions] = useState<SupplierMotion[]>([]);
  const [loading, setLoading] = useState(Boolean(uid));
  const [error, setError] = useState<string | null>(null);
  // retry() 는 값만 올려 effect 를 다시 돌린다 = 재구독.
  const [attempt, setAttempt] = useState(0);
  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  useEffect(() => {
    if (!uid) {
      setMotions([]);
      setLoading(false);
      setError(null);
      return;
    }
    setLoading(true);
    const q = query(collection(db, 'reference'), where('supplierUid', '==', uid));
    const unsub = onSnapshot(
      q,
      (snap) => {
        const list: SupplierMotion[] = [];
        snap.forEach((d) => {
          const m = normalizeRegistration(d.id, d.data() as Record<string, unknown>);
          if (m) list.push(m);
        });
        setMotions(list);
        setLoading(false);
        setError(null);
      },
      (err: FirestoreError) => {
        if (__DEV__) console.warn('[supplierMotions] onSnapshot error', err);
        setLoading(false);
        setError(supplierCopy.home.listError);
      },
    );
    return unsub;
  }, [uid, attempt]);

  return { motions, loading, error, retry };
}

export interface SupplierRegistrationPrivateState {
  priv: SupplierMotionPrivate | null;
  loading: boolean;
  // Firestore 오류 코드(예: 'permission-denied' = 남의 doc). 화면은 이 코드면 목록으로 돌아간다.
  error: string | null;
}

// 상세 패널이 열렸을 때만 비공개 doc 1건을 구독한다(리뷰 R13). 규칙상 본인만 읽힌다
// (38-06 T3: supplierUid == request.auth.uid) — 목록에서는 구독하지 않는다(행 N 개 × 읽기 방지).
// 훅은 조건부 호출 없이 항상 부를 수 있게 refId null 가드를 effect 안에 둔다.
export function useSupplierRegistrationPrivate(
  refId: string | null,
): SupplierRegistrationPrivateState {
  const [state, setState] = useState<SupplierRegistrationPrivateState>({
    priv: null,
    loading: Boolean(refId),
    error: null,
  });

  useEffect(() => {
    if (!refId) {
      setState({ priv: null, loading: false, error: null });
      return;
    }
    setState({ priv: null, loading: true, error: null });
    const unsub = onSnapshot(
      doc(db, 'reference', refId, 'private', 'registration'),
      (snap) => {
        setState({ priv: normalizePrivate(snap.data()), loading: false, error: null });
      },
      (err: FirestoreError) => {
        if (__DEV__) console.warn('[supplierMotions] private onSnapshot error', err);
        setState({ priv: null, loading: false, error: err.code });
      },
    );
    return unsub;
  }, [refId]);

  return state;
}

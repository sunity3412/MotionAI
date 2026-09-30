// 마이 탭 강사 코드 — Firestore 입출력 층 (quick-260930-o0u, 38-DESIGN-v2 §W2).
//
// 화면은 Firestore 를 직접 만지지 않는다(bodyProfile.ts · userAnalyses.ts 패턴). 규칙 판정은
// instructorCode.ts(순수), 쓰기 허용 여부의 최종 판정은 firestore.rules isValidInstructorLink.
// 세 함수 모두 throw 하지 않는다 — 결과 kind 로 돌려주고 화면이 문구를 고른다.
//
// 플래너 결정:
//   (b) 읽기는 구독 없이 uid 당 get 1회 — Firestore Spark 읽기 캡(메모리 firestore-spark-50k).
//       운영 해제(instructor_link.py unlink)는 앱을 다시 켜야 보인다.
//   (c) 연결 쓰기 = runTransaction(tx.get → 있으면 already / 없으면 tx.set = 규칙상 create).
//       트랜잭션은 오프라인이면 바로 실패하므로 쓰기가 큐에 쌓였다가 몰래 반영되지 않는다.

import {
  doc,
  getDoc,
  runTransaction,
  serverTimestamp,
  type FirestoreError,
} from 'firebase/firestore';
import { useEffect, useState } from 'react';
import { db } from './firebase';
import {
  classifyCodeDoc,
  INSTRUCTOR_LINKS_COLLECTION,
  mapFirestoreErrorCode,
  normalizeInstructorLink,
  planLookup,
  SUPPLIER_CODES_COLLECTION,
  type FoundCode,
  type InstructorLink,
  type LookupResult,
} from './instructorCode';

function errorCode(err: unknown): string | undefined {
  const code = (err as FirestoreError | undefined)?.code;
  return typeof code === 'string' ? code : undefined;
}

// 입력값 → supplierCodes/{CODE} get 1회. 형식 밖이면 네트워크 없이 notFound(결정 (e)).
export async function lookupInstructorCode(
  raw: string,
  authUid: string | null,
): Promise<LookupResult> {
  const plan = planLookup(raw);
  if (plan.kind === 'invalid') return { kind: 'notFound' };
  try {
    const snap = await getDoc(doc(db, SUPPLIER_CODES_COLLECTION, plan.code));
    const c = classifyCodeDoc(snap.exists() ? snap.data() : null, authUid);
    if (c.kind === 'found') {
      return { kind: 'found', code: plan.code, supplierUid: c.supplierUid, displayName: c.displayName };
    }
    return c;
  } catch (err) {
    // denied 는 규칙 게시 전이 아니면 나올 일이 없다 — 알 수 없는 오류로 묶는다.
    return mapFirestoreErrorCode(errorCode(err)) === 'offline' ? { kind: 'offline' } : { kind: 'failed' };
  }
}

export type LinkOutcome =
  | { kind: 'linked'; link: InstructorLink }
  | { kind: 'already'; link: InstructorLink | null }
  | { kind: 'denied' }
  | { kind: 'offline' }
  | { kind: 'failed' };

// instructorLinks/{uid} 를 한 번 만든다. 필드는 넷뿐(규칙 hasOnly) — 크레딧 없음.
export async function linkInstructor(uid: string, found: FoundCode): Promise<LinkOutcome> {
  const ref = doc(db, INSTRUCTOR_LINKS_COLLECTION, uid);
  try {
    return await runTransaction(db, async (tx): Promise<LinkOutcome> => {
      const snap = await tx.get(ref);
      if (snap.exists()) {
        return { kind: 'already', link: normalizeInstructorLink(snap.data()) };
      }
      tx.set(ref, {
        code: found.code,
        supplierUid: found.supplierUid,
        displayName: found.displayName,
        linkedAt: serverTimestamp(),
      });
      // linkedAtMs 는 화면 표시용 추정 — 저장값은 서버 시각(규칙 linkedAt == request.time).
      return {
        kind: 'linked',
        link: {
          code: found.code,
          supplierUid: found.supplierUid,
          displayName: found.displayName,
          linkedAtMs: Date.now(),
        },
      };
    });
  } catch (err) {
    const kind = mapFirestoreErrorCode(errorCode(err));
    if (kind === 'denied') {
      // 거부 = 이미 연결돼 있어 create 가 update 로 판정됐거나, 그 사이 코드가 비활성화됐다.
      try {
        const snap = await getDoc(ref);
        if (snap.exists()) return { kind: 'already', link: normalizeInstructorLink(snap.data()) };
      } catch {
        // 다시 읽기도 실패 — 아래 denied 로.
      }
      return { kind: 'denied' };
    }
    return { kind };
  }
}

export type InstructorLinkStatus = 'loading' | 'ready' | 'error';

// uid 가 바뀔 때마다 get 1회. onSnapshot 을 쓰지 않는다(결정 (b)). uid null 이면 loading 유지.
// error = 읽기 실패 — 화면은 미연결로 그린다(이미 연결된 사람이 눌러도 트랜잭션이 already 를 돌려준다).
export function useInstructorLink(uid: string | null): {
  link: InstructorLink | null;
  status: InstructorLinkStatus;
  setLink: (link: InstructorLink | null) => void;
} {
  const [link, setLink] = useState<InstructorLink | null>(null);
  const [status, setStatus] = useState<InstructorLinkStatus>('loading');

  useEffect(() => {
    setLink(null);
    setStatus('loading');
    if (!uid) return;
    let cancelled = false;
    getDoc(doc(db, INSTRUCTOR_LINKS_COLLECTION, uid))
      .then((snap) => {
        if (cancelled) return;
        setLink(snap.exists() ? normalizeInstructorLink(snap.data()) : null);
        setStatus('ready');
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (__DEV__) console.warn('[useInstructorLink] error', errorCode(err));
        setLink(null);
        setStatus('error');
      });
    return () => {
      cancelled = true;
    };
  }, [uid]);

  return { link, status, setLink };
}

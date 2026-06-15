// 자가입력 신체 프로필 데이터 소스 레이어 (Phase 3, Plan 03-01).
//
// users/{uid} 단일 doc 의 bodyProfile 필드를 읽고/쓴다. 화면은 데이터 소스에
// 무지하도록 격리 — 나중에 GraphQL/REST 로 바꿔도 이 파일만 교체 (userAnalyses.ts
// 와 동일 패턴). 화면은 Firestore 직접 접근 금지 — 모두 이 hook/helper 경유.
//
// 익명 인증(게스트)도 정상 — 보안 규칙: users/{uid}/{**} 본인만 read/write.
//
// 순환 import 주의: 이 파일은 userAnalyses.ts 를 import 하지 않는다 (useBodyProfile
// 은 useAnalysisDoc 을 재사용하지 않고 onSnapshot 을 직접 구현). userAnalyses.ts
// 가 이 파일의 normalizeBodyProfile 만 단방향 import 한다.

import { doc, getDoc, onSnapshot, setDoc, type FirestoreError } from 'firebase/firestore';
import { onAuthStateChanged } from 'firebase/auth';
import { useEffect, useState } from 'react';
import { auth, db } from './firebase';
import type {
  BodyProfile,
  DominantHand,
  ExperienceLevel,
  PainArea,
} from '../types/analysis';

// 계약 union 멤버 (analysis.ts / models.py lockstep). 검증 멤버십 source.
const EXPERIENCE_LEVELS: readonly ExperienceLevel[] = [
  'beginner',
  'intermediate',
  'advanced',
];
const DOMINANT_HANDS: readonly DominantHand[] = ['left', 'right', 'both'];
const PAIN_AREAS: readonly PainArea[] = [
  'shoulder',
  'wrist',
  'lower_back',
  'knee',
  'ankle',
  'neck',
  'hip',
  'elbow',
];

// height/weight 합리적 범위 (models.normalize_body_profile 와 동일 — 이중 정규화).
const HEIGHT_CM_MIN = 90;
const HEIGHT_CM_MAX = 250;
const WEIGHT_KG_MIN = 25;
const WEIGHT_KG_MAX = 200;

function numberInRange(
  value: unknown,
  lo: number,
  hi: number,
): number | null {
  if (typeof value !== 'number' || !Number.isFinite(value)) return null;
  if (value < lo || value > hi) return null;
  return value;
}

// [R1/R5] 단일 normalizer — userAnalyses.ts(snapshot 보존) 와 getBodyProfileOnce
// (snapshot 기록) 가 공유한다. 각 필드 독립 검증, 잘못된 타입/enum/범위 → null.
// **전 필드 None/빈이면 전체 null 반환** ("all-empty → omit snapshot" 규칙을 helper
// 안에 둠 — R5). 절대 throw 안 함 (D-06 graceful).
export function normalizeBodyProfile(
  raw: Record<string, unknown> | undefined | null,
): BodyProfile | null {
  if (!raw || typeof raw !== 'object') return null;

  const heightCm = numberInRange(raw.heightCm, HEIGHT_CM_MIN, HEIGHT_CM_MAX);
  // weightKg 는 보조 ONLY (D-05) — 정규화만 하고 scoring 경로에는 절대 전달 X.
  const weightKg = numberInRange(raw.weightKg, WEIGHT_KG_MIN, WEIGHT_KG_MAX);

  const experience = EXPERIENCE_LEVELS.includes(raw.experience as ExperienceLevel)
    ? (raw.experience as ExperienceLevel)
    : null;
  const dominantHand = DOMINANT_HANDS.includes(raw.dominantHand as DominantHand)
    ? (raw.dominantHand as DominantHand)
    : null;

  const painAreas: PainArea[] = Array.isArray(raw.painAreas)
    ? (raw.painAreas as unknown[]).filter(
        (x): x is PainArea =>
          typeof x === 'string' && PAIN_AREAS.includes(x as PainArea),
      )
    : [];

  if (
    heightCm === null &&
    weightKg === null &&
    experience === null &&
    dominantHand === null &&
    painAreas.length === 0
  ) {
    return null;
  }

  return { heightCm, weightKg, experience, painAreas, dominantHand };
}

// 라이브 프로필 구독 (마이페이지 read / old-doc fallback 전용). 결과 화면 기본
// 소스 아님 (결과는 AnalysisDoc.bodyProfile snapshot 을 읽음, R1).
export function useBodyProfile(): {
  profile: BodyProfile | null;
  loading: boolean;
} {
  const [profile, setProfile] = useState<BodyProfile | null>(null);
  const [loading, setLoading] = useState<boolean>(!!auth.currentUser);
  const [uid, setUid] = useState<string | null>(auth.currentUser?.uid ?? null);

  // 콜드스타트 race 대비 — 게스트 uid 가 mount 시 미준비일 수 있음.
  useEffect(() => {
    const unsub = onAuthStateChanged(auth, (u) => setUid(u?.uid ?? null));
    return unsub;
  }, []);

  useEffect(() => {
    if (!uid) {
      setProfile(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    const ref = doc(db, 'users', uid);
    const unsub = onSnapshot(
      ref,
      (snap) => {
        const raw = snap.exists()
          ? (snap.data()?.bodyProfile as Record<string, unknown> | undefined)
          : undefined;
        setProfile(normalizeBodyProfile(raw));
        setLoading(false);
      },
      (err: FirestoreError) => {
        if (__DEV__) console.warn('[useBodyProfile] error', err);
        setProfile(null);
        setLoading(false);
      },
    );
    return unsub;
  }, [uid]);

  return { profile, loading };
}

// [R5] one-shot 읽기 — loading.tsx 의 snapshot 전용 (raw getDoc spread 금지 강제).
// client normalize + all-empty→null 규칙이 helper 안에 박제됨. all-empty → null
// 이면 caller 가 snapshot 을 생략한다 (graceful).
export async function getBodyProfileOnce(): Promise<BodyProfile | null> {
  const uid = auth.currentUser?.uid;
  if (!uid) return null;
  const snap = await getDoc(doc(db, 'users', uid));
  const raw = snap.exists()
    ? (snap.data()?.bodyProfile as Record<string, unknown> | undefined)
    : undefined;
  return normalizeBodyProfile(raw);
}

// 부분 입력 merge-write (D-06). 기존 필드 보존하며 전달된 필드만 갱신.
export async function saveBodyProfile(
  partial: Partial<BodyProfile>,
): Promise<void> {
  const uid = auth.currentUser?.uid;
  if (!uid) throw new Error('로그인이 필요합니다.');
  await setDoc(
    doc(db, 'users', uid),
    { bodyProfile: { ...partial, updatedAt: Date.now() } },
    { merge: true },
  );
}

// 첫 분석 권유 모달 once-flag (03-03). 본 helper 도 merge — 다른 프로필 필드 보존.
export async function dismissBodyProfilePrompt(): Promise<void> {
  const uid = auth.currentUser?.uid;
  if (!uid) throw new Error('로그인이 필요합니다.');
  await setDoc(
    doc(db, 'users', uid),
    { bodyProfile: { promptDismissedAt: Date.now() } },
    { merge: true },
  );
}

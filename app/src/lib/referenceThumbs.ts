// 기준 동작 썸네일 URL 데이터 소스 (quick-260930-w9l).
//
// 공급자 링크로 등록된 기준 동작은 Pod 가 서 있는 시작 창 가운데 프레임으로 thumb.jpg 를 만들고
// 공개 doc 에 S3 키(thumbnailS3Key)만 적는다. 화면은 이 훅으로 1시간 서명 URL 을 받는다 —
// POST /playback-url {referenceMotionId, asset: 'thumbnail'} (api.ts fetchReferenceThumbUrl).
// doc 에 URL 을 박지 않는 이유 = 서명 URL 은 만료된다(motionThumbs.ts 머리 주석의 함정).
//
// 규율(userAnalyses · referenceMotions 와 같은 데이터 소스 격리):
//   · 키가 없으면 요청하지 않고 null — 번들 썸네일(기존 11개)이 있는 화면은 키 대신 null 을 넘긴다.
//   · 모듈 Map 캐시: 같은 motionId + 같은 키이고 만료까지 5분 넘게 남으면 재사용.
//   · 진행 중 요청 공유: 목록의 여러 행이 같은 동작을 동시에 물어도 요청은 1개.
//   · 실패는 null(아이콘/회색 자리) — 재시도 루프 없음, console.log 없음. 다음 마운트 때 다시 묻는다.
//   · 언마운트 뒤 setState 금지.

import { useEffect, useState } from 'react';
import { fetchReferenceThumbUrl } from './api';

const REUSE_MARGIN_MS = 5 * 60 * 1000;

type Entry = { key: string; url: string; expiresAtMs: number };

const cache = new Map<string, Entry>();
const inflight = new Map<string, Promise<Entry | null>>();

function fresh(entry: Entry | undefined, key: string, now: number): entry is Entry {
  return !!entry && entry.key === key && entry.expiresAtMs - now > REUSE_MARGIN_MS;
}

function load(motionId: string, key: string): Promise<Entry | null> {
  const id = `${motionId}\n${key}`;
  const pending = inflight.get(id);
  if (pending) return pending;
  const p = fetchReferenceThumbUrl(motionId)
    .then((res) => {
      const entry: Entry = { key, url: res.url, expiresAtMs: Date.now() + res.expiresInSec * 1000 };
      cache.set(motionId, entry);
      return entry;
    })
    .catch(() => null)
    .finally(() => {
      inflight.delete(id);
    });
  inflight.set(id, p);
  return p;
}

/**
 * 기준 동작 썸네일의 표시 URL. thumbnailS3Key 가 없거나 요청이 실패하면 null.
 * 훅은 조건 없이 부르고, 번들 썸네일이 있는 동작이면 thumbnailS3Key 자리에 null 을 넘긴다.
 */
export function useReferenceThumbUri(
  motionId: string,
  thumbnailS3Key: string | null | undefined,
): string | null {
  const key = typeof thumbnailS3Key === 'string' && thumbnailS3Key.length > 0 ? thumbnailS3Key : null;
  const [uri, setUri] = useState<string | null>(() => {
    if (!key) return null;
    const hit = cache.get(motionId);
    return fresh(hit, key, Date.now()) ? hit.url : null;
  });

  useEffect(() => {
    if (!key) {
      setUri(null);
      return;
    }
    const hit = cache.get(motionId);
    if (fresh(hit, key, Date.now())) {
      setUri(hit.url);
      return;
    }
    let alive = true;
    void load(motionId, key).then((entry) => {
      if (alive) setUri(entry ? entry.url : null);
    });
    return () => {
      alive = false;
    };
  }, [motionId, key]);

  return uri;
}

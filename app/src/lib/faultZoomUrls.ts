// 확대 비교 PNG 열람 시점 재발급 (quick-260824-q6p).
//
// 결함: faultZoomComparisons[].imageUrl 은 분석 시점 7일 presigned — 7일 넘은
// doc 을 열면 비교 패널이 전부 회색이 된다 (belle 08-24 실기기). 영상 링크는
// result.tsx freshMyUrl/freshPrevUrl/freshRefUrl 이 이미 해결했고, 죽는 것은
// zoom PNG 뿐이었다. 이 모듈이 그 마지막 조각을 같은 선례(6일 마진 재발급 +
// fail-closed 폴백)로 배선한다.
//
// 구조: 순수 함수(zoomCardKey/buildFreshZoomUrlMap — node --test 고정) + RN 훅
// (useFreshFaultZoomUrls). './api' 는 **지연 동적 import** — 값 import 를 걸면
// node --test 가 이 모듈을 로드할 때 './api' → './firebase' 체인이 평가되며
// RN 전용 전역(__DEV__)·firebase 초기화가 plain node 에서 터진다. 훅이 실제
// 호출되는 RN 런타임에서만 로드된다 (Metro 는 dynamic import 지원).

import { useEffect, useRef, useState } from 'react';

import type { FaultZoomUrlItem } from './api';
import type { FaultZoomComparison } from '../types/analysis';

// result.tsx freshMyUrl(:973) 선례와 동일 마진·동일 근거 — presigned 7일 TTL 에
// 하루 안전 마진. 6일 미만 doc 은 저장 imageUrl 이 아직 유효하다.
const SAFE_TTL_MS = 6 * 24 * 60 * 60 * 1000;

/**
 * 카드 join 키 — 서버 canonical key 유일성 축(tier × key_base)과 동형.
 *
 * 백엔드 s3keys.build_fault_zoom_key lockstep: tier 'advisory' 만 별도
 * prefix(zoom_adv_), key_base = criterion(있으면) or joint. doc item 과 서버
 * echo item(contract.md "asset: 'faultZoom'" 응답) **양쪽에 같은 함수**를
 * 적용해 조인한다 — 재료 필드(tier/criterion/joint)가 동일하므로 키도 동일.
 * S3 key 문자열 자체를 재구성하지 않는 이유: 앱은 uid/키 규칙을 몰라야 한다
 * (H-05 — key 는 서버 소유).
 */
export function zoomCardKey(z: {
  tier?: string | null;
  criterion?: string;
  joint: string;
}): string {
  return (z.tier === 'advisory' ? 'adv:' : 'conf:') + (z.criterion || z.joint);
}

/** 서버 echo items → zoomCardKey 조회 맵. 불량 item(빈 joint/URL)은 무시. */
export function buildFreshZoomUrlMap(
  items: FaultZoomUrlItem[],
): Record<string, string> {
  const map: Record<string, string> = {};
  for (const it of items) {
    if (it == null || typeof it !== 'object') continue;
    if (typeof it.joint !== 'string' || it.joint.length === 0) continue;
    if (typeof it.playbackUrl !== 'string' || it.playbackUrl.length === 0) {
      continue;
    }
    map[zoomCardKey(it)] = it.playbackUrl;
  }
  return map;
}

// './api' 지연 로드 (모듈 헤더 주석 참조 — node --test 안전).
async function fetchFresh(analysisId: string) {
  const { fetchFaultZoomUrls } = await import('./api');
  return fetchFaultZoomUrls(analysisId);
}

/**
 * 확대 비교 fresh URL 훅 — freshMyUrl 선례 미러 (fail-closed).
 *
 * · 자동 재발급: doc 이 6일 넘었고 카드가 있으면 mount 시 1회 배치 재발급.
 * · onZoomImageError: Image 로드 실패 시 나이 무관 재발급 (시계 오차·조기 만료
 *   커버). ref single-flight — mount 당 최대 1회 (재발급 URL 도 실패하면 다시
 *   onError 가 도는 무한 루프 차단).
 * · 실패(네트워크·미배포 백엔드의 400 bad_request 포함) = 맵 비움 유지 + __DEV__
 *   warn 만 — 렌더 경계의 `freshZoomUrls[key] ?? zoom.imageUrl` 폴백이 현행 회색
 *   fail-closed 그대로다. **백엔드 배포 전 앱이 먼저 나가도 회귀 0 인 순서
 *   독립성이 이 폴백의 존재 이유다.**
 * · doc item 무변형 — 맵은 렌더 경계에서만 조회한다 (deductionSheet.ts 의
 *   imageUrl 동일성 비교는 doc 저장값끼리라 무접촉).
 */
export function useFreshFaultZoomUrls(args: {
  analysisId: string;
  createdAt: number | undefined;
  comparisons: FaultZoomComparison[] | null | undefined;
}): {
  freshZoomUrls: Record<string, string>;
  onZoomImageError: () => void;
} {
  const { analysisId, createdAt, comparisons } = args;
  const [freshZoomUrls, setFreshZoomUrls] = useState<Record<string, string>>(
    {},
  );
  const errorRefetchDone = useRef(false);
  const hasComparisons = comparisons != null && comparisons.length > 0;

  useEffect(() => {
    // 분석 전환 시 리셋 — 다른 doc 의 fresh 맵·onError single-flight 가 남지
    // 않게 (renderedUnavailable 세션 리셋 선례).
    setFreshZoomUrls({});
    errorRefetchDone.current = false;
    if (!analysisId || !hasComparisons) return;
    const age = Date.now() - (createdAt || 0);
    if (age < SAFE_TTL_MS) return; // 만료 전 — 저장 imageUrl 그대로 사용.
    let cancelled = false;
    fetchFresh(analysisId)
      .then((resp) => {
        if (!cancelled) setFreshZoomUrls(buildFreshZoomUrlMap(resp.items));
      })
      .catch((err) => {
        if (__DEV__) console.warn('[playback-url] faultZoom 재발급 실패', err);
      });
    return () => {
      cancelled = true;
    };
  }, [analysisId, createdAt, hasComparisons]);

  const onZoomImageError = () => {
    if (errorRefetchDone.current) return;
    errorRefetchDone.current = true;
    if (!analysisId || !hasComparisons) return;
    fetchFresh(analysisId)
      .then((resp) => setFreshZoomUrls(buildFreshZoomUrlMap(resp.items)))
      .catch((err) => {
        if (__DEV__) {
          console.warn('[playback-url] faultZoom onError 재발급 실패', err);
        }
      });
  };

  return { freshZoomUrls, onZoomImageError };
}

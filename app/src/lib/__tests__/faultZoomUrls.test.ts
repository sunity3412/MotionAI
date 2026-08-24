// 확대 비교 재발급 순수 함수 검증 (quick-260824-q6p).
//
// 실행: node --test app/src/lib/__tests__/faultZoomUrls.test.ts
// cueTrack.test.ts 관례 — node:test / node:assert + `.ts` import, 신규 의존성 0.
// 훅(useFreshFaultZoomUrls)은 RN 런타임(effect/fetch/__DEV__)이라 여기서 제외 —
// 순수 함수(zoomCardKey/buildFreshZoomUrlMap)만 고정한다.
//
// zoomCardKey 는 백엔드 s3keys.build_fault_zoom_key 의 유일성 축(tier×key_base)
// 과 동형이어야 한다 — advisory 만 별도 prefix, key_base = criterion or joint.

import test from 'node:test';
import assert from 'node:assert/strict';
import { buildFreshZoomUrlMap, zoomCardKey } from '../faultZoomUrls.ts';
import type { FaultZoomUrlItem } from '../api.ts';

test('zoomCardKey: advisory tier 는 adv: prefix — 서버 zoom_adv_ 축과 동형', () => {
  assert.equal(
    zoomCardKey({ tier: 'advisory', joint: 'left_shoulder' }),
    'adv:left_shoulder',
  );
});

test('zoomCardKey: confirmed/부재/null tier 는 conf: prefix (legacy=confirmed 취급)', () => {
  assert.equal(
    zoomCardKey({ tier: 'confirmed', joint: 'left_knee' }),
    'conf:left_knee',
  );
  assert.equal(zoomCardKey({ joint: 'left_knee' }), 'conf:left_knee');
  assert.equal(zoomCardKey({ tier: null, joint: 'left_knee' }), 'conf:left_knee');
});

test('zoomCardKey: criterion 우선 — 두 record 의 대표 관절이 같아도 키가 갈린다', () => {
  assert.equal(
    zoomCardKey({
      tier: 'confirmed',
      criterion: 'angle_vs_reference__left_knee',
      joint: 'left_knee',
    }),
    'conf:angle_vs_reference__left_knee',
  );
  // 빈 criterion 은 joint 폴백 — 서버 key_base(criterion 비어있지 않을 때만)와 정합.
  assert.equal(
    zoomCardKey({ tier: 'confirmed', criterion: '', joint: 'left_knee' }),
    'conf:left_knee',
  );
});

test('buildFreshZoomUrlMap: echo items → zoomCardKey 조회 맵', () => {
  const items: FaultZoomUrlItem[] = [
    {
      joint: 'left_knee',
      tier: 'confirmed',
      criterion: 'split_angle',
      playbackUrl: 'https://fresh.example/zoom_split_angle.png',
    },
    {
      joint: 'left_shoulder',
      tier: 'advisory',
      playbackUrl: 'https://fresh.example/zoom_adv_left_shoulder.png',
    },
  ];
  const map = buildFreshZoomUrlMap(items);
  // doc item 에 같은 함수를 적용하면 같은 키로 조회된다 (join 동형성).
  // (strict deepEqual 은 타입을 기대 리터럴로 좁히므로 조회를 먼저 한다.)
  const docItem = {
    joint: 'left_knee',
    tier: 'confirmed' as const,
    criterion: 'split_angle',
  };
  assert.equal(
    map[zoomCardKey(docItem)],
    'https://fresh.example/zoom_split_angle.png',
  );
  assert.deepEqual(map, {
    'conf:split_angle': 'https://fresh.example/zoom_split_angle.png',
    'adv:left_shoulder': 'https://fresh.example/zoom_adv_left_shoulder.png',
  });
});

test('buildFreshZoomUrlMap: 불량 item(빈 joint/URL·비객체)은 조용히 무시 — 부분 성공 보존', () => {
  const items = [
    { joint: '', playbackUrl: 'https://x/1.png' },
    { joint: 'left_knee', playbackUrl: '' },
    null,
    'garbage',
    { joint: 'right_elbow', playbackUrl: 'https://x/ok.png' },
  ] as unknown as FaultZoomUrlItem[];
  assert.deepEqual(buildFreshZoomUrlMap(items), {
    'conf:right_elbow': 'https://x/ok.png',
  });
});

test('buildFreshZoomUrlMap: 빈 배열 → 빈 맵 (렌더 경계 폴백이 저장 imageUrl 유지)', () => {
  assert.deepEqual(buildFreshZoomUrlMap([]), {});
});

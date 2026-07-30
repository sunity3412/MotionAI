// 일러스트 장면일치 판정 (quick-260731-2jt — 33-G S13/S25).
//
// 승인 스펙 원본 = `.planning/phases/33-result-trust-recovery/mockups/index.html`
// (7R, belle 승인 2026-07-29) `DETAILS`. 승인본은 일러스트를 **항목(부위)별 데이터**로
// 둔다 — legs 시트 `:1047` = "파워스핀 위·아래 일자 스플릿" / shoulder 시트 `:1073` =
// "그립 어깨 견갑 고정" / refonly 시트 `:1081` = **null**. 세 시트가 서로 다른 값을
// 갖고, null 이면 슬롯 DOM 자체가 생기지 않는다 (`:1114` `if(d.illust)` — 빈 박스나
// 플레이스홀더가 아니라 **자리 자체가 없음**).
//
// 현 구현의 결함 (belle 확인 ② #8·#9·#11 = 33-G S13/S25 FAIL): 배선이 motionId 만 키로
// 써서 **동작당 1장을 그 동작의 모든 항목에 공통 부착**했다 → 어깨 항목에 다리 일러스트.
// "말하는 부위 = 가리키는 부위" 원리의 일러스트 축 위반이고, 틀린 그림은 없는 것보다
// 나쁘다 (D-43 · D-15 동원리).
//
// 왜 순수 모듈인가 (P-5): `require('*.jpg')` 를 가진 모듈은 `node --test` 로 실행할 수
// 없다 (Node 가 jpg 를 못 읽는다). 규칙을 떼어내야 렌더 환경 없이 검증할 수 있다.
// 에셋 require 맵은 DefectIllustration 이 계속 소유하고, **두 표의 키 목록 일치는
// grep/diff 게이트로 봉인**한다 (한쪽만 늘면 "메타는 있는데 그림이 없는" 조용한 실패).
//
// 불변식:
//   - 동작명 조건 분기 0 (D-41) — 거동은 아래 데이터 맵으로만 갈린다.
//   - 부위 단위 = `deductionSheet.regionPartKeyForRecord` 의 키 (P-1). 두 번째 그룹핑
//     규칙 금지 — 마커 그룹·부위 칩·부위 시트가 이미 그 키 하나로 통일돼 있다.
//   - 매칭 = **항목 부위 토큰 ⊆ 장면 부위 토큰** (전부 포함, P-2). 부분 겹침은
//     불일치다 — 일부만 담은 그림은 나머지 부위에 대해 틀린 그림이다.
//   - 토큰 공집합·criterion 단독 그룹은 규칙 **앞** 게이트에서 즉시 미부착 (P-3).
//     공집합은 부분집합 판정이 vacuously 참이라 게이트가 없으면 모든 에셋과 매칭된다
//     (fail-closed 가 정반대로 뒤집히는 버그).
//   - 장면 토큰은 33-14 기록 + **에셋 실물 열람**에서만 부여한다 (P-4). `provenance`
//     없는 등재 금지. 확신이 안 서면 토큰을 **빼는** 쪽(= 덜 붙는 쪽)이 정답이다.
//   - 저장값·번들 에셋 read-only. 점수/판정 재계산 0 (deductionSheet 헤더 계승).
//
// 미구현(의도된 공백):
//   - **어깨·팔 부위용 일러스트 세트.** 등재 6장은 실물 열람 결과 전부 다리 장면이라
//     어깨·팔 항목에는 아무것도 붙지 않는다. 신규 생성은 생성·검수 라운드가 필요해
//     수리 사이클 밖(D-43)이다. **부착 건수가 주는 것은 결함이 아니라 이 수리의 목적**
//     이고, 억지 매칭으로 건수를 지키는 것이 belle 반려의 재생산이다.

import { BODY_PART_OF_KEYPOINT } from './deductionLabels.ts';

/** criterion 단독 그룹 키 접두 — deductionSheet 와 문자 동일 (투영 공집합 갈래). */
const CRITERION_GROUP_PREFIX = 'criterion:';

/**
 * 유효 부위 토큰 = `BODY_PART_OF_KEYPOINT` 의 **치역 재사용** (P-1 — 새 부위 사전
 * 신설 금지). 오타 토큰(`legs` 같은)이 조용히 미매칭으로 흘러 "왜 안 붙지"가 되는
 * 것을 단위 테스트가 잡을 수 있도록 여기서 한 벌만 파생한다.
 */
const VALID_PART_TOKENS: ReadonlySet<string> = new Set<string>(
  Object.values(BODY_PART_OF_KEYPOINT),
);

export interface IllustrationScene {
  /**
   * 이 그림이 **가리키는** 부위 토큰. "프레임에 보이는" 부위가 아니다 — 전신 그림은
   * 언제나 어깨·팔이 보이므로 가시성으로 토큰을 주면 전부 매칭되어 지금의 결함이
   * 그대로 남는다. 판정 축 = 가이드 표시(곧은 선 / 부위 원)가 어느 부위 위에 얹혀
   * 있는가 + 그림이 강조하는 신체 부위가 무엇인가 (승인본 shoulder 시트의
   * "그립 어깨 견갑 고정"이 그 그림의 **주제**를 말하는 것과 같은 축).
   */
  readonly parts: readonly string[];
  /**
   * 토큰 부여 근거 1줄 박제 (P-4). 화면 미노출 — 내부 검수용. 문서 근거와 실물
   * 열람 결과가 함께 들어가야 한다 (문서만 보고 정하면 D-40 위반).
   */
  readonly provenance: string;
}

/**
 * 등재 에셋의 장면 메타. 키 = reference 라이브러리 motionId (동작명 코드 분기가 아니라
 * **데이터 맵** — 33-14 배선 규약 계승). 항목 추가 = 33-14 검수 게이트 재수행 +
 * 실물 열람 후에만.
 *
 * **6/6 전부 다리 장면이 관찰 결과다.** 목표가 아니라 관측이다 (P-4): 가이드 표시가
 * 실제로 다리 위에만 얹혀 있고, 팔·어깨 쪽 정직 노트는 전부 "재구성/반전/굽은 그립"
 * 같은 UNVERIFIED 축이라 토큰 부여 근거가 되지 않는다.
 */
export const ILLUSTRATION_SCENES: Record<string, IllustrationScene> = {
  'ref-power-spin': {
    parts: ['leg'],
    provenance:
      '33-14 입력 8.50s (두 다리 폴 축 한 줄 최곧음) · 채택본 검수 provenance = 수직 스플릿·선 한 줄 · 실물 열람 = 붉은 직선 1줄이 위 다리 발끝→골반→아래 다리 발끝 관통, 그립 팔·어깨에는 표시 없음',
  },
  'ref-kip-up': {
    parts: ['leg'],
    provenance:
      '33-14 입력 3.75s (등면 와이드 스트래들 + 양 무릎 신전) · 검수 PASS 세부 = 선 2줄 곧음 · 실물 열람 = 좌·우 다리에 각각 붉은 직선(골반→무릎→발목), 든 팔·어깨 표시 없음. 정직 노트의 그립 팔 좌우 반전은 UNVERIFIED 축이라 팔 토큰 근거가 되지 않는다',
  },
  'ref-climb': {
    parts: ['leg'],
    provenance:
      '33-14 입력 5.25s (X자 잠금) · 검수 PASS 세부 = 부위 원 · 실물 열람 = 붉은 원 1개가 앞무릎 중심(뒷무릎 일부 포함 — 33-14 정직 노트와 일치). 아래 그립 팔은 실측 신전이 아닌 굽은 스태거로 그려졌다는 정직 노트가 있어 팔 토큰 부여 불가',
  },
  'ref-invert': {
    parts: ['leg'],
    provenance:
      '33-14 입력 7.25s (대칭 와이드 스플릿 최대 개방) · 검수 PASS(try2) 세부 = 선 2줄 곧음 · 실물 열람 = 좌·우 다리에 각각 붉은 직선, 어깨·팔 표시 없음 (벌림각 과소 표현은 33-14 정직 노트 — 목표 방향 동일)',
  },
  'ref-foxtop': {
    parts: ['leg'],
    provenance:
      '33-14 입력 18.25s (위 다리 수직 + 아래 다리 신전) · 33-14 Deviation 4 로 highlight = 위 다리 한 줄 확정 · 실물 열람 = 붉은 직선 1줄이 위(수직) 다리 골반→발끝, 아래 다리·팔 표시 없음',
  },
  'ref-foxtop-split': {
    parts: ['leg'],
    provenance:
      '33-14 입력 12.25s (신전측 다리 곧음 + 벌림 개방) · 6R 선 교정 후 검수 = 직선이 다리 위에만·잔재 0 · 실물 열람 = 굵은 붉은 직선 1줄이 수평 신전 다리 골반→발끝, 어깨·팔 표시 없음',
  },
};

/**
 * 항목 부위 토큰이 장면 부위 토큰에 **전부** 덮이는가 (P-2 부분집합 규칙 1벌).
 *
 * 공집합 게이트가 규칙 **안**에 있는 이유 (P-3): 어느 호출자를 통해 들어와도
 * 공집합이 vacuously 참이 되지 않아야 한다. 밖에 두면 새 소비처가 게이트를 건너뛴다.
 *
 * 등재 에셋 6장이 전부 같은 계열이라(다리) 실맵만으로는 "부분 겹침 → 불일치" 분기를
 * 밟을 수 없다. 규칙을 합성 토큰으로 고정할 수 있도록 export 한다 (P-13).
 */
export function sceneCoversParts(
  itemTokens: readonly string[] | null | undefined,
  sceneParts: readonly string[] | null | undefined,
): boolean {
  if (!Array.isArray(itemTokens) || itemTokens.length === 0) return false;
  if (!Array.isArray(sceneParts) || sceneParts.length === 0) return false;
  const scene = new Set<string>(sceneParts);
  return itemTokens.every(
    (token) => VALID_PART_TOKENS.has(token) && scene.has(token),
  );
}

/**
 * 부위 그룹 키 → 부위 토큰 배열. 판정 불가면 null (fail-closed).
 *   - `criterion:` 접두 = 투영 keypoint 공집합 갈래 → 항상 null (P-3).
 *   - 빈 문자열·공백만 → null.
 * 토큰 유효성은 `sceneCoversParts` 가 마지막으로 한 번 더 본다 (규칙 사본 0).
 */
function partTokensOfKey(partKey: string): string[] | null {
  if (partKey.startsWith(CRITERION_GROUP_PREFIX)) return null;
  const tokens = partKey
    .split('+')
    .map((t) => t.trim())
    .filter((t) => t.length > 0);
  return tokens.length > 0 ? tokens : null;
}

/**
 * 이 항목(부위)에 붙일 일러스트의 motionId. 붙일 수 없으면 null.
 *
 * 순서 = ① 입력 유효성 ② 부위 토큰 산출(공집합·criterion 즉시 차단, P-3)
 *        ③ 등재 장면 조회 ④ 부분집합 판정 (P-2).
 *
 * null 갈래 (전부 조용한 hidden — 배너·안내 문구 0):
 *   - mode3 / 미등재 동작 / 에셋 미보유 4동작 → motionId 부재이거나 맵에 없음
 *   - 항목 부위가 장면과 어긋남 → **이 수리의 목적** (어깨 항목에 다리 그림 차단)
 *   - 투영 공집합 항목 → 가리킬 부위가 없어 어떤 그림도 맞다고 말할 수 없음
 */
export function illustrationMotionForPart(
  motionId: string | null | undefined,
  partKey: string | null | undefined,
): string | null {
  if (typeof motionId !== 'string' || motionId.length === 0) return null;
  if (typeof partKey !== 'string' || partKey.length === 0) return null;
  const tokens = partTokensOfKey(partKey);
  if (tokens === null) return null;
  if (!Object.prototype.hasOwnProperty.call(ILLUSTRATION_SCENES, motionId)) {
    return null;
  }
  const scene = ILLUSTRATION_SCENES[motionId];
  if (!scene) return null;
  return sceneCoversParts(tokens, scene.parts) ? motionId : null;
}

/**
 * 같은 판정의 boolean 형 — 렌더 여부만 알면 되는 소비처용 (음성 중 illu-float 콜백).
 * 독립 구현 금지: 판정이 두 벌이 되면 시트와 영상 위가 서로 다른 그림을 보여준다.
 */
export function hasIllustrationFor(
  motionId: string | null | undefined,
  partKey: string | null | undefined,
): boolean {
  return illustrationMotionForPart(motionId, partKey) !== null;
}

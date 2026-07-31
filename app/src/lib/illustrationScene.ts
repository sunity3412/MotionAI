// 일러스트 장면일치 판정 (quick-260731-2jt — 33-G S13/S25 · quick-260731-plf — §C-4 3번).
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
// **왜 표가 배열인가 (quick-260731-plf, §C-4 3번).** 2jt 는 틀린 부착을 끊어 절반을
// 닫았고(어깨 항목에 다리 그림 0), 이 플랜이 맞는 부착을 채워 나머지를 닫는다. 그런데
// 종전 자료구조는 `Record<motionId, Scene>` 이라 **한 동작에 다리 그림과 어깨 그림을
// 같이 둘 자리가 없었다**. 승인본이 legs/shoulder/refonly 시트에 서로 다른 일러스트
// 값을 두므로 부위별 개별 에셋이 승인 스펙이고, 따라서 키가 `(motionId, parts)` 여야
// 한다. 배열 + 필터가 그 키의 가장 단순한 형태다.
//
// **`asset` 은 파생 규칙이 아니라 명시 데이터다.** `{motionId}--{parts}` 로 기계 파생하지
// 않는다 — 33-14 통과 6장은 접미 없는 `{motionId}.jpg` 로 이미 belle 열람을 통과해 번들에
// 들어가 있고(승인 자산), 파생 규칙을 도입하면 그 6개 파일의 경로·바이트를 건드려야
// 한다(L-10 위반). 그래서 기존 6항목의 `asset` 은 `motionId` 와 문자 동일하게 남고,
// 신규 항목만 `{motionId}--{parts를 '-' 로 이은 것}` 규칙으로 이름을 짓는다. 규칙이
// 아니라 값이므로 표를 읽으면 어느 파일이 붙는지 그대로 보인다.
//
// 왜 순수 모듈인가 (P-5): `require('*.jpg')` 를 가진 모듈은 `node --test` 로 실행할 수
// 없다 (Node 가 jpg 를 못 읽는다). 규칙을 떼어내야 렌더 환경 없이 검증할 수 있다.
// 에셋 require 맵은 DefectIllustration 이 계속 소유하고, **두 표의 키 목록 일치는
// grep/diff 게이트로 봉인**한다 (한쪽만 늘면 "메타는 있는데 그림이 없는" 조용한 실패).
//
// 불변식:
//   - 동작명 조건 분기 0 (D-41) — 거동은 아래 데이터 표로만 갈린다.
//   - 부위 단위 = `deductionSheet.regionPartKeyForRecord` 의 키 (P-1). 두 번째 그룹핑
//     규칙 금지 — 마커 그룹·부위 칩·부위 시트가 이미 그 키 하나로 통일돼 있다.
//   - 매칭 = **항목 부위 토큰 ⊆ 장면 부위 토큰** (전부 포함, P-2). 부분 겹침은
//     불일치다 — 일부만 담은 그림은 나머지 부위에 대해 틀린 그림이다.
//   - 복수 후보가 덮으면 **가장 구체적인 장면**(parts 최소)이 이긴다. 어깨 항목에는
//     어깨 전용 그림이, 어깨+팔 항목에는 두 부위를 함께 짚는 그림이 가야 한다.
//   - 토큰 공집합·criterion 단독 그룹은 규칙 **앞** 게이트에서 즉시 미부착 (P-3).
//     공집합은 부분집합 판정이 vacuously 참이라 게이트가 없으면 모든 에셋과 매칭된다
//     (fail-closed 가 정반대로 뒤집히는 버그).
//   - 장면 토큰은 33-14 기록 + **에셋 실물 열람**에서만 부여한다 (P-4). `provenance`
//     없는 등재 금지. 확신이 안 서면 토큰을 **빼는** 쪽(= 덜 붙는 쪽)이 정답이다.
//     전신 그림은 언제나 어깨·팔이 보이므로 **가시성으로 토큰을 주면 전부 매칭되어**
//     belle M-5 반려가 그대로 재생산된다 — 다토큰 장면은 가이드 표시가 실제로 두 부위를
//     함께 짚을 때만 허용한다.
//   - 저장값·번들 에셋 read-only. 점수/판정 재계산 0 (deductionSheet 헤더 계승).
//
// 부착 범위 (현 상태 — 목표가 아니라 관측):
//   - 다리 6장(33-14) + 어깨/팔 신규분(quick-260731-plf, 아래 표의 `--` 접미 항목).
//   - 표에 없는 (동작 × 부위) 조합은 **조용히 미부착**으로 남는다. 억지 매칭으로
//     건수를 채우는 것이 belle 반려의 재생산이므로, 미완은 SUMMARY 에 이름과 사유로
//     남기고 화면에는 자리를 만들지 않는다 (D-43 · D-15).

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
  /** reference 라이브러리 motionId. 같은 동작이 여러 장면을 가질 수 있다. */
  readonly motionId: string;
  /**
   * 이 그림이 **가리키는** 부위 토큰. "프레임에 보이는" 부위가 아니다 — 전신 그림은
   * 언제나 어깨·팔이 보이므로 가시성으로 토큰을 주면 전부 매칭되어 지금의 결함이
   * 그대로 남는다. 판정 축 = 가이드 표시(곧은 선 / 부위 원)가 어느 부위 위에 얹혀
   * 있는가 + 그림이 강조하는 신체 부위가 무엇인가 (승인본 shoulder 시트의
   * "그립 어깨 견갑 고정"이 그 그림의 **주제**를 말하는 것과 같은 축).
   */
  readonly parts: readonly string[];
  /**
   * 에셋 조회 키 = `DefectIllustration.VERIFIED_ILLUSTRATIONS` 의 키이자 파일명
   * (`app/assets/illustrations/{asset}.jpg`). 헤더 참조 — **명시 데이터**이지
   * motionId·parts 로부터의 파생 규칙이 아니다.
   */
  readonly asset: string;
  /**
   * 토큰 부여 근거 1줄 박제 (P-4). 화면 미노출 — 내부 검수용. 문서 근거와 실물
   * 열람 결과가 함께 들어가야 한다 (문서만 보고 정하면 D-40 위반).
   */
  readonly provenance: string;
}

/**
 * 등재 에셋의 장면 표 (동작명 코드 분기가 아니라 **데이터** — 33-14 배선 규약 계승).
 * 항목 추가 = 33-14 검수 게이트 4종 재수행 + 실물 열람 후에만.
 *
 * 다리 6장 = 33-14 통과본. 그 6장의 `asset` 이 `motionId` 와 문자 동일한 이유는 헤더
 * 참조(승인 자산 무접촉). 어깨/팔 항목 = quick-260731-plf 생성·검수분.
 */
export const ILLUSTRATION_SCENES: readonly IllustrationScene[] = [
  {
    motionId: 'ref-power-spin',
    parts: ['leg'],
    asset: 'ref-power-spin',
    provenance:
      '33-14 입력 8.50s (두 다리 폴 축 한 줄 최곧음) · 채택본 검수 provenance = 수직 스플릿·선 한 줄 · 실물 열람 = 붉은 직선 1줄이 위 다리 발끝→골반→아래 다리 발끝 관통, 그립 팔·어깨에는 표시 없음',
  },
  {
    motionId: 'ref-kip-up',
    parts: ['leg'],
    asset: 'ref-kip-up',
    provenance:
      '33-14 입력 3.75s (등면 와이드 스트래들 + 양 무릎 신전) · 검수 PASS 세부 = 선 2줄 곧음 · 실물 열람 = 좌·우 다리에 각각 붉은 직선(골반→무릎→발목), 든 팔·어깨 표시 없음. 정직 노트의 그립 팔 좌우 반전은 UNVERIFIED 축이라 팔 토큰 근거가 되지 않는다',
  },
  {
    motionId: 'ref-climb',
    parts: ['leg'],
    asset: 'ref-climb',
    provenance:
      '33-14 입력 5.25s (X자 잠금) · 검수 PASS 세부 = 부위 원 · 실물 열람 = 붉은 원 1개가 앞무릎 중심(뒷무릎 일부 포함 — 33-14 정직 노트와 일치). 아래 그립 팔은 실측 신전이 아닌 굽은 스태거로 그려졌다는 정직 노트가 있어 팔 토큰 부여 불가',
  },
  {
    motionId: 'ref-invert',
    parts: ['leg'],
    asset: 'ref-invert',
    provenance:
      '33-14 입력 7.25s (대칭 와이드 스플릿 최대 개방) · 검수 PASS(try2) 세부 = 선 2줄 곧음 · 실물 열람 = 좌·우 다리에 각각 붉은 직선, 어깨·팔 표시 없음 (벌림각 과소 표현은 33-14 정직 노트 — 목표 방향 동일)',
  },
  {
    motionId: 'ref-foxtop',
    parts: ['leg'],
    asset: 'ref-foxtop',
    provenance:
      '33-14 입력 18.25s (위 다리 수직 + 아래 다리 신전) · 33-14 Deviation 4 로 highlight = 위 다리 한 줄 확정 · 실물 열람 = 붉은 직선 1줄이 위(수직) 다리 골반→발끝, 아래 다리·팔 표시 없음',
  },
  {
    motionId: 'ref-foxtop-split',
    parts: ['leg'],
    asset: 'ref-foxtop-split',
    provenance:
      '33-14 입력 12.25s (신전측 다리 곧음 + 벌림 개방) · 6R 선 교정 후 검수 = 직선이 다리 위에만·잔재 0 · 실물 열람 = 굵은 붉은 직선 1줄이 수평 신전 다리 골반→발끝, 어깨·팔 표시 없음',
  },
  {
    motionId: 'ref-power-spin',
    parts: ['shoulder'],
    asset: 'ref-power-spin--shoulder',
    provenance:
      'plf 입력 8.75s (33-A1 hold 창 7.1~10.2s 내 — 8.50s 는 양 견갑이 상의·머리카락에 가려 교체) · A-1 ④ "양 견갑" · 가이드 = 원(③ "어깨 으쓱하지 마(견갑 안정)" = 잠금 계열) · 실물 열람 + 2x 확대 = 붉은 원 1개가 등면 브라 스트랩 사이 견갑 위에만 있고 다리·팔에는 표시 0, 입력 대조에서 자세 복제 아님 확인',
  },
  {
    motionId: 'ref-kip-up',
    parts: ['shoulder'],
    asset: 'ref-kip-up--shoulder',
    provenance:
      'plf 입력 3.75s (33-A1 스윙~후방 통과 3~5.5s) · A-1 ④ "양 어깨" + fault 가 left/right_shoulder 로 실포착 · 가이드 = 원(③ "어깨 눌러(으쓱 금지)" = 잠금 계열) · 실물 열람 + 2x 확대 = 붉은 원 1개가 등면 좌·우 견갑을 함께 감싸고 다리는 프레임 밖, 그립 손가락 5개 정상',
  },
  {
    motionId: 'ref-elbow-twist-sister',
    parts: ['arm'],
    asset: 'ref-elbow-twist-sister--arm',
    provenance:
      'plf 입력 13.00s (33-A1 메인 hold peak, f117) · A-1 ④ "엘보 그립 팔" · 가이드 = 원(③ "팔꿈치로 감아" = hook 계열, 굽힘이 정답이라 직선 금지) · 실물 열람 + 2x 확대 = 붉은 원 1개가 폴을 감은 팔꿈치 잠금부 위에만 있고 어깨·다리 표시 0, 사지 2팔 2다리 확인(팔꿈치 그립 팔의 전완이 몸통으로 되돌아오는 형상)',
  },
];

/**
 * 항목 부위 토큰이 장면 부위 토큰에 **전부** 덮이는가 (P-2 부분집합 규칙 1벌).
 *
 * 공집합 게이트가 규칙 **안**에 있는 이유 (P-3): 어느 호출자를 통해 들어와도
 * 공집합이 vacuously 참이 되지 않아야 한다. 밖에 두면 새 소비처가 게이트를 건너뛴다.
 *
 * 등재 에셋이 한 계열로만 채워진 구간에서는 실표만으로 "부분 겹침 → 불일치" 분기를
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
 * 이 항목(부위)에 붙일 일러스트의 에셋 키. 붙일 수 없으면 null.
 * 반환값은 `DefectIllustration.VERIFIED_ILLUSTRATIONS` 의 조회 키다.
 *
 * 순서 = ① 입력 유효성 ② 부위 토큰 산출(공집합·criterion 즉시 차단, P-3)
 *        ③ motionId 일치 후보 필터 ④ 부분집합 판정 (P-2) ⑤ 최구체 우선.
 *
 * ⑤ 최구체 우선 = `parts.length` 오름차순, 동률이면 표 등재 순서 먼저. 어깨 항목이
 * 어깨 전용 그림과 어깨+팔 그림 양쪽에 덮일 때 **더 좁게 짚은 그림**이 이긴다 —
 * 넓은 그림은 그 항목에 대해 "가리키는 곳이 둘"이라 덜 정확하기 때문.
 *
 * 배열 순회라 프로토타입 키(`__proto__` 등)로 표를 우회하는 갈래는 원천 소멸하지만,
 * 회귀 방지를 위해 테스트 축은 유지한다.
 *
 * null 갈래 (전부 조용한 hidden — 배너·안내 문구 0):
 *   - mode3 / 미등재 동작 / 에셋 미보유 동작 → motionId 부재이거나 표에 없음
 *   - 항목 부위가 장면과 어긋남 → **이 수리의 목적** (어깨 항목에 다리 그림 차단)
 *   - 투영 공집합 항목 → 가리킬 부위가 없어 어떤 그림도 맞다고 말할 수 없음
 */
export function illustrationAssetForPart(
  motionId: string | null | undefined,
  partKey: string | null | undefined,
): string | null {
  if (typeof motionId !== 'string' || motionId.length === 0) return null;
  if (typeof partKey !== 'string' || partKey.length === 0) return null;
  const tokens = partTokensOfKey(partKey);
  if (tokens === null) return null;

  let best: IllustrationScene | null = null;
  for (const scene of ILLUSTRATION_SCENES) {
    if (scene.motionId !== motionId) continue;
    if (!sceneCoversParts(tokens, scene.parts)) continue;
    if (best === null || scene.parts.length < best.parts.length) best = scene;
  }
  return best === null ? null : best.asset;
}

/**
 * 같은 판정의 boolean 형 — 렌더 여부만 알면 되는 소비처용 (음성 중 illu-float 콜백).
 * 독립 구현 금지: 판정이 두 벌이 되면 시트와 영상 위가 서로 다른 그림을 보여준다.
 * 시그니처·의미 무변경 (result.tsx 무접촉의 근거).
 */
export function hasIllustrationFor(
  motionId: string | null | undefined,
  partKey: string | null | undefined,
): boolean {
  return illustrationAssetForPart(motionId, partKey) !== null;
}

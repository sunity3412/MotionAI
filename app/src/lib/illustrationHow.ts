// "어떻게" 일러스트 오버레이 — 앵커 데이터 + 순수 계산 (quick-260818-nnm).
//
// belle 2026-08-18 결정: 일러스트의 역할은 확대 비교(사진)를 다시 그리는 것이 아니라
// **방법**을 보여주는 것이다. 그림 파일에는 정은지 완벽 자세만 있고(표시 0), 아래 셋은
// 앱이 학생 값으로 그린다:
//   · 잔상 = 그림 속 정은지 다리를 골반 기준으로 학생 각도만큼 돌려 연하게 얹은 것
//            (선이 아니라 다리 픽셀 — belle "사마귀 다리냐". 길이·굵기·선 스타일이 실선과 같다)
//   · 화살표 = 잔상 발 → 실선 발 (시작점이 정의상 "지금 내 자리")
//   · 표기 = 값이 있으면 방향으로: "50° 정도 더 벌리세요". 상태("좁아요") 금지.
//            값이 없으면 잔상·화살표·표기 전부 그리지 않는다 — 모르면 안 그린다.
//
// 왜 잔상까지 앱이 그리나: 잔상 각도는 학생마다 다르다. 그림에 구우면 어떤 학생에게도
// 안 맞는다(첫 생성본이 다리를 완전히 붙여버린 이유). 앱이 그리면 "지금"이 진짜 내 자리다.
//
// 이 파일은 순수 데이터 + 순수 함수만 — require('*.jpg') 도 RN 도 없어서 node --test 로
// 검증 가능(illustrationScene 의 P-5 선례). 그리기는 DefectIllustration 이 한다.
//
// 앵커는 **그림당 한 번** 정하는 값(폭·높이 대비 0~1 비율). 새 그림을 넣을 때 같이 찍는다.
// 좌표계 = 이미지 좌상단 원점, x 오른쪽, y 아래.

/** 0~1 비율 좌표. */
export type Frac = readonly [number, number];

export interface HowLimb {
  /** 회전축 (예: 골반 중심). 잔상은 이 점을 중심으로 돈다. */
  readonly pivot: Frac;
  /** 실선(정은지) 말단 — 화살표의 끝점. */
  readonly tip: Frac;
  /** 잔상으로 잘라낼 영역(다각형). 배경이 균일하니 넉넉해도 티가 안 난다. */
  readonly clip: readonly Frac[];
  /**
   * 학생이 "부족"할 때 이 사지가 도는 방향. +1 = 화면 시계방향, -1 = 반시계.
   * (예: 왼다리를 안쪽으로 모으면 반시계 = -1, 오른다리는 시계 = +1)
   */
  readonly inwardSign: 1 | -1;
}

export interface HowAnchors {
  /** 사지들. 스트래들은 다리 2개, 팔꿈치 하나면 1개. */
  readonly limbs: readonly HowLimb[];
  /** 각 사지 회전량 = 총 각도 차이 × share. 좌우 대칭 스트래들이면 0.5/0.5. */
  readonly shares: readonly number[];
  /**
   * 그림 안에서 잔상 **앞에** 다시 얹을 영역 (폴). 잔상이 폴을 가리면 이상하다.
   * 없으면 생략.
   */
  readonly frontClip?: readonly Frac[];
  /**
   * 방향 문장 틀. `{n}` 에 정수 각도가 들어간다. 이 문장은 상태가 아니라 **행동**이다
   * (belle: "좁다는 표현보다는 벌리라고").
   */
  readonly directionSentence: string;
  /** "지금" 표기를 둘 위치 힌트 — 잔상 발들의 중점 기준 아래 offset(비율). */
  readonly nowLabelOffsetY: number;
}

/**
 * 에셋 키 → 앵커. 없는 에셋은 오버레이를 그리지 않는다(종전 그림 그대로).
 * ref-kip-up--leg: 08-18 solid1 (896x1200 → 720x964 리사이즈, 비율 동일) 에서 실측.
 */
export const HOW_ANCHORS: Readonly<Record<string, HowAnchors>> = {
  'ref-kip-up--leg': {
    limbs: [
      {
        pivot: [0.5, 0.615],
        tip: [0.115, 0.905],
        clip: [
          [0.485, 0.62], [0.38, 0.61], [0.22, 0.72], [0.02, 0.88],
          [0.02, 0.99], [0.22, 0.99], [0.4, 0.8], [0.485, 0.71],
        ],
        inwardSign: -1,
      },
      {
        pivot: [0.5, 0.615],
        tip: [0.885, 0.905],
        clip: [
          [0.515, 0.62], [0.62, 0.61], [0.78, 0.72], [0.98, 0.88],
          [0.98, 0.99], [0.78, 0.99], [0.6, 0.8], [0.515, 0.71],
        ],
        inwardSign: 1,
      },
    ],
    shares: [0.5, 0.5],
    frontClip: [[0.478, 0], [0.522, 0], [0.522, 1], [0.478, 1]],
    directionSentence: '{n}° 정도 더 벌리세요',
    nowLabelOffsetY: 0.03,
  },
};

/** 화면에 그릴 준비가 끝난 오버레이 1건. 좌표는 전부 비율(0~1) — 소비처가 픽셀로 곱한다. */
export interface HowOverlay {
  readonly deltaDeg: number;
  readonly directionText: string;
  readonly limbs: readonly {
    readonly clip: readonly Frac[];
    readonly pivot: Frac;
    /** 잔상 회전각(도). 화면 시계방향 양수. */
    readonly rotateDeg: number;
    /** 잔상 말단(회전 후) — 화살표 시작점·"지금" 점. */
    readonly ghostTip: Frac;
    /** 실선 말단 — 화살표 끝점. */
    readonly tip: Frac;
  }[];
  readonly frontClip?: readonly Frac[];
  /** "지금" 표기 위치. */
  readonly nowLabel: Frac;
}

/** 비율 좌표를 픽셀 비(aspect = H/W)를 고려해 회전. 반환은 다시 비율. */
function rotateFrac(p: Frac, c: Frac, deg: number, aspect: number): Frac {
  // y 축을 aspect 로 늘려 실제 픽셀 공간에서 회전해야 각도가 맞는다.
  const x = p[0] - c[0];
  const y = (p[1] - c[1]) * aspect;
  const r = (deg * Math.PI) / 180;
  const rx = x * Math.cos(r) - y * Math.sin(r);
  const ry = x * Math.sin(r) + y * Math.cos(r);
  return [c[0] + rx, c[1] + ry / aspect];
}

/**
 * 학생 측정값으로 오버레이 계산. 조건이 하나라도 안 맞으면 null — 그리지 않는다.
 *   - 앵커 없는 에셋
 *   - unit 이 'deg' 가 아님
 *   - measured/target 중 하나라도 없음
 *   - 차이가 3° 미만 — 잔상이 실선과 겹쳐 보이지 않는다
 *
 * 차이 = |measured − target|. record 의 수치는 두 모양이 있다 — 절대각(94°→71°) 또는
 * **기준 대비 차이**(50°→0°, kip-up split_angle 실측 배지). 어느 쪽이든 "얼마나"는 절대값이고,
 * "어느 쪽으로"는 이 record 가 아니라 **에셋 앵커**(inwardSign·directionSentence)가 안다 —
 * 그 record 는 그 방향의 결함일 때만 발생하므로(phrasebook 이 한 방향 문장) 방향을 수치
 * 부호에서 읽지 않는다.
 */
export function buildHowOverlay(
  asset: string | null | undefined,
  measured: number | null | undefined,
  target: number | null | undefined,
  unit: string | null | undefined,
  aspect: number,
): HowOverlay | null {
  if (!asset) return null;
  const a = HOW_ANCHORS[asset];
  if (!a) return null;
  if (unit !== 'deg') return null;
  if (typeof measured !== 'number' || typeof target !== 'number') return null;
  if (!Number.isFinite(measured) || !Number.isFinite(target)) return null;
  const delta = Math.abs(target - measured);
  if (delta < 3) return null;
  const n = Math.round(delta);

  const limbs = a.limbs.map((limb, i) => {
    const rot = limb.inwardSign * delta * (a.shares[i] ?? 0);
    return {
      clip: limb.clip,
      pivot: limb.pivot,
      rotateDeg: rot,
      ghostTip: rotateFrac(limb.tip, limb.pivot, rot, aspect),
      tip: limb.tip,
    };
  });
  const gx = limbs.reduce((s, l) => s + l.ghostTip[0], 0) / limbs.length;
  const gy = Math.max(...limbs.map((l) => l.ghostTip[1]));
  return {
    deltaDeg: n,
    directionText: a.directionSentence.replace('{n}', String(n)),
    limbs,
    frontClip: a.frontClip,
    nowLabel: [gx, Math.min(0.96, gy + a.nowLabelOffsetY)],
  };
}

// "어떻게" 일러스트 오버레이 — 앵커 데이터 + 순수 계산 (quick-260818-nnm · quick-260821-gb7).
//
// belle 2026-08-18 결정: 일러스트의 역할은 확대 비교(사진)를 다시 그리는 것이 아니라
// **방법**을 보여주는 것이다. 앱이 학생 값으로 그리는 것:
//   · 화살표 = 잔상 발 → 실선 발 (시작점이 정의상 "지금 내 자리")
//   · 표기 = 값이 있으면 방향으로: "50° 정도 더 벌리세요". 상태("좁아요") 금지.
//            값이 없으면 화살표·표기를 그리지 않는다 — 모르면 안 그린다.
//
// belle 2026-08-21 결정 (quick-260821-gb7, BELLE-0821-1~4): 잔상은 **그림에 구워진**
// 승인 에셋을 쓴다 — exq stage20-1 (보드 실물 3회 확인, 896x1200). 잔상을 앱이
// 회전복사로 그리는 rotate 방식은 이 에셋에서 비활성이다: 잔상이 이미 그림 안에
// 있으므로 clip/pivot/회전 재료가 필요 없고, 앱은 화살표 2개(잔상 발 → 같은 쪽
// 실선 발)와 수치 문장만 그린다(B 방식). 겉모습 원본 =
// `.planning/quick/260821-fe9-20-a-vs-b/out/ref-kip-up--leg__B-overlay20-1.png`
// (compose_b.py 가 만든 승인 실물 — 화살표 기하를 그대로 이식).
// 그래서 앵커는 판별 union 이다: kind 'rotate'(종전 기계, 로직 무변경 보존) /
// kind 'baked'(화살표 앵커만). 한 에셋에 앵커는 한 벌만.
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

/** 잔상을 앱이 회전복사로 그리는 에셋용 (quick-260818-nnm 원형). */
export interface HowAnchorsRotate {
  readonly kind: 'rotate';
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
  /**
   * 회전각의 자로 쓸 record criterion (quick-260824-jw4). 회전은 "벌림/사이각"
   * 의미라 시트 대표 measure(예: 무릎 펴짐)와 단위가 달라질 수 있다 — 지정하면
   * 소비처가 그 criterion 의 record 측정으로 how 를 대체한다. 미지정 = 대표 measure.
   */
  readonly measureCriterion?: string;
}

/** 화살표 1개의 앵커 — 잔상이 그림에 구워진 에셋용 (belle 08-21). */
export interface HowArrowAnchor {
  /** 시작 = 그림에 구워진 잔상의 발 ("지금 내 자리"). */
  readonly from: Frac;
  /** 끝 = 같은 쪽 실선(정은지) 발. */
  readonly to: Frac;
  /** quadratic bezier 제어점 = from·to 중점 + 이 offset (compose_b.py 기하). */
  readonly ctrlOffset: Frac;
}

/**
 * 잔상이 그림에 구워진 에셋용 (belle 08-21, BELLE-0821-4). 회전복사 재료
 * (clip/pivot/inwardSign/shares/frontClip/nowLabelOffsetY)가 **없다** — 잔상이
 * 이미 그림 안에 있으므로 앱은 화살표·문장만 그린다.
 */
export interface HowAnchorsBaked {
  readonly kind: 'baked';
  readonly arrows: readonly HowArrowAnchor[];
  /** 방향 문장 틀 — rotate 와 같은 규약 ("좁다" 금지, BELLE-0821-3). */
  readonly directionSentence: string;
  /**
   * 발전 캡션 원문 (quick-260822-oe1, BELLE-0821-P2). 문구는 belle 08-22 갱신
   * 판정 "저번보다 나아졌어요 정도가 괜찮을 것 같은데"를 따른다 (08-21 초안
   * '더 벌어졌어요'는 split 전용이라 belle 이 일반형으로 교체). — 변형·수치
   * 삽입·악화 문구 발명 금지. optional 이라 없는 에셋은 자동 미대상 (데이터
   * opt-in, 코드 분기 0). 판정·소비는 progressCaption.buildProgressCaption 이 한다.
   */
  readonly progressSentence?: string;
}

export type HowAnchors = HowAnchorsRotate | HowAnchorsBaked;

/**
 * 에셋 키 → 앵커. 없는 에셋은 오버레이를 그리지 않는다(그림만 표시).
 *
 * ref-kip-up--leg (belle 08-21 승인 — exq stage20-1, 896x1200):
 *   발 좌표 = fe9 meta.json 절대픽셀의 0~1 환산 (PLAN 확정값, 재계산 금지):
 *     ghostL (213,1043) / solidL (110,1015) / ghostR (645,1035) / solidR (742,990)
 *   ctrl offset = 중점 + (좌 -8px, 우 +8px, 공통 +46px) 의 비율 환산.
 *   구 rotate 앵커(08-18 solid1 720x964 실측)는 새 그림에 무효라 폐기 —
 *   한 에셋에 앵커 두 벌 금지.
 */
export const HOW_ANCHORS: Readonly<Record<string, HowAnchors>> = {
  // quick-260824-jw4 (belle 08-24) — 파워스핀 다리: rotate 기계 재활성.
  // 잔상 = 그림 자신의 두 다리를 record 실측 부족각만큼 안쪽으로 돌린 것.
  // 원시 스켈레톤 잔상(전신 관절 투영)은 belle 기각("파워스핀에 저런 자세가
  // 있어?") — 몸통 정렬 회전이 실존하지 않는 방향을 만들고 저신뢰 관절이 빠져
  // 몸이 깨져 보였다. 베이스 그림도 belle 지시로 교체됨(구 도립본은 파워스핀에
  // 없는 자세) — 좌표 = 새 에셋 ref-power-spin--leg.jpg 896x1200 격자 실측.
  'ref-power-spin--leg': {
    kind: 'rotate',
    limbs: [
      // 윗다리 (폴 옆 위) — 부족하면 폴에서 떨어져 오른쪽으로 기운다 (시계 +1).
      {
        pivot: [530 / 896, 650 / 1200],
        tip: [582 / 896, 78 / 1200],
        clip: [
          [505 / 896, 660 / 1200], [530 / 896, 480 / 1200], [545 / 896, 330 / 1200],
          [555 / 896, 180 / 1200], [560 / 896, 70 / 1200], [612 / 896, 66 / 1200],
          [608 / 896, 180 / 1200], [600 / 896, 330 / 1200], [585 / 896, 480 / 1200],
          [565 / 896, 640 / 1200], [540 / 896, 682 / 1200],
        ],
        inwardSign: 1,
      },
      // 아랫다리 (아래앞) — 부족하면 수평 쪽으로 들린다 (반시계 -1).
      {
        pivot: [505 / 896, 705 / 1200],
        tip: [655 / 896, 1095 / 1200],
        clip: [
          [480 / 896, 690 / 1200], [540 / 896, 730 / 1200], [580 / 896, 800 / 1200],
          [620 / 896, 890 / 1200], [655 / 896, 990 / 1200], [675 / 896, 1080 / 1200],
          [668 / 896, 1112 / 1200], [630 / 896, 1110 / 1200], [600 / 896, 1010 / 1200],
          [560 / 896, 900 / 1200], [520 / 896, 800 / 1200], [470 / 896, 730 / 1200],
        ],
        inwardSign: -1,
      },
    ],
    shares: [0.5, 0.5],
    // 폴이 잔상 위로 다시 얹힌다 — 잔상이 폴을 가리면 이상하다.
    frontClip: [
      [488 / 896, 0], [532 / 896, 0], [536 / 896, 1], [492 / 896, 1],
    ],
    // 승인본(킵업 20-1) 문구 틀 그대로 — 단순 스타일 (belle 08-24 "오케이한
    // 거 그 단순한 스타일로").
    directionSentence: '{n}° 정도 더 벌리세요',
    nowLabelOffsetY: 0.03,
    // 회전각의 자 = 다리 사이각(split_angle) record. 시트 대표 measure 는 무릎
    // 펴짐(leg_extension)일 수 있는데 그 편차(예: 101°)로 다리를 돌리면 회전
    // 의미가 깨진다 — 시뮬 실측으로 확인된 결함.
    measureCriterion: 'split_angle',
  },
  'ref-kip-up--leg': {
    kind: 'baked',
    arrows: [
      { from: [0.2377, 0.8692], to: [0.1228, 0.8458], ctrlOffset: [-0.0089, 0.0383] },
      { from: [0.7199, 0.8625], to: [0.8281, 0.825], ctrlOffset: [0.0089, 0.0383] },
    ],
    directionSentence: '{n}° 정도 더 벌리세요',
    // belle 08-22 갱신 원문 그대로 (BELLE-0821-P2) — 단일 소스. 사본 금지.
    progressSentence: '저번보다 나아졌어요',
  },
};

/** rotate 오버레이 — 잔상 회전복사 + 직선 화살표 + "지금" (quick-260818-nnm 원형). */
export interface HowOverlayRotate {
  readonly kind: 'rotate';
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

/** baked 오버레이 — 곡선 화살표 + 문장만 (belle 08-21, 승인 실물 B-overlay20-1 겉모습). */
export interface HowOverlayBaked {
  readonly kind: 'baked';
  readonly deltaDeg: number;
  readonly directionText: string;
  /** quadratic bezier: M from Q ctrl to. ctrl 계산은 이 lib 이 소유한다. */
  readonly arrows: readonly { readonly from: Frac; readonly ctrl: Frac; readonly to: Frac }[];
}

/** 화면에 그릴 준비가 끝난 오버레이 1건. 좌표는 전부 비율(0~1) — 소비처가 픽셀로 곱한다. */
export type HowOverlay = HowOverlayRotate | HowOverlayBaked;

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
 * (fail-closed 게이트는 rotate/baked 두 kind 공통 — null 이어도 그림 자체는 표시된다.)
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
  const directionText = a.directionSentence.replace('{n}', String(n));

  if (a.kind === 'baked') {
    // 잔상은 그림에 구워져 있다 — 화살표 좌표만 계산 (ctrl = 중점 + offset).
    return {
      kind: 'baked',
      deltaDeg: n,
      directionText,
      arrows: a.arrows.map((ar) => ({
        from: ar.from,
        ctrl: [
          (ar.from[0] + ar.to[0]) / 2 + ar.ctrlOffset[0],
          (ar.from[1] + ar.to[1]) / 2 + ar.ctrlOffset[1],
        ] as const,
        to: ar.to,
      })),
    };
  }

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
    kind: 'rotate',
    deltaDeg: n,
    directionText,
    limbs,
    frontClip: a.frontClip,
    nowLabel: [gx, Math.min(0.96, gy + a.nowLabelOffsetY)],
  };
}

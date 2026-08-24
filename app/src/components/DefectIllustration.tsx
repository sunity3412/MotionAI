// 결함 일러스트 (A-7, 33-14 — D-15).
//
// 근거:
//  · D-15 — 일러스트는 검수 통과본만 배선한다. VERIFIED_ILLUSTRATIONS 에 없는
//    동작은 'hidden' = 아무것도 렌더하지 않는다 (Alert/Toast/에러 배너 0,
//    ReferenceCornerSection 표준의 조용한 폴백). 틀린 그림은 없는 것보다 나쁘다.
//  · D-18 — 등록본 = 33-14 검수 게이트 4종(익명·자세 충실·가이드 선·해부학)
//    육안 전수 통과본만. 미완 4동작(peter-pan, elbow-twist-sister, pdshape,
//    sideway-spin)은 의도된 부재 — 33-14-SUMMARY 검수 표가 기록 원본.
//  · D-05 — 일러스트는 말을 대체한다. 캡션/라벨 텍스트를 덧붙이지 않는다.
//  · 승인 불변식 ② (33-11, 장면-일러스트 일치 게이트) — 각 에셋의 입력은 해당
//    동작 기준 영상의 국면 완성 프레임 (33-A1 표 국면 데이터 키잉). 생성 경로 =
//    gemini-3-pro-image 이미지 투 이미지, 스타일 앵커 = 7R 후보 1 경로.
//  · 키 = reference 라이브러리 motionId (동작명 코드 분기 0 — 데이터 맵).
//    mode3/미등재 동작은 motionId 부재 → 자동 hidden (fail-closed).
//
// 33-G S13/S25 (quick-260731-2jt) — **장면일치 게이트 추가**. 종전에는 motionId
// 하나만 키로 써서 동작당 1장을 그 동작의 **모든 항목**에 공통 부착했다 → 어깨
// 항목 상세에 다리 일러스트 (belle 확인 ② #8·#9·#11 = 승인본 위반). 승인 목업의
// `DETAILS` 는 일러스트를 항목(부위)별 데이터로 두고(`:1047` `:1073` `:1081`),
// 불일치는 슬롯 DOM 자체를 만들지 않는다(`:1114`).
//  · P-2 — 부착 조건 = **항목 부위 토큰 ⊆ 에셋 장면 토큰**. 부분 겹침은 불일치.
//  · P-3 — 투영 공집합(criterion 단독 그룹)은 규칙 앞에서 즉시 미부착.
//  · D-43 — 적합한 에셋이 없으면 **아무것도 안 붙이는 것이 정답**이다. 이 변경으로
//    부착 건수가 주는 것은 결함이 아니라 목적이다.
// 판정 규칙 본체는 `lib/illustrationScene` 가 소유한다 (P-5 — require('*.jpg') 가
// 있는 이 파일은 node --test 로 실행할 수 없어 규칙을 떼어내야 검증 가능). 이
// 파일은 **에셋 맵만** 소유하고 판정을 소비한다. 두 표의 키 목록 일치 = grep 게이트.
//
// §C-4 3번 (quick-260731-plf) — **키가 motionId 에서 에셋 키로 바뀌었다.** 승인 목업의
// legs/shoulder/refonly 시트가 서로 다른 일러스트 값을 두므로 한 동작이 부위별로 여러
// 장을 갖는다. 종전 `Record<motionId, require>` 에는 그 자리가 없었다. 아래 맵의 키는
// 이제 `illustrationScene.ILLUSTRATION_SCENES[].asset` 이며, 33-14 통과 6장은 승인 자산
// 무접촉을 위해 `asset === motionId` 로 남아 파일 경로·바이트가 그대로다. 신규분만
// `{motionId}--{부위}` 형태를 쓴다.
//
// ScoreBreakdownSection 표준형: named export + inline prop 타입 + 헤더 주석 +
// StyleSheet 하단 + theme 토큰만. 하드코딩 색상/간격/반경 0. 이모지 0. 라이트 전용.

import { useState } from 'react';
import { Image, StyleSheet, Text, View } from 'react-native';
import Svg, {
  ClipPath,
  Defs,
  Image as SvgImage,
  Line,
  Path,
  Polygon,
  Circle,
  G,
} from 'react-native-svg';

import { illustrationAssetForPart } from '../lib/illustrationScene';
import {
  HOW_ANCHORS,
  buildHowOverlay,
  type HowOverlay,
  type HowOverlayBaked,
  type HowOverlayRotate,
} from '../lib/illustrationHow';
import { buildProgressCaption, type MeasureLike } from '../lib/progressCaption';
import {
  GHOST_ALIGN,
  GHOST_EDGES,
  buildGhostPoseForAsset,
  type GhostPose,
  type KeypointReportLike,
} from '../lib/ghostPose';
import { colors, radius, typography } from '../theme';

// 등재 에셋 원본 비율 (720x964 — 기본). 높이 = 실측 폭 × 이 값.
// 예외는 아래 override 맵 (quick-260821-gb7) — 비율이 다른 에셋이 하나라도 있으면
// 카드 기하(capW·h)와 buildHowOverlay 의 aspect 가 **같은 값**을 써야 한다.
const ASSET_H_OVER_W = 964 / 720;
// quick-260821-gb7 — belle 08-21 승인 잔상 에셋은 896x1200 (sips 실측). 720x964 전제의
// 예외를 데이터로 등재한다 (코드 분기 0).
const ASSET_H_OVER_W_OVERRIDES: Readonly<Record<string, number>> = {
  'ref-kip-up--leg': 1200 / 896,
  // quick-260824-jw4 — belle 실촬영 기반 재생성본 (gt1 r8 after-1, 896x1200).
  'ref-power-spin--leg': 1200 / 896,
};

// 검수 PASS 에셋 맵 — RN 정적 require (번들 포함). 키 = 장면 표의 `asset`.
// 항목 추가 = 33-14 게이트 재수행 후에만 (틀린 그림 유입 차단).
const VERIFIED_ILLUSTRATIONS: Record<string, number> = {
  'ref-power-spin': require('../../assets/illustrations/ref-power-spin.jpg'),
  // quick-260824-jw4 — belle 08-24: 구 다리 그림(도립)은 파워스핀에 없는 자세라
  // 기각, belle 실촬영 프레임 재현본으로 교체 (gt1 r8 after-1, 896x1200).
  'ref-power-spin--leg': require('../../assets/illustrations/ref-power-spin--leg.jpg'),
  'ref-kip-up': require('../../assets/illustrations/ref-kip-up.jpg'),
  // quick-260821-gb7 — belle 08-21 승인 (보드 실물 3회 확인): 잔상 포함 "어떻게" 그림
  // (exq stage20-1, 896x1200). 화살표·수치 문장은 앱이 그린다 — HOW_ANCHORS baked.
  'ref-kip-up--leg': require('../../assets/illustrations/ref-kip-up--leg.jpg'),
  'ref-climb': require('../../assets/illustrations/ref-climb.jpg'),
  'ref-invert': require('../../assets/illustrations/ref-invert.jpg'),
  'ref-foxtop': require('../../assets/illustrations/ref-foxtop.jpg'),
  'ref-foxtop-split': require('../../assets/illustrations/ref-foxtop-split.jpg'),
  // §C-4 3번 (quick-260731-plf) — 어깨·팔 부위별 신규분.
  'ref-power-spin--shoulder': require('../../assets/illustrations/ref-power-spin--shoulder.jpg'),
  'ref-kip-up--shoulder': require('../../assets/illustrations/ref-kip-up--shoulder.jpg'),
  'ref-elbow-twist-sister--arm': require('../../assets/illustrations/ref-elbow-twist-sister--arm.jpg'),
  // quick-260809-ill — 33-14 미완 3동작 (belle 08-09 "하나라도 불가능하면 기능 자체를
  // 못 넣어"). 33-14 가 8회 실패했던 것들로, 실패 주 원인은 **앵커 선택**이었다:
  // 방위만 맞춘 앵커가 자기 자세를 복제시켰다. 앵커를 "의도"로 고르자 통과 —
  // 자세 의도(신전+직선) = sideway/peter-pan, 구도 의도(부분 프레이밍) = pdshape.
  'ref-pdshape--leg': require('../../assets/illustrations/ref-pdshape--leg.jpg'),
  'ref-peter-pan--leg': require('../../assets/illustrations/ref-peter-pan--leg.jpg'),
  'ref-sideway-spin--leg': require('../../assets/illustrations/ref-sideway-spin--leg.jpg'),
  // belle 08-09 "콤보도 등재해서 A-1 채우자". 콤보는 33-A1 표에 없지만(미등재 동작)
  // 레퍼런스 doc 자체가 국면·부위·기대관절을 데이터로 들고 있어 그것에서 키잉했다 —
  // 지어낸 값 0. 상세 = illustrationScene provenance.
  'ref-combo--leg': require('../../assets/illustrations/ref-combo--leg.jpg'),
  // 2차 배치 — 실측으로 드러난 구멍을 메운다. "동작 11/11 보유"여도 표시 판정은
  // (동작, 부위) 짝이라, 전 doc 감점 149건 중 **65건(44%)이 짝 미커버로 그림 없이**
  // 나가고 있었다(belle 피터팬 = 어깨 감점인데 다리 그림만 있어 미표시).
  // 이 6장으로 실제 발생 짝 13개가 전부 커버된다.
  'ref-pdshape--shoulder': require('../../assets/illustrations/ref-pdshape--shoulder.jpg'),
  'ref-pdshape--arm': require('../../assets/illustrations/ref-pdshape--arm.jpg'),
  'ref-elbow-twist-sister--leg': require('../../assets/illustrations/ref-elbow-twist-sister--leg.jpg'),
  'ref-elbow-twist-sister--shoulder': require('../../assets/illustrations/ref-elbow-twist-sister--shoulder.jpg'),
  'ref-peter-pan--shoulder': require('../../assets/illustrations/ref-peter-pan--shoulder.jpg'),
  'ref-peter-pan--arm': require('../../assets/illustrations/ref-peter-pan--arm.jpg'),
};

export function DefectIllustration({
  motionId,
  partKey,
  maxHeight,
  how,
  prevHow,
  criterion,
  ghostSource,
}: {
  /** mode1 기준 모션 ID. null/미등록 = silent hidden (렌더 0). */
  motionId: string | null | undefined;
  /**
   * 이 항목의 부위 키 (`deductionSheet.regionPartKeyForRecord` — 마커 그룹·부위
   * 칩·부위 시트와 **같은 단위**). 그림 장면과 어긋나면 silent hidden (S13/S25).
   */
  partKey: string | null | undefined;
  /**
   * 이 슬롯이 쓸 수 있는 **최대 높이**(pt). 넘기면 비율을 유지한 채 폭을 줄여
   * 그 안에 맞춘다 (belle 2026-07-31 "전체가 안 들어오면 적응형으로"). 값의
   * 출처는 소비처가 **실측**해서 준다 — 이 컴포넌트가 시트 기하를 손계산하지
   * 않는다. 미지정이면 상한 없음(폭 우선) = 종전 거동.
   */
  maxHeight?: number;
  /**
   * quick-260818-nnm — "어떻게" 오버레이 재료. 학생 측정값·목표·단위. 앵커가 있는
   * 에셋에서만 잔상·화살표·표기가 그려지고, 값이 없거나 조건이 안 맞으면 그림만.
   */
  how?: { measured?: number | null; target?: number | null; unit?: string | null };
  /**
   * quick-260822-oe1 (belle 08-21 판정, 문구는 08-22 갱신) — 같은 동작 직전
   * 분석의 같은 criterion 측정 재료. 오버레이(수치 문장)가 그려질 때만
   * buildProgressCaption 으로 판정해 카드 아래에 "저번보다 나아졌어요" 캡션을
   * 붙인다. null/부재 = 캡션 없음
   * (직전 분석 없음 / mode3 — 기존 겉모습 그대로).
   */
  prevHow?: MeasureLike;
  /**
   * quick-260824-bxf — 이 항목의 감점 criterion (`sheetView.primaryCriterion`).
   * 캡션 노이즈 문턱을 criterion 으로 조회한다 (기본 12 + split_angle 21 —
   * progressCaption PROGRESS_NOISE_THRESHOLDS). **prevHow 를 만든 criterion 과
   * 같은 값이어야 문턱이 의미를 갖는다** — 직전/현재 측정과 문턱 조회가 다른
   * criterion 을 보면 비교 자체가 성립하지 않는다. null/부재 = 캡션 없음
   * (fail-closed — 배선 불일치를 기본 문턱으로 덮지 않는다).
   */
  criterion?: string | null;
  /**
   * quick-260824-jw4 (belle 08-24 "뭐가 됐든 기능 완료") — 잔상 데이터 렌더 재료.
   * 학생 keypointReport + 이 시트 부위의 감점 records. 판정·정규화·정렬은 전부
   * lib(buildGhostPoseForAsset — GHOST_ALIGN 메타 등재 에셋만). 어느 축이든
   * 실패 = 잔상 없이 그림만 (fail-closed — 기존 겉모습 회귀 0).
   */
  ghostSource?: {
    report: KeypointReportLike | null;
    records: ReadonlyArray<{
      atVideoSec?: number | null;
      criterion?: string;
      measuredValue?: number | null;
      baselineValue?: number | null;
      unit?: string | null;
    }>;
  } | null;
}) {
  // 장면일치 통과분만 조회 키가 된다 (P-2/P-3). 불일치·미등재·mode3 → null.
  const matched = illustrationAssetForPart(motionId, partKey);
  const source = matched ? VERIFIED_ILLUSTRATIONS[matched] : undefined;
  // 실측 폭 (quick-260731-plf V-3). Hook 은 early return 앞에 둔다
  // (조건부 Hook 금지 — matched 가 null 이어도 호출 순서가 같아야 한다).
  const [availW, setAvailW] = useState(0);
  if (source == null) return null; // 'hidden' — 미검증/불일치는 조용히 생략 (D-15/D-18/D-43)

  // 에셋별 비율 — override 맵에 있으면 그 값, 없으면 기본 720x964 (quick-260821-gb7).
  const hOverW = ASSET_H_OVER_W_OVERRIDES[matched ?? ''] ?? ASSET_H_OVER_W;
  // 폭 우선, 단 높이 상한을 넘으면 **상한에 맞춰 폭을 줄인다**. 비율이 그대로라
  // 잘림도 letterbox 도 없고, 그림이 작아질 뿐이다 — 일러스트는 전신 기하가 곧
  // 메시지이므로 "조금 작게 전부" 가 "크게 반쪽" 보다 낫다.
  const capW =
    typeof maxHeight === 'number' && maxHeight > 0
      ? maxHeight / hOverW
      : Number.POSITIVE_INFINITY;
  const w = Math.floor(Math.min(availW, capW));
  const h = Math.round(w * hOverW);
  // quick-260824-jw4 — rotate 앵커가 measureCriterion 을 지정하면 그 criterion 의
  // record 측정으로 how 를 대체한다 (회전각의 자 = 사이각. 시트 대표 measure 가
  // 무릎 펴짐이면 회전 의미가 깨지는 것을 시뮬 실측으로 확인). 해당 record 가
  // 없으면 오버레이를 그리지 않는다 (fail-closed — 다른 자로 돌리지 않는다).
  const anchor = matched ? HOW_ANCHORS[matched] : undefined;
  let effHow = how;
  if (anchor?.kind === 'rotate' && anchor.measureCriterion) {
    const rec = ghostSource?.records?.find(
      (r) => r?.criterion === anchor.measureCriterion,
    );
    effHow = rec
      ? {
          measured: typeof rec.measuredValue === 'number' ? rec.measuredValue : null,
          target: typeof rec.baselineValue === 'number' ? rec.baselineValue : null,
          unit: typeof rec.unit === 'string' ? rec.unit : null,
        }
      : undefined;
  }
  // quick-260818-nnm — 오버레이는 순수 계산(illustrationHow) 이 결정한다. null 이면 그림만.
  const overlay = effHow
    ? buildHowOverlay(matched, effHow.measured, effHow.target, effHow.unit, hOverW)
    : null;
  // quick-260822-oe1 (belle 08-21 판정) — 발전 캡션. **오버레이 게이트 뒤에서만**
  // 판정한다 (BELLE-0821-P4: 수치 문장이 있는 곳에만 캡션이 붙는다 — 오버레이
  // 게이트는 이 컴포넌트 소유, 캡션 게이트(문턱·unit·악화)는 lib 소유로 분리).
  // 카드 **아래** Text — 시트 카드가 작을 때 오버레이 pill 이 화살표를 가렸던
  // 전례(gb7 시뮬 실측)가 있어 오버레이 안에 두 번째 pill 을 넣지 않는다.
  const progressCaption =
    overlay != null && prevHow != null
      ? buildProgressCaption(matched, criterion, how, prevHow)
      : null;
  // quick-260824-jw4 — 잔상 데이터 렌더. GHOST_ALIGN 메타 등재 에셋 + 재료가
  // 있을 때만 (판정은 lib 순수 함수 — 이 컴포넌트는 픽셀 곱만).
  const ghostPose = ghostSource
    ? buildGhostPoseForAsset(matched, ghostSource.report, ghostSource.records)
    : null;
  const ghostMeta = matched ? GHOST_ALIGN[matched] : undefined;

  return (
    <View style={styles.wrap} onLayout={(e) => setAvailW(e.nativeEvent.layout.width)}>
      {w > 0 ? (
        // 높이를 **카드에도 직접** 준다. 자식(Image) 높이만 키우면 카드가 따라오지
        // 않는다 (RN 은 자식 높이를 부모로 밀어올리지 않는다). 두 박스를 같은 값으로
        // 확정해야 `overflow:hidden` 이 잘라낼 여지가 0 이 된다.
        <View style={[styles.card, { width: w, height: h }]}>
          <Image
            source={source}
            style={{ width: w, height: h }}
            resizeMode="cover"
            accessibilityLabel="목표 자세 일러스트"
          />
          {ghostPose && ghostMeta ? (
            <GhostPoseLayer pose={ghostPose} meta={ghostMeta} w={w} h={h} />
          ) : null}
          {overlay ? <HowOverlayLayer overlay={overlay} source={source} w={w} h={h} /> : null}
        </View>
      ) : null}
      {w > 0 && progressCaption ? (
        <Text style={styles.progressCaption}>{progressCaption}</Text>
      ) : null}
    </View>
  );
}

/**
 * 잔상 데이터 렌더 (quick-260824-jw4). 학생의 결함 순간 실측 자세를 스켈레톤으로
 * 그림 위에 얹는다 — 좌표는 lib 가 정규화·몸통 정렬까지 끝낸 값이라 여기서는
 * 에셋 메타(골반 위치·몸통 픽셀)로 픽셀 곱만 한다. 양 끝 관절이 다 있는 변만
 * 그린다. 색·굵기 = theme 토큰 파생 (하드코딩 0).
 */
function GhostPoseLayer({
  pose,
  meta,
  w,
  h,
}: {
  pose: GhostPose;
  meta: (typeof GHOST_ALIGN)[string];
  w: number;
  h: number;
}) {
  const scale = meta.torsoF * h;
  const cx = meta.pelvisFx * w;
  const cy = meta.pelvisFy * h;
  const byKey = new Map(pose.points.map((p) => [p.key, p]));
  const stroke = Math.max(2.5, w * 0.009);
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      <Svg width={w} height={h}>
        <G opacity={0.45}>
          {GHOST_EDGES.map(([a, b], i) => {
            const pa = byKey.get(a);
            const pb = byKey.get(b);
            if (!pa || !pb) return null;
            return (
              <Line
                key={`ge${i}`}
                x1={cx + pa.x * scale}
                y1={cy + pa.y * scale}
                x2={cx + pb.x * scale}
                y2={cy + pb.y * scale}
                stroke={colors.textMid}
                strokeWidth={stroke}
                strokeLinecap="round"
              />
            );
          })}
          {pose.points.map((p) => (
            <Circle
              key={`gp${p.key}`}
              cx={cx + p.x * scale}
              cy={cy + p.y * scale}
              r={stroke * 0.9}
              fill={colors.textMid}
            />
          ))}
        </G>
      </Svg>
    </View>
  );
}

/**
 * "어떻게" 오버레이 (quick-260818-nnm · quick-260821-gb7). 그림 위에 얹는 계층 —
 * 그림 파일은 손대지 않는다. 좌표는 전부 비율 → 여기서 픽셀로 곱한다.
 * kind 분기 (illustrationHow 판별 union):
 *   'rotate' → 잔상 회전복사 + frontClip + 직선 화살표 + "지금" pill (종전 그대로)
 *   'baked'  → 잔상이 그림에 구워져 있다 (belle 08-21 승인, BELLE-0821-4). 곡선 화살표
 *              2개 + 하단 중앙 수치 문장만 그린다 — 잔상 SvgImage·frontClip·"지금"
 *              pill·잔상 점은 생략.
 */
function HowOverlayLayer({
  overlay,
  source,
  w,
  h,
}: {
  overlay: HowOverlay;
  source: number;
  w: number;
  h: number;
}) {
  if (overlay.kind === 'baked') {
    return <BakedHowLayer overlay={overlay} w={w} h={h} />;
  }
  return <RotateHowLayer overlay={overlay} source={source} w={w} h={h} />;
}

/**
 * baked 렌더 (quick-260821-gb7, BELLE-0821-2/-3). 승인 실물과 같은 겉모습 —
 * `.planning/quick/260821-fe9-20-a-vs-b/out/ref-kip-up--leg__B-overlay20-1.png`
 * (compose_b.py 기하 이식): quadratic bezier 화살표(잔상 발 → 같은 쪽 실선 발,
 * 선 굵기 ≈ 폭 0.6%, 화살촉 ≈ 폭 2.5%, 촉 반각 0.45 rad, 촉 방향 = 제어점→끝점
 * 접선) + 수치 문장 하단 중앙 1곳.
 */
function BakedHowLayer({
  overlay,
  w,
  h,
}: {
  overlay: HowOverlayBaked;
  w: number;
  h: number;
}) {
  const px = (f: readonly [number, number]) => [f[0] * w, f[1] * h] as const;
  const stroke = Math.max(2, w * 0.006);
  const head = Math.max(8, w * 0.025);
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      <Svg width={w} height={h}>
        {overlay.arrows.map((a, i) => {
          const [x0, y0] = px(a.from);
          const [cx, cy] = px(a.ctrl);
          const [x1, y1] = px(a.to);
          // 촉이 앉는 만큼 몸통 끝을 살짝 줄인다 (compose_b `_arrow` 이식 — 둥근
          // 선끝이 촉 꼭짓점 밖으로 삐져나오지 않게). De Casteljau 좌분할: t 에서
          // 자른 앞쪽 곡선의 제어점 = P0, lerp(P0,P1,t), 곡선 위 점(t).
          const dist = Math.hypot(x1 - x0, y1 - y0);
          const t = 1 - Math.min(0.3, (head * 0.5) / Math.max(1, dist));
          const qx = x0 + (cx - x0) * t;
          const qy = y0 + (cy - y0) * t;
          const rx = cx + (x1 - cx) * t;
          const ry = cy + (y1 - cy) * t;
          const ex = qx + (rx - qx) * t;
          const ey = qy + (ry - qy) * t;
          // 화살촉 — 방향 = 제어점→끝점 접선, 반각 0.45 rad (compose_b 동일).
          const ang = Math.atan2(y1 - cy, x1 - cx);
          const p1 = [x1 - head * Math.cos(ang - 0.45), y1 - head * Math.sin(ang - 0.45)];
          const p2 = [x1 - head * Math.cos(ang + 0.45), y1 - head * Math.sin(ang + 0.45)];
          return (
            <G key={`b${i}`}>
              <Path
                d={`M ${x0} ${y0} Q ${qx} ${qy} ${ex} ${ey}`}
                stroke={colors.brand}
                strokeWidth={stroke}
                strokeLinecap="round"
                fill="none"
              />
              <Polygon
                points={`${x1},${y1} ${p1[0]},${p1[1]} ${p2[0]},${p2[1]}`}
                fill={colors.brand}
              />
            </G>
          );
        })}
      </Svg>
      {/* 수치 문장 — 하단 중앙 (승인 실물의 텍스트 상단 y≈0.948 과 등가, BELLE-0821-3).
          시뮬 실측(quick-260821-gb7): 시트 카드가 작아 dirPill 원형(padding 14/6,
          bottom 3.5%)이 화살표 몸통을 덮었다 — 승인 실물은 문장이 화살표 아래
          여백에 있다. padding 을 좁히고 바닥에 붙여 화살표가 보이게 한다. */}
      <View style={[styles.dirPill, styles.bakedDirPill, { bottom: h * 0.01 }]}>
        <Text style={styles.dirText}>{overlay.directionText}</Text>
      </View>
    </View>
  );
}

/**
 * rotate 렌더 (quick-260818-nnm 원형 — 로직 무변경).
 *   1) 잔상 = 같은 그림을 다리 영역으로 클립해 골반 기준으로 학생 각도만큼 돌린 것 (연하게)
 *   2) 폴 등 frontClip 영역을 다시 위에 (잔상이 폴을 가리지 않게)
 *   3) 화살표 = 잔상 말단 → 실선 말단 · 잔상 말단에 점 · "지금"
 *   4) 방향 문장 ("50° 정도 더 벌리세요") — 값이 있을 때만, 방향으로만
 */
function RotateHowLayer({
  overlay,
  source,
  w,
  h,
}: {
  overlay: HowOverlayRotate;
  source: number;
  w: number;
  h: number;
}) {
  const px = (f: readonly [number, number]) => [f[0] * w, f[1] * h] as const;
  const pts = (poly: readonly (readonly [number, number])[]) =>
    poly.map((f) => px(f).join(',')).join(' ');
  const arrowHead = (from: readonly [number, number], to: readonly [number, number]) => {
    const [ax, ay] = px(from);
    const [bx, by] = px(to);
    const ang = Math.atan2(by - ay, bx - ax);
    const head = Math.max(10, w * 0.03);
    const p1 = [bx - head * Math.cos(ang - 0.5), by - head * Math.sin(ang - 0.5)];
    const p2 = [bx - head * Math.cos(ang + 0.5), by - head * Math.sin(ang + 0.5)];
    return `${bx},${by} ${p1[0]},${p1[1]} ${p2[0]},${p2[1]}`;
  };
  const stroke = Math.max(3, w * 0.008);
  const dot = Math.max(5, w * 0.014);
  const [nx, ny] = px(overlay.nowLabel);
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      <Svg width={w} height={h}>
        <Defs>
          {overlay.limbs.map((l, i) => (
            <ClipPath id={`limb${i}`} key={`c${i}`}>
              <Polygon points={pts(l.clip)} />
            </ClipPath>
          ))}
          {overlay.frontClip ? (
            <ClipPath id="front">
              <Polygon points={pts(overlay.frontClip)} />
            </ClipPath>
          ) : null}
        </Defs>
        {/* 1) 잔상 — 같은 그림을 클립·회전·반투명 */}
        {overlay.limbs.map((l, i) => {
          const [cx, cy] = px(l.pivot);
          return (
            <G key={`g${i}`} clipPath={`url(#limb${i})`} opacity={0.42}>
              <SvgImage
                href={source}
                x={0}
                y={0}
                width={w}
                height={h}
                preserveAspectRatio="none"
                transform={`rotate(${l.rotateDeg} ${cx} ${cy})`}
              />
            </G>
          );
        })}
        {/* 2) 폴 등 앞에 있어야 할 것 */}
        {overlay.frontClip ? (
          <G clipPath="url(#front)">
            <SvgImage href={source} x={0} y={0} width={w} height={h} preserveAspectRatio="none" />
          </G>
        ) : null}
        {/* 3) 화살표 잔상 발 → 실선 발 — 승인본(킵업 20-1, gb7 B 방식)과 같은
            곡선 bezier + 접선 화살촉. belle 08-24 "오케이한 그 단순한 스타일" —
            "지금" pill·직선 화살표·잔상 점은 승인 전 옛 문법이라 제거. */}
        {overlay.limbs.map((l, i) => {
          const [x0, y0] = px(l.ghostTip);
          const [x1, y1] = px(l.tip);
          const head = Math.max(8, w * 0.025);
          const bstroke = Math.max(2, w * 0.006);
          const mx = (x0 + x1) / 2;
          const my = (y0 + y1) / 2 + h * 0.038;
          const dist = Math.hypot(x1 - x0, y1 - y0);
          const t = 1 - Math.min(0.3, (head * 0.5) / Math.max(1, dist));
          const qx = x0 + (mx - x0) * t;
          const qy = y0 + (my - y0) * t;
          const rx = mx + (x1 - mx) * t;
          const ry = my + (y1 - my) * t;
          const ex = qx + (rx - qx) * t;
          const ey = qy + (ry - qy) * t;
          const ang = Math.atan2(y1 - my, x1 - mx);
          const p1 = [x1 - head * Math.cos(ang - 0.45), y1 - head * Math.sin(ang - 0.45)];
          const p2 = [x1 - head * Math.cos(ang + 0.45), y1 - head * Math.sin(ang + 0.45)];
          return (
            <G key={`a${i}`}>
              <Path
                d={`M ${x0} ${y0} Q ${qx} ${qy} ${ex} ${ey}`}
                stroke={colors.brand}
                strokeWidth={bstroke}
                strokeLinecap="round"
                fill="none"
              />
              <Polygon points={`${x1},${y1} ${p1[0]},${p1[1]} ${p2[0]},${p2[1]}`} fill={colors.brand} />
            </G>
          );
        })}
      </Svg>
      {/* 방향 문장 — 승인본과 같은 하단 중앙 좁은 pill (bakedDirPill 상속). */}
      <View style={[styles.dirPill, styles.bakedDirPill, { bottom: h * 0.01 }]}>
        <Text style={styles.dirText}>{overlay.directionText}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  // quick-260818-nnm — 오버레이 표기. brand 채움 + cardBg 글자 (지금) / cardBg 채움 +
  // brand 테두리·글자 (방향 문장). 수치는 이 문장 1곳 (D-09 예외는 belle 08-18 결정).
  nowPill: {
    position: 'absolute',
    transform: [{ translateX: -26 }],
    backgroundColor: colors.brand,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 3,
  },
  nowText: { ...typography.caption, fontWeight: '700', color: colors.cardBg },
  dirPill: {
    position: 'absolute',
    alignSelf: 'center',
    backgroundColor: colors.cardBg,
    borderWidth: 1.5,
    borderColor: colors.brand,
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 6,
  },
  dirText: { ...typography.caption, fontWeight: '700', color: colors.brand },
  // baked 전용 (quick-260821-gb7) — 카드가 작을 때 화살표를 덮지 않도록 dirPill 보다
  // 좁은 padding. 색·타이포는 dirPill/dirText 그대로 상속.
  bakedDirPill: {
    paddingHorizontal: 10,
    paddingVertical: 3,
  },
  // 높이를 **실측 폭 × 비율**로 준다 (quick-260731-plf V-3). 종전에는 Image 가
  // `width:'100%' + aspectRatio` 를 들고 카드에는 높이 제약이 없었는데, 그 조합에서
  // Image 가 카드보다 크게 깔리고 카드의 overflow:hidden 이 잘라냈다. 그 결함은
  // 이 코드로 **해결됐다** — 아래 실측이 근거다.
  //
  // debug `illustration-slot-crop` (2026-07-31) 종결 — 종전 이 자리에 있던
  // "카드가 여전히 360x260 이라 54% 만 보인다"는 경고는 **오측이었다. 철회한다.**
  // 임시로 `accessible` + `accessibilityLabel`(onLayout 수치)을 달고 계기 2종으로 실측:
  //   · 네이티브 AXFrame  = {{20, …}, {362, 484.67}}   (idb ui describe-all)
  //   · RN onLayout       = card 362x485, image 362x485
  //   → 기대치(폭 362 → 362 × 964/720 = 484.67)와 **정확히 일치**. 잘림 0.
  // 260 의 정체 = **시트 ScrollView 뷰포트(화면 y 264..776 = 512pt)에 보이던 조각**.
  // 카드(485)가 뷰포트(512)보다 27pt 작을 뿐이라 최하단까지 스크롤하면 카드 위쪽이
  // 뷰포트 밖으로 밀려 아래쪽 262pt 만 남는다. 그 상태를 카드 높이로 오인한 것이다.
  // (자체 반증: 그때 보이던 것은 그림의 **아래쪽**(정강이·폴 받침)이었다. 카드가
  //  260 이고 위에서 잘린 것이라면 **위쪽**(골반·허벅지)이 보였어야 한다.)
  //
  // 곁가지로 확인된 것 — RN 0.81.5 + New Architecture 의 `aspectRatio` 는 **문서대로
  // width/height** 다. 카드에 `aspectRatio: 3/4` 를 주면 h = 362/0.75 = 482.67 이 나온다
  // (직접 실험). "축이 반대로 잡힌다"던 기록도 같은 오측이었다 — Fabric 특이동작 아님.
  //
  // 에셋 9/9 전부 720x964 (`sips` 전수 실측) 이라 `resizeMode="cover"` 가 잘라낼
  // 여백이 없다. 새 에셋을 넣을 때 비율이 다르면 이 전제가 깨진다 — 그때는
  // ASSET_H_OVER_W 와 cover 를 함께 다시 봐야 한다.
  //
  // **적응형 (belle 2026-07-31).** 폭 고정이면 작은 화면에서 카드가 시트 뷰포트를
  // 넘어 한 화면에 안 들어온다 (iPhone 16 Pro = 카드 485 vs 뷰포트 512 로 여유 27pt,
  // SE 급 = 뷰포트 약 350 < 448.5 로 불가). 이제 소비처가 준 `maxHeight` 안에
  // 맞추므로 기기 크기와 무관하게 전체가 보인다. wrap 이 폭을 실측하고, 줄어든
  // 카드는 가운데 정렬한다.
  wrap: {
    width: '100%',
    alignItems: 'center',
  },
  card: {
    borderRadius: radius.card,
    overflow: 'hidden',
  },
  // quick-260822-oe1 — 발전 캡션 (belle 08-21 원문). 카드 아래 보조 텍스트 —
  // theme 토큰만 (typography.caption + textMid), 신규 hex/수치 0.
  progressCaption: {
    ...typography.caption,
    color: colors.textMid,
    marginTop: 6,
    textAlign: 'center',
  },
});

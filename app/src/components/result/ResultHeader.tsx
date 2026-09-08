// 분석 결과 화면 상단 — 아래로 볼록한 빨강 헤더 + 타이틀 행 + 4탭 (belle 09-08).
//
// 피그마 `분석 디자인 업데이트` 섹션 시안. 이 섹션은 노드 706개가 전부 vector/group
// 이고 텍스트 레이어·컴포넌트·변수가 0개다(다른 도구에서 붙여넣은 벡터 아트워크).
// 그래서 치수는 두 계기로만 얻었다:
//   1) 벡터 노드의 바운딩 박스 (정확) — 위치·크기
//   2) 렌더 픽셀 샘플링 (정확) — 색
//
// ★ 헤더 곡선은 **눈대중으로 그리지 않았다.** 렌더 픽셀로는 "각진 배너"로 보였는데
// (겹쳐 놓인 카드가 가운데를 가려서), 실제 벡터 패스를 받아 보니 아래로 볼록한
// 베지어 2개였다. 아래 HEADER_PATH 는 피그마가 내보낸 패스 원문 그대로다.
//
// ★ 빨강은 시안의 #E94D37 이 아니라 브랜드 #FF4B33 이다 — belle 09-08 판정
// (colors.ts 의 result* 토큰 주석에 근거를 적어 두었다).
//
// ★ 왜 두 층으로 나뉘나: 시안에서 **카드가 곡선 위로 겹친다**(동작비교는 카드 윗변이
// 곡선 최심보다 한참 위에 있다). 그러려면 곡선은 스크롤 콘텐츠보다 **뒤**에, 타이틀·탭은
// **앞**에 있어야 한다. 한 컴포넌트로 얹으면 곡선이 카드를 덮거나(앞) 탭이 카드에
// 가려진다(뒤). 그래서 Backdrop / Bar 로 나눈다. 둘 다 화면에 고정이고, 탭 아래
// 영역(≈126pt)은 콘텐츠가 침범하지 않는다.
//
// 크기 규약: 시안 화면 폭 467.206px 를 390pt 로 본다(가장 흔한 iOS 시안 폭). 헤더는
// 그래픽 덩어리라 곡선·타이포·간격을 **한 덩어리로** 기기 폭에 비례 확대한다
// (s = width / 390). 390pt 기기에서는 시안과 1:1 이고, 더 넓은 기기에서도 곡선과
// 글자의 관계가 시안 그대로 유지된다. FULLSCREEN_TEXT_SCALE(VideoCompare) 선례.
import {
  Pressable,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Svg, { Path } from 'react-native-svg';
import { Ionicons } from '@expo/vector-icons';

import { colors, typography } from '../../theme';

/** 피그마 노드 254:681 이 내보낸 패스 원문 (viewBox 467.206 × 363.365). */
const HEADER_PATH =
  'M0 0V272.859C63.002 329.145 146.12 363.365 237.201 363.365C328.282 363.365 405.164 331.672 467.206 279.16V0H0Z';
const HEADER_VB_W = 467.206;
const HEADER_VB_H = 363.365;

/** 시안 화면 폭(px) → pt 환산 기준. */
export const RESULT_DESIGN_W = 390;

/**
 * 시안 실측 (화면 좌상단 기준 px → pt, k = 390 / 467.206 = 0.83474).
 *
 * 세로 좌표는 전부 **시안 화면 상단**(y=0) 기준이다. 실제 배치에서 곡선은 그 y=0 을
 * 기기 화면 상단에 그대로 두고, 글자·탭·콘텐츠만 useResultTopDelta 만큼 내린다.
 */
export const RESULT_HEADER = {
  /** 곡선 최심(중앙)까지의 깊이. 좌 227.8 / 우 233.0 은 패스가 갖고 있다. */
  curveDepth: HEADER_VB_H * (RESULT_DESIGN_W / HEADER_VB_W), // 303.3
  titleTop: 39.7,
  titleH: 22.2,
  sideInset: 50.3,
  backH: 13.0,
  shareH: 13.9,
  tabsTop: 89.8,
  tabsH: 15.3,
  tabsInset: 49.9,
  underlineTop: 124.2,
  underlineInset: 43.2,
  underlineH: 1.36,
  /** 탭 밑줄 아랫변 — 스크롤 콘텐츠가 이보다 위로 올라오면 안 된다. */
  barBottom: 124.2 + 1.36, // 125.6
  /** 타이틀이 상태바 밑에서 최소한 띄울 간격. */
  statusGap: 4,
} as const;

export interface ResultTab {
  key: string;
  label: string;
}

/** 화면 폭에서 확대 배율. 헤더·점수 원이 같은 배율을 공유해야 시안 비율이 유지된다. */
export function useResultScale(): number {
  const { width } = useWindowDimensions();
  return width / RESULT_DESIGN_W;
}

/**
 * 시안에는 **상태바가 그려져 있지 않다**. 그래서 y=0 을 무엇으로 읽느냐가 갈린다:
 *   (a) safe-area 상단 = 글자는 안전하지만 헤더가 상태바 높이만큼 통째로 길어져
 *       시안과 비율이 달라진다 (실측: 곡선 바닥이 시안 363px → 430px).
 *   (b) 화면 상단 = 비율은 시안과 같지만 타이틀이 상태바에 깔린다.
 * 그래서 **둘을 나눈다**: 곡선은 화면 상단에 고정해 시안 비율을 그대로 지키고
 * (곡선 깊이 / 화면 폭 = 0.7777 불변), 글자·탭·그 아래 콘텐츠만 상태바를 피할
 * 만큼 내린다. 이 delta 가 그 값이고, 상태바가 없는 기기에서는 0 이라 시안과 1:1 이다.
 */
export function useResultTopDelta(): number {
  const insets = useSafeAreaInsets();
  const s = useResultScale();
  return Math.max(0, insets.top + RESULT_HEADER.statusGap - RESULT_HEADER.titleTop * s);
}

/**
 * 뒤 층 — 상태바를 채우는 빨강 + 아래로 볼록한 곡선. 터치를 받지 않는다.
 * 스크롤 콘텐츠보다 **먼저** 렌더해서 카드가 곡선 위로 올라오게 한다.
 */
export function ResultHeaderBackdrop() {
  const { width } = useWindowDimensions();
  const s = useResultScale();
  const curveH = RESULT_HEADER.curveDepth * s;

  // 화면 상단(상태바 포함)에 고정 — useResultTopDelta 주석 참조. 곡선이 상태바 뒤를
  // 직접 채우므로 별도 사각형이 필요 없다.
  return (
    <View style={styles.backdrop} pointerEvents="none">
      <Svg
        width={width}
        height={curveH}
        viewBox={`0 0 ${HEADER_VB_W} ${HEADER_VB_H}`}
        style={styles.curve}
      >
        <Path d={HEADER_PATH} fill={colors.brand} />
      </Svg>
    </View>
  );
}

export interface ResultHeaderBarProps {
  title: string;
  tabs: readonly ResultTab[];
  activeKey: string;
  onTabPress: (key: string) => void;
  onBack?: () => void;
  /** 미전달 시 공유 아이콘을 그리지 않는다 (타이틀은 계속 가운데). */
  onShare?: () => void;
}

/**
 * 앞 층 — 타이틀 행 + 4탭 + 밑줄. 스크롤 콘텐츠보다 **나중에** 렌더한다.
 * box-none 이라 탭·버튼만 터치를 받고 나머지는 아래로 통과한다.
 */
export function ResultHeaderBar({
  title,
  tabs,
  activeKey,
  onTabPress,
  onBack,
  onShare,
}: ResultHeaderBarProps) {
  const s = useResultScale();
  const topDelta = useResultTopDelta();

  return (
    <View style={[styles.bar, { top: topDelta }]} pointerEvents="box-none">
      <View
        style={[
          styles.titleRow,
          { height: RESULT_HEADER.titleH * s, marginTop: RESULT_HEADER.titleTop * s },
        ]}
        pointerEvents="box-none"
      >
        {onBack ? (
          <Pressable
            onPress={onBack}
            accessibilityRole="button"
            accessibilityLabel="뒤로"
            hitSlop={16}
            style={[styles.sideBtn, { left: RESULT_HEADER.sideInset * s }]}
          >
            <Ionicons
              name="chevron-back"
              size={Math.round(RESULT_HEADER.backH * s)}
              color={colors.textWhite}
            />
          </Pressable>
        ) : null}
        <Text
          style={[styles.title, { fontSize: typography.resultTitle.fontSize * s }]}
          numberOfLines={1}
        >
          {title}
        </Text>
        {onShare ? (
          <Pressable
            onPress={onShare}
            accessibilityRole="button"
            accessibilityLabel="분석 결과 공유"
            hitSlop={16}
            style={[styles.sideBtn, { right: RESULT_HEADER.sideInset * s }]}
          >
            <Ionicons
              name="share-outline"
              size={Math.round(RESULT_HEADER.shareH * s)}
              color={colors.textWhite}
            />
          </Pressable>
        ) : null}
      </View>

      {/* 탭 — 시안은 space-between 이다(4개 폭 합 258.5px, 남는 88.7px 가 3등분
          29.6px 씩으로 관측된 것과 일치). 활성/비활성은 **둘 다 순백**이고 굵기만
          다르다: 같은 글자 '동작비교' 를 활성/비활성 화면에서 각각 재니 최대 α 는
          둘 다 1.000 인데 잉크 총량이 2.8배 차이였다(투명도가 아니라 weight). */}
      <View
        style={[
          styles.tabs,
          {
            marginTop:
              (RESULT_HEADER.tabsTop - RESULT_HEADER.titleTop - RESULT_HEADER.titleH) * s,
            height: RESULT_HEADER.tabsH * s,
            paddingHorizontal: RESULT_HEADER.tabsInset * s,
          },
        ]}
      >
        {tabs.map((t) => {
          const active = t.key === activeKey;
          return (
            <Pressable
              key={t.key}
              onPress={() => onTabPress(t.key)}
              accessibilityRole="tab"
              accessibilityLabel={t.label}
              accessibilityState={{ selected: active }}
              hitSlop={12}
            >
              <Text
                style={[
                  active ? styles.tabActive : styles.tabIdle,
                  {
                    fontSize:
                      (active
                        ? typography.resultTabActive.fontSize
                        : typography.resultTabIdle.fontSize) * s,
                  },
                ]}
              >
                {t.label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <View
        style={[
          styles.underline,
          {
            marginTop:
              (RESULT_HEADER.underlineTop - RESULT_HEADER.tabsTop - RESULT_HEADER.tabsH) * s,
            marginHorizontal: RESULT_HEADER.underlineInset * s,
            height: Math.max(StyleSheet.hairlineWidth, RESULT_HEADER.underlineH * s),
          },
        ]}
        pointerEvents="none"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
  },
  curve: {
    position: 'absolute',
    top: 0,
    left: 0,
  },
  bar: {
    position: 'absolute',
    left: 0,
    right: 0,
  },
  titleRow: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  sideBtn: {
    position: 'absolute',
    justifyContent: 'center',
    alignItems: 'center',
  },
  title: {
    ...typography.resultTitle,
    color: colors.textWhite,
    textAlign: 'center',
  },
  tabs: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  tabActive: {
    ...typography.resultTabActive,
    color: colors.textWhite,
  },
  tabIdle: {
    ...typography.resultTabIdle,
    color: colors.textWhite,
  },
  underline: {
    backgroundColor: colors.textWhite,
  },
});

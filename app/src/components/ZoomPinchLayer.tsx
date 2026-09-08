// 전체화면 영상 손가락 확대(핀치 줌) 제스처 호스트 — 색·문구 0 의 얇은 레이어.
//
// 왜 (belle 09-07): 자동 확대 카드가 엉뚱한 부위를 가리키는 문제를 "카드를 더 똑똑하게"
// 로 풀지 않기로 했다. 코칭이 결함을 짚는 순간 사용자가 직접 멈추고 손가락으로 확대해
// 보게 한다 — belle 원문 "손가락으로 영상을 멈추고 확대할 수 있게". 이 슬라이스는
// 멈춤 + 핀치 줌까지이고, 캡처/공유는 다음 슬라이스다(네이티브 빌드 필요).
//
// 신규 의존성 0 이 이 슬라이스의 전제다(OTA 로 전달되어야 한다). 제스처 라이브러리
// 대신 RN 코어 PanResponder 의 멀티터치를 쓴다 — gestureState.numberActiveTouches 와
// nativeEvent.touches 가 이미 노출되어 있다(PanResponder.js:176,338 / CoreEventTypes.d.ts:95).
// 배율·팬·초점 수학은 전부 순수 모듈 pinchZoom.ts 가 갖고, 여기는 손가락 → 그 함수
// 입력으로 옮기는 배선만 한다.
//
// 렌더 구조는 VideoCompare.tsx 의 fsVideoBox(:2905) / fsZoomBox(:2911) 2겹을 그대로
// 옮긴 것이다: 클리핑 래퍼(boxW×boxH, overflow hidden) + 내부 확대 박스(absolute,
// width/height/left/top 숫자 주입). transform: scale 이 아니라 **레이아웃 수치**인
// 이유는 expo-video 의 Android VideoView 가 SurfaceView 라 transform 이 영상 표면에
// 제대로 먹지 않기 때문이고(quick-260705-k8y 계승), 그 덕에 확대 박스 안의
// overlayContainer(absoluteFill)가 영상과 함께 확대·클리핑돼 키포인트 마커 정합이
// 공짜로 유지된다 — children 좌표를 여기서 다시 계산하지 않는다.
//
// 색·문구를 한 톨도 담지 않는 것은 의도다(테마 규칙 위반이 구조적으로 불가능해진다).
// 배경색은 호출측이 style 로 넣고(예: styles.fsVideoBox = colors.videoFullscreenBg),
// 접근성 라벨도 이 레이어가 무엇을 감쌌는지 아는 호출측이 붙인다.
import { useEffect, useMemo, useRef, type ReactNode } from 'react';
import {
  PanResponder,
  StyleSheet,
  View,
  type GestureResponderEvent,
  type NativeTouchEvent,
  type PanResponderGestureState,
  type StyleProp,
  type ViewStyle,
} from 'react-native';

import {
  applyPinch,
  clampZoom,
  pinchDistance,
  MIN_ZOOM,
  type TouchPoint,
  type ZoomState,
} from '../lib/pinchZoom';

// 탭(=멈춤/재생) 판정 — RenderedComparePlayer 가 걷어낸 Pressable 의 자리를 그대로
// 잇는다. 그래서 판정 기준도 **Pressable 과 같아야** 한다: 움직이지 않았으면 탭이고,
// 얼마나 오래 대고 있었는지는 묻지 않는다.
//
// belle 09-07 감사 수리 — 종전에는 여기에 250ms 상한이 있었다. Pressable 의 onPress
// 에는 시간 상한이 없어서(손가락을 1초 대고 떼도 발동) 실사용 탭 250~400ms 가 그대로
// 삼켜졌다 — "탭이 씹힌다". 상한을 없애도 팬·핀치와 섞이지 않는다: 팬은 이동량
// (TAP_MAX_MOVE_PX)으로, 핀치는 손가락 수(multiTouchSeen)로 이미 배제된다.
const TAP_MAX_MOVE_PX = 8;

// 팬 표본 폐기 임계 — 한 프레임에 박스 절반을 넘는 이동은 손가락이 아니라 좌표계가
// 바뀐 것(아래 '좌표계 주의' 참조)이므로 버린다.
const PAN_JUMP_REJECT_RATIO = 0.5;

export interface ZoomPinchLayerProps {
  /** 클리핑 박스 폭 (VideoCompare 의 fsBoxW). */
  boxW: number;
  /** 클리핑 박스 높이 (VideoCompare 의 fsBoxH). */
  boxH: number;
  /** 현재 확대 상태. 소유는 호출측(제어 컴포넌트). */
  state: ZoomState;
  /** 제스처 결과. 이미 clampZoom 을 통과한 값이라 그대로 state 로 되돌리면 된다. */
  onChange: (next: ZoomState) => void;
  /** 움직임 없는 짧은 탭 — 호출측이 재생/일시정지에 쓴다. */
  onTap?: () => void;
  /** 핀치 1회당 1번. 호출측이 안내 문구를 걷어내는 신호. */
  onPinchStart?: () => void;
  children: ReactNode;
  /** 클리핑 래퍼에 얹을 추가 스타일(배경색 등). overflow: 'hidden' 은 덮지 말 것. */
  style?: StyleProp<ViewStyle>;
  /**
   * 이 표면이 무엇인지 읽어 주는 라벨 (belle 09-07 회귀 수리).
   *
   * 이 레이어가 대체한 것은 `accessibilityRole="button"` +
   * `accessibilityLabel="재생 또는 일시정지"` 를 달고 있던 Pressable 이다. 탭 =
   * 재생/일시정지라는 사실은 그대로인데 라벨만 사라지면 스크린리더 사용자에게
   * 전체화면 영상이 조작 불가능한 면으로 보인다. 레이어는 자기가 무엇을 감쌌는지
   * 모르므로(파일 헤더 규칙 — 색·문구 0) 호출측이 붙인다.
   */
  accessibilityLabel?: string;
}

type TouchPair = readonly [NativeTouchEvent, NativeTouchEvent];
// RN 은 identifier 를 string 으로 선언한다(런타임 값은 숫자여도). 직접 적지 않고
// RN 선언에서 끌어와 타입이 갈라지지 않게 한다.
type TouchId = NativeTouchEvent['identifier'];

/**
 * 핀치에 쓸 두 손가락을 **identifier 로 고정해서** 고른다.
 *
 * belle 09-07 감사 수리 — 종전에는 매 프레임 touches[0]/[1] 을 그냥 읽었다. RN 의
 * nativeEvent.touches 는 손가락이 빠지면 배열이 재압축되므로, 세 손가락 중 하나를
 * 떼면 배열 위치 0/1 이 **다른 손가락 쌍**을 가리킨다. 그러면 시작 거리(|엄지−검지|)와
 * 현재 거리(|검지−중지|)를 비교하게 되어, 손을 전혀 움직이지 않았는데 배율이 즉시
 * 점프한다. ids 가 있는데 못 찾으면 null 을 돌려 호출측이 기준을 다시 잡게 한다.
 */
function pickPair(
  touches: readonly NativeTouchEvent[] | undefined,
  ids: readonly [TouchId, TouchId] | null,
): TouchPair | null {
  if (!Array.isArray(touches) || touches.length < 2) return null;
  if (ids) {
    const a = touches.find((t) => t.identifier === ids[0]);
    const b = touches.find((t) => t.identifier === ids[1]);
    return a && b ? [a, b] : null;
  }
  const a = touches[0];
  const b = touches[1];
  return a && b ? [a, b] : null;
}

function toTouchPoints(pair: TouchPair): TouchPoint[] {
  return [
    { pageX: pair[0].pageX, pageY: pair[0].pageY },
    { pageX: pair[1].pageX, pageY: pair[1].pageY },
  ];
}

/**
 * 두 손가락 중점을 클리핑 박스 좌상단 기준 좌표로 환산한다.
 *
 * 좌표계 주의: 전체화면은 90° 회전 컨테이너 안이라(t0v 패턴) page 좌표축과 박스의
 * 로컬 축이 다르다. 거리(핀치 배율)는 회전에 불변이라 pageX/pageY 로 재도 되지만,
 * **초점과 팬은 로컬 좌표라야** 한다 — 그래서 locationX/locationY 를 쓴다(RN 이
 * transform 을 반영해 매핑, VideoCompare.tsx:1492 선례).
 *
 * ★ locationX 는 **히트 타깃 뷰** 기준이다(iOS RCTSurfaceTouchHandler 의
 * locationInView:, Android JSTouchDispatcher 는 ACTION_MOVE 마다 재계산). 클리핑
 * 박스 안은 확대 박스가 100% 덮고 그 안 VideoView 가 다시 '100%' 라, 아무 조치 없이
 * 두면 타깃이 **움직이는 확대 박스**가 되어 locationX = clipX − zoomLeft 가 된다 —
 * applyPinch 가 요구하는 클리핑 박스 좌표계와 어긋난다(초점이 밀리고, 팬은
 * dx_n = 이동 − 직전 팬 으로 자기상쇄해 손가락 절반 속도로 덜컥거린다).
 * 그래서 클리핑 박스에 `pointerEvents="box-only"` 를 걸어 **타깃을 클리핑 박스로
 * 못박는다**(아래 렌더 참조). 이 레이어의 자식은 영상과 pointerEvents 없는
 * 오버레이뿐이라 잃는 조작이 없다.
 */
function localFocal(
  pair: TouchPair,
  boxW: number,
  boxH: number,
): { x: number; y: number } | null {
  const x = (pair[0].locationX + pair[1].locationX) / 2;
  const y = (pair[0].locationY + pair[1].locationY) / 2;
  if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
  return {
    x: Math.max(0, Math.min(boxW, x)),
    y: Math.max(0, Math.min(boxH, y)),
  };
}

interface GestureBook {
  movedPx: number;
  pinching: boolean;
  pinchNotified: boolean;
  /** 이 접촉에서 손가락이 2개 이상이었던 적이 있는가 — 탭 배제용. */
  multiTouchSeen: boolean;
  /** 지금 배율을 재고 있는 두 손가락의 identifier. 배열 위치가 아니다(pickPair 주석). */
  pinchIds: readonly [TouchId, TouchId] | null;
  pinchStartDist: number;
  pinchStartState: ZoomState;
  hasPanSample: boolean;
  lastLocalX: number;
  lastLocalY: number;
}

function freshBook(state: ZoomState): GestureBook {
  return {
    movedPx: 0,
    pinching: false,
    pinchNotified: false,
    multiTouchSeen: false,
    pinchIds: null,
    pinchStartDist: 0,
    pinchStartState: state,
    hasPanSample: false,
    lastLocalX: 0,
    lastLocalY: 0,
  };
}

export function ZoomPinchLayer({
  boxW,
  boxH,
  state,
  onChange,
  onTap,
  onPinchStart,
  children,
  style,
  accessibilityLabel,
}: ZoomPinchLayerProps) {
  // 스테일 클로저 방어 (이 컴포넌트에서 제일 틀리기 쉬운 곳).
  // PanResponder 는 mount 때 한 번만 만든다 — 제스처 중에 다시 만들면 내부
  // gestureState 가 grant 없이 초기화돼 dx/dy 누적이 깨진다. 그런데 팬 1프레임마다
  // onChange → 호출측 setState → 리렌더가 일어나므로, 핸들러가 붙잡고 있는 props 는
  // 곧바로 낡는다. 그래서 (1) 살아있는 값은 전부 ref 로 읽고, (2) 우리가 방금 내보낸
  // 값을 emit 안에서 liveRef 에 **즉시** 반영한다. props 왕복(커밋 → 이펙트)을
  // 기다리지 않으므로, 한 손가락 팬 도중 두 번째 손가락이 내려와 핀치 시작 상태를
  // 캡처하는 순간에도 한 프레임 낡은 값을 집을 수 없다 — "두 번째 제스처에서 줌이
  // 되돌아가는" 증상의 원인이 그 지점이다.
  const liveRef = useRef<ZoomState>(state);
  const boxRef = useRef({ w: boxW, h: boxH });
  const cbRef = useRef({ onChange, onTap, onPinchStart });
  const bookRef = useRef<GestureBook>(freshBook(state));

  useEffect(() => {
    liveRef.current = state;
  }, [state]);
  useEffect(() => {
    boxRef.current = { w: boxW, h: boxH };
  }, [boxW, boxH]);
  useEffect(() => {
    cbRef.current = { onChange, onTap, onPinchStart };
  });

  const panResponder = useMemo(() => {
    // 내보내기 전에 clampZoom 을 태운다 — 호출측 state 가 항상 화면에 그릴 수 있는
    // 값(정수 팬, 경계 안, 유한 배율)으로 유지되고, clampZoom 은 멱등이라 렌더에서
    // 한 번 더 통과시켜도 결과가 같다.
    const emit = (next: ZoomState) => {
      const { w, h } = boxRef.current;
      const g = clampZoom(next, w, h);
      const settled: ZoomState = { scale: g.scale, tx: g.tx, ty: g.ty };
      liveRef.current = settled;
      cbRef.current.onChange(settled);
    };

    return PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      // 제스처 도중 부모(모달·스크롤)에게 뺏기지 않는다 — 확대 중 손을 놓지도 않았는데
      // 그림이 멈추는 것을 막는다.
      onPanResponderTerminationRequest: () => false,

      onPanResponderGrant: (evt: GestureResponderEvent) => {
        const book = freshBook(liveRef.current);
        bookRef.current = book;
        // 두 손가락이 동시에 닿는 드문 경우까지 여기서 시작점을 잡아둔다.
        // (보통은 한 손가락 → 두 손가락 순이라 아래 move 에서 잡힌다.)
        const pair = pickPair(evt.nativeEvent.touches, null);
        if (!pair) return;
        book.multiTouchSeen = true;
        const dist = pinchDistance(toTouchPoints(pair));
        if (dist > 0) {
          book.pinching = true;
          book.pinchIds = [pair[0].identifier, pair[1].identifier];
          book.pinchStartDist = dist;
          book.pinchStartState = liveRef.current;
        }
      },

      onPanResponderMove: (evt: GestureResponderEvent, g: PanResponderGestureState) => {
        const book = bookRef.current;
        const { w, h } = boxRef.current;
        const touches = evt.nativeEvent.touches;
        // 탭 판정용 이동량 — page 좌표 거리라 회전 컨테이너에서도 그대로 유효하다.
        const moved = Math.hypot(g.dx, g.dy);
        if (Number.isFinite(moved) && moved > book.movedPx) book.movedPx = moved;

        const active = Math.max(
          g.numberActiveTouches,
          Array.isArray(touches) ? touches.length : 0,
        );

        if (active >= 2) {
          book.multiTouchSeen = true;
          // 잡고 있던 두 손가락을 identifier 로 다시 찾는다. 못 찾으면(3개 이상에서
          // 하나를 뗀 경우 — numberActiveTouches 는 여전히 2 이상이라 팬 분기로도
          // 안 빠진다) 남은 손가락으로 기준을 **다시 잡는다**.
          const held = pickPair(touches, book.pinchIds);
          const rebase = book.pinchIds !== null && held === null;
          const pair = held ?? pickPair(touches, null);
          if (!pair) return;
          const dist = pinchDistance(toTouchPoints(pair));
          if (dist <= 0) return;
          if (!book.pinching || rebase) {
            // 핀치 시작 프레임 — grant 가 아니라 **두 번째 손가락이 닿은 이 순간**의
            // 상태를 기준으로 잡아야 앞선 한 손가락 팬 결과가 유지된다. 손가락 쌍이
            // 바뀐 프레임(rebase)도 같은 처분 — 옛 시작거리를 새 쌍에 견주면 손을
            // 움직이지 않았는데 배율이 튄다.
            book.pinching = true;
            book.pinchIds = [pair[0].identifier, pair[1].identifier];
            book.pinchStartDist = dist;
            book.pinchStartState = liveRef.current;
            book.hasPanSample = false;
          }
          if (!book.pinchNotified) {
            book.pinchNotified = true;
            cbRef.current.onPinchStart?.();
          }
          const focal = localFocal(pair, w, h);
          emit(
            applyPinch({
              startState: book.pinchStartState,
              startDist: book.pinchStartDist,
              curDist: dist,
              // 초점을 못 읽으면 박스 중앙 — 확대 방향은 유지되고 그림이 튀지 않는다.
              focalX: focal ? focal.x : w / 2,
              focalY: focal ? focal.y : h / 2,
              boxW: w,
              boxH: h,
            }),
          );
          return;
        }

        // 손가락 하나 — 팬. 핀치에서 넘어온 첫 프레임은 기준 표본을 다시 잡는다.
        if (book.pinching) {
          book.pinching = false;
          book.pinchIds = null;
          book.hasPanSample = false;
        }
        const live = liveRef.current;
        // 최소 배율에서는 밀어낼 여백이 없다. 아무것도 하지 않아 주변 UI 와 다투지 않는다.
        if (!(live.scale > MIN_ZOOM)) return;

        const lx = evt.nativeEvent.locationX;
        const ly = evt.nativeEvent.locationY;
        if (!Number.isFinite(lx) || !Number.isFinite(ly)) return;
        if (!book.hasPanSample) {
          book.hasPanSample = true;
          book.lastLocalX = lx;
          book.lastLocalY = ly;
          return;
        }
        const dx = lx - book.lastLocalX;
        const dy = ly - book.lastLocalY;
        book.lastLocalX = lx;
        book.lastLocalY = ly;
        // 좌표계가 바뀐 표본(타깃 뷰 전환)은 손가락 이동으로 볼 수 없다 — 버린다.
        if (Math.abs(dx) > w * PAN_JUMP_REJECT_RATIO) return;
        if (Math.abs(dy) > h * PAN_JUMP_REJECT_RATIO) return;
        if (dx === 0 && dy === 0) return;
        emit({ scale: live.scale, tx: live.tx + dx, ty: live.ty + dy });
      },

      onPanResponderRelease: (_evt: GestureResponderEvent, g: PanResponderGestureState) => {
        const book = bookRef.current;
        const moved = Math.max(book.movedPx, Math.hypot(g.dx, g.dy));
        // 손가락이 둘 이상이었던 접촉은 탭이 아니다 — 핀치를 알리기 전(움직이지 않은
        // 두 손가락 터치)도 포함한다. 시간은 묻지 않는다(TAP_MAX_MOVE_PX 주석).
        const wasTap =
          !book.multiTouchSeen &&
          Number.isFinite(moved) &&
          moved < TAP_MAX_MOVE_PX;
        bookRef.current = freshBook(liveRef.current);
        if (wasTap) cbRef.current.onTap?.();
      },

      onPanResponderTerminate: () => {
        bookRef.current = freshBook(liveRef.current);
      },
    });
    // 의존성 없음이 의도다 — 위 스테일 클로저 주석 참조(제스처 중 재생성 금지).
  }, []);

  const geom = clampZoom(state, boxW, boxH);

  return (
    <View
      style={[styles.clipBox, { width: boxW, height: boxH }, style]}
      // 탭 핸들러가 있을 때만 버튼으로 읽힌다 — 확대만 되는 표면을 누를 수 있는 것처럼
      // 알리지 않는다. 라벨은 호출측 소유(위 prop 주석).
      accessibilityRole={onTap ? 'button' : undefined}
      accessibilityLabel={accessibilityLabel}
      // ★ 초점·팬 좌표계의 전제 (localFocal 주석). box-only = "이 뷰는 터치 타깃이
      // 되지만 자식은 되지 않는다" — locationX/Y 가 **클리핑 박스** 기준으로 오게
      // 못박는다. 자식은 영상과 pointerEvents 없는 오버레이뿐이라 잃는 조작 0
      // (전체화면 KeypointOverlay 는 onMarkerPress 미전달 → pointerEvents 'none',
      // result.tsx:3006).
      pointerEvents="box-only"
      {...panResponder.panHandlers}
    >
      <View
        style={[
          styles.zoomBox,
          { width: geom.zoomW, height: geom.zoomH, left: geom.zoomLeft, top: geom.zoomTop },
        ]}
      >
        {children}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  // VideoCompare.tsx:2905 fsVideoBox 계승 — overflow hidden 이 확대 박스의 튀어나온
  // 부분을 잘라낸다. 배경색은 호출측 style 이 넣는다(이 파일에 색 0).
  clipBox: {
    overflow: 'hidden',
  },
  // VideoCompare.tsx:2911 fsZoomBox 계승 — 좌표 정합의 기준 박스.
  zoomBox: {
    position: 'absolute',
  },
});

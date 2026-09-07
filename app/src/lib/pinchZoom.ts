// 전체화면 영상 손가락 확대(핀치 줌) 순수 기하 — react/react-native/expo 의존 0.
//
// 왜 이 모듈이 존재하나 (belle 09-07): 자동 생성 확대 카드가 엉뚱한 부위를 가리키는
// 문제를 "카드를 더 똑똑하게" 로 풀지 않기로 했다. 코칭이 결함을 짚는 순간 사용자가
// 직접 멈추고 손가락으로 확대해 보게 한다 — belle 원문 "손가락으로 영상을 멈추고
// 확대할 수 있게". 이 슬라이스는 멈춤 + 핀치 줌까지이고, 캡처/공유는 다음 슬라이스다
// (네이티브 빌드 필요 — 여기서는 신규 의존성 0 이어야 OTA 로 전달된다).
//
// 왜 제스처 라이브러리를 안 쓰나: RN 코어 PanResponder 가 이미 멀티터치를 노출한다
// (gestureState.numberActiveTouches, nativeEvent.touches). 핀치 거리 계산과 초점
// 보존은 아래 순수 함수로 충분하다 — 신규 npm 의존성 0.
//
// 왜 transform: scale 이 아니라 레이아웃 수치인가 (VideoCompare.tsx:1941-1944 계승):
// expo-video 의 Android VideoView 는 SurfaceView 라 transform 이 영상 표면에 제대로
// 먹지 않는다. 오늘 코드가 확대 박스의 width/height/left/top 숫자를 직접 주입하는
// 이유이고, overlayContainer 가 그 박스의 absoluteFill 이라 키포인트 오버레이가
// 영상과 함께 확대·클리핑되며 정합이 공짜로 유지된다. 이 모듈도 같은 레이아웃 수치
// (zoomW/zoomH/zoomLeft/zoomTop)만 산출한다 — 마커 좌표를 다시 계산하지 않는다.

/** 확대 상태. tx/ty 는 중앙 정렬 기준에서 밀어낸 팬 오프셋(px). */
export interface ZoomState {
  scale: number;
  tx: number;
  ty: number;
}

/**
 * 기본 배율 = 1.35.
 *
 * 이 값은 새로 고른 숫자가 아니라 **오늘 화면에 이미 적용된 프레이밍** 이다
 * (VideoCompare.tsx:404 FULLSCREEN_ZOOM, quick-260705-k8y, belle 실기기 3차
 * 2026-07-05 승인 — 세로영상 위아래 여백을 잘라내고 인물을 키운다). 핀치 줌은 이
 * 승인된 프레이밍에서 출발하고, 손을 떼고 초기화하면 정확히 여기로 되돌아온다.
 * 픽셀 한 톨도 달라지면 belle 이 승인한 화면이 바뀌는 것이므로 clampZoom 은 이
 * 배율에서 오늘의 인라인 수식을 그대로 재현한다(pinchZoom.test.ts 회귀 잠금).
 */
export const DEFAULT_ZOOM = 1.35;

/** 최소 배율 = 1.0. 이보다 작으면 확대 박스가 클리핑 박스보다 작아져 가장자리가 드러난다. */
export const MIN_ZOOM = 1.0;

/** 최대 배율 = 4.0. 그 이상은 영상 원본 해상도가 뭉개져 "직접 보게 한다" 는 목적을 잃는다. */
export const MAX_ZOOM = 4.0;

/** 핀치 거리 계산에 쓰는 터치 좌표 (RN NativeTouchEvent 의 부분집합). */
export interface TouchPoint {
  pageX: number;
  pageY: number;
}

function clampNumber(v: number, lo: number, hi: number): number {
  if (v < lo) return lo;
  if (v > hi) return hi;
  return v;
}

/**
 * 두 손가락 사이 거리(px). 손가락이 2개 미만이면 0.
 *
 * 0 은 "핀치 아님" 신호로 쓴다 — 호출측은 0 을 받으면 배율을 건드리지 않는다
 * (한 손가락 드래그가 배율을 흔드는 것을 막는다).
 */
export function pinchDistance(touches: TouchPoint[]): number {
  if (!Array.isArray(touches) || touches.length < 2) return 0;
  const a = touches[0];
  const b = touches[1];
  if (!a || !b) return 0;
  const dx = b.pageX - a.pageX;
  const dy = b.pageY - a.pageY;
  if (!Number.isFinite(dx) || !Number.isFinite(dy)) return 0;
  return Math.hypot(dx, dy);
}

export interface ApplyPinchArgs {
  /** 핀치 시작 시점(두 번째 손가락이 닿은 순간)의 확대 상태. */
  startState: ZoomState;
  /** 핀치 시작 시점의 두 손가락 거리. 0 이하이면 배율 변화 없음. */
  startDist: number;
  /** 현재 두 손가락 거리. */
  curDist: number;
  /** 두 손가락 중점의 X — 클리핑 박스 좌상단 기준(px). */
  focalX: number;
  /** 두 손가락 중점의 Y — 클리핑 박스 좌상단 기준(px). */
  focalY: number;
  /** 클리핑 박스 폭(fsBoxW). */
  boxW: number;
  /** 클리핑 박스 높이(fsBoxH). */
  boxH: number;
}

/**
 * 핀치 배율비를 초점(두 손가락 중점) 기준으로 적용한다 — 손가락 아래 픽셀이 그 자리에
 * 머문다.
 *
 * 좌표 모델(clampZoom 과 공유, 반올림 전 연속값):
 *   left(s, tx) = boxW * (1 - s) / 2 + tx      // 중앙 정렬 + 팬
 *   화면 X = left + u * boxW * s               // u = 확대 박스 내 정규화 위치 [0,1]
 * 초점 아래의 u0 를 배율 전후로 고정하면 새 left 가 결정되고, 거기서 tx 를 되돌린다.
 *
 * 배율은 여기서 [MIN_ZOOM, MAX_ZOOM] 으로 먼저 잘라낸 뒤 **실제 적용된 비율**로 초점을
 * 계산한다 — 상한에 붙은 뒤에도 그림이 계속 밀려나는 것을 막는다.
 * 팬 경계 클램프는 하지 않는다(clampZoom 담당). 여기 결과는 아직 float 이다.
 */
export function applyPinch(args: ApplyPinchArgs): ZoomState {
  const { startState, startDist, curDist, focalX, focalY, boxW, boxH } = args;
  const s0 = Number.isFinite(startState?.scale) ? startState.scale : DEFAULT_ZOOM;
  const tx0 = Number.isFinite(startState?.tx) ? startState.tx : 0;
  const ty0 = Number.isFinite(startState?.ty) ? startState.ty : 0;
  const base: ZoomState = { scale: clampNumber(s0, MIN_ZOOM, MAX_ZOOM), tx: tx0, ty: ty0 };

  // 핀치 성립 조건이 아니면 배율·팬 모두 그대로 (0 나눗셈·NaN 유입 차단).
  if (
    !Number.isFinite(startDist) ||
    !Number.isFinite(curDist) ||
    startDist <= 0 ||
    curDist <= 0 ||
    !Number.isFinite(boxW) ||
    !Number.isFinite(boxH) ||
    boxW <= 0 ||
    boxH <= 0 ||
    !Number.isFinite(focalX) ||
    !Number.isFinite(focalY)
  ) {
    return base;
  }

  const s1 = clampNumber(base.scale * (curDist / startDist), MIN_ZOOM, MAX_ZOOM);

  const left0 = (boxW * (1 - base.scale)) / 2 + base.tx;
  const top0 = (boxH * (1 - base.scale)) / 2 + base.ty;
  // 초점 아래 정규화 위치 (배율 전후 불변량).
  const u0 = (focalX - left0) / (boxW * base.scale);
  const v0 = (focalY - top0) / (boxH * base.scale);
  const left1 = focalX - u0 * boxW * s1;
  const top1 = focalY - v0 * boxH * s1;

  return {
    scale: s1,
    tx: left1 - (boxW * (1 - s1)) / 2,
    ty: top1 - (boxH * (1 - s1)) / 2,
  };
}

/** renderFullscreenSlot 이 확대 박스에 그대로 주입하는 레이아웃 수치. */
export interface ZoomGeometry {
  zoomW: number;
  zoomH: number;
  zoomLeft: number;
  zoomTop: number;
  /** 클램프가 끝난 배율 — 다음 프레임의 startState 로 되먹인다. */
  scale: number;
  /** 클램프·반올림이 끝난 팬 오프셋(px). zoomLeft = 중앙정렬left + tx. */
  tx: number;
  ty: number;
}

/**
 * 확대 상태를 확대 박스 레이아웃 수치로 환산한다 (배율·팬 경계 클램프 포함).
 *
 * 반올림은 오늘 VideoCompare.tsx:1941-1944 인라인 수식을 **글자 그대로** 따른다:
 *   zoomW    = Math.round(boxW * scale)
 *   zoomLeft = -Math.round((zoomW - boxW) / 2)        // 폭을 먼저 반올림하고, 그 차의 절반을 다시 반올림
 * 순서를 바꾸거나 한쪽만 반올림하면 belle 이 실기기에서 승인한 프레이밍이 픽셀 단위로
 * 어긋난다. scale = DEFAULT_ZOOM · tx/ty = 0 이면 여기 결과가 오늘 화면과 완전히 같다.
 *
 * 팬 경계: 확대 박스는 항상 클리핑 박스를 덮어야 한다(가장자리 노출 금지).
 *   zoomLeft <= 0  그리고  zoomLeft + zoomW >= boxW
 * 배율 1.0 에서는 두 경계가 만나 팬이 0 으로 강제된다 — 밀어낼 여백이 없다.
 */
export function clampZoom(state: ZoomState, boxW: number, boxH: number): ZoomGeometry {
  const rawScale = Number.isFinite(state?.scale) ? state.scale : DEFAULT_ZOOM;
  const scale = clampNumber(rawScale, MIN_ZOOM, MAX_ZOOM);

  if (!Number.isFinite(boxW) || !Number.isFinite(boxH) || boxW <= 0 || boxH <= 0) {
    return { zoomW: 0, zoomH: 0, zoomLeft: 0, zoomTop: 0, scale, tx: 0, ty: 0 };
  }

  const zoomW = Math.round(boxW * scale);
  const zoomH = Math.round(boxH * scale);
  // 오늘의 중앙 정렬 오프셋 (팬 0 일 때의 left/top).
  const centeredLeft = -Math.round((zoomW - boxW) / 2);
  const centeredTop = -Math.round((zoomH - boxH) / 2);

  // 팬 허용 범위 = 중앙 정렬 기준의 좌우/상하 여유. 확대 박스가 클리핑 박스를 덮는
  // 조건을 tx 로 옮긴 것 (배율 1.0 이면 상·하한이 0 으로 만난다).
  const txMax = -centeredLeft;
  const txMin = boxW - zoomW - centeredLeft;
  const tyMax = -centeredTop;
  const tyMin = boxH - zoomH - centeredTop;

  const rawTx = Number.isFinite(state?.tx) ? Math.round(state.tx) : 0;
  const rawTy = Number.isFinite(state?.ty) ? Math.round(state.ty) : 0;
  const tx = clampNumber(rawTx, txMin, txMax);
  const ty = clampNumber(rawTy, tyMin, tyMax);

  return {
    zoomW,
    zoomH,
    zoomLeft: centeredLeft + tx,
    zoomTop: centeredTop + ty,
    scale,
    tx,
    ty,
  };
}

// 분석 결과 동작 비교 — 좌(내 영상) / 우(기준) 나란히 + 동기 재생.
//
// 영상 URL 이 비어 있을 때도 같은 레이아웃의 자리표시를 보여줘서, #7-follow 에서
// 실 영상이 들어오면 그대로 슬롯에 들어간다 ([[sim-scaffold-not-decorate]]).
//
// 동기 재생: 단일 Play/Pause 가 양 플레이어를 동시에 제어. 타임라인은 좌측을
// 기준으로 표시하되 seek 는 양쪽 동일 시각으로 보낸다. 영상 길이가 서로 달라도
// 짧은 쪽이 끝나면 일시정지(루프 X) — 비교 시 동기 어긋남 방지.

import { Ionicons } from '@expo/vector-icons';
import { requireOptionalNativeModule } from 'expo-modules-core';
import { StatusBar } from 'expo-status-bar';
import { useVideoPlayer, VideoView, type VideoPlayer } from 'expo-video';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  type LayoutChangeEvent,
  Modal,
  PanResponder,
  Pressable,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';
import {
  normalizeMotionAlignment,
  segmentRate,
  warpTime,
} from '../lib/alignmentWarp';
import { circledNumberKo } from '../lib/deductionLabels';
import { colors, layout, radius, spacing, typography } from '../theme';
import type { MotionAlignment } from '../types/analysis';

type SlotProps = {
  label: string;
  url?: string;
  player: VideoPlayer | null;
  /**
   * Phase 12 신설 (Plan 12-02 T4 / R7 render prop).
   * 영상 위 absolute overlay layer (KeypointOverlay 등). pointerEvents 'none'.
   * VideoCompare 가 player lifecycle 안에서 callback 호출 — caller (result.tsx)
   * 가 player state 별도 관리 X (R7 dual-state pattern 차단).
   * Wave 2 가 KeypointOverlay 내부 useEvent(player, 'timeUpdate') 박제 site.
   *
   * quick-260702-t0v — 2번째 인자 opts.sizeScale 확장. 세로 카드는 opts 생략
   * (기존 렌더 무회귀), 가로 전체화면 뷰어가 { sizeScale: 2.0 } 전달.
   */
  overlay?: OverlayRenderProp;
};

// quick-260702-t0v — overlay render prop 단일 타입 (VideoCompareProps + SlotProps 공유).
type OverlayRenderProp = (
  player: VideoPlayer | null,
  opts?: { sizeScale?: number },
) => React.ReactNode;

function fmtTime(s: number): string {
  if (!isFinite(s) || s < 0) return '0:00';
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, '0')}`;
}

// Phase 12 후속 B — currentTime 은 0.1s 정밀 표시. belle 요구: "0.0초 단위".
function fmtTimeDecimal(s: number): string {
  if (!isFinite(s) || s < 0) return '0:00.0';
  const m = Math.floor(s / 60);
  const sec = s - m * 60;
  return `${m}:${sec.toFixed(1).padStart(4, '0')}`;
}

function VideoSlot({ label, url, player, overlay }: SlotProps) {
  return (
    <View style={styles.slot}>
      <View style={styles.slotFrame}>
        {url && player ? (
          <>
            <VideoView
              player={player}
              style={styles.video}
              contentFit="contain"
              nativeControls={false}
              allowsFullscreen={false}
              allowsPictureInPicture={false}
            />
            {overlay && (
              <View style={styles.overlayContainer} pointerEvents="box-none">
                {overlay(player)}
              </View>
            )}
          </>
        ) : (
          <View style={styles.slotEmpty}>
            <Ionicons
              name="videocam-outline"
              size={22}
              color={colors.textDisabled}
            />
            <Text style={styles.slotEmptyText}>준비 중</Text>
          </View>
        )}
      </View>
      <Text style={styles.slotLabel}>{label}</Text>
    </View>
  );
}

export type VideoCompareProps = {
  leftLabel: string;
  rightLabel: string;
  leftUrl?: string;
  rightUrl?: string;
  /**
   * Phase 12 신설 (Plan 12-02 T4) — 영상 위 absolute layer (KeypointOverlay 등).
   * pointerEvents 'none'. R7 render prop — result.tsx 가 player state 들지 않고
   * VideoCompare 가 자기 player lifecycle 안에서 callback 호출. Wave 2 가
   * KeypointOverlay 내부 useEvent(player, 'timeUpdate') 박제 site (B3 iter-4 정합).
   *
   * quick-260702-t0v — 2번째 인자 opts.sizeScale 확장 (전체화면 뷰어가 2.0 전달).
   */
  leftOverlay?: OverlayRenderProp;
  rightOverlay?: OverlayRenderProp;
  /**
   * quick-260702-t0v — 가로 전체화면 뷰어 상단 bar 우측 슬롯 (닫기 버튼 왼쪽).
   * result.tsx 가 KeypointOverlayToggle 을 전달 → 전체화면에서도 오버레이 토글
   * 유지 (state 단일 출처 = caller, 토글 시 render prop 재실행으로 즉시 반영).
   */
  fullscreenHeaderExtra?: React.ReactNode;
  /**
   * quick-260705-r6v — 가로 전체화면 위쪽 검은 여백(fsTopBar 좌측)에 고정 범례.
   * 재생 중 영상 위 텍스트 pill 을 없앤 대신, "① 행동구 −감점" 을 여백에 나열한다
   * (Tempo "폼 피드백 상시 노출 demoralizing" 계열 — 설명은 여백으로). 각 entry =
   * brand 원문자 번호 + 흰 텍스트. 미전달/빈 배열이면 미렌더.
   */
  fullscreenLegend?: { number: number; text: string }[];
  /**
   * quick-260705-r6v — 범례 entry 탭 콜백. iOS 중첩 Modal 함정 회피를 위해
   * closeFullscreen() 을 먼저 실행한 뒤 콜백을 호출한다 (전체화면 Modal 위에
   * sibling 시트를 띄우면 iOS 에서 표시 실패 — planner_findings 3).
   */
  onLegendPress?: (markerNumber: number) => void;
  /**
   * quick-260705-r6v — 재생바 결함 측정 시점 틱 (buildDeductionTicks, frame 도메인).
   * 탭 시 양쪽 영상을 그 시점으로 동기 seek. 29 리뷰 WR-01 — tickFrameCount =
   * doc top-level anglesFrames (9fps angles 공간 T). frameIndex 가 9fps 인덱스
   * 이므로 keypointReport.frames(18fps 업샘플) 배선 금지 — 절반 시각으로 어긋남.
   * 초 환산 기준 duration 은 leftDuration(사용자=master 도메인). 세로 카드/
   * 전체화면 공용 (renderControls 공유). 데이터 없으면 틱 생략.
   */
  timelineTicks?: { numbers: number[]; frameIndex: number }[];
  tickFrameCount?: number;
  /**
   * 28-06 (D-01/D-02) — 동작 기준 정렬 맵. 부재/null = 현행 절대시계 100% 보존
   * (faultZoomStatus/tier legacy 폴백 선례 — no migration). 학생(left)=master 로
   * 시계 불변, 정은지(right)만 warp(tStudent)→tRef 로 따라간다. malformed 는
   * normalizeMotionAlignment 로 소비측에서 재검증(T-28-02) — 통과분만 재생 제어.
   */
  alignment?: MotionAlignment | null;
};

// UAT 4차 (Build 14) finding 1+2 drift/replay 보정 상수 — Build 16 (iter-2).
//
// Build 15 → Build 16 변경 (UAT 5차에서 drift 1-2s 잔존 + 반복 재생 멈춤 + 랜덤 버벅):
//   - tick interval 250ms → 100ms — drift 누적 전 빨리 잡음
//   - DRIFT_CORRECT_THRESHOLD_S 0.3 → 0.2 — 더 일찍 보정 진입
//   - hysteresis (DRIFT_RESET_THRESHOLD_S + correctingDriftRef) 제거 —
//     매 tick drift > 0.2 면 즉시 보정 (stutter 위험 < 동기화 우선)
//   - REPLAY_SEEK_DELAY_MS 60 → 200 — 정은지 영상 S3 buffer reset 충분 시간
//   - togglePlay 시작 시 강제 sync — play() 전 둘이 currentTime 다르면 작은 값
//     으로 맞춤. 초기 drift 0 보장.
const TICK_INTERVAL_MS = 100;
const DRIFT_CORRECT_THRESHOLD_S = 0.2;
const REPLAY_SEEK_DELAY_MS = 200;
const START_SYNC_THRESHOLD_S = 0.05;

// Phase 12 후속 B — VideoCompare scrub/step 컨트롤.
//   STEP_SECONDS: ← / → 버튼 한 번 = 0.1s 이동 (belle "0.0초 단위" 요구).
//   THUMB_RADIUS: timeline 위 drag 손잡이 hit area 반지름. 트랙 두께 4 + 손잡이 12.
const STEP_SECONDS = 0.1;
const THUMB_DIAMETER = 14;

// quick-260702-t0v (belle TestFlight #27 — 각도 라벨 가독) — 전체화면 오버레이 배율.
// KeypointOverlay 는 viewBox 정규화 구조라 라벨 유효 크기 = 14 × 렌더높이/1280.
// 세로 카드(높이 ~290pt) → 가로 전체화면(~393pt) 전환만으로는 ~1.35배뿐이라
// 판독 불가 잔존 → sizeScale 2.0 병행. belle 실기기 확인 후 미세조정 가능하도록
// 상수화 (부족하면 상향).
const FULLSCREEN_OVERLAY_SCALE = 2.0;

// follow-up (belle 실기기 1차 — 시간 라벨 등 텍스트가 세로 카드 크기 그대로라 작음).
// 전체화면 UI 텍스트 배율 = 오버레이 배율에서 파생. SVG 각도 라벨(2.0)만큼 키우면
// 시간 라벨이 과대해져 0.75 계수로 완화 (captionSmall 10pt → 15pt).
const FULLSCREEN_TEXT_SCALE = FULLSCREEN_OVERLAY_SCALE * 0.75;

// 폴스포츠 = 세로 영상 위주 (design.md §10-4) — 세로 카드 slotFrame 의 9:16
// 가정과 동일. 전체화면 슬롯 안 영상 박스를 같은 비율로 잡아 KeypointOverlay
// (viewBox 0 0 1 1, preserveAspectRatio "none") 가 영상 표시 영역과 정확히 겹침
// (박스가 임의 비율이면 오버레이 좌표가 letterbox 포함 영역으로 늘어나 어긋남).
const VIDEO_ASPECT = 9 / 16;

// quick-260705-k8y — 전체화면 고정 줌. belle 실기기 3차 2026-07-05 승인 —
// 세로영상 위아래 여백(천장 등)을 잘라내고 인물을 키운다. 클리핑 래퍼가 기존
// 박스 자리를 유지하므로 두 박스 row 레이아웃/컨트롤 배치 불변. 9:16 영상이
// 9:16 박스에 contain(레터박스 없음)이라 1.35배 확대 시 상하/좌우 각 ~17.5%
// 크롭 — 인물은 통상 중앙이라 안전. 크롭 정도 조정은 이 상수만 상향/하향.
const FULLSCREEN_ZOOM = 1.35;

// 29-CONTEXT D-11/D-12 — 진짜 가로 + 구빌드(27) 폴백. 정적 import = OTA 크래시 (RESEARCH Pitfall 3).
// expo-screen-orientation 9.0.9 는 모듈 최상위에서 requireNativeModule('ExpoScreenOrientation')
// 를 실행한다(build/ExpoScreenOrientation.js 실측) — 파일 상단 정적 import 를 넣으면 네이티브
// 모듈이 없는 구빌드(TestFlight 27)가 OTA 번들 평가 시점에 앱 전체 크래시한다(가로 기능 미사용도).
// requireOptionalNativeModule 은 부재 시 throw 없이 null 반환 → 런타임 감지만으로 분기.
// 실제 lockAsync 호출은 함수 스코프 lazy require('expo-screen-orientation') 뒤에서만(Metro 는
// require 호출 시점 평가 → 구빌드에서 해당 함수 미호출이면 안전).
const hasNativeOrientation =
  requireOptionalNativeModule('ExpoScreenOrientation') != null;

export function VideoCompare({
  leftLabel,
  rightLabel,
  leftUrl,
  rightUrl,
  leftOverlay,
  rightOverlay,
  fullscreenHeaderExtra,
  fullscreenLegend,
  onLegendPress,
  timelineTicks,
  tickFrameCount,
  alignment: alignmentInput,
}: VideoCompareProps) {
  // expo-video: source 가 null 이면 자원만 잡고 재생 가능 상태 아님 — 훅 순서를
  // 깨지 않으면서 빈 URL 도 안전. 음소거 + 루프 끄기(비교에 방해 안 되게).
  //
  // Phase 12 Wave 2 (Plan 12-03 T1): timeUpdateEventInterval=0.033 (~30fps).
  // KeypointOverlay 가 useEvent(player, 'timeUpdate') 로 native emit 구독 →
  // frame index 자동 산출. 기존 250ms 폴링(타임라인 label) 과 공존 — 타임라인은
  // 250ms / 오버레이는 33ms 분기 (R10 iter-2 정합, D-12-C5).
  const leftPlayer = useVideoPlayer(leftUrl ?? null, (p) => {
    p.muted = true;
    p.loop = false;
    p.timeUpdateEventInterval = 0.033;
  });
  const rightPlayer = useVideoPlayer(rightUrl ?? null, (p) => {
    p.muted = true;
    p.loop = false;
    p.timeUpdateEventInterval = 0.033;
  });

  const hasLeft = !!leftUrl;
  const hasRight = !!rightUrl;
  const hasAny = hasLeft || hasRight;

  // currentTime 폴링 — expo-video 는 prop 변경 이벤트가 따로 없음. 재생 중에만
  // 250ms 마다 갱신 → 타임라인 따라잡기. 정지 상태면 폴링 멈춰 배터리 보호.
  //
  // 12-deferred §12-C — 두 영상 native duration / fps 가 다르면 단일 타임라인이
  // drift 시각화 가림. left/right currentTime + duration 분리 상태로 저장 → 시간
  // 라벨 두 개 동시 표시 (progress bar 는 짧은 쪽 기준 단일 유지).
  const [leftCurrent, setLeftCurrent] = useState(0);
  const [leftDuration, setLeftDuration] = useState(0);
  const [rightCurrent, setRightCurrent] = useState(0);
  const [rightDuration, setRightDuration] = useState(0);
  const [playing, setPlaying] = useState(false);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // Build 16 (iter-2): hysteresis 제거. UAT 5차에서 보정 후 0.15 미만 안 들어와
  // 다음 보정 못 하는 사이 drift 1-2s 누적 finding. 매 tick drift > 0.2 면 즉시
  // 보정 (stutter 위험 < 동기화 우선). 보정 직후 100ms 안에 또 보정 진입은 fine.

  // Phase 12 후속 B — scrub 중일 때 drift correction 우회. PanResponder 가
  // 양쪽 currentTime 을 동일 값으로 setter — 다음 tick 의 drift > 0.2 가짜로
  // 잡혀 또 seek 보내면 stutter. drag 중에는 보정 skip.
  const scrubbingRef = useRef(false);
  const wasPlayingBeforeScrubRef = useRef(false);
  const trackWidthRef = useRef(0);

  // quick-260702-t0v (belle TestFlight #27 — 각도 라벨 가독) — 가로 전체화면 뷰어.
  // 29-CONTEXT D-11/D-12 — 새 빌드는 hasNativeOrientation 감지 시 진짜 가로(LANDSCAPE)로
  // lock, 구빌드(27)는 Modal 안 뷰 90° 회전 핵으로 가로 레이아웃 시뮬레이트(폴백 보존).
  // 같은 leftPlayer/rightPlayer 인스턴스에 두 번째 VideoView 를 attach → 재생
  // 위치/상태 연속, drift 보정 tick·togglePlay·seekBoth 가 양 레이아웃을 그대로 제어.
  const [fullscreen, setFullscreen] = useState(false);
  // 전체화면 타임라인 track 은 폭이 다름 — scrubAtX 가 활성 레이아웃의 폭을 읽도록
  // ref 분리 (portrait track 은 Modal 뒤에 mount 유지라 onLayout 재발화 없음).
  const fullscreenRef = useRef(false);
  const fsTrackWidthRef = useRef(0);
  // useWindowDimensions = 반응형 hook 값 직접 사용 (Modal 마운트 시점 캐싱 없음).
  // portrait 고정이라 width=short/height=long 이 정상이나, 순간 오보고에도 축
  // 스왑이 깨지지 않도록 short/long 파생으로 사용 (follow-up: 레이아웃 fix).
  const { width: winW, height: winH } = useWindowDimensions();
  const fsShort = Math.min(winW, winH);
  const fsLong = Math.max(winW, winH);
  // belle 실기기 2차 2026-07-05 — 퍼센트(height '100%')+aspectRatio 박스가 90°
  // 회전 absolute 컨테이너 + flex 반쪽 슬롯 안에서 ~68% 축소 렌더 (실기기 확인).
  // 퍼센트/aspectRatio 를 버리고 window 파생 숫자 치수로 전환 — 세로영상이 화면
  // 짧은 변을 100% 채우는 9:16 박스. window 파생값이라 하드코딩 아님.
  const fsBoxH = fsShort;
  const fsBoxW = Math.round(fsShort * VIDEO_ASPECT);

  // 29-CONTEXT D-11 — 진짜 가로 lock. hasNativeOrientation === false(구빌드)면 no-op →
  // 기존 90° 회전 핵 폴백이 그대로 동작(D-12). lazy require 는 함수 스코프 — 정적 import
  // 금지(모듈 최상위 requireNativeModule 크래시, Pitfall 3). lockAsync 실패는 무해화
  // (iPad/기기 자동회전 설정 등 — Pitfall 5, HUMAN-UAT 관찰 항목).
  const lockLandscape = useCallback(() => {
    if (!hasNativeOrientation) return;
    const ScreenOrientation = require('expo-screen-orientation');
    ScreenOrientation.lockAsync(
      ScreenOrientation.OrientationLock.LANDSCAPE_RIGHT,
    ).catch(() => {
      /* 가로 lock 실패 — 폴백 없이 세로 유지(HUMAN-UAT) */
    });
  }, []);
  const lockPortrait = useCallback(() => {
    if (!hasNativeOrientation) return;
    const ScreenOrientation = require('expo-screen-orientation');
    ScreenOrientation.lockAsync(
      ScreenOrientation.OrientationLock.PORTRAIT_UP,
    ).catch(() => {
      /* 세로 복귀 실패 — 무해화 */
    });
  }, []);

  const openFullscreen = () => {
    fullscreenRef.current = true;
    setFullscreen(true);
    // 진입 lock 은 Modal 마운트(commit) 이후 effect 에서 — 마운트 전 lock 은 무효(Pattern 4).
  };
  const closeFullscreen = () => {
    // 이탈 시퀀스: PORTRAIT_UP lock 을 setState 전에 먼저 — 역순이면 세로 복귀 전 Modal 이
    // 닫혀 flicker(Pattern 4). onRequestClose(Android back)도 이 경로 공유.
    lockPortrait();
    fullscreenRef.current = false;
    setFullscreen(false);
  };

  // 29-CONTEXT D-11 — 가로/세로 전환 부수효과. fullscreen 진입 시 Modal 마운트 이후(effect=
  // commit 이후) 가로 lock, 이탈/언마운트 시 세로 복원. closeFullscreen 이 선제 lockPortrait
  // 하므로 cleanup 은 다른 이탈 경로(언마운트, 화면 이탈) 안전망. 구빌드는 두 helper 가 no-op.
  useEffect(() => {
    if (fullscreen) lockLandscape();
    return () => {
      lockPortrait();
    };
  }, [fullscreen, lockLandscape, lockPortrait]);

  // ── 28-06 (D-01/D-02) 동작 기준 워핑 소비 ──────────────────────────────────
  // 학생(left)=master 시계 불변, 정은지(right)만 warp(tStudent)→tRef. alignment
  // 부재/null/disabled = 현행 절대시계 100% 보존. 소비측에서 normalizeMotionAlignment
  // 재검증(T-28-02) — malformed/모순 alignment 가 재생 제어(rate/seek) 오작동시키는
  // 것 순수 함수로 격리 차단.
  const alignment = normalizeMotionAlignment(alignmentInput ?? null);
  const alignmentActive = !!alignment && alignment.tier !== 'disabled';
  // 최신 alignment 를 tick(setInterval 클로저)이 읽도록 ref 미러 — alignment 는 매
  // 렌더 새 객체라 effect deps 에 넣으면 interval 재설치 churn. ref 로 stale 클로저
  // 회피(선행 tick/scrub ref 패턴 동일).
  const alignmentRef = useRef(alignment);
  alignmentRef.current = alignment;
  // rate feedforward 직전 설정값 기억 — 구간 경계에서만 실변경(매 tick 재설정 =
  // 플랫폼 재버퍼 위험, 28-RESEARCH Anti-Patterns).
  const lastRateRef = useRef(1.0);

  // right 목표시각 = 정렬 활성 시 warp(tStudent), 아니면 identity. 순수 계산.
  const targetRefTime = (tStudent: number): number => {
    const a = alignmentRef.current;
    return a && a.tier !== 'disabled' ? warpTime(a, tStudent) : tStudent;
  };
  // WR-01 — 정렬 활성 경로에서만 warp 목표시각을 [0, dR] 로 클램프. warpTime 은 범위
  // 밖을 기울기 1.0 으로 연장하므로 u0>r0(학생 준비 구간 > 정은지 트림 시작)이면
  // warp(cL)<0 구간이 생겨, 플레이어가 음수를 0 으로 무는 동안 drift 가 임계를 계속
  // 넘어 매 tick(100ms) 음수 seek 를 발사(정은지 프레임0 버벅). 끝쪽 warp>dR 초과
  // seek 도 차단. 비활성(legacy) = identity 무클램프 → 절대시계 byte-동일 보존.
  const clampRefTarget = (tStudent: number, dR: number): number => {
    const a = alignmentRef.current;
    const raw = a && a.tier !== 'disabled' ? warpTime(a, tStudent) : tStudent;
    if (!a || a.tier === 'disabled') return raw; // legacy identity — 무클램프
    return dR > 0 ? Math.max(0, Math.min(raw, dR)) : Math.max(0, raw);
  };
  // right 쓰기의 유일한 warp 경유 지점 (MEDIUM-1 코드 형태 규율) — 정렬 활성 경로의
  // rightPlayer.currentTime 대입은 전부 여기로 격리, 비활성 시 identity 라 legacy 동일.
  const setRightToStudentTime = (tStudent: number) => {
    if (rightPlayer) {
      rightPlayer.currentTime = clampRefTarget(tStudent, rightPlayer.duration ?? 0);
    }
  };
  // legacy 절대 동기 전용 (부재/disabled 경로) — 호출은 반드시 `!alignmentActive`
  // 가드 분기 안에서만. 리뷰 MEDIUM-1: 절대시간 대입이 정렬 활성 경로에 새는 것
  // 구조적 차단.
  const setBothAbsoluteTime = (t: number) => {
    if (leftPlayer) leftPlayer.currentTime = t;
    if (rightPlayer) rightPlayer.currentTime = t;
  };

  useEffect(() => {
    if (!hasAny) return;
    const tick = () => {
      const cL = leftPlayer?.currentTime ?? 0;
      const cR = rightPlayer?.currentTime ?? 0;
      const dL = leftPlayer?.duration ?? 0;
      const dR = rightPlayer?.duration ?? 0;
      setLeftCurrent(cL);
      setRightCurrent(cR);
      setLeftDuration(dL);
      setRightDuration(dR);
      // 비교 기준 길이 = 둘 중 짧은 쪽. 짧은 쪽 끝나면 함께 멈추도록.
      const shorter =
        dL > 0 && dR > 0 ? Math.min(dL, dR) : Math.max(dL, dR);
      const ref = hasLeft ? leftPlayer : rightPlayer;
      const bothPlaying = !!leftPlayer?.playing && !!rightPlayer?.playing;
      setPlaying(!!ref?.playing);

      // UAT 4차 Finding 1 — drift 보정 (Build 16 iter-2).
      //   tick 100ms 마다 매번 drift > 0.2s 면 즉시 보정. hysteresis 없음.
      //   조건: 둘 다 재생 중 + 둘 다 native duration 산정됨 + 끝부분 진입 전.
      //   Phase 12 후속 B — scrub 중에는 보정 skip (PanResponder 가 동시 seek 한
      //   상태에서 또 보정 들어가면 stutter).
      const aTick = alignmentRef.current;
      const activeTick = !!aTick && aTick.tier !== 'disabled';
      if (
        hasLeft &&
        hasRight &&
        bothPlaying &&
        !scrubbingRef.current &&
        dL > 0 &&
        dR > 0 &&
        leftPlayer &&
        rightPlayer
      ) {
        if (activeTick) {
          // 28-06 D-01 — 워핑 활성: left=master 로 back-seek 없음, 목표값만
          //   cR ≈ cL 에서 cR ≈ warpTime(cL) 로 교체. rate=feedforward(아래),
          //   이 tick seek=feedback 안전망 (A2 — expo-video rate 지연 미문서화,
          //   0.2s 내 동기 보장). 끝부분 진입 전에만 보정(left 기준).
          if (cL < dL - 0.1) {
            // WR-01 — 클램프된 목표와 cR 의 차이로 drift 판정. 클램프 없이 음수
            // target 이면 플레이어가 cR 을 0 으로 물어 drift 가 영구히 임계 초과 →
            // seek 폭풍. 클램프 후 임계 이하면 seek 생략(정은지 시작 프레임 자연 대기).
            const target = clampRefTarget(cL, dR);
            const drift = Math.abs(cR - target);
            if (drift > DRIFT_CORRECT_THRESHOLD_S) {
              rightPlayer.currentTime = target;
            }
          }
        } else if (shorter > 0 && Math.max(cL, cR) < shorter - 0.1) {
          // legacy(부재/null/disabled) — 기존 상호 back-seek 그대로. 직접 대입은
          // helper 경유로만 치환(right 는 setRightToStudentTime, 비활성=identity).
          const drift = Math.abs(cL - cR);
          if (drift > DRIFT_CORRECT_THRESHOLD_S) {
            // 느린 쪽 시각을 authoritative time 으로 사용 (빠른 쪽 back-seek).
            const slowerTime = Math.min(cL, cR);
            if (cL > cR) {
              leftPlayer.currentTime = slowerTime;
            } else {
              setRightToStudentTime(slowerTime);
            }
          }
        }
      }

      // 28-06 (Task 2) rate feedforward — 구간 기울기를 정은지(right) playbackRate
      //   로 선반영. **직전 설정값과 다를 때만 실변경** (구간 경계에서만, 초당 최대
      //   2회) — 매 tick 재설정은 플랫폼 재버퍼 위험(28-RESEARCH Anti-Patterns).
      //   비활성/pause 시 1.0 복원. preservesPitch 는 muted=true 라 무접촉.
      if (rightPlayer) {
        const desiredRate =
          activeTick && aTick && bothPlaying ? segmentRate(aTick, cL) : 1.0;
        if (desiredRate !== lastRateRef.current) {
          rightPlayer.playbackRate = desiredRate;
          lastRateRef.current = desiredRate;
        }
      }

      // UAT 4차 Finding 2 — 짧은 쪽 끝났는데 다른 쪽이 계속 가는 상황 방지.
      //   이전 (Build 14): OR (`cL >= shorter || cR >= shorter`) — 빠른 쪽이
      //   먼저 도달하면 양쪽 pause → 느린 쪽은 실 native duration 못 채운 채
      //   pause, 다음 replay 시 빠른 쪽은 이미 자기 native end 넘어 진행 X.
      //   현재 (Build 15): AND-like (Math.min 둘 다 도달) — drift 보정 위와 결합.
      //   드물게 둘 중 한 쪽만 end 도달하면 보정 fail 케이스 → safety net 으로
      //   max 가 자기 native duration 도달 시도 같이 pause (둘 다 native end).
      const minReachedShortEnd = shorter > 0 && Math.min(cL, cR) >= shorter - 0.05;
      const leftReachedOwnEnd = dL > 0 && cL >= dL - 0.05;
      const rightReachedOwnEnd = dR > 0 && cR >= dR - 0.05;
      const bothReachedOwnEnd =
        (!hasLeft || leftReachedOwnEnd) && (!hasRight || rightReachedOwnEnd);
      // 28-06 D-01 — 워핑 활성 시 비교 재생 정의역 = min(dL, uN)(uN=마지막 앵커
      //   학생초). warp(uN) 이후는 기울기 1.0 연장이라 어느 한 쪽이 자기 native end
      //   도달 시 pause. cR 이 warp(ref-time)이라 min(cL,cR) 혼합이 무의미 → 활성
      //   경로는 either-own-end 로 종료 판정(비활성은 기존 로직 그대로 보존).
      const eitherReachedOwnEnd = leftReachedOwnEnd || rightReachedOwnEnd;
      const shouldPauseAtEnd = activeTick
        ? eitherReachedOwnEnd
        : minReachedShortEnd || bothReachedOwnEnd;
      if (shouldPauseAtEnd) {
        leftPlayer?.pause();
        rightPlayer?.pause();
      }
    };
    tick();
    tickRef.current = setInterval(tick, TICK_INTERVAL_MS);
    return () => {
      if (tickRef.current) clearInterval(tickRef.current);
      tickRef.current = null;
      // 28-06 (Task 2) — unmount/재설치 시 정은지 rate 1.0 복원 (feedforward 잔존
      // 배속이 다음 마운트로 새지 않게).
      // WR-05 — unmount 시 useVideoPlayer(상단 선언) 내부 cleanup 이 먼저 player 를
      // release 하면 released shared object 속성 쓰기가 예외를 던질 수 있다 (결과
      // 화면 이탈 = 매 unmount). try/catch 로 무해화 (deps 재설치 경로는 안전).
      try {
        if (rightPlayer) rightPlayer.playbackRate = 1.0;
      } catch {
        /* released object — 무해 */
      }
      lastRateRef.current = 1.0;
    };
  }, [hasAny, hasLeft, hasRight, leftPlayer, rightPlayer]);

  // progress bar / restart 등 단일 기준 값 — 짧은 쪽 기준 (기존 로직 보존).
  const current = hasLeft ? leftCurrent : rightCurrent;
  // 28-06 (WR-02) — 정렬 활성 시 재생 정의역 = left(master) 도메인. cR=warp(cL)라
  //   min(dL,dR) 혼합은 무의미(progress bar 조기 100% 고정 / seek 상한 오절단). 활성
  //   경로는 leftDuration 단일 기준, 비활성은 기존 로직(짧은 쪽) 그대로 보존.
  const duration = alignmentActive
    ? leftDuration
    : hasLeft && hasRight
      ? leftDuration > 0 && rightDuration > 0
        ? Math.min(leftDuration, rightDuration)
        : Math.max(leftDuration, rightDuration)
      : hasLeft
        ? leftDuration
        : rightDuration;

  const togglePlay = () => {
    if (!hasAny) return;
    if (playing) {
      leftPlayer?.pause();
      rightPlayer?.pause();
      setPlaying(false);
    } else {
      // UAT 4차 Finding 2 — 끝난 상태에서 다시 재생 시 정은지 영상 멈춤 finding.
      //   이전 (Build 14): `current` (= leftCurrent) 한쪽만 검사 → 우측이 자기
      //   native end 넘어가 있어도 reset 발동 안 함. 또한 seek = 0 직후 즉시
      //   play() → expo-video 가 seek 적용 전에 play 호출 받아 우측 정지.
      //   현재 (Build 15):
      //     1) 끝 판정 = Math.max(leftCurrent, rightCurrent) — 어느 한쪽이라도
      //        end 도달했으면 둘 다 reset.
      //     2) reset 시 explicit seek=0 + REPLAY_SEEK_DELAY_MS 후 play() — seek
      //        완료 보장 (60ms 는 한 frame 보다 살짝 길게).
      //     3) drift 보정 상태 reset (`correctingDriftRef`).
      // 28-06 (WR-02) — 정렬 활성 시 종료 판정도 either-own-end(tick 과 동일 도메인).
      //   max(cL,cR) >= min(dL,dR) 혼합은 cR=warp(cL) 가 짧은 정은지 duration 을 조기
      //   초과하면 중간 일시정지 후 재개가 0초 재시작이 되는 버그. 비활성은 기존 유지.
      const maxCurrent = Math.max(leftCurrent, rightCurrent);
      const isAtEnd = alignmentActive
        ? (leftDuration > 0 && leftCurrent >= leftDuration - 0.05) ||
          (rightDuration > 0 && rightCurrent >= rightDuration - 0.05)
        : duration > 0 && maxCurrent >= duration - 0.05;
      // Build 16 iter-2: 시작/재시작 강제 sync — play() 호출 전 둘이 currentTime
      // 다르면 작은 값으로 맞춤. 초기 drift 0 보장.
      const drift = Math.abs(leftCurrent - rightCurrent);
      const needsStartSync =
        hasLeft && hasRight && drift > START_SYNC_THRESHOLD_S;
      if (isAtEnd) {
        if (leftPlayer) leftPlayer.currentTime = 0;
        // 28-06 — right 는 warp 경유(활성 시 r0 오프셋 반영이 옳음, 비활성=0).
        setRightToStudentTime(0);
        // Build 16: seek 적용 시간 확보 후 play (60→200ms — 정은지 S3 buffer reset).
        setTimeout(() => {
          leftPlayer?.play();
          rightPlayer?.play();
          setPlaying(true);
        }, REPLAY_SEEK_DELAY_MS);
      } else if (needsStartSync && leftPlayer && rightPlayer) {
        // 중간 정지 후 다시 재생 시 두 player 시각 동기화 먼저.
        if (alignmentActive) {
          // 28-06 D-01 (MEDIUM-1) — 워핑 활성: left(master) 유지 + right 만
          //   warp(leftCurrent). slowerTime min 절대시간 대입은 워핑 하 무의미
          //   (right 타임라인이 다름) — 활성 경로에 절대 대입 잔존 차단.
          setRightToStudentTime(leftCurrent);
        } else {
          // legacy — 절대 동기(작은 값). setBothAbsoluteTime 은 !alignmentActive 전용.
          const slowerTime = Math.min(leftCurrent, rightCurrent);
          setBothAbsoluteTime(slowerTime);
        }
        setTimeout(() => {
          leftPlayer.play();
          rightPlayer.play();
          setPlaying(true);
        }, REPLAY_SEEK_DELAY_MS);
      } else {
        leftPlayer?.play();
        rightPlayer?.play();
        setPlaying(true);
      }
    }
  };

  const restart = () => {
    if (!hasAny) return;
    if (leftPlayer) leftPlayer.currentTime = 0;
    // 28-06 — right 는 warp 경유(활성 시 r0 오프셋 반영, 비활성=0).
    setRightToStudentTime(0);
    setLeftCurrent(0);
    setRightCurrent(targetRefTime(0));
  };

  // Phase 12 후속 B — 양쪽 동시 seek (drift 0 보장). target 은 짧은 쪽 duration
  // 으로 clamp — 비교 기준 길이를 넘어가지 않게.
  const seekBoth = useCallback(
    (target: number) => {
      const dL = leftPlayer?.duration ?? 0;
      const dR = rightPlayer?.duration ?? 0;
      // 28-06 (WR-02) — 정렬 활성 시 seek 상한 = dL(master). target 은 학생초라
      //   min(dL,dR) 로 자르면 warp(X)<dR 인 비교가능 구간까지 스크럽이 막힌다. right
      //   는 setRightToStudentTime 이 warp+[0,dR] 클램프 담당. alignmentRef 로 활성
      //   판정(선행 ref 패턴 — 콜백 churn 회피). 비활성은 기존 로직.
      const aSeek = alignmentRef.current;
      const activeSeek = !!aSeek && aSeek.tier !== 'disabled';
      const maxAllowed = activeSeek
        ? dL
        : hasLeft && hasRight && dL > 0 && dR > 0
          ? Math.min(dL, dR)
          : hasLeft
            ? dL
            : dR;
      const safe = Math.max(0, Math.min(maxAllowed > 0 ? maxAllowed : target, target));
      if (leftPlayer) leftPlayer.currentTime = safe;
      // 28-06 — right 는 warp 경유(비활성=identity 라 legacy 동일 동작, 분기 불필요).
      setRightToStudentTime(safe);
      // 폴링은 다음 tick 까지 0~100ms 지연 — 즉시 라벨 갱신(right 는 warp 목표시각).
      if (hasLeft) setLeftCurrent(safe);
      if (hasRight) setRightCurrent(targetRefTime(safe));
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps -- setRightToStudentTime/
    // targetRefTime 은 alignmentRef 를 읽어 stale 클로저 무해(선행 tick ref 패턴 동일).
    [hasLeft, hasRight, leftPlayer, rightPlayer],
  );

  // 0.1s 앞/뒤 step. 현재 시각 = 둘 중 작은 값 (slower side 가 진짜 sync 위치).
  const stepBy = useCallback(
    (deltaS: number) => {
      if (!hasAny) return;
      // CR-02 — 정렬 활성 시 base 는 master(left)만. rightCurrent=warp(cL) 은 다른
      //   타임라인이라 min(cL,cR) 혼합이 학생 영상을 수 초 점프시킨다 (u0>r0 이면
      //   base=cL-오프셋 → "0.1초 앞으로"가 학생을 오프셋만큼 뒤로 점프). right 는
      //   seekBoth → setRightToStudentTime 이 warp 로 따라간다. 비활성은 기존 유지
      //   (느린 쪽 = 진짜 sync 위치).
      const base = alignmentActive
        ? leftCurrent
        : hasLeft && hasRight
          ? Math.min(leftCurrent, rightCurrent)
          : hasLeft
            ? leftCurrent
            : rightCurrent;
      seekBoth(base + deltaS);
    },
    [hasAny, hasLeft, hasRight, leftCurrent, rightCurrent, seekBoth, alignmentActive],
  );

  // PanResponder — timeline track drag = scrub. locationX 가 track element 내부
  // 좌표를 반환 → trackWidthRef 측정값과 비율 계산. drag 중 재생 중이면 pause,
  // release 시 wasPlaying 복원.
  const onTrackLayout = useCallback((e: LayoutChangeEvent) => {
    trackWidthRef.current = e.nativeEvent.layout.width;
  }, []);

  // quick-260702-t0v — 전체화면 track 폭 분리 측정 (회전 컨테이너 안 폭이 다름).
  const onFsTrackLayout = useCallback((e: LayoutChangeEvent) => {
    fsTrackWidthRef.current = e.nativeEvent.layout.width;
  }, []);

  const scrubAtX = useCallback(
    (x: number) => {
      // quick-260702-t0v — 활성 레이아웃(세로/전체화면)의 track 폭 사용.
      // PanResponder 의 locationX 는 RN 이 transform 반영 로컬 좌표로 매핑하므로
      // 회전 뷰에서도 그대로 유효.
      const w = fullscreenRef.current
        ? fsTrackWidthRef.current
        : trackWidthRef.current;
      if (w <= 0 || duration <= 0) return;
      const ratio = Math.max(0, Math.min(1, x / w));
      seekBoth(duration * ratio);
    },
    [duration, seekBoth],
  );

  const panResponder = useMemo(
    () =>
      PanResponder.create({
        onStartShouldSetPanResponder: () => hasAny,
        onMoveShouldSetPanResponder: () => hasAny,
        onPanResponderGrant: (e) => {
          scrubbingRef.current = true;
          wasPlayingBeforeScrubRef.current = playing;
          if (playing) {
            leftPlayer?.pause();
            rightPlayer?.pause();
            setPlaying(false);
          }
          scrubAtX(e.nativeEvent.locationX);
        },
        onPanResponderMove: (e) => {
          scrubAtX(e.nativeEvent.locationX);
        },
        onPanResponderRelease: () => {
          scrubbingRef.current = false;
          if (wasPlayingBeforeScrubRef.current) {
            // seek 적용 후 play — 빠른 release 시 seek 미반영 stall 방지.
            setTimeout(() => {
              leftPlayer?.play();
              rightPlayer?.play();
              setPlaying(true);
            }, REPLAY_SEEK_DELAY_MS);
          }
        },
        onPanResponderTerminate: () => {
          scrubbingRef.current = false;
        },
      }),
    [hasAny, leftPlayer, playing, rightPlayer, scrubAtX],
  );

  const progressPct =
    duration > 0 ? Math.min(100, (current / duration) * 100) : 0;

  // quick-260702-t0v — 컨트롤 공유 (로직 중복 0). 세로 카드와 가로 전체화면이
  // 같은 핸들러(togglePlay/stepBy/seekBoth/restart/panResponder)와 같은 JSX 를
  // 공유. dark=true(전체화면)면 어두운 배경 위 색만 토큰 분기.
  const renderControls = (dark: boolean) => (
    <View style={styles.controls}>
      <Pressable
        onPress={togglePlay}
        accessibilityRole="button"
        accessibilityLabel={playing ? '일시정지' : '재생'}
        hitSlop={8}
        style={styles.playBtn}
      >
        <Ionicons
          name={playing ? 'pause' : 'play'}
          size={20}
          color={colors.textWhite}
        />
      </Pressable>
      {/* Phase 12 후속 B — 0.1s 앞/뒤 step.
          자세 미세 비교 시 1-frame 수준 정렬용. belle 요구: "0.0초 단위". */}
      <Pressable
        onPress={() => stepBy(-STEP_SECONDS)}
        accessibilityRole="button"
        accessibilityLabel="0.1초 뒤로"
        hitSlop={8}
        style={[styles.stepBtn, dark && styles.stepBtnDark]}
      >
        <Ionicons
          name="play-back"
          size={16}
          color={dark ? colors.textWhite : colors.brand}
        />
      </Pressable>
      <Pressable
        onPress={() => stepBy(STEP_SECONDS)}
        accessibilityRole="button"
        accessibilityLabel="0.1초 앞으로"
        hitSlop={8}
        style={[styles.stepBtn, dark && styles.stepBtnDark]}
      >
        <Ionicons
          name="play-forward"
          size={16}
          color={dark ? colors.textWhite : colors.brand}
        />
      </Pressable>
      <View style={styles.timeline}>
        {/* quick-260705-r6v — 결함 측정 시점 틱 (track 위 별도 줄, panResponder 와
            겹치지 않게 분리). 29 리뷰 WR-01 — sec = frameIndex * leftDuration /
            tickFrameCount: frameIndex 는 좌측(사용자) 영상 9fps angles 도메인이라
            환산 기준은 leftDuration(master). legacy 경로의 duration=min(dL,dR)을
            쓰면 우측이 짧은 doc 에서 틱이 추가로 앞당겨진다. 트랙 위 위치(pct)만
            재생 도메인 duration 기준(기존 클램프 유지). 탭 = 양쪽 동기
            seek(seekBoth). 세로/전체화면 공용. */}
        {timelineTicks &&
          timelineTicks.length > 0 &&
          tickFrameCount != null &&
          tickFrameCount > 0 &&
          leftDuration > 0 &&
          duration > 0 && (
            <View style={styles.tickRow} pointerEvents="box-none">
              {timelineTicks.map((tick) => {
                const sec = (tick.frameIndex * leftDuration) / tickFrameCount;
                if (!isFinite(sec) || sec < 0) return null;
                const leftPct = Math.max(0, Math.min(100, (sec / duration) * 100));
                const label = tick.numbers.map((n) => circledNumberKo(n)).join('');
                return (
                  <Pressable
                    key={`tick-${tick.frameIndex}`}
                    onPress={() => seekBoth(sec)}
                    accessibilityRole="button"
                    accessibilityLabel={`${tick.numbers.join(', ')}번 감점 시점으로 이동`}
                    hitSlop={8}
                    style={[styles.tick, { left: `${leftPct}%` }]}
                  >
                    <Text style={styles.tickLabel} numberOfLines={1}>
                      {label}
                    </Text>
                    <View style={styles.tickMark} />
                  </Pressable>
                );
              })}
            </View>
          )}
        {/* Phase 12 후속 B — track 자체가 PanResponder. drag 시 양쪽 동시
            seek + scrubbingRef 가 drift 보정 우회 (tick 가드). */}
        <View
          style={styles.timelineTrack}
          onLayout={dark ? onFsTrackLayout : onTrackLayout}
          {...panResponder.panHandlers}
        >
          <View style={styles.timelineRail} pointerEvents="none" />
          <View
            style={[styles.timelineFill, { width: `${progressPct}%` }]}
            pointerEvents="none"
          />
          <View
            style={[styles.timelineThumb, { left: `${progressPct}%` }]}
            pointerEvents="none"
          />
        </View>
        {/* 12-deferred §12-C — 두 영상 timeline 분리 표시.
            progress bar 는 단일 (짧은 쪽 기준), 시간 라벨은 좌·우 분리.
            Phase 12 후속 B — 0.1s 정밀 표시(소수 1자리). */}
        <Text
          style={[styles.timeText, dark && styles.timeTextDark]}
          numberOfLines={1}
        >
          {hasLeft
            ? `${leftLabel} ${fmtTimeDecimal(leftCurrent)} / ${fmtTime(leftDuration)}`
            : ''}
          {hasLeft && hasRight ? '  ·  ' : ''}
          {hasRight
            ? `${rightLabel} ${fmtTimeDecimal(rightCurrent)} / ${fmtTime(rightDuration)}`
            : ''}
        </Text>
      </View>
      <Pressable
        onPress={restart}
        accessibilityRole="button"
        accessibilityLabel="처음으로"
        hitSlop={8}
      >
        <Ionicons
          name="refresh"
          size={20}
          color={dark ? colors.textWhite : colors.textSecondary}
        />
      </Pressable>
    </View>
  );

  // quick-260702-t0v — 전체화면 슬롯. 새 useVideoPlayer 호출 금지 — 기존 player
  // 인스턴스에 두 번째 VideoView attach (expo-video 다중 VideoView 지원).
  // 오버레이는 sizeScale=FULLSCREEN_OVERLAY_SCALE 로 호출 (각도 라벨 확대).
  //
  // belle 실기기 2차 2026-07-05 — 슬롯 = 박스 자체 (fsSlot flex 반쪽 래퍼 폐기).
  //   이전 퍼센트 기반(높이 100% + aspectRatio)이 실기기에서 ~68% 축소 + 박스
  //   사이 ~200pt 간격 + 오버레이 유령 마커로 붕괴 → fsBoxW/fsBoxH 숫자 치수를
  //   render 에서 인라인 주입. 박스 치수가 정확하면 overlayContainer(absoluteFill)
  //   위 KeypointOverlay(viewBox 0 0 1 1) 정합이 자동 회복된다.
  //   라벨은 박스 내부 상단 absolute — 각 영상 상단 중앙에 부착.
  //
  // quick-260705-k8y — 2겹 구조: 클리핑 래퍼(fsBoxW×fsBoxH, overflow hidden)
  // + 내부 FULLSCREEN_ZOOM 배 확대 박스(중앙 정렬). VideoView·overlayContainer
  // 를 내부 확대 박스로 이동 — overlayContainer 가 absoluteFill 이라 오버레이가
  // 영상과 함께 확대·클리핑돼 마커 정합 자동 유지 (정합 기준 박스 = 내부 박스).
  // 확대/오프셋 수치는 전부 fsBoxW/fsBoxH 파생 (하드코딩 픽셀 0).
  const renderFullscreenSlot = (
    label: string,
    url: string | undefined,
    player: VideoPlayer | null,
    overlay?: OverlayRenderProp,
  ) => {
    const zoomW = Math.round(fsBoxW * FULLSCREEN_ZOOM);
    const zoomH = Math.round(fsBoxH * FULLSCREEN_ZOOM);
    const zoomLeft = -Math.round((zoomW - fsBoxW) / 2);
    const zoomTop = -Math.round((zoomH - fsBoxH) / 2);
    return (
      <View style={[styles.fsVideoBox, { width: fsBoxW, height: fsBoxH }]}>
        {url && player ? (
          <View
            style={[
              styles.fsZoomBox,
              { width: zoomW, height: zoomH, left: zoomLeft, top: zoomTop },
            ]}
          >
            <VideoView
              player={player}
              style={styles.video}
              contentFit="contain"
              nativeControls={false}
              allowsFullscreen={false}
              allowsPictureInPicture={false}
            />
            <View style={styles.overlayContainer} pointerEvents="box-none">
              {overlay?.(player, { sizeScale: FULLSCREEN_OVERLAY_SCALE })}
            </View>
          </View>
        ) : (
          <View style={styles.slotEmpty}>
            <Ionicons
              name="videocam-outline"
              size={22}
              color={colors.textDisabled}
            />
            <Text style={styles.slotEmptyText}>준비 중</Text>
          </View>
        )}
        {/* 라벨 = 클리핑 래퍼 직속 absolute 상단 중앙 — 확대 박스 밖이라 잘리지
            않는다 (하단은 공유 컨트롤이 차지) */}
        <Text style={styles.fsSlotLabel} pointerEvents="none">
          {label}
        </Text>
      </View>
    );
  };

  // 28-06 (Task 2) — tier 별 정직한 배지 카피. alignment 부재(legacy doc) = null →
  //   기존 정적 배지 유지(D-05 배너는 28-07 result.tsx 책임, 배지/배너 분리). 수치
  //   표기 안 함 — DTW distance 원값은 사용자 의미 없음(Phase 20 A4, 가짜/무의미 수치
  //   금지). tier 사다리 3단(D-02, belle 지정 톤).
  const alignBadgeCopy: { title: string; hint: string } | null = !alignment
    ? null
    : alignment.tier === 'warped'
      ? { title: '자동 구간 맞춤', hint: '동작 기준으로 자동 구간을 맞췄어요' }
      : alignment.tier === 'trim_only'
        ? {
            title: '자동 구간 맞춤',
            hint: '동작 차이가 있어 시작점만 맞췄어요 (배속 조정은 꺼짐)',
          }
        : { title: '자동 정렬 꺼짐', hint: '기준 동작과 차이가 커 자동 정렬을 껐어요' };

  return (
    <View style={styles.card}>
      <View style={styles.row}>
        <VideoSlot
          label={leftLabel}
          url={leftUrl}
          player={leftPlayer}
          overlay={leftOverlay}
        />
        <VideoSlot
          label={rightLabel}
          url={rightUrl}
          player={rightPlayer}
          overlay={rightOverlay}
        />
      </View>

      {/* Phase 20 (UI A4) — "자동 구간 맞춤" 신뢰 배지.
          belle 가 서로 다른 시작점의 두 영상을 자동 정렬한 점을 호평 → 이 정렬이
          의도된 것임을 사용자에게 정직하게 알린다. 두 영상이 모두 있을 때만 노출
          (단일 영상은 정렬 대상 없음).

          Phase 28 해소 — tier 실데이터 기반: alignment prop 이 있으면 tier 사다리
          3단(warped/trim_only/disabled)을 정직하게 고지(alignBadgeCopy). 부재(legacy
          doc)면 기존 정적 카피 유지. 수치(DTW distance)는 표기 안 함 — 사용자 의미
          없는 원값(가짜/무의미 수치 금지, Phase 20 A4). */}
      {hasLeft && hasRight && (
        <View style={styles.alignBadgeRow}>
          <View style={styles.alignBadge}>
            <Ionicons
              name="git-compare-outline"
              size={12}
              color={colors.brand}
            />
            <Text style={styles.alignBadgeText}>
              {alignBadgeCopy ? alignBadgeCopy.title : '자동 구간 맞춤'}
            </Text>
          </View>
          <Text style={styles.alignBadgeHint}>
            {alignBadgeCopy
              ? alignBadgeCopy.hint
              : '서로 다른 시작점을 핵심 구간 기준으로 자동 정렬했어요.'}
          </Text>
        </View>
      )}

      {/* quick-260702-t0v (belle TestFlight #27 — 각도 라벨 가독) — 가로 전체화면
          진입 버튼. 세로 나란히 2개 레이아웃에선 각도 라벨이 판독 불가 → 탭 시
          두 영상을 좌우로 크게 보는 전체화면 뷰어. */}
      {hasAny && (
        <Pressable
          onPress={openFullscreen}
          accessibilityRole="button"
          accessibilityLabel="가로 전체화면으로 크게 보기"
          hitSlop={8}
          style={styles.fullscreenBtn}
        >
          <Ionicons name="expand" size={16} color={colors.brand} />
          <Text style={styles.fullscreenBtnText}>가로로 크게 보기</Text>
        </Pressable>
      )}

      {hasAny ? (
        renderControls(false)
      ) : (
        <Text style={styles.hint}>
          분석 서버가 연결되면 두 영상을 동시에 재생하며 관절 차이를 비교할 수
          있어요.
        </Text>
      )}

      {/* quick-260702-t0v — 가로 전체화면 뷰어. portrait 고정 유지 + 뷰 90° 회전
          (검증된 가로 시뮬레이트 패턴). 조건부 렌더 — 닫힌 동안 native 리소스 0
          (T-t0v-01). 같은 player 라 열고 닫아도 재생 위치·상태 자동 연속. */}
      {fullscreen && (
        <Modal
          visible
          transparent={false}
          animationType="fade"
          statusBarTranslucent
          // 29-CONTEXT D-11 — 진짜 가로 분기는 Modal 이 landscape 를 허용해야 실제 회전한다
          // (RN Modal 은 자체 orientation 허용 목록 보유, Pattern 4). 구빌드 폴백은 portrait
          // 고정 유지(90° 회전 핵이 가로를 시뮬레이트하므로 실제 회전 불필요).
          supportedOrientations={
            hasNativeOrientation ? ['portrait', 'landscape'] : ['portrait']
          }
          onRequestClose={closeFullscreen}
        >
          {/* 모달 unmount 시 root _layout 의 StatusBar 로 자연 복귀 */}
          <StatusBar hidden />
          <View style={styles.fsRoot}>
            {/* follow-up (belle 실기기 1차) — 컨테이너는 short/long 파생 치수.
                영상 row 가 컨테이너 전체를 채우고(absoluteFill), 상단 bar 와 하단
                컨트롤은 영상 위 overlay — 스택 배치로 영상 높이를 깎지 않는다
                (스택이면 유효 영상 높이 ~250pt = 세로 카드와 동급이 근본 원인).
                29-CONTEXT D-11 — 진짜 가로(hasNativeOrientation)면 기기가 실제 회전하므로
                90° transform·축 스왑 오프셋을 생략하고 화면(=fsLong×fsShort)을 그대로 채운다.
                구빌드 폴백은 fsRotated(rotate 90deg) + 중앙 오프셋 핵을 byte-보존. */}
            <View
              style={
                hasNativeOrientation
                  ? [styles.fsLandscape, { width: fsLong, height: fsShort }]
                  : [
                      styles.fsRotated,
                      {
                        width: fsLong,
                        height: fsShort,
                        left: (fsShort - fsLong) / 2,
                        top: (fsLong - fsShort) / 2,
                      },
                    ]
              }
            >
              {/* belle 실기기 2차 2026-07-05 — url 있는 슬롯만 렌더. 단일 영상
                  (hasLeft xor hasRight)이면 justifyContent center 가 1박스를
                  자동 중앙 배치. 진입 버튼이 hasAny 가드라 0박스 케이스 없음. */}
              <View style={styles.fsVideoRow}>
                {hasLeft &&
                  renderFullscreenSlot(leftLabel, leftUrl, leftPlayer, leftOverlay)}
                {hasRight &&
                  renderFullscreenSlot(
                    rightLabel,
                    rightUrl,
                    rightPlayer,
                    rightOverlay,
                  )}
              </View>
              <View style={styles.fsTopBar}>
                {/* quick-260705-r6v — 검은 여백 좌측 고정 범례 (flex:1). 재생 중
                    영상 위 텍스트 pill 을 없앤 대신 "① 행동구 −감점" 을 여백에
                    가로 나열(여백 좁으면 flexWrap). 탭 = closeFullscreen 선행 후
                    드릴다운(iOS 중첩 Modal 함정 회피). */}
                <View style={styles.fsLegend} pointerEvents="box-none">
                  {(fullscreenLegend ?? []).map((item) => (
                    <Pressable
                      key={`legend-${item.number}`}
                      onPress={() => {
                        closeFullscreen();
                        onLegendPress?.(item.number);
                      }}
                      accessibilityRole="button"
                      accessibilityLabel={`${item.number}번 감점 상세 보기`}
                      hitSlop={6}
                      style={styles.fsLegendItem}
                    >
                      <Text style={styles.fsLegendNumber}>
                        {circledNumberKo(item.number)}
                      </Text>
                      <Text style={styles.fsLegendText} numberOfLines={1}>
                        {item.text}
                      </Text>
                    </Pressable>
                  ))}
                </View>
                {fullscreenHeaderExtra}
                <Pressable
                  onPress={closeFullscreen}
                  accessibilityRole="button"
                  accessibilityLabel="전체화면 닫기"
                  hitSlop={12}
                  style={styles.fsCloseBtn}
                >
                  <Ionicons name="close" size={22} color={colors.textWhite} />
                </Pressable>
              </View>
              <View style={styles.fsControlsWrap}>{renderControls(true)}</View>
            </View>
          </View>
        </Modal>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.cardBg,
    borderRadius: radius.card,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    padding: spacing.cardPadding,
    gap: 12,
    width: '100%',
  },
  row: {
    flexDirection: 'row',
    gap: 8,
  },
  slot: {
    flex: 1,
    gap: 6,
  },
  // 폴스포츠 = 세로 영상 위주(design.md §10-4). 9:16 비율 슬롯에 contain 으로
  // 가로/세로 모두 안전하게 들어옴.
  slotFrame: {
    width: '100%',
    aspectRatio: 9 / 16,
    borderRadius: 12,
    overflow: 'hidden',
    backgroundColor: colors.divider,
    borderWidth: 1,
    borderColor: colors.divider,
  },
  video: {
    width: '100%',
    height: '100%',
  },
  // Phase 12 신설 (Plan 12-02 T4) — KeypointOverlay 박제 site.
  // quick-260705-r6v — 래퍼 pointerEvents 를 box-none 으로 전환(렌더 site 인라인):
  // 번호 점 Pressable 히트 레이어가 탭을 받되, 빈 영역은 아래로 통과. 영상 본체엔
  // 제스처 핸들러가 없어 무해(planner_findings 2).
  overlayContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
  },
  slotEmpty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    backgroundColor: '#F4F4F4',
  },
  slotEmptyText: {
    ...typography.captionSmall,
    color: colors.textDisabled,
  },
  slotLabel: {
    ...typography.captionSmall,
    color: colors.textSecondary,
    textAlign: 'center',
  },
  controls: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  playBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
  },
  // Phase 12 후속 B — 0.1s 앞/뒤 step 버튼.
  // quick-260706-sis (D3): divider(회색) 배경 + textSecondary 아이콘이라 비활성
  // 처럼 보여 "누를 수 있는지 모르겠다"는 실증 피드백. 연한 브랜드 틴트 배경 +
  // 브랜드 아이콘으로 '탭 가능' 신호. 꽉 찬 브랜드 원인 playBtn 과는 톤 차등(보조).
  stepBtn: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: colors.brandTint,
    alignItems: 'center',
    justifyContent: 'center',
  },
  timeline: {
    flex: 1,
    gap: 6,
  },
  // Phase 12 후속 B — track 이 PanResponder 박힘 site. 두께 12 로 키워 drag hit
  // area 확보 (시각 트랙 4 + 손잡이 14 가 안쪽에 박힘). overflow 'visible' 가
  // 손잡이 위/아래로 비집고 나옴.
  timelineTrack: {
    width: '100%',
    height: 14,
    justifyContent: 'center',
  },
  timelineRail: {
    position: 'absolute',
    top: 5,
    left: 0,
    right: 0,
    height: 4,
    backgroundColor: colors.divider,
    borderRadius: 2,
  },
  timelineFill: {
    position: 'absolute',
    top: 5,
    left: 0,
    height: 4,
    backgroundColor: colors.brand,
    borderRadius: 2,
  },
  timelineThumb: {
    position: 'absolute',
    top: (14 - THUMB_DIAMETER) / 2,
    width: THUMB_DIAMETER,
    height: THUMB_DIAMETER,
    borderRadius: THUMB_DIAMETER / 2,
    backgroundColor: colors.brand,
    marginLeft: -THUMB_DIAMETER / 2,
    borderWidth: 2,
    borderColor: colors.cardBg,
  },
  timeText: {
    ...typography.captionSmall,
    color: colors.textSecondary,
  },
  hint: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  // Phase 20 (UI A4) — 자동 정렬 신뢰 배지 + 한 줄 설명 (정적, 토큰만).
  alignBadgeRow: {
    gap: 4,
  },
  alignBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 9,
    backgroundColor: colors.brandTint,
  },
  alignBadgeText: {
    ...typography.captionSmall,
    color: colors.brand,
    fontWeight: '700',
  },
  alignBadgeHint: {
    ...typography.captionSmall,
    color: colors.textSecondary,
    lineHeight: 15,
  },
  // ── quick-260702-t0v — 가로 전체화면 뷰어 (belle TestFlight #27) ─────────
  // 진입 버튼: 전체 너비 pill (brandTint 배경 + brand 텍스트, 토큰만).
  fullscreenBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    width: '100%',
    paddingVertical: 10,
    borderRadius: radius.button,
    backgroundColor: colors.brandTint,
  },
  fullscreenBtnText: {
    ...typography.caption,
    color: colors.brand,
    fontWeight: '700',
  },
  // 몰입형 영상 전체화면 배경 — videoFullscreenBg 토큰 (다크 배경 금지 원칙의
  // 의도적 예외, colors.ts 주석 참조).
  fsRoot: {
    flex: 1,
    backgroundColor: colors.videoFullscreenBg,
  },
  // 90° 회전 컨테이너 — width/height/left/top 은 render 에서 short/long 파생값
  // 으로 주입. follow-up: padding/gap 제거 — 영상 row 가 edge-to-edge 로 채우고
  // 상단 bar/컨트롤은 overlay (스택 배치가 영상 높이를 깎던 버그 fix).
  fsRotated: {
    position: 'absolute',
    transform: [{ rotate: '90deg' }],
  },
  // 29-CONTEXT D-11 — 진짜 가로 컨테이너. 기기가 실제 회전하므로 fsLong×fsShort 가 곧
  // 화면 치수 → top/left 0 에서 전체를 채운다(90° transform·중앙 오프셋 불필요). 내부
  // fsVideoRow/fsTopBar/fsControlsWrap 는 회전 핵과 동일 좌표계라 렌더 코드 공유.
  fsLandscape: {
    position: 'absolute',
    top: 0,
    left: 0,
  },
  // 상단 bar overlay — 우측에 토글 + 닫기. 두 9:16 박스가 중앙 인접 배치라
  // (393 기기 기준 박스 우측 끝 x 는 약 639) 우측 끝 버튼 영역과 겹치지 않음.
  fsTopBar: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: 16,
    paddingHorizontal: spacing.cardPadding,
    paddingTop: 10,
  },
  fsCloseBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.videoBg,
  },
  // quick-260705-r6v — 전체화면 여백 고정 범례 ("① 행동구 −감점" 나열).
  // flex:1 로 좌측 여백을 채우고, 여백이 좁으면 flexWrap 으로 줄바꿈(승인 사항).
  // 우측 헤더 토글/닫기 버튼과 겹치지 않게 paddingRight.
  fsLegend: {
    flex: 1,
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: 8,
    paddingRight: 12,
  },
  fsLegendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  fsLegendNumber: {
    ...typography.captionSmall,
    fontSize: typography.captionSmall.fontSize * FULLSCREEN_TEXT_SCALE,
    color: colors.brand,
    fontWeight: '700',
  },
  fsLegendText: {
    ...typography.captionSmall,
    fontSize: typography.captionSmall.fontSize * FULLSCREEN_TEXT_SCALE,
    color: colors.textWhite,
  },
  // quick-260705-r6v — 재생바 결함 틱 (track 위 별도 줄). tick = 시간 위치 앵커
  // (left%) 에 중앙 정렬된 44pt 터치 박스 (번호 미니 라벨 + 세로 마크).
  tickRow: {
    width: '100%',
    height: 20,
    position: 'relative',
    justifyContent: 'flex-end',
  },
  tick: {
    position: 'absolute',
    bottom: 0,
    width: 44,
    marginLeft: -22,
    alignItems: 'center',
  },
  tickLabel: {
    ...typography.captionSmall,
    color: colors.brand,
    fontWeight: '700',
  },
  tickMark: {
    width: 2,
    height: 6,
    borderRadius: 1,
    marginTop: 1,
    backgroundColor: colors.brand,
  },
  // 하단 컨트롤 overlay (영상 letterbox 영역 위 — 표준 비디오 플레이어 UX).
  fsControlsWrap: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    paddingHorizontal: spacing.cardPadding,
    paddingBottom: 10,
  },
  // 영상 row = 회전 컨테이너 전체. belle 실기기 2차 2026-07-05 — flex 반쪽
  // 슬롯(fsSlot) 폐기, 두 박스를 중앙 인접 배치 (gap 8 = 세로 카드 row 와 동일).
  // 기하 (iPhone 393×852): 박스 221×393 두 개 + gap 8 = 450pt ≤ fsLong 852.
  fsVideoRow: {
    ...StyleSheet.absoluteFillObject,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 8,
  },
  // 세로 영상 최대화 — width/height 는 render 에서 fsBoxW/fsBoxH 숫자 주입
  // (belle 실기기 2차 2026-07-05 — 퍼센트+aspectRatio 가 회전 absolute 컨테이너
  // 안에서 ~68% 축소 렌더).
  // quick-260705-k8y — 클리핑 래퍼로 전환: overflow hidden 이 내부 확대 박스의
  // 위아래(및 좌우) 튀어나온 부분을 잘라낸다.
  fsVideoBox: {
    backgroundColor: colors.videoFullscreenBg,
    overflow: 'hidden',
  },
  // quick-260705-k8y — 내부 확대 박스 (FULLSCREEN_ZOOM 배, 중앙 정렬 오프셋은
  // render 에서 fsBox 파생 숫자 주입). 오버레이 좌표 정합의 기준 박스.
  fsZoomBox: {
    position: 'absolute',
  },
  // belle 실기기 2차 2026-07-05 — 라벨을 박스 내부 absolute 로 이동 (박스 기준
  // 상단 중앙). left/right 0 + textAlign center 로 박스 폭 전체에 중앙 정렬.
  fsSlotLabel: {
    ...typography.captionSmall,
    fontSize: typography.captionSmall.fontSize * FULLSCREEN_TEXT_SCALE,
    color: colors.textWhite,
    textAlign: 'center',
    position: 'absolute',
    top: 12,
    left: 0,
    right: 0,
  },
  // 어두운 배경 위 컨트롤 색 분기 (dark variant) — 토큰만.
  stepBtnDark: {
    backgroundColor: colors.videoBg,
  },
  // follow-up — 시간 라벨 가독 (FULLSCREEN_TEXT_SCALE 파생, 매직넘버 아님).
  timeTextDark: {
    color: colors.textWhite,
    fontSize: typography.captionSmall.fontSize * FULLSCREEN_TEXT_SCALE,
    lineHeight: typography.captionSmall.fontSize * FULLSCREEN_TEXT_SCALE * 1.3,
  },
});

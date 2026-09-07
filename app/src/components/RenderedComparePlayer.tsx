// Phase 35 (quick-260808-jix) — 합성 비교 영상 단일 mp4 플레이어.
//
// 서버(Pod 사후 스테이지)가 user·ref 두 패널 + 감점 정지·코칭 음성·자막을 이미
// 한 mp4 에 구워 놓았다 (contract.md §12.9 — 리그 ALL PASS 만 도착). 여기는
// **재생만** 한다 — 오버레이·동기·스냅·재개 로직 0 (그 계열 버그가 재생기
// 차원에서 소멸하는 것이 돌파 ① 의 목적). 신규 화면 디자인 아님 — 기존
// '동작 비교' 섹션 내 재생원 교체.
//
// UI 라운드 (belle 실기기):
//   · 가로 크게 보기 — 260702-t0v 90° 회전 Modal 패턴 재사용 (portrait 고정
//     유지, JS-only OTA 가능). 단일 플레이어라 동기 로직 불요 — 같은 player
//     인스턴스에 두 번째 VideoView attach (expo-video 다중 VideoView, t0v 선례
//     — 새 useVideoPlayer 호출 금지).
//
// quick-260809-jnb — 조작 UI 복귀 (belle 08-09 실기기 반려):
//   증상 = "조작 UI가 이상해져 있다". 원인 = `nativeControls`(iOS 기본, 몇 초 뒤
//   자동 숨김) + 얇은 틱 바 조합이라, 컨트롤이 숨은 뒤엔 **트랙 위에 점 하나만
//   남아 멈춘 재생바로 읽혔다**(belle 화면 실측: 영상 18.53s / 정지 5.13s =
//   27.7% 지점 = 스크린샷의 그 점). 트랙+점은 "재생 위치"의 시각 문법인데 실제
//   의미는 "감점 정지 지점"이라 의미가 충돌한 것.
//   → 듀얼 플레이어(VideoCompare)의 컨트롤 세트를 그대로 가져온다: 재생/일시정지
//     · 실제 스크럽 트랙(rail/fill/thumb + 드래그) · 시간 · 처음으로. 정지 틱은
//     트랙 **위 별도 줄**에 번호(①②③)를 달아 표시 — 아래 진짜 스크러버가 있으면
//     번호 달린 마커는 재생바로 오독되지 않는다(듀얼 플레이어에서 검증된 배치).
//   ★ 정렬 미세조정 컨트롤(0.1초 뒤로/앞으로 · 시작점 오프셋 슬라이더 · 초기화)은
//     **의도적으로 안 가져온다** — belle 08-09: "알아서 짜맞춰서 비교해줄거면
//     뒤로 조정 앞으로 조정 없어도 될 것 같다". 그것들은 두 영상을 사람이 손으로
//     맞추던 시절의 장치이고, 서버가 정렬해 한 파일로 굽는 지금은 대상이 없다.
//
// URL 은 1시간 TTL asset 서명이라 저장·재사용하지 않고 mount(=analysisId)마다
// 재발급한다 (만료 재서명 = 기존 asset 패턴, H-02 URL 비저장).
// fetch 실패/404 → onUnavailable() — 화면이 기존 듀얼 플레이어로 강등
// (catch 삼킴 금지 — [[icloud-offload-breaks-original-asset-picker]] 교훈,
// __DEV__ warn 으로 원인 가시화).
//
// belle 09-07 — 가로 전체화면에 손가락 확대(핀치) + 탭 멈춤을 얹는다. 이 가지에도
// 필요한 이유: 어느 가지가 그려질지는 기기의 실시간 Firestore 상태가 정한다
// (renderedCompareReady — result.tsx:1094). 듀얼 플레이어에만 확대를 달면 합성
// 영상이 도착한 분석에서는 belle 이 그 기능을 아예 만나지 못한다.
//
// ★ 이 가지의 한계 — 감추지 않고 적어 둔다 (듀얼 플레이어와 같은 것을 주지 못한다):
//   1) 두 패널이 **한 프레임에 이미 구워져** 있다. 그래서 핀치는 좌·우를 따로
//      확대하지 못하고 둘을 함께 키운다. 왼쪽만 크게 보려면 손가락으로 확대한 뒤
//      밀어서(팬) 그쪽으로 옮겨야 한다.
//   2) **인증된 짝 순간으로 뛰어드는 진입점이 없다.** 이 가지가 가진 유일한 시각은
//      freezes[].outSec 인데 그것은 **출력 mp4 의 시계**이지 학생 영상 초가 아니다
//      (학생 도메인 초 = DeductionRecord.atVideoSec — 여기엔 없다). 그래서
//      momentJump/openFullscreenAtRef 배선을 하지 않고, 기준 짝 정직 문구도 띄우지
//      않는다. 짝을 말할 근거가 없는데 말하면 그것이 곧 날조다. 대신 기존 정지 틱
//      (outSec 기반, 출력 시계 안에서는 정확)이 그 순간으로 데려다 준다.
//   3) 기본 배율은 **1.0** 이다. 듀얼 플레이어의 1.35 는 세로 인물 영상을 위해
//      belle 이 승인한 프레이밍이고, 여기 소스는 가로로 나란한 패널 2장이라 같은
//      값을 쓰면 승인된 적 없는 크롭이 된다 (오늘 화면과 픽셀 동일 = 1.0).
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Modal,
  PanResponder,
  Pressable,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
  type LayoutChangeEvent,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { useVideoPlayer, VideoView, type VideoPlayer } from 'expo-video';

import { fetchVisualAssetUrl } from '../lib/api';
import {
  hasSeenFullscreenPinchHint,
  markFullscreenPinchHintSeen,
} from '../lib/coachmark';
import { circledNumberKo } from '../lib/deductionLabels';
import { MIN_ZOOM, type ZoomState } from '../lib/pinchZoom';
import type { RenderedCompareFreeze } from '../types/analysis';
import { colors, radius, spacing, typography } from '../theme';
import { ZoomPinchLayer } from './ZoomPinchLayer';

// 정지 직전 여유 — 틱 탭이 정지 화면이 아니라 그 직전 재생부터 보이게
// (지정 -0.5s — freeze 진입 크로스페이드 0.17s 계열보다 넉넉).
const TICK_JUMP_LEAD_S = 0.5;

// 재생 위치 폴링 — VideoCompare 와 동일 주기(같은 체감 부드러움).
const TICK_INTERVAL_MS = 100;
const THUMB_DIAMETER = 14;
// 가로 전체화면 텍스트 배율 (t0v 관례 — 세로 대비 크게).
const FULLSCREEN_TEXT_SCALE = 1.6;

// belle 09-07 — 이 가지의 확대 출발점·복귀점. 1.0 = 오늘 화면과 픽셀 동일
// (파일 헤더 한계 3 참조 — 듀얼 플레이어의 1.35 를 여기 가져오면 승인된 적 없는
// 크롭이 된다). 팬은 1.0 에서 clampZoom 이 0 으로 강제하므로 오늘과 완전히 같다.
const freshRenderedZoom = (): ZoomState => ({ scale: MIN_ZOOM, tx: 0, ty: 0 });

// 첫 전체화면 진입 안내 pill 자동 소멸 시간(ms). VideoCompare 의 같은 안내와 같은
// 값·같은 문구·같은 1회 플래그(coachmark.ts)를 쓴다 — 사용자에게는 같은 제스처를
// 배우는 한 번의 경험이라, 가지가 둘이라고 두 번 가르치면 안 된다.
const PINCH_HINT_AUTO_DISMISS_MS = 4000;

function fmtTime(s: number): string {
  if (!isFinite(s) || s < 0) return '0:00';
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, '0')}`;
}

// 0.1초 정밀 (belle 기존 요구 "0.0초 단위" 승계).
function fmtTimeDecimal(s: number): string {
  if (!isFinite(s) || s < 0) return '0:00.0';
  const m = Math.floor(s / 60);
  const sec = s - m * 60;
  return `${m}:${sec.toFixed(1).padStart(4, '0')}`;
}

// rid("r00") → 감점 카드 번호(1-base). 계약 §12.3 recordId 콜론 앞 축약이라
// 뒤 숫자가 곧 레코드 인덱스. 형식이 달라지면 번호 없이 마커만 (fail-open).
function freezeNumber(rid: string): number | null {
  const m = /(\d+)\s*$/.exec(rid);
  if (!m) return null;
  const n = Number(m[1]);
  return Number.isFinite(n) ? n + 1 : null;
}

export default function RenderedComparePlayer({
  analysisId,
  onUnavailable,
  freezes,
}: {
  analysisId: string;
  onUnavailable: () => void;
  // doc renderedCompare.freezes — 부재(구버전 doc) = 틱 없이 재생만 (fail-open).
  freezes?: RenderedCompareFreeze[];
}) {
  const [url, setUrl] = useState<string | null>(null);
  const [fullscreen, setFullscreen] = useState(false);
  // onUnavailable 는 보통 인라인 콜백(매 렌더 새 참조)이라 effect deps 에 넣으면
  // 렌더마다 재발급이 돈다 — ref 로 최신 참조만 유지 (deps = analysisId 만).
  const onUnavailableRef = useRef(onUnavailable);
  onUnavailableRef.current = onUnavailable;

  useEffect(() => {
    let cancelled = false;
    setUrl(null); // 분석 전환 시 이전 영상 잔상 방지
    fetchVisualAssetUrl(analysisId, 'renderedCompare')
      .then((playbackUrl) => {
        if (!cancelled) setUrl(playbackUrl);
      })
      .catch((err) => {
        // 404(부재/failed/stale) 포함 전부 폴백 강등 — 조용한 실패 금지.
        if (__DEV__) console.warn('[renderedCompare] URL 발급 실패 — 듀얼 플레이어 강등', err);
        if (!cancelled) onUnavailableRef.current();
      });
    return () => {
      cancelled = true;
    };
  }, [analysisId]);

  // expo-video: 훅은 조건부 호출 불가 — 항상 호출하고 URL 유무로 제어
  // (VideoCompare/ReferenceCornerSection 선례). 음성이 구워져 있으므로 muted
  // 금지 — 이 mp4 의 오디오가 코칭 음성 그 자체다.
  const player = useVideoPlayer(url, (p) => {
    p.loop = false;
  });

  // ── 재생 상태 폴링 (커스텀 컨트롤의 유일한 상태원) ────────────────────────
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  // 드래그 중에는 폴링이 썸을 되돌리지 않게 차단 (VideoCompare scrubbingRef 선례).
  const scrubbingRef = useRef(false);

  useEffect(() => {
    setPlaying(false);
    setCurrentTime(0);
    setDuration(0);
    const id = setInterval(() => {
      try {
        const d = player.duration;
        if (d && d > 0) setDuration(d);
        setPlaying(player.playing);
        if (!scrubbingRef.current) setCurrentTime(player.currentTime ?? 0);
      } catch {
        // player 해제 직후 접근 — 폴링은 다음 tick 에서 정상화 (무해).
      }
    }, TICK_INTERVAL_MS);
    return () => clearInterval(id);
  }, [player]);

  const togglePlay = () => {
    if (player.playing) player.pause();
    else player.play();
  };
  const restart = () => {
    player.currentTime = 0;
    setCurrentTime(0);
    player.play();
  };
  const seekTo = (sec: number) => {
    const clamped = Math.max(0, duration > 0 ? Math.min(sec, duration) : sec);
    player.currentTime = clamped;
    setCurrentTime(clamped);
  };

  // 트랙 드래그 스크럽 — 세로/가로가 각자 폭을 재고(회전 컨테이너라 폭이 다름)
  // 같은 핸들러를 쓴다.
  const trackWidthRef = useRef(0);
  const fsTrackWidthRef = useRef(0);
  const draggingFsRef = useRef(false);
  const onTrackLayout = (e: LayoutChangeEvent) => {
    trackWidthRef.current = e.nativeEvent.layout.width;
  };
  const onFsTrackLayout = (e: LayoutChangeEvent) => {
    fsTrackWidthRef.current = e.nativeEvent.layout.width;
  };

  const panResponder = useMemo(
    () =>
      PanResponder.create({
        onStartShouldSetPanResponder: () => true,
        onMoveShouldSetPanResponder: () => true,
        onPanResponderGrant: (e) => {
          scrubbingRef.current = true;
          const w = draggingFsRef.current
            ? fsTrackWidthRef.current
            : trackWidthRef.current;
          if (w > 0 && duration > 0) {
            seekTo((e.nativeEvent.locationX / w) * duration);
          }
        },
        onPanResponderMove: (e) => {
          const w = draggingFsRef.current
            ? fsTrackWidthRef.current
            : trackWidthRef.current;
          if (w > 0 && duration > 0) {
            const x = Math.max(0, Math.min(w, e.nativeEvent.locationX));
            seekTo((x / w) * duration);
          }
        },
        onPanResponderRelease: () => {
          scrubbingRef.current = false;
        },
        onPanResponderTerminate: () => {
          scrubbingRef.current = false;
        },
      }),
    // duration 이 잡힌 뒤 재생성되어야 초 환산이 유효 (0 이면 no-op).
    [duration],
  );

  // t0v 선례 — 90° 회전 컨테이너 치수 (portrait 고정 앱에서 가로 시뮬레이트,
  // useWindowDimensions = 반응형 hook 값 직접 사용).
  const { width: winW, height: winH } = useWindowDimensions();
  const fsShort = Math.min(winW, winH);
  const fsLong = Math.max(winW, winH);
  const validFreezes = freezes ?? [];

  // ── belle 09-07 손가락 확대 (파일 헤더의 한계 3건과 함께 읽을 것) ────────────
  //
  // 확대 상태는 여기가 소유하고, 배율·팬 수학은 lib/pinchZoom, 제스처 배선은
  // components/ZoomPinchLayer 가 갖는다 (듀얼 플레이어와 같은 3분할 — 사본 0).
  const [zoom, setZoom] = useState<ZoomState>(freshRenderedZoom);
  // ZoomPinchLayer 는 클리핑 박스의 **숫자** 치수를 요구한다(퍼센트 금지 —
  // 90° 회전 absolute 컨테이너 안에서 퍼센트가 축소 렌더된다, t0v 실측). 이 가지의
  // 영상 자리는 컨트롤 높이에 따라 달라져 미리 계산할 수 없으므로 실측한다.
  const [fsBox, setFsBox] = useState({ w: 0, h: 0 });
  const onFsVideoLayout = (e: LayoutChangeEvent) => {
    const { width, height } = e.nativeEvent.layout;
    setFsBox((prev) =>
      prev.w === Math.round(width) && prev.h === Math.round(height)
        ? prev
        : { w: Math.round(width), h: Math.round(height) },
    );
  };
  // 기본 프레이밍에서 벗어났는가 = '원래대로' 노출 조건. 배율 1.0 에서는 팬이
  // clampZoom 에 의해 0 으로 강제되므로 사실상 배율 판정이지만, 판정 문법은
  // 듀얼 플레이어와 같게 둔다(두 곳이 다른 규칙을 갖지 않는다).
  const zoomTouched =
    Math.abs(zoom.scale - MIN_ZOOM) > 0.001 || zoom.tx !== 0 || zoom.ty !== 0;

  // 첫 진입 1회 안내. 낙관적 초기값 true(=이미 봄)라 AsyncStorage 읽기 전에
  // 한 프레임 깜빡이지 않고, 읽기 실패도 true 로 수렴한다(coachmark.ts 계약).
  const [pinchHintSeen, setPinchHintSeen] = useState(true);
  const pinchHintSeenRef = useRef(true);
  pinchHintSeenRef.current = pinchHintSeen;
  const [pinchHintVisible, setPinchHintVisible] = useState(false);
  const pinchHintTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let alive = true;
    hasSeenFullscreenPinchHint()
      .then((seen) => {
        if (alive) setPinchHintSeen(seen);
      })
      .catch(() => {
        /* graceful — 실패 시 초기값 true 유지(안내 미노출) */
      });
    return () => {
      alive = false;
    };
  }, []);
  useEffect(
    () => () => {
      if (pinchHintTimerRef.current) clearTimeout(pinchHintTimerRef.current);
    },
    [],
  );

  // 안내 종료 = 실제 핀치 / 영상 탭 / 4초 경과. 어느 경로든 "봤다"로 기록해 다음
  // 진입부터 뜨지 않는다 (쓰기는 fire-and-forget — coachmark.ts 계약).
  const dismissPinchHint = useCallback(() => {
    if (pinchHintTimerRef.current) {
      clearTimeout(pinchHintTimerRef.current);
      pinchHintTimerRef.current = null;
    }
    setPinchHintVisible(false);
    if (!pinchHintSeenRef.current) {
      pinchHintSeenRef.current = true;
      setPinchHintSeen(true);
      markFullscreenPinchHintSeen();
    }
  }, []);

  const openFullscreen = () => {
    setFullscreen(true);
    if (!pinchHintSeenRef.current) {
      setPinchHintVisible(true);
      if (pinchHintTimerRef.current) clearTimeout(pinchHintTimerRef.current);
      pinchHintTimerRef.current = setTimeout(() => {
        pinchHintTimerRef.current = null;
        dismissPinchHint();
      }, PINCH_HINT_AUTO_DISMISS_MS);
    }
  };
  const closeFullscreen = () => {
    setFullscreen(false);
    // 닫으면 기본 프레이밍으로 복귀 — 다음에 열었을 때 지난번 확대가 남아 있으면
    // "왜 이렇게 크게 나오지"가 된다 (듀얼 플레이어 closeFullscreen 과 같은 처분).
    setZoom(freshRenderedZoom());
    if (pinchHintTimerRef.current) {
      clearTimeout(pinchHintTimerRef.current);
      pinchHintTimerRef.current = null;
    }
    setPinchHintVisible(false);
  };
  const progressPct =
    duration > 0 ? Math.max(0, Math.min(100, (currentTime / duration) * 100)) : 0;

  // 컨트롤 공유 (t0v renderControls(dark) 선례 — 로직 중복 0). dark=true 는
  // 가로 전체화면: 어두운 배경 위 색·배율만 토큰 분기.
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
      <View style={styles.timeline}>
        {/* 정지 틱 — 트랙 위 별도 줄. 번호는 감점 카드 번호와 같은 문법(①②③)
            이라 "몇 번 지적이 여기서 멈춘다"가 읽힌다. 탭 = 정지 직전으로 이동. */}
        {validFreezes.length > 0 && duration > 0 && (
          <View style={styles.tickRow} pointerEvents="box-none">
            {validFreezes.map((f) => {
              const leftPct = Math.max(0, Math.min(100, (f.outSec / duration) * 100));
              const n = freezeNumber(f.rid);
              return (
                <Pressable
                  key={f.rid}
                  onPress={() => seekTo(Math.max(0, f.outSec - TICK_JUMP_LEAD_S))}
                  accessibilityRole="button"
                  accessibilityLabel={
                    n != null
                      ? `${n}번 지적 지점으로 이동`
                      : '지적 지점으로 이동'
                  }
                  hitSlop={8}
                  style={[styles.tick, { left: `${leftPct}%` }]}
                >
                  {n != null && (
                    <Text style={styles.tickLabel} numberOfLines={1}>
                      {circledNumberKo(n)}
                    </Text>
                  )}
                  <View style={styles.tickMark} />
                </Pressable>
              );
            })}
          </View>
        )}
        <View
          style={styles.timelineTrack}
          onLayout={dark ? onFsTrackLayout : onTrackLayout}
          onTouchStart={() => {
            draggingFsRef.current = dark;
          }}
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
        <Text style={[styles.timeText, dark && styles.timeTextDark]} numberOfLines={1}>
          {`${fmtTimeDecimal(currentTime)} / ${fmtTime(duration)}`}
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

  return (
    <View>
      <View style={styles.frame}>
        {url ? (
          <>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="재생 또는 일시정지"
              onPress={togglePlay}
            >
              <VideoView
                player={player}
                style={styles.video}
                // 두 패널 합성 mp4 — 오버레이·동기 로직 없이 재생만.
                // nativeControls=false: 자동 숨김 컨트롤이 아래 커스텀 컨트롤과
                // 이중으로 겹쳐 "조작 UI가 이상하다"의 원인이었다 (260809-jnb).
                nativeControls={false}
                contentFit="contain"
                allowsPictureInPicture={false}
                accessibilityLabel="동작 비교 영상"
              />
            </Pressable>
            {/* 가로 크게 보기 진입 — 카드 우상단 (t0v 진입 버튼 관례) */}
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="가로로 크게 보기"
              hitSlop={10}
              onPress={openFullscreen}
              style={styles.expandBtn}
            >
              <Ionicons name="expand" size={16} color={colors.textWhite} />
            </Pressable>
          </>
        ) : (
          <View style={styles.placeholder}>
            <Text style={styles.placeholderText}>비교 영상을 불러오고 있어요</Text>
          </View>
        )}
      </View>
      {url ? <View style={styles.controlsWrap}>{renderControls(false)}</View> : null}

      {/* 가로 전체화면 — 260702-t0v 90° 회전 Modal 패턴 (portrait 고정 유지).
          같은 player 인스턴스에 두 번째 VideoView attach — 재생 위치·상태 공유
          (동기 로직 0). 탭 = 재생/일시정지 토글, 우상단 닫기, 하단 컨트롤 공유.
          belle 09-07 — 영상 표면은 ZoomPinchLayer 가 감싼다(손가락 확대 + 탭 멈춤). */}
      <Modal
        visible={fullscreen}
        animationType="fade"
        statusBarTranslucent
        supportedOrientations={['portrait']}
        onRequestClose={closeFullscreen}
      >
        <StatusBar hidden />
        <View style={styles.fsRoot}>
          <View
            style={[
              styles.fsRotated,
              {
                width: fsLong,
                height: fsShort,
                left: (fsShort - fsLong) / 2,
                top: (fsLong - fsShort) / 2,
              },
            ]}
          >
            {/* 종전의 Pressable 래퍼는 걷어냈다 — 같은 표면이 핀치·팬도 받아야
                하는데 Pressable 과 PanResponder 가 responder 를 두고 다투면 확대
                도중 탭이 끼어들어 재생이 토글된다. 탭 멈춤은 ZoomPinchLayer 의
                onTap(움직이지 않은 짧은 접촉)으로 옮겼고, 보조기술용 재생/일시정지
                버튼은 아래 fsControls 안에 accessibilityRole="button" 으로 이미
                따로 있다(중복 표면을 잃은 것이지 기능을 잃은 것이 아니다). */}
            <View style={styles.fsVideoWrap} onLayout={onFsVideoLayout}>
              {fsBox.w > 0 && fsBox.h > 0 ? (
                <ZoomPinchLayer
                  boxW={fsBox.w}
                  boxH={fsBox.h}
                  state={zoom}
                  onChange={setZoom}
                  onTap={() => {
                    dismissPinchHint();
                    togglePlay();
                  }}
                  onPinchStart={dismissPinchHint}
                  style={styles.fsVideoBox}
                  accessibilityLabel="재생 또는 일시정지"
                >
                  <VideoView
                    player={player}
                    style={styles.fsVideo}
                    contentFit="contain"
                    nativeControls={false}
                    // allowsFullscreen 은 expo-video 에서 deprecated(경고 발생)이고,
                    // nativeControls=false 면 전체화면 진입 UI 자체가 없어 무의미하다.
                    allowsPictureInPicture={false}
                    accessibilityLabel="동작 비교 영상 (가로)"
                  />
                </ZoomPinchLayer>
              ) : null}
            </View>
            <View style={styles.fsControls}>{renderControls(true)}</View>
            {/* belle 09-07 — 첫 진입 1회 안내. 손가락 확대는 화면에 단서가 없는
                제스처라 처음 한 번은 말해 준다. 핀치·탭·4초 중 무엇이든 오면
                사라지고 다시 뜨지 않는다(듀얼 플레이어와 같은 1회 플래그). */}
            {pinchHintVisible ? (
              <View style={styles.fsPinchHintWrap} pointerEvents="box-none">
                <Pressable
                  onPress={dismissPinchHint}
                  accessibilityRole="button"
                  accessibilityLabel="확대 안내 닫기"
                  hitSlop={8}
                  style={styles.fsPinchHintPill}
                >
                  <Ionicons name="resize" size={12} color={colors.textWhite} />
                  <Text style={styles.fsPinchHintText}>
                    두 손가락으로 벌리면 크게 보여요
                  </Text>
                </Pressable>
              </View>
            ) : null}
            {/* belle 09-07 — 벌린 뒤 원래 프레이밍(1.0)으로 되돌리는 길. 닫기
                버튼 왼쪽에 두어 우상단 두 손잡이가 겹치지 않는다. */}
            {zoomTouched ? (
              <Pressable
                onPress={() => setZoom(freshRenderedZoom())}
                accessibilityRole="button"
                accessibilityLabel="확대 원래대로"
                hitSlop={8}
                style={styles.fsZoomResetPill}
              >
                <Ionicons name="contract" size={12} color={colors.textWhite} />
                <Text style={styles.fsZoomResetText}>원래대로</Text>
              </Pressable>
            ) : null}
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="가로 보기 닫기"
              hitSlop={12}
              onPress={closeFullscreen}
              style={styles.fsCloseBtn}
            >
              <Ionicons name="close" size={22} color={colors.textWhite} />
            </Pressable>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  frame: {
    width: '100%',
    borderRadius: radius.card,
    overflow: 'hidden',
    // 영상 카드 배경 — design.md §5-1 다크 예외 토큰 (영상 콘텐츠 자체의 어두움).
    backgroundColor: colors.videoBg,
  },
  video: {
    width: '100%',
    // 렌더러 출력 = 세로 패널 2장 나란히 (PANEL_H 1080, 파일럿 세로 영상 기준
    // 약 1224x1080). 비율이 다른 소스는 contain 이 videoBg 위에 레터박스.
    aspectRatio: 1224 / 1080,
  },
  expandBtn: {
    position: 'absolute',
    top: 8,
    right: 8,
    padding: 6,
    borderRadius: radius.listItem,
    backgroundColor: colors.brandOverlay,
  },
  placeholder: {
    width: '100%',
    aspectRatio: 1224 / 1080,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.cardPadding,
  },
  placeholderText: {
    ...typography.caption,
    color: colors.textWhite,
    textAlign: 'center',
  },
  // ── 컨트롤 (VideoCompare 세트 이식 — 정렬 미세조정 버튼만 제외) ────────────
  controlsWrap: {
    paddingTop: 10,
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
  timeline: {
    flex: 1,
    gap: 6,
  },
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
  timeTextDark: {
    color: colors.textWhite,
    fontSize: typography.captionSmall.fontSize * FULLSCREEN_TEXT_SCALE,
    lineHeight: typography.captionSmall.fontSize * FULLSCREEN_TEXT_SCALE * 1.3,
  },
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
  // ── 가로 전체화면 (t0v 90° 회전 패턴) ──────────────────────────────────
  fsRoot: {
    flex: 1,
    backgroundColor: colors.videoBg,
  },
  fsRotated: {
    position: 'absolute',
    transform: [{ rotate: '90deg' }],
    paddingVertical: 6,
  },
  fsVideoWrap: {
    flex: 1,
  },
  // belle 09-07 — ZoomPinchLayer 의 클리핑 래퍼에 얹는 배경. overflow:'hidden' 은
  // 레이어가 갖고 있으므로 여기서 덮지 않는다 (색만 호출측 몫 — 그 파일에 색 0).
  fsVideoBox: {
    backgroundColor: colors.videoBg,
  },
  fsVideo: {
    // 확대 박스(ZoomPinchLayer 내부 absolute, 숫자 치수)를 채운다 — 퍼센트의
    // 기준이 그 숫자 박스라 회전 컨테이너의 퍼센트 축소 함정에 걸리지 않는다.
    width: '100%',
    height: '100%',
  },
  // belle 09-07 — 첫 진입 안내 pill / '원래대로' pill. 문법은 듀얼 플레이어와
  // 동일(videoBg + textWhite + radius.button + Ionicons — 신규 색 0).
  fsPinchHintWrap: {
    position: 'absolute',
    top: 56,
    left: 0,
    right: 0,
    alignItems: 'center',
  },
  fsPinchHintPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: radius.button,
    backgroundColor: colors.videoBg,
  },
  fsPinchHintText: {
    ...typography.captionSmall,
    fontSize: typography.captionSmall.fontSize * FULLSCREEN_TEXT_SCALE,
    color: colors.textWhite,
    fontWeight: '700',
  },
  fsZoomResetPill: {
    position: 'absolute',
    top: 10,
    // 닫기 버튼(right 12, padding 8 × 2 + icon 22 = 38) 왼쪽에 8 간격으로.
    right: 12 + 38 + 8,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: radius.button,
    backgroundColor: colors.videoBg,
  },
  fsZoomResetText: {
    ...typography.captionSmall,
    fontSize: typography.captionSmall.fontSize * FULLSCREEN_TEXT_SCALE,
    color: colors.textWhite,
    fontWeight: '700',
  },
  fsControls: {
    paddingHorizontal: 16,
    paddingTop: 6,
  },
  fsCloseBtn: {
    position: 'absolute',
    top: 10,
    right: 12,
    padding: 8,
    borderRadius: radius.listItem,
    backgroundColor: colors.brandOverlay,
  },
});

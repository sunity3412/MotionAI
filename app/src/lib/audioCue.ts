// 재생 중 큐 오디오 어댑터 (D-18 B안 — AWS Polly 사전합성 mp3 재생, 32-12).
//
// 확정 방식 = 32-GATE-DECISIONS §샘플 게이트 "① 오디오 (D-18) = B안 (클라우드 TTS,
// AWS Polly neural)". 백엔드(32-16)가 분석 **사후** 스테이지에서 records 의 cueLine
// (승인 문구집 골격 — D-09 무수치)을 Polly 로 사전 합성해 S3 에 저장하고
// result.coachAudio.items[{recordId, key}] 로 도착시킨다. 이 어댑터는 그 mp3 를
// 재생만 한다 (합성·저장·계약은 32-16 소유 — 이 파일은 소비만).
//
// 설계 (리뷰 반영):
//   - cue 객체 시그니처(text 단독 금지) — cueId=recordId 로 mp3 를 조인한다.
//   - prefetchCueAudio 가 화면 진입 시 cueId 별 playback-url presigned URL 을 일괄
//     발급받아 메모리 캐시(재생 시점 네트워크 0 — 자막·음성 동기 어긋남 방지).
//   - speakCue 는 캐시된 cueId URL 을 재생. 새 큐 = 이전 발화 자동 중단(replace).
//   - 설정 게이트: '@sunity:audio_cue_enabled' (AsyncStorage). **기본 off** — 학원
//     소음 환경. off 이면 자막만(graceful — 분석·자막 무영향).
//   - 합성 실패(coachAudio.status='failed')·미조인 cueId·재서명 실패는 전부 조용한
//     폴백(자막만). 오디오는 보조 채널 — 어떤 실패도 재생 흐름을 막지 않는다.
//
// 순수 재생 어댑터(비 React) — expo-audio createAudioPlayer 의 명령형 API 를 쓴다
// (useAudioPlayer 훅은 컴포넌트 전용). 단일 모듈 플레이어를 재사용(replace)해 리소스
// 를 아낀다. coachmark.ts 의 AsyncStorage 플래그 관례(@sunity: prefix)와 정합.

import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  createAudioPlayer,
  setAudioModeAsync,
  type AudioPlayer,
} from 'expo-audio';
import { fetchCoachAudioUrl } from './api';

// @sunity: prefix 필수 — Firebase Auth backing store 와 namespace 충돌 회피
// (coachmark.ts / result.tsx '@sunity:keypoint_overlay_enabled' 선례와 정합).
const AUDIO_CUE_ENABLED_KEY = '@sunity:audio_cue_enabled';

/**
 * 재생 큐 (cueTrack.CueWindow 파생). cueId=recordId(§12.3) — mp3 조인 키.
 * cueId 가 null 이면 오디오 조인 불가(자막만). text 는 로그/폴백용.
 */
export type Cue = { cueId: string | null; text: string };

// 설정 상태 — 동기 조회(isAudioCueEnabled)를 위해 메모리 미러. AsyncStorage 는 비동기라
// VideoCompare 의 tick(100ms 폴링 클로저)에서 await 불가 → 캐시로 노출한다.
let enabled = false;
let hydrated = false;

// cueId → presigned mp3 URL (prefetch 산출). 재생 시점 네트워크 0.
const urlCache = new Map<string, string>();

// 단일 재생 플레이어(lazy). 새 큐 = replace → 이전 발화 자동 중단.
let player: AudioPlayer | null = null;
let playingCueId: string | null = null;

// 33-13 (A-6, D-13 대표 UX) — 발화 진행 플래그. speakCue 성공 시 true,
// didJustFinish 이벤트/stopCue 에서 false. VideoCompare 의 기존 100ms tick 이
// isCueSpeaking() 폴링으로 "음성 끝 → 영상 재개"를 판정한다 (신규 타이머 0).
// player.playing 단독 판정은 mp3 버퍼링 중 false 라 즉시 재개 오판 — 이벤트
// 기반 플래그가 로딩 구간을 관통해 유지된다.
let speechActive = false;
let statusListenerAttached = false;

// didJustFinish 구독 1회 부착 (player 인스턴스 재사용·replace 에도 유지).
function attachStatusListener(): void {
  if (statusListenerAttached || !player) return;
  statusListenerAttached = true;
  player.addListener('playbackStatusUpdate', (status) => {
    if (status.didJustFinish) {
      speechActive = false;
      playingCueId = null;
    }
  });
}

/** 발화 진행 중 여부 (버퍼링 포함). VideoCompare tick 의 재개 판정 소비. */
export function isCueSpeaking(): boolean {
  return speechActive;
}

// 설정값을 AsyncStorage 에서 메모리 캐시로 로드 + 오디오 세션 1회 설정. graceful:
// 읽기 실패 시 off(기본값)로 둔다 — 오류가 원치 않는 발화를 만들면 안 되므로 조용히
// 꺼지는 방향으로 실패한다. 여러 번 호출해도 1회만 실효(hydrated 가드).
async function hydrate(): Promise<void> {
  if (hydrated) return;
  hydrated = true;
  try {
    const v = await AsyncStorage.getItem(AUDIO_CUE_ENABLED_KEY);
    enabled = v === 'true';
  } catch {
    enabled = false;
  }
  // 무음 모드에서도 코치 큐가 들리게(playsInSilentMode) + 다른 앱 오디오는 잠깐
  // 볼륨만 낮춤(duckOthers — 큐는 짧은 안내). 실패는 무해화(권한/플랫폼 편차).
  setAudioModeAsync({
    playsInSilentMode: true,
    interruptionMode: 'duckOthers',
  }).catch(() => {
    /* graceful — 오디오 세션 설정 실패해도 재생 시도는 유지 */
  });
}

/** 오디오 큐 on/off (동기 — tick 에서 즉시 판정). 캐시 미로드 시 기본 off. */
export function isAudioCueEnabled(): boolean {
  return enabled;
}

/**
 * 오디오 큐 on/off 설정 + 영속화. off 로 바꾸면 진행 중 발화를 즉시 멈춘다.
 * fire-and-forget 영속화 — 실패해도 현재 세션 상태는 이미 반영(다음 실행에 재적용될 뿐).
 * 최초 hydrate 전에 호출돼도 hydrated 를 세워 이후 로드가 사용자 선택을 덮지 않게 한다.
 */
export async function setAudioCueEnabled(next: boolean): Promise<void> {
  enabled = next;
  hydrated = true;
  if (!next) stopCue();
  try {
    await AsyncStorage.setItem(AUDIO_CUE_ENABLED_KEY, next ? 'true' : 'false');
  } catch {
    /* graceful — 영속화 실패는 흐름 차단 금지 */
  }
}

/**
 * 화면 진입 시 cueId 별 mp3 재생 URL 을 일괄 prefetch → 메모리 캐시. 재생 시점
 * 네트워크 지연으로 자막·음성이 어긋나지 않게 한다(리뷰 반영). 설정 hydrate 를
 * 겸한다 — 최초 호출이 영속 설정값을 캐시로 올린다(VideoCompare 마운트에서 이 완료
 * 후 isAudioCueEnabled() 로 토글 초기값을 읽는다).
 *
 * off 이면 네트워크 0(학원 소음 기본 off — 불필요 발급 억제). cueId 가 null 인 큐,
 * 이미 캐시된 cueId 는 스킵. 개별 발급 실패는 조용히 건너뜀(자막만 — graceful).
 *
 * 플랜 시그니처(cues 만)를 analysisId 동반으로 확장: B안 재서명은 analysisId 로만
 * 서버가 canonical key 를 구성하므로 필수 (Rule 3 — 확정 B안에서 시그니처 보정).
 */
export async function prefetchCueAudio(
  analysisId: string,
  cues: readonly Cue[],
): Promise<void> {
  await hydrate();
  if (!enabled) return;
  const ids = Array.from(
    new Set(
      cues
        .map((c) => c.cueId)
        .filter((id): id is string => !!id && !urlCache.has(id)),
    ),
  );
  await Promise.all(
    ids.map((recordId) =>
      fetchCoachAudioUrl(analysisId, recordId)
        .then((url) => {
          urlCache.set(recordId, url);
        })
        .catch(() => {
          /* 조용한 폴백 — 이 cueId 는 자막만 (분석/자막 무영향) */
        }),
    ),
  );
}

/**
 * 큐 발화. 설정 on + cueId 조인 + prefetch 캐시 히트일 때만 재생한다. 새 큐는
 * replace 로 이전 발화를 자동 중단(리뷰 — 이전 발화 stop). 같은 cueId 재요청은
 * 무시(중복 재시작 stutter 방지 — tick 은 큐 전환 시에만 호출하나 방어).
 * 캐시 미스(prefetch 실패/미조인)는 no-op(자막만).
 *
 * 33-13 — 발화 시작 여부 boolean 반환. VideoCompare 가 true 일 때만 영상을
 * 일시정지한다(대표 UX 패턴) — 캐시 미스/미조인 큐(false)는 자막만이라 멈춤도
 * 없다 (짝 없는 큐 미발동, D-18 고아 가드).
 */
export function speakCue(cue: Cue): boolean {
  if (!enabled) return false;
  const id = cue.cueId;
  if (!id) return false;
  const url = urlCache.get(id);
  if (!url) return false; // 미조인/미prefetch → 자막만
  if (playingCueId === id && player?.playing) return true;
  try {
    if (!player) {
      player = createAudioPlayer(url);
    } else {
      player.replace(url); // 이전 발화 중단 + 새 소스
    }
    attachStatusListener();
    playingCueId = id;
    speechActive = true;
    player.play();
    return true;
  } catch {
    // released/플랫폼 예외 — 무해화(자막만). 다음 큐에서 재시도.
    playingCueId = null;
    speechActive = false;
    return false;
  }
}

/** 발화 중단 (일시정지·seek·언마운트·off 전환 시). 리소스는 유지(재사용). */
export function stopCue(): void {
  playingCueId = null;
  speechActive = false;
  if (!player) return;
  try {
    if (player.playing) player.pause();
  } catch {
    /* released object — 무해 */
  }
}

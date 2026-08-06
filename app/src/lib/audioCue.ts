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
//   - speakCue 는 캐시된 cueId URL 을 재생. 새 큐 = 이전 플레이어 해제 + 새 플레이어
//     발급(quick-260806-wj3) → 이전 발화 중단은 그대로 성립.
//   - 설정 게이트: '@sunity:audio_cue_enabled' (AsyncStorage). **기본 off** — 학원
//     소음 환경. off 이면 자막만(graceful — 분석·자막 무영향).
//   - 합성 실패(coachAudio.status='failed')·미조인 cueId·재서명 실패는 전부 조용한
//     폴백(자막만). 오디오는 보조 채널 — 어떤 실패도 재생 흐름을 막지 않는다.
//
// 순수 재생 어댑터(비 React) — expo-audio createAudioPlayer 의 명령형 API 를 쓴다
// (useAudioPlayer 훅은 컴포넌트 전용).
//
// quick-260806-wj3 — **큐마다 플레이어를 새로 만든다.** 종전 전제였던 "단일 모듈
// 플레이어를 재사용해 리소스를 아낀다"는 이 수리로 철회됐다: 리소스 절약보다
// **아이템 정합**이 우선이다. 스테일 아이템 재재생 = 자막과 다른 음성 = 신뢰 파괴
// (belle 실기기 ① — 큐2 자막에 큐1 음성이 처음부터 다시 났다). 아이템 정합을 지키는
// 값이 플레이어 객체 몇 개보다 비싸다. quick-260801-f77 의 세대(seq) 무효화 설계는
// 그대로 유지된다 — 이번에 철회되는 것은 플레이어 재사용 전제 하나뿐이다.
//
// coachmark.ts 의 AsyncStorage 플래그 관례(@sunity: prefix)와 정합.

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

// cueId → presigned mp3 URL + 만료 시각 (prefetch 산출). 재생 시점 네트워크 0.
//
// quick-260801-f77 — 종전에는 `Map<string, string>` 이라 만료 개념이 없었고 어디서도
// 비워지지 않았다. presigned URL 수명은 1시간(playback-url `_ASSET_EXPIRES = 3600`)이라
// 앱을 오래 띄워두면 죽은 URL 을 계속 재생 시도했다. 캐시를 없애지는 않는다 —
// "재생 시점 네트워크 0 → 자막·음성 동기 유지"가 이 캐시의 존재 이유이기 때문이다
// (아래 prefetchCueAudio 주석). 만료를 인지하게 고칠 뿐이다.
type CachedAudio = { url: string; expiresAtMs: number };
const urlCache = new Map<string, CachedAudio>();

// 만료 여유. 경계에서 발화 도중 URL 이 죽으면 안 되므로 2분을 미리 깎는다.
// prefetch 와 실제 발화 사이 간격은 사용자의 화면 체류 시간만큼 벌어질 수 있고,
// 기기 시계 오차(서버 기준 만료 vs Date.now())도 이 여유가 흡수한다.
const URL_EXPIRY_MARGIN_MS = 120_000;

// 캐시가 어느 분석의 것인지. recordId 는 `r{index:02d}:{criterion}` (contract.md §12.3)
// 이라 **분석 간 고유하지 않다** — `r00:...` 는 대부분의 분석에 존재한다. 무효화가
// 없으면 결과 A 를 본 뒤 결과 B 를 열었을 때 A 의 mp3 가 재생된다.
let cachedAnalysisId: string | null = null;

/**
 * 캐시 엔트리가 지금 써도 되는가. **만료 판정은 이 함수에만 둔다** — prefetch 와
 * speakCue 가 각자 경계식을 들고 있으면 한쪽만 고쳐지는 사고가 난다.
 * 타입 술어로 둬서 통과 후 `entry.url` 접근에 non-null 단언이 필요 없게 한다.
 */
function isFresh(
  entry: CachedAudio | undefined,
  nowMs: number,
): entry is CachedAudio {
  return !!entry && entry.expiresAtMs - URL_EXPIRY_MARGIN_MS > nowMs;
}

// 현재 발화 중인 큐의 플레이어. **큐 1개당 1개** — 새 큐는 activatePlayer 가
// 이전 것을 해제하고 새로 만든다(quick-260806-wj3). null = 발화 아이템 없음.
let player: AudioPlayer | null = null;
let playingCueId: string | null = null;

// 33-13 (A-6, D-13 대표 UX) — 발화 진행 플래그. speakCue 성공 시 true,
// didJustFinish 이벤트/stopCue 에서 false. VideoCompare 의 기존 100ms tick 이
// isCueSpeaking() 폴링으로 "음성 끝 → 영상 재개"를 판정한다 (신규 타이머 0).
// player.playing 단독 판정은 mp3 버퍼링 중 false 라 즉시 재개 오판 — 이벤트
// 기반 플래그가 로딩 구간을 관통해 유지된다.
let speechActive = false;
let statusListenerAttached = false;

// ── quick-260801-f77 결함 B·C — 로드 실패 감시(watchdog) ────────────────────────
//
// expo-audio 는 로드 **실패**를 알려주지 않는다. `AudioStatus` 에 error 필드가 없고
// (`expo-audio/build/Audio.types.d.ts`), 네이티브 `setupPublisher()` 는
// `currentItem?.status == .readyToPlay` 일 때만 이벤트를 쏘며 `.failed` 는 조용히
// return 한다. 종료 알림은 `AVPlayerItemDidPlayToEndTime` 전용이라 실패 시 오지
// 않고, time observer 도 재생 시각이 전진해야 발화한다. 즉 **실패는 이벤트로 관측
// 불가**하고 오직 "성공 신호의 부재"로만 판정된다 → 감시 타이머가 유일한 수단이다.
// 성공 신호로는 `isLoaded`(= `currentItem?.status == .readyToPlay`, 아이템 단위)만
// 쓴다. `playbackState` 는 아이템이 아니라 **플레이어** 상태 문자열이라 개별 mp3 의
// 403 을 잡지 못한다 — 실패 판정에 쓰지 말 것.
//
// 3000ms 의 근거는 상한에서 역산한 값이다: 최대 2회 시도(최초 + 재시도 1회)
// × 3000ms = 감시 6000ms + 재발급 왕복 1회. VideoCompare 의 안전망
// `CUE_PAUSE_MAX_MS`(15000ms)보다 확실히 짧아야 우리 복구가 안전망보다 먼저
// 작동하는데, 재발급이 9초를 넘게 끌지 않는 한 성립한다. (그 경우엔 fetch 가 아직
// 매달려 있어 우리 콜백이 못 깨어나므로 종전처럼 15초 안전망이 받는다 — 악화 없음.)
// URL 은 prefetch 로 이미 확보돼 있고 큐 mp3 는 수 초 분량이라 정상 경로는 1초 내
// isLoaded — 3초는 학원 wifi 여유분이다.
const SPEECH_LOAD_TIMEOUT_MS = 3000;

// 재발급 재시도 상한. 무한 재발급 루프 금지 (T-f77-01 자해 DoS).
const MAX_SPEECH_RETRY = 1;

// 발화 세대 번호. speakCue 진입·stopCue 에서 증가한다. 지연 콜백(감시 타이머·재발급
// 응답)이 **자기 세대가 아직 유효할 때만** 상태를 건드리게 하는 유일한 장치 —
// 큐 B 가 큐 A 를 밀어낸 뒤 A 의 타이머가 깨어나 B 를 죽이는 사고를 막는다.
let speechSeq = 0;
let loadWatchdog: ReturnType<typeof setTimeout> | null = null;

// 현재 발화에 한정된 재시도 소모량. speakCue 진입에서만 0 으로 리셋한다 —
// 그래야 큐 하나가 실패해도 다음 큐가 온전한 예산을 받는다.
let speechRetryCount = 0;

function clearLoadWatchdog(): void {
  if (loadWatchdog !== null) {
    clearTimeout(loadWatchdog);
    loadWatchdog = null;
  }
}

/** 플레이어 정지 (released 객체·플랫폼 예외 무해화). stopCue 기존 로직과 동일. */
function pausePlayerSafely(): void {
  try {
    if (player?.playing) player.pause();
  } catch {
    /* released object — 무해 */
  }
}

/**
 * 플레이어 해제 — 재생 아이템의 **유일한 소멸 경로** (quick-260806-wj3, belle ①).
 *
 * 왜 필요한가: 종전에는 플레이어를 재사용하며 소스만 갈아끼웠는데(replace), 이번
 * 큐의 URL 로드가 실패하면 플레이어에는 **이전 큐의 아이템**이 그대로 남고 직후
 * play() 가 그 끝난 아이템을 처음부터 되돌린다. 아이템을 물려주지 않고 통째로
 * 버리면 그 경로 자체가 사라진다.
 *
 * `player = null` 을 **먼저** 세우는 이유: 아래 pause/remove 가 던지더라도 죽은
 * 참조가 모듈에 남지 않게 하기 위해서다(재진입 안전). teardown 은 expo-audio 가
 * 문서화한 `remove()`("Remove the player from memory to free up resources",
 * AudioModule.types.d.ts:176)를 쓴다 — base 의 release() 가 아니다.
 */
function releasePlayer(): void {
  const p = player;
  player = null;
  // 리스너는 플레이어에 붙어 있으므로 플레이어와 수명을 같이한다.
  statusListenerAttached = false;
  if (!p) return;
  try {
    if (p.playing) p.pause();
  } catch {
    /* released object — 무해 */
  }
  try {
    p.remove();
  } catch {
    /* released object·플랫폼 예외 — 무해 */
  }
}

/**
 * 이번 큐 전용 플레이어 발급 — **재생 아이템의 유일한 출생지** (quick-260806-wj3).
 *
 * 모든 재생 아이템이 `createAudioPlayer(url)` 로만 태어나면, 요청한 URL 이 아닌
 * 아이템이 플레이어에 존재할 수 있는 상태 자체가 없다. 그래서 로드 실패의 결과가
 * 구조적으로 무음(자막만)으로 고정된다 — fail-closed. "남의 음성"은 replace 라는
 * 단 하나의 벡터로만 들어왔고, 그 벡터를 없앤 것이 이 수리의 전부다.
 *
 * 반환값을 쓰는 이유는 TS 좁히기다. 호출부가 `player?.play()` 로 옵셔널 체이닝하면
 * "실은 null 이라 아무 일도 일어나지 않음"이 조용히 통과하므로 `p.play()` 로 못 박는다.
 */
function activatePlayer(url: string): AudioPlayer {
  releasePlayer();
  const p = createAudioPlayer(url);
  player = p;
  attachStatusListener();
  return p;
}

/**
 * 복구 불가 판정 — 결함 C 의 수리 본체.
 *
 * `speechActive = false` 가 핵심이다. VideoCompare 는 이미 100ms tick 으로
 * `isCueSpeaking()` 을 폴링하며 재개를 판정하므로(`VideoCompare.tsx` 재개 블록),
 * 이 플래그를 정직하게 내려주기만 하면 **다음 tick 에** 양쪽 영상이 재개된다.
 * 그래서 이 수리에서 VideoCompare 는 한 줄도 바뀌지 않는다.
 *
 * `pausePlayerSafely()` 를 같이 부르는 이유: 뒤늦게(예: 10초 뒤) 로드가 성공하면
 * 이미 재개된 영상 위로 음성이 튀어나온다.
 */
function failSpeech(seq: number): void {
  if (seq !== speechSeq) return; // 만료된 세대의 지연 콜백 — 무시
  clearLoadWatchdog();
  playingCueId = null;
  speechActive = false;
  pausePlayerSafely();
}

function armLoadWatchdog(seq: number): void {
  clearLoadWatchdog();
  loadWatchdog = setTimeout(() => onLoadTimeout(seq), SPEECH_LOAD_TIMEOUT_MS);
}

/**
 * 감시 만료 — 정해진 시간 안에 isLoaded 가 오지 않았다. 1회까지 URL 을 재발급해
 * 다시 시도하고, 예산을 다 쓰면 발화를 포기해 영상을 풀어준다.
 */
function onLoadTimeout(seq: number): void {
  if (seq !== speechSeq) return;
  // 오탐 방지 — 이벤트를 놓쳤을 뿐 로드는 됐을 수 있다. 실시간 프로퍼티로 재확인한다.
  if (player?.isLoaded) {
    clearLoadWatchdog();
    return;
  }
  const recordId = playingCueId;
  if (speechRetryCount >= MAX_SPEECH_RETRY || !recordId) {
    failSpeech(seq);
    return;
  }
  speechRetryCount += 1;
  urlCache.delete(recordId); // 죽은 엔트리 축출 — 재발급으로만 되살린다
  try {
    void reissue(recordId)
      .then((entry) => {
        if (seq !== speechSeq) return; // 그 사이 다른 큐/정지로 세대가 넘어감
        if (!entry) {
          failSpeech(seq);
          return;
        }
        try {
          // quick-260806-wj3 — 재발급에도 같은 규칙을 적용한다. 같은 큐라도 이
          // 시점의 플레이어에는 **로드에 실패한 아이템**이 들어 있으므로 물려받지
          // 않는다(= belle ① 의 벡터가 여기에도 있었다).
          const p = activatePlayer(entry.url);
          declareAudioMode();
          p.play();
          armLoadWatchdog(seq); // 재시도분 감시를 다시 건다
        } catch {
          // presigned URL 은 로그·에러 메시지에 싣지 않는다 (T-f77-02).
          failSpeech(seq);
        }
      })
      // reissue 는 스스로 삼키지만, then 콜백의 예상 못 한 throw 까지 여기서 막는다.
      // 미처리 rejection 하나가 발화 플래그를 true 로 남기면 영상이 다시 갇힌다.
      .catch(() => {
        failSpeech(seq);
      });
  } catch {
    failSpeech(seq);
  }
}
// ───────────────────────────────────────────────────────────────────────────────

// 상태 구독 부착. 플레이어가 큐마다 새로 태어나므로(quick-260806-wj3 activatePlayer)
// 부착도 **플레이어 1개당 1회**다 — 플래그는 releasePlayer 가 함께 내린다.
function attachStatusListener(): void {
  if (statusListenerAttached || !player) return;
  statusListenerAttached = true;
  player.addListener('playbackStatusUpdate', (status) => {
    if (status.didJustFinish) {
      clearLoadWatchdog();
      speechActive = false;
      playingCueId = null;
      // quick-260806-wj3 — 여기서 releasePlayer() 를 부르지 않는 이유:
      // (a) 네이티브 이벤트 콜백 안에서 공유 객체를 해제하는 재진입을 피한다,
      // (b) 다음 발화가 어차피 activatePlayer 로 이전 플레이어를 해제하고,
      // (c) 큐 종료 시 VideoCompare 가 stopCue() 를 부르는 경로도 있어 메모리는
      //     실제로 회수된다.
      // 끝난 아이템이 잠시 남아도 그것이 재생될 경로는 없다 — 다음 재생은 반드시
      // 새 플레이어에서 일어나기 때문이다(출생지가 activatePlayer 하나).
    }
    // 로드 확인 = 403 계열 실패가 배제됨 → 감시를 내린다. 로드 후 중간 정지(stall)는
    // VideoCompare 의 CUE_PAUSE_MAX_MS 안전망이 계속 담당한다(그 상수 무변경).
    if (status.isLoaded) clearLoadWatchdog();
  });
}

/** 발화 진행 중 여부 (버퍼링 포함). VideoCompare tick 의 재개 판정 소비. */
export function isCueSpeaking(): boolean {
  return speechActive;
}

/**
 * 오디오 모드 선언 — 무음 모드에서도 코치 큐가 들리게(playsInSilentMode) + 다른 앱
 * 오디오는 잠깐 볼륨만 낮춤(duckOthers — 큐는 짧은 안내).
 *
 * **F-6 후보(미확정)**: 종전엔 이 선언이 `hydrate()` 안에서 **앱 수명당 1회**만
 * 실행됐다. 그런데 `AVAudioSession` 은 expo-audio 와 expo-video 가 **공유**하고,
 * expo-video 는 재생 상태가 바뀔 때마다 공유 세션을 자기 계산값으로 다시 쓴다
 * (`expo-video/ios/VideoPlayer.swift:311` → `VideoManager.swift:105-111`).
 * 음성 큐 1회당 pause 2 + play 2 = 최대 4번의 재작성이 **발화 직전·직후에** 일어나므로
 * 우리의 1회성 선언은 그 사이에 덮인다. 그래서 재생 직전에 다시 선언한다.
 *
 * **이것이 실기기 무음의 원인이라는 증명은 없다** — 두 작성자 모두 카테고리는
 * `.playback` 으로 수렴해서 무음 스위치 축은 이 경합으로 설명되지 않는다(SUMMARY
 * `## F-6 재조사` 참조). 기존 성공 경로의 상위집합이라 회귀는 불가능하다는 것만이
 * 이 변경의 보증이다.
 *
 * **되돌리는 방법**: `speakCue` 안의 `declareAudioMode();` 한 줄을 지운다
 * (hydrate 쪽 호출은 종전 동작 그대로라 남겨둔다).
 */
function declareAudioMode(): void {
  try {
    setAudioModeAsync({
      playsInSilentMode: true,
      interruptionMode: 'duckOthers',
    }).catch(() => {
      /* graceful — 오디오 세션 설정 실패해도 재생 시도는 유지 */
    });
  } catch {
    /* 동기 throw 도 무해화 — speakCue 반환 semantics 불변 */
  }
}

// 설정값을 AsyncStorage 에서 메모리 캐시로 로드 + 오디오 세션 설정. graceful:
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
  declareAudioMode();
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
 * **아직 신선한** 캐시를 가진 cueId 는 스킵. 개별 발급 실패는 조용히 건너뜀(자막만).
 *
 * 플랜 시그니처(cues 만)를 analysisId 동반으로 확장: B안 재서명은 analysisId 로만
 * 서버가 canonical key 를 구성하므로 필수 (Rule 3 — 확정 B안에서 시그니처 보정).
 */
export async function prefetchCueAudio(
  analysisId: string,
  cues: readonly Cue[],
): Promise<void> {
  await hydrate();
  // quick-260801-f77 — 분석 전환 시 캐시 무효화. **enabled 게이트보다 먼저** 해야 한다:
  // 오디오를 끈 채로 분석을 갈아탄 뒤 다시 켜면, 여기서 return 해버린 탓에 이전 분석의
  // 캐시가 살아남아 남의 음성이 재생된다.
  if (cachedAnalysisId !== analysisId) {
    urlCache.clear();
    cachedAnalysisId = analysisId;
  }
  if (!enabled) return;
  // 루프 전에 한 번만 잡아 재사용 — id 마다 now 가 흔들리면 경계에서 판정이 갈린다.
  const now = Date.now();
  const ids = Array.from(
    new Set(
      cues
        .map((c) => c.cueId)
        // "미보유 **또는 만료 임박**" 재발급. 종전 `!urlCache.has(id)` 는 한 번
        // 캐시된 id 를 영원히 재발급 대상에서 제외해 결함 A 의 본체였다.
        .filter((id): id is string => !!id && !isFresh(urlCache.get(id), now)),
    ),
  );
  await Promise.all(
    ids.map((recordId) =>
      fetchCoachAudioUrl(analysisId, recordId)
        .then(({ url, expiresInSec }) => {
          urlCache.set(recordId, {
            url,
            expiresAtMs: Date.now() + expiresInSec * 1000,
          });
        })
        .catch(() => {
          /* 조용한 폴백 — 이 cueId 는 자막만 (분석/자막 무영향) */
        }),
    ),
  );
}

/**
 * 단일 cueId URL 재발급 (캐시 갱신). 성공 시 저장된 엔트리를, 실패/전제 미충족 시
 * null 을 돌려준다 — 오디오는 보조 채널이라 어떤 실패도 던지지 않는다.
 * prefetch 이후에 만료된 큐(speakCue)와 로드 실패 재시도(onLoadTimeout)가 공유한다.
 */
async function reissue(recordId: string): Promise<CachedAudio | null> {
  const analysisId = cachedAnalysisId;
  // 어느 분석의 recordId 인지 모르면 서버가 canonical key 를 만들 수 없다.
  if (!analysisId) return null;
  try {
    const { url, expiresInSec } = await fetchCoachAudioUrl(
      analysisId,
      recordId,
    );
    // 응답이 도착하는 사이 다른 분석으로 갈아탔으면 남의 캐시를 오염시키지 않는다.
    if (cachedAnalysisId !== analysisId) return null;
    const entry: CachedAudio = {
      url,
      expiresAtMs: Date.now() + expiresInSec * 1000,
    };
    urlCache.set(recordId, entry);
    return entry;
  } catch {
    // 조용한 폴백 — 자막만. presigned URL 은 로그·에러에 싣지 않는다 (T-f77-02).
    return null;
  }
}

/**
 * 큐 발화. 설정 on + cueId 조인 + prefetch 캐시 히트일 때만 재생한다. 새 큐는
 * 이전 플레이어를 해제하고 새로 만든다(quick-260806-wj3 activatePlayer — 이전 발화
 * 중단은 그대로 성립하고, 이전 큐의 아이템이 남는 경로만 사라진다). 같은 cueId
 * 재요청은 무시(중복 재시작 stutter 방지 — tick 은 큐 전환 시에만 호출하나 방어).
 * 캐시 미스(prefetch 실패/미조인)는 no-op(자막만).
 *
 * 33-13 — 발화 시작 여부 boolean 반환. VideoCompare 가 true 일 때만 영상을
 * 일시정지한다(대표 UX 패턴) — 캐시 미스/미조인 큐(false)는 자막만이라 멈춤도
 * 없다 (짝 없는 큐 미발동, D-18 고아 가드).
 *
 * quick-260801-f77 — 이 boolean 은 "지금 발화를 **시작**했다(= VideoCompare 가 영상을
 * 멈출 근거)" 라는 뜻이지 "끝까지 성공한다" 는 약속이 아니다. 로드 실패는 비동기라
 * 여기서 알 수 없고, 반환값을 뒤집는 대신 **VideoCompare 가 이미 폴링 중인 같은
 * 채널**(`isCueSpeaking()`)로 드러난다 — `failSpeech` 가 `speechActive` 를 내리면
 * 다음 tick(100ms)에 영상이 재개된다. 그래서 VideoCompare 는 무수정이다.
 */
export function speakCue(cue: Cue): boolean {
  if (!enabled) return false;
  const id = cue.cueId;
  if (!id) return false;
  const entry = urlCache.get(id);
  // quick-260801-f77 — 죽은 것이 확실한 URL 로는 재생을 시도하지 않는다. false 를
  // 돌려주면 VideoCompare 가 영상을 멈추지 않으므로(대표 UX 패턴) 이 큐에서는 정지
  // 자체가 발생하지 않는다 — 만료를 알면서 15초 멈추는 것이 가장 나쁜 선택이다.
  if (!isFresh(entry, Date.now())) {
    // **만료**(엔트리는 있었는데 시간이 지남)일 때만 재발급을 건다. 이 큐는 이미
    // 놓쳤지만 다음 큐는 살린다. 반대로 **미조인/미prefetch**(entry 부재)는 종전대로
    // 네트워크 0 no-op 이다 — audioCues 는 cueWindows 전체에서 파생될 뿐 mp3 보유
    // 여부로 걸러지지 않아서(VideoCompare `audioCues`), 합성 실패 분석에서는 모든
    // 큐가 영구 미스다. 여기서 무조건 재발급하면 큐가 바뀔 때마다 404 POST 를
    // 쏘게 된다 (T-f77-01 자해 DoS).
    if (entry) {
      urlCache.delete(id); // 죽은 엔트리 축출
      void reissue(id); // fire-and-forget — speakCue 는 동기 계약
    }
    return false;
  }
  const url = entry.url;
  if (playingCueId === id && player?.playing) return true;
  // 새 발화 = 새 세대. **플레이어 발급보다 먼저** 올린다: 아래 try 가 던지면 catch 는
  // 발화를 포기하는데, 세대가 그대로면 이전 큐의 재발급 응답이 뒤늦게 도착해
  // seq 가드를 통과하고 재생을 되살린다(영상은 이미 재개된 상태 → 유령 음성).
  speechSeq += 1;
  const mySeq = speechSeq;
  speechRetryCount = 0; // 큐마다 온전한 재시도 예산
  try {
    // quick-260806-wj3 — 이 큐의 URL 로 새 플레이어를 만든다. 이전 플레이어(와
    // 그 아이템)는 여기서 해제되므로, 아래 play() 가 닿을 수 있는 아이템은
    // 이 URL 로 만들어진 것 하나뿐이다.
    const p = activatePlayer(url);
    playingCueId = id;
    speechActive = true;
    // F-6 후보(미확정) — 공유 AVAudioSession 이 expo-video 의 재생 상태 전이마다
    // 재작성되므로, 발화 직전에 우리 모드를 다시 선언한다. 되돌리려면 이 한 줄 삭제.
    declareAudioMode();
    p.play();
    armLoadWatchdog(mySeq);
    return true;
  } catch {
    // released/플랫폼 예외 — 무해화(자막만). 다음 큐에서 재시도.
    clearLoadWatchdog();
    playingCueId = null;
    speechActive = false;
    return false;
  }
}

/**
 * 발화 중단 (일시정지·seek·언마운트·off 전환 시).
 *
 * quick-260801-f77 — 세대를 올려 진행 중인 지연 콜백(감시 타이머·재발급 응답)을
 * 전부 무효화한다. 사용자가 일시정지·seek·화면 이탈했는데 뒤늦게 도착한 재발급
 * 응답이 재생을 되살리는 경로를 구조적으로 차단한다. 호출처는 VideoCompare 의
 * pause·언마운트·overMax·토글 off — 전 경로가 이 무효화를 받는다.
 *
 * quick-260806-wj3 — 종전의 "리소스는 유지(재사용)"를 철회하고 플레이어까지
 * 해제한다. 정지 이후에는 어떤 아이템도 남지 않으므로, 위 전 경로가 아이템
 * 무효화까지 함께 받는다.
 */
export function stopCue(): void {
  speechSeq += 1;
  clearLoadWatchdog();
  playingCueId = null;
  speechActive = false;
  releasePlayer(); // player 미생성도 내부에서 흡수(early return)
}

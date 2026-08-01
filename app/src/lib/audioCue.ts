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
  try {
    if (!player) {
      player = createAudioPlayer(url);
    } else {
      player.replace(url); // 이전 발화 중단 + 새 소스
    }
    attachStatusListener();
    playingCueId = id;
    speechActive = true;
    // F-6 후보(미확정) — 공유 AVAudioSession 이 expo-video 의 재생 상태 전이마다
    // 재작성되므로, 발화 직전에 우리 모드를 다시 선언한다. 되돌리려면 이 한 줄 삭제.
    declareAudioMode();
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

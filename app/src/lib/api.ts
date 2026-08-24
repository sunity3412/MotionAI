// Motion AI HTTP API 클라이언트.
// 백엔드 SAM 스택 `sunity-motion-pilot` 의 HTTP API (API Gateway).
// Firebase ID 토큰을 Authorization 헤더로 검증 (sunity_shared.auth.verify_request).
// EXPO_PUBLIC_API_BASE_URL 미설정 시 명확히 에러 — .env 참고.

import { auth } from './firebase';
import type {
  UploadUrlRequest,
  UploadUrlResponse,
  VideoFormat,
} from '../types/analysis';

const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL;

/**
 * 백엔드 오류 봉투 `{error:{code,message}}` (contract.md §2) 의 `code` 를 보존하는
 * 타입 오류 (리뷰 M-05).
 *
 * 왜 필요한가: 이전에는 모든 실패가 평문 `Error` 였고, 호출부가 분기하려면
 * `message.includes('daily_limit')` 같은 문자열 파싱을 해야 했다. 그 방식은
 * (a) 백엔드가 메시지 문구만 바꿔도 조용히 깨지고 (b) 사용자 노출 메시지와
 * 분기 키가 한 문자열에 묶여 번역/문구 수정이 로직을 망가뜨린다.
 * `code` 는 계약에 명시된 안정 식별자이므로 분기는 여기에만 건다.
 *
 * `message` 포맷은 기존과 동일하게 유지한다 — 기존 소비처 무회귀.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(message: string, status: number, code: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

// 오류 응답 본문에서 계약상 code 를 추출. 파싱 실패(비-JSON 5xx, 게이트웨이 HTML 등)
// 는 'unknown' — 던지지 않는다. 오류 처리 경로가 다시 던지면 원인이 가려진다.
function parseErrorCode(text: string): string {
  try {
    const body = JSON.parse(text) as { error?: { code?: unknown } };
    const code = body?.error?.code;
    return typeof code === 'string' && code.length > 0 ? code : 'unknown';
  } catch {
    return 'unknown';
  }
}

async function authedJson<T>(
  path: string,
  init: { method: 'GET' | 'POST'; body?: unknown },
): Promise<T> {
  if (!API_BASE_URL) {
    throw new ApiError(
      'EXPO_PUBLIC_API_BASE_URL 미설정. app/.env 확인.',
      0,
      'config_missing',
    );
  }
  const user = auth.currentUser;
  if (!user) throw new ApiError('로그인이 필요합니다.', 0, 'unauthenticated');
  const token = await user.getIdToken();
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: init.method,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: init.body == null ? undefined : JSON.stringify(init.body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    // 메시지 포맷 불변 (기존 소비처 무회귀) — 분기용 code 만 추가로 실어 보낸다.
    throw new ApiError(
      `${init.method} ${path} ${res.status}: ${text.slice(0, 200)}`,
      res.status,
      parseErrorCode(text),
    );
  }
  return res.json() as Promise<T>;
}

// POST /upload-url — S3 presigned PUT URL + analysisId 발급.
// 응답을 받은 뒤 앱이: (1) Firestore users/{uid}/analyses/{analysisId} 에
// status='uploading' 문서 생성 (2) uploadUrl 로 영상 PUT.
export function requestUploadUrl(
  req: UploadUrlRequest,
): Promise<UploadUrlResponse> {
  return authedJson<UploadUrlResponse>('/upload-url', {
    method: 'POST',
    body: req,
  });
}

// 박제 (2026-06-06 belle): myVideoUrl 의 S3 signed URL 은 7일 TTL.
// mode3 second+ 가 일주일 뒤 prev 영상 fetch 시 만료 → 영상 안 뜸 보고.
// POST /playback-url — analysisId + ext 박제 → fresh signed GET URL 반환.
export interface PlaybackUrlResponse {
  playbackUrl: string;
  expiresInSec: number;
}

export function requestPlaybackUrl(
  analysisId: string,
  ext: VideoFormat = 'mp4',
): Promise<PlaybackUrlResponse> {
  return authedJson<PlaybackUrlResponse>('/playback-url', {
    method: 'POST',
    body: { analysisId, ext },
  });
}

// 29-CONTEXT D-09 — D1 fix (진단: presigned 7일 TTL 만료).
// mode1 우측(정은지) 비교영상 재발급 — referenceMotionId 변형 (contract.md §2).
// 백엔드가 Firestore reference/{id} doc 의 videoS3Key 화이트리스트 경유로만
// 서명 (임의 S3 키 서명 불가, inactive/prefix 밖 키는 404).
export function requestReferencePlaybackUrl(
  referenceMotionId: string,
): Promise<PlaybackUrlResponse> {
  return authedJson<PlaybackUrlResponse>('/playback-url', {
    method: 'POST',
    body: { referenceMotionId },
  });
}

// Phase 31 (D-06) — POST /visual/rotation. 회전 참고 영상 온디맨드 생성 요청.
// 건당 ~6-7분·과금이라 자동 생성하지 않는다 (contract.md §2).
// 202 = 신규 접수/재시도 수락, 200 = 이미 완료. 어느 쪽도 URL 을 담지 않는다 —
// 표시 URL 은 fetchVisualAssetUrl('rotation') 재서명 전용 (URL 비저장, 리뷰 H-02).
export function requestRotationVideo(
  analysisId: string,
): Promise<{ rotationStatus: 'pending' | 'done' }> {
  return authedJson<{ rotationStatus?: unknown }>('/visual/rotation', {
    method: 'POST',
    body: { analysisId },
  }).then((res) => {
    // 스키마 방어: 200/202 라도 계약 필드가 없으면 성공으로 취급하지 않는다.
    // 이걸 안 막으면 빈 응답이 'pending' 으로 흘러가 카드가 영원히 로딩으로 남는다.
    if (res.rotationStatus !== 'pending' && res.rotationStatus !== 'done') {
      throw new ApiError(
        'POST /visual/rotation: rotationStatus 필드 부재/형식 오류',
        200,
        'malformed_response',
      );
    }
    return { rotationStatus: res.rotationStatus };
  });
}

// Phase 31 (리뷰 H-02) — 시각 산출물 표시 URL 재서명. Firestore 문서에는 presigned
// URL 을 저장하지 않으므로(죽은 URL 박제 방지) 표시 시점마다 여기서 발급한다.
// 클라이언트는 asset '종류'만 고르고 실제 S3 key 선택은 전적으로 서버 몫이다
// (server-selected key — 임의 key 서명 경로 없음, contract.md §2).
// 미생성/미완료/prefix 불일치는 전부 404 not_found 로 합산된다 (leak 0).
// Phase 35 (quick-260808-jix) — 'renderedCompare' 합성 비교 영상 mp4 추가
// (contract.md §12.9 — done + exact 이중 가드, 시그니처 외 로직 무변경).
export function fetchVisualAssetUrl(
  analysisId: string,
  asset: 'correctedPose' | 'rotation' | 'renderedCompare',
): Promise<string> {
  return authedJson<{ playbackUrl?: unknown }>('/playback-url', {
    method: 'POST',
    body: { analysisId, asset },
  }).then((res) => {
    if (typeof res.playbackUrl !== 'string' || res.playbackUrl.length === 0) {
      throw new ApiError(
        'POST /playback-url: playbackUrl 필드 부재/형식 오류',
        200,
        'malformed_response',
      );
    }
    return res.playbackUrl;
  });
}

// Phase 32 (Plan 32-12 — D-18 B안 재생 중 큐 오디오) — coachAudio mp3 표시 URL 재서명.
// 백엔드(32-16)가 분석 사후 스테이지에서 records 의 cueLine 을 Polly 로 합성해 S3 에
// 저장하고 result.coachAudio.items[{recordId, key}] 로 도착시킨다. URL 은 문서에 저장하지
// 않으므로(죽은 URL 박제 방지, 리뷰 H-02) 재생 시점마다 여기서 재서명한다.
// 클라이언트는 recordId(=cueId)만 넘기고 실제 S3 key 구성·검증은 전적으로 서버 몫이다
// (server-selected canonical key + 저장 key exact 비교 — 임의 key 서명 경로 없음).
// 미등재 recordId·형식 위반·타 uid 는 전부 404/400 로 합산된다 (leak 0, 32-16 스모크 실증).
//
// quick-260801-f77 — 바로 위 "재생 시점마다 재서명한다" 는 선언은 지켜지지 않고 있었다.
// 소비처(audioCue.ts)가 발급받은 URL 을 만료 개념 없는 Map 에 무기한 캐시해서, 앱을
// 1시간 넘게 띄워두면 죽은 URL 을 계속 재생 시도했다(presigned TTL 3600s —
// backend/functions/playback-url/app.py `_ASSET_EXPIRES`). 서버는 이미 응답에
// expiresInSec 를 실어 보내고 있었는데 앱이 그 값을 버리고 있었을 뿐이다. 이제 만료
// 시각을 함께 넘겨 캐시가 스스로 갱신하게 한다 (판정은 audioCue.ts `isFresh`).
export type CoachAudioUrl = { url: string; expiresInSec: number };

// 서버가 expiresInSec 를 안 주거나 형식이 깨졌을 때 쓰는 보수적 기본값.
// 짧은 쪽으로 실패하는 이유: 과다 추정의 대가는 무음(사용자가 겪는 결함)이고,
// 과소 추정의 대가는 authed POST 1회(재발급)뿐이다. 구 Lambda 가 떠 있어도
// 앱이 죽지 않게 하는 하위호환 장치이기도 하다.
const COACH_AUDIO_TTL_FALLBACK_SEC = 300;

export function fetchCoachAudioUrl(
  analysisId: string,
  recordId: string,
): Promise<CoachAudioUrl> {
  return authedJson<{ playbackUrl?: unknown; expiresInSec?: unknown }>(
    '/playback-url',
    {
      method: 'POST',
      body: { analysisId, asset: 'coachAudio', recordId },
    },
  ).then((res) => {
    if (typeof res.playbackUrl !== 'string' || res.playbackUrl.length === 0) {
      throw new ApiError(
        'POST /playback-url: playbackUrl 필드 부재/형식 오류',
        200,
        'malformed_response',
      );
    }
    // expiresInSec 는 검증 실패해도 던지지 않는다 — URL 자체는 멀쩡한데 부가
    // 필드 하나 때문에 발화를 통째로 잃는 것이 더 나쁘다. 폴백으로 흡수한다.
    const ttl =
      typeof res.expiresInSec === 'number' &&
      Number.isFinite(res.expiresInSec) &&
      res.expiresInSec > 0
        ? res.expiresInSec
        : COACH_AUDIO_TTL_FALLBACK_SEC;
    return { url: res.playbackUrl, expiresInSec: ttl };
  });
}

// quick-260824-q6p — 확대 비교 PNG 배치 재서명. faultZoomComparisons[].imageUrl
// 은 분석 시점 7일 presigned 라 7일 뒤 전부 죽는다(비교 패널 회색 — belle 08-24
// 실기기). 열람 시점에 여기서 재발급한다 (URL 비저장 원칙 확장, H-02).
// 클라이언트는 asset 종류만 보내고 key 는 절대 싣지 않는다 — 서버가 canonical
// key 를 구성해 doc 저장 key 와 exact 비교한다 (server-selected key, H-05 —
// contract.md "asset: 'faultZoom'" 절). tier/criterion echo = 앱 join 키 재료
// (faultZoomUrls.zoomCardKey — doc item 과 echo item 에 같은 함수 적용).
export type FaultZoomUrlItem = {
  joint: string;
  tier?: string;
  criterion?: string;
  playbackUrl: string;
};

export function fetchFaultZoomUrls(
  analysisId: string,
): Promise<{ items: FaultZoomUrlItem[]; expiresInSec: number }> {
  return authedJson<{ items?: unknown; expiresInSec?: unknown }>(
    '/playback-url',
    {
      method: 'POST',
      body: { analysisId, asset: 'faultZoom' },
    },
  ).then((res) => {
    // 스키마 방어 (fetchVisualAssetUrl 선례) — items 가 배열이 아니면 실패.
    if (!Array.isArray(res.items)) {
      throw new ApiError(
        'POST /playback-url: items 필드 부재/형식 오류',
        200,
        'malformed_response',
      );
    }
    // 불량 item 은 조용히 filter — 배치라 부분 성공을 보존한다 (하나 때문에
    // 던지면 멀쩡한 카드까지 저장 URL 폴백으로 떨어진다).
    const items: FaultZoomUrlItem[] = [];
    for (const raw of res.items) {
      if (raw == null || typeof raw !== 'object') continue;
      const it = raw as Record<string, unknown>;
      if (typeof it.joint !== 'string' || it.joint.length === 0) continue;
      if (typeof it.playbackUrl !== 'string' || it.playbackUrl.length === 0) {
        continue;
      }
      items.push({
        joint: it.joint,
        playbackUrl: it.playbackUrl,
        tier: typeof it.tier === 'string' ? it.tier : undefined,
        criterion: typeof it.criterion === 'string' ? it.criterion : undefined,
      });
    }
    // expiresInSec 검증 실패는 던지지 않는다 (fetchCoachAudioUrl 선례 — 보수적
    // 폴백. 과소 추정의 대가는 authed POST 1회뿐).
    const ttl =
      typeof res.expiresInSec === 'number' &&
      Number.isFinite(res.expiresInSec) &&
      res.expiresInSec > 0
        ? res.expiresInSec
        : 3600;
    return { items, expiresInSec: ttl };
  });
}

// S3 presigned PUT 으로 영상 업로드. Content-Type 은 서명에 묶지 않지만
// (upload-url Lambda 가 Params 에서 제외) PUT 헤더로 보내면 S3 가 그 값을 객체
// 메타데이터로 저장한다. 이걸 안 박으면 binary/octet-stream 으로 저장돼서
// 나중에 결과 화면의 expo-video 가 영상으로 인식 못 한다(P0 #6).
const CONTENT_TYPE_BY_FORMAT: Record<VideoFormat, string> = {
  mp4: 'video/mp4',
  mov: 'video/quicktime',
};

export async function uploadToS3(
  uploadUrl: string,
  fileUri: string,
  format: VideoFormat,
): Promise<void> {
  const file = await fetch(fileUri);
  const blob = await file.blob();
  const res = await fetch(uploadUrl, {
    method: 'PUT',
    body: blob,
    headers: { 'Content-Type': CONTENT_TYPE_BY_FORMAT[format] },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`s3 PUT ${res.status}: ${text.slice(0, 200)}`);
  }
}

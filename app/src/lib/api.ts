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
export function fetchVisualAssetUrl(
  analysisId: string,
  asset: 'correctedPose' | 'rotation',
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
export function fetchCoachAudioUrl(
  analysisId: string,
  recordId: string,
): Promise<string> {
  return authedJson<{ playbackUrl?: unknown }>('/playback-url', {
    method: 'POST',
    body: { analysisId, asset: 'coachAudio', recordId },
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

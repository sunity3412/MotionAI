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

async function authedJson<T>(
  path: string,
  init: { method: 'GET' | 'POST'; body?: unknown },
): Promise<T> {
  if (!API_BASE_URL) {
    throw new Error('EXPO_PUBLIC_API_BASE_URL 미설정. app/.env 확인.');
  }
  const user = auth.currentUser;
  if (!user) throw new Error('로그인이 필요합니다.');
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
    throw new Error(`${init.method} ${path} ${res.status}: ${text.slice(0, 200)}`);
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

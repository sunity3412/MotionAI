// Motion AI HTTP API 클라이언트.
// 백엔드 SAM 스택 `sunity-motion-pilot` 의 HTTP API (API Gateway).
// Firebase ID 토큰을 Authorization 헤더로 검증 (sunity_shared.auth.verify_request).
// EXPO_PUBLIC_API_BASE_URL 미설정 시 명확히 에러 — .env 참고.

import { auth } from './firebase';
import type { UploadUrlRequest, UploadUrlResponse } from '../types/analysis';

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

// S3 presigned PUT 으로 영상 업로드. Content-Type 은 서명에 묶지 않음(서버 정책).
// 성공 = res.ok. 실패 시 RN fetch 의 status/body 를 그대로 노출.
export async function uploadToS3(
  uploadUrl: string,
  fileUri: string,
): Promise<void> {
  const file = await fetch(fileUri);
  const blob = await file.blob();
  const res = await fetch(uploadUrl, { method: 'PUT', body: blob });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`s3 PUT ${res.status}: ${text.slice(0, 200)}`);
  }
}

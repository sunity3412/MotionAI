// 웹 영상 길이 읽기 — 공급자 올리기 폼 전용 (Phase 38 D-14 · RESEARCH A12).
//
// 브라우저 `<video preload="metadata">` 의 `duration` 을 **초** 그대로 돌려준다 —
// 38-03 `validateFile` 의 `durationSec` 이 초로 판정하므로 변환하지 않는다.
// (picker `asset.duration` 은 단위가 플랫폼마다 달라 videoDuration.pickerDurationMs 를 거친다 —
// 여기와 섞지 않는다, 38-10 Task 0.)
//
// 못 읽으면 null(fail-open) — 서버가 2차로 길이를 검증한다(공급자 경로, 38-06).
// `document` 가 없는 환경(네이티브 · node 테스트)에서는 바로 null.

const METADATA_TIMEOUT_MS = 8000;

export function readVideoDurationSec(src: Blob | string): Promise<number | null> {
  if (typeof document === 'undefined') return Promise.resolve(null);
  return new Promise((resolve) => {
    const video = document.createElement('video');
    video.preload = 'metadata';
    const objectUrl = typeof src === 'string' ? null : URL.createObjectURL(src);
    let settled = false;
    const finish = (value: number | null) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      video.onloadedmetadata = null;
      video.onerror = null;
      video.removeAttribute('src');
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      resolve(value);
    };
    const timer = setTimeout(() => finish(null), METADATA_TIMEOUT_MS);
    video.onloadedmetadata = () => {
      const d = video.duration;
      finish(Number.isFinite(d) && d > 0 ? d : null);
    };
    video.onerror = () => finish(null);
    video.src = objectUrl ?? (src as string);
  });
}

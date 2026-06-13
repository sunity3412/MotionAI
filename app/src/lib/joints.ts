// Firestore flat joints3d → (T, 17, 3) reshape 로더.
//
// 박제 정신 (04-02 PLAN Task 3, R3):
//   · 04-01 신설 joints3d / joints3dKeys / joints3dFrames 필드 전용 reshaper.
//   · result.angles (관절각 (T, J) 스칼라) 는 이 함수에 절대 입력하지 않는다 —
//     angles 는 XYZ 좌표가 아니므로 (T, 17, 3) reshape 불가. length guard 가
//     불일치를 잡아 null 반환하지만, 의미상 오용이므로 source 단계에서 차단.
//   · firestore-nested-array-flat 박제 정합 — Firestore 가 nested array 를
//     허용하지 않아 백엔드가 flat list + Frames + JointKeys 메타로 저장하고
//     읽는 쪽 (본 모듈) 에서 reshape 한다.
//
// graceful 정책: 형식 불일치 / 누락 / 길이 mismatch 시 throw 대신 null 반환.
// PoseViewer3D 가 joints null → return null 로 섹션 자체 graceful 생략.

/**
 * Firestore doc 에서 3D joint sequence 를 (T, J, 3) 으로 reshape 한다.
 *
 * @param flat (T * J * 3) 길이의 flat number list (RTMW pose-aligned). 형식
 *             불일치 / null / undefined / 비배열 시 null 반환.
 * @param jointKeys 길이 J 의 joint 이름 list (보통 17, COCO-17).
 * @param frames T (정수). 0 이면 null 반환 (joints.length === 0 와 동일 효과).
 * @returns number[][][] 형식의 (T, J, 3) 배열. 실패 시 null.
 */
export function reshapePose3dData(
  flat: unknown,
  jointKeys: unknown,
  frames: unknown,
): number[][][] | null {
  if (!Array.isArray(flat)) return null;
  if (!Array.isArray(jointKeys)) return null;
  if (typeof frames !== 'number') return null;

  const J = jointKeys.length;
  // joint 가 0 이면 (T, 0, 3) 무의미 — 빈 시퀀스로 취급해 null 반환.
  // (W3: flat.length === 0 도 length-product guard 보다 먼저 이 가드에서 catch.)
  if (J === 0) return null;

  const T = frames;
  // length guard. coordDim=3 고정 (analysis.ts 박제 정합).
  // result.angles (length = T * J, 1D 스칼라) 오입력 시 T*J !== T*J*3 이므로 null.
  if (flat.length !== T * J * 3) return null;

  const out: number[][][] = [];
  for (let t = 0; t < T; t++) {
    const frame: number[][] = [];
    for (let j = 0; j < J; j++) {
      const base = (t * J + j) * 3;
      frame.push([
        flat[base] as number,
        flat[base + 1] as number,
        flat[base + 2] as number,
      ]);
    }
    out.push(frame);
  }
  return out;
}

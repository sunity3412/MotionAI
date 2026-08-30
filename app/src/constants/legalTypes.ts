// 약관·방침 문서의 공통 형태 (Phase 36).
//
// 본문은 문단 배열이다. "· " 로 시작하는 줄은 화면에서 목록 항목으로 그린다 —
// 별도 마크다운 렌더러를 들이지 않기 위한 최소 규약.
//
// status:
//   'draft'    — 법무 검토 전. 화면 상단에 검토 중 배너를 띄운다.
//   'reviewed' — 검토 완료. 배너 없음.
// 검토가 끝나면 문서 파일에서 이 값만 바꾸면 된다.

export type LegalSection = {
  heading: string;
  body: string[];
};

export type LegalDocument = {
  status: 'draft' | 'reviewed';
  title: string;
  /** 개정 이력 추적용. 문안이 바뀌면 올린다. */
  version: string;
  effectiveNote: string;
  intro: string[];
  sections: LegalSection[];
};

// 약관 문서 색인 (Phase 36) — 화면이 라우트 파라미터로 문서를 고를 때 쓴다.

import { privacyPolicy } from './legalPrivacy';
import { termsOfService } from './legalTerms';
import type { LegalDocument } from './legalTypes';

export type LegalDocKey = 'terms' | 'privacy';

export const legalDocuments: Record<LegalDocKey, LegalDocument> = {
  terms: termsOfService,
  privacy: privacyPolicy,
};

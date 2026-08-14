// 앱 자막 조립기(composeCueSubtitleKo) 실행 프로브 — 양엔진 lockstep 의 TS 측
// (quick-260814-rcz).
//
// 왜 프로브인가: 종전 lockstep 은 "python 코드와 TS 코드를 사람이 눈으로 대조"였고
// 그래서 2026-08-07 에 음성·자막이 실제로 갈라진 채 belle 실기기까지 나갔다
// (debug va-subtitle-audio-mismatch). 소스 눈대조는 증거가 아니다 — 같은 fixture 를
// **양쪽 엔진에 실제로 통과시켜** 산출 문자열을 비교해야 갈라짐이 잡힌다.
//
// 계약:
//   stdin  = JSON 배열. 각 항목 = { record: DeductionRecord-유사 dict,
//            fallback: string|null }  (fallback 생략 시 null 취급)
//   stdout = JSON 배열 한 줄. 각 항목 = composeCueSubtitleKo 반환값(string|null)
//   stderr = Node 의 MODULE_TYPELESS_PACKAGE_JSON 경고 등 잡음 — 호출측은
//            **stdout 만** 파싱할 것 (실측 확인: 경고는 stderr 로만 나간다).
//
// 실행: node backend/tests/phase32/compose_cue_probe.mjs   (Node 24 타입 스트리핑)
// 프로덕션 코드 아님 — 테스트 하네스.

import { composeCueSubtitleKo } from '../../../app/src/lib/deductionSheet.ts';

async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  return Buffer.concat(chunks).toString('utf-8');
}

const raw = await readStdin();
const rows = JSON.parse(raw);
if (!Array.isArray(rows)) {
  throw new Error('probe 입력은 JSON 배열이어야 한다');
}
const out = rows.map((row) => {
  const record = row && typeof row === 'object' && 'record' in row ? row.record : row;
  const fallback = row && typeof row === 'object' && 'fallback' in row ? row.fallback : null;
  return composeCueSubtitleKo(record, fallback);
});
process.stdout.write(JSON.stringify(out));

// pa2 게이트: 공급자 화면 3파일 + SupplierUi 의 주석 밖 한국어 · 색 리터럴 · 이모지 · 브라우저 confirm/alert.
import fs from 'node:fs';
const root = process.argv[2];
const files = [
  'app/src/app/supplier/index.tsx',
  'app/src/app/supplier/upload.tsx',
  'app/src/app/supplier/guide.tsx',
  'app/src/components/SupplierUi.tsx',
];
function stripComments(src) {
  // 블록 주석(JSX {/* */} 포함) → 줄 수 보존 공백, 그다음 줄 주석. 문자열 안 '//' 는 'http' 뿐이라 따로 피한다.
  let out = src.replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, ' '));
  out = out.split('\n').map((line) => line.replace(/(^|[^:'"])\/\/.*$/, '$1')).join('\n');
  return out;
}
let bad = 0;
for (const f of files) {
  const code = stripComments(fs.readFileSync(`${root}/${f}`, 'utf8'));
  const lines = code.split('\n');
  lines.forEach((l, i) => {
    const hits = [];
    if (/[가-힣]/.test(l)) hits.push('hangul');
    if (/#[0-9a-fA-F]{3,8}\b/.test(l)) hits.push('hex-color');
    if (/rgba?\(/.test(l)) hits.push('rgba');
    if (/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u.test(l)) hits.push('emoji');
    if (/window\.(confirm|alert)|Alert\.alert/.test(l)) hits.push('browser-dialog');
    if (hits.length) { bad++; console.log(`${f}:${i + 1} ${hits.join(',')} :: ${l.trim()}`); }
  });
}
console.log(bad === 0 ? 'LITERAL_GATE_OK' : `LITERAL_GATE_FAIL ${bad}`);
process.exit(bad === 0 ? 0 : 1);

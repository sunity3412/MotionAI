// 웹 번들 문구 검사 — 번들은 한글을 \uXXXX 로 내보내므로 풀어서 센다. 인자: 번들 파일 경로(로컬) 또는 URL.
import fs from 'node:fs';
const src = process.argv[2];
const raw = src.startsWith('http') ? await (await fetch(src)).text() : fs.readFileSync(src, 'utf8');
// \uXXXX(한글)와 \xXX(가운뎃점 · 등) 둘 다 푼다 — 하나만 풀면 '·' 가 든 문구를 0 으로 잘못 센다.
const text = raw
  .replace(/\\u([0-9a-fA-F]{4})/g, (_, h) => String.fromCharCode(parseInt(h, 16)))
  .replace(/\\x([0-9a-fA-F]{2})/g, (_, h) => String.fromCharCode(parseInt(h, 16)));
const want = ['검토 중이에요', '검토 요청 취소', '요청 취소됨', '검토는 보통 하루 안에 끝나요',
  '검토를 요청했어요. 보통 하루 안에 끝나요.', '검토 요청을 취소할까요?', '지금은 취소할 수 없어요',
  // 디코더 검증용 — 가운뎃점(\xb7)이 든 기존 문구가 1 이상이어야 '·' 문구의 0 이 믿을 만하다.
  '{name} · {athlete} 선수'];
const gone = ['확인 중 · 끝나면 수강생에게 보여요', '운영팀 확인이 끝나면 앱에 보여요', '메일로 알려', '일 이내'];
const count = (t) => text.split(t).length - 1;
let ok = true;
for (const t of want) { const n = count(t); if (n < 1) ok = false; console.log(`want>=1\t${n}\t${t}`); }
for (const t of gone) { const n = count(t); if (n !== 0) ok = false; console.log(`want=0\t${n}\t${t}`); }
console.log(ok ? 'BUNDLE_COPY_OK' : 'BUNDLE_COPY_FAIL');
process.exit(ok ? 0 : 1);

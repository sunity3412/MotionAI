# gate_out_v11 — Omni 1.1 재게이트 산출 (2026-09-18)

7월 산출물(`../gate_out/`)과 **분리**된 디렉터리다. 7월 것은 건드리지 않았다.

- `power-spin__r1.mp4` — `gemini-omni-1.1-flash` 출력. **회전 안 됨**(원본 대비 픽셀차 2.4).
- `_ctl_oldmodel.mp4` — 대조군. 같은 REST 호출을 `gemini-omni-flash-preview` 로.
  **회전 됨**(37.7) — 내 호출 shape 이 정상임을 증명한다.
- `journal_v11.json` — 호출 기록(interaction id / 토큰 / 비용 / 회전델타).

판정과 근거는 `.planning/quick/260918-et1-omni11-regate/260918-et1-SUMMARY.md`.

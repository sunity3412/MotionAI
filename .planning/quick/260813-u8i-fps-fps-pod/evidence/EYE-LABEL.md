# EYE-LABEL — 카드 실물 육안 판정 (quick-260813-u8i, frames-before-numbers)

판정자: Claude (오케스트레이터 실행분). 본 런(무패치, 실효 fps 라벨) 카드 3장을
Read 로 열어 좌하단 초 라벨 픽셀이 label_check.json labelTable 의 신 라벨 값과
일치하는지 눈으로 확인했다 — 기계 산출 필드만 믿고 픽셀을 안 본 채 제시 금지.

| 카드 | 표 신 라벨 | 픽셀 실측 | 구 라벨(÷9.0) | 판정 |
|---|---|---|---|---|
| pdshapefault zoom_angle_vs_reference__left_elbow (user 패널) | 8.603s | "8.6s" | 9.556s ("9.6s") | PASS |
| elbow zoom_angle_vs_reference__right_elbow (user 패널) | 11.119s | "11.1s" | 12.333s ("12.3s") | PASS |
| powerspin zoom_angle_vs_reference__left_shoulder (user/ref 양 패널 — spin stamp_ref) | u 3.205s / r 5.700s | "3.2s" / "5.7s" | u 3.556s / r 6.333s | PASS |

- 세 장 모두 0.1s 표시 정밀도에서 표의 신 라벨과 픽셀이 일치, 구 라벨 값은 소멸.
- 마크(V/원/스포트라이트)·크롭·장면은 대조 런(md5 == nh4 정본)과 동일 구조 —
  라벨 텍스트만 변한 것을 육안으로도 재확인 (pdshape left_elbow 카드는 nh4
  PORT-EYE-VERDICT 의 같은 카드와 같은 장면).
- 경계 케이스 한계 박제: peterpan user 라벨 6.1s 는 freeze 초(6.444s)가 아니라
  클립 마지막 프레임(클립 길이 6.223s)의 실초다 — freeze 초 자체가 클립 밖인
  것은 freeze 타임베이스 상류 의제 (이 수리 밖). 종전 라벨 6.8s 는 6.2s 클립에
  존재하지 않는 초를 가리켰다.

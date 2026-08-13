# staging/ — S3 업로드 보류분 (belle 복귀 확인 후 별도 1단계)

**S3 업로드 금지 상태** — 이 디렉터리의 실물은 로컬 스테이징만이다. 업로드는
belle 복귀 확인 후 별도 1단계로 진행한다 (플랜 명기).

## 왼무릎 (pdshapefault r03) — override 재렌더 **미수행** (모호 경로)

content-match 는 belle 스크린샷 우측(ref) = **4.067s 접힘**을 명확히
분리했으나 (frame_match.json fineScan), 다음이 갈려 해석 금지 경로로 종료:

- 스크린샷이 가리킨 실물 짝 = [user **2.87s 접힘** | ref 4.067s 접힘] —
  그런데 카드의 user 순간은 freeze u3.667(실초 3.30s, **벌림 OPEN-V**)로
  고정이고 pair-override 는 ref 순간만 바꾼다 (user 변경 = 재정박, 경로 없음).
- belle 서사("학생 2초대 동작 같아서 후보3 어울리지 않음")의 벌림-벌림 짝은
  ref 2.4s = **현행 반려 baseline 과 같은 초**다.

판정 재료 3장 (원본 프레임 그대로, 마크 무추가):

| 파일 | 내용 |
|------|------|
| knee_candidate_A_userfreeze_ref4.067s.png | user freeze(벌림) \| ref 4.067s(접힘) — 스크린샷 우측 초를 override 로 반영하면 나오는 짝 |
| knee_candidate_B_userfreeze_ref2.4s.png | user freeze(벌림) \| ref 2.4s(벌림) — 요소 일치 짝 = 현행 반려 baseline |
| knee_candidate_C_screenshot_pair_user2.87_ref4.067.png | belle 스크린샷이 실제 가리킨 짝 (접힘-접힘) — user 순간 변경 필요 = override 표현 밖 |

belle 확인 1개: **A / B / C 중 카드가 보여줄 짝은?** (C 선택 시 freeze 상속
원칙의 예외 승인이 필요함을 함께 판정)

---

## 판정 결과 (2026-08-13, belle) — 역할 종료

belle: "A와 B가 같은 시간대인 거 같고 이때는 B. C는 좀 더 지난 장면이야"
→ **B 채택 = 현행 짝과 같은 초 → override·재렌더·S3 업로드 전부 불필요.**
반려 원인(ref 무마크+전신 크롭)은 B 스펙 렌더로 기해소. C 기각(더 뒤의 별개
장면) — freeze 상속 예외 불필요. 이 디렉터리는 판정 재료로 역할 종료,
업로드 보류분 없음. 정본 기록 = xa1 JUDGMENT.md 라운드 5 최종 절.

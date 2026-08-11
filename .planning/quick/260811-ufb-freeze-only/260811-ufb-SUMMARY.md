---
quick_id: 260811-ufb
slug: freeze-only
date: 2026-08-11
status: complete
commits:
  - 4d1b1b49  # feat: _run_gated_card_inherit 수술 — 재정박·절정 재배치 제거, 방출 게이트 전용
  - 5ddc1e3a  # feat: 로컬 기계 증명 + 승인 5동작 스윕 (freeze 일치 / 결정론 / 무회귀)
  - "(Pod 실증 증거 + 본 SUMMARY 커밋)"
duration: 약 1.5시간 (Task 3 Pod 단계는 오케스트레이터가 SSH 권한 획득 후 대행)
---

# freeze-only 수리 — 카드 = 영상 정지 순수 상속 + 확대만

> **기계 판정 한 줄**: fresh 2회 + **승인 5동작 전부**에서 방출 순간 == 영상 freezes[]
> 전건 일치(순간 발명 0) + 별도 프로세스 2회 완전 동일(비결정 소멸) + 승인 9/9 ·
> pytest 기준선 59 무회귀 + **Pod 재분석(p34fresh1786458292) 실증: 재정박 없이 freeze
> 상속 카드 2장 방출, 점수 60, 분석 666s→404s, 눈 호출 47→2회**.

## belle 반려 (스펙 원문)

"영상이라는 기본 승인 틀이 있는데 왜 자꾸 다르게 하는건지" · "하다못해 확대를 해도
되겠구만" · "조정을 좋은쪽으로 하라고 했지 이상한대를 비교하라고 하질 않았는데"
+ "지금 쓴 영상만 잘 돌아가는건 아닌지 항상 점검하고" (일반화 재강조).

## 무엇을 수술했나

- `_run_gated_card_inherit`: **재정박(새 순간 탐색)·절정 재배치 코드 제거** (플래그
  아님 — 같은 서브시스템 3회째 구조 제거 규율. 코드는 kpo 커밋 이력에 보존).
  215줄 중 172줄 삭제. 게이트(홀드/짝정합/기계눈)는 **freeze 방출 판정 전용**:
  통과한 freeze 만 그 순간 그대로 확대 카드, 실패 freeze 는 미방출(정직한 침묵).
- 배정 = 생존 freeze |dev| 내림차순, 상한 4장 (kpo 동일). 채점 5파일 diff 0.
- verdict 로그에서 `reanchored` 필드 삭제, 방출 순간 `@u/r` 명기.

## 검증 결과

| 항목 | 결과 |
|---|---|
| 순간 발명 0 | fresh 2회 + 승인 5동작: 방출 @u/r == freezes[] 전건 일치, u_sec/r_sec 덮어쓰기 연산 0 (grep+코드+로그 3층) |
| 결정론 | 별도 프로세스 2회: survivors/dropped/카드 목록/PNG md5 동일 (kpo 의 12.8s↔10.5s 비결정 소멸) |
| 승인 무회귀 | joint-scope 9/9 (hold+pair) + align-peak 비구속 3 + pytest 59 failed 기준선 동일 / 4149 passed |
| 5동작 스윕 (사전 예측 박제) | 방출 9 / 침묵 4. elbow r02 침묵 = 예측 적중. **눈이 승인 정지 2건 기각** — pdshapefault r01 은 트랙 환각을 정확히 잡음(옳은 기각), peterpan r00 은 unclear → confirmed 0장. 임계 무조정 박제 |
| D-41 | 게이트·배선 동작명 리터럴 분기 0 (grep 재확인) |
| Pod 실증 | commitSha 5ddc1e3a == HEAD, score **60**, 404.1s, renderedCompare done freeze 5 |
| verdict (운영) | `survivors=['r00:inherit@u5.302/r5.13', 'r03:inherit@u16.667/r15.20'] dropped=[r01/r04: hold=moving, r02: pose_far] eye_calls=2` + 대체 부착 confirmed=2 advisory=1 |
| 크롭 | 전 카드 vertex_centered=True, frac 0.40~0.55 밴드 내. 카드 실물 육안 = 양 패널 같은 국면 짝 + 타이트 크롭 (evidence/pod_cards/) |

## 정직 박제

1. **왼골반(r03) 카드가 16.7s 영상 freeze 상속으로 방출** — kpo 정답표("왼골반
   소멸")와 다르지만 이번 스펙(freeze-only, 영상이 틀)의 올바른 산출. 그 freeze 는
   홀드+짝정합을 그 순간에서 통과했다. **belle 육안 최종 판정 대상.**
2. **왼무릎(r04)·오른팔꿈치(r01)·오른어깨(r02) 침묵** — 각자의 freeze 가 게이트
   미달(hold=moving / pose_far). 왼무릎 결함 카드는 신규 발굴 사이클(별도, belle
   사전 대조) 없이는 나오지 않는다.
3. **카드 초 표기 ÷9.0 잔존** — 5.3s→5.9s, 16.7s→18.6s 표기. 기존 결함, 범위 밖.
4. **Pod 운영 사고 2건 + 수리**: (a) 1차 재기동이 기동 완료 후 1~2분 내 graceful
   shutdown — ssh 세션 종료/프로세스 그룹 정리 겹침 추정, **setsid+nohup+disown+
   </dev/null 완전 분리**로 해소 (원격 재기동 표준으로 박제). (b) 재분석 1차 시도가
   env 블록 source 의 cwd 변경 + 상대경로 cd 로 즉사 — 절대경로 + 완료 마커
   (/workspace/_ufb_done) 수리. 스크립트 = /workspace/_run_ufb.sh.
5. 실행자(서브에이전트)가 SSH 권한 차단으로 Task 3 진입 불가 → belle 이 허용 규칙
   추가(`Bash(ssh -p 11638 ...)`) 후 오케스트레이터가 대행. 이후 실행자 트랜스크립트
   소멸로 SUMMARY 도 오케스트레이터 작성.

## LLM 학습 영향

Gemini 호출은 추론(기계 눈 방출 판정)뿐 — 운영 2회, 학습 전송 0. 눈 원장 신규:
S3 `results/fvcNXzEqKjgqVxRPVSj1iwFnIpn2/p34fresh1786458292/eye/` 2건 + 로컬 스윕
원장(evidence/*/ledger.json)은 5ddc1e3a 커밋분. Phase 22 플라이휠 후보 누적.

## 재료 좌표

- 새 doc: uid `fvcNXzEqKjgqVxRPVSj1iwFnIpn2` / `p34fresh1786458292` (score 60)
- Pod: cv8poc707mqtxh 유지 (스톱/터미네이트 안 함). 서버 = 5ddc1e3a.
  재분석 로그 = `/workspace/_ufb_reanalysis.log`
- 카드 실물: `evidence/pod_cards/` (confirmed 2 + 구 스테이지 산출 3)
- 검증 드라이버: `verify_local.py` / 스윕·결정론·0장 verdict = `evidence/*.json`

## 다음 (belle 판정 대기)

1. 카드 2장(왼팔꿈치 5.3s · 왼골반 16.7s) 육안 판정 — 앱 또는 evidence/pod_cards/.
2. 왼무릎 신규 발굴 사이클 진행 여부 (영상에 없는 결함 카드 — 풀 게이트 + 사전 대조).
3. 눈 기각 2건(승인 정지 r01 환각·r00 unclear)의 처분 — 승인 영상 쪽 재검토 대상.

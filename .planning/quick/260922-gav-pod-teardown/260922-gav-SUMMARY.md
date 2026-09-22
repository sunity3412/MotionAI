---
quick_id: 260922-gav
slug: pod-teardown
date: 2026-09-22
status: complete
---

# Quick 260922-gav — pod_teardown.py 안전 수리 2건 (완료)

## 판정

**둘 다 고쳤고 실측으로 닫았다.** 단 **실제 종료 실행은 하지 않았다** — 같은 시각
Mode1 측정이 `m2czli3w4wqpe5` 에서 돌고 있어 종료 경로를 밟으면 측정이 죽는다.
그래서 `_gql` 조회와 필터 선택을 **분리해서** 검증했다.

## 결함 ① Cloudflare 1010 — 수정 + 검증

`_gql` 에 `User-Agent: sunity-motion-pod-teardown/1.0` 추가.

```
[확인] 수정 전: urllib 기본 UA → HTTP 403, body "error code: 1010"
[확인] 수정 후: 같은 키·같은 쿼리 → 200, pods 2건 반환
[확인] UA 3종 대조 — None=403 / curl/8.7.1=200 / 커스텀=200
       → 키·권한 문제가 아니라 UA 차단이다
```

## 결함 ② 무인자 실행이 계정 전체 종료 — 수정 + 검증

`OWNED_NAME_PREFIX = "sunity-motion"` 도입. 무인자 실행은 이름이 그 접두사로
시작하는 Pod 만 종료하고, 나머지는 **종료하지 않고 건너뜀 메시지**를 출력한다.
명시적으로 id 를 인자로 주면 그대로 존중한다(사람의 의도).

```
[확인] 드라이런(종료 호출 없이 선택만):
       종료대상 = ['m2czli3w4wqpe5']            (sunity-motion-serve2)
       건너뜀   = [('u9f1ykw4e89cxz', 'sunity-pipe-translator-q9b')]
```

## 왜 ②가 ①보다 무거운가

이 스크립트는 2026-09-22 아침에 belle 에게 *"제가 못 끄면 이걸 누르세요"* 로
안내됐다. 그 시각 계정에는 다른 프로젝트(Sunityfunding) 학습 Pod 이 돌고 있었다.
①이 없었으면 스크립트가 403 으로 죽어 아무 일도 안 났겠지만, ①만 고치고 ②를
놓쳤다면 **안내대로 눌렀을 때 남의 학습이 죽었다.** 두 결함이 서로를 가리고 있었다.

## 남은 것 (이번 범위 밖)

- `[미확인]` 종료 경로 전체(terminate → Lambda 자리표시자 → SSM) 를 끝까지 실행한
  검증은 없다. 오늘 측정이 끝나고 Pod 을 내릴 때 그 실행이 곧 검증이 된다.
- 접두사 방식의 한계: `sunity-motion` 으로 시작하지 않는 이름으로 우리 Pod 을
  만들면 무인자 실행이 놓친다. 놓치는 쪽을 택한 것은 의도다(fail-safe).

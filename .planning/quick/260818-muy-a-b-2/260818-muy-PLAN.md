---
phase: quick-260818-muy
quick_id: 260818-muy
slug: a-b-2
date: 2026-08-18
status: planned
description: >
  일러스트 골격 조건부 A/B 2장 (belle "일러스트가 최대의 숙제, 언넝 해보자" 2026-08-18).
  08-17 미승인 제안의 실물화 — 같은 동작·같은 순간으로 [A] 현행(자세를 텍스트로 부탁) vs
  [B] 골격 조건부(RTMW 133관절로 그 프레임의 뼈대 이미지를 만들어 **입력**으로 넣음) 를
  나란히 만들어 belle 판정을 받는다. 대상 = 어제 3회 재시도 후에도 실패한 5장 중
  실패 사유가 "전신을 그림(구도)"+"표시가 엉뚱한 관절(위치)" 로 가장 또렷한 ref-pdshape--leg.
  판정은 게이트 통과가 아니라 belle 눈이다(08-17: "게이트 통과 숫자를 성적으로 쓰지 말 것").
wave: 1
depends_on: []
type: execute
plan: 01
autonomous: true
requirements: [QUICK-260818-MUY]
files_modified:
  - .planning/quick/260818-muy-a-b-2/extract_skeleton.py
  - .planning/quick/260818-muy-a-b-2/generate_ab.py
  - .planning/quick/260818-muy-a-b-2/out/
must_haves:
  truths:
    - "예측을 생성 전에 박제한다 — 08-17 규율(재고→예측 박제→belle 확인). 판정 후 자를 고르지 않는다"
    - "A 와 B 는 입력 프레임·앵커·프롬프트 본문·모델·해상도가 동일하고 오직 '골격 이미지 입력 + 그것을 따르라는 한 문단' 만 다르다 — 그래야 차이가 골격 때문이다"
    - "골격은 그 프레임에서 RTMW 로 실제 추출한 좌표로 그린다. 학습 캐시(53프레임 저fps·12관절)를 재사용하지 않는다"
    - "belle 판정 재료는 원본 크기 2장을 나란히 + 어느 쪽이 A/B 인지 가린 채 낸다 (눈가림). 정답은 판정 후 공개"
    - "app/assets/illustrations 는 손대지 않는다 — 반영은 belle 판정 후 별도"
  artifacts:
    - path: ".planning/quick/260818-muy-a-b-2/extract_skeleton.py"
      provides: "Pod 에서 실행 — 기준 영상 t초 프레임 → RTMW 133 → 뼈대 PNG(cropBox 적용) + 좌표 JSON"
    - path: ".planning/quick/260818-muy-a-b-2/generate_ab.py"
      provides: "generate.py 의 build_prompt 재사용 + B 팔에만 골격 파트 추가. 동작명 분기 0"
    - path: ".planning/quick/260818-muy-a-b-2/PREDICTION.md"
      provides: "생성 전 박제한 예측"
---

# quick-260818-muy — 골격 조건부 A/B

## 왜 골격인가 (어제 실패 원문이 말해준 것)

어제 3회 재시도로도 못 넘은 5장의 실패 사유는 두 종류뿐이다:

```
구도   "다리 클로즈업으로 그려라" → 전신을 그린다        (pdshape--leg 3/3, kip-up 2/3)
위치   "무릎에 표시하라"          → 사타구니에 그린다     (pdshape--leg 2/3)
```

둘 다 **"어디"를 말로 부탁했는데 못 지킨 것**이다. 골격 이미지는 그 "어디"를 픽셀로 준다 —
무릎이 어느 좌표인지, 프레임 안에 어느 부위까지 들어오는지가 입력에 박힌다.

## 하지 않는 것

- 5장 전부 재생성 안 함. **2장으로 방향만 가른다.** 갈리면 그때 5장.
- 게이트 통과를 목적으로 하지 않음. belle 눈이 판정.

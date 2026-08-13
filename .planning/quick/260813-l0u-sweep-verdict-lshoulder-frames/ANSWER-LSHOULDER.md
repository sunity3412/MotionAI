# 피디쉐입 왼어깨 — belle 질문 답변 재료 (quick-260813-l0u)

belle 08-13 질문 원문: "너무 미세해서 뭘 봐야할지 모르겠네 영상은 어떻지..?"

대상 카드 (스윕 시트 5번):
[../260813-ivs-5/evidence/sweep_cards/pdshapefault/zoom_angle_vs_reference__left_shoulder.png](../260813-ivs-5/evidence/sweep_cards/pdshapefault/zoom_angle_vs_reference__left_shoulder.png)
— record = pdshapefault **r02** `angle_vs_reference__left_shoulder`, freeze u3.222/r2.00
(라벨 공간, sweep_verdict.json 정본).

---

## 1. 이 카드가 무엇을 지적하는 감점인가 (P35 doc 정본, recordId `r02:angle_vs_reference__left_shoulder`)

역립 홀드에서 왼쪽 어깨(겨드랑이) 각 — 팔과 몸통 사이 각 — 이 기준(정은지) 대비
**26.79도** 벌어져 있고, 허용 오차 **20.0도**를 **6.79도** 초과해 **-8.2점** 감점된
record 다 (ruleId `angle_vs_reference_over_tol_linear`, source geometry, exerciseId
`shoulder_unstable`, 측정 순간 atVideoSec **3.222** — 라벨 공간). doc 원문:

- statusLine: "왼쪽 어깨(겨드랑이) 각도가 기준 셰이프와 차이가 있어요"
- whyLine: "어깨로 버티는 지지 각이 무너지면 셰이프가 한쪽으로 쏠리는 부분이에요"
- cueLine: "목표는 거꾸로 매달려 한 다리는 걸고 한 다리는 깊게 접은 모양을 그대로
  지키는 거예요. 어깨가 귀 쪽으로 말리지 않게 눌러 잡은 채, 팔과 몸통 사이 각을
  기준 자세에 겹쳐 맞춰보세요"

### 수치 불일치 (그대로 보고 — 해석 발명 0)

- **감점 산정측** (doc.json r02): deviation **6.79** / measuredValue 26.79 /
  tolerance 20.0 / atVideoSec 3.222
- **카드 표시측** (sweep_verdict.json `.pdshapefault.attached.comparisons`
  left_shoulder): deficitDeg **70.0** / userVideoSec 3.556 / refVideoSec 2.222
- 두 값은 출처가 다른 값이며 서로 다르다. 왜 다른지는 이 사이클에서 측정하지
  않았다 (미측정 = 단정 금지) — 다음 라운드 입력으로만 남긴다.

"너무 미세해서"의 수치 배경: 감점 산정측 기준으로 초과분이 6.79도다 — 360px 크롭
패널에서 한 자릿수 도(度) 차이는 원 마크(부위 지시)만으로는 갈리지 않는 크기이고,
v7 승인 문법은 이것을 각도선 + 수치(121°/147°)로 갈랐다 (아래 회수물 2).

---

## 2. 회수물 1 — freeze 순간 전신 프레임 짝 (영상에서 보이는 그대로)

[evidence/lshoulder_fullframe_pair.png](evidence/lshoulder_fullframe_pair.png)
(좌 = user 풀프레임 2160x3840 / 우 = ref 풀프레임 1080x1920, 같은 높이 스케일,
흰 6px 구분선 — 마크·자막 추가 0, 원본 그대로)

- 프레임 선정 검증 (1줄): naive 초 환산이 아니라 **카드 패널 content-match** —
  후보창(user 프레임 66~114 / ref 12~75, 30fps)을 크롭 박스(measure.json crops,
  user [326,1758,907] / ref [169,802,454]) -> 360px 리사이즈 -> 카드 패널 grayscale
  평균 절대 diff 최소로 기계 선정, 기록 =
  [evidence/frame_match.json](evidence/frame_match.json).
- 선정 결과: user **프레임 96** (실초 3.2s, diff 5.44 — 이웃 8.74/9.06 대비 뚜렷한
  골) / ref **프레임 60** (실초 2.0s, diff 2.48 — 이웃 7.44/7.69 대비 뚜렷한 골).
  cropLines 참고값(user_frame=32 rep 공간 x step 3 = 96, ref_video_idx=20 x 3 = 60)
  과 독립 일치.
- 육안 대조 (frames-before-numbers): 선정 크롭 vs 카드 패널 나란히 열어 확인 —
  양측 모두 동일 장면 (카드와의 차이는 구운 원 마크 + 초 라벨뿐).

## 3. 회수물 2 — v7 승인 비교 영상의 왼어깨 freeze 프레임

[evidence/lshoulder_v7_freeze.png](evidence/lshoulder_v7_freeze.png)
(출처 = `s3://sunity-motion-pilot-videos/proto/phase35/pdshape_v3.mp4`, read-only
GET 1회 — 1224x1080, 30fps, 1769프레임)

- 정지 run 스캔 (인접 프레임 diff < 0.5 가 0.8s 이상): 4개 run 검출, 그중
  **run 1 (13.10~24.57s, 대표 프레임 565)** 이 왼어깨 구간 — 구운 자막
  "왼쪽 어깨(겨드랑이) 각도가 기준 셰이프와 차이가 있어요. 어깨가 귀 쪽으로
  말리지 않게 눌러 잡은 채, 팔과 몸통 사이 각을 기준 자세에 겹쳐 맞춰보세요"
  로 특정 (run 0 은 오른팔꿈치 구간 — 대조로 배제).
- belle "영상은 어떻지"의 직접 답: v7 승인본은 **전신 프레임 위에** 각도선 V +
  수치(**user 121° / ref 147°**)를 구워서 나갔다 — 같은 순간을 카드는 어깨 크롭
  + 원 마크로, v7 은 전신 + 각도선 + 수치로 보여준다.

## 4. 한계 (박제)

- 캐시 영상(user.mp4/ref.mp4)은 세션 scratchpad 휘발 — 이 사이클에서 소비 완료,
  보존물은 리포의 회수 프레임 실물뿐 (원본 영상 정본은 S3).
- 이 카드(r02)는 08-11 실눈 기각 이력이 **없는** record 다 — 눈 스텁 때문에
  방출된 카드(피디쉐입 r01·피터팬 r00)가 아니다. 단 이번 스윕 자체가 machine_eye
  스텁이라 r02 의 실눈 판정 기록은 별도로 없다.
- v7 프레임의 타임라인은 렌더 영상 자체 시간(freeze 구간 삽입)이라 라벨 공간
  atVideoSec 3.222 와 직접 비교 불가 — 구간 특정은 구운 자막 내용으로 했다.
- 카드측 deficitDeg 70.0 vs doc deviation 6.79 불일치는 §1 대로 미해석 보고만.

## 회수물 사본 (보드 게시용, 오케스트레이터 몫)

- `/Users/Shared/sunity-sweep-260813/왼어깨-영상전신짝.png` (= 회수물 1)
- `/Users/Shared/sunity-sweep-260813/왼어깨-승인영상프레임.png` (= 회수물 2)

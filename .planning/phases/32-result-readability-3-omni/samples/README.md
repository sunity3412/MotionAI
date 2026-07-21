# 32-08 샘플 게이트 재료 (D-18 오디오 방식 · D-21 일러스트 품질)

belle 실기기 청취/검수용 샘플 세트. **belle이 결정할 것 2가지:**

1. **오디오(D-18):** 재생 중 큐 음성 = **A. 기기 TTS** vs **B. 클라우드 TTS(Polly)** — 같은 코칭 문장 2종 청취 비교.
2. **일러스트(D-21):** "형태감 있는 고품질 인체 일러스트" 품질이 도입 기준을 넘는지 → **도입** vs **실프레임+텍스트 정직 폴백**.

> 이 결정을 답하면 Claude가 `32-GATE-DECISIONS.md` "## 샘플 게이트 (D-18/D-21)" 섹션에 적재하고,
> **B안 확정 시** 백엔드 TTS 스테이지(32-12 Task 2)를 별도 플랜 **32-16**으로 물리 분리한다(W-2).
> 오디오 구현 자체는 게이트 확정 후 **32-12**가 담당한다(이 플랜은 재료 제출까지).

---

## 코칭 문장 (두 TTS 동일 · 문구집 실제 cueLine + whyLine)

문구집(`backend/data/phrasebook.json`) `__common__.leg_extension` 의 **행동문(cueLine) + 이유문(whyLine)** 조합 2문장. 수치 0 (D-09 준수), 안전 결함 아님(D-14 무관):

```
발끝으로 천장을 길게 밀어낸다는 느낌으로 다리를 쭉 뻗어보세요.
다리 라인이 끝까지 뻗지 않으면 심사에서 신전 완성도로 감점되는 부분이에요.
```

---

## 1. 오디오 샘플 (D-18)

### A안 — 기기 TTS (expo-speech / iOS AVSpeechSynthesizer)

**belle 실기기 청취 절차 (iPhone, 약 1분):** 실제 기기 TTS 엔진을 직접 듣는다.
iOS 단축어의 '텍스트 말하기'와 `expo-speech`(`Speech.speak(text, {language:'ko-KR'})`)는
**동일한 AVSpeechSynthesizer 엔진·동일 시스템 음성**을 쓰므로 실기기 출력을 대표한다.

1. 아이폰 **단축어(Shortcuts)** 앱 → 우상단 **+** → 새 단축어.
2. **동작 추가** → `텍스트 말하기`(Speak Text) 검색 후 추가.
3. 위 코칭 문장 2줄을 그대로 **붙여넣기**.
4. 음성: 기본(시스템)으로 두면 됨. 더 자연스러운 음성을 원하면
   **설정 › 손쉬운 사용 › 말하기 콘텐츠 › 음성 › 한국어**에서 원하는 음성(유나 등)을 받아두면 반영됨.
5. **재생(▶)** → 실기기 시스템 TTS로 문장을 듣는다. (이 소리가 앱에서 나올 실제 음질)

**참고 녹음 파일(비대표):** `tts_device_approx.m4a`
- macOS `say -v Yuna` 로 만든 **데스크톱 음성 근사치**다. iOS 기기 음성과 **다르다** → **비대표(참고용)**.
  실제 판단은 위 iPhone 단축어 청취로 할 것. 이 파일은 "대략 이런 톤" 참고에만 사용.
- 재생: Finder/Preview 에서 더블클릭 (Mac 기본 재생).

### B안 — 클라우드 TTS (AWS Polly, neural, Seoyeon)

**파일:** `tts_polly.mp3` — belle 실기기로 전달(AirDrop/카톡)해 **같은 iPhone 스피커**로 A안과 비교 청취.
- Polly neural 음성 `Seoyeon`(ko-KR), 사전 생성(mp3) → 앱은 재생만(expo-audio). 78자, 비용 무시 가능 수준.
- Mac 에서 바로 듣기: Finder 더블클릭.

### 공통 전제 (★결정 재료 — 어느 쪽이든 해당)

- **어느 방식이든 Expo 오디오 native 모듈 1개 추가가 필요**하다(A=`expo-speech ~14.0.8`, B=`expo-audio ~1.1.1`).
  둘 다 expo 공식·SDK 54 번들 매니페스트 등재·Package Legitimacy [OK] (D-18 예외 승인 항목).
- **native 모듈은 OTA로 기존 TestFlight 바이너리에 배포할 수 없다.** 32-12 에서 앱 버전 bump
  (1.0.0→1.1.0, runtimeVersion=appVersion) + **새 EAS build + TestFlight 제출 + belle 재설치**가 1회 수반된다.
- A/B 어느 쪽이든 오디오는 **이번 phase(32-12) 안에서 출시 완결**된다. B안 = 이연 아님 —
  구현 비용 차이만 있다(B는 백엔드 Polly 합성 스테이지 + S3 playback asset + 계약 확장 + IAM + SAM 배포).
- **B안 확정 시:** 32-12 Task 2(백엔드 TTS 스테이지, 파일 9개)를 별도 플랜 **32-16**(wave 7)으로 분리(W-2).

### 재생성 커맨드 (재현용)

```bash
# 코칭 문장 (동일)
SENTENCE="발끝으로 천장을 길게 밀어낸다는 느낌으로 다리를 쭉 뻗어보세요. 다리 라인이 끝까지 뻗지 않으면 심사에서 신전 완성도로 감점되는 부분이에요."

# A안 참고 녹음 (비대표 — macOS 데스크톱 음성)
say -v Yuna -o tts_device_approx.aiff "$SENTENCE"
afconvert tts_device_approx.aiff tts_device_approx.m4a -d aac -f m4af && rm tts_device_approx.aiff

# B안 Polly (ap-northeast-2, --profile sunity-motion 필수)
aws polly synthesize-speech --engine neural --voice-id Seoyeon --language-code ko-KR \
  --output-format mp3 --text "$SENTENCE" \
  --profile sunity-motion --region ap-northeast-2 tts_polly.mp3
```

---

## 2. 일러스트 샘플 (D-21)

**기준선(belle):** "형태감 있는 고품질 인체 일러스트". 캐릭터화 X, 졸라맨(단순 선) X.
품질이 이 바를 넘으면 **도입**, 미달이면 **시각 표현 없이 실프레임+텍스트로 정직 폴백**.

**한눈에 보기:** `illust_gallery.html` (Finder 더블클릭 → 3안 나란히 + 폴백 설명).

| 파일 | 생성 모델 | 스타일 |
|------|-----------|--------|
| `illust_variant1_pro.jpg` | Gemini `gemini-3-pro-image` | 클린 에디토리얼 벡터 + 코럴 큐 흐름 (측면, 익명 무표정) |
| `illust_variant2_pro.jpg` | Gemini `gemini-3-pro-image` | 소프트 준실사 해부 일러스트 + 코럴 라인 (핸드드로잉 톤) |
| `illust_variant3_flash.jpg` | Gemini `gemini-3.1-flash-image` | 벡터 실루엣 + 코럴 아웃라인 (저비용 티어 품질 비교용) |

상황: **무릎 접기 → 다리 신전(leg_extension) 외부 큐** 순간. 코럴 강조선 = "발끝으로 천장을 길게" 큐 방향.

### Provenance (리뷰 반영 — 필수 기록)

- **생성 도구:** Google Gemini 이미지 모델(`gemini-3-pro-image` / `gemini-3.1-flash-image`), belle Gemini API 키(SSM `/sunity/motion/gemini-api-key`). REST `generateContent`, `responseModalities:[TEXT,IMAGE]`, `aspectRatio 3:4`.
- **프롬프트 요지:** 익명 운동 인체가 폴 위에서 한 다리를 곧게 신전(발끝 포인)한 자세, **형태·볼륨 있는 고품질 일러스트(졸라맨/캐릭터 아님)**, 무표정·무얼굴(익명), 밝은 배경, 신전 다리에 코럴 `#FF4B33` 강조, 텍스트/워터마크 없음. (전문은 아래 "재생성 커맨드"의 PROMPT.)
- **사용권:** Gemini API 생성물은 Google 약관상 사용자 소유·상업 사용 가능(불가시 SynthID 워터마크 포함). **최종 상업 사용 확정은 belle 판단** — 도입 결정 시 약관 재확인 1회.
- **정은지 likeness 회피(확인):** 프롬프트에 **실존 인물 사진·이름 미사용**, "anonymous / no recognizable facial features" 명시. 산출물 3종 모두 얼굴 특징 없음(익명) — 특정인(정은지 포함) 닮음 회피됨.
- **런타임 invariant:** 도입 시 **정적 에셋(빌드타임 번들)** 로만 사용 — **런타임 생성 AI 0**(32-RESEARCH). 제작만 오프라인.

### 재생성 커맨드 (재현용)

```bash
export GEMINI_KEY=$(aws ssm get-parameter --name /sunity/motion/gemini-api-key --with-decryption \
  --profile sunity-motion --region ap-northeast-2 --query Parameter.Value --output text)
MODEL="gemini-3-pro-image"   # 또는 gemini-3.1-flash-image
PROMPT="High-quality editorial illustration of an anonymous athletic woman performing a pole-fitness pose with one leg fully extended straight upward and toes strongly pointed... (익명·형태감·졸라맨 아님·코럴 #FF4B33 강조·텍스트/워터마크 없음)"
# v1beta generateContent(responseModalities:[TEXT,IMAGE], imageConfig.aspectRatio 3:4) → inlineData(base64) → 파일 기록
# (반환 mime 가 image/jpeg 라 확장자 .jpg 로 저장)
```

---

## 파일 목록

- `tts_device_approx.m4a` — A안 참고 녹음(**비대표**, macOS 데스크톱 음성)
- `tts_polly.mp3` — B안 클라우드 TTS(Polly Seoyeon neural)
- `illust_variant1_pro.jpg` / `illust_variant2_pro.jpg` / `illust_variant3_flash.jpg` — 일러스트 3안
- `illust_gallery.html` — 일러스트 3안 + 폴백 설명 뷰어
- `README.md` — 이 문서

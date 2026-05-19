# /app/CLAUDE.md — React Native 앱

---

## 핵심 규칙

```
- UI 작업 전 반드시 design.md 읽기
- 브랜드 컬러 #FF4B33 절대 변경 금지
- 다크 테마 전용. 라이트 모드 없음.
- 미설계 화면도 design.md 기준으로 자체 구현 (멈추지 말 것)
```

## 네비게이션 구조

```
[온보딩] 인트로 → 로그인/회원가입 → 알림설정 → 레벨선택 → 종목선택 → 플랜안내 → 홈
[메인] 바텀탭 4개: 홈 / 분석 / 기록 / 마이
[분석 플로우] 분석탭 → 영상소스선택 → 카메라/갤러리 → AI로딩 → 기준모션선택 → 결과
```

## MVP 화면 우선순위

```
Phase 1 (파일럿 필수):
  1. 온보딩 (간소화 — 게스트 모드 허용)
  2. 영상 업로드 화면
  3. AI 분석 로딩 화면 (단계별 메시지)
  4. 분석 결과 화면 (Mode 3: 자기 비교)
  5. 기준 모션 선택 화면
  6. 분석 결과 화면 (Mode 1: 정은지 비교)

Phase 2 (파일럿 이후):
  결제 플랜, 게이미피케이션, 실시간 카메라
```

## 주요 컴포넌트

```
원형 점수 게이지     : 외곽 트랙 + 채워지는 원호 + 중앙 점수
바텀 네비게이션      : 반투명 블러 배경, 활성탭 #FF4B33
CTA 버튼            : 전체너비, 높이 54pt, radius 12pt
카드                : 배경 #1E1E2E, radius 16pt
분석 로딩           : 단계별 메시지 (스피너 금지)
레벨 다이얼          : PanResponder로 원형 슬라이더 직접 구현
```

## 차트 라이브러리

```
Victory Native        : 성장 그래프 (시계열 관절 데이터 — 추천)
react-native-gifted-charts : 세부 점수 차트 (상체/하체/코어)

설치:
  npm install victory-native
  npm install react-native-gifted-charts
  expo install react-native-svg   ← 두 라이브러리 공통 의존성
```

## 영상 업로드 방식 (S3 Presigned URL)

```
Lambda를 통해 영상 전달 금지 (용량 초과, 타임아웃)
→ S3 Presigned URL 직접 업로드 방식 사용

흐름:
  앱 → Lambda에 업로드 URL 요청
  Lambda → S3 Presigned URL 발급 → 앱으로 반환
  앱 → S3에 직접 PUT 업로드
  S3 → Lambda 트리거 → 분석 파이프라인 실행
```

## 앱스토어 AI 앱 심사 주의

```
Apple: AI 동작을 App Intents 스키마로 사전 정의 필수
       통제 불가 Agentic AI 기능은 리젝 대상
Google: 과도한 시스템 API 접근 시 자동 반려
→ 카메라/갤러리 권한 요청 시 데이터 수집 목적 명확히 고지
```

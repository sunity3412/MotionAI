# CLAUDE.md — Sunity AI Coach
> 작업 시작 전 반드시 이 순서로 읽을 것: CLAUDE.md → design.md → plan.md

---

## 1. 프로젝트 한 줄 요약

폴스포츠 수강생이 연습 영상을 올리면 AI가 프로 선수 모션과 비교해 자세 교정 피드백을 주는 모바일 앱.

**북극성**: 폴스포츠 학원에서 수강생이 혼자 앱을 켜고 분석 결과를 확인하는 것.

---

## 2. 파일럿 목표 (개발의 최우선 기준)

```
Step 1. 앱 MVP 완성 → 정은지 선수(폴스포츠 세계챔피언)에게 시연
Step 2. 정은지 선수 촬영 → 백엔드로 업로드 → 기준 모션 자동 등록
Step 3. 폴스포츠 학원 파일럿 실증

파일럿 성공 기준:
  수강생이 혼자서 아래 두 가지를 완료할 수 있어야 함
  - Mode 3: 본인 영상 2개 비교 → 성장 확인
  - Mode 1: 정은지 모션 불러와 비교 → 전문가 기준 점수 확인
```

**파일럿 최소 요건**
```
✅ 영상 업로드 → 관절 분석 → 결과 화면 (Mode 3)
✅ 정은지 기준 모션 1개 이상 → 비교 점수 (Mode 1)
✅ TestFlight로 게스트 모드 바로 사용 가능
❌ 결제 플랜 불필요   ❌ 회원가입 강제 불필요
```

---

## 3. 기술 스택 (결정 완료 — 변경 금지)

```
앱        : React Native + Expo (TypeScript)
백엔드     : AWS Lambda (Python) + API Gateway
DB        : Firebase Firestore
스토리지   : AWS S3
ML        : YOLO11 → ViTPose-S → MotionDTW (FastDTW)
LLM       : Cerebras (빠른 추론)
결제       : RevenueCat (iOS/Android 통합)
배포       : EAS Build (Expo)
```

---

## 4. 디자인 시스템

> **모든 UI 작업 전 design.md 필독.**

```
브랜드 컬러 : #FF4B33  (절대 변경 금지)
폰트        : Pretendard
테마        : 라이트 전용 (다크 모드 구현 불필요)
배경        : 가입/로그인/서브 = 흰색(#FFFFFF), 홈 = 브랜드 그라디언트.
             다크 블랙 배경 금지. 상세는 design.md §5-1 참조.
```

미설계 화면도 멈추지 말 것. design.md 규칙 따라 자체 판단으로 구현.
(알림창, 에러 팝업, 권한 요청 등 모두 포함)

---

## 5. 세부 컨텍스트 파일 위치

```
ML 파이프라인 작업   → /ml/CLAUDE.md
앱 (React Native)   → /app/CLAUDE.md
백엔드 (Lambda)     → /backend/CLAUDE.md
현재 할 일          → /plan.md         ← 매 세션 반드시 확인
개발 원칙/에이전트   → /docs/principles.md
화면 스펙 (IA)      → /docs/ia.md      ← 특정 화면 작업 시 참조
```

> IA 참조 방법: "docs/ia.md에서 AC-VID 관련 스펙 읽고 구현해줘"

---

## 6. 멀티 플랫폼 전환 프로토콜

```
전환 순서: Claude Code ↔ Cursor AI (Opus) ↔ Codex

전환 전 반드시:
  1. plan.md 업데이트 (완료/진행중/다음 할 것)
  2. 미완성 파일에 TODO 주석 삽입

새 플랫폼 세션 시작:
  CLAUDE.md → design.md → plan.md 읽기 → "현재 상태 요약해줘" 확인
```

**모델 선택**
```
일반 구현    : claude-sonnet-4-6
복잡한 설계  : claude-opus-4-6 (필요할 때만)
UI 빠른 생성 : Codex Sub-Agents
```

---

## 7. 코드 품질 원칙

```
- 작은 단위로 작업. 한 번에 전체 코드베이스 변경 금지.
- 의미있는 테스트만. 수치 채우기 금지.
- 이모지 금지. 슬롭 코드 금지.
- 막히면 "Do not work yet" 후 질문 먼저.
- 작업 완료 시 plan.md 업데이트.
```

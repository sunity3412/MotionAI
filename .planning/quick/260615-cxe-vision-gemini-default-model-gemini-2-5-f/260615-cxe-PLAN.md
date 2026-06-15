---
phase: 260615-cxe
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py
autonomous: true
requirements:
  - VISION-MODEL-DEFAULT
must_haves:
  truths:
    - "DEFAULT_GEMINI_MODEL 폴백 리터럴이 'gemini-2.5-pro' 이다"
    - "env GEMINI_MODEL 재정의 메커니즘이 그대로 살아 있다"
    - "주석이 2.5-pro (vision-only 2.5 예외)를 정확히 설명한다"
  artifacts:
    - path: backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py
      provides: "vision/recognizer 경로 Gemini 모델 default"
      contains: "gemini-2.5-pro"
  key_links:
    - from: gemini_moment_extractor.py
      to: Gemini API
      via: DEFAULT_GEMINI_MODEL fallback
      pattern: "gemini-2\\.5-pro"
---

<objective>
vision/recognizer 경로의 Gemini 기본 모델을 gemini-2.5-flash 에서 gemini-2.5-pro 로 변경한다.

Purpose: belle 지시 (2026-06-15) — 비전 경로는 2.5-pro 를 써야 한다. Google 이 아직
video multimodal 을 완전 지원하는 3.x 모델을 출시하지 않았으므로 2.5-pro 가 올바른
중간 모델이다 (memory: gemini-latest-model-versions — vision-only 2.5 예외 적용).
모델 문자열 `gemini-2.5-pro` 는 live ListModels 로 검증 완료 (generateContent + multimodal
지원, -preview suffix 없음).

Output: DEFAULT_GEMINI_MODEL 폴백 리터럴 + 주석 블록 수정. 다른 코드 경로 무변경.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: DEFAULT_GEMINI_MODEL 폴백 + 주석 업데이트</name>
  <files>backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py</files>
  <action>
    파일 lines 53-57 의 주석 블록과 DEFAULT_GEMINI_MODEL 정의를 교체한다.

    변경 범위:
      - lines 53-55 주석: 현재 "default = 'gemini-2.5-flash' — 현재 stable Flash family…"
        → 아래 새 주석으로 교체 (memory: gemini-latest-model-versions 박제)
      - line 57 리터럴: "gemini-2.5-flash" → "gemini-2.5-pro"
      - lines 55-56 (3.x env 전환 안내): 내용을 유지하되, 3.x vision 출시 시 교체 맥락으로 표현 업데이트

    새 주석 (lines 53-56 교체 대상, 이하 한글 prose):
    ```
    # vision-only 2.5 예외 (memory: gemini-latest-model-versions, 2026-06-15):
    #   Google 이 video multimodal 을 완전 지원하는 3.x 모델을 아직 미출시.
    #   따라서 이 경로에 한해 2.5-pro (stable, suffix 없음) 가 올바른 중간 모델.
    #   ListModels 2026-06-15 박제: gemini-2.5-pro = generateContent + multimodal 지원.
    #   3.x video-capable 모델 출시 시 env GEMINI_MODEL=gemini-3.x-pro 로 즉시 전환 가능.
    ```

    교체 후 line 57:
    ```python
    DEFAULT_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")
    ```

    규칙:
      - line 42 의 Phase 5 D-13 역사 주석(lines 42-52)은 건드리지 말 것 — 히스토리 보존.
      - lines 59 이하 _COORDINATE_REJECT_PATTERNS 는 완전 무변경.
      - 이모지 금지. CLAUDE.md §7.
  </action>
  <verify>
    <automated>grep -n "gemini-2.5-pro" /Users/kimtaesung/Dev/SunityMotion/backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py && grep -c "gemini-2.5-flash" /Users/kimtaesung/Dev/SunityMotion/backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py | grep -qx "0" && echo "PASS: flash 완전 제거"</automated>
  </verify>
  <done>
    - DEFAULT_GEMINI_MODEL 폴백이 "gemini-2.5-pro" 이다
    - "gemini-2.5-flash" 문자열이 파일에 0건이다
    - env GEMINI_MODEL 재정의 패턴이 그대로이다 (os.environ.get("GEMINI_MODEL", ...) 구조 유지)
    - 주석이 vision-only 2.5 예외 이유와 3.x 전환 경로를 정확히 기술한다
    - lines 42-52 히스토리 주석 무변경
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Lambda env → DEFAULT_GEMINI_MODEL | GEMINI_MODEL env 미설정 시 폴백 리터럴이 사용됨 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-cxe-01 | Tampering | DEFAULT_GEMINI_MODEL 리터럴 | accept | 이 변경은 단순 문자열 교체; API key 는 SSM Parameter Store 관리 — 무변경 |
| T-cxe-SC | Tampering | npm/pip/cargo installs | accept | 이 plan 에 패키지 설치 없음 |
</threat_model>

<verification>
변경 후 확인:

1. grep 으로 "gemini-2.5-pro" 가 line 57 에 존재하는지 확인
2. grep -c 로 "gemini-2.5-flash" 가 0건인지 확인
3. python -c "import ast; ast.parse(open('backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py').read()); print('syntax OK')" 로 파싱 오류 없음 확인
</verification>

<success_criteria>
- DEFAULT_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro") 한 줄로 정착
- gemini-2.5-flash 문자열 완전 제거 (0건)
- 주석: vision-only 2.5 예외 이유 + ListModels 날짜 박제 + 3.x 전환 안내 포함
- 기존 히스토리 주석(lines 42-52) 및 _COORDINATE_REJECT_PATTERNS(lines 59+) 무변경
</success_criteria>

<output>
완료 후 .planning/quick/260615-cxe-vision-gemini-default-model-gemini-2-5-f/260615-cxe-01-SUMMARY.md 생성
</output>

# Phase 1: PoseEngine 추상화 + MediaPipe 어댑터 + 폴 축 정렬 + NLF R&D 격리 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-31
**Phase:** 1-PoseEngine 추상화 + MediaPipe 어댑터 + 폴 축 정렬 + NLF R&D 격리
**Areas discussed:** MediaPipe variant 선택, NLF R&D 격리 방식, 폴 축 검출 방법, MediaPipe vs NLF 회귀 검증 기준

---

## MediaPipe Variant 선택

### Q1: BlazePose variant
| Option | Description | Selected |
|---|---|---|
| BlazePose Heavy | SOTA 정확도, 가림/접힌 자세 강함, 200~400ms/frame | ✓ |
| BlazePose Full | 정확·속도 균형, 100~150ms/frame | |
| BlazePose Lite | 온디바이스 실시간용, 정확도 낮음 | |

**User's choice:** BlazePose Heavy
**Notes:** 폴 가림 challenge에 정확도 우선

### Q2: API 선택
| Option | Description | Selected |
|---|---|---|
| MediaPipe Tasks API | 신 API, 공식 권장, 장기 지원 | ✓ |
| Solutions (legacy) mp.solutions.pose | 구 API, deprecated 예고 | |

**User's choice:** MediaPipe Tasks API

### Q3: 3D vs 2D
| Option | Description | Selected |
|---|---|---|
| world landmarks(metric 3D) 기본 | BlazePose GHUM, 근사 미터단위 3D, 점대출·각도 필수 | ✓ |
| image landmarks(2D + 상대z) | 2D 정확, z는 명암 깊이. UI 오버레이용 | |
| 둘 다 출력 | 분석 = world, UI = image. PoseFrame에 두 필드 | |

**User's choice:** world landmarks 기본 (image도 함께 출력 — D-03 종합 결정)

### Q4: Keypoint 스키마
| Option | Description | Selected |
|---|---|---|
| COCO-17 유지 + MediaPipe 33→17 매핑 | 기존 코드 재사용, 마이그레이션 안전 | |
| MediaPipe 33 확장 | 손끝/발끝/얼굴 디테일 살림, 전 스코어링 코드 변경 | |

**User's choice (free text — 정책 수준 결정):**
- 원본 저장 = MediaPipe 33 전체 (절대 17로 떨궈 저장 X)
- 스코어링/분석 계약 = COCO-17 + 폴 확장 (toe·heel·grip)
- 기존 skeleton.py / JOINT_ANGLES / KEYPOINT_NAMES / features / temporal 유지
- 어댑터 = MediaPipe33ToCOCO17Adapter (+ 폴 확장 추출)
- 엔진 교체 시 SMPLXToCOCO17Adapter로 교체
- 폴 확장 landmark = 별도 feature set + confidence 게이트

### Q5: Confidence 처리 (visibility/presence ↔ uncertainty)
| Option | Description | Selected |
|---|---|---|
| visibility → (1-visibility) uncertainty 변환 | 기존 temporal/features 재사용. 안전·빠른 마이그레이션 | ✓ |
| PoseFrame에 visibility 별도 필드 | 더 정확, 단 PoseFrame 확장 + 다운스트림 조정 필요 | |
| visibility 임계값만 사용 | 단순, 기존 보간 로직 재설계 필요 | |

**User's choice (정책 수준 결정):**
- 변환식: `confidence = visibility × presence`, `uncertainty_proxy = 1 - confidence`
- 저장 필드: raw_visibility, raw_presence, confidence, uncertainty_proxy 모두 별도 저장
- 사용처: 신뢰도 체크, 저신뢰 필터링, 각도 유효성, temporal 스무딩, short-gap 보간, 리포트 경고
- 저신뢰 키포인트 → 각도 "low reliability" 마킹. 저신뢰 비율 높은 구간 과분석 금지
- 고객 리포트: 기술 용어 노출 금지. "이 구간은 무릎 위치가 영상에서 명확하게 보이지 않아..." 톤
- 향후 NLF 통합 시 동일 인터페이스로 매핑 (feature pipeline 재설계 금지)

---

## NLF R&D 격리 방식

### Q1: NLF 위치
| Option | Description | Selected |
|---|---|---|
| backend/research/pose_engines/nlf/ | 제품 패키지 밖 완전 분리, import 자체 불가 | ✓ |
| backend/shared/python/sunity_shared/analysis_rd/ | 최소 변경, 문화적 분리만 | |
| 별도 repo (sunity-motion-rd) | 가장 강한 격리, 운영 오버헤드 | |

**User's choice:** backend/research/pose_engines/nlf/

### Q2: Import 차단
| Option | Description | Selected |
|---|---|---|
| 물리 경로 분리만 충분 | sunity_shared과 별개 경로라 자연스레 import 불가. Lambda 레이어 미포함 | ✓ |
| import-linter 룰 + CI 검증 | 확실, 도구 추가 필요 | |
| 둘 다 (경로 + import-linter) | 두 계층 방어, 도구 오버헤드 | |

**User's choice:** 물리 경로 분리만

### Q3: 평가 스크립트 위치
| Option | Description | Selected |
|---|---|---|
| backend/research/evaluations/ | R&D 디렉토리 안, compare_engines.py 등 | ✓ |
| backend/scripts/ 기존 위치 유지 | sys.path 신경 쓰기 필요 | |
| 별도 RunPod notebook | Pod 안에서만 돌고 repo 외부 유지 | |

**User's choice:** backend/research/evaluations/

### Q4: 기존 NLF 제품 코드 처리
| Option | Description | Selected |
|---|---|---|
| MediaPipe 완성 후 한 번에 swap | atomic, 중간 상태 없음. 단 swap 전까지 NLF 남음 | ✓ |
| Config 플래그로 점진 롤아웃 | POSE_ENGINE 환경변수. 안전하나 이중 모드 오버헤드 | |
| 잘라내고 MediaPipe만 + 수동 테스트 | 명확하나 자동화 회귀 안전망 없음 | |

**User's choice:** atomic swap

---

## 폴 축 검출 방법

### Q1: 검출 방법
| Option | Description | Selected |
|---|---|---|
| 자동 검출 (Hough Line Transform + 수직 prior) | OpenCV CV. 일반 폴에 잘 동작. 배경 잡음/조명에 취약. UX 마찰 0 | ✓ |
| 사용자 1-탭 가이드 | 첫 프레임에서 폴 상단·하단 탭. 정확도 최상. UX +1초 | |
| 하이브리드 (자동 우선 + 실패 시 가이드) | confidence 낮으면 사용자 탭 요청. 분기 처리 복잡 | |
| 수직 가정 + confidence 표기 | 카메라 고정·폴 수직 가정. 0원. 기울어진 카메라에서 부정확 | |

**User's choice:** Hough Line Transform + 수직 prior 자동

### Q2: 시간 안정성
| Option | Description | Selected |
|---|---|---|
| 영상 전체 평균 축 1개 | 일반 폴(고정) 가정. 운영 단순 | ✓ |
| 프레임별 축 + 시간 스무딩 | 스피닝 폴 권장. 계산·저장 복잡. v1엔 과이용 | |

**User's choice:** 영상 전체 평균 축 1개

### Q3: 검출 실패 처리
| Option | Description | Selected |
|---|---|---|
| 수직 가정 폴백 + confidence='low' | 분석 진행, 결과 화면에 안내. 사용자 차운 머음 없음 | ✓ |
| 분석 실패 (재촬영 요청) | low_pole_axis_confidence 에러. 안전. 사용자 탈락 위험 | |
| 자동 실패 시 사용자 가이드 fallback | Q1에서 hybrid 안 골랐으면 구현 복잡 | |

**User's choice:** 수직 가정 폴백 + confidence='low'

### Q4: 좌표 저장 방식
| Option | Description | Selected |
|---|---|---|
| 원본 + 정렬된 둘 다 저장 | PoseFrame.keypoints3D(raw) + keypoints3DPoleAligned. 용량 2배, 근거 명확 | ✓ |
| 정렬된 것만 저장 (PoleAxis 메타) | 용량 절약. 디버그 불편 | |
| 원본만 저장, 매 분석에서 정렬 재계산 | 용량 최소. 다운스트림 매번 정렬 연산 반복 | |

**User's choice:** 원본 + 정렬된 둘 다 저장

---

## MediaPipe vs NLF 회귀 검증 기준

### Q1: 검증 영상 세트
| Option | Description | Selected |
|---|---|---|
| 정은지 5·10 + 경력/체형 10 + 고의 평이 5 (총 20~25개) | 다양성 충분. R&D 평가에 이상적 | (목표) |
| 정은지 영상 5개만 (빠른 검증) | 최소 검증. 시연 후 회귀 위험 | ✓ |
| AMASS/BEDLAM 데이터셋 포함 | 폴스포츠 도메인 겹치지 X. 보조적 | |

**User's choice:** 옵션 2로 시작하되 옵션 1의 다양성이 본래 목표 — 데이터 확보에 시간 걸리므로 belle에게 지속 요청해서 인지 유지

### Q2: 점수 갭 허용
| Option | Description | Selected |
|---|---|---|
| ±5점 이내 | 결정·리포트 톤 변하지 않을 수준 | ✓ |
| ±10점 이내 (관대) | 고수 위양성 감지 뚜렷일 위험 | |
| ±3점 이내 (엄격) | MediaPipe 정확도 한계로 달성 어려움. 대멸 위험 | |

**User's choice:** ±5점 이내

### Q3: 추가 검증 지표 (multiSelect)
| Option | Description | Selected |
|---|---|---|
| 고수 위양성 없음 (정은지 ≥70점) | SCORE-04 직결. 41점 같은 위양성 절대 재발 금지 | ✓ |
| Top-3 실패 원인 일치 | 동일 영상에서 두 엔진 Top-3 최소 2/3 겹침 | ✓ |
| 키포인트 confidence 분포 | 정상 영상에서 평균 confidence 임계값 이상 | ✓ |
| 추론 속도 (ms/frame) | Lambda CPU 일정 안에 도는지 | ✓ |

**User's choice:** 4개 모두

### Q4: 검증 실패 시 대응
| Option | Description | Selected |
|---|---|---|
| Phase 1 종료 보류, 원인 분석 후 재시도 | Hough·매핑·confidence 튜닝. swap 안 됐으니 회귀 없음 | ✓ |
| swap 강행 + 제품에서 이터레이팅 튜닝 | 일정 압박 시만. 품질 위험 | |
| MediaPipe 포기 + NLF 라이선스 우선 협의 | MediaPipe 근본 부적합 입증 시. 전략 반전 | |

**User's choice:** Phase 1 종료 보류 + 재시도

---

## Claude's Discretion

- 폴 확장 landmark(toe/heel/grip)의 정확한 MediaPipe 33 인덱스 매핑
- `PoseEngine` 인터페이스 메서드 시그니처 세부
- `MediaPipe33ToCOCO17Adapter` / `SMPLXToCOCO17Adapter` 모듈 위치
- Hough Line Transform 파라미터 초기값
- 회귀 검증 보고서 출력 포맷
- `pose_landmarker_heavy.task` 모델 파일 배포 위치
- MediaPipe 실패 시 `NoHumanError` 재사용 여부

## Deferred Ideas

- RunPod GPU pod 처분 (Phase 1 회귀 검증 + 속도 측정 후 결정)
- 기존 Firestore 분석 결과/정은지 기준 모션 본자이션 (Phase 14에서 다각도 재구축이 자연스러움)
- pose_landmarker_heavy.task 배포 위치 (Lambda 레이어 vs S3)
- MediaPipe Heavy SLA 부적합 시 병렬화/캐싱 전략
- NLF/SMPL-X 상업 라이선스 협의 (belle 평행, 향후 NLF 재도입 시 게이트)

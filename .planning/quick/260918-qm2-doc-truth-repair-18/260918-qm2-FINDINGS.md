# 정리 2차 실측 — 원문 (2026-09-18, 에이전트 6대)

======================================================================
## w1:debug원장
살았다 1 / 죽었다 4 / 보류 1 — 미종결 6건 중 4건은 이미 수리·기능제거로 사문이고, 살아있는 것은 역립 귀속 마커의 회전 이후 재측정 1건뿐이다

### [죽었다] illustration-slot-crop.md
**왜:** 일러스트 기능이 2026-08-24 에 전면 제거돼 이 결함이 붙을 표면 자체가 없다. 컴포넌트·판정 lib·에셋 디렉터리가 모두 파일시스템에 부재하고, app/src 전체에서 illustration 문자열은 VideoCompare 의 죽은 prop 4줄뿐이다. 더구나 이 문서 자신의 Resolution 이 이미 '보고된 결함은 존재하지 않았다(오측) — 360x260 은 카드 높이가 아니라 시트 스크롤 조각'으로 닫고 주석만 고쳤다고 적어 두었다. 즉 기능 제거와 오측 판정으로 이중으로 죽었다.

**근거:** ls app/src/components/DefectIllustration.tsx app/src/lib/illustrationScene.ts app/assets/illustrations → 3건 모두 'No such file'. git log --grep=일러스트 → fb2eef19 'lib 4종·테스트 4종·에셋 21장 제거 — 일러스트 참조 0', eddbdf0e '일러스트 표시 배선 제거'(둘 다 2026-08-24). grep -rni illustration app/src → app/src/components/VideoCompare.tsx:365,562,2471,2472 (renderCueIllustration prop, 전 저장소에 전달자 0). 문서 자체 Resolution = .planning/debug/illustration-slot-crop.md 의 root_cause 블록.

**원장 한 줄:** | illustration-slot-crop | 죽었다 | 일러스트 전면 제거(2026-08-24 fb2eef19) — 컴포넌트·lib·에셋 부재, 참조 0. 문서 Resolution 도 오측 판정 |

### [살았다] inversion-joint-attribution.md
**왜:** 문서가 남긴 next(IN-01 앱측 소비)는 완료됐다 — 백엔드 마커와 앱 억제 게이트가 모두 배선돼 있다. 그런데 2026-09-17 회전 묶음이 이 마커가 노리는 서명 자체를 크게 녹였다: belle 역립(pdshape) 케이스의 tol 초과 관절이 8개에서 2개로 떨어졌는데, 발화 임계는 여전히 5개다. 즉 역립 문서에서 억제가 조용히 꺼졌거나 켜졌을 수 있고, 회전 ON 이후 발화 분포를 아무도 재지 않았다. 임계 3개는 코드 주석에 '[5-fixture 유도]'로 못 박혀 있고 그 유도는 회전 이전 분포다. 2026-09-10 에 닫힌 좌우 팔꿈치 건(RTMW 라벨 정오)과는 다른 트랙이다 — 이쪽은 라벨이 아니라 저신뢰 역립에서 다관절 편차가 균일 부양되는 크기·귀속 문제다.

**근거:** backend/functions/pipeline/app.py:2399-2401 (_ATTR_MIN_OVER_TOL_JOINTS=5 / _ATTR_MAX_VISIBILITY=0.70 / _ATTR_MAX_DTW_DISTANCE=60.0, 전부 '[5-fixture 유도]' 주석) · :8477 _attach_attribution_marker 호출 · :8470-8474 운영 전수(925건 중 발화 18건, 17건이 elbow-twist). 앱 소비 = app/src/app/analysis/result.tsx:858 및 1067/1072/1079/1089/1096/1103/1172/2217, app/src/lib/userAnalyses.ts:777, app/src/types/analysis.ts:979. 회전 이후 초과 관절 8→2 = .planning/quick/260917-hjy-reference-drift-all11/evidence/SCORE-IF-BUNDLED.md §1 표.

**원장 한 줄:** | inversion-joint-attribution | 살았다 | 마커 배선 완료(app.py:2399, result.tsx:858). 남은 것 = 회전 ON 이후 발화 재측정 — 초과 관절 8→2, 임계는 5 |

### [죽었다] kipup-split-injection-lost.md
**왜:** 문서가 next_action 으로 적은 fix 가 문서와 같은 날 적용·커밋됐다. rule 1 이 body_part 단독이 아니라 body_part+fault_state 를 합친 문자열로 split 을 라우팅한다. 그 뒤 fault_category enum 을 0순위로 올려 어휘 드리프트 자체에 의존하지 않게 됐다. 문서가 남긴 유일한 blind spot(dev==tol 이면 over 0 이라 점수가 99 로 남는다)도 2026-08-31 에 vision 측정값의 tol 우회로 닫혔다. 회귀 테스트도 있다. 08-31 kip-up 재발은 이 문서의 라우팅 유실이 아니라 tol 재적용이라는 다른 뿌리였고 그것도 닫혔으며, 09-18 회전 묶음 배포 검증에서 kip-up 99→99 로 무회귀 확인됐다.

**근거:** backend/shared/python/sunity_shared/analysis/ipsf_criteria.py:330 combined = f"{body_part} {fault_state}" → :348 if _contains(combined, _SPLIT_KEYWORDS): return ("split_angle",). 커밋 3399fd78 (2026-07-04) 'fix(25-04): sweep FAIL #1 — split 라우팅을 combined(body_part...' , e697364e (2026-07-04) 'feat(25-05): 라우터 fault_category enum 1순위 소비'. tol 우회 = backend/shared/python/sunity_shared/analysis/deduction_engine.py:622 over = d if vision_sourced else max(0.0, d - tol) (:594 주석 quick-260831-isk). 테스트 = backend/tests/test_deduction_engine.py:244,297,308. 회전 후 무회귀 = .planning/quick/260918-day-closeout/HANDOFF.md:18.

**원장 한 줄:** | kipup-split-injection-lost | 죽었다 | 요청된 combined 라우팅 fix 가 같은 날 3399fd78 적용, enum 1순위 e697364e 추가 — status 만 미갱신 |

### [죽었다] viewer-axis-flat-skeleton.md
**왜:** 두 겹으로 죽었다. 첫째, 원인이던 컴파일타임 상수 AXIS_V=2 가 2026-07-20 에 폐기되고 포즈별 런타임 축 선택으로 바뀌었다 — 코드 주석이 y-era/z-era 두 세대 공존을 실측 근거와 함께 박제하고 있다. 둘째, 그 카드를 띄우던 화면이 사라졌다. PoseCompareViewer 는 ReferenceCornerSection 한 곳에서만 import 되는데 ReferenceCornerSection 을 import 하는 파일이 저장소에 0개다. result.tsx 의 import 블록(17~78행)에 둘 다 없고, 09-09 재디자인이 옛 섹션을 통째로 걷어냈다. 그리는 화면이 없으니 가로 일직선으로 뭉개질 표면도 없다.

**근거:** app/src/components/PoseCompareViewer.tsx:44-60 pickVerticalAxis() (상단 주석 '[fix 2026-07-20] ... 컴파일타임 상수가 이 버그의 원인이었다'), 커밋 89402fc5 (2026-07-20). 소비처 = grep -rn 'import.*ReferenceCornerSection' app/src → 0건; grep -rn '<ReferenceCornerSection' app/src → 0건. 철거 커밋 = git log -S ReferenceCornerSection -- app/src/app/analysis/result.tsx → aadf0375 / a5089955 (둘 다 2026-09-09, '시안이 대체한 옛 섹션 전부 제거', '죽은 코드 1107줄 제거').

**원장 한 줄:** | viewer-axis-flat-skeleton | 죽었다 | 축 버그는 89402fc5 수리, 카드를 쓰던 ReferenceCornerSection 은 09-09 aadf0375 철거 — 소비처 0 |

### [죽었다] recognizer-ipsf-fallback.md
**왜:** 문서가 지목한 이중 차단이 둘 다 풀렸다. REGISTERED_MOTIONS 는 5개에서 10개로 늘어 문제의 5동작이 전부 등재됐고, criteria yaml 도 10동작 전수 생성됐다. 운영 인식기는 FallbackRecognizer 가 아니라 GeminiTechniqueRecognizer 다 — Pod 기동 스크립트가 상시 gemini 로 켠다. 남아 있는 line=None 은 배선 갭이 아니라 belle 2026-06-27 결정의 결과다: pod 재스윕에서 정타 form 이 무릎을 굽히거나 신호가 역전돼 무릎 신전이 결함 축이 아님이 드러나 EXTEND 를 의도적으로 뺐고, 그 이유가 각 yaml 헤더에 박제돼 있다. 실제로 EXTEND 가 살아 있는 곳은 power-spin 양 무릎 2개뿐이다. 즉 '객관 트랙이 한 번도 안 켜졌다'가 아니라 '켤 자리에만 켜져 있다'로 바뀌었다.

**근거:** backend/shared/python/sunity_shared/analysis/gemini_motion_classifier.py:25-40 (REGISTERED_MOTIONS 10개, 'P1 step 4 (2026-06-27)' 주석). yaml 전수 = backend/judging_data/criteria/*.yaml 10개. EXTEND 실집계(파일별 grep -c 'extension_class: *EXTEND'): ref-power-spin=2, 나머지 9편=0. 제거 근거 = ref-kip-up.yaml:1-13, ref-pdshape.yaml:2-5, ref-peter-pan.yaml:2-5, ref-elbow-twist-sister.yaml:1-7 (belle 결정 2026-06-27 '굽힘 form 엔 신전기준 강요 금지'). 인식기 = backend/runpod_inference/start_server.sh:42 export RECOGNIZER_BACKEND=gemini → backend/functions/pipeline/app.py:1243-1265. FallbackRecognizer 실사용은 backend/research/ 스크립트뿐.

**원장 한 줄:** | recognizer-ipsf-fallback | 죽었다 | REGISTERED_MOTIONS 10개 + yaml 전수 생성, 인식기 상시 gemini. EXTEND 부재는 belle 06-27 결정 |

### [보류] ref-student-substrate-gap.md
**왜:** 문서의 출발점이던 비대칭은 해소됐다. 2026-09-17 에 기준 11편을 rot180_v1 로 승격하고 학생 경로 회전 플래그를 같은 묶음으로 켜서 양쪽이 같은 보정을 받는다 — belle pdshape 60→87, 정은지 자기비교 60→100. M3(동작 구간 탐색이 12/12 전부 무력화)도 코드에서 수리됐다: nu<nr 경로가 생겨 기준을 학생 길이로 슬라이딩한다. 남은 것은 fps 비대칭인데(기준은 저장본과 같은 프레임 공간으로 재추출돼 여전히 학생보다 조밀하다) 09-17 전수 측정이 허용오차 초과 0개로 무해 판정했다. 진짜 미결은 이 문서의 수용 기준 중 두 가지 — pdshape ±30점 요동과 elbow-twist 여유 +0.2° — 를 새 기질 위에서 아직 안 잰 것이고, 그건 학생 영상 회전 ON 재분석이 필요해 Pod 기동이 조건이다. 09-18 인계서가 같은 항목을 다음 후보 4번으로 이미 올려 두었다.

**근거:** 묶음 배포 = backend/runpod_inference/start_server.sh:24 ROT180_INVERSION_ENABLED=1 (기준 승격과 한 묶음 명시) + .planning/quick/260917-hjy-reference-drift-all11/evidence/SCORE-IF-BUNDLED.md §1 (60→86, 자기비교 60→100). M3 수리 = backend/shared/python/sunity_shared/analysis/motiondtw.py:177-216 (nu<nr 슬라이딩 + COVERAGE_FLOOR/_window_ambiguous/ref_boundary 3중 바닥). fps 무해 = evidence/REFERENCE-DRIFT-ALL11.md:47-51 ('88개 쌍 중 허용오차 초과 0개, 최대 15.6°', 'fps 차이는 무해하다'). 프레임 공간 유지 = evidence/BUNDLE-STAGED.md:20 '프레임 수가 저장본과 전부 일치'. 미측정 잔여 = .planning/quick/260918-day-closeout/HANDOFF.md:97 '회전 묶음 남은 4편 측정 — elbow-twist(학생 ON 재분석 1편)'.

**원장 한 줄:** | ref-student-substrate-gap | 보류 | 비대칭은 09-17 묶음으로 해소(60→87/100), M3 도 수리. 남은 것 = elbow-twist 학생 ON 재분석 1편, Pod 필요 |

======================================================================
## w1:phase22-31
살았다 0 / 죽었다 2 / 보류 3 — 22-06 은 이미 끝난 일(SUMMARY만 없음), 22-08·09·10 은 승격 대기 보류, 31-12 는 belle 상위결정 3중으로 죽었다

### [죽었다] 22-06 (bake-off 실행 + 백본 확정)
**왜:** 미완 작업이 아니다 — 실행이 끝났고 SUMMARY 파일만 안 썼다. 플랜이 요구한 산출물 2개가 모두 존재하고 커밋돼 있다: backend/training/setup_training_pod.sh(17,658바이트, 최종 커밋 ab0f5124 'fix(22-06): vllm 0.24 --limit-mm-per-prompt')와 22-BAKEOFF-RESULT.md(judgment: CONFIRMED, Qwen3-VL-8B, belle 공식 확정 2026-07-13, 커밋 2cdc76e0). run6 리포트 9개 + 결정성 64/64 기록까지 문서에 박혀 있다. STATE 원장에도 260713-jjq 로 남아 있다. 여기서 재개할 일은 없고, 필요한 것은 SUMMARY 한 장 또는 원장에 '완료' 표기뿐이다.

**근거:** ls -la .planning/phases/22-custom-vlm-finetune/ (22-06-PLAN.md 있고 22-06-SUMMARY.md 없음) / cat 22-BAKEOFF-RESULT.md 1행 '판정: CONFIRMED — 우승 Qwen/Qwen3-VL-8B-Instruct (belle 공식 확정 2026-07-13)' / git log -1 -- backend/training/setup_training_pod.sh -> ab0f5124 2026-07-11 / .planning/STATE.md:310 260713-jjq 원장행

**원장 한 줄:** 22-06 bake-off — 실행 완료(Qwen3-VL-8B CONFIRMED, belle 2026-07-13, 산출물 2/2 커밋). SUMMARY 파일만 미작성. 미종결 트랙 아님.

### [보류] 22-08 (서빙 swap 1단 — VlmJudge Protocol + vLLM 동거)
**왜:** 코드가 단 한 줄도 없다. 플랜이 선언한 artifact 3개 전부 부재: vlm_judge.py MISSING, setup_vllm.sh MISSING, test_vlm_judge.py MISSING. 운영 코드에서 VlmJudge/VLM_JUDGE_BACKEND/VLM_JUDGE_SHADOW 참조 0건. 다만 상위 결정으로 기각된 적은 없다 — STATE:63 이 '잔여 플랜: 22-08~10 서빙 swap(게이트 PASS 시 promotion_ledger current 진입 조건)'으로 살려두고 있고, 22-12-SUMMARY 의 affects 에도 '22-08 서빙 swap(current 포인터 진입 조건)'이 적혀 있다. 재개 조건은 명확하다: promotion_ledger.json 의 current 가 null 이 아니게 되는 것. 지금은 entries 5건(v28·v29·v35·v36·v38) 전부 promoted=false, current=null 이라 꽂을 모델 자체가 없다.

**근거:** 테스트: for f in vlm_judge.py setup_vllm.sh test_vlm_judge.py -> 전부 MISSING / grep -rn 'VlmJudge|VLM_JUDGE_SHADOW|VLM_JUDGE_BACKEND' backend/ | wc -l -> 0 / cat backend/training/sft/promotion_ledger.json -> "current": null, entries 5건 promoted:false / .planning/STATE.md:63

**원장 한 줄:** 22-08 서빙 swap 1단 — 미착수(artifact 3/3 부재, 운영 참조 0건). 보류: promotion_ledger.current 가 null 을 벗어나야 재개.

### [보류] 22-09 (shadow 병행 — Gemini vs 자체 모델 diff 축적)
**왜:** 22-08 없이는 성립하지 않는 하류 플랜이고, 그 앞단인 22-03 배선도 안 끝났다. shadow_report.py MISSING, pipeline/app.py 에 VLM_JUDGE_SHADOW 0건. 존재하는 backend/tests/phase22/test_shadow_wiring.py 는 22-09 것이 아니라 22-03 Task 1 helper 테스트다 — 파일 docstring 이 직접 그렇게 적고 있고 '배선(Task 2)/Pod 실측(Task 4)은 belle-gated 후속 세션으로 이월'까지 명시한다(본문만 보고 배선 완료로 오독하면 안 됨). 실제로 firestore_admin.store_vlm_shadow(:2746) 는 정의만 있고 호출자 0 — 22-09 가 집계할 diff 를 만들 생산자가 아예 없다. 기각된 적은 없으므로 죽었다고 부를 근거는 없다.

**근거:** ls backend/evals/phase22/ -> shadow_report.py 없음 / head -10 backend/tests/phase22/test_shadow_wiring.py -> 'Phase 22 Plan 22-03 Task 1 ... 배선(Task 2)/Pod 실측(Task 4)은 belle-gated 후속 세션으로 이월' / grep -rn 'store_vlm_shadow' backend/ (테스트 제외) -> firestore_admin.py:2746 정의 1건, 호출 0건 / .planning/STATE.md:66

**원장 한 줄:** 22-09 shadow 병행 — 미착수. 22-03 Task2~4 배선도 belle-gated 이월 상태라 store_vlm_shadow 호출자 0. 22-08 뒤 보류.

### [보류] 22-10 (역할별 순차 swap — veto/recognizer/coach)
**왜:** 사슬의 맨 끝이라 앞 두 개가 없으면 시작 자체가 불가능하다. test_swap_toggle.py MISSING, 22-SWAP-LOG.md MISSING, VLM_JUDGE_BACKEND 참조 0건. 운영 판정은 현재 전부 Gemini 로 확인된다 — sunity_shared/gemini/ 13모듈, judging/ 4모듈 모두 Gemini 경유이고 판정 백엔드를 고르는 스위치(JUDGE_BACKEND 류)가 코드에 없다. 재개 조건이 2중이다: (1) 승격된 체크포인트 존재, (2) 22-09 가 만든 'Gemini 이상' 증거. 게다가 재학습 한 사이클 비용 $33~38 대비 RunPod 잔액 $18.90 로 충전이 선행이고, TRAINING-DUE.md 가 '이번 실증(2026-10 중순)에는 안 닿는다. 재학습은 실증 뒤 우선순위로 belle 에게 물을 것'으로 스스로 이월 처리했다. belle 이 기각한 것이 아니라 아직 안 물어본 상태다.

**근거:** 테스트: test_swap_toggle.py MISSING, .planning/phases/22-custom-vlm-finetune/22-SWAP-LOG.md MISSING / grep -rn 'VLM_JUDGE_BACKEND' backend/ -> 0 / grep -rn 'JUDGE_BACKEND|judge_backend' backend/shared/python backend/functions -> 0 / ls backend/shared/python/sunity_shared/{gemini,judging}/ / .planning/TRAINING-DUE.md '파일럿 연결 — 없음' 절

**원장 한 줄:** 22-10 역할별 swap — 미착수(VLM_JUDGE_BACKEND 0건). 보류: 승격 + 22-09 증거 + RunPod 충전($18.90<$33~38). 실증 후 belle 판정 대상.

### [죽었다] 31-12 (배포 게이트 — Phase 31 마지막 플랜)
**왜:** 원 플랜이 상위결정으로 기각됐고, 그 기각이 3개 층에서 각각 확인된다. (1) 31-CLOSEOUT.md 가 belle 확정을 머리말에 박아뒀다: '31 부분에서 지킬 거 지키고 그냥 안 할 거 안 하는 게 나을 것 같은데' → '원 31-12-PLAN.md 는 생성 기능 배포를 전제하므로 그대로 실행하지 않는다', 교정 이미지(성공률 25%)·회전 영상(sliding-spin 에서 봉 잡은 자세가 떨어진 자세로 바뀜)·학습 페어 적재 전부 OFF. (2) 게이트 통과가 구조적으로 불가 — 31-12 는 CALIBRATION.json 의 chosen 4값을 요구하는데 그 파일은 blocked:true 이고 이유가 'insufficient_pass_samples:3<4'와 'confidence_axis_non_discriminating:all_4_grid_values_tie_at_FA4' 다. 표본이 늘어야 풀리는데 표본 생산자가 OFF 다. (3) 소비처가 사라졌다 — 31-11 이 result.tsx 에 붙였던 참고코너를 2026-09-09 belle 재디자인이 제거했다(aadf0375 '시안이 대체한 옛 섹션 전부 제거'에서 '참고코너' 명시, a5089955 '참고코너 전체 — 교정된 자세 이미지 + 회전 영상 ... 아무도 안 읽는 S3 재서명 두 벌'). 지금 ReferenceCornerSection.tsx 와 visualCards.ts 는 화면 import 0건이다. 배포 스택에도 Visual 리소스 0개다.

**근거:** aws cloudformation list-stack-resources --stack-name sunity-motion-pilot ...starts_with(LogicalResourceId,'Visual') -> 빈 출력 / get-template 결과에 'Visual' 0회, 파라미터 5개·리소스 26개 / smoke/CALIBRATION.json blocked:true, blocked_reasons 2건 / .planning/phases/31-api-visual-correction/31-CLOSEOUT.md §1·§3·§4 / git log -S ReferenceCornerSection -- app/src/app/analysis/result.tsx -> 3d3c5801(31-11 배선) → aadf0375·a5089955(09-09 제거) / grep -rn visualCards app/src -> 자기 테스트 1건뿐

**원장 한 줄:** 31-12 배포 게이트 — 죽었다. belle 2026-07-20 축소마감(31-CLOSEOUT)이 원 플랜 기각 + CALIBRATION blocked + 09-09 재디자인이 앱 소비처 제거 + 배포 Visual 0개.

======================================================================
## w1:phase33-36
살았다 1 / 죽었다 5 / 보류 1 — Phase 33 미종결 3건(33-07·33-16·33-21)은 전부 사문이고, Phase 36 은 이미 배포돼 belle 실계정 로그인 확인 1건만 남았다

### [죽었다] 33-07-PLAN.md (C+M3 atomic tuple flip)
**왜:** 33-07 이 쓰려던 flip 기계장치는 2026-09-17 에 실제로 돌았다 — 다만 payload 가 다르다. promote_reference_version.py 가 33-07 이 지정한 `_flip_active_pointer` 를 그대로 호출해 pre_phase4 백업 → activeVersion → top-level 미러 → `reference/_release.activeCandidate=rot180_v1` → 11/11 해시 검증까지 마쳤고, 09-18 별도 세션이 라이브에서 `activeVersion=rot180_v1` 을 재확인했다. 33-07 의 payload 였던 `phase33-cm3-run1`(9fps 재추출)은 코드에 테스트 픽스처 이름으로만 남았고, 지금 그것으로 flip 하면 정은지 자기비교가 100→60 으로 되돌아간다 — 즉 원문대로 실행하면 해롭다. M3(정렬 window)는 env 플래그 없이 채점 경로에 상시 활성이라 flip 을 기다린 적이 없다. 단 한 다리는 살아서 Phase 34 로 넘어간다: rot180_v1 은 `--target-fps` 없이 기본 18.0 으로 재추출됐으므로 '기준 18fps vs 학생 9fps' 비대칭은 그대로다.

**근거:** 커밋 02b1155a·ec9c9ef4 (git show); backend/scripts/promote_reference_version.py:13-16,84 (`_flip_active_pointer` 그대로 호출); backend/scripts/reprocess_reference_motions_phase4.py:599-602 (--target-fps 기본 18.0 "pipeline 정합"); backend/shared/python/sunity_shared/analysis/frame_extractor.py:60 (학생 target_fps=9.0); backend/functions/pipeline/app.py:1992,3679,5242,6542 (학생 경로 9.0 고정); motiondtw.py:75-80 (M3 상수, env 게이트 0); .planning/quick/260918-fyf-rotbundle-other-motions/evidence/MEASUREMENTS.md:62 (라이브 activeVersion=rot180_v1 재확인)

**원장 한 줄:** - [x] 33-07 — 죽었다(09-18 판정). flip 은 09-17 rot180_v1 로 실행됨(02b1155a). C(phase33-cm3-run1 9fps) 폐기·M3 는 상시 활성. 잔여 = 기준 18fps vs 학생 9fps → Phase 34 겹2.

### [죽었다] 33-16-PLAN.md (phase gate + belle UAT ②)
**왜:** 플랜은 미실행이 아니라 '실행됐고 반려로 끝난' 것이다. 33-PHASE-GATE-EVIDENCE.md 에 Task 0~3 이 전부 기록돼 있다 — 6동작 시리얼 re-sweep 13/13, crop PNG 26장·coach mp3 22건 전수 열람, 시뮬 렌더, OTA 발행, 그리고 07-30 심야 belle 실기기 UAT ② = 반려 12건. 남은 체크박스 2개는 이후 상위 결정으로 소멸했다: '일러스트 미완 4동작'은 belle 2026-08-24 일러스트 기능 전면 제거로 없어졌고(앱에 에셋 0, VideoCompare 의 renderCueIllustration 은 result.tsx 가 넘기지 않는 죽은 옵션 prop), '§9 수리 사이클'이 겨누던 화면(DeductionCard·ScoreBreakdownSection·InjuryRiskSection·참고코너)은 09-08~09 피그마 4탭 재디자인이 통째로 걷어냈다. 이 플랜의 스펙 원천인 승인 목업 라운드7 도 시안 5장으로 대체됐다. 살아남은 substance 는 M-2/M-4(확대 카드 표식이 말하는 부위와 어긋남) 하나인데, 그건 이미 09-18 게이트 2단 판정 수리로 이어지는 별도 활성 트랙이다.

**근거:** 33-PHASE-GATE-EVIDENCE.md:245-258(잔여 체크박스)·259-301(belle 반려 12건); .continue-here.md(07-31, OTA 092c312 후 belle 확인 ③ 대기); .planning/quick/260909-bhc-result-redesign/SUMMARY.md(4탭 구현 + 쳐낸 표면 목록 + OTA e7023625); grep renderCueIllustration app/src/app/analysis/result.tsx = 0건; ls app/assets = 일러스트 에셋 0

**원장 한 줄:** - [x] 33-16 — 죽었다. Task 0~3 실행·belle UAT ② 반려 12건까지 33-PHASE-GATE-EVIDENCE.md 에 기록됨. 게이트 대상 화면은 08-24 일러스트 제거 + 09-09 4탭 재디자인으로 소멸.

### [죽었다] 33-21-PLAN.md (elbow-twist HALT gap-closure)
**왜:** 조건부 플랜이고 조건이 성립하지 않았다. 플랜 본문이 직접 규정한다 — '33-06 이 여유 ≥ +2.0° 를 기록했으면 이 플랜은 NO-OP(33-06 의 margin 을 인용한 한 줄 SUMMARY 로 완료 표시)'. 33-06-SUMMARY 는 elbow-twist 여유 +3.10 을 기록했고, 같은 문서가 '33-21 no-op(HALT 없음, belle 질문 불요)' 라고 이미 판정해 뒀다. 남은 일은 작업이 아니라 표기뿐이다. 함께 차단하던 33-07 도 위에서 사문 판정이라 이 게이트가 막을 대상 자체가 없다.

**근거:** 33-21-PLAN.md must_haves truths 1행("if 33-06 recorded ≥ +2.0°, this plan is a NO-OP"); 33-06-SUMMARY.md:23("elbow-twist 여유 +3.10 (≥+2.0 → 33-21 HALT no-op)")·78·115·119

**원장 한 줄:** - [x] 33-21 — 죽었다(no-op). 33-06 elbow-twist 여유 +3.10 ≥ +2.0 이라 플랜 자신이 규정한 no-op. HALT 없음, belle 질문 불요.

### [죽었다] 36-01-PLAN.md (계정 화면 3종 + 라우팅)
**왜:** 실행·배포 완료다. 커밋 f957bad9 가 인트로·로그인·가입 3화면과 authCopy.ts 를 넣었고 파일이 전부 실재한다. 더해서 이 플랜의 must_have 앞 두 줄('시작하기 = 지금과 똑같이 게스트 익명 로그인 직행', '게스트 세션이 있으면 인트로가 CTA 를 안 그리고 통과')은 belle 2026-09-01 결정으로 **대체**됐다 — 지금 인트로 '시작하기' 는 /auth/login 으로 push 하고, 게스트 버튼은 로그인 화면에 있으며, 익명 세션은 자동 진입하지 않고 멤버(비익명) 세션만 자동 홈 진입한다. 코드 주석이 그 대체를 명시한다. 즉 이 플랜은 남은 작업이 없고 전제 일부는 상위 결정으로 무효다.

**근거:** 커밋 f957bad9; app/src/app/auth/login.tsx·signup.tsx·src/constants/authCopy.ts 실재(ls); app/src/app/index.tsx:12-18 ("belle 2026-09-01 결정 (08-30 '시작하기=게스트 진입 그대로'를 **대체**)")·39-50(멤버만 자동 진입); login.tsx:88-100,147-155(게스트 버튼)

**원장 한 줄:** - [x] 36-01 — 죽었다(실행 완료, f957bad9). 전제 "시작하기=게스트 직행"은 belle 2026-09-01 로그인 게이트 결정으로 대체(app/src/app/index.tsx:12-18).

### [살았다] 36-02-PLAN.md (Google 로그인 + 게스트 승계)
**왜:** 코드는 전부 배포됐다 — google-signin SDK 설치, app.json iosUrlScheme, socialAuth.ts 가 게스트면 linkWithCredential 을 먼저 시도하고 credential-already-in-use 를 switched 로 갈라 화면이 알린다. 그런데 플랜이 스스로 '★검증의 한계(정직)' 로 박아둔 단 하나가 아직 안 닫혔다: linked(uid 유지)까지는 belle 이 실제 구글 계정으로 한 번 로그인해야 확인된다. 커밋 메시지도 '★uid 유지(linked)까지는 belle 확인 대기' 라고 남겼다. 09-01 세션의 uid 불변 실측은 게스트→게스트 세션 재사용이지 게스트→Google link 가 아니다. 이건 Phase 36 Success #4 그 자체이고, 실증은 게스트 모드로 돌아가므로 파일럿 차단은 아니다. 작업량은 belle 이 로그인 1회 + 마이 탭 uid 앞 4자리 대조.

**근거:** 커밋 41fa1abd 메시지 말미("★uid 유지(linked)까지는 실제 구글 계정 로그인이 필요해 belle 확인 대기"); app/src/lib/socialAuth.ts:73,84,91,95; app/package.json:17; app/app.json:69; .planning/quick/260901-nms-login-gate-guest/260901-nms-SUMMARY.md:93(게스트→게스트 uid 불변만 실측); 36-02-PLAN.md "★검증의 한계(정직)" 절

**원장 한 줄:** - [ ] 36-02 — 살았다. Google 배선·게스트 승계 코드는 배포됨(41fa1abd). 남은 것 1건 = belle 실계정 로그인으로 linked/uid 유지 실측(Success #4). 파일럿 비차단.

### [보류] Phase 36 카카오·네이버 (36-CONTEXT POST /auth/social 포함)
**왜:** 죽은 게 아니라 belle 이 시점을 미룬 것이다. socialProviders.ts 가 이유를 문서화해 뒀다 — 'belle 2026-08-31 결정: 카카오·네이버는 출시 준비 때 붙인다(각자 개발자 콘솔 등록 + Firebase 미지원이라 커스텀 토큰 교환 필요). 그때 이 배열에 id 두 개만 되돌리면 화면은 자동으로 4개가 된다'. 색·치수·아이콘 벡터는 SOCIAL_PROVIDERS 카탈로그에 그대로 보존돼 있고 화면은 WIRED_SOCIAL_PROVIDERS 만 렌더하므로 눌러도 안 되는 버튼은 없다. 백엔드 쪽 커스텀 토큰 교환(POST /auth/social)은 36-CONTEXT.md 의 설계 메모 한 줄뿐이고 배포 스택에 /auth 라우트가 없다. 재개 조건은 명확하다: belle 콘솔 등록 + Lambda 라우트 신설.

**근거:** app/src/constants/socialProviders.ts:60-77 (belle 2026-08-31 결정 주석, WIRED_PROVIDER_IDS=['google','apple']); app/src/app/auth/login.tsx:124·signup.tsx:79 (WIRED 만 렌더); .planning/phases/36-account-system/36-CONTEXT.md:145 (POST /auth/social 설계 메모); backend/template.yaml 라우트 = /upload-url·/playback-url·/reference/auto-register·/reference·/visual/rotation (/auth 없음)

**원장 한 줄:** - [ ] 36 카카오·네이버 — 보류. belle 2026-08-31 "출시 준비 때". WIRED_PROVIDER_IDS=['google','apple'] 이라 버튼 미렌더. POST /auth/social 은 설계 메모뿐, 배포 라우트 0.

### [죽었다] app/src/lib/resultSections.ts + __tests__/resultSections.test.ts
**왜:** Phase 33 잔여물이 아니라 **Phase 32-11** 산물이다(두 파일 헤더가 '32-11 Task 1' 을 명시). result.tsx 는 커밋 15ec4490 에서 실제로 import 했고, 09-09 4탭 재디자인이 그 import 를 두 단계로 걷어냈다 — a5089955 가 type import 를, 32c22a10('예상 부위 (참고)' 카드 제거)이 마지막 value import 를 지웠다. 내보내기 5개(deriveResultSections·buildRecordMaps·pickExpandAnchorY·selectEstimatedZoomEntries·RESULT_SECTION_ORDER) 전부 프로덕션 소비처 0이다. 남은 것은 result.tsx:1389-1393 의 '순서·가시성은 resultSections 뷰모델 단일 지점이 결정한다'는 주석 — 지금 화면은 4탭(summary/compare/points/exercise)이라 그 10항 순서와 무관하다. 그런데 348줄 테스트 11건은 지금도 통과한다(직접 실행 확인). 죽은 스펙을 초록불로 지키고 있는 셈이고, 이게 belle 이 말한 '정리가 안 되는' 자리다.

**근거:** app/src/lib/resultSections.ts:1("32-11 Task 1"); 소비처 grep 5개 심볼 전부 0건(테스트·자기자신 제외); git log -S 로 a5089955:109(type import 제거)·32c22a10:33(value import 제거) 확인; app/src/app/analysis/result.tsx:259-264(4탭 정의)·1389-1393(낡은 주석); `node --test src/lib/__tests__/resultSections.test.ts` = tests 11 / pass 11 / fail 0

**원장 한 줄:** - [x] resultSections.ts — 죽었다. 32-11 산물, 09-09 재디자인(a5089955·32c22a10)이 import 제거. 내보내기 5개 소비처 0, 348줄 테스트 11건은 여전히 통과.

======================================================================
## w1:문서어긋남
살았다 15 / 죽었다 3 / 보류 0 — 문서 18곳이 코드와 어긋났고, 그중 Lambda 는 지금도 종료된 Pod 을 가리키고 있다

### [살았다] 1. CLAUDE.md 포즈 엔진 (48/140/144행)
**왜:** 운영 엔진은 RTMW 다. pipeline 이 `_RTMWNlfCompat` 를 세우고 그 안이 `RTMWPoseEngine` 이며(app.py:1282,1348), 검출기는 YOLO11 이 아니라 YOLOX-m onnx 다(rtmw_engine.py:51-54,157). 48행의 ViTPose-S 와 140행의 NLF 3D 둘 다 틀렸고, 특히 NLF 는 라이선스 차단 목록(Max Planck 비상업)에 올라 있어 '결정 완료 스택'으로 가르치면 위험하다. 새 세션이 가장 먼저 읽는 문서라 우선순위 1위다.

**근거:** CLAUDE.md:48 `ML        : YOLO11 → ViTPose-S → MotionDTW (FastDTW)` / :140 `... S3 / YOLO11→NLF 3D→MotionDTW ...` / :144 `NLF 3D는 CUDA 필수`. 코드 근거 = backend/functions/pipeline/app.py:1272-1284(`_RTMWNlfCompat` → `RTMWPoseEngine`), :1348(`_POSE_ESTIMATOR = _RTMWNlfCompat()`), shared/.../pose_engines/rtmw/rtmw_engine.py:51-54(`_YOLOX_DET_ENV`), :157(`det=yolox_onnx_path`), shared/.../config.py:27(`_DEFAULT_POSE_ENGINE = "RTMW"`). 가중치 = weights_manifest.json 중 production_eligible=true 는 `rtmw-x-384x288`(commercial_ok) 1건뿐(python3 로 덤프 확인). NLF 잔존 위치 = shared/.../analysis/pose_estimator.py(제품 경로에 파일은 있으나 interfaces.py:6 에 `DEPRECATED` 명시, inversion_warp.py:19 `DEPRECATED 미사용 경로`), backend/research/spikes·evaluations 4곳, backend/scripts/verify_nlf_pipeline.py·_nlf_smoke.py, 가중치 backend/scripts/nlf_l_multi.torchscript(493MB). 제품 파이프라인에서 NlfPoseEstimator 를 세우는 코드는 0건. ── 제안 after: 48행 `ML        : YOLOX-m(검출) → RTMW-x 133 wholebody → COCO-17 → MotionDTW (Sakoe-Chiba band)`, 140행 `... / S3 / YOLOX→RTMW-x 133→MotionDTW / Cerebras LLM / EAS Build`, 144행 `**GPU 의존**: RTMW ONNX 추론은 CUDA 필요(onnxruntime-gpu). 실분석은 RunPod Pod 에 위임`. 48행 아래 한 줄 추가 권장: `> NLF/ViTPose 는 운영 경로에 없다 — NLF 는 backend/research/ 와 verify_nlf_pipeline.py 에만 남은 R&D 잔재이고 상업 라이선스가 막혀 있다.`

**원장 한 줄:** CLAUDE.md:48 — `YOLO11 → ViTPose-S` → `YOLOX-m → RTMW-x 133 → COCO-17 → MotionDTW`; :140 `YOLO11→NLF 3D` → `YOLOX→RTMW`; :144 NLF→RTMW

### [살았다] 2. CLAUDE.md 자동생성부의 원본 (.planning/PROJECT.md · codebase/STACK.md · ARCHITECTURE.md)
**왜:** CLAUDE.md 128행부터는 GSD 가 `.planning` 원본에서 재생성하는 블록이다. 140/144행만 고치면 다음 `/gsd:docs-update` 때 NLF 서술이 되돌아온다. 원본 세 파일을 같이 고쳐야 1번이 유지된다.

**근거:** CLAUDE.md:128 `<!-- GSD:project-start source:PROJECT.md -->`, :150 `source:codebase/STACK.md`, :393 `source:ARCHITECTURE.md`. 원본 실측 — .planning/PROJECT.md:21(`YOLO11n → NLF 3D → band-constrained DTW`), :74(`현 포즈 = NLF 3D`), :82, :86. .planning/codebase/STACK.md:38, :93(`ultralytics ... YOLO11n person bounding-box detection`), :94(`NLF (Neural Localizer Fields, NeurIPS'24)`), :123, :141, :151(`ViTPose-S - ... superseded by NLF 3D backbone`). .planning/codebase/ARCHITECTURE.md:37,56,58,71,114,115,129,195,200,225.

**원장 한 줄:** .planning/PROJECT.md:21,74,82,86 + codebase/STACK.md:38,93,94,151 + ARCHITECTURE.md:56,114,129 — NLF/YOLO11 → RTMW/YOLOX (CLAUDE.md 재생성 원본)

### [살았다] 3. docs/reference-motions.md §5 — 등록 목록이 5편에서 멈춤
**왜:** 문서는 스스로 '기준 모션 단일 진실'이라 선언하고 시드 스크립트도 그렇게 인용하는데, §5 에는 5편만 있다. 라이브·시드·S3 는 모두 11편이다. 파일럿 Step 2 에서 이 문서를 읽고 등록하면 6편이 없는 것으로 오인한다.

**근거:** docs/reference-motions.md:103-500 에 ref-sideway-spin(107) · ref-climb(171) · ref-invert(240) · ref-foxtop(323) · ref-foxtop-split(410) 5블록뿐. 대조 — app/scripts/seed-reference-motions.mjs 의 MOTIONS 는 11건(142,166,191,216,244,275,301,327,353,379,405행). backend/scripts/promote_reference_version.py:40-43 `DEFAULT_MOTIONS` 도 11건. `aws s3 ls s3://sunity-motion-pilot-videos/reference/` → mp4 11개(ref-climb ~ ref-sideway-spin). ── 적용법: 문서 501행(§5 끝, 502행 `---` 앞)에 6블록을 append. 원값은 seed-reference-motions.mjs 의 각 블록을 그대로 옮기되 camelCase→문서 표기로 변환: ref-kip-up 274-299행(킵업/basic/swing_entry/clip 0·1·4·7.2·10) · ref-peter-pan 300-325(피터팬/basic/swing_entry/0·0.7·4·7.4·10) · ref-power-spin 326-351(파워스핀/intermediate/swing_entry/0·0.5·7·9.9·12) · ref-elbow-twist-sister 352-377(엘보 트위스트 시스터/advanced/lift_entry/0·5.5·13·21.9·25) · ref-pdshape 378-403(pdshape/advanced/lift_entry/0·3.5·8·15·18) · ref-combo 404-429(콤보/advanced/swing_entry/0·1.5·33·57.5·65). 각 블록의 checkpoints 7행(left/right shoulder·hip·knee + spine_mid)도 그대로.

**원장 한 줄:** docs/reference-motions.md:501 — §5 5편 → 11편(kip-up·peter-pan·power-spin·elbow-twist-sister·pdshape·combo 6블록 append, 원값=seed 274-429행)

### [살았다] 4. docs/reference-motions.md §6 — 새 모션 등록 절차에 실제 경로가 통째로 빠짐
**왜:** §6 은 'S3 업로드 → seed:reference' 로 끝난다. 그런데 시드 스크립트는 `--angles` 없이는 angles 를 안 쓰고, mode1 파이프라인은 angles 없는 기준 doc 을 만나면 곧장 RuntimeError 를 던진다. 게다가 전역 포인터 `_release.activeCandidate=rot180_v1` 이 켜져 있어 새 모션은 candidate 버전 doc 이 없으면 top-level 폴백으로 떨어진다. 그대로 따르면 등록은 성공한 것처럼 보이고 분석만 실패한다 — 파일럿 Step 2 가 여기 걸려 있다.

**근거:** docs/reference-motions.md:504-532 가 현행 §6(6단계 + Claude Code 명령 템플릿, 마지막이 `npm run seed:reference`). 깨지는 소비처 = backend/functions/pipeline/app.py:7896-7898 `if ref is None or "angles" not in ref: raise RuntimeError("기준 모션 또는 keyframe 데이터 없음")`. 시드 쪽 = app/scripts/seed-reference-motions.mjs:493-499(`if (anglesPayload && ...) doc.angles = ...` — 인자 없으면 미기록), :485-487(camelCase clipRange/checkpoints/isActive). 해석 순서 = shared/.../firestore_admin.py:2474-2532 `get_reference_motion`(shadow env → `reference/_release.activeCandidate` → top-level 폴백, 폴백 시 WARNING). 현재 포인터 rot180_v1 = .planning/quick/260917-hjy-reference-drift-all11/evidence/BUNDLE-STAGED.md:1-8 및 .planning/STATE.md(`activeCandidate=rot180_v1`(11/11 verify PASS)). ── 제안 after(§6 본문 교체): `[1] 영상 분석 + §5 블록 확정 → 이 파일에 append` / `[2] aws s3 cp {파일}.mp4 s3://sunity-motion-pilot-videos/reference/{motionId}.mp4` / `[3] seed-reference-motions.mjs MOTIONS 에 블록 추가(camelCase) → cd app && npm run seed:reference (메타·presigned URL·isActive 만 씀)` / `[4] ★Pod GPU: python backend/scripts/reprocess_reference_motions_phase4.py --version <활성버전> --no-flip --motions {motionId}` → `reference/{id}/versions/<활성버전>` 에 angles·joints3d·keypointReport 생성 / `[5] ★Pod GPU: python backend/scripts/backfill_reference_downstream.py --reference-version <활성버전> --write-candidate --motions {motionId}` → meanAngles·techniqueProfile·bodyNormalizationProfile·forceDirectionPattern·bodyComparisonSourcePose·captureViews 백필 / `[6] FIREBASE_SA_PATH=firebase-sa.json python backend/scripts/promote_reference_version.py --version <활성버전> --motions <11편+신규> [--dry-run]` → `_release.activeCandidate` flip + top-level 미러 / `[7] 검수: 새 모션으로 mode1 분석 1건 완주(done) 확인`. 주의 3줄도 같이: (a) 활성 버전은 `reference/_release.activeCandidate` 를 먼저 읽어 그 이름을 쓸 것(2026-09-18 현재 rot180_v1), (b) [4][5] 는 CUDA 필수 — Pod 기동 절차는 `/start`, (c) ref-combo 는 top-level 1013KB 로 Firestore 1MB 한도의 99% — 콤보보다 긴 모션은 한도에 걸린다.

**원장 한 줄:** docs/reference-motions.md:504-532 — §6 `seed:reference 로 끝` → `S3→seed(메타)→reprocess --no-flip→backfill --write-candidate→promote` 7단계

### [살았다] 5. docs/reference-motions.md §3 — 스키마가 snake_case 인데 실제는 camelCase
**왜:** §3 은 `entry_type`/`clip_range`/`prep_start_s` 로 적혀 있는데 Firestore 에 실제로 쓰이는 키는 camelCase 다. 앱 타입도 camelCase 다. §6 템플릿이 이 §3 을 기준으로 contract.md 와 analysis.ts 를 맞추라고 지시하므로, 따라가면 세 곳이 함께 틀어진다.

**근거:** docs/reference-motions.md:46-77(`entry_type?`, `clip_range`, `prep_start_s`, `exec_start_s`, `exec_peak_s`, `land_end_s`, `recommended_record_s`). 실제 write = app/scripts/seed-reference-motions.mjs:473-487(`entryType`, `entryDescription`, `clipRange`, `videoS3Key`, `isActive`) + :318-324 등 clipRange 내부가 `prepStartS/execStartS/execPeakS/landEndS/recommendedRecordS`. 앱 타입 = app/src/types/analysis.ts:1207-1224(`entryType?`, `clipRange?`, `sharedBaseMotionId`, `baseUntilS`). §3 에 없는 실사용 필드 = angles/anglesJointKeys/anglesFrames/meanAngles(analysis.ts:1226-1234), bodyNormalizationProfile·bodyComparisonSourcePose(:1239,:1244), referenceKeypointReport, videoS3Key, videoUrlExpiresAt.

**원장 한 줄:** docs/reference-motions.md:46-77 — §3 snake_case(entry_type/clip_range/prep_start_s) → camelCase(entryType/clipRange/prepStartS) + angles·meanAngles·bodyNormalizationProfile·videoS3Key 추가

### [죽었다] 6. docs/reference-motions.md §4 런타임 추출 규칙 — 소비처 0
**왜:** §4 의 세 규칙은 코드에 소비처가 없다. clip_range 로 reference 프레임을 자르는 코드가 없고(추출 스크립트에 clip_range 문자열 0건), KISMAM 은 checkpoints[].weight 를 전혀 읽지 않으며 고정 8관절 JOINT_KEYS 로 돈다. heroFrameUrl 은 리포 전체에 0건이다. '오래됐다'가 아니라 소비처가 0이라 죽었다고 판정한다.

**근거:** docs/reference-motions.md:85-98(§4 규칙 1~4). 소비처 검색 — `grep -ni "clip_range|clipRange|exec_peak" backend/functions/pipeline/app.py` → 7989,7993행 2건뿐이고 둘 다 공유 베이스 경계(`segments.ref_boundary_frame`) 용도. `grep -ni checkpoint backend/functions/pipeline/app.py` → 0건. `grep -rn heroFrameUrl backend app/src` → 0건. `grep -ni "clip_range|exec_start|land_end" backend/scripts/extract_reference_angles.py backend/scripts/reprocess_reference_motions_phase4.py` → 0건(= 기준 angles 는 영상 전체에서 뽑힌다). 실제 채점 관절 = shared/.../analysis/skeleton.py:50-62 JOINT_KEYS 8개(elbow·shoulder·hip·knee 좌우) — 시드 checkpoints 의 `spine_mid` 는 이 집합에 없다.

**원장 한 줄:** docs/reference-motions.md:85-98 — §4 규칙 1·3·4(clip_range 구간 추출 / checkpoints 가중평균 / heroFrameUrl) 삭제, 실제=전체프레임 + JOINT_KEYS 8관절

### [죽었다] 7. docs/reference-motions.md §7 — ViTPose 검증 미결 2항목
**왜:** §7 의 미결 항목 중 두 개는 ViTPose-S 출력 매핑 확인과 ViTPose overlay 시각 검증이다. ViTPose 는 제품에 배포된 적이 없고 백본이 RTMW 로 바뀌었으므로 이 두 항목은 영원히 실행될 수 없다. 같은 줄이 참조하는 `ml/CLAUDE.md` 도 존재하지 않는 경로다.

**근거:** docs/reference-motions.md:553-556(`joint 이름 ↔ ViTPose-S 출력 매핑 ... ml/CLAUDE.md ViTPose-S 출력 스펙과 함께 검토`), :558-561(`5개 reference 영상 ViTPose 시각 검증 ... Phase 2 의 ST-GCN / ViTPose-H`), :665(같은 문구 재언급). 코드 근거 = `grep -rn ViTPose backend --include=*.py` → skeleton.py:1,9 의 주석(COCO 17 순서 설명)뿐, 추론 코드 0건. `ls ml/CLAUDE.md` → No such file(실제는 ml/ml_CLAUDE.md). spine_mid 는 skeleton.py 의 JOINT_KEYS 8개에 없어 '보간 관절 결정' 항목도 채점에 닿지 않는다.

**원장 한 줄:** docs/reference-motions.md:553-561,665 — §7 ViTPose 매핑·overlay 검증 2항목 삭제(엔진 RTMW 전환으로 영구 미실행), `ml/CLAUDE.md` 참조도 제거

### [살았다] 8. .planning/quick/260918-gpx-gate-false-suppress/DEMO-CARD.md — 죽은 Pod 정본 + 시간 모순
**왜:** 카드가 종료된 Pod `elevev58iv4mox` 를 실증용 정본으로 박아뒀고, 그 주소는 지금 404 를 돌려준다. 게다가 같은 문서 안에서 다운로드 시간을 '25초 미만'(46행)과 '156.3s'(68행)로 둘 다 말한다. 88.7MB 를 25초에 받았다는 서술은 80행의 '20~30MB 면 40~50초' 추정과도 앞뒤가 안 맞는다 — 156.3s 가 맞는 실측이다.

**근거:** DEMO-CARD.md:7 `| Pod | \`elevev58iv4mox\` · L4 · 루마니아(RO) · $0.49/hr |`, :8 `| 서버 | https://elevev58iv4mox-8000.proxy.runpod.net |`, :18 curl 예시, :46 `(오늘 실측: 88MB 가 25초 미만 — 종전 기록 752초보다 훨씬 빨랐습니다.)`, :68 `| **s3_download** | **156.3s** ← 전체의 44% |`, :80 `수강생 폰 영상(20~30MB)이면 다운로드가 40~50초로`. 실행 확인 — `curl -s --max-time 15 -o /dev/null -w "%{http_code}" https://elevev58iv4mox-8000.proxy.runpod.net/health` → `404`(Pod 소멸). 메모리 정정본도 156초 = ~/.claude/.../memory/demo-only-pod-bring-up-procedure.md:76-78 `★ 정정 1 — "89MB 다운로드 752초"는 재현되지 않았다 ... s3_download 156초`. ── 제안 after: 7행 `| Pod | \`{podId}\` · (기동 후 채워넣기) · GPU/시간당 비용 |`, 8행 `| 서버 | https://{podId}-8000.proxy.runpod.net |`, 18행 `curl -s https://{podId}-8000.proxy.runpod.net/health | python3 -m json.tool`, 46행 `(2026-09-18 실측: 88.7MB 가 156초 — 아래 단계별 표와 같은 값입니다. 종전 기록 752초는 재현되지 않았습니다.)`.

**원장 한 줄:** DEMO-CARD.md:7,8,18 — `elevev58iv4mox` 고정 → `{podId}` 빈칸(기동 후 기입); :46 `88MB 25초 미만` → `88.7MB 156초`(:68 실측과 일치)

### [살았다] 9. Pod 종료 절차 — Lambda RUNPOD_ANALYZE_URL 되돌리기가 빠져 있다
**왜:** 기동 절차는 Lambda env 를 죽은 Pod 주소로 바꾸라고 하는데, 종료 절차는 'terminate + pod-expected=down' 두 가지뿐이고 Lambda 를 되돌리라는 문장이 어디에도 없다. 지금 실제로 Lambda 가 종료된 Pod 을 가리키고 있다 — pod-expected 는 down 인데 env 는 그대로다. 이 상태에서 사용자가 분석을 올리면 폴백 없이 실패한다.

**근거:** 실행 확인 — `aws lambda get-function-configuration --function-name sunity-motion-pilot-pipeline --query Environment.Variables.RUNPOD_ANALYZE_URL` → `https://elevev58iv4mox-8000.proxy.runpod.net/analyze`, `aws ssm get-parameter --name /sunity/motion/pod-expected` → `down`, 그 주소 health → 404. 빠진 문장의 위치 3곳: (a) .claude/commands/start.md:99 `★**쓰고 나면 반드시 terminate + \`pod-expected=down\`.** 켜둔 채 세션이 끝나면 돈이 샌다.` — 기동은 :83-92 에서 env 치환을 지시한다(`이 API 는 병합이 아니라 치환`). (b) .planning/quick/260906-n2j-stage-1-advisory/evidence/POD-RUNBOOK-2026-09-06.md:59 `7. 끝나면 **terminate + \`pod-expected=down\`**.` (c) 정본 메모리 ~/.claude/projects/-Users-kimtaesung-Dev-SunityMotion/memory/demo-only-pod-bring-up-procedure.md:37 `6. **시연 끝나면 terminate + \`pod-expected=down\`.**` ── 제안 after(세 곳 동일 문구 추가): `+ Lambda 의 RUNPOD_ANALYZE_URL 을 비우거나 지울 것 — aws lambda update-function-configuration ... 로 나머지 변수를 통째로 다시 넣으며 이 키만 제거한다(이 API 는 병합이 아니라 치환). 안 지우면 Lambda 가 죽은 주소로 위임해 분석이 폴백 없이 실패한다. SSM /sunity/motion/runpod-analyze-url 도 함께 비운다.`

**원장 한 줄:** .claude/commands/start.md:99 · POD-RUNBOOK-2026-09-06.md:59 · memory/demo-only-pod-bring-up-procedure.md:37 — `terminate + pod-expected=down` → `+ Lambda RUNPOD_ANALYZE_URL 제거(치환)`

### [살았다] 10. design.md — 2026-09-09 결과 화면 재디자인 반영 안 됨
**왜:** design.md 최종 커밋은 2026-05-28 인데 결과 화면은 2026-09-09 에 피그마 시안으로 전면 재디자인됐다(곡선 헤더 + 점수 원 + 4탭). 그런데 §7 은 결과 화면을 `[미완성]` 으로, §8 은 결과·기록·마이 세 화면을 전부 `❌ 설계 필요` 로 적고 있다 — 셋 다 이미 구현돼 있다. 전면 재작성은 범위 밖이니 경고 배너 + 세 지점만 고치면 된다.

**근거:** git log -1 design.md → `3e7819ae 2026-05-28`. 재디자인 커밋 = `git log --diff-filter=A -- app/src/components/result/ResultScoreDial.tsx` → `f2ce68d4 2026-09-09 feat(app): 분석 결과 재디자인 슬라이스 1 — 곡선 헤더 + 4탭 셸 + 점수 원`. 어긋난 절: design.md:427 `→ [미완성] 분석 결과 화면`; :432-455 §8 `❌ 분석 결과 화면 / ❌ 기록 탭 / ❌ 마이페이지`(실제 존재 = app/src/app/analysis/result.tsx, app/src/app/(tabs)/history.tsx, profile.tsx); :493 `5. AI 분석 대기 시간 (30~60초)`(실측 352초 — DEMO-CARD.md:61 `elapsedSec 352`); :484 `react-native-linear-gradient 설치 필요`(실제 app/package.json:31 `expo-linear-gradient`). 유효한 절 = §5-5 옥타곤(홈에서 여전히 사용, app/src/app/(tabs)/index.tsx:275), §5-2 4탭(app/src/app/(tabs)/_layout.tsx 홈·분석·기록·마이 일치). 실제 결과 화면 4탭 = result.tsx:260-264 요약·동작비교·교정포인트·보완운동. ── 제안: (a) design.md:5 바로 뒤(`---` 앞)에 배너 삽입 — `> ⚠ 본 문서는 2026-05-28 이 마지막 갱신이다. **분석 결과 화면은 2026-09-09 에 피그마 시안으로 전면 재디자인됐다**(곡선 빨강 헤더 + 흰 점수 원 + 상단 4탭: 요약/동작비교/교정포인트/보완운동). §7·§8·§10-5 는 그 이전 서술이다 — 결과 화면 작업은 이 문서 대신 app/src/app/analysis/result.tsx 와 app/src/components/result/ 를 정본으로 볼 것.` (b) :432 제목 → `## 8. 미완성 화면 (2026-05-28 시점 — ⚠ 결과/기록/마이는 이후 구현 완료)` 로 바꾸고 :437-451 세 블록의 `❌` → `✅ 구현됨 —` + 파일 경로. (c) :427 `→ [미완성] 분석 결과 화면` → `→ 분석 결과 화면 (4탭: 요약/동작비교/교정포인트/보완운동)`. (d) :493 `(30~60초)` → `(실측 3~6분 — 88MB 영상 352초, 2026-09-18)`. (e) :484 `react-native-linear-gradient` → `expo-linear-gradient`.

**원장 한 줄:** design.md:6 배너 신설(`§7·§8·§10-5 는 2026-09-09 결과화면 재디자인 이전`) + :427 `[미완성]` 제거 · :432-451 ❌→✅ · :493 `30~60초`→`3~6분` · :484 expo-linear-gradient

### [살았다] 11. app/src/types/analysis.ts — 백본 주석 4곳
**왜:** 98행 주석이 `pose_analysis` 단계를 YOLO11 + ViTPose-S 라고 설명한다. 같은 파일의 156·1202행은 keypoint 이름을 'ViTPose 17' 이라 부르고, 1226행은 reference angles 를 'NLF 추출 시퀀스' 라 적는다. 넷 다 현행 엔진과 다르다 — 이 파일은 앱·백엔드 공용 계약의 정본이라 주석이 곧 온보딩 문서다.

**근거:** app/src/types/analysis.ts:98 `  | 'pose_analysis' // YOLO11 + ViTPose-S`, :156 `  key: string; // ViTPose 17 keypoint 이름 (예: 'left_knee')`, :1202 `  joint: string; // ViTPose 17 keypoint 이름 (spine_mid 등 보간 관절 포함)`, :1226 `  // NLF 추출 시퀀스 (extract_reference_angles.py 결과를 seed-reference-motions`. 반대 근거 = backend/shared/python/sunity_shared/analysis/skeleton.py:9-28 `COCO 17 keypoint 순서`, backend/scripts/extract_reference_angles.py:1 `정은지 reference 영상 → RTMW 파이프라인 → reference angles JSON (GPU 필요)` 및 :6-11(RTMWPoseEngine 직접 사용, `NLF path 는 R&D 격리`). ── 제안 after: :98 `  | 'pose_analysis' // YOLOX 사람검출 + RTMW-x 133 wholebody → COCO-17`, :156 `  key: string; // COCO-17 keypoint 이름 (예: 'left_knee')`, :1202 `  joint: string; // COCO-17 keypoint 이름 (spine_mid 등 보간 관절 포함)`, :1226 `  // RTMW 추출 시퀀스 (extract_reference_angles.py 결과를 seed-reference-motions`.

**원장 한 줄:** app/src/types/analysis.ts:98 — `// YOLO11 + ViTPose-S` → `// YOLOX 검출 + RTMW-x 133 → COCO-17`; :156,:1202 `ViTPose 17`→`COCO-17`; :1226 `NLF`→`RTMW`

### [살았다] 12. ml/ml_CLAUDE.md — NLF/YOLO11 을 '현행'으로 가르친다
**왜:** ML 파이프라인 문서가 모델 표에서 YOLO11n 과 NLF 를 '현행' 으로, ViTPose 를 '폐기' 로 적고 파이프라인 도식도 NLF 기준이다. 실제 현행은 YOLOX-m + RTMW-x 133 이고 NLF 는 라이선스 차단 + R&D 격리 대상이다. CLAUDE.md §5 가 ML 작업 시 읽으라고 지목하는 문서라 1번과 같은 무게다.

**근거:** ml/ml_CLAUDE.md:19-21(`2D 포즈 추정(ViTPose 포함)은 ... 3D HMR 백본 NLF 로 전환`), :29 `| YOLO11n | 인체 bbox 탐지 (NLF 입력 박스) | 현행 |`, :30 `| NLF (Neural Localizer Fields) | 3D 포즈 백본 ... | 현행 |`, :38-39(파이프라인 도식 `→ YOLO11 ... → NLF ...`). 반대 근거 = 1번 항목의 코드 근거 일체 + shared/.../config.py:27 기본값 RTMW + 라이선스 메모(NLF = Max Planck 비상업, 상업 사용 불가). ── 제안 after: 29-31행 표를 `| YOLOX-m (onnx) | 인체 bbox 탐지 (RTMW 입력 박스, Apache-2.0) | 현행 |` / `| RTMW-x 133 wholebody (rtmlib ONNX) | 포즈 백본 — 133 → COCO-17 변환 | 현행 |` / `| NLF / ViTPose-S/H | 라이선스·정확도 사유로 폐기 — NLF 는 backend/research 전용 | - |` 로, 38-39행을 `→ YOLOX-m (인체 bbox)` / `→ RTMW-x 133 → COCO-17 어댑터 (17 keypoint + score)` 로.

**원장 한 줄:** ml/ml_CLAUDE.md:19-21,29-31,38-39 — `NLF/YOLO11n 현행` → `YOLOX-m + RTMW-x 133(rtmlib ONNX) 현행, NLF 는 backend/research 전용`

### [살았다] 13. docs/contract.md:38 — 계약 문서의 파이프라인 한 줄
**왜:** contract.md 는 앱·백엔드 계약의 정본인데 상태 전이 설명 바로 밑에 `YOLO11 → ViTPose-S` 가 박혀 있다. analysis.ts:98 과 같은 문장이 두 곳에 복제돼 있어 한쪽만 고치면 다시 어긋난다.

**근거:** docs/contract.md:37-38 `  status: queued → frame_extraction → pose_analysis → comparison → done` / `  YOLO11 → ViTPose-S → MotionDTW → KISMAM → Cerebras`. 같은 파일 :848,:898,:931,:939-942 는 이미 RTMW 를 운영 path 로, NLF_SMPLX 를 R&D 로 옳게 적고 있어 38행만 낡았다. ── 제안 after: `  YOLOX-m → RTMW-x 133 → COCO-17 → MotionDTW → KISMAM → Cerebras`.

**원장 한 줄:** docs/contract.md:38 — `YOLO11 → ViTPose-S → MotionDTW → KISMAM → Cerebras` → `YOLOX-m → RTMW-x 133 → COCO-17 → MotionDTW → KISMAM → Cerebras`

### [살았다] 14. CLAUDE.md §5 — 가리키는 파일 3개 중 2개가 없다
**왜:** §5 '세부 컨텍스트 파일 위치'가 `/ml/CLAUDE.md`, `/backend/CLAUDE.md`, `/docs/principles.md` 를 가리키는데 앞의 하나는 파일명이 다르고 나머지 둘은 리포에 없다. 새 세션이 가장 먼저 따라가는 경로라 첫 3분을 태운다.

**근거:** 실행 확인 — `for f in ml/CLAUDE.md app/CLAUDE.md backend/CLAUDE.md docs/principles.md docs/ia.md ml/ml_CLAUDE.md` 존재 검사 결과: ml/CLAUDE.md MISSING · backend/CLAUDE.md MISSING · docs/principles.md MISSING · app/CLAUDE.md EXISTS · docs/ia.md EXISTS · ml/ml_CLAUDE.md EXISTS. 해당 줄 = CLAUDE.md:80 `ML 파이프라인 작업   → /ml/CLAUDE.md`, :82 `백엔드 (Lambda)     → /backend/CLAUDE.md`, :84 `개발 원칙/에이전트   → /docs/principles.md`. ── 제안 after: :80 → `ML 파이프라인 작업   → /ml/ml_CLAUDE.md`, :82 → `백엔드 (Lambda)     → /backend/runpod_inference/README.md + backend/template.yaml (전용 CLAUDE.md 없음)`, :84 삭제(또는 `개발 원칙 → CLAUDE.md §7`).

**원장 한 줄:** CLAUDE.md:80 — `/ml/CLAUDE.md` → `/ml/ml_CLAUDE.md`; :82 `/backend/CLAUDE.md`(부재) → backend/runpod_inference/README.md; :84 `/docs/principles.md`(부재) 삭제

### [살았다] 15. app/CLAUDE.md §차트 라이브러리 — 설치하라는 두 패키지가 없다
**왜:** app/CLAUDE.md 가 Victory Native 와 react-native-gifted-charts 를 설치하라고 지시하는데 둘 다 package.json 에 없고 코드에서도 안 쓰인다. 실제 차트는 react-native-svg 로 직접 그린다. 지시대로 따르면 쓰지도 않을 의존성 두 개가 들어온다.

**근거:** app/CLAUDE.md:54-64 (`Victory Native ... react-native-gifted-charts ... 설치: npm install victory-native / npm install react-native-gifted-charts`). `grep -n "victory|gifted" app/package.json` → 0건. 실제 구현 = app/src/components/GrowthChart.tsx:1-12 (`react-native-svg` 의 Polyline/Polygon/Circle 직접 사용), app/src/components/OctagonScore.tsx(react-native-svg Polygon). ── 제안 after: 56-64행 블록을 `react-native-svg      : 성장 그래프·점수 위젯을 직접 그린다 (GrowthChart.tsx / OctagonScore.tsx / ResultScoreDial.tsx)` / `차트 전용 라이브러리는 쓰지 않는다 — Victory Native / gifted-charts 는 도입된 적 없음.` 으로 교체.

**원장 한 줄:** app/CLAUDE.md:54-64 — `victory-native + react-native-gifted-charts 설치` → `react-native-svg 로 직접 구현(GrowthChart/OctagonScore/ResultScoreDial)`

### [살았다] 16. backend/runpod_inference/README.md — 24/7 운영 · NLF · ROT180 기본 off
**왜:** README 첫 줄이 'Pod 24/7 운영, NLF 모델 메모리 상주' 라고 적는다. 운영 방침은 2026-08-28 belle 결정으로 '시연 때만' 으로 바뀌었고 모델도 RTMW 다. 36-37행의 'ROT180_INVERSION_ENABLED 는 off 가 기본' 도 2026-09-17 승인 이후 start_server.sh 에서 1 로 켜져 있어 반대다.

**근거:** backend/runpod_inference/README.md:3 `... Lambda 가 NLF GPU 추론을 직접 못 돌리는 문제(CPU NaN)를 풀기 위한 위임 서버. **Pod 24/7 운영**, NLF 모델 메모리 상주.`, :18 `│ S3 다운로드 → NLF 추출 → reference 비교 │`, :36-37 `> \`ROT180_INVERSION_ENABLED\` 는 off 가 기본이라 지금은 누락돼도 그 함정이 아니지만,`. 반대 근거 = backend/runpod_inference/start_server.sh:24 `export ROT180_INVERSION_ENABLED=1  # quick-260917-hjy: belle 승인(2026-09-17) 후 ON`; 운영 방침 = memory demo-only-pod-bring-up-procedure.md:11 `belle 결정 2026-08-28: "시연 때만 띄우자."`. ── 제안 after: :3 → `... RTMW GPU 추론 위임 서버. **시연·실증 때만 기동**(belle 2026-08-28), RTMW-x ONNX 모델 VRAM 상주(~1.3GB).`, :18 → `│ S3 다운로드 → RTMW 추출 → reference 비교 │`, :36-37 → `> \`ROT180_INVERSION_ENABLED\` 는 2026-09-17 승인 이후 **기본 ON**(start_server.sh:24) — 맨손 기동에서 누락하면 조용한 OFF 함정이다.`

**원장 한 줄:** backend/runpod_inference/README.md:3,18 — `Pod 24/7 운영 / NLF` → `시연 때만 기동(2026-08-28) / RTMW`; :36-37 `ROT180 off 가 기본` → `2026-09-17 이후 ON`

### [죽었다] 17. docs/runpod-fast-restart.md — mmpose/RTMPose 부트스트랩 절차
**왜:** 이 문서는 새 Pod 에서 mmcv/mmpose 를 빌드해 spike 를 돌리는 절차다. 서빙 부트스트랩은 rtmlib + onnxruntime-gpu 뿐이고 정본은 bootstrap_full.sh 다. mmpose 를 import 하는 코드는 research/spikes/spike_rtmpose.py 한 파일뿐이라 이 절차를 따를 소비처가 사실상 0이다. start.md 가 이미 '구본을 그대로 쓰면 15~45분 태운다'고 경고하는데 정작 이 문서에는 그 경고가 없다.

**근거:** docs/runpod-fast-restart.md:3-4(`새 Pod launch ~15-20분 안에 spike 실행 가능 상태로 복구`), :55-72(`setup.sh 가 NLF / MotionBERT / MediaPipe 처리` + `pip install mmcv` / `mim install mmpose`). 반대 근거 = backend/runpod_inference/bootstrap_full.sh:21 (`pip install ... rtmlib==0.0.15 google-genai cerebras-cloud-sdk fastapi uvicorn pydantic` — mmcv/mmpose 없음), .claude/commands/start.md:57-59 (`정본 = backend/runpod_inference/bootstrap_full.sh` · `.claude/scripts/setup_pod_full.sh 도 있는데 그건 ... 구본 ... mmcv CUDA 빌드까지 하느라 15~45분`). mmpose import 소비처 = backend/research/spikes/spike_rtmpose.py:168,225 뿐. ── 제안: 문서 1행 아래에 배너 `> ⚠ **사문(2026-08-31 이후).** 서빙 Pod 부트스트랩 정본은 backend/runpod_inference/bootstrap_full.sh (rtmlib + onnxruntime-gpu 1.22) 이고 기동 절차는 /start 다. 본 문서의 mmcv/mmpose 절차는 backend/research/spikes/spike_rtmpose.py 를 돌릴 때만 쓴다 — 서빙에 쓰면 15~45분을 태운다.`

**원장 한 줄:** docs/runpod-fast-restart.md:1 — 배너 신설 `사문(2026-08-31 이후). 서빙 정본 = bootstrap_full.sh + /start; 본 mmpose 절차는 spike_rtmpose.py 전용`

### [살았다] 18. pose_engines/__init__.py:6 — 존재하지 않는 경로를 가리키는 docstring
**왜:** 모듈 docstring 이 NlfPoseEngine 을 `backend/research/pose_engines/nlf/` 에 격리했다고 적는데 그 디렉터리가 없다. 실제 NLF 는 여전히 제품 패키지 안 pose_estimator.py 에 있고 research 쪽이 그것을 import 한다. 1번의 '어디에 남아 있나' 문장을 쓸 때 이 docstring 을 그대로 믿으면 틀린다.

**근거:** backend/shared/python/sunity_shared/analysis/pose_engines/__init__.py:6 `  - NlfPoseEngine: R&D 격리 (backend/research/pose_engines/nlf/ — 제품 import 경로 밖)`. `ls -d backend/research/pose_engines` → `No such file or directory`(실재 = __init__.py, evaluations/, spikes/). `grep -rn NlfPoseEngine backend --include=*.py` → 위 docstring 1건뿐(클래스 자체가 없다; __all__ 과 __getattr__ 에도 없음). 실물 NLF = shared/.../analysis/pose_estimator.py 의 `NlfPoseEstimator`, 이를 import 하는 곳 = research/evaluations/compare_engines.py:207, research/spikes/spike_motionbert.py:336, spike_rtmpose.py:427, debug_gap_root_cause.py:975, scripts/verify_nlf_pipeline.py:35, scripts/verify_self_comparison.py:226. ── 제안 after: `  - NLF: 클래스는 없다. sunity_shared/analysis/pose_estimator.py 의 NlfPoseEstimator 가 DEPRECATED 로 남아 있고(interfaces.py:6), 호출처는 backend/research/ 와 backend/scripts/verify_nlf_pipeline.py 뿐 — 제품 파이프라인 호출 0건.`

**원장 한 줄:** pose_engines/__init__.py:6 — `backend/research/pose_engines/nlf/`(부재) → `pose_estimator.py 의 NlfPoseEstimator(DEPRECATED), 호출처는 research/·scripts/verify_nlf_pipeline.py 뿐`

======================================================================
## 비평가 반려
살았다 6 / 죽었다 4 / 보류 2 — 플라이휠 크롭 반출 0 은 고장이 아니라 "올릴 게 없다"였고(진짜 미결은 강등 40건), 네 영역이 통째로 안 본 곳이 넷 있다(REQUIREMENTS 17건·ROADMAP 낡은 체크 14건·Phase 18/21/35·유령 worktree). 문서 수정안 2건은 적용하면 깨진다.

### [살았다] FLYWHEEL-LOG 크롭 반출 7사이클 0
**왜:** 반출기는 고장이 아니다. 사이클은 `admit 이면서 uploaded 아닌` 행만 올리는데(harvest_eye.py:700-707) 지금 admit 104건이 전부 uploaded=True 라 pending=0 이다 — 0 은 정상이고, 실제 반출 2회(08-14 100건 a0c172f0, 08-26 46건 afa40739)는 둘 다 사이클 밖 수동 실행이었다. 진짜 미결은 따로 있다: 09-14 재판정이 admit 144→104 로 40건을 hold 로 강등했는데 그 40건은 uploaded=True 인 채 남아 크롭이 학습 미디어 키에 그대로 있고(코드에 해제·삭제 경로 0 — harvest_eye.py 안에서 uploaded 를 쓰는 곳은 :743 True 대입 하나뿐), 그중 1건의 사유는 customer_anonymize_required 다. 그리고 09-14 신규 63행은 전부 hold(customer_anonymize_required 43 / optin_unverified_post_cutoff 20) — 눈 트랙 재료는 08-26 이후 한 건도 안 늘었다. '정상이라고도 고장이라고도 선언 안 됐다'의 답은 정상이지만, 그 칸을 보는 대신 봐야 할 칸은 admit 증감이다.

**근거:** backend/scripts/flywheel_cycle.sh:67-71(반출 단계, `업로드 N` 파싱) · backend/training/datagen/harvest_eye.py:700-707,743 · python3 집계: eye_manifest.json rows 216 / admit 104 / uploaded 104 / pending 0 · 09-14 직전본(git show 71289874^) rows 153 / admit 144 / uploaded 144 · 증분 diff: 신규 63행 전부 hold, admit→hold 40건(motion_unknown 39 / customer_anonymize_required 1) 이며 40건 모두 uploaded=True · `ls .planning/FLYWHEEL-BROKEN.md` → 없음(마지막 사이클 rc 전부 0)

**원장:** | 플라이휠 크롭 반출 0 | 살았다 | 반출기 정상(pending=0). 미결 = 09-14 강등 40건이 uploaded=True 로 S3 잔류(해제 경로 0) + 신규 63행 전량 hold |

### [살았다] .planning/REQUIREMENTS.md — Pending 17건 (SCORE-09 포함)
**왜:** 네 영역 중 아무도 REQUIREMENTS.md 를 열지 않았다. 여기 상태표에 Pending 17건이 남아 있고, STATE.md 는 그중 SCORE-09 를 두 곳에서 '별도 PENDING 잔류, Phase 23 을 SCORE-09 미처리로 닫지 말 것'이라고 명시적으로 못 박아두었다 — 정리 대상 1순위인데 판정이 안 됐다. 게다가 표 자체가 낡았다: SCORE-10(감점 엔진 교체)은 deduction_engine.tally 가 실재하고 vision_veto.SEVERITY_CAP·apply_downward_cap 이 코드에서 사라져 이미 완료인데 Pending 으로 적혀 있다. SCORE-09 의 실질 잔여(미보유+above-cutoff sensitivity 셋)는 Phase 18 의 '남은 일'과 같은 물건이라 두 곳이 같은 미결을 따로 세고 있다.

**근거:** .planning/REQUIREMENTS.md:42(SCORE-09 본문, belle 2026-06-23 소유권 문단) · :203-206 상태표 · awk 집계 = Complete 22 / Pending 17 · .planning/STATE.md:27,46 · 코드 대조: `grep -rn "def tally" deduction_engine.py` → :268 존재, `grep -rn SEVERITY_CAP vision_veto.py` → 0건, `grep -rn apply_downward_cap backend`(테스트 제외) → 0건

**원장:** | REQUIREMENTS Pending 17 | 살았다 | 네 영역 모두 미검토. SCORE-09 는 belle 지시로 열려 있고 SCORE-10 은 구현 완료인데 Pending — 표 재판정 필요 |

### [죽었다] ROADMAP.md 미체크 29건 중 14건
**왜:** 미체크 항목을 '남은 일'로 읽으면 안 된다. 29건 중 최소 14건(01-23/24/25, 05-03/04/05, 12-01/02/03, 23-03, 24-03, 25-01, 25-04, 32-15)은 디스크에 SUMMARY 가 이미 있다 — 체크박스만 안 찍혔다. w1:phase22-31 이 Phase 36 한 곳의 ROADMAP 어긋남만 잡았는데, 같은 병이 로드맵 전체에 퍼져 있다. 진짜로 안 끝난 미체크는 22-06(실행 완료·SUMMARY 없음)·22-08/09/10·31-12·33-07/16/21 과 TBD 4줄뿐이다.

**근거:** python3 스캔(.planning/phases 전수, PLAN↔SUMMARY 대조): 미작성은 22-06/08/09/10, 31-12, 33-07/16/21, 36-01/02 뿐 · 대조 실행 `ls <plan베이스>*SUMMARY*` → 위 14건 전부 EXISTS · `grep -c '\- \[ \]' .planning/ROADMAP.md` → 29

**원장:** | ROADMAP 미체크 29건 | 죽었다(14건) | SUMMARY 실재하는데 체크만 안 됨(01-23~25·05-03~05·12-01~03·23-03·24-03·25-01/04·32-15) |

### [죽었다] Phase 35 — 서버측 정렬 합성 비교 영상
**왜:** ROADMAP 은 'Plans: 0 plans / - [ ] TBD(run /gsd-plan-phase 35)' 로 미착수라 적는데, 핵심 산출물인 단일 합성 mp4 재생 경로는 이미 앱에 배선돼 운영 중이다 — result.tsx 가 RenderedComparePlayer 를 import 해 렌더하고, 백엔드에 canonical 키 생성기와 playback-url 재서명 계약이 있다. 플랜 트랙으로 재개할 대상이 아니라 quick 트랙으로 우회 완료된 것이고, ROADMAP 항목이 그 사실을 모른다. 다만 ROADMAP 의 세부 목표(전 동작 프로토타입 배치 → belle 느낌 평가)까지 전부 닫혔는지는 확인하지 않았다 — 닫아야 할 것은 '미착수' 표기다.

**근거:** app/src/app/analysis/result.tsx:44-46(import) · :1720(<RenderedComparePlayer …>) · app/src/types/analysis.ts:734-736,1070(renderedCompare 계약) · backend/shared/python/sunity_shared/s3keys.py:136 build_rendered_compare_key, backend/functions/pipeline/app.py:113 import · .planning/ROADMAP.md:1286 '- [ ] TBD (run /gsd-plan-phase 35 to break down)'

**원장:** | Phase 35 | 죽었다 | 합성 mp4 경로는 이미 배선·운영(result.tsx:1720). ROADMAP '0 plans/미착수' 표기가 낡음 |

### [보류] Phase 18 — expert deliberate-fault eval set
**왜:** PLAN 0 이라 네 영역 모두 건너뛰었지만 실체가 있다. 2026-06-19 에 pod-free baseline 이 박제돼 backend/evals/phase18/ 에 dataset·baseline·assert_baseline.py 가 실재하고, 다른 페이즈 게이트가 이 baseline 을 인용한다(ROADMAP:646 'EVAL18 변별 4쌍 퇴행0'). ROADMAP:587 이 남은 일을 직접 적어놨다 — 'Pod 재개 후 live sweep ↔ baseline 정량 대조 + sensitivity 셋(미보유+above-cutoff) Deferred'. 그 sensitivity 셋이 곧 SCORE-09 의 잔여라, 두 항목은 같은 재개 조건(Pod)을 공유한다.

**근거:** `ls backend/evals/phase18` → README.md, assert_baseline.py, baseline, dataset · .planning/ROADMAP.md:583-589(§Phase 18, 특히 :587 '남은 일') · :646(다른 게이트가 EVAL18 인용) · .planning/REQUIREMENTS.md:42(SCORE-09 sensitivity 정의와 동일 문구)

**원장:** | Phase 18 | 보류 | baseline·assert 실재(backend/evals/phase18). 남은 것 = Pod live sweep + sensitivity 셋 = SCORE-09 잔여와 동일 |

### [살았다] Phase 21 — 프로 셀프서비스 기준 등록
**왜:** PLAN 0 이라 네 영역이 안 봤는데, 이건 belle 2026-08-30 요구사항이고 파일럿 Step 2(정은지 촬영 → 자동 등록)와 직결이다. 더 중요한 건 충돌이다 — w1:문서어긋남 의 수정안 #4 는 '새 모션 등록 = 7단계 수동 절차(S3→seed 편집→Pod GPU 2회→promote)'를 문서에 박자고 제안하는데, Phase 21 성공기준 1·2 가 정확히 그 수동 절차를 없애는 것이다. 게다가 이미 배포된 엔드포인트 POST /reference/auto-register 가 메타(motionId/clipRange/checkpointJoints)를 Gemini A 로 자동 생성해 upsert 하는데 수정안이 그 존재를 아예 언급하지 않는다. 수동 런북을 정본으로 박으면 Phase 21 이 지워야 할 절차를 문서가 고착시킨다.

**근거:** .planning/ROADMAP.md:700-713(Phase 21 성공기준 1·2, 'Plans: 0 plans') · backend/functions/reference-auto-register/app.py:1-28(흐름 1~8, Gemini A → set_reference_motion_with_gemini) · backend/template.yaml:298-299(POST /reference/auto-register 라우트 배포됨) · .planning/STATE.md:47 '21-reference-angles-gpu ← 프로 셀프서비스 기준 등록. belle 08-30 요구사항'

**원장:** | Phase 21 | 살았다 | 파일럿 Step 2 직결. 수정안 #4 의 수동 7단계와 정면 충돌 — /reference/auto-register 가 이미 배포돼 있다 |

### [죽었다] 문서 수정안 #4 — docs/reference-motions.md §6 (7단계 등록 절차)
**왜:** 이 제안은 그대로 적용하면 새 기준 모션을 망가진 기질로 등록시킨다. 제안의 [4]단계 `reprocess_reference_motions_phase4.py --no-flip` 에 ROT180_INVERSION_ENABLED=1 이 빠져 있다 — 이 플래그는 RTMW 엔진이 런타임 env 로만 읽고 코드 기본은 off 라(rtmw_engine.py:62-66), 현행 활성 기질 rot180_v1 은 그 플래그가 켜진 상태로 추출된 것이다. 안 켜고 돌리면 신규 1편만 비회전 각도로 들어가 11편과 기질이 섞이고, 그 비대칭의 실측 결과가 '정은지 자기비교 100 → 60'이다(start_server.sh:24 가 같은 경고를 적어놨다). 추가로 §5 에 6블록을 append 하자는 제안은 이미 문서·seed 스크립트·Firestore 3중 사본인 데이터를 한 벌 더 늘린다 — 드리프트가 실제로 난 자리다.

**근거:** backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/rtmw_engine.py:62-66(`_ROT180_INVERSION_ENV`, '코드 기본 off. 켜는 곳은 Pod start_server.sh') · backend/runpod_inference/start_server.sh:24(ON + '한쪽만 되돌리면 … 정은지 자기비교 100 -> 60') · `grep -rn ROT180_INVERSION_ENABLED backend` → 스크립트/reprocess 경로에 설정 0건 · backend/scripts/reprocess_reference_motions_phase4.py:610-612(--no-flip 은 포인터 flip 생략일 뿐 회전과 무관) · Firestore 실측 reference/_release.activeCandidate = rot180_v1 (updateTime 2026-09-17T05:54:16Z)

**원장:** | 수정안 #4 (§6 7단계) | 죽었다 | 그대로 쓰면 ROT180 env 누락으로 신규 1편만 비회전 = 기질 혼합(100→60). auto-register 경로도 누락 |

### [보류] 문서 수정안 #9 — Pod 종료 시 Lambda RUNPOD_ANALYZE_URL 제거
**왜:** 관측(Lambda·SSM 이 죽은 Pod 을 가리킨다)은 내가 직접 재현했고 맞다. 그런데 처방 두 줄이 틀렸다. (1) '지우면 폴백 없이 실패하는 상태가 풀린다'는 인상을 주는데, 지워도 분석은 살아나지 않는다 — URL 이 비면 lambda_handler 가 로컬 _process 로 가는데 그 경로는 배포 환경에서 ImportError 로 의도적으로 막혀 있다(pipeline/requirements.txt 머리말). 사용자 결과는 양쪽 다 server_error 다. (2) 'SSM 파라미터도 함께 비운다'는 실행 불가에 가깝다 — 해당 파라미터는 Type=String 이라 빈 값을 못 넣고, template.yaml:342/481 이 배포 때 `{{resolve:ssm:…}}` 로 이 이름을 해석하므로 삭제하면 다음 sam deploy 가 그 자리에서 깨진다. 절차에 한 줄 넣는 것 자체는 맞지만 문구는 '자리표시자 URL 로 되돌린다 + 분석은 Pod 없이는 어차피 실패한다'여야 한다.

**근거:** 실행(AWS_PROFILE=sunity-motion): `aws ssm get-parameter --name /sunity/motion/pod-expected` → down · `aws lambda get-function-configuration … RUNPOD_ANALYZE_URL` → https://elevev58iv4mox-8000.proxy.runpod.net/analyze · 같은 값이 SSM /sunity/motion/runpod-analyze-url 에도 있고 Type=String · `curl … /health` → 404 · backend/functions/pipeline/app.py:9159-9175(URL 없으면 _process) · backend/functions/pipeline/requirements.txt:1-4('Lambda 폴백(_process) 경로는 deploy 환경에서 ImportError 로 의도적 차단') · backend/template.yaml:342,481

**원장:** | 수정안 #9 (종료 시 URL 제거) | 보류 | 관측은 맞으나 처방 오류 — 지워도 분석 안 살아남(ImportError), SSM 빈값 불가·삭제 시 sam deploy 파손 |

### [죽었다] backend/template.yaml:29-40 — RunpodAnalyzeUrl / RunpodAuthToken 파라미터
**왜:** 문서어긋남 영역이 template.yaml 의 파라미터 설명문을 안 봤다. 이 두 파라미터는 선언만 있고 템플릿 어디에서도 !Ref 되지 않는다 — 실제 env 는 SSM dynamic reference 로 들어간다(:342,:481). 즉 사문인데, 설명문이 지금도 'RunPod URL 이 빈 문자열이면 PipelineFunction 이 자체적으로 NLF 추론 시도(폴백, Lambda CPU 에선 NaN)'라고 가르친다. 백본은 RTMW 로 바뀌었고 그 폴백은 ImportError 로 막혀 있으니 두 번 틀린 문장이며, 하필 수정안 #9 가 같은 오해 위에 서 있다. 배포 스택에는 이 파라미터가 낡은 값으로 박제돼 있기까지 하다.

**근거:** backend/template.yaml:29-40(선언 + 설명), `grep -n 'RunpodAnalyzeUrl\|RunpodAuthToken\|!Ref Runpod' backend/template.yaml` → 선언 2줄과 주석 2줄뿐, 참조 0 · :342/:481 `{{resolve:ssm:/sunity/motion/runpod-analyze-url}}` · 실행 `aws cloudformation describe-stacks --stack-name sunity-motion-pilot` → Parameters 에 RunpodAnalyzeUrl=https://p56qusi8cgc91z-8000.proxy.runpod.net/analyze (현 Lambda env 와 다른 세대), LastUpdatedTime 2026-07-21T16:17Z

**원장:** | template.yaml Runpod 파라미터 2개 | 죽었다 | 참조 0 의 사문 파라미터. 설명문이 NLF 폴백을 가르침 — 수정안 #9 의 오해 근원 |

### [살았다] backend/template.yaml Phase 31 파라미터 5개 (Default 없음) — 배포 차단
**왜:** w1:phase22-31 이 surprise 로만 적었지만 이건 네 영역 통틀어 가장 실질적인 잠긴 문제라 항목으로 올린다. 독립 확인: Default 없는 파라미터는 VisualInputBucketName·DisplayJudgeConfidence·TrainingJudgeConfidence·DisplayPoseTolDeg·TrainingPoseTolDeg 5개이고 samconfig 의 parameter_overrides 는 3개만 준다. 배포 스택에는 그 5개가 아예 없고(파라미터 5개 = Stage/VideoBucket/FirebaseSaParam/RunpodAnalyzeUrl/RunpodAuthToken) 마지막 갱신이 2026-07-21 이다. 즉 죽은 Phase 31 생성 트랙의 잔해가 살아 있는 백엔드의 배포 경로를 실제로 막고 있고, 실증이 한 달 뒤인데 지금 Lambda 코드를 고쳐야 할 일이 생기면 여기서 멈춘다.

**근거:** python3 파싱(backend/template.yaml Parameters): default=False 인 것 5개 = VisualInputBucketName, DisplayJudgeConfidence, TrainingJudgeConfidence, DisplayPoseTolDeg, TrainingPoseTolDeg · backend/samconfig.toml:18 parameter_overrides 3개 · 실행 `aws cloudformation describe-stacks` → 배포 파라미터 5개(Visual* 없음), Status UPDATE_COMPLETE, Updated 2026-07-21T16:17Z · .planning/phases/31-api-visual-correction/smoke/CALIBRATION.json → blocked:true, blocked_reasons ['insufficient_pass_samples:3<4','confidence_axis_non_discriminating:all_4_grid_values_tie_at_FA4']

**원장:** | template.yaml Phase31 파라미터 | 살았다 | Default 없는 5개 vs samconfig 3개 → sam deploy 불가. 배포 스택(07-21)엔 Visual 파라미터 0 |

### [살았다] backend/runpod_inference/README.md:36-37 — ROT180 기본값 문구
**왜:** 문서어긋남 영역이 이 줄을 '낡음'으로 분류했는데 심각도를 올려야 한다. 이 문장은 단순히 오래된 게 아니라 '지금은 누락돼도 그 함정이 아니다'라고 안심시킨다 — 09-17 에 기준 라이브러리가 rot180_v1 로 승격된 뒤로는 그 누락이 곧 학생만 비회전인 비대칭 비교이고 실측 결과가 100→60 이다. 실증이 한 달 뒤이고 Pod 은 매번 새로 띄우므로 맨손 기동 한 번이면 그대로 발현된다. 다만 제안 문구 '기본 ON' 은 코드와 어긋난다 — 코드 기본은 여전히 off 이고 ON 은 start_server.sh 한 곳뿐이다. 그리고 포인터(Firestore)와 엔진 플래그(env)를 묶어 검증하는 코드가 없다 — promote 스크립트는 per-doc 해시만 본다.

**근거:** backend/runpod_inference/README.md:36-37 원문 · rtmw_engine.py:62-66(코드 기본 off) · start_server.sh:24(ON, 100→60 경고) · Firestore 실측 reference/_release.activeCandidate=rot180_v1 · `grep -rn activeCandidate backend | grep '\.py:'` → 파이프라인/서버 기동 경로에 플래그-포인터 정합 단언 0건(promote_reference_version.py 는 content hash 만 검증)

**원장:** | runpod README:36-37 | 살았다 | '누락돼도 함정 아님'은 09-17 이후 위험 문구(맨손 기동 시 100→60). 단 '기본 ON' 표현은 코드와 불일치 |

### [죽었다] 유령 worktree .claude/worktrees/agent-a572524a5cb0c0b23
**왜:** 네 영역 모두 못 봤다. 48일 전(2026-08-01) quick-260801-gbk 의 RED 테스트 커밋에 물린 worktree 와 브랜치가 그대로 남아 있고, 그 안에 .planning 전체 사본이 있어 전수 grep·find 가 항상 두 벌을 집는다(이번 CALIBRATION.json 검색에서 실제로 두 경로가 나왔다). 메모리에 이미 '서브에이전트 게이트 수치를 믿지 말 것 — worktree 에 backend/.venv 가 없어 다른 인터프리터로 돈다'는 함정이 박혀 있는데 그 물건이 아직 살아 있는 것이다. belle 이 말한 '정리가 안 되는' 자리 중 하나.

**근거:** `git worktree list` → /Users/kimtaesung/Dev/SunityMotion/.claude/worktrees/agent-a572524a5cb0c0b23  c0d662de [worktree-agent-a572524a5cb0c0b23] · `git log -1 --date=short c0d662de` → 2026-08-01 test(quick-260801-gbk): 감점별 측정 순간 산출 실패 테스트 (RED) · `git branch` 에 worktree-agent-… 존재 · `find . -name CALIBRATION.json` → 본체와 worktree 사본 2건

**원장:** | worktree agent-a572524a5cb0c0b23 | 죽었다 | 2026-08-01 RED 커밋에 물린 유령 worktree+브랜치. .planning 사본이 전수 검색을 오염 |

- 놀란것: w1:phase22-31 의 surprise '.planning/TRAINING-DUE.md 는 git 미추적(??)' 은 이미 해소됐다. 1차 정리 커밋 994fd341 이 내용을 정정해 커밋했고 b47e53b5 가 .gitignore 를 정리했다 — `git ls-files --error-unmatch .planning/TRAINING-DUE.md` 가 통과한다. 그 보고서는 1차 정리 이전 HEAD(d96d18e5) 기준이라 최소 이 한 건은 이미 낡았다. 지금 남은 미추적은 docs/openapi.yaml(2026-08-18, 라이브 4라우트와 일치 — /visual/rotation 만 없음)과 reference-downstream-backfill.json(2026-06-15 산출 아티팩트) 둘뿐이다.

- 놀란것: 배포 스택과 실환경이 서로 다른 Pod 세대를 가리키고 있다. CloudFormation 파라미터 RunpodAnalyzeUrl = p56qusi8cgc91z, 실제 Lambda env 와 SSM = elevev58iv4mox, 그리고 그 주소는 404 다(직접 curl). Lambda env 를 CLI 로 바꿔 온 이력과 스택 파라미터가 3중으로 갈라져 있어, 누가 sam deploy 를 하면 어느 값이 남는지 아무도 예측 못 한다.

- 놀란것: 역립 귀속 마커(inversion-joint-attribution)는 '살았다'가 맞지만, 회전 묶음 이후 사실상 발화 0 일 가능성이 크다. 운영 925건 전수에서 발화 18건 중 17건이 elbow-twist 한 동작이었고(pipeline/app.py:8470-8474), 묶음은 belle 역립 케이스의 tol 초과 관절을 8→2 로 줄였는데 발화 하한은 여전히 5 다(:2399). 즉 게이트가 켜져 있는지 꺼져 있는지를 재는 것이 다음 일이고, 그 재측정 없이는 '살았다'도 '죽었다'도 확정 못 한다.

- 놀란것: 네 영역이 '완료'를 '죽었다'로 적었다(22-06 bake-off, 36-01 계정 화면). 과제가 준 정의는 죽었다 = 사문·상위결정 기각·기능제거이고 완료는 그 셋 중 아무것도 아니다. 원장에 그대로 붙이면 belle 이 'Qwen3-VL-8B 백본 결정이 기각됐다'로 읽는다 — 라벨을 '완료(원장 표기만 누락)'로 바꿔야 한다.

- 놀란것: 네 영역의 커버리지 자체는 debug/ 에 한해 정확했다. .planning/debug 의 나머지 4건(keypoint-drift-fps-label, phase17-e2e-five-issues, same-video-score-mismatch, video-sync-and-keypoint-finetune)은 전부 status: fixed/resolved 라 제외한 것이 옳다. 반대로 phases/ 는 22·31·33·36 만 봤고 PLAN 0 인 18·21·34·35 를 통째로 비웠다 — 그 넷이 이번 판정의 빈칸이었다.

- 놀란것: docs/reference-motions.md §4 를 '전부 죽었다'로 지우자는 제안은 한 칸 과하다. checkpoints 가중평균과 heroFrameUrl 은 소비처 0 이 맞지만, clipRange 는 백엔드(pipeline/app.py:7989-7993 공유 베이스 경계)와 앱(referenceMotions.ts:178 정규화, analysis.ts:1217 타입)에 살아 있다. 규칙 1 은 '전량 삭제'가 아니라 '실제 소비처는 공유 베이스 경계 한 곳'으로 정정하는 편이 맞다.

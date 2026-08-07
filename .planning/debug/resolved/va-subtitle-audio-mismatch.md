---
status: resolved
trigger: "V-A 자막-음성 불일치: 감점 카드 음성 안내가 자막(cueLine)과 다른 내용으로 재생됨. belle 실기기에서 앱측 수리 2회(usc 재생 불변식, wj3 플레이어 큐마다 재생성·스테일 replace 제거, OTA 747ee98f) 후에도 재현"
created: 2026-08-07T09:02:36+09:00
updated: 2026-08-07T10:33:00+09:00 (2차 수리 — belle 반려 반영)
---

## Current Focus

reasoning_checkpoint:
  hypothesis: "quick-260802-mrg(08-02)가 자막을 결함-선행(statusLine + 목표절 제거 actionLine)으로 바꿨는데 Polly 합성 텍스트는 cueLine 전문(목표절 포함) 그대로라, 08-02 이후 모든 큐에서 음성 내용≠자막 내용이 구조적으로 성립한다. 08-06 F-6 해소로 음성이 처음 들리자 표면화됐고, 재생 역학 수리(usc/wj3)로는 원리적으로 잡히지 않는다"
  confirming_evidence:
    - "whisper 실측: 현세대 mp3 4개 = cueLine 전문(목표문 '목표는 거꾸로 매달린 채…' 포함) — 4개 전부 같은 도입문"
    - "코드 실측: 자막 = composeCueSubtitleKo = statusLine + actionLine(목표절 삭제) (deductionSheet.ts:406-422) / 합성 = Text=rec['cueLine'] (pipeline/app.py:3809)"
    - "260802-mrg-SUMMARY.md:284 — '음성 mp3 ↔ 자막 낭독 차이 = 안 들었다(F-6 무음이라 관측 불가)' 로 박제된 알려진 미검증 리스크"
    - "조인 사슬 전 구간 recordId 원자 조인 확인 — 교차 record 오귀속 벡터 부재 (S-3 소거)"
  falsification_test: "belle 재확인에서 '음성이 자막과 다른 관절을 말한다'(예: 팔꿈치 자막에 무릎 음성)가 관측되면 이 가설만으론 불충분 — 그 경우 S-2(OTA 미적용으로 스테일 replace 잔존)를 재조사. 반대로 '음성 첫 문장이 화면에 없다/큐마다 같은 문장으로 시작한다'는 관측은 본 가설 확증"
  fix_rationale: "음성이 자막과 같은 텍스트를 말하게 만든다 — 합성 텍스트를 자막 조립식(statusLine + actionLine)과 동일하게 변경(백엔드 미러). 자막을 cueLine 으로 되돌리는 역방향은 belle 승인 UX(결함-선행, mrg 의 수리 대상이 바로 그것)를 파괴하므로 배제. 기존 belle doc 은 로컬 Polly 재합성으로 같은 S3 키에 덮어쓰기(키 불변 → doc 무접촉)"
  blind_spots: "(1) belle 기기 OTA 적용 여부 미확인 — 단 최신 코드에서도 발산이 성립하므로 수리 필요성은 불변 (2) belle 의 정확한 지각(어느 문장을 '다르다'고 인지했는지)은 실기기 확인에서만 판별 (3) 32-GATE B안 '문구 변경 금지=cueLine 그대로 합성' 결정을 변경함 — 근거: 그 결정의 전제(자막==cueLine)가 mrg 로 소멸, 실측>이전 결정"
next_action: "종결 — belle 08-07 낮 실기기 확인: '엘보 좋다'(큐 4개 제 순간·문장 상이·마침표) + '파워스핀도 잘 나옴'. 음성==자막 계약 성립. 킵업 무발화는 의도 동작으로 설명·수용(음성 복귀 = V-2 데이터측, split 측정 순간 산출 후 Pod 재분석). belle 신규 4건(번호 시간순·재개 백오프·인접 큐 체이닝·음성 부위 빨강)은 quick-260807-fpw 로 분리 수리"

## Symptoms

expected: 각 감점 카드 큐에서 자막(cueLine)과 같은 내용의 음성이 재생된다
actual: belle 실기기에서 자막과 다른 내용의 음성이 재생된다. 앱측 오재생 경로 제거(wj3: 큐마다 플레이어 신규 생성, replace 0) 후에도 증상 불변
errors: 없음 (음성은 정상 재생되나 내용이 자막과 다름 — silent mismatch)
reproduction: belle 실기기, belle 계정 엘보 분석(elbowtwistsisterFault1785373695) 재생. 08-06 밤 3차 확인에서 재현. 시뮬 재현 여부는 미확인(시뮬에선 음성 내용 대조를 아직 안 함)
started: 08-06 밤 — 음성·영상이 동시에 살아 돌아간 첫날 관측. usc(불변식)·wj3(플레이어 재생성) 2회 수리+OTA(747ee98f) 후에도 belle 3차 확인에서 재현

## Suspects (우선순위순 — 하나씩 죽일 것, 원인 확정 전 수리 금지)

- S-1: 현세대 mp3 4개의 내용이 cueLine 과 다르게 합성 — 판별: whisper 전사 vs cueLine 대조 (결정적, 기기 불요)
- S-2: OTA 미적용 — belle 재확인이 발행 직후라 옛 번들(747ee98f 이전)일 수 있음. 판별: belle 앱 완전 종료 2회 후 재확인 + `eas update:list` 대조. S-1 양성이면 부차
- S-3: 자막-음성 조인 어긋남 — cueWindows 는 시간순 정렬인데 recordId 부여가 doc 순서 인덱스면 짝이 밀림. 판별: app/src/app/analysis/result.tsx 의 cueWindows/audioCues 빌드 지점에서 text·recordId 가 같은 record 객체에서 나오는지 코드 판독 + 조인 단위 테스트
- S-4: 합성 시점 원본 — 08-06 재분석 중 "Cerebras 코칭 실패 → 수치 폴백" 2건. 폴백 경로가 cueLine-음성 짝을 깨는지. 판별: backend/functions/pipeline/app.py ~3866 `_synthesize_coach_audio_items` 판독 — 텍스트 소스가 record.cueLine 인지, 인덱스 재사용인지

## Environment / Access (조사에 필요한 실무 정보)

- S3: bucket `sunity-motion-pilot-videos`, belle 엘보 prefix `results/csKWYvI3WCPYPysNQ9KkWecaUvq1/elbowtwistsisterFault1785373695/`. aws CLI profile `sunity-motion`
- 현세대 mp3 4개 = r00 right_elbow / r01 right_shoulder / r02 left_hip / r03 right_knee. 구세대 8개(r00~r07, 07-31 옛 8-record 명명)와 같은 prefix 에 공존
- Firestore: project `sunity-ai-coach`, doc = users/csKWYvI3WCPYPysNQ9KkWecaUvq1/analyses/elbowtwistsisterFault1785373695. Admin SA 키 = 레포 루트 firebase-sa.json (backend 스크립트들이 쓰는 것과 동일). 참고: 같은 문서 ID 가 시뮬 계정들(fvcNXzEqKjgqVxRPVSj1iwFnIpn2, Wm5KTg0OsObIHchuMmfMr1hDSxy2) 아래에도 존재 — 계정 혼동 금지 (08-01 의 교훈)
- whisper: faster-whisper 설치 여부 미확인 — 없으면 pip 설치(CPU, small 모델이면 4개 수십 초). 대안 = Gemini flash 오디오 전사(키는 SSM, --profile sunity-motion)
- 시뮬 검증 루프(수리 후): 개발 빌드 #29 + Metro + 시뮬 계정 Wm5KTg0OsObIHchuMmfMr1hDSxy2 (doc 4건+S3 복사 완료)
- pytest 기준선: `PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests` = 59 passed (인터프리터 고정 필수)
- 재합성 필요 시: Polly 는 AWS — 로컬 boto3 합성 가능성 먼저 확인, 불가하면 새 Pod 1회 (Pod 는 현재 없음, 238o5d6rfok4g6 은 08-06 밤 Terminate·볼륨 보존)

## Prior Evidence (자정 S3 실측 — 이 세션 시작 전 확보)

- timestamp: 2026-08-07T00:30 (approx)
  checked: belle 계정 엘보 prefix S3 목록 + 12개 mp3 전부 다운로드·md5
  found: mp3 12개 = 현세대 4(r00 right_elbow / r01 right_shoulder / r02 left_hip / r03 right_knee) + 07-31 구세대 8(r00~r07 옛 명명). 구세대 안에서 r02:left_shoulder.mp3 md5 == r03:right_shoulder.mp3 md5 — 좌/우 어깨 음성이 바이트 동일
  implication: 합성 파이프라인이 잘못된 내용(다른 record 의 텍스트)을 쓸 수 있음이 실증됨. 단 이것은 구세대 산출물 — 현세대 4개도 같은 결함인지가 S-1 의 판별 대상. (다운로드본은 이전 세션 스크래치라 소멸 — 재다운로드 1분)

- timestamp: 2026-08-06T23:50 (approx)
  checked: 앱측 오재생 경로 (wj3 수리)
  found: 큐마다 플레이어를 새로 만들어(replace 제거) 스테일 아이템 재재생 경로를 구조적으로 제거. 시뮬 회귀 PASS(큐 4개 발화·대칭·17초 완주). 그 후에도 belle 실기기에서 자막-음성 불일치 재현
  implication: "이전 큐 음성이 남아 재재생" 계열 앱 원인의 개연성이 크게 낮아짐 — 원인이 앱 재생 로직 밖(데이터 자체 또는 조인)일 가능성 증가. 단 OTA 적용 여부(S-2) 미확인이라 완전 소거는 아님

## Eliminated

- hypothesis: "expo-audio 네이티브 결함 (play 가 종료 옵저버 미등록 / replaceCurrentItem 이 이전 위치에서 재생 / isPlaying 스테일)"
  evidence: 소스 판독으로 반증 — play() 는 종료 옵저버를 매번 재등록(AudioPlayer.swift:63-65), replaceCurrentItem 은 새 아이템을 0에서 시작, isPlaying 은 실시간 조회 (08-01 세션 실측, CONTINUE "안 건드릴 것" 절)
  timestamp: 2026-08-01

- hypothesis: "S-1 — 현세대 mp3 4개의 내용이 cueLine 과 다르게 합성되어 있다"
  evidence: faster-whisper(small, ko) 전사 4건 전부 제 record 의 cueLine 과 일치 (변별 중간절 1:1 정합). md5 동일 건(현세대 r00 == 구세대 r01 right_elbow)은 같은 텍스트의 결정적 Polly 재합성으로 설명 — 오귀속 아님
  timestamp: 2026-08-07T09:52

- hypothesis: "S-3 — 자막-음성 조인 어긋남 (교차 record 오귀속)"
  evidence: 조인 사슬 전 구간(cueWindows 빌드→cueTrack→VideoCompare tick→audioCue 캐시→playback-url exact 비교)이 recordId 키 원자 조인 — text 와 audio 가 항상 같은 record 객체/키에서 유래. 인덱스 조인 없음. 역사적 교차 벡터(플레이어 replace)는 wj3 가 제거
  timestamp: 2026-08-07T10:10

- hypothesis: "S-4 — Cerebras 폴백 경로가 cueLine-음성 짝을 깨뜨림"
  evidence: whisper 전사로 4개 mp3 == 각자의 cueLine 확증 — 합성 시점 텍스트-키 짝은 정상이므로 폴백 경로 무관 (S-1 판별이 S-4 도 함께 소거)
  timestamp: 2026-08-07T09:52

## Known-good (재조사 금지)

- 재생 불변식(usc): belle 실기기에서 작동 실증 — 큐1 재개 정상, 실패 시 대칭 정지 (08-06 밤 2차 관측 스크린샷)
- playback-url 훅은 doc 저장 키와 exact 비교 — 구세대 mp3 가 같은 prefix 에 있어도 재생 대상으로 선택될 수 없음 (구세대 공존 자체는 오재생의 직접 원인이 아님; 대신 합성 버그의 물증이자 진단 오염원)
- coachAudio 키 정합: 08-06 belle 계정 복사 검증에서 음성 키 전건 belle uid + S3 객체 존재 확인 (_verify_belle_0806.py)

## Evidence

- timestamp: 2026-08-07T09:40
  checked: belle 엘보 prefix mp3 12개 재다운로드 + md5 전수 대조 (scratchpad/va-mp3)
  found: 현세대 r00:right_elbow == 구세대 r01:right_elbow 바이트 동일(d2d418c4). 구세대 좌/우 어깨 동일(6b065e87) 재확인. 현세대 r01/r02/r03 은 각각 유일 md5. S3 타임스탬프 12개 전부 08-06 19:43 (belle 계정 복사 시점 — 복사가 타임스탬프 갱신)
  implication: md5 동일 = "같은 텍스트 → 결정적 Polly → 같은 바이트"로 설명 가능 — 그 자체로는 오귀속 증거 아님. 전사 대조가 결정

- timestamp: 2026-08-07T09:50
  checked: Firestore belle doc (users/csKWYvI3WCPYPysNQ9KkWecaUvq1/analyses/elbowtwistsisterFault1785373695) — result.deductionBreakdown.records 4건 cueLine + result.coachAudio
  found: records = r00 right_elbow(-10.7) / r01 right_shoulder(-10.0) / r02 left_hip(-2.6) / r03 right_knee(-4.4), 각각 고유 cueLine(공통 도입문 + 변별 중간절). result.coachAudio.status=done, items 4건 = 현세대 키와 정확히 일치 (coachAudio 는 top-level 아닌 result 하위)
  implication: 앱이 재생 대상으로 삼는 키 = 현세대 4개 확정. 구세대 8개는 doc 에서 참조되지 않음

- timestamp: 2026-08-07T09:52
  checked: 현세대 mp3 4개 faster-whisper(small, ko) 전사 vs cueLine 1:1 대조
  found: 4건 전부 제 cueLine 과 일치 (r00 "팔꿈치로 폴을 단단히 감은 엘보 그립…" / r01 "그립 쪽 견갑을 단단히 잡은 채 팔과 몸통 사이 각…" / r02 "가위 스플릿을 유지한 채 왼쪽 다리 각…" / r03 "윗다리는 폴 축을 따라 수직으로 뽑고 훅은 걸린 모양 그대로 둔 채 오른쪽 무릎…"). whisper 소오류(경갑/겉구로)뿐, 변별 절 전부 정확
  implication: S-1 소거 — S3 음성 데이터는 cueLine 과 정합. 원인은 데이터가 아니라 앱측 조인(S-3) 또는 OTA 미적용(S-2). 주의 — 4개 cueLine 은 도입문이 동일해 짝이 밀려도 첫 문장은 같게 들림 (belle 가 "다른 내용"을 인지한 건 중간절 차이)

- timestamp: 2026-08-07T10:10
  checked: 자막-음성 조인 사슬 전체 코드 판독 (result.tsx cueWindows 빌드 → cueTrack.ts buildCueWindows/activeCue → VideoCompare.tsx tick speakCue → audioCue.ts urlCache/speakCue → backend playback-url _handle_coach_audio)
  found: 전 구간 recordId 키 원자 조인 — cueWindow 는 같은 record 객체에서 text+recordId 동반 생성(result.tsx:1980-1985), activeCue 는 윈도우 통째 반환, speakCue({cueId: cue.recordId, text: cue.text}) 동일 객체, urlCache 는 recordId 키, 백엔드는 recordId 로 canonical key 구성 + doc items 의 같은 recordId 항목과 exact 비교 후 그 key 만 서명(playback-url/app.py:157-169). 인덱스 기반 조인 없음
  implication: 현재 코드에는 record 간 짝밀림 벡터가 없다 — S-3(교차 record 오귀속) 소거. 유일한 역사적 교차 벡터(플레이어 재사용 replace)는 wj3 가 제거

- timestamp: 2026-08-07T10:15
  checked: 자막 조립(deductionSheet.ts composeCueSubtitleKo/splitGoalClause) vs 음성 합성 소스(pipeline app.py _synthesize_coach_audio_items)
  found: 자막 = statusLine + actionLine(cueLine 에서 목표절 "목표는 …예요. " 제거) — quick-260802-mrg. 음성 = Polly Text=rec["cueLine"] 전문(목표절 포함, pipeline/app.py:3809). 즉 음성 도입문("목표는 거꾸로 매달린 채 윗다리를 폴을 따라 곧게 뽑는 자세예요" — 이 분석 4개 record 전부 동일)은 화면에 없고, 자막 도입문(statusLine 결함문)은 음성에 없다
  implication: 08-02 이후 모든 큐에서 음성≠자막이 구조적으로 성립. 게다가 한 분석의 4개 큐가 전부 같은 문장으로 발화를 시작 — "이전 큐 음성이 또 나온다" 인식(belle ① 보고)도 이중 설명됨

- timestamp: 2026-08-07T10:18
  checked: .planning/quick/260802-mrg-merge-display-and-fix-copy/260802-mrg-SUMMARY.md 미검증 표
  found: 284행 — "| 4 | 음성 mp3 ↔ 자막 낭독 차이 | 안 들었다 | mp3 는 분석 시점 cueLine(목표 포함), 자막은 statusLine+행동. 음성 기본 off + F-6 무음 미해결이라 현재 관측 불가 |"
  implication: 이 발산은 mrg 시점에 알려진 미검증 리스크로 박제돼 있었다. 08-06 F-6 해소로 음성이 처음 들리자 그대로 표면화 — 증상 시작일(08-06)·수리 2회 무효(재생 역학과 직교)·전 큐 재현이 전부 이 하나로 설명된다

- timestamp: 2026-08-07T10:45
  checked: 수리 적용 + 3중 검증 (미러 정합 / whisper 재전사 / S3 실측)
  found: 앱 실함수 vs Python 미러 12 record 문자 단위 일치. belle 재합성본 4건 whisper 전사 = 자막과 동일 문장 시작(전 큐 상이한 결함문, '목표는' 시작 0건). 3계정 12키 08-07 09:24 갱신·md5 유일. pytest 기준선 유지(coach_audio 27 passed), tsc 통과. doc 무접촉(키 불변)이라 앱은 재생만 하면 새 음성 — OTA·재로그인 불요
  implication: 음성==자막 계약이 데이터·코드 양쪽에 성립. 남은 것 = belle 실기기 지각 확인 (falsification_test — 만약 여전히 '다른 관절을 말한다'면 S-2 재조사)

- timestamp: 2026-08-07T10:55
  checked: 오케스트레이터 갭 검사 — 재합성 범위가 엘보 한 동작에 매몰됐는지 (collection_group("analyses") 전수 스캔, 1125 doc)
  found: coachAudio 보유 76 doc / 4 uid. 유저 대면 3계정에 엘보 외 잔여 15키 — 킵업 1 + 파워스핀 3 (계정별) + belle 실업로드 071df9f894d64d1696f106e613f51f5c 3키. phase25e…(eval 하네스) 66 doc 은 앱 재생처 없음 → 재합성 제외
  implication: 발산은 08-02 이후 전 음성 큐에 성립하므로 엘보 12키만으로는 불완결 — belle 이 파워스핀/킵업을 열면 V-A 그대로 재현됐을 것 (fix-generalize 원칙)

- timestamp: 2026-08-07T11:00
  checked: 잔여 15키 재합성 (resynth_all.py — 실 pipeline _synthesize_coach_audio_items/_coach_audio_speech_text 사용) + whisper 전수 검증 (verify_new.py)
  found: 15/15 업로드, 전건 키 집합 == doc itemKeys (doc 무접촉). whisper 전사 15건: 전건 제 자막 문장과 일치, "목표는" 시작 0건 (불일치로 보인 10건은 ASR 표기 오차 — 킵업→키복, 파워스핀→파워스픈, 견갑→경갑, 괄호→쉼표)
  implication: 유저 대면 3계정의 음성==자막 계약이 27키 전부(엘보 12 + 잔여 15)에서 성립

- timestamp: 2026-08-07T11:05
  checked: 구세대 mp3 잔재 정리 (cleanup_oldgen.py — results/{uid}/ 전 prefix 의 mp3 중 어떤 doc coachAudio.items 에도 미참조 = 고아)
  found: 고아 42키(3계정 x 14, 전부 07-31 구세대 8-record 명명 — pdshapeCorrect 하위 포함) dry-run 매니페스트 검수 후 삭제. 재목록 = belle 11 / 구시뮬 8 / 신시뮬 8, 고아 0, referenced-but-missing 0
  implication: 세대 혼합 진단 오염원 제거 완료. 참조 키는 전건 보존

- timestamp: 2026-08-07T morning (2차 사이클 — belle 실기기 반려 접수)
  checked: belle 킵업 확인 — "포인트가 아닌 처음 시작하자마자 음성안내가 뜸" + "마침표가 되어야할 문장을 그대로 읽기도 함"
  found: 반려 ① = V-2 로 알려져 있던 미인증 큐 앵커(킵업 split 은 측정 순간이 없어 zoom userFrameIdx=16 → 0.889s 가짜 시각 폴백)가 실사용을 막는 수준임이 확정. 반려 ② = 1차 수리의 결함 — 합성·자막 모두 statusLine+action 을 **공백으로만 결합**(둘 다 문장부호 없음 실측)해 Polly 가 run-on 낭독. whisper 검증이 문장부호를 지운 정규화 비교라 이 결함을 못 잡았다 (검증 맹점)
  implication: 수리 2건 — (a) 마침표 경계(양측 lockstep) (b) 큐 앵커를 인증 순간으로

- timestamp: 2026-08-07T10:00
  checked: 큐/틱 앵커 데이터 전수 실측 (belle 3 doc + 실업로드)
  found: 엘보 4 record 전건 atVideoSec(4.9/7.4/10.1/11.1s) 보유 — zoom 프레임도 그 순간과 일치(큐 위치는 이미 정상). 가짜 앵커는 **측정 순간 없는 record 뿐** = split_angle(킵업 0.889s, 파워스핀 r01 2.11s) + 실업로드 071df9f8(3건 전부 미보유, zoom 전부 frame 34 동일). 큐 배선은 rec.atVideoSec 을 안 쓰고 zoom.userFrameIdx 만 사용, 틱 빌더는 공유 median 단일 시점(record별 분리가 예정 확장으로 주석 명기)
  implication: 정책 = 기존 승인 게이트("사진 인증 없으면 감점 부분이라 말하지 않는다")의 시간축 적용 — atVideoSec 인증 record 만 그 순간에 자동 발화, 미인증은 억제(카드에 존치, 재분석 시 자동 복귀). 틱은 record별 분리 + 미인증만 종전 median 유지(wj3 복원 보존)

- timestamp: 2026-08-07T10:30
  checked: 2차 수리 적용 + 검증 (마침표 lockstep + centerSec 큐 + record별 틱)
  found: 앱 테스트 78 passed(신규 centerSec 4케이스·틱 4케이스 포함), tsc GREEN, coach_audio 27 passed, 미러 정합 27/27 문자 단위. 27키 전 재합성 + whisper 전수: "목표는" 0건·관절 키워드 불일치 0건. **시뮬(개발빌드 #29) 실측**: 킵업 = 전 구간 자막 0·정지 0·6.7s 완주(스플릿 킥은 실제 중반부 — 구 앵커가 가짜였음 시각 확정) / 엘보 = 4큐가 4.9→7.4→10.1→11.1s 순서로 발화, 자막 "…있어요. 위아래로…" 마침표 판독, 잠시 멈춤·재개 대칭, 17.9s 완주, 틱 4개 분산 / 파워스핀 = 0→2.1s 무정지(미인증 r01 의 구 앵커 2.11s 발화 없음), 2.5·2.7s 인증 2큐 정지·재개, 8s 완주
  implication: 반려 2건 모두 코드+실데이터+시뮬까지 해소. OTA 3채널 발행(production e096f9f2 / preview 4441c980 / development f3db8421, 직전 production = 747ee98f). 남은 것 = belle 실기기 (OTA 수신 필요 — 앱 완전 종료 2회)

## Resolution

root_cause: "quick-260802-mrg 가 재생 중 자막을 결함-선행(statusLine + 목표절 제거 actionLine)으로 재조립했지만 Polly 음성 합성 텍스트는 cueLine 전문(목표절 포함)으로 남아, 08-02 이후 모든 큐에서 음성 내용과 자막 내용이 구조적으로 발산. 한 분석의 전 record 가 같은 목표문으로 발화를 시작해 '다른/같은 음성 반복' 지각을 이중 유발. 08-06 F-6(무음) 해소로 음성이 처음 들리며 표면화 — 재생 역학 수리(usc/wj3)와 직교라 2회 수리에도 불변"
fix: "(1) pipeline/app.py 합성 텍스트를 자막 조립식과 동일화 — _cue_action_line(splitGoalClause 미러) + _coach_audio_speech_text(composeCueSubtitleKo 미러) 신설, Text=cueLine → Text=_coach_audio_speech_text(rec). (2) deductionSheet.ts composeCueSubtitleKo 에 Python lockstep 주석. (3) 유저 대면 3계정(belle csKW…·시뮬 Wm5K…/fvcN…)의 coachAudio 보유 전 doc 재합성 = 엘보 12키 + 킵업/파워스핀/belle 실업로드(071df9f8…) 15키 = 27키, 로컬 boto3 Polly(Seoyeon neural)로 같은 S3 키에 덮어쓰기 — doc 무접촉(키 불변, playback-url exact 비교 그대로 성립). eval 하네스 계정(phase25e…, 66 doc)은 앱 재생처가 없어 제외 — 코드 수리가 향후 합성을 커버. (4) 구세대 고아 mp3 42키 삭제(3계정, 참조 키 전건 보존). (5) [2차 — belle 반려 반영] 결함문-행동문 마침표 경계, 자막·합성 lockstep(`35eb03d3`) + 27키 전 재재합성. (6) [2차] 큐·틱을 record 인증 순간으로 — cueTrack `centerSec`(atVideoSec) / 미인증 record 큐 자동 발화 억제 / 재생바 틱 record 별 분리(`ae398c51`). 2차는 앱 코드 변경이라 **OTA 필요** — 3채널 발행(production `e096f9f2` / preview `4441c980` / development `f3db8421`, 직전 production `747ee98f`)"
verification: "(a) 미러 정합: 앱 실함수 composeCueSubtitleKo(node 24 TS 직행) vs Python _coach_audio_speech_text — 3계정 12 record 문자 단위 일치 0 불일치. (b) 재합성본 whisper 전사 = 엘보 4건 + 일반화분 15건 전수: 전건 제 자막 문장과 일치(관절별 결함문 시작), '목표는' 시작 0건, ASR 표기 오차만. (c) S3 실측: 유저 대면 27키 전부 08-07 갱신, 구세대 고아 42키 삭제 후 재목록 = 참조 키만 잔존(11/8/8)·결측 0. (d) pytest 기준선 유지(59 failed 기존/3954 passed, coach_audio 27 passed — 신규 미러 핀 테스트 포함; 오케스트레이터 재실행으로 재확인). (e) tsc --noEmit 통과. (f) [2차] 앱 node 테스트 78 passed(centerSec·틱 신규 케이스 포함), 미러 정합 27/27, whisper 재전수(목표문 0·관절 키워드 불일치 0), 시뮬 3동작 재생 실측(킵업 무발화 완주 / 엘보 4큐 제 순간·마침표 자막 / 파워스핀 인증 2큐만) — Evidence 10:30 항목"
files_changed:
  - backend/functions/pipeline/app.py (합성 텍스트 = 자막 조립식 미러)
  - backend/tests/phase32/test_coach_audio.py (미러 핀 테스트 + 기존 단언 주석 보정)
  - app/src/lib/deductionSheet.ts (lockstep 주석만 — 동작 무변경)

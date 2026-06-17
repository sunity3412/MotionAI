# 15-DELIV-EVIDENCE — DELIV-01 TestFlight 게스트 Mode 1+3 실기기 완주

> **소유:** 15-05. Claude-side(빌드 config + static/build 회귀) 를 먼저 PASS 로 박고, 사람-전용 실기기 검증(런타임 SIGABRT 부재 + 게스트 완주 + 영상 재생)만 belle 에게 핸드오프(D-09 verify-before-handoff).
> **상태(2026-06-17):** Task 2(testflight-preview 프로필) + static/회귀 체크 PASS, **그러나 Task 3 EAS 빌드 2회 연속 FAIL(Install dependencies 단계, UNKNOWN_ERROR)** → D-09 에 따라 belle 핸드오프 보류. 아래 §빌드/submit + §빌드 실패 진단 참조.

---

## §testflight-preview 프로필 diff (Task 2)

`app/eas.json` 에 store-signed `testflight-preview` 빌드 프로필 신설 (commit `3486bbd`):

| 키 | 값 | 근거 |
|---|---|---|
| distribution | (미설정 = store) | internal 부재 — TestFlight/ASC submit 가능 (HIGH 3) |
| channel | `preview` | preview EAS Update 채널 |
| autoIncrement | `true` | buildNumber 자동 증가 (R6) |
| env (7키) | production env mirror | EXPO_PUBLIC_FIREBASE_* 6 + EXPO_PUBLIC_API_BASE_URL — production 값과 동일(node assert PASS) |
| 기존 preview | distribution:`internal` 보존 | 내부 설치 전용, TestFlight submit 미사용 |
| submit 섹션 | 미변경(production만) | Task 3 가 `--auto-submit-with-profile production` 으로 재사용 (R5) |

**node assert:** `testflight-preview OK` (distribution≠internal / channel=preview / autoIncrement=true / 7키 production mirror / preview=internal 보존 모두 PASS).

---

## §static/build 체크 표 (Task 3 — Claude-side)

| # | 체크 | 결과 | 근거 |
|---|---|---|---|
| 1 | `tsc --noEmit` clean | **PASS** | `npm run typecheck` exit 0 |
| 2 | typography.ts:15 `track=()=>0` present | **PASS** | `const track = (_size: number) => 0;` 존재 |
| 3 | negative-letterSpacing 곱셈 패턴 grep | **PASS (0)** | active(non-comment) letterSpacing 전부 `track()`(=0) 또는 `typography.caption.letterSpacing`(=0) 경유. line 4 의 `fontSize * -0.04` 는 주석(비활성) |
| 4 | EAS 빌드 성공 | **FAIL** | Build 17(`e78f4957…`) + Build 18(`bb2bfd5a…`) 둘 다 Install dependencies 단계 errored (아래 진단) |
| 5 | TestFlight submit 성공 | **N/A (빌드 선행 실패)** | submit 은 scheduled 되나 빌드 errored 로 아티팩트 없음 → submit 미완 |

> LOW 7: 런타임 SIGABRT 부재는 build 로그로 단언하지 않는다 — release 런타임 크래시 경로라 build 로그 불가시. belle 실기기 device 결과가 유일 증거(§belle 핸드오프).

---

## §빌드/submit 로그 요약 (Task 3)

| 항목 | Build 17 | Build 18 (retry) |
|---|---|---|
| Build ID | `e78f4957-3781-4f18-969c-69b80ab34d33` | `bb2bfd5a-d3a5-40b1-844c-5840c85a8767` |
| Profile / Distribution | testflight-preview / **store** | testflight-preview / **store** |
| Channel | preview | preview |
| App Version / Build number | 1.0.0 / 17 | 1.0.0 / 18 |
| Commit | `3486bbd` | `3486bbd` |
| Status | **errored** | **errored** |
| Started → Finished | 8:15:04 → 8:16:05 (~1분) | 8:19:02 → 8:20:09 (~1분) |
| 실패 단계 | Install dependencies | Install dependencies |
| errorCode | UNKNOWN_ERROR | UNKNOWN_ERROR |
| Submission | scheduled `61529cc7…` (빌드 실패로 미완) | scheduled `1839ec0b…` (빌드 실패로 미완) |
| 빌드 로그 | expo.dev/.../builds/e78f4957-… | expo.dev/.../builds/bb2bfd5a-… |

**config 검증된 부분(둘 다 통과):** 환경변수 7키(testflight-preview env) 정상 로드 / remote iOS credentials ready (Distribution Cert serial 14EBFBFF…, Provisioning Profile 373ZWPHANB active, 둘 다 2027-05-23 만료) / ASC API Key ASM44H4TB4 set up / **ASC App ID 6772934567** (production submit profile) 재사용 확인 / project fingerprint 산출 / 22.5MB 업로드 성공. → 프로필/자격/submit 경로 자체는 정상. 실패는 **remote Install dependencies 단계**에서만 발생.

---

## §빌드 실패 진단 (Claude-side, belle 결정 필요)

| 진단 항목 | 결과 |
|---|---|
| 로컬 `npm ci` (동일 committed lockfile, clean dir) | **PASS** (977 packages, exit 0, 경고만) — lockfile/peer-dep 원인 아님 |
| package.json `eas-build-*` hook | 없음 |
| 커스텀 postinstall script | 없음 |
| app.json plugins | 표준(expo-router/expo-image-picker/expo-video/expo-asset) |
| app/ working tree | clean (eas.json 변경은 3486bbd 로 커밋됨) |
| 직전 성공 빌드 | Build 14/15/16 (production, store, SDK 54) — **각 ~3시간** 정상 finished (6/11) |
| 실패 빌드 소요 | **~1분** (install 단계 즉시 errored) |
| EAS 로그 오프라인 디코드 | EAS 독점 바이너리 압축 포맷 → 오프라인 파싱 불가. errorCode=UNKNOWN_ERROR 외 상세 미노출 |

**해석:** 동일 lockfile 로컬 `npm ci` 정상 + config/자격/submit 경로 정상 + 직전 production 빌드(동일 SDK/distribution) 정상 finished. 실패는 EAS **remote worker 의 Install dependencies 단계**에서만, **2회 연속 ~1분 즉시 errored**. 2회 연속 동일 단계 실패라 단순 transient 로 단정 불가(1회 retry 후 재발). 원인은 repo 측 수정으로 해소 불가능한 범위(EAS 워커 이미지/레지스트리/계정-side install) 로 추정 — 상세 진단은 EAS 웹 빌드 로그(브라우저 렌더) 또는 EAS 지원 확인 필요.

**조치(D-09):** Claude-side 빌드 PASS 가 아니므로 **belle 실기기 핸드오프 보류**. 미검증 빌드를 belle 에게 넘기지 않는다(T-15.05-07 mitigate). belle 결정/확인 필요 항목은 아래 §belle 확인 요청.

---

## §회귀 체크리스트 (D-10) — Claude-side PASS

| # | 항목 | 결과 | 근거 |
|---|---|---|---|
| 1 | presigned URL refresh path 존재 (7일 TTL) | **PASS** | `POST /playback-url` route (template.yaml:180) + `functions/playback-url/app.py` (`_PLAYBACK_EXPIRES = 7*24*60*60`, 7일). assemble.py:631 `myVideoKey` 박제 → 만료 시 GET 재발급 |
| 2 | S3 PUT Content-Type 명시 (octet-stream 방지) | **PASS** | app `api.ts:89` `headers: { 'Content-Type': CONTENT_TYPE_BY_FORMAT[format] }` (mp4→video/mp4, mov→video/quicktime). 결과 화면 expo-video 재생 정합(P0 #6) |

회귀 체크리스트는 빌드 성공 여부와 독립(소스 경로 존재 확인)이라 PASS 유지.

---

## §belle 확인 요청 (빌드 실패 — D-09 핸드오프 보류)

> belle 가 Xcode open + 빌드/submit pre-authorized. 아래는 빌드 실패 원인 규명/해소에 belle 입력 필요 지점.

1. **EAS 웹 빌드 로그 확인(브라우저):** Install dependencies 단계 상세 원인 — 둘 중 하나:
   - Build 17: https://expo.dev/accounts/sunity3412/projects/sunity-ai-coach/builds/e78f4957-3781-4f18-969c-69b80ab34d33
   - Build 18: https://expo.dev/accounts/sunity3412/projects/sunity-ai-coach/builds/bb2bfd5a-d3a5-40b1-844c-5840c85a8767
   "Install dependencies" 단계를 펼쳐 실제 에러 라인(npm/network/registry/worker) 확인 → 공유해 주면 Claude 가 repo-side fix 가능 여부 판정.
2. **EAS 무료 플랜 큐/워커 상태:** 직전 정상 빌드가 ~3시간 큐(무료 플랜)였음. 1분 즉시 errored 는 워커 provisioning/registry 일시 장애 가능 — EAS status(status.expo.dev) 확인 후 재시도 판단.

**해소 후 재개:** 위 로그로 원인 확정 → (repo-side 면 Claude fix 후 재빌드 / EAS-infra 면 재시도) → 빌드+submit Claude-side PASS 확인 → 그 다음 §belle 핸드오프 진행.

---

## §belle 핸드오프 (실기기 게스트 완주 — **빌드 PASS 이후로 보류, awaiting**)

> ⛔ **현재 보류:** 위 빌드 실패가 해소되어 testflight-preview 빌드+submit 이 Claude-side PASS 가 된 이후에만 진행한다(D-09). 아래는 빌드 통과 후 belle 가 실기기에서 수행할 사람-전용 검증 절차(미리 기록).

belle 실기기 검증 절차:
1. TestFlight 에서 submit 된 testflight-preview 빌드를 실기기에 설치.
2. 회원가입 없이 익명 게스트로 진입(인트로 → 탭).
3. **Mode 1 완주** — 정은지 기준 모션 선택 → 본인 영상 업로드 → 실분석 결과 + 전문가 기준 점수 표시 확인.
4. **Mode 3 완주** — 본인 영상 2개 업로드 → "지난 분석보다 N점 발전" 차원 점수 델타 표시 확인.
5. **결과 영상 재생** — 결과 화면에서 영상이 octet-stream 깨짐/만료 없이 재생되는지.
6. **런타임 SIGABRT 부재** — 앱이 letterSpacing SIGABRT 로 튕기지 않는지(release 빌드 전용 크래시, build 로그 불가시). 이 device 결과를 아래 표에 기록.

### 런타임 SIGABRT / 게스트 완주 결과 (belle device 결과 — **awaiting belle**)

| 항목 | 결과 |
|---|---|
| 게스트 진입(회원가입 없이) | _awaiting belle device result_ |
| Mode 1 완주 + 전문가 점수 | _awaiting belle device result_ |
| Mode 3 완주 + N점 발전 델타 | _awaiting belle device result_ |
| 결과 영상 재생(octet-stream/만료 부재) | _awaiting belle device result_ |
| **런타임 SIGABRT 부재(letterSpacing 크래시 없음)** | **_awaiting belle device result_** ← LOW 7: device 결과가 유일 증거, build 로그 단언 금지 |

resume-signal: 완주 + 재생 + SIGABRT 부재 정상이면 "approved", 문제 있으면 단계/증상 기술(gap closure 후속).

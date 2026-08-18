"""게이트 내장 재생성 드라이버 (quick-260816-ill2 Task 3).

08-16 반려 10장을 Task 1 이 수리한 generate.py::build_prompt() (cropBox/cropNote/
orientation 배선)로 재생성하고, 오늘 19장 전수 선별에 쓴 것과 동일한 9항목 기계
게이트(gemini-3.7-flash)로 즉시 재판정한다. 자산당 재시도 상한 3, 통과 즉시 그
자산의 재시도를 중단한다 — 통과 못 한 자산은 "still_failing" 으로 정직하게 남긴다
(억지 통과·은폐 금지).

새 생성 로직은 작성하지 않는다 — gen.generate() 를 그대로 호출하므로 Task 1 이
고친 build_prompt() 를 자동으로 탄다(빌드 경로 분기 0). 판정 호출(gemini-3.7-flash)
만 이 파일에 신규 작성하며 raw urllib REST 를 쓴다(google-genai SDK 미사용 —
generate.py 자신의 generate() 관례 승계, 오늘 조사용 스크립트는 SDK 를 썼지만 그건
1회성이라 커밋 코드 관례에서 제외).

GATE_PROMPT 는 오늘 19장 전수 선별에 실제로 쓰인 원문(scratchpad ill_screen.py,
휘발 전 그대로 옮김)과 한 글자도 다르지 않다 — 오늘 결과와의 판정 연속성이 근거다.
(9개 항목 자체는 손대지 않는다 — 아래 게이트 결함 수리는 항목 뒤에 덧붙는 별도
안내문과 파싱/집계 로직만 고친다.)

호출 예산: 반려 10장 x 재시도 상한 3 x (이미지 생성 1 + 게이트 판정 1)
= 이미지 생성 <=30회 + 판정 <=30회, 합계 <=60회. 신규 pip 설치 0, S3/Firestore
쓰기 0.

게이트 결함 수리 (coordinator 2026-08-16, 최초 생성 라운드 완주 후 발견):
  실측 결과 3건이 정직한 결함이 아니라 게이트 자체의 결함이었다.
  1) 크롭맹(crop-blindness) — ①(익명/머리카락)·④(사지 개수)·⑤(머리카락)·
     ⑥(착의)·⑧(목 방향) 같은 "신체 특정 부위가 보여야 답할 수 있는" 항목이,
     cropBox/cropNote 로
     의도적으로 그 부위를 프레임 밖에 두도록 지시한 타깃(peter-pan--arm 등)
     에서마저 "안 보이니 fail" 로 판정됐다 — 요구한 적 없는 것을 벌하는
     08-16 v29 게이트 폭주 수리(quick-260816-e26)와 같은 계열의 결함.
     CROP_AWARE_ADDENDUM 이 크롭 타깃(cropBox/cropNote 유무로 **데이터**
     판별, 추측 금지)에만 덧붙어 "프레임 밖이라 원천적으로 안 보이는 항목은
     n/a" 를 명시한다. n/a 는 overall 집계에서 제외된다(_recompute_overall).
  2) 판정 응답 잘림 — 그리디 정규식(re.search 로 첫 '{' ~ 마지막 '}')이 트레일링/잘린 응답에서
     JSONDecodeError 를 냈고, 이게 "자산이 실패했다" 는 fail 로 오집계됐다
     (schema.py::extract_report_json 의 raw_decode 관례와 같은 원리 —
     coach_writer.py:298 도 파싱 실패를 fallback {} 로 흡수하지 fail 로
     쓰지 않는다). _parse_gate_json 이 json.JSONDecoder.raw_decode 로 교체
     하고, 파싱 실패는 overall="gate_error" 로 fail 과 분리해 기록한다.
  둘 다 판정 기준을 느슨하게 만든 게 아니라, 요구한 적 없는 능력을 요구하던
  계측 결함을 제거한 것이다 — 실제 결함(구도 불일치·해부 이상 등)은 그대로
  fail 로 남는다.

재판정 모드(--rejudge): 이미 생성된 gen/*__try90*.jpg 를 재사용해 고친
게이트로만 다시 판정한다 — Gemini 이미지 생성 호출 0, 판정 호출만 발생.
크롭 신호가 없는 자산(예: kip-up 계열 — 그립 문제, 배선 축과 무관)은 고친
게이트와 결과가 동일할 수밖에 없어 재판정 대상에서 제외한다(예산 절약,
정직한 스코프 — 데이터로 판별, 추측 아님).

실행:
    GEMINI_API_KEY 는 ds._ensure_gemini_key() 가 SSM 에서 자동 주입한다(키 값은
    절대 로그하지 않음).
    python3 regenerate_gated.py
    python3 regenerate_gated.py --asset ref-kip-up--shoulder   # 1건만 재실행
    python3 regenerate_gated.py --rejudge                       # 재생성 없이 재판정만
"""

from __future__ import annotations

import argparse
import datetime as _dt
import importlib.util
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]

# generate.py 를 모듈로 로드 — build_prompt/generate/load_targets/asset_name/
# inline_part/MODEL/ENDPOINT 재사용(새 생성 로직 0). build_prompt 를 이 파일이
# 직접 호출하지 않는다 — 반드시 gen.generate() 경유로 Task1 수리분을 탄다.
_GEN_PATH = REPO / ".planning/quick/260809-ill-missing-illustrations/generate.py"
_spec = importlib.util.spec_from_file_location("generate_recipe", _GEN_PATH)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

# discover_sweep.py 를 sys.path 로 임포트 — _ensure_gemini_key() (SSM 조회) 재사용.
sys.path.insert(0, str(REPO / ".planning/quick/260814-ehz-5"))
import discover_sweep as ds  # noqa: E402 - sys.path 삽입 후 임포트

VERDICTS_PATH = HERE / "regen_verdicts.json"

# 순서 고정 10행 — Task 2 검증에 쓴 것과 동일 리스트(반려 10장).
TARGET_KEYS: list[tuple[str, str]] = [
    ("ref-combo", "leg"),
    ("ref-elbow-twist-sister", "shoulder"),
    ("ref-kip-up", "leg"),
    ("ref-kip-up", "shoulder"),
    ("ref-pdshape", "arm"),
    ("ref-pdshape", "leg"),
    ("ref-peter-pan", "arm"),
    ("ref-peter-pan", "leg"),
    ("ref-peter-pan", "shoulder"),
    ("ref-power-spin", "leg"),
]

MAX_ATTEMPTS = 3
# gen/ 안의 기존 try1~21 이력(08-09 라운드)과 충돌하지 않는 네임스페이스.
ATTEMPT_BASE = 900

GATE_MODEL = "gemini-3.7-flash"
GATE_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GATE_MODEL}:generateContent"
)

# 오늘 19장 전수 선별에 실제로 쓰인 9항목 게이트 원문 — 한 글자도 바꾸지 않는다
# (scratchpad ill_screen.py 에서 그대로 옮김, quick-260816-ill2).
GATE_PROMPT = """이 그림은 폴스포츠 수강생에게 "이렇게 되어야 한다"는 목표 자세를 보여주는 일러스트입니다.
아래 9개 항목을 각각 pass/fail 로 판정하고, fail 이면 이유를 한 문장으로. 추측 말고 보이는 것만.

1 익명: 얼굴 이목구비가 드러나지 않는가(머리카락은 있어야 함)
2 자세 충실: 아래 의도한 자세와 방위(도립/직립)·형태가 맞는가   <- 가장 중요
3 가이드 표시(빨간 원/선)가 의도한 부위에 있는가
4 사지 개수: 팔 2·다리 1~2 로 셀 수 있는가(여분 팔다리 없음)
5 머리카락이 있는가(민머리 아님)
6 착의: 상의·하의를 입고 있는가
7 폴 1개·인물 1명인가
8 목 방향이 자연스러운가
9 사지 길이·비례가 자연스러운가

JSON 만 출력: {"items":{"1":{"v":"pass|fail","why":""},...,"9":{...}},"overall":"pass|fail","worst":"번호"}"""

# 크롭 타깃 전용 안내문 — 9개 항목 원문(위)은 무변경, 이 문단만 크롭 신호가 있는
# 타깃에 한해 뒤에 덧붙는다. "신체 특정 부위가 보여야 답할 수 있는" 항목이 의도된
# 부분 크롭 때문에 그 부위가 원천적으로 안 보일 때 fail 대신 n/a 를 허용한다
# (coordinator 2026-08-16 지적 — quick-260816-ill2 재판정 수리).
CROP_AWARE_ADDENDUM = (
    "\n\n[부분 크롭 안내] 이 타깃은 의도적으로 신체 일부만 담는 클로즈업 구도입니다"
    "(아래 '의도한 자세' 에 프레임 밖이 정상인 부위가 서술돼 있습니다). 위 9개 항목"
    " 중 판정 대상 신체 부위가 그 의도된 크롭 때문에 프레임 밖이라 원천적으로 안"
    " 보이는 항목은 fail 이 아니라 \"v\":\"n/a\" 로 표시하고 why 에 어떤 부위가"
    " 프레임 밖인지 적으세요. 반대로 보이는 범위 안에 실제 결함(여분 신체·잘못된"
    " 위치·부자연스러운 비례 등)이 있거나, 의도된 구도 자체가 지켜지지 않았다면"
    "(예: 부분만 보여야 하는데 전신이 다 보이거나 반대로 전신이 보여야 하는데"
    " 부분만 보임) 그건 n/a 가 아니라 fail 입니다. JSON 형식은 동일하되 v 값에"
    " \"n/a\" 도 허용됩니다: {\"items\":{...,\"n\":{\"v\":\"pass|fail|n/a\","
    "\"why\":\"\"}},\"overall\":\"pass|fail\",\"worst\":\"번호\"}"
)


def _is_crop_target(row: dict) -> bool:
    """generate.py::_framing_block 과 동일 신호 — 크롭 여부는 데이터(cropBox/
    cropNote)로만 판별한다, 이미지를 보고 추측하지 않는다."""
    return bool(row.get("cropBox") or row.get("cropNote"))


def _parse_gate_json(text: str) -> dict | None:
    """게이트 응답에서 JSON 객체 1개를 추출한다. 그리디 정규식(r'\\{.*\\}') 은
    트레일링/잘린 응답에서 JSONDecodeError 를 내고 그게 fail 로 오집계됐다
    (coordinator 2026-08-16 지적). json.JSONDecoder.raw_decode 로 실제 파서가
    구조 경계를 판단하게 한다 — schema.py::extract_report_json 의 raw_decode
    관례와 같은 원리(quick-260816-e26 전례, 이 파일에 재구현 아님 — 독립
    적용). 실패하면 None(호출자가 gate_error 로 분류)."""
    start = text.find("{")
    if start == -1:
        return None
    try:
        obj, _end = json.JSONDecoder().raw_decode(text, start)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _recompute_overall(parsed: dict) -> dict:
    """모델이 스스로 낸 overall 을 신뢰하지 않고 items 에서 결정론적으로
    재계산한다 — n/a 항목은 통과 판정에서 제외(판정 불가이지 결함이 아님),
    n/a 를 제외한 나머지 중 fail 이 하나라도 있으면 overall=fail
    (quick-260816-ill2, 투명한 감산 집계 — 밴드/모델 자기신고 신뢰 금지 원칙과
    동일선상)."""
    items = parsed.get("items") or {}
    votes = [it.get("v") for it in items.values() if isinstance(it, dict)]
    if any(v == "fail" for v in votes):
        parsed["overall"] = "fail"
    elif votes:
        parsed["overall"] = "pass"
    return parsed


def gate_judge(image_path: Path, row: dict) -> dict:
    """9항목 게이트 실호출 — 어떤 예외도 이 함수 밖으로 내보내지 않는다(배치
    전체를 죽이지 않기 위함). generate() 의 sys.exit 와 달리 이 함수는 절대
    sys.exit 를 호출하지 않는다.

    판정 실패(호출/파싱 오류)는 overall="gate_error" 로 반환한다 — "fail"
    과 절대 혼동하지 않는다(자산 결함과 계측 결함을 섞으면 안 된다,
    coordinator 2026-08-16 지적)."""
    key = __import__("os").environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        return {"overall": "gate_error", "worst": "?",
                "error": "GEMINI_API_KEY 미설정"}
    intent = (
        f"의도한 자세: {row['promptPose'][:400]}\n"
        f"의도한 방위: {row.get('orientation') or '(미기재)'}\n"
        f"가이드 대상: {row.get('guideTarget') or '(미기재)'}"
    )
    text_prompt = GATE_PROMPT + "\n\n" + intent
    if _is_crop_target(row):
        text_prompt += CROP_AWARE_ADDENDUM
    body = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": text_prompt},
                    gen.inline_part(image_path),
                ],
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            # 응답 잘림(coordinator 2026-08-16 지적, JSONDecodeError 의 원인)
            # 재발 방지 — n/a 안내문 추가로 응답이 더 길어질 수 있어 여유 확보.
            "maxOutputTokens": 4096,
        },
    }
    req = urllib.request.Request(
        f"{GATE_ENDPOINT}?key={key}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        text = ""
        for cand in payload.get("candidates", []):
            for part in cand.get("content", {}).get("parts", []):
                if part.get("text"):
                    text += part["text"]
        parsed = _parse_gate_json(text)
        if parsed is None:
            return {"overall": "gate_error", "worst": "?",
                    "error": f"JSON 파싱 실패(응답 잘림 가능): {text[:300]!r}"}
        return _recompute_overall(parsed)
    except Exception as e:  # noqa: BLE001 - 배치 계속 위해 전부 흡수
        return {"overall": "gate_error", "worst": "?",
                "error": f"{type(e).__name__}: {e}"}


def _load_verdicts() -> dict:
    if VERDICTS_PATH.exists():
        return json.loads(VERDICTS_PATH.read_text(encoding="utf-8"))
    return {
        "meta": {
            "generatedAt": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "maxAttempts": MAX_ATTEMPTS,
            "attemptBase": ATTEMPT_BASE,
            "genModel": gen.MODEL,
            "gateModel": GATE_MODEL,
        },
        "assets": {},
    }


def _save_verdicts(verdicts: dict) -> None:
    verdicts["meta"]["generatedAt"] = _dt.datetime.now(_dt.timezone.utc).isoformat()
    VERDICTS_PATH.write_text(
        json.dumps(verdicts, ensure_ascii=False, indent=1), encoding="utf-8")


def run_asset(key: tuple[str, str], row: dict, verdicts: dict) -> None:
    motion_id, part = key
    asset_key = f"{motion_id}--{part}"
    attempts: list[dict] = []
    final_status = "still_failing"
    chosen_file: str | None = None
    for n in range(1, MAX_ATTEMPTS + 1):
        attempt_num = ATTEMPT_BASE + n
        try:
            outpath = gen.generate(row, attempt_num, None)
        except (SystemExit, Exception) as e:  # noqa: BLE001 - 배치 계속
            attempts.append({
                "attempt": attempt_num, "status": "generate_error",
                "error": str(e),
            })
            print(f"[{asset_key}] try{attempt_num} -> generate_error: {e}",
                  flush=True)
            continue
        gate_result = gate_judge(outpath, row)
        attempts.append({
            "attempt": attempt_num,
            "file": str(outpath.relative_to(REPO)),
            "gate": gate_result,
        })
        print(f"[{asset_key}] try{attempt_num} -> "
              f"{gate_result.get('overall', '?')}", flush=True)
        if gate_result.get("overall") == "pass":
            final_status = "pass"
            chosen_file = str(outpath.relative_to(REPO))
            break
    verdicts["assets"][asset_key] = {
        "finalStatus": final_status,
        "chosenFile": chosen_file,
        "attempts": attempts,
    }
    _save_verdicts(verdicts)


def rejudge_asset(key: tuple[str, str], row: dict, verdicts: dict) -> None:
    """재생성 없이 기존 gen/*__try90*.jpg 를 고친 게이트로만 재판정한다 —
    최초 시도 순서(try901→902→903)대로 훑어 pass 가 나오면 즉시 멈춘다
    (Gemini 이미지 생성 호출 0, 판정 호출만). 각 재판정 attempt 는 수리 전
    게이트 응답을 gatePreFix 에 보존해 감사 가능하게 남긴다(wiring-claims
    -need-log-evidence — 덮어써서 지우지 않는다)."""
    motion_id, part = key
    asset_key = f"{motion_id}--{part}"
    existing = verdicts["assets"].get(asset_key)
    if not existing:
        print(f"[{asset_key}] REJUDGE 스킵 — 기존 verdicts 없음", flush=True)
        return
    old_attempts = existing.get("attempts") or []
    new_attempts: list[dict] = []
    final_status = "still_failing"
    chosen_file: str | None = None
    for old in old_attempts:
        file_rel = old.get("file")
        if not file_rel:
            new_attempts.append(old)  # generate_error 였던 시도는 그대로 보존
            continue
        image_path = REPO / file_rel
        gate_result = gate_judge(image_path, row)
        rec = dict(old)
        rec["gatePreFix"] = old.get("gate")
        rec["gate"] = gate_result
        rec["gateFixNote"] = ("quick-260816-ill2 coordinator 2026-08-16 재판정 "
                               "— 크롭맹 n/a + 응답잘림 파싱 수리 적용")
        new_attempts.append(rec)
        old_overall = (old.get("gate") or {}).get("overall", "?")
        print(f"[{asset_key}] REJUDGE try{old['attempt']} -> "
              f"{gate_result.get('overall', '?')} (수리전: {old_overall})",
              flush=True)
        if gate_result.get("overall") == "pass":
            final_status = "pass"
            chosen_file = file_rel
            break
    verdicts["assets"][asset_key] = {
        "finalStatus": final_status,
        "chosenFile": chosen_file,
        "attempts": new_attempts,
        "rejudged": True,
    }
    _save_verdicts(verdicts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset", default=None,
                     help="'{motionId}--{part}' 형식 1건만 재실행")
    ap.add_argument("--rejudge", action="store_true",
                     help="재생성 없이 기존 이미지를 고친 게이트로만 재판정 "
                          "(still_failing + 크롭 신호 있는 자산만 대상)")
    args = ap.parse_args()

    ds._ensure_gemini_key()

    rows_by_key = {(r["motionId"], r["part"]): r for r in gen.load_targets()}

    if args.rejudge:
        verdicts = _load_verdicts()
        todo: list[tuple[str, str]] = []
        for asset_key, rec in verdicts["assets"].items():
            if rec.get("finalStatus") == "pass":
                continue  # 완화 방향 수리 — 이미 pass 면 뒤집힐 수 없어 생략
            motion_id, part = asset_key.split("--", 1)
            row = rows_by_key.get((motion_id, part))
            if row is None or not _is_crop_target(row):
                continue  # 크롭 신호 없음 — 고친 게이트도 동일 결과, 생략
            todo.append((motion_id, part))
        print(f"REJUDGE 대상 {len(todo)}건: "
              f"{[f'{a}--{b}' for a, b in todo]}", flush=True)
        for key in todo:
            rejudge_asset(key, rows_by_key[key], verdicts)
        n_pass = sum(1 for a in verdicts["assets"].values()
                     if a["finalStatus"] == "pass")
        n_fail = sum(1 for a in verdicts["assets"].values()
                     if a["finalStatus"] == "still_failing")
        print(f"REJUDGE DONE pass={n_pass} still_failing={n_fail}")
        return

    keys = TARGET_KEYS
    if args.asset:
        found = next((k for k in TARGET_KEYS if f"{k[0]}--{k[1]}" == args.asset),
                      None)
        if found is None:
            sys.exit(f"미등록 asset: {args.asset} (가능: "
                      f"{', '.join(f'{a}--{b}' for a, b in TARGET_KEYS)})")
        keys = [found]

    verdicts = _load_verdicts()
    for key in keys:
        row = rows_by_key.get(key)
        if row is None:
            sys.exit(f"targets.json 에 행 없음: {key}")
        run_asset(key, row, verdicts)

    n_pass = sum(1 for a in verdicts["assets"].values()
                 if a["finalStatus"] == "pass")
    n_fail = sum(1 for a in verdicts["assets"].values()
                 if a["finalStatus"] == "still_failing")
    n_attempts = sum(len(a["attempts"]) for a in verdicts["assets"].values())
    print(f"DONE pass={n_pass} still_failing={n_fail} "
          f"totalAttempts={n_attempts}")


if __name__ == "__main__":
    main()

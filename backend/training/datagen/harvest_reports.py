"""운영 분석 리포트 → 학습 트랙(report) 수확기 — belle 지시 2026-08-15.

belle 원문: "내가 요청한대로 앞으로 분석할 때마다 학습할 여지가 있다면 하는거고" /
"안들어가는게 문제면 해결해야되는거 아녀?"

실측(2026-08-15): Firestore 에 완료(done) 분석이 **962건**(116 계정) 쌓여 있고 그중
**635건이 감점 기록(deductionBreakdown)** 을 갖는다. 그런데 학습셋의 분석 과제 행은
Gemini 증류 81행뿐이었다 — 운영 분석은 **한 건도** 분석 과제 학습에 들어가지 않았다.
게이트가 요구하는 `faults`(결함 짚기)를 어느 학습 판도 못 낸 이유가 여기 있다.

★기존 `shadow` 트랙에 부으면 안 된다: 그 트랙은 `"faults": []` 를 **하드코딩**한다
  (build_jsonl._build_shadow_samples). 거기에 운영 분석을 넣으면 "결함 없음"을
  가르치게 되고, 그것이 정확히 지금 모델이 하는 짓이다. 그래서 새 트랙이다.

동의 축은 새로 만들지 않는다 — harvest_eye 의 `owner_scope`/`consent_disposition`
을 그대로 재사용한다(재발명 금지). 앱 미오픈 내부 계정은 admit, 명단 밖 계정은
`learningOptIn` 실측이 True 일 때만 admit 이다. 즉 **베타 오픈 후 동의한 사용자의
분석은 자동으로 학습에 들어오고, 동의 안 한 계정은 자동으로 막힌다.**

순수성: 변환(criterion→fault)·판정은 전부 순수 함수다. Firestore/S3 접촉은 CLI
계층에만 있다 — 단위 테스트가 네트워크 없이 전 분기를 돈다.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[3]
LEDGER_PATH = _REPO / "backend" / "training" / "data" / "report_manifest.json"

# ── criterion → 부위/범위/분류 (새 분류 발명 0 — vision_veto.FAULT_CATEGORIES 재사용) ──
# criterion 은 두 형태다:
#   · 절대 축      — leg_extension / arm_extension / split_angle / line / body_relative_reach
#   · 기준 상대 축 — angle_vs_reference__{joint}
_REF_PREFIX = "angle_vs_reference__"

# 관절 → part_scope. 명단 밖은 None 으로 두고 행을 버린다(추측 금지).
_JOINT_SCOPE = {
    "left_shoulder": "upper_body", "right_shoulder": "upper_body",
    "left_elbow": "upper_body", "right_elbow": "upper_body",
    "left_wrist": "upper_body", "right_wrist": "upper_body",
    "left_hip": "core", "right_hip": "core",
    "left_knee": "lower_body", "right_knee": "lower_body",
    "left_ankle": "lower_body", "right_ankle": "lower_body",
}

# 절대 축 criterion → (body_part, part_scope, fault_category)
_ABSOLUTE_CRITERIA = {
    "leg_extension": ("leg", "lower_body", "limb_extension"),
    "arm_extension": ("arm", "upper_body", "limb_extension"),
    "split_angle": ("hip", "core", "split_angle"),
    "line": ("body_line", "line", "alignment"),
    "body_relative_reach": ("body_line", "line", "alignment"),
}


def criterion_parts(criterion) -> tuple[str, str, str] | None:
    """criterion → (body_part, part_scope, fault_category). 미상이면 None(행 폐기).

    ★fail-closed: 모르는 criterion 을 `other` 로 뭉뚱그리지 않는다. 라우팅 1순위
    소비 키라 잘못 분류하면 감점 엔진이 엉뚱한 데로 보낸다 — 모르면 안 넣는다.
    """
    if not isinstance(criterion, str) or not criterion:
        return None
    if criterion in _ABSOLUTE_CRITERIA:
        return _ABSOLUTE_CRITERIA[criterion]
    if criterion.startswith(_REF_PREFIX):
        joint = criterion[len(_REF_PREFIX):]
        scope = _JOINT_SCOPE.get(joint)
        if not scope:
            return None
        return joint, scope, "alignment"
    return None


def _num(value):
    """숫자만 통과 (bool 은 숫자가 아니다)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def fault_from_record(record, phrases=None) -> dict | None:
    """감점 기록 1건 → FAULT_ITEM_KEYS 결함 1건. 계약 미충족이면 None.

    각도쌍(student/reference)과 폴백(approx_deviation) 중 하나는 있어야 한다
    (build_jsonl._faults_satisfy_contract 와 같은 계약 — 통과 못 할 행을 만들지 않는다).

    · deviationSource=ipsf_absolute → baselineValue 가 정타 각도라 **각도쌍 성립**
    · deviationSource=reference_relative → baselineValue 가 0(편차 기준선)이라
      기준 각도를 모른다 → 각도쌍을 짓지 않고 편차 폴백만 쓴다. **여기서 0 을
      기준 각도라고 적으면 재지 않은 것을 쟀다고 말하는 셈이다.**

    phrases = 승인 문구집 entry (선택). 문면은 문구집만 소유한다 — 여기서 새 문장을
    짓지 않는다(D-11). root_cause_hypothesis 는 **기준 서술 원인만** 싣는다
    (quick-260815-fzi: 학생 서술 원인은 분석 1건의 읽기라 재사용 불가).
    """
    if not isinstance(record, dict):
        return None
    parts = criterion_parts(record.get("criterion"))
    if parts is None:
        return None
    body_part, part_scope, fault_category = parts

    unit = record.get("unit")
    measured = _num(record.get("measuredValue"))
    baseline = _num(record.get("baselineValue"))
    deviation = _num(record.get("deviation"))
    dev_source = record.get("deviationSource")

    student_deg = measured if unit == "deg" else None
    reference_deg = baseline if (unit == "deg" and dev_source == "ipsf_absolute") else None
    approx = abs(deviation) if deviation is not None else None

    has_pair = student_deg is not None and reference_deg is not None
    if not has_pair and approx is None:
        return None  # 계약 미충족 — 조립 단계에서 어차피 버려진다.

    rule_id = record.get("ruleId")
    basis = f"운영 파이프라인 감점 기록 (rule={rule_id}, 기준={dev_source}, 단위={unit})"

    entry = phrases if isinstance(phrases, dict) else {}
    cause = entry.get("causeLine")
    if cause and entry.get("causeSubject") != "reference":
        cause = None  # 학생 서술 원인은 재사용 금지 (belle 2026-08-15).

    return {
        "approx_angle_deviation_deg": approx,
        "body_part": body_part,
        "correct_state": None,          # 승인 문면이 없으면 짓지 않는다.
        "fault_category": fault_category,
        "fault_state": entry.get("statusLine"),
        "ipsf_note": record.get("ipsfAnchor"),
        "measurement_basis": basis,
        "part_scope": part_scope,
        "reference_angle_deg": reference_deg,
        "root_cause_hypothesis": cause,
        "source": "geometry" if record.get("source") == "geometry" else "vision_hypothesis",
        "student_angle_deg": student_deg,
    }


def faults_from_result(result, phrasebook_entries=None, reference_id=None) -> list[dict]:
    """분석 result → faults[]. 감점 기록이 없거나 전부 미상이면 빈 리스트."""
    if not isinstance(result, dict):
        return []
    breakdown = result.get("deductionBreakdown")
    records = breakdown.get("records") if isinstance(breakdown, dict) else None
    if not isinstance(records, list):
        return []
    entries = phrasebook_entries if isinstance(phrasebook_entries, dict) else {}
    out = []
    for rec in records:
        key = None
        if reference_id and isinstance(rec, dict) and rec.get("criterion"):
            key = f"{reference_id}.{rec['criterion']}"
        fault = fault_from_record(rec, entries.get(key) if key else None)
        if fault is not None:
            out.append(fault)
    return out


def coaching_from_result(result) -> str | None:
    """코칭 문장 — tips 의 detail 을 이어 붙인다(운영이 실제로 낸 문면 그대로).

    새 문장을 짓지 않는다. tips 가 없으면 None.
    """
    if not isinstance(result, dict):
        return None
    tips = result.get("tips")
    if not isinstance(tips, list) or not tips:
        return None
    parts = [t.get("detail") for t in tips if isinstance(t, dict) and t.get("detail")]
    return " ".join(parts) if parts else None


def report_from_analysis(doc, phrasebook_entries=None) -> dict | None:
    """분석 문서 → 학습 타깃 리포트. 결함 0건이면 None(빈 골격을 가르치지 않는다).

    ★이 게이트가 이 파일의 존재 이유다. 결함 없는 리포트를 학습에 넣으면
    "무엇을 넣든 빈 배열"을 가르치게 되고, 그것이 2026-08-15 게이트 FAIL 의
    관측된 증상이다(29건 전부 빈 골격).
    """
    if not isinstance(doc, dict):
        return None
    result = doc.get("result")
    faults = faults_from_result(result, phrasebook_entries, doc.get("referenceMotionId"))
    if not faults:
        return None
    return {
        "coaching": coaching_from_result(result),
        "corrected_coords": None,
        "faults": faults,
        "segments": None,
        "svg_spec": None,
        "time_anchors": None,
    }


def is_script_created_uid(uid) -> bool:
    """앱에서 나올 수 **없는** uid 인가 — 구조 판정(휴리스틱 아님).

    앱은 Firebase 익명 로그인만 쓰고(app/src/app/index.tsx), Firebase Auth uid 는
    **항상 28자 영숫자**다. 그 형태가 아닌 uid 는 Auth 를 거치지 않고 스크립트가
    Firestore 에 직접 쓴 것 — `phase25eval` `genpod2` `mock_e2e_v3_1781249495`
    같은 러너 계정이다. 실제 수강생 계정은 이 분기에 **원리적으로** 못 들어온다.

    ★sha16 명단을 116개로 늘리지 않는 이유가 이것이다: 명단은 손으로 관리되어
      낡고, 낡은 명단은 조용히 틀린다. 구조 판정은 낡지 않는다.
    ★반대로 28자 익명 uid 는 우리 기기 테스트분이라도 여기서 통과시키지 않는다 —
      실제 사용자와 형태가 같아 구분할 근거가 없다. 그쪽은 명단/동의 실측이 판단한다.
    """
    if not isinstance(uid, str) or len(uid) != 28:
        return isinstance(uid, str) and bool(uid)
    return not uid.isalnum()


def analysis_disposition(doc, owner_scope_fn, consent_lookup=None) -> tuple[str, str]:
    """(disposition, reason) — 동의 축은 harvest_eye 규율을 그대로 따른다.

    · learningOptIn is False → hold/consent_denied (내부 계정이라도 뒤집지 않는다)
    · 스크립트 생성 uid       → admit/internal_runner   (앱에서 나올 수 없는 계정)
    · 앱 미오픈 내부 계정      → admit/prelaunch_internal
    · 그 외 + optIn True      → admit/optin_verified   ← 베타 오픈 후의 정상 경로
    · 그 외                   → hold/optin_unverified
    """
    uid = doc.get("uid")
    consent = doc.get("learningOptIn")
    if consent is None and callable(consent_lookup):
        consent = consent_lookup(uid)
    if consent is False:
        return "hold", "consent_denied"
    if is_script_created_uid(uid):
        return "admit", "internal_runner"
    if owner_scope_fn(uid) == "prelaunch_internal":
        return "admit", "prelaunch_internal"
    if consent is True:
        return "admit", "optin_verified"
    return "hold", "optin_unverified"


# ── 원장 I/O (append-only — eye_manifest 패턴) ────────────────────────────────
def load_ledger(path=LEDGER_PATH) -> dict:
    p = Path(path)
    if not p.exists():
        return {"_meta": {"schema": "report-v1"}, "rows": []}
    return json.loads(p.read_text(encoding="utf-8"))


def save_ledger(ledger, path=LEDGER_PATH) -> None:
    Path(path).write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


MEDIA_PREFIX = "training/phase22/report/"


def media_sha16(media_key) -> str | None:
    """운영 S3 키 → 학습용 식별자(16자). uid 는 해시에 녹아 원문이 남지 않는다(P-4)."""
    import hashlib

    if not isinstance(media_key, str) or not media_key:
        return None
    return hashlib.sha256(media_key.encode("utf-8")).hexdigest()[:16]


def training_media_key(sha16) -> str | None:
    """학습 경로 키. ★운영 `uploads/` 를 학습이 직접 참조하지 않는다 — eye 선례.

    운영 객체는 수명주기 정책의 대상이라 언제든 사라질 수 있고, 사라지면 학습셋이
    조용히 깨진다. 반출본을 학습 경로에 두고 그것만 참조한다.
    """
    return f"{MEDIA_PREFIX}{sha16}.mp4" if sha16 else None


def training_rows(ledger) -> list[dict]:
    """원장 → 학습에 실제로 쓸 행. **영상 1개당 1행**으로 접는다.

    ★실측 2026-08-15: admit 322행의 고유 영상은 **39개**였다. 평가 러너가 같은
    픽스처 영상을 최대 61회 재분석했기 때문이다. 접지 않고 넣으면 그 39개 클립에
    과적합하고, 동작 균등 게이트도 중복이 부풀린 수치로 통과한다(가짜 균등).

    같은 영상의 여러 분석 중 **가장 최근 것**을 고른다 — 파이프라인이 계속 고쳐져
    왔으므로 최신 분석이 현재 채점 규율에 가장 가깝다. 결함이 많은 것을 고르면
    과검출 쪽으로 체계적 편향이 생기므로 쓰지 않는다.
    원장은 전 행을 그대로 보관한다(수확 이력은 지우지 않는다) — 접기는 소비 시점에만.
    """
    best: dict[str, dict] = {}
    for row in ledger.get("rows", []):
        if row.get("disposition") != "admit" or not row.get("media_uploaded"):
            continue
        sha = row.get("media_sha16")
        if not sha:
            continue
        cur = best.get(sha)
        if cur is None or _recency_key(row) > _recency_key(cur):
            best[sha] = row
    return [best[k] for k in sorted(best)]


def _recency_key(row) -> tuple:
    """정렬 키 — createdAt 우선, 없으면 analysis_id (결정론 보장)."""
    return (str(row.get("created_at") or ""), str(row.get("analysis_id") or ""))


def row_key(row) -> tuple:
    """원장 유일키 = (계정, 분석). ★analysis_id 단독은 유일하지 않다.

    실측 2026-08-15: 331행을 넣었더니 321행만 남았다 — 문서 경로가
    `users/{uid}/analyses/{analysisId}` 라 **다른 계정이 같은 analysisId 를 가질 수
    있다**(러너 스크립트가 같은 id 를 재사용). uid 를 키에서 빼면 뒤에 온 계정의
    분석이 조용히 사라진다.
    """
    return (row.get("uid_sha16"), row.get("analysis_id"))


def merge_rows(ledger, new_rows) -> tuple[dict, int, int]:
    """(계정, 분석) 기준 append-only 병합 → (ledger, 신규, 기존skip)."""
    existing = {row_key(r) for r in ledger.get("rows", [])}
    added = skipped = 0
    for row in new_rows:
        key = row_key(row)
        if key in existing:
            skipped += 1
            continue
        ledger.setdefault("rows", []).append(row)
        existing.add(key)
        added += 1
    return ledger, added, skipped


def _load_phrasebook_entries():
    p = _REPO / "backend" / "data" / "phrasebook.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("entries") or {}
    except Exception:  # noqa: BLE001 - 문구집 부재는 문면 없이 진행(결함은 그대로 실린다)
        return {}


def scan(limit=None, write=False, ledger_path=LEDGER_PATH):
    """Firestore 전수 스캔 → 리포트 변환 + 원장 반영. I/O 계층(테스트 대상 아님)."""
    import hashlib

    import firebase_admin
    from firebase_admin import credentials, firestore

    try:  # 패키지 경로 우선, 스크립트 직접 실행도 지원.
        from datagen.harvest_eye import owner_scope  # 동의 규율 단일 출처 재사용.
    except ImportError:
        from harvest_eye import owner_scope

    if not firebase_admin._apps:  # noqa: SLF001
        firebase_admin.initialize_app(credentials.Certificate(str(_REPO / "firebase-sa.json")))
    db = firestore.client()
    entries = _load_phrasebook_entries()

    stats = {"scanned": 0, "done": 0, "with_faults": 0, "admit": 0, "hold": 0, "no_media": 0}
    reasons = {}
    rows = []
    q = db.collection_group("analyses")
    for d in (q.limit(limit).stream() if limit else q.stream()):
        stats["scanned"] += 1
        o = d.to_dict() or {}
        if o.get("status") != "done":
            continue
        stats["done"] += 1
        uid = d.reference.parent.parent.id if d.reference.parent.parent else None
        o = {**o, "uid": uid}
        report = report_from_analysis(o, entries)
        if report is None:
            continue
        stats["with_faults"] += 1
        disposition, reason = analysis_disposition(o, owner_scope)
        reasons[reason] = reasons.get(reason, 0) + 1
        stats[disposition] += 1
        media_key = ((o.get("result") or {}).get("myVideoKey")) if isinstance(o.get("result"), dict) else None
        if not media_key:
            stats["no_media"] += 1
        sha16 = media_sha16(media_key)
        rows.append({
            "analysis_id": d.id,
            "created_at": str(o.get("createdAt") or ""),
            "owner_scope": owner_scope(uid),
            "uid_sha16": hashlib.sha256((uid or "").encode("utf-8")).hexdigest()[:16],
            "mode": o.get("mode"),
            "motion": o.get("referenceMotionId"),
            "reference_id": o.get("referenceMotionId"),
            "source_media_key": media_key,
            "media_sha16": sha16,
            "media_key": training_media_key(sha16),
            "media_uploaded": False,   # 반출 전 — 조립기는 이 값이 True 인 행만 쓴다.
            "disposition": disposition,
            "disposition_reason": reason,
            "fault_count": len(report["faults"]),
            "report": report,
        })

    print("스캔 %d | done %d | 결함 보유 %d | admit %d / hold %d | media 없음 %d"
          % (stats["scanned"], stats["done"], stats["with_faults"],
             stats["admit"], stats["hold"], stats["no_media"]))
    print("판정 사유:", reasons)
    if rows:
        counts = {}
        for r in rows:
            counts[r["fault_count"]] = counts.get(r["fault_count"], 0) + 1
        print("결함 수 분포:", dict(sorted(counts.items())))
    if write:
        ledger = load_ledger(ledger_path)
        ledger, added, skipped = merge_rows(ledger, rows)
        ledger["_meta"]["rows_after"] = len(ledger["rows"])
        ledger["_meta"]["admit_after"] = sum(1 for r in ledger["rows"] if r.get("disposition") == "admit")
        save_ledger(ledger, ledger_path)
        print("원장 기록: 신규 %d / 기존 skip %d / rows_after %d / admit_after %d"
              % (added, skipped, ledger["_meta"]["rows_after"], ledger["_meta"]["admit_after"]))
    else:
        print("(--run 없이 실행 — 원장 미기록)")
    return stats


def upload_media(write=False, ledger_path=LEDGER_PATH, bucket="sunity-motion-pilot-videos"):
    """admit 행의 운영 영상을 학습 경로로 반출 (S3 서버사이드 복사).

    ★조립기의 fail-closed 를 여는 유일한 경로다 — 반출 안 된 행은 학습에 안 들어간다
    (harvest_eye --upload-media 선례). 복사이므로 운영 객체는 무접촉이다.
    """
    import boto3
    from botocore.exceptions import ClientError

    s3 = boto3.client("s3")
    ledger = load_ledger(ledger_path)
    todo = [
        r for r in ledger.get("rows", [])
        if r.get("disposition") == "admit" and not r.get("media_uploaded")
        and r.get("source_media_key") and r.get("media_key")
    ]
    print("반출 대상 %d행 (admit 중 미반출)" % len(todo))
    done = skipped = failed = 0
    for r in todo:
        dst = r["media_key"]
        try:
            s3.head_object(Bucket=bucket, Key=dst)
            r["media_uploaded"] = True
            skipped += 1
            continue
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") not in ("404", "NoSuchKey", "403"):
                raise
        if not write:
            continue
        try:
            s3.copy_object(
                Bucket=bucket, Key=dst,
                CopySource={"Bucket": bucket, "Key": r["source_media_key"]},
            )
            r["media_uploaded"] = True
            done += 1
        except ClientError as exc:  # noqa: PERF203 - 행 단위 실패를 전체 중단으로 키우지 않는다
            code = exc.response.get("Error", {}).get("Code")
            r["media_upload_error"] = code
            failed += 1
    if write:
        ledger["_meta"]["media_uploaded"] = sum(
            1 for r in ledger.get("rows", []) if r.get("media_uploaded"))
        save_ledger(ledger, ledger_path)
    print("반출 완료 %d / 이미 존재 %d / 실패 %d%s"
          % (done, skipped, failed, "" if write else "  (--run 없이 실행 — 복사 안 함)"))
    return {"uploaded": done, "skipped": skipped, "failed": failed}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="운영 분석 리포트 → 학습 트랙 수확")
    ap.add_argument("--run", action="store_true", help="원장/S3 에 기록 (없으면 조사만)")
    ap.add_argument("--limit", type=int, default=None, help="스캔 문서 상한(조사용)")
    ap.add_argument("--upload-media", action="store_true",
                    help="admit 행 영상을 학습 경로로 반출 (조립 fail-closed 해제)")
    args = ap.parse_args(argv)
    if args.upload_media:
        upload_media(write=args.run)
    else:
        scan(limit=args.limit, write=args.run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

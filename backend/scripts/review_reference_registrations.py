"""공급자 등록 검수 운영 CLI (quick-261001-thx, belle 2026-10-01 "1단계 오케이" — 1단계-가).

기계 판정은 분석 불가(사람 없음 · 포즈 재료 없음 · 파일 문제)만 막고, 통과한 등록은
`registrationStatus: 'review'` + `isActive: false` 로 수강생 picker 에 안 보인 채 기다린다.
운영자(Claude)가 이 CLI 로 사진을 뽑아 belle 에게 보여 주고, belle OK 뒤에 승인한다.

서브커맨드 다섯 개:
  list                                        검수 대기(review) 표 — refId 앞 8자 · 강사 코드 · 동작 이름 ·
                                              선수 · 레벨 · 자기 재현성(점수, 없으면 상태) · 진단 요약
                                              (여러 명 비율 · 저신뢰 관절 수와 이름 · 서 있는 시작).
                                              읽기 = 2N(공개 N + 비공개 N) — Spark 무료 플랜 5만/일 캡.
  show <refId> [--out DIR]                    썸네일 · 영상(v1) 을 내려받고 길이의 10% · 50% · 90% 순간
                                              프레임 3장을 jpg 로 뽑아 경로 5줄을 출력. 기본 폴더 =
                                              /Users/Shared/sunity-motion-review/<refId>/ (권한 700, 홈
                                              디렉터리 밖 — 홈은 git 저장소라 정은지 영상(초상)이 새면 안 된다).
  approve <refId> [--by] [--dry-run]          review → active + isActive true (수강생 picker 에 뜬다).
  reject <refId> --reason "<한국어>" [--by] [--dry-run]
                                              review → failed + 사유(공급자 실패 패널에 그대로 보인다).
                                              사유는 앞뒤 공백과 끝 마침표를 떼고 200자 이하.
  deactivate <refId> [--reason] [--by] [--dry-run]
                                              승인된(active) 기준 내리기 — isActive false(수강생 picker 에서 빠진다).
                                              상태는 active 그대로, 누가/언제/사유는 비공개 doc `deactivation` 에만.
                                              되살리기 명령은 없다(belle 10-01 "아주 심플하게" — 다시 올리면 새 refId).

반복 실행 무해 — 두 번째 approve/reject/deactivate 는 'already_approved' / 'already_rejected' /
'already_inactive' 를 출력하고 쓰기 0.
legacy `ref-*`(손 등록 11개)는 입력 단계에서 거부(종료 2) — writer 도 같은 가드를 첫 줄에 둔다.
--dry-run 은 현재 상태와 바뀔 상태만 출력하고 writer 를 부르지 않는다(읽기 1).
--by 기본값 = "ops:" + 로컬 계정 이름. 누가/언제는 비공개 doc `review` 에만 남는다.

자격: Firebase Admin SA = 리포 루트 SA 파일을 FIREBASE_SA_PATH 로(supplier_invite.py 관례).
S3 = 셸의 AWS_PROFILE(sunity-motion). 둘 다 서브커맨드 실행 안에서만 — `--help` 는 자격 없이 돈다.
로컬 ffmpeg = imageio_ffmpeg(backend/.venv) — reference_media.extract_thumbnail 가 찾는다.

종료 코드: 0 성공 · 1 Firestore 쪽 거부(ValueError — 문구를 stderr 에) · 2 입력 규칙 위반(Firestore 호출 전).
"""

from __future__ import annotations

import argparse
import getpass
import os
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_LAYER = _REPO / "backend" / "shared" / "python"
if str(_LAYER) not in sys.path:
    sys.path.insert(0, str(_LAYER))

from sunity_shared import firestore_admin, models  # noqa: E402  (클라이언트는 첫 호출 때 lazy)
from sunity_shared.analysis import reference_media  # noqa: E402  (ffmpeg 는 호출 때만)
from sunity_shared.analysis.registration_checks import joint_labels_ko  # noqa: E402

_SA_JSON = _REPO / "sunity-ai-coach-firebase-adminsdk-fbsvc-7055d7d3d1.json"
_REGION = "ap-northeast-2"
_DEFAULT_BUCKET = "sunity-motion-pilot-videos"
REVIEW_ROOT = Path("/Users/Shared/sunity-motion-review")
# 공급자 등록 refId = 서버 uuid4 hex(reference-upload-url). legacy `ref-*` 는 따로 먼저 거른다.
_REF_ID_RE = re.compile(r"^[0-9a-f]{32}$")
FRAME_FRACTIONS = (0.10, 0.50, 0.90)
FRAME_WIDTH = 720  # 검수 사진 — 썸네일(360)보다 크게
_NONE = "없음"


def _ensure_credentials() -> None:
    """SA 파일을 FIREBASE_SA_PATH 로(이미 지정됐으면 그대로)."""
    if not (os.environ.get("FIREBASE_SA_JSON") or os.environ.get("FIREBASE_SA_PATH")) and _SA_JSON.exists():
        os.environ["FIREBASE_SA_PATH"] = str(_SA_JSON)


def _s3_client():
    import boto3

    return boto3.client("s3", region_name=_REGION)


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)


def _check_ref_id(ref_id: str) -> str | None:
    """입력 규칙 — 통과면 None, 위반이면 stderr 문구(호출측이 종료 2)."""
    if ref_id.startswith("ref-"):
        return f"legacy 기준(ref-*)은 검수 대상이 아니에요: {ref_id}"
    if not _REF_ID_RE.match(ref_id):
        return f"refId 는 32자리 소문자 hex 예요(list 끝의 전체 id): {ref_id}"
    return None


def _default_by() -> str:
    return f"ops:{getpass.getuser()}"


def _clean_reason(raw: str) -> str:
    """앞뒤 공백과 끝 마침표를 뗀다 — 문구 '사유: {reason}. ' 에 마침표가 두 번 찍히지 않게."""
    return raw.strip().rstrip(".").rstrip()


def _fmt_self(doc: dict) -> str:
    score = doc.get("selfScore")
    if isinstance(score, (int, float)) and not isinstance(score, bool):
        return f"{score:.1f}"
    return str(doc.get("selfCheckStatus") or "-")


def _fmt_diag(diag: dict | None) -> str:
    if not isinstance(diag, dict) or not diag:
        return "진단 없음"
    ratio = diag.get("personRatio")
    ratio_s = f"{float(ratio):.2f}" if isinstance(ratio, (int, float)) else "-"
    low = [j for j in (diag.get("lowConfidenceJoints") or []) if isinstance(j, str)]
    low_s = f"{len(low)}({','.join(joint_labels_ko(low))})" if low else "0"
    return f"여러명={ratio_s} 저신뢰={low_s} 서있는시작={diag.get('standingStart') or '-'}"


# ─────────────────────── 서브커맨드 ───────────────────────


def _cmd_list(_args) -> int:
    _ensure_credentials()
    rows = firestore_admin.list_reference_registrations_by_status(models.REGISTRATION_STATUS_REVIEW)
    if not rows:
        print("검수 대기 0건")
        return 0
    rows = sorted(rows, key=lambda d: d.get("createdAt") or 0, reverse=True)
    print(f"검수 대기 {len(rows)}건")
    print("ref8      code      name / athlete / level            self    진단")
    full_ids: list[tuple[str, str]] = []
    for doc in rows:
        ref_id = str(doc.get("motionId") or "")
        priv = firestore_admin.get_reference_registration_private(ref_id) or {}
        who = f"{doc.get('name') or '-'} / {doc.get('athleteName') or '-'} / {doc.get('level') or '-'}"
        print(
            f"{ref_id[:8]:<9} {str(doc.get('supplierCode') or '-'):<9} {who:<33} "
            f"{_fmt_self(doc):<7} {_fmt_diag(priv.get('registrationDiagnostics'))}"
        )
        full_ids.append((ref_id[:8], ref_id))
    print()
    print("전체 refId (show / approve / reject 에 이 값을 쓴다):")
    for short, full in full_ids:
        print(f"  {short} = {full}")
    return 0


def _prepare_out_dir(path: Path) -> Path:
    """폴더를 만들고 700 으로. 기본 루트(/Users/Shared/sunity-motion-review)도 700."""
    if path.parent == REVIEW_ROOT:
        REVIEW_ROOT.mkdir(parents=True, exist_ok=True)
        os.chmod(REVIEW_ROOT, 0o700)
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    return path


def _cmd_show(args) -> int:
    problem = _check_ref_id(args.ref_id)
    if problem:
        _err(problem)
        return 2
    _ensure_credentials()
    doc = firestore_admin.get_reference_registration(args.ref_id)
    if doc is None:
        _err(f"reference/{args.ref_id} 가 없어요.")
        return 1
    priv = firestore_admin.get_reference_registration_private(args.ref_id) or {}
    out = _prepare_out_dir(Path(args.out) if args.out else REVIEW_ROOT / args.ref_id)
    s3 = _s3_client()
    bucket = args.bucket

    print(
        f"ref={args.ref_id} status={doc.get('registrationStatus')} name={doc.get('name')} "
        f"athlete={doc.get('athleteName')} level={doc.get('level')} self={_fmt_self(doc)} "
        f"{_fmt_diag(priv.get('registrationDiagnostics'))}"
    )

    thumb_line = _NONE
    thumb_key = doc.get("thumbnailS3Key")
    if isinstance(thumb_key, str) and thumb_key:
        dst = out / "thumb.jpg"
        try:
            s3.download_file(bucket, thumb_key, str(dst))
            thumb_line = str(dst)
        except Exception as e:  # noqa: BLE001 - 썸네일 실패는 나머지를 막지 않는다
            thumb_line = f"{_NONE} (내려받기 실패: {type(e).__name__})"
    print(f"thumb   {thumb_line}")

    video_key = doc.get("videoS3Key")
    video_path: Path | None = None
    if isinstance(video_key, str) and video_key:
        video_path = out / Path(video_key).name
        try:
            s3.download_file(bucket, video_key, str(video_path))
        except Exception as e:  # noqa: BLE001
            print(f"video   {_NONE} (내려받기 실패: {type(e).__name__})")
            video_path = None
        else:
            print(f"video   {video_path}")
    else:
        print(f"video   {_NONE}")

    frames = doc.get("anglesFrames")
    fps = doc.get("anglesRealFps")
    duration = (
        float(frames) / float(fps)
        if isinstance(frames, (int, float)) and isinstance(fps, (int, float)) and fps > 0 and frames > 0
        else None
    )
    for frac in FRAME_FRACTIONS:
        label = f"frame{int(round(frac * 100)):02d}"
        if video_path is None or duration is None:
            print(f"{label} {_NONE}")
            continue
        t = max(0.0, min(duration * frac, duration - 0.1))
        dst = out / f"{label}.jpg"
        try:
            reference_media.extract_thumbnail(str(video_path), t, str(dst), width=FRAME_WIDTH)
            print(f"{label} {dst}  (t={t:.2f}s)")
        except Exception as e:  # noqa: BLE001
            print(f"{label} {_NONE} (추출 실패: {type(e).__name__})")
    return 0


def _dry_run(ref_id: str, action: str, target: str) -> int:
    doc = firestore_admin.get_reference_registration(ref_id)
    if doc is None:
        _err(f"reference/{ref_id} 가 없어요.")
        return 1
    status = doc.get("registrationStatus")
    if status == models.REGISTRATION_STATUS_REVIEW:
        print(f"dry-run {action} ref={ref_id} 현재={status} → {target} (쓰기 없음)")
    else:
        print(
            f"dry-run {action} ref={ref_id} 현재={status} — review 가 아니라 실제 실행은 "
            "already_* 이거나 거부(종료 1)예요 (쓰기 없음)"
        )
    return 0


def _cmd_approve(args) -> int:
    problem = _check_ref_id(args.ref_id)
    if problem:
        _err(problem)
        return 2
    by = (args.by or _default_by()).strip()
    if not by:
        _err("--by 가 비었어요.")
        return 2
    _ensure_credentials()
    if args.dry_run:
        return _dry_run(args.ref_id, "approve", models.REGISTRATION_STATUS_ACTIVE)
    try:
        result = firestore_admin.approve_reference_registration(args.ref_id, by=by)
    except ValueError as e:
        _err(str(e))
        return 1
    print(f"{result} ref={args.ref_id} by={by}")
    return 0


def _cmd_reject(args) -> int:
    problem = _check_ref_id(args.ref_id)
    if problem:
        _err(problem)
        return 2
    reason = _clean_reason(args.reason)
    if not reason:
        _err("--reason 이 비었어요. 공급자 화면에 그대로 보이는 한국어 사유를 적어주세요.")
        return 2
    if len(reason) > firestore_admin.REJECT_REASON_MAX_LEN:
        _err(f"--reason 은 {firestore_admin.REJECT_REASON_MAX_LEN}자 이하로 적어주세요.")
        return 2
    by = (args.by or _default_by()).strip()
    if not by:
        _err("--by 가 비었어요.")
        return 2
    _ensure_credentials()
    if args.dry_run:
        return _dry_run(args.ref_id, "reject", f"{models.REGISTRATION_STATUS_FAILED}(사유: {reason})")
    try:
        result = firestore_admin.reject_reference_registration(args.ref_id, reason=reason, by=by)
    except ValueError as e:
        _err(str(e))
        return 1
    print(f"{result} ref={args.ref_id} by={by} reason={reason}")
    return 0


def _cmd_deactivate(args) -> int:
    problem = _check_ref_id(args.ref_id)
    if problem:
        _err(problem)
        return 2
    reason = _clean_reason(args.reason) if args.reason is not None else None
    if reason is not None and len(reason) > firestore_admin.REJECT_REASON_MAX_LEN:
        _err(f"--reason 은 {firestore_admin.REJECT_REASON_MAX_LEN}자 이하로 적어주세요.")
        return 2
    by = (args.by or _default_by()).strip()
    if not by:
        _err("--by 가 비었어요.")
        return 2
    _ensure_credentials()
    if args.dry_run:
        doc = firestore_admin.get_reference_registration(args.ref_id)
        if doc is None:
            _err(f"reference/{args.ref_id} 가 없어요.")
            return 1
        status, active = doc.get("registrationStatus"), doc.get("isActive")
        if status == models.REGISTRATION_STATUS_ACTIVE and active is not False:
            print(f"dry-run deactivate ref={args.ref_id} 현재=active isActive={active} → isActive=False (쓰기 없음)")
        else:
            print(
                f"dry-run deactivate ref={args.ref_id} 현재={status} isActive={active} — 실제 실행은 "
                "already_inactive 이거나 거부(종료 1)예요 (쓰기 없음)"
            )
        return 0
    try:
        result = firestore_admin.deactivate_reference_registration(args.ref_id, by=by, reason=reason or None)
    except ValueError as e:
        _err(str(e))
        return 1
    print(f"{result} ref={args.ref_id} by={by}" + (f" reason={reason}" if reason else ""))
    return 0


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="review_reference_registrations.py",
        description="공급자 등록 검수 — review 대기 목록 · 사진 · 승인 · 반려 (quick-261001-thx)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="검수 대기(review) 표")

    s = sub.add_parser("show", help="썸네일 · 영상 · 10/50/90%% 프레임 3장 내려받기")
    s.add_argument("ref_id")
    s.add_argument("--out", default=None, help=f"내려받을 폴더 (기본 {REVIEW_ROOT}/<refId>, 권한 700)")
    s.add_argument("--bucket", default=os.environ.get("VIDEO_BUCKET", _DEFAULT_BUCKET))

    a = sub.add_parser("approve", help="review → active (수강생 picker 노출)")
    a.add_argument("ref_id")
    a.add_argument("--by", default=None, help="운영자 id (기본 ops:<로컬 계정>)")
    a.add_argument("--dry-run", action="store_true")

    r = sub.add_parser("reject", help="review → failed + 사유")
    r.add_argument("ref_id")
    r.add_argument("--reason", required=True, help="공급자 실패 패널에 그대로 보이는 한국어 사유, 200자 이하")
    r.add_argument("--by", default=None, help="운영자 id (기본 ops:<로컬 계정>)")
    r.add_argument("--dry-run", action="store_true")

    d = sub.add_parser("deactivate", help="승인된 기준 내리기 (isActive false, 수강생 picker 에서 빠짐)")
    d.add_argument("ref_id")
    d.add_argument("--reason", default=None, help="내린 이유(운영 기록용, 공급자에게 안 보인다), 200자 이하")
    d.add_argument("--by", default=None, help="운영자 id (기본 ops:<로컬 계정>)")
    d.add_argument("--dry-run", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.cmd == "list":
        return _cmd_list(args)
    if args.cmd == "show":
        return _cmd_show(args)
    if args.cmd == "approve":
        return _cmd_approve(args)
    if args.cmd == "deactivate":
        return _cmd_deactivate(args)
    return _cmd_reject(args)


if __name__ == "__main__":
    sys.exit(main())

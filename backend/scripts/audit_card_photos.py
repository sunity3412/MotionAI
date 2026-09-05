"""확대 카드 사진 감사 — 완성된 카드 사진이 제목의 부위를 보여주는가 (quick-260905-mvm).

관찰 전용 계측기 — 채점·파이프라인·Firestore 쓰기 0. 09-05 belle 발견("6.1초 오른팔꿈치
카드가 5.3초 왼팔꿈치 카드와 같은 팔로 보인다") → 09-03 라이브 21장 중 5장이 제목과 다른
부위였는데, 현행 통과 기준("expected_units == emitted")은 사진 **장수**만 센다. 이 스크립트가
사진 내용을 센다.

절차 (카드마다):
  Firestore 문서 → result.faultZoomComparisons[] → imageUrl(presigned) 로 합성 PNG 내려받기
  (실패 시 imageKey 로 S3 폴백) → **좌/우 패널로 이등분** → 패널마다
  card_gates.eye_judge_majority(panel, "part") → card_photo_audit.audit_card 로 제목과 대조.

  ★ 이등분해서 패널마다 따로 묻는다 — 기존 눈은 "한 장 한 판정" 형상이라 반쪽씩 물어야
    답이 섞이지 않는다. 합성 = fault_zoom._compose "[user | ref] 가로 합성, 가운데 흰 구분선"
    (정사각 패널 2 + gap) 이므로 높이를 패널 변으로 삼아 gap 을 기하로 복원한다.
  ★ 눈의 질문에는 좌우·기대 관절이 없다 (card_gates._CLAIM_QUESTION["part"]) — 눈은
    "무엇이 보이는가"만 답하고 대조는 card_photo_audit(순수)가 한다.
  ★ 2단 판정 (quick-260905-ota): 1단(정중앙, part)이 허용 밖으로 읽힌 패널 가운데
    **표시가 있는 패널에만** "빨간 표시가 놓인 부위"(mark_part) 를 같은 N회 최빈으로 더
    묻고 card_photo_audit.adjudicate 로 결말을 정한다 — 표시가 허용 안이면 통과(by=mark,
    정중앙은 인접 맥락), 밖이면 확정 불일치(mark_elsewhere). 표시 없는 패널은 2단 없이
    확정(by=none). 표시 유무 = doc userMarked/refMarked (09-05 감사에서 21장 전부 실제
    그림과 일치). 호출 비용 = 1단 그대로 + 탈락 패널분(mvm 21장 기준 8장 × 1~2패널).
  ★ 패널마다 --rounds 회 묻고 **최빈 토큰**으로 확정한다 (동률 = unclear, fail-closed).
    plan 은 eye_judge_majority 를 지목했지만 part claim 에서 그 함수의 "불일치"는
    unclear/error(못 읽음)뿐이라 읽어낸 토큰이 1회차에 확정된다 — 09-05 실측(같은 21장
    2회 연속, temperature 0): 42 패널 중 4 패널의 토큰이 바뀌고(무릎→팔꿈치, 목→머리,
    팔꿈치→허벅지, 팔꿈치→정상) 카드 판정 2장이 뒤집혔다. "같은 입력에 같은 판정" 은
    토큰 다수결로만 성립한다. 질문·스키마·판정은 eye_judge 그대로 — 표만 여기서 센다
    (eye_judge_majority 가 match 표를 세는 것과 같은 자리, 세는 대상만 토큰).

모델 = gemini.config.resolve_model("C") (raw 문자열 박제 0). 키 = 기존 경로 재사용
(env GEMINI_API_KEY → SSM /sunity/motion/gemini-api-key; judging.gemini_moment_extractor).

실행 (로컬):
    cd backend && FIREBASE_SA_PATH=../firebase-sa.json AWS_PROFILE=sunity-motion \\
      .venv/bin/python scripts/audit_card_photos.py \\
      --uid verifyupx0903 --analysis-id c357f6b44117489281662072a640895c \\
      [--rounds 3] [--out audit.json] [--dump-dir panels/]
    --pairs uid:aid,uid:aid,...  로 여러 문서 한 번에.

출력 마지막 줄(로그 grep 가능한 불변식): `card_photo_audit total=N mismatched=M unresolved=K`
결말 = card_photo_audit.card_verdict — mismatched 는 어느 패널이든 2단 뒤 ok False
(mark_elsewhere / no_mark_and_center_elsewhere), unresolved 는 판정 불가(못 읽음·doc 과 그림의
표시 유무 어긋남). 감사 불가(no_expectation)·다운로드 실패는 unaudited 로 따로 센다 —
눈이 못 본 것은 틀린 게 아니다. 카드 행마다 패널별 `{center}→{mark} ok/by:reason` 을 싣는다.

하지 않는 일: 파이프라인에 붙이지 않는다(분석 시점 게이트 승격은 다음 단위), 좌표로 감사하지
않는다(crop 중심 출처가 경로마다 달라 rep12 신뢰도 판정은 오판 — 09-05 확인).
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent  # scripts/ → backend
for _p in (BACKEND / "shared" / "python", BACKEND):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from sunity_shared import firestore_admin as fa  # noqa: E402
from sunity_shared.analysis import card_gates as cg  # noqa: E402
from sunity_shared.analysis import card_photo_audit as cpa  # noqa: E402
from sunity_shared.gemini.config import resolve_model  # noqa: E402
from sunity_shared.judging.gemini_moment_extractor import _load_api_key  # noqa: E402

DEFAULT_BUCKET = "sunity-motion-pilot-videos"  # S3 폴백용 (imageKey) — VIDEO_BUCKET env 우선
_MAX_GAP_PX = 32  # 합성 구분선 폭 상한 — 이보다 크면 기하 복원 포기, 단순 이등분


def parse_pairs(args: argparse.Namespace) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    if args.uid and args.analysis_id:
        pairs.append((args.uid, args.analysis_id))
    for tok in (args.pairs or "").split(","):
        tok = tok.strip()
        if not tok:
            continue
        if ":" not in tok:
            raise SystemExit(f"--pairs 항목은 uid:analysisId 형식이어야 함: {tok!r}")
        uid, aid = tok.split(":", 1)
        pairs.append((uid.strip(), aid.strip()))
    if not pairs:
        raise SystemExit("입력 없음 — --uid/--analysis-id 또는 --pairs 필요")
    return pairs


def fetch_png(card: dict, *, timeout_s: float = 30.0) -> bytes:
    """카드 합성 PNG bytes — imageUrl(presigned GET) 우선, 실패 시 imageKey 로 S3."""
    url = card.get("imageUrl")
    err: Exception | None = None
    if url:
        try:
            with urllib.request.urlopen(url, timeout=timeout_s) as resp:  # noqa: S310
                return resp.read()
        except Exception as e:  # noqa: BLE001 - 폴백 사유로 보존
            err = e
    key = card.get("imageKey")
    if key:
        import boto3  # lazy — presigned 경로만 쓰면 AWS 의존 0

        bucket = os.environ.get("VIDEO_BUCKET", DEFAULT_BUCKET)
        obj = boto3.client("s3").get_object(Bucket=bucket, Key=key)
        return obj["Body"].read()
    raise RuntimeError(f"imageUrl 다운로드 실패 + imageKey 부재: {err!r}")


def split_panels(png: bytes):
    """[user | ref] 합성 → (user_panel, ref_panel) PIL RGB.

    fault_zoom._compose 는 정사각 패널 2 장을 가로로 붙이고 사이에 흰 gap 을 둔다 —
    높이 = 패널 변, gap = 너비 − 2·높이. 형상이 그와 다르면(gap 음수·과대) 단순 이등분.
    """
    from PIL import Image

    img = Image.open(io.BytesIO(png)).convert("RGB")
    w, h = img.size
    gap = w - 2 * h
    if 0 <= gap <= _MAX_GAP_PX:
        left = img.crop((0, 0, h, h))
        right = img.crop((h + gap, 0, 2 * h + gap, h))
    else:
        half = w // 2
        left = img.crop((0, 0, half, h))
        right = img.crop((w - half, 0, w, h))
    return left, right


def modal_token(observed: list[str], vocab: frozenset[str] = cpa.PART_VOCAB) -> str:
    """토큰 다수결 — 읽어낸 토큰(vocab 안) 중 최빈값. 동률·전부 못 읽음 = 'unclear'.

    vocab 은 claim 의 "읽어냈다" 집합 — part = PART_VOCAB, mark_part = MARK_VOCAB
    (no_mark 도 표다: 표시가 없다는 관측). 기본값은 종전(part) 그대로.
    """
    counts: dict[str, int] = {}
    for tok in observed:
        if tok in vocab:
            counts[tok] = counts.get(tok, 0) + 1
    if not counts:
        return "unclear"
    best = max(counts.values())
    winners = [t for t, n in counts.items() if n == best]
    return winners[0] if len(winners) == 1 else "unclear"


_CLAIM_VOCAB = {"part": cpa.PART_VOCAB, "mark_part": cpa.MARK_VOCAB}


def judge_panel(panel, *, api_key: str, model: str, rounds: int,
                claim: str = "part") -> dict:
    """패널 1장 → claim 관측: eye_judge 를 rounds 회 호출, 최빈 토큰으로 확정.

    claim = "part"(1단, 정중앙 부위) | "mark_part"(2단, 표시가 놓인 부위 — quick-260905-ota).
    각 호출은 운영 경로(card_gates.eye_judge — 질문·JSON 스키마·temperature 0) 그대로.
    반환 observed = 최빈 토큰(동률/전부 못 읽음 = unclear), votes = 토큰별 표,
    reason = 최빈 토큰 첫 응답의 근거 문장.
    """
    if claim not in _CLAIM_VOCAB:
        raise ValueError(f"unknown audit claim: {claim}")
    results = [cg.eye_judge(panel, claim, api_key=api_key, model=model)
               for _ in range(rounds)]
    tokens = [str(r.get("observed")) for r in results]
    winner = modal_token(tokens, _CLAIM_VOCAB[claim])
    first = next((r for r in results if r.get("observed") == winner), results[0])
    votes: dict[str, int] = {}
    for t in tokens:
        votes[t] = votes.get(t, 0) + 1
    return {
        "claim": claim,
        "observed": winner,
        "limb": first.get("limb"),
        "confidence": first.get("confidence"),
        "reason": first.get("reason"),
        "rounds": len(results),
        "votes": votes,
    }


def _fmt_side(center: dict, mark: dict | None, adj: dict) -> str:
    """패널 한 쪽의 로그 표기 — `{center}→{mark|-} ok/by:reason`."""
    m = mark["observed"] if mark else "-"
    return f"{center['observed']}→{m} {adj['ok']}/{adj['by']}:{adj['reason']}"


def audit_doc(uid: str, aid: str, *, api_key: str, model: str, rounds: int,
              dump_dir: Path | None) -> list[dict]:
    doc = fa.get_analysis(uid, aid)
    if doc is None:
        print(f"DOC NOT FOUND uid={uid} analysisId={aid}", flush=True)
        return []
    res = doc.get("result") or {}
    cards = res.get("faultZoomComparisons") or []
    ref_id = doc.get("referenceMotionId")
    print(f"\n## {uid}/{aid} reference={ref_id} cards={len(cards)}", flush=True)
    rows: list[dict] = []
    for i, card in enumerate(cards):
        if not isinstance(card, dict):
            continue
        joint = card.get("joint")
        crit = card.get("criterion")
        tier = card.get("tier") or "confirmed"
        # 표시 인증 flag 부재 = 종전 렌더(표시 있음) — 렌더러는 못 그렸을 때만 False 를
        # 싣는다 (contract §11.9/§11.11). 값은 플래그 이름(mark_mismatch/part_not_shown)만 가른다.
        user_marked = bool(card.get("userMarked", True))
        ref_marked = bool(card.get("refMarked", True))
        expected = cpa.expected_parts(crit, joint)
        row = {
            "uid": uid, "analysisId": aid, "reference": ref_id, "index": i,
            "tier": tier, "joint": joint, "criterion": crit,
            "userVideoSec": card.get("userVideoSec"), "refVideoSec": card.get("refVideoSec"),
            "userMarked": user_marked, "refMarked": ref_marked,
            "expected": sorted(expected),
        }
        try:
            png = fetch_png(card)
            user_panel, ref_panel = split_panels(png)
        except Exception as e:  # noqa: BLE001 - 실패를 삼키지 않고 행에 노출
            row.update({"error": f"{type(e).__name__}: {e}",
                        "audit": {"userOk": None, "refOk": None, "flags": ["fetch_failed"]}})
            rows.append(row)
            print(f"  [{i}] {tier} {joint} {crit} FETCH FAILED: {e!r}", flush=True)
            continue
        if dump_dir is not None:
            dump_dir.mkdir(parents=True, exist_ok=True)
            stem = f"{aid[:8]}_{i:02d}_{crit or joint}"
            user_panel.save(dump_dir / f"{stem}_user.jpg", quality=90)
            ref_panel.save(dump_dir / f"{stem}_ref.jpg", quality=90)
        # 1단 — 정중앙 부위 (mvm 그대로)
        u = judge_panel(user_panel, api_key=api_key, model=model, rounds=rounds)
        r = judge_panel(ref_panel, api_key=api_key, model=model, rounds=rounds)
        audit = cpa.audit_card(expected, u["observed"], r["observed"],
                               user_marked=user_marked, ref_marked=ref_marked)
        # 2단 — 1단 탈락 + 표시 있는 패널에만 표시 위치를 묻는다 (quick-260905-ota)
        um = rm = None
        if cpa.needs_mark_query(expected, u["observed"], marked=user_marked):
            um = judge_panel(user_panel, api_key=api_key, model=model, rounds=rounds,
                             claim="mark_part")
        if cpa.needs_mark_query(expected, r["observed"], marked=ref_marked):
            rm = judge_panel(ref_panel, api_key=api_key, model=model, rounds=rounds,
                             claim="mark_part")
        u_adj = cpa.adjudicate(expected, u["observed"], um["observed"] if um else None,
                               marked=user_marked)
        r_adj = cpa.adjudicate(expected, r["observed"], rm["observed"] if rm else None,
                               marked=ref_marked)
        verdict = cpa.card_verdict(u_adj, r_adj)
        row.update({"user": u, "ref": r, "userMark": um, "refMark": rm,
                    "audit": audit, "userAdj": u_adj, "refAdj": r_adj,
                    "verdict": verdict, "mismatch": verdict == "mismatch"})
        rows.append(row)
        votes = f"votes user={u['votes']} ref={r['votes']}"
        if um:
            votes += f" userMark={um['votes']}"
        if rm:
            votes += f" refMark={rm['votes']}"
        print(
            f"  [{i}] {tier:9s} {str(joint):15s} {str(crit):35s} "
            f"user={_fmt_side(u, um, u_adj)} ref={_fmt_side(r, rm, r_adj)} "
            f"{verdict.upper() if verdict != 'ok' else 'ok'}  {votes}",
            flush=True,
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(
        description="확대 카드 사진 감사 — 사진이 제목의 부위를 보여주는가 (관찰 전용)")
    ap.add_argument("--uid", default=None)
    ap.add_argument("--analysis-id", default=None)
    ap.add_argument("--pairs", default=None, metavar="uid:aid,uid:aid",
                    help="여러 문서 — 콤마 구분 uid:analysisId")
    ap.add_argument("--rounds", type=int, default=3,
                    help="패널당 질문 횟수 — 최빈 토큰으로 확정, 홀수 (기본 3)")
    ap.add_argument("--out", default=None, metavar="JSON", help="카드별 상세 JSON 저장 경로")
    ap.add_argument("--dump-dir", default=None, metavar="DIR",
                    help="이등분한 패널 JPEG 저장 (눈으로 대조용)")
    args = ap.parse_args()
    if args.rounds < 1 or args.rounds % 2 == 0:
        raise SystemExit(f"--rounds 는 양의 홀수여야 함 (다수결 동률 방지): {args.rounds}")

    pairs = parse_pairs(args)
    model = resolve_model("C")
    api_key = _load_api_key()
    dump_dir = Path(args.dump_dir) if args.dump_dir else None
    print(f"card_photo_audit model={model} rounds={args.rounds} docs={len(pairs)}", flush=True)

    rows: list[dict] = []
    for uid, aid in pairs:
        rows.extend(audit_doc(uid, aid, api_key=api_key, model=model,
                              rounds=args.rounds, dump_dir=dump_dir))

    total = len(rows)
    verdicts = [r.get("verdict", "unaudited") for r in rows]   # fetch 실패 행 = unaudited
    mismatched = verdicts.count("mismatch")
    unresolved = verdicts.count("unresolved")
    unaudited = verdicts.count("unaudited")
    tier2_panels = sum(1 for r in rows for k in ("userMark", "refMark") if r.get(k))
    if args.out:
        Path(args.out).write_text(
            json.dumps({"model": model, "rounds": args.rounds, "cards": rows},
                       ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"\nwrote {args.out}", flush=True)
    for label in ("mismatch", "unresolved"):
        print(f"\n# {label} cards", flush=True)
        for r in rows:
            if r.get("verdict") == label:
                print(f"  {r['reference']} [{r['index']}] {r['tier']} {r['joint']} "
                      f"{r['criterion']} user={_fmt_side(r['user'], r.get('userMark'), r['userAdj'])} "
                      f"ref={_fmt_side(r['ref'], r.get('refMark'), r['refAdj'])}", flush=True)
    print(f"card_photo_audit unaudited={unaudited} tier2_panels={tier2_panels}", flush=True)
    print(f"card_photo_audit total={total} mismatched={mismatched} unresolved={unresolved}",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

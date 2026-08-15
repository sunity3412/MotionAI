"""판정이 영상을 보면 무엇이 갈리는가 — 텍스트 판정 vs 영상 판정 대조.

belle 2026-08-15: "판정도 3.7flash video 로 하면 안 되는겨?"

측정 동기 (코드 실측):
  `gemini_teacher.judge_report` 는 교사가 만든 **JSON 리포트 텍스트만** 받는다
  (`contents=[prompt]` — 영상 없음). 즉 판정은 "글이 구체적인가"만 재고, **글은
  멀쩡한데 영상과 다른 것**은 원리적으로 못 잡는다. 교사가 없는 결함을 그럴듯하게
  지어내면 통과한다. belle 원칙 [[vision-score-must-analyze-not-stamp]] 위반 구조다.

이 스파이크가 재는 것: **같은 리포트**를 (A) 텍스트만 보는 판정 (B) 영상까지 보는
판정에 태워 점수가 갈리는 건수와 방향. 갈리는 건 = "교사가 지어냈는데 통과된 것"
후보이고, 그 숫자가 판정 구조를 바꿀지의 근거다.

★모델 버전으로 고르지 않는다 — 3.5/3.6/3.7 은 컨텍스트·출력 한도가 동일하고 설명도
  비어 있어 스펙으로는 우열을 못 가린다(2026-08-15 API 조회). 갈리는 지점만 본다.

실행 (Pod, 라벨링이 끝난 뒤 — 동시 실행은 429 로 진행 중 사이클을 죽인다):
  PYTHONPATH=shared/python:training:. python3 -m research.spikes.spike_judge_sees_video \\
    --accepted-dir /workspace/phase22_distill_out/accepted --limit 20
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import random
import sys

_BACKEND = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_BACKEND / "training"))

VIDEO_JUDGE_MODEL = "gemini-3.7-flash-video-understanding-eap"
TEXT_JUDGE_MODEL = "gemini-3.5-flash"


def _judge_prompt(report: dict, motion=None) -> str:
    """현행 judge 프롬프트를 그대로 재사용 — 프롬프트를 바꾸면 모델 효과가 아니라
    프롬프트 효과를 재게 된다. gemini_teacher 의 분기 규칙을 그대로 부른다."""
    from distill import gemini_teacher as gt

    # gemini_teacher 는 프롬프트를 함수 안에서 조립하므로 같은 규칙을 재현한다.
    faults = (report or {}).get("faults")
    motion_line = (
        f"분석 대상 동작: {motion}. 결함 판정의 타당성은 이 동작의 기술 요건에 "
        "비추어 평가하세요 — 이 동작에서 기술상 의도된 자세를 결함으로 짚었다면 "
        "판정 오류로 감점 대상입니다.\n"
        if motion
        else ""
    )
    if faults:
        rubric_line = (
            "이 리포트는 결함(faults)을 짚었습니다. 채점 기준: 짚기·측정의 구체성·"
            "일관성·물리적 타당성 + 해당 동작의 기술 요건에 비춘 결함 판정의 타당성. "
            "억지 결함(동작상 정상 자세를 결함으로 짚음)이면 감점하세요. 결함 개수나 "
            "숫자가 많다는 이유만으로 고득점을 주지 마세요.\n"
        )
    else:
        rubric_line = (
            "이 리포트는 결함(faults)이 빈 배열입니다 — 정타 판정. 결함이 없다는 것 "
            "자체를 감점하지 마세요. 채점 기준: 코칭 문장의 구체성·기술 정합성·실행 "
            "가능성.\n"
        )
    assert gt.JUDGE_MODEL  # 모듈 계약 존재 확인(프롬프트 출처 명시).
    return (
        "다음 폴스포츠 모션 분석 리포트의 품질을 0~10 정수로만 채점하세요.\n"
        f"{motion_line}{rubric_line}"
        "채점 앵커: 구체적이고 타당하면 8~10, 모호하거나 일반론이면 4~7, 부정확하거나 "
        "물리적으로 불가능한 서술이면 0~3.\n"
        "숫자 하나만 출력:\n"
        + json.dumps(report, ensure_ascii=False, sort_keys=True)
    )


def _video_judge_prompt(report: dict, motion=None) -> str:
    """영상 판정 — 같은 루브릭에 **영상 대조 한 줄만** 추가한다.

    추가 문장이 하나뿐인 이유: 프롬프트 차이를 최소화해야 '영상을 봤다'는 것 자체의
    효과를 분리할 수 있다. 문장을 여러 개 바꾸면 무엇이 갈랐는지 못 가린다.
    """
    base = _judge_prompt(report, motion)
    return base.replace(
        "숫자 하나만 출력:\n",
        "★함께 첨부된 영상을 직접 보고, 리포트가 짚은 결함이 실제로 영상에 있는지 "
        "대조하세요. 영상에 없는 결함을 짚었으면 그것이 가장 큰 감점 사유입니다.\n"
        "숫자 하나만 출력:\n",
    )


def _score(text) -> int:
    from distill.gemini_teacher import _parse_judge_score

    return _parse_judge_score(text)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="텍스트 판정 vs 영상 판정 대조")
    ap.add_argument("--accepted-dir", default="/workspace/phase22_distill_out/accepted")
    ap.add_argument("--manifest", default=str(_BACKEND / "training" / "data" / "manifest.json"))
    ap.add_argument("--bucket", default="sunity-motion-pilot-videos")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--seed", type=int, default=0, help="표본 선택 결정론")
    ap.add_argument("--out", default="/tmp/judge_video_compare.json")
    args = ap.parse_args(argv)

    import boto3
    from google import genai

    from distill.gemini_teacher import _delete_uploaded, _upload_and_wait

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("GEMINI_API_KEY 미설정 — 중단", file=sys.stderr)
        return 2
    client = genai.Client(api_key=key)
    s3 = boto3.client("s3")

    manifest = json.loads(pathlib.Path(args.manifest).read_text(encoding="utf-8"))
    by_hash = {r.get("video_hash"): r for r in manifest.get("rows", []) if r.get("video_hash")}

    files = sorted(pathlib.Path(args.accepted_dir).glob("*.json"))
    random.Random(args.seed).shuffle(files)
    rows, agree, disagree = [], 0, 0
    for p in files:
        if len(rows) >= args.limit:
            break
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        report = rec.get("report")
        vh = rec.get("video_hash")
        src = by_hash.get(vh)
        if not isinstance(report, dict) or not src or not src.get("s3_key"):
            continue
        motion = src.get("motion")

        # (A) 텍스트 판정 — 현행 구조 그대로.
        a = _score(client.models.generate_content(
            model=TEXT_JUDGE_MODEL,
            contents=[_judge_prompt(report, motion)],
            config={"temperature": 0.0},
        ).text)

        # (B) 영상 판정 — 같은 루브릭 + 영상 첨부.
        local = f"/tmp/_judge_{vh}.mp4"
        s3.download_file(args.bucket, src["s3_key"], local)
        uploaded = None
        try:
            uploaded = _upload_and_wait(client, local)
            b = _score(client.models.generate_content(
                model=VIDEO_JUDGE_MODEL,
                contents=[uploaded, _video_judge_prompt(report, motion)],
                config={"temperature": 0.0},
            ).text)
        finally:
            if uploaded is not None:
                _delete_uploaded(client, uploaded)
            pathlib.Path(local).unlink(missing_ok=True)

        n_faults = len(report.get("faults") or [])
        flipped = (a >= 7) != (b >= 7)  # JUDGE_MIN_SCORE 근방 통과/폐기 뒤집힘
        agree += (not flipped)
        disagree += flipped
        rows.append({
            "video_hash": vh, "motion": motion, "faults": n_faults,
            "text_judge": a, "video_judge": b, "delta": b - a, "flipped": flipped,
        })
        print("  %-16s %-24s faults=%d  텍스트=%2d  영상=%2d  Δ%+d%s"
              % (str(vh)[:16], str(motion)[:24], n_faults, a, b, b - a,
                 "  ★통과여부 뒤집힘" if flipped else ""))

    if not rows:
        print("표본 0 — accepted 리포트와 manifest 조인 실패", file=sys.stderr)
        return 1
    deltas = [r["delta"] for r in rows]
    print("\n표본 %d | 통과여부 뒤집힘 %d건 (%.0f%%)"
          % (len(rows), disagree, 100.0 * disagree / len(rows)))
    print("영상 판정이 더 낮게 준 건: %d | 더 높게: %d | 동일: %d"
          % (sum(1 for d in deltas if d < 0), sum(1 for d in deltas if d > 0),
             sum(1 for d in deltas if d == 0)))
    print("평균 Δ(영상-텍스트): %+.2f" % (sum(deltas) / len(deltas)))
    pathlib.Path(args.out).write_text(
        json.dumps({"rows": rows, "text_model": TEXT_JUDGE_MODEL,
                    "video_model": VIDEO_JUDGE_MODEL}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print("저장:", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""정타(잘된예시) 6편에 vision 판정 → 보고되는 편차 크기 분포 측정.

목적 (quick-260831-isk 리뷰 지적): vision-sourced 편차의 tol 우회(over=dev)가
소음 크기(2~5°) 감점을 만들어 정타에 위양성을 내는지. 근거가 N=1 이었다 → N=6 으로.

측정: 각 정타 페어에서 supported_differences 의 (student_angle_deg, reference_angle_deg)
편차 크기와, 그것이 현행 규칙에서 만들 감점 points.
Pod 불필요 (Gemini 호출만). 결과 JSONL append.
"""
import json
import os
import pathlib
import sys
import time

sys.path.insert(0, '/Users/kimtaesung/Dev/SunityMotion/backend/shared/python')
from sunity_shared.analysis.gemini_vision_scorer import assess_fault_context_video  # noqa: E402
from sunity_shared.analysis import ipsf_criteria  # noqa: E402
from sunity_shared.analysis.deduction_engine import PER_RECORD_DEDUCTION_CAP  # noqa: E402

SP = pathlib.Path('/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/98fff9b3-a04d-444f-8292-bb7ea4f5a77c/scratchpad')
VID = pathlib.Path('/Users/kimtaesung/Downloads/정은지 선수 추가 영상/잘된 예시')
OUT = SP / 'vision_noise_results.jsonl'

PAIRS = [
    ('peter-pan', VID / 'fixtures:peter-pan-correct.mp4', SP / 'ref-peter-pan.mp4'),
    ('power-spin', VID / 'fixtures:power-spin-correct.mp4', SP / 'ref-power-spin.mp4'),
    ('climb', VID / 'fixtures:climb-correct.mp4', SP / 'ref-climb.mp4'),
    ('kip-up', VID / 'fixtures:kip-up-correct.mp4', SP / 'ref-kip-up.mp4'),
    ('elbow-twist-sister', SP / 'elbow-correct-1080.mp4', SP / 'ref-elbow-twist-sister.mp4'),
    ('pdshape', VID / 'fixtures:pdshape-correct.mp4  .mp4', SP / 'ref-pdshape.mp4'),
]


def as_dict(o):
    if isinstance(o, dict):
        return o
    return getattr(o, '__dict__', {}) or {}


def split_rule():
    """split_angle criterion 의 slope/tolerance (실측 — 하드코딩 금지)."""
    for c in ipsf_criteria.CRITERION_GROUPS:
        if c.get('id') == 'split_angle':
            return c
    return {}


def main() -> None:
    rule = split_rule()
    slope = rule.get('slope')
    cap = PER_RECORD_DEDUCTION_CAP  # 관절당 상한 -20 (ipsf_cap 90 보다 먼저 물림)
    tol = rule.get('tolerance')
    print(f'split_angle rule: slope={slope} cap={cap} tol={tol}', flush=True)
    for motion, student, ref in PAIRS:
        assert student.exists(), f'missing {student}'
        assert ref.exists(), f'missing {ref}'
    for motion, student, ref in PAIRS:
        t0 = time.time()
        try:
            r = assess_fault_context_video(str(student), str(ref))
        except Exception as exc:  # noqa: BLE001
            row = {'motion': motion, 'error': repr(exc)[:300]}
            with OUT.open('a') as f:
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
            print(f'[{motion}] ERROR {exc}', flush=True)
            continue
        diffs = [as_dict(d) for d in (r.get('supported_differences') or [])]
        items = []
        for d in diffs:
            sa, ra = d.get('student_angle_deg'), d.get('reference_angle_deg')
            dev = None
            if isinstance(sa, (int, float)) and isinstance(ra, (int, float)):
                dev = abs(float(sa) - float(ra))
            pts_new = pts_old = None
            if dev is not None and slope and cap:
                pts_new = -min(cap, dev * slope)                      # 수리 후 (tol 우회)
                pts_old = -min(cap, max(0.0, dev - (tol or 0)) * slope)  # 수리 전
            items.append({
                'category': d.get('fault_category'), 'body_part': d.get('body_part'),
                'student_deg': sa, 'reference_deg': ra, 'dev': dev,
                'severity': d.get('severity'),
                'points_after_fix': pts_new, 'points_before_fix': pts_old,
            })
        row = {'motion': motion, 'status': r.get('status'),
               'n_supported': len(diffs), 'items': items,
               'elapsed_s': round(time.time() - t0)}
        with OUT.open('a') as f:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
        print(f"[{motion}] status={row['status']} supported={row['n_supported']} "
              f"items={[(i['category'], i['dev'], i['points_after_fix']) for i in items]} "
              f"({row['elapsed_s']}s)", flush=True)


if __name__ == '__main__':
    main()

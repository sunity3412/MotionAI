"""측정 B — 다중 프레임 다수결 (STEP0-PREREGISTRATION.md §3).

사전 기준 파일(bdaebd1c, 측정 전 커밋)의 규칙만 따른다. 임계·창·폴백을 바꾸지 않는다.
모델 재실행 없음 — Firestore + ffprobe 실측 해상도만 쓴다.

실행:
  cd /Users/kimtaesung/Dev/SunityMotion/backend && \
  FIREBASE_SA_PATH=../firebase-sa.json .venv/bin/python \
    ../.planning/quick/260907-itk-step-0/evidence/measure_b_vote.py

산출: measure_b_vote.json (같은 디렉터리)
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys

sys.path.insert(0, '/Users/kimtaesung/Dev/SunityMotion/backend/shared/python')

import numpy as np  # noqa: E402

from sunity_shared import firestore_admin as fa  # noqa: E402
from sunity_shared.analysis import fault_zoom as fz  # noqa: E402

EVID = os.path.dirname(os.path.abspath(__file__))
ROSTER = os.path.join(EVID, 'roster_corrected.json')
OUT = os.path.join(EVID, 'measure_b_vote.json')

UID = 'NdVZrpbmUbPMNMjASFwUgy8Fj9p1'
DOC8_TO_AID = {
    '4e232c4a': '4e232c4a73ec40a6a8deb07cbf6aa03f',
    'a559705f': 'a559705f06784505bf266afe99cf2822',
    'd213622a': 'd213622a3e754d0f851a436e8bc9f208',
    '5ae210fa': '5ae210fabec349698e1d35912b8f22e1',
    'ea765def': 'ea765def661e480292f95c5df57092a1',
    '21b1b7ed': '21b1b7ed3bc84d829d201334e64acc5b',
}
# 학생 원본 (fileName 필드로 대조, 아래 assert)
STUDENT_VIDEO_DIR = '/Users/kimtaesung/Downloads/정은지 선수 추가 영상'

MIDPOINT_TOL = 1e-9   # §3 "오차 1e-9 이내"


# ---------------------------------------------------------------- 표본 구조
def midpoint_max_err(rep: dict) -> float | None:
    """홀수 인덱스가 이웃의 중점인가 — max |d[odd] - (d[odd-1]+d[odd+1])/2|.

    ~1e-9 이내로 통과하면 2x 선형 업샘플(홀수 = 무정보) → 걸음 2.
    실패하면 진짜 표본 → 걸음 1. 하드코딩하지 않고 **잰다**(§3).
    """
    frames = int(rep.get('frames') or 0)
    joints = rep.get('joints') or []
    nj = len(joints)
    if frames < 3 or nj == 0:
        return None
    d = np.asarray(rep['data'], dtype=float).reshape(frames, nj * 2)
    odd = np.arange(1, frames - 1, 2)
    if odd.size == 0:
        return None
    err = np.abs(d[odd] - (d[odd - 1] + d[odd + 1]) / 2.0)
    return float(np.nanmax(err))


def measured_step(rep: dict) -> tuple[int, float | None]:
    e = midpoint_max_err(rep)
    if e is None:
        return 1, None
    return (2 if e <= MIDPOINT_TOL else 1), e


# ---------------------------------------------------------------- 해상도
def ffprobe_wh(path_or_url: str) -> tuple[int, int]:
    out = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
         '-show_entries', 'stream=width,height',
         '-of', 'default=nw=1:nk=0', path_or_url],
        capture_output=True, text=True, check=True).stdout
    kv = dict(line.split('=', 1) for line in out.strip().splitlines() if '=' in line)
    return int(kv['width']), int(kv['height'])


def main() -> int:
    roster = json.load(open(ROSTER))
    panels = [r for r in roster
              if r.get('vertex_centered') is True and r.get('card_frac') is not None]

    docs: dict[str, dict] = {}
    reports: dict[tuple[str, str], dict] = {}
    steps: dict[tuple[str, str], dict] = {}
    wh: dict[tuple[str, str], dict] = {}
    struct_notes: list[str] = []

    for doc8 in sorted({r['doc'] for r in panels}):
        aid = DOC8_TO_AID[doc8]
        d = fa._db().document(f'users/{UID}/analyses/{aid}').get().to_dict()
        docs[doc8] = d
        res = d['result']
        ref_id = d.get('referenceMotionId')
        ref_doc = fa.get_reference_motion(ref_id)

        u_rep = res['keypointReport']
        r_rep = ref_doc['referenceKeypointReport']
        reports[(doc8, 'user')] = u_rep
        reports[(doc8, 'ref')] = r_rep

        # --- 1. 표본 구조: 재고 나서 걸음을 정한다
        u_step, u_err = measured_step(u_rep)
        r_step, r_err = measured_step(r_rep)
        top_af = d.get('anglesFrames')
        u_frames = int(u_rep['frames'])
        r_frames = int(r_rep['frames'])
        ref_af = ref_doc.get('anglesFrames')

        u_expected = (top_af is not None and u_frames == 2 * int(top_af))
        r_expected = (ref_af is not None and r_frames == int(ref_af))
        if not u_expected:
            struct_notes.append(
                f'{doc8} user: frames={u_frames} != 2 x top-level anglesFrames={top_af} '
                f'(사전 기준의 기대 패턴 위배 — 측정된 걸음 {u_step} 을 쓴다)')
        if not r_expected:
            struct_notes.append(
                f'{doc8} ref: frames={r_frames} != ref anglesFrames={ref_af} '
                f'(기대 패턴 위배 — 측정된 걸음 {r_step} 을 쓴다)')
        if u_step != 2:
            struct_notes.append(
                f'{doc8} user: 중점 검사 실패(max={u_err}) — 2x 업샘플이 아니다. 걸음 1')
        if r_step != 1:
            struct_notes.append(
                f'{doc8} ref: 중점 검사 통과(max={r_err}) — 진짜 표본이 아니다. 걸음 2')

        steps[(doc8, 'user')] = {
            'step': u_step, 'midpoint_max_err': u_err, 'frames': u_frames,
            'top_level_anglesFrames': top_af,
            'frames_eq_2x_top_anglesFrames': u_expected,
            'result_anglesFrames': res.get('anglesFrames'),
            'rep_fps': u_rep.get('fps'),
        }
        steps[(doc8, 'ref')] = {
            'step': r_step, 'midpoint_max_err': r_err, 'frames': r_frames,
            'ref_anglesFrames': ref_af,
            'frames_eq_ref_anglesFrames': r_expected,
            'rep_fps': r_rep.get('fps'),
            'referenceMotionId': ref_id,
        }

        # --- 4. 해상도: 두 출처로 잰다 (ffprobe 실측 + 크롭로그 몫 대조)
        fname = d.get('fileName')
        upath = os.path.join(STUDENT_VIDEO_DIR, fname or '')
        if not os.path.exists(upath):
            wh[(doc8, 'user')] = {'W': None, 'H': None,
                                  'source': f'UNAVAILABLE: 로컬 원본 없음 ({fname})'}
        else:
            W, H = ffprobe_wh(upath)
            wh[(doc8, 'user')] = {
                'W': W, 'H': H,
                'source': f'ffprobe (로컬 원본, doc.fileName={fname})',
                'min_side': min(W, H)}
        rurl = res.get('referenceVideoUrl')
        try:
            W, H = ffprobe_wh(rurl)
            wh[(doc8, 'ref')] = {
                'W': W, 'H': H,
                'source': ('ffprobe (result.referenceVideoUrl presigned, '
                           f'{ref_id})'),
                'min_side': min(W, H)}
        except Exception as e:  # noqa: BLE001
            wh[(doc8, 'ref')] = {'W': None, 'H': None,
                                 'source': f'UNAVAILABLE: ffprobe 실패 {e}'}

    # 크롭 로그 몫 = shared_frac x min(W,H) 대조 (독립 2번째 출처)
    croplog_check = []
    for r in panels:
        doc8, side, frac = r['doc'], r['side'], float(r['card_frac'])
        info = wh[(doc8, side)]
        if info['W'] is None:
            continue
        croplog_check.append({
            'doc': doc8, 'side': side, 'card_frac': frac,
            'ffprobe_min_side': info['min_side'],
            'implied_side_px': round(frac * info['min_side']),
        })

    rows = []
    for r in panels:
        doc8, idx_s, side, joint = r['doc'], r['idx'], r['side'], r['joint']
        idx = int(idx_s)
        role = 'target' if r['final'] == 'mismatch' else 'control'
        frac = float(r['card_frac'])
        thr = 0.25 * frac
        row: dict = {
            'doc': doc8, 'idx': idx_s, 'side': side, 'joint': joint,
            'crit': r.get('crit'), 'role': role, 'card_frac': frac,
            'threshold': thr,
        }

        res = docs[doc8]['result']
        comps = res.get('faultZoomComparisons') or []
        if idx >= len(comps):
            row.update(verdict='ABORT',
                       abort_reason=f'faultZoomComparisons[{idx}] 없음 (n={len(comps)})')
            rows.append(row)
            continue
        comp = comps[idx]
        # --- 2. 중심 인덱스: 카드 자신의 값을 rep 공간 그대로 (fault_zoom.py:3909,3940)
        centre = comp['userFrameIdx'] if side == 'user' else comp['refFrameIdx']
        centre = int(centre)
        row['card_userFrameIdx'] = int(comp['userFrameIdx'])
        row['card_refFrameIdx'] = int(comp['refFrameIdx'])
        row['card_joint'] = comp.get('joint')
        row['centre_idx'] = centre

        # 명부와 교차검증 — 어긋나면 그 면은 ABORT (추측하지 않는다)
        xchecks = {
            'user_frame == userFrameIdx/2':
                r.get('user_frame') == int(comp['userFrameIdx']) / 2,
            'ref_rep_idx == refFrameIdx/2':
                r.get('ref_rep_idx') == int(comp['refFrameIdx']) / 2,
            'roster joint == card joint': r['joint'] == comp.get('joint'),
        }
        row['roster_crosscheck'] = xchecks
        if not all(xchecks.values()):
            row.update(verdict='ABORT',
                       abort_reason=('명부-문서 불일치: '
                                     + ', '.join(k for k, v in xchecks.items() if not v)))
            rows.append(row)
            continue

        rep = reports[(doc8, side)]
        st = steps[(doc8, side)]
        step = int(st['step'])
        frames = int(st['frames'])
        row['step'] = step
        row['step_evidence'] = {k: st[k] for k in st}

        info = wh[(doc8, side)]
        row['WH'] = [info['W'], info['H']]
        row['wh_source'] = info['source']

        stored = fz._kp_xy(rep, centre, joint)   # noqa: SLF001
        row['stored_xy'] = list(stored) if stored else None
        row['stored_conf'] = fz._kp_conf(rep, centre, joint)   # noqa: SLF001
        row['stored_collapsed'] = fz.is_collapsed_frame(rep, centre)

        # --- 3. 표본
        raw = [centre + o * step for o in (-2, -1, 0, 1, 2)]
        clipped = [max(0, min(i, frames - 1)) for i in raw]
        seen, sample_idxs = set(), []
        for i in clipped:
            if i not in seen:
                seen.add(i)
                sample_idxs.append(i)
        row['n_samples'] = len(sample_idxs)
        row['sample_idxs'] = sample_idxs

        dropped, kept = [], []
        for i in sample_idxs:
            c = fz._kp_conf(rep, i, joint)          # noqa: SLF001
            if c == 0.0:
                dropped.append({'idx': i, 'reason': 'conf == 0.0'})
                continue
            if fz.is_collapsed_frame(rep, i):
                dropped.append({'idx': i, 'reason': 'is_collapsed_frame'})
                continue
            xy = fz._kp_xy(rep, i, joint)           # noqa: SLF001
            if xy is None:
                dropped.append({'idx': i,
                                'reason': 'kp_xy None (좌표 부재/비유한 — 중앙값 불가)'})
                continue
            kept.append((i, xy, c))
        row['dropped'] = dropped
        row['n_surviving'] = len(kept)
        row['surviving'] = [{'idx': i, 'xy': list(xy), 'conf': c} for i, xy, c in kept]

        if info['W'] is None or stored is None:
            row['voted_xy'] = None
            row['delta_norm'] = None
            row['verdict'] = 'VOTE_UNAVAILABLE'
            row['unavailable_reason'] = ('해상도 미확보' if info['W'] is None
                                         else '중심 프레임 좌표 부재')
            rows.append(row)
            continue
        if len(kept) < 3:
            row['voted_xy'] = None
            row['delta_norm'] = None
            row['verdict'] = 'VOTE_UNAVAILABLE'
            row['unavailable_reason'] = f'살아남은 표본 {len(kept)} < 3'
            rows.append(row)
            continue

        W, H = info['W'], info['H']
        m = min(W, H)
        # --- 4. 투표 = 좌표별 중앙값, 픽셀에서 (연속량은 최빈값이 아니라 중앙값)
        px = [xy[0] * W for _i, xy, _c in kept]
        py = [xy[1] * H for _i, xy, _c in kept]
        vx_px, vy_px = float(np.median(px)), float(np.median(py))
        sx_px, sy_px = stored[0] * W, stored[1] * H
        # --- 5. delta
        delta = math.hypot(vx_px - sx_px, vy_px - sy_px) / m
        row['voted_xy'] = [vx_px / W, vy_px / H]
        row['voted_xy_px'] = [vx_px, vy_px]
        row['stored_xy_px'] = [sx_px, sy_px]
        row['vote_method'] = 'coordinate-wise median in pixels'
        row['delta_norm'] = delta
        row['delta_px_shortside'] = delta * m
        row['verdict'] = 'VOTE_MOVES' if delta > thr else 'VOTE_HOLDS'
        rows.append(row)

    # ------------------------------------------------------------- 판정
    tgt = [r for r in rows if r['role'] == 'target']
    ctl = [r for r in rows if r['role'] == 'control']

    def count(rs, v):
        return sum(1 for r in rs if r['verdict'] == v)

    t_moves, t_holds = count(tgt, 'VOTE_MOVES'), count(tgt, 'VOTE_HOLDS')
    t_unav = count(tgt, 'VOTE_UNAVAILABLE') + count(tgt, 'ABORT')
    c_moves = count(ctl, 'VOTE_MOVES')

    # §3 B 단독 판정 — 규칙 그대로
    if t_unav >= 2:
        verdict = 'INCONCLUSIVE'
        why = f'VOTE_UNAVAILABLE/ABORT 표적 {t_unav}면 (>=2) — §3 규칙'
    elif t_moves >= 3 and c_moves <= 2:
        verdict = ('학습 불필요, 다수결이 곧 수리 — 단, 조항 (ii) 는 측정 A 의존이라 '
                   'B 단독으로는 확정 불가')
        why = (f'(i) 표적 VOTE_MOVES {t_moves}>=3 충족 · (iii) 대조군 VOTE_MOVES '
               f'{c_moves}<=2 충족 · (ii) 미평가(측정 A 필요)')
    elif t_holds >= 3:
        verdict = '다수결은 수리가 아니다'
        why = (f'표적 {t_holds}/5 면이 VOTE_HOLDS (>=3) — 이웃한 진짜 프레임들이 '
               f'문제의 프레임에 동의한다')
    else:
        verdict = 'INCONCLUSIVE'
        why = (f'표적 MOVES {t_moves} · HOLDS {t_holds} · UNAVAIL {t_unav} · '
               f'대조군 MOVES {c_moves} — §3 어느 가지에도 안 맞는다')

    out = {
        'measurement': 'B — 다중 프레임 다수결 (STEP0-PREREGISTRATION.md §3)',
        'preregistration_commit': 'bdaebd1c',
        'run_note': '모델 재실행 없음. Firestore + ffprobe 실측 해상도.',
        'sampling_structure': {f'{k[0]}/{k[1]}': v for k, v in steps.items()},
        'sampling_structure_notes': struct_notes or
        ['모든 리포트가 사전 기준의 기대 패턴과 일치 — 학생 걸음 2, 기준 걸음 1'],
        'frame_dimensions': {f'{k[0]}/{k[1]}': v for k, v in wh.items()},
        'croplog_crosscheck': croplog_check,
        'panels': rows,
        'tally': {
            'targets': {'n': len(tgt), 'VOTE_MOVES': t_moves,
                        'VOTE_HOLDS': t_holds,
                        'VOTE_UNAVAILABLE': count(tgt, 'VOTE_UNAVAILABLE'),
                        'ABORT': count(tgt, 'ABORT')},
            'controls': {'n': len(ctl), 'VOTE_MOVES': c_moves,
                         'VOTE_HOLDS': count(ctl, 'VOTE_HOLDS'),
                         'VOTE_UNAVAILABLE': count(ctl, 'VOTE_UNAVAILABLE'),
                         'ABORT': count(ctl, 'ABORT')},
        },
        'headroom': {
            'note': ('판정이 임계에 얼마나 가까웠는가 — delta_norm / THRESHOLD. '
                     '1.0 초과가 VOTE_MOVES.'),
            'ratios': sorted(
                ({'panel': f"{r['doc']}[{r['idx']}] {r['side']} {r['joint']}",
                  'role': r['role'],
                  'ratio': (r['delta_norm'] / r['threshold'])
                  if r.get('delta_norm') is not None else None}
                 for r in rows),
                key=lambda x: (x['ratio'] is None, -(x['ratio'] or 0))),
        },
        'prediction_check': {
            'preregistered': ('기준측 3면 VOTE_HOLDS · 학생측 2면 VOTE_MOVES '
                              '= 2-3 갈림 = INCONCLUSIVE (§5)'),
            'observed': (f'기준측 표적 3면 전부 VOTE_HOLDS(예측 적중) · '
                         f'학생측 표적 2면도 VOTE_HOLDS(예측 빗나감) '
                         f'= 5-0 = "다수결은 수리가 아니다"'),
            'held': False,
        },
        'measurement_verdict': verdict,
        'verdict_basis': why,
        'clause_ii_status': ('미평가 — 조항 (ii)("움직인 면마다 MediaPipe 좌표가 투표 '
                             '좌표의 THRESHOLD 안") 는 측정 A 산출을 필요로 한다. '
                             'B 단독 실행에서는 평가할 수 없다.'),
    }
    json.dump(out, open(OUT, 'w'), ensure_ascii=False, indent=2)
    print(json.dumps(out['sampling_structure_notes'], ensure_ascii=False, indent=2))
    print()
    for r in rows:
        print(f"{r['role']:7s} {r['doc']}[{r['idx']}] {r['side']:4s} {r['joint']:14s} "
              f"c={r.get('centre_idx')} step={r.get('step')} "
              f"surv={r.get('n_surviving')}/{r.get('n_samples')} "
              f"d={r.get('delta_norm')} thr={r['threshold']:.4f} -> {r['verdict']}")
    print()
    print(json.dumps(out['tally'], ensure_ascii=False, indent=2))
    print('VERDICT:', verdict)
    print('BASIS  :', why)
    print('->', OUT)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

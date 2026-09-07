"""측정 A — 독립 2차 모델(MediaPipe BlazePose Heavy) 대조.

사전 기준: STEP0-PREREGISTRATION.md §2. 임계·판정 규칙을 여기서 바꾸지 않는다.

  AGREE        d_norm <= 0.25*card_frac  AND  visibility >= 0.5
  DISAGREE     d_norm >  0.25*card_frac  AND  visibility >= 0.5
  INCONCLUSIVE visibility < 0.5 또는 미검출 (불일치로 세지 않는다)

거리는 **픽셀에서** 잰다 (§1): 저장 좌표는 x 를 W 로, y 를 H 로 따로 정규화하므로
정규화 좌표를 그대로 빼면 안 된다. dpx=(x2-x1)*W, dpy=(y2-y1)*H, d=hypot/min(W,H).

프레임 원장(§0)은 roster_corrected.json 이 준다 — 인덱스 산술을 여기서 새로 하지 않는다.
  · 학생 패널: user_frame  → 학생 영상 9fps 프레임 배열 인덱스
  · 기준 패널: ref_video_idx → 기준 영상 9fps 프레임 배열 인덱스
                (이미 fault_zoom.ref_display_frame_index 를 통과한 값)
저장 좌표 조회 인덱스는 카드 자신의 rep 인덱스(userFrameIdx / refFrameIdx, 18fps 공간).

3 단계, 2 개의 venv (mediapipe 는 backend/.venv 에 절대 넣지 않는다 — Py3.14 +
opencv-contrib 충돌):
  stage stored : backend/.venv   (Firestore + fault_zoom 헬퍼)
  stage mp     : scratchpad/mpcheck (mediapipe==0.10.35, RunningMode.IMAGE)
  stage join   : 아무 venv
"""
from __future__ import annotations

import json
import math
import os
import sys

EV = '/Users/kimtaesung/Dev/SunityMotion/.planning/quick/260907-itk-step-0/evidence'
FRAMES = os.path.join(EV, 'frames')
ROSTER = os.path.join(EV, 'roster_corrected.json')
MANIFEST = os.path.join(EV, 'frames_manifest_a.json')
STORED = os.path.join(EV, 'stored_panels_a.json')
MPOUT = os.path.join(EV, 'mp_landmarks_a.json')
FINAL = os.path.join(EV, 'measure_a_mediapipe.json')

MODEL_TASK = ('/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/'
              'ef43362f-c430-4e36-8fdb-e8f1b3e28e8d/scratchpad/pose_landmarker_heavy.task')

UID = 'NdVZrpbmUbPMNMjASFwUgy8Fj9p1'
AIDS = {
    '4e232c4a': '4e232c4a73ec40a6a8deb07cbf6aa03f',
    'a559705f': 'a559705f06784505bf266afe99cf2822',
    'd213622a': 'd213622a3e754d0f851a436e8bc9f208',
    '5ae210fa': '5ae210fabec349698e1d35912b8f22e1',
    'ea765def': 'ea765def661e480292f95c5df57092a1',
    '21b1b7ed': '21b1b7ed3bc84d829d201334e64acc5b',
}

VIS_MIN = 0.5        # = fault_zoom._KP_CONF_MIN, 사전 기준 §2
THRESH_K = 0.25      # = 크롭 반지름의 절반, 사전 기준 §1


def panels() -> list[dict]:
    """대상 5 + 대조 13 = vertex_centered True 이고 card_frac 이 기록된 면 전부."""
    rows = json.load(open(ROSTER))
    out = []
    for r in rows:
        if not r.get('vertex_centered') or r.get('card_frac') is None:
            continue
        out.append({
            'doc': r['doc'], 'idx': r['idx'], 'side': r['side'], 'joint': r['joint'],
            'crit': r['crit'], 'card_frac': float(r['card_frac']),
            'role': 'target' if r['final'] == 'mismatch' else 'control',
            'roster_final': r['final'],
            'video_frame_idx': int(r['user_frame']) if r['side'] == 'user' else int(r['ref_video_idx']),
            'roster_user_frame': r['user_frame'],
            'roster_ref_rep_idx': r['ref_rep_idx'],
            'roster_ref_video_idx': r['ref_video_idx'],
        })
    return out


# ── stage stored ────────────────────────────────────────────────────────────
def stage_stored() -> None:
    sys.path.insert(0, '/Users/kimtaesung/Dev/SunityMotion/backend/shared/python')
    from sunity_shared import firestore_admin as fa
    from sunity_shared.analysis import fault_zoom as fz

    docs, refs = {}, {}
    rows = panels()
    for p in rows:
        short = p['doc']
        if short not in docs:
            d = fa._db().document(f"users/{UID}/analyses/{AIDS[short]}").get().to_dict()
            docs[short] = d
        d = docs[short]
        res = d['result']
        cards = res.get('faultZoomComparisons') or []
        card = cards[int(p['idx'])]
        p['card_criterion'] = card.get('criterion') or card.get('joint')
        p['card_tier'] = card.get('tier')

        if p['side'] == 'user':
            report = res['keypointReport']
            rep_idx = int(card['userFrameIdx'])
            p['report'] = 'keypointReport'
        else:
            rid = res.get('referenceMotionId') or d.get('referenceMotionId')
            if rid not in refs:
                refs[rid] = fa.get_reference_motion(rid)['referenceKeypointReport']
            report = refs[rid]
            rep_idx = int(card['refFrameIdx'])
            p['report'] = f'referenceKeypointReport:{rid}'
        p['centre_rep_idx'] = rep_idx
        p['report_frames'] = int(report.get('frames') or 0)
        p['report_fps'] = report.get('fps')
        xy = fz._kp_xy(report, rep_idx, p['joint'])
        p['stored_xy'] = list(xy) if xy else None
        p['stored_conf'] = fz._kp_conf(report, rep_idx, p['joint'])
        p['stored_frame_collapsed'] = bool(fz.is_collapsed_frame(report, rep_idx))
        # 원장 교차검증: 카드 rep 인덱스가 명부의 값과 정합한가 (산술이 아니라 대조)
        exp = int(p['roster_user_frame']) if p['side'] == 'user' else int(p['roster_ref_rep_idx'])
        p['ledger_consistent'] = (rep_idx == exp * 2)

    json.dump(rows, open(STORED, 'w'), ensure_ascii=False, indent=1)
    print(f'stored: {len(rows)} panels -> {STORED}')
    bad = [p for p in rows if not p['ledger_consistent']]
    print('ledger mismatches:', bad if bad else 'none')


# ── stage mp ────────────────────────────────────────────────────────────────
def stage_mp() -> None:
    sys.path.insert(0, '/Users/kimtaesung/Dev/SunityMotion/backend/shared/python')
    from sunity_shared.analysis.adapters.mediapipe_to_coco17 import MEDIAPIPE_33_TO_COCO17
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    rows = json.load(open(STORED))
    manifest = json.load(open(MANIFEST))

    wanted = sorted({p['joint'] for p in rows})
    for j in wanted:
        if j not in MEDIAPIPE_33_TO_COCO17:
            raise SystemExit(f'joint {j} not in repo MediaPipe map')

    opts = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=MODEL_TASK),
        running_mode=vision.RunningMode.IMAGE,   # 사전 기준 §2 — VIDEO 모드 금지
        num_poses=1,
        output_segmentation_masks=False,
    )
    landmarker = vision.PoseLandmarker.create_from_options(opts)

    out = {}
    files = set()
    for p in rows:
        key = f"{p['side']}:{p['doc']}"
        entry = manifest[key]['saved'][str(p['video_frame_idx'])]
        files.add((key, p['video_frame_idx'], entry['file'], entry['W'], entry['H']))

    for key, fidx, fn, W, H in sorted(files):
        img = mp.Image.create_from_file(os.path.join(FRAMES, fn))
        res = landmarker.detect(img)
        rec = {'file': fn, 'W': W, 'H': H, 'n_poses': len(res.pose_landmarks),
               'mp_version': mp.__version__, 'joints': {}}
        if res.pose_landmarks:
            lms = res.pose_landmarks[0]
            for j, mi in MEDIAPIPE_33_TO_COCO17.items():
                lm = lms[mi]
                rec['joints'][j] = {'x': float(lm.x), 'y': float(lm.y), 'z': float(lm.z),
                                    'visibility': float(lm.visibility),
                                    'presence': float(lm.presence)}
        out[f'{key}#{fidx}'] = rec
        print(key, fidx, fn, 'poses=', rec['n_poses'], flush=True)
    landmarker.close()
    json.dump(out, open(MPOUT, 'w'), ensure_ascii=False, indent=1)
    print(f'mp: {len(out)} frames -> {MPOUT}')


# ── stage join ──────────────────────────────────────────────────────────────
def stage_join() -> None:
    rows = json.load(open(STORED))
    manifest = json.load(open(MANIFEST))
    mpres = json.load(open(MPOUT))

    results = []
    for p in rows:
        key = f"{p['side']}:{p['doc']}"
        ent = manifest[key]['saved'][str(p['video_frame_idx'])]
        rec = mpres[f"{key}#{p['video_frame_idx']}"]
        W, H = int(rec['W']), int(rec['H'])
        thr = THRESH_K * p['card_frac']
        r = {
            'doc': p['doc'], 'idx': p['idx'], 'side': p['side'], 'joint': p['joint'],
            'crit': p['crit'], 'role': p['role'], 'roster_final': p['roster_final'],
            'frame_idx': p['video_frame_idx'], 'centre_rep_idx': p['centre_rep_idx'],
            'report': p['report'], 'report_frames': p['report_frames'],
            'video_path': manifest[key]['video_path'],
            'video_bytes': manifest[key]['video_bytes'],
            'video_n_frames_9fps': manifest[key]['n_frames_9fps'],
            'frame_png': ent['file'], 'W': W, 'H': H,
            'stored_xy': p['stored_xy'], 'stored_conf': p['stored_conf'],
            'stored_frame_collapsed': p['stored_frame_collapsed'],
            'card_frac': p['card_frac'], 'threshold': round(thr, 6),
            'threshold_px_minWH': round(thr * min(W, H), 2),
            'mp_n_poses': rec['n_poses'],
        }
        jr = rec['joints'].get(p['joint'])
        if p['stored_xy'] is None:
            r.update({'mp_xy': None, 'mp_visibility': None, 'mp_presence': None,
                      'd_norm': None, 'd_px': None, 'verdict': 'INCONCLUSIVE',
                      'reason': 'stored coordinate missing'})
        elif jr is None:
            r.update({'mp_xy': None, 'mp_visibility': None, 'mp_presence': None,
                      'd_norm': None, 'd_px': None, 'verdict': 'INCONCLUSIVE',
                      'reason': 'no detection'})
        else:
            dpx = (jr['x'] - p['stored_xy'][0]) * W
            dpy = (jr['y'] - p['stored_xy'][1]) * H
            dpix = math.hypot(dpx, dpy)
            d = dpix / min(W, H)
            if jr['visibility'] < VIS_MIN:
                v, why = 'INCONCLUSIVE', f"visibility {jr['visibility']:.3f} < {VIS_MIN}"
            elif d <= thr:
                v, why = 'AGREE', ''
            else:
                v, why = 'DISAGREE', ''
            r.update({'mp_xy': [jr['x'], jr['y']], 'mp_visibility': jr['visibility'],
                      'mp_presence': jr['presence'], 'd_norm': round(d, 6),
                      'd_px': round(dpix, 2), 'dpx': round(dpx, 2), 'dpy': round(dpy, 2),
                      'verdict': v, 'reason': why})
        results.append(r)

    def tally(role):
        sub = [x for x in results if x['role'] == role]
        return {'n': len(sub),
                'AGREE': sum(1 for x in sub if x['verdict'] == 'AGREE'),
                'DISAGREE': sum(1 for x in sub if x['verdict'] == 'DISAGREE'),
                'INCONCLUSIVE': sum(1 for x in sub if x['verdict'] == 'INCONCLUSIVE')}

    t, c = tally('target'), tally('control')

    # 사전 기준 §2 "A 단독 판정" — 순서 고정 (대조군 조항이 반증자)
    if c['DISAGREE'] > 2:
        verdict = 'INCONCLUSIVE'
        why = (f"대조군 {c['n']}면 중 DISAGREE {c['DISAGREE']} > 2 — "
               'MediaPipe 는 심판 자격이 없다 (§2 반증자 조항).')
    elif t['DISAGREE'] >= 3:
        verdict = '학습 필요'
        why = f"대상 5면 중 DISAGREE {t['DISAGREE']} >= 3, 대조군 DISAGREE {c['DISAGREE']} <= 2."
    elif t['AGREE'] >= 3 and t['DISAGREE'] == 0:
        verdict = '학습 불필요'
        why = f"대상 5면 중 AGREE {t['AGREE']} >= 3 이고 DISAGREE 0."
    else:
        verdict = 'INCONCLUSIVE'
        why = (f"대상 AGREE {t['AGREE']} / DISAGREE {t['DISAGREE']} / "
               f"INCONCLUSIVE {t['INCONCLUSIVE']} — §2 어느 가지에도 안 맞는다.")

    pred_held = (t['AGREE'] >= 4 and t['DISAGREE'] == 0)
    doc = {
        'measurement': 'A — independent second model cross-check',
        'preregistration': 'STEP0-PREREGISTRATION.md §2 (committed bdaebd1c, before measurement)',
        'model': {'name': 'MediaPipe Pose / BlazePose HEAVY',
                  'mediapipe': (json.load(open(MPOUT)) or {}) and
                               next(iter(json.load(open(MPOUT)).values()))['mp_version'],
                  'running_mode': 'IMAGE', 'num_poses': 1,
                  'model_asset': MODEL_TASK, 'model_asset_bytes': os.path.getsize(MODEL_TASK)},
        'extractor': 'sunity_shared.analysis.frame_extractor.FfmpegFrameExtractor(target_fps=9.0, max_side=640)',
        'distance_rule': 'dpx=(x_mp-x_stored)*W; dpy=(y_mp-y_stored)*H; d=hypot(dpx,dpy)/min(W,H)',
        'threshold_rule': '0.25 * card_frac (normalised by the short side)',
        'visibility_min': VIS_MIN,
        'targets': t, 'controls': c,
        'measurement_verdict': verdict, 'verdict_reason': why,
        'prediction': '>=4 of 5 AGREE and 0 DISAGREE',
        'prediction_held': pred_held,
        'panels': results,
    }
    json.dump(doc, open(FINAL, 'w'), ensure_ascii=False, indent=1)

    for x in results:
        print(f"{x['role'][:4]:4} {x['doc']}[{x['idx']}] {x['side']:4} {x['joint']:15} "
              f"f={x['frame_idx']:4} d={x['d_norm']} thr={x['threshold']} "
              f"vis={x['mp_visibility']} -> {x['verdict']} {x['reason']}")
    print('\ntargets ', t)
    print('controls', c)
    print('VERDICT :', verdict, '|', why)
    print('prediction (>=4 AGREE, 0 DISAGREE) held:', pred_held)
    print('->', FINAL)


if __name__ == '__main__':
    {'stored': stage_stored, 'mp': stage_mp, 'join': stage_join}[sys.argv[1]]()

"""프레임 원장 교차검증 — 명부의 ref_video_idx 를 fault_zoom.ref_display_frame_index 로 재현.
(재계산으로 대체하는 것이 아니라, 명부 값이 그 함수를 통과한 값임을 확인하는 대조.)"""
import sys, json, os
sys.path.insert(0,'/Users/kimtaesung/Dev/SunityMotion/backend/shared/python')
from sunity_shared import firestore_admin as fa
from sunity_shared.analysis import fault_zoom as fz
EV='/Users/kimtaesung/Dev/SunityMotion/.planning/quick/260907-itk-step-0/evidence'
man=json.load(open(os.path.join(EV,'frames_manifest_a.json')))
rows=json.load(open(os.path.join(EV,'stored_panels_a.json')))
REF={'4e232c4a':'ref-pdshape','a559705f':'ref-climb','d213622a':'ref-elbow-twist-sister',
     '5ae210fa':'ref-power-spin','21b1b7ed':'ref-peter-pan'}
out=[]
cache={}
for p in rows:
    if p['side']!='ref': continue
    rid=REF[p['doc']]
    if rid not in cache: cache[rid]=fa.get_reference_motion(rid)
    m=cache[rid]
    n=man[f"ref:{p['doc']}"]['n_frames_9fps']
    got=fz.ref_display_frame_index(int(p['roster_ref_rep_idx']), n,
                                   int(m['anglesFrames']), float(m['referenceKeypointReport']['fps']))
    out.append({'doc':p['doc'],'idx':p['idx'],'joint':p['joint'],'ref_rep_idx':p['roster_ref_rep_idx'],
                'ref_video_n':n,'rep_frames':m['anglesFrames'],'rep_fps':m['referenceKeypointReport']['fps'],
                'recomputed':got,'roster':p['roster_ref_video_idx'],'match':got==p['roster_ref_video_idx']})
    # 함정 대조: round(videoSec*9.0) 로 하면 얼마가 나오는가
json.dump(out,open(os.path.join(EV,'ledger_check_a.json'),'w'),ensure_ascii=False,indent=1)
for o in out: print(o)
print('all match:', all(o['match'] for o in out))

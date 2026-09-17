import sys
sys.path.insert(0, 'backend/shared/python'); sys.path.insert(0, 'backend/scripts')
import e2e_app_path  # noqa: F401
from sunity_shared import firestore_admin
IDS = ["ref-climb","ref-combo","ref-elbow-twist-sister","ref-foxtop","ref-foxtop-split",
       "ref-invert","ref-kip-up","ref-pdshape","ref-peter-pan","ref-power-spin","ref-sideway-spin"]
print(f"{'기준':24s}{'pipelineVer':>12s}{'프레임':>7s}{'refKR':>10s}{'kpReport':>10s}{'j3d':>7s}{'판정':>7s}")
ok = True
import logging; logging.disable(logging.INFO)
for mid in IDS:
    r = firestore_admin.get_reference_motion(mid) or {}
    rk, kr = r.get("referenceKeypointReport") or {}, r.get("keypointReport") or {}
    good = (r.get("pipelineVersion") == "rot180_v1" and rk.get("frames") == r.get("anglesFrames")
            and kr.get("frames") == r.get("anglesFrames") and bool(r.get("joints3d")))
    ok &= good
    print(f"{mid:24s}{str(r.get('pipelineVersion')):>12s}{str(r.get('anglesFrames')):>7s}"
          f"{str(rk.get('frames')):>10s}{str(kr.get('frames')):>10s}"
          f"{('있음' if r.get('joints3d') else '없음'):>7s}{('OK' if good else '★'):>7s}")
print("\n11/11 정합 — 각도·두 보고서·좌표가 같은 프레임 공간" if ok else "\n★ 불일치 있음")

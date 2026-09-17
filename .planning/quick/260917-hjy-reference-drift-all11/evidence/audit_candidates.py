import json, sys
sys.path.insert(0, 'backend/scripts')
import e2e_app_path as e2e
db = e2e.firestore_client()
IDS = ["ref-climb","ref-combo","ref-elbow-twist-sister","ref-foxtop","ref-foxtop-split",
       "ref-invert","ref-kip-up","ref-pdshape","ref-peter-pan","ref-power-spin","ref-sideway-spin"]
NEED = ["angles","joints3d","keypointReport","meanAngles","techniqueProfile",
        "bodyNormalizationProfile","forceDirectionPattern","bodyComparisonSourcePose","captureViews"]
print(f"{'기준':24s}{'필드':>5s}{'필수 결손':>10s}{'refKR':>8s}{'프레임':>7s}{'백필':>16s}")
ok = True
for mid in IDS:
    d = db.document(f"reference/{mid}/versions/rot180_v1").get().to_dict() or {}
    miss = [k for k in NEED if not d.get(k)]
    if miss: ok = False
    rk = "있음" if d.get("referenceKeypointReport") else "생략"
    print(f"{mid:24s}{len(d):5d}{(','.join(miss) or '없음'):>10s}{rk:>8s}{str(d.get('anglesFrames')):>7s}{str(d.get('downstreamBackfillVersion')):>16s}")
print("\n전원 완비" if ok else "\n★결손 있음")

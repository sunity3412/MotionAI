"""vj1 오프라인 게이트 — 운영 함수(_measured_phrase_variants)를 저장 doc 10편 + 기준 5편으로 재구성.
학생 keypointReport = 저장 18fps 판의 짝수 프레임(= 파이프라인 keypoint_report_raw 9fps 판).
constant_joints = 운영과 같은 판정(창 상수 표본이 있는 관절 중 Gemini pointed 가 아닌 것) — 저장 doc 에 seed_audit 이 없어
                  각 record 의 measuredValue 가 창 상수와 같은지로 대조해 '상수 경로가 쟀다'를 확인한다."""
import importlib.util, json, pathlib, sys, logging
import numpy as np
REPO = pathlib.Path("/Users/kimtaesung/Dev/SunityMotion")
sys.path.insert(0, str(REPO / "backend/shared/python")); sys.path.insert(0, str(REPO / "backend"))
spec = importlib.util.spec_from_file_location("mra", REPO / "backend/scripts/measure_reference_axis.py")
mra = importlib.util.module_from_spec(spec); spec.loader.exec_module(mra)
app = mra.app
from sunity_shared import firestore_admin as fa, models
from sunity_shared.analysis import hold_height as hh
H = pathlib.Path(__file__).parent
RUNS = [l.split() for l in """jxEGDQNZ6sYIA6SA1VZOPIJdAv02 4541a570db20407b87d6c6225fa9d217 ref-power-spin correct
iidjGKz7E6NpSYq2bGGqWqTpa9H2 c4ebed20573a41ee813b6a7f86854edd ref-power-spin fault
GWRGgPsaQgd9WbhTsSbBNVCKTPI3 e62645353ff740ee85529a7e5f2c8849 ref-kip-up correct
TbXjwbLpCtMjcNcUONfT6TbhJ6m2 dacc44676451478987df0704ba021650 ref-kip-up fault
eOUk0QoZ9qZbppC3ExvXCNuqXeP2 240e265e604e4657ac79fe5cd3647de2 ref-climb correct
ku1d1pvfdGebQK8cyb4P1DxahDb2 1d00cc6051b741b8ba0fbc456def74a8 ref-climb fault
6sm398BNaGdulAaEC9u418hpvQ02 9a35ca8ae86742c2adbe17d98e3ea420 ref-peter-pan correct
3KWLGvMir4ep9KwHl9gzOOOccmh2 29b4749721ce45698e87ecd832fb7fc9 ref-peter-pan fault
Jghqo8gJICdgL5RUWXVJZHXjppo1 d50cf45716d340b88d7ba36f80712ca9 ref-pdshape correct
SG7HL1IugjcrpJKFHeOTTr8tSjv2 8aad6846ef114fcfb2be6a01d32babdb ref-pdshape fault""".splitlines()]
cache = H / "gate10_cache.json"
data = json.loads(cache.read_text()) if cache.exists() else {"docs": {}, "refs": {}}
for uid, aid, ref, intent in RUNS:
    if aid not in data["docs"]:
        data["docs"][aid] = fa.get_analysis(uid, aid)
    if ref not in data["refs"]:
        data["refs"][ref] = fa.get_reference_motion(ref)
cache.write_text(json.dumps(data, ensure_ascii=False, default=str))
logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger().handlers[0].setLevel(logging.WARNING)  # 로그는 아래 요약만
def raw(kr):
    J = len(kr["joints"]); T = kr["frames"]
    X = np.asarray(kr["data"], float).reshape(T, J, 2)[::2]; C = np.asarray(kr["confidence"], float).reshape(T, J)[::2]
    return {"joints": kr["joints"], "frames": X.shape[0], "data": X.reshape(-1).tolist(), "confidence": C.reshape(-1).tolist()}
print(f"{'동작':14s} {'판':7s} {'점수':>4s}  {'엉덩이':>7s} {'낮은발':>7s} {'그립손':>7s} {'손아래엉덩이':>9s}  1/3 전부 낮음  대체 문장")
for uid, aid, ref, intent in RUNS:
    d = data["docs"][aid]; rd = data["refs"][ref]
    A = np.asarray(d["angles"], float).reshape(-1, 8); R = np.asarray(rd["angles"], float).reshape(-1, 8)
    rwin = app._reference_exec_window(rd, app._reference_angles_fps(rd), len(R))
    dev, m = mra.deviate(A, rd)
    recs = d["result"]["deductionBreakdown"]["records"]
    uwin = app._student_window_from_match(m, *rwin) if rwin else None
    samp = app._window_constant_samples(A, R, uwin, rwin) if uwin else {}
    const = []
    for r in recs:
        c = r.get("criterion", "")
        if c.startswith("angle_vs_reference__"):
            jk = c.split("__", 1)[1]; j = list(mra.JOINT_KEYS).index(jk)
            if j in samp and abs(abs(samp[j][1] - samp[j][2]) - float(r["measuredValue"])) < 0.02:
                const.append(jk)
    stu_kp = raw(d["result"]["keypointReport"])
    out = app._measured_phrase_variants(
        mode=models.MODE_EXPERT, motion_id=ref, reference_motion_id=ref, result=d["result"], angles=A, reference_angles=R,
        reference_exec_window=rwin, reference_dtw_match=m, student_keypoint_report=stu_kp,
        reference_keypoint_report=rd["referenceKeypointReport"], constant_joints=const, uid=uid, analysis_id=aid,
        student_fps=(len(A) / float(d["result"]["keypointReport"]["frames"] / 2 / 9.9733) if False else 9.9733), reference_fps=app._reference_angles_fps(rd))
    h = hh.hold_window_heights(stu_kp, rd["referenceKeypointReport"], uwin, rwin) if uwin else None
    if h:
        low_all = all(s - r < -hh.NOISE_BODY_LENGTH for s, r in h["hip"]["thirds"]) and all(s - r < -hh.NOISE_BODY_LENGTH for s, r in h["lowFoot"]["thirds"])
        print(f"{ref:14s} {intent:7s} {d['result']['overallScore']:4d}  {h['hip']['diff']:+7.3f} {h['lowFoot']['diff']:+7.3f} {h['grip']['diff']:+7.3f} {h['hipBelowHand']['diff']:+9.3f}  {str(low_all):12s}  {list(out) or '-'}")
    else:
        print(f"{ref:14s} {intent:7s} {d['result']['overallScore']:4d}  높이 못 잼(None) — 창 {uwin}/{rwin}  대체 {list(out) or '-'}")
    if out:
        for k, v in out.items():
            print(f"     pattern={v['pattern']} atFrameIdx={v['atFrameIdx']} atVideoSec={v['atVideoSec']:.3f} atRefVideoSec={v['atRefVideoSec']:.3f}")
            for slot, text in v["slots"].items():
                print(f"     {slot}: {text}")

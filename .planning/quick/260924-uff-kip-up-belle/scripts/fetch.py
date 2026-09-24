"""읽기 전용 — kip-up 실수 doc + 기준 doc 1건씩 JSON 으로 저장 (Firestore 읽기 2회)."""
import json, sys
from pathlib import Path
B = Path("/Users/kimtaesung/Dev/SunityMotion/backend")
sys.path.insert(0, str(B / "shared" / "python")); sys.path.insert(0, str(B))
from sunity_shared import firestore_admin as fa
out = Path(__file__).parent
doc = fa.get_analysis("TbXjwbLpCtMjcNcUONfT6TbhJ6m2", "dacc44676451478987df0704ba021650")
(out / "fault_doc.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1, default=str))
ref = fa.get_reference_motion("ref-kip-up")
(out / "ref_doc.json").write_text(json.dumps(ref, ensure_ascii=False, indent=1, default=str))
print("fault keys:", sorted(doc.keys()) if doc else None)
print("ref keys:", sorted(ref.keys()) if ref else None)

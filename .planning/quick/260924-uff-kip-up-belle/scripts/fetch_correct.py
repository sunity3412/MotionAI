import json, sys
from pathlib import Path
B = Path("/Users/kimtaesung/Dev/SunityMotion/backend")
sys.path.insert(0, str(B / "shared" / "python")); sys.path.insert(0, str(B))
from sunity_shared import firestore_admin as fa
doc = fa.get_analysis("GWRGgPsaQgd9WbhTsSbBNVCKTPI3", "e62645353ff740ee85529a7e5f2c8849")
Path(__file__).with_name("correct_doc.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1, default=str))
print(doc["result"]["overallScore"], doc["result"]["analysisVersion"], doc["anglesFrames"])

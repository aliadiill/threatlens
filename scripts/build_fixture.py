import json
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from scripts.generate_events import events
from backend.domain import normalize, detect
items = []
for event in events():
    incident = detect(normalize(event))
    if incident:
        incident["updatedAt"] = incident["createdAt"]
        incident["timeline"] = [{"at": incident["createdAt"], "kind": "DETECTED", "actor": "demo-detector", "text": incident["response"]}]
        items.append(incident)
(root / "src" / "fixtures.json").write_text(json.dumps(items, indent=2), encoding="utf-8")
print(f"Generated {len(items)} reproducible incidents from 12 events (two benign)")

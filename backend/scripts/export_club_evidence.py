"""Read-only export of stored measurements, with provenance for slides."""
import sqlite3, json, sys, csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
OUT=ROOT/'artifacts/bradford_review'
from app.pipeline.location_breakdown import compute_location_ai_percentages, compute_zone_detail
c=sqlite3.connect(f'file:{ROOT / "backend/data/app.db"}?mode=ro',uri=True)
c.row_factory=sqlite3.Row
locations=[dict(r) for r in c.execute('select * from location_configs order by order_index')]
print('LOCATIONS',json.dumps(locations,indent=2))
rows=c.execute('select id,video_name,video_duration_seconds,result_json,facts_json from analyses order by analyzed_at desc limit 4').fetchall()
evidence={'locations':locations,'analyses':[]}
for r in rows:
    d=dict(r); result=json.loads(d.pop('result_json')); facts=json.loads(d.pop('facts_json') or '[]')
    d.update(result=result,fact_count=len(facts))
    enabled=['size','position','clarity','obb','durationWeight']
    mapping={l['id']:l['anchor_id'] for l in locations if l['brand_key']}
    d['location_ai']=compute_location_ai_percentages(facts,enabled,mapping)
    d['zone_detail']=compute_zone_detail(facts,enabled)
    evidence['analyses'].append(d)
    print(d['video_name'],d['id'],d['fact_count'],list(result))
(OUT/'stored_evidence.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')

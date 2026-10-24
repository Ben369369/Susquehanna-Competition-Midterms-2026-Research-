"""Build a reviewable case register and model snapshot from current evidence."""
import csv
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import build

ROOT=Path(__file__).resolve().parents[1]
d=build()
(ROOT/'research/forecast.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
lines=['# Challenge case register','',f'Evidence as of {d["as_of"]}. Model {d["version"]}. Probabilities are provisional; rating baselines are uncalibrated analyst conversions.','', '| Contest | Basis | D estimate | Outside rating | Research next step |','|---|---|---:|---|---|']
with (ROOT/'research/predictions.csv').open('w',newline='',encoding='utf-8') as f:
 writer=csv.writer(f);writer.writerow(['race_id','contest','party','pasted_yes','provisional_probability','difference','basis','as_of','model_version'])
 for r in d['races']:
  p=f'{100*r["model"]["dem_probability"]:.1f}%' if r['model'] else 'Withheld'
  note=r.get('research_note') or ('Build candidate-level and settlement mapping.' if 'Independent' in r['quotes'] else 'Validate complete seat and caucus mapping.' if r['office']=='Control' else 'Add independent polling; inspect candidate field and actual ask.' if r['model'] and r['model']['status']=='Provisional polling model' else 'Replace rating baseline with local evidence; validate 2026 geography and candidate field.')
  lines.append(f'| {r["title"]} | {r["status"]} | {p} | {r.get("rating",{}).get("label","—")} | {note} |')
  for party,q in r['quotes'].items():
   e=r['edges'].get(party,{})
   writer.writerow([r['id'],r['title'],party,q['yes'],e.get('probability',''),e.get('difference',''),r['status'],d['as_of'],d['version']])
(ROOT/'research/CASES.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(f'Exported {len(d["races"])} cases and {d["coverage"]["contracts"]} contracts.')

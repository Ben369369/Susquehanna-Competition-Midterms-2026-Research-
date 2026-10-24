"""Validate and import reviewed poll CSV; updates remain separate from seeded evidence."""
import argparse
import csv
import json
import math
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def read_polls(path,seed):
    known={r['id'] for r in seed['races']}
    observations=[];sources=[];seen=set()
    with open(path,encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            required=['id','race_id','pollster','end','published','margin','n','url']
            if any(not row.get(k) for k in required):raise ValueError('Required columns: '+', '.join(required))
            if row['id'] in seen:raise ValueError('Duplicate observation ID: '+row['id'])
            seen.add(row['id'])
            if row['race_id'] not in known:raise ValueError('Unknown race_id: '+row['race_id'])
            end=date.fromisoformat(row['end']);published=date.fromisoformat(row['published'])
            if published<end or published>date.today():raise ValueError('Invalid publication / fieldwork dates')
            n=int(row['n']);margin=float(row['margin'])
            if n<50 or n>100000 or not math.isfinite(margin) or abs(margin)>100:raise ValueError('Invalid sample or margin')
            if not row['url'].startswith('https://'):raise ValueError('Source must be an HTTPS URL')
            source_id='import-'+row['id']
            observations.append(dict(id=row['id'],race_id=row['race_id'],pollster=row['pollster'],end=row['end'],published=row['published'],margin=margin,n=n,kind='poll',source_id=source_id,note=row.get('note','Reviewed user CSV import.')))
            sources.append(dict(id=source_id,title=row['pollster']+' / '+row['race_id'],url=row['url'],type='Imported primary poll',published=row['published'],note=row.get('note','Reviewed user CSV import.')))
    if not observations:raise ValueError('No poll rows')
    return observations,sources

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('csv');args=parser.parse_args()
    seed=json.loads((ROOT/'data/seed.json').read_text(encoding='utf-8'))
    observations,sources=read_polls(args.csv,seed)
    target=ROOT/'data/custom-polls.json'
    old=json.loads(target.read_text()) if target.exists() else {'observations':[],'sources':[]}
    existing={p['id'] for p in seed['observations']+old['observations']}
    if existing.intersection(p['id'] for p in observations):raise SystemExit('IDs already exist. Preserve history and use distinct observation IDs.')
    target.write_text(json.dumps({'observations':old['observations']+observations,'sources':old['sources']+sources},indent=2),encoding='utf-8')
    print(f'Imported {len(observations)} observations. Reload portal and save a new snapshot.')

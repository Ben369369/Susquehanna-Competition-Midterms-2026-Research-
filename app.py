"""Local election research portal: python app.py (Python standard library only)."""
import csv
import io
import json
import math
import random
import sqlite3
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from model import VERSION, forecast

ROOT=Path(__file__).resolve().parent
DB=ROOT/'data/research.sqlite3'

def connect():
    con=sqlite3.connect(DB)
    con.execute('CREATE TABLE IF NOT EXISTS snapshots (id INTEGER PRIMARY KEY, created_at TEXT, as_of TEXT, version TEXT, payload TEXT)')
    return con

def build(shift=0, error_scale=1, as_of=None):
    seed=json.loads((ROOT/'data/seed.json').read_text(encoding='utf-8'))
    custom=ROOT/'data/custom-polls.json'
    if custom.exists():
        extra=json.loads(custom.read_text(encoding='utf-8'))
        seed['observations']+=extra['observations'];seed['sources']+=extra['sources']
        seed['as_of']=max([seed['as_of']]+[p['published'] for p in extra['observations']])
    as_of=as_of or seed['as_of']
    races=forecast(seed['races'],seed['observations'],as_of,shift,error_scale)
    return {**seed,'as_of':as_of,'races':races,'version':VERSION,'scenario':{'shift':shift,'error_scale':error_scale},
            'coverage':{'races':len(races),'contracts':sum(len(r['quotes']) for r in races),
                        'modeled':sum(bool(r['model']) for r in races),
                        'polled':sum(bool(r['model']) and r['model']['status']=='Provisional polling model' for r in races),
                        'rated':sum(bool(r['model']) and r['model']['status']=='Rating-derived baseline' for r in races),
                        'missing_senate':['Ohio omitted from paste; present in outside ratings universe'],
                        'chamber_status':'Unavailable pending independent-winner, caucus, special-seat and settlement mapping. Full ratings universe archived; control prices remain snapshots.'}}

def save_snapshot(payload):
    with connect() as con:
        con.execute('INSERT INTO snapshots(created_at,as_of,version,payload) VALUES(?,?,?,?)',
                    (datetime.now(timezone.utc).isoformat(),payload['as_of'],VERSION,json.dumps(payload)))

def simulate(payload, count=10000):
    races=[r for r in payload['races'] if r['model']]
    rng=random.Random(20260929)
    hist=[0]*(len(races)+1)
    for _ in range(count):
        national=rng.gauss(0,1)
        states={r.get('state_code',r['location']):rng.gauss(0,1) for r in races}
        wins=0
        for race in races:
            m=race['model']
            wins += m['mean_margin']+national*m['national_sd']+states[race.get('state_code',race['location'])]*m['state_sd']+rng.gauss(0,m['local_sd'])>0
        hist[wins]+=1
    return {'count':count,'modeled_races':len(races),'histogram':hist,
            'label':'Democratic wins among modeled races only (mixed offices); not chamber control',
            'seed':20260929}

class Handler(BaseHTTPRequestHandler):
    def send(self, body, code=200, mime='application/json'):
        if not isinstance(body,bytes): body=json.dumps(body,allow_nan=False).encode()
        self.send_response(code)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed=urlparse(self.path)
        query=parse_qs(parsed.query)
        try:
            shift=float(query.get('shift',['0'])[0]); scale=float(query.get('scale',['1'])[0])
            if not math.isfinite(shift) or not math.isfinite(scale) or not -10<=shift<=10 or not .5<=scale<=2:
                raise ValueError('Scenario outside supported range')
            if parsed.path in ('/api/forecast','/api/simulate','/api/export'):
                payload=build(shift,scale)
                if parsed.path=='/api/forecast': return self.send(payload)
                if parsed.path=='/api/simulate': return self.send(simulate(payload))
                buf=io.StringIO(); writer=csv.writer(buf)
                writer.writerow(['race','party','snapshot_yes','model_probability','difference','status','as_of','model_version','scenario_shift','error_scale'])
                for r in payload['races']:
                    for party,q in r['quotes'].items():
                        edge=r['edges'].get(party,{})
                        writer.writerow([r['title'],party,q['yes'],edge.get('probability',''),edge.get('difference',''),r['status'],payload['as_of'],VERSION,shift,scale])
                return self.send(buf.getvalue().encode(),mime='text/csv; charset=utf-8')
            if parsed.path=='/api/history':
                with connect() as con:
                    rows=con.execute('SELECT id,created_at,as_of,version,payload FROM snapshots ORDER BY id DESC LIMIT 100').fetchall()
                return self.send([{'id':i,'created_at':t,'as_of':a,'version':v,'predictions':{r['id']:r['model']['dem_probability'] for r in json.loads(p)['races'] if r['model']}} for i,t,a,v,p in rows])
            paths={'/':('index.html','text/html'),'/app.js':('app.js','text/javascript'),'/style.css':('style.css','text/css')}
            if parsed.path in paths:
                name,mime=paths[parsed.path]
                return self.send((ROOT/'static'/name).read_bytes(),mime=mime+'; charset=utf-8')
            return self.send({'error':'Not found'},404)
        except (ValueError,KeyError) as exc:
            return self.send({'error':str(exc)},400)

    def do_POST(self):
        # Same-origin local mutation only; no credentials, arbitrary URLs, or orders.
        origin=self.headers.get('Origin')
        if origin and origin != 'http://'+self.headers.get('Host',''):
            return self.send({'error':'Cross-origin writes denied'},403)
        if self.path!='/api/snapshot': return self.send({'error':'Not found'},404)
        save_snapshot(build())
        return self.send({'saved':True})

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    with connect() as con:
        empty=con.execute('SELECT count(*) FROM snapshots').fetchone()[0]==0
    if empty: save_snapshot(build())
    print(f'Susquehanna Research Desk: http://127.0.0.1:{args.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()

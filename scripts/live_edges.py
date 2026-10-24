"""Compare model probabilities with executable orderbook prices (read-only).

PowerShell: $env:SIG_API_KEY='...'; python scripts/sync_markets.py; python scripts/live_edges.py
Uses the newest archive from sync_markets.py to map market IDs, then fetches live orderbooks
for polled races only. Buying YES costs the best ask; buying NO costs 1 - best bid.
Never submits orders. Without a key, falls back to archived last-trade prices.
"""
import csv
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import build
from model import MIN_EDGE, tradability
from sync_markets import get

def live_markets():
    files = sorted(glob.glob(str(ROOT/'data/market-archives/*.json')))
    if not files: raise SystemExit('Run scripts/sync_markets.py first.')
    archive = json.loads(Path(files[-1]).read_text(encoding='utf-8'))
    markets = {}
    for page in archive['pages']:
        for m in page['data']:
            t = re.match(r'Will the (\w+) Party win the ([^?]+)\?', m['title'])
            if t and m['status'] == 'open':
                markets[(re.sub(r'[^a-z0-9]+', '-', t[2].lower()).strip('-'), t[1])] = m
    return archive, markets

def book(market, key, tournament):
    if not key: return None, None, market['exchanges'][0]['latestPrice']
    data = get(f"/markets/{market['id']}/orderbook?tournamentId={tournament}&depth=5", key)
    ex = next(e for e in data['exchanges'] if e['option'] == 'YES')
    bid = max((l['price'] for l in ex['bids']), default=None)
    ask = min((l['price'] for l in ex['asks']), default=None)
    return bid, ask, market['exchanges'][0]['latestPrice']

if __name__ == '__main__':
    key = os.getenv('SIG_API_KEY')
    archive, markets = live_markets()
    base, wide = build(), build(error_scale=1.3)
    wide_p = {r['id']: r['model'] for r in wide['races']}
    rows = []
    for race in base['races']:
        m = race['model']
        if not m or m['status'] != 'Provisional polling model': continue
        for party in race['quotes']:
            market = markets.get((race['id'], party))
            if not market: continue
            p = m['dem_probability'] if party == 'Democratic' else 1-m['dem_probability']
            pw = wide_p[race['id']]['dem_probability'] if party == 'Democratic' else 1-wide_p[race['id']]['dem_probability']
            bid, ask, last = book(market, key, archive['tournament_id'])
            yes_cost = ask if ask is not None else last
            no_cost = 1-bid if bid is not None else 1-last
            rows.append(dict(race=race['title'], party=party, market_id=market['id'], model=round(p, 3), model_wide=round(pw, 3),
                             bid=bid, ask=ask, last=last, buy_yes_edge=round(min(p, pw)-yes_cost, 3),
                             buy_no_edge=round(min(1-p, 1-pw)-no_cost, 3),
                             evidence=tradability(m, race['observations']) or 'ok'))
    rows.sort(key=lambda r: -max(r['buy_yes_edge'], r['buy_no_edge']))
    print(f"{'race':24}{'party':11}{'model':>6}{'wide':>6}{'bid':>6}{'ask':>6}  best action (edge uses the more cautious model)")
    for r in rows:
        side, edge = ('BUY YES', r['buy_yes_edge']) if r['buy_yes_edge'] >= r['buy_no_edge'] else ('BUY NO', r['buy_no_edge'])
        fmt = lambda x: '     -' if x is None else f'{x:6.2f}'
        flag = f"  [{r['evidence']}]" if r['evidence'] != 'ok' else ('  <-- candidate' if edge >= MIN_EDGE else '')
        print(f"{r['race']:24}{r['party']:11}{r['model']:6.2f}{r['model_wide']:6.2f}{fmt(r['bid'])}{fmt(r['ask'])}  {side} {edge:+.2f}{flag}")
    out = ROOT/'data/market-archives'/('edges-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.csv')
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"\n{'Live orderbooks' if key else 'No key: archived last-trade prices'}; saved {out.name}. Model edges are uncalibrated; size accordingly.")

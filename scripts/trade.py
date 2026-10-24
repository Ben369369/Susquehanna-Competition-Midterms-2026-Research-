"""Semi-automatic order placement from a reviewed plan. Dry run unless --execute.

PowerShell:
  $env:SIG_API_KEY='read-key'; python scripts/sync_markets.py      # refresh market map
  python scripts/trade.py                                           # dry run: shows what it would do
  $env:SIG_TRADE_KEY='trade-key'; python scripts/trade.py --execute # asks y/n per order

Guardrails: never pays above a plan item's max_price; skips markets that moved past it;
budgets are TOTAL cost per market including existing positions; keeps the cash reserve;
requires a minimum model edge at the order price; limit orders only, expiring after
--expire-hours; deterministic idempotency keys so a retried run cannot double-submit.
"""
import argparse
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'scripts'))
from app import build
from live_edges import live_markets
from sync_markets import BASE, get

TICK = .005

def floor_tick(price):
    return round(math.floor(price/TICK+1e-9)*TICK, 3)

def model_probs():
    base, wide = build(), build(error_scale=1.3)
    out = {}
    for b, w in zip(base['races'], wide['races']):
        if b['model'] and b['model']['status'] == 'Provisional polling model':
            out[b['id']] = min(b['model']['dem_probability'], w['model']['dem_probability']), max(b['model']['dem_probability'], w['model']['dem_probability'])
    return out

def cautious(probs, race_id, party, side):
    """Least favourable model probability that the bought side wins."""
    lo, hi = probs[race_id]
    win_lo, win_hi = (lo, hi) if party == 'Democratic' else (1-hi, 1-lo)
    return win_lo if side == 'yes' else 1-win_hi

def plan_orders(plan, markets, positions, open_orders, books, balance, probs):
    """Pure sizing logic: returns (orders, notes). books maps exchangeId -> (best_bid, best_ask) for YES."""
    orders, notes, cash = [], [], balance-plan['reserve']
    for item in plan['trades']:
        label = f"{item['race_id']} {item['party']} {item['side'].upper()}"
        market = markets.get((item['race_id'], item['party']))
        if not market: notes.append(f'SKIP {label}: market not found in archive'); continue
        exchange = market['exchanges'][0]['id']
        held = [p for p in positions if p['marketId'] == market['id'] and p['quantity']]
        sides = {lot['side'].lower() for p in held for lot in p.get('lots', [])} & {'yes', 'no'}
        if sides - {item['side']}: notes.append(f'SKIP {label}: you hold the opposite side; review manually'); continue
        spent = sum(abs(p['costBasis']) for p in held)
        resting = [o for o in open_orders if o['exchangeId'] == exchange]
        if resting: notes.append(f'SKIP {label}: open order already resting (id {resting[0]["id"]})'); continue
        need = item['budget']-spent
        if need < plan.get('min_order', 200): notes.append(f'DONE {label}: {spent:,.0f} of {item["budget"]:,} already invested'); continue
        bid, ask = books.get(exchange, (None, None))
        price = ask if item['side'] == 'yes' else (None if bid is None else 1-bid)
        if price is None: notes.append(f'SKIP {label}: no liquidity on the book'); continue
        if price > item['max_price']+1e-9: notes.append(f'SKIP {label}: price {price:.3f} above max {item["max_price"]:.3f}'); continue
        limit = floor_tick(min(price, item['max_price']))
        edge = cautious(probs, item['race_id'], item['party'], item['side'])-limit if item['race_id'] in probs else None
        if edge is None or edge < item.get('min_edge', plan['min_edge']):
            notes.append(f'SKIP {label}: model edge {"n/a" if edge is None else f"{edge:+.3f}"} below minimum'); continue
        spend = min(need, cash)
        quantity = int(spend/limit)
        if quantity < 1 or spend < plan.get('min_order', 200): notes.append(f'SKIP {label}: reserve of {plan["reserve"]:,} reached'); continue
        cash -= quantity*limit
        orders.append(dict(label=label, title=market['title'], exchangeId=exchange, side=item['side'], price=limit,
                           quantity=quantity, cost=round(quantity*limit, 2), edge=round(edge, 3), already=round(spent, 2)))
    return orders, notes

def stale_orders(plan, markets, open_orders):
    """Open orders priced above the plan's cap for that market, e.g. a mistyped 58% limit."""
    caps = {}
    for item in plan['trades']:
        m = markets.get((item['race_id'], item['party']))
        if m: caps[(m['exchanges'][0]['id'], item['side'])] = item['max_price']
    return [o for o in open_orders if o['action'] == 'buy' and o['priceLimit'] is not None
            and o['priceLimit'] > caps.get((o['exchangeId'], o['side']), 1)+1e-9]

def send(method, path, key, body=None):
    import urllib.error, urllib.request
    req = urllib.request.Request(BASE+path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={'Authorization': 'Bearer '+key, 'Accept': 'application/json', 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return json.load(r)
    except urllib.error.HTTPError as exc:
        try: err = json.load(exc).get('error', {})
        except ValueError: err = {}
        raise RuntimeError(f"HTTP {exc.code} {err.get('code', '')}: {err.get('message', '')}") from None

def confirm(prompt):
    return input(prompt+' [y/N] ').strip().lower() == 'y'

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', default=str(ROOT/'data/trade-plan.json'))
    parser.add_argument('--execute', action='store_true', help='place orders (asks y/n for each)')
    parser.add_argument('--expire-hours', type=float, default=12)
    args = parser.parse_args()
    read_key, trade_key = os.getenv('SIG_API_KEY'), os.getenv('SIG_TRADE_KEY')
    if not read_key and not trade_key: raise SystemExit('Set SIG_API_KEY (read) locally; SIG_TRADE_KEY only for --execute.')
    if args.execute and not trade_key: raise SystemExit('--execute needs SIG_TRADE_KEY (a key with the trade scope).')
    key = read_key or trade_key
    plan = json.loads(Path(args.plan).read_text(encoding='utf-8'))
    archive, markets = live_markets()
    tid = archive['tournament_id']
    tournament = next(t for t in get('/tournaments?limit=100', key)['data'] if t['id'] == tid)
    positions = get(f"/tournaments/{tournament['slug']}/portfolio/positions", key)['positions']
    open_orders = get(f'/orders?status=open&limit=200&tournamentId={tid}', key)['data']
    books = {}
    for item in plan['trades']:
        m = markets.get((item['race_id'], item['party']))
        if not m: continue
        ex = next(e for e in get(f"/markets/{m['id']}/orderbook?tournamentId={tid}&depth=5", key)['exchanges'] if e['option'] == 'YES')
        books[m['exchanges'][0]['id']] = (max((l['price'] for l in ex['bids']), default=None), min((l['price'] for l in ex['asks']), default=None))

    balance = tournament['myBalance']
    print(f"Balance {balance:,.2f} SUSQies · reserve {plan['reserve']:,} · {len(positions)} positions · {len(open_orders)} open orders")
    for o in stale_orders(plan, markets, open_orders):
        print(f"WARNING stale order {o['id']}: buy {o['side']} {o['quantity']:.0f} @ {o['priceLimit']} exceeds plan cap")
        if args.execute and confirm('  Cancel it?'):
            send('DELETE', f"/orders/{o['id']}", trade_key); print('  cancelled')
    orders, notes = plan_orders(plan, markets, positions, open_orders, books, balance, model_probs())
    for n in notes: print(n)
    for o in orders:
        print(f"ORDER {o['label']:38} buy {o['quantity']:>7,} @ {o['price']:.3f} = {o['cost']:>9,.2f}  edge {o['edge']:+.3f}  (held {o['already']:,.0f})")
    print(f"Total new spend {sum(o['cost'] for o in orders):,.2f}; cash after if all fill {balance-sum(o['cost'] for o in orders):,.2f}")
    if not args.execute:
        print('\nDry run only. Re-run with --execute and SIG_TRADE_KEY to place these.'); sys.exit()
    expires = (datetime.now(timezone.utc)+timedelta(hours=args.expire_hours)).isoformat().replace('+00:00', 'Z')
    day = datetime.now(timezone.utc).strftime('%Y%m%d')
    for o in orders:
        print(f"\n{o['title']}\n  BUY {o['side'].upper()} {o['quantity']:,} @ {o['price']:.3f} (cost up to {o['cost']:,.2f})")
        if not confirm('  Place this limit order?'): print('  skipped'); continue
        body = dict(exchangeId=o['exchangeId'], side=o['side'], action='buy', quantity=o['quantity'], price=o['price'], tournamentId=tid)
        body['idempotencyKey'] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()+day.encode()).hexdigest()[:40]
        body['expirationDate'] = expires
        r = send('POST', '/orders', trade_key, body)
        print(f"  filled {r.get('quantityTraded', 0):,.0f} @ {r.get('fillPrice')} · cost {r.get('totalCost', 0):,.2f} · "
              f"{'resting ' + format(r.get('remainingQuantity', 0), ',.0f') + ' until ' + expires if r.get('open') else 'complete'}")

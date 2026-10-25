"""Read-only official API archive. Requires a user-configured key and tournament UUID.

PowerShell: $env:SIG_API_KEY='...'; $env:SIG_TOURNAMENT_ID='...'
python scripts/sync_markets.py
Never prints a credential and never submits orders. Archives raw responses for review;
does not silently replace pasted quotes with potentially different contract contexts.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime,timezone
from pathlib import Path

BASE='https://sig.thesuper.market/api/v1'

def get(path,key):
    req=urllib.request.Request(BASE+path,headers={'Authorization':'Bearer '+key,'Accept':'application/json'})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code==429 and attempt<3:
                time.sleep(min(30,2**attempt*2));continue
            try:err=json.load(exc).get('error',{})
            except (ValueError,AttributeError):err={}
            code=err.get('code','')
            hint={'INVALID_API_KEY':'Key not recognised: paste the real key from Super Market account settings, not a placeholder.',
                  'API_KEY_EXPIRED':'Key has expired; create a new one.',
                  'INSUFFICIENT_SCOPES':f"Key is missing scope(s) {(err.get('details') or {}).get('missing','?')}: use a key with the read scope as SIG_API_KEY."
                  }.get(code,'Verify key access and tournament context.')
            raise RuntimeError(f'API returned HTTP {exc.code} {code}. {hint}') from None
    raise RuntimeError('Rate limit retry exhausted')

def sync(key,tournament):
    pages=[];cursor=None;seen=set()
    for _ in range(100):
        params={'limit':100,'tournamentId':tournament}
        if cursor:params['cursor']=cursor
        page=get('/markets?'+urllib.parse.urlencode(params),key)
        if not isinstance(page.get('data'),list):raise ValueError('Unexpected market response')
        pages.append(page)
        pagination=page.get('pagination',{})
        if not pagination.get('hasMore'):break
        cursor=pagination.get('nextCursor')
        if not cursor or cursor in seen:raise ValueError('Invalid pagination cursor')
        seen.add(cursor)
    else:raise ValueError('Pagination safety limit exceeded')
    now=datetime.now(timezone.utc)
    result={'retrieved_at':now.isoformat(),'tournament_id':tournament,'pages':pages}
    target=Path(__file__).resolve().parents[1]/'data'/'market-archives'
    target.mkdir(parents=True,exist_ok=True)
    file=target/(now.strftime('%Y%m%dT%H%M%SZ')+'.json')
    file.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(f'Archived {sum(len(p["data"]) for p in pages)} market records to {file.name}. Contract mapping requires review.')

def find_tournament(key):
    """Pick the caller's midterm tournament when SIG_TOURNAMENT_ID is unset."""
    mine=get('/tournaments?limit=100',key)['data']
    for t in mine:print(f"  {t['id']}  {t['slug']}  {t['name']}  ({t['status']}, balance {t.get('myBalance')})")
    matches=[t for t in mine if 'midterm' in (t['slug']+t['name']).lower()] or mine
    if len(matches)!=1:raise SystemExit('Could not pick one tournament; set SIG_TOURNAMENT_ID to an id listed above.')
    print('Using',matches[0]['name'])
    return matches[0]['id']

if __name__=='__main__':
    key=os.getenv('SIG_API_KEY');tournament=os.getenv('SIG_TOURNAMENT_ID')
    if not key or key.strip('.')=='':raise SystemExit('Set SIG_API_KEY locally to your real key. Do not paste keys into chat.')
    if tournament:
        try:uuid.UUID(tournament)
        except ValueError:
            print('Ignoring SIG_TOURNAMENT_ID: not a UUID (a leftover placeholder?). Auto-detecting instead.')
            tournament=None
    sync(key,tournament or find_tournament(key))

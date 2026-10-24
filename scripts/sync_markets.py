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
            raise RuntimeError(f'API returned HTTP {exc.code}; verify key access and tournament context.') from None
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

if __name__=='__main__':
    key=os.getenv('SIG_API_KEY');tournament=os.getenv('SIG_TOURNAMENT_ID')
    if not key or not tournament:raise SystemExit('Set SIG_API_KEY and SIG_TOURNAMENT_ID locally. Do not paste keys into chat.')
    sync(key,tournament)

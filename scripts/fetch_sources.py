"""Archive public source documents. No account access or order submission."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
URLS = {
    'platform-docs': 'https://sig.thesuper.market/api/v1/docs',
    'platform-openapi': 'https://sig.thesuper.market/api/v1/openapi.json',
    'emerson': 'https://emersoncollegepolling.com/',
    'silver': 'https://www.natesilver.net/p/nate-silver-2026-midterm-election-polls-model',
    'rules': 'https://predictionscup.com/rules/',
    'unh-nh': 'https://scholars.unh.edu/cgi/viewcontent.cgi?article=2004&context=survey_center_polls',
    'unh-vt': 'https://scholars.unh.edu/cgi/viewcontent.cgi?article=2005&context=survey_center_polls',
    'ratings-house': 'https://insideelections.com/wp-content/themes/inside-elections/cache/ratings_latest_house_year=2026_district=all_clean.json',
    'ratings-senate': 'https://insideelections.com/wp-content/themes/inside-elections/cache/ratings_latest_senate_year=2026_district=all_clean.json',
    'ratings-governor': 'https://insideelections.com/wp-content/themes/inside-elections/cache/ratings_latest_governor_year=2026_district=all_clean.json',
}
seed_path = ROOT / 'data' / 'seed.json'
if seed_path.exists():
    for source in json.loads(seed_path.read_text(encoding='utf-8'))['sources']:
        if source['type'] == 'Primary poll':
            URLS[source['id']] = source['url']

def fetch(item):
    name, url = item
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ElectionResearch/0.1'})
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read(8_000_000)
        path = ROOT / 'data' / 'raw' / (name + '.txt')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        digest = hashlib.sha256(body).hexdigest()
        archive = ROOT / 'data' / 'source-archives' / (name + '-' + digest[:16] + '.txt')
        archive.parent.mkdir(parents=True, exist_ok=True)
        if not archive.exists():
            archive.write_bytes(body)
        return {'id': name, 'url': url, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
                'sha256': digest, 'bytes': len(body), 'status': 'archived'}
    except Exception as exc:
        return {'id': name, 'url': url, 'status': 'failed', 'error': str(exc)}

if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(fetch, URLS.items()))
    (ROOT / 'data' / 'fetch-log.json').write_text(json.dumps(results, indent=2))
    log_archive = ROOT / 'data' / 'source-archives' / ('fetch-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.json')
    log_archive.parent.mkdir(parents=True, exist_ok=True)
    log_archive.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))

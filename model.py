"""Transparent research prototype. Margins are Democratic minus Republican points."""
import math
import re
from collections import defaultdict
from datetime import date
from statistics import NormalDist

NORMAL = NormalDist()
VERSION = '0.2.0-research'

def rating_estimate(rating, as_of, shift=0, error_scale=1):
    if not rating or rating['date']>as_of:return None
    label=rating['label']
    favored={'Solid':.99,'Likely':.90,'Lean':.75,'Tilt':.60,'Toss-up':.50}.get(label.split()[0])
    if favored is None:return None
    p=favored if 'Democrat' in label or label=='Toss-up' else 1-favored
    mu=NORMAL.inv_cdf(p)*6+shift
    sd=6*error_scale
    return {'dem_probability':NORMAL.cdf(mu/sd),'mean_margin':mu,'sd':sd,
            'interval80':[mu-1.281551566*sd,mu+1.281551566*sd],
            'national_sd':2.5*error_scale,'state_sd':1.5*error_scale,
            'local_sd':math.sqrt(36-2.5**2-1.5**2)*error_scale,
            'used_ids':[], 'latest':rating['date'],'status':'Rating-derived baseline',
            'assumption':'Heuristic category conversion, not publisher probability; margin is synthetic; D/R approximation'}

def parse_challenge(text):
    pattern = r'Will the (Republican|Democratic|Independent) Party win the ([^?]+)\?\s*Yes\s*(\d+)%[\s\S]*?No\s*(\d+)%'
    races = {}
    for party, title, yes, no in re.findall(pattern, text):
        office = 'Control' if title.startswith('U.S.') else ('House' if 'House race' in title else title.split()[-1])
        location = title.replace(' House race', '').removesuffix(' Senate').removesuffix(' Governor')
        key = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        race = races.setdefault(key, {'id': key, 'title': title, 'location': location, 'office': office, 'quotes': {}})
        if int(yes) + int(no) != 100:
            raise ValueError(f'Invalid binary prices: {title}')
        race['quotes'][party] = {'yes': int(yes)/100, 'no': int(no)/100}
    if not races:
        raise ValueError('No questions found')
    for race in races.values():
        total = sum(q['yes'] for q in race['quotes'].values())
        race['quote_sum'] = round(total, 4)
        race['flags'] = []
        if abs(total-1) > .005:
            race['flags'].append('Listed party YES prices do not sum to 100%; these are separate contracts, not an executable arbitrage.')
        if 'Independent' in race['quotes']:
            race['flags'].append('Independent-party settlement and candidate identity require review; do not infer caucus affiliation.')
        if race['office'] == 'House':
            race['flags'].append('Verify 2026 district boundaries before using historical returns.')
    return list(races.values())

def estimate(observations, as_of, shift=0, error_scale=1):
    """Weak N(0,15²) prior; average OR raw polls, never overlapping both."""
    today = date.fromisoformat(as_of)
    eligible = [p for p in observations if date.fromisoformat(p['published']) <= today and date.fromisoformat(p['end']) <= today]
    if not eligible:
        return None
    averages = [p for p in eligible if p['kind'] == 'average']
    # An average replaces earlier constituent polls. Newer raw polls supersede a stale
    # average rather than being combined with unknown overlap.
    latest_average=max(averages,key=lambda p:p['end']) if averages else None
    newer=[p for p in eligible if p['kind']=='poll' and latest_average and p['end']>latest_average['end']]
    selected = newer if newer else ([latest_average] if latest_average else eligible)
    # One effective contribution per polling firm; repeat releases cannot create spurious precision.
    groups = defaultdict(list)
    for p in selected:
        age = (today-date.fromisoformat(p['end'])).days
        variance = p.get('se', 100/math.sqrt(p.get('n', 600)))**2
        precision = math.exp(-math.log(2)*age/21) / (variance + 2.0**2)
        groups[p['pollster']].append((p['margin'], precision))
    precision, numerator = 1/225, 0
    for group in groups.values():
        total = sum(w for _,w in group)
        effective = max(w for _,w in group)
        numerator += sum(m*w for m,w in group)/total*effective
        precision += effective
    mu = numerator/precision + shift
    days = max(0, (date(2026,11,3)-today).days)
    national_sd, state_sd = 2.5*error_scale, 1.5*error_scale
    local_variance = (1/precision + 2.0**2 + days*.035)*error_scale**2
    sd = math.sqrt(local_variance + national_sd**2 + state_sd**2)
    return {'dem_probability': NORMAL.cdf(mu/sd), 'mean_margin':mu, 'sd':sd,
            'interval80':[mu-1.281551566*sd,mu+1.281551566*sd],
            'national_sd':national_sd,'state_sd':state_sd,'local_sd':math.sqrt(local_variance),
            'used_ids':[p['id'] for p in selected], 'latest':max(p['end'] for p in selected),
            'status':'Provisional polling model', 'assumption':'D/R winner approximation; other-party wins not modeled'}

def forecast(races, observations, as_of, shift=0, error_scale=1):
    output=[]
    for race in races:
        row = dict(race)
        obs = [p for p in observations if p['race_id']==race['id']]
        row['observations'] = obs
        row['model'] = None if 'Independent' in race['quotes'] or race['office']=='Control' else estimate(obs,as_of,shift,error_scale)
        if not row['model'] and 'Independent' not in race['quotes'] and race['office']!='Control' and not race.get('suppress_rating'):
            row['model']=rating_estimate(race.get('rating'),as_of,shift,error_scale)
        row['status'] = row['model']['status'] if row['model'] else 'Market snapshot only'
        row['edges'] = {}
        if row['model']:
            for party, quote in race['quotes'].items():
                p = row['model']['dem_probability'] if party=='Democratic' else 1-row['model']['dem_probability']
                row['edges'][party] = {'probability':p,'difference':p-quote['yes']}
        output.append(row)
    return output

def score(predictions):
    """Proper scoring metrics for externally supplied, genuinely held-out predictions."""
    if not predictions:
        raise ValueError('No resolved predictions')
    for p,y in predictions:
        if not 0<=p<=1 or y not in (0,1):
            raise ValueError('Invalid probability/outcome')
    return {'n':len(predictions),'brier':sum((p-y)**2 for p,y in predictions)/len(predictions),
            'log_loss':-sum(y*math.log(max(p,1e-12))+(1-y)*math.log(max(1-p,1e-12)) for p,y in predictions)/len(predictions)}

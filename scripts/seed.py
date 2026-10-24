import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from model import parse_challenge

ROOT=Path(__file__).resolve().parents[1]
BASE='https://emersoncollegepolling.com/'
sources=[
 {'id':'nevada','title':'Emerson / KLAS Nevada','url':BASE+'nevada-2026-poll-ford-and-lombardo/','type':'Primary poll','published':'2026-09-10','note':'September 5–8; 680 likely voters. Governor D44/R42; 11% undecided.'},
 {'id':'unh-nh','title':'UNH New Hampshire September release','url':'https://scholars.unh.edu/survey_center_polls/1005/','type':'Qualitative poll evidence','published':'2026-09-24','note':'Abstract describes a narrow Democratic Senate lead and statistical ties in NH-01 and governor. Full PDF access returned 403; numeric results are not ingested.'},
 {'id':'unh-vt','title':'UNH Vermont September release','url':'https://scholars.unh.edu/survey_center_polls/1006/','type':'Qualitative poll evidence','published':'2026-09-24','note':'Abstract describes a statistical tie for governor. Conflicts with an older Solid Republican rating; flag for urgent review. Full PDF returned 403; no numeric poll entered.'},
 {'id':'silver','title':'Silver Bulletin public polling averages, September 29','url':'https://www.natesilver.net/p/nate-silver-2026-midterm-election-polls-model','type':'Polling average','published':'2026-09-29','note':'Public article supplies six Senate margins. These are polling averages, not Silver win probabilities. Full forecast is subscriber-only.'},
 {'id':'kansas','title':'Emerson / Nexstar Kansas','url':BASE+'kansas-2026/','type':'Primary poll','published':'2026-09-18','note':'September 15–16; 750 likely voters. Senate D45/R43; Governor D44/R51.'},
 {'id':'texas','title':'Emerson / Nexstar Texas','url':BASE+'texas-2026-poll-talarico-and-paxton-in-dead-heat-abbott-maintains-edge/','type':'Primary poll','published':'2026-09-17','note':'September 12–14; 1,000 likely voters. Senate D47/R46; Governor D46/R49.'},
 {'id':'michigan','title':'Emerson / Nexstar Michigan','url':BASE+'michigan-2026-poll-el-sayed-and-rogers-locked-in-close-election/','type':'Primary poll','published':'2026-09-17','note':'September 12–14; 1,000 likely voters. Senate D48/R46; Governor D49/R42.'},
 {'id':'iowa','title':'Emerson / Nexstar Iowa','url':BASE+'iowa-2026-poll-hinson-leads-turek/','type':'Primary poll','published':'2026-09-03','note':'August 31–September 1; 750 likely voters. Senate D45/R50; Governor D49/R46. Older Senate poll retained for audit, not combined with newer average.'},
 {'id':'rules','title':'Susquehanna Predictions Cup official rules','url':'https://predictionscup.com/rules/','type':'Contest rules','published':'2026-09-23','note':'Simulated trading scored by final SUSQies balance; 100,000 initial units. Market Info tabs define settlement. API permitted subject to platform controls.'},
 {'id':'api','title':'Platform API reference','url':'https://sig.thesuper.market/api/v1/docs','type':'API documentation','published':None,'note':'Schema archived. Bearer authentication; tournament-scoped prices must be selected explicitly. Read-only connector included.'},
 {'id':'aapor','title':'AAPOR polling accuracy','url':'https://aapor.org/polling-accuracy/','type':'Methods','published':None,'note':'Polling uncertainty includes more than sampling error. Averages do not remove shared bias.'},
 {'id':'method','title':'FLIPR methodology','url':'https://www.natesilver.net/p/flipr-midterms-model-methodology','type':'Methods','published':'2026-08-11','note':'Research reference for combining evidence and correlated outcomes. This project is not a reproduction of FLIPR.'},
 {'id':'mit','title':'MIT Election Lab historical data','url':'https://electionlab.mit.edu/articles/inside-2024-precinct-project','type':'Historical database','published':'2026-05-13','note':'Historical returns resource identified; not yet ingested or used to fit coefficients.'},
 {'id':'fec','title':'FEC bulk data and OpenFEC','url':'https://www.fec.gov/data/browse-data/','type':'Finance database','published':None,'note':'Candidate and campaign-finance source identified. Financial variables are not yet in the model.'},
 {'id':'cook','title':'Cook 2026 Senate overview','url':'https://www.cookpolitical.com/races-at-a-glance/2026/senate','type':'Expert ratings','published':'2026-09-23','note':'Identifies 35 Senate contests. Full data restricted; no unverified ratings entered.'},
]
obs=[]
obs.append(dict(id='emerson-nevada-governor',race_id='nevada-governor',kind='poll',pollster='Emerson',end='2026-09-08',published='2026-09-10',margin=2,n=680,source_id='nevada',note='Rounded D44/R42; 11% undecided.'))
for state,margin in [('Texas',3.6),('Maine',2.7),('Ohio',5.3),('Iowa',2.1),('Michigan',3.4),('Alaska',2.5)]:
 obs.append(dict(id='silver-'+state.lower(),race_id=state.lower()+'-senate',kind='average',pollster='Silver Bulletin',end='2026-09-29',published='2026-09-29',margin=margin,se=2.5,source_id='silver',note='Average SE is an analyst assumption, not supplied by publisher.'))
for state,sen,gov,n,end,pub in [('kansas',2,-7,750,'2026-09-16','2026-09-18'),('texas',1,-3,1000,'2026-09-14','2026-09-17'),('michigan',2,7,1000,'2026-09-14','2026-09-17'),('iowa',-5,3,750,'2026-09-01','2026-09-03')]:
 for office,margin in [('senate',sen),('governor',gov)]:
  obs.append(dict(id='emerson-'+state+'-'+office,race_id=state+'-'+office,kind='poll',pollster='Emerson',end=end,published=pub,margin=margin,n=n,source_id=state,note='Reported rounded D minus R margin; multi-party and undecided responses remain a modeling limitation.'))
races=parse_challenge((ROOT/'data/challenge.txt').read_text(encoding='utf-8'))
STATE_NAMES='Alabama,Alaska,Arizona,Arkansas,California,Colorado,Connecticut,Delaware,Florida,Georgia,Hawaii,Idaho,Illinois,Indiana,Iowa,Kansas,Kentucky,Louisiana,Maine,Maryland,Massachusetts,Michigan,Minnesota,Mississippi,Missouri,Montana,Nebraska,Nevada,New Hampshire,New Jersey,New Mexico,New York,North Carolina,North Dakota,Ohio,Oklahoma,Oregon,Pennsylvania,Rhode Island,South Carolina,South Dakota,Tennessee,Texas,Utah,Vermont,Virginia,Washington,West Virginia,Wisconsin,Wyoming'.split(',')
STATE_CODES='AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split()
state_codes=dict(zip(STATE_NAMES,STATE_CODES))
universe=[]
for office in ['house','senate','governor']:
 path=ROOT/'data/raw'/('ratings-'+office+'.txt')
 if not path.exists():continue
 document=json.loads(path.read_text(encoding='utf-8'))
 sources.append({'id':'ratings-'+office,'title':'Inside Elections '+office+' ratings database','url':'https://insideelections.com/ratings/'+office+'/', 'type':'Imported ratings database','published':document['last_updated'][:10], 'note':f'Imported {document["total"]} records. Labels are publisher judgments; numeric probability conversion is our uncalibrated assumption. Last change dates are not fresh poll dates.'})
 for entry in document['ratings']:
  universe.append({'office':office,'district':entry['district'],'rating':entry['rating'],'party':entry.get('party'),'date':entry['date'],'incumbent':entry.get('incumbent',[]),'special':entry['special']})
 for race in races:
  if race['office'].lower()!=office:continue
  district=race['location'] if office=='house' else state_codes.get(race['location'])
  matches=[e for e in document['ratings'] if e['district']==district and e['rating']!='Not Up This Cycle']
  if len(matches)==1:
   e=matches[0]
   race['rating']={'label':e['rating'],'date':e['date'][:10],'source_id':'ratings-'+office,'open_seat':e['open'],'incumbents':e.get('incumbent',[]),'source_note':e.get('note','')}
  elif len(matches)>1:race['flags'].append('Multiple seats match this state; contract identity must be resolved.')
  race['state_code']=district.split('-')[0] if district else None
for race in races:
 if race['id'] in ['new-hampshire-senate','new-hampshire-governor','nh-01-house-race']:
  race['research_note']='UNH September 24 abstract describes a narrow D Senate lead and statistical ties for governor and NH-01. Numeric PDF unavailable; review against market confidence.'
  race['research_source']='unh-nh'
 if race['id']=='vermont-governor':
  race['research_note']='UNH September 24 abstract describes a statistical tie, conflicting with the imported Solid Republican rating. Rating-derived probability is suppressed pending numeric evidence.'
  race['research_source']='unh-vt'
  race['suppress_rating']=True
(ROOT/'data/universe.json').write_text(json.dumps(universe,indent=2),encoding='utf-8')
payload={'as_of':'2026-09-29','election_date':'2026-11-03','market_captured_at':None,'market_imported_on':'2026-09-29','sources':sources,'observations':obs,'races':races}
(ROOT/'data/seed.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
print(f'{len(races)} races, {sum(len(r["quotes"]) for r in races)} contracts, {len(obs)} observations')

import copy
import json
import math
import unittest
from pathlib import Path
from model import estimate,forecast,parse_challenge,score,rating_estimate
from app import build,simulate

class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed=json.loads(Path('data/seed.json').read_text())
    def test_import_covers_questions(self):
        races=parse_challenge(Path('data/challenge.txt').read_text(encoding='utf-8'))
        self.assertEqual(len(races),117)
        self.assertEqual(sum(len(r['quotes']) for r in races),237)
        self.assertEqual(len({r['id'] for r in races}),117)
    def test_bad_binary_quote(self):
        with self.assertRaises(ValueError):parse_challenge('Will the Democratic Party win the Iowa Senate? Yes 60% No 45%')
    def test_future_evidence_excluded(self):
        self.assertIsNone(estimate(self.seed['observations'],'2025-01-01'))
    def test_no_average_double_count(self):
        obs=[p for p in self.seed['observations'] if p['race_id']=='texas-senate']
        result=estimate(obs,'2026-09-29')
        self.assertEqual(result['used_ids'],['silver-texas'])
    def test_repeat_poll_does_not_create_precision(self):
        obs=[p for p in self.seed['observations'] if p['race_id']=='kansas-senate']
        a=estimate(obs,'2026-09-29');b=estimate(obs*100,'2026-09-29')
        self.assertAlmostEqual(a['sd'],b['sd'])
        self.assertAlmostEqual(a['dem_probability'],b['dem_probability'])
    def test_shift_monotonic_and_uncertainty(self):
        obs=self.seed['observations'][:1]
        a=estimate(obs,'2026-09-29');b=estimate(obs,'2026-09-29',3)
        self.assertGreater(b['dem_probability'],a['dem_probability'])
        c=estimate(obs,'2026-09-29',0,2)
        self.assertLess(abs(c['dem_probability']-.5),abs(a['dem_probability']-.5))
    def test_forecasts_finite_and_no_unsupported_control(self):
        for r in build()['races']:
            if r['office']=='Control' or 'Independent' in r['quotes']:self.assertIsNone(r['model'])
            if r['model']:
                self.assertTrue(0<r['model']['dem_probability']<1)
                self.assertTrue(math.isfinite(r['model']['sd']))
                self.assertAlmostEqual(sum(e['probability'] for e in r['edges'].values()),1)
            else:self.assertEqual(r['edges'],{})
    def test_simulation_count_reproducible(self):
        a=simulate(build(),500)
        self.assertEqual(sum(a['histogram']),500)
        self.assertEqual(a,simulate(build(),500))
    def test_proper_scoring(self):
        self.assertEqual(score([(.5,1),(.5,0)])['brier'],.25)
        self.assertEqual(score([(1,1),(0,0)])['brier'],0)
        with self.assertRaises(ValueError):score([(1.1,1)])
    def test_rating_mapping_and_lookahead(self):
        r={'label':'Lean Republican','date':'2026-09-20'}
        self.assertAlmostEqual(rating_estimate(r,'2026-09-29')['dem_probability'],.25)
        self.assertIsNone(rating_estimate(r,'2026-09-19'))
    def test_conflicting_rating_withheld(self):
        race=next(r for r in build()['races'] if r['id']=='vermont-governor')
        self.assertIsNone(race['model'])
    def test_new_poll_supersedes_stale_average(self):
        obs=[p for p in self.seed['observations'] if p['race_id']=='texas-senate']
        newer=dict(obs[-1],id='new',end='2026-10-01',published='2026-10-02')
        result=estimate(obs+[newer],'2026-10-02')
        self.assertEqual(result['used_ids'],['new'])
    def test_rating_edges_never_tradable(self):
        for race in build()['races']:
            for edge in race['edges'].values():
                if race['model']['status']=='Rating-derived baseline':self.assertFalse(edge['tradable'])
                if edge['tradable']:self.assertGreaterEqual(abs(edge['difference']),.08)
    def test_database_universe(self):
        rows=json.loads(Path('data/universe.json').read_text())
        self.assertEqual(sum(r['office']=='house' for r in rows),435)
        self.assertEqual(sum(r['office']=='senate' and r['rating']!='Not Up This Cycle' for r in rows),35)

if __name__=='__main__':unittest.main()

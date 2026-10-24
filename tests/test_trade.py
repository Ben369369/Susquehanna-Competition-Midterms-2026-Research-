import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from trade import floor_tick, plan_orders, stale_orders

MARKETS = {('ga', 'Democratic'): {'id': '166', 'title': 'GA D', 'exchanges': [{'id': '9'}]},
           ('ks', 'Democratic'): {'id': '356', 'title': 'KS D', 'exchanges': [{'id': '7'}]}}
PROBS = {'ga': (.36, .39), 'ks': (.59, .61)}

def plan(*trades, reserve=45000):
    return {'reserve': reserve, 'min_edge': .04, 'min_order': 200, 'trades': list(trades)}

GA = {'race_id': 'ga', 'party': 'Democratic', 'side': 'no', 'budget': 21000, 'max_price': .42}
KS = {'race_id': 'ks', 'party': 'Democratic', 'side': 'yes', 'budget': 10000, 'max_price': .43}

class TradeTests(unittest.TestCase):
    def test_tick_rounds_down(self):
        self.assertEqual(floor_tick(.4199), .415)
        self.assertEqual(floor_tick(.42), .42)
    def test_no_price_is_complement_of_yes_bid(self):
        orders, _ = plan_orders(plan(GA), MARKETS, [], [], {'9': (.60, .61)}, 100000, PROBS)
        self.assertEqual(orders[0]['price'], .4)
        self.assertEqual(orders[0]['quantity'], int(21000/.4))
    def test_budget_counts_existing_position(self):
        held = [{'marketId': '166', 'quantity': 24793, 'costBasis': 10241, 'lots': [{'side': 'NO'}]}]
        orders, _ = plan_orders(plan(GA), MARKETS, held, [], {'9': (.60, .61)}, 89758, PROBS)
        self.assertAlmostEqual(orders[0]['cost'], 21000-10241, delta=1)
    def test_skips_when_price_moved_past_cap(self):
        orders, notes = plan_orders(plan(KS), MARKETS, [], [], {'7': (.44, .45)}, 100000, PROBS)
        self.assertEqual(orders, []); self.assertIn('above max', notes[0])
    def test_reserve_limits_spend(self):
        orders, _ = plan_orders(plan(GA, KS, reserve=95000), MARKETS, [], [], {'9': (.60, .61), '7': (.41, .42)}, 100000, PROBS)
        self.assertLessEqual(sum(o['cost'] for o in orders), 5000)
    def test_skips_opposite_side_and_resting(self):
        held = [{'marketId': '166', 'quantity': 100, 'costBasis': 50, 'lots': [{'side': 'YES'}]}]
        _, notes = plan_orders(plan(GA), MARKETS, held, [], {'9': (.60, .61)}, 100000, PROBS)
        self.assertIn('opposite side', notes[0])
        _, notes = plan_orders(plan(GA), MARKETS, [], [{'id': 1, 'exchangeId': '9', 'quantity': 10, 'priceLimit': .4}], {'9': (.60, .61)}, 100000, PROBS)
        self.assertIn('resting', notes[0])
    def test_flags_mistyped_limit(self):
        orders = [{'id': 5, 'exchangeId': '9', 'side': 'no', 'action': 'buy', 'priceLimit': .58, 'quantity': 1}]
        self.assertEqual([o['id'] for o in stale_orders(plan(GA), MARKETS, orders)], [5])

if __name__ == '__main__': unittest.main()

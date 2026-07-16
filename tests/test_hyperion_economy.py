import math
import unittest

from trade_sim import EVENT_DEFINITIONS, GOOD_DATA, HyperionEconomySim, SimulationConfig


class HyperionEconomyTests(unittest.TestCase):
    def test_reproducible_tick_state(self) -> None:
        sim_a = HyperionEconomySim(SimulationConfig(ticks=3, seed=123))
        sim_b = HyperionEconomySim(SimulationConfig(ticks=3, seed=123))

        for _ in range(3):
            sim_a.step()
            sim_b.step()

        a_state = [(w.name, round(w.prosperity, 4), round(w.stability, 4)) for w in sim_a.worlds]
        b_state = [(w.name, round(w.prosperity, 4), round(w.stability, 4)) for w in sim_b.worlds]
        self.assertEqual(a_state, b_state)

    def test_hyperion_is_special_and_risky(self) -> None:
        sim = HyperionEconomySim(SimulationConfig(ticks=1, seed=5))
        hyperion = next(w for w in sim.worlds if w.name == "Hyperion")

        self.assertTrue(hyperion.hyperion_special)
        self.assertTrue(hyperion.periphery)
        self.assertGreaterEqual(hyperion.pilgrim_pull, 1.5)

    def test_summary_contains_required_sections(self) -> None:
        sim = HyperionEconomySim(SimulationConfig(ticks=1, seed=99))
        sim.step()
        text = sim.summary()

        self.assertIn("Tick 1", text)
        self.assertIn("Top-Preise", text)
        self.assertIn("Größte Engpässe", text)
        self.assertIn("Fraktionen", text)

    def test_world_table_contains_worlds(self) -> None:
        sim = HyperionEconomySim(SimulationConfig(ticks=1, seed=11))
        table = sim.world_table()
        self.assertIn("WELTENSTATUS", table)
        self.assertIn("Hyperion", table)

    def test_model_data_is_loaded_from_assets(self) -> None:
        sim = HyperionEconomySim(SimulationConfig(ticks=1, event_chance=0))
        self.assertEqual(len(GOOD_DATA), 8)
        self.assertEqual(len(sim.worlds), 8)
        self.assertGreaterEqual(len(EVENT_DEFINITIONS), 8)
        self.assertEqual({world.name for world in sim.worlds}, {"Hyperion", "Lusus", "Tau Ceti", "Maui-Covenant", "Marsim", "Qom-Riyadh", "Bressia", "Hebron"})

    def test_invalid_configuration_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            SimulationConfig(ticks=0)
        with self.assertRaises(ValueError):
            SimulationConfig(event_chance=1.1)
        with self.assertRaises(ValueError):
            SimulationConfig(trade_intensity=-1)

    def test_trade_books_cash_and_respects_route_capacity(self) -> None:
        sim = HyperionEconomySim(SimulationConfig(ticks=1, event_chance=0, route_capacity=2))
        seller, buyer = sim.worlds[0], sim.worlds[1]
        good = "nahrung"
        seller.stock[good] = sim._reserve(seller) + 10
        buyer.stock[good] = 0
        seller.prices[good] = 10
        buyer.prices[good] = 100
        seller_cash = seller.cash
        buyer_cash = buyer.cash

        sim._trade()

        self.assertTrue(sim.trade_log)
        self.assertLessEqual(10 - seller.stock[good] + sim._reserve(seller), 2.01)
        self.assertGreater(seller.cash, seller_cash)
        self.assertLess(buyer.cash, buyer_cash)

    def test_long_run_preserves_basic_invariants(self) -> None:
        sim = HyperionEconomySim(SimulationConfig(ticks=10, seed=21, event_chance=0.5))
        for _ in range(10):
            sim.step()

        for world in sim.worlds:
            for good in GOOD_DATA:
                self.assertGreaterEqual(world.stock[good], 0)
                self.assertGreaterEqual(world.prices[good], 4)
                self.assertTrue(math.isfinite(world.prices[good]))
            self.assertGreaterEqual(world.cash, 0)


if __name__ == "__main__":
    unittest.main()

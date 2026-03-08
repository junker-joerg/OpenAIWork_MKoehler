import unittest

from trade_sim import HyperionEconomySim, SimulationConfig


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


if __name__ == "__main__":
    unittest.main()

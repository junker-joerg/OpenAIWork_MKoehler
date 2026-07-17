import tempfile
import unittest
from pathlib import Path

from juno_demo import export_demo, kpi_table, run_simulation, scenario_table


class JunoDemoTests(unittest.TestCase):
    def test_demo_frames_are_compact_and_reproducible(self) -> None:
        first = run_simulation(years=4, seed=7, num_runs=1, event_chance=0)
        second = run_simulation(years=4, seed=7, num_runs=1, event_chance=0)

        self.assertEqual(set(first), {"yearly", "world", "price", "events", "trades"})
        self.assertEqual(first["world"].shape, (32, 14))
        self.assertTrue(first["yearly"].equals(second["yearly"]))
        self.assertTrue(first["price"].equals(second["price"]))

    def test_fixed_scenario_forces_the_story_event(self) -> None:
        frames = run_simulation(years=4, seed=17, num_runs=1, event_chance=0, scenario="farcaster")
        self.assertIn("farcaster_stoerung", set(frames["events"]["event_key"]))

    def test_kpis_and_scenario_table_have_demo_fields(self) -> None:
        frames = run_simulation(years=4, seed=7, num_runs=1, event_chance=0)
        kpis = kpi_table(frames)
        comparison = scenario_table(years=4, event_chance=0)
        self.assertIn("total_trade_value", kpis)
        self.assertEqual(len(comparison), 3)
        self.assertIn("final_time_debt", comparison)

    def test_export_always_writes_csv(self) -> None:
        frames = run_simulation(years=2, seed=7, num_runs=1, event_chance=0)
        with tempfile.TemporaryDirectory() as directory:
            result = export_demo(frames, directory)
            self.assertTrue(result["csv_files"])
            self.assertTrue(Path(directory, "yearly.csv").is_file())
            self.assertTrue(Path(directory, "metadata.json").is_file())


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from juno_showcase import (
    BOKEH_AVAILABLE,
    agent_council_table,
    build_showcase,
    compose_scenario,
    export_demo_capsule,
    flight_recorder_table,
    scenario_comparison,
)


class JunoShowcaseTests(unittest.TestCase):
    def test_showcase_contains_all_story_products(self) -> None:
        showcase = build_showcase(episodes=2, years=4, seed=7)

        self.assertEqual(len(showcase["summary"]), 3)
        self.assertFalse(showcase["decisions"].empty)
        self.assertIn("best_action", showcase["decisions"])
        self.assertIn("realized_reward", showcase["decisions"])
        self.assertIn("source", showcase["routes"])
        self.assertIn("name", showcase["nodes"])
        self.assertEqual(len(agent_council_table(showcase["summary"])), 3)

    def test_scenario_composer_forces_selected_event(self) -> None:
        frames, kpis = compose_scenario(
            event_name="farcaster_stoerung", event_year=2, years=4, seed=7
        )

        self.assertIn("farcaster_stoerung", set(frames["events"]["event_key"]))
        self.assertEqual(int(kpis.iloc[0]["final_year"]), 4)

        with self.assertRaises(ValueError):
            compose_scenario(event_name="not-an-event", event_year=2, years=4)
        with self.assertRaises(ValueError):
            compose_scenario(event_name="keines", event_year=5, years=4)

    def test_scenario_comparison_is_presentation_ready(self) -> None:
        comparison = scenario_comparison(
            event_names=("keines", "pilgerboom"), event_year=2, years=4, seed=7
        )

        self.assertEqual(list(comparison["event_name"]), ["keines", "pilgerboom"])
        self.assertIn("final_stability", comparison)
        self.assertIn("event_year", comparison)

    def test_flight_recorder_explains_decisions(self) -> None:
        showcase = build_showcase(episodes=1, years=3, seed=7)
        recorder = flight_recorder_table(showcase["decisions"])

        self.assertEqual(len(recorder), len(showcase["decisions"]))
        self.assertTrue(recorder["explanation"].map(bool).all())

    def test_demo_capsule_exports_without_optional_bokeh(self) -> None:
        showcase = build_showcase(episodes=1, years=3, seed=7)
        showcase["council_markdown"] = agent_council_table(
            showcase["summary"]
        ).to_string(index=False)

        with tempfile.TemporaryDirectory() as directory:
            result = export_demo_capsule(showcase, directory)
            self.assertTrue(Path(directory, "DEMO_REPORT.md").is_file())
            self.assertTrue(Path(directory, "metadata.json").is_file())
            self.assertIn("summary.csv", " ".join(result["files"]))
            self.assertEqual(
                result["metadata"], str(Path(directory, "metadata.json"))
            )

    @unittest.skipUnless(BOKEH_AVAILABLE, "Bokeh ist in dieser Umgebung optional")
    def test_bokeh_builders_return_layouts(self) -> None:
        from bokeh.models import LayoutDOM
        from juno_showcase import (
            bokeh_agent_dashboard,
            bokeh_route_map,
            bokeh_scenario_dashboard,
        )

        showcase = build_showcase(episodes=1, years=3, seed=7)
        self.assertIsInstance(bokeh_agent_dashboard(showcase), LayoutDOM)
        self.assertIsInstance(
            bokeh_scenario_dashboard(showcase["scenario_runs"]), LayoutDOM
        )
        self.assertIsInstance(
            bokeh_route_map(showcase["routes"], showcase["nodes"]), LayoutDOM
        )


if __name__ == "__main__":
    unittest.main()

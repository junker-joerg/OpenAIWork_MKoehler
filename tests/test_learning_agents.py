import json
import io
import sys
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch

from learning_agents import (
    ACTIONS,
    ALGORITHMS,
    Agent,
    create_default_agents,
    evaluate_agents,
    evaluation_summary,
    load_agent_memory,
    market_state,
    run_episode,
    save_agent_memory,
    train_agents,
)
from run_juno_agents import main as run_juno_agents_main


class LearningAgentTests(unittest.TestCase):
    def test_all_algorithms_use_hyperion_market_snapshots(self):
        agents = create_default_agents(7)
        rows = run_episode(agents, years=5, seed=7)
        self.assertEqual({row["algorithm"] for row in rows}, set(ALGORITHMS))
        self.assertTrue(all("benchmark_value" in row for row in rows))
        self.assertTrue(all(float(row["final_value"]) > 0 for row in rows))
        self.assertTrue(all(row["insolvent"] is False for row in rows))

    def test_training_is_reproducible_with_local_rngs(self):
        first = train_agents(episodes=4, years=5, seed=11, memory_path=None)
        second = train_agents(episodes=4, years=5, seed=11, memory_path=None)
        self.assertEqual(first["history"], second["history"])
        self.assertEqual(
            [agent.to_dict() for agent in first["agents"]],
            [agent.to_dict() for agent in second["agents"]],
        )

    def test_memory_round_trip_and_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = Path(directory) / "nested" / "agent_memory.json"
            initial = train_agents(episodes=2, years=4, seed=5, memory_path=str(memory))
            payload = json.loads(memory.read_text(encoding="utf-8"))
            self.assertEqual(payload["format"], 2)
            restored = load_agent_memory(str(memory), seed=5)
            self.assertEqual(
                [agent.to_dict() for agent in initial["agents"]],
                [agent.to_dict() for agent in restored],
            )
            continued = train_agents(
                episodes=1,
                years=4,
                seed=6,
                agents=restored,
                memory_path=str(memory),
            )
            self.assertEqual(len(continued["history"]), 3)

    def test_legacy_memory_list_can_be_loaded(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = Path(directory) / "legacy.json"
            agents = create_default_agents(3)
            memory.write_text(
                json.dumps([agent.to_dict() for agent in agents]), encoding="utf-8"
            )
            restored = load_agent_memory(str(memory), seed=3)
            self.assertEqual([agent.name for agent in restored], [agent.name for agent in agents])

    def test_actions_and_state_are_valid(self):
        state = market_state(
            {"price": 260.0, "stability": 0.8, "time_debt": 0.5, "event_count": 0, "stock": 40},
            1000.0,
            0,
        )
        self.assertEqual(len(state), 7)
        agent = Agent("Test", "sarsa", 0.2, 0.9, seed=1)
        allowed = agent.allowed_actions(1000.0, 0, 260.0)
        self.assertIn("halten", allowed)
        self.assertNotIn("verkaufen", allowed)
        self.assertTrue(all(agent.choose(state, allowed) in ACTIONS for _ in range(20)))

    def test_evaluation_summary_has_benchmark_and_risk_metrics(self):
        agents = create_default_agents(7)
        train_agents(episodes=3, years=5, seed=7, agents=agents, memory_path=None)
        rows = evaluate_agents(agents, episodes=3, years=5, seed=100)
        summary = evaluation_summary(rows)
        self.assertEqual(len(summary), 3)
        for row in summary:
            self.assertIn("std_final_value", row)
            self.assertIn("win_rate", row)
            self.assertIn("insolvency_rate", row)
            self.assertGreaterEqual(float(row["win_rate"]), 0.0)
            self.assertLessEqual(float(row["win_rate"]), 1.0)

    def test_launcher_supports_new_and_resume_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = Path(directory) / "launcher-memory.json"
            for extra in ([], ["--resume"]):
                arguments = [
                    "run_juno_agents.py",
                    "--episodes",
                    "1",
                    "--years",
                    "3",
                    "--memory",
                    str(memory),
                    *extra,
                ]
                output = io.StringIO()
                with patch.object(sys, "argv", arguments), redirect_stdout(output):
                    run_juno_agents_main()
                self.assertIn("Training abgeschlossen", output.getvalue())
            self.assertTrue(memory.is_file())


if __name__ == "__main__":
    unittest.main()

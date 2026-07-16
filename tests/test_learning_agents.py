import json
import tempfile
import unittest
from pathlib import Path

from learning_agents import (
    ACTIONS,
    QLearningTrader,
    create_default_agents,
    evaluate_agents,
    load_agent_memory,
    market_state,
    save_agent_memory,
    train_agents,
)


class LearningAgentTests(unittest.TestCase):
    def test_training_is_reproducible(self):
        first = train_agents(episodes=4, years=5, seed=11)
        second = train_agents(episodes=4, years=5, seed=11)
        self.assertEqual(first["history"], second["history"])
        self.assertEqual(
            [agent.q_table for agent in first["agents"]],
            [agent.q_table for agent in second["agents"]],
        )

    def test_q_learning_memory_round_trip(self):
        result = train_agents(episodes=2, years=4, seed=5)
        with tempfile.TemporaryDirectory() as directory:
            memory = Path(directory) / "agent_memory.json"
            save_agent_memory(result["agents"], str(memory), episodes=2, seed=5)
            payload = json.loads(memory.read_text(encoding="utf-8"))
            self.assertEqual(payload["format"], 1)
            restored = load_agent_memory(str(memory), seed=5)
            self.assertEqual(
                [agent.q_table for agent in result["agents"]],
                [agent.q_table for agent in restored],
            )

    def test_actions_and_state_are_small_and_valid(self):
        state = market_state(260.0, 0.8, 1000.0, 0)
        self.assertIn("price=mid", state)
        agent = QLearningTrader("Test", 0.2)
        for _ in range(20):
            self.assertIn(agent.choose_action(state), ACTIONS)
        agent.update(state, "hold", 1.0, state)
        self.assertGreater(agent.q_table[state]["hold"], 0.0)

    def test_three_agents_and_evaluation(self):
        agents = create_default_agents(7)
        self.assertEqual(
            [agent.name for agent in agents],
            ["Profit-Scout", "Reserve-Keeper", "Hyperion-Speculator"],
        )
        result = train_agents(episodes=2, years=4, seed=7, agents=agents)
        evaluation = evaluate_agents(agents, episodes=2, years=4, seed=17)
        self.assertEqual(len(result["history"]), 6)
        self.assertEqual(len(evaluation), 6)
        self.assertTrue(all(float(row["final_value"]) > 0 for row in evaluation))


if __name__ == "__main__":
    unittest.main()

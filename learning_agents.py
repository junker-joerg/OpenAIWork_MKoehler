
import json
import random
from pathlib import Path

ACTIONS = ("halten", "kaufen", "verkaufen")


def _values(table, state):
   state = tuple(state)
   if state not in table:
       table[state] = {action: 0.0 for action in ACTIONS}
   return table[state]


def _best(values):
   maximum = max(values.values())
   return random.choice([
       action for action, value in values.items()
       if value == maximum
   ])


class Agent:
   def __init__(self, name, algorithm, alpha, gamma):
       self.name = name
       self.algorithm = algorithm
       self.alpha = alpha
       self.gamma = gamma
       self.epsilon = 0.30
       self.epsilon_min = 0.05
       self.epsilon_decay = 0.94
       self.q_table = {}
       self.transitions = {}
       self.bandit_counts = {action: 0 for action in ACTIONS}
       self.bandit_values = {action: 0.0 for action in ACTIONS}

   def choose(self, state, explore=True):
       values = (
           self.bandit_values
           if self.algorithm == "bandit"
           else _values(self.q_table, state)
       )
       if explore and random.random() < self.epsilon:
           return random.choice(ACTIONS)
       return _best(values)

   def sarsa_update(self, state, action, reward, next_state, next_action):
       current = _values(self.q_table, state)
       following = _values(self.q_table, next_state)
       target = reward + self.gamma * following[next_action]
       current[action] += self.alpha * (target - current[action])

   def q_update(self, state, action, reward, next_state):
       current = _values(self.q_table, state)
       following = _values(self.q_table, next_state)
       target = reward + self.gamma * max(following.values())
       current[action] += self.alpha * (target - current[action])

   def bandit_update(self, action, reward):
       count = self.bandit_counts[action] + 1
       old = self.bandit_values[action]
       self.bandit_counts[action] = count
       self.bandit_values[action] = old + (reward - old) / count

   def remember(self, state, action, reward, next_state):
       self.transitions[(tuple(state), action)] = (
           float(reward), tuple(next_state)
       )

   def replay(self, steps=8):
       if not self.transitions:
           return
       items = list(self.transitions.items())
       for _ in range(min(steps, len(items))):
           (state, action), (reward, next_state) = random.choice(items)
           self.q_update(state, action, reward, next_state)


def _state(market, stock):
   price, stability, liquidity = market
   return (
       0 if price < 85 else 1 if price < 115 else 2,
       0 if stability < 0.38 else 1 if stability < 0.70 else 2,
       0 if liquidity < 0.35 else 1,
       0 if stock == 0 else 1,
   )


def _step(market, action, stock, cash):
   price, stability, liquidity = market
   old_value = cash + stock * price
   price = max(
       20.0,
       price
       * (1 + random.uniform(-0.08, 0.08))
       * (1 + random.uniform(-0.16, 0.16) * (1 - stability)),
   )
   stability = max(
       0.0, min(1.0, stability + random.uniform(-0.08, 0.08))
   )
   liquidity = max(
       0.0, min(1.0, liquidity + random.uniform(-0.10, 0.10))
   )
   if action == "kaufen" and cash >= price and liquidity > 0.18:
       cash -= price
       stock += 1
   elif action == "verkaufen" and stock > 0 and liquidity > 0.12:
       cash += price
       stock -= 1
   new_value = cash + stock * price
   return (price, stability, liquidity), stock, cash, new_value - old_value


def _make_agents(seed):
   random.seed(seed)
   return [
       Agent("Profit-Scout", "sarsa", 0.24, 0.94),
       Agent("Reserve-Keeper", "dyna-q", 0.16, 0.86),
       Agent("Hyperion-Speculator", "bandit", 0.20, 0.0),
   ]


def _episode(agent, years, explore, learn):
   market = (100.0, 0.72, 0.72)
   stock, cash = 0, 1000.0
   state = _state(market, stock)
   action = agent.choose(state, explore)
   total_reward = 0.0
   trades = 0

   for _ in range(years):
       old_stock = stock
       next_market, stock, cash, reward = _step(
           market, action, stock, cash
       )
       next_state = _state(next_market, stock)
       total_reward += reward
       trades += int(stock != old_stock)

       if learn and agent.algorithm == "sarsa":
           next_action = agent.choose(next_state, explore)
           agent.sarsa_update(
               state, action, reward, next_state, next_action
           )
       elif learn and agent.algorithm == "dyna-q":
           next_action = agent.choose(next_state, explore)
           agent.q_update(state, action, reward, next_state)
           agent.remember(state, action, reward, next_state)
           agent.replay()
       elif learn:
           next_action = agent.choose(next_state, explore)
           agent.bandit_update(action, reward)
       else:
           next_action = agent.choose(next_state, False)

       state, market, action = next_state, next_market, next_action

   if learn:
       agent.epsilon = max(
           agent.epsilon_min,
           agent.epsilon * agent.epsilon_decay,
       )
   return {
       "final_value": round(cash + stock * market[0], 2),
       "total_reward": round(total_reward, 2),
       "trades": trades,
   }


def train_agents(
   episodes=30, years=20, seed=7, memory_path="agent_memory.json"
):
   agents = _make_agents(seed)
   history = []
   for episode in range(episodes):
       for index, agent in enumerate(agents):
           random.seed(seed + episode * 101 + index)
           result = _episode(agent, years, True, True)
           history.append({
               "episode": episode + 1,
               "agent": agent.name,
               "algorithm": agent.algorithm,
               **result,
               "q_states": len(agent.q_table),
               "epsilon": round(agent.epsilon, 6),
           })
   _save(agents, memory_path)
   return {"agents": agents, "history": history}


def evaluate_agents(agents, episodes=5, years=20, seed=1007):
   rows = []
   for episode in range(episodes):
       for index, agent in enumerate(agents):
           random.seed(seed + episode * 101 + index)
           result = _episode(agent, years, False, False)
           rows.append({
               "episode": episode + 1,
               "agent": agent.name,
               "algorithm": agent.algorithm,
               **result,
               "epsilon": agent.epsilon,
               "q_states": len(agent.q_table),
           })
   return rows


def _save(agents, path):
   data = []
   for agent in agents:
       data.append({
           "name": agent.name,
           "algorithm": agent.algorithm,
           "alpha": agent.alpha,
           "gamma": agent.gamma,
           "epsilon": agent.epsilon,
           "q_table": [
               [list(state), values]
               for state, values in agent.q_table.items()
           ],
           "transitions": [
               [list(state), action, reward, list(next_state)]
               for (state, action), (reward, next_state)
               in agent.transitions.items()
           ],
           "bandit_counts": agent.bandit_counts,
           "bandit_values": agent.bandit_values,
       })
   Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_agent_memory(path="agent_memory.json", seed=7):
   agents = _make_agents(seed)
   data = json.loads(Path(path).read_text(encoding="utf-8"))
   lookup = {agent.name: agent for agent in agents}
   for item in data:
       agent = lookup[item["name"]]
       agent.algorithm = item.get("algorithm", agent.algorithm)
       agent.alpha = item.get("alpha", agent.alpha)
       agent.gamma = item.get("gamma", agent.gamma)
       agent.epsilon = item.get("epsilon", agent.epsilon)
       agent.q_table = {
           tuple(state): values
           for state, values in item.get("q_table", [])
       }
       agent.transitions = {
           (tuple(state), action): (reward, tuple(next_state))
           for state, action, reward, next_state
           in item.get("transitions", [])
       }
       agent.bandit_counts.update(item.get("bandit_counts", {}))
       agent.bandit_values.update(item.get("bandit_values", {}))
   return agents

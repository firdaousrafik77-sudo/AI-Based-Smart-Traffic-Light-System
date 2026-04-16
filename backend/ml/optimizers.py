"""
Layer 3 - ML: Optimization algorithms
Two optimizers that each learn better traffic-light timing over time:

  1. ReinforcementLearningOptimizer  — Q-Learning
     Learns which axis (NS or EW) to favour based on current state.

  2. GeneticAlgorithmOptimizer — Evolutionary search
     Evolves a population of timing configs toward higher throughput.
"""

import numpy as np
from typing import Dict, List, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


# ========================================================================= #
#  Q-Learning                                                                #
# ========================================================================= #

class ReinforcementLearningOptimizer:
    """
    Q-Learning based traffic light optimizer.

    State  = (flow_level, congestion_balance, skip_counter_level)
    Action = one of: 'NS', 'EW', 'adaptive_cycle', 'emergency'
    Reward = penalise wait time, reward throughput, bonus for balance
    """

    def __init__(self, learning_rate: float = 0.1, discount_factor: float = 0.95):
        # Q-table: state → {action → value}
        self.q_table = defaultdict(lambda: defaultdict(float))
        self.lr      = learning_rate
        self.gamma   = discount_factor
        self.epsilon = 0.1      # exploration rate
        self.actions = ['NS', 'EW', 'adaptive_cycle', 'emergency']

    def get_state(self, traffic: Dict[str, int],
                  skip_counter: Dict[str, int]) -> str:
        """
        Compress the intersection state into a short string key.
        Example: "medium_balanced_low_skip"
        """
        total = sum(traffic.values())
        max_road = max(traffic.values())
        congestion_ratio = max_road / (total + 1)

        flow_level = 'low' if total < 30 else ('medium' if total < 70 else 'high')
        imbalance  = 'unbalanced' if congestion_ratio > 0.6 else 'balanced'
        skip_level = max(skip_counter.values())
        skip_str   = 'high_skip' if skip_level >= 3 else (
                     'med_skip'  if skip_level >= 1 else 'low_skip')

        return f"{flow_level}_{imbalance}_{skip_str}"

    def choose_action(self, state: str) -> str:
        """Epsilon-greedy: explore randomly 10% of the time, else pick best."""
        if np.random.random() < self.epsilon:
            return np.random.choice(self.actions)
        state_q = self.q_table[state]
        if not state_q:
            return 'NS'
        return max(state_q, key=state_q.get)

    def update(self, state: str, action: str,
               reward: float, next_state: str):
        """Standard Q-Learning update rule."""
        best_next = max(self.q_table[next_state].values(),
                        default=0.0)
        current_q = self.q_table[state][action]
        self.q_table[state][action] = (
            current_q + self.lr * (reward + self.gamma * best_next - current_q)
        )

    def calculate_reward(self, traffic: Dict[str, int],
                         wait_times: Dict[str, int]) -> float:
        """
        Reward = throughput bonus - wait penalty - imbalance penalty
        Higher is better.
        """
        total_wait  = sum(wait_times.values())
        total_cars  = sum(traffic.values())
        variance    = np.var(list(traffic.values()))

        wait_penalty      = -total_wait / 100
        throughput_reward =  total_cars  / 10
        balance_bonus     = -variance    / 50

        return wait_penalty + throughput_reward + balance_bonus


# ========================================================================= #
#  Genetic Algorithm                                                         #
# ========================================================================= #

class GeneticAlgorithmOptimizer:
    """
    Genetic Algorithm that evolves traffic light timing configurations.

    An 'individual' is one timing config:
        {'green_duration': int, 'yellow_duration': int,
         'red_duration': int,   'cycle_length': int}

    Fitness = throughput / (wait_time + 1)  — higher is better.
    """

    def __init__(self, population_size: int = 20, mutation_rate: float = 0.1):
        self.population_size = population_size
        self.mutation_rate   = mutation_rate

    # ------------------------------------------------------------------ #
    #  Individual / population                                            #
    # ------------------------------------------------------------------ #

    def create_individual(self) -> Dict[str, int]:
        return {
            'green_duration':  np.random.randint(10, 40),
            'yellow_duration': 3,
            'red_duration':    np.random.randint(5, 15),
            'cycle_length':    np.random.randint(30, 90),
        }

    def create_population(self) -> List[Dict[str, int]]:
        return [self.create_individual() for _ in range(self.population_size)]

    # ------------------------------------------------------------------ #
    #  Fitness                                                             #
    # ------------------------------------------------------------------ #

    def fitness(self, individual: Dict[str, int],
                traffic_history: List[Dict]) -> float:
        """Score an individual against historical traffic snapshots."""
        total_throughput = 0
        total_wait       = 0
        capacity = individual['green_duration'] * 2

        for snapshot in traffic_history:
            flow       = min(capacity, sum(snapshot.values()))
            total_throughput += flow / (individual['cycle_length'] + 1)
            total_wait       += max(0, sum(snapshot.values()) - capacity) * 2

        return total_throughput / (total_wait + 1)

    # ------------------------------------------------------------------ #
    #  Genetic operators                                                   #
    # ------------------------------------------------------------------ #

    def _select_parents(self, population: List,
                        scores: List[float]) -> Tuple[Dict, Dict]:
        """Tournament selection: pick 3 random, take the best."""
        selected = []
        for _ in range(2):
            idx    = np.random.choice(len(population), 3, replace=False)
            winner = max(idx, key=lambda i: scores[i])
            selected.append(population[winner])
        return selected[0], selected[1]

    def _crossover(self, parent1: Dict, parent2: Dict) -> Dict:
        """Uniform crossover: each gene comes from either parent."""
        return {key: (parent1[key] if np.random.random() < 0.5 else parent2[key])
                for key in parent1}

    def _mutate(self, individual: Dict) -> Dict:
        """Randomly tweak one gene with probability = mutation_rate."""
        if np.random.random() >= self.mutation_rate:
            return individual
        key = np.random.choice(list(individual.keys()))
        deltas = {
            'green_duration':  (-5, 5,  10, 40),
            'yellow_duration': (-1, 1,   2,  5),
            'red_duration':    (-3, 3,   5, 15),
            'cycle_length':    (-10, 10, 30, 90),
        }
        lo, hi, mn, mx = deltas[key]
        individual[key] = int(np.clip(individual[key] + np.random.randint(lo, hi + 1),
                                      mn, mx))
        return individual

    # ------------------------------------------------------------------ #
    #  Evolution step                                                      #
    # ------------------------------------------------------------------ #

    def evolve(self, population: List,
               traffic_history: List[Dict]) -> List[Dict]:
        """Run one generation: score → elitism → crossover + mutation."""
        scores = [self.fitness(ind, traffic_history) for ind in population]

        # Keep the 2 best individuals unchanged (elitism)
        elite_idx  = np.argsort(scores)[-2:]
        new_pop    = [population[i] for i in elite_idx]

        while len(new_pop) < self.population_size:
            p1, p2 = self._select_parents(population, scores)
            child  = self._crossover(p1, p2)
            child  = self._mutate(child)
            new_pop.append(child)

        return new_pop

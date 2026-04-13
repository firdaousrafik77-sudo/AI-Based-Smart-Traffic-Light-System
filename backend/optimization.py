import numpy as np
from typing import Dict, List, Tuple
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReinforcementLearningOptimizer:
    """Q-Learning based traffic optimization"""
    
    def __init__(self, learning_rate: float = 0.1, discount_factor: float = 0.95):
        self.q_table = defaultdict(lambda: defaultdict(float))
        self.lr = learning_rate
        self.gamma = discount_factor
        self.epsilon = 0.1
        self.actions = ['NS', 'EW', 'adaptive_cycle', 'emergency']
        
    def get_state(self, traffic: Dict[str, int], skip_counter: Dict[str, int]) -> str:
        total_cars = sum(traffic.values())
        congestion_ratio = max(traffic.values()) / (total_cars + 1)
        
        if total_cars < 30:
            flow_level = 'low'
        elif total_cars < 70:
            flow_level = 'medium'
        else:
            flow_level = 'high'
            
        if congestion_ratio > 0.6:
            imbalance = 'unbalanced'
        else:
            imbalance = 'balanced'
            
        skip_level = max(skip_counter.values())
        if skip_level >= 3:
            skip = 'high_skip'
        elif skip_level >= 1:
            skip = 'med_skip'
        else:
            skip = 'low_skip'
            
        return f"{flow_level}_{imbalance}_{skip}"
    
    def choose_action(self, state: str) -> str:
        if np.random.random() < self.epsilon:
            return np.random.choice(self.actions)
        else:
            state_actions = self.q_table[state]
            if not state_actions:
                return 'NS'
            return max(state_actions, key=state_actions.get)
    
    def update(self, state: str, action: str, reward: float, next_state: str):
        best_next = max(self.q_table[next_state].values()) if self.q_table[next_state] else 0
        current_q = self.q_table[state][action]
        new_q = current_q + self.lr * (reward + self.gamma * best_next - current_q)
        self.q_table[state][action] = new_q
        
    def calculate_reward(self, traffic: Dict[str, int], wait_times: Dict[str, int]) -> float:
        total_wait = sum(wait_times.values())
        total_cars = sum(traffic.values())
        wait_penalty = -total_wait / 100
        throughput_reward = total_cars / 10
        variance = np.var(list(traffic.values()))
        balance_bonus = -variance / 50
        return wait_penalty + throughput_reward + balance_bonus

class GeneticAlgorithmOptimizer:
    """Optimize traffic light timing using genetic algorithms"""
    
    def __init__(self, population_size: int = 20):
        self.population_size = population_size
        self.mutation_rate = 0.1
        
    def create_individual(self) -> Dict[str, int]:
        return {
            'green_duration': np.random.randint(10, 40),
            'yellow_duration': 3,
            'red_duration': np.random.randint(5, 15),
            'cycle_length': np.random.randint(30, 90)
        }
    
    def create_population(self) -> List[Dict[str, int]]:
        return [self.create_individual() for _ in range(self.population_size)]
    
    def fitness(self, individual: Dict[str, int], traffic_data: List[Dict]) -> float:
        total_throughput = 0
        total_wait = 0
        
        for data in traffic_data:
            capacity = individual['green_duration'] * 2
            actual_flow = min(capacity, sum(data.values()))
            throughput = actual_flow / (individual['cycle_length'] + 1)
            total_throughput += throughput
            wait_time = max(0, sum(data.values()) - capacity) * 2
            total_wait += wait_time
        
        return total_throughput / (total_wait + 1)
    
    def select_parents(self, population: List, fitness_scores: List[float]) -> Tuple:
        tournament_size = 3
        selected = []
        
        for _ in range(2):
            tournament_indices = np.random.choice(len(population), tournament_size, replace=False)
            winner_idx = max(tournament_indices, key=lambda i: fitness_scores[i])
            selected.append(population[winner_idx])
        
        return selected[0], selected[1]
    
    def crossover(self, parent1: Dict, parent2: Dict) -> Dict:
        child = {}
        for key in parent1.keys():
            child[key] = parent1[key] if np.random.random() < 0.5 else parent2[key]
        return child
    
    def mutate(self, individual: Dict) -> Dict:
        if np.random.random() < self.mutation_rate:
            key = np.random.choice(list(individual.keys()))
            if key == 'green_duration':
                individual[key] = np.clip(individual[key] + np.random.randint(-5, 5), 10, 40)
            elif key == 'yellow_duration':
                individual[key] = np.clip(individual[key] + np.random.randint(-1, 1), 2, 5)
            elif key == 'red_duration':
                individual[key] = np.clip(individual[key] + np.random.randint(-3, 3), 5, 15)
            elif key == 'cycle_length':
                individual[key] = np.clip(individual[key] + np.random.randint(-10, 10), 30, 90)
        return individual
    
    def evolve(self, population: List, traffic_history: List[Dict]) -> List:
        fitness_scores = [self.fitness(ind, traffic_history) for ind in population]
        elite_indices = np.argsort(fitness_scores)[-2:]
        new_population = [population[i] for i in elite_indices]
        
        while len(new_population) < self.population_size:
            parent1, parent2 = self.select_parents(population, fitness_scores)
            child = self.crossover(parent1, parent2)
            child = self.mutate(child)
            new_population.append(child)
        
        return new_population

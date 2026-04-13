import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from collections import deque
import joblib
import asyncio
from typing import List, Tuple, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrafficPredictor:
    """ML-based traffic flow predictor using ensemble methods"""
    
    def __init__(self, history_window: int = 10):
        self.history_window = history_window
        self.flow_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.congestion_model = GradientBoostingClassifier(n_estimators=50, random_state=42)
        self.scaler = StandardScaler()
        self.training_data = []
        self.is_trained = False
        self.history = {road: deque(maxlen=history_window) for road in ["North", "South", "East", "West"]}
        self.last_prediction = None
        
    def generate_training_data(self, n_samples: int = 10000):
        """Generate synthetic training data for initial training"""
        logger.info(f"Generating {n_samples} training samples...")
        
        data = []
        for _ in range(n_samples):
            hour = np.random.randint(0, 24)
            day = np.random.randint(0, 7)
            weather = np.random.uniform(0, 1)
            event = np.random.choice([0, 1, 2], p=[0.8, 0.15, 0.05])

            base_flow = 20 + 30 * np.sin(np.pi * hour / 12)
            if 7 <= hour <= 9 or 17 <= hour <= 19:
                base_flow *= 1.5

            north_flow = base_flow + np.random.normal(0, 5)
            south_flow = base_flow + np.random.normal(0, 5)
            east_flow = base_flow * 0.7 + np.random.normal(0, 4)
            west_flow = base_flow * 0.7 + np.random.normal(0, 4)

            if event == 1:
                north_flow *= 1.2
                south_flow *= 1.2
            elif event == 2:
                north_flow *= 1.5
                south_flow *= 1.5

            avg_flow = np.mean([north_flow, south_flow, east_flow, west_flow])
            if avg_flow < 25:
                congestion = 0
            elif avg_flow < 50:
                congestion = 1
            else:
                congestion = 2
                
            data.append([hour, day, weather, event, north_flow, south_flow, east_flow, west_flow, congestion])
        
        df = pd.DataFrame(data, columns=['hour', 'day', 'weather', 'event', 
                                        'north', 'south', 'east', 'west', 'congestion'])
        
        X = df[['hour', 'day', 'weather', 'event', 'north', 'south', 'east', 'west']].values
        y_flow = df[['north', 'south', 'east', 'west']].values
        y_congestion = df['congestion'].values
        
        # Split and train flow model
        X_train, X_test, y_flow_train, y_flow_test = train_test_split(X, y_flow, test_size=0.2, random_state=42)
        X_scaled = self.scaler.fit_transform(X_train)
        self.flow_model.fit(X_scaled, y_flow_train)
        
        # Evaluate models
        X_test_scaled = self.scaler.transform(X_test)
        flow_score = self.flow_model.score(X_test_scaled, y_flow_test)
        logger.info(f"Flow model R² score: {flow_score:.3f}")
        
        # Train congestion model
        X_cong_train, X_cong_test, y_cong_train, y_cong_test = train_test_split(X, y_congestion, test_size=0.2, random_state=42)
        X_cong_scaled = self.scaler.transform(X_cong_train)
        self.congestion_model.fit(X_cong_scaled, y_cong_train)
        
        cong_score = self.congestion_model.score(self.scaler.transform(X_cong_test), y_cong_test)
        logger.info(f"Congestion model accuracy: {cong_score:.3f}")
        
        self.is_trained = True
        logger.info("ML models trained successfully")
        
    async def predict_traffic(self, current_traffic: Dict[str, int], 
                             time_of_day: int, day_of_week: int) -> Dict[str, int]:
        """Predict traffic volumes for next 5, 10, 15 minutes"""
        
        if not self.is_trained:
            logger.info("Models not yet trained, generating synthetic training data...")
            self.generate_training_data(5000)
        
        for road, count in current_traffic.items():
            self.history[road].append(count)
        
        weather = 0.8
        event = 0
        
        features = np.array([[time_of_day, day_of_week, weather, event,
                             current_traffic['North'], current_traffic['South'],
                             current_traffic['East'], current_traffic['West']]])
        
        try:
            features_scaled = self.scaler.transform(features)
            predictions = self.flow_model.predict(features_scaled)[0]
            congestion = self.congestion_model.predict(features_scaled)[0]
        except Exception as e:
            logger.warning(f"Prediction error: {e}, using fallback")
            predictions = [current_traffic[road] * 1.1 for road in ['North', 'South', 'East', 'West']]
            congestion = 1
        
        result = {
            'North': max(0, int(predictions[0])), 
            'South': max(0, int(predictions[1])), 
            'East': max(0, int(predictions[2])), 
            'West': max(0, int(predictions[3])), 
            'congestion_level': int(congestion)
        }
        
        self.last_prediction = result
        return result
    
    def get_optimal_duration(self, traffic_volume: int, congestion_level: int) -> int:
        """Calculate optimal green light duration based on predictions"""
        base_duration = 15
        if traffic_volume > 50:
            base_duration = 30
        elif traffic_volume > 30:
            base_duration = 25
        elif traffic_volume < 10:
            base_duration = 10
            
        if congestion_level == 2:
            base_duration = min(40, base_duration + 10)
        elif congestion_level == 0:
            base_duration = max(8, base_duration - 5)
            
        return base_duration

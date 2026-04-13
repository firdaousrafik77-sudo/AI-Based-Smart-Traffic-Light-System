"""SQLite database module for traffic system persistence"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
import logging
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "traffic_system.db"

class TrafficDatabase:
    """Handle database operations for traffic system"""
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_throughput INTEGER,
                average_wait_time REAL,
                congestion_events INTEGER,
                emergency_activations INTEGER
            )
        ''')
        
        # Traffic data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS traffic_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                north INTEGER,
                south INTEGER,
                east INTEGER,
                west INTEGER,
                current_green TEXT
            )
        ''')
        
        # Predictions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                north INTEGER,
                south INTEGER,
                east INTEGER,
                west INTEGER,
                congestion_level INTEGER
            )
        ''')
        
        # Emergency events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS emergency_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT,
                location TEXT,
                priority INTEGER,
                response_time_seconds INTEGER
            )
        ''')
        
        # System log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                level TEXT,
                message TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")
    
    def save_metrics(self, metrics: Dict):
        """Save system metrics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO metrics 
            (total_throughput, average_wait_time, congestion_events, emergency_activations)
            VALUES (?, ?, ?, ?)
        ''', (
            metrics.get('total_throughput', 0),
            metrics.get('average_wait_time', 0),
            metrics.get('congestion_events', 0),
            metrics.get('emergency_activations', 0)
        ))
        
        conn.commit()
        conn.close()
    
    def save_traffic_data(self, traffic: Dict[str, int], current_green: Optional[str] = None):
        """Save traffic data snapshot"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO traffic_data (north, south, east, west, current_green)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            traffic.get('North', 0),
            traffic.get('South', 0),
            traffic.get('East', 0),
            traffic.get('West', 0),
            current_green
        ))
        
        conn.commit()
        conn.close()
    
    def save_prediction(self, prediction: Dict):
        """Save ML prediction"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO predictions (north, south, east, west, congestion_level)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            prediction.get('North', 0),
            prediction.get('South', 0),
            prediction.get('East', 0),
            prediction.get('West', 0),
            prediction.get('congestion_level', 0)
        ))
        
        conn.commit()
        conn.close()
    
    def save_emergency_event(self, event_type: str, location: str, priority: int, response_time: int = 0):
        """Save emergency event"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO emergency_events (event_type, location, priority, response_time_seconds)
            VALUES (?, ?, ?, ?)
        ''', (event_type, location, priority, response_time))
        
        conn.commit()
        conn.close()
    
    def save_log(self, level: str, message: str):
        """Save system log"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO system_logs (level, message)
            VALUES (?, ?)
        ''', (level, message))
        
        conn.commit()
        conn.close()
    
    def get_metrics_summary(self, hours: int = 1) -> Dict:
        """Get metrics summary for last N hours"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f'''
            SELECT 
                AVG(total_throughput) as avg_throughput,
                AVG(average_wait_time) as avg_wait_time,
                SUM(congestion_events) as total_congestion,
                SUM(emergency_activations) as total_emergencies
            FROM metrics
            WHERE timestamp >= datetime('now', '-{hours} hours')
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        return {
            'avg_throughput': row[0] or 0,
            'avg_wait_time': row[1] or 0,
            'total_congestion': row[2] or 0,
            'total_emergencies': row[3] or 0
        }
    
    def get_recent_traffic(self, limit: int = 100) -> List[Dict]:
        """Get recent traffic data"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, north, south, east, west, current_green
            FROM traffic_data
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_emergency_events(self, hours: int = 24) -> List[Dict]:
        """Get emergency events from last N hours"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f'''
            SELECT timestamp, event_type, location, priority, response_time_seconds
            FROM emergency_events
            WHERE timestamp >= datetime('now', '-{hours} hours')
            ORDER BY timestamp DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def cleanup_old_data(self, days: int = 7):
        """Clean up data older than N days"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        tables = ['metrics', 'traffic_data', 'predictions', 'system_logs']
        for table in tables:
            cursor.execute(f'''
                DELETE FROM {table}
                WHERE timestamp < datetime('now', '-{days} days')
            ''')
        
        conn.commit()
        conn.close()
        logger.info(f"Cleaned up data older than {days} days")

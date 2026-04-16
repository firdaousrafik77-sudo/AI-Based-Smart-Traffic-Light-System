"""
Layer 2 - Data: SQLite database
Responsible for reading and writing data to disk.
Nothing here makes decisions — it only stores and retrieves.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class TrafficDatabase:
    """Handles all database operations for the traffic system."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_tables()

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _connect(self):
        """Open a connection with dict-style row access."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        """Create tables if they do not exist yet."""
        conn = self._connect()
        cursor = conn.cursor()

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
        logger.info(f"Database ready at {self.db_path}")

    # ------------------------------------------------------------------ #
    #  Write operations                                                    #
    # ------------------------------------------------------------------ #

    def save_metrics(self, metrics: Dict):
        conn = self._connect()
        conn.execute('''
            INSERT INTO metrics (total_throughput, average_wait_time,
                                 congestion_events, emergency_activations)
            VALUES (?, ?, ?, ?)
        ''', (
            metrics.get('total_throughput', 0),
            metrics.get('average_wait_time', 0),
            metrics.get('congestion_events', 0),
            metrics.get('emergency_activations', 0),
        ))
        conn.commit()
        conn.close()

    def save_traffic_data(self, traffic: Dict[str, int],
                          current_green: Optional[str] = None):
        conn = self._connect()
        conn.execute('''
            INSERT INTO traffic_data (north, south, east, west, current_green)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            traffic.get('North', 0),
            traffic.get('South', 0),
            traffic.get('East', 0),
            traffic.get('West', 0),
            current_green,
        ))
        conn.commit()
        conn.close()

    def save_prediction(self, prediction: Dict):
        conn = self._connect()
        conn.execute('''
            INSERT INTO predictions (north, south, east, west, congestion_level)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            prediction.get('North', 0),
            prediction.get('South', 0),
            prediction.get('East', 0),
            prediction.get('West', 0),
            prediction.get('congestion_level', 0),
        ))
        conn.commit()
        conn.close()

    def save_emergency_event(self, event_type: str, location: str,
                             priority: int, response_time: int = 0):
        conn = self._connect()
        conn.execute('''
            INSERT INTO emergency_events
                (event_type, location, priority, response_time_seconds)
            VALUES (?, ?, ?, ?)
        ''', (event_type, location, priority, response_time))
        conn.commit()
        conn.close()

    def save_log(self, level: str, message: str):
        conn = self._connect()
        conn.execute('INSERT INTO system_logs (level, message) VALUES (?, ?)',
                     (level, message))
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------ #
    #  Read operations                                                     #
    # ------------------------------------------------------------------ #

    def get_metrics_summary(self, hours: int = 1) -> Dict:
        conn = self._connect()
        row = conn.execute(f'''
            SELECT
                AVG(total_throughput)    AS avg_throughput,
                AVG(average_wait_time)   AS avg_wait_time,
                SUM(congestion_events)   AS total_congestion,
                SUM(emergency_activations) AS total_emergencies
            FROM metrics
            WHERE timestamp >= datetime('now', '-{hours} hours')
        ''').fetchone()
        conn.close()
        return {
            'avg_throughput':   row[0] or 0,
            'avg_wait_time':    row[1] or 0,
            'total_congestion': row[2] or 0,
            'total_emergencies':row[3] or 0,
        }

    def get_recent_traffic(self, limit: int = 100) -> List[Dict]:
        conn = self._connect()
        rows = conn.execute('''
            SELECT timestamp, north, south, east, west, current_green
            FROM traffic_data ORDER BY timestamp DESC LIMIT ?
        ''', (limit,)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_emergency_events(self, hours: int = 24) -> List[Dict]:
        conn = self._connect()
        rows = conn.execute(f'''
            SELECT timestamp, event_type, location, priority, response_time_seconds
            FROM emergency_events
            WHERE timestamp >= datetime('now', '-{hours} hours')
            ORDER BY timestamp DESC
        ''').fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def cleanup_old_data(self, days: int = 7):
        """Delete records older than N days to keep the DB small."""
        conn = self._connect()
        for table in ['metrics', 'traffic_data', 'predictions', 'system_logs']:
            conn.execute(f'''
                DELETE FROM {table}
                WHERE timestamp < datetime('now', '-{days} days')
            ''')
        conn.commit()
        conn.close()
        logger.info(f"Cleaned up data older than {days} days")

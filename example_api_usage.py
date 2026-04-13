#!/usr/bin/env python3
"""Example API usage for Smart Traffic System"""

import requests
import asyncio
import json
import time
from datetime import datetime

API_BASE = "http://localhost:3000/api"

class TrafficAPIClient:
    """Client for interacting with Smart Traffic System API"""
    
    def __init__(self, base_url=API_BASE):
        self.base_url = base_url
        self.session = requests.Session()
    
    def start_simulation(self):
        """Start the traffic simulation"""
        print("Starting simulation...")
        response = self.session.post(f"{self.base_url}/simulation/start")
        print(f"  Response: {response.json()}\n")
        return response.json()
    
    def stop_simulation(self):
        """Stop the traffic simulation"""
        print("Stopping simulation...")
        response = self.session.post(f"{self.base_url}/simulation/stop")
        print(f"  Response: {response.json()}\n")
        return response.json()
    
    def get_state(self):
        """Get current system state"""
        response = self.session.get(f"{self.base_url}/state")
        return response.json()
    
    def get_metrics(self):
        """Get system metrics"""
        response = self.session.get(f"{self.base_url}/metrics")
        return response.json()
    
    def get_analytics_summary(self, hours=1):
        """Get analytics summary"""
        response = self.session.get(f"{self.base_url}/analytics/summary", params={"hours": hours})
        return response.json()
    
    def get_traffic_history(self, limit=10):
        """Get recent traffic data"""
        response = self.session.get(f"{self.base_url}/analytics/traffic", params={"limit": limit})
        return response.json()
    
    def get_emergency_events(self, hours=24):
        """Get emergency events"""
        response = self.session.get(f"{self.base_url}/analytics/emergencies", params={"hours": hours})
        return response.json()
    
    def get_recommendations(self):
        """Get optimization recommendations"""
        response = self.session.get(f"{self.base_url}/optimization/recommendations")
        return response.json()
    
    def report_emergency(self, location, emergency_type="accident", priority=3):
        """Report an emergency"""
        print(f"Reporting {emergency_type} at {location}...")
        response = self.session.post(
            f"{self.base_url}/emergency",
            json={
                "type": emergency_type,
                "location": location,
                "priority": priority
            }
        )
        print(f"  Response: {response.json()}\n")
        return response.json()
    
    def update_sensor_data(self, north, south, east, west):
        """Update sensor data"""
        response = self.session.post(
            f"{self.base_url}/sensor/update",
            json={
                "north": north,
                "south": south,
                "east": east,
                "west": west
            }
        )
        return response.json()
    
    def print_dashboard(self, state):
        """Print a nice dashboard of current state"""
        print("\n" + "=" * 60)
        print("🚦 TRAFFIC SYSTEM DASHBOARD")
        print("=" * 60)
        
        traffic = state['traffic']
        flow_rates = state['flow_rates']
        wait_times = state['wait_times']
        current_green = state['current_green']
        metrics = state['metrics']
        
        print(f"\nCurrent Green Light: {current_green}\n")
        
        print("📊 TRAFFIC DATA:")
        print("  Road              Vehicles  Flow Rate  Wait Time")
        print("  " + "-" * 54)
        for road in ['North', 'South', 'East', 'West']:
            indicator = "🟢" if (current_green == 'NS' and road in ['North', 'South']) or \
                               (current_green == 'EW' and road in ['East', 'West']) else "🔴"
            print(f"  {indicator} {road:12}     {traffic[road]:3}      {flow_rates[road]:5.1f}      {wait_times[road]:3}s")
        
        print("\n📈 METRICS:")
        print(f"  Total Throughput:      {metrics['total_throughput']}")
        print(f"  Average Wait Time:     {metrics['average_wait_time']:.1f}s")
        print(f"  Congestion Events:     {metrics['congestion_events']}")
        print(f"  Emergency Activations: {metrics['emergency_activations']}")
        
        if state.get('predictions'):
            print("\n🤖 ML PREDICTIONS (Next Cycle):")
            pred = state['predictions']
            print(f"  North: {pred['North']}, South: {pred['South']}, East: {pred['East']}, West: {pred['West']}")
            congestion_level = ['Low', 'Medium', 'High'][pred.get('congestion_level', 0)]
            print(f"  Congestion Level: {congestion_level}")
        
        print("=" * 60 + "\n")

def main():
    """Main example demonstrating API usage"""
    
    client = TrafficAPIClient()
    
    try:
        print("\n🚦 Smart Traffic System - API Example\n")
        
        # Start simulation
        client.start_simulation()
        time.sleep(2)
        
        # Get initial state
        print("Getting initial state...")
        state = client.get_state()
        client.print_dashboard(state)
        
        # Simulate some time passing
        print("Simulating traffic for 10 seconds...\n")
        for i in range(10):
            time.sleep(1)
            state = client.get_state()
            traffic = state['traffic']
            print(f"[{i+1}] Traffic - N:{traffic['North']} S:{traffic['South']} E:{traffic['East']} W:{traffic['West']}")
        
        # Get current metrics
        print("\n\nGetting current metrics...")
        metrics = client.get_metrics()
        print(json.dumps(metrics, indent=2))
        
        # Get recommendations
        print("\nGetting optimization recommendations...")
        recommendations = client.get_recommendations()
        if recommendations:
            print("Recommendations:")
            for rec in recommendations:
                print(f"  • {rec['type']}: {rec['reason']}")
                print(f"    💡 {rec['suggestion']}")
        else:
            print("✓ No recommendations - system is running optimally")
        
        # Get dashboard
        print("\n\nGetting updated dashboard...")
        state = client.get_state()
        client.print_dashboard(state)
        
        # Report an emergency
        print("Reporting emergency scenario...")
        client.report_emergency("North", "ambulance", priority=3)
        time.sleep(2)
        state = client.get_state()
        client.print_dashboard(state)
        
        # Get traffic history
        print("Getting recent traffic history...")
        history = client.get_traffic_history(limit=5)
        print(f"Recent records: {history['count']}")
        for record in history['data'][:3]:
            print(f"  {record['timestamp']}: N:{record['north']} S:{record['south']} E:{record['east']} W:{record['west']}")
        
        # Get emergency events
        print("\n\nGetting emergency events...")
        emergencies = client.get_emergency_events(hours=24)
        print(f"Emergency events (24h): {emergencies['count']}")
        for event in emergencies['events'][:3]:
            print(f"  {event['timestamp']}: {event['event_type']} at {event['location']}")
        
        # Get analytics summary
        print("\n\nGetting analytics summary...")
        summary = client.get_analytics_summary(hours=1)
        print(json.dumps(summary['data'], indent=2))
        
        # Stop simulation
        print("\n\nStopping simulation...")
        client.stop_simulation()
        
        print("\n✓ Example completed successfully!")
        
    except requests.exceptions.ConnectionError:
        print("✗ Error: Could not connect to API server")
        print("  Make sure the server is running: python run.py")
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        try:
            client.stop_simulation()
        except:
            pass

if __name__ == "__main__":
    main()

# 🚦 Smart Traffic Control System

An AI-powered traffic control system that uses machine learning, reinforcement learning, and genetic algorithms to optimize traffic flow at intersections in real-time.

## Features

✨ **Core Features:**
- 🤖 **ML-Based Traffic Prediction** - RandomForest + GradientBoosting for traffic volume and congestion prediction
- 🧠 **Reinforcement Learning** - Q-Learning based optimizer for adaptive light timing
- 🧬 **Genetic Algorithm Optimization** - Evolutionary optimization of traffic light parameters
- 🚨 **Emergency Response** - Automatic priority handling for emergency vehicles
- 📊 **Real-time Dashboard** - Interactive web interface with live updates via WebSocket
- 💾 **Data Persistence** - SQLite database for metrics, traffic data, and emergency logs
- 📈 **Analytics & Reports** - Historical data and performance analysis

## Quick Start

### Prerequisites
- Python 3.8+
- pip

### Installation

1. **Clone/Download the project**
```bash
cd smart_traffic_system
```

2. **Install dependencies**
```bash
pip install -r backend/requirements.txt
```

3. **Setup configuration** (optional)
```bash
cp .env.example .env
# Edit .env to customize settings
```

4. **Run the system**
```bash
python run.py
```

Or directly with uvicorn:
```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 3000
```

### Access the System
- **Frontend Dashboard**: http://localhost:3000/
- **API Documentation**: http://localhost:3000/docs
- **WebSocket Updates**: ws://localhost:3000/ws

## Project Structure

```
smart_traffic_system/
├── backend/
│   ├── main.py                     # FastAPI server, endpoints, WebSocket
│   ├── traffic_controller.py       # Main intersection controller
│   ├── ml_predictor.py             # ML-based traffic prediction
│   ├── optimization.py             # RL & GA optimizers
│   ├── sensors.py                  # Sensor data models
│   ├── database.py                 # SQLite persistence
│   ├── config.py                   # Configuration management
│   └── requirements.txt            # Python dependencies
├── frontend/
│   └── index.html                  # Interactive web dashboard
├── data/
│   └── traffic_patterns.csv        # Sample traffic data
├── .env                            # Environment configuration (local)
├── .env.example                    # Environment config template
├── run.py                          # Startup script
└── README.md                       # This file
```

## Configuration

Edit `.env` to customize system behavior:

### Server Settings
```env
HOST=0.0.0.0
PORT=3000
DEBUG=False
```

### Traffic Simulation
```env
SPAWN_RATE_RUSH_HOUR=2    # Seconds between spawn (7-9am, 5-7pm)
SPAWN_RATE_NORMAL=3       # Normal hours
SPAWN_RATE_NIGHT=5        # Late night (11pm-5am)
```

### Traffic Light Timing
```env
YELLOW_DURATION=3          # Yellow light seconds
MIN_GREEN_DURATION=10      # Minimum green light
MAX_GREEN_DURATION=40      # Maximum green light
```

### ML Model
```env
ML_TRAINING_SAMPLES=5000   # Samples for initial training
ML_HISTORY_WINDOW=10       # Historical data window
```

### Thresholds
```env
CONGESTION_THRESHOLD=60                 # Vehicles before congestion detected
EMERGENCY_TRAFFIC_THRESHOLD=100         # Total vehicles for emergency
EMERGENCY_SINGLE_ROAD_THRESHOLD=50      # Single road for emergency
```

### Optimization Algorithms
```env
RL_LEARNING_RATE=0.1       # Q-Learning learning rate
RL_DISCOUNT_FACTOR=0.95    # Q-Learning discount factor
GA_POPULATION_SIZE=20      # Genetic algorithm population
GA_MUTATION_RATE=0.1       # GA mutation probability
```

## API Endpoints

### Simulation Control
- `POST /api/simulation/start` - Start traffic simulation
- `POST /api/simulation/stop` - Stop simulation
- `GET /api/state` - Get current system state (with predictions)

### Emergency & Sensors
- `POST /api/emergency` - Report emergency
- `POST /api/sensor/update` - Update sensor data

### Analytics & Reports
- `GET /api/metrics` - Get system metrics
- `GET /api/analytics/summary?hours=1` - Get analytics summary
- `GET /api/analytics/traffic?limit=100` - Get traffic history
- `GET /api/analytics/emergencies?hours=24` - Get emergency events
- `GET /api/optimization/recommendations` - Get optimization recommendations

### WebSocket
- `WS /ws` - Real-time updates

## System Architecture

### Traffic Controller
The `TrafficIntersection` class manages:
- Four roads (North, South, East, West)
- Two axes (NS and EW)
- Sensor data processing
- Light state management (Green/Yellow/Red)
- Wait time tracking
- Performance metrics

### ML Prediction Pipeline
1. **RandomForestRegressor** - Predicts traffic flow (vehicles per road)
2. **GradientBoostingClassifier** - Predicts congestion level (0-2)
3. **StandardScaler** - Feature normalization
4. Training Data: Synthetic data generation based on:
   - Time of day (hourly patterns)
   - Day of week
   - Weather conditions
   - Traffic events (0 = normal, 1 = moderate, 2 = heavy)

### Reinforcement Learning Optimizer
- **Algorithm**: Q-Learning
- **State Space**: Flow level (low/medium/high), Congestion balance, Skip counter
- **Actions**: NS, EW, adaptive_cycle, emergency
- **Reward Function**: Minimizes wait time, maximizes throughput, balances traffic

### Genetic Algorithm Optimizer
- **Population**: Traffic light timing configurations
- **Fitness**: Throughput / (Wait time + 1)
- **Operations**: Tournament selection, crossover, mutation
- **Genes**: Green duration, yellow duration, red duration, cycle length

## Database Schema

### Tables
- **metrics** - System performance over time
- **traffic_data** - Vehicle counts and light state
- **predictions** - ML predictions
- **emergency_events** - Emergency reports
- **system_logs** - Application logs

## WebSocket Message Format

Received every second when simulation is running:
```json
{
  "intersection": "Main Intersection",
  "state": "green",
  "current_green": "NS",
  "traffic": {"North": 15, "South": 12, "East": 8, "West": 10},
  "flow_rates": {"North": 2.5, "South": 2.0, ...},
  "wait_times": {"North": 40, "South": 35, ...},
  "metrics": {
    "total_throughput": 145,
    "average_wait_time": 35.2,
    "congestion_events": 3,
    "emergency_activations": 0
  },
  "predictions": {
    "North": 18, "South": 14, "East": 10, "West": 12,
    "congestion_level": 1
  },
  "timestamp": "2024-04-12T14:30:45.123456"
}
```

## Performance Metrics

The system tracks:
- **Total Throughput** - Total vehicles passed through intersection
- **Average Wait Time** - Mean waiting time for vehicles
- **Congestion Events** - Count of high-traffic periods
- **Emergency Activations** - Count of emergency responses

## Troubleshooting

### Port Already in Use
```bash
# Change port in .env
PORT=8002
```

### Database Issues
```bash
# Delete old database to reset
rm traffic_system.db
```

### ML Model Training Slow
```bash
# Reduce training samples in .env
ML_TRAINING_SAMPLES=2000
```

### Import Errors
```bash
# Ensure PYTHONPATH includes backend
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"
```

## Performance Tips

1. **Increase Green Duration** during peak hours → adjust `MAX_GREEN_DURATION`
2. **Enable RL Learning** → let it optimize over 24+ hours
3. **Monitor Congestion** → use `/api/analytics/emergencies` to identify problem times
4. **Tune Spawn Rates** → match your actual traffic patterns
5. **Database Cleanup** → automatic, runs daily

## Future Enhancements

- 🗺️ Multi-intersection coordination
- 📡 Real IoT sensor integration
- 🌡️ Weather impact modeling
- 🚗 Vehicle type classification
- 📱 Mobile app for incident reporting
- 🎯 Target-based optimization
- 🔄 Adaptive learning from real patterns

## License

MIT License - Feel free to use and modify!

## Support

For issues or questions:
1. Check the API docs: http://localhost:3000/docs
2. Review logs: `traffic_system.log`
3. Check database: `traffic_system.db` (SQLite)

## System Requirements

- **CPU**: Minimal (suitable for embedded systems)
- **RAM**: 512MB+ (for Python + ML models)
- **Storage**: 100MB+ (for database logs)
- **Network**: For WebSocket dashboard only

---

**Version**: 1.0.0  
**Last Updated**: April 2024

🚦 **Optimize your traffic. Reduce congestion. Save time.**

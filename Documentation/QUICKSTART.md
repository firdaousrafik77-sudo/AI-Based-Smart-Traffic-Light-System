# 🚀 Quick Start Guide

## 30-Second Setup

```bash
# 1. Install dependencies
pip install -r backend/requirements.txt

# 2. Run the system
python run.py

# 3. Open browser
# http://localhost:3000
```

## What's Running?

✅ **Backend API** - http://localhost:3000/api  
✅ **Frontend Dashboard** - http://localhost:3000/  
✅ **API Documentation** - http://localhost:3000/docs  
✅ **WebSocket** - ws://localhost:3000/ws  

## Your First Steps

### 1️⃣ Open Dashboard
Open http://localhost:3000/ in your browser

### 2️⃣ Start Simulation
Click **"▶ Start Simulation"** button

### 3️⃣ Watch Traffic Flow
- See vehicles accumulate on different roads
- Watch traffic lights adapt automatically
- Check real-time metrics

### 4️⃣ Test Emergency Mode
Click **"🚨 Emergency Mode"** button to:
- Trigger emergency vehicle response
- See lights change automatically
- View system reacting to events

## API Quick Examples

### Get Current State
```bash
curl http://localhost:3000/api/state
```

### Start Simulation
```bash
curl -X POST http://localhost:3000/api/simulation/start
```

### Report Emergency
```bash
curl -X POST http://localhost:3000/api/emergency \
  -H "Content-Type: application/json" \
  -d '{
    "type": "ambulance",
    "location": "North",
    "priority": 3
  }'
```

### Get Metrics
```bash
curl http://localhost:3000/api/metrics
```

### Get Recommendations
```bash
curl http://localhost:3000/api/optimization/recommendations
```

### View Traffic History
```bash
curl http://localhost:3000/api/analytics/traffic?limit=10
```

## Test All Features

```bash
python example_api_usage.py
```

This will:
- Start and stop simulation
- Show real-time data
- Report emergencies
- Display analytics
- Test all endpoints

## Configuration

### Change Port
Edit `.env`:
```env
PORT=8002
```

### Change Log Level
Edit `.env`:
```env
LOG_LEVEL=DEBUG
```

### Customize Traffic Rates
Edit `.env`:
```env
SPAWN_RATE_NORMAL=2
SPAWN_RATE_RUSH_HOUR=1
```

See `.env.example` for all options.

## Using Docker

```bash
# One command
docker-compose up

# Then visit http://localhost:3000
```

## Logs & Debugging

### View Logs
```bash
tail -f traffic_system.log
```

### Check API Docs
http://localhost:3000/docs

### View Database
```bash
sqlite3 traffic_system.db
.tables
SELECT COUNT(*) FROM traffic_data;
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 3000 in use | Change PORT in `.env` |
| ModuleNotFoundError | Run `pip install -r backend/requirements.txt` |
| Database locked | Delete `traffic_system.db*` files |
| Slow startup | Reduce `ML_TRAINING_SAMPLES` in `.env` |
| WebSocket won't connect | Check firewall allows port 3000 |

## System Architecture

```
User Browser
    ↓
[Frontend Dashboard - HTML/JS/CSS]
    ↓
[FastAPI Backend] ← WebSocket updates
    ├── Traffic Controller
    ├── ML Predictor
    ├── RL Optimizer
    ├── GA Optimizer
    └── SQLite Database
```

## Key Components

🚦 **Traffic Intersection**
- 4 roads (N, S, E, W)
- 2 axes (NS, EW)
- Real-time vehicle tracking

🤖 **Machine Learning**
- Predicts traffic volume
- Detects congestion level
- Adapts signal timing

🧠 **Reinforcement Learning**
- Learns optimal decisions
- Q-Learning algorithm
- Improves over time

🧬 **Genetic Algorithm**
- Optimizes parameters
- Evolves solutions
- Balances conflicting goals

📊 **Database**
- Stores all metrics
- Tracks emergency events
- Enables analytics

## Performance

- **Throughput**: ~200-300 vehicles/hour per intersection
- **Average Wait**: 20-40 seconds (depends on traffic)
- **Response Time**: <100ms for API calls
- **WebSocket**: Real-time updates every second
- **Memory**: ~200-300MB runtime

## Next Steps

After getting comfortable with the system:

1. **Explore API** - http://localhost:3000/docs
2. **Check Analytics** - http://localhost:3000/api/analytics/traffic
3. **Monitor Metrics** - http://localhost:3000/api/metrics
4. **Read README** - See full documentation
5. **Deploy** - See DEPLOYMENT.md for production

## Need Help?

- 📖 Read README.md
- 🚀 See DEPLOYMENT.md
- 🔧 Check COMPLETION_SUMMARY.md
- 📊 View API docs at /docs
- 🐛 Check logs: `tail -f traffic_system.log`

## Common Commands

```bash
# Start system
python run.py

# Stop (Ctrl+C)

# Install (if needed)
pip install -r backend/requirements.txt

# View logs
tail -f traffic_system.log

# Reset database
rm traffic_system.db

# Test API
python example_api_usage.py

# Docker
docker-compose up
docker-compose down
docker-compose logs -f
```

## What's Included?

✨ Full-stack traffic control system
✨ ML-based predictions
✨ Real-time dashboard
✨ REST API
✨ WebSocket updates
✨ Database persistence
✨ Docker support
✨ Comprehensive docs

## Ready?

```bash
python run.py
```

Then open: **http://localhost:3000/** 🚦

---

**Enjoy optimizing traffic!** 🎉

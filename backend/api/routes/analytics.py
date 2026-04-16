"""
Layer 5 - API Routes: Metrics, analytics, and optimization recommendations
"""

import logging
from datetime import datetime

from fastapi import APIRouter

from ..dependencies import intersection, db, rl_optimizer

router = APIRouter(prefix="/api", tags=["analytics"])
logger = logging.getLogger(__name__)


@router.get("/metrics")
async def get_metrics():
    """Live performance counters (throughput, wait time, congestion events)."""
    return intersection.metrics


@router.get("/analytics/summary")
async def get_analytics_summary(hours: int = 1):
    """Aggregate metrics stored in the database for the last N hours."""
    summary = db.get_metrics_summary(hours)
    return {
        "hours":     hours,
        "data":      summary,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/analytics/traffic")
async def get_traffic_history(limit: int = 100):
    """Most recent traffic snapshots from the database."""
    data = db.get_recent_traffic(limit)
    return {"count": len(data), "data": data}


@router.get("/analytics/emergencies")
async def get_emergency_history(hours: int = 24):
    """Emergency events logged in the database for the last N hours."""
    events = db.get_emergency_events(hours)
    return {"hours": hours, "count": len(events), "events": events}


@router.get("/optimization/recommendations")
async def get_recommendations():
    """
    Generate plain-language suggestions based on current metrics and
    what the RL agent has learned so far.
    """
    recommendations = []
    traffic = intersection.get_status()['traffic']
    ns_total = traffic.get('North', 0) + traffic.get('South', 0)
    ew_total = traffic.get('East',  0) + traffic.get('West',  0)

    if intersection.metrics['average_wait_time'] > 30:
        recommendations.append({
            "type":       "increase_green_duration",
            "reason":     f"High average wait time: {intersection.metrics['average_wait_time']:.1f}s",
            "suggestion": "Increase MAX_GREEN_DURATION in .env during peak hours",
        })

    if intersection.metrics['congestion_events'] > 10:
        recommendations.append({
            "type":       "reroute_traffic",
            "reason":     f"Multiple congestion events: {intersection.metrics['congestion_events']}",
            "suggestion": "Consider dynamic lane management or alternate routes",
        })

    if ns_total > ew_total * 1.5:
        recommendations.append({
            "type":       "balance_traffic",
            "reason":     f"NS has {ns_total} vehicles vs EW {ew_total}",
            "suggestion": "Extend green time for the North-South axis",
        })
    elif ew_total > ns_total * 1.5:
        recommendations.append({
            "type":       "balance_traffic",
            "reason":     f"EW has {ew_total} vehicles vs NS {ns_total}",
            "suggestion": "Extend green time for the East-West axis",
        })

    if rl_optimizer.q_table:
        # Build a per-action best-Q map by iterating all states in the table.
        # q_table structure: {state_str: {action_str: q_value}}
        best_q_per_action: dict = {}
        for state_actions in rl_optimizer.q_table.values():
            for action, q_val in state_actions.items():
                if q_val > best_q_per_action.get(action, float('-inf')):
                    best_q_per_action[action] = q_val

        if best_q_per_action:
            best_action = max(best_q_per_action, key=best_q_per_action.get)
            recommendations.append({
                "type":       "rl_suggestion",
                "reason":     f"Q-Learning has explored {len(rl_optimizer.q_table)} states",
                "suggestion": f"Learned optimal action: {best_action} "
                              f"(Q={best_q_per_action[best_action]:.2f})",
            })

    return recommendations

// Smart Traffic Control System - Optimized JavaScript
let simulationActive = false;
let ws = null;

async function startSimulation() {
  try {
    const response = await fetch('/api/simulation/start', { method: 'POST' });
    const data = await response.json();
    simulationActive = true;
    showNotification('Simulation started successfully!', 'success');
    connectWebSocket();
  } catch (error) {
    showNotification('Failed to start simulation', 'error');
  }
}

async function stopSimulation() {
  try {
    const response = await fetch('/api/simulation/stop', { method: 'POST' });
    simulationActive = false;
    if (ws) ws.close();
    showNotification('Simulation stopped', 'info');
  } catch (error) {
    // Silent error handling
  }
}

async function triggerEmergency() {
  // Create a modal dialog for better UX
  showEmergencyModal();
}

function showEmergencyModal() {
  // Remove existing modal if any
  const existingModal = document.getElementById('emergencyModal');
  if (existingModal) existingModal.remove();
  
  const modal = document.createElement('div');
  modal.id = 'emergencyModal';
  modal.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.85);
    backdrop-filter: blur(8px);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 10000;
    animation: fadeIn 0.2s ease;
  `;
  
  modal.innerHTML = `
    <div style="background: linear-gradient(135deg, #1a2a3a, #0d1c2a); border-radius: 28px; padding: 28px; max-width: 420px; width: 90%; border: 2px solid #e74c3c; box-shadow: 0 20px 40px rgba(0,0,0,0.5);">
      <h2 style="color: #e74c3c; margin-bottom: 20px; display: flex; align-items: center; gap: 10px;">
        <span>🚨</span> EMERGENCY OVERRIDE
      </h2>
      <p style="margin-bottom: 20px; opacity: 0.9;">Select emergency location to get immediate green light:</p>
      
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 24px;">
        <button id="emergencyNorth" style="background: #e74c3c; padding: 14px; font-size: 1.1rem; border: none; border-radius: 12px; cursor: pointer; color: white; font-weight: bold;">⬆️ NORTH</button>
        <button id="emergencySouth" style="background: #e74c3c; padding: 14px; font-size: 1.1rem; border: none; border-radius: 12px; cursor: pointer; color: white; font-weight: bold;">⬇️ SOUTH</button>
        <button id="emergencyEast" style="background: #e74c3c; padding: 14px; font-size: 1.1rem; border: none; border-radius: 12px; cursor: pointer; color: white; font-weight: bold;">➡️ EAST</button>
        <button id="emergencyWest" style="background: #e74c3c; padding: 14px; font-size: 1.1rem; border: none; border-radius: 12px; cursor: pointer; color: white; font-weight: bold;">⬅️ WEST</button>
      </div>
      
      <div style="display: flex; gap: 12px; margin-bottom: 20px;">
        <select id="emergencyType" style="flex: 1; padding: 12px; border-radius: 12px; background: #2a3a4a; color: white; border: 1px solid #e74c3c;">
          <option value="ambulance">🚑 Ambulance</option>
          <option value="fire_truck">🔥 Fire Truck</option>
          <option value="accident">💥 Accident</option>
          <option value="police">🚔 Police</option>
        </select>
      </div>
      
      <button id="emergencyCancel" style="background: #555; width: 100%; padding: 12px; border: none; border-radius: 12px; cursor: pointer; color: white; font-weight: bold; margin-top: 8px;">Cancel</button>
    </div>
  `;
  
  document.body.appendChild(modal);
  
  // Add animation keyframes if not present
  if (!document.querySelector('#emergencyAnimations')) {
    const style = document.createElement('style');
    style.id = 'emergencyAnimations';
    style.textContent = `
      @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
      }
      @keyframes slideInLeft {
        from { transform: translateX(-100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }
      @keyframes slideOutLeft {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(-100%); opacity: 0; }
      }
      @keyframes emergencyFlash {
        0%, 100% { background: rgba(231,76,60,0.3); }
        50% { background: rgba(231,76,60,0.6); }
      }
    `;
    document.head.appendChild(style);
  }
  
  // Add event listeners
  const locations = ['North', 'South', 'East', 'West'];
  locations.forEach(loc => {
    const btn = document.getElementById(`emergency${loc}`);
    if (btn) {
      btn.onclick = () => {
        const emergencyType = document.getElementById('emergencyType').value;
        modal.remove();
        sendEmergencyRequest(loc, emergencyType);
      };
      btn.onmouseenter = () => { btn.style.transform = 'scale(1.02)'; btn.style.transition = 'transform 0.2s'; };
      btn.onmouseleave = () => { btn.style.transform = 'scale(1)'; };
    }
  });
  
  document.getElementById('emergencyCancel').onclick = () => modal.remove();
  document.getElementById('emergencyCancel').onmouseenter = (e) => { e.target.style.transform = 'scale(1.02)'; };
  document.getElementById('emergencyCancel').onmouseleave = (e) => { e.target.style.transform = 'scale(1)'; };
  
  // Close on escape key
  const closeOnEscape = (e) => {
    if (e.key === 'Escape') {
      modal.remove();
      document.removeEventListener('keydown', closeOnEscape);
    }
  };
  document.addEventListener('keydown', closeOnEscape);
}

async function sendEmergencyRequest(location, emergencyType) {
  showNotification(`🚨 SENDING EMERGENCY: ${emergencyType.toUpperCase()} at ${location}...`, 'warning');
  
  try {
    const response = await fetch('/api/emergency', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        type: emergencyType, 
        location: location, 
        priority: 3 
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    
    // Visual feedback - flash the traffic light card for the emergency direction
    flashEmergencyLight(location);
    
    showNotification(`🚨 ${data.action}`, 'emergency');
    
    // Also show a persistent banner for emergency active
    showEmergencyBanner(location, emergencyType);
    
  } catch (error) {
    console.error('Emergency request failed:', error);
    showNotification(`❌ Failed to activate emergency: ${error.message}`, 'error');
  }
}

function flashEmergencyLight(location) {
  // Find the card for the location and flash it
  const cards = document.querySelectorAll('.traffic-card');
  for (const card of cards) {
    if (card.querySelector('.road-name')?.innerText.includes(location)) {
      const originalBorder = card.style.border;
      const originalBg = card.style.background;
      card.style.transition = 'all 0.1s ease';
      let flashes = 0;
      const flashInterval = setInterval(() => {
        if (flashes >= 6) {
          clearInterval(flashInterval);
          card.style.border = originalBorder;
          card.style.background = originalBg;
          return;
        }
        if (flashes % 2 === 0) {
          card.style.border = '3px solid #e74c3c';
          card.style.background = 'rgba(231,76,60,0.3)';
        } else {
          card.style.border = originalBorder;
          card.style.background = originalBg;
        }
        flashes++;
      }, 200);
      break;
    }
  }
}

function showEmergencyBanner(location, emergencyType) {
  // Remove existing banner
  const existingBanner = document.getElementById('activeEmergencyBanner');
  if (existingBanner) existingBanner.remove();
  
  const banner = document.createElement('div');
  banner.id = 'activeEmergencyBanner';
  banner.style.cssText = `
    position: fixed;
    top: 80px;
    left: 20px;
    right: 20px;
    background: linear-gradient(135deg, #e74c3c, #c0392b);
    padding: 16px 24px;
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    z-index: 9999;
    box-shadow: 0 8px 20px rgba(0,0,0,0.3);
    animation: slideInLeft 0.3s ease;
    font-weight: bold;
  `;
  
  const icon = emergencyType === 'ambulance' ? '🚑' : emergencyType === 'fire_truck' ? '🔥' : emergencyType === 'accident' ? '💥' : '🚔';
  
  banner.innerHTML = `
    <div style="display: flex; align-items: center; gap: 12px;">
      <span style="font-size: 2rem;">${icon}</span>
      <div>
        <div style="font-size: 1rem;">EMERGENCY ACTIVE</div>
        <div style="font-size: 0.85rem; opacity: 0.9;">${emergencyType.toUpperCase()} at ${location} • GREEN LIGHT active</div>
      </div>
    </div>
    <button id="dismissEmergencyBanner" style="background: rgba(255,255,255,0.2); border: none; padding: 8px 16px; border-radius: 20px; color: white; cursor: pointer;">Dismiss</button>
  `;
  
  document.body.appendChild(banner);
  
  document.getElementById('dismissEmergencyBanner').onclick = () => {
    banner.remove();
  };
  
  // Auto-dismiss after 10 seconds
  setTimeout(() => {
    if (document.getElementById('activeEmergencyBanner')) {
      banner.style.animation = 'slideOutLeft 0.3s ease';
      setTimeout(() => banner.remove(), 300);
    }
  }, 10000);
}

function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

  ws.onopen = () => {};
  ws.onmessage = (event) => updateDashboard(JSON.parse(event.data));
  ws.onerror = () => {};
  ws.onclose = () => {
    if (simulationActive) setTimeout(connectWebSocket, 3000);
  };
}

async function updateDashboard(data) {
  updateTrafficDashboard(data);
  updateMetrics(data);
  if (data.predictions) updatePredictions(data);
  await updateRecommendations();
  await updateEmergencyLog();
}

function updateTrafficDashboard(data) {
  const dashboard = document.getElementById('dashboard');
  const roads = ['North', 'South', 'East', 'West'];
  
  // Use per-road light states from backend if available
  const hasLightStates = data.light_states && typeof data.light_states === 'object';

  let congestionRoads = [];  // Track roads with heavy traffic for warnings

  dashboard.innerHTML = roads.map(road => {
    const traffic = data.traffic[road];
    const flowRate = data.flow_rates[road];
    const waitTime = data.wait_times[road];
    
    // Get actual light state from backend
    let lightState = 'red';  // default
    if (hasLightStates && data.light_states[road]) {
      lightState = data.light_states[road];  // 'green', 'yellow', or 'red'
    } else {
      // Fallback for old backend or mock mode
      const isGreen = data.current_green === 'NS' ?
        (road === 'North' || road === 'South') :
        (road === 'East' || road === 'West');
      lightState = isGreen ? 'green' : 'red';
    }
    
    // Map light state to display text and styling
    let statusText = '';
    let statusClass = '';
    let cardClass = '';
    
    if (lightState === 'green') {
      statusText = '🟢 GREEN';
      statusClass = 'status-active';
      cardClass = 'green-highlight';
    } else if (lightState === 'yellow') {
      statusText = '🟡 YELLOW';
      statusClass = 'status-warning';
      cardClass = 'yellow-highlight';
    } else {
      statusText = '🔴 RED';
      statusClass = 'status-inactive';
      cardClass = 'red-highlight';
    }
    
    // Track heavy traffic for congestion warnings
    if (traffic >= 18) {
      congestionRoads.push({ road, traffic, level: 'critical' });
    } else if (traffic >= 12) {
      congestionRoads.push({ road, traffic, level: 'moderate' });
    }
    
    // Calculate traffic load percentage (0-55 vehicles = 0-100%)
    const loadPercentage = Math.min(100, (traffic / 55) * 100);
    
    // Build congestion warning badge
    let congestionWarning = '';
    if (traffic >= 12) {
      const warningLevel = traffic >= 18 ? 'critical' : 'active';
      congestionWarning = `<div class="congestion-warning ${warningLevel}"><span>⚠️ CONGESTION</span></div>`;
    }

    return `<div class="traffic-card ${cardClass}">
      <div class="road-name">${road}<span class="status-badge ${statusClass}">${statusText}</span></div>
      <div class="vehicle-count">🚗 ${traffic}</div>
      <div class="traffic-load-bar">
        <div class="traffic-load-bar-fill" style="width: ${loadPercentage}%"></div>
      </div>
      <div class="flow-rate">📊 Flow: ${flowRate.toFixed(1)} veh/min</div>
      <div class="wait-time">⏱ Wait: ${waitTime}s</div>
      ${congestionWarning}
    </div>`;
  }).join('');
  
  // Update heavy traffic warning section
  updateHeavyTrafficSection(congestionRoads);
  
  // Update emergency indicators
  updateEmergencyIndicators(data);
}

function updateMetrics(data) {
  const metrics = document.getElementById('metrics');
  const m = data.metrics;
  metrics.innerHTML = `
    <div class="metric-card"><div>🚦 Current Green</div><div class="metric-value">${data.current_green || 'None'}</div></div>
    <div class="metric-card"><div>📈 Total Throughput</div><div class="metric-value">${m.total_throughput}</div></div>
    <div class="metric-card"><div>⏱ Avg Wait Time</div><div class="metric-value">${m.average_wait_time.toFixed(1)}s</div></div>
    <div class="metric-card"><div>⚠️ Congestion Events</div><div class="metric-value">${m.congestion_events}</div></div>
    <div class="metric-card"><div>🚨 Emergency Activations</div><div class="metric-value">${m.emergency_activations}</div></div>
  `;
}

function updatePredictions(data) {
  const predictionsHtml = `<div class="predictions">
    <strong>🤖 ML Predictions (Next Cycle):</strong><br>
    ${Object.entries(data.predictions).map(([road, count]) =>
      `<span class="prediction-item">${road}: ${count} cars</span>`
    ).join('')}
    <br><small>Congestion Level: ${getCongestionLevel(data.predictions.congestion_level)}</small>
  </div>`;
  document.querySelector('.card:first-child')?.insertAdjacentHTML('beforeend', predictionsHtml);
}

async function updateRecommendations() {
  try {
    const response = await fetch('/api/optimization/recommendations');
    const recommendations = await response.json();
    const recommendationsList = document.getElementById('recommendations-list');

    if (recommendations.length === 0) {
      recommendationsList.innerHTML = '<p>✅ No recommendations at this time. System is running optimally.</p>';
    } else {
      recommendationsList.innerHTML = recommendations.map(rec =>
        `<div class="recommendation-item"><strong>${rec.type}:</strong> ${rec.reason}<br><small>💡 ${rec.suggestion}</small></div>`
      ).join('');
    }
  } catch (error) {
    // Silent error handling
  }
}

function getCongestionLevel(level) {
  return ['Low', 'Medium', 'High'][level] || 'Unknown';
}

// Update heavy traffic warning section
function updateHeavyTrafficSection(congestionRoads) {
  const section = document.getElementById('heavy-traffic-section');
  const roadsList = document.getElementById('congestion-roads-list');
  
  if (!section || !roadsList) return;  // Skip if elements don't exist
  
  if (congestionRoads.length === 0) {
    section.classList.remove('active');
  } else {
    section.classList.add('active');
    roadsList.innerHTML = congestionRoads.map(({ road, traffic, level }) => `
      <div class="congestion-road-item">
        ${road}: ${traffic} vehicles ${level === 'critical' ? '🔴 CRITICAL' : '🟠 MODERATE'}
      </div>
    `).join('');
  }
}

function updateEmergencyIndicators(data) {
  const emergencySection = document.getElementById('emergency-section');
  const emergencyList = document.getElementById('emergency-list');
  
  if (!emergencySection || !emergencyList) return;  // Skip if elements don't exist
  
  if (!data.active_emergencies || data.active_emergencies.length === 0) {
    emergencySection.classList.remove('active');
  } else {
    emergencySection.classList.add('active');
    emergencyList.innerHTML = data.active_emergencies.map(emergency => {
      const icon = getEmergencyIcon(emergency.type);
      const priority = emergency.priority || 1;
      const priorityClass = priority >= 3 ? 'high-priority' : priority >= 2 ? 'medium-priority' : 'low-priority';
      
      return `<div class="emergency-item ${priorityClass}">
        <div class="emergency-icon">${icon}</div>
        <div class="emergency-details">
          <div class="emergency-type">${emergency.type.toUpperCase()}</div>
          <div class="emergency-location">📍 ${emergency.location}</div>
          <div class="emergency-time">⏰ ${new Date(emergency.timestamp).toLocaleTimeString()}</div>
        </div>
      </div>`;
    }).join('');
  }
}

function getEmergencyIcon(type) {
  const icons = {
    'accident': '💥',
    'ambulance': '🚨',
    'fire_truck': '🔥',
    'police': '🚔',
    'congestion': '⚠️',
    'time_based': '⏰',
    'weather': '🌧️',
    'predictive': '🔮',
    'manual': '👤'
  };
  return icons[type] || '🚨';
}

async function updateEmergencyLog() {
  try {
    const response = await fetch('/api/emergencies');
    const data = await response.json();
    const logList = document.getElementById('emergency-log-list');
    
    if (!logList) return;  // Skip if element doesn't exist
    
    const emergencies = data.emergencies || [];
    
    if (emergencies.length === 0) {
      logList.innerHTML = '<div class="emergency-log-item"><div class="emergency-log-type">NO EMERGENCIES</div><div class="emergency-log-details">System monitoring active • All roads clear</div></div>';
    } else {
      // Sort by timestamp (most recent first) and take last 10
      const recentEmergencies = emergencies
        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
        .slice(0, 10);
      
      logList.innerHTML = recentEmergencies.map(emergency => {
        const icon = getEmergencyIcon(emergency.type);
        const time = new Date(emergency.timestamp).toLocaleString();
        
        return `<div class="emergency-log-item ${emergency.type}">
          <div class="emergency-log-type">${icon} ${emergency.type.toUpperCase()}</div>
          <div class="emergency-log-details">📍 ${emergency.location} • ⏰ ${time} • ${emergency.description || 'Emergency protocol activated'}</div>
        </div>`;
      }).join('');
    }
  } catch (error) {
    // Silent error handling for emergency log
  }
}

function showNotification(message, type) {
  const notification = document.createElement('div');
  notification.className = 'notification';
  if (type === 'success') notification.style.background = '#4CAF50';
  else if (type === 'error') notification.style.background = '#f44336';
  else if (type === 'warning') notification.style.background = '#ff9800';
  else if (type === 'emergency') notification.style.background = '#e74c3c';
  else notification.style.background = '#2196F3';
  notification.textContent = message;
  document.body.appendChild(notification);

  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease';
    setTimeout(() => notification.remove(), 300);
  }, 4000);
}

// Add slideOut animation
const slideOutStyle = document.createElement('style');
slideOutStyle.textContent = `
  @keyframes slideOut {
    from { transform: translateX(0); opacity: 1; }
    to { transform: translateX(100%); opacity: 0; }
  }
  .notification {
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 14px 24px;
    color: white;
    border-radius: 60px;
    font-weight: 500;
    z-index: 2000;
    box-shadow: 0 6px 18px black;
    backdrop-filter: blur(8px);
    animation: slideInRight 0.25s ease-out;
  }
  @keyframes slideInRight {
    from { transform: translateX(120%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
  }
`;
document.head.appendChild(slideOutStyle);

// Initial load
updateRecommendations();
updateEmergencyLog();
setInterval(updateRecommendations, 30000);
setInterval(updateEmergencyLog, 10000); // Update emergency log more frequently
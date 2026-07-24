<template>
  <div class="app-container">
    <header>
      <div class="logo">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--accent-color);">
          <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14v-4z"></path>
          <rect x="3" y="6" width="12" height="12" rx="2" ry="2"></rect>
        </svg>
        Web<span>HMI</span>
      </div>
      <div class="status-badge" :class="{ connected: status.connected }">
        <div class="status-dot"></div>
        <span>{{ status.connected ? 'Connected' : 'Disconnected' }}</span>
      </div>
    </header>

    <main>
      <CameraStream :frame="frame" :fps="fps" />

      <div class="side-panel">
        <Controls @connect="handleConnect" @disconnect="handleDisconnect" />
        <TelemetryPanel :status="status" />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import CameraStream from './components/CameraStream.vue'
import Controls from './components/Controls.vue'
import TelemetryPanel from './components/TelemetryPanel.vue'

const frame = ref(null)
const fps = ref(0)
const status = ref({
  connected: false,
  ip: null,
  temperature: null,
  exposure: 0
})

let ws = null
let framesReceived = 0
let lastFpsTime = Date.now()
let reconnectTimeout = null

const connectWebSocket = () => {
  // If running via dev server, point to local backend API (assuming proxy or explicit URL)
  // Usually the vite server is on 5173, backend is on 8000 or 8024
  const wsUrl = `ws://localhost:8024/camera/ws`
  
  console.log(`Connecting to ${wsUrl}...`)
  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    console.log('WebSocket Connected')
    status.value.connected = true
    
    ws.send(JSON.stringify({
      action: "subscribe",
      types: ["video", "telemetry"]
    }))
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      
      if (data.action === "video" && data.frame) {
        frame.value = data.frame
        framesReceived++
        
        const now = Date.now()
        if (now - lastFpsTime >= 1000) {
          fps.value = framesReceived
          framesReceived = 0
          lastFpsTime = now
        }
      } 
      else if (data.action === "telemetry" && data.status) {
        // Only update telemetry values, preserve websocket connection state
        status.value = {
          ...status.value,
          ...data.status
        }
      }
    } catch (e) {
      console.error("Error parsing message", e)
    }
  }

  ws.onclose = () => {
    console.log('WebSocket Disconnected')
    status.value.connected = false
    frame.value = null
    fps.value = 0
    
    reconnectTimeout = setTimeout(connectWebSocket, 3000)
  }

  ws.onerror = (err) => {
    console.error('WebSocket Error:', err)
    ws.close()
  }
}

const handleConnect = async () => {
  try {
    const res = await fetch('http://localhost:8024/camera/connect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ip: "192.168.30.170" })
    })
    console.log("Connect command sent:", await res.json())
  } catch (e) {
    console.error("Error connecting camera", e)
  }
}

const handleDisconnect = async () => {
  try {
    const res = await fetch('http://localhost:8024/camera/disconnect', { method: 'POST' })
    console.log("Disconnect command sent:", await res.json())
  } catch (e) {
    console.error("Error disconnecting camera", e)
  }
}

onMounted(() => {
  connectWebSocket()
})

onUnmounted(() => {
  if (reconnectTimeout) clearTimeout(reconnectTimeout)
  if (ws) ws.close()
})
</script>

<style>
:root {
  --bg-color: #0f172a;
  --surface-color: rgba(30, 41, 59, 0.7);
  --surface-border: rgba(255, 255, 255, 0.1);
  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --accent-color: #3b82f6;
  --accent-hover: #60a5fa;
  --success: #10b981;
  --danger: #ef4444;
}

body {
  margin: 0;
  padding: 0;
  font-family: 'Inter', sans-serif;
  background-color: var(--bg-color);
  background-image: 
    radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.15) 0px, transparent 50%),
    radial-gradient(at 100% 100%, rgba(16, 185, 129, 0.1) 0px, transparent 50%);
  color: var(--text-primary);
  min-height: 100vh;
}

.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

header {
  padding: 1.5rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--surface-border);
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(12px);
  z-index: 10;
}

.logo {
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: 1px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo span {
  color: var(--accent-color);
}

.status-badge {
  padding: 0.5rem 1rem;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(239, 68, 68, 0.1);
  color: var(--danger);
  border: 1px solid rgba(239, 68, 68, 0.2);
  transition: all 0.3s ease;
}

.status-badge.connected {
  background: rgba(16, 185, 129, 0.1);
  color: var(--success);
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: currentColor;
  box-shadow: 0 0 8px currentColor;
}

.status-badge.connected .status-dot {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.2); }
  100% { opacity: 1; transform: scale(1); }
}

main {
  flex: 1;
  padding: 2rem;
  display: flex;
  gap: 2rem;
  max-width: 1600px;
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
}

.side-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}
</style>

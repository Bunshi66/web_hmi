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

    <nav class="tabs-nav">
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'stream' }" 
        @click="activeTab = 'stream'"
      >Stream</button>
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'settings' }" 
        @click="activeTab = 'settings'"
      >Settings</button>
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'ai' }" 
        @click="activeTab = 'ai'"
      >AI Models</button>
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'control' }" 
        @click="activeTab = 'control'"
      >Control</button>
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'logs' }" 
        @click="loadLogs"
      >Logs</button>
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'archive' }" 
        @click="activeTab = 'archive'"
      >Archive</button>
      
      <div class="auth-panel">
        <span class="auth-role" :class="roleClass">Role: {{ userRole }}</span>
        <button class="btn secondary" style="padding: 0.5rem 1rem; font-size: 0.875rem;" @click="showAuth = true">Login</button>
      </div>
    </nav>

    <!-- STREAM TAB -->
    <div v-show="activeTab === 'stream'" class="tab-content">
      <div style="flex: 2; display: flex; flex-direction: column; gap: 1rem;">
        <CameraStream :videoData="latestFrame" :fps="currentFps" />
        <div style="display: flex; justify-content: flex-end;">
          <button class="btn danger" style="background-color: #ef4444; border-color: #ef4444; color: white;" @click="saveManualDefect">Save Frame to Archive</button>
        </div>
      </div>

      <div class="side-panel">
        <Controls @connect="handleConnect" @disconnect="handleDisconnect" />
        <TelemetryPanel :status="status" />
      </div>
    </div>

    <!-- SETTINGS TAB -->
    <div v-show="activeTab === 'settings'" class="tab-content" style="display: flex; gap: 1rem; flex-wrap: wrap;">
      <div class="card" style="flex: 1; min-width: 300px;">
        <h3>Camera Image Settings</h3>
        <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">Configure Hikrobot camera exposure and gain.</p>
        
        <div v-if="userRole === 'Operator'" class="warning-alert">
          <strong>Access Denied:</strong> Operators cannot modify camera settings. Please login as Engineer or Admin.
        </div>

        <div style="display: flex; flex-direction: column; gap: 1rem; max-width: 400px; margin-top: 1rem;" :class="{ disabled: userRole === 'Operator' }">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="color: var(--text-primary);">Exposure Time (us)</span>
            <input type="number" v-model.number="settingsForm.exposure" :disabled="userRole === 'Operator'" style="background: rgba(0,0,0,0.2); border: 1px solid var(--surface-border); color: white; padding: 0.5rem; border-radius: 4px; width: 100px;">
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="color: var(--text-primary);">Gain</span>
            <input type="number" v-model.number="settingsForm.gain" step="0.1" :disabled="userRole === 'Operator'" style="background: rgba(0,0,0,0.2); border: 1px solid var(--surface-border); color: white; padding: 0.5rem; border-radius: 4px; width: 100px;">
          </div>
          <button class="btn" style="margin-top: 1rem;" :disabled="userRole === 'Operator'" @click="applySettings">Apply Image Settings</button>
        </div>
      </div>

      <div class="card" style="flex: 1; min-width: 300px;">
        <h3>Connection Settings</h3>
        <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">Configure auto-reconnect and target IP.</p>

        <div v-if="userRole === 'Operator'" class="warning-alert">
          <strong>Access Denied:</strong> Operators cannot modify connection settings.
        </div>

        <div style="display: flex; flex-direction: column; gap: 1rem; max-width: 400px; margin-top: 1rem;" :class="{ disabled: userRole === 'Operator' }">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="color: var(--text-primary);">Target Camera IP</span>
            <input type="text" v-model="connectionForm.target_ip" :disabled="userRole === 'Operator'" style="background: rgba(0,0,0,0.2); border: 1px solid var(--surface-border); color: white; padding: 0.5rem; border-radius: 4px; width: 150px;">
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="color: var(--text-primary);">Auto-Reconnect</span>
            <input type="checkbox" v-model="connectionForm.auto_reconnect" :disabled="userRole === 'Operator'" style="width: 20px; height: 20px;">
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="color: var(--text-primary);">Interval (sec)</span>
            <input type="number" v-model.number="connectionForm.reconnect_interval" :disabled="userRole === 'Operator'" style="background: rgba(0,0,0,0.2); border: 1px solid var(--surface-border); color: white; padding: 0.5rem; border-radius: 4px; width: 100px;">
          </div>
          <button class="btn" style="margin-top: 1rem;" :disabled="userRole === 'Operator'" @click="applyConnectionSettings">Save Connection Settings</button>
        </div>
      </div>
    </div>

    <!-- AI MODELS TAB -->
    <div v-show="activeTab === 'ai'" class="tab-content" style="display: flex; gap: 1rem; flex-wrap: wrap;">
      <div class="card" style="flex: 1; min-width: 300px; max-width: 600px;">
        <h3>YOLO11 Model Configuration</h3>
        <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">Select the active Neural Network model for telemetry overlay and configure inference parameters.</p>

        <div v-if="userRole === 'Operator'" class="warning-alert">
          <strong>Access Denied:</strong> Operators cannot modify AI models.
        </div>

        <div style="display: flex; flex-direction: column; gap: 1rem; max-width: 500px; margin-top: 1rem;" :class="{ disabled: userRole === 'Operator' }">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="color: var(--text-primary);">Active Model</span>
            <select v-model="appSettingsForm.active_ml_model" :disabled="userRole === 'Operator'" style="background: rgba(0,0,0,0.2); border: 1px solid var(--surface-border); color: white; padding: 0.5rem; border-radius: 4px; width: 150px;">
              <option value="detection">Detection</option>
              <option value="segmentation">Segmentation</option>
              <option value="classification">Classification</option>
            </select>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="color: var(--text-primary);">Confidence Threshold</span>
            <div style="display: flex; gap: 1rem; align-items: center;">
              <input type="range" v-model.number="appSettingsForm.confidence_threshold" min="0.1" max="0.99" step="0.01" :disabled="userRole === 'Operator'" style="width: 150px;">
              <span style="width: 40px; text-align: right;">{{ appSettingsForm.confidence_threshold }}</span>
            </div>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="color: var(--text-primary);">IOU Threshold</span>
            <div style="display: flex; gap: 1rem; align-items: center;">
              <input type="range" v-model.number="appSettingsForm.iou_threshold" min="0.1" max="0.99" step="0.01" :disabled="userRole === 'Operator'" style="width: 150px;">
              <span style="width: 40px; text-align: right;">{{ appSettingsForm.iou_threshold }}</span>
            </div>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="color: var(--text-primary);">Max Detections</span>
            <div style="display: flex; gap: 1rem; align-items: center;">
              <input type="range" v-model.number="appSettingsForm.max_det" min="1" max="300" step="1" :disabled="userRole === 'Operator'" style="width: 150px;">
              <span style="width: 40px; text-align: right;">{{ appSettingsForm.max_det }}</span>
            </div>
          </div>
          
          <button class="btn" style="margin-top: 1rem;" :disabled="userRole === 'Operator'" @click="applyAppSettings">Save AI Settings</button>
        </div>
      </div>
    </div>

    <!-- CONTROL TAB -->
    <div v-show="activeTab === 'control'" class="tab-content">
      <ControlPanel :userRole="userRole" />
    </div>

    <!-- LOGS TAB -->
    <div v-show="activeTab === 'logs'" class="tab-content">
      <div class="card" style="flex: 1; display: flex; flex-direction: column;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
          <h3 style="margin: 0;">System Logs</h3>
          <button v-if="userRole !== 'Operator'" class="btn secondary" @click="downloadLogs" style="padding: 0.5rem 1rem; font-size: 0.875rem;">Download .txt</button>
        </div>
        
        <div style="flex: 1; background: #000; border-radius: 8px; padding: 1rem; font-family: monospace; color: var(--text-secondary); font-size: 0.85rem; overflow-y: auto; min-height: 400px;">
          <div v-for="(log, i) in systemLogs" :key="i">{{ log }}</div>
          <div v-if="serviceTelemetryData" style="color: var(--success); margin-top: 1rem;">
            -- Live Service Telemetry --<br>
            Processing Time: {{ serviceTelemetryData.processing_time_ms }} ms<br>
            Engine: {{ serviceTelemetryData.capture_engine }}
          </div>
          <span style="color: var(--accent-color);">_</span>
        </div>
      </div>
    </div>

    <!-- ARCHIVE TAB -->
    <div v-show="activeTab === 'archive'" class="tab-content">
      <Archive />
    </div>

    <LoginModal :show="showAuth" @close="showAuth = false" @role-selected="handleRoleChange" />

    <!-- Connection Lost Modal -->
    <div v-if="showConnectionLost" class="modal-overlay" @click="showConnectionLost = false">
      <div class="modal-content" @click.stop style="max-width: 400px; text-align: center; padding: 2rem; border-top: 4px solid #ef4444;">
        <h3 style="margin-top: 0; color: #ef4444;">Connection Lost</h3>
        <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">The connection to the camera has been lost. If auto-reconnect is enabled, the system will attempt to restore it automatically.</p>
        <button class="btn" style="width: 100%; background-color: #ef4444; border-color: #ef4444;" @click="showConnectionLost = false">Dismiss</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import CameraStream from './components/CameraStream.vue'
import Controls from './components/Controls.vue'
import TelemetryPanel from './components/TelemetryPanel.vue'
import LoginModal from './components/LoginModal.vue'
import Archive from './components/Archive.vue'
import ControlPanel from './components/ControlPanel.vue'

const activeTab = ref('stream')
const showAuth = ref(false)
const userRole = ref(localStorage.getItem('userRole') || 'Operator')

const videoData = ref(null)
const serviceTelemetryData = ref(null)
const fps = ref(0)
const status = ref({
  connected: false,
  ip: null,
  temperature: null,
  exposure: 5000,
  gain: 1.0
})

const settingsForm = ref({
  exposure: 5000,
  gain: 1.0
})

const connectionForm = ref({
  target_ip: '192.168.1.64',
  auto_reconnect: true,
  reconnect_interval: 5
})

const appSettingsForm = ref({
  active_ml_model: 'detection',
  confidence_threshold: 0.5,
  iou_threshold: 0.45,
  max_det: 100
})

const showConnectionLost = ref(false)

watch(() => status.value.connected, (newVal, oldVal) => {
  if (oldVal === true && newVal === false) {
    showConnectionLost.value = true
  }
})

const systemLogs = ref([])

let ws = null
let framesReceived = 0
let lastFpsTime = Date.now()
let reconnectTimeout = null

const roleClass = computed(() => {
  if (userRole.value === 'Admin') return 'role-admin'
  if (userRole.value === 'Engineer') return 'role-engineer'
  return 'role-operator'
})

const handleRoleChange = async (role) => {
  userRole.value = role
  localStorage.setItem('userRole', role)
  // Request the backend to log this role change
  try {
    await fetch('/camera/log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: `Role changed to ${role}` })
    })
    loadLogs()
  } catch (e) {}
}

const loadLogs = async () => {
  activeTab.value = 'logs'
  try {
    const res = await fetch('/camera/logs')
    const data = await res.json()
    systemLogs.value = data.logs
  } catch (error) {
    console.error('Failed to trigger capture:', error)
    alert('Failed to trigger capture')
  }
}

const saveManualDefect = async () => {
  try {
    const response = await fetch('/camera/manual-defect', { method: 'POST' })
    if (response.ok) {
      alert('Save frame requested successfully!')
    } else {
      alert('Failed to save frame')
    }
  } catch (error) {
    console.error('Error triggering manual save:', error)
    alert('Error triggering manual save')
  }
}

const downloadLogs = async () => {
  const content = systemLogs.value.join('\n')
  const blob = new Blob([content], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'web_hmi_logs.txt'
  a.click()
  URL.revokeObjectURL(url)
}

const applySettings = async () => {
  try {
    const res = await fetch('/camera/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settingsForm.value)
    })
    const data = await res.json()
    if (data.success) {
      alert('Settings applied successfully')
    } else {
      alert('Failed to apply settings')
    }
  } catch (e) {
    console.error("Error applying settings", e)
  }
}

const loadConnectionSettings = async () => {
  try {
    const res = await fetch('/camera/settings/connection')
    const data = await res.json()
    connectionForm.value = data
  } catch (e) {
    console.error("Failed to load connection settings", e)
  }
}

const applyConnectionSettings = async () => {
  try {
    const res = await fetch('/camera/settings/connection', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(connectionForm.value)
    })
    const data = await res.json()
    if (data.success) {
      alert('Connection settings applied successfully')
    } else {
      alert('Failed to apply connection settings')
    }
  } catch (e) {
    console.error("Error applying connection settings", e)
  }
}

const loadAppSettings = async () => {
  try {
    const res = await fetch('/camera/settings/app')
    const data = await res.json()
    appSettingsForm.value.confidence_threshold = data.confidence_threshold || 0.5
    appSettingsForm.value.iou_threshold = data.iou_threshold || 0.45
    appSettingsForm.value.max_det = data.max_det || 100
  } catch (error) {
    console.error("Failed to load app settings", e)
  }
}

const applyAppSettings = async () => {
  try {
    const res = await fetch('/camera/settings/app', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(appSettingsForm.value)
    })
    const data = await res.json()
    if (data.success) {
      alert('AI Model settings applied successfully')
    } else {
      alert('Failed to apply AI settings')
    }
  } catch (e) {
    console.error("Error applying app settings", e)
  }
}

const connectWebSocket = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/camera/ws`
  
  console.log(`Connecting to ${wsUrl}...`)
  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    console.log('WebSocket Connected')
    status.value.connected = true
    ws.send(JSON.stringify({ action: "subscribe", types: ["video", "telemetry"] }))
  }

  ws.onmessage = async (event) => {
    try {
      if (event.data instanceof Blob) {
        const arrayBuffer = await event.data.arrayBuffer()
        const dataView = new DataView(arrayBuffer)
        const metaLen = dataView.getUint32(0, true) // little endian
        
        const metaBytes = new Uint8Array(arrayBuffer, 4, metaLen)
        const metaStr = new TextDecoder().decode(metaBytes)
        const data = JSON.parse(metaStr)
        
        const imgBytes = new Uint8Array(arrayBuffer, 4 + metaLen)
        const blob = new Blob([imgBytes], { type: 'image/jpeg' })
        const url = URL.createObjectURL(blob)
        
        if (data.action === "video") {
          // Release old URL to avoid memory leak
          if (videoData.value && videoData.value.url) {
            URL.revokeObjectURL(videoData.value.url)
          }
          data.url = url
          
          videoData.value = data
          serviceTelemetryData.value = data.service_telemetry
          if (data.camera_temp !== undefined) {
            status.value.temperature = data.camera_temp
          }
          framesReceived++
          
          const now = Date.now()
          if (now - lastFpsTime >= 1000) {
            fps.value = framesReceived
            framesReceived = 0
            lastFpsTime = now
          }
        }
      } else {
        const data = JSON.parse(event.data)
        if (data.action === "telemetry" && data.status) {
          status.value = { ...status.value, ...data.status }
        }
      }
    } catch (e) {
      console.error("Error parsing message", e)
    }
  }

  ws.onclose = () => {
    console.log('WebSocket Disconnected')
    status.value.connected = false
    videoData.value = null
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
    const res = await fetch('/camera/connect', {
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
    const res = await fetch('/camera/disconnect', { method: 'POST' })
    console.log("Disconnect command sent:", await res.json())
  } catch (e) {
    console.error("Error disconnecting camera", e)
  }
}

onMounted(() => {
  connectWebSocket()
  loadConnectionSettings()
  loadAppSettings()
})

onUnmounted(() => {
  if (reconnectTimeout) clearTimeout(reconnectTimeout)
  if (ws) ws.close()
})
</script>

<style>
/* Previous CSS remains */
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
  --warning: #f59e0b;
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

.tabs-nav {
  display: flex;
  background: rgba(15, 23, 42, 0.9);
  border-bottom: 1px solid var(--surface-border);
  padding: 0 2rem;
  align-items: center;
}

.tab-btn {
  background: transparent;
  color: var(--text-secondary);
  border: none;
  padding: 1rem 1.5rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s ease;
  font-family: inherit;
}

.tab-btn:hover {
  color: var(--text-primary);
}

.tab-btn.active {
  color: var(--accent-color);
  border-bottom-color: var(--accent-color);
}

.auth-panel {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.auth-role {
  font-size: 0.875rem;
  font-weight: 600;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  border: 1px solid transparent;
}

.role-operator { background: rgba(59, 130, 246, 0.1); color: var(--accent-color); border-color: rgba(59, 130, 246, 0.2); }
.role-engineer { background: rgba(16, 185, 129, 0.1); color: var(--success); border-color: rgba(16, 185, 129, 0.2); }
.role-admin { background: rgba(245, 158, 11, 0.1); color: var(--warning); border-color: rgba(245, 158, 11, 0.2); }

.tab-content {
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

.card {
  background: var(--surface-color);
  border: 1px solid var(--surface-border);
  border-radius: 16px;
  padding: 1.5rem;
  backdrop-filter: blur(16px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}

.card h3 {
  margin: 0 0 1.2rem 0;
  font-size: 1.1rem;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn {
  background: var(--accent-color);
  color: white;
  border: none;
  padding: 0.875rem 1.5rem;
  border-radius: 8px;
  font-weight: 600;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.btn:hover:not(:disabled) {
  background: var(--accent-hover);
  transform: translateY(-2px);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn.secondary {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

.btn.secondary:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.15);
}

.warning-alert {
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.2);
  color: var(--warning);
  padding: 1rem;
  border-radius: 8px;
  font-size: 0.9rem;
}

.disabled {
  opacity: 0.5;
  pointer-events: none;
}

@media (max-width: 900px) {
  .tab-content {
    flex-direction: column;
    padding: 1rem;
    gap: 1rem;
  }
}
</style>

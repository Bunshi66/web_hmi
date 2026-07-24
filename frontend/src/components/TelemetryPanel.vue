<template>
  <div class="card">
    <h3>
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
      </svg>
      Telemetry
    </h3>
    <div class="telemetry-grid">
      <div class="telemetry-item">
        <div class="telemetry-label">Status</div>
        <div 
          class="telemetry-value" 
          :style="{ color: status.connected ? 'var(--success)' : 'var(--text-secondary)' }"
        >
          {{ status.connected ? 'Active' : 'Offline' }}
        </div>
      </div>
      <div class="telemetry-item">
        <div class="telemetry-label">IP Address</div>
        <div class="telemetry-value" style="font-size: 1.1rem;">{{ status.ip || '-' }}</div>
      </div>
      <div class="telemetry-item">
        <div class="telemetry-label">Temperature</div>
        <div class="telemetry-value">{{ status.temperature ? status.temperature.toFixed(1) + '°C' : '-' }}</div>
      </div>
      <div class="telemetry-item">
        <div class="telemetry-label">Exposure</div>
        <div class="telemetry-value">{{ status.exposure || '0' }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  status: {
    type: Object,
    default: () => ({
      connected: false,
      ip: null,
      temperature: null,
      exposure: 0
    })
  }
})
</script>

<style scoped>
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

.telemetry-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.telemetry-item {
  background: rgba(0, 0, 0, 0.2);
  padding: 1rem;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.telemetry-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 0.5rem;
}

.telemetry-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--accent-color);
}
</style>

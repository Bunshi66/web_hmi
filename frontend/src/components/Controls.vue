<template>
  <div class="card controls">
    <h3>
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"></path>
      </svg>
      Controls
    </h3>
    <button class="btn" @click="$emit('connect')">Connect Camera</button>
    <button class="btn secondary" @click="$emit('disconnect')">Disconnect</button>
  </div>
</template>

<script setup>
defineEmits(['connect', 'disconnect'])
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

.controls {
  display: flex;
  flex-direction: column;
  gap: 1rem;
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

.btn:hover {
  background: var(--accent-hover);
  transform: translateY(-2px);
}

.btn:active {
  transform: translateY(0);
}

.btn.secondary {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

.btn.secondary:hover {
  background: rgba(255, 255, 255, 0.15);
}
</style>

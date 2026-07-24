<template>
  <div class="video-container">
    <div class="video-header">
      <div class="video-title">Live Camera Stream</div>
      <div class="fps-counter">{{ fps }} FPS</div>
    </div>
    <div class="video-wrapper">
      <div v-if="!frame" class="no-signal">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7"></path>
        </svg>
        <span>Waiting for video stream...</span>
      </div>
      <img v-else :src="`data:image/jpeg;base64,${frame}`" alt="Live Stream" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  frame: {
    type: String,
    default: null
  },
  fps: {
    type: Number,
    default: 0
  }
})
</script>

<style scoped>
.video-container {
  flex: 2;
  background: var(--surface-color);
  border: 1px solid var(--surface-border);
  border-radius: 20px;
  overflow: hidden;
  backdrop-filter: blur(16px);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  position: relative;
}

.video-header {
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--surface-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.video-title {
  font-weight: 600;
  font-size: 1.1rem;
}

.fps-counter {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.video-wrapper {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  min-height: 400px;
}

img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  transition: opacity 0.3s ease;
}

.no-signal {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: var(--text-secondary);
  font-size: 1.2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.no-signal svg {
  width: 48px;
  height: 48px;
  opacity: 0.5;
}
</style>

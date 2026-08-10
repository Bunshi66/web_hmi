<template>
  <div class="video-container">
    <div class="video-header">
      <div class="video-title">Live Camera Stream</div>
      <div class="fps-counter">{{ fps }} FPS</div>
    </div>
    <div class="video-wrapper">
      <div v-if="!videoData || !videoData.frame" class="no-signal">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7"></path>
        </svg>
        <span>Waiting for video stream...</span>
      </div>
      
      <div v-else class="stream-content">
        <!-- The actual video frame -->
        <img :src="`data:image/jpeg;base64,${videoData.frame}`" alt="Live Stream" />
        
        <!-- The SVG overlay for telemetry -->
        <svg 
          v-if="videoData.overlay_telemetry" 
          class="telemetry-overlay"
          :viewBox="`0 0 ${videoData.width || 640} ${videoData.height || 480}`"
          preserveAspectRatio="xMidYMid meet"
        >
          <!-- Crosshair -->
          <g v-if="videoData.overlay_telemetry.crosshair" class="crosshair">
            <line 
              :x1="videoData.overlay_telemetry.crosshair.x - 20" 
              :y1="videoData.overlay_telemetry.crosshair.y" 
              :x2="videoData.overlay_telemetry.crosshair.x + 20" 
              :y2="videoData.overlay_telemetry.crosshair.y" 
            />
            <line 
              :x1="videoData.overlay_telemetry.crosshair.x" 
              :y1="videoData.overlay_telemetry.crosshair.y - 20" 
              :x2="videoData.overlay_telemetry.crosshair.x" 
              :y2="videoData.overlay_telemetry.crosshair.y + 20" 
            />
          </g>

          <!-- Bounding Boxes -->
          <g v-for="(box, i) in videoData.overlay_telemetry.bboxes" :key="i">
            <rect 
              :x="box.x" 
              :y="box.y" 
              :width="box.w" 
              :height="box.h" 
              class="bbox" 
            />
            <text :x="box.x" :y="box.y - 5" class="bbox-label">{{ box.label }}</text>
          </g>
        </svg>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  videoData: {
    type: Object,
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
  overflow: hidden;
}

.stream-content {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  transition: opacity 0.3s ease;
}

.telemetry-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none; /* Let clicks pass through if needed */
}

.crosshair line {
  stroke: #10b981;
  stroke-width: 2;
  opacity: 0.8;
}

.bbox {
  fill: none;
  stroke: #ef4444;
  stroke-width: 3;
}

.bbox-label {
  fill: #ef4444;
  font-size: 16px;
  font-family: monospace;
  font-weight: bold;
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

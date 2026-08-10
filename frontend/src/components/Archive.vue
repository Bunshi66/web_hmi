<template>
  <div class="card" style="flex: 1; display: flex; flex-direction: column;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
      <h3 style="margin: 0;">Defects Archive</h3>
      <button class="btn secondary" @click="loadDefects" style="padding: 0.5rem 1rem; font-size: 0.875rem;">Refresh</button>
    </div>

    <div v-if="loading" style="text-align: center; color: var(--text-secondary); padding: 2rem;">Loading...</div>
    
    <div v-else-if="defects.length === 0" style="text-align: center; color: var(--text-secondary); padding: 2rem;">
      No defects found in the database.
    </div>

    <div v-else style="overflow-x: auto;">
      <table class="archive-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Timestamp</th>
            <th>Type</th>
            <th>Confidence</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="defect in defects" :key="defect.id">
            <td>#{{ defect.id }}</td>
            <td>{{ new Date(defect.timestamp).toLocaleString() }}</td>
            <td><span class="badge">{{ defect.defect_type }}</span></td>
            <td>{{ (defect.confidence * 100).toFixed(1) }}%</td>
            <td>
              <button class="btn view-btn" @click="viewDefect(defect)">View Image</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal for viewing image -->
    <div v-if="selectedDefect" class="modal-overlay" @click="selectedDefect = null">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>Defect #{{ selectedDefect.id }} - {{ new Date(selectedDefect.timestamp).toLocaleString() }}</h3>
          <button class="close-btn" @click="selectedDefect = null">×</button>
        </div>
        <div class="modal-body">
          <div class="image-container">
            <img :src="selectedDefect.image_url" alt="Defect" />
            <svg 
              v-if="selectedDefect.bbox_data" 
              class="telemetry-overlay"
              viewBox="0 0 640 480"
              preserveAspectRatio="xMidYMid meet"
            >
              <rect 
                :x="selectedDefect.bbox_data.x" 
                :y="selectedDefect.bbox_data.y" 
                :width="selectedDefect.bbox_data.w" 
                :height="selectedDefect.bbox_data.h" 
                class="bbox" 
              />
            </svg>
          </div>
          <div style="margin-top: 1rem; color: var(--text-secondary);">
            Type: {{ selectedDefect.defect_type }} | Confidence: {{ (selectedDefect.confidence * 100).toFixed(1) }}%
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const defects = ref([])
const loading = ref(true)
const selectedDefect = ref(null)

const loadDefects = async () => {
  loading.value = true
  try {
    const res = await fetch('/camera/defects')
    const data = await res.json()
    defects.value = data.items
  } catch (e) {
    console.error("Failed to load defects", e)
  } finally {
    loading.value = false
  }
}

const viewDefect = (defect) => {
  selectedDefect.value = defect
}

onMounted(() => {
  loadDefects()
})
</script>

<style scoped>
.archive-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.archive-table th {
  padding: 1rem;
  border-bottom: 1px solid var(--surface-border);
  color: var(--text-secondary);
  font-weight: 600;
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 1px;
}

.archive-table td {
  padding: 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
}

.archive-table tr:hover td {
  background: rgba(255, 255, 255, 0.02);
}

.badge {
  background: rgba(239, 68, 68, 0.15);
  color: var(--danger);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 600;
}

.view-btn {
  padding: 0.4rem 0.8rem;
  font-size: 0.85rem;
  background: rgba(59, 130, 246, 0.2);
  color: var(--accent-color);
}

.view-btn:hover {
  background: rgba(59, 130, 246, 0.4);
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-content {
  background: #0f172a;
  border: 1px solid var(--surface-border);
  border-radius: 12px;
  width: 90%;
  max-width: 800px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.modal-header {
  padding: 1.5rem;
  border-bottom: 1px solid var(--surface-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
}

.close-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 1.5rem;
  cursor: pointer;
}

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
}

.image-container {
  position: relative;
  width: 100%;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  justify-content: center;
}

.image-container img {
  max-width: 100%;
  max-height: 60vh;
  object-fit: contain;
}

.telemetry-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.bbox {
  fill: none;
  stroke: #ef4444;
  stroke-width: 3;
}
</style>

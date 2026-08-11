<template>
  <div class="card" style="flex: 1;">
    <h3>Discrete IO Control</h3>
    <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">Configure and control physical outputs of the camera.</p>
    
    <div v-if="userRole === 'Operator'" class="warning-alert">
      <strong>Access Denied:</strong> Operators cannot control hardware IO. Please login as Engineer or Admin.
    </div>

    <div style="display: flex; flex-direction: column; gap: 2rem; max-width: 500px; margin-top: 1rem;" :class="{ disabled: userRole === 'Operator' }">
      
      <!-- Configure Section -->
      <div class="control-section">
        <h4 style="margin-top: 0; color: var(--accent-color);">1. Configure Output Line</h4>
        <div class="form-group">
          <label>Line Selector</label>
          <select v-model="configForm.line_name" class="styled-input">
            <option value="Line0">Line 0</option>
            <option value="Line1">Line 1</option>
            <option value="Line2">Line 2</option>
          </select>
        </div>
        <div class="form-group">
          <label>Output Name</label>
          <select v-model="configForm.output_name" class="styled-input">
            <option value="UserOutput1">UserOutput1</option>
            <option value="UserOutput2">UserOutput2</option>
            <option value="UserOutput3">UserOutput3</option>
          </select>
        </div>
        <button class="btn" @click="configureIO">Configure IO</button>
      </div>

      <!-- Set Section -->
      <div class="control-section">
        <h4 style="margin-top: 0; color: var(--success);">2. Control Signal</h4>
        <div class="form-group">
          <label>Output Name</label>
          <select v-model="setForm.output_name" class="styled-input">
            <option value="UserOutput1">UserOutput1</option>
            <option value="UserOutput2">UserOutput2</option>
            <option value="UserOutput3">UserOutput3</option>
          </select>
        </div>
        
        <div style="display: flex; gap: 1rem; margin-top: 1rem;">
          <button class="btn success-btn" @click="setIO(true)" style="flex: 1;">Turn ON (High)</button>
          <button class="btn danger-btn" @click="setIO(false)" style="flex: 1;">Turn OFF (Low)</button>
        </div>
      </div>
      
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  userRole: {
    type: String,
    default: 'Operator'
  }
})

const configForm = ref({
  line_name: 'Line2',
  output_name: 'UserOutput1'
})

const setForm = ref({
  output_name: 'UserOutput1'
})

const configureIO = async () => {
  try {
    const res = await fetch('/camera/io/configure', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(configForm.value)
    })
    const data = await res.json()
    if (data.success) {
      alert(`Successfully configured ${configForm.value.line_name} as ${configForm.value.output_name}`)
    } else {
      alert('Failed to configure IO')
    }
  } catch (e) {
    console.error("Error configuring IO", e)
    alert("Network error while configuring IO")
  }
}

const setIO = async (state) => {
  try {
    const res = await fetch('/camera/io/set', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        state: state,
        output_name: setForm.value.output_name
      })
    })
    const data = await res.json()
    if (data.success) {
      console.log(`Set ${setForm.value.output_name} to ${state}`)
    } else {
      alert('Failed to set IO state')
    }
  } catch (e) {
    console.error("Error setting IO", e)
  }
}
</script>

<style scoped>
.control-section {
  background: rgba(0, 0, 0, 0.2);
  padding: 1.5rem;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.form-group {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.form-group label {
  color: var(--text-primary);
  font-weight: 500;
}

.styled-input {
  background: rgba(0,0,0,0.4);
  border: 1px solid var(--surface-border);
  color: white;
  padding: 0.5rem;
  border-radius: 6px;
  width: 150px;
  font-family: inherit;
}

.styled-input:focus {
  outline: none;
  border-color: var(--accent-color);
}

.success-btn {
  background: var(--success);
}
.success-btn:hover {
  background: #059669;
}

.danger-btn {
  background: var(--danger);
}
.danger-btn:hover {
  background: #dc2626;
}
</style>

<template>
  <div v-if="show" class="modal-overlay" @click.self="close">
    <div class="modal-content card">
      <h3>Select Role</h3>
      <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">Choose a role to determine your access level.</p>
      
      <div class="role-list">
        <button 
          class="btn secondary role-btn" 
          @click="selectRole('Operator')"
        >
          <div class="role-title">Operator</div>
          <div class="role-desc">View stream and telemetry only.</div>
        </button>
        
        <button 
          class="btn secondary role-btn" 
          @click="selectRole('Engineer')"
        >
          <div class="role-title">Engineer</div>
          <div class="role-desc">Can configure camera settings and download logs.</div>
        </button>
        
        <button 
          class="btn secondary role-btn" 
          @click="selectRole('Admin')"
        >
          <div class="role-title">Admin</div>
          <div class="role-desc">Full access to all system features.</div>
        </button>
      </div>
      
      <button class="btn" style="margin-top: 1.5rem; width: 100%;" @click="close">Cancel</button>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'

const props = defineProps({
  show: Boolean
})

const emit = defineEmits(['close', 'role-selected'])

const selectRole = (role) => {
  emit('role-selected', role)
  close()
}

const close = () => {
  emit('close')
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-content {
  width: 90%;
  max-width: 400px;
  background: var(--bg-color);
  padding: 2rem;
}

.role-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.role-btn {
  text-align: left;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.role-btn:hover {
  background: rgba(59, 130, 246, 0.1);
  border-color: rgba(59, 130, 246, 0.3);
}

.role-title {
  font-weight: 700;
  color: var(--text-primary);
}

.role-desc {
  font-size: 0.8rem;
  font-weight: 400;
  color: var(--text-secondary);
}
</style>
